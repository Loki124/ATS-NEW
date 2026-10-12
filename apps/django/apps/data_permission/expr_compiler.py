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

import logging
from typing import Dict, List

from django.db.models import Q

logger = logging.getLogger(__name__)

from .attribute_fields import attribute_fields_for
from .context_resolvers import (
    DYNAMIC_RELATIONS,
    DYNAMIC_SOURCE_KEYS,
    ContextResolveError,
    resolve_dynamic,
    resolve_relation_dept_ids,
)
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

def validate_expr(expr: str, max_index: int) -> str | None:
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

def _op_to_q(field: str, operator: str, value=None, meta: dict | None = None) -> Q | None:
    """把 UnifiedOperator（含关系维度小写 in/not_in）映射成 Django Q。

    属性条件右值=字面量（property filter）：record.field OP value。
    不支持的运算符 -> None（fail-safe no-op，不放行也不报错）。
    """
    if not field:
        return None
    op = str(operator or '').upper()
    meta = meta or {}
    if op in ('EQ', '=', '=='):
        if value is None or value == '':
            return None
        return Q(**{field: value})
    if op in ('NEQ', '!=', '<>'):
        if value is None or value == '':
            return None
        return ~Q(**{field: value})
    if op in ('GT', '>'):
        if value is None or value == '':
            return None
        return Q(**{f'{field}__gt': value})
    if op in ('GTE', '>='):
        if value is None or value == '':
            return None
        return Q(**{f'{field}__gte': value})
    if op in ('LT', '<'):
        if value is None or value == '':
            return None
        return Q(**{f'{field}__lt': value})
    if op in ('LTE', '<='):
        if value is None or value == '':
            return None
        return Q(**{f'{field}__lte': value})
    if op in ('BETWEEN',):
        lo = meta.get('min')
        hi = meta.get('max')
        if lo is None or hi is None or lo == '' or hi == '':
            return None
        return Q(**{f'{field}__gte': lo, f'{field}__lte': hi})
    if op in ('IN',):
        vals = value if isinstance(value, list) else [value]
        vals = [v for v in vals if v is not None and v != '']
        if not vals:
            return None
        return Q(**{f'{field}__in': vals})
    if op in ('NOT_IN',):
        vals = value if isinstance(value, list) else [value]
        vals = [v for v in vals if v is not None and v != '']
        if not vals:
            return None
        return ~Q(**{f'{field}__in': vals})
    if op in ('IS_EMPTY',):
        return Q(**{f'{field}__isnull': True}) | Q(**{f'{field}': ''})
    if op in ('IS_NOT_EMPTY',):
        return Q(**{f'{field}__isnull': False}) & ~Q(**{f'{field}': ''})
    # CONTAINS / NOT_CONTAINS / REGEX_MATCH 等留待后续属性条件扩展
    logger.warning('[expr_compiler] 属性条件不支持运算符 "%s", no-op', operator)
    return None


def _deny_all() -> Q:
    """fail-closed 空集：匹配不到任何行。

    动态条件的任何异常（来源未注册 / 无登录用户 / 无负责部门 / DB 异常）
    都必须退到这里，而不是退化成无约束放行。语义上等价于静态路径里
    scope_resolver 的「空部门集合 -> 仅看自己创建」，此处更严格（完全不可见），
    因为动态条件本就没有可回退的静态语义。
    """
    return Q(pk__in=[])


def _compile_dynamic_dept(cond: dict, field: str, dimension: str, *, user) -> Q:
    """动态值来源条件 -> Q。

    仅 dept 维度支持动态取值：部门有树语义，可定义「包含 / 属于」；
    user / creator 等维度是标量（用户 id），套树语义会得到错误结果，
    故非 dept 维度一律 fail-closed。
    """
    if dimension != 'dept':
        logger.warning('[expr_compiler] 维度 "%s" 暂不支持动态取值, fail-closed', dimension)
        return _deny_all()

    try:
        ids = resolve_dynamic(cond.get('dynamicKey'), user)
    except ContextResolveError as e:
        logger.warning('[expr_compiler] 动态值来源解析失败(%s), fail-closed: %s',
                       cond.get('dynamicKey'), e)
        return _deny_all()
    except Exception:  # noqa: BLE001 — DB 异常等同样拒绝, 不可静默放行
        logger.exception('[expr_compiler] 动态上下文解析异常, fail-closed')
        return _deny_all()

    if not ids:
        # 用户不负责任何部门 -> 该条件无意义, fail-closed
        logger.warning('[expr_compiler] 用户无负责部门, 动态条件 fail-closed')
        return _deny_all()

    try:
        target_ids = resolve_relation_dept_ids(cond.get('relation'), ids)
    except ContextResolveError as e:
        logger.warning('[expr_compiler] 包含关系解析失败, fail-closed: %s', e)
        return _deny_all()

    if not target_ids:
        return _deny_all()
    return Q(**{f'{field}__in': sorted(target_ids)})


