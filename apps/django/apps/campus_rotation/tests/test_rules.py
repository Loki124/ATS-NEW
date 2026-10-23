"""校招域规则护栏（聂荣 2026-10-23《校招生管理系统 - 需求文档》口径）。

锁三条被「人员管理 / 轮岗安排 / 班级管理」共用的规则，任何一条口径被改都判红：

1. **批次编号**（月中 15 号为界；历史段 260001 / 260002）
2. **成班方案**（默认 30 人、30~35 人上限、剩余 <10 均分 / ≥10 独立成班）
3. **导师分配**（上限 5 人、直播间导师优先、饱和度最低、并列随机）

前端镜像实现见 `web/app/src/utils/campus.ts`（`batchNoFor` / `planClassSizes`），
两侧期望值必须一致 —— 前端那份由 `campusRules.test.ts` 锁定。
"""
from datetime import date

import pytest

from apps.campus_rotation import rules


# ---------------------------------------------------------------------------
# 一、批次编号
# ---------------------------------------------------------------------------

class TestBatchNo:
    """批次编号：年中 15 号为界 + 历史两段固定号。"""

    @pytest.mark.parametrize(
        'entry_date,expected',
        [
            # 通用规则：YY + MM + 期号（15 号及以前 = 01，15 号后 = 02）
            (date(2026, 7, 1), '260701'),
            (date(2026, 7, 14), '260701'),
            (date(2026, 7, 15), '260701'),
            (date(2026, 7, 16), '260702'),
            (date(2026, 7, 31), '260702'),
            (date(2026, 8, 15), '260801'),
            (date(2026, 8, 16), '260802'),
            (date(2026, 12, 20), '261202'),
            # 历史段：1-3 月 = 260001，4-5 月 = 260002（不再按日切期）
            (date(2026, 1, 5), '260001'),
            (date(2026, 3, 31), '260001'),
            (date(2026, 4, 1), '260002'),
            (date(2026, 5, 31), '260002'),
            # 6 月起走通用规则
            (date(2026, 6, 10), '260601'),
        ],
    )
    def test_按规则生成(self, entry_date, expected):
        assert rules.batch_no(entry_date) == expected

    def test_历史段只锚定2026年(self):
        """27 年 1 月不得复用 "260001"（否则批次号会跨年撞号）。"""
        assert rules.batch_no(date(2027, 1, 10)) == '270101'
        assert rules.batch_no(date(2027, 4, 10)) == '270401'

    @pytest.mark.parametrize('empty', [None, '', 'not-a-date'])
    def test_无入职日期不臆造批次(self, empty):
        assert rules.batch_no(empty) == ''

    def test_接受字符串日期(self):
        assert rules.batch_no('2026-07-16') == '260702'


# ---------------------------------------------------------------------------
# 二、成班方案
# ---------------------------------------------------------------------------

class TestPlanClassSizes:
    """成班方案：默认 30 人成班，剩余 <10 均分、≥10 独立成班，均分后超 35 则不均分。"""

    @pytest.mark.parametrize(
        'total,expected',
        [
            (0, []),
            (1, [1]),
            (29, [29]),
            # 刚好整除 → 全 30 人班，无剩余
            (30, [30]),
            (60, [30, 30]),
            # 剩余 <10 → 均分到所有班
            (32, [32]),
            (65, [33, 32]),
            (95, [32, 32, 31]),
            # 剩余 ≥10 → 独立成班
            (40, [30, 10]),
            (70, [30, 30, 10]),
            (100, [30, 30, 30, 10]),
            (101, [30, 30, 30, 11]),
        ],
    )
    def test_成班方案(self, total, expected):
        assert rules.plan_class_sizes(total) == expected

    def test_均分后超35人则不均分独立成班(self):
        """total=39：1 个班 + 剩余 9 人，均分后该班会变 39 人 > 35 → 不均分。"""
        assert rules.plan_class_sizes(39) == [30, 9]

    def test_每班人数均为正且不丢人(self):
        """独立成班的剩余班人数 <30 是规则的必然结果（30*k+剩余 无法整除成 30~35）。"""
        for total in range(1, 200):
            sizes = rules.plan_class_sizes(total)
            assert sum(sizes) == total, f'total={total} 人数未守恒'
            assert all(s > 0 for s in sizes), f'total={total} 出现空班'

    def test_守恒_人数不丢不重(self):
        for total in (35, 66, 99, 128):
            assert sum(rules.plan_class_sizes(total)) == total


# ---------------------------------------------------------------------------
# 三、导师分配
# ---------------------------------------------------------------------------

class TestMentorRules:
    """导师分配：上限 5 人、直播间导师优先、饱和度最低、并列最低随机。"""

    def test_容量上限为5(self):
        assert rules.MENTOR_CAPACITY == 5

    def test_饱和度(self):
        assert rules.mentor_saturation(0) == 0.0
        assert rules.mentor_saturation(5) == 1.0
        assert rules.mentor_saturation(2) == pytest.approx(0.4)

    def test_容量为0时不除零(self):
        assert rules.mentor_saturation(3, capacity=0) == 1.0

    def test_优先分配给直播间导师(self):
        """直播间导师未满 → 优先它，即便其他导师饱和度更低。"""
        picked = rules.pick_mentor([
            {'id': 'room', 'load': 4, 'is_resource_mentor': True},
            {'id': 'other', 'load': 0, 'is_resource_mentor': False},
        ])
        assert picked['id'] == 'room'

    def test_直播间导师满额则回落到饱和度最低(self):
        """直播间导师已带满 5 人 → 全体按饱和度升序，取最低者。"""
        picked = rules.pick_mentor([
            {'id': 'room', 'load': 5, 'is_resource_mentor': True},
            {'id': 'other', 'load': 1, 'is_resource_mentor': False},
        ])
        assert picked['id'] == 'other'

    def test_多个直播间导师取饱和度最低(self):
        picked = rules.pick_mentor([
            {'id': 'room-a', 'load': 4, 'is_resource_mentor': True},
            {'id': 'room-b', 'load': 1, 'is_resource_mentor': True},
        ])
        assert picked['id'] == 'room-b'

    def test_饱和度并列最低时随机(self):
        """两名导师饱和度相同 → 结果在两人之间随机（不能恒定取同一个）。"""
        import random as _random
        candidates = [
            {'id': 'a', 'load': 1, 'is_resource_mentor': True},
            {'id': 'b', 'load': 1, 'is_resource_mentor': True},
        ]
        picks = {
            rules.pick_mentor(candidates, rng=_random.Random(seed))['id']
            for seed in range(30)
        }
        assert picks == {'a', 'b'}

    def test_候选为空返回None(self):
        assert rules.pick_mentor([]) is None
