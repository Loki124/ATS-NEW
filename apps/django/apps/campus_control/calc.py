"""人员比例管控系统 v2.1 — 核心计算引擎（纯函数，适用范围由规则/目标自带）。

v2.1 关键变更：
- 适用范围（bu/position/level，全空=全局）直接挂在 rule / headcount 上，不再有独立「方案」。
- 比例分母统一 = 该规则适用范围内的计入人数。
- 100% 加和校验按 (bu, position, level, dimension) 分组。

v2.8 关键变更（G1 真删人数规划）：
- 移除 compute_count / kpi（人数规划看板与 plan 端点），占比看板仅保留 compute_ratio。
- count_status / _accounting_month 保留供 simulate 录入校验使用。
- 新增 _largest_remainder_allocate（最大余数法），供后端按维度总人数精确分配 annual_target。
"""
import math
from calendar import monthrange
from datetime import date as _date
from decimal import Decimal

from .constants import (
    RATIO_NORMAL, RATIO_BELOW, RATIO_ABOVE,
    COUNT_MET, COUNT_GAP, COUNT_UNSET,
    VERDICT_BLOCK, VERDICT_WARN, VERDICT_PASS, VERDICT_LEVEL,
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


def _largest_remainder_allocate(total: int, weights: list) -> list:
    """按权重(weights，和须≈1)把整数 total 分配为若干整数，保证加和严格 = total。

    最大余数法（Hamilton / 最大余数法）：先各取下限 floor，余下整数按小数位降序逐一 +1。
    返回与 weights 同序的整数列表。weights 之和应为 1（100% 校验已保证），浮点毛刺仅影响排序不参与加和。
    """
    n = len(weights)
    if n == 0:
        return []
    total = int(total)
    if total <= 0:
        return [0] * n
    w = [Decimal(str(x)) for x in weights]
    exact = [total * x for x in w]
    floors = [math.floor(e) for e in exact]
    remainder = total - sum(floors)
    order = sorted(range(n), key=lambda i: (exact[i] - floors[i]), reverse=True)
    alloc = floors[:]
    for i in range(remainder):
        alloc[order[i % n]] += 1
    return alloc


def _scope_key(x: dict) -> tuple:
    """适用范围分组键：bu/position/level 归一为空串。"""
    return (
        (x.get('bu') or '').strip(),
        (x.get('position') or '').strip(),
        (x.get('level') or '').strip(),
    )


# legacy 三维度在 Person 上有写死字段；其余（如 身份证籍贯）走动态维度存储 __dim__<维度名>。
_LEGACY_DIM_FIELDS = {'院校标签': 'school', '专业标签': 'major', '性别': 'sex'}


def _dim_field(dimension: str) -> str:
    """返回某维度在人员 dict 上的取值键：legacy 走原字段，动态维度走 __dim__<维度名>。"""
    return _LEGACY_DIM_FIELDS.get(dimension, f'__dim__{dimension}')


def _indicator_filter(dimension: str, indicator: str) -> dict:
    """维度 + 指标 -> 人员过滤条件。"""
    return {_dim_field(dimension): indicator}


def rule_matches(p: dict, rule: dict) -> bool:
    """人员是否命中规则的适用范围（bu/position/level 为空表示不限）。"""
    for field in ('bu', 'position', 'level'):
        rv = rule.get(field) or ''
        if rv and p.get(field) != rv:
            return False
    return True


# 计入核算的人员状态集合（v2.5 核心术语）
_COUNTED_STATUSES = {'在职', '在途Offer', '在途待入职'}


def _accounting_month(p: dict) -> str:
    """返回人员应被计入的核算月份。

    在职人员按「实际入职日期」计入；在途Offer / 在途待入职按「预计入职日期」计入。
    日期不存在时回退到 month 字段。
    """
    status = p.get('status')
    if status == '在职':
        d = p.get('actual_entry_date')
    else:
        d = p.get('expected_entry_date')
    if d:
        # ISO 日期字符串或 date 对象统一处理
        s = str(d)
        try:
            from datetime import date
            if isinstance(d, date):
                return f'{d.month}月'
            # 尝试解析 ISO 字符串
            parts = s.split('-')
            if len(parts) >= 2:
                return f'{int(parts[1])}月'
        except (ValueError, TypeError):
            pass
    return p.get('month') or ''


def persons_for_rule(persons, rule) -> list:
    """命中规则适用范围、且计入核算的人员（counted=true 且状态在核算范围内）。"""
    return [
        p for p in persons
        if p.get('counted') and p.get('status') in _COUNTED_STATUSES and rule_matches(p, rule)
    ]


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


def _count_achievement(persons, rule, month_label=None):
    """年度/本月 达成(在职) / 在途(在途Offer·在途待入职) / 实际(计入核算且指标命中) 人数。

    month_label 指定时仅统计核算月份==该月的人员（本月口径）；否则统计全年（年度口径）。
    """
    in_scope = persons_for_rule(persons, rule)  # 适用范围命中 + counted + 状态在核算集
    ind_filter = _indicator_filter(rule['dimension'], rule['indicator'])
    achieved = in_progress = actual = 0
    for p in in_scope:
        if not all(p.get(k) == v for k, v in ind_filter.items()):
            continue
        if month_label is not None and _accounting_month(p) != month_label:
            continue
        actual += 1
        st = p.get('status')
        if st == '在职':
            achieved += 1
        elif st in ('在途Offer', '在途待入职'):
            in_progress += 1
    return achieved, in_progress, actual


def compute_ratio(persons, rules):
    """实时看板：占比视角(兼容既有测试) + 人数达成视角(年度/本月 × 达成/在途/达成率)。

    v2.10 增量（PRD §3.5 / 设计文档 §1）：
      - 每行新增 4 字段：monthRollBase / monthRollActual / monthRollover / monthAvailableTarget
      - rollover_enabled=False 时 4 字段全为 0、monthAvailableTarget == monthTarget（v2.4 看板零回归）
      - rollover_enabled=True 时按 compute_rollover_target 取值
    """
    total = len([p for p in persons if p.get('counted') and p.get('status') in _COUNTED_STATUSES])
    cur_month = f'{_date.today().month}月'
    cur_idx = _date.today().month - 1
    rows = []
    for r in rules:
        ratio = ratio_of(r, persons)
        ann_ach, ann_ip, _ = _count_achievement(persons, r)
        mon_ach, mon_ip, _ = _count_achievement(persons, r, cur_month)
        annual_target = int(r.get('annual_target') or 0)
        mt = r.get('monthly_targets') or [0] * 12
        month_target = int(mt[cur_idx]) if isinstance(mt, (list, tuple)) and len(mt) >= 12 else 0
        annual_rate = (_round3(_dec(ann_ach) / _dec(annual_target))) if annual_target > 0 else None
        month_rate = (_round3(_dec(mon_ach) / _dec(month_target))) if month_target > 0 else None

        # v2.10：本月浮动 4 字段（按 rollover_enabled 分支；False 时 monthAvailableTarget == monthTarget）
        if r.get('rollover_enabled'):
            roll_base, roll_actual, _rollover, month_rollover = compute_rollover_target(r, persons)
            month_available_target = month_target + month_rollover
        else:
            roll_base = roll_actual = month_rollover = 0
            month_available_target = month_target

        rows.append({
            'dimension': r['dimension'],
            'indicator': r['indicator'],
            'bu': r.get('bu') or '',
            'position': r.get('position') or '',
            'level': r.get('level') or '',
            # —— 新增：人数达成视角 ——
            'annualTarget': annual_target,
            'annualAchieved': ann_ach,
            'annualInProgress': ann_ip,
            'annualRate': annual_rate,
            'monthTarget': month_target,
            'monthAchieved': mon_ach,
            'monthInProgress': mon_ip,
            'monthRate': month_rate,
            # —— v2.10：本月浮动 4 字段 ——
            'monthRollBase': roll_base,
            'monthRollActual': roll_actual,
            'monthRollover': month_rollover,
            'monthAvailableTarget': month_available_target,
            # —— 保留：占比视角（既有测试断言依赖，勿删） ——
            'actual': count_rule(r, persons),
            'denom': denom_rule(r, persons),
            'ratio': _round3(ratio),
            'target': _dec(r['target']),
            'status': ratio_status(ratio, r),
            'strength': r['strength'],
        })
    return {'total': total, 'rows': rows}


def _in_past_months(actual_iso_str, today: _date) -> bool:
    """实际入职日期是否落在「本年 1/1 至 today 月份的上一个月末」闭区间内（v2.10 浮动判定辅助）。

    Q4-A：用于「已过去月份」的精确边界判断。
      - 解析 ISO 字符串（'YYYY-MM-DD'）→ date
      - 越界（解析失败 / 去年 / 未来月）→ False
      - 范围：[today.year-01-01, last_day_of_(today.month - 1)]
      - 1 月时 today.month-1=0 → 不存在上月，自然返 False（B8 边界）

    Parameters
    ----------
    actual_iso_str : str | None
        人员的「实际入职日期」（ISO 字符串，可能为 None）
    today : datetime.date
        当前日期（决定本年 + 已过去月份范围）

    Returns
    -------
    bool
        True 表示该人员入职月份属于「已过去月份」（计入 rollActual）
    """
    if not actual_iso_str:
        return False
    try:
        s = str(actual_iso_str)
        parts = s.split('-')
        if len(parts) < 3:
            return False
        d = _date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, TypeError, IndexError):
        return False
    # 仅「本年」才纳入（去年 / 未来年一律 False）
    if d.year != today.year:
        return False
    # 1 月时无「上月」→ 任何 1 月人员都不算过去（保留 1 月入职人员被本月吸收）
    if today.month <= 1:
        return False
    # 上月末日期 = monthrange(year, today.month-1)[1]（monthrange 返回 [1, 当月天数]）
    prev_month = today.month - 1
    _, last_day_prev = monthrange(today.year, prev_month)
    last_day_date = _date(today.year, prev_month, last_day_prev)
    # 闭区间：[本年-01-01, 上月末]
    return _date(today.year, 1, 1) <= d <= last_day_date


