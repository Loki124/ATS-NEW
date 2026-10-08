"""EntryCondition ↔ Metrics 接入回归测试（2026-10-01 接入）。

覆盖：
    - EntryConditionEvaluator._get_candidate_value 优先走 AtomicMetric + 快照 + 解析器
    - 指标缺失时回退到 legacy getattr
    - age 回填：birth_date 存在时主表 age 为空也能拿到
"""
from __future__ import annotations

from datetime import date, timedelta

from django.test import TestCase
from nanoid import generate as nanoid_generate

from apps.entry_condition.services import (
    LEGACY_CANDIDATE_FIELD_TO_PATH,
    EntryConditionEvaluator,
)
from apps.metrics.models import AtomicMetric, MetricDataType


def _new_id():
    return nanoid_generate(size=21)


class CandidateValueMetricsDrivenTest(TestCase):
    """_get_candidate_value 走指标库 + 字段解析器。

    _get_candidate_value 只读 self.candidate，self.link 在该路径下未被使用，
    因此可直接挂一个最简单的满足构造签名的 stub，避免 ProcessStageLink 的 FK 约束。
    """

    def _make_candidate(self, **fields):
        from apps.candidate.models import Candidate
        return Candidate.objects.create(id=_new_id(), **fields)

    def _stub_link(self, cand):
        # stub：仅满足构造签名，方法 _get_candidate_value 不触发任何属性
        class _StubLink:
            pass
        return _StubLink()

    def test_age_resolved_via_metrics_with_birth_date_fallback(self):
        """主表 age 为空 + 有 birth_date：走指标解析应拿到回填的年龄。"""
        cand = self._make_candidate(name='张三', birth_date=date(1990, 6, 15))
        AtomicMetric.objects.create(
            id=_new_id(), name='tst_age_by_birthdate', source_path='candidate.age',
            data_type=MetricDataType.NUMBER, status='enabled',
        )
        evaluator = EntryConditionEvaluator(self._stub_link(cand), cand)
        # 新目录直接以 source_path 作为 field
        age = evaluator._get_candidate_value('candidate.age')
        # 期望按完整周岁算（2026-10-01 算 36 岁）
        expected_age = (date(2026, 10, 1) - date(1990, 6, 15)).days // 365
        self.assertEqual(age, expected_age)

    def test_age_resolved_via_metrics_when_age_field_populated(self):
        """主表 age 直接有值：解析结果与字段一致（不回填主表）。"""
        cand = self._make_candidate(name='李四', age=40, birth_date=date(1980, 1, 1))
        AtomicMetric.objects.create(
            id=_new_id(), name='tst_age_field_set', source_path='candidate.age',
            data_type=MetricDataType.NUMBER, status='enabled',
        )
        evaluator = EntryConditionEvaluator(self._stub_link(cand), cand)
        self.assertEqual(evaluator._get_candidate_value('candidate.age'), 40)

    def test_legacy_key_still_resolves_backward_compat(self):
        """存量 legacy 键（AGE）仍能被反向映射解析（兼容迁移前数据）。"""
        cand = self._make_candidate(name='张三', birth_date=date(1990, 6, 15))
        AtomicMetric.objects.create(
            id=_new_id(), name='tst_age_by_birthdate', source_path='candidate.age',
            data_type=MetricDataType.NUMBER, status='enabled',
        )
        evaluator = EntryConditionEvaluator(self._stub_link(cand), cand)
        expected_age = (date(2026, 10, 1) - date(1990, 6, 15)).days // 365
        # 旧写法 field='AGE' 仍应解析（反向映射）
        self.assertEqual(evaluator._get_candidate_value('AGE'), expected_age)

    def test_extra_candidate_metric_resolves_when_seeded(self):
        """0010 类扩展候选指标（如 current_company）有 seed 即能真实求值。"""
        cand = self._make_candidate(name='钱七', current_company='腾讯')
        AtomicMetric.objects.create(
            id=_new_id(), name='tst_current_company', source_path='candidate.current_company',
            data_type=MetricDataType.STRING, status='enabled',
        )
        evaluator = EntryConditionEvaluator(self._stub_link(cand), cand)
        self.assertEqual(evaluator._get_candidate_value('candidate.current_company'), '腾讯')

    def test_falls_back_to_legacy_when_metric_missing(self):
        """指标未定义：legacy 键回退到 _LEGACY_CANDIDATE_FALLBACK（直接 getattr）。"""
        from apps.entry_condition.services import LEGACY_CANDIDATE_FIELD_TO_PATH
        original = LEGACY_CANDIDATE_FIELD_TO_PATH.copy()
        try:
            LEGACY_CANDIDATE_FIELD_TO_PATH['GENDER'] = 'candidate.tst_nometic_gender'
            LEGACY_CANDIDATE_FIELD_TO_PATH['HIGHEST_EDU'] = 'candidate.tst_nometic_edu'

            cand = self._make_candidate(name='王五', gender='male', highest_education='本科')
            evaluator = EntryConditionEvaluator(self._stub_link(cand), cand)
            self.assertEqual(evaluator._get_candidate_value('GENDER'), 'male')
            self.assertEqual(evaluator._get_candidate_value('HIGHEST_EDU'), '本科')
        finally:
            LEGACY_CANDIDATE_FIELD_TO_PATH.clear()
            LEGACY_CANDIDATE_FIELD_TO_PATH.update(original)

    def test_returns_none_when_legacy_field_missing(self):
        """字段完全没值（含 fallback）：返回 None（不抛异常）。"""
        from apps.entry_condition.services import LEGACY_CANDIDATE_FIELD_TO_PATH
        original = LEGACY_CANDIDATE_FIELD_TO_PATH.copy()
        try:
            for k in LEGACY_CANDIDATE_FIELD_TO_PATH:
                LEGACY_CANDIDATE_FIELD_TO_PATH[k] = f'candidate.tst_void_{k.lower()}'
            cand = self._make_candidate(name='赵六')
            evaluator = EntryConditionEvaluator(self._stub_link(cand), cand)
            self.assertIsNone(evaluator._get_candidate_value('AGE'))
            self.assertIsNone(evaluator._get_candidate_value('WORK_YEARS'))
            # 新写法：未 seed 的 source_path 也返回 None（不抛异常）
            self.assertIsNone(evaluator._get_candidate_value('candidate.tst_void_age'))
        finally:
            LEGACY_CANDIDATE_FIELD_TO_PATH.clear()
            LEGACY_CANDIDATE_FIELD_TO_PATH.update(original)

    def test_legacy_field_map_covers_six_keys(self):
        """legacy 映射覆盖 6 个候选字段键，且全部指向 candidate.*。"""
        expected_keys = {'AGE', 'GENDER', 'HIGHEST_EDU',
                         'WORK_YEARS', 'CURRENT_CITY', 'EXPECTED_CITY'}
        self.assertEqual(set(LEGACY_CANDIDATE_FIELD_TO_PATH.keys()), expected_keys)
        for path in LEGACY_CANDIDATE_FIELD_TO_PATH.values():
            self.assertTrue(path.startswith('candidate.'), path)


