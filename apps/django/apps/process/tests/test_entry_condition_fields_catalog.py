"""阶段配置规则组件 — GET /api/v1/expressions/fields 目录端点验证。

口径（2026-10 收口）：目录字段不再暴露 source_path，而是以**指标模板 id** 作为
field / key —— ConditionItem.field 直接存模板 id，与 MetricEngine 的取值入口一致
（见 process.views._build_metric_template_catalog 的注释）。

因此本文件的断言全部按「field = 模板 id」组织：
  1. field 可反查回模板，模板的底层指标路径（原子 source_path / 派生 base_path）
     决定它出现在哪个 source（CANDIDATE / DEMAND / POSITION）
  2. value_type 由底层指标的 data_type 推导；**枚举型由模板的 param_enums 决定**
     （param_enums 非空 → value_type='enum' 并渲染 options）
  3. 目录只列 enabled、未软删的**模板**；只建指标不建模板不会进目录（用例显式覆盖）

用例自带 seed（指标 + 配套模板），不依赖迁移 seed 的具体路径集合——迁移 seed 会随
迭代增减，硬编码一份路径清单只会让测试在别人加指标时误报。
"""
from __future__ import annotations

from django.test import TestCase
from nanoid import generate as nanoid_generate

from apps.metrics.models import AtomicMetric, MetricDataType, MetricTemplate
from apps.process.views import EntryConditionFieldCatalogView

# 底层指标 data_type → 目录 value_type（非枚举情形）
DTYPE_TO_VTYPE = {
    MetricDataType.NUMBER: 'number',
    MetricDataType.STRING: 'string',
    MetricDataType.DATE: 'date',
    MetricDataType.BOOLEAN: 'boolean',
}


class CatalogTestBase(TestCase):
    """目录查询 + seed 辅助。"""

    def _get_catalog(self):
        resp = EntryConditionFieldCatalogView().get(None)
        self.assertTrue(resp.data['success'])
        return resp.data['data']

    def _source(self, key):
        return next(s for s in self._get_catalog()['sources'] if s['key'] == key)

    def _seed(self, path: str, name: str, dtype: str, *, operators=None,
              param_enums=None, with_template=True, **extra):
        """建原子指标，并按需配套一个指标模板。

        目录只读 MetricTemplate，所以「进目录」这件事必须指标 + 模板成对；
        with_template=False 用于验证「只有指标没有模板不会进目录」。
        """
        metric = AtomicMetric.objects.create(
            id=nanoid_generate(size=21),
            name=name, source_path=path, data_type=dtype,
            status='enabled', **extra,
        )
        if not with_template:
            return metric, None
        tpl = MetricTemplate.objects.create(
            id=nanoid_generate(size=21),
            name=name, atomic_metric=metric,
            operators=operators or ['IS_EMPTY'],
            param_enums=param_enums if param_enums is not None else [],
            value_domain={'segments': []},
            status='enabled',
        )
        return metric, tpl

    def _tpl_of(self, field_id: str) -> MetricTemplate:
        """目录 field 即模板 id —— 反查模板是校验目录语义的前提。"""
        return MetricTemplate.objects.get(pk=field_id)


