"""V2 权限实时查询. 无 cache, 每个请求重查."""
from django.core.cache import cache
from django.db.utils import OperationalError, ProgrammingError

from .models_permission_v2 import PermissionResource, RolePermissionV2, UserRoleV2
from .role_v2_query import is_super_admin

# 已停用资源码缓存（与 permissions_v2.known_resource_codes 同机制）。
# 停用（status=0）资源永不可授权 —— 即便 role_permission 仍残留授权行。
_DISABLED_CODES_CACHE_KEY = 'ats:v2:disabled_resource_codes'
_DISABLED_CODES_TTL_DEFAULT = 300


def disabled_resource_codes() -> set:
    """返回 PermissionResource 中已停用（status=0）的资源码集合（缓存 5 分钟）。

    V2 schema 未应用时降级为空集合（同 known_resource_codes 的降级口径）。
    """
    codes = cache.get(_DISABLED_CODES_CACHE_KEY)
    if codes is not None:
        return codes
    try:
        codes = set(
            PermissionResource.objects.filter(status=0).values_list(
                'resource_code', flat=True
            )
        )
    except (OperationalError, ProgrammingError):
        # V2 schema 未就绪：降级为空，不阻断（与 known_resource_codes 一致）
        codes = set()
    cache.set(_DISABLED_CODES_CACHE_KEY, codes, _DISABLED_CODES_TTL_DEFAULT)
    return codes


def invalidate_disabled_codes():
    """PermissionResource 变更后调用，让禁用码缓存立即失效。"""
    cache.delete(_DISABLED_CODES_CACHE_KEY)


def has_perm(user, resource_code: str) -> bool:
    """检查 user 是否拥有某 resource_code 的权限. 多角色 UNION.
    is_super_admin 直接 True (bypass).

    T17 schema 未应用前: user_roles 表缺 V2 列 (role_code/system_code/...), 任何
    V2-only 字段引用都会抛 OperationalError. 此处 catch 后返回 False (保守兜底,
    没有显式 V2 角色授权 → 没有权限).

    🔴 停用资源拒绝授权：status=0 的资源码即使仍被某角色持有 role_permission 授权行，
    也一律拒绝。否则 0026/0029 已下线的功能（旧内外部用户列表、Offer 两级审批等）
    会凭残留授权继续可访问 —— 既违反「下线即失效」，也构成「误导性遗留状态」。
    未知码（库内不存在，如 action 派生回退码）不在此列，交由下方既有逻辑判定。
    """
    if not (user and user.is_authenticated):
        return False
    if is_super_admin(user):
        return True
    if resource_code in disabled_resource_codes():
        return False
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