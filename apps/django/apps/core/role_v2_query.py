"""V2 Role/UserRole 查询辅助函数 — 替代 V1 user.user_roles 关联.

V1 时代 user.user_roles 反向关联 (Django 自动, 通过 V1 UserRole.related_name='user_roles')
已不存在,因为 V1 表被 DROP, V2 UserRoleV2 是 BigIntegerField (无 FK).

所有 V1 风格的 user.user_roles.filter(role__code__in=[...]) 必须改为
user_has_role(user, code) / user_has_any_role(user, codes) — 见下.
"""
import logging
from typing import Iterable, Optional

from django.db.utils import OperationalError, ProgrammingError


logger = logging.getLogger(__name__)

SYSTEM_CODE_RECRUIT = 'recruit'

# HR 及以上角色白名单 — 跨文件共享, 避免 drift.
# 注意: HRBP_TIER 是 HRBP (无 HR 角色), HR_TIER 是 HR 及以上. 两个层级语义不同, 不能合并.
HRBP_TIER = ('SUPER_ADMIN', 'HRBP')
HR_TIER = ('SUPER_ADMIN', 'HRBP', 'HR')

# Backwards-compat alias for code that uses generic HR-above naming.
HR_ABOVE = HR_TIER


def _system_code_for_user(user) -> str:
    """V2 schema 用 system_code 隔离, recruit 是当前唯一活跃 system."""
    return SYSTEM_CODE_RECRUIT


def user_role_codes(user, system_code: Optional[str] = None) -> list:
    """返回 user 在 V2 user_roles 表中的所有 role_code (str 列表).

    出错时返回 [] (OperationalError / ProgrammingError 兜底).
    """
    if not (user and getattr(user, 'is_authenticated', False)):
        return []
    # 延迟 import — 避免 module-level 循环 (tests/conftest 早期会引用 models)
    from apps.core.models_permission_v2 import UserRoleV2
    sys = system_code or _system_code_for_user(user)
    try:
        return list(UserRoleV2.objects.filter(
            user_id=user.pk, system_code=sys,
        ).values_list('role_code', flat=True))
    except (OperationalError, ProgrammingError) as e:
        logger.warning('user_role_codes query failed (sys=%s, err=%s); returning []', sys, e)
        return []


def user_has_role(user, role_code: str, system_code: Optional[str] = None) -> bool:
    """user 是否拥有指定 role_code."""
    if not (user and getattr(user, 'is_authenticated', False)):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    from apps.core.models_permission_v2 import UserRoleV2
    sys = system_code or _system_code_for_user(user)
    try:
        return UserRoleV2.objects.filter(
            user_id=user.pk, role_code=role_code, system_code=sys,
        ).exists()
    except (OperationalError, ProgrammingError) as e:
        logger.warning('user_has_role query failed (role=%s, err=%s); returning False', role_code, e)
        return False


def user_has_any_role(user, role_codes: Iterable[str], system_code: Optional[str] = None) -> bool:
    """user 是否拥有 role_codes 列表中的任一角色."""
    if not (user and getattr(user, 'is_authenticated', False)):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    codes = list(role_codes)
    if not codes:
        return False
    from apps.core.models_permission_v2 import UserRoleV2
    sys = system_code or _system_code_for_user(user)
    try:
        return UserRoleV2.objects.filter(
            user_id=user.pk, role_code__in=codes, system_code=sys,
        ).exists()
    except (OperationalError, ProgrammingError) as e:
        logger.warning('user_has_any_role query failed (codes=%s, err=%s); returning False', codes, e)
        return False