"""rule_engine 模型层测试（Phase 0）。

覆盖：枚举值齐全、Rule→Condition/Action 级联、RuleExecutionLog 写入、软删字段存在。
"""
import pytest
from django.db.models import CharField

from apps.rule_engine.models import (
    Action,
    Condition,
    ConditionLogic,
    ConditionType,
    EvaluateResult,
    Priority,
    Rule,
    RuleCategory,
    RuleExecutionLog,
    RuleStatus,
    UnifiedActionType,
    UnifiedOperator,
    UnifiedTriggerType,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# 枚举值齐全
# ---------------------------------------------------------------------------

def test_rule_category_values():
    assert {c.value for c in RuleCategory} == {'TCA', 'CONSTRAINT', 'POLICY'}


def test_trigger_type_values():
    assert {c.value for c in UnifiedTriggerType} == {
        'STAGE_ENTERED', 'STATE_CHANGED', 'EVALUATION_SUBMITTED', 'SCHEDULED',
        'STAGE_DWELL_TIMEOUT', 'OFFER_SUBMITTED', 'BUSINESS_EVENT',
    }


def test_action_type_values():
    assert {c.value for c in UnifiedActionType} == {
        'AUTO_ADVANCE', 'SKIP_TO', 'REMIND', 'REJECT_TO_POOL', 'ALLOW', 'REJECT',
        'LOCK', 'UNLOCK', 'BLOCK_HARD', 'BLOCK_SOFT', 'ASSIGN_HANDLER', 'SET_PERMISSION',
    }


def test_operator_values_are_eleven():
    assert {c.value for c in UnifiedOperator} == {
        'EQ', 'NEQ', 'GT', 'GTE', 'LT', 'LTE',
        'BETWEEN', 'IN', 'NOT_IN', 'IS_EMPTY', 'IS_NOT_EMPTY',
    }
    assert len(UnifiedOperator.choices) == 11


def test_condition_type_values():
    assert {c.value for c in ConditionType} == {'STAGE_STATUS', 'CANDIDATE', 'DEMAND', 'CUSTOM'}


def test_priority_and_status_and_result_values():
    assert {c.value for c in Priority} == {'P0', 'P1', 'P2'}
    assert {c.value for c in RuleStatus} == {'ENABLED', 'DISABLED'}
    assert {c.value for c in EvaluateResult} == {
        'MATCHED', 'UNMATCHED', 'ERROR', 'ALLOWED', 'REJECTED',
        'BLOCKED', 'SKIPPED', 'LOCKED',
    }
    assert {c.value for c in ConditionLogic} == {'ALL', 'ANY'}


# ---------------------------------------------------------------------------
# 模型实例 / 级联
# ---------------------------------------------------------------------------

def _make_rule(**kwargs):
    return Rule.objects.create(
        name=kwargs.pop('name', '测试规则'),
        trigger_type=kwargs.pop('trigger_type', UnifiedTriggerType.STAGE_ENTERED),
        **kwargs,
    )


def test_rule_creates_with_nanoid_pk():
    rule = _make_rule()
    assert rule.id and len(rule.id) == 21  # UUIDModel: nanoid size=21


def test_rule_condition_action_cascade():
    rule = _make_rule()
    c1 = Condition.objects.create(rule=rule, seq=1, field='age', operator=UnifiedOperator.GT, value=18)
    a1 = Action.objects.create(rule=rule, seq=1, action_type=UnifiedActionType.ALLOW)
    assert rule.ordered_conditions.count() == 1
    assert rule.ordered_actions.count() == 1
    assert rule.ordered_conditions.first().id == c1.id

    rule.delete()  # CASCADE：条件与动作随之删除
    assert Condition.objects.filter(pk=c1.id).count() == 0
    assert Action.objects.filter(pk=a1.id).count() == 0


def test_rule_execution_log_written():
    rule = _make_rule()
    log = RuleExecutionLog.objects.create(
        rule=rule,
        rule_category=rule.category,
        trigger_type=rule.trigger_type,
        evaluate_result=EvaluateResult.MATCHED,
        execution_ms=12,
    )
    assert RuleExecutionLog.objects.count() == 1
    assert log.rule_id == rule.id
    # execution_logs 反向关系
    assert rule.execution_logs.count() == 1


# ---------------------------------------------------------------------------
# 软删字段存在（继承 FullAuditModel）
# ---------------------------------------------------------------------------

def test_soft_delete_field_exists():
    field_names = [f.name for f in Rule._meta.get_fields()]
    for col in ('deleted_at', 'created_at', 'updated_at', 'created_by', 'updated_by'):
        assert col in field_names, f'Rule 缺少软删/审计字段: {col}'

    # 软删生效：deleted_at 不为空 → _load_candidate_rules 的 deleted_at__isnull 过滤能生效
    rule = _make_rule()
    assert rule.deleted_at is None
    rule.soft_delete()
    rule.refresh_from_db()
    assert rule.deleted_at is not None
