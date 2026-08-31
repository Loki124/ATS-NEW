"""Phase 3：双写信号接线 + evaluator 委托（RULE_ENGINE_DISPATCH）接线测试。

覆盖：
- entry_condition / time_limit 保存时信号自动镜像到统一表（best-effort 双写接线）；
- 条件项变更触发父规则重同步；
- 软删通过信号传播到统一侧；
- RULE_ENGINE_DISPATCH=True 时，legacy evaluator 委托统一引擎派发并翻译回 legacy 形态；
- 委托路径与 legacy 路径结果一致（默认关 → 行为零变化）。
"""
import uuid

import pytest
from django.test import override_settings

from apps.candidate.models import Candidate
from apps.entry_condition.models import ConditionItem, EntryConditionRule
from apps.entry_condition.services import EntryConditionEvaluator, evaluate_stage_entry
from apps.process.models import ProcessStageLink, RecruitmentProcess, RecruitmentStage
from apps.rule_engine.bridge import (
    sync_entry_condition_rule_to_unified,
    sync_time_limit_rule_to_unified,
)
from apps.rule_engine.models import Rule, RuleExecutionLog
from apps.rule_engine.services import action_registry
from apps.time_limit.models import TimeLimitRule
from apps.time_limit.services import calc_time_limit

pytestmark = pytest.mark.django_db


@pytest.fixture
def real_executors():
    """临时从全局 action_registry 移除 test_engine 的 catch-all 测试执行器，确保真实
    ALLOW/LOCK 执行器在委托派发时被命中；测试结束后恢复原注册表（避免影响其它模块）。"""
    from apps.rule_engine.services import action_registry
    from apps.rule_engine.integrations.entry_condition_executors import (
        register_entry_condition_executors,
    )
    from apps.rule_engine.integrations.time_limit_executors import (
        register_time_limit_executors,
    )
    register_entry_condition_executors()
    register_time_limit_executors()
    saved = list(action_registry._executors)
    action_registry._executors = [
        e for e in saved
        if e.__class__.__module__ != 'apps.rule_engine.tests.test_engine'
    ]
    yield
    action_registry._executors = saved


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
    return ProcessStageLink.objects.create(process=proc, stage=stage, order=1, is_required=True)


def _make_candidate(gender='M'):
    return Candidate.objects.create(name=_uniq('候选人'), phone=f'13{uuid.uuid4().hex[:9]}', gender=gender)


def _make_entry_condition_rule(link, gender_value='M'):
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process.id, workflow_version='V1.0',
        rule_name=_uniq('准入'), rule_seq=1, status='ENABLED',
        expression='1', reject_message='未满足条件',
    )
    ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='CANDIDATE',
        field='GENDER', operator='EQ', value=gender_value,
    )
    return rule


def _make_time_limit_rule(link, gender_value='M'):
    return TimeLimitRule.objects.create(
        link=link, process_id=link.process.id, workflow_version='V1.0',
        rule_name=_uniq('限时'), conditions=[
            {'field': 'GENDER', 'operator': 'EQ', 'value': gender_value},
        ],
        lock_duration=5, extension_per_person=2,
        effective_scope='NEW_ONLY', priority=0, enabled=True,
    )


# ============================================================
# 信号接线（双写）
# ============================================================
def test_entry_condition_signal_mirrors_on_save():
    link = _make_link()
    rule = _make_entry_condition_rule(link)
    unified = Rule.objects.filter(source_app='entry_condition', legacy_id=rule.id).first()
    assert unified is not None
    assert unified.trigger_type == 'STAGE_ENTERED'
    assert unified.actions.filter(action_type='ALLOW').exists()
    assert unified.conditions.count() == 1


def test_entry_condition_item_change_resyncs_parent():
    link = _make_link()
    rule = _make_entry_condition_rule(link)
    # 新增一条条件项 → 应触发父规则重同步，统一侧条件数变为 2
    ConditionItem.objects.create(
        rule=rule, item_seq=2, condition_type='CANDIDATE',
        field='AGE', operator='GT', value=18,
    )
    unified = Rule.objects.get(source_app='entry_condition', legacy_id=rule.id)
    assert unified.conditions.count() == 2


def test_entry_condition_soft_delete_propagates_via_signal():
    link = _make_link()
    rule = _make_entry_condition_rule(link)
    unified = Rule.objects.get(source_app='entry_condition', legacy_id=rule.id)
    assert unified.deleted_at is None
    rule.soft_delete()
    unified.refresh_from_db()
    assert unified.deleted_at is not None