def _compile_condition(
    cond: dict,
    field_map: Dict[str, str | None],
    attribute_map: Dict[str, dict] | None = None,
    *,
    user=None,
) -> Q | None:
    """单条条件 -> Q。

    - 关系维度（kind 缺省 / 'relationship'）：沿用原逻辑（维度 -> ORM 字段 -> in/not_in）。
    - 属性条件（kind='attribute'）：field 为 source_path（如 demand.state），右值=字面量，
      经 _op_to_q 映射 UnifiedOperator。维度无真实字段 / 属性字段未注册 / 无业务值 -> None（no-op）。
    - 动态条件（valueSource='dynamic'）：运行时由 context_resolvers 注入当前用户上下文，
      经 _compile_dynamic_dept 转 Q；异常一律 fail-closed（_deny_all）。
    """
    if not isinstance(cond, dict):
        return None
    kind = str(cond.get('kind') or 'relationship').lower()

    if kind == 'attribute':
        attribute_map = attribute_map or {}
        field_path = str(cond.get('field') or '')
        meta = attribute_map.get(field_path)
        if not meta:
            logger.warning('[expr_compiler] 属性条件字段 "%s" 未注册, no-op', field_path)
            return None
        orm_field = field_path.split('.', 1)[1] if '.' in field_path else field_path
        operator = cond.get('operator') or 'EQ'
        value = cond.get('value')
        if isinstance(value, dict):
            # 兼容 {id,label} 形态（前端误传），取 id
            value = value.get('id')
        return _op_to_q(orm_field, operator, value, cond.get('meta') or {})

    # ---- 关系维度（原逻辑）----
    dimension = str(cond.get('dimension') or '').lower()
    operator = str(cond.get('operator') or 'in').lower()
    values = cond.get('values') or []
    if not values and cond.get('value') is not None:
        values = [cond['value']]
    field = field_map.get(dimension)
    if not field:
        return None

    # 动态取值分支：值来自当前用户上下文，不读配置里的 values。
    # 注意必须在 field 校验之后 —— 维度无真实 ORM 字段时 no-op（不放行也不报错）。
    if str(cond.get('valueSource') or 'static') == 'dynamic':
        return _compile_dynamic_dept(cond, field, dimension, user=user)

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


def _build_attribute_map(entity: str) -> Dict[str, dict]:
    """按实体构建 属性字段 sourcePath -> 元数据 映射，供属性条件编译/校验使用。
    查询失败（metrics 未装载等）-> 返回空 dict（属性条件降级为 no-op，不阻断整体）。"""
    try:
        return {f['sourcePath']: f for f in attribute_fields_for(entity)}
    except Exception as e:  # noqa: BLE001 — 属性字段源异常降级为空，不影响关系维度编译
        logger.warning('[expr_compiler] 构建属性字段映射失败, 属性条件降级 no-op: %s', e)
        return {}


