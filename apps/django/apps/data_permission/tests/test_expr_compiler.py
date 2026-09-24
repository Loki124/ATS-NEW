"""expr_compiler 单测（纯逻辑，无需 DB）。

覆盖设计文档 §2.4 的 6 条语法规则 + 编译 + 保存校验。
"""
from django.db.models import Q
from django.test import TestCase

from apps.data_permission.expr_compiler import (
    compile_scope_q,
    validate_expr,
    validate_scope_payload,
)
from apps.data_permission.field_map import MODULE_DIMENSION_FIELDS


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
