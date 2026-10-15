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

from django.db.models import Q, Subquery

logger = logging.getLogger(__name__)

from .attribute_fields import SCENARIO_ROW_FILTER, attribute_fields_for
from .context_resolvers import (
    DYNAMIC_DIMENSION_RULES,
    DYNAMIC_RELATIONS,
    DYNAMIC_VALUE_TYPES,
    ContextResolveError,
    resolve_dynamic,
    resolve_relation_dept_ids,
    subtree_dept_ids,
)
from .field_map import DIMENSION_META, MODULE_DIMENSION_FIELDS


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
    """部门类动态值来源条件 -> Q（dept 维度 + relation 包含关系）。

    仅 dept 维度支持部门树语义（exact/in_subtree/contains/overlap）；
    user / creator / unit 等维度不套树语义（标量或复合展开另有分发）。
    维度适配规则 = context_resolvers.DYNAMIC_DIMENSION_RULES['dept']。
    """
    if dimension not in DYNAMIC_DIMENSION_RULES['dept']:
        logger.warning('[expr_compiler] 维度 "%s" 暂不支持部门类动态取值, fail-closed', dimension)
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
    q = Q(**{f'{field}__in': sorted(target_ids)})
    operator = str(cond.get('operator') or 'in').lower()
    if operator in ('not_in', 'neq', '!=', 'not_eq'):
        return ~q
    return q


def _compile_dynamic_user(cond: dict, field: str, dimension: str, *, user) -> Q:
    """用户类动态值来源条件 -> Q（owner/creator 维度, 标量 __in）。

    典型配置: 「负责人 包含 当前登录用户」—— 运行时解析为 {user.pk},
    编译为 Q(owner_path__in=[user.pk])。空集（未登录等）-> fail-closed。
    维度适配规则 = context_resolvers.DYNAMIC_DIMENSION_RULES['user']。
    """
    if dimension not in DYNAMIC_DIMENSION_RULES['user']:
        logger.warning('[expr_compiler] 维度 "%s" 暂不支持用户类动态取值, fail-closed', dimension)
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
        logger.warning('[expr_compiler] 用户类动态值为空, fail-closed')
        return _deny_all()
    q = Q(**{f'{field}__in': sorted(ids)})
    operator = str(cond.get('operator') or 'in').lower()
    if operator in ('not_in', 'neq', '!=', 'not_eq'):
        return ~q
    return q


def _compile_dynamic(cond: dict, field: str, dimension: str, *, user) -> Q:
    """动态值来源条件 -> Q（按值类型分发 + 维度适配, M03）。

    - 来源未注册 / 维度不适配 -> fail-closed；
    - dept 值类型 -> _compile_dynamic_dept（树语义 + relation）；
    - user 值类型 -> _compile_dynamic_user（标量 __in）；
    - unit 值类型由 _compile_unit_condition 处理（复合展开），不进本函数。
    维度适配规则唯一来源 = context_resolvers.DYNAMIC_DIMENSION_RULES，
    与保存期校验共用，防「校验放行但编译拒绝」的口径分叉。
    """
    key = str(cond.get('dynamicKey') or '')
    value_type = DYNAMIC_VALUE_TYPES.get(key)
    if value_type is None:
        logger.warning('[expr_compiler] 未注册的动态值来源 "%s", fail-closed', key)
        return _deny_all()
    if dimension not in DYNAMIC_DIMENSION_RULES.get(value_type, frozenset()):
        logger.warning('[expr_compiler] 值类型 "%s" 不适用于维度 "%s", fail-closed',
                       value_type, dimension)
        return _deny_all()
    if value_type == 'dept':
        return _compile_dynamic_dept(cond, field, dimension, user=user)
    if value_type == 'user':
        return _compile_dynamic_user(cond, field, dimension, user=user)
    # unit 值类型不应到达此处（_compile_condition 已提前分发），防御性 fail-closed
    logger.warning('[expr_compiler] 值类型 "%s" 无编译分发, fail-closed', value_type)
    return _deny_all()