def compute_rollover_target(rule_dict: dict, persons: list, today: _date | None = None) -> tuple:
    """v2.10 本月浮动目标（roll-over）纯函数。

    口径（Q-A10 拍板 — 单一函数内部按 rule.rollover_enabled 切换月目标）：
      - rollBase   = Σ monthly_targets[0..curMonth-2]（已过去月份额定目标合计；B8 边界 curMonth=1 → 0）
      - rollActual = 「在职」且 actual_entry_date ∈ [本年 1/1, curMonth-1 月末] 且
                     命中规则适用范围与指标的人员数（Q4-A / Q5-A）
      - rollover   = max(0, rollBase - rollActual)（Q6-B 负数裁 0）
      - monthRollover = rollover（透传，关闭时恒 0，零回归）

    入口防御（顺序）：
      1. today 默认 → date.today()
      2. cur_month 越界（∉ [1,12]）→ (0,0,0,0)（Q-A4）
      3. rule.year != today.year → (0,0,0,0)（Q-A5 跨年）
      4. rollover_enabled=False → (0,0,0,0)（Q-A10 零回归 + 短路优化）

    计数 MUST REUSE calc.py 的 _COUNTED_STATUSES / rule_matches / _indicator_filter，
    禁止另写谓词，避免与 ratio 看板漂移（设计文档 §7.4 计数口径铁律）。

    Returns
    -------
    tuple[int, int, int, int]
        (rollBase, rollActual, rollover, monthRollover)
    """
    # 1) today 默认
    if today is None:
        today = _date.today()
    # 2) curMonth 越界防御（Q-A4）
    cur_month = today.month
    if not (1 <= cur_month <= 12):
        return (0, 0, 0, 0)
    # 3) 跨年防御（Q-A5）
    if int(rule_dict.get('year', 0) or 0) != today.year:
        return (0, 0, 0, 0)
    # 4) 关闭 → 零回归 + 短路（Q-A10）
    if not rule_dict.get('rollover_enabled'):
        return (0, 0, 0, 0)

    # rollBase = 已过去月份额定目标合计
    # 口径：curMonth=N → Σ monthly_targets[0..N-2]（即前 N-1 月；B8 边界 curMonth=1 → 0）
    # 设计文档 §7.6（`range(curMonth - 2)`） + QA 测试用例 Q3-A 锁定：curMonth=9 → Σ[0..6] = 7 月 = 71。
    # slice 端点 = `cur_month - 2`，外层用 `cur_month >= 3` 守卫避免 `monthly[:-1]`（cur_month=1 时返 11 月）。
    monthly = rule_dict.get('monthly_targets') or [0] * 12
    if cur_month >= 3:
        # 等价于 `sum(monthly[i] for i in range(cur_month - 2))`
        # cur_month=3 → 1 月；cur_month=9 → 1..7 月（QA 测试断言 71）
        roll_base = sum(monthly[:cur_month - 2])
    else:
        # B8 边界 + cur_month=2 退化：均无「前 N-1 月」（slice 为空），统一返 0
        roll_base = 0

    # 口径对齐：rollBase slice `[:cur_month - 2]` 与 _in_past_months 闭区间 [本年 1/1, 上月末] 在
    # 「已过去月份」维度对齐；cur_month ∈ {1, 2} 时 rollBase 由守卫回 0。

    # rollActual = 在职 + 命中规则（范围 + 指标）+ actual_entry_date ∈ [本年 1/1, curMonth-1 月末]
    dim_name = rule_dict.get('dimension', '')
    ind_name = rule_dict.get('indicator', '')
    ind_filter = _indicator_filter(dim_name, ind_name) if dim_name and ind_name else {}
    roll_actual = sum(
        1 for p in persons
        if p.get('counted')
        and p.get('status') == '在职'
        and rule_matches(p, rule_dict)
        and all(p.get(k) == v for k, v in ind_filter.items())
        and _in_past_months(p.get('actual_entry_date'), today)
    )

    # rollover = max(0, rollBase - rollActual)（Q6-B 负数裁 0）
    rollover = max(0, roll_base - roll_actual)
    return (roll_base, roll_actual, rollover, rollover)


