"""Phase 3：check_rule_engine_consistency 管理命令对 entry_condition / time_limit 的覆盖测试。

校验：
- 双写正常时报告「一致」且退出码 0；
- 镜像字段漂移时报告 DRIFT 并退出码 1；
- 缺镜像时报告 MISSING；
- legacy 已软删但统一侧仍 active 时报告 NOT_SOFT_DELETED；
- --fix 能重新同步消除不一致。

依赖双写信号（RULE_ENGINE_DOUBLE_WRITE 默认 True）在保存 legacy 规则时自动镜像；
本文件显式校验信号接线与命令行为。
"""
import uuid

import pytest
from django.core.management import call_command

from apps.entry_condition.models import ConditionItem, EntryConditionRule
from apps.process.models import ProcessStageLink, RecruitmentProcess, RecruitmentStage
from apps.rule_engine.management.commands.check_rule_engine_consistency import Command
from apps.rule_engine.models import Rule
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
    return ProcessStageLink.objects.create(process=proc, stage=stage, order=1, is_required=True)


def _make_entry_condition_rule(link):
    rule = EntryConditionRule.objects.create(
        link=link, process_id=link.process.id, workflow_version='V1.0',
        rule_name=_uniq('准入'), rule_seq=1, status='ENABLED',
        expression='1', reject_message='no',
    )
    ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='CANDIDATE',
        field='GENDER', operator='EQ', value='M',
    )
    return rule


def _make_time_limit_rule(link):
    return TimeLimitRule.objects.create(
        link=link, process_id=link.process.id, workflow_version='V1.0',
        rule_name=_uniq('限时'), conditions=[{'field': 'GENDER', 'operator': 'EQ', 'value': 'M'}],
        lock_duration=5, extension_per_person=1,
        effective_scope='NEW_ONLY', priority=0, enabled=True,
    )


# ============================================================
# entry_condition
# ============================================================
def test_entry_condition_consistent_when_double_write_ok(capsys):
    link = _make_link()
    _make_entry_condition_rule(link)  # 保存即触发双写信号
    call_command(Command())
    out = capsys.readouterr().out
    assert '一致' in out


def test_entry_condition_detects_drift(capsys):
    link = _make_link()
    rule = _make_entry_condition_rule(link)
    unified = Rule.objects.get(source_app='entry_condition', legacy_id=rule.id)
    unified.name = '被篡改'
    unified.save()

    with pytest.raises(SystemExit) as exc:
        call_command(Command())
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert 'DRIFT' in out
    assert '[entry_condition]' in out


def test_entry_condition_fix_resolves_drift(capsys):
    link = _make_link()
    rule = _make_entry_condition_rule(link)
    unified = Rule.objects.get(source_app='entry_condition', legacy_id=rule.id)
    unified.name = '被篡改'
    unified.save()

    with pytest.raises(SystemExit):
        call_command(Command())

    call_command(Command(), '--fix')
    out = capsys.readouterr().out
    assert '重新同步' in out

    unified.refresh_from_db()
    assert unified.name == rule.rule_name
    call_command(Command())
    assert '一致' in capsys.readouterr().out


def test_entry_condition_detects_missing(capsys):
    link = _make_link()
    rule = _make_entry_condition_rule(link)
    Rule.objects.filter(source_app='entry_condition', legacy_id=rule.id).delete()

    with pytest.raises(SystemExit) as exc:
        call_command(Command())
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert 'MISSING' in out


def test_entry_condition_detects_not_soft_deleted(capsys):
    link = _make_link()
    rule = _make_entry_condition_rule(link)
    rule.soft_delete()  # legacy 软删 → 信号应把统一侧也软删

    # 强制把统一侧恢复为 active，制造不一致
    unified = Rule.objects.get(source_app='entry_condition', legacy_id=rule.id)
    unified.deleted_at = None
    unified.save()

    with pytest.raises(SystemExit) as exc:
        call_command(Command())
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert 'NOT_SOFT_DELETED' in out

    call_command(Command(), '--fix')
    unified.refresh_from_db()
    assert unified.deleted_at is not None


# ============================================================
# time_limit
# ============================================================
def test_time_limit_consistent_when_double_write_ok(capsys):
    link = _make_link()
    _make_time_limit_rule(link)
    call_command(Command())
    out = capsys.readouterr().out
    assert '一致' in out


def test_time_limit_detects_drift(capsys):
    link = _make_link()
    rule = _make_time_limit_rule(link)
    unified = Rule.objects.get(source_app='time_limit', legacy_id=rule.id)
    unified.name = '被篡改'
    unified.save()

    with pytest.raises(SystemExit) as exc:
        call_command(Command())
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert 'DRIFT' in out
    assert '[time_limit]' in out


def test_time_limit_fix_resolves_drift(capsys):
    link = _make_link()
    rule = _make_time_limit_rule(link)
    unified = Rule.objects.get(source_app='time_limit', legacy_id=rule.id)
    unified.name = '被篡改'
    unified.save()

    with pytest.raises(SystemExit):
        call_command(Command())

    call_command(Command(), '--fix')
    out = capsys.readouterr().out
    assert '重新同步' in out

    unified.refresh_from_db()
    assert unified.name == rule.rule_name
    call_command(Command())
    assert '一致' in capsys.readouterr().out


def test_time_limit_detects_missing(capsys):
    link = _make_link()
    rule = _make_time_limit_rule(link)
    Rule.objects.filter(source_app='time_limit', legacy_id=rule.id).delete()

    with pytest.raises(SystemExit) as exc:
        call_command(Command())
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert 'MISSING' in out


def test_time_limit_detects_not_soft_deleted(capsys):
    link = _make_link()
    rule = _make_time_limit_rule(link)
    rule.soft_delete()

    unified = Rule.objects.get(source_app='time_limit', legacy_id=rule.id)
    unified.deleted_at = None
    unified.save()

    with pytest.raises(SystemExit) as exc:
        call_command(Command())
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert 'NOT_SOFT_DELETED' in out

    call_command(Command(), '--fix')
    unified.refresh_from_db()
    assert unified.deleted_at is not None
