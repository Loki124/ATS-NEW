"""人员比例管控系统 v2 — 核心计算引擎（纯函数，scope 感知，与 v2 数据模型对齐）。

所有函数输入 persons / rules / headcounts 均为 dict 列表，便于在 View 层（模型 → dict）
与 verify 脚本（内存数据）之间共用。计算仅对 counted=True 且命中适用范围的人员生效。

v2 关键变更：
- 维度/指标取代旧的 (dim, group)：rule 含 dimension（维度名）+ indicator（指标名）。
- 性别维度指标为「男/女」，分母按 scope.bu（适用范围所属部门）。
- 人数目标（年度 + 12 个月）落在 headcount（指标层），由 compute_count / simulate 使用。
- 新增 sum100 校验：同一 (scope, dimension) 下所有 indicator 的 target 之和必须 == 1.0。
"""
from decimal import Decimal

from .constants import (
    RATIO_NORMAL, RATIO_BELOW, RATIO_ABOVE,
    COUNT_MET, COUNT_GAP, COUNT_UNSET,
    VERDICT_BLOCK, VERDICT_WARN, VERDICT_PASS,
    month_to_index,
)

# 占比加和容差（0.01%），用于 100% 硬校验，规避 2 位小数百分比的舍入毛刺。
SUM_TOLERANCE = Decimal('0.0001')


def _dec(x):
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def _round3(d: Decimal) -> Decimal:
    return d.quantize(Decimal('0.001'))


def _indicator_filter(dimension: str, indicator: str) -> dict:
    """维度 + 指标 -> 人员过滤条件。"""
    if dimension == '院校标签':
        return {'school': indicator}
    if dimension == '专业标签':
        return {'major': indicator}
    if dimension == '性别':
        return {'sex': indicator}
    return {}


def scope_filter(p: dict, scope: dict) -> bool:
    """人员是否命中适用范围（bu 必匹配；position/level 为空表示不限）。"""
    if p.get('bu') != scope.get('bu'):
        return False
    pos = scope.get('position') or ''
    lvl = scope.get('level') or ''
    if pos and p.get('position') != pos:
        return False
    if lvl and p.get('level') != lvl:
        return False
    return True


def persons_in_scope(persons, scope: dict) -> list:
    """适用范围内、且计入核算的人员。"""
    return [p for p in persons if p.get('counted') and scope_filter(p, scope)]


def count(persons, filters):
    n = 0
    for p in persons:
        ok = True
        for k, v in filters.items():
            if p.get(k) != v:
                ok = False
                break
        if ok:
            n += 1
    return n


def count_rule(rule, persons):
    return count(persons, _indicator_filter(rule['dimension'], rule['indicator']))


def denom_rule(rule, persons, scope):
    """比例分母：性别维度 = 该适用范围所属部门人数；其余 = 范围内全部人数。"""
    if rule['dimension'] == '性别':
        return count(persons, {'bu': scope['bu']})
    return len(persons)


def ratio_of(rule, persons, scope):
    n = count_rule(rule, persons)
    d = denom_rule(rule, persons, scope)
    if d == 0:
        return Decimal('0')
    return _dec(n) / _dec(d)


def ratio_status(ratio, rule):
    lo = _dec(rule['lo'])
    hi = _dec(rule['hi'])
    if ratio < lo:
        return RATIO_BELOW
    if ratio > hi:
        return RATIO_ABOVE
    return RATIO_NORMAL


def count_status(actual, target):
    if target is None:
        return COUNT_UNSET
    if actual >= target:
        return COUNT_MET
    return COUNT_GAP


def compute_ratio(persons, rules, scope):
    """实时看板比例（scope 感知）。返回 {total, rows}。"""
    active = persons_in_scope(persons, scope)
    total = len(active)
    rows = []
    for r in rules:
        ratio = ratio_of(r, active, scope)
        rows.append({
            'dimension': r['dimension'],
            'indicator': r['indicator'],
            'actual': count_rule(r, active),
            'denom': denom_rule(r, active, scope),
            'ratio': _round3(ratio),
            'target': _dec(r['target']),
            'lo': _dec(r['lo']),
            'hi': _dec(r['hi']),
            'status': ratio_status(ratio, r),
            'strength': r['strength'],
        })
    return {'total': total, 'rows': rows}


