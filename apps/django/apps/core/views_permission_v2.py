"""V2 权限系统 ViewSets + function views."""
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
    ManagementUnit, UserRoleV2, UserAppDataScope, ManagementUnitMember,
)
from apps.data_permission.models import DataPermissionRule, DimensionType, RowScopeType
from .permissions_v2 import V2Permission
from .scope_resolver import resolve_scope


class PermissionResourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PermissionResource.objects.filter(status=1)
    permission_classes = [V2Permission]
    pagination_class = None
    filterset_fields = ['module', 'resource_type']
    search_fields = ['resource_code', 'resource_name']

    def get_serializer_class(self):
        from .serializers_permission_v2 import PermissionResourceSerializer
        return PermissionResourceSerializer

    def list(self, request, *args, **kwargs):
        """T30.176: 包 {success, data} 包装层, 对齐其它 V2 endpoint (menus/functions/mous) 与 FE helper 期望."""
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})


class PermissionTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PermissionTemplate.objects.filter(status=1)
    permission_classes = [V2Permission]
    pagination_class = None
    filterset_fields = ['is_system']

    def get_serializer_class(self):
        from .serializers_permission_v2 import PermissionTemplateSerializer
        return PermissionTemplateSerializer

    def list(self, request, *args, **kwargs):
        """T30.176: 包 {success, data} 包装层, 对齐其它 V2 endpoint."""
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})


