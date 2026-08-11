"""T10：历史"假升级"审计脚本回归（规格 §1.4）。

被测对象是 ``apps/application/management/commands/audit_fake_upgrades.py``。

为什么需要这个脚本
==================
T3 修复之前，升版本实现**从不改写 ``application.process``**——只写了一条
``UPGRADE_VERSION`` 审计，候选人实际仍跑在旧流程版本上。所以历史上每一条
``UPGRADE_VERSION`` 都可能是"审计说升了、数据没升"的假升级。

脚本只诊断不修复：当时 ``is_latest`` 概念尚不存在，老行的 ``current_version``
又被 V2 的版本号拼接 bug 污染（``'1.0'`` → ``'1.0+1'`` → …），
"这条记录当年应该升到哪一行"无从反推，自动改写历史数据危险且不可验证。

判据
====
T3 之后的实现必定在 detail 里写入 ``stage_remapped`` 键（由 ``resolve_stage_mapping``
产出）；修复前的实现不产生该键。于是：含该键 = LIKELY_REAL，缺 = SUSPECT_FAKE，
detail 非 dict / 为 None = MALFORMED_DETAIL（单独一类，不与前两类混淆）。

dev 库实测 ``ApplicationHistory`` 为 **0 行**，脚本在真实数据上是空跑必绿——
本文件所有样本因此全部自建，否则等于没测。

变异自证（靶心）
================
把命令模块里的 ``_REAL_UPGRADE_MARKER = 'stage_remapped'`` 改成任何别的键名，
:func:`test_command_counts_all_three_verdicts` 与
:func:`test_default_run_skips_likely_real` 应当立刻变红（分类整体反转）。
"""
from __future__ import annotations

import csv
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.application.management.commands.audit_fake_upgrades import (
    VERDICT_MALFORMED,
    VERDICT_REAL,
    VERDICT_SUSPECT,
    classify,
)
from apps.application.models import (
    Application,
    ApplicationHistory,
    ApplicationState,
)
from apps.candidate.models import Candidate
from apps.position.models import Position, PositionState
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageType,
)

pytestmark = pytest.mark.django_db

COMMAND = 'audit_fake_upgrades'


# ============================================================
# Seed 工具（dev 库 ApplicationHistory=0，一切自建）
# ============================================================
def make_stage(key: str) -> RecruitmentStage:
    stage, _ = RecruitmentStage.objects.get_or_create(
        code=f'AUD{key}',
        defaults={'name': f'审计测试阶段-{key}', 'stage_type': StageType.SCREEN},
    )
    return stage


def make_process(code: str, seq: int) -> RecruitmentProcess:
    return RecruitmentProcess.objects.create(
        code=code,
        name=f'{code} 审计测试流程 V{seq}',
        current_version=f'V{seq}.0',
        version_seq=seq,
        is_latest=(seq == 1),
        status='ENABLED',
    )


@pytest.fixture
def audit_position(db, department, super_user) -> Position:
    process = make_process('AUDPOS', 1)
    ProcessStageLink.objects.create(
        process=process, stage=make_stage('POS'), order=1, is_required=True,
    )
    pos = Position.objects.create(
        code='P_AUDIT_FAKE',
        title='假升级审计职位',
        description='T10 回归用',
        department=department,
        hiring_manager=super_user,
        owner=super_user,
        headcount=3,
        state=PositionState.DRAFT,
        process=process,
    )
    pos.submit_publish(); pos.save()
    pos.publish(); pos.save()
    pos.start_recruiting(); pos.save()
    return pos


def make_application(code: str, position: Position, phone: str) -> Application:
    process = position.process
    link = ProcessStageLink.objects.filter(process=process).first()
    candidate = Candidate.objects.create(name=f'审计候选人-{code}', phone=phone)
    return Application.objects.create(
        code=code,
        candidate=candidate,
        position=position,
        process=process,
        workflow_version=process.current_version,
        state=ApplicationState.ACTIVE,
        current_link=link,
        current_stage=link.stage,
        last_advanced_at=timezone.now(),
    )


