"""阶段自动跳过 / 自动归档 集成测试（P1-1）。

验证「阶段进入时」(advance_application_to_next_stage 生产入口) 触发 skip/archive：
- skip_rules 命中 → 该阶段记录置 SKIPPED，候选人自动进入下一阶段（级联）；
- archive_rules 命中 → 整申请置归档终态（TIMEOUT）；
- 无规则 → 无副作用；
- 流程无后续阶段 → 停在最后一阶段（当前记录 SKIPPED）。

dev 库 Application=0，一切自建（参考 test_change_process.py 的 seed 工具）。
"""
from __future__ import annotations

import pytest
from django.utils import timezone

from apps.application.models import (
    Application,
    ApplicationHistory,
    ApplicationState,
    ApplicationStageRecord,
)
from apps.application.services import ApplicationService
from apps.candidate.models import Candidate
from apps.metrics.models import AtomicMetric, MetricTemplate
from apps.position.models import Position, PositionState
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageRule,
    StageType,
)
from nanoid import generate as nanoid_generate

pytestmark = pytest.mark.django_db


# ============================================================
# Seed 工具
# ============================================================
def _cid() -> str:
    return nanoid_generate(size=21)


def make_stage(key: str) -> RecruitmentStage:
    stage, _ = RecruitmentStage.objects.get_or_create(
        code=f'SKA{key}',
        defaults={'name': f'跳过归档集成阶段-{key}', 'stage_type': StageType.SCREEN},
    )
    return stage


def make_process(code: str) -> RecruitmentProcess:
    return RecruitmentProcess.objects.create(
        code=code, name=f'{code} 跳过归档集成流程',
        current_version='V1.0', version_seq=1, is_latest=True,
    )


def add_link(process: RecruitmentProcess, stage: RecruitmentStage, order: int,
             is_required: bool = True) -> ProcessStageLink:
    return ProcessStageLink.objects.create(
        process=process, stage=stage, order=order, is_required=is_required,
    )


def make_position(code: str, department, super_user) -> Position:
    holder = make_process('SKAPOS')
    add_link(holder, make_stage('POS'), 1)
    pos = Position.objects.create(
        code=code,
        title='跳过归档集成职位',
        description='P1-1 集成用',
        department=department,
        hiring_manager=super_user,
        owner=super_user,
        headcount=5,
        state=PositionState.DRAFT,
        process=holder,
    )
    pos.submit_publish()
    pos.save()
    pos.publish()
    pos.save()
    return pos


