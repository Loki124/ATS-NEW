"""动态策略保存期表达式语法校验（DynamicStrategySerializer.validate）回归.

2026-10-20 兵哥 BugFix：动态策略「配置权限与规则」弹窗恢复组内/组间且或关系的
手填能力后，后端保存期必须同口径拦截非法表达式。

安全背景（为什么必须拦）：
  非法表达式（如 `1 and 2 or 3` 同层混用）若被保存成功，运行时
  enforcement -> compile_scope_q 编译期抛 ExprError，被 except 吞掉 ->
  compiled=None -> Q(pk__in=[]) -> 该模块对**所有人**静默全拒。
  保存期 400 把失败暴露在配置时，而不是留一个「看起来保存成功、实际全员拒绝」的暗礁。

范围纪律：只校验表达式**语法**（validate_expr 不碰维度/取值），存量合法配置
不受牵连；all/owner/none 模式无表达式语义，不校验。
"""
from django.test import TestCase

from apps.core.serializers_permission_v2 import DynamicStrategySerializer
from apps.data_permission.expr_compiler import ExprError, compile_scope_q


def _cond(dimension: str = 'creator', value_id: int = 1) -> dict:
    """一条静态关系维度条件（candidate 实体的 creator -> created_by_id）。"""
    return {
        'kind': 'relationship',
        'dimension': dimension,
        'operator': 'in',
        'valueSource': 'static',
        'values': [{'id': value_id, 'label': f'用户{value_id}'}],
    }


def _scope_groups(intra_expr: str = '') -> list:
    return [
        {'expr': intra_expr, 'conditions': [_cond(value_id=1), _cond(value_id=2)]},
        {'expr': '', 'conditions': [_cond(value_id=3)]},
    ]


def _serializer(module_config: dict) -> DynamicStrategySerializer:
    return DynamicStrategySerializer(data={
        'strategy_code': 'STRAT_EXPR_GUARD',
        'strategy_name': '表达式守卫测试',
        'status': 1,
        'governed_functions': ['candidate'],
        'granted_resource_codes': [],
        'module_config': module_config,
    })


class DynamicStrategyExprGuardTest(TestCase):
    """scope 模式表达式语法校验：非法拒绝 / 合法放行 / 其他模式不校验。"""

    def test_scope_invalid_intra_expr_rejected(self):
        """scope 模式非法组内表达式（`1 and`）-> ValidationError，错误定位到模块与组号。"""
        s = _serializer({
            'candidate': {
                'mode': 'scope', 'expr': '', 'actions': ['edit'],
                'groups': _scope_groups(intra_expr='1 and'),
            },
        })
        self.assertFalse(s.is_valid())
        self.assertIn('module_config', s.errors)
        msg = str(s.errors['module_config'])
        self.assertIn('candidate', msg)
        self.assertIn('第 1 组表达式有误', msg)

    def test_scope_invalid_inter_expr_rejected(self):
        """scope 模式非法组间表达式（同层混用 and/or）-> ValidationError。"""
        s = _serializer({
            'candidate': {
                'mode': 'scope', 'expr': '1 and 2 or 3', 'actions': ['edit'],
                'groups': _scope_groups(),
            },
        })
        self.assertFalse(s.is_valid())
        msg = str(s.errors['module_config'])
        self.assertIn('candidate', msg)
        self.assertIn('组间组合表达式有误', msg)

    def test_scope_out_of_range_index_rejected(self):
        """组间表达式引用不存在的组序号（2 组却写 1 and 3）-> ValidationError。"""
        s = _serializer({
            'candidate': {
                'mode': 'scope', 'expr': '1 and 3', 'actions': ['edit'],
                'groups': _scope_groups(),
            },
        })
        self.assertFalse(s.is_valid())
        self.assertIn('组间组合表达式有误', str(s.errors['module_config']))

    def test_scope_valid_exprs_accepted(self):
        """合法表达式（组内 `1 or 2`、组间 `1 and 2`）-> 保存通过。"""
        s = _serializer({
            'candidate': {
                'mode': 'scope', 'expr': '1 and 2', 'actions': ['edit'],
                'groups': _scope_groups(intra_expr='1 or 2'),
            },
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_scope_blank_exprs_accepted(self):
        """留空表达式合法（组内默认 AND、组间默认 OR）-> 保存通过。"""
        s = _serializer({
            'candidate': {
                'mode': 'scope', 'expr': '', 'actions': ['edit'],
                'groups': _scope_groups(),
            },
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_all_mode_skips_expr_validation(self):
        """all 模式不校验表达式（无表达式语义）—— 即便带脏表达式也放行。"""
        s = _serializer({
            'candidate': {
                'mode': 'all', 'expr': '1 and 2 or 3', 'actions': ['edit'],
                'groups': _scope_groups(intra_expr='1 and'),
            },
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_owner_mode_skips_expr_validation(self):
        """owner 模式不校验表达式。"""
        s = _serializer({
            'candidate': {
                'mode': 'owner', 'expr': '1 and', 'actions': ['edit'],
                'groups': _scope_groups(intra_expr='1 and'),
            },
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_invalid_expr_would_deny_all_at_runtime(self):
        """佐证守卫必要性：绕过序列化器存入的非法组间表达式，编译期抛 ExprError
        （enforcement 吞掉后该模块对所有人静默全拒）—— 所以保存期必须拦。"""
        payload = {
            'expr': '1 and 2 or 3',
            'groups': [
                {'expr': '', 'conditions': [_cond(value_id=1)]},
                {'expr': '', 'conditions': [_cond(value_id=2)]},
            ],
        }
        with self.assertRaises(ExprError):
            compile_scope_q(payload, 'candidate')
