
"""Field ACL Views (DRF) - PRD v4 §4.4"""
import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.pagination import StandardResultsSetPagination
from apps.common.viewsets import EnvelopeAuditModelViewSet
from apps.core.permissions import IsSuperAdmin

from .models import FieldACL
from .serializers import (
    FieldAclRuleSerializer,
    FieldACLSerializer,
    FieldACLWriteSerializer,
    permission_to_action,
)
from .services import FieldAclService

logger = logging.getLogger(__name__)

#: 可配实体 → 展示名 + 该实体下**有意义可配**的字段清单。
#:
#: 字段清单的来源是 FieldAclService.DEFAULT_SENSITIVE_FIELDS（后端唯一真源），
#: 前端不再自建一份 —— 自建就会出现"前端能选、后端不认识"的静默失败字段。
ENTITY_CATALOG = {
    'candidate': {'label': '候选人', 'fields': ('phone', 'email', 'id_card_no')},
    'application': {'label': '投递', 'fields': ('candidate_phone', 'candidate_email')},
    'offer': {'label': '报价', 'fields': ('salary', 'bonus')},
    'demand': {'label': '需求', 'fields': ('salary_range',)},
}


def _audit_acl_change(request, action_name, detail, row_count):
    """ACL 变更审计（薄封装，复用 data_permission.views._audit_config_change）。

    审计失败**不阻断**保存（沿用 _audit_config_change 既有语义）：
    权限配置本身已落库，审计缺失可从日志追，但记 error 级日志暴露。
    """
    from apps.data_permission.views import _audit_config_change
    _audit_config_change(
        request.user, 'field_acl', detail.get('role_code', ''), f'ACL_{action_name}',
        None, {**detail, 'rows': row_count}, request,
    )