def make_application(code: str, process: RecruitmentProcess, link: ProcessStageLink,
                    position: Position, *, phone: str) -> Application:
    candidate = Candidate.objects.create(name=f'候选人-{code}', phone=phone, age=40)
    app = Application.objects.create(
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
    # 初始阶段记录（advance 要求当前 link 存在 stage_record）
    ApplicationStageRecord.objects.create(
        application=app,
        link=link,
        stage=link.stage,
        state=ApplicationStageRecord.StageState.PENDING,
        entered_at=timezone.now(),
    )
    return app


def make_metric_template() -> MetricTemplate:
    metric = AtomicMetric.objects.create(
        name=f'am_age_{_cid()}', source_path='candidate.age', data_type='number',
    )
    return MetricTemplate.objects.create(
        name=f'age_tpl_{_cid()}', atomic_metric=metric, operators=['GT', 'LT', 'EQ'],
    )


def attach_skip_rule(link: ProcessStageLink, tpl: MetricTemplate, rule_id: str = 'sk1') -> None:
    StageRule.objects.create(
        link=link,
        skip_rules=[{
            'id': rule_id, 'name': f'{rule_id}-name', 'enabled': True, 'expression': '1',
            'items': [
                {
                    'id': f'{rule_id}_i', 'item_seq': 1, 'condition_type': 'METRIC',
                    'field': str(tpl.id), 'operator': 'GT', 'value': '0',
                },
            ],
        }],
    )


def attach_archive_rule(link: ProcessStageLink, tpl: MetricTemplate, rule_id: str = 'ar1') -> None:
    StageRule.objects.create(
        link=link,
        archive_rules=[{
            'id': rule_id, 'name': f'{rule_id}-name', 'enabled': True, 'expression': '1',
            'items': [
                {
                    'id': f'{rule_id}_i', 'item_seq': 1, 'condition_type': 'METRIC',
                    'field': str(tpl.id), 'operator': 'GT', 'value': '0',
                },
            ],
        }],
    )


def _reload(application: Application) -> Application:
    """重新查库（protected FSMField 不可 refresh_from_db）。"""
    return Application.objects.get(pk=application.pk)


def _latest_record(application: Application, link: ProcessStageLink) -> ApplicationStageRecord:
    return application.stage_records.filter(link=link, deleted_at__isnull=True).order_by('-entered_at').first()


# ============================================================
# 用例
# ============================================================
@pytest.mark.django_db
def test_advance_skip_cascade(department, super_user):
    """S1→S2（命中 skip）→ 级联进入 S3，S2 记录 SKIPPED，S3 记录 PENDING。"""
    tpl = make_metric_template()
    process = make_process('WSKIP1')
    s1, s2, s3 = make_stage('S1'), make_stage('S2'), make_stage('S3')
    l1, l2, l3 = add_link(process, s1, 0), add_link(process, s2, 1), add_link(process, s3, 2)
    attach_skip_rule(l2, tpl)

    pos = make_position('P_SKIP_ARCHIVE', department, super_user)
    app = make_application('ASKIP1', process, l1, pos, phone='13900000101')

    ApplicationService.advance_application_to_next_stage(app)

    app = _reload(app)
    assert app.current_stage_id == s3.id
    assert _latest_record(app, l1).state == ApplicationStageRecord.StageState.PASSED
    assert _latest_record(app, l2).state == ApplicationStageRecord.StageState.SKIPPED
    assert _latest_record(app, l3).state == ApplicationStageRecord.StageState.PENDING
    assert app.state == ApplicationState.ACTIVE


@pytest.mark.django_db
def test_advance_archive_terminal(department, super_user):
    """S1→S2（命中 archive）→ 整申请置归档终态 TIMEOUT，S2 记录 ARCHIVED。"""
    tpl = make_metric_template()
    process = make_process('WARCH1')
    s1, s2 = make_stage('A1'), make_stage('A2')
    l1, l2 = add_link(process, s1, 0), add_link(process, s2, 1)
    attach_archive_rule(l2, tpl)

    pos = make_position('P_SKIP_ARCHIVE', department, super_user)
    app = make_application('AARCH1', process, l1, pos, phone='13900000102')

    ApplicationService.advance_application_to_next_stage(app)

    app = _reload(app)
    assert app.state == ApplicationState.TIMEOUT
    assert _latest_record(app, l2).state == ApplicationStageRecord.StageState.ARCHIVED
    # 审计：AUTO_ARCHIVE_RULE
    assert ApplicationHistory.objects.filter(
        application=app, action=ApplicationHistory.ActionType.TIMEOUT,
        detail__reason='AUTO_ARCHIVE_RULE',
    ).exists()


@pytest.mark.django_db
def test_advance_no_rule_no_side_effect(department, super_user):
    """无规则 → 候选正常停在下一阶段，无 SKIPPED / 无归档。"""
    process = make_process('WNORULE1')
    s1, s2 = make_stage('N1'), make_stage('N2')
    l1, l2 = add_link(process, s1, 0), add_link(process, s2, 1)
    # l2 不挂任何 StageRule

    pos = make_position('P_SKIP_ARCHIVE', department, super_user)
    app = make_application('ANORULE', process, l1, pos, phone='13900000103')

    ApplicationService.advance_application_to_next_stage(app)

    app = _reload(app)
    assert app.current_stage_id == s2.id
    assert app.state == ApplicationState.ACTIVE
    assert _latest_record(app, l2).state != ApplicationStageRecord.StageState.SKIPPED
    assert app.state != ApplicationState.TIMEOUT


@pytest.mark.django_db
def test_advance_skip_no_further_stage(department, super_user):
    """流程无后续阶段：停在当前最后一阶段（记录 SKIPPED），不强行发 OFFER/归档。"""
    tpl = make_metric_template()
    process = make_process('WLAST1')
    s1, s2 = make_stage('L1'), make_stage('L2')
    l1, l2 = add_link(process, s1, 0), add_link(process, s2, 1)
    attach_skip_rule(l2, tpl)

    pos = make_position('P_SKIP_ARCHIVE', department, super_user)
    app = make_application('ALAST1', process, l1, pos, phone='13900000104')

    ApplicationService.advance_application_to_next_stage(app)

    app = _reload(app)
    # 无后续阶段：停在当前最后一阶段 S2（记录 SKIPPED）
    assert app.current_stage_id == s2.id
    assert _latest_record(app, l2).state == ApplicationStageRecord.StageState.SKIPPED
    assert app.state == ApplicationState.ACTIVE


@pytest.mark.django_db
def test_advance_skip_priority_over_archive(department, super_user):
    """同阶段 skip + archive 同时命中 → 走归档（archive 优先）。"""
    tpl = make_metric_template()
    process = make_process('WPRI1')
    s1, s2 = make_stage('P1'), make_stage('P2')
    l1, l2 = add_link(process, s1, 0), add_link(process, s2, 1)
    # l2 同时挂 skip 与 archive（均已命中）
    StageRule.objects.create(
        link=l2,
        skip_rules=[{
            'id': 'sk1', 'name': 'skip', 'enabled': True, 'expression': '1',
            'items': [{'id': 'ski', 'item_seq': 1, 'condition_type': 'METRIC',
                       'field': str(tpl.id), 'operator': 'GT', 'value': '0'}],
        }],
        archive_rules=[{
            'id': 'ar1', 'name': 'archive', 'enabled': True, 'expression': '1',
            'items': [{'id': 'ari', 'item_seq': 1, 'condition_type': 'METRIC',
                       'field': str(tpl.id), 'operator': 'GT', 'value': '0'}],
        }],
    )

    pos = make_position('P_SKIP_ARCHIVE', department, super_user)
    app = make_application('APRI1', process, l1, pos, phone='13900000105')

    ApplicationService.advance_application_to_next_stage(app)

    app = _reload(app)
    assert app.state == ApplicationState.TIMEOUT  # archive 优先，终态
    assert _latest_record(app, l2).state == ApplicationStageRecord.StageState.ARCHIVED


# ============================================================
# QA 缺陷猎杀用例（由 test_skip_archive_defects_qa.py 并入）
# 对应 D1 / D2 / D3 / D4 四个真实缺陷证据，复用上方 seed 工具。
# ============================================================
@pytest.mark.django_db
def test_cascade_skip_should_skip_optional_stage(department, super_user):
    """D1：级联推进必须过滤 is_required（与正常 advance 一致）。

    S1(req)→S2(req,skip)→S3(opt,is_required=False)→S4(req)。
    skip 级联应跳过可选阶段、落到下一必经阶段 S4，而非卡在可选 S3。
    """
    tpl = make_metric_template()
    process = make_process('QASKIPOPT')
    s1, s2, s3, s4 = (
        make_stage('Q1'), make_stage('Q2'), make_stage('Q3'), make_stage('Q4'),
    )
    l1 = add_link(process, s1, 0)
    l2 = add_link(process, s2, 1)
    l3 = add_link(process, s3, 2, is_required=False)  # 可选阶段
    l4 = add_link(process, s4, 3)
    attach_skip_rule(l2, tpl)

    pos = make_position('P_QSKIPOPT', department, super_user)
    app = make_application('AQSKIPOPT', process, l1, pos, phone='13900000701')

    ApplicationService.advance_application_to_next_stage(app)

    app = _reload(app)
    assert app.current_stage_id == s4.id, (
        f'候选人应落到下一必经阶段 S4，实际停在 {app.current_stage_id}'
    )
    assert app.stage_records.filter(link=l3, deleted_at__isnull=True).count() == 0
    assert _latest_record(app, l2).state == ApplicationStageRecord.StageState.SKIPPED
    assert _latest_record(app, l4).state == ApplicationStageRecord.StageState.PENDING


@pytest.mark.django_db
def test_cascade_landing_stage_history_not_skipped(department, super_user):
    """D2：级联「停留阶段」审计应为 ADVANCED，而非被误标 SKIPPED。

    S1(req)→S2(req,skip)→S3(req,无规则)。级联进入 S3 并停留，S3 阶段记录为
    PENDING（候选人真实处于该阶段），其进入审计应为 ADVANCED。
    """
    tpl = make_metric_template()
    process = make_process('QALAND')
    s1, s2, s3 = make_stage('L1'), make_stage('L2'), make_stage('L3')
    l1, l2, l3 = add_link(process, s1, 0), add_link(process, s2, 1), add_link(process, s3, 2)
    attach_skip_rule(l2, tpl)  # S3 不挂任何规则

    pos = make_position('P_QLAND', department, super_user)
    app = make_application('AQLAND', process, l1, pos, phone='13900000702')

    ApplicationService.advance_application_to_next_stage(app)

    app = _reload(app)
    assert _latest_record(app, l3).state == ApplicationStageRecord.StageState.PENDING
    land_hist = ApplicationHistory.objects.filter(
        application=app, to_stage=s3,
    ).order_by('-id').first()
    assert land_hist is not None
    assert land_hist.action == ApplicationHistory.ActionType.ADVANCED, (
        f'停留阶段 S3 审计应为 ADVANCED（候选人在该阶段），实际为 {land_hist.action}'
    )


@pytest.mark.django_db
def test_cascade_archive_stage_history_not_duplicate_skipped(department, super_user):
    """D3：级联中命中归档的阶段，不应同时多出 SKIPPED 审计。

    S1(req)→S2(req,skip)→S3(req,archive)。级联：S2 skip → 进入 S3 → S3 命中 archive
    → 整申请归档。S3 阶段记录应 ARCHIVED，审计应仅一条 TIMEOUT(AUTO_ARCHIVE_RULE)。
    """
    tpl = make_metric_template()
    process = make_process('QAARCHCAS')
    s1, s2, s3 = make_stage('C1'), make_stage('C2'), make_stage('C3')
    l1, l2, l3 = add_link(process, s1, 0), add_link(process, s2, 1), add_link(process, s3, 2)
    attach_skip_rule(l2, tpl)
    attach_archive_rule(l3, tpl)

    pos = make_position('P_QARCHCAS', department, super_user)
    app = make_application('AQAARCHCAS', process, l1, pos, phone='13900000703')

    ApplicationService.advance_application_to_next_stage(app)

    app = _reload(app)
    assert app.state == ApplicationState.TIMEOUT
    assert _latest_record(app, l3).state == ApplicationStageRecord.StageState.ARCHIVED
    skip_for_s3 = ApplicationHistory.objects.filter(
        application=app, to_stage=s3, action=ApplicationHistory.ActionType.SKIPPED,
    ).count()
    assert skip_for_s3 == 0, (
        f'被归档的 S3 不应有 SKIPPED 审计，实际 {skip_for_s3} 条'
    )


@pytest.mark.django_db
def test_archive_execution_failure_does_not_rollback_advance(monkeypatch, department, super_user):
    """D4：自动归档「执行」异常应降级，不回滚已进入的推进。

    archive 规则命中，但 _apply_auto_archive 执行抛异常。降级铁律（FAIL-not-500 +
    不阻断已进入动作）：执行分支应包 try/except，保留已进入的推进、不重抛、不回滚。
    """
    tpl = make_metric_template()
    process = make_process('QAEXEC')
    s1, s2 = make_stage('X1'), make_stage('X2')
    l1, l2 = add_link(process, s1, 0), add_link(process, s2, 1)
    attach_archive_rule(l2, tpl)

    pos = make_position('P_QEXEC', department, super_user)
    app = make_application('AQAEXEC', process, l1, pos, phone='13900000704')

    def boom(application, actor, rule_name=''):  # noqa: ANN001, ANN201
        raise RuntimeError('boom-in-execution')

    monkeypatch.setattr(ApplicationService, '_apply_auto_archive', boom)

    try:
        ApplicationService.advance_application_to_next_stage(app)
    except Exception as e:  # noqa: BLE001 — 期望不抛出；抛出即证明降级缺口
        pytest.fail(f'自动归档执行异常回滚了已进入的推进（降级契约被破坏）：{e}')

    app = _reload(app)
    # 已进入 S2 的推进应被保留，不被回滚到 S1
    assert app.current_stage_id == s2.id
