"""阶段配置规则组件 — GET /api/v1/expressions/fields 目录端点验证。

数据必须来自 services.py:_get_actual_value 实际解析的字段，
覆盖 CANDIDATE / DEMAND / STAGE_STATUS 三个 source。

2026-10-01 起：CANDIDATE 字段改为指标库驱动（apps.metrics.AtomicMetric）。
"""
from __future__ import annotations

from django.test import TestCase
from nanoid import generate as nanoid_generate

from apps.entry_condition.services import LEGACY_CANDIDATE_FIELD_TO_PATH
from apps.metrics.models import AtomicMetric, MetricDataType
from apps.process.views import EntryConditionFieldCatalogView


class EntryConditionFieldsCatalogTest(TestCase):
    def _get_catalog(self):
        resp = EntryConditionFieldCatalogView().get(None)
        self.assertTrue(resp.data['success'])
        return resp.data['data']

    def test_structure_has_sources_and_common_operators(self):
        data = self._get_catalog()
        self.assertIn('sources', data)
        self.assertIn('common_operators', data)
        self.assertIsInstance(data['common_operators'], list)
        self.assertGreater(len(data['common_operators']), 0)

    def test_three_sources_present(self):
        data = self._get_catalog()
        keys = {s['key'] for s in data['sources']}
        self.assertEqual(
            keys, {'DEMAND', 'CANDIDATE', 'STAGE_STATUS'},
            '必须包含 DEMAND / CANDIDATE / STAGE_STATUS 三个 source',
        )

    def test_candidate_fields_aligned_with_services(self):
        data = self._get_catalog()
        candidate = next(s for s in data['sources'] if s['key'] == 'CANDIDATE')
        fields = {f['key'] for f in candidate['fields']}
        self.assertEqual(
            fields,
            {'AGE', 'GENDER', 'HIGHEST_EDU', 'WORK_YEARS', 'CURRENT_CITY', 'EXPECTED_CITY'},
        )

    def test_demand_fields_aligned_with_services(self):
        data = self._get_catalog()
        demand = next(s for s in data['sources'] if s['key'] == 'DEMAND')
        fields = {f['key'] for f in demand['fields']}
        self.assertEqual(
            fields,
            {'HIRING_MANAGER', 'HIRING_MANAGER_SUPER', 'BU_PRESIDENT',
             'SOLID_VP', 'DOTTED_VP', 'DEMAND_LEVEL', 'DEPARTMENT'},
        )

    def test_stage_status_field_uses_stage_list_value_source(self):
        data = self._get_catalog()
        stage = next(s for s in data['sources'] if s['key'] == 'STAGE_STATUS')
        self.assertEqual(len(stage['fields']), 1)
        self.assertEqual(stage['fields'][0]['key'], 'STAGE_NAME')
        self.assertEqual(stage['fields'][0]['value_source'], 'STAGE_LIST')

    def test_every_field_has_operators(self):
        data = self._get_catalog()
        for source in data['sources']:
            for field in source['fields']:
                self.assertIn('operators', field)
                self.assertIsInstance(field['operators'], list)
                self.assertGreater(len(field['operators']), 0)