def test_time_limit_signal_mirrors_on_save():
    link = _make_link()
    rule = _make_time_limit_rule(link)
    unified = Rule.objects.filter(source_app='time_limit', legacy_id=rule.id).first()
    assert unified is not None
    assert unified.trigger_type == 'STAGE_DWELL_TIMEOUT'
    assert unified.actions.filter(action_type='LOCK').exists()
    assert unified.conditions.count() == 1


def test_time_limit_soft_delete_propagates_via_signal():
    link = _make_link()
    rule = _make_time_limit_rule(link)
    unified = Rule.objects.get(source_app='time_limit', legacy_id=rule.id)
    assert unified.deleted_at is None
    rule.soft_delete()
    unified.refresh_from_db()
    assert unified.deleted_at is not None


# ============================================================
# evaluator 委托（RULE_ENGINE_DISPATCH）
# ============================================================
@override_settings(RULE_ENGINE_DISPATCH=True)
def test_entry_condition_dispatch_allows_when_matched(real_executors):
    link = _make_link()
    rule = _make_entry_condition_rule(link, gender_value='M')
    sync_entry_condition_rule_to_unified(rule)  # 确保镜像存在
    candidate = _make_candidate(gender='M')

    result = EntryConditionEvaluator(link, candidate).evaluate(save_log=False)
    assert result.overall_passed is True
    assert result.matched_rule_seq == rule.rule_seq
    # 委托路径应写入统一执行日志（ALLOWED）
    assert RuleExecutionLog.objects.filter(
        trigger_type='STAGE_ENTERED', candidate_id=candidate.id,
    ).exists()


@override_settings(RULE_ENGINE_DISPATCH=True)
def test_entry_condition_dispatch_rejects_when_unmatched(real_executors):
    link = _make_link()
    rule = _make_entry_condition_rule(link, gender_value='M')
    sync_entry_condition_rule_to_unified(rule)
    candidate = _make_candidate(gender='F')  # 不匹配

    result = EntryConditionEvaluator(link, candidate).evaluate(save_log=False)
    assert result.overall_passed is False
    assert result.reject_message == rule.reject_message


def test_entry_condition_dispatch_off_preserves_legacy_behavior():
    """默认关：委托路径不触发，结果仍由 legacy evaluator 得出（行为零变化）。"""
    link = _make_link()
    rule = _make_entry_condition_rule(link, gender_value='M')
    sync_entry_condition_rule_to_unified(rule)
    candidate = _make_candidate(gender='M')

    # 显式确认 DISPATCH 为关（默认）
    from django.conf import settings
    assert settings.RULE_ENGINE_DISPATCH is False
    result = EntryConditionEvaluator(link, candidate).evaluate(save_log=False)
    assert result.overall_passed is True
    # 关时不应写入统一执行日志（委托路径未走）
    assert not RuleExecutionLog.objects.filter(
        trigger_type='STAGE_ENTERED', candidate_id=candidate.id,
    ).exists()


@override_settings(RULE_ENGINE_DISPATCH=True)
def test_time_limit_dispatch_returns_matched_calc(real_executors):
    link = _make_link()
    rule = _make_time_limit_rule(link, gender_value='M')
    sync_time_limit_rule_to_unified(rule)
    candidate = _make_candidate(gender='M')

    res = calc_time_limit(link, candidate, interviewer_count=1)
    assert res.matched is True
    assert res.rule_id == rule.id
    # lock_duration(5) + extension_per_person(2) * (1-1) = 5
    assert res.total_lock_days == 5


@override_settings(RULE_ENGINE_DISPATCH=True)
def test_time_limit_dispatch_returns_unmatched_default(real_executors):
    link = _make_link()
    rule = _make_time_limit_rule(link, gender_value='M')
    sync_time_limit_rule_to_unified(rule)
    candidate = _make_candidate(gender='F')  # 不匹配

    res = calc_time_limit(link, candidate, interviewer_count=1)
    assert res.matched is False
    assert res.total_lock_days == 0


def test_phase3_executors_registered(real_executors):
    """ALLOW / LOCK 执行器应已注册到全局 action_registry。"""
    from apps.rule_engine.integrations.entry_condition_executors import (
        register_entry_condition_executors,
    )
    from apps.rule_engine.integrations.time_limit_executors import (
        register_time_limit_executors,
    )
    from apps.rule_engine.models import UnifiedActionType

    register_entry_condition_executors()
    register_time_limit_executors()

    # 通过 registry 派发一个虚拟 action 验证执行器可命中
    from apps.rule_engine.models import Action
    from apps.rule_engine.services import EvaluationContext

    ctx = EvaluationContext(trigger_type='STAGE_ENTERED', candidate_id='x')
    allow_action = Action(action_type=UnifiedActionType.ALLOW, params_json={})
    r = action_registry.dispatch(ctx, allow_action, rule=None)
    assert r.success is True
    assert r.action_type == UnifiedActionType.ALLOW
