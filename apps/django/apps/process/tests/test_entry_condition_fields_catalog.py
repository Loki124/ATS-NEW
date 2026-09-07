"""阶段配置规则组件 — GET /api/v1/expressions/fields 目录端点验证。

数据必须来自 services.py:284-360 (_get_actual_value) 实际解析的字段，
覆盖 CANDIDATE / DEMAND / STAGE_STATUS 三个 source。
"""
from __future__ import annotations

from django.test import TestCase

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
