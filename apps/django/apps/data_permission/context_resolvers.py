"""数据权限：动态值上下文解析（valueSource='dynamic' 的运行时取值来源）。

## 为什么需要这层

数据权限条件原本只有「配置时手工选死」的静态 values（见 expr_compiler 的静态分支），
这无法表达「需求所属部门 **包含** 当前用户的负责部门」这类**随登录人变化**的条件。
本模块把「当前用户上下文」解析成集合，交由 expr_compiler 转成 ORM 条件。

## 职责边界（刻意收窄）

本模块**只产出集合**，不做任何 ORM 过滤拼接、不认识 entity / 字段名。
包含关系（exact / in_subtree / contains / overlap）的判定留在 expr_compiler，
好处：解析器可独立单测、可缓存，编译器只负责映射。

## 「负责部门」为何天然多值

User.department 是**单值 FK**（models.py:59），真正让一个人管多个部门的是
Department.leader（models.py:195）。而 leader 的 related_name='+' 是匿名的，
没有反向属性可用，只能 Department.objects.filter(leader=user) 显式查询。
因此负责部门 = 所属部门 ∪ 其作为 leader 管辖的部门。

## 部门层级：用 parent 链而非 path 前缀

ancestor 用 parent FK 在内存回溯，subtree 用 path 前缀匹配（与
scope_resolver._subtree_ids_from_dept 保持同源语义）。两者都只全表加载一次
id/path/parent_id 后在内存计算 —— 部门表量级很小（百至千行），
换来 0 次 N+1 查询，且不依赖 path 字段格式是否规范。

## M03 (2026-10-12) 扩展：用户 id 与管理单元 id 来源

原有 dept 两键只能服务 dept 维度。ARCH §3 增加两类键，服务 owner/creator
（标量用户 id）与 unit（复合管理单元）维度：
  - currentUser.id           -> 用户 id 集合 {user.pk}（owner/creator 维度）
  - currentUser.managedUnits -> 管理单元 id 集合（unit 维度；全角色并集口径，
    与 scope_resolver.user_management_unit_ids 同源，不新造组织关系计算）
值类型见 DYNAMIC_VALUE_TYPES；维度适配规则由 expr_compiler 的
_compile_dynamic 按 value_type 分发。
"""
from __future__ import annotations

import logging

from apps.core.models import Department
from apps.core.scope_resolver import user_management_unit_ids

logger = logging.getLogger(__name__)

# 防 parent 链成环时的死循环上限（正常组织层级 <= 6 层，留足余量）
_MAX_DEPTH = 32


class ContextResolveError(Exception):
    """动态上下文解析失败。上层必须 fail-closed（拒绝全部数据），不得放行。"""


# ---- 已注册的动态值来源（与前端 DynamicSourceKey 保持一致）----
DYNAMIC_SOURCE_KEYS: frozenset[str] = frozenset({
    'currentUser.departments',   # 当前用户负责的部门（所属部门 ∪ 其任 leader 的部门）
    'currentUser.deptSubtree',   # 上述部门 + 其所有子部门
    'currentUser.id',            # 当前登录用户 id（owner/creator 维度用）
    'currentUser.managedUnits',  # 当前用户全角色并集的管理单元 id（unit 维度用）
})

# ---- 动态值来源 -> 值类型（决定编译器如何把集合映射到 ORM 条件）----
#   dept : 部门 id 集合，支持 exact/in_subtree/contains/overlap 包含关系
#   user : 用户 id 集合，标量 __in（owner/creator 维度）
#   unit : 管理单元 id 集合，复合展开（unit 维度，见 expr_compiler._compile_unit_condition）
# key 集合与上方 DYNAMIC_SOURCE_KEYS 一致：某 key 在本表中即视为已注册。
DYNAMIC_VALUE_TYPES: dict[str, str] = {
    'currentUser.departments': 'dept',
    'currentUser.deptSubtree': 'dept',
    'currentUser.id': 'user',
    'currentUser.managedUnits': 'unit',
}

# ---- 值类型 -> 可配置维度（保存期校验与编译期分发共用的唯一规则来源）----
#   dept : 仅 dept 维度（唯一支持 relation 树语义的维度）
#   user : owner / creator 维度（标量 __in）
#   unit : unit 复合维度（iter_unit_scopes 展开）
# 修改本表须同步确认 expr_compiler._compile_dynamic 与 validate_scope_payload
# 的行为 —— 两者均引用本表，不得各自硬编码（防「校验放行但编译拒绝」分叉）。
DYNAMIC_DIMENSION_RULES: dict[str, frozenset[str]] = {
    'dept': frozenset({'dept'}),
    'user': frozenset({'owner', 'creator', 'hr', 'requested_by'}),
    'unit': frozenset({'unit'}),
}

# ---- 业务字段集合与动态集合的包含关系 ----
DYNAMIC_RELATIONS: frozenset[str] = frozenset({
    'exact',       # 业务字段 ∈ 动态集合（精确）
    'in_subtree',  # 业务字段 ∈ 动态集合 ∪ 其所有子部门
    'contains',    # 业务字段是动态集合中某元素的祖先（业务部门为上级）
    'overlap',     # 上述三者取并
})