class SnapshotAgeFallbackTest(TestCase):
    """build_candidate_snapshot 的 age 回填逻辑（2026-10-01）。"""

    def test_age_filled_when_main_field_blank(self):
        from apps.candidate.models import Candidate
        from apps.metrics.services.candidate_snapshot import build_candidate_snapshot
        cand = Candidate.objects.create(id=_new_id(), name='测试', birth_date=date(1990, 6, 15))
        snap = build_candidate_snapshot(cand.id)
        self.assertEqual(
            snap['candidate']['age'],
            (date(2026, 10, 1) - date(1990, 6, 15)).days // 365,
        )

    def test_age_preserved_when_main_field_populated(self):
        from apps.candidate.models import Candidate
        from apps.metrics.services.candidate_snapshot import build_candidate_snapshot
        cand = Candidate.objects.create(
            id=_new_id(), name='测试', age=42, birth_date=date(1990, 6, 15),
        )
        snap = build_candidate_snapshot(cand.id)
        # 主表值不为空时不覆盖（与原语义一致）
        self.assertEqual(snap['candidate']['age'], 42)

    def test_age_unchanged_when_birth_date_missing(self):
        from apps.candidate.models import Candidate
        from apps.metrics.services.candidate_snapshot import build_candidate_snapshot
        cand = Candidate.objects.create(id=_new_id(), name='测试')
        snap = build_candidate_snapshot(cand.id)
        # 主表 age 为 None，birth_date 也无 → 维持 None
        self.assertIsNone(snap['candidate']['age'])