class EntryConditionFieldsCatalogTest(CatalogTestBase):
    def test_structure_has_sources_and_common_operators(self):
        data = self._get_catalog()
        self.assertIn('sources', data)
        self.assertIn('common_operators', data)
        self.assertIsInstance(data['common_operators'], list)
        self.assertGreater(len(data['common_operators']), 0)

    def test_five_sources_present(self):
        """目录含 DEMAND / POSITION / CANDIDATE / METRIC / STAGE_STATUS 五个 source。"""
        keys = {s['key'] for s in self._get_catalog()['sources']}
        self.assertEqual(
            keys, {'DEMAND', 'POSITION', 'CANDIDATE', 'METRIC', 'STAGE_STATUS'},
            '必须包含 DEMAND / POSITION / CANDIDATE / METRIC / STAGE_STATUS 五个 source',
        )

    def test_metric_source_present(self):
        metric = next((s for s in self._get_catalog()['sources'] if s['key'] == 'METRIC'), None)
        self.assertIsNotNone(metric, 'catalog 缺少 METRIC 源')
        self.assertEqual(metric['condition_type'], 'METRIC')
        self.assertEqual(metric['source'], 'METRIC')

    def test_source_dicts_expose_source_key_for_frontend(self):
        # 前端 ConditionPicker.vue 读 s.source（SPEC-stage-rule-config.md 契约）
        for s in self._get_catalog()['sources']:
            self.assertIn('source', s)
            self.assertEqual(s['source'], s['key'])

    def test_candidate_source_is_metric_driven(self):
        """CANDIDATE 源由 candidate.* 指标模板驱动，且每项都带 value_type / operators。"""
        _, tpl = self._seed('candidate.t_cat_probe', 't_候选人探针', MetricDataType.NUMBER)
        fields = self._source('CANDIDATE')['fields']

        self.assertTrue(all(f['field'] == f['key'] for f in fields), 'field 必须等于 key')
        self.assertIn(str(tpl.id), {f['field'] for f in fields}, '新建的 candidate.* 模板应出现在目录')

        for f in fields:
            t = self._tpl_of(f['field'])
            self.assertTrue(
                t.metric_path.startswith('candidate.'),
                f'{f["label"]} 底层路径应为 candidate.*，实际 {t.metric_path}',
            )
            self.assertIn('value_type', f)
            self.assertIsInstance(f['operators'], list)
            self.assertGreater(len(f['operators']), 0)

    def test_candidate_field_value_type_by_data_type(self):
        """value_type 由底层指标的 data_type 推导；枚举型由 param_enums 决定并给 options。"""
        _, num_tpl = self._seed(
            'candidate.t_vt_number', 't_数值探针', MetricDataType.NUMBER,
            operators=['IS_EMPTY', 'GT', 'GTE', 'LT', 'LTE', 'BETWEEN'],
        )
        _, enum_tpl = self._seed(
            'candidate.t_vt_enum', 't_枚举探针', MetricDataType.STRING,
            is_enum=True, param_enums=['A', 'B', 'C'],
        )
        by_field = {f['field']: f for f in self._source('CANDIDATE')['fields']}

        num_def = by_field[str(num_tpl.id)]
        self.assertEqual(num_def['value_type'], 'number')
        self.assertTrue({'GT', 'GTE', 'LT', 'LTE', 'BETWEEN'}.issubset(set(num_def['operators'])))

        # param_enums 非空 → 枚举型，options 来自 param_enums（规则配置下拉的唯一来源）
        enum_def = by_field[str(enum_tpl.id)]
        self.assertEqual(enum_def['value_type'], 'enum')
        self.assertEqual({o['value'] for o in enum_def['options']}, {'A', 'B', 'C'})

        # 其余项：目录实现的枚举判定依据是 **param_enums 是否非空**（与 is_enum 标志无关，
        # 见 _build_metric_template_catalog），故按此口径逐项校验推导结果。
        for f in by_field.values():
            if f['field'] == str(enum_tpl.id):
                continue
            t = self._tpl_of(f['field'])
            metric = t.atomic_metric or t.derived_metric
            if t.param_enums:
                self.assertEqual(f['value_type'], 'enum', f'{f["label"]} 有 param_enums 应为 enum')
                self.assertTrue(f.get('options'), f'{f["label"]} 为 enum 时必须给 options')
                continue
            self.assertEqual(
                f['value_type'], DTYPE_TO_VTYPE[metric.data_type], f'{f["label"]} value_type 推导不符',
            )

    def test_field_without_template_does_not_appear(self):
        """只建指标、不建模板 → 不进目录（目录的唯一数据源是 MetricTemplate）。"""
        metric, tpl = self._seed(
            'candidate.t_no_tpl', 't_无模板探针', MetricDataType.NUMBER, with_template=False,
        )
        self.assertIsNone(tpl)
        self.assertNotIn(str(metric.id), {f['field'] for f in self._source('CANDIDATE')['fields']})

    def test_demand_fields_aligned_with_services(self):
        """DEMAND 源 = 7 个 legacy 硬编码字段 + demand.* 指标模板。"""
        _, d_tpl = self._seed('demand.t_demand_probe', 't_需求探针', MetricDataType.NUMBER)
        demand = self._source('DEMAND')
        self.assertTrue(all(f['field'] == f['key'] for f in demand['fields']))

        fields = {f['field'] for f in demand['fields']}
        # 7 个 legacy 硬编码字段必须仍在（services._get_demand_value 的映射键）
        legacy_fields = {
            'HIRING_MANAGER', 'HIRING_MANAGER_SUPER', 'BU_PRESIDENT',
            'SOLID_VP', 'DOTTED_VP', 'DEMAND_LEVEL', 'DEPARTMENT',
        }
        self.assertTrue(
            legacy_fields.issubset(fields), f'legacy 需求字段缺失: {legacy_fields - fields}',
        )
        self.assertIn(str(d_tpl.id), fields, 'demand.* 模板应进入 DEMAND 源')

    def test_position_source_is_metric_driven(self):
        """POSITION 源由 position.* 指标模板驱动，数值项带 value_type 与比较运算符。"""
        _, p_tpl = self._seed(
            'position.t_pos_probe', 't_职位探针', MetricDataType.NUMBER,
            operators=['IS_EMPTY', 'GT', 'GTE', 'EQ', 'LT', 'LTE', 'BETWEEN'],
        )
        position = self._source('POSITION')
        fields = {f['field'] for f in position['fields']}
        self.assertGreater(len(fields), 0, 'POSITION 源不应为空')
        self.assertIn(str(p_tpl.id), fields)

        for f in position['fields']:
            t = self._tpl_of(f['field'])
            self.assertTrue(
                t.metric_path.startswith('position.'),
                f'{f["label"]} 底层路径应为 position.*，实际 {t.metric_path}',
            )

        probe = next(f for f in position['fields'] if f['field'] == str(p_tpl.id))
        self.assertEqual(probe['value_type'], 'number')
        self.assertTrue({'GT', 'GTE', 'LT', 'LTE', 'BETWEEN'}.issubset(set(probe['operators'])))

    def test_stage_status_field_uses_stage_list_value_source(self):
        stage = self._source('STAGE_STATUS')
        self.assertEqual(len(stage['fields']), 1)
        self.assertEqual(stage['fields'][0]['key'], 'STAGE_NAME')
        self.assertEqual(stage['fields'][0]['field'], 'STAGE_NAME')
        self.assertEqual(stage['fields'][0]['value_source'], 'STAGE_LIST')

    def test_every_field_has_operators(self):
        for source in self._get_catalog()['sources']:
            for field in source['fields']:
                self.assertIn('operators', field)
                self.assertIsInstance(field['operators'], list)
                self.assertGreater(len(field['operators']), 0)


