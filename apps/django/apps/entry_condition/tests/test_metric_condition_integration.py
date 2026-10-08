"""entry_condition 接入 METRIC 源集成测试（T04）。

验证 EntryConditionEvaluator 在 _get_actual_value / _evaluate_item 中正确委托
MetricEngine.evaluate_metric_condition 取回 actual 并完成比较。

注意：EntryConditionEvaluator 的 METRIC 分支不触碰 link，故用满足构造签名的 stub link。
"""
import pytest
from nanoid import generate as nanoid_generate

from apps.candidate.models import Candidate
from apps.entry_condition.models import ConditionFieldType, ConditionItem, ConditionOperator
from apps.entry_condition.services import EntryConditionEvaluator
from apps.metrics.models import AtomicMetric, MetricTemplate


def _cid() -> str:
    return nanoid_generate(size=21)


def _make_candidate(age=None, **fields) -> Candidate:
    return Candidate.objects.create(
        id=_cid(), name='测试', phone='13900000077', age=age, **fields,
    )


def _make_atomic_template(name, source_path, data_type='number', operators=None):
    metric = AtomicMetric.objects.create(
        name=f'am_{name}_{_cid()}', source_path=source_path, data_type=data_type,
    )
    return MetricTemplate.objects.create(
        name=f'{name}_{_cid()}', atomic_metric=metric,
        operators=operators or ['GT', 'LT', 'EQ'],
    )


class _StubLink:
    """满足构造签名即可，METRIC 分支不触碰 link 任何属性。"""
    pass


@pytest.mark.django_db
def test_get_actual_value_metric_returns_actual():
    tpl = _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=40)
    item = ConditionItem(
        id=_cid(), item_seq=1,
        condition_type=ConditionFieldType.METRIC, field=str(tpl.id),
        operator=ConditionOperator.GT, value=30,
    )
    evaluator = EntryConditionEvaluator(_StubLink(), cand)
    actual = evaluator._get_actual_value(item)
    # MetricEngine 对 number 类型做 type_cast → Decimal('40')，等于 40
    assert actual == 40


@pytest.mark.django_db
def test_evaluate_item_metric_passes_and_fails():
    tpl = _make_atomic_template('年龄', 'candidate.age', 'number', ['GT', 'LT'])
    cand = _make_candidate(age=40)
    hit = ConditionItem(
        id=_cid(), item_seq=1,
        condition_type=ConditionFieldType.METRIC, field=str(tpl.id),
        operator=ConditionOperator.GT, value=30,
    )
    miss = ConditionItem(
        id=_cid(), item_seq=2,
        condition_type=ConditionFieldType.METRIC, field=str(tpl.id),
        operator=ConditionOperator.GT, value=100,
    )
    evaluator = EntryConditionEvaluator(_StubLink(), cand)
    cr_hit = evaluator._evaluate_item(hit)
    cr_miss = evaluator._evaluate_item(miss)
    assert cr_hit.passed is True
    assert cr_hit.actual_value == 40
    assert cr_miss.passed is False


@pytest.mark.django_db
def test_get_actual_value_metric_is_empty_hit():
    """METRIC 源 IS_EMPTY 命中（审查补充覆盖）：age=None → actual None，
    entry_condition _compare(IS_EMPTY, None) → 通过。"""
    tpl = _make_atomic_template('年龄', 'candidate.age', 'number', ['IS_EMPTY', 'IS_NOT_EMPTY'])
    cand = _make_candidate(age=None)
    item = ConditionItem(
        id=_cid(), item_seq=1,
        condition_type=ConditionFieldType.METRIC, field=str(tpl.id),
        operator=ConditionOperator.IS_EMPTY, value=None,
    )
    evaluator = EntryConditionEvaluator(_StubLink(), cand)
    cr = evaluator._evaluate_item(item)
    assert cr.passed is True
    assert cr.actual_value is None


@pytest.mark.django_db
def test_evaluate_item_metric_boolean_eq_true():
    """METRIC 源布尔 EQ 'true' 命中（F2 必修）：is_blacklisted=True → pass True。

    验证 MetricEngine 把原生 bool 归一成 'true' 字符串，entry_condition 二次比较
    'true' == 'true' 恒成立（修复前 bool(True) != 'true' 导致恒为未命中）。
    """
    metric = AtomicMetric.objects.create(
        name=f'am_black_{_cid()}', source_path='candidate.is_blacklisted',
        data_type='boolean',
    )
    tpl = MetricTemplate.objects.create(
        name=f'黑名单_{_cid()}', atomic_metric=metric, operators=['EQ', 'NEQ'],
    )
    cand = _make_candidate(is_blacklisted=True)
    item = ConditionItem(
        id=_cid(), item_seq=1,
        condition_type=ConditionFieldType.METRIC, field=str(tpl.id),
        operator=ConditionOperator.EQ, value='true',
    )
    evaluator = EntryConditionEvaluator(_StubLink(), cand)
    cr = evaluator._evaluate_item(item)
    assert cr.passed is True
    assert cr.actual_value == 'true'
