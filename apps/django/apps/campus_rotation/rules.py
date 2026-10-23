"""校招域业务规则 —— 聂荣《校招生管理系统 - 需求文档》（2026-10-23）口径的**唯一真源**。

## 为什么单独收口

需求文档把同一条规则写在两个模块里（这正是「同一语义分散在 N 处判定」的典型形态）：

| 规则 | 需求文档出处 A | 需求文档出处 B |
|---|---|---|
| 批次编号 | 人员管理模块 · 字段及规则 | 轮岗安排模块 · 字段及规则 |
| 成班方案 | 人员管理模块 · 字段及规则 | 轮岗安排模块 · 字段及规则 |
| 导师分配 | 人员管理模块 · 字段及规则 | 轮岗安排模块 · 字段及规则（建议导师） |

三处若各写一份，改口径时必然漏改一处 ⇒ 同一批人在「人员管理」和「轮岗安排」里
落到不同批次 / 不同班级 / 不同导师，对不上账。故全部收敛到本模块的纯函数，
两个模块都从这里取数。

## 本模块的硬约束

- **纯函数**：不碰 ORM、不读配置、不抛业务异常 → 可被前端镜像实现、也可被单测逐条锁定。
- **口径可追溯**：每条规则都标注需求文档原文出处，避免"实现与文档各说各话"。

## 前端镜像

前端镜像实现在 `web/app/src/utils/campus.ts`（`batchNoFor` / `planClassSizes`），
两侧必须同步修改 —— 由 `apps/django/apps/campus_rotation/tests/test_rules.py`
与 `web/app/src/utils/__tests__/campusRules.test.ts` 各自锁定同一组期望值。
"""

from __future__ import annotations

import random
from datetime import date, datetime

# ---------------------------------------------------------------------------
# 一、导师带教容量
# ---------------------------------------------------------------------------

#: 导师带教人数上限（聂荣口径：**5 人**）。
#:
#: ⚠️ 历史值是 20（见 `validators.MENTOR_ONGOING_CAPACITY` 的旧注释），
#:    与需求文档「导师带教人数上限为5人」不符 —— 2026-10-23 按需求文档口径下调为 5。
#:    下调后**存量**：某导师名下若已有 > 5 条 ONGOING 轮岗安排，再触发
#:    「进入轮岗中」会被判名额饱和（409 / TransitionNotAllowed）—— 这是口径收紧的
#:    预期行为，不是缺陷；存量超编需业务侧先分流。
MENTOR_CAPACITY = 5


def mentor_saturation(load: int, capacity: int = MENTOR_CAPACITY) -> float:
    """导师带教饱和度 = 已带教人数 ÷ 带教上限。

    :param load: 该导师名下**在轮岗中**的人数
    :param capacity: 带教上限（默认 `MENTOR_CAPACITY`）
    :return: 0.0 ~ 1.0+ 的饱和度；``capacity <= 0`` 时返回 1.0（视为已满，避免除零）
    """
    if capacity <= 0:
        return 1.0
    return max(0, load) / capacity


def pick_mentor(candidates, capacity: int = MENTOR_CAPACITY, rng=None):
    """按聂荣口径挑带教导师。

    需求原文：「带教导师（导师带教人数上限为5人，优先分配给直播间导师，
    如果导师带教已达上限，则按照所有导师带教饱和度进行排序优先分配给饱和度最低的，
    如有相同最低，则随机分配给最低的）」

    判定顺序：

    1. **优先直播间导师**：候选里带 ``is_resource_mentor=True`` 的（= 轮岗资源台账上的
       直播间导师）优先；其中**未达上限**的，取饱和度最低者；
    2. **满额回落**：直播间导师全部达上限 → 回到**全体候选**按饱和度升序排序，
       取最低者；
    3. **同最低随机**：饱和度并列最低 → 随机取一个（避免同批人被固定分配给同一人）。

    :param candidates: 候选导师序列，元素形如
        ``{'id': 'xxx', 'load': 3, 'is_resource_mentor': True}``
        （``load`` = 在轮岗中的人数；``is_resource_mentor`` 缺省视为 False）
    :param capacity: 带教上限
    :param rng: 随机源（``random.Random`` 兼容接口）；默认用模块级 ``random``，
        单测可注入固定种子以获得确定性结果
    :return: 选中的导师 dict；候选为空时返回 ``None``
    """
    items = [c for c in candidates if c]
    if not items:
        return None

    def _lowest(pool):
        """饱和度最低者；并列最低时随机取一个。"""
        best = min(mentor_saturation(c.get('load', 0), capacity) for c in pool)
        tied = [
            c for c in pool
            if mentor_saturation(c.get('load', 0), capacity) == best
        ]
        if len(tied) == 1:
            return tied[0]
        chooser = rng or random
        return chooser.choice(tied)

    room_mentors = [c for c in items if c.get('is_resource_mentor')]
    if room_mentors:
        free = [c for c in room_mentors if c.get('load', 0) < capacity]
        if free:
            return _lowest(free)
    # 直播间导师全满（或没有直播间导师）→ 全体按饱和度最低
    return _lowest(items)


