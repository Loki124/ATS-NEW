"""V2 权限系统 ViewSets + function views."""
import base64
import binascii
import json

from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError
from rest_framework import status as http_status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets
from django.shortcuts import get_object_or_404

from .models_permission_v2 import (
    PermissionResource, PermissionTemplate, RoleV2, RolePermissionV2,
    ManagementUnit, UserRoleV2, ManagementUnitMember,
)
# (Tier 3) DataPermissionRule 行级镜像已移除; 列级规则由 field_acl / enforcement 直接消费.
from .permissions_v2 import V2Permission
from .scope_resolver import resolve_scope, compile_data_range_q, _pick_app_json
from apps.common.views import EnvelopeReadOnlyMixin, EnvelopeWriteMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response


class PermissionResourceViewSet(EnvelopeReadOnlyMixin, viewsets.ReadOnlyModelViewSet):
    queryset = PermissionResource.objects.filter(status=1)
    permission_classes = [V2Permission]
    pagination_class = StandardResultsSetPagination  # per P1 audit 恢复服务端分页
    filterset_fields = ['module', 'resource_type']
    search_fields = ['resource_code', 'resource_name']

    def get_serializer_class(self):
        from .serializers_permission_v2 import PermissionResourceSerializer
        return PermissionResourceSerializer

    def list(self, request, *args, **kwargs):
        """T30.176: 包 {success, data} 包装层, 对齐其它 V2 endpoint (menus/functions/mous) 与 FE helper 期望. per P1 audit 恢复服务端分页."""
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return success_response(serializer.data)


class PermissionTemplateViewSet(EnvelopeReadOnlyMixin, viewsets.ReadOnlyModelViewSet):
    queryset = PermissionTemplate.objects.filter(status=1)
    permission_classes = [V2Permission]
    pagination_class = StandardResultsSetPagination  # per P1 audit 恢复服务端分页
    filterset_fields = ['is_system']

    def get_serializer_class(self):
        from .serializers_permission_v2 import PermissionTemplateSerializer
        return PermissionTemplateSerializer

    def list(self, request, *args, **kwargs):
        """T30.176: 包 {success, data} 包装层, 对齐其它 V2 endpoint. per P1 audit 恢复服务端分页."""
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return success_response(serializer.data)