def _compile_unit_condition(cond: dict, field_map: Dict[str, dict | str | bool | None], *, user) -> Q | None:
    """unit 复合维度 -> Q（M03, ARCH §3.3.2）。

    管理单元是复合范围: 组织范围(org_scope + 成员 DEPT, 含子级展开) ∪ 人员范围
    (成员 USER/PERSON)。展开唯一实现点 = scope_resolver.iter_unit_scopes，与默认
    scope 的管理单元分支同构（Q(dept_path__in) | Q(creator_path__in)），
    不引入第二套归属语义。

    语义边界（明确决策）: CUSTOM 表达式中的 unit 维度 = 组织+成员展开后的命中，
    **不含**单元内 data_range / person_data_range 的 AND 限制 —— 那是默认 scope
    （管理单元作为行级基础范围）的专属语义，两套语义不混淆。

    值形态:
      静态: cond.values = [{id}] 管理单元 id 列表（引用语义, 单元后续变更自动生效）；
      动态: cond.dynamicKey='currentUser.managedUnits'（运行时解析当前用户授权单元）。
    空壳单元（无组织范围且无成员）-> Q(pk__in=[]) 不放行（fail-safe, 不兜底放宽）；
    动态解析为空集（用户无任何管理单元授权）-> 同样不放行。
    """
    from apps.core.scope_resolver import iter_unit_scopes

    dept_path = field_map.get('dept')
    creator_path = field_map.get('creator')
    if not dept_path and not creator_path:
        return None  # 该实体无任何可展开路径 -> no-op（与未支持维度语义一致）

    if str(cond.get('valueSource') or 'static') == 'dynamic':
        key = str(cond.get('dynamicKey') or '')
        if DYNAMIC_VALUE_TYPES.get(key) != 'unit':
            logger.warning('[expr_compiler] unit 维度动态值来源 "%s" 未注册, fail-closed', key)
            return _deny_all()
        try:
            unit_ids = sorted(resolve_dynamic(key, user))
        except ContextResolveError as e:
            logger.warning('[expr_compiler] 管理单元动态解析失败, fail-closed: %s', e)
            return _deny_all()
        except Exception:  # noqa: BLE001 — DB 异常等同样拒绝, 不可静默放行
            logger.exception('[expr_compiler] 管理单元动态解析异常, fail-closed')
            return _deny_all()
        if not unit_ids:
            logger.warning('[expr_compiler] 用户无管理单元授权, unit 动态条件 fail-closed')
            return _deny_all()
    else:
        raw = cond.get('values') or ([] if cond.get('value') is None else [cond.get('value')])
        unit_ids = [v.get('id') if isinstance(v, dict) else v for v in raw]
        unit_ids = [v for v in unit_ids if v is not None and v != '']
        if not unit_ids:
            return None  # 静态无值 -> no-op（与静态关系维度语义一致）

    q = Q()
    for uid in unit_ids:
        # org_dr / person_dr 刻意不用: CUSTOM 的 unit 维度不含单元内数据范围 AND 限制
        # (默认 scope 专属语义, 见函数 docstring 语义边界)。
        for dept_ids, user_ids, _org_dr, _person_dr, has_all in iter_unit_scopes(
            [uid], app_code='recruit',
        ):
            if has_all:
                return Q()  # 整公司哨兵 -> 恒真（OR 聚合中任一项全量即整体全量）
            unit_q = Q()
            if dept_ids and dept_path:
                unit_q |= Q(**{f'{dept_path}__in': dept_ids})
            if user_ids and creator_path:
                unit_q |= Q(**{f'{creator_path}__in': user_ids})
            if not unit_q.children:
                unit_q = Q(pk__in=[])  # 空壳单元 -> 不放行
            q |= unit_q
    return q if q.children else Q(pk__in=[])


def _norm_ids(cond) -> list:
    """从条件里抽出业务值 id 列表（兼容 {id,label} 形态与单值 value）。"""
    raw = cond.get('values') or []
    if not raw and cond.get('value') is not None:
        raw = [cond['value']]
    return [v.get('id') if isinstance(v, dict) else v for v in raw]


def _negate_if_needed(q, operator):
    """operator 为 not_in/neq/!=/not_eq 时对 Q 取反（语义翻转）。"""
    if str(operator or 'in').lower() in ('not_in', 'neq', '!=', 'not_eq'):
        return ~q
    return q


