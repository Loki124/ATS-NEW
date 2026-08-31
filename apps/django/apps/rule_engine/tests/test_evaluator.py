"""ConditionEvaluator 单测（Phase 0）。

覆盖：condition_expression 组合（AND/OR）、condition_logic 兜底（ALL/ANY）、
各运算符示例、validate_expression / extract_ids 被正确使用。
"""
import pytest

from apps.process.services.expression_service import extract_ids, validate_expression
from apps.rule_engine.models import Condition, ConditionLogic, Rule, UnifiedOperator, UnifiedTriggerType
from apps.rule_engine.services import ConditionEvaluator, EvaluationContext

pytestmark = pytest.mark.django_db


def _make_rule(conditions, expression='', logic=ConditionLogic.ALL):
    """按条件定义构造 Rule + Condition（seq 自动递增）。"""
    rule = Rule.objects.create(
        name='eval-rule',
        trigger_type=UnifiedTriggerType.STAGE_ENTERED,
        condition_expression=expression,
        condition_logic=logic,
    )
    for seq, spec in enumerate(conditions, start=1):
        Condition.objects.create(
            rule=rule, seq=seq,
            field=spec['field'],
            operator=spec['operator'],
            value=spec.get('value'),
            meta_json=spec.get('meta_json', {}),
        )
    return rule


def _ctx(extra):
    return EvaluationContext(trigger_type=UnifiedTriggerType.STAGE_ENTERED, extra=extra)


# ---------------------------------------------------------------------------
# condition_expression 组合
# ---------------------------------------------------------------------------

def test_expression_and():
    # age>18 AND level=='P1'
    rule = _make_rule(
        conditions=[
            {'field': 'age', 'operator': UnifiedOperator.GT, 'value': 18},
            {'field': 'level', 'operator': UnifiedOperator.EQ, 'value': 'P1'},
        ],
        expression='(1 AND 2)',
    )
    ev = ConditionEvaluator()

    matched, detail = ev.evaluate(rule, _ctx({'age': 20, 'level': 'P1'}))
    assert matched is True
    assert detail['expression'] == '(1 AND 2)'
    assert detail['seq_results'] == {1: True, 2: True}

    matched, _ = ev.evaluate(rule, _ctx({'age': 20, 'level': 'X'}))
    assert matched is False  # 2 不满足 → AND 失败


def test_expression_or():
    rule = _make_rule(
        conditions=[
            {'field': 'age', 'operator': UnifiedOperator.GT, 'value': 18},
            {'field': 'level', 'operator': UnifiedOperator.EQ, 'value': 'P1'},
        ],
        expression='(1 OR 2)',
    )
    ev = ConditionEvaluator()

    # 仅 cond1 满足 → OR 命中
    matched, detail = ev.evaluate(rule, _ctx({'age': 20, 'level': 'X'}))
    assert matched is True
    assert detail['seq_results'] == {1: True, 2: False}

    # 都不满足 → OR 失败
    matched, _ = ev.evaluate(rule, _ctx({'age': 10, 'level': 'X'}))
    assert matched is False


# ---------------------------------------------------------------------------
# condition_logic 兜底（无 expression）
# ---------------------------------------------------------------------------

def test_logic_all_fallback():
    rule = _make_rule(
        conditions=[
            {'field': 'age', 'operator': UnifiedOperator.GT, 'value': 18},
            {'field': 'level', 'operator': UnifiedOperator.EQ, 'value': 'P1'},
        ],
        expression='',
        logic=ConditionLogic.ALL,
    )
    ev = ConditionEvaluator()
    # 仅一个满足 → ALL 不命中
    assert ev.evaluate(rule, _ctx({'age': 20, 'level': 'X'}))[0] is False
    # 全部满足 → 命中
    assert ev.evaluate(rule, _ctx({'age': 20, 'level': 'P1'}))[0] is True


def test_logic_any_fallback():
    rule = _make_rule(
        conditions=[
            {'field': 'age', 'operator': UnifiedOperator.GT, 'value': 18},
            {'field': 'level', 'operator': UnifiedOperator.EQ, 'value': 'P1'},
        ],
        expression='',
        logic=ConditionLogic.ANY,
    )
    ev = ConditionEvaluator()
    # 仅一个满足 → ANY 命中
    assert ev.evaluate(rule, _ctx({'age': 20, 'level': 'X'}))[0] is True
    # 都不满足 → 不命中
    assert ev.evaluate(rule, _ctx({'age': 10, 'level': 'X'}))[0] is False


