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
from typing import List, Tuple

from django.core.cache import cache

from apps.data_permission.expr_compiler import compile_scope_q
from apps.data_permission.models import (
    DataPermissionRule,
    DimensionType,
    RowScopeAccess,
    RowScopeType,
)

logger = logging.getLogger(__name__)

# 列级规则缓存 TTL(秒). 规则低频配置, 但列表每行都要查.
_COLUMN_RULES_CACHE_TTL = 60

# 权限严格度 (数值越大越严格)
_SEVERITY = {'READ': 0, 'MASK': 1, 'NONE': 2}

# M07：实体 -> 负责人(owner)字段路径。
# 候选人的「负责人」即推荐人 referrer（Candidate 无独立 owner/locked_by 字段）；
# 未登记实体回退 created_by（绝大多数模型以 created_by 标识创建人/负责人）。
# 写范围 scope_type=OWNER 时据此生成 Q(<owner_field>=user.pk)。
OWNER_FIELD_BY_ENTITY = {
    'candidate': 'referrer',
}


def most_restrictive(a: str | None, b: str | None) -> str | None:
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
    except Exception:  # noqa: BLE001 — ROLE 维度计算失败跳过该维度 (数据权限降级, 不阻断整体 filter)
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


def column_permission_for(user, entity: str, field: str) -> str | None:
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
    result: str | None = None
    for p in perms:
        result = most_restrictive(result, p)
    return result


def clear_column_cache(entity: str | None = None) -> None:
    """规则变更后清列级缓存 (entity 为空时清全部已登记实体).

    2026-10-12 M02: 原实现硬编码 ('candidate','offer','application') 三 entity,
    新增模块 (如 application 之外的 onboarding/invitation) 配了列级规则也会漏清缓存。
    现改为权威集合派生: 库中 distinct entity (含 field_acl 侧实体) ∪ field_map
    登记的全部模块 key —— 两侧取并集, 既不漏新增实体, 也不回归原有三实体。
    """
    if entity:
        cache.delete(f'data_perm:col:{entity}')
        return
    from .field_map import MODULE_DIMENSION_FIELDS

    entities = set(MODULE_DIMENSION_FIELDS)
    entities.update(
        e for e in DataPermissionRule.objects.filter(level='COLUMN')
        .values_list('entity', flat=True).distinct()
        if e
    )
    for ent in entities:
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
    except ImportError:  # role_v2_query 导入失败返 None (无角色范围 = no-op, 不让数据权限计算崩)
        logger.warning('导入 role_v2_query 失败, 角色自定义范围 no-op')
        return None

    if not (user and getattr(user, 'is_authenticated', False)):
        return None
    if is_super_admin(user):
        return None

    try:
        role_codes = list(user_role_codes(user))
    except Exception:  # noqa: BLE001 — user_role_codes 计算失败返 None (no-op, 不阻断数据权限过滤主路径)
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
                # user= 用于 valueSource='dynamic' 的条件（如「需求所属部门 包含
                # 我的负责部门」）在运行时注入当前用户上下文；静态条件不依赖它。
                compiled = compile_scope_q(r.scope_payload, entity, user=user)
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


# ---------------------------------------------------------------------------
# 写范围 enforcement（M07 读写分离）：对称镜像 role_entity_scope_q，但只认 WRITE 规则
# ---------------------------------------------------------------------------

def _owner_field_for(entity: str) -> str:
    """返回实体对应的负责人字段路径（OWNER 写范围用）。"""
    return OWNER_FIELD_BY_ENTITY.get(entity, 'created_by')


