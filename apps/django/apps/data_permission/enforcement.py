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

from apps.data_permission.models import DataPermissionRule, DimensionType, RowScopeType
from apps.data_permission.expr_compiler import compile_scope_q

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


# ---------------------------------------------------------------------------
# 行级 enforcement：角色自定义范围（CUSTOM 表达式）接入 scope_resolver 真相源
# ---------------------------------------------------------------------------

def role_entity_scope_q(user, entity: str):
    """返回当前用户在某业务模块（entity）的「角色自定义范围」Q；无配置返回 None。

    语义（RBAC 并集）：
      - 用户任一角色的该模块规则为 ALL -> 整个模块对该用户可见（返回 Q()，调用方 AND 分区）。
      - 角色规则为 NONE -> 该角色贡献空集（Q(pk__in=[])），在 OR 并集中等价于 no-op。
      - 角色规则为 CUSTOM -> 编译其 {expr, groups} 表达式 Q 并参与 OR 并集。
      - 若所有角色对该模块都只有 NONE（无 ALL/无有效 CUSTOM）-> 返回 Q(pk__in=[])（看不到数据）。
      - 若所有角色对该模块都无有效规则 -> 返回 None（调用方回退默认 scope，向后兼容）。
    超管直接返回 None（超管本就全量，且 UI 禁止为其配置）。
    """
    from django.db.models import Q

    try:
        from apps.core.role_v2_query import is_super_admin, user_role_codes
    except Exception:  # noqa: BLE001
        logger.warning('导入 role_v2_query 失败, 角色自定义范围 no-op')
        return None

    if not (user and getattr(user, 'is_authenticated', False)):
        return None
    if is_super_admin(user):
        return None

    try:
        role_codes = list(user_role_codes(user))
    except Exception:  # noqa: BLE001
        logger.warning('计算用户角色码失败, 角色自定义范围 no-op')
        return None
    if not role_codes:
        return None

    rules = DataPermissionRule.objects.filter(
        dimension_type=DimensionType.ROLE,
        dimension_value__in=role_codes,
        level='ROW',
        status=1,
        entity=entity,
    )
    if not rules.exists():
        return None

    qs: list = []
    for r in rules:
        if r.scope_type == RowScopeType.ALL:
            return Q()  # 并集：任一角色 ALL -> 全量
        if r.scope_type == RowScopeType.NONE:
            qs.append(Q(pk__in=[]))  # 该角色贡献空集（OR 并集中 no-op）
            continue
        if r.scope_type == RowScopeType.CUSTOM and r.scope_payload:
            try:
                compiled = compile_scope_q(r.scope_payload, entity)
            except Exception as e:  # noqa: BLE001  (ExprError 等, fail-safe no-op)
                logger.warning('角色自定义范围编译失败, 该规则 no-op: %s', e)
                continue
            # 空 Q（无有效条件）视为无效 -> no-op（不误判为全量）
            if compiled is not None and compiled.children:
                qs.append(compiled)
            else:
                qs.append(Q(pk__in=[]))
        # DEPT / DEPT_AND_SUB / SELF 等旧 scope_type（无 payload）在本新路径 no-op。

    if not qs:
        return None
    combined = qs[0]
    for nxt in qs[1:]:
        combined = combined | nxt
    return combined


class DataPermissionEnforcement:
    """统一入口 (委派到上方模块函数, 兼容 field_acl / candidate 的命名空间式调用).

    注(Tier 3): 行级 row_filter_q 已移除, 行级范围改由 apps.core.scope_resolver.scope_filter_q 提供.
    本类仅保留列级 ACL 相关入口.
    """

    column_permission_for = staticmethod(column_permission_for)
    most_restrictive = staticmethod(most_restrictive)
    clear_column_cache = staticmethod(clear_column_cache)
