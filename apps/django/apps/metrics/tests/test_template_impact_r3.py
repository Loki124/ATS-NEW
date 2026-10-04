"""LIFE-1 T05-A：R3 受影响规则扫描锁定测试。

get_template_affected_rules 必须扫描 metrics.MetricRule.conditions（R3 路径），
命中条件中 templateId / template_id 指向目标模板的规则；与 R1/R2 合并计入 total。
此前 LIFE-2 的「受影响规则枚举」遗漏此 JSON 路径，本测试将其锁定。
"""
import pytest

pytestmark = pytest.mark.django_db

from ..models import AtomicMetric, MetricRule, MetricTemplate
from ..services.template_impact import get_template_affected_rules


def _make_atomic():
    return AtomicMetric.objects.create(
        name='R3 原子指标', source_path='candidate.age',
        data_type='number', unit='岁', status='enabled',
    )


def _make_template(atomic, name='R3 模板'):
    return MetricTemplate.objects.create(
        name=name, atomic_metric=atomic, operators=['GT'], status='enabled',
    )


def test_r3_metric_rule_condition_matches_template_id(super_user):
    """MetricRule.conditions 中 templateId 命中 -> 出现在 metric_rules（R3 命中）。"""
    atomic = _make_atomic()
    tpl = _make_template(atomic)

    rule = MetricRule.objects.create(
        name='R3 命中规则',
        scene='FILTER',
        conditions=[{'templateId': str(tpl.id), 'operator': 'GT', 'value': 5}],
        action_type='VETO',
    )
    # 干扰规则引用别的模板，不应命中
    MetricRule.objects.create(
        name='R3 干扰规则',
        scene='FILTER',
        conditions=[{'templateId': '000000000000000000000000', 'operator': 'GT', 'value': 5}],
        action_type='VETO',
    )

    result = get_template_affected_rules(str(tpl.id))

    matched_ids = {m['rule_id'] for m in result['metric_rules']}
    assert str(rule.id) in matched_ids
    # 干扰规则不应出现（按规则 id 去重，至多 1 条）
    assert len(result['metric_rules']) == 1
    # total 应等于三路之和
    assert result['total'] == (
        len(result['entry_conditions']) + len(result['stage_rules']) + len(result['metric_rules'])
    )


def test_r3_accepts_snake_template_id_spelling(super_user):
    """兼容性：conditions 用 template_id（snake）拼写也应命中。"""
    atomic = _make_atomic()
    tpl = _make_template(atomic)
    rule = MetricRule.objects.create(
        name='R3 snake 拼写规则',
        scene='SCORING',
        conditions=[{'template_id': str(tpl.id), 'operator': 'IN', 'value': [1, 2]}],
        action_type='BONUS',
    )
    result = get_template_affected_rules(str(tpl.id))
    matched_ids = {m['rule_id'] for m in result['metric_rules']}
    assert str(rule.id) in matched_ids


def test_r3_no_match_when_template_not_referenced(super_user):
    """模板未被任何 MetricRule 引用 -> metric_rules 为空。"""
    atomic = _make_atomic()
    tpl = _make_template(atomic)
    MetricRule.objects.create(
        name='无关规则',
        scene='FILTER',
        conditions=[{'templateId': 'ffffffffffffffffffffffff', 'operator': 'GT', 'value': 1}],
        action_type='VETO',
    )
    result = get_template_affected_rules(str(tpl.id))
    assert result['metric_rules'] == []
