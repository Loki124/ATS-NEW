"""expr_compiler 单测（纯逻辑，无需 DB）。

覆盖设计文档 §2.4 的 6 条语法规则 + 编译 + 保存校验。
"""
from django.db.models import Q
from django.test import TestCase

from apps.data_permission.attribute_fields import attribute_fields_for
from apps.data_permission.expr_compiler import (
    compile_scope_q,
    validate_expr,
    validate_scope_payload,
)
from apps.data_permission.field_map import MODULE_DIMENSION_FIELDS
from apps.metrics.models import AtomicMetric


class ExprCompilerTestCase(TestCase):
    # ---- 6 条规则：合法示例 ----
    def test_valid_examples(self):
        for expr, n in [
            ('1', 1), ('1 and 2 and 3', 3), ('(1 or 2) and 3', 3),
            ('(1 or 2) and (3 or 4)', 4), ('3 and (1 or 2)', 3),
            ('(1 or 2 or 3)', 3), ('(1 OR 2) AND 3', 3),
        ]:
            self.assertIsNone(validate_expr(expr, n), f'应合法: {expr}')

    # ---- 规则 5：同层混用 and/or 未加括号 ----
    def test_invalid_mixed_and_or(self):
        self.assertIsNotNone(validate_expr('1 or 2 and 3', 3))
        self.assertIsNotNone(validate_expr('(1 or 2 and 3)', 3))

    # ---- 规则 4：括号嵌套 ----
    def test_invalid_nested_paren(self):
        self.assertIsNotNone(validate_expr('((1 or 2))', 2))

    # ---- 规则 1：中文括号 ----
    def test_invalid_cjk_paren(self):
        self.assertIsNotNone(validate_expr('（1 or 2）', 2))

    # ---- 规则 2：非法保留字 ----
    def test_invalid_reserved_word(self):
        self.assertIsNotNone(validate_expr('1 xor 2', 2))

    # ---- 规则 3 / 括号未闭合 ----
    def test_invalid_unbalanced_paren(self):
        self.assertIsNotNone(validate_expr('(1 or 2', 2))
        self.assertIsNotNone(validate_expr('1 or 2)', 2))

    # ---- 规则 6：编号越界 ----
    def test_invalid_index_out_of_range(self):
        self.assertIsNotNone(validate_expr('5', 2))
        self.assertIsNotNone(validate_expr('(1 or 2) and 3', 2))

    # ---- 编译：组间 + 组内正确生成 Q ----
    def test_compile_scope_q_ok(self):
        # candidate: dept->referrer__department_id, creator->created_by_id
        payload = {
            'expr': '(1 or 2) and 3',
            'groups': [
                {'expr': '1 or 2', 'conditions': [
                    {'dimension': 'dept', 'operator': 'in', 'values': [{'id': 'D1'}, {'id': 'D2'}]},
                    {'dimension': 'creator', 'operator': 'in', 'values': [{'id': 7}]},
                ]},
                {'expr': '1', 'conditions': [
                    {'dimension': 'dept', 'operator': 'not_in', 'values': [{'id': 'D9'}]},
                ]},
                {'expr': '1', 'conditions': [
                    {'dimension': 'creator', 'operator': 'in', 'values': [{'id': 10}]},
                ]},
            ],
        }
        q = compile_scope_q(payload, 'candidate')
        self.assertIsNotNone(q)
        # 还原为字符串断言结构：((dept in D1,D2 OR creator in 7) OR (dept not_in D9)) AND (creator in 10)
        s = str(q)
        self.assertIn('referrer__department_id', s)
        self.assertIn('created_by_id', s)
        self.assertIn('NOT', s)  # not_in 产生 NOT

    def test_compile_scope_q_empty(self):
        self.assertIsNone(compile_scope_q({}, 'candidate'))
        self.assertIsNone(compile_scope_q({'groups': []}, 'candidate'))

    def test_compile_scope_q_unsupported_dim_noop(self):
        # talent 的 dept/owner 为 None -> 全部 no-op -> None
        payload = {
            'expr': '1',
            'groups': [{'expr': '1', 'conditions': [
                {'dimension': 'dept', 'operator': 'in', 'values': [{'id': 'D1'}]},
            ]}],
        }
        self.assertIsNone(compile_scope_q(payload, 'talent'))

    # ---- 保存校验 ----
    def test_validate_scope_payload_ok(self):
        payload = {
            'expr': '1',
            'groups': [{'expr': '(1 or 2)', 'conditions': [
                {'dimension': 'dept', 'operator': 'in', 'values': [{'id': 'D1'}]},
                {'dimension': 'creator', 'operator': 'in', 'values': [{'id': 5}]},
            ]}],
        }
        self.assertIsNone(validate_scope_payload(payload, 'candidate'))

    def test_validate_scope_payload_no_values(self):
        payload = {
            'expr': '1',
            'groups': [{'expr': '1', 'conditions': [
                {'dimension': 'dept', 'operator': 'in', 'values': []},
            ]}],
        }
        self.assertIsNotNone(validate_scope_payload(payload, 'candidate'))

    def test_validate_scope_payload_unsupported_dim(self):
        payload = {
            'expr': '1',
            'groups': [{'expr': '1', 'conditions': [
                {'dimension': 'process', 'operator': 'in', 'values': [{'id': 'P1'}]},
            ]}],
        }
        # process 维度在 candidate 不支持
        self.assertIsNotNone(validate_scope_payload(payload, 'candidate'))

    def test_validate_scope_payload_bad_inter_expr(self):
        payload = {
            'expr': '1 or 2 and 3',
            'groups': [{'expr': '1', 'conditions': [
                {'dimension': 'dept', 'operator': 'in', 'values': [{'id': 'D1'}]},
            ]}],
        }
        self.assertIsNotNone(validate_scope_payload(payload, 'candidate'))

    def test_module_field_map_coverage(self):
        # 确保每个模块 key 都在映射中
        for mk in ('demand', 'process', 'position', 'candidate', 'talent'):
            self.assertIn(mk, MODULE_DIMENSION_FIELDS)


