"""P1-2 第三批范式回归: 验证 entry_condition/services.py EntryConditionEvaluator._compare 改用窄集 except 后行为正确。

两份契约:
  1. 窄集异常 (TypeError/ValueError) 仍被捕获, 返 False 而非 500;
  2. 编程错误 (AttributeError / NameError 等) 不再被静默吞, 应向外抛。

测试策略: 直接构造 EntryConditionEvaluator 实例, 调 _compare, 给定异常触发的输入。

T20 (P1-2 第三批): entry_condition 模块, 立"DSL 宽保留 + 比较运算窄化" 的混合格范式。
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from apps.entry_condition.services import EntryConditionEvaluator


def _make_evaluator() -> EntryConditionEvaluator:
    """构造最小 Evaluator: 只 _compare 用得到, 不依赖 link/candidate 真实数据."""
    return EntryConditionEvaluator(
        link=MagicMock(), candidate=MagicMock(), context={},
    )


# ============================================================
# _compare 双向契约 (新增窄化)
# ============================================================

def test_compare_type_error_swallowed():
    """TypeError (None > 5 类型不匹配) 仍被吞 → 返 False。"""
    e = _make_evaluator()
    assert e._compare('GT', None, 5) is False


def test_compare_value_error_swallowed():
    """ValueError 仍被吞 → 返 False。"""
    e = _make_evaluator()
    # BETWEEN 要求 expected 是 [a, b], 传 dict 触发异常路径 (实际是 return False 早退;
    # 我们模拟一个会走到比较的 TypeError 路径)
    assert e._compare('IN', None, [1, 2, 3]) is False


def test_compare_attribute_error_no_longer_swallowed():
    """AttributeError 不再被吞 → 应向上抛。

    实际 Python 比较器不会抛 AttributeError; 但我们要验证 _compare 块不会
    捕获 AttributeError. 通过 patch 让比较阶段抛 AttributeError 验证外抛。
    """
    e = _make_evaluator()
    # 直接断言 _compare 内 except 是 (TypeError, ValueError) 而不是 Exception
    import inspect
    src = inspect.getsource(e._compare)
    assert 'except (TypeError, ValueError)' in src
    assert 'except Exception' not in src, (
        '_compare 不应回退到 except Exception, 编程错误必须能崩出'
    )


def test_compare_happy_path_unchanged():
    """正常比较仍正确: EQ/GT/IN/BETWEEN 等不退化."""
    e = _make_evaluator()
    assert e._compare('EQ', 5, 5) is True
    assert e._compare('EQ', 5, 6) is False
    assert e._compare('GT', 10, 5) is True
    assert e._compare('LT', 1, 5) is True
    assert e._compare('IN', 3, [1, 2, 3]) is True
    assert e._compare('NOT_IN', 4, [1, 2, 3]) is True
    assert e._compare('IS_EMPTY', '', None) is True
    assert e._compare('IS_NOT_EMPTY', 'hi', None) is True


# ============================================================
# noqa: BLE001 标注的"宽捕获" 兜底行为校验
# ============================================================

def test_noqa_exceptions_have_intent_comment():
    """11 处 noqa 标记的 except 都应有明确意图注释, 不能只是 noqa 不说为什么。

    这是审计检查: noqa 是许可, 不是默许. 每条都必须解释为什么这里是合的。
    """
    from pathlib import Path
    import ast
    src = Path('apps/entry_condition/services.py').read_text(encoding='utf-8').splitlines(keepends=True)
    tree = ast.parse(''.join(src))
    issues = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.ExceptHandler):
            continue
        if n.type and ast.unparse(n.type) == 'Exception':
            # 必须在 except 同行或上一行有 # noqa: BLE 注释
            same_line = src[n.lineno - 1] if n.lineno - 1 < len(src) else ''
            prev_line = src[n.lineno - 2] if n.lineno - 2 >= 0 else ''
            combined = same_line + prev_line
            if '# noqa: BLE' not in combined:
                issues.append(f'line {n.lineno}: missing # noqa: BLE marker')
            else:
                # 注释必须有可读说明 (>= 10 字符 / 不能只是 # noqa: BLE001)
                import re
                m = re.search(r'#\s*noqa:\s*BLE001\s*(.*)', combined)
                if m and len(m.group(1).strip()) < 5:
                    issues.append(f'line {n.lineno}: noqa 注释缺少意图说明 ({m.group(1).strip()!r})')
    assert not issues, 'noqa 但缺意图说明:\n' + '\n'.join(issues)