def _draft_hits_rule(draft, rule) -> bool:
    """录入草稿是否命中某规则（适用范围匹配 且 指标匹配）。"""
    if not rule_matches(draft, rule):
        return False
    d = rule['dimension']
    return rule['indicator'] == draft.get(_dim_field(d))


def simulate(draft, rules, persons, year, month=None):
    """录入校验。draft = {bu, position?, level?, school, sex, major, month?}。

    月度目标从规则（annual_target / monthly_targets）读取，不再依赖独立人数目标表。
    v2.5 按新核心术语计算：draft 默认视为「在途待入职」，按 expected_entry_date 回退到 month。
    """
    tmp_month = draft.get('month') or month or '8月'
    tmp = {
        **draft, 'month': tmp_month, 'counted': True,
        'status': '在途待入职',
        'expected_entry_date': None,
        'actual_entry_date': None,
    }

    rmap = {}
    for r in rules:
        rmap[(_scope_key(r), r['indicator'], r.get('year'))] = r.get('monthly_targets') or [0] * 12
    idx = month_to_index(tmp_month)

    # v2.7 录入校验只看「人数」，且以「配额是否已满」作为阻断条件：
    #   - 任意规则「本月实际 >= 本月目标」→ 阻断（配额已满，不可再加）
    #   - 否则若有规则「本月实际 < 本月目标」→ 警告（未达配额，但允许提交）
    #   - 否则 → 通过
    # 占比不再参与校验（兵哥决策：占比仅用于规则配置时把规划人数按占比拆到各月）。
    # month_target == 0（未设目标）的规则不参与 verdict 判定，countStatus 显示为「未设目标」。
    block = False
    warn = False
    checks = []
    sim = persons + [tmp]
    for r in rules:
        if r.get('year') != year:
            continue
        if not _draft_hits_rule(draft, r):
            continue
        mt = rmap.get((_scope_key(r), r['indicator'], r.get('year')))
        month_target = int(mt[idx - 1]) if mt and 1 <= idx <= 12 else 0
        if 1 <= idx <= 12:
            month_actual = sum(
                1 for p in sim
                if rule_matches(p, r) and p.get('counted') and p.get('status') in _COUNTED_STATUSES
                and _accounting_month(p) == tmp_month
                and all(p.get(k) == v for k, v in _indicator_filter(r['dimension'], r['indicator']).items())
            )
        else:
            month_actual = 0
        if month_target > 0:
            cstatus = count_status(month_actual, month_target)
            if cstatus == COUNT_MET:
                block = True
            elif cstatus == COUNT_GAP:
                warn = True
        else:
            cstatus = COUNT_UNSET
        checks.append({
            'dimension': r['dimension'],
            'indicator': r['indicator'],
            'bu': r.get('bu') or '',
            'position': r.get('position') or '',
            'level': r.get('level') or '',
            'monthActual': month_actual,
            'monthTarget': month_target,
            'countStatus': cstatus,
        })

    verdict = VERDICT_BLOCK if block else (VERDICT_WARN if warn else VERDICT_PASS)
    return {'verdict': verdict, 'verdict_level': VERDICT_LEVEL[verdict], 'checks': checks}


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
