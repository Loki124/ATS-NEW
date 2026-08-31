"""Phase 2：统一规则引擎双写镜像桥单元测试（apps/rule_engine/bridge.py）。

校验 sync_automation_rule_to_unified 的字段映射 / 条件重建 / 动作重建 / 幂等 /
软删传播，以及 sync_automation_log_to_unified 的 best-effort 镜像。

不依赖现网 automation 引擎，仅验证镜像数据正确性。
"""
import uuid

import pytest
from apps.automation.models import AutomationLog, AutomationRule
from apps.process.models import RecruitmentProcess, RecruitmentStage
from apps.rule_engine.bridge import (
    AUTOMATION_LEGACY_MODEL,
    AUTOMATION_SOURCE_APP,
    sync_automation_log_to_unified,
    sync_automation_rule_to_unified,
)
from apps.rule_engine.models import (
    Action,
    Condition,
    Rule,
    RuleCategory,
    RuleExecutionLog,
    RuleStatus,
    UnifiedActionType,
)

pytestmark = pytest.mark.django_db


def _uniq(prefix: str) -> str:
    return f'{prefix}{uuid.uuid4().hex[:10]}'


def _make_process_stage():
    proc = RecruitmentProcess.objects.create(
        code=_uniq('W'),
        name=_uniq('流程'),
        current_version='V1.0',
        version_seq=1,
        is_latest=True,
        is_template=False,
        is_enabled=True,
    )
    stage = RecruitmentStage.objects.create(
        code=_uniq('P'),
        name=_uniq('阶段'),
        stage_type='SCREEN',
    )
    return proc, stage


def _make_rule(proc, stage, **kwargs):
    defaults = dict(
        name=_uniq('规则'),
        process=proc,
        stage=stage,
        trigger_type='STAGE_ENTERED',
        trigger_timing='IMMEDIATE',
        action_type='AUTO_ADVANCE',
        priority='P1',
        condition_json=[
            {'field': 'candidate_id', 'operator': 'IS_NOT_EMPTY', 'value': None},
            {'field': 'position_id', 'operator': 'IN', 'value': ['pos1', 'pos2']},
        ],
        scope_json={'positions': ['pos1'], 'priority': ['P1']},
        enabled=True,
    )
    defaults.update(kwargs)
    return AutomationRule.objects.create(**defaults)


# ============================================================
# sync_automation_rule_to_unified
# ============================================================
def test_sync_maps_header_fields():
    proc, stage = _make_process_stage()
    rule = _make_rule(proc, stage)

    unified = sync_automation_rule_to_unified(rule)

    assert unified.source_app == AUTOMATION_SOURCE_APP
    assert unified.legacy_id == rule.id
    assert unified.legacy_model == AUTOMATION_LEGACY_MODEL
    assert unified.name == rule.name
    assert unified.category == RuleCategory.TCA
    assert unified.trigger_type == rule.trigger_type
    assert unified.trigger_timing == rule.trigger_timing
    assert unified.priority == rule.priority
    assert unified.priority_rank == 0
    assert unified.status == RuleStatus.ENABLED
    assert unified.enabled is True
    assert unified.failure_rate_threshold == rule.failure_rate_threshold
    assert unified.condition_expression == ''
    assert unified.condition_logic == rule.condition_logic
    assert unified.config_json == {
        'process_id': str(rule.process_id),
        'stage_id': str(rule.stage_id),
    }
    assert unified.scope_json == rule.scope_json


def test_sync_rebuilds_conditions():
    proc, stage = _make_process_stage()
    rule = _make_rule(proc, stage)
    unified = sync_automation_rule_to_unified(rule)

    conds = unified.conditions.order_by('seq')
    assert conds.count() == 2
    assert [c.seq for c in conds] == [1, 2]
    assert conds[0].condition_type == 'CUSTOM'
    assert conds[0].field == 'candidate_id'
    assert conds[0].operator == 'IS_NOT_EMPTY'
    assert conds[1].field == 'position_id'
    assert conds[1].operator == 'IN'
    assert conds[1].value == ['pos1', 'pos2']


def test_sync_rebuilds_action_and_params():
    proc, stage = _make_process_stage()
    target = RecruitmentStage.objects.create(
        code=_uniq('P'), name=_uniq('目标'), stage_type='INTERVIEW',
    )
    rule = _make_rule(
        proc, stage, action_type='SKIP_TO', next_stage=target,
        scope_json={'remind_to': 'CUSTOM', 'remind_message': 'hi', 'custom_user_ids': ['u1']},
    )
    unified = sync_automation_rule_to_unified(rule)

    assert unified.actions.count() == 1
    action = unified.actions.first()
    assert action.seq == 1
    assert action.action_type == UnifiedActionType.SKIP_TO
    assert action.params_json['next_stage_id'] == target.id
    assert action.params_json['skip_check'] is False
    assert action.params_json['remind_to'] == 'CUSTOM'
    assert action.params_json['remind_message'] == 'hi'
    assert action.params_json['custom_user_ids'] == ['u1']


def test_sync_is_idempotent():
    proc, stage = _make_process_stage()
    rule = _make_rule(proc, stage)
    sync_automation_rule_to_unified(rule)
    sync_automation_rule_to_unified(rule)
    sync_automation_rule_to_unified(rule)

    assert Rule.objects.filter(
        source_app=AUTOMATION_SOURCE_APP, legacy_id=rule.id,
    ).count() == 1
    unified = Rule.objects.get(source_app=AUTOMATION_SOURCE_APP, legacy_id=rule.id)
    assert unified.conditions.count() == 2
    assert unified.actions.count() == 1


def test_sync_propagates_soft_delete():
    proc, stage = _make_process_stage()
    rule = _make_rule(proc, stage)
    unified = sync_automation_rule_to_unified(rule)
    assert unified.deleted_at is None

    # 软删 legacy → 同步后统一侧也软删
    rule.soft_delete()
    sync_automation_rule_to_unified(rule)

    unified.refresh_from_db()
    assert unified.deleted_at is not None


def test_sync_disabled_rule_maps_to_disabled_status():
    proc, stage = _make_process_stage()
    rule = _make_rule(proc, stage, enabled=False)
    unified = sync_automation_rule_to_unified(rule)
    assert unified.enabled is False
    assert unified.status == RuleStatus.DISABLED


# ============================================================
# sync_automation_log_to_unified（best-effort）
# ============================================================
def test_sync_log_creates_execution_log():
    proc, stage = _make_process_stage()
    rule = _make_rule(proc, stage)
    log = AutomationLog.objects.create(
        rule=rule,
        candidate_id='cand-123',
        evaluate_result='MATCHED',
        action_taken='advanced to X',
        execution_ms=12,
    )
    result = sync_automation_log_to_unified(log)
    assert isinstance(result, RuleExecutionLog)
    assert result.candidate_id == 'cand-123'
    assert result.evaluate_result == 'MATCHED'
    assert result.rule_category == RuleCategory.TCA
    assert RuleExecutionLog.objects.filter(candidate_id='cand-123').count() >= 1


def test_sync_log_resolves_unified_rule():
    proc, stage = _make_process_stage()
    rule = _make_rule(proc, stage)
    sync_automation_rule_to_unified(rule)
    log = AutomationLog.objects.create(
        rule=rule, candidate_id='cand-9', evaluate_result='UNMATCHED',
    )
    unified = sync_automation_log_to_unified(log)
    assert unified.rule is not None
    assert unified.rule.legacy_id == rule.id