# ---------------------------------------------------------------------------
# 各运算符示例（至少各一例）
# ---------------------------------------------------------------------------

def test_operators_eq_neq():
    ev = ConditionEvaluator()
    # EQ
    r = _make_rule([{'field': 'status', 'operator': UnifiedOperator.EQ, 'value': 'open'}], '')
    assert ev.evaluate(r, _ctx({'status': 'open'}))[0] is True
    assert ev.evaluate(r, _ctx({'status': 'closed'}))[0] is False
    # NEQ
    r = _make_rule([{'field': 'status', 'operator': UnifiedOperator.NEQ, 'value': 'closed'}], '')
    assert ev.evaluate(r, _ctx({'status': 'open'}))[0] is True
    assert ev.evaluate(r, _ctx({'status': 'closed'}))[0] is False


def test_operators_gt_lt():
    ev = ConditionEvaluator()
    r = _make_rule([{'field': 'age', 'operator': UnifiedOperator.GT, 'value': 18}], '')
    assert ev.evaluate(r, _ctx({'age': 20}))[0] is True
    assert ev.evaluate(r, _ctx({'age': 10}))[0] is False
    r = _make_rule([{'field': 'age', 'operator': UnifiedOperator.LTE, 'value': 60}], '')
    assert ev.evaluate(r, _ctx({'age': 60}))[0] is True
    assert ev.evaluate(r, _ctx({'age': 61}))[0] is False


def test_operator_in_not_in():
    ev = ConditionEvaluator()
    r = _make_rule([{'field': 'city', 'operator': UnifiedOperator.IN, 'value': ['BJ', 'SH']}], '')
    assert ev.evaluate(r, _ctx({'city': 'BJ'}))[0] is True
    assert ev.evaluate(r, _ctx({'city': 'GZ'}))[0] is False
    r = _make_rule([{'field': 'city', 'operator': UnifiedOperator.NOT_IN, 'value': ['BJ']}], '')
    assert ev.evaluate(r, _ctx({'city': 'SH'}))[0] is True
    assert ev.evaluate(r, _ctx({'city': 'BJ'}))[0] is False


def test_operator_between_uses_meta_json():
    ev = ConditionEvaluator()
    r = _make_rule([{
        'field': 'score', 'operator': UnifiedOperator.BETWEEN,
        'meta_json': {'min': 60, 'max': 100},
    }], '')
    assert ev.evaluate(r, _ctx({'score': 75}))[0] is True
    assert ev.evaluate(r, _ctx({'score': 59}))[0] is False
    assert ev.evaluate(r, _ctx({'score': 100}))[0] is True


def test_operator_is_empty():
    ev = ConditionEvaluator()
    r = _make_rule([{'field': 'note', 'operator': UnifiedOperator.IS_EMPTY}], '')
    assert ev.evaluate(r, _ctx({'note': ''}))[0] is True
    assert ev.evaluate(r, _ctx({'note': None}))[0] is True
    assert ev.evaluate(r, _ctx({'note': 'hi'}))[0] is False
    r = _make_rule([{'field': 'note', 'operator': UnifiedOperator.IS_NOT_EMPTY}], '')
    assert ev.evaluate(r, _ctx({'note': 'hi'}))[0] is True
    assert ev.evaluate(r, _ctx({'note': ''}))[0] is False


# ---------------------------------------------------------------------------
# validate_expression / extract_ids 被正确使用
# ---------------------------------------------------------------------------

def test_extract_ids_usage():
    assert extract_ids('(1 AND 2) OR 3') == [1, 2, 3]


def test_validate_expression_invalid_short_circuits_evaluate():
    """expression 引用超出条件数 → validate_expression 判非法 → evaluate 返回 False。"""
    rule = _make_rule(
        conditions=[{'field': 'age', 'operator': UnifiedOperator.GT, 'value': 18}],
        expression='(1 AND 9)',  # 仅 1 条条件，引用 9 超范围
    )
    validation = validate_expression('(1 AND 9)', max_id=1)
    assert validation.valid is False
    ev = ConditionEvaluator()
    matched, detail = ev.evaluate(rule, _ctx({'age': 20}))
    assert matched is False
    assert detail.get('expression_error') is not None