class AttributeConditionTestCase(TestCase):
    """属性条件（attribute kind，复用指标目录标量字段，右值=字面量）。"""

    @classmethod
    def setUpTestData(cls):
        # 确保存在 source_path=demand.state / demand.headcount 的启用指标。
        # 用 source_path 作为 get_or_create 键（非 unique），并强制 status=enabled，
        # 既复用迁移 0012 已 seed 的行，又避免与已存在的 name 撞 UNIQUE。
        for sp, nm, dt in [
            ('demand.state', '需求状态', 'string'),
            ('demand.headcount', '招聘人数', 'number'),
        ]:
            obj, _ = AtomicMetric.objects.get_or_create(
                source_path=sp,
                defaults={'name': nm, 'data_type': dt, 'status': 'enabled'},
            )
            if obj.status != 'enabled':
                obj.status = 'enabled'
                obj.save(update_fields=['status'])

    def test_attribute_fields_for_demand(self):
        fields = {f['sourcePath']: f for f in attribute_fields_for('demand')}
        # demand.state 走 FSMField + state 分支 -> enum，带中文运算符
        state = fields.get('demand.state')
        self.assertIsNotNone(state)
        self.assertEqual(state['dataType'], 'enum')
        self.assertTrue(any(o['value'] == 'EQ' for o in state['operators']))
        self.assertTrue(any(o['label'] == '等于' for o in state['operators']))
        # demand.headcount 走 IntegerField -> number
        hc = fields.get('demand.headcount')
        self.assertIsNotNone(hc)
        self.assertEqual(hc['dataType'], 'number')

    def test_compile_scope_q_attribute_enum(self):
        payload = {
            'expr': '1',
            'groups': [{'expr': '1', 'conditions': [
                {'kind': 'attribute', 'field': 'demand.state', 'operator': 'EQ', 'value': 'RECRUITING'},
            ]}],
        }
        q = compile_scope_q(payload, 'demand')
        self.assertIsNotNone(q)
        s = str(q)
        self.assertIn('state', s)
        self.assertIn('RECRUITING', s)

    def test_compile_scope_q_attribute_number(self):
        payload = {
            'expr': '1',
            'groups': [{'expr': '1', 'conditions': [
                {'kind': 'attribute', 'field': 'demand.headcount', 'operator': 'GT', 'value': 3},
            ]}],
        }
        q = compile_scope_q(payload, 'demand')
        self.assertIsNotNone(q)
        s = str(q)
        self.assertIn('headcount__gt', s)

    def test_compile_scope_q_attribute_between(self):
        payload = {
            'expr': '1',
            'groups': [{'expr': '1', 'conditions': [
                {'kind': 'attribute', 'field': 'demand.headcount', 'operator': 'BETWEEN',
                 'value': None, 'meta': {'min': 1, 'max': 10}},
            ]}],
        }
        q = compile_scope_q(payload, 'demand')
        self.assertIsNotNone(q)
        s = str(q)
        self.assertIn('headcount__gte', s)
        self.assertIn('headcount__lte', s)

    def test_compile_scope_q_attribute_unregistered_field_noop(self):
        # 未注册的字段 -> no-op -> 整体 None
        payload = {
            'expr': '1',
            'groups': [{'expr': '1', 'conditions': [
                {'kind': 'attribute', 'field': 'demand.unknown_field', 'operator': 'EQ', 'value': 1},
            ]}],
        }
        self.assertIsNone(compile_scope_q(payload, 'demand'))

    def test_validate_scope_payload_attribute_ok(self):
        payload = {
            'expr': '1',
            'groups': [{'expr': '1', 'conditions': [
                {'kind': 'attribute', 'field': 'demand.state', 'operator': 'EQ', 'value': 'RECRUITING'},
            ]}],
        }
        self.assertIsNone(validate_scope_payload(payload, 'demand'))

    def test_validate_scope_payload_attribute_bad_operator(self):
        payload = {
            'expr': '1',
            'groups': [{'expr': '1', 'conditions': [
                # demand.state 不支持 CONTAINS
                {'kind': 'attribute', 'field': 'demand.state', 'operator': 'CONTAINS', 'value': 'x'},
            ]}],
        }
        self.assertIsNotNone(validate_scope_payload(payload, 'demand'))

    def test_validate_scope_payload_attribute_missing_value(self):
        payload = {
            'expr': '1',
            'groups': [{'expr': '1', 'conditions': [
                {'kind': 'attribute', 'field': 'demand.headcount', 'operator': 'GT', 'value': None},
            ]}],
        }
        self.assertIsNotNone(validate_scope_payload(payload, 'demand'))

    def test_validate_scope_payload_attribute_between_no_range(self):
        payload = {
            'expr': '1',
            'groups': [{'expr': '1', 'conditions': [
                {'kind': 'attribute', 'field': 'demand.headcount', 'operator': 'BETWEEN',
                 'value': None, 'meta': {'min': 1, 'max': None}},
            ]}],
        }
        self.assertIsNotNone(validate_scope_payload(payload, 'demand'))

    def test_validate_scope_payload_attribute_in_empty(self):
        payload = {
            'expr': '1',
            'groups': [{'expr': '1', 'conditions': [
                {'kind': 'attribute', 'field': 'demand.state', 'operator': 'IN', 'value': []},
            ]}],
        }
        self.assertIsNotNone(validate_scope_payload(payload, 'demand'))
