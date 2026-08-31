"""6 个 legacy 适配器映射正确性 + aggregate_rules 过滤（Phase 1）。

适配器对 legacy 实例用 SimpleNamespace 模拟（无必填 FK 时更轻量），断言 to_unified 产出
正确的 category/trigger_type/name/source_app 与 conditions/actions summary。
aggregate_rules 的过滤用真实轻量实例（FieldACL 无 FK；ControlRule 仅需 dimension/indicator）。
"""
import decimal
from types import SimpleNamespace

import pytest

from apps.campus_control.models import ControlDimension, ControlIndicator, ControlRule
from apps.field_acl.models import FieldACL
from apps.rule_engine.adapters import (
    AutomationAdapter,
    ConstraintAdapter,
    EntryConditionAdapter,
    MouAdapter,
    PolicyAdapter,
    TimeLimitAdapter,
    aggregate_rules,
)
from apps.rule_engine.models import RuleCategory, UnifiedActionType, UnifiedTriggerType

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# automation
# ---------------------------------------------------------------------------

def test_automation_adapter():
    legacy = SimpleNamespace(
        id='a1', name='自动推进', trigger_type=UnifiedTriggerType.STAGE_ENTERED,
        trigger_timing='IMMEDIATE', scope_json={'positions': ['p1']}, priority='P0',
        condition_logic='ALL', condition_json=[
            {'field': 'age', 'operator': 'GT', 'value': 18},
            {'field': 'level', 'operator': 'EQ', 'value': 'P1'},
        ],
        action_type=UnifiedActionType.AUTO_ADVANCE, next_stage_id='s2', skip_check=False,
        enabled=True,
    )
    dto = AutomationAdapter().to_unified(legacy)
    assert dto.category == RuleCategory.TCA
    assert dto.trigger_type == UnifiedTriggerType.STAGE_ENTERED
    assert dto.source_app == 'automation'
    assert dto.name == '自动推进'
    assert dto.priority == 'P0'
    assert dto.enabled is True
    assert len(dto.conditions_summary) == 2
    assert dto.conditions_summary[0]['field'] == 'age'
    assert dto.actions_summary[0]['action_type'] == UnifiedActionType.AUTO_ADVANCE
    assert dto.actions_summary[0]['params']['next_stage_id'] == 's2'


# ---------------------------------------------------------------------------
# entry_condition
# ---------------------------------------------------------------------------

def test_entry_condition_adapter():
    legacy = SimpleNamespace(
        id='e1', rule_name='进入条件', process_id='proc1', rule_seq=2,
        status='ENABLED', expression='(1 AND 2)', match_type='ALL',
        reject_message='不满足',
        items=[
            SimpleNamespace(item_seq=1, condition_type='CANDIDATE', field='age', operator='GT', value=18),
            SimpleNamespace(item_seq=2, condition_type='STAGE_STATUS', field='stage', operator='EQ', value='X'),
        ],
    )
    dto = EntryConditionAdapter().to_unified(legacy)
    assert dto.category == RuleCategory.TCA
    assert dto.trigger_type == UnifiedTriggerType.STAGE_ENTERED
    assert dto.source_app == 'entry_condition'
    assert dto.condition_expression == '(1 AND 2)'
    assert dto.condition_logic == 'ALL'
    assert dto.actions_summary[0]['action_type'] == UnifiedActionType.ALLOW
    assert dto.config_json['reject_message'] == '不满足'
    # seq 取 item_seq
    assert [c['seq'] for c in dto.conditions_summary] == [1, 2]
    assert dto.conditions_summary[1]['condition_type'] == 'STAGE_STATUS'


# ---------------------------------------------------------------------------
# time_limit
# ---------------------------------------------------------------------------

def test_time_limit_adapter():
    legacy = SimpleNamespace(
        id='t1', rule_name='限时锁', process_id='proc1', priority=5, enabled=True,
        lock_duration=30, extension_per_person=3, effective_scope='NEW_ONLY',
        conditions=[
            {'field': 'HIRING_LEVEL', 'operator': 'IN', 'value': ['P5', 'P6']},
        ],
    )
    dto = TimeLimitAdapter().to_unified(legacy)
    assert dto.category == RuleCategory.TCA
    assert dto.trigger_type == UnifiedTriggerType.STAGE_DWELL_TIMEOUT
    assert dto.source_app == 'time_limit'
    assert dto.priority_rank == 5
    act = dto.actions_summary[0]
    assert act['action_type'] == UnifiedActionType.LOCK
    assert act['params']['lock_duration'] == 30
    assert act['params']['effective_scope'] == 'NEW_ONLY'
    assert dto.conditions_summary[0]['field'] == 'HIRING_LEVEL'