def _entity_model(entity: str):
    """按模块 key 取实体模型类（懒加载，避免模块级循环导入）。

    返回 None 表示未知模块（调用方应 fail-closed）。
    """
    from apps.candidate.models import Candidate
    from apps.demand.models import Demand
    from apps.position.models import Position

    return {
        'candidate': Candidate,
        'demand': Demand,
        'position': Position,
    }.get(entity)


def _resolve_user_ids(cond: dict, dimension: str, *, user) -> list | None:
    """统一解析用户类维度的目标 id 集合（静态 values 或 动态 currentUser.id）。

    返回字符串 id 列表（与 dfv/JSON 的 `str(i)` 形态对齐，规避 JSON 字面量跨库比较），
    或 None（无值 / 动态源未注册 / 维度不适配 / 异常 —— 调用方据此 no-op / fail-closed）。

    设计约束见 docs/DESIGN_数据权限规则弹窗选项表.md §3.1：
    动态仅支持 currentUser.id；其余动态源（departments/deptSubtree/managedUnits）
    由 dept / unit 分支单独处理，不在此处。
    """
    if str(cond.get('valueSource') or 'static') == 'dynamic':
        key = str(cond.get('dynamicKey') or '')
        if key != 'currentUser.id':
            logger.warning('[expr_compiler] 维度 "%s" 动态源 "%s" 不支持, no-op', dimension, key)
            return None
        if dimension not in DYNAMIC_DIMENSION_RULES['user']:
            logger.warning('[expr_compiler] 维度 "%s" 不适配 currentUser.id, no-op', dimension)
            return None
        try:
            return [str(i) for i in resolve_dynamic('currentUser.id', user)]
        except ContextResolveError as e:
            logger.warning('[expr_compiler] 动态值来源解析失败(%s), no-op: %s', key, e)
            return None
        except Exception:  # noqa: BLE001 — DB 异常等同样拒绝, 不可静默放行
            logger.exception('[expr_compiler] 动态上下文解析异常, no-op')
            return None
    ids = [str(v) for v in _norm_ids(cond) if v not in (None, '')]
    return ids or None


def _compile_json_contains_condition(spec: dict, ids: list, operator: str) -> Q | None:
    """sharers 等多值 JSON 维度 -> Q(field__contains=[ids])。

    sharers 是 JSONField 存用户 id 列表；__contains 表示「列表含全部给定 id」。
    ids 为空（未选值）-> None（no-op，与静态关系维度语义一致）。
    """
    ids = [v for v in ids if v not in (None, '')]
    if not ids:
        return None
    return _negate_if_needed(Q(**{f"{spec['field']}__contains": ids}), operator)


def _compile_dfv_condition(spec: dict, ids: list, operator: str, *, entity_model) -> Q | None:
    """DynamicFieldValue PERSON 维度 -> 子查询命中目标实体 pk。

    DynamicFieldValue 无反向 FK（按 resource+entity_id 字符串键），故用子查询：
    先在 dfv 表找「resource + field_key + value ∈ 目标用户」的 Demand entity_id 集合，
    再按 `via` 把「实体 → Demand」的 ORM 路径映射回当前实体：
      - via == '' ：实体自身即 Demand -> Q(pk__in=demand_ids)
      - via != '' ：entity_model.filter({via}__in=demand_ids) 子查询收口
        （如 position 的 via='demand'、candidate 的 via='applications__position__demand'）
    PERSON value 可能存 int 或 str（前端/历史差异），用 OR 兼容两种；
    ids 为空 -> None（no-op，由上游 _resolve_user_ids 已保证非空）。
    """
    from apps.dynamic_field.models import DynamicFieldValue

    if entity_model is None:
        logger.warning('[expr_compiler] 未知实体模型, dfv 维度 no-op')
        return None
    id_filter = Q()
    for i in ids:
        id_filter |= Q(value=i)
        id_filter |= Q(value=str(i))
    demand_ids = list(
        DynamicFieldValue.objects.filter(
            resource=spec['resource'], field_key=spec['field_key'],
        ).filter(id_filter).values_list('entity_id', flat=True)
    )
    via = spec.get('via', '')
    if not via:
        target = Q(pk__in=demand_ids)
    else:
        linked = Subquery(entity_model.objects.filter(**{f'{via}__in': demand_ids}).values('pk'))
        target = Q(pk__in=linked)
    return _negate_if_needed(target, operator)


