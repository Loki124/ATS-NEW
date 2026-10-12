"""数据权限模板：实例化 / 参数绑定 / 版本漂移 单测。

锁住三条关键性质（详见 scope_templates 模块说明）：
  1. 绑定结果必须通过通用校验（模板也要被校验，不能因「来自模板」而豁免）；
  2. 快照语义：模板改版后，已实例化的规则内容**不变**（无语义漂移）；
  3. 模板软删后，引用方仍按快照正常执行。
"""
from django.test import TestCase

from apps.data_permission.expr_compiler import compile_scope_q
from apps.data_permission.models import DataPermTemplate
from apps.data_permission.scope_templates import (
    TemplateBindError,
    build_template_ref,
    drift_of,
    instantiate,
    summarize_drift,
    unbound_placeholders,
)

# 与内置模板 DPT0001 等价：部门包含规则，relation 参数化
DEPT_CONTAINS_TEMPLATE = {
    'module_key': 'demand',
    'params': [
        {
            'key': 'relation', 'label': '包含关系', 'valueType': 'text',
            'required': True, 'default': 'contains',
            'enum': ['exact', 'in_subtree', 'contains', 'overlap'],
        }
    ],
    'groups': [
        {
            'expr': '',
            'conditions': [
                {
                    'kind': 'relationship',
                    'dimension': 'dept',
                    'valueSource': 'dynamic',
                    'dynamicKey': 'currentUser.departments',
                    'relation': '${relation}',
                }
            ],
        }
    ],
}


def _mk_template(name='本部门及所辖部门', **over):
    payload = {**DEPT_CONTAINS_TEMPLATE, **over}
    return DataPermTemplate.objects.create(name=name, **payload)


class TemplateInstantiateTestCase(TestCase):
    def setUp(self):
        self.tpl = _mk_template()

    # ---- 编号自动生成 / 软删 ----
    def test_code_auto_assigned_dpt_format(self):
        self.assertRegex(self.tpl.code, r'^DPT\d{4}$')

    def test_code_not_reused_after_soft_delete(self):
        _mk_template(name='模板B')
        _mk_template(name='模板C')
        _mk_template(name='模板D').soft_delete()
        new = _mk_template(name='模板E')
        nums = [int(t.code[3:]) for t in DataPermTemplate.all_objects.all()
                if t.code.startswith('DPT')]
        self.assertEqual(len(nums), len(set(nums)), '编号不可重复')
        # 新编号必须大于本次运行中已占用的最大序号（含软删占用的）
        others = [int(t.code[3:]) for t in DataPermTemplate.all_objects.all()
                  if t.code.startswith('DPT') and t.pk != new.pk]
        self.assertGreater(int(new.code[3:]), max(others))

    def test_soft_deleted_hidden_from_default_manager(self):
        before_live = DataPermTemplate.objects.count()
        before_all = DataPermTemplate.all_objects.count()
        self.tpl.soft_delete()
        self.assertEqual(DataPermTemplate.objects.count(), before_live - 1)
        self.assertEqual(DataPermTemplate.all_objects.count(), before_all)

    # ---- 基本绑定 ----
    def test_instantiate_with_explicit_binding(self):
        groups = instantiate(self.tpl, {'relation': 'contains'})
        cond = groups[0]['conditions'][0]
        self.assertEqual(cond['relation'], 'contains')
        self.assertEqual(cond['dynamicKey'], 'currentUser.departments')

    def test_instantiate_falls_back_to_param_default(self):
        self.assertEqual(
            instantiate(self.tpl, {})[0]['conditions'][0]['relation'], 'contains')

    def test_instantiate_binding_overrides_default(self):
        self.assertEqual(
            instantiate(self.tpl, {'relation': 'in_subtree'})[0]['conditions'][0]['relation'],
            'in_subtree')

    # ---- 缺参数 ----
    def test_missing_required_binding_raises(self):
        no_default = _mk_template(
            name='无默认值的模板',
            params=[{'key': 'relation', 'label': '包含关系', 'required': True}],
        )
        with self.assertRaises(TemplateBindError) as ctx:
            instantiate(no_default, {})
        self.assertIn('缺少参数', str(ctx.exception))

    # ---- 未声明占位符 ----
    def test_undeclared_placeholder_raises(self):
        bad = _mk_template(
            name='未声明占位符',
            params=[],
            groups=[{'expr': '', 'conditions': [
                {'dimension': 'dept', 'relation': '${nope}'},
            ]}],
        )
        with self.assertRaises(TemplateBindError) as ctx:
            instantiate(bad, {})
        self.assertIn('未声明的占位符', str(ctx.exception))

    def test_unbound_placeholders_reports_names(self):
        bad = _mk_template(
            name='探测占位符',
            params=[],
            groups=[{'expr': '', 'conditions': [
                {'dimension': 'dept', 'relation': '${alpha}'},
            ]}],
        )
        self.assertEqual(unbound_placeholders(bad.groups), {'alpha'})

    # ---- 控制字段禁止占位符（防注入）----
    def test_placeholder_in_control_field_rejected(self):
        evil = _mk_template(
            name='注入尝试',
            params=[],
            groups=[{'expr': '', 'conditions': [
                {'dimension': '${evilDim}', 'relation': 'contains'},
            ]}],
        )
        with self.assertRaises(TemplateBindError) as ctx:
            instantiate(evil, {})
        self.assertIn('控制字段', str(ctx.exception))

    def test_placeholder_in_dynamic_key_rejected(self):
        evil = _mk_template(
            name='注入尝试2',
            params=[],
            groups=[{'expr': '', 'conditions': [
                {'dimension': 'dept', 'dynamicKey': '${evil}', 'relation': 'contains'},
            ]}],
        )
        with self.assertRaises(TemplateBindError):
            instantiate(evil, {})

    # ---- 转义 ----
    def test_escaped_literal_placeholder_survives(self):
        """模板里若要写字面 ${...}，必须用 \\${ 转义，否则会被当成占位符。"""
        tricky = _mk_template(
            name='含转义占位符',
            params=[{'key': 'relation', 'label': 'R', 'default': 'contains'}],
            groups=[{'expr': '', 'conditions': [
                {'dimension': 'dept', 'valueSource': 'dynamic',
                 'dynamicKey': 'currentUser.departments', 'relation': '${relation}',
                 'note': r'\${notAPlaceholder}'},
            ]}],
        )
        groups = instantiate(tricky, {'relation': 'contains'})
        self.assertEqual(groups[0]['conditions'][0]['note'], '${notAPlaceholder}')

    # ---- 绑定结果仍走通用校验 ----
    def test_binding_result_validated_against_module(self):
        bad = _mk_template(
            name='非法维度模板',
            params=[],
            groups=[{'expr': '', 'conditions': [
                {'dimension': 'not_a_dimension', 'operator': 'in',
                 'values': [{'id': 'D1', 'label': 'X'}]},
            ]}],
        )
        with self.assertRaises(TemplateBindError) as ctx:
            instantiate(bad, {})
        self.assertIn('不合法', str(ctx.exception))

    def test_binding_result_validated_for_unknown_source(self):
        bad = _mk_template(
            name='非法来源模板',
            params=[],
            groups=[{'expr': '', 'conditions': [
                {'dimension': 'dept', 'valueSource': 'dynamic', 'dynamicKey': 'bogus'},
            ]}],
        )
        with self.assertRaises(TemplateBindError):
            instantiate(bad, {})

    # ---- 深拷贝 ----
    def test_instantiate_does_not_mutate_template(self):
        instantiate(self.tpl, {'relation': 'overlap'})
        self.assertEqual(self.tpl.groups[0]['conditions'][0]['relation'], '${relation}')

    def test_repeated_instantiate_is_stable(self):
        a = instantiate(self.tpl, {'relation': 'overlap'})
        b = instantiate(self.tpl, {'relation': 'overlap'})
        self.assertEqual(a, b)


