"""Phase 3：entry_condition + time_limit 双写镜像桥单元测试（apps/rule_engine/bridge.py）。

校验 sync_entry_condition_rule_to_unified / sync_time_limit_rule_to_unified 的字段映射 /
条件重建 / 动作重建 / 幂等 / 软删传播，以及 sync_entry_condition_log_to_unified 的镜像。

不依赖现网 evaluator，仅验证镜像数据正确性（双写链路本身由 test_phase3_dispatch.py 的
信号接线测试覆盖）。
"""
import uuid

import pytest

from apps.entry_condition.models import ConditionItem, EntryConditionLog, EntryConditionRule
from apps.process.models import ProcessStageLink, RecruitmentProcess, RecruitmentStage
from apps.rule_engine.bridge import (
    ENTRY_CONDITION_LEGACY_MODEL,
    ENTRY_CONDITION_SOURCE_APP,
    TIME_LIMIT_LEGACY_MODEL,
    TIME_LIMIT_SOURCE_APP,
    sync_entry_condition_log_to_unified,
    sync_entry_condition_rule_to_unified,
    sync_time_limit_rule_to_unified,
)
from apps.rule_engine.models import (
    Action,
    Condition,
    Rule,
    RuleCategory,
    RuleExecutionLog,
    RuleStatus,
    UnifiedActionType,
    UnifiedTriggerType,
)
from apps.time_limit.models import TimeLimitRule

pytestmark = pytest.mark.django_db


def _uniq(prefix: str) -> str:
    return f'{prefix}{uuid.uuid4().hex[:10]}'


def _make_link():
    proc = RecruitmentProcess.objects.create(
        code=_uniq('W'), name=_uniq('流程'),
        current_version='V1.0', version_seq=1,
        is_latest=True, status='ENABLED',
    )
    stage = RecruitmentStage.objects.create(
        code=_uniq('P'), name=_uniq('阶段'), stage_type='SCREEN',
    )
    link = ProcessStageLink.objects.create(
        process=proc, stage=stage, order=1, is_required=True,
    )
    return proc, stage, link


def _make_entry_condition_rule(link, **kwargs):
    defaults = dict(
        link=link, process_id=link.process.id, workflow_version='V1.0',
        rule_name=_uniq('准入'), rule_seq=1, status='ENABLED',
        expression='1', reject_message='不满足条件',
    )
    defaults.update(kwargs)
    rule = EntryConditionRule.objects.create(**defaults)
    # 一条条件项（命中即放行）
    ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='CANDIDATE',
        field='GENDER', operator='EQ', value='M',
        stage_name='', stage_statuses=[],
    )
    return rule


def _make_time_limit_rule(link, **kwargs):
    defaults = dict(
        link=link, process_id=link.process.id, workflow_version='V1.0',
        rule_name=_uniq('限时'), conditions=[
            {'field': 'GENDER', 'operator': 'EQ', 'value': 'M'},
        ],
        lock_duration=5, extension_per_person=1,
        effective_scope='NEW_ONLY', priority=0, enabled=True,
    )
    defaults.update(kwargs)
    return TimeLimitRule.objects.create(**defaults)


# ============================================================
# entry_condition → STAGE_ENTERED + ALLOW
# ============================================================
def test_sync_entry_condition_maps_header_and_action():
    _, _, link = _make_link()
    rule = _make_entry_condition_rule(link)

    unified = sync_entry_condition_rule_to_unified(rule)

    assert unified.source_app == ENTRY_CONDITION_SOURCE_APP
    assert unified.legacy_id == rule.id
    assert unified.legacy_model == ENTRY_CONDITION_LEGACY_MODEL
    assert unified.name == rule.rule_name
    assert unified.category == RuleCategory.TCA
    assert unified.trigger_type == UnifiedTriggerType.STAGE_ENTERED
    assert unified.enabled is True
    assert unified.status == RuleStatus.ENABLED
    assert unified.priority_rank == rule.rule_seq
    assert unified.condition_expression == rule.expression
    assert unified.config_json['reject_message'] == rule.reject_message
    assert unified.config_json['link_id'] == str(link.id)
    assert unified.scope_json['link_id'] == str(link.id)
    # 动作：固定 1 条 ALLOW，reject_message 冗余存入 params_json
    assert unified.actions.count() == 1
    action = unified.actions.first()
    assert action.action_type == UnifiedActionType.ALLOW
    assert action.params_json['reject_message'] == rule.reject_message


def test_sync_entry_condition_rebuilds_conditions_with_item_seq():
    _, _, link = _make_link()
    rule = _make_entry_condition_rule(link)
    # 增加第二条条件项
    ConditionItem.objects.create(
        rule=rule, item_seq=2, condition_type='CANDIDATE',
        field='AGE', operator='GT', value=18,
    )
    unified = sync_entry_condition_rule_to_unified(rule)

    conds = unified.conditions.order_by('seq')
    assert conds.count() == 2
    assert [c.seq for c in conds] == [1, 2]
    assert conds[0].condition_type == 'CANDIDATE'
    assert conds[0].field == 'GENDER'
    assert conds[0].operator == 'EQ'
    assert conds[1].field == 'AGE'
    assert conds[1].operator == 'GT'