def _compile_path_condition(spec: dict, ids: list, operator: str, *, entity_model) -> Q | None:
    """resume_grabber / 候选人 demand_* / position_* 等多跳反向 FK 维度 -> 子查询收口。

    spec['field'] 是相对 entity_model 的跨表 ORM 路径（如
    positions__applications__grabbed_by_id / applications__position__demand__hr_id）；
    先子查询把「命中路径的实体 pk」算出来，再 Q(pk__in=subq) 收口，
    杜绝 Demand→Position→Application / Candidate→Application→Position→Demand
    多对多展开导致的重复行（fan-out）。
    ids 为空 -> None（no-op）。
    """
    if entity_model is None:
        logger.warning('[expr_compiler] 未知实体模型, path 维度 no-op')
        return None
    ids = [v for v in ids if v not in (None, '')]
    if not ids:
        return None
    subq = Subquery(entity_model.objects.filter(**{f"{spec['field']}__in": ids}).values('pk'))
    return _negate_if_needed(Q(pk__in=subq), operator)


def _compile_lock_owner_condition(spec: dict, cond: dict, operator: str, *, user) -> Q | None:
    """简历锁定人复合条件（formal_locked_by OR (temp_locked_by AND 未过期)）。

    支持两种用法：
      - 空值运算符（is_empty / is_not_empty）：忽略 values，按「当前是否被锁定」判断；
      - 用户类运算符（in / not_in）：静态 values 或动态 currentUser.id 解析成 id 集合后匹配。
    空集 / 动态失败 -> None（no-op，与用户类维度统一语义）。
    """
    from django.utils import timezone

    operator = str(operator or 'in').lower()
    now = timezone.now()
    if operator in ('is_empty', 'is_not_empty'):
        empty = Q(formal_locked_by_id__isnull=True) & (
            Q(temp_locked_by_id__isnull=True) | Q(temp_lock_expires_at__lte=now)
        )
        return (~empty) if operator == 'is_not_empty' else empty

    ids = _resolve_user_ids(cond, 'lock_owner', user=user)
    if ids is None:
        return None
    locked = Q(formal_locked_by_id__in=ids) | Q(temp_locked_by_id__in=ids, temp_lock_expires_at__gt=now)
    return _negate_if_needed(locked, operator)