class RoleViewSet(viewsets.ModelViewSet):
    queryset = RoleV2.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:role:list'
    pagination_class = StandardResultsSetPagination  # per P1 audit 恢复服务端分页
    search_fields = ['role_code', 'role_name']
    filterset_fields = ['status', 'is_system']

    def get_serializer_class(self):
        from .serializers_permission_v2 import RoleSerializer
        return RoleSerializer

    def list(self, request, *args, **kwargs):
        """T30.176: 包 {success, data} 包装层, 对齐其它 V2 endpoint 与 FE helper 期望. per P1 audit 恢复服务端分页."""
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return success_response(
            serializer.data,
            status_code=http_status.HTTP_201_CREATED,
            headers=headers,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(serializer.data)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def clone_from_template(self, request):
        """POST /roles/clone-from-template/
        body: {template_code, role_code, role_name, custom_permissions?: {add:[], remove:[]}}
        """
        body = request.data
        template_code = body.get('template_code')
        new_role_code = body.get('role_code')
        new_role_name = body.get('role_name')
        if not all([template_code, new_role_code, new_role_name]):
            return Response(
                {'success': False, 'message': 'template_code/role_code/role_name 必填'},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        template = PermissionTemplate.objects.filter(
            template_code=template_code, status=1
        ).first()
        if not template:
            return Response(
                {'success': False, 'message': f'Template {template_code} 不存在'},
                status=http_status.HTTP_404_NOT_FOUND,
            )
        if RoleV2.objects.filter(role_code=new_role_code, system_code='recruit').exists():
            return Response(
                {'success': False, 'message': f'角色 {new_role_code} 已存在'},
                status=http_status.HTTP_409_CONFLICT,
            )

        # 1. 新建 role
        role = RoleV2.objects.create(
            system_code='recruit',
            role_code=new_role_code,
            role_name=new_role_name,
            template_code=template_code,
            description=f'从 {template_code} 复制于 {request.user.username}',
        )
        # 2. permission_codes: 模板 + 加 - 删
        codes = list(template.permission_codes or [])
        custom = body.get('custom_permissions') or {}
        codes = [c for c in codes if c not in (custom.get('remove') or [])]
        codes = list(set(codes + (custom.get('add') or [])))
        # 3. 批量插 role_permission
        if codes:
            RolePermissionV2.objects.bulk_create([
                RolePermissionV2(role_code=new_role_code, resource_code=c, system_code='recruit')
                for c in codes
            ])
        return Response(
            self.get_serializer(role).data,
            status=http_status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='sync-resources')
    @transaction.atomic
    def sync_resources(self, request, pk=None):
        """POST /roles/{id}/sync-resources/
        body: {resource_codes: ["recruit:candidate:list", ...]}

        整组替换该 role 在 role_permission 表的所有记录.
        T29 fix: 之前 PUT /roles/{id}/ 的 permissionCodes 被 SerializerMethodField 忽略,
        用户保存后 checkbox 数据丢失. 此 action 显式写 role_permission 表.
        """
        role = self.get_object()
        codes = request.data.get('resource_codes') or []
        if not isinstance(codes, list):
            return Response(
                {'success': False, 'message': 'resource_codes 必须是数组'},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        # 去重 + 过滤空字符串
        codes = [str(c).strip() for c in codes if c and str(c).strip()]
        # 校验所有 code 在 permission_resource 表存在 (defense-in-depth)
        valid_codes = set(
            PermissionResource.objects.filter(
                resource_code__in=codes, status=1, system_code='recruit',
            ).values_list('resource_code', flat=True)
        )
        invalid = [c for c in codes if c not in valid_codes]
        if invalid:
            return Response(
                {'success': False, 'message': f'无效资源码: {invalid[:5]}', 'invalid': invalid},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        try:
            RolePermissionV2.objects.filter(
                role_code=role.role_code, system_code=role.system_code,
            ).delete()
            RolePermissionV2.objects.bulk_create([
                RolePermissionV2(role_code=role.role_code, resource_code=c, system_code=role.system_code)
                for c in codes
            ])
        except (OperationalError, ProgrammingError) as e:
            return Response(
                {'success': False, 'message': f'role_permission 表不可写: {e}'},
                status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        # 返回更新后的 role (含 permission_codes 重算)
        return Response({'success': True, 'data': self.get_serializer(role).data})

    # ------------------------------------------------------------------
    # 角色数据权限（数据权限向导）：按模块配置行级可见范围
    # GET  /roles/{id}/data-permissions/            读取 5 模块配置
    # POST /roles/{id}/data-permissions/            一次性保存 5 模块
    # GET  /roles/{id}/data-permissions/options/    模块×维度矩阵 + 维度值选项
    # ------------------------------------------------------------------
    @action(detail=True, methods=['get', 'post'], url_path='data-permissions')
    def data_permissions(self, request, pk=None):
        """GET  /roles/{id}/data-permissions/ 读取某角色的数据权限配置
        POST /roles/{id}/data-permissions/ 一次性保存某角色 5 模块数据权限。

        注意：GET 与 POST 必须合并到同一个 @action（同一 url_path），
        否则 DRF 路由会为同路径生成两条 pattern，Django 解析器命中首条
        GET-only 路由，导致 POST 返回 405。合并后单 pattern 的 method_map
        同时含 get/post，POST 即可正常进入本分支。
        """
        if request.method == 'POST':
            with transaction.atomic():
                role = self.get_object()
                from apps.data_permission.role_scope_api import upsert_modules, validate_modules
                modules = request.data.get('modules')
                reason = validate_modules(modules)
                if reason:
                    return Response(
                        {'success': False, 'message': reason},
                        status=http_status.HTTP_400_BAD_REQUEST,
                    )
                data = upsert_modules(role, modules, request.user)
                return Response({'success': True, 'data': data})
        # GET
        role = self.get_object()
        from apps.data_permission.role_scope_api import build_modules_response
        return Response({'success': True, 'data': build_modules_response(role)})

    @action(detail=True, methods=['get'], url_path='data-permissions/options')
    def data_permissions_options(self, request, pk=None):
        """GET /roles/{id}/data-permissions/options/ —— 模块×维度矩阵与维度值选项。"""
        from apps.data_permission.role_scope_api import options_payload
        return Response({'success': True, 'data': options_payload()})


class EnvelopeWriteMixin:
    """写操作统一包 {success, data} 信封 (对齐本项目 V2 read 接口与前端 r.data.data 约定).

    DRF 默认 create/update 直接返回序列化体, 不包信封会让前端 r.data.data 为 undefined.
    参考 apps.library.views.EnvelopeWriteMixin, 在 core 内独立完成以避免跨 app 耦合.
    """

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return success_response(serializer.data, status_code=http_status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_object()).data)

    def destroy(self, request, *args, **kwargs):
        self.perform_destroy(self.get_object())
        return success_response(None)


class ManagementUnitViewSet(EnvelopeWriteMixin, viewsets.ModelViewSet):
    queryset = ManagementUnit.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:mgmt_unit:list'
    pagination_class = StandardResultsSetPagination  # per P1 audit 恢复服务端分页
    filterset_fields = ['unit_type', 'status']

    def get_serializer_class(self):
        from .serializers_permission_v2 import ManagementUnitSerializer
        return ManagementUnitSerializer

    def list(self, request, *args, **kwargs):
        """T30.176: 包 {success, data} 包装层, 对齐其它 V2 endpoint.

        北森列表序: 显示顺序(display_order)升序, 同名回退 id. per P1 audit 恢复服务端分页.
        """
        qs = self.filter_queryset(self.get_queryset()).order_by('display_order', 'id')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return success_response(serializer.data)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """GET /api/v1/management-units/tree/ — 按 parent_id 返回嵌套树.

        方案 A(2026-09-15): 前端 MouManagement 树形视图(对齐北森图1/2)直接消费.
        """
        units = list(self.filter_queryset(self.get_queryset()))
        nodes = {
            u.id: {
                'id': u.id, 'unit_name': u.unit_name, 'unit_type': u.unit_type,
                'parent_id': u.parent_id, 'status': u.status,
                'code': u.code, 'description': u.description, 'display_order': u.display_order,
                'org_scope': u.org_scope,
                'data_range': u.data_range,
                'org_scopes': u.org_scopes, 'data_ranges': u.data_ranges,
                'person_data_range': u.person_data_range, 'person_data_ranges': u.person_data_ranges,
                'member_count': ManagementUnitMember.objects.filter(unit_id=u.id, status=1).count(),
                'children': [],
            }
            for u in units
        }
        roots = []
        for node in nodes.values():
            parent = nodes.get(node['parent_id'])
            if parent:
                parent['children'].append(node)
            else:
                roots.append(node)
        return Response({'success': True, 'data': roots})

    # NOTE(Tier 3): sync-data-rules 端点已移除 —— 行级范围不再镜像为 DataPermissionRule,
    # 改由 scope_resolver (scope_filter_q) 作为唯一真相源直接计算.

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        """GET/POST /api/v1/management-units/{id}/members/

        GET: 列出该单元启用的成员 (含 DEPT/USER/PERSON 名称回填);
        POST: 新增成员, 写入前按 (unit, member_type, 引用列) 查重返回 400 (避免 MySQL 多 nullable 列唯一约束陷阱).
        成员变更后由 scope_resolver 实时按管理单元解析范围, 无需重建镜像规则.
        """
        unit = self.get_object()
        if request.method == 'GET':
            qs = ManagementUnitMember.objects.filter(unit_id=unit.id, status=1)
            from .serializers_permission_v2 import ManagementUnitMemberSerializer
            return Response({'success': True, 'data': ManagementUnitMemberSerializer(qs, many=True).data})
        data = request.data or {}
        mt = data.get('member_type')
        app_code = data.get('app_code') or None
        ref_map = {'DEPT': 'department_id', 'USER': 'user_id', 'PERSON': 'person_id'}
        ref_col = ref_map.get(mt)
        ref_val = data.get(ref_col) if ref_col else None
        if not mt or ref_val in (None, ''):
            return Response({'success': False, 'message': 'member_type 与对应引用ID必填'},
                            status=http_status.HTTP_400_BAD_REQUEST)
        if ManagementUnitMember.objects.filter(unit_id=unit.id, member_type=mt,
                                                app_code=app_code,
                                                **{ref_col: ref_val}).exists():
            return Response({'success': False, 'message': '该成员已存在于此管理单元(同应用)'},
                            status=http_status.HTTP_400_BAD_REQUEST)
        member = ManagementUnitMember.objects.create(
            unit_id=unit.id, member_type=mt, app_code=app_code, **{ref_col: ref_val},
            include_children=int(data['include_children']) if data.get('include_children') is not None else 1,
            remark=data.get('remark') or '', status=1)
        from .serializers_permission_v2 import ManagementUnitMemberSerializer
        return Response({'success': True, 'data': ManagementUnitMemberSerializer(member).data},
                        status=http_status.HTTP_201_CREATED)

    @action(detail=True, methods=['put', 'patch', 'delete'], url_path='members/(?P<member_id>[^/.]+)')
    def member_detail(self, request, pk=None, member_id=None):
        """PUT/PATCH/DELETE /api/v1/management-units/{id}/members/{member_id}

        PUT/PATCH: 更新 include_children / remark;
        DELETE: 软删 (status=0) 并重建执行面规则.
        """
        unit = self.get_object()
        member = get_object_or_404(ManagementUnitMember, id=member_id, unit_id=unit.id)
        if request.method == 'DELETE':
            member.status = 0
            member.save()
            return Response({'success': True, 'data': None})
        data = request.data or {}
        if 'include_children' in data:
            # 注意: 不能用 `data['include_children'] or 1`, 否则传 0(不含子级)会被误判为缺失而默认回 1
            inc = data['include_children']
            member.include_children = int(inc) if inc is not None else 1
        if 'remark' in data:
            member.remark = data['remark']
        member.save()
        from .serializers_permission_v2 import ManagementUnitMemberSerializer
        return Response({'success': True, 'data': ManagementUnitMemberSerializer(member).data})

    @action(detail=True, methods=['get'], url_path='resolved-persons')
    def resolved_persons(self, request, pk=None):
        """GET /api/v1/management-units/{id}/resolved-persons/?app_code=xx

        需求 E(2026-09-18): 「配置人员范围」详情回显 —— 基于 person_data_range 的
        部门条件解析出实际相关人员(系统用户), 而非回显规则文字.

        仅按部门条件解析: 对 User.department_id 套用 compile_data_range_q(scope_field='department_id'),
        复用 scope_resolver 单一真相源(含子级 includeSub 与组间 op 合并).
        返回 {id, name, email, department_id, department_name}. 纯只读, 无副作用.
        无有效部门条件(未配置或维度暂不支持)时返回空列表, 避免 fail-safe 误放行全量用户.
        """
        from django.contrib.auth import get_user_model
        from django.db.models import Q
        from .models import Department

        unit = self.get_object()
        app_code = request.query_params.get('app_code') or None
        person_dr = _pick_app_json(
            getattr(unit, 'person_data_ranges', None),
            getattr(unit, 'person_data_range', None),
            app_code,
        )
        if not person_dr:
            return Response({'success': True, 'data': [], 'message': '（未配置人员范围）'})
        q = compile_data_range_q(person_dr, scope_field='department_id', creator_field='created_by')
        if q == Q():
            return Response({'success': True, 'data': [], 'message': '（未配置可解析的部门条件）'})
        User = get_user_model()
        users = User.objects.filter(q, deleted_at__isnull=True).select_related('department').order_by('id')
        rows = [{
            'id': u.id,
            'name': u.get_full_name() or u.username,
            'email': u.email or '',
            'department_id': u.department_id,
            'department_name': u.department.name if u.department_id else '',
        } for u in users]
        return Response({'success': True, 'data': rows})


class UserRoleViewSet(EnvelopeWriteMixin, viewsets.ModelViewSet):
    queryset = UserRoleV2.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:user_role:list'
    pagination_class = StandardResultsSetPagination  # per P1 audit 恢复服务端分页
    filterset_fields = ['user_id', 'role_code', 'system_code']

    def get_serializer_class(self):
        from .serializers_permission_v2 import UserRoleSerializer
        return UserRoleSerializer

    def list(self, request, *args, **kwargs):
        """T30.176: 包 {success, data} 包装层, 对齐其它 V2 endpoint. per P1 audit 恢复服务端分页."""
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return success_response(serializer.data)

    @action(detail=False, methods=['get'])
    def suggest_scope(self, request):
        """GET /user-roles/suggest-scope/?user_id=X&role_code=Y[&app_code=Z]

        方案 A(2026-09-15): 新增 app_code 透传, 按应用返回对应管理单元候选
        (resolve_scope 在 app_code 命中 UserRoleV2.app_data_scopes 时优先返回 per-app 范围).
        """
        user_id = request.query_params.get('user_id')
        role_code = request.query_params.get('role_code')
        app_code = request.query_params.get('app_code')
        if not (user_id and role_code):
            return Response({'success': False, 'message': 'user_id + role_code 必填'},
                            status=http_status.HTTP_400_BAD_REQUEST)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(pk=user_id).first()
        if not user:
            return Response({'success': False, 'message': 'user 不存在'},
                            status=http_status.HTTP_404_NOT_FOUND)
        try:
            scope = resolve_scope(user, app_code=app_code)
        except (OperationalError, ProgrammingError):
            scope = {}
        if scope.get('all'):
            return Response({
                'suggested_unit_ids': [],
                'derived_from': 'L2',
                'rationale': '角色 default=ALL, 不需要管理单元',
            })
        # 简化: 返回所有 unit 让 admin 选
        try:
            units = ManagementUnit.objects.filter(status=1).values('id', 'org_scope', 'unit_name')
        except (OperationalError, ProgrammingError):
            units = []
        return Response({
            'suggested_unit_ids': [u['id'] for u in units],
            'derived_from': 'L4',
            'rationale': '兜底: 返回所有可用管理单元',
            'app_code': app_code,
        })


# NOTE(Tier 3): 以下「管理单元范围 -> DataPermissionRule ROW 镜像」桥接函数已整体移除:
#   _collect_user_unit_ids / _sync_user_data_rule / _rebuild_rules_for_unit / _rebuild_user_rules
# 行级范围现由 apps.core.scope_resolver.scope_filter_q 直接依据 resolve_scope 计算.


def _make_app_scope_pk(user_id, role_code, app_code):
    """为 (user_id, role_code, app_code) 生成稳定且可逆的 synthetic id (供前端 DELETE 定位)."""
    raw = json.dumps(
        {'u': user_id, 'r': role_code, 'a': app_code},
        separators=(',', ':'), ensure_ascii=False,
    ).encode('utf-8')
    return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')


def _parse_app_scope_pk(pk):
    """解析 synthetic id -> (user_id, role_code, app_code); 失败返回 (None, None, None)."""
    if not pk:
        return None, None, None
    try:
        padded = pk + '=' * (-len(pk) % 4)
        d = json.loads(base64.urlsafe_b64decode(padded.encode('ascii')).decode('utf-8'))
        return d.get('u'), d.get('r'), d.get('a')
    except (binascii.Error, ValueError):  # V2 pk 解包异常 (格式错误/base64 损坏) 返 (None, None, None), 上层视为未授权
        return None, None, None


def _build_app_scope_rows(user_id=None, role_code=None, app_code=None):
    """从 UserRoleV2.app_data_scopes 合成 per-app 数据范围行 (沿用旧 UserAppDataScope 字段形状)."""
    from .serializers_permission_v2 import UserAppDataScopeSerializer

    rows = []
    qs = UserRoleV2.objects.all()
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    if role_code is not None:
        qs = qs.filter(role_code=role_code)
    for ur in qs:
        scopes = ur.app_data_scopes or {}
        for ac, ids in scopes.items():
            if app_code is not None and ac != app_code:
                continue
            rows.append({
                'id': _make_app_scope_pk(ur.user_id, ur.role_code, ac),
                'user_id': ur.user_id,
                'role_code': ur.role_code,
                'system_code': ur.system_code or 'recruit',
                'app_code': ac,
                'management_unit_ids': ids,
                'granted_by_id': ur.granted_by_id,
                'granted_at': ur.granted_at,
                'updated_at': ur.updated_at,
            })
    return UserAppDataScopeSerializer(rows, many=True).data


class UserAppDataScopeViewSet(EnvelopeWriteMixin, viewsets.ModelViewSet):
    """用户-角色-应用 数据范围(管理单元)读写.

    路由 /api/v1/user-app-data-scopes/ 契约保持不变(对齐北森图12 按应用管理单元):
    - list: 支持 ?user_id=&role_code=&app_code= 过滤, 返回行形如旧 UserAppDataScope;
    - create: upsert by (user_id, role_code, app_code), 写入 UserRoleV2.app_data_scopes[app_code];
             范围由 apps.core.scope_resolver 在执行面实时按管理单元解析, 不再镜像 DataPermissionRule;
    - destroy: 移除对应 per-app 项; 范围解析随 app_data_scopes 变更实时生效.

    数据源已从独立 user_app_data_scope 表合并进 UserRoleV2.app_data_scopes(JSON).
    """

    queryset = UserRoleV2.objects.none()
    permission_classes = [V2Permission]
    permission_required = 'recruit:user_app_data_scope:list'
    pagination_class = StandardResultsSetPagination  # per P1 audit 恢复服务端分页

    def get_serializer_class(self):
        from .serializers_permission_v2 import UserAppDataScopeSerializer
        return UserAppDataScopeSerializer

    def list(self, request, *args, **kwargs):
        uid = request.query_params.get('user_id')
        user_id = None
        if uid not in (None, ''):
            try:
                user_id = int(uid)
            except ValueError:
                user_id = None
        role_code = request.query_params.get('role_code')
        app_code = request.query_params.get('app_code')
        rows = _build_app_scope_rows(user_id, role_code, app_code)
        # per P1 audit 恢复服务端分页: 合成 list 同样走 StandardResultsSetPagination 分页信封.
        page = self.paginate_queryset(rows)
        if page is not None:
            return self.get_paginated_response(page)
        return success_response(rows)

    def create(self, request, *args, **kwargs):
        data = request.data
        user_id = data.get('user_id')
        role_code = data.get('role_code')
        app_code = data.get('app_code')
        system_code = data.get('system_code') or 'recruit'
        if not all([user_id is not None, role_code, app_code]):
            return Response(
                {'success': False, 'message': 'user_id / role_code / app_code 必填'},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        ur, _ = UserRoleV2.objects.get_or_create(
            user_id=user_id, role_code=role_code, system_code=system_code,
            defaults={'management_unit_ids': None},
        )
        scopes = ur.app_data_scopes or {}
        scopes[app_code] = data.get('management_unit_ids')
        ur.app_data_scopes = scopes
        ur.save()
        row = {
            'id': _make_app_scope_pk(ur.user_id, ur.role_code, app_code),
            'user_id': ur.user_id,
            'role_code': ur.role_code,
            'system_code': ur.system_code or 'recruit',
            'app_code': app_code,
            'management_unit_ids': data.get('management_unit_ids'),
            'granted_by_id': ur.granted_by_id,
            'granted_at': ur.granted_at,
            'updated_at': ur.updated_at,
        }
        return success_response(
            self.get_serializer(row).data,
            status_code=http_status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        user_id, role_code, app_code = _parse_app_scope_pk(kwargs.get('pk'))
        if user_id is None:
            return Response(
                {'success': False, 'message': '无效的 id'},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        ur = UserRoleV2.objects.filter(user_id=user_id, role_code=role_code).first()
        if ur:
            scopes = ur.app_data_scopes or {}
            scopes.pop(app_code, None)
            ur.app_data_scopes = scopes
            ur.save()
        return success_response(None)