class DemandPositionMetricValueTest(TestCase):
    """demand.* / position.* 对象路径指标接入进入条件（2026-10-02）。

    - ConditionFieldType.DEMAND + field='demand.xxx' → 需求快照 + 指标解析器
    - ConditionFieldType.POSITION + field='position.xxx' → 职位快照 + 指标解析器
    - DEMAND 源 legacy 硬编码字段（HIRING_MANAGER 等）行为不变
    - 无 context（无 demand/position 实体）→ None，不抛异常
    """

    def _stub_link(self):
        class _StubLink:
            pass
        return _StubLink()

    def _make_item(self, condition_type: str, field: str):
        from apps.entry_condition.models import ConditionItem
        return ConditionItem(
            id=_new_id(), item_seq=1,
            condition_type=condition_type, field=field,
            operator='EQ', value=None,
        )

    def _make_demand(self):
        from django.contrib.auth import get_user_model

        from apps.core.models import Department
        from apps.demand.models import Demand
        from apps.process.models import RecruitmentProcess
        user = get_user_model().objects.create_user(
            username=f'tst_hr_{_new_id()[:8]}', password='Test@1234')
        dept = Department.objects.create(id=_new_id(), name='tst_部门', code=_new_id()[:10])
        process = RecruitmentProcess.objects.create(
            code=_new_id()[:12], name='tst_流程', current_version='V1.0',
            version_seq=1, is_latest=True, status='ENABLED',
        )
        return Demand.objects.create(
            id=_new_id(), code=f'TST-{_new_id()[:8]}', title='tst_测试需求',
            department=dept, requested_by=user, hr=user,
            process=process, headcount=3,
        )

    def _make_position(self, demand=None):
        from django.contrib.auth import get_user_model

        from apps.core.models import Department
        from apps.position.models import Position
        from apps.process.models import RecruitmentProcess
        user = get_user_model().objects.create_user(
            username=f'tst_mgr_{_new_id()[:8]}', password='Test@1234')
        dept = Department.objects.create(id=_new_id(), name='tst_部门', code=_new_id()[:10])
        process = RecruitmentProcess.objects.create(
            code=_new_id()[:12], name='tst_流程', current_version='V1.0',
            version_seq=1, is_latest=True, status='ENABLED',
        )
        return Position.objects.create(
            id=_new_id(), code=f'TST-{_new_id()[:8]}', title='tst_测试职位',
            department=dept, hiring_manager=user, owner=user,
            process=process, headcount=5, demand=demand,
        )

    def test_demand_metric_resolves_via_snapshot(self):
        demand = self._make_demand()
        evaluator = EntryConditionEvaluator(
            self._stub_link(), None, context={'demand': demand},
        )
        item = self._make_item('DEMAND', 'demand.headcount')
        self.assertEqual(evaluator._get_actual_value(item), 3)

    def test_position_metric_resolves_via_snapshot(self):
        position = self._make_position()
        evaluator = EntryConditionEvaluator(
            self._stub_link(), None, context={'position': position},
        )
        item = self._make_item('POSITION', 'position.headcount')
        self.assertEqual(evaluator._get_actual_value(item), 5)

    def test_demand_type_accepts_position_path(self):
        """DEMAND 源下混选 position.* 字段（需求/职位一一关联场景）也能解析。"""
        demand = self._make_demand()
        position = self._make_position(demand=demand)
        evaluator = EntryConditionEvaluator(
            self._stub_link(), None, context={'demand': demand, 'position': position},
        )
        item = self._make_item('DEMAND', 'position.headcount')
        self.assertEqual(evaluator._get_actual_value(item), 5)

    def test_no_context_returns_none(self):
        """无 demand/position 上下文：返回 None，不抛异常。"""
        evaluator = EntryConditionEvaluator(self._stub_link(), None)
        self.assertIsNone(evaluator._get_actual_value(self._make_item('DEMAND', 'demand.headcount')))
        self.assertIsNone(evaluator._get_actual_value(self._make_item('POSITION', 'position.headcount')))