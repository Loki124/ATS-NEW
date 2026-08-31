"""Phase 2：check_rule_engine_consistency 管理命令测试。

校验：
- 双写正常时报告「一致」且退出码 0；
- 镜像字段漂移时报告 DRIFT 并退出码 1；
- --fix 能重新同步消除不一致。
"""
import uuid

import pytest
from apps.automation.models import AutomationRule
from apps.process.models import RecruitmentProcess, RecruitmentStage
from apps.rule_engine.management.commands.check_rule_engine_consistency import Command
from apps.rule_engine.models import Rule
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def _uniq(prefix: str) -> str:
    return f'{prefix}{uuid.uuid4().hex[:10]}'


def _make_rule():
    proc = RecruitmentProcess.objects.create(
        code=_uniq('W'), name=_uniq('流程'),
        current_version='V1.0', version_seq=1,
        is_latest=True, is_template=False, is_enabled=True,
    )
    stage = RecruitmentStage.objects.create(
        code=_uniq('P'), name=_uniq('阶段'), stage_type='SCREEN',
    )
    return AutomationRule.objects.create(
        name=_uniq('规则'), process=proc, stage=stage,
        trigger_type='STAGE_ENTERED', trigger_timing='IMMEDIATE',
        action_type='AUTO_ADVANCE', priority='P1',
        condition_json=[{'field': 'candidate_id', 'operator': 'IS_NOT_EMPTY', 'value': None}],
        scope_json={}, enabled=True,
    )


def test_consistent_when_double_write_ok(capsys):
    _make_rule()  # 保存即触发双写信号
    call_command(Command())  # 一致时不抛异常（退出码 0）
    out = capsys.readouterr().out
    assert '一致' in out


def test_detects_drift_without_fix(capsys):
    rule = _make_rule()
    # 手动制造漂移：改统一侧 name（不触发 automation 信号）
    unified = Rule.objects.get(source_app='automation', legacy_id=rule.id)
    unified.name = '被篡改的名字'
    unified.save()

    with pytest.raises(SystemExit) as exc:
        call_command(Command())
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert 'DRIFT' in out


def test_fix_resolves_drift(capsys):
    rule = _make_rule()
    unified = Rule.objects.get(source_app='automation', legacy_id=rule.id)
    unified.name = '被篡改的名字'
    unified.save()

    # 先看到不一致
    with pytest.raises(SystemExit):
        call_command(Command())

    # --fix 重新同步
    call_command(Command(), '--fix')
    out = capsys.readouterr().out
    assert '重新同步' in out

    # 再次检查应一致（不抛异常，退出码 0）
    unified.refresh_from_db()
    assert unified.name == rule.name
    call_command(Command())
    out = capsys.readouterr().out
    assert '一致' in out


def test_detects_missing_mirror(capsys):
    rule = _make_rule()
    # 删掉镜像，制造 MISSING
    Rule.objects.filter(source_app='automation', legacy_id=rule.id).delete()

    with pytest.raises(SystemExit) as exc:
        call_command(Command())
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert 'MISSING' in out
