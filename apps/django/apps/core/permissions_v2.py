"""V2 权限 DRF 接入层. V2Permission 校验资源级权限, ScopeQuerysetMixin 做数据级过滤."""
from django.db.utils import OperationalError, ProgrammingError
from rest_framework.permissions import BasePermission

from .permission_check import has_perm
from .scope_resolver import resolve_scope, unit_ids_to_dept_ids, ALL_UNIT_SENTINEL
from .role_v2_query import is_super_admin
from .models_permission_v2 import ManagementUnit


class V2Permission(BasePermission):
    """v2 统一守卫: has_perm 校验资源级权限. superuser bypass.

    view 可声明 permission_required (str 或 list), 来自 PermissionResource.resource_code.
    未声明 → 放行 (依赖 ScopeQuerysetMixin 做数据级过滤).
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if is_super_admin(request.user):
            return True
        required = getattr(view, 'permission_required', None)
        if not required:
            # view 没声明 → 默认放行
            return True
        codes = required if isinstance(required, (list, tuple)) else [required]
        return any(has_perm(request.user, c) for c in codes)


class ScopeQuerysetMixin:
    """替代 apps/core/permissions.py 旧 ScopedQuerysetMixin.

    ViewSet 在 get_queryset() 末尾调用 self.scope_queryset(qs, scope_field='department_id').
    superuser bypass; resolve_scope 4 层堆栈; ManagementUnit.org_scope 转 dept_id 集合.
    """

    scope_field: str = ''
    # 招聘类型硬分区 (opt-in): 子类设 None 即不参与分区; 默认 'recruit_type'.
    # 仅当模型确有该字段时生效 (hasattr 守卫), 不影响未分区模型.
    recruit_type_field: str = 'recruit_type'

    def scope_queryset(self, qs, scope_field: str = '', entity: str = ''):
        user = self.request.user
        # 硬系统分区: 对所有用户(含超管)生效, 先于行级 scope 应用.
        # opt-in: 仅当模型确有 recruit_type 字段时过滤, 否则 no-op.
        rt_field = self.recruit_type_field
        if rt_field and hasattr(qs.model, rt_field):
            qs = qs.filter(**{rt_field: getattr(self.request, 'recruit_type', 'social')})
        if is_super_admin(user):
            return qs
        # 角色自定义范围（数据权限向导）优先于默认 scope：有配置则替换，无配置回退。
        entity = entity or getattr(self, 'data_perm_entity', '')
        if entity:
            from apps.data_permission.enforcement import role_entity_scope_q
            custom_q = role_entity_scope_q(user, entity)
            if custom_q is not None:
                return qs.filter(custom_q)
        scope_field = scope_field or self.scope_field

        scope = resolve_scope(user)
        if scope.get('all'):
            return qs

        # R8 (2026-08-03): resolve_scope 的 DEPT / DEPT_AND_SUB 分支直接返回部门 id
        # 集合 (Department.pk 是 CharField(32), 和 ManagementUnit 的 int 主键不是同一
        # id 空间), 这里单独处理, 不要再过 ManagementUnit 那一层转换。
        dept_ids = scope.get('department_ids') or []
        if dept_ids:
            if not scope_field:
                # 没声明 scope_field 就无法按部门过滤, 保守退回 SELF
                return qs.filter(created_by=user)
            return qs.filter(**{f'{scope_field}__in': dept_ids})

        unit_ids = scope.get('management_unit_ids', [])
        if not unit_ids:
            # SELF 兜底: 仅自己创建的
            return qs.filter(created_by=user)

        # 把 management_unit_ids 转 dept_id 集合 (复用 type-safe 解析, 避免 dict org_scope
        # 把 key 当部门 id 泄漏进过滤条件). 整公司级单元(ALL sentinel) -> 可见全量.
        try:
            resolved = unit_ids_to_dept_ids(unit_ids)
            if ALL_UNIT_SENTINEL in resolved:
                return qs
            unit_dept_ids = set(d for d in resolved if d != ALL_UNIT_SENTINEL)
        except (OperationalError, ProgrammingError):
            # V2 schema 未应用 → ManagementUnit 表可能缺列. fallback SELF.
            return qs.filter(created_by=user)

        if not unit_dept_ids:
            return qs.filter(created_by=user)
        return qs.filter(**{f'{scope_field}__in': unit_dept_ids})

    def _rt_field(self):
        """返回当前 ViewSet 应注入的招聘类型字段名 (opt-in).

        仅当 recruit_type_field 已声明且 queryset 模型确有该字段时返回字段名,
        否则返回 None —— 调用方据此决定是否走默认写入路径.
        """
        rt_field = self.recruit_type_field
        if not rt_field:
            return None
        model_cls = getattr(getattr(self, 'queryset', None), 'model', None)
        if model_cls and hasattr(model_cls, rt_field):
            return rt_field
        return None

    def perform_create(self, serializer):
        """写入守卫: 创建时由请求上下文权威注入 recruit_type (覆盖客户端自填值)."""
        rt_field = self._rt_field()
        if rt_field:
            serializer.save(**{rt_field: getattr(self.request, 'recruit_type', 'social')})
        else:
            super().perform_create(serializer)

    def perform_update(self, serializer):
        """写入守卫: 更新时由请求上下文权威注入 recruit_type (覆盖客户端自填值)."""
        rt_field = self._rt_field()
        if rt_field:
            serializer.save(**{rt_field: getattr(self.request, 'recruit_type', 'social')})
        else:
            super().perform_update(serializer)
