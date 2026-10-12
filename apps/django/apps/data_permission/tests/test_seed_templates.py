"""内置权限模板 seed 命令单测（幂等性是核心契约）。

幂等策略：按 code upsert，默认不覆盖已存在模板的 groups/params，
避免管理员在 UI 改过模板后被下次 seed 悄悄重置。
"""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.data_permission.models import DataPermTemplate
from apps.data_permission.scope_templates import instantiate, unbound_placeholders


class SeedDataPermTemplatesTestCase(TestCase):
    def _seed(self, *args):
        out = StringIO()
        call_command('seed_data_perm_templates', *args, stdout=out)
        return out.getvalue()

    def test_first_run_creates_builtin_templates(self):
        self._seed()
        self.assertEqual(DataPermTemplate.objects.count(), 2)
        codes = set(DataPermTemplate.objects.values_list('code', flat=True))
        self.assertEqual(codes, {'DPT0001', 'DPT0002'})

    def test_seed_is_idempotent(self):
        self._seed()
        self._seed()
        self._seed()
        self.assertEqual(DataPermTemplate.objects.count(), 2)

    def test_second_run_does_not_reset_admin_edits(self):
        """核心契约：管理员改过的模板，重复 seed 不得被重置。"""
        self._seed()
        tpl = DataPermTemplate.objects.get(code='DPT0001')
        tpl.name = '管理员改过的名字'
        tpl.params = [{'key': 'relation', 'label': 'X', 'required': True, 'default': 'exact'}]
        tpl.save()
        self._seed()
        tpl.refresh_from_db()
        self.assertEqual(tpl.name, '管理员改过的名字')
        self.assertEqual(tpl.params[0]['default'], 'exact')

    def test_reset_flag_overwrites_and_bumps_version(self):
        self._seed()
        tpl = DataPermTemplate.objects.get(code='DPT0001')
        tpl.name = '被改坏的名字'
        tpl.version = 5
        tpl.save()
        self._seed('--reset')
        tpl.refresh_from_db()
        self.assertEqual(tpl.name, '本部门及所辖部门')
        self.assertEqual(tpl.version, 6, '覆盖应视为语义变更并升版本')

    def test_soft_deleted_template_is_restored(self):
        self._seed()
        DataPermTemplate.objects.get(code='DPT0002').soft_delete()
        self.assertEqual(DataPermTemplate.objects.count(), 1)
        self._seed()
        self.assertEqual(DataPermTemplate.objects.count(), 2, '软删的模板应被恢复')

    def test_builtin_template_is_instantiable(self):
        self._seed()
        tpl = DataPermTemplate.objects.get(code='DPT0001')
        groups = instantiate(tpl, {})
        cond = groups[0]['conditions'][0]
        self.assertEqual(cond['relation'], 'contains')
        self.assertEqual(cond['dynamicKey'], 'currentUser.departments')
        self.assertEqual(cond['dimension'], 'dept')

    def test_builtin_templates_have_no_undeclared_placeholders(self):
        self._seed()
        for tpl in DataPermTemplate.objects.all():
            declared = {p['key'] for p in tpl.params}
            self.assertEqual(unbound_placeholders(tpl.groups) - declared, set())

    def test_builtin_templates_only_target_demand(self):
        self._seed()
        for tpl in DataPermTemplate.objects.all():
            self.assertEqual(tpl.module_key, 'demand')