def compute_count(persons, rules, headcounts, scope, year, month):
    """人数规划（scope 感知，指标层 headcount）。返回 CountRow[]。"""
    active = persons_in_scope(persons, scope)
    # indicator -> strength（来自规则，便于展示）
    strength_map = {(r['dimension'], r['indicator']): r['strength'] for r in rules}
    rows = []
    for h in headcounts:
        dim = h['dimension']
        ind = h['indicator']
        onjob = count(active, _indicator_filter(dim, ind))
        annual_target = int(h.get('annual_target', 0) or 0)
        annual_gap = max(annual_target - onjob, 0)
        idx = month_to_index(month)
        monthly = h.get('monthly_targets') or [0] * 12
        month_target = int(monthly[idx - 1]) if 1 <= idx <= 12 else 0
        month_actual = count(active, {**_indicator_filter(dim, ind), 'month': month}) if 1 <= idx <= 12 else 0
        gap = max(month_target - month_actual, 0)
        rows.append({
            'dimension': dim,
            'indicator': ind,
            'strength': strength_map.get((dim, ind), ''),
            'onjob': onjob,
            'annualTarget': annual_target,
            'annualGap': annual_gap,
            'monthTarget': month_target,
            'monthActual': month_actual,
            'gap': gap,
            'status': count_status(month_actual, month_target),
        })
    return rows


def kpi(persons, rules, headcounts, scope, year, month):
    ratio_res = compute_ratio(persons, rules, scope)
    count_res = compute_count(persons, rules, headcounts, scope, year, month)
    warn_count = 0
    hard_violation = 0
    for row in ratio_res['rows']:
        if row['status'] != RATIO_NORMAL:
            if row['strength'] == '硬约束':
                hard_violation += 1
            else:
                warn_count += 1
    month_gap = sum(r['gap'] for r in count_res)
    return {
        'total': ratio_res['total'],
        'ruleCount': len(rules),
        'warnCount': warn_count,
        'hardViolationCount': hard_violation,
        'monthGap': month_gap,
    }


def simulate(draft, rules, persons, headcounts, scope, year, month=None):
    """录入校验（scope 感知）。draft = {school, sex, major, month?}（bu 取 scope）。"""
    active = persons_in_scope(persons, scope)
    tmp_month = draft.get('month') or month
    if month is None:
        month = tmp_month
    tmp = {
        'bu': scope['bu'],
        'school': draft['school'],
        'sex': draft['sex'],
        'major': draft['major'],
        'month': tmp_month,
        'position': scope.get('position') or '',
        'level': scope.get('level') or '',
        'counted': True,
    }
    sim = active + [tmp]

    # 指标层月度目标查找表：(indicator, year) -> 12 月目标
    hmap = {(h['indicator'], h['year']): (h.get('monthly_targets') or [0] * 12) for h in headcounts}
    idx = month_to_index(month)

    rel = [
        next((r for r in rules if r['dimension'] == '院校标签' and r['indicator'] == draft['school']), None),
        next((r for r in rules if r['dimension'] == '专业标签' and r['indicator'] == draft['major']), None),
        next((r for r in rules if r['dimension'] == '性别' and r['indicator'] == draft['sex']), None),
    ]

    block = False
    warn = False
    checks = []
    for r in rel:
        if r is None:
            continue
        ratio = ratio_of(r, sim, scope)
        rstatus = ratio_status(ratio, r)
        month_target = 0
        if 1 <= idx <= 12:
            mt = hmap.get((r['indicator'], year))
            month_target = int(mt[idx - 1]) if mt else 0
        month_actual = count(sim, {**_indicator_filter(r['dimension'], r['indicator']), 'month': month}) if 1 <= idx <= 12 else 0
        cstatus = count_status(month_actual, month_target)
        checks.append({
            'dimension': r['dimension'],
            'indicator': r['indicator'],
            'strength': r['strength'],
            'ratio': _round3(ratio),
            'ratioStatus': rstatus,
            'monthActual': month_actual,
            'monthTarget': month_target,
            'countStatus': cstatus,
        })
        if rstatus != RATIO_NORMAL:
            if r['strength'] == '硬约束':
                block = True
            else:
                warn = True
        mt = month_target or 0
        if cstatus == COUNT_GAP and mt > 0:
            warn = True

    if block:
        verdict = VERDICT_BLOCK
    elif warn:
        verdict = VERDICT_WARN
    else:
        verdict = VERDICT_PASS
    return {'verdict': verdict, 'checks': checks}


# ============================ 100% 加和校验 ============================
def dimension_target_sum(rules, scope_id, dimension) -> Decimal:
    """给定 (scope, dimension)，返回所有 indicator 的 target 之和。"""
    s = Decimal('0')
    for r in rules:
        if r.get('scope_id') == scope_id and r.get('dimension') == dimension:
            s += _dec(r.get('target', 0))
    return s


def check_dimension_sums(rules, scope_id) -> list:
    """返回该 scope 下每个维度的加和校验结果；ok=True 表示 == 100%。"""
    dims = []
    for r in rules:
        if r.get('scope_id') == scope_id and r.get('dimension') not in dims:
            dims.append(r['dimension'])
    out = []
    for d in dims:
        s = dimension_target_sum(rules, scope_id, d)
        out.append({
            'dimension': d,
            'sum': _round3(s),
            'ok': abs(s - Decimal('1')) <= SUM_TOLERANCE,
        })
    return out