# ---------------------------------------------------------------------------
# 二、批次编号
# ---------------------------------------------------------------------------

#: 月中分界日（聂荣口径：**15 号**）—— 当日及以前为第 01 期，之后为第 02 期。
BATCH_DAY_BOUNDARY = 15

#: 历史入职批次的分段映射（聂荣口径：「历史入职的批次按照1-3月为260001,4-5月为260002」）。
#:
#: 结构：``(年份, 起始月, 结束月, 批次号)``。
#: ⚠️ 只锚定 **2026 年**：文档里的「历史」指的是 26 年那批已入职存量；
#:    26 年之后的月份一律走「年月 + 期号」通用规则（否则 27 年 1 月会拿到 "260001"）。
HISTORICAL_BATCH_SEGMENTS = (
    (2026, 1, 3, '260001'),
    (2026, 4, 5, '260002'),
)


def batch_no(entry_date) -> str:
    """按入职时间生成批次编号。

    需求原文：「批次（基于入职时间自动生成，以月中15号为界，15号及以前为01，
    15号后为02，整体编号为260701/260702）」+「历史入职的批次按照1-3月为260001，
    4-5月为260002」。

    规则：

    - **历史段**（2026 年 1-3 月 / 4-5 月）→ 固定 ``260001`` / ``260002``；
    - **通用规则** → ``YY + MM + 期号``，期号按日是否 ≤ 15 取 01 / 02
      （2026-07-15 → ``260701``，2026-07-16 → ``260702``）；
    - 无入职日期 → 返回 ``''``（不臆造批次）。

    :param entry_date: ``datetime.date`` / ``datetime.datetime`` / ``'YYYY-MM-DD'`` 字符串 / None
    :return: 批次编号字符串
    """
    d = _coerce_date(entry_date)
    if d is None:
        return ''
    for year, m_from, m_to, no in HISTORICAL_BATCH_SEGMENTS:
        if d.year == year and m_from <= d.month <= m_to:
            return no
    period = '01' if d.day <= BATCH_DAY_BOUNDARY else '02'
    return f'{d.year % 100:02d}{d.month:02d}{period}'


def _coerce_date(value):
    """把 date / datetime / 'YYYY-MM-DD' 统一成 ``date``；无法解析返回 None。"""
    if value is None or value == '':
        return None
    # ⚠️ datetime 是 date 的子类 → 必须先判 datetime，否则取不到「日期部分」
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# 三、成班方案
# ---------------------------------------------------------------------------

#: 每班目标人数（聂荣口径：默认 **30 人**成班）
CLASS_TARGET_SIZE = 30
#: 每班人数上限（聂荣口径：每 **30-35** 人成立一个班级）
CLASS_MAX_SIZE = 35
#: 剩余人数阈值（聂荣口径：低于 **10** 人均分，超过（含）10 人独立成班）
CLASS_MIN_LEFTOVER = 10


def plan_class_sizes(
    total: int,
    target: int = CLASS_TARGET_SIZE,
    max_size: int = CLASS_MAX_SIZE,
    min_leftover: int = CLASS_MIN_LEFTOVER,
):
    """按聂荣口径算出成班方案（返回各班人数）。

    需求原文：「班级（按照当前批次每30-35人成立一个班级，默认30人成班，
    若剩余人数低于10人则均分至所有班级，超过10人则独立成班，
    若均分后单个班级人数超过35人，则不均分，独立成班）」

    推演：

    1. 先按 30 人成班：``k = total // 30``，得到 ``k`` 个 30 人班，剩余 ``r = total % 30``；
    2. ``r < 10`` → 把 r **均分**到这 k 个班（多的班多 1 人）；
       但若均分后某个班 > 35 人 → **不均分**，剩余独立成班；
    3. ``r >= 10`` → 剩余 **独立成班**；
    4. ``total < 30`` → 只开 1 个班（人数即 total）。

    例子：``total=65`` → ``[33, 32]``；``total=95`` → ``[32, 32, 31]``；
    ``total=100`` → ``[30, 30, 30, 10]``（剩余 10 人 ≥ 10 → 独立成班）。

    :param total: 该批次的总人数
    :return: 各班人数列表（空列表表示无人）
    """
    total = int(total or 0)
    if total <= 0:
        return []
    if total < target:
        return [total]

    k = total // target
    remainder = total - k * target
    if remainder < min_leftover:
        # 均分：每班先 +q，多出 rem 个人给靠前的班
        q, rem = divmod(remainder, k)
        # 均分后最大班人数 = target + q + (1 if rem else 0)
        biggest = target + q + (1 if rem else 0)
        if biggest > max_size:
            # 均分会让某个班超过 35 人 → 不均分，剩余独立成班
            return [target] * k + [remainder]
        return [target + q + (1 if i < rem else 0) for i in range(k)]
    # 剩余人数 ≥ 10 → 独立成班
    return [target] * k + [remainder]