class TemplateDriftTestCase(TestCase):
    def setUp(self):
        self.tpl = _mk_template()

    def _group_with_ref(self):
        # instantiate() 返回的是 **groups 列表**，取第 0 组的 conditions 才是条件数组
        groups = instantiate(self.tpl, {'relation': 'contains'})
        return {
            'expr': '',
            'templateRef': build_template_ref(self.tpl, {'relation': 'contains'}),
            'conditions': groups[0]['conditions'],
        }

    def test_build_ref_shape(self):
        ref = build_template_ref(self.tpl, {'relation': 'contains'})
        self.assertEqual(ref['templateCode'], self.tpl.code)
        self.assertEqual(ref['templateVersion'], self.tpl.version)
        self.assertEqual(ref['bindings'], {'relation': 'contains'})

    def test_no_drift_when_version_matches(self):
        self.assertIsNone(drift_of(self._group_with_ref(), {self.tpl.code: self.tpl}))

    def test_outdated_detected_when_template_version_bumps(self):
        g = self._group_with_ref()
        self.tpl.version = 2
        self.tpl.save()
        d = drift_of(g, {self.tpl.code: self.tpl})
        self.assertIsNotNone(d)
        self.assertEqual(d['state'], 'outdated')
        self.assertEqual(d['snapshotVersion'], 1)
        self.assertEqual(d['latestVersion'], 2)

    def test_missing_detected_when_template_soft_deleted(self):
        g = self._group_with_ref()
        self.tpl.soft_delete()
        d = drift_of(g, {})  # 软删后不在默认 manager 内，查不到
        self.assertIsNotNone(d)
        self.assertEqual(d['state'], 'missing')

    def test_snapshot_still_compiles_after_template_deleted(self):
        """核心性质：模板软删后，快照里的条件仍能正常编译（不失效）。"""
        g = self._group_with_ref()
        self.tpl.soft_delete()
        q = compile_scope_q({'expr': '', 'groups': [g]}, 'demand', user=None)
        self.assertIsNotNone(q)

    def test_summarize_drift_lists_all_drifted_groups(self):
        # 顺序要紧：先按当前版本建立快照，再升模板版本，才能测出「已落后」
        groups = [self._group_with_ref(), {'expr': '', 'conditions': []}]
        self.tpl.version = 3
        self.tpl.save()
        out = summarize_drift(groups, {self.tpl.code: self.tpl})
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['state'], 'outdated')

    def test_group_without_template_ref_is_ignored(self):
        self.assertIsNone(drift_of({'expr': '', 'conditions': []}, {}))