# ---------------------------------------------------------------------------
# campus_control
# ---------------------------------------------------------------------------

def test_constraint_adapter():
    legacy = SimpleNamespace(
        id='c1', code='G0001', is_active=True,
        dimension=SimpleNamespace(name='院校'), indicator=SimpleNamespace(name='985'),
        target=decimal.Decimal('0.5'), strength='硬约束', year=2026, annual_target=10,
        bu='', position='', level='',
    )
    dto = ConstraintAdapter().to_unified(legacy)
    assert dto.category == RuleCategory.CONSTRAINT
    assert dto.trigger_type == UnifiedTriggerType.OFFER_SUBMITTED
    assert dto.source_app == 'campus_control'
    assert dto.conditions_summary == []
    assert dto.actions_summary == []
    assert dto.config_json['target'] == 0.5
    assert dto.config_json['dimension'] == '院校'
    assert dto.config_json['indicator'] == '985'
    assert dto.scope_json['bu'] is None


# ---------------------------------------------------------------------------
# mou
# ---------------------------------------------------------------------------

def test_mou_adapter_list_conditions():
    legacy = SimpleNamespace(
        id='m1', name='MOU规则', is_active=True, trigger_event='stage-entered',
        conditions=[{'field': 'x', 'operator': 'EQ', 'value': 1}],
        actions=[{'action_type': 'NOTIFY', 'params': {'to': 'hr'}}],
    )
    dto = MouAdapter().to_unified(legacy)
    assert dto.category == RuleCategory.TCA
    assert dto.trigger_type == UnifiedTriggerType.BUSINESS_EVENT
    assert dto.source_app == 'mou'
    assert dto.config_json['event'] == 'stage-entered'
    assert len(dto.conditions_summary) == 1
    assert dto.actions_summary[0]['action_type'] == 'NOTIFY'


def test_mou_adapter_dict_conditions_fallback_to_config():
    legacy = SimpleNamespace(
        id='m2', name='MOU规则2', is_active=True, trigger_event='candidate-added',
        conditions={'raw': '...'}, actions={'raw': '...'},
    )
    dto = MouAdapter().to_unified(legacy)
    assert dto.conditions_summary == []
    assert dto.actions_summary == []
    assert dto.config_json['conditions'] == {'raw': '...'}
    assert dto.config_json['actions'] == {'raw': '...'}


# ---------------------------------------------------------------------------
# field_acl
# ---------------------------------------------------------------------------

def test_policy_adapter():
    legacy = SimpleNamespace(
        id='f1', entity='candidate', field='phone', role_code='HR', permission='READ',
    )
    dto = PolicyAdapter().to_unified(legacy)
    assert dto.category == RuleCategory.POLICY
    assert dto.trigger_type == ''
    assert dto.source_app == 'field_acl'
    assert dto.actions_summary[0]['action_type'] == UnifiedActionType.SET_PERMISSION
    assert dto.config_json == {
        'entity': 'candidate', 'field': 'phone',
        'role_code': 'HR', 'permission': 'READ',
    }


# ---------------------------------------------------------------------------
# aggregate_rules 过滤（真实轻量实例）
# ---------------------------------------------------------------------------

def test_aggregate_rules_filter_by_source_app():
    FieldACL.objects.create(entity='candidate', field='phone', role_code='HR', permission='READ')
    dim = ControlDimension.objects.create(name='院校', code='S')
    ind = ControlIndicator.objects.create(dimension=dim, name='985')
    ControlRule.objects.create(dimension=dim, indicator=ind, target=decimal.Decimal('0.5'), is_active=True)

    dtos = aggregate_rules({'source_app': 'field_acl'})
    assert dtos, '应至少包含 field_acl'
    assert all(d.source_app == 'field_acl' for d in dtos)
    assert not any(d.source_app == 'campus_control' for d in dtos)


def test_aggregate_rules_filter_by_category():
    FieldACL.objects.create(entity='candidate', field='salary', role_code='HR', permission='MASK')
    dim = ControlDimension.objects.create(name='专业', code='M')
    ind = ControlIndicator.objects.create(dimension=dim, name='工学')
    ControlRule.objects.create(dimension=dim, indicator=ind, target=decimal.Decimal('0.3'), is_active=True)

    policy = aggregate_rules({'category': RuleCategory.POLICY})
    assert all(d.category == RuleCategory.POLICY for d in policy)
    assert any(d.source_app == 'campus_control' for d in policy) is False

    constraint = aggregate_rules({'category': RuleCategory.CONSTRAINT})
    assert all(d.category == RuleCategory.CONSTRAINT for d in constraint)
    assert all(d.source_app == 'campus_control' for d in constraint)
