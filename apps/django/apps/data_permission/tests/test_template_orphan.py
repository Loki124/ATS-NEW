"""「模板删除即失效」的单测（2026-10-12 决策）。

契约：
  - 软删模板 -> 引用它的条件组被打上 orphaned -> 编译时 fail-closed（看不到数据）
  - restore   -> 标记摘除 -> 规则原样复活（一条命令即可回滚误删）
  - 条件本体不被销毁（快照是管理员的配置内容，必须可逆）
  - 失效组只让自己变空，不连累同模块内其它组（组间 OR 下是 no-op）
  - 未引用该模板的规则完全不受影响
"""
from django.test import TestCase

from apps.data_permission.expr_compiler import compile_scope_q
from apps.data_permission.models import DataPermissionRule, DataPermTemplate, RowScopeType
from apps.data_permission.scope_templates import (
    apply_orphan_flag, build_template_ref, instantiate,
)


class TemplateOrphanTestCase(TestCase):
    def setUp(self):
        from apps.core.models import Department, User
        # 用户必须有负责部门：否则动态条件本身就是 fail-closed 空集，
        # 就无法区分「因 orphaned 失效」与「本来就匹配不到任何数据」。
        self.dept = Department.objects.create(name='智能BG')
        self.user = User.objects.create(username='orphan_actor', department=self.dept)
        self.tpl = DataPermTemplate.objects.create(
            code='TPL_ORPHAN', name='测试用模板', module_key='demand',
            params=[{'key': 'relation', 'label': '包含关系', 'required': True, 'default': 'contains'}],
            groups=[{'expr': '', 'conditions': [
                {'kind': 'relationship', 'dimension': 'dept', 'valueSource': 'dynamic',
                 'dynamicKey': 'currentUser.departments', 'relation': '${relation}'},
            ]}],
        )

    def _template_group(self):
        g = instantiate(self.tpl, {'relation': 'contains'})
        return {
            'expr': '',
            'templateRef': build_template_ref(self.tpl, {'relation': 'contains'}),
            'conditions': g[0]['conditions'],
        }

    def _static_group(self, dept='D9'):
        return {'expr': '', 'conditions': [
            {'dimension': 'dept', 'operator': 'in', 'values': [{'id': dept, 'label': '静态组'}]},
        ]}

    def _make_rule(self, groups, role='HRBP'):
        return DataPermissionRule.objects.create(
            dimension_type='ROLE', dimension_value=role, level='ROW', entity='demand',
            scope_type=RowScopeType.CUSTOM, scope_payload={'expr': '', 'groups': groups},
            created_by=self.user.pk,
        )

    def _reloaded(self, rule):
        rule.refresh_from_db()
        return rule.scope_payload['groups']

    # ---- 打标记 ----
    def test_flag_marks_only_matching_template(self):
        rule = self._make_rule([self._template_group(), self._static_group()])
        n = apply_orphan_flag([rule], ['TPL_ORPHAN'], orphaned=True)
        self.assertEqual(n, 1)
        groups = self._reloaded(rule)
        self.assertTrue(groups[0]['templateRef']['orphaned'])
        self.assertNotIn('templateRef', groups[1])

    def test_flag_is_idempotent(self):
        rule = self._make_rule([self._template_group()])
        apply_orphan_flag([rule], ['TPL_ORPHAN'], orphaned=True)
        n2 = apply_orphan_flag([rule], ['TPL_ORPHAN'], orphaned=True)
        self.assertEqual(n2, 0, '已是目标状态不应重复写')

    def test_flag_ignores_unrelated_codes(self):
        rule = self._make_rule([self._template_group()])
        self.assertEqual(apply_orphan_flag([rule], ['DPT9999'], orphaned=True), 0)
        self.assertFalse(self._reloaded(rule)[0]['templateRef'].get('orphaned'))

    def test_unflag_removes_key_entirely(self):
        rule = self._make_rule([self._template_group()])
        apply_orphan_flag([rule], ['TPL_ORPHAN'], orphaned=True)
        apply_orphan_flag([rule], ['TPL_ORPHAN'], orphaned=False)
        self.assertNotIn('orphaned', self._reloaded(rule)[0]['templateRef'])

    # ---- 编译期 fail-closed ----
    def test_orphaned_group_fails_closed(self):
        rule = self._make_rule([self._template_group()])
        apply_orphan_flag([rule], ['TPL_ORPHAN'], orphaned=True)
        q = compile_scope_q({'expr': '', 'groups': self._reloaded(rule)}, 'demand', user=self.user)
        self.assertEqual(list(q.children[0][1]), [], '失效组必须拒绝全部数据')

    def test_non_orphaned_group_still_works(self):
        rule = self._make_rule([self._template_group()])
        q = compile_scope_q({'expr': '', 'groups': self._reloaded(rule)}, 'demand', user=self.user)
        self.assertNotEqual(list(q.children[0][1]), [], '未失效时不得受影响')

    def test_orphaned_group_does_not_block_sibling_in_or(self):
        """组间 OR：失效组贡献空集(noop)，同模块其它组照常放行。"""
        rule = self._make_rule([self._template_group(), self._static_group('D7')])
        apply_orphan_flag([rule], ['TPL_ORPHAN'], orphaned=True)
        q = compile_scope_q(
            {'expr': '1 or 2', 'groups': self._reloaded(rule)},
            'demand', user=self.user,
        )
        q_str = str(q)
        self.assertIn('D7', q_str, '静态组必须仍然生效')

    # ---- 可逆性 ----
    def test_restore_revives_rule(self):
        rule = self._make_rule([self._template_group()])
        apply_orphan_flag([rule], ['TPL_ORPHAN'], orphaned=True)
        apply_orphan_flag([rule], ['TPL_ORPHAN'], orphaned=False)
        q = compile_scope_q({'expr': '', 'groups': self._reloaded(rule)}, 'demand', user=self.user)
        self.assertNotEqual(list(q.children[0][1]), [], '恢复后规则应复活')

    def test_conditions_body_survives_orphaning(self):
        """条件本体不能被销毁 —— 它是管理员的配置内容，删掉不可逆。"""
        rule = self._make_rule([self._template_group()])
        before = len(self._reloaded(rule)[0]['conditions'])
        apply_orphan_flag([rule], ['TPL_ORPHAN'], orphaned=True)
        after = self._reloaded(rule)[0]
        self.assertEqual(len(after['conditions']), before)
        self.assertEqual(after['conditions'][0]['dynamicKey'], 'currentUser.departments')

    # ---- 隔离性 ----
    def test_other_roles_rules_untouched(self):
        r1 = self._make_rule([self._template_group()], role='HRBP')
        r2 = self._make_rule([self._template_group()], role='HR_SPECIALIST')
        apply_orphan_flag([r1], ['TPL_ORPHAN'], orphaned=True)
        self.assertTrue(self._reloaded(r1)[0]['templateRef'].get('orphaned'))
        self.assertFalse(self._reloaded(r2)[0]['templateRef'].get('orphaned'))