class EntryConditionFieldsCatalogMetricsDrivenTest(CatalogTestBase):
    """指标库驱动的 CANDIDATE 字段目录：按底层路径前缀分流到不同 source。"""

    def test_candidate_source_lists_metrics_with_template(self):
        _, tpl = self._seed(
            'candidate.tst_extra_score', 'tst_额外评分', MetricDataType.NUMBER,
            operators=['IS_EMPTY', 'GT'],
        )
        candidate = self._source('CANDIDATE')
        self.assertIn(
            str(tpl.id), {f['field'] for f in candidate['fields']},
            '配了模板的 candidate.* 指标应出现在 CANDIDATE 源',
        )
        self.assertTrue(all('value_type' in f for f in candidate['fields']))

    def test_candidate_source_excludes_non_candidate_metrics(self):
        _, d_tpl = self._seed('demand.tst_level', 'tst_需求级别', MetricDataType.STRING)
        self.assertNotIn(
            str(d_tpl.id), {f['field'] for f in self._source('CANDIDATE')['fields']},
            'demand.* 模板不应出现在 CANDIDATE 源',
        )
        # 但它应出现在自己的 DEMAND 源里（证明是「按前缀分流」而非被丢弃）
        self.assertIn(str(d_tpl.id), {f['field'] for f in self._source('DEMAND')['fields']})

    def test_disabled_template_is_excluded(self):
        """目录只列 enabled 的模板。"""
        _, tpl = self._seed('candidate.tst_disabled', 'tst_停用指标', MetricDataType.NUMBER)
        tpl.status = 'disabled'
        tpl.save(update_fields=['status'])
        self.assertNotIn(str(tpl.id), {f['field'] for f in self._source('CANDIDATE')['fields']})