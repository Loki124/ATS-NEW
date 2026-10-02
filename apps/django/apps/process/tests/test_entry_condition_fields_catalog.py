"""阶段配置规则组件 — GET /api/v1/expressions/fields 目录端点验证。

数据必须来自 services.py:_get_actual_value 实际解析的字段，
覆盖 DEMAND（legacy 7 字段 + demand.* 指标）/ POSITION（position.* 指标）/
CANDIDATE（candidate.* 指标）/ STAGE_STATUS 四个 source。

2026-10-01 第二轮：CANDIDATE 字段完全由指标库（apps.metrics.AtomicMetric，
source_path=candidate.*）驱动，field=source_path、label=指标名、value_type 由 data_type 推导。
"""
from __future__ import annotations

from django.test import TestCase
from nanoid import generate as nanoid_generate

from apps.metrics.models import AtomicMetric, MetricDataType
from apps.process.views import EntryConditionFieldCatalogView


class EntryConditionFieldsCatalogTest(TestCase):
    def _get_catalog(self):
        resp = EntryConditionFieldCatalogView().get(None)
        self.assertTrue(resp.data['success'])
        return resp.data['data']

    def _candidate(self, data):
        return next(s for s in data['sources'] if s['key'] == 'CANDIDATE')

    def test_structure_has_sources_and_common_operators(self):
        data = self._get_catalog()
        self.assertIn('sources', data)
        self.assertIn('common_operators', data)
        self.assertIsInstance(data['common_operators'], list)
        self.assertGreater(len(data['common_operators']), 0)

    def test_four_sources_present(self):
        """2026-10-02 起需求/职位指标接入：DEMAND / POSITION / CANDIDATE / STAGE_STATUS 四 source。"""
        data = self._get_catalog()
        keys = {s['key'] for s in data['sources']}
        self.assertEqual(
            keys, {'DEMAND', 'POSITION', 'CANDIDATE', 'STAGE_STATUS'},
            '必须包含 DEMAND / POSITION / CANDIDATE / STAGE_STATUS 四个 source',
        )

    def test_source_dicts_expose_source_key_for_frontend(self):
        # 前端 ConditionPicker.vue 读 s.source（SPEC-stage-rule-config.md 契约）
        data = self._get_catalog()
        for s in data['sources']:
            self.assertIn('source', s)
            self.assertEqual(s['source'], s['key'])

    def test_candidate_source_is_metric_driven(self):
        """CANDIDATE 源完全由 candidate.* 指标驱动：field=source_path，且带 value_type。"""
        data = self._get_catalog()
        candidate = self._candidate(data)
        # 契约：前端读 f.field
        self.assertTrue(all(f['field'] == f['key'] for f in candidate['fields']))
        self.assertTrue(all(f['field'].startswith('candidate.') for f in candidate['fields']))
        # 指标管理里全部 24 个 candidate.* 指标均应以 source_path 出现（0009/0010/0016 seed）
        expected_all = {
            # 0009 补的 10 + 0001 既有 4（age/gender/birth_date/school_tag，由 0016 补齐）
            'candidate.id', 'candidate.name', 'candidate.age', 'candidate.gender',
            'candidate.birth_date', 'candidate.highest_education', 'candidate.school_tag',
            'candidate.work_years', 'candidate.current_city', 'candidate.expected_city',
            'candidate.current_company', 'candidate.current_position', 'candidate.major_tag',
            'candidate.resume_score',
            # 0010 补的 10
            'candidate.recruit_type', 'candidate.resume_file_url', 'candidate.resume_text',
            'candidate.referral_type', 'candidate.current_state', 'candidate.is_blacklisted',
            'candidate.blacklist_reason', 'candidate.moka_candidate_id',
            'candidate.is_archived', 'candidate.archived_at',
        }
        fields = {f['field'] for f in candidate['fields']}
        self.assertEqual(fields, expected_all, f'目录与指标库不一致，缺: {expected_all - fields}')
        # 每个字段都有 value_type + operators
        for f in candidate['fields']:
            self.assertIn('value_type', f)
            self.assertIsInstance(f['operators'], list)
            self.assertGreater(len(f['operators']), 0)

    def test_candidate_field_value_type_by_data_type(self):
        data = self._get_catalog()
        candidate = self._candidate(data)
        by_field = {f['field']: f for f in candidate['fields']}
        # number → value_type=number，含数值比较运算符
        age = by_field['candidate.age']
        self.assertEqual(age['value_type'], 'number')
        self.assertTrue({'GT', 'GTE', 'LT', 'LTE', 'BETWEEN'}.issubset(set(age['operators'])))
        # date → value_type=date
        self.assertEqual(by_field['candidate.birth_date']['value_type'], 'date')
        # boolean → value_type=boolean，带 是/否 下拉
        bl = by_field['candidate.is_blacklisted']
        self.assertEqual(bl['value_type'], 'boolean')
        self.assertIn('options', bl)
        self.assertEqual({o['value'] for o in bl['options']}, {'true', 'false'})
        # string → value_type=string
        self.assertEqual(by_field['candidate.name']['value_type'], 'string')
        self.assertEqual(by_field['candidate.gender']['value_type'], 'string')

    def test_demand_fields_aligned_with_services(self):
        data = self._get_catalog()
        demand = next(s for s in data['sources'] if s['key'] == 'DEMAND')
        # 契约：前端读 f.field
        self.assertTrue(all(f['field'] == f['key'] for f in demand['fields']))
        fields = {f['field'] for f in demand['fields']}
        # 7 个 legacy 硬编码字段必须仍在（services._get_demand_value 的映射键）
        legacy_fields = {
            'HIRING_MANAGER', 'HIRING_MANAGER_SUPER', 'BU_PRESIDENT',
            'SOLID_VP', 'DOTTED_VP', 'DEMAND_LEVEL', 'DEPARTMENT',
        }
        self.assertTrue(
            legacy_fields.issubset(fields),
            f'legacy 需求字段缺失: {legacy_fields - fields}',
        )
        # 2026-10-02 接入：demand.* 指标（0012 seed）也进入 DEMAND 源
        self.assertIn('demand.headcount', fields)
        self.assertIn('demand.title', fields)

    def test_position_source_is_metric_driven(self):
        """POSITION 源完全由 position.* 指标驱动（0012 seed）。"""
        data = self._get_catalog()
        position = next(s for s in data['sources'] if s['key'] == 'POSITION')
        self.assertTrue(all(f['field'] == f['key'] for f in position['fields']))
        fields = {f['field'] for f in position['fields']}
        self.assertGreater(len(fields), 0, 'POSITION 源不应为空（0012 已 seed position.* 指标）')
        self.assertTrue(all(f.startswith('position.') for f in fields))
        # 数值指标带 value_type（前端据选输入控件）
        by_field = {f['field']: f for f in position['fields']}
        self.assertEqual(by_field['position.headcount']['value_type'], 'number')
        self.assertTrue({'GT', 'GTE', 'LT', 'LTE', 'BETWEEN'}.issubset(
            set(by_field['position.headcount']['operators'])))

    def test_stage_status_field_uses_stage_list_value_source(self):
        data = self._get_catalog()
        stage = next(s for s in data['sources'] if s['key'] == 'STAGE_STATUS')
        self.assertEqual(len(stage['fields']), 1)
        self.assertEqual(stage['fields'][0]['key'], 'STAGE_NAME')
        self.assertEqual(stage['fields'][0]['field'], 'STAGE_NAME')
        self.assertEqual(stage['fields'][0]['value_source'], 'STAGE_LIST')

    def test_every_field_has_operators(self):
        data = self._get_catalog()
        for source in data['sources']:
            for field in source['fields']:
                self.assertIn('operators', field)
                self.assertIsInstance(field['operators'], list)
                self.assertGreater(len(field['operators']), 0)