def make_history(application: Application, detail, *, action=None) -> ApplicationHistory:
    return ApplicationHistory.objects.create(
        application=application,
        action=action or ApplicationHistory.ActionType.UPGRADE_VERSION,
        detail=detail,
    )


def run_command(*args, **kwargs) -> str:
    out = StringIO()
    call_command(COMMAND, *args, stdout=out, **kwargs)
    return out.getvalue()


def parse_csv_rows(output: str) -> list[dict]:
    """从命令 stdout 里切出 CSV 段（统计区之前的部分）。"""
    lines = output.splitlines()
    body = []
    for line in lines:
        if line.startswith('=' * 10):
            break
        if line.strip():
            body.append(line)
    if not body:
        return []
    return list(csv.DictReader(body))


# ============================================================
# 1. 判据本身（单元级，覆盖不便落库的形态）
# ============================================================
def test_classify_missing_marker_is_suspect() -> None:
    verdict, reason = classify({'from_version': '1.0', 'to_version': '2.0'})
    assert verdict == VERDICT_SUSPECT
    assert 'stage_remapped' in reason


def test_classify_with_marker_is_likely_real() -> None:
    verdict, _ = classify({'stage_remapped': False, 'from_version': 'V1.0'})
    assert verdict == VERDICT_REAL, 'stage_remapped 为 False 也算 T3 后写入——看的是键在不在'


def test_classify_none_detail_is_malformed() -> None:
    verdict, reason = classify(None)
    assert verdict == VERDICT_MALFORMED
    assert 'None' in reason


@pytest.mark.parametrize('bad', ['legacy string', ['a', 'b'], 42])
def test_classify_non_dict_detail_is_malformed(bad) -> None:
    verdict, reason = classify(bad)
    assert verdict == VERDICT_MALFORMED
    assert type(bad).__name__ in reason


# ============================================================
# 2. 端到端：三类判定同时出现时的计数与导出
# ============================================================
@pytest.fixture
def mixed_histories(audit_position):
    """一条真升级 + 两条假升级 + 一条形态异常。"""
    app = make_application('APP-AUD-01', audit_position, '13950000001')
    real = make_history(app, {
        'stage_remapped': True, 'from_version': 'V1.0', 'to_version': 'V2.0',
    })
    fake1 = make_history(app, {'from_version': '1.0', 'to_version': '1.0+1'})
    fake2 = make_history(app, {})
    malformed = make_history(app, ['legacy', 'list', 'payload'])
    # 混入一条非 UPGRADE_VERSION 记录，脚本不得把它算进来
    noise = make_history(app, {'note': '推进'}, action=ApplicationHistory.ActionType.ADVANCED)
    return {
        'app': app, 'real': real, 'fake1': fake1,
        'fake2': fake2, 'malformed': malformed, 'noise': noise,
    }


def test_command_counts_all_three_verdicts(mixed_histories) -> None:
    output = run_command()

    assert 'UPGRADE_VERSION 记录总数：4' in output, \
        'ADVANCED 记录不得被计入（脚本只审计 UPGRADE_VERSION）'
    assert '疑似假升级 SUSPECT_FAKE     ：2' in output
    assert '可信记录   LIKELY_REAL      ：1' in output
    assert '形态异常   MALFORMED_DETAIL ：1' in output


def test_default_run_skips_likely_real(mixed_histories) -> None:
    rows = parse_csv_rows(run_command())

    verdicts = sorted(r['verdict'] for r in rows)
    assert verdicts == [VERDICT_MALFORMED, VERDICT_SUSPECT, VERDICT_SUSPECT], \
        '默认只导出需要人工处理的记录，LIKELY_REAL 不进清单'
    assert mixed_histories['real'].id not in {r['history_id'] for r in rows}


def test_all_flag_includes_likely_real(mixed_histories) -> None:
    rows = parse_csv_rows(run_command('--all'))

    assert len(rows) == 4
    assert mixed_histories['real'].id in {r['history_id'] for r in rows}


