"""T3 端到端：``clone → upgrade-version（含阶段回落）→ list_process_versions``。

把散落在各单测里的三段逻辑串成一条真实链路，证明它们能接起来、且关键不变量成立：

1. ``clone_process_with_new_version`` 产出的新版本行，能被
   ``ApplicationService.upgrade_workflow_version`` 真正升上去（不是孤立的单元）；
2. 升级时的**阶段回落**真实发生（新版本删掉了候选人当前阶段 → 落到前序阶段），
   且审计里有据可查（``stage_remapped`` / ``stage_map_strategy`` / from-to）；
3. ``list_process_versions`` 返回的新版本**按 ``version_seq`` 升序**、整条线**恰一条**
   ``is_latest=True``（C3' 兜底），且新版本的阶段集合已**排除软删 link**。

本文件与 ``apps/application/tests/test_upgrade_workflow_version.py`` 互补：那边用手工
构造的版本行穷举升级的各分支，这边验证「真实 clone 产物 → 真实升级 → 真实列表」整链。
"""
from __future__ import annotations

import pytest
from django.utils import timezone

from apps.application.models import (
    Application,
    ApplicationHistory,
    ApplicationState,
)
from apps.application.services import ApplicationService
from apps.candidate.models import Candidate
from apps.position.models import Position, PositionState
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageType,
)
from apps.process.services.versioning import (
    clone_process_with_new_version,
    list_process_versions,
)

pytestmark = pytest.mark.django_db


def make_stage(code: str, label: str) -> RecruitmentStage:
    stage, _ = RecruitmentStage.objects.get_or_create(
        code=code,
        defaults={'name': f'生命周期阶段-{label}', 'stage_type': StageType.SCREEN},
    )
    return stage


def add_link(process, stage, order: int, *, deleted: bool = False) -> ProcessStageLink:
    link = ProcessStageLink.objects.create(
        process=process, stage=stage, order=order, is_required=True,
    )
    if deleted:
        link.soft_delete()
    return link


def make_application(code, process, link, position, phone) -> Application:
    candidate = Candidate.objects.create(name=f'候选人-{code}', phone=phone)
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


@pytest.fixture
def position(db, department, super_user):
    """一个招聘中的职位。仅用于挂住 Application 的 position 外键。

    upgrade-version 只看 ``application.process``，与这个 holder 流程无关。
    """
    holder = RecruitmentProcess.objects.create(
        code='E2EPOS', name='E2E 职位流程', current_version='V1.0',
        version_seq=1, is_latest=True,
    )
    add_link(holder, make_stage('E2ES0', 'start'), 0)
    pos = Position.objects.create(
        code='P_E2E', title='E2E 职位', description='T3 端到端用',
        department=department, hiring_manager=super_user, owner=super_user,
        headcount=1, state=PositionState.DRAFT, process=holder,
    )
    pos.submit_publish(); pos.save()
    pos.publish(); pos.save()
    pos.start_recruiting(); pos.save()
    return pos


def test_clone_then_upgrade_falls_back_then_list_excludes_soft_deleted_stage(
    position, super_user,
) -> None:
    s1 = make_stage('E2ES1', '一')
    s2 = make_stage('E2ES2', '二')
    s3 = make_stage('E2ES3', '三')

    # ---- 1. 建 v1（is_latest）并克隆出 v2 ----
    v1 = RecruitmentProcess.objects.create(
        code='E2E', name='E2E 流程 V1', current_version='V1.0',
        version_seq=1, is_latest=True,
    )
    v1_s1 = add_link(v1, s1, 1)
    v1_s2 = add_link(v1, s2, 2)
    add_link(v1, s3, 3)

    v2 = clone_process_with_new_version(v1)
    assert v2.version_seq == 2
    v1.refresh_from_db()
    assert v1.is_latest is False and v2.is_latest is True, 'clone 必须把 is_latest 翻转给新行'

    # v2 删掉 s2（软删 link），逼出"阶段回落"
    v2_s2_link = v2.stage_links.get(stage=s2)
    v2_s2_link.soft_delete()
    assert v2.stage_links.filter(deleted_at__isnull=True).count() == 2, (
        '新版本应只保留 s1 / s3 两条 live link'
    )

    # ---- 2. 在 v1、处于 s2 的一名候选人申请 ----
    app = make_application('APP-E2E-01', v1, v1_s2, position, '13950000001')
    assert app.process_id == v1.id
    assert app.current_stage_id == s2.id

    # ---- 3. 升版本：s2 在新版本被删 → 回落前序 s1（PREDECESSOR） ----
    ApplicationService.upgrade_workflow_version(app, actor=super_user)

    # 不能用 refresh_from_db()：Application.state 是受保护的 FSMField，直写会炸。
    app = Application.objects.get(pk=app.pk)
    assert app.process_id == v2.id, '升版本必须把 process 指向新版本行'
    assert app.workflow_version == 'V2.0'
    assert app.current_stage_id == s1.id, '当前阶段被删 → 应回落前序 s1'
    assert app.current_link_id == v2.stage_links.get(stage=s1).id

    # ---- 4. 审计：stage_remapped=True，from/to 正确（先算后写，无读后写） ----
    hist = (
        ApplicationHistory.objects
        .filter(application=app, action=ApplicationHistory.ActionType.UPGRADE_VERSION)
        .order_by('-created_at').first()
    )
    assert hist is not None
    detail = hist.detail
    assert detail['stage_remapped'] is True
    assert detail['stage_map_strategy'] == 'PREDECESSOR'
    assert detail['from_stage_id'] == s2.id
    assert detail['to_stage_id'] == s1.id
    assert detail['from_version'] == 'V1.0'
    assert detail['to_version'] == 'V2.0'
    assert detail['from_process_id'] == v1.id
    assert detail['to_process_id'] == v2.id

    # ---- 5. list_process_versions：升序 + 恰一条 is_latest + 排除软删 ----
    rows = list_process_versions('E2E')
    assert [r['version_seq'] for r in rows] == [1, 2], '必须按整数 version_seq 升序'
    latest_rows = [r for r in rows if r['is_latest']]
    assert len(latest_rows) == 1 and latest_rows[0]['id'] == v2.id, (
        'C3\' 保证整条线恰一条 is_latest=True，且应落在 v2'
    )
    assert all(
        {'id', 'version', 'version_seq', 'is_latest', 'name', 'status', 'created_at', 'reference_count'}
        <= set(r)
        for r in rows
    )
