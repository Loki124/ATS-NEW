"""数据权限规则 enforcement (列级 ACL 唯一保留用途).

集成策略 (Tier 3 之后):
- 行级数据范围已完全交由 apps.core.scope_resolver 作为唯一真相源
  (CandidateViewSet.get_queryset 直接调 scope_filter_q), DataPermissionRule 不再承载行级规则.
- 列级: FieldAclService.apply_acl 在按 FieldACL 判定之外, 再叠加本模块的列级规则
        (按 ROLE/DEPARTMENT/USER 维度匹配当前用户), 取最严格.

维度匹配: 对当前 user 计算候选键集合
  USER:<user.pk> / DEPARTMENT:<user.department_id> / ROLE:<每个 role_code>
与 DataPermissionRule(dimension_type, dimension_value, status=1, level='COLUMN') 求交.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from django.core.cache import cache

from apps.data_permission.models import DataPermissionRule, DimensionType

logger = logging.getLogger(__name__)

# 列级规则缓存 TTL(秒). 规则低频配置, 但列表每行都要查.
_COLUMN_RULES_CACHE_TTL = 60

# 权限严格度 (数值越大越严格)
_SEVERITY = {'READ': 0, 'MASK': 1, 'NONE': 2}


def most_restrictive(a: Optional[str], b: Optional[str]) -> Optional[str]:
    """取两条权限中最严格的一条; 任一为 None 则返回另一条."""
    if a is None:
        return b
    if b is None:
        return a
    return a if _SEVERITY[a] >= _SEVERITY[b] else b


def _dimension_match_keys(user) -> List[Tuple[str, str]]:
    """返回 (dimension_type, dimension_value) 候选键集合."""
    keys: List[Tuple[str, str]] = []
    pk = getattr(user, 'pk', None)
    if pk:
        keys.append((DimensionType.USER, str(pk)))
    dept_id = getattr(user, 'department_id', None)
    if dept_id:
        keys.append((DimensionType.DEPARTMENT, str(dept_id)))
    # ROLE: 延迟 import, 避免 module 级循环.
    try:
        from apps.core.role_v2_query import user_role_codes
        for rc in user_role_codes(user):
            keys.append((DimensionType.ROLE, str(rc)))
    except Exception:  # noqa: BLE001
        logger.warning('计算用户角色维度键失败, 跳过 ROLE 维度')
    return keys


# ---------------------------------------------------------------------------
# 列级 enforcement
# ---------------------------------------------------------------------------

def _column_rules_for_entity(entity: str) -> List[Tuple[str, str, str, str]]:
    """取某实体的全部生效列级规则 (field, dimension_type, dimension_value, permission), 带缓存."""
    cache_key = f'data_perm:col:{entity}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    rules = list(
        DataPermissionRule.objects.filter(level='COLUMN', status=1, entity=entity)
    )
    out = [(r.field, r.dimension_type, r.dimension_value, r.permission) for r in rules]
    cache.set(cache_key, out, _COLUMN_RULES_CACHE_TTL)
    return out


def column_permission_for(user, entity: str, field: str) -> Optional[str]:
    """返回该用户对某实体字段的列级权限 (READ/MASK/NONE) 或 None (无 DataPermissionRule 规则)."""
    rules = _column_rules_for_entity(entity)
    if not rules:
        return None
    keys = set(_dimension_match_keys(user))
    perms: List[str] = []
    for f, dt, dv, perm in rules:
        if f == field and (dt, dv) in keys:
            perms.append(perm)
    if not perms:
        return None
    result: Optional[str] = None
    for p in perms:
        result = most_restrictive(result, p)
    return result


def clear_column_cache(entity: Optional[str] = None) -> None:
    """规则变更后清列级缓存 (entity 为空时按已知实体全清)."""
    if entity:
        cache.delete(f'data_perm:col:{entity}')
    else:
        # 列级缓存 key 形如 data_perm:col:<entity>, 无法精准枚举则全清本前缀常见实体.
        for ent in ('candidate', 'offer', 'application'):
            cache.delete(f'data_perm:col:{ent}')


class DataPermissionEnforcement:
    """统一入口 (委派到上方模块函数, 兼容 field_acl / candidate 的命名空间式调用).

    注(Tier 3): 行级 row_filter_q 已移除, 行级范围改由 apps.core.scope_resolver.scope_filter_q 提供.
    本类仅保留列级 ACL 相关入口.
    """

    column_permission_for = staticmethod(column_permission_for)
    most_restrictive = staticmethod(most_restrictive)
    clear_column_cache = staticmethod(clear_column_cache)