def compile_scope_q(payload: dict, entity: str, *, user=None) -> Q | None:
    """把 {expr, groups} 编译为 Q。无有效条件/表达式 -> 返回 None（调用方回退默认 scope）。

    payload 结构：
      {"expr": <组间组合，引用组序号 1..N>,
       "groups": [{"expr": <组内，引用条件序号 1..N>,
                   "conditions": [{"dimension","operator","values":[{id,label}]}]}]}
    同一模块多角色并集的语义由 enforcement.role_entity_scope_q 负责组合，本函数只编单个 payload。

    user（可选，仅动态条件需要）：当前登录用户上下文，供 valueSource='dynamic'
    的条件注入「负责部门」等运行时取值。**默认 None 是安全的** —— 静态条件完全
    不依赖它；动态条件在 user 缺失时会 fail-closed（_deny_all），不会误放行。
    因此老调用方（不传 user）保持原行为不变。
    """
    if not isinstance(payload, dict):
        return None
    field_map = MODULE_DIMENSION_FIELDS.get(entity, {})
    attribute_map = _build_attribute_map(entity)
    groups = payload.get('groups') or []
    if not groups:
        return None

    group_qs: Dict[int, Q] = {}
    for gi, g in enumerate(groups, start=1):
        if not isinstance(g, dict):
            continue
        # 模板被删除后，引用它的条件组立即失效（fail-closed）。
        # 条件本体保留不动，便于模板 restore 后原样复活。
        # 注意语义：失效组贡献空集，在组间 OR 里是 no-op（不连累同模块其它组），
        # 在组内 AND 里则会让整组无结果 —— 都符合「这一条规则已作废」的预期。
        if (g.get('templateRef') or {}).get('orphaned'):
            group_qs[gi] = _deny_all()
            continue
        conds = g.get('conditions') or []
        cond_qs: Dict[int, Q] = {}
        for ci, c in enumerate(conds, start=1):
            q = _compile_condition(c, field_map, attribute_map, user=user)
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

def validate_scope_payload(payload: dict, entity: str) -> str | None:
    """保存前校验 CUSTOM scope_payload。返回非法原因；合法返回 None。"""
    if not isinstance(payload, dict):
        return 'scope_payload 必须是对象'
    groups = payload.get('groups')
    if not isinstance(groups, list) or not groups:
        return '请至少配置 1 个条件组'
    field_map = MODULE_DIMENSION_FIELDS.get(entity, {})
    try:
        attribute_map = {f['sourcePath']: f for f in attribute_fields_for(entity)}
    except Exception:  # noqa: BLE001 — 字段源异常时属性条件无法校验，按不支持处理
        attribute_map = {}
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
            kind = str(c.get('kind') or 'relationship').lower()
            if kind == 'attribute':
                field_path = str(c.get('field') or '')
                meta = attribute_map.get(field_path)
                if not meta:
                    return f'条件组 {gi} 第 {ci} 条：属性字段 "{field_path}" 在该模块不支持'
                operator = c.get('operator')
                allowed = {o['value'] for o in meta.get('operators', [])}
                if operator not in allowed:
                    return f'条件组 {gi} 第 {ci} 条：运算符 "{operator}" 对该字段不支持'
                value = c.get('value')
                if operator in ('IS_EMPTY', 'IS_NOT_EMPTY'):
                    pass  # 无需值
                elif operator in ('IN', 'NOT_IN'):
                    if not isinstance(value, list) or not value:
                        return f'条件组 {gi} 第 {ci} 条：请为集合运算符选择业务值'
                elif operator == 'BETWEEN':
                    mv = c.get('meta') or {}
                    if mv.get('min') in (None, '') or mv.get('max') in (None, ''):
                        return f'条件组 {gi} 第 {ci} 条：区间运算符需填写最小值与最大值'
                else:
                    if value is None or value == '':
                        return f'条件组 {gi} 第 {ci} 条：请填写条件值'
            else:
                dimension = str(c.get('dimension') or '').lower()
                if dimension not in field_map or not field_map.get(dimension):
                    return f'条件组 {gi} 第 {ci} 条：维度 "{dimension}" 在该模块不支持'
                # 动态取值：不校验业务值（运行时由当前用户上下文注入），
                # 但必须校验来源与包含关系已注册，且仅 dept 维度支持。
                if str(c.get('valueSource') or 'static') == 'dynamic':
                    if dimension != 'dept':
                        return f'条件组 {gi} 第 {ci} 条：维度 "{dimension}" 暂不支持动态取值'
                    if str(c.get('dynamicKey') or '') not in DYNAMIC_SOURCE_KEYS:
                        return f'条件组 {gi} 第 {ci} 条：动态值来源 "{c.get("dynamicKey")}" 未注册'
                    if str(c.get('relation') or 'exact') not in DYNAMIC_RELATIONS:
                        return f'条件组 {gi} 第 {ci} 条：包含关系 "{c.get("relation")}" 非法'
                else:
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
