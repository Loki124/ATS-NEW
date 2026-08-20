"""人员比例管控系统 — 核心计算引擎（纯函数，与 PRD §3 严格对齐）。

所有函数输入 persons / rules 均为 dict 列表（键见 models / constants），
便于在 View 层（模型 → dict）与 verify 脚本（内存数据）之间共用。
计算仅对 counted=True 的人员生效（§3 开头约定）。
"""
from decimal import Decimal

from .constants import (
    RATIO_NORMAL, RATIO_BELOW, RATIO_ABOVE,
    COUNT_MET, COUNT_GAP, COUNT_UNSET,
    VERDICT_BLOCK, VERDICT_WARN, VERDICT_PASS,
)


def _dec(x):
    """统一转 Decimal，兼容 int/float/str/Decimal。"""
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def _round3(d: Decimal) -> Decimal:
    return d.quantize(Decimal('0.001'))


def count(persons, filters):
    """返回 persons 中满足 filters 全部相等条件的记录数。"""
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


def count_rule(rule, persons, extra=None):
    """将 rule 映射为对 persons 的计数（§3.2）。"""
    k = {}
    dim = rule['dim']
    group = rule['group']
    if dim == '院校标签':
        k['school'] = group
    elif dim == '专业标签':
        k['major'] = group
    elif dim == '性别':
        bu, sex = group.split('-', 1)
        k['bu'] = bu
        k['sex'] = sex
    if extra:
        k.update(extra)
    return count(persons, k)


def denom_rule(rule, persons):
    """比例分母（§3.3）。性别维度分母=该部门人数，其余=全公司。"""
    if rule['dim'] == '性别':
        bu = rule['group'].split('-', 1)[0]
        return count(persons, {'bu': bu})
    return len(persons)


def ratio_of(rule, persons):
    """占比 = 命中数 / 分母；分母=0 时占比记为 0（§3.4 / §8 边界）。"""
    n = count_rule(rule, persons)
    d = denom_rule(rule, persons)
    if d == 0:
        return Decimal('0')
    return _dec(n) / _dec(d)


def ratio_status(ratio, rule):
    """比例状态：正常 / 低于下限 / 高于上限（闭区间，§3.5）。"""
    lo = _dec(rule['lo'])
    hi = _dec(rule['hi'])
    if ratio < lo:
        return RATIO_BELOW
    if ratio > hi:
        return RATIO_ABOVE
    return RATIO_NORMAL


def count_status(actual, target):
    """人数状态（§3.6）。"""
    if target is None:
        return COUNT_UNSET
    if actual >= target:
        return COUNT_MET
    return COUNT_GAP


def compute_ratio(persons, rules):
    """实时看板比例（§F3）。返回 {total, rows}。"""
    active = [p for p in persons if p.get('counted')]
    total = len(active)
    rows = []
    for r in rules:
        ratio = ratio_of(r, active)
        rows.append({
            'dim': r['dim'],
            'group': r['group'],
            'actual': count_rule(r, active),
            'denom': denom_rule(r, active),
            'ratio': _round3(ratio),
            'target': _dec(r['target']),
            'lo': _dec(r['lo']),
            'hi': _dec(r['hi']),
            'status': ratio_status(ratio, r),
            'strength': r['strength'],
        })
    return {'total': total, 'rows': rows}


def compute_count(persons, rules, month):
    """人数规划（§F4）。返回 CountRow[]。"""
    active = [p for p in persons if p.get('counted')]
    rows = []
    for r in rules:
        onjob = count_rule(r, active)
        whole = int(r.get('whole', 0) or 0)
        month_target = int(r.get('month_target', 0) or 0)
        month_actual = count_rule(r, active, {'month': month})
        whole_gap = max(whole - onjob, 0)
        gap = max(month_target - month_actual, 0)
        rows.append({
            'dim': r['dim'],
            'group': r['group'],
            'strength': r['strength'],
            'onjob': onjob,
            'whole': whole,
            'whole_gap': whole_gap,
            'month_target': month_target,
            'month_actual': month_actual,
            'gap': gap,
            'status': count_status(month_actual, month_target),
        })
    return rows


def kpi(persons, rules, month):
    """KPI 汇总（§F3 kpi）。"""
    ratio_res = compute_ratio(persons, rules)
    count_res = compute_count(persons, rules, month)
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
        'group_count': len(rules),
        'warn_count': warn_count,
        'hard_violation_count': hard_violation,
        'month_gap': month_gap,
    }


def simulate(draft, rules, persons, month=None):
    """录入校验（§3.7）。draft = {bu, school, sex, major, month?}。"""
    active = [p for p in persons if p.get('counted')]
    tmp_month = draft.get('month') or month
    tmp = {
        'bu': draft['bu'],
        'school': draft['school'],
        'sex': draft['sex'],
        'major': draft['major'],
        'month': tmp_month,
        'counted': True,
    }
    sim = active + [tmp]
    if month is None:
        month = tmp_month

    rel = [
        next((r for r in rules if r['dim'] == '院校标签' and r['group'] == draft['school']), None),
        next((r for r in rules if r['dim'] == '专业标签' and r['group'] == draft['major']), None),
        next((r for r in rules if r['dim'] == '性别' and r['group'] == f"{draft['bu']}-{draft['sex']}"), None),
    ]

    block = False
    warn = False
    checks = []
    for r in rel:
        if r is None:
            continue
        ratio = ratio_of(r, sim)
        rstatus = ratio_status(ratio, r)
        month_actual = count_rule(r, sim, {'month': month})
        cstatus = count_status(month_actual, r.get('month_target'))
        checks.append({
            'dim': r['dim'],
            'group': r['group'],
            'strength': r['strength'],
            'ratio': _round3(ratio),
            'ratio_status': rstatus,
            'month_actual': month_actual,
            'month_target': r.get('month_target'),
            'count_status': cstatus,
        })
        # 比例结论
        if rstatus != RATIO_NORMAL:
            if r['strength'] == '硬约束':
                block = True
            else:
                warn = True  # 软约束 / 仅提示 均计入 warn
        # 人数结论
        mt = r.get('month_target') or 0
        if cstatus == COUNT_GAP and mt > 0:
            warn = True

    if block:
        verdict = VERDICT_BLOCK
    elif warn:
        verdict = VERDICT_WARN
    else:
        verdict = VERDICT_PASS
    return {'verdict': verdict, 'checks': checks}