class FieldACLViewSet(EnvelopeAuditModelViewSet):
    """字段级 ACL ViewSet - 仅超管可操作"""
    queryset = FieldACL.objects.all()
    serializer_class = FieldACLSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['entity', 'field', 'role_code', 'permission']
    search_fields = ['entity', 'field', 'role_code']
    ordering_fields = ['entity', 'field', 'role_code']
    ordering = ['entity', 'field', 'role_code']

    @action(detail=False, methods=['get'], url_path='matrix')
    def matrix(self, request):
        """GET /field-acl/matrix - 返回前端 `FieldAclMatrix` 权限矩阵。

        把所有 FieldACL 行聚合成嵌套结构:
            { resource: { field: { roleCode: {permission, action} } } }
        其中 resource ← entity。

        2026-10-14 P0-2（设计文档 §3.3 ④ / D4）：**同时**返回
        `permission`（代码枚举 READ/MASK/NONE，权威口径）与 `action`
        （旧前端词汇 VIEW/MASK/HIDE）双字段。

        为什么必须双字段而不是直接切换：旧前端 `field-acl.ts` 用
        FieldAclAction('VIEW'|'MASK'|'HIDE')，它把 matrix 值直接喂给 n-tag
        的 type。一旦这里改成只返回 permission 对象而旧前端还在跑，
        tag 会渲染出 `[object Object]` —— 权限收紧的页面看起来像坏了。
        `action` 字段保留一个批次做过渡，前端本批次起全部只用 `permission`。
        """
        matrix_dict: dict[str, dict[str, dict[str, dict[str, str]]]] = {}

        rows = FieldACL.objects.all().values_list(
            'entity', 'field', 'role_code', 'permission',
        )
        for entity, field_name, role_code, permission in rows:
            resource_bucket = matrix_dict.setdefault(entity, {})
            field_bucket = resource_bucket.setdefault(field_name, {})
            field_bucket[role_code] = {
                'permission': permission,
                # TODO(P0-4 过渡):下批删除 action 字段。
                'action': permission_to_action(permission),
            }

        return Response({'success': True, 'data': matrix_dict})

    @action(detail=False, methods=['get'], url_path='catalog')
    def catalog(self, request):
        """GET /field-acl/catalog - 可配实体与字段清单（前端矩阵的列/行定义）。

        为什么要这个接口：矩阵的"有哪些实体、每实体有哪些敏感字段可配"若写在前端，
        就会与后端 DEFAULT_SENSITIVE_FIELDS 漂移 —— 前端能选出一个后端不认识的字段，
        保存后规则永不命中，表现为"配了没生效"（静默失败，最难查的一类）。
        故由后端下发，前端只渲染。
        """
        data = {
            entity: {
                'label': meta['label'],
                'fields': list(meta['fields']),
                # 该实体下"未配规则时的默认脱敏字段"全集 —— 前端据此在矩阵里
                # 给这些字段打「默认脱敏」标记，让管理员知道哪些格子是安全兜底。
                'defaultMasked': list(FieldAclService.DEFAULT_SENSITIVE_FIELDS.get(entity, [])),
            }
            for entity, meta in ENTITY_CATALOG.items()
        }
        return Response({'success': True, 'data': data})

    @action(detail=False, methods=['get', 'put', 'delete'], url_path='rules')
    def rules(self, request):
        """GET/PUT/DELETE /field-acl/rules —— 规则列表 + 按三元组 upsert/删除。

        ⚠️ GET / PUT / DELETE **必须挂在同一个 @action 上**（不能新加一个
        url_path='rules' 的 action），这是 DRF 路由的硬约束：
        router 会为每个 @action 各生成一条 `^field-acl/rules/$` pattern，
        而 Django 解析器**命中首条即止**，之后由该 view 自己按 method_map 决定
        响应 —— 首条若是 GET-only，后来者永远不会被解析到（POST 返405，
        DELETE 返 405而非 404）。合并成单pattern 后 method_map 同时含
        get/put/delete，三者都进同一分支。
        （同项目 views_permission_v2.data_permissions 的 GET+POST 合并是同一原因。）

        契约（幂等 upsert，天然防"重复点保存"）：
          PUT    /field-acl/rules   body={entity, field, role_code, permission}
          DELETE /field-acl/rules   body 同上（去掉 permission）
        ACL 的唯一键是 (entity, field, role_code) 三元组，没有单条 pk 语义，
        delete 用三元组定位比用 nanoid pk 更符合领域语义，前端也无需先查列表拿 id。
        """
        if request.method == 'DELETE':
            return self._delete_rule(request)
        if request.method == 'PUT':
            return self._upsert_rule(request)
        return self._list_rules(request)

    def _list_rules(self, request):
        """GET 分支：返回前端 `FieldAclRule[]` 规则列表（只读投影）。

        可选查询参数:
            resource: 过滤 entity (前端命名 → 模型命名)
            roleCode: 过滤 role_code
        """
        queryset = FieldACL.objects.all()

        resource = request.query_params.get('resource')
        if resource:
            queryset = queryset.filter(entity=resource)

        role_code = request.query_params.get('roleCode')
        if role_code:
            queryset = queryset.filter(role_code=role_code)

        serializer = FieldAclRuleSerializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})

    def _upsert_rule(self, request):
        """PUT 分支：按 (entity, field, role_code) upsert 单条 ACL（200 更新 / 201 新建）。"""
        ser = FieldACLWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        obj, created = FieldACL.objects.update_or_create(
            entity=data['entity'],
            field=data['field'],
            role_code=data['role_code'],
            defaults={'permission': data['permission']},
        )
        # 缓存失效是必做项（设计文档 §1.4.2④ / RK-7）：get_rules_map 有 60s TTL，
        # 不清则"保存成功但最长 60s 内不生效"—— 收紧权限不生效比不配更危险。
        # （FieldACL 已有 post_save 信号会清，但显式调一次是为了不依赖信号注册顺序，
        #   且 update_or_create 走 update 分支时信号语义与批量操作不同。）
        FieldAclService.invalidate_rules_cache(obj.entity)
        _audit_acl_change(
            request, 'CREATE' if created else 'UPDATE', data, 1,
        )
        return Response(
            {'success': True, 'data': {
                'id': obj.id, 'entity': obj.entity, 'field': obj.field,
                'roleCode': obj.role_code, 'permission': obj.permission,
            }},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def _delete_rule(self, request):
        """DELETE 分支：按三元组删除单条 ACL。

        幂等语义：删不存在的规则返回 200 + `deleted: 0`，**不报错** ——
        前端"撤销"流程（单条删除后 Toast 撤销 5-8s）可无脑重放，不会因
        重复点击而报错打扰用户。
        """
        entity = _body_get(request.data, 'entity')
        field_name = _body_get(request.data, 'field')
        role_code = _body_get(request.data, 'role_code', 'roleCode')
        missing = [
            k for k, v in
            (('entity', entity), ('field', field_name), ('role_code', role_code))
            if not v
        ]
        if missing:
            return Response(
                {'success': False, 'message': f'缺少必填参数：{", ".join(missing)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        deleted, _ = FieldACL.objects.filter(
            entity=entity, field=field_name, role_code=role_code,
        ).delete()
        FieldAclService.invalidate_rules_cache(entity)
        if deleted:
            _audit_acl_change(
                request, 'DELETE',
                {'entity': entity, 'field': field_name, 'role_code': role_code}, deleted,
            )
        return Response({'success': True, 'data': {'deleted': deleted}})

    @action(detail=False, methods=['post'], url_path='rules/batch')
    def batch_rules(self, request):
        """POST /field-acl/rules/batch —— 批量按角色/实体套用（P0-2 流程 D5）。

        body: {mode:'by_role'|'by_entity', roleCode|entity,
               items:[{field, permission}], dryRun?: bool}

        dryRun=true 时**只返回影响预览不落库** —— 前端批量破坏性操作前必须先调它
        （AGENTS.md R-106 破坏性操作分级：批量必须确认框 + 后果与影响范围，
        "影响范围"的数据来源就是这个接口，不能靠前端自己瞎猜）。

        落库时按 (entity, field, role_code) 逐条 upsert，**不删除**未列出的既有规则：
        批量操作语义是"把这些字段设为某态"，不是"替换整个角色的规则集"。

        ⚠️ 取参用 `_body_get`：项目全局挂CamelCaseJSONParser
        （config/settings/base.py），JSON body 的 camelCase 键在到达视图前已被
        归一为 snake_case。这里同时兼容两种写法，避免前端传 role_code 时
        视图读到None 而报「必须指定 roleCode」这种难以定位的错误。
        """
        body = request.data
        mode = _body_get(body, 'mode')
        role_code = _body_get(body, 'roleCode', 'role_code')
        entity = _body_get(body, 'entity')
        items = _body_get(body, 'items')
        dry_run = bool(_body_get(body, 'dryRun', 'dry_run') or False)

        if mode not in ('by_role', 'by_entity'):
            return _batch_error("mode 只能是 by_role（按角色批量）或 by_entity（按实体批量）")
        if mode == 'by_role' and not role_code:
            return _batch_error('按角色批量时必须指定 roleCode')
        if mode == 'by_entity' and not entity:
            return _batch_error('按实体批量时必须指定 entity')
        if not isinstance(items, list) or not items:
            return _batch_error('items 必须是非空数组')

        from apps.core.models_permission_v2 import RoleV2
        # 先把作用范围解析成 (entity, field, role_code) 三元组集合：
        # by_role = 该角色 × 所有实体的全部字段；by_entity = 所有角色 × 该实体字段。
        if mode == 'by_role':
            if not RoleV2.objects.filter(role_code=role_code).exists():
                return _batch_error(f'角色「{role_code}」不存在，请重新选择')
            role_codes = [role_code]
            entities = list(ENTITY_CATALOG)
        else:
            if entity not in ENTITY_CATALOG:
                return _batch_error(f'实体「{entity}」不在可配范围内')
            role_codes = list(
                RoleV2.objects.filter(status=1)
                .order_by('system_code', 'role_code')
                .values_list('role_code', flat=True)
                .distinct()
            )
            entities = [entity]

        item_map = {i.get('field'): i.get('permission') for i in items if isinstance(i, dict)}
        targets = [
            (ent, fld, rc)
            for rc in role_codes for ent in entities
            for fld in ENTITY_CATALOG[ent]['fields'] if fld in item_map
        ]
        if not targets:
            return _batch_error('没有可应用的字段（items 里的字段名不在该实体的可配清单内）')

        valid_perms = {c[0] for c in _permission_choices()}
        # 注意：targets 的第三元是 role_code，不是 permission —— 必须回查 item_map
        bad = sorted({
            f'{fld}={item_map[fld]}'
            for _, fld, _rc in targets if item_map[fld] not in valid_perms
        })
        if bad:
            return _batch_error(f'字段可见性只能是「可读 / 脱敏可见 / 不可见」之一：{"、".join(bad)}')

        will_create = 0
        will_update = 0
        for ent, fld, rc in targets:
            if FieldACL.objects.filter(entity=ent, field=fld, role_code=rc).exists():
                will_update += 1
            else:
                will_create += 1

        result = {
            'dryRun': dry_run,
            'affectedRoles': len(set(rc for _, _, rc in targets)),
            'affectedFields': len(set(fld for _, fld, _ in targets)),
            'affectedEntities': len(set(ent for ent, _, _ in targets)),
            'willCreate': will_create,
            'willUpdate': will_update,
        }
        if dry_run:
            return Response({'success': True, 'data': result})

        created = 0
        for ent, fld, rc in targets:
            _, was_created = FieldACL.objects.update_or_create(
                entity=ent, field=fld, role_code=rc,
                defaults={'permission': item_map[fld]},
            )
            created += 1 if was_created else 0
        # 批量跨多个实体 → 必须逐实体清缓存，不能只清一个
        for ent in {e for e, _, _ in targets}:
            FieldAclService.invalidate_rules_cache(ent)
        _audit_acl_change(request, 'BATCH', {
            'mode': mode, 'roleCode': role_code, 'entity': entity,
            'fields': sorted(set(fld for _, fld, _ in targets)),
        }, len(targets))
        result['created'] = created
        return Response({'success': True, 'data': result})

    @action(detail=False, methods=['get'], url_path='audit')
    def audit(self, request):
        """GET /field-acl/audit - ACL 访问审计日志。

        读取 FieldAclAccessLog 表 (由 FieldAclSerializerMixin 在 HTTP 序列化时
        按 (request, entity) 去重埋点写入)。可选查询参数: entity / username。
        返回最近 500 条 (按时间倒序)。
        """
        from .models import FieldAclAccessLog

        queryset = FieldAclAccessLog.objects.all()

        entity = request.query_params.get('entity')
        if entity:
            queryset = queryset.filter(entity=entity)

        username = request.query_params.get('username')
        if username:
            queryset = queryset.filter(username__icontains=username)

        rows = [
            {
                'id': r.id,
                'entity': r.entity,
                'user_id': r.user_id,
                'username': r.username,
                'role_codes': r.role_codes,
                'masked_fields': r.masked_fields,
                'hidden_fields': r.hidden_fields,
                'request_path': r.request_path,
                'client_ip': r.client_ip,
                'created_at': r.created_at.isoformat() if r.created_at else None,
            }
            for r in queryset.order_by('-created_at')[:500]
        ]
        return Response({'success': True, 'data': rows})


def _body_get(body, *keys, default=None):
    """从 request.data 取值，兼容 camelCase / snake_case 两种键名。

    项目全局挂 CamelCaseJSONParser（config/settings/base.py），JSON body 的
    camelCase 键在到达视图前已被归一为 snake_case；但 DELETE 带 body、
    multipart 与直传 dict 等路径不一定经该 parser，故两种写法都认。
    避免出现「前端明明传了 role_code，视图却报『必须指定 roleCode』」这类
    难以定位的键名不一致错误。
    """
    for k in keys:
        if k in body:
            return body[k]
    return default


def _permission_choices():
    """FieldPermission 枚举 choices（从模型取，避免在 views 里硬编码三态）。"""
    from .models import FieldPermission
    return FieldPermission.choices


def _batch_error(message: str) -> Response:
    """批量接口的 400 统一出口（message 即前端错误三段式第一段的人话描述）。"""
    return Response(
        {'success': False, 'message': message},
        status=status.HTTP_400_BAD_REQUEST,
    )
