"""排名算法 —— 纯函数层（契约 §2.3 / 逆向清单 §5 A1~A9）。

本模块**只做算术**，不碰数据库、不碰 request —— 这样每个公式都能被单测
逐个锁死数值（契约 §2.4 要求「5 个公式各 ≥1 例 + 边界」），
DB 取数与聚合在 `services.py`。

公式逐条对齐（逆向清单 §5 原文）：

| 编号 | 算法 | 公式 | 证据 |
|---|---|---|---|
| A1 | 月度总分 | `round(KPI×0.6 + 考试×0.4) + 加减分` | core.js:255 |
| A2 | 累计综合均分 | 所有月度总分的算术平均（保留 1 位） | core.js:268 |
| A3 | 综合排名 | `round(KPI×0.5) + round(学习成长×0.3) + round(五行五力×0.2) + 附加分` | views2.js:101 |
| A4 | 学习成长维度 | `平均(课程进度均值, 考试得分均值)`（有哪项算哪项） | views2.js:71 |
| A5 | 五行五力 | 5 维均值 | data.js:897, views2.js:82 |
| A6 | 附加分 | 活动奖励分值 + 历月加减分之和 | views2.js:88 |
| A7 | 月报综合得分 | `业务导师总分×0.7 + 成长导师总分×0.3`，各总分 = 5 子项之和 | core.js:258 |
| A8 | 班主任排名 | 按所带学生累计综合均分降序；另算 5 维平均名次 | views2.js:128 |
| A9 | 考勤维度 | `Σ(出勤 − 迟到×0.5) / 月数` | views2.js:141 |

🔴 **四舍五入语义必须复刻 JS，不能直接用 Python 内置 round()**：
原始实现是 JS（core.js / views2.js），`Math.round` 对 .5 一律**向 +∞ 进位**
（Math.round(2.5)=3、Math.round(-2.5)=-2）；
而 Python 内置 `round()` 是「银行家舍入」（round-half-to-even）：round(2.5)=2、
round(-2.5)=-2 —— 同一批数据算出的总分/排名会**系统性偏离目标站**。
本模块统一用 `decimal` 复刻 JS 语义（见 `js_round`）。
"""
import re
from decimal import Decimal, ROUND_HALF_DOWN, ROUND_HALF_UP

#: 活动奖励文本解析：形如「+3 分」「3」「-1分」的整数（逆向清单 A6 / 契约 §3.2 备注）
_REWARD_INT_RE = re.compile(r'[-+]?\d+')


