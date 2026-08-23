"""人员比例管控系统 v2.1 — 核心计算引擎（纯函数，适用范围由规则/目标自带）。

v2.1 关键变更：
- 适用范围（bu/position/level，全空=全局）直接挂在 rule / headcount 上，不再有独立「方案」。
- 比例分母统一 = 该规则适用范围内的计入人数。
- 100% 加和校验按 (bu, position, level, dimension) 分组。
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

# 占比状态容差：实际占比超过 target + RATIO_TOL 才判定为「高于上限」，规避浮点毛刺。
# 取 0.0001（万分之一 = 0.01 个百分点），仅吸收浮点误差，避免把 30.1% 误判为合规。
RATIO_TOL = Decimal('0.0001')


def _dec(x):
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def _round3(d: Decimal) -> Decimal:
    return d.quantize(Decimal('0.001'))


def _scope_key(x: dict) -> tuple:
    """适用范围分组键：bu/position/level 归一为空串。"""
    return (
        (x.get('bu') or '').strip(),
        (x.get('position') or '').strip(),
        (x.get('level') or '').strip(),
    )


def _indicator_filter(dimension: str, indicator: str) -> dict:
    """维度 + 指标 -> 人员过滤条件。"""
    if dimension == '院校标签':
        return {'school': indicator}
    if dimension == '专业标签':
        return {'major': indicator}
    if dimension == '性别':
        return {'sex': indicator}
    return {}


def rule_matches(p: dict, rule: dict) -> bool:
    """人员是否命中规则的适用范围（bu/position/level 为空表示不限）。"""
    for field in ('bu', 'position', 'level'):
        rv = rule.get(field) or ''
        if rv and p.get(field) != rv:
            return False
    return True


def persons_for_rule(persons, rule) -> list:
    """命中规则适用范围、且计入核算的人员。"""
    return [p for p in persons if p.get('counted') and rule_matches(p, rule)]


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
    in_scope = persons_for_rule(persons, rule)
    return count(in_scope, _indicator_filter(rule['dimension'], rule['indicator']))


def denom_rule(rule, persons):
    """比例分母 = 该规则适用范围内的计入人数。"""
    return len(persons_for_rule(persons, rule))


def ratio_of(rule, persons):
    n = count_rule(rule, persons)
    d = denom_rule(rule, persons)
    if d == 0:
        return Decimal('0')
    return _dec(n) / _dec(d)


def ratio_status(ratio, rule):
    """占比状态（v2.4：取消上下限，以 target 为管控上限）。

    实际占比 > target + RATIO_TOL 即视为「高于上限」（超标）；
    否则为「正常」。不再区分低于下限。
    """
    target = _dec(rule['target'])
    if ratio > target + RATIO_TOL:
        return RATIO_ABOVE
    return RATIO_NORMAL


def count_status(actual, target):
    if target is None:
        return COUNT_UNSET
    if actual >= target:
        return COUNT_MET
    return COUNT_GAP


def compute_ratio(persons, rules):
    """实时看板比例。返回 {total, rows}。total = 全部计入人数（跨适用范围）。"""
    total = len([p for p in persons if p.get('counted')])
    rows = []
    for r in rules:
        ratio = ratio_of(r, persons)
        rows.append({
            'dimension': r['dimension'],
            'indicator': r['indicator'],
            'bu': r.get('bu') or '',
            'position': r.get('position') or '',
            'level': r.get('level') or '',
            'actual': count_rule(r, persons),
            'denom': denom_rule(r, persons),
            'ratio': _round3(ratio),
            'target': _dec(r['target']),
            'status': ratio_status(ratio, r),
            'strength': r['strength'],
        })
    return {'total': total, 'rows': rows}


def compute_count(persons, rules, year, month):
    """人数规划（目标承载于规则上，按年度过滤）。返回 CountRow[]。

    每条规则（指标层）自带 annual_target / monthly_targets，作为该指标在该适用范围内的
    人数目标；人数规划的目标数据即直接来源于规则。
    """
    rows = []
    for r in rules:
        if r.get('year') != year:
            continue
        dim = r['dimension']
        ind = r['indicator']
        in_scope = persons_for_rule(persons, r)
        filt = _indicator_filter(dim, ind)
        onjob = count(in_scope, filt)
        # 在途 offer：命中指标 + 状态=已Offer（不限月份，视为当前在途）
        pending_offer = count(in_scope, {**filt, 'status': '已Offer'})
        # 在途待入职：命中指标 + 状态=已入职 且 招聘月份 > 当前 month（未来月份到岗，视为待入职）
        pending_entry = count(in_scope, {**filt, 'status': '已入职', 'month': month}) if month else 0
        annual_target = int(r.get('annual_target', 0) or 0)
        annual_gap = max(annual_target - onjob - pending_offer - pending_entry, 0)
        idx = month_to_index(month)
        monthly = r.get('monthly_targets') or [0] * 12
        month_target = int(monthly[idx - 1]) if 1 <= idx <= 12 else 0
        month_actual = count(in_scope, {**filt, 'month': month}) if 1 <= idx <= 12 else 0
        gap = max(month_target - month_actual, 0)
        rows.append({
            'dimension': dim,
            'indicator': ind,
            'bu': r.get('bu') or '',
            'position': r.get('position') or '',
            'level': r.get('level') or '',
            'strength': r.get('strength', ''),
            'onjob': onjob,
            'pendingOffer': pending_offer,
            'pendingEntry': pending_entry,
            'annualTarget': annual_target,
            'annualGap': annual_gap,
            'monthTarget': month_target,
            'monthActual': month_actual,
            'gap': gap,
            'status': count_status(month_actual, month_target),
        })
    return rows


def kpi(persons, rules, year, month):
    ratio_res = compute_ratio(persons, rules)
    count_res = compute_count(persons, rules, year, month)
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


def _draft_hits_rule(draft, rule) -> bool:
    """录入草稿是否命中某规则（适用范围匹配 且 指标匹配）。"""
    if not rule_matches(draft, rule):
        return False
    d = rule['dimension']
    if d == '院校标签':
        return rule['indicator'] == draft.get('school')
    if d == '专业标签':
        return rule['indicator'] == draft.get('major')
    if d == '性别':
        return rule['indicator'] == draft.get('sex')
    return False


def simulate(draft, rules, persons, year, month=None):
    """录入校验。draft = {bu, position?, level?, school, sex, major, month?}。

    月度目标从规则（annual_target / monthly_targets）读取，不再依赖独立人数目标表。
    """
    tmp_month = draft.get('month') or month or '8月'
    tmp = {**draft, 'month': tmp_month, 'counted': True}

    rmap = {}
    for r in rules:
        rmap[(_scope_key(r), r['indicator'], r.get('year'))] = r.get('monthly_targets') or [0] * 12
    idx = month_to_index(tmp_month)

    block = False
    warn = False
    checks = []
    sim = persons + [tmp]
    for r in rules:
        if not _draft_hits_rule(draft, r):
            continue
        ratio = ratio_of(r, sim)
        rstatus = ratio_status(ratio, r)
        mt = rmap.get((_scope_key(r), r['indicator'], r.get('year')))
        month_target = int(mt[idx - 1]) if mt and 1 <= idx <= 12 else 0
        month_actual = count(
            [p for p in sim if rule_matches(p, r)],
            {**_indicator_filter(r['dimension'], r['indicator']), 'month': tmp_month},
        ) if 1 <= idx <= 12 else 0
        cstatus = count_status(month_actual, month_target)
        checks.append({
            'dimension': r['dimension'],
            'indicator': r['indicator'],
            'bu': r.get('bu') or '',
            'position': r.get('position') or '',
            'level': r.get('level') or '',
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
        if cstatus == COUNT_GAP and month_target > 0:
            warn = True

    if block:
        verdict = VERDICT_BLOCK
    elif warn:
        verdict = VERDICT_WARN
    else:
        verdict = VERDICT_PASS
    return {'verdict': verdict, 'checks': checks}


# ============================ 100% 加和校验（按适用范围分组） ============================
def distinct_scope_keys(rules) -> list:
    """返回规则中出现的所有适用范围分组键。"""
    keys = []
    for r in rules:
        k = _scope_key(r)
        if k not in keys:
            keys.append(k)
    return keys


def dimension_target_sum(rules, scope_key, dimension, year=None) -> Decimal:
    """给定 (适用范围, 维度)，返回所有 indicator 的 target 之和（year 过滤可选）。"""
    s = Decimal('0')
    for r in rules:
        if _scope_key(r) != scope_key or r.get('dimension') != dimension:
            continue
        if year is not None and r.get('year') != year:
            continue
        s += _dec(r.get('target', 0))
    return s


def check_dimension_sums(rules, scope_key, year=None) -> list:
    """返回该适用范围下每个维度的加和校验结果；ok=True 表示 == 100%。

    year 为 None 时不对年份做过滤（纯函数测试用）；否则仅统计该规划年度的规则。
    """
    dims = []
    for r in rules:
        if _scope_key(r) != scope_key:
            continue
        if year is not None and r.get('year') != year:
            continue
        if r.get('dimension') not in dims:
            dims.append(r['dimension'])
    out = []
    for d in dims:
        s = dimension_target_sum(rules, scope_key, d, year)
        out.append({
            'dimension': d,
            'sum': _round3(s),
            'ok': abs(s - Decimal('1')) <= SUM_TOLERANCE,
        })
    return out
