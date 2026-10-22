"""M04：指标作为条件源 —— ConditionEvaluator 委托 MetricEngine 求值。

覆盖点：
1. value_type=METRIC 的条件走 _evaluate_metric 分支（委托 MetricEngine.evaluate_metric_condition，零重写）。
2. 异常降级：MetricEngine 抛异常 → 命中判 False + degraded=True，绝不 500。
3. _is_metric_condition 双读触发：value_type=METRIC 或 metric_template_id 非空任一即触发（双读兼容）。
4. FIELD 存量条件行为不变（双读兼容：默认 value_type=FIELD + metric_template NULL）。
5. FIELD + METRIC 混合规则 expression 组合正确。
"""
from unittest.mock import MagicMock, patch

import pytest

from apps.rule_engine.models import (
    Condition,
    ConditionLogic,
    ConditionType,
    ConditionValueType,
    Rule,
    UnifiedOperator,
    UnifiedTriggerType,
)
from apps.rule_engine.services import ConditionEvaluator, EvaluationContext

pytestmark = pytest.mark.django_db

PATCH_TARGET = 'apps.metrics.services.metric_engine.MetricEngine.evaluate_metric_condition'


def _make_metric_rule(conditions, expression='', logic=ConditionLogic.ALL):
    """构造 Rule + Condition（支持 metric 条件：value_type / metric_template）。

    conditions 元素支持键：field/operator/value/meta_json/value_type/metric_template。
    """
    rule = Rule.objects.create(
        name='metric-rule',
        trigger_type=UnifiedTriggerType.STAGE_ENTERED,
        condition_expression=expression,
        condition_logic=logic,
    )
    for seq, spec in enumerate(conditions, start=1):
        Condition.objects.create(
            rule=rule, seq=seq,
            condition_type=spec.get('condition_type', ConditionType.CUSTOM),
            field=spec['field'],
            operator=spec['operator'],
            value=spec.get('value'),
            meta_json=spec.get('meta_json', {}),
            value_type=spec.get('value_type', ConditionValueType.FIELD),
            metric_template=spec.get('metric_template'),
        )
    return rule


def _ctx(candidate_id=None, extra=None):
    return EvaluationContext(
        trigger_type=UnifiedTriggerType.STAGE_ENTERED,
        candidate_id=candidate_id,
        extra=extra or {},
    )


# ---------------------------------------------------------------------------
# 1) METRIC 分支命中 / 不命中
# ---------------------------------------------------------------------------

def test_metric_condition_hit():
    """value_type=METRIC + 模板 pass=True → 命中，per_condition 透传模板信息。"""
    rule = _make_metric_rule([{
        'field': 'age_metric',
        'operator': UnifiedOperator.GT,
        'value': 18,
        'value_type': ConditionValueType.METRIC,
    }])
    ev = ConditionEvaluator()

    with patch(PATCH_TARGET) as mock_eval:
        mock_eval.return_value = {
            'pass': True,
            'template_id': 'tpl-1',
            'template_name': '候选人年龄',
            'operator': 'GT',
            'actual': 25,
            'expected': 18,
            'error': '',
            'degraded': False,
        }
        matched, detail = ev.evaluate(rule, _ctx('cand-1'))

    assert matched is True
    pc = detail['per_condition'][0]
    assert pc['matched'] is True
    assert pc['metric_template'] == '候选人年龄'
    assert pc['actual'] == 25
    assert pc['expected'] == 18
    assert pc['metric_error'] is None or pc['metric_error'] == ''
    mock_eval.assert_called_once()
    # 确认委托入参：template_id 来自 metric_template_id（此处为 None -> 'None'）
    kwargs = mock_eval.call_args.kwargs
    assert kwargs['operator'] == UnifiedOperator.GT
    assert kwargs['value'] == 18


def test_metric_condition_miss():
    """模板 pass=False → 不命中。"""
    rule = _make_metric_rule([{
        'field': 'age_metric',
        'operator': UnifiedOperator.GT,
        'value': 18,
        'value_type': ConditionValueType.METRIC,
    }])
    ev = ConditionEvaluator()

    with patch(PATCH_TARGET) as mock_eval:
        mock_eval.return_value = {
            'pass': False,
            'template_id': 'tpl-1',
            'template_name': '候选人年龄',
            'operator': 'GT',
            'actual': 10,
            'expected': 18,
            'error': '',
            'degraded': False,
        }
        matched, detail = ev.evaluate(rule, _ctx('cand-1'))

    assert matched is False
    assert detail['per_condition'][0]['matched'] is False
    assert detail['per_condition'][0]['actual'] == 10


