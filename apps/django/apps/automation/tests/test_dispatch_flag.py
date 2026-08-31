"""Phase 2：automation 执行委托开关（RULE_ENGINE_DISPATCH）路由测试。

核心约束：RULE_ENGINE_DISPATCH=False（默认）时，AutomationEngine.run() 走原
automation 引擎路径，绝不变更现网行为；=True 时改走统一引擎 RuleEngine 派发，
结果翻译回 automation 形态、调用方无感。
"""
import uuid
from unittest.mock import Mock, patch

import pytest
from apps.automation.models import AutomationRule
from apps.automation.services import AutomationEngine, TriggerContext
from apps.process.models import RecruitmentProcess, RecruitmentStage

pytestmark = pytest.mark.django_db


def _uniq(prefix: str) -> str:
    return f'{prefix}{uuid.uuid4().hex[:10]}'


def _make_process_stage():
    proc = RecruitmentProcess.objects.create(
        code=_uniq('W'), name=_uniq('流程'),
        current_version='V1.0', version_seq=1,
        is_latest=True, is_template=False, is_enabled=True,
    )
    stage = RecruitmentStage.objects.create(
        code=_uniq('P'), name=_uniq('阶段'), stage_type='SCREEN',
    )
    return proc, stage


def _make_rule(proc, stage, trigger_type='STAGE_ENTERED'):
    return AutomationRule.objects.create(
        name=_uniq('规则'), process=proc, stage=stage,
        trigger_type=trigger_type, trigger_timing='IMMEDIATE',
        action_type='AUTO_ADVANCE', priority='P1',
        condition_json=[], scope_json={}, enabled=True,
    )


class _FakeAction:
    action_type = 'AUTO_ADVANCE'
    success = True
    message = 'ok'


class _FakeUnifiedResult:
    def __init__(self, rule_id):
        self.rule_id = rule_id
        self.matched = True
        self.action_results = [_FakeAction()]
        self.log_id = 'log-1'


def test_dispatch_flag_default_false():
    from django.conf import settings
    assert getattr(settings, 'RULE_ENGINE_DISPATCH', False) is False


def test_run_routes_to_unified_engine_when_dispatch_on():
    proc, stage = _make_process_stage()
    rule = _make_rule(proc, stage)
    fake_unified = _FakeUnifiedResult('u-rule-x')

    with patch('apps.rule_engine.services.RuleEngine') as FakeEngine:
        FakeEngine.return_value.dispatch.return_value = [fake_unified]
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr('django.conf.settings.RULE_ENGINE_DISPATCH', True)
            results = AutomationEngine(TriggerContext(
                trigger_type='STAGE_ENTERED', candidate_id='c1',
                application_id='a1', stage_id=stage.id,
            )).run()

    # 统一引擎被调用，且仅处理 automation 家族
    FakeEngine.return_value.dispatch.assert_called_once()
    ctx_arg, kw = FakeEngine.return_value.dispatch.call_args
    assert kw.get('source_app') == 'automation'
    # 结果翻译回 automation 形态（rule_id 还原为 legacy id 'u-rule-x'）
    assert len(results) == 1
    assert results[0].rule_id == 'u-rule-x'
    assert results[0].matched is True


def test_run_keeps_legacy_path_when_dispatch_off():
    proc, stage = _make_process_stage()
    rule = _make_rule(proc, stage)

    with patch('apps.rule_engine.services.RuleEngine') as FakeEngine:
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr('django.conf.settings.RULE_ENGINE_DISPATCH', False)
            results = AutomationEngine(TriggerContext(
                trigger_type='STAGE_ENTERED', candidate_id='c1',
                stage_id=stage.id,
            )).run()

    # 默认路径：不调用统一引擎（现网行为不变）
    FakeEngine.return_value.dispatch.assert_not_called()
    # legacy 路径对无 application_id 的 AUTO_ADVANCE 仅记日志、不抛错
    assert isinstance(results, list)
