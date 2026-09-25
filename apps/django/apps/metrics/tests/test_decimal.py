"""T5：Decimal 全局化验证（INV-9）。

- type_cast NUMBER 统一返回 Decimal，杜绝 float 二进制精度陷阱
- metric_engine 的期望值解析 / 比较全程 Decimal（BETWEEN / IN / EQ / GT ...）
- 端到端：数值规则用字符串值也能精确比较
"""
import pytest
from decimal import Decimal

from apps.metrics.models import MetricDataType
from apps.metrics.services.field_resolver import TypeCastError, type_cast
from apps.metrics.services.metric_engine import MetricEngine
from apps.rule_engine.models import UnifiedOperator


# --------------------------------------------------------------------------
# type_cast
# --------------------------------------------------------------------------
def test_type_cast_returns_decimal():
    assert type_cast(30, MetricDataType.NUMBER) == Decimal('30')
    assert type_cast(30.5, MetricDataType.NUMBER) == Decimal('30.5')
    assert type_cast('30.5', MetricDataType.NUMBER) == Decimal('30.5')
    assert isinstance(type_cast('42', MetricDataType.NUMBER), Decimal)


def test_type_cast_no_float_precision_loss():
    # 经典 float 陷阱：0.1 + 0.2 != 0.3
    assert 0.1 + 0.2 != 0.3
    d = type_cast('0.1', MetricDataType.NUMBER) + type_cast('0.2', MetricDataType.NUMBER)
    assert d == Decimal('0.3')
    # 长尾小数直接以字符串进入，不丢精度
    assert type_cast('0.30000000000000004', MetricDataType.NUMBER) == Decimal('0.30000000000000004')


def test_type_cast_rejects_bool_and_garbage():
    with pytest.raises(TypeCastError):
        type_cast(True, MetricDataType.NUMBER)
    with pytest.raises(TypeCastError):
        type_cast('abc', MetricDataType.NUMBER)
    with pytest.raises(TypeCastError):
        type_cast('', MetricDataType.NUMBER)


# --------------------------------------------------------------------------
# metric_engine._compare / _expected
# --------------------------------------------------------------------------
def test_expected_decimal_for_number():
    expected, _ = MetricEngine._expected({'operator': 'GT', 'value': '30.5'}, MetricDataType.NUMBER)
    assert expected == Decimal('30.5') and isinstance(expected, Decimal)

    (low, high), _ = MetricEngine._expected(
        {'operator': 'BETWEEN', 'meta': {'min': '18', 'max': '35'}}, MetricDataType.NUMBER,
    )
    assert (low, high) == (Decimal('18'), Decimal('35'))


def test_compare_between_decimal_inclusive():
    expected = (Decimal('18.0'), Decimal('35.0'))
    assert MetricEngine._compare(UnifiedOperator.BETWEEN, Decimal('30.0'), expected, {}) is True
    # 闭区间：恰好等于上界应通过
    assert MetricEngine._compare(UnifiedOperator.BETWEEN, Decimal('35.0'), expected, {}) is True
    assert MetricEngine._compare(UnifiedOperator.BETWEEN, Decimal('36.0'), expected, {}) is False


def test_compare_in_decimal():
    expected = [Decimal('1'), Decimal('3'), Decimal('5')]
    assert MetricEngine._compare(UnifiedOperator.IN, Decimal('3'), expected, {}) is True
    assert MetricEngine._compare(UnifiedOperator.NOT_IN, Decimal('2'), expected, {}) is True
    assert MetricEngine._compare(UnifiedOperator.IN, Decimal('2'), expected, {}) is False


def test_compare_eq_gt_decimal():
    assert MetricEngine._compare(UnifiedOperator.EQ, Decimal('30'), Decimal('30'), {}) is True
    assert MetricEngine._compare(UnifiedOperator.GT, Decimal('35'), Decimal('30'), {}) is True
    assert MetricEngine._compare(UnifiedOperator.LTE, Decimal('30'), Decimal('30.0'), {}) is True


# --------------------------------------------------------------------------
# 端到端（需 DB）：数值规则用字符串值精确比较
# --------------------------------------------------------------------------
@pytest.mark.django_db
def test_execute_number_rule_decimal_end_to_end():
    from apps.metrics.models import AtomicMetric, MetricRule, MetricTemplate

    metric = AtomicMetric.objects.create(
        name='年龄D', source_path='candidate.age', data_type='number', unit='岁',
    )
    tmpl = MetricTemplate.objects.create(
        name='年龄模板D', atomic_metric=metric, operators=['GT'],
    )
    rule = MetricRule.objects.create(
        name='年龄规则D', scene='MANUAL', action_type='DEDUCT',
        conditions=[{'templateId': tmpl.pk, 'operator': 'GT', 'value': '30'}],
    )

    out_pass = MetricEngine.execute(rule.to_engine_conditions(), {'candidate': {'age': 35}}, 'AND')
    assert out_pass['pass'] is True
    # actual 经 type_cast 转为 Decimal
    assert out_pass['steps'][0]['actual'] == Decimal('35')

    out_fail = MetricEngine.execute(rule.to_engine_conditions(), {'candidate': {'age': 25}}, 'AND')
    assert out_fail['pass'] is False
