"""V2 权限实时查询. 无 cache, 每个请求重查."""
from django.db.utils import OperationalError, ProgrammingError

from .models_permission_v2 import RolePermissionV2, UserRoleV2
from .role_v2_query import is_super_admin


def has_perm(user, resource_code: str) -> bool:
    """检查 user 是否拥有某 resource_code 的权限. 多角色 UNION.
    is_super_admin 直接 True (bypass).

    T17 schema 未应用前: user_roles 表缺 V2 列 (role_code/system_code/...), 任何
    V2-only 字段引用都会抛 OperationalError. 此处 catch 后返回 False (保守兜底,
    没有显式 V2 角色授权 → 没有权限)."""
    if not (user and user.is_authenticated):
        return False
    if is_super_admin(user):
        return True
    try:
        role_codes = list(
            UserRoleV2.objects
            .filter(user_id=user.pk)
            .values_list('role_code', flat=True)
        )
    except (OperationalError, ProgrammingError):
        # V2 schema 未应用 → user_roles 表缺 role_code 列. 视为无 V2 角色.
        return False
    if not role_codes:
        return False
    return RolePermissionV2.objects.filter(
        role_code__in=role_codes,
        resource_code=resource_code,
    ).exists()