class EntryConditionFieldsCatalogMetricsDrivenTest(TestCase):
    """指标库驱动的 CANDIDATE 字段目录（2026-10-01 接入）。

    AtomicMetric.name 用作展示 label，data_type 决定 value_source/operators。

    注意：迁移 0009/0010 已 seed 14+ 条同名指标（年龄 / 性别 / 学历 / ...）。本类
    必须用「唯一路径」避免与既有 seed 冲突（AtomicMetric.source_path UNIQUE 约束，
    故把 source_path 标记成测试专用前缀），同时验证「同名迁移 seed 不会覆盖测试字段」。
    """

    def _seed(self, path: str, name: str, dtype: str) -> AtomicMetric:
        return AtomicMetric.objects.create(
            id=nanoid_generate(size=21),
            name=name, source_path=path, data_type=dtype,
            status='enabled',
        )

    def test_candidate_fields_driven_by_atomic_metrics(self):
        # 把 6 条标准字段 source_path/name 都加 tst_ 前缀，避免与既有迁移 seed 冲突。
        self._seed('candidate.tst_age', 'tst_候选人年龄', MetricDataType.NUMBER)
        self._seed('candidate.tst_gender', 'tst_性别枚举', MetricDataType.STRING)
        self._seed('candidate.tst_highest_education', 'tst_学历', MetricDataType.STRING)
        self._seed('candidate.tst_work_years', 'tst_工龄', MetricDataType.NUMBER)
        self._seed('candidate.tst_current_city', 'tst_所在城市', MetricDataType.STRING)
        self._seed('candidate.tst_expected_city', 'tst_期望城市', MetricDataType.STRING)

        from apps.entry_condition.services import LEGACY_CANDIDATE_FIELD_TO_PATH
        original = LEGACY_CANDIDATE_FIELD_TO_PATH.copy()
        try:
            LEGACY_CANDIDATE_FIELD_TO_PATH.update({
                'AGE': 'candidate.tst_age',
                'GENDER': 'candidate.tst_gender',
                'HIGHEST_EDU': 'candidate.tst_highest_education',
                'WORK_YEARS': 'candidate.tst_work_years',
                'CURRENT_CITY': 'candidate.tst_current_city',
                'EXPECTED_CITY': 'candidate.tst_expected_city',
            })

            data = EntryConditionFieldCatalogView().get(None).data['data']
            candidate = next(s for s in data['sources'] if s['key'] == 'CANDIDATE')
            by_key = {f['key']: f for f in candidate['fields']}

            expected_order = list(LEGACY_CANDIDATE_FIELD_TO_PATH.keys())
            actual_order = [f['key'] for f in candidate['fields']]
            self.assertEqual(actual_order, expected_order)

            self.assertEqual(by_key['AGE']['label'], 'tst_候选人年龄')
            self.assertEqual(by_key['AGE']['value_source'], 'NUMBER')
            self.assertEqual(set(by_key['AGE']['operators']),
                             {'GT', 'GTE', 'LT', 'LTE', 'BETWEEN', 'EQ'})

            self.assertEqual(by_key['GENDER']['label'], 'tst_性别枚举')
            self.assertEqual(by_key['GENDER']['value_source'], 'STRING')
            self.assertEqual(set(by_key['GENDER']['operators']),
                             {'EQ', 'NEQ', 'IN', 'NOT_IN'})
        finally:
            LEGACY_CANDIDATE_FIELD_TO_PATH.clear()
            LEGACY_CANDIDATE_FIELD_TO_PATH.update(original)

    def test_candidate_falls_back_when_metrics_empty(self):
        # 指标库为空时：返回硬编码 6 字段（迁移未跑/刚初始化也能正常下拉）。
        # 但本测试运行在已有迁移 seed 的 DB 上，需把临时映射改到「无人 seed 的路径」。
        from apps.entry_condition.services import LEGACY_CANDIDATE_FIELD_TO_PATH
        original = LEGACY_CANDIDATE_FIELD_TO_PATH.copy()
        try:
            for k in LEGACY_CANDIDATE_FIELD_TO_PATH:
                LEGACY_CANDIDATE_FIELD_TO_PATH[k] = f'candidate.tst_fallback_{k.lower()}'

            data = EntryConditionFieldCatalogView().get(None).data['data']
            candidate = next(s for s in data['sources'] if s['key'] == 'CANDIDATE')
            keys = {f['key'] for f in candidate['fields']}
            self.assertEqual(
                keys,
                {'AGE', 'GENDER', 'HIGHEST_EDU', 'WORK_YEARS', 'CURRENT_CITY', 'EXPECTED_CITY'},
            )
        finally:
            LEGACY_CANDIDATE_FIELD_TO_PATH.clear()
            LEGACY_CANDIDATE_FIELD_TO_PATH.update(original)

    def test_candidate_ignores_metrics_outside_legacy_keys(self):
        # 路径不在 LEGACY 映射内的指标不进 catalog（避免污染下拉）
        self._seed('candidate.tst_extra_id', '测试ID', MetricDataType.STRING)
        data = EntryConditionFieldCatalogView().get(None).data['data']
        candidate = next(s for s in data['sources'] if s['key'] == 'CANDIDATE')
        # 验证 'candidate.tst_extra_id' 没让 'TEST_ID' 之类的 key 冒泡
        keys = {f['key'] for f in candidate['fields']}
        # 所有 catalog 字段 key 都来自 LEGACY_CANDIDATE_FIELD_TO_PATH
        self.assertTrue(keys.issubset(set(LEGACY_CANDIDATE_FIELD_TO_PATH.keys())),
                        f'发现非 LEGACY key 冒泡: {keys - set(LEGACY_CANDIDATE_FIELD_TO_PATH.keys())}')
