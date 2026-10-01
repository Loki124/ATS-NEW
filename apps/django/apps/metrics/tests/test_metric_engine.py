"""MetricEngine 端到端单元测试 —— 对齐 PRD AC-01 / AC-02 / AC-04，并覆盖派生指标。"""
import pytest

from apps.metrics.models import AtomicMetric, DerivedMetric, MetricTemplate
from apps.metrics.services.metric_engine import MetricEngine

DATA = {
    'candidate': {
        'age': 32,
        'workExperience': [
            {'company': 'A', 'start_date': '2020-01-01', 'end_date': '2021-01-01'},
            {'company': 'B', 'start_date': '2021-07-01', 'end_date': '2022-01-01'},
        ],
    }
}


def _age_template(operators=None):
    metric = AtomicMetric.objects.create(
        name='年龄(引擎测试)', source_path='candidate.age', data_type='number', unit='岁',
    )
    return MetricTemplate.objects.create(
        name='年龄限制', atomic_metric=metric,
        operators=operators or ['GT', 'LT', 'EQ'],
    )


@pytest.mark.django_db
def test_ac01_age_gt_30_passes():
    """AC-01：配置「年龄 > 30」并执行 → PASS，且步骤详情描述完整。"""
    tpl = _age_template()
    result = MetricEngine.execute(
        [{'templateId': tpl.pk, 'operator': 'GT', 'value': '30'}], DATA,
    )
    assert result['pass'] is True
    step = result['steps'][0]
    assert step['pass'] is True
    assert step['detail'] == '年龄限制(candidate.age) = 32岁 大于 30岁'


@pytest.mark.django_db
def test_ac02_change_threshold_to_40_fails():
    """AC-02：阈值改 35/40 立即生效 → FAIL（无需改代码）。"""
    tpl = _age_template()
    result = MetricEngine.execute(
        [{'templateId': tpl.pk, 'operator': 'GT', 'value': '40'}], DATA,
    )
    assert result['pass'] is False
    assert result['steps'][0]['pass'] is False


@pytest.mark.django_db
def test_ac04_operator_not_supported_by_template():
    """AC-04：后端拒绝模板不支持的运算符（不 500，降级为该步 FAIL + 明确错误）。"""
    tpl = _age_template(operators=['GT', 'LT', 'EQ'])
    result = MetricEngine.execute(
        [{'templateId': tpl.pk, 'operator': 'BETWEEN', 'value': None}], DATA,
    )
    assert result['pass'] is False
    assert '不支持运算符' in result['steps'][0]['error']


@pytest.mark.django_db
def test_missing_template_reports_error_not_exception():
    result = MetricEngine.execute(
        [{'templateId': 'not-exist', 'operator': 'GT', 'value': '30'}], DATA,
    )
    assert result['pass'] is False
    assert '不存在' in result['steps'][0]['error']


@pytest.mark.django_db
def test_missing_field_reports_resolve_error():
    tpl = _age_template()
    result = MetricEngine.execute(
        [{'templateId': tpl.pk, 'operator': 'GT', 'value': '30'}],
        {'candidate': {}},
    )
    assert result['pass'] is False
    assert '字段解析失败' in result['steps'][0]['error']


@pytest.mark.django_db
def test_derived_metric_max_gap():
    """PRD 原子架构覆盖不了的规则：空窗期 ≤ 6 个月 —— 由派生指标零代码完成。"""
    metric = DerivedMetric.objects.create(
        name='最大空窗期', calc_func='MAX_GAP',
        base_path='candidate.workExperience', data_type='number', unit='月',
    )
    tpl = MetricTemplate.objects.create(
        name='空窗期限制', derived_metric=metric, operators=['LTE', 'GT'],
    )
    result = MetricEngine.execute(
        [{'templateId': tpl.pk, 'operator': 'LTE', 'value': '6'}], DATA,
    )
    assert result['pass'] is True, result['steps'][0]
    assert result['steps'][0]['actual'] == 6

    # 阈值收紧到 5 → 立即 FAIL（验证可调）
    tight = MetricEngine.execute(
        [{'templateId': tpl.pk, 'operator': 'LTE', 'value': '5'}], DATA,
    )
    assert tight['pass'] is False


@pytest.mark.django_db
def test_or_logic():
    tpl = _age_template()
    conditions = [
        {'templateId': tpl.pk, 'operator': 'GT', 'value': '40'},   # False
        {'templateId': tpl.pk, 'operator': 'LT', 'value': '40'},   # True
    ]
    assert MetricEngine.execute(conditions, DATA, logic='OR')['pass'] is True
    assert MetricEngine.execute(conditions, DATA, logic='AND')['pass'] is False


@pytest.mark.django_db
def test_empty_conditions():
    result = MetricEngine.execute([], DATA)
    assert result['pass'] is False
    assert '没有配置任何条件' in result['summary']


@pytest.mark.django_db
def test_between_uses_meta_min_max():
    """BETWEEN 的 min/max 走 meta（复用 rule_engine 既有约定，非单 value）。"""
    tpl = _age_template(operators=['BETWEEN'])
    result = MetricEngine.execute(
        [{'templateId': tpl.pk, 'operator': 'BETWEEN', 'value': None,
          'meta': {'min': '25', 'max': '35'}}], DATA,
    )
    assert result['pass'] is True


@pytest.mark.django_db
def test_is_empty_operator():
    tpl = _age_template(operators=['IS_EMPTY', 'IS_NOT_EMPTY'])
    result = MetricEngine.execute(
        [{'templateId': tpl.pk, 'operator': 'IS_NOT_EMPTY', 'value': None}], DATA,
    )
    assert result['pass'] is True