def _dec(value):
    """转 Decimal（float 走 str() 避免二进制尾数误差：0.1+0.2 问题）。"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(str(value))


def js_round(value, digits=0):
    """复刻 JS `Math.round` 的四舍五入（.5 向 +∞ 进位），而非 Python 银行家舍入。

    Args:
        value: 数值（int / float / Decimal / str）。
        digits: 保留小数位（0 = 取整）。

    Returns:
        Decimal（四舍五入后的值）。
    """
    d = _dec(value)
    quant = Decimal(1).scaleb(-digits)
    # JS Math.round = floor(x + 0.5)：正数 .5 进位、负数 .5 保持（向 0）。
    # decimal 的 ROUND_HALF_UP 是「远离 0」，负数会与 JS 不一致 → 按符号选舍入模式。
    rounding = ROUND_HALF_UP if d >= 0 else ROUND_HALF_DOWN
    return d.quantize(quant, rounding=rounding)


def parse_reward(text):
    """从活动奖励文本里解析整数分值（逆向清单 A6）。

    契约 §3.2 备注：`reward` 文本形如「+3 分」，排名计算时解析其中的整数。
    解析不到数字时按 0 计（不抛错 —— 一条脏数据不该让整个排名挂掉）。
    """
    if text is None:
        return 0
    if isinstance(text, (int, Decimal)):
        return int(text)
    m = _REWARD_INT_RE.search(str(text))
    return int(m.group()) if m else 0


# ---------------------------------------------------------------------------
# A1 月度总分
# ---------------------------------------------------------------------------
def monthly_total_score(kpi, exam, adjust=0):
    """A1：`totalScore = round(KPI×0.6 + 考试×0.4) + 加减分`。

    ⚠️ 先对加权分取整，**再加**加减分 —— 加减分是整数分，不参与小数进位。
    """
    base = js_round(_dec(kpi) * Decimal('0.6') + _dec(exam) * Decimal('0.4'))
    return base + _dec(adjust or 0)


# ---------------------------------------------------------------------------
# A2 累计综合均分
# ---------------------------------------------------------------------------
def avg_total(total_scores):
    """A2：所有月度 totalScore 的算术平均（保留 1 位）。

    无数据时返回 None（不返回 0 —— 「没有考核记录」与「考核得 0 分」是两回事）。
    """
    values = [_dec(v) for v in total_scores if v is not None]
    if not values:
        return None
    return js_round(sum(values) / len(values), 1)


# ---------------------------------------------------------------------------
# KPI 维度
# ---------------------------------------------------------------------------
def dim_kpi(kpis):
    """KPI 维度：`round(所有月度 kpi 的算术平均)`（契约 §2.3）。"""
    values = [_dec(v) for v in kpis if v is not None]
    if not values:
        return None
    return js_round(sum(values) / len(values))


# ---------------------------------------------------------------------------
# A4 学习成长
# ---------------------------------------------------------------------------
def dim_learn(course_avg, exam_avg):
    """A4：`round(mean(课程进度均值, 考试得分均值))`（有哪项算哪项）。

    两个来源都缺时返回 None（调用方按 0 计入综合分，见 composite_score）。
    """
    parts = [_dec(v) for v in (course_avg, exam_avg) if v is not None]
    if not parts:
        return None
    return js_round(sum(parts) / len(parts))


# ---------------------------------------------------------------------------
# A5 五行五力
# ---------------------------------------------------------------------------
def dim_force(values):
    """A5：`round(5 个维度分值的算术平均)`。"""
    numbers = [_dec(v) for v in values if v is not None]
    if not numbers:
        return None
    return js_round(sum(numbers) / len(numbers))


# ---------------------------------------------------------------------------
# A6 附加分
# ---------------------------------------------------------------------------
def dim_add(activity_rewards, adjusts):
    """A6：`Σ活动奖励分值 + Σ历月加减分`。

    `activity_rewards` 传**原始文本或整数**均可（文本走 parse_reward 解析）。
    """
    reward_total = sum(
        parse_reward(r) if not isinstance(r, (int, Decimal)) else int(r)
        for r in (activity_rewards or [])
    )
    adjust_total = sum(int(_dec(a) or 0) for a in (adjusts or []))
    return Decimal(reward_total + adjust_total)


# ---------------------------------------------------------------------------
# A3 综合得分
# ---------------------------------------------------------------------------
def composite_score(dim_kpi_value, dim_learn_value, dim_force_value, dim_add_value):
    """A3：`round(KPI×0.5) + round(学习成长×0.3) + round(五行五力×0.2) + 附加分`。

    ⚠️ 每一项**分别**取整后再相加（不是先加权和再取整）—— 契约 §2.3 与
    逆向清单 A3 的写法都是逐项 round，照抄。
    缺失维度按 0 计入（无学习数据的人不会因「无数据」被额外惩罚，也不会被加分）。
    """
    kpi_part = js_round(_dec(dim_kpi_value or 0) * Decimal('0.5'))
    learn_part = js_round(_dec(dim_learn_value or 0) * Decimal('0.3'))
    force_part = js_round(_dec(dim_force_value or 0) * Decimal('0.2'))
    return kpi_part + learn_part + force_part + _dec(dim_add_value or 0)


# ---------------------------------------------------------------------------
# A7 月报综合得分
# ---------------------------------------------------------------------------
def report_role_total(case, insight, problem, clarity, executable):
    """A7 之一：角色总分 = 5 子项之和（case/insight/problem/clarity/executable）。"""
    return (
        _dec(case or 0) + _dec(insight or 0) + _dec(problem or 0)
        + _dec(clarity or 0) + _dec(executable or 0)
    )


def report_final_score(business_total, growth_total):
    """A7：`round(业务导师总分×0.7 + 成长导师总分×0.3, 1)`。"""
    return js_round(
        _dec(business_total or 0) * Decimal('0.7')
        + _dec(growth_total or 0) * Decimal('0.3'),
        1,
    )


# ---------------------------------------------------------------------------
# A9 考勤维度
# ---------------------------------------------------------------------------
def attendance_dim(rows):
    """A9：`round(Σ(出勤 − 迟到×0.5) / 月数, 1)`。

    Args:
        rows: 每项含 `attend_days` / `late_count`（月度考勤汇总行）。

    无月度考勤记录时返回 None。
    """
    if not rows:
        return None
    total = Decimal(0)
    for row in rows:
        attend = _dec(row.get('attend_days') or 0)
        late = _dec(row.get('late_count') or 0)
        total += attend - late * Decimal('0.5')
    return js_round(total / len(rows), 1)


# ---------------------------------------------------------------------------
# A8 班主任排名
# ---------------------------------------------------------------------------
def teacher_avg_total(student_avg_totals):
    """A8：`avgTotal = 所带学生 avgTotal 的算术平均`（保留 1 位）。"""
    values = [_dec(v) for v in student_avg_totals if v is not None]
    if not values:
        return None
    return js_round(sum(values) / len(values), 1)


def teacher_rank_avg(student_ranks):
    """A8：`rankAvg[dim] = 所带学生在该维度名次的算术平均`（保留 1 位）。"""
    values = [_dec(v) for v in student_ranks if v is not None]
    if not values:
        return None
    return js_round(sum(values) / len(values), 1)


# ---------------------------------------------------------------------------
# 名次
# ---------------------------------------------------------------------------
def competition_ranks(values):
    """并列名次（标准 1224 口径）：同分同名次，后续名次跳过占位。

    Args:
        values: 已按名次排好序的数值序列（Decimal / int）。

    Returns:
        与入参等长的名次列表。
    """
    ranks = []
    prev = None
    prev_rank = 0
    for idx, value in enumerate(values, start=1):
        if prev is not None and _dec(value) == _dec(prev):
            ranks.append(prev_rank)
        else:
            ranks.append(idx)
            prev_rank = idx
        prev = value
    return ranks
