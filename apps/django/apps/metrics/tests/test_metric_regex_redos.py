"""指标正则条件 ReDoS 缓解回归测试 —— Fix 2 (审计 P3).

证明:
- REGEX_MATCH 期望值(来自 HR 配置)长度超过 MAX_REGEX_PATTERN_LEN(200) → 判非法,
  比较阶段降级为 FAIL (TypeCastError), 不抛 500。
- 正常正则仍正常匹配, 不受长度闸门影响。
- 超长待匹配文本(>MAX_REGEX_INPUT_LEN=4096)跳过正则, 直接判不匹配 (避免灾难性回溯)。
"""
import pytest

from apps.metrics.models import AtomicMetric, MetricTemplate
from apps.metrics.services.metric_engine import (
    MAX_REGEX_INPUT_LEN,
    MAX_REGEX_PATTERN_LEN,
    MetricEngine,
)
from apps.rule_engine.models import UnifiedOperator

DATA = {
    'candidate': {
        'age': 32,
    }
}


def _age_template():
    metric = AtomicMetric.objects.create(
        name='年龄(ReDoS测试)', source_path='candidate.age', data_type='number', unit='岁',
    )
    return MetricTemplate.objects.create(
        name='年龄限制', atomic_metric=metric,
        operators=['REGEX_MATCH'],
    )


@pytest.mark.django_db
def test_regex_pattern_too_long_degrades_to_fail():
    """超长正则模式(>200)判非法 → 降级 FAIL (TypeCastError), 不 500."""
    long_pattern = 'a' * (MAX_REGEX_PATTERN_LEN + 1)
    tpl = _age_template()
    result = MetricEngine.execute(
        [{'templateId': tpl.pk, 'operator': 'REGEX_MATCH', 'value': long_pattern}], DATA,
    )
    assert result['pass'] is False
    step = result['steps'][0]
    assert step['degraded'] is True
    assert '过长' in step['error']


@pytest.mark.django_db
def test_regex_normal_match_still_works():
    """正常正则仍正常匹配 (回归)."""
    tpl = _age_template()
    result = MetricEngine.execute(
        [{'templateId': tpl.pk, 'operator': 'REGEX_MATCH', 'value': r'\d+'}], DATA,
    )
    assert result['pass'] is True, result['steps'][0]


def test_compare_regex_skips_overlong_input():
    """超长待匹配文本跳过正则, 直接判不匹配 (避免灾难性回溯). 无需 DB."""
    long_input = 'a' * (MAX_REGEX_INPUT_LEN + 1)
    # 灾难性回溯正则 (a+)+$ 对超长串本应卡死, 这里被长度闸门拦截返回 False
    result = MetricEngine._compare(UnifiedOperator.REGEX_MATCH, long_input, r'(a+)+$', {})
    assert result is False
