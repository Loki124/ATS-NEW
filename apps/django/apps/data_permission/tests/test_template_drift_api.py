"""读接口透出模板版本漂移（templateDrifts）的单测。

契约：
  - 无任何 templateRef 时不产生模板表查询，且 templateDrifts 为空
  - 模板升版本 -> outdated（含 snapshot/latest 版本号）
  - 模板软删    -> missing（引用仍按快照执行，不报错）
  - 只有实际引用的模板才进 lookup（避免全表扫）
"""
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.data_permission.models import DataPermissionRule, DataPermTemplate, RowScopeType
from apps.data_permission.role_scope_api import build_modules_response
from apps.data_permission.scope_templates import build_template_ref, instantiate


def manual_group():
    """手工条件组（无 templateRef），用于验证漂移只定位到模板组。"""
    return {'expr': '', 'conditions': [
        {'dimension': 'dept', 'operator': 'in', 'values': [{'id': 'D9', 'label': '手工组'}]},
    ]}


class TemplateDriftApiTestCase(TestCase):
    def setUp(self):
        from apps.core.models import User
        from apps.core.models_permission_v2 import RoleV2

        # 2026-10-21 卡 B5：改 get_or_create —— `recruit-HRBP` 是**已提交**的系统角色
        # （apps/campus_rotation 的 post_migrate 回调 seed_campus_roles 预置），
        # 裸 create 会撞 roles.uk_system_role。本用例只用到 role_code，不关心其它字段。
        self.role, _created = RoleV2.objects.get_or_create(
            system_code='recruit', role_code='HRBP',
            defaults={'role_name': 'HRBP 角色'},
        )
        self.tpl = DataPermTemplate.objects.create(
            code='TPL_DRIFT', name='测试用模板', module_key='demand',
            params=[{'key': 'relation', 'label': '包含关系', 'required': True, 'default': 'contains'}],
            groups=[{'expr': '', 'conditions': [
                {'kind': 'relationship', 'dimension': 'dept', 'valueSource': 'dynamic',
                 'dynamicKey': 'currentUser.departments', 'relation': '${relation}'},
            ]}],
        )
        self.user = User.objects.create(username='admin_api')

    def _save_rule(self, groups):
        DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value=self.role.role_code, level='ROW',
            entity='demand', scope_type=RowScopeType.CUSTOM,
            scope_payload={'expr': '', 'groups': groups},
            created_by=self.user.pk,
        )

    def _group_from_template(self):
        groups = instantiate(self.tpl, {'relation': 'contains'})
        return {
            'expr': '',
            'templateRef': build_template_ref(self.tpl, {'relation': 'contains'}),
            'conditions': groups[0]['conditions'],
        }

    def _drifts_of_demand(self):
        resp = build_modules_response(self.role)
        mod = next(m for m in resp['modules'] if m['moduleKey'] == 'demand')
        return mod['templateDrifts']

    # ---- 无引用 ----
    def test_no_template_ref_yields_empty_drifts(self):
        self._save_rule([{'expr': '', 'conditions': [
            {'dimension': 'dept', 'operator': 'in', 'values': [{'id': 'D1', 'label': 'X'}]},
        ]}])
        self.assertEqual(self._drifts_of_demand(), [])

    def test_no_ref_means_no_template_query(self):
        with CaptureQueriesContext(connection) as ctx:
            resp = build_modules_response(self.role)
        sql = ' '.join(q['sql'].lower() for q in ctx.captured_queries)
        self.assertNotIn('data_perm_templates', sql, '无引用时不应查模板表')
        for m in resp['modules']:
            self.assertEqual(m['templateDrifts'], [])

    # ---- 版本落后 ----
    def test_outdated_reported_after_version_bump(self):
        self._save_rule([self._group_from_template()])
        self.assertEqual(self._drifts_of_demand(), [], '版本一致时不该报漂移')

        self.tpl.version = 2
        self.tpl.save()
        drifts = self._drifts_of_demand()
        self.assertEqual(len(drifts), 1)
        self.assertEqual(drifts[0]['state'], 'outdated')
        self.assertEqual(drifts[0]['snapshotVersion'], 1)
        self.assertEqual(drifts[0]['latestVersion'], 2)
        self.assertEqual(drifts[0]['templateCode'], 'TPL_DRIFT')

    # ---- 模板软删 ----
    def test_missing_reported_after_soft_delete(self):
        self._save_rule([self._group_from_template()])
        self.tpl.soft_delete()
        drifts = self._drifts_of_demand()
        self.assertEqual(len(drifts), 1)
        self.assertEqual(drifts[0]['state'], 'missing')
        self.assertEqual(drifts[0]['templateCode'], 'TPL_DRIFT')

    def test_soft_deleted_template_still_found_via_all_objects(self):
        """软删不应退化成「查不到就当没引用」，必须显式报 missing。"""
        self._save_rule([self._group_from_template()])
        self.tpl.soft_delete()
        drifts = self._drifts_of_demand()
        self.assertEqual(drifts[0]['state'], 'missing')

    # ---- 多模块 / 多组 ----
    def test_drift_is_scoped_to_the_right_module(self):
        self._save_rule([self._group_from_template()])
        self.tpl.version = 5
        self.tpl.save()
        resp = build_modules_response(self.role)
        by_key = {m['moduleKey']: m['templateDrifts'] for m in resp['modules']}
        self.assertEqual(len(by_key['demand']), 1)
        for mk in ('process', 'position', 'candidate', 'talent'):
            self.assertEqual(by_key[mk], [], '{} 不该有漂移'.format(mk))

    def test_multiple_drifted_groups_all_reported(self):
        self._save_rule([self._group_from_template(), self._group_from_template()])
        self.tpl.version = 9
        self.tpl.save()
        drifts = self._drifts_of_demand()
        self.assertEqual(len(drifts), 2)

    def test_drift_carries_group_index_for_targeted_upgrade(self):
        """漂移必须带 groupIndex —— 前端据此只替换该组，不动同模块其它手工条件。"""
        manual = {'expr': '', 'conditions': [
            {'dimension': 'dept', 'operator': 'in', 'values': [{'id': 'D9', 'label': '手工组'}]},
        ]}
        self._save_rule([manual, self._group_from_template()])
        self.tpl.version = 4
        self.tpl.save()
        drifts = self._drifts_of_demand()
        self.assertEqual(len(drifts), 1)
        self.assertEqual(drifts[0]['groupIndex'], 1, '应指向模板组而非手工组')

    def test_group_index_tracks_position_of_manual_groups(self):
        self._save_rule([self._group_from_template(), manual_group(), self._group_from_template()])
        self.tpl.version = 7
        self.tpl.save()
        drifts = self._drifts_of_demand()
        self.assertEqual(sorted(d['groupIndex'] for d in drifts), [0, 2])

    def test_mode_all_modules_have_empty_drift_list(self):
        resp = build_modules_response(self.role)
        self.assertTrue(all('templateDrifts' in m for m in resp['modules']))
        # 模块清单取后端唯一真源（2026-10-21 S5-32 新增校招生管理卡后已非 5 个）；
        # 写死数字会让每次加模块都要改测试，且漏改时报的是无关的「总数不对」。
        from apps.data_permission.field_map import MODULE_ORDER
        self.assertEqual(len(resp['modules']), len(MODULE_ORDER))
        self.assertEqual({m['moduleKey'] for m in resp['modules']}, set(MODULE_ORDER))
