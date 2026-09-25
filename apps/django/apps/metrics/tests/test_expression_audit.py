"""P1-C：条件表达式引擎安全审计 —— 把「无 eval/exec」与「白名单拒绝非法字符」锁成回归测试。

expressions.py 是手写 tokenizer + 递归下降 + Shunting-Yard RPN 求值器，
全程不依赖 eval/exec/compile/pickle。本测试防止日后有人误加危险调用，
也防止白名单被放宽（任何白名单外字符必须抛 ExpressionError）。
"""
import inspect

from django.test import TestCase

from apps.process import expressions


class ExpressionAuditTest(TestCase):
    def test_no_dangerous_calls(self):
        """静态扫描：源码不得包含任何危险调用。"""
        src = inspect.getsource(expressions)
        forbidden = (
            'eval(',
            'exec(',
            'compile(',
            'pickle',
            '__import__',
            'subprocess',
            'os.system',
        )
        for bad in forbidden:
            self.assertNotIn(bad, src, f'表达式引擎包含危险调用: {bad}')

    def test_tokenize_rejects_illegal_char(self):
        """白名单外字符（字母变量名）必须抛 ExpressionError。"""
        with self.assertRaises(expressions.ExpressionError):
            expressions.tokenize('1 AND x')

    def test_tokenize_rejects_symbol(self):
        with self.assertRaises(expressions.ExpressionError):
            expressions.tokenize('1 AND @')

    def test_validate_syntax_valid(self):
        result = expressions.validate_syntax('1 AND 2', max_id=2)
        self.assertTrue(result['valid'])
        self.assertIsNone(result['error'])

    def test_validate_syntax_invalid(self):
        result = expressions.validate_syntax('1 AND @', max_id=2)
        self.assertFalse(result['valid'])
        self.assertIsNotNone(result['error'])

    def test_validate_syntax_empty(self):
        result = expressions.validate_syntax('', max_id=2)
        self.assertFalse(result['valid'])

    def test_evaluate_rpn(self):
        self.assertTrue(
            expressions.evaluate('1 AND (2 OR 3)', {1: True, 2: False, 3: True})
        )
        self.assertFalse(
            expressions.evaluate('1 AND 2', {1: True, 2: False})
        )
        # 优先级：AND > OR
        self.assertTrue(
            expressions.evaluate('1 OR 2 AND 3', {1: False, 2: True, 3: True})
        )
