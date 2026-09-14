"""V2 权限 DRF 接入层. V2Permission 校验资源级权限, ScopeQuerysetMixin 做数据级过滤."""
from django.db.utils import OperationalError, ProgrammingError
from rest_framework.permissions import BasePermission

from .permission_check import has_perm
from .scope_resolver import resolve_scope
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

    def scope_queryset(self, qs, scope_field: str = ''):
        user = self.request.user
        if is_super_admin(user):
            return qs
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

        # 把 management_unit_ids 转 dept_id 集合
        try:
            unit_dept_ids = set()
            for u in ManagementUnit.objects.filter(id__in=unit_ids, status=1):
                unit_dept_ids.update(u.org_scope or [])
        except (OperationalError, ProgrammingError):
            # V2 schema 未应用 → ManagementUnit 表可能缺列. fallback SELF.
            return qs.filter(created_by=user)

        if not unit_dept_ids:
            return qs.filter(created_by=user)
        return qs.filter(**{f'{scope_field}__in': unit_dept_ids})