def test_csv_carries_traceable_columns(mixed_histories) -> None:
    rows = parse_csv_rows(run_command())
    suspect = next(r for r in rows if r['history_id'] == mixed_histories['fake1'].id)

    app = mixed_histories['app']
    assert suspect['application_id'] == app.id
    assert suspect['application_code'] == 'APP-AUD-01'
    assert suspect['current_process_id'] == app.process_id, \
        '需带出当前 process_id，人工审计才能判断"数据到底升没升"'
    assert suspect['from_version'] == '1.0'
    assert suspect['to_version'] == '1.0+1'
    assert suspect['created_at'], 'created_at 不得为空'


def test_malformed_detail_does_not_crash(mixed_histories) -> None:
    """detail 是 list 时，取 from_version/to_version 不能抛，留空即可。"""
    rows = parse_csv_rows(run_command())
    malformed = next(r for r in rows if r['verdict'] == VERDICT_MALFORMED)

    assert malformed['from_version'] == ''
    assert malformed['to_version'] == ''
    assert 'legacy' in malformed['detail_repr'], '原始 detail 需留痕供人工判断'


def test_warning_shown_when_suspects_exist(mixed_histories) -> None:
    output = run_command()
    assert '请人工审计，勿批量改写' in output
    assert '只读诊断' in output


def test_clean_database_reports_zero(audit_position) -> None:
    """没有任何 UPGRADE_VERSION 记录时不得崩，且不能虚报。"""
    output = run_command()
    assert 'UPGRADE_VERSION 记录总数：0' in output
    assert '疑似假升级 SUSPECT_FAKE     ：0' in output
    assert '请人工审计' not in output, '没有可疑记录时不应吓唬人'


# ============================================================
# 3. 参数
# ============================================================
def test_since_filters_older_records(mixed_histories) -> None:
    old = mixed_histories['fake1']
    ApplicationHistory.objects.filter(pk=old.pk).update(
        created_at=timezone.make_aware(
            timezone.datetime(2020, 1, 1), timezone.get_current_timezone(),
        ),
    )

    output = run_command('--since', '2021-01-01')

    assert 'UPGRADE_VERSION 记录总数：3' in output, '2020 年那条应被 --since 排除'
    assert '疑似假升级 SUSPECT_FAKE     ：1' in output


def test_invalid_since_raises_command_error() -> None:
    with pytest.raises(CommandError) as exc:
        run_command('--since', '2026/01/01')
    assert 'YYYY-MM-DD' in str(exc.value), '错误信息需给出正确格式，而不是让人猜'


def test_output_file_is_written(mixed_histories, tmp_path) -> None:
    target = tmp_path / 'fake_upgrades.csv'

    output = run_command('--output', str(target))

    assert target.exists()
    assert f'CSV 已写入：{target}' in output
    with open(target, encoding='utf-8-sig', newline='') as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 3
    assert {r['verdict'] for r in rows} == {VERDICT_SUSPECT, VERDICT_MALFORMED}


# ============================================================
# 4. 只读性——规格明确要求"不自动改写"
# ============================================================
def test_command_mutates_nothing(mixed_histories) -> None:
    """跑一遍脚本，历史记录与申请数据必须逐字节不变。"""
    def snapshot():
        histories = list(
            ApplicationHistory.objects.order_by('id')
            .values('id', 'action', 'detail', 'application_id',
                    'from_stage_id', 'to_stage_id', 'created_at')
        )
        apps = list(
            Application.objects.order_by('id')
            .values('id', 'process_id', 'workflow_version',
                    'current_link_id', 'current_stage_id', 'state')
        )
        return histories, apps

    before = snapshot()
    run_command('--all')
    after = snapshot()

    assert before == after, '审计脚本必须是纯只读的，不得产生任何写副作用'
    assert ApplicationHistory.objects.count() == 5, \
        '脚本自身也不能留下审计记录（那会污染下一轮审计）'