class EntryConditionFieldsCatalogMetricsDrivenTest(TestCase):
    """指标库驱动的 CANDIDATE 字段目录（2026-10-01 第二轮：全量 candidate.* 指标）。

    CANDIDATE 源列出所有 source_path 以 candidate. 开头、enabled、未软删的 AtomicMetric；
    非 candidate.* 的指标（如 demand.*）不应进入 CANDIDATE 源。
    """

    def _seed(self, path: str, name: str, dtype: str, **extra) -> AtomicMetric:
        return AtomicMetric.objects.create(
            id=nanoid_generate(size=21),
            name=name, source_path=path, data_type=dtype,
            status='enabled', **extra,
        )

    def test_candidate_source_lists_all_candidate_metrics(self):
        # 额外 seed 一条 candidate.* 测试指标（tst_ 前缀避免与迁移 seed 的 source_path 冲突）
        self._seed('candidate.tst_extra_score', 'tst_额外评分', MetricDataType.NUMBER)
        data = EntryConditionFieldCatalogView().get(None).data['data']
        candidate = next(s for s in data['sources'] if s['key'] == 'CANDIDATE')
        fields = {f['field'] for f in candidate['fields']}
        self.assertIn('candidate.tst_extra_score', fields)
        # 全部字段的 field 都是 candidate.* 且带 value_type
        self.assertTrue(all(f.startswith('candidate.') for f in fields))
        self.assertTrue(all(('value_type' in f_def) for f_def in candidate['fields']))

    def test_candidate_source_excludes_non_candidate_metrics(self):
        # demand.* 指标不应出现在 CANDIDATE 源
        self._seed('demand.tst_level', 'tst_需求级别', MetricDataType.STRING)
        data = EntryConditionFieldCatalogView().get(None).data['data']
        candidate = next(s for s in data['sources'] if s['key'] == 'CANDIDATE')
        fields = {f['field'] for f in candidate['fields']}
        self.assertNotIn('demand.tst_level', fields)

    def test_candidate_field_value_type_and_options_from_seed(self):
        # 测试指标：number 应带 value_type=number；enum 应带 options
        self._seed('candidate.tst_enum_field', 'tst_枚举字段', MetricDataType.STRING,
                   is_enum=True, enum_values=['A', 'B', 'C'])
        data = EntryConditionFieldCatalogView().get(None).data['data']
        candidate = next(s for s in data['sources'] if s['key'] == 'CANDIDATE')
        by_field = {f['field']: f for f in candidate['fields']}
        self.assertIn('candidate.tst_enum_field', by_field)
        enum_def = by_field['candidate.tst_enum_field']
        self.assertEqual(enum_def['value_type'], 'enum')
        self.assertEqual({o['value'] for o in enum_def['options']}, {'A', 'B', 'C'})