class RoleViewSet(viewsets.ModelViewSet):
    queryset = RoleV2.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:role:list'
    pagination_class = None
    search_fields = ['role_code', 'role_name']
    filterset_fields = ['status', 'is_system']

    def get_serializer_class(self):
        from .serializers_permission_v2 import RoleSerializer
        return RoleSerializer

    def list(self, request, *args, **kwargs):
        """T30.176: 包 {success, data} 包装层, 对齐其它 V2 endpoint 与 FE helper 期望."""
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({'success': True, 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {'success': True, 'data': serializer.data},
            status=http_status.HTTP_201_CREATED,
            headers=headers,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({'success': True, 'data': serializer.data})

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


class EnvelopeWriteMixin:
    """写操作统一包 {success, data} 信封 (对齐本项目 V2 read 接口与前端 r.data.data 约定).

    DRF 默认 create/update 直接返回序列化体, 不包信封会让前端 r.data.data 为 undefined.
    参考 apps.library.views.EnvelopeWriteMixin, 在 core 内独立完成以避免跨 app 耦合.
    """

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'success': True, 'data': serializer.data}, status=http_status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({'success': True, 'data': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        return Response({'success': True, 'data': self.get_serializer(self.get_object()).data})

    def destroy(self, request, *args, **kwargs):
        self.perform_destroy(self.get_object())
        return Response({'success': True, 'data': None})


class ManagementUnitViewSet(EnvelopeWriteMixin, viewsets.ModelViewSet):
    queryset = ManagementUnit.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:mgmt_unit:list'
    pagination_class = None
    filterset_fields = ['unit_type', 'status']

    def get_serializer_class(self):
        from .serializers_permission_v2 import ManagementUnitSerializer
        return ManagementUnitSerializer

    def list(self, request, *args, **kwargs):
        """T30.176: 包 {success, data} 包装层, 对齐其它 V2 endpoint."""
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})

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
                'org_scope': u.org_scope, 'personnel_scope': u.personnel_scope,
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

    @action(detail=True, methods=['post'], url_path='sync-data-rules')
    @transaction.atomic
    def sync_data_rules(self, request, pk=None):
        """POST /api/v1/management-units/{id}/sync-data-rules/

        方案 A M4(2026-09-15): 把引用该单元的全部「用户-角色-应用」分配镜像成
        DataPermissionRule(USER 维度, 行级 CUSTOM), 接进 enforcement.row_filter_q.

        有效单元集合 = 自身 + (include_children 时) 所有后代(按 parent_id BFS);
        仅用于按钮反馈 (effectiveUnitIds). 真正的执行面规则按 USER 维度逐用户重建,
        避免按 ROLE 建规则导致的跨用户越权.

        维度键 USER:<user_id> 与 enforcement._dimension_match_keys 的 USER 键一致,
        scope_payload 同时带 management_unit_ids(溯源) 与 department_ids(由 org_scope 解析).
        """
        unit = self.get_object()
        effective = [unit.id]
        frontier = [unit.id]
        while frontier:
            children = list(ManagementUnit.objects.filter(parent_id__in=frontier, status=1))
            nxt = [c.id for c in children if c.id not in effective]
            for cid in nxt:
                effective.append(cid)
            frontier = nxt
        effective = list(dict.fromkeys(effective))  # 去重保序

        # 扫描引用该单元的全部分配, 收集受影响 user_id (按用户重建规则, 防跨用户越权)
        user_ids = set()
        for s in UserAppDataScope.objects.filter(management_unit_ids__contains=[unit.id]):
            user_ids.add(s.user_id)
        for ur in UserRoleV2.objects.filter(management_unit_ids__contains=[unit.id]):
            user_ids.add(ur.user_id)

        rule_ids = []
        for uid in user_ids:
            rule = _rebuild_user_rules(uid)
            if rule:
                rule_ids.append(rule.id)

        return Response({
            'success': True,
            'data': {
                'effective_unit_ids': effective,
                'rule_ids': rule_ids,
                'rule_id': rule_ids[0] if rule_ids else None,
                'synced_user_count': len(user_ids),
            },
            'note': '管理单元范围已镜像为 DataPermissionRule(USER 维度, CUSTOM); enforcement.row_filter_q 现已消费 management_unit_ids',
        })

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        """GET/POST /api/v1/management-units/{id}/members/

        GET: 列出该单元启用的成员 (含 DEPT/USER/PERSON 名称回填);
        POST: 新增成员, 写入前按 (unit, member_type, 引用列) 查重返回 400 (避免 MySQL 多 nullable 列唯一约束陷阱).
        成员变更后重建所有引用该单元的用户执行面规则.
        """
        unit = self.get_object()
        if request.method == 'GET':
            qs = ManagementUnitMember.objects.filter(unit_id=unit.id, status=1)
            from .serializers_permission_v2 import ManagementUnitMemberSerializer
            return Response({'success': True, 'data': ManagementUnitMemberSerializer(qs, many=True).data})
        data = request.data or {}
        mt = data.get('member_type')
        ref_map = {'DEPT': 'department_id', 'USER': 'user_id', 'PERSON': 'person_id'}
        ref_col = ref_map.get(mt)
        ref_val = data.get(ref_col) if ref_col else None
        if not mt or ref_val in (None, ''):
            return Response({'success': False, 'message': 'member_type 与对应引用ID必填'},
                            status=http_status.HTTP_400_BAD_REQUEST)
        if ManagementUnitMember.objects.filter(unit_id=unit.id, member_type=mt,
                                                **{ref_col: ref_val}).exists():
            return Response({'success': False, 'message': '该成员已存在于此管理单元'},
                            status=http_status.HTTP_400_BAD_REQUEST)
        member = ManagementUnitMember.objects.create(
            unit_id=unit.id, member_type=mt, **{ref_col: ref_val},
            include_children=int(data['include_children']) if data.get('include_children') is not None else 1,
            remark=data.get('remark') or '', status=1)
        _rebuild_rules_for_unit(unit.id)
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
            _rebuild_rules_for_unit(unit.id)
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


class UserRoleViewSet(viewsets.ModelViewSet):
    queryset = UserRoleV2.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:user_role:list'
    pagination_class = None
    filterset_fields = ['user_id', 'role_code', 'system_code']

    def get_serializer_class(self):
        from .serializers_permission_v2 import UserRoleSerializer
        return UserRoleSerializer

    def list(self, request, *args, **kwargs):
        """T30.176: 包 {success, data} 包装层, 对齐其它 V2 endpoint."""
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['get'])
    def suggest_scope(self, request):
        """GET /user-roles/suggest-scope/?user_id=X&role_code=Y[&app_code=Z]

        方案 A(2026-09-15): 新增 app_code 透传, 按应用返回对应管理单元候选
        (resolve_scope 在 app_code 命中 UserAppDataScope 时优先返回 per-app 范围).
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


def _collect_user_unit_ids(user_id):
    """方案 A M4: 汇总某用户全部管理单元范围 (UserAppDataScope per-app + UserRoleV2 全局兜底)."""
    unit_ids = set()
    for s in UserAppDataScope.objects.filter(user_id=user_id):
        unit_ids.update(s.management_unit_ids or [])
    for ur in UserRoleV2.objects.filter(user_id=user_id):
        unit_ids.update(ur.management_unit_ids or [])
    return sorted(unit_ids)


def _sync_user_data_rule(user_id, unit_ids):
    """把某用户的全部管理单元范围镜像成 DataPermissionRule(USER 维度, 行级).

    维度 USER:<user_id> 与 enforcement._dimension_match_keys 的 USER 键一致,
    避免按 ROLE 建规则导致的「同角色跨用户越权」.

    解析结果三种形态:
      - 含整公司级单元 (org_scope={'level':'ROOT'}) -> ALL 规则 (可见全量);
      - 解析出部门 id -> CUSTOM 规则, department_ids 供 row_filter_q 消费;
      - 解析不出任何部门范围 (dict 无 dept 子键且非整公司) -> 不建 NEW 引擎规则,
        回退 OLD 引擎 / SELF, 绝不产生无效应规则.
    """
    from apps.core.scope_resolver import (
        unit_ids_to_dept_ids, collect_unit_member_users, ALL_UNIT_SENTINEL,
    )
    resolved = unit_ids_to_dept_ids(unit_ids)
    user_ids = collect_unit_member_users(unit_ids)
    if ALL_UNIT_SENTINEL in resolved:
        rule, _ = DataPermissionRule.objects.update_or_create(
            id=f'uads_user_{user_id}',
            defaults={
                'dimension_type': DimensionType.USER,
                'dimension_value': str(user_id),
                'level': 'ROW',
                'scope_type': RowScopeType.ALL,
                'scope_payload': {
                    'management_unit_ids': list(unit_ids),
                    'user_ids': sorted(user_ids),
                },
                'priority': 50,
                'status': 1,
                'remark': f'用户应用数据范围同步(user={user_id}, 整公司)',
                'created_by': None,
            },
        )
        return rule
    dept_ids = [d for d in resolved if d != ALL_UNIT_SENTINEL]
    if not dept_ids and not user_ids:
        # 无可用部门范围且无成员用户 -> 不建 NEW 引擎规则, 回退 OLD 引擎 / SELF
        return None
    rule, _ = DataPermissionRule.objects.update_or_create(
        id=f'uads_user_{user_id}',
        defaults={
            'dimension_type': DimensionType.USER,
            'dimension_value': str(user_id),
            'level': 'ROW',
            'scope_type': RowScopeType.CUSTOM,
            'scope_payload': {
                'management_unit_ids': list(unit_ids),
                'department_ids': sorted(dept_ids),
                'user_ids': sorted(user_ids),
            },
            'priority': 50,
            'status': 1,
            'remark': f'用户应用数据范围同步(user={user_id})',
            'created_by': None,
        },
    )
    return rule


def _rebuild_rules_for_unit(unit_id):
    """管理单元成员变更后, 重建所有引用该单元的用户执行面规则."""
    user_ids = set()
    for s in UserAppDataScope.objects.filter(management_unit_ids__contains=[unit_id]):
        user_ids.add(s.user_id)
    for ur in UserRoleV2.objects.filter(management_unit_ids__contains=[unit_id]):
        user_ids.add(ur.user_id)
    for uid in user_ids:
        _rebuild_user_rules(uid)


def _rebuild_user_rules(user_id):
    """重建某用户的管理单元数据范围规则: 有范围则 upsert, 无范围(或范围解析为空)则删除回退 OLD 引擎.

    注意: _sync_user_data_rule 在「有管理单元但解析不出任何部门/成员范围」时返回 None
    (如某单元 org_scope 为空且无其它部门成员, 仅剩的 PERSON/USER 成员被移除).
    此时必须清掉旧规则, 否则会残留过期的 user_ids/department_ids 导致越权可见.
    """
    unit_ids = _collect_user_unit_ids(user_id)
    if unit_ids:
        rule = _sync_user_data_rule(user_id, unit_ids)
        if rule is None:
            DataPermissionRule.objects.filter(id=f'uads_user_{user_id}').delete()
        return rule
    DataPermissionRule.objects.filter(id=f'uads_user_{user_id}').delete()
    return None


class UserAppDataScopeViewSet(EnvelopeWriteMixin, viewsets.ModelViewSet):
    """方案 A(2026-09-15): 用户-角色-应用 数据范围(管理单元)读写.

    路由 /api/v1/user-app-data-scopes/ (对齐北森图12 按应用管理单元).
    - list: 支持 ?user_id=&role_code=&app_code= 过滤.
    - create: upsert by (user_id, role_code, app_code), 写入 management_unit_ids;
             同时把该用户的全部管理单元范围镜像成 DataPermissionRule(USER 维度),
             接进 enforcement.row_filter_q 执行面.
    - destroy: 删除后重建该用户规则 (无范围则清规则回退 OLD 引擎).
    """

    queryset = UserAppDataScope.objects.all()
    permission_classes = [V2Permission]
    permission_required = 'recruit:user_app_data_scope:list'
    pagination_class = None

    def get_serializer_class(self):
        from .serializers_permission_v2 import UserAppDataScopeSerializer
        return UserAppDataScopeSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        user_id = request.query_params.get('user_id')
        role_code = request.query_params.get('role_code')
        app_code = request.query_params.get('app_code')
        if user_id is not None:
            qs = qs.filter(user_id=user_id)
        if role_code is not None:
            qs = qs.filter(role_code=role_code)
        if app_code is not None:
            qs = qs.filter(app_code=app_code)
        serializer = self.get_serializer(qs, many=True)
        return Response({'success': True, 'data': serializer.data})

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
        obj, _ = UserAppDataScope.objects.update_or_create(
            user_id=user_id, role_code=role_code, app_code=app_code, system_code=system_code,
            defaults={
                'management_unit_ids': data.get('management_unit_ids'),
                'granted_by_id': request.user.id,
            },
        )
        # 方案 A M4: 同步镜像该用户全部管理单元范围到 DataPermissionRule 执行面
        _rebuild_user_rules(user_id)
        return Response(
            {'success': True, 'data': self.get_serializer(obj).data},
            status=http_status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        uid = instance.user_id
        self.perform_destroy(instance)
        # 方案 A M4: 删除后重建该用户规则 (无范围则清规则, 回退 OLD 引擎)
        _rebuild_user_rules(uid)
        return Response({'success': True, 'data': None})