def _compile_condition(
    cond: dict,
    field_map: Dict[str, dict | str | bool | None],
    attribute_map: Dict[str, dict] | None = None,
    *,
    user=None,
    entity_model=None,
) -> Q | None:
    """单条条件 -> Q。

    - 关系维度（kind 缺省 / 'relationship'）：沿用原逻辑（维度 -> ORM 字段 -> in/not_in）。
    - 属性条件（kind='attribute'）：field 为 source_path（如 demand.state），右值=字面量，
      经 _op_to_q 映射 UnifiedOperator。维度无真实字段 / 属性字段未注册 / 无业务值 -> None（no-op）。
    - 动态条件（valueSource='dynamic'）：运行时由 context_resolvers 注入当前用户上下文，
      按值类型分发（dept 树语义 / user 标量 / unit 复合展开）；异常一律 fail-closed（_deny_all）。
    - unit 复合维度（M03）：静态 unit_id 列表或动态 managedUnits，经 iter_unit_scopes
      展开为「部门集合 ∪ 成员用户集合」（_compile_unit_condition）。
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

    # unit 复合维度（M03）：不走单字段路径，专门经 iter_unit_scopes 展开。
    # 必须在通用 field 校验之前 —— field_map 中 unit 的值是复合标记(True)而非 ORM 路径。
    if dimension == 'unit':
        return _compile_unit_condition(cond, field_map, user=user)

    field = field_map.get(dimension)
    if not field:
        return None

    # ---- dict spec 维度（json_contain / dfv / path / lock_owner）----
    # field 既可能是字符串 ORM 路径（既有 dept/owner/creator 等），
    # 也可能是 dict spec（上述四类）。
    if isinstance(field, dict):
        spec = field
        kind = spec.get('kind')
        # 简历锁定人：复合条件 + 空值运算符（人员维度，但额外支持 is_empty/is_not_empty）
        if kind == 'lock_owner':
            return _compile_lock_owner_condition(spec, cond, operator, user=user)
        # 其余用户类维度：统一前置解析（静态 values 或 动态 currentUser.id）
        ids = _resolve_user_ids(cond, dimension, user=user)
        if ids is None:
            return None  # 无值/动态失败 -> no-op（与用户类维度语义一致）
        if kind == 'json_contain':
            return _compile_json_contains_condition(spec, ids, operator)
        if kind == 'dfv':
            return _compile_dfv_condition(spec, ids, operator, entity_model=entity_model)
        if kind == 'path':
            return _compile_path_condition(spec, ids, operator, entity_model=entity_model)
        if kind == 'reverse':  # 兼容旧 spec：无 via 的反向维度，按 path 收口
            return _compile_path_condition(spec, ids, operator, entity_model=entity_model)
        logger.warning('[expr_compiler] 未知维度 spec kind "%s", no-op', kind)
        return None

    # ---- 字符串路径维度（既有：dept/owner/creator 等）----
    # 动态取值分支：值来自当前用户上下文，不读配置里的 values。
    # 注意必须在 field 校验之后 —— 维度无真实 ORM 字段时 no-op（不放行也不报错）。
    if str(cond.get('valueSource') or 'static') == 'dynamic':
        return _compile_dynamic(cond, field, dimension, user=user)

    if not values:
        return None
    raw_vals = [v.get('id') if isinstance(v, dict) else v for v in values]
    raw_vals = [v for v in raw_vals if v is not None and v != '']
    if not raw_vals:
        return None
    # 部门「属于（含下级）」静态支持：relation=in_subtree 时把所选部门 id 展开为
    # 「自身 + 所有子孙部门」后再 __in（复用 context_resolvers.subtree_dept_ids，
    # 与动态 dept 分支同源）。exact 维持原 field__in。
    if dimension == 'dept' and str(cond.get('relation') or 'exact') == 'in_subtree':
        vals = sorted(subtree_dept_ids([str(v) for v in raw_vals]))
    else:
        vals = raw_vals
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
        return {
            f['sourcePath']: f
            for f in attribute_fields_for(entity, scenario=SCENARIO_ROW_FILTER)
        }
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
    entity_model = _entity_model(entity)
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
            q = _compile_condition(c, field_map, attribute_map, user=user, entity_model=entity_model)
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
        attribute_map = {
            f['sourcePath']: f
            for f in attribute_fields_for(entity, scenario=SCENARIO_ROW_FILTER)
        }
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
                # 运算符按维度校验（防前端越权传 is_empty 到普通用户维度）。
                # 隐藏维度（无 DIMENSION_META.operators 条目）跳过校验，保留存量兼容。
                op = str(c.get('operator') or 'in').lower()
                meta = DIMENSION_META.get(dimension)
                allowed_ops = {o['value'] for o in (meta or {}).get('operators', [])}
                if allowed_ops and op not in allowed_ops:
                    return f'条件组 {gi} 第 {ci} 条：运算符 "{op}" 对维度 "{dimension}" 不支持'
                # 简历锁定人空值运算符不要求业务值；其余分支照常校验业务值/动态源。
                if not (dimension == 'lock_owner' and op in ('is_empty', 'is_not_empty')):
                    # 动态取值：不校验业务值（运行时由当前用户上下文注入），
                    # 但来源必须已注册、维度必须适配（M03：dept/user/unit 三值类型
                    # 各有维度适配规则，与编译期共用 DYNAMIC_DIMENSION_RULES，
                    # 防止校验放行但编译拒绝）；仅 dept 值类型有 relation 树语义需校验。
                    if str(c.get('valueSource') or 'static') == 'dynamic':
                        key = str(c.get('dynamicKey') or '')
                        value_type = DYNAMIC_VALUE_TYPES.get(key)
                        if value_type is None:
                            return f'条件组 {gi} 第 {ci} 条：动态值来源 "{c.get("dynamicKey")}" 未注册'
                        allowed_dims = DYNAMIC_DIMENSION_RULES.get(value_type, frozenset())
                        if dimension not in allowed_dims:
                            return (
                                f'条件组 {gi} 第 {ci} 条：动态值来源 "{key}" 不适用于维度 "{dimension}"'
                                f'（仅支持 {" / ".join(sorted(allowed_dims))}）'
                            )
                        if value_type == 'dept':
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
