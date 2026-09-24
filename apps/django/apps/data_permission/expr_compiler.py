"""两级布尔表达式编译器（数据权限自定义范围）。

模型（与设计文档 §2.4 一致）：
  - 组内表达式 (group.expr) 引用本组条件序号 1..N；
  - 组间组合 (module.expr)  引用条件组序号 1..N；
  - 合法字符：英文圆括号、数字、and/or（大小写不敏感）。

6 条语法约束（校验顺序：词法 -> 括号成对/不嵌套 -> 同层不混用 and/or -> 编号真实）：
  1. 仅支持英文圆括号 ( )（中文括号视为非法字符）
  2. 仅允许 and / or（其余单词视为非法保留字）
  3. 括号须成对出现
  4. 括号不可嵌套（最多一层）
  5. 同一对括号内不得同时出现 and 与 or（须用括号分隔）
  6. 引用的编号须真实存在（组内引用本组条件序号；组间引用条件组序号）

本模块同时提供：
  - validate_expr(expr, max_index) -> None | reason：纯校验（编号范围 1..max_index），返回非法原因或 None。
  - validate_scope_payload(payload, entity) -> None | reason：保存期整包校验。
  - compile_scope_q(payload, entity) -> Q | None：把 {expr, groups} 编译为 Django Q（strict 模式）。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from django.db.models import Q

from .field_map import MODULE_DIMENSION_FIELDS


class ExprError(Exception):
    """表达式语法错误，携带可读原因（对应 §2.4 的 6 条规则）。"""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


# ---------------------------------------------------------------------------
# 词法
# ---------------------------------------------------------------------------

def _tokenize(expr: str) -> list:
    """切成 token：(NUM, int) | (OP, 'and'|'or') | (PAREN, '('|')')。非法字符/保留字直接抛 ExprError。"""
    tokens: list = []
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
            continue
        if ord(c) > 127:
            raise ExprError(f'非法字符 "{c}"（仅支持英文圆括号与 and/or）')
        if c == '(' or c == ')':
            tokens.append(('PAREN', c))
            i += 1
            continue
        if c.isalpha():
            j = i
            while j < n and expr[j].isalpha():
                j += 1
            word = expr[i:j]
            if word.lower() not in ('and', 'or'):
                raise ExprError(f'非法保留字 "{word}"（仅允许 and / or）')
            tokens.append(('OP', word.lower()))
            i = j
            continue
        if c.isdigit():
            j = i
            while j < n and expr[j].isdigit():
                j += 1
            tokens.append(('NUM', int(expr[i:j])))
            i = j
            continue
        raise ExprError(f'非法字符 "{c}"')
    return tokens


# ---------------------------------------------------------------------------
# 递归下降解析（同时做校验 + 求值）
# ---------------------------------------------------------------------------

def _eval_expr(expr: str, max_index: int, index_map: Dict[int, Q], strict: bool) -> Q:
    """把表达式编译为 Q。

    - max_index：合法编号上界（引用须 ∈ 1..max_index）。
    - index_map：编号 -> 真实 Q（求值用）；strict=True 时，引用了不在 index_map 的编号即报"不存在"。
    - 同时完成全部 6 条语法校验；任一不通过抛 ExprError。
    """
    if not expr or not expr.strip():
        raise ExprError('表达式为空')
    tokens = _tokenize(expr)
    pos = [0]

    def atom(depth: int) -> Q:
        if pos[0] >= len(tokens):
            raise ExprError('表达式不完整')
        tok = tokens[pos[0]]
        if tok == ('PAREN', '('):
            if depth >= 1:
                raise ExprError('括号不可嵌套（最多一层）')
            pos[0] += 1
            inner, _ = _or(depth + 1)
            if pos[0] >= len(tokens) or tokens[pos[0]] != ('PAREN', ')'):
                raise ExprError('括号未闭合')
            pos[0] += 1
            return inner
        if tok[0] == 'NUM':
            num = tok[1]
            if num < 1 or num > max_index:
                raise ExprError(f'编号 {num} 超出范围（应为 1..{max_index}）')
            if strict and num not in index_map:
                raise ExprError(f'编号 {num} 不存在')
            pos[0] += 1
            return index_map.get(num, Q())
        raise ExprError('表达式语法错误')

    def _and(depth: int):
        left = atom(depth)
        and_seen = False
        while pos[0] < len(tokens) and tokens[pos[0]] == ('OP', 'and'):
            and_seen = True
            pos[0] += 1
            right = atom(depth)
            left = left & right
        return left, and_seen

    def _or(depth: int):
        left, and_seen = _and(depth)
        or_seen = False
        while pos[0] < len(tokens) and tokens[pos[0]] == ('OP', 'or'):
            if and_seen:
                raise ExprError('同一括号层不能同时出现 and 与 or（需用括号分隔）')
            or_seen = True
            pos[0] += 1
            right, and_seen2 = _and(depth)
            and_seen = and_seen or and_seen2
            left = left | right
        if or_seen and and_seen:
            raise ExprError('同一括号层不能同时出现 and 与 or（需用括号分隔）')
        return left, and_seen

    q, _ = _or(0)
    if pos[0] != len(tokens):
        raise ExprError('表达式存在多余内容')
    return q


# ---------------------------------------------------------------------------
# 对外校验接口
# ---------------------------------------------------------------------------

def validate_expr(expr: str, max_index: int) -> Optional[str]:
    """校验表达式（引用编号须 ∈ 1..max_index）。返回非法原因；合法返回 None。

    不依赖真实 index_map（只验证编号范围），故可独立用于前端等价校验 / 后端保存校验。
    """
    if not expr or not expr.strip():
        return None  # 空表达式由调用方按「默认 AND/OR」处理，不算非法
    try:
        _eval_expr(expr, max_index, {}, strict=False)
    except ExprError as e:
        return e.reason
    return None


# ---------------------------------------------------------------------------
# 编译：条件 -> Q，组 -> Q，组间 -> Q
# ---------------------------------------------------------------------------

def _compile_condition(cond: dict, field_map: Dict[str, Optional[str]]) -> Optional[Q]:
    """单条条件 -> Q。维度无真实字段或无业务值 -> 返回 None（fail-safe no-op）。"""
    if not isinstance(cond, dict):
        return None
    dimension = str(cond.get('dimension') or '').lower()
    operator = str(cond.get('operator') or 'in').lower()
    values = cond.get('values') or []
    if not values and cond.get('value') is not None:
        values = [cond['value']]
    field = field_map.get(dimension)
    if not field:
        return None
    if not values:
        return None
    vals = [v.get('id') if isinstance(v, dict) else v for v in values]
    vals = [v for v in vals if v is not None and v != '']
    if not vals:
        return None
    target = f'{field}__in'
    if operator in ('not_in', 'neq', '!=', 'not_eq'):
        return ~Q(**{target: vals})
    return Q(**{target: vals})


def _combine_qs(qs: List[Q], op: str) -> Q:
    if not qs:
        return Q()
    q = qs[0]
    for nxt in qs[1:]:
        q = (q | nxt) if op == 'or' else (q & nxt)
    return q


def compile_scope_q(payload: dict, entity: str) -> Optional[Q]:
    """把 {expr, groups} 编译为 Q。无有效条件/表达式 -> 返回 None（调用方回退默认 scope）。

    payload 结构：
      {"expr": <组间组合，引用组序号 1..N>,
       "groups": [{"expr": <组内，引用条件序号 1..N>,
                   "conditions": [{"dimension","operator","values":[{id,label}]}]}]}
    同一模块多角色并集的语义由 enforcement.role_entity_scope_q 负责组合，本函数只编单个 payload。
    """
    if not isinstance(payload, dict):
        return None
    field_map = MODULE_DIMENSION_FIELDS.get(entity, {})
    groups = payload.get('groups') or []
    if not groups:
        return None

    group_qs: Dict[int, Q] = {}
    for gi, g in enumerate(groups, start=1):
        if not isinstance(g, dict):
            continue
        conds = g.get('conditions') or []
        cond_qs: Dict[int, Q] = {}
        for ci, c in enumerate(conds, start=1):
            q = _compile_condition(c, field_map)
            if q is not None:
                cond_qs[ci] = q
        if not cond_qs:
            continue
        intra_expr = (g.get('expr') or '').strip()
        if not intra_expr:
            gq = _combine_qs(list(cond_qs.values()), 'and')
        else:
            try:
                gq = _eval_expr(intra_expr, len(conds), cond_qs, strict=True)
            except ExprError as e:  # 非法组内表达式 -> 该组 no-op（fail-safe，不放行）
                raise ExprError(f'条件组 {gi} 组内表达式有误：{e.reason}')
        group_qs[gi] = gq

    if not group_qs:
        return None

    inter_expr = (payload.get('expr') or '').strip()
    if not inter_expr:
        return _combine_qs(list(group_qs.values()), 'or')
    try:
        return _eval_expr(inter_expr, len(groups), group_qs, strict=True)
    except ExprError as e:
        raise ExprError(f'组间组合表达式有误：{e.reason}')


# ---------------------------------------------------------------------------
# 保存期校验（payload 结构 + 语法 + 维度支持性）
# ---------------------------------------------------------------------------

def validate_scope_payload(payload: dict, entity: str) -> Optional[str]:
    """保存前校验 CUSTOM scope_payload。返回非法原因；合法返回 None。"""
    if not isinstance(payload, dict):
        return 'scope_payload 必须是对象'
    groups = payload.get('groups')
    if not isinstance(groups, list) or not groups:
        return '请至少配置 1 个条件组'
    field_map = MODULE_DIMENSION_FIELDS.get(entity, {})
    total_conditions = 0
    for gi, g in enumerate(groups, start=1):
        if not isinstance(g, dict):
            return f'条件组 {gi} 格式错误'
        conds = g.get('conditions') or []
        if not isinstance(conds, list) or not conds:
            return f'条件组 {gi} 至少需要 1 条条件'
        cond_idx_map: Dict[int, Q] = {}
        for ci, c in enumerate(conds, start=1):
            if not isinstance(c, dict):
                return f'条件组 {gi} 第 {ci} 条条件格式错误'
            dimension = str(c.get('dimension') or '').lower()
            if dimension not in field_map or not field_map.get(dimension):
                return f'条件组 {gi} 第 {ci} 条：维度 "{dimension}" 在该模块不支持'
            values = c.get('values') or ([] if c.get('value') is None else [c.get('value')])
            if not values:
                return f'条件组 {gi} 第 {ci} 条：请为每条条件选择业务值'
            cond_idx_map[ci] = Q()  # 占位，仅用于编号范围校验
            total_conditions += 1
        # 组内表达式语法校验（引用本组条件序号 1..len(conds)）
        intra_expr = (g.get('expr') or '').strip()
        if intra_expr:
            reason = validate_expr(intra_expr, len(conds))
            if reason:
                return f'条件组 {gi} 组内表达式有误：{reason}'
    if total_conditions == 0:
        return '请至少配置 1 条条件'
    # 组间组合语法校验（引用条件组序号 1..len(groups)）
    inter_expr = (payload.get('expr') or '').strip()
    if inter_expr:
        reason = validate_expr(inter_expr, len(groups))
        if reason:
            return f'组间组合表达式有误：{reason}'
    return None