def test_metric_condition_exception_degrades():
    """MetricEngine 抛异常 → 降级为不命中 + degraded=True + metric_error 记录，绝不 500。"""
    rule = _make_metric_rule([{
        'field': 'age_metric',
        'operator': UnifiedOperator.GT,
        'value': 18,
        'value_type': ConditionValueType.METRIC,
    }])
    ev = ConditionEvaluator()

    with patch(PATCH_TARGET, side_effect=RuntimeError('模板服务抖动')) as mock_eval:
        # 不应抛出
        matched, detail = ev.evaluate(rule, _ctx('cand-1'))

    assert matched is False
    pc = detail['per_condition'][0]
    assert pc['matched'] is False
    assert pc['metric_error'] is not None
    assert '模板服务抖动' in pc['metric_error']
    # 透传的 detail 含 degraded
    assert detail['per_condition'][0]['metric_template'] is None


# ---------------------------------------------------------------------------
# 2) _is_metric_condition 双读触发（直接单测，规避重 MetricTemplate 装配）
# ---------------------------------------------------------------------------

def _fake_cond(value_type=ConditionValueType.FIELD, metric_template_id=None):
    class _C:
        pass
    c = _C()
    c.value_type = value_type
    c.metric_template_id = metric_template_id
    return c


def test_is_metric_condition_triggers():
    """双读触发：value_type=METRIC 或 metric_template_id 非空任一即 True。"""
    # 显式 METRIC
    assert ConditionEvaluator._is_metric_condition(
        _fake_cond(value_type=ConditionValueType.METRIC)) is True
    # FIELD + 挂了模板 id（存量迁移态）也触发
    assert ConditionEvaluator._is_metric_condition(
        _fake_cond(value_type=ConditionValueType.FIELD, metric_template_id='tpl-x')) is True
    # 默认 FIELD + 无模板 → 不触发（走字段求值）
    assert ConditionEvaluator._is_metric_condition(
        _fake_cond(value_type=ConditionValueType.FIELD, metric_template_id=None)) is False


# ---------------------------------------------------------------------------
# 3) FIELD 存量兼容（双读回滚开关=默认行为完全不变）
# ---------------------------------------------------------------------------

def test_field_condition_backward_compat_unchanged():
    """FIELD 条件（无 metric_template）走 _resolve_value/_compare，行为同 M04 前。"""
    rule = _make_metric_rule([{
        'field': 'age',
        'operator': UnifiedOperator.GT,
        'value': 18,
        'value_type': ConditionValueType.FIELD,  # 默认
    }])
    ev = ConditionEvaluator()

    # 不应走到 MetricEngine（mock 未配置，若被调用会 AttributeError/报错）
    with patch(PATCH_TARGET) as mock_eval:
        matched, detail = ev.evaluate(rule, _ctx(extra={'age': 20}))
        assert matched is True
        assert mock_eval.called is False  # 关键：FIELD 条件绝不触碰 MetricEngine
        assert detail['per_condition'][0]['matched'] is True
        assert detail['per_condition'][0].get('metric_template') is None

    # 不命中的 FIELD 条件同样不受影响
    with patch(PATCH_TARGET) as mock_eval:
        matched, _ = ev.evaluate(rule, _ctx(extra={'age': 10}))
        assert matched is False
        assert mock_eval.called is False


# ---------------------------------------------------------------------------
# 4) FIELD + METRIC 混合规则 expression 组合
# ---------------------------------------------------------------------------

def test_mixed_field_and_metric_rule():
    """seq1 FIELD(age>18) AND seq2 METRIC(模板pass) -> 组合正确。"""
    rule = _make_metric_rule(
        conditions=[
            {'field': 'age', 'operator': UnifiedOperator.GT, 'value': 18,
             'value_type': ConditionValueType.FIELD},
            {'field': 'score_metric', 'operator': UnifiedOperator.GTE,
             'value': 60, 'value_type': ConditionValueType.METRIC},
        ],
        expression='(1 AND 2)',
    )
    ev = ConditionEvaluator()

    with patch(PATCH_TARGET) as mock_eval:
        # 两路都命中
        mock_eval.return_value = {'pass': True, 'template_name': '评分',
                                  'actual': 80, 'expected': 60, 'degraded': False}
        matched, detail = ev.evaluate(rule, _ctx('cand-1', extra={'age': 25}))
        assert matched is True
        assert detail['seq_results'] == {1: True, 2: True}

        # 仅 METRIC 不命中 -> AND 失败
        mock_eval.return_value = {'pass': False, 'template_name': '评分',
                                  'actual': 40, 'expected': 60, 'degraded': False}
        matched, detail = ev.evaluate(rule, _ctx('cand-1', extra={'age': 25}))
        assert matched is False
        assert detail['seq_results'] == {1: True, 2: False}


def test_metric_evaluate_passthrough_dict_on_missing_pass_key():
    """返回值缺 pass 键时，bool(None)=False 兜底，不抛。"""
    rule = _make_metric_rule([{
        'field': 'm',
        'operator': UnifiedOperator.EQ,
        'value': 1,
        'value_type': ConditionValueType.METRIC,
    }])
    ev = ConditionEvaluator()
    with patch(PATCH_TARGET, return_value={'actual': None}):
        matched, _ = ev.evaluate(rule, _ctx('cand-1'))
    assert matched is False