def write_scope_q(user, entity: str, action: str | None = None):
    """返回当前用户在某业务模块（entity）的「写范围」Q；无 WRITE 规则返回 None。

    对称镜像 role_entity_scope_q，但仅过滤 level='ROW' AND row_access='WRITE' 的规则。
    RBAC 并集语义与读路径一致（任一角色 ALL -> Q()；NONE -> Q(pk__in=[]) 在 OR 中 no-op；
    CUSTOM -> 编译表达式并参与 OR；OWNER -> 负责人字段命中）。

    关键设计（opt-in 安全默认）：无 WRITE 规则时返回 None，调用方据 None 判定「无额外写限制」
    —— 即不配置写规则 = 沿用既有功能权限（可见即可操作现状不变）。这避免 M07 上线即锁死
    所有写入口。超管直接返回 None。

    v2 动作级 fail-closed（2026-10-13，docs/plan-read-write-action-permission.md §3.4）：
    配置了写范围之后，语义从 fail-open 切换为 fail-closed ——
      1. 停用动作（动作字典 enabled=False）一律拒绝（Q(pk__in=[])）；
      2. 只有 `actions` 授权了当前动作的规则才**贡献范围**（actions=NULL 授权全部）；
         没有任何规则授权该动作 -> 一律拒绝，**绝不回落到功能权限**。
      否则会出现反向放大漏洞：只配 ['edit'] 后 delete 因"无规则包含它"而被 fail-open 放行。
    字典/规则不可读时兜底为种子全集（fail-open），不因基础设施故障扩大拒绝面。
    """
    from django.db.models import Q

    from apps.data_permission import action_registry
    from apps.data_permission.action_map import validate_action

    if action is not None:
        # 早失败：调用方拼错动作名立即暴露，而非静默放行（代码层契约，与字典无关）
        validate_action(action)

    if not (user and getattr(user, 'is_authenticated', False)):
        return None

    try:
        from apps.core.role_v2_query import is_super_admin, user_role_codes
    except ImportError:
        logger.warning('导入 role_v2_query 失败, 写范围 no-op')
        return None

    if is_super_admin(user):
        return None

    try:
        role_codes = list(user_role_codes(user))
    except Exception:  # noqa: BLE001 — user_role_codes 计算失败 no-op, 不阻断写入口主路径
        logger.warning('计算用户角色码失败, 写范围 no-op')
        return None
    if not role_codes:
        return None

    rules = list(DataPermissionRule.objects.filter(
        dimension_type=DimensionType.ROLE,
        dimension_value__in=role_codes,
        level='ROW',
        row_access=RowScopeAccess.WRITE,
        status=1,
        entity=entity,
    ))
    if not rules:
        return None

    # ---- v2 动作级 fail-closed ----
    # 1) 停用动作一律拒绝（字典不可读时 is_action_enabled 兜底为种子全集，不误拒）
    if action is not None and not action_registry.is_action_enabled(action):
        logger.info('写范围拒绝(动作已停用): entity=%s action=%s', entity, action)
        return Q(pk__in=[])

    # 2) 只有授权了当前动作的规则才贡献范围：
    #    actions=NULL 授权全部；否则 action 必须出现在该规则的 actions 里。
    #    任何规则都未授权该动作 -> 一律拒绝（不许回落功能权限）。
    authorized = [
        r for r in rules
        if r.actions is None or (action is not None and action in r.actions)
    ]
    if action is not None and not authorized:
        logger.info('写范围拒绝(动作未授权): entity=%s action=%s', entity, action)
        return Q(pk__in=[])

    qs: list = []
    for r in authorized:
        if r.scope_type == RowScopeType.ALL:
            return Q()  # 并集：任一角色 ALL -> 全量可写
        if r.scope_type == RowScopeType.NONE:
            qs.append(Q(pk__in=[]))  # OR 并集中 no-op
            continue
        if r.scope_type == RowScopeType.OWNER:
            owner_field = _owner_field_for(entity)
            qs.append(Q(**{owner_field: user.pk}))  # 仅负责人可写
            continue
        if r.scope_type == RowScopeType.CUSTOM and r.scope_payload:
            try:
                compiled = compile_scope_q(r.scope_payload, entity, user=user)
            except Exception as e:  # noqa: BLE001 (ExprError 等, fail-safe no-op)
                logger.warning('写范围自定义编译失败, 该规则 no-op: %s', e)
                continue
            if compiled is not None and compiled.children:
                qs.append(compiled)
            else:
                qs.append(Q(pk__in=[]))
        # DEPT / DEPT_AND_SUB / SELF 等旧 scope_type 在本新路径 no-op。

    if not qs:
        return None
    combined = qs[0]
    for nxt in qs[1:]:
        combined = combined | nxt
    return combined


def is_writable(user, entity: str, instance, action: str | None = None) -> bool:
    """当前用户能否写该实体实例（写范围守卫，opt-in fail-open）。

    - 超管 -> True
    - 无 WRITE 规则（write_scope_q 返回 None）-> True（沿用既有功能权限，不锁死写入口）
    - 否则 -> 该实例是否在写范围 Q 内（按 pk 命中）
    """
    wq = write_scope_q(user, entity, action=action)
    if wq is None:
        return True
    model = type(instance)
    return model.objects.filter(wq, pk=instance.pk).exists()


def ensure_writable(user, entity: str, instance, action: str | None = None) -> None:
    """写范围守卫：不可写则抛 django PermissionDenied（DRF 自动转 403）。

    写入口在 get_object() 之后调用即可闭合「可见即可操作」越权写缺口
    （eval 文档 §4.1 风险 V3）。
    """
    from django.core.exceptions import PermissionDenied

    if not is_writable(user, entity, instance, action=action):
        raise PermissionDenied(
            f'无写权限：用户对该 {entity} 记录无写访问（action={action}）'
        )


def filter_writable(user, entity: str, queryset, action: str | None = None):
    """返回 queryset 中当前用户可写的子集（写范围 Q 作为 AND 约束）。

    write_scope_q 为 None 时原样返回（无额外写限制）。
    """
    wq = write_scope_q(user, entity, action=action)
    if wq is None:
        return queryset
    return queryset.filter(wq)


class DataPermissionEnforcement:
    """统一入口 (委派到上方模块函数, 兼容 field_acl / candidate 的命名空间式调用).

    注(Tier 3): 行级 row_filter_q 已移除, 行级范围改由 apps.core.scope_resolver.scope_filter_q 提供.
    本类仅保留列级 ACL 相关入口.
    """

    column_permission_for = staticmethod(column_permission_for)
    most_restrictive = staticmethod(most_restrictive)
    clear_column_cache = staticmethod(clear_column_cache)
    # M07 写范围守卫
    write_scope_q = staticmethod(write_scope_q)
    is_writable = staticmethod(is_writable)
    ensure_writable = staticmethod(ensure_writable)
    filter_writable = staticmethod(filter_writable)