def test_sync_entry_condition_disabled_maps_to_disabled():
    _, _, link = _make_link()
    rule = _make_entry_condition_rule(link, status='DISABLED')
    unified = sync_entry_condition_rule_to_unified(rule)
    assert unified.enabled is False
    assert unified.status == RuleStatus.DISABLED


def test_sync_entry_condition_is_idempotent():
    _, _, link = _make_link()
    rule = _make_entry_condition_rule(link)
    sync_entry_condition_rule_to_unified(rule)
    sync_entry_condition_rule_to_unified(rule)
    sync_entry_condition_rule_to_unified(rule)
    assert Rule.objects.filter(
        source_app=ENTRY_CONDITION_SOURCE_APP, legacy_id=rule.id,
    ).count() == 1
    unified = Rule.objects.get(
        source_app=ENTRY_CONDITION_SOURCE_APP, legacy_id=rule.id)
    assert unified.conditions.count() == 1
    assert unified.actions.count() == 1


def test_sync_entry_condition_propagates_soft_delete():
    _, _, link = _make_link()
    rule = _make_entry_condition_rule(link)
    unified = sync_entry_condition_rule_to_unified(rule)
    assert unified.deleted_at is None

    rule.soft_delete()
    sync_entry_condition_rule_to_unified(rule)
    unified.refresh_from_db()
    assert unified.deleted_at is not None


def test_sync_entry_condition_log_to_unified():
    _, _, link = _make_link()
    rule = _make_entry_condition_rule(link)
    log = EntryConditionLog.objects.create(
        rule=rule, candidate_id='cand-ec-1', stage_id=link.stage_id,
        link_id=link.id, passed=True, reject_message='',
    )
    result = sync_entry_condition_log_to_unified(log)
    assert isinstance(result, RuleExecutionLog)
    assert result.candidate_id == 'cand-ec-1'
    assert result.trigger_type == UnifiedTriggerType.STAGE_ENTERED
    assert result.evaluate_result == 'ALLOWED'
    assert result.rule_category == RuleCategory.TCA
    assert RuleExecutionLog.objects.filter(candidate_id='cand-ec-1').count() >= 1

    # 未通过 → REJECTED
    log2 = EntryConditionLog.objects.create(
        rule=rule, candidate_id='cand-ec-2', stage_id=link.stage_id,
        link_id=link.id, passed=False, reject_message='拦下',
    )
    r2 = sync_entry_condition_log_to_unified(log2)
    assert r2.evaluate_result == 'REJECTED'


# ============================================================
# time_limit → STAGE_DWELL_TIMEOUT + LOCK
# ============================================================
def test_sync_time_limit_maps_header_and_lock_action():
    _, _, link = _make_link()
    rule = _make_time_limit_rule(link)

    unified = sync_time_limit_rule_to_unified(rule)

    assert unified.source_app == TIME_LIMIT_SOURCE_APP
    assert unified.legacy_id == rule.id
    assert unified.legacy_model == TIME_LIMIT_LEGACY_MODEL
    assert unified.name == rule.rule_name
    assert unified.category == RuleCategory.TCA
    assert unified.trigger_type == UnifiedTriggerType.STAGE_DWELL_TIMEOUT
    assert unified.enabled is True
    assert unified.status == RuleStatus.ENABLED
    assert unified.priority_rank == rule.priority
    assert unified.config_json['link_id'] == str(link.id)
    assert unified.scope_json['link_id'] == str(link.id)
    # 条件：内联 JSON 重建为 seq=1
    assert unified.conditions.count() == 1
    cond = unified.conditions.first()
    assert cond.seq == 1
    assert cond.field == 'GENDER'
    assert cond.operator == 'EQ'
    # 动作：固定 1 条 LOCK，参数搬运三层
    assert unified.actions.count() == 1
    action = unified.actions.first()
    assert action.action_type == UnifiedActionType.LOCK
    assert action.params_json['lock_duration'] == rule.lock_duration
    assert action.params_json['extension_per_person'] == rule.extension_per_person
    assert action.params_json['effective_scope'] == rule.effective_scope


def test_sync_time_limit_disabled_maps_to_disabled():
    _, _, link = _make_link()
    rule = _make_time_limit_rule(link, enabled=False)
    unified = sync_time_limit_rule_to_unified(rule)
    assert unified.enabled is False
    assert unified.status == RuleStatus.DISABLED


def test_sync_time_limit_is_idempotent():
    _, _, link = _make_link()
    rule = _make_time_limit_rule(link)
    sync_time_limit_rule_to_unified(rule)
    sync_time_limit_rule_to_unified(rule)
    assert Rule.objects.filter(
        source_app=TIME_LIMIT_SOURCE_APP, legacy_id=rule.id,
    ).count() == 1
    unified = Rule.objects.get(
        source_app=TIME_LIMIT_SOURCE_APP, legacy_id=rule.id)
    assert unified.conditions.count() == 1
    assert unified.actions.count() == 1


def test_sync_time_limit_propagates_soft_delete():
    _, _, link = _make_link()
    rule = _make_time_limit_rule(link)
    unified = sync_time_limit_rule_to_unified(rule)
    assert unified.deleted_at is None

    rule.soft_delete()
    sync_time_limit_rule_to_unified(rule)
    unified.refresh_from_db()
    assert unified.deleted_at is not None