def responsible_department_ids(user) -> set[str]:
    """当前用户负责的部门 id 集合 = 所属部门 ∪ 其作为 leader 管辖的部门。

    返回空集表示「该用户不负责任何部门」，调用方必须据此 fail-closed。
    """
    if user is None or not getattr(user, 'is_authenticated', False):
        raise ContextResolveError('无登录用户上下文')

    ids: set[str] = set()
    dept_id = getattr(user, 'department_id', None)
    if dept_id:
        ids.add(str(dept_id))

    # leader 反向 related_name='+'（models.py:199 匿名），只能显式查询
    led = Department.objects.filter(leader=user).values_list('id', flat=True)
    ids.update(str(x) for x in led if x)

    # 只保留真实存在的部门（防悬空 FK / 脏数据）
    if not ids:
        return set()
    return {str(x) for x in Department.objects.filter(id__in=ids).values_list('id', flat=True)}


def resolve_dynamic(key: str, user) -> set:
    """把动态值来源解析为对应值类型的 id 集合（部门 / 用户 / 管理单元）。

    失败一律抛 ContextResolveError（含来源未注册、DB 异常向上冒泡），
    由编译器转成 Q(pk__in=[]) —— 即 fail-closed，绝不静默放行。
    """
    key = str(key or '')
    if key not in DYNAMIC_SOURCE_KEYS:
        raise ContextResolveError(f'未注册的动态值来源: {key!r}')
    if user is None or not getattr(user, 'is_authenticated', False):
        raise ContextResolveError('无登录用户上下文')

    if key == 'currentUser.id':
        pk = getattr(user, 'pk', None)
        if pk is None:
            raise ContextResolveError('登录用户无 pk')
        return {pk}

    if key == 'currentUser.managedUnits':
        # 全角色并集口径, 与默认 scope 的 L1 同源 (scope_resolver 单一实现点)
        return set(user_management_unit_ids(user))

    own = responsible_department_ids(user)
    if key == 'currentUser.departments':
        return own
    # 'currentUser.deptSubtree'
    return subtree_dept_ids(sorted(own))


def ancestor_dept_ids(dept_ids) -> set[str]:
    """返回这些部门的**所有祖先**部门 id（不含自身）。

    用于 relation='contains'：需求部门若是用户负责部门的上级，则应可见。
    例：负责「智能BG/前端组」 -> 祖先 {智能BG, 根}，需求挂在「智能BG」上即命中。

    用 parent FK 内存回溯（而非 path 前缀）：不依赖 path 字段格式，
    且天然防脏数据里的空 path。
    """
    wanted = {str(x) for x in (dept_ids or []) if x not in (None, '')}
    if not wanted:
        return set()

    parent_of = {
        str(did): (str(pid) if pid else None)
        for did, pid in Department.objects.all().values_list('id', 'parent_id')
    }
    out: set[str] = set()
    for start in wanted:
        cur = parent_of.get(start)
        depth = 0
        while cur and depth < _MAX_DEPTH:
            if cur in out:       # 已访问过 -> 成环或已展开，停止
                break
            out.add(cur)
            cur = parent_of.get(cur)
            depth += 1
    return out


def subtree_dept_ids(dept_ids) -> set[str]:
    """返回这些部门**自身 + 所有子孙**部门 id（按 Department.path 前缀匹配）。

    用于 relation='in_subtree'：部门负责人看本部门及下级的全部数据。
    与 scope_resolver._subtree_ids_from_dept 同源语义，同样不把祖先塞进范围。
    """
    wanted = {str(x) for x in (dept_ids or []) if x not in (None, '')}
    if not wanted:
        return set()

    rows = [(str(did), path or '') for did, path in Department.objects.all().values_list('id', 'path')]
    prefixes = [path for did, path in rows if did in wanted and path]
    if not prefixes:
        return wanted
    return {did for did, path in rows if any(path.startswith(p) for p in prefixes)}


def resolve_relation_dept_ids(relation: str, dynamic_ids: set[str]) -> set[str]:
    """按包含关系把「动态集合」映射为最终要匹配的部门 id 集合。

    编译器专用：返回空集时调用方须 fail-closed。
    """
    relation = str(relation or 'exact')
    if relation not in DYNAMIC_RELATIONS:
        raise ContextResolveError(f'未注册的包含关系: {relation!r}')
    if not dynamic_ids:
        return set()

    if relation == 'exact':
        return set(dynamic_ids)
    if relation == 'in_subtree':
        # subtree_dept_ids 已含自身
        return subtree_dept_ids(sorted(dynamic_ids))
    if relation == 'contains':
        # ancestor 不含自身，这里必须并上：需求恰好挂在用户自己负责的部门上时
        # 同样应当可见（「自己的部门包含自己的部门」）。
        return set(dynamic_ids) | ancestor_dept_ids(sorted(dynamic_ids))
    # overlap：exact ∪ in_subtree ∪ contains
    return (
        set(dynamic_ids)
        | subtree_dept_ids(sorted(dynamic_ids))
        | ancestor_dept_ids(sorted(dynamic_ids))
    )