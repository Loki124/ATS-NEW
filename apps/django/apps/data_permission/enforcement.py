"""数据权限规则 enforcement (RBAC 复核 #9 补全: 让 DataPermissionRule 真正生效).

集成策略 (低风险, 路径 A — 不替换旧引擎):
- 行级: CandidateViewSet.get_queryset 在调用 scope_resolver 前先问本模块;
        若当前用户有「生效的行级规则」, 以其为准 (权威); 否则回退 scope_resolver。
- 列级: FieldAclService.apply_acl 在按 FieldACL 判定之外, 再叠加本模块的列级规则
        (按 ROLE/DEPARTMENT/USER 维度匹配当前用户), 取最严格。

维度匹配: 对当前 user 计算候选键集合
  USER:<user.pk> / DEPARTMENT:<user.department_id> / ROLE:<每个 role_code>
与 DataPermissionRule(dimension_type, dimension_value, status=1) 求交。
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from django.core.cache import cache
from django.db.models import Q

from .models import (
    DataPermissionRule,
    DimensionType,
    RowScopeType,
)

from apps.core.role_v2_query import is_super_admin

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


def _active_rules(user, level: str) -> List[DataPermissionRule]:
    """取当前用户生效的某层级 (ROW/COLUMN) 规则."""
    keys = _dimension_match_keys(user)
    if not keys:
        return []
    types = [k[0] for k in keys]
    values = [k[1] for k in keys]
    return list(
        DataPermissionRule.objects.filter(
            status=1, level=level,
            dimension_type__in=types, dimension_value__in=values,
        )
    )


# ---------------------------------------------------------------------------
# 行级 enforcement
# ---------------------------------------------------------------------------

def _dept_ids_for(scope_type: str, user) -> List[str]:
    """把行级 DEPT/DEPT_AND_SUB 解析成部门 id 集合 (复用 scope_resolver 的树爬取)."""
    from apps.core.scope_resolver import _dept_and_sub_ids, _own_dept_ids
    if scope_type == RowScopeType.DEPT:
        return _own_dept_ids(user)
    if scope_type == RowScopeType.DEPT_AND_SUB:
        return _dept_and_sub_ids(user)
    return []


def row_filter_q(user, scope_field: str = '', creator_field: str = 'created_by') -> Optional[Q]:
    """返回当前用户行级可见范围的 Q 对象; 无生效规则返回 None (调用方回退旧引擎).

    - 存在 ALL 规则 → 返回空 Q() (全量可见, 短路旧 scope_resolver)
    - SELF 规则 → Q(creator_field=user.pk)
    - DEPT / DEPT_AND_SUB / CUSTOM → 按 scope_field(部门 FK 路径) 或 creator 的 department_id 过滤
    - 多条规则取并集 (OR)
    """
    if not (user and getattr(user, 'is_authenticated', False)):
        return None
    if is_super_admin(user):
        # 超管/SUPER_ADMIN 角色走 scope_resolver (其内部 bypass), 保持既有语义
        return None
    rules = _active_rules(user, 'ROW')
    if not rules:
        return None
    if any(r.scope_type == RowScopeType.ALL for r in rules):
        return Q()
    q = Q()
    for r in rules:
        if r.scope_type == RowScopeType.SELF:
            q |= Q(**{creator_field: user.pk})
        elif r.scope_type in (RowScopeType.DEPT, RowScopeType.DEPT_AND_SUB):
            dept_ids = _dept_ids_for(r.scope_type, user)
            if dept_ids:
                target = f'{scope_field}__in' if scope_field else f'{creator_field}__department_id__in'
                q |= Q(**{target: dept_ids})
        elif r.scope_type == RowScopeType.CUSTOM:
            payload = r.scope_payload or {}
            dept_ids = payload.get('department_ids') or []
            if dept_ids:
                target = f'{scope_field}__in' if scope_field else f'{creator_field}__department_id__in'
                q |= Q(**{target: dept_ids})
    # 若没有任何规则能解析出有效范围 (如 DEPT 规则但用户无部门) → 回退旧引擎
    return q if q.children else None


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
    """统一入口 (委派到上方模块函数, 兼容 field_acl / candidate 的命名空间式调用)."""

    row_filter_q = staticmethod(row_filter_q)
    column_permission_for = staticmethod(column_permission_for)
    most_restrictive = staticmethod(most_restrictive)
    clear_column_cache = staticmethod(clear_column_cache)
