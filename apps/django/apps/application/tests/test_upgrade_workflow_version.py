"""T3 回归：``upgrade_workflow_version`` 真升版本（§1.3）+ ``upgrade-version`` 端点。

T3 之前它错在哪
===============
活实现（``application/services/__init__.py``）只做了一件事::

    application.workflow_version = application.process.current_version
    application.save()

``process`` 没换、``current_link`` 没换。也就是说"升版本"只刷新了一个展示用的
字符串，候选人跑的还是老流程的关联行。更糟的是它读的是
``application.process.current_version`` —— 而 ``application.process`` 就是**旧行**，
所以除非有人原地改写旧行的版本号（正是 T2 干掉的 ``bump_version`` 老行为），
这个条件永远相等，端点恒抛 409。clone 出新行之后调它，同样 409。

另一份死代码 ``versioning.upgrade_application_to_latest_version`` 有"改指 process"
的正确骨架，却带 V5 读后写 bug：先 ``application.workflow_version = target...``
再在 return 里读 ``application.workflow_version`` 当 ``from_version``，
使审计里 ``from_version`` 恒等于 ``to_version``。T3 只合并它的"改指"，
快照一律在赋值前采集 —— 见 :func:`test_audit_from_version_is_not_read_after_write`。

本文件的覆盖面
==============
- 正路：改指 process / workflow_version / current_link / current_stage 四件套；
- 阶段映射三分支（精确 / 前序回落 / 起点）与审计里的 ``stage_remapped``；
- 校验四条：跨 code / 非最新中间版 / 已归档 / 降版本，全部 409；
- 审计快照不得读后写（V5）；
- HTTP 端点：成功 200、各类拒绝 409、``detail=True`` 路由可达。

真实 clone 链路的端到端（clone → upgrade-version → versions）在
``apps/process/tests/test_process_version_lifecycle_e2e.py``，与本文件互补：
本文件用手工构造的版本行穷举分支，那边验证真实 clone 产物能被正确升上去。
"""
from __future__ import annotations

from typing import Optional

import pytest
from django.utils import timezone

from apps.application.models import (
    Application,
    ApplicationHistory,
    ApplicationState,
)
from apps.application.services import ApplicationService
from apps.candidate.models import Candidate
from apps.common.exceptions import StateTransitionError
from apps.position.models import Position, PositionState
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageType,
)

pytestmark = pytest.mark.django_db

UPGRADE_URL = '/api/v1/applications/{id}/upgrade-version/'


# ============================================================
# Seed 工具（dev 库 Application=0，一切自建）
# ============================================================
def make_stage(key: str) -> RecruitmentStage:
    stage, _ = RecruitmentStage.objects.get_or_create(
        code=f'UV{key}',
        defaults={'name': f'升版本测试阶段-{key}', 'stage_type': StageType.SCREEN},
    )
    return stage


def make_process(
    code: str, seq: int, *, is_latest: bool, status: str = 'ENABLED',
) -> RecruitmentProcess:
    return RecruitmentProcess.objects.create(
        code=code,
        name=f'{code} 升版本测试流程 V{seq}',
        current_version=f'V{seq}.0',
        version_seq=seq,
        is_latest=is_latest,
        status=status,
    )


def add_link(
    process: RecruitmentProcess, stage: RecruitmentStage, order: int,
    *, deleted: bool = False,
) -> ProcessStageLink:
    link = ProcessStageLink.objects.create(
        process=process, stage=stage, order=order, is_required=True,
    )
    if deleted:
        link.soft_delete()
    return link


def _reload(application: Application) -> Application:
    """重新查库。不能用 refresh_from_db —— protected FSMField 会炸。"""
    return Application.objects.get(pk=application.pk)


def make_application(
    code: str, process: RecruitmentProcess, link: ProcessStageLink,
    position: Position, *, phone: str,
) -> Application:
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
    """一个招聘中的职位。process 字段随便挂一个，升版本只看 application.process。"""
    holder = make_process('WUVPOS', 1, is_latest=True)
    add_link(holder, make_stage('POS'), 1)
    pos = Position.objects.create(
        code='P_UPGRADE_VER',
        title='升版本回归职位',
        description='T3 回归用',
        department=department,
        hiring_manager=super_user,
        owner=super_user,
        headcount=5,
        state=PositionState.DRAFT,
        process=holder,
    )
    pos.submit_publish(); pos.save()
    pos.publish(); pos.save()
    pos.start_recruiting(); pos.save()
    return pos


def _last_upgrade_history(application: Application) -> ApplicationHistory:
    history = ApplicationHistory.objects.filter(
        application=application,
        action=ApplicationHistory.ActionType.UPGRADE_VERSION,
    ).order_by('-created_at').first()
    assert history is not None, '升版本必须留下 UPGRADE_VERSION 审计'
    return history


# ============================================================
# 1. 正路：四件套真的都改了
# ============================================================
def test_upgrade_repoints_process_link_and_stage(position, super_user) -> None:
    s1, s2 = make_stage('A1'), make_stage('A2')

    old = make_process('WUV01', 1, is_latest=False)
    old_link = add_link(old, s1, 1)
    add_link(old, s2, 2)

    new = make_process('WUV01', 2, is_latest=True)
    new_link_1 = add_link(new, s1, 1)
    add_link(new, s2, 2)

    app = make_application('APP-UV-01', old, old_link, position, phone='13930000001')

    ApplicationService.upgrade_workflow_version(app, actor=super_user)

    reloaded = _reload(app)
    assert reloaded.process_id == new.id, 'process 必须真的改指新版本行'
    assert reloaded.workflow_version == 'V2.0'
    assert reloaded.current_link_id == new_link_1.id, 'current_link 必须指向新流程的关联'
    assert reloaded.current_stage_id == s1.id, '阶段未变（精确匹配）'


def test_upgrade_resolves_latest_row_automatically(position, super_user) -> None:
    """不传 target 时自动解析同 code 的 is_latest=True 行（跳过中间版本）。"""
    s1 = make_stage('B1')
    v1 = make_process('WUV02', 1, is_latest=False)
    v1_link = add_link(v1, s1, 1)
    make_process('WUV02', 2, is_latest=False)  # 中间版本，不得被选中
    v3 = make_process('WUV02', 3, is_latest=True)
    add_link(v3, s1, 1)

    app = make_application('APP-UV-02', v1, v1_link, position, phone='13930000002')

    ApplicationService.upgrade_workflow_version(app, actor=super_user)

    assert _reload(app).process_id == v3.id
    assert _reload(app).workflow_version == 'V3.0'


def test_audit_contains_stage_remapped_false_on_exact_match(position, super_user) -> None:
    s1 = make_stage('C1')
    old = make_process('WUV03', 1, is_latest=False)
    old_link = add_link(old, s1, 1)
    new = make_process('WUV03', 2, is_latest=True)
    add_link(new, s1, 1)

    app = make_application('APP-UV-03', old, old_link, position, phone='13930000003')
    ApplicationService.upgrade_workflow_version(app, actor=super_user)

    detail = _last_upgrade_history(app).detail
    assert detail['stage_remapped'] is False
    assert detail['stage_map_strategy'] == 'EXACT'
    assert detail['from_version'] == 'V1.0'
    assert detail['to_version'] == 'V2.0'
    assert detail['from_process_id'] == old.id
    assert detail['to_process_id'] == new.id


# ============================================================
# 2. 阶段映射三分支 + stage_remapped
# ============================================================
def test_upgrade_falls_back_to_predecessor_when_stage_removed(position, super_user) -> None:
    """新版本删掉了候选人当前阶段 → 回落前序，且审计 stage_remapped=True。"""
    s1, s2, s3 = make_stage('D1'), make_stage('D2'), make_stage('D3')

    old = make_process('WUV04', 1, is_latest=False)
    old_link = add_link(old, s3, 3)

    new = make_process('WUV04', 2, is_latest=True)
    add_link(new, s1, 1)
    expected = add_link(new, s2, 2)
    add_link(new, s3, 3, deleted=True)  # 当前阶段在新版本被删

    app = make_application('APP-UV-04', old, old_link, position, phone='13930000004')
    ApplicationService.upgrade_workflow_version(app, actor=super_user)

    reloaded = _reload(app)
    assert reloaded.current_link_id == expected.id
    assert reloaded.current_stage_id == s2.id

    detail = _last_upgrade_history(app).detail
    assert detail['stage_remapped'] is True
    assert detail['stage_map_strategy'] == 'PREDECESSOR'
    assert detail['from_stage_id'] == s3.id
    assert detail['to_stage_id'] == s2.id


def test_upgrade_falls_back_to_start_when_no_predecessor(position, super_user) -> None:
    s1, s2 = make_stage('E1'), make_stage('E2')

    old = make_process('WUV05', 1, is_latest=False)
    old_link = add_link(old, s1, 1)

    new = make_process('WUV05', 2, is_latest=True)
    start = add_link(new, s2, 1)

    app = make_application('APP-UV-05', old, old_link, position, phone='13930000005')
    ApplicationService.upgrade_workflow_version(app, actor=super_user)

    assert _reload(app).current_link_id == start.id
    detail = _last_upgrade_history(app).detail
    assert detail['stage_map_strategy'] == 'START'
    assert detail['stage_remapped'] is True


def test_upgrade_history_from_to_stage_columns_are_filled(position, super_user) -> None:
    """审计的 from_stage / to_stage 两个**列**（不只是 detail）必须写对。"""
    s1, s2 = make_stage('F1'), make_stage('F2')
    old = make_process('WUV06', 1, is_latest=False)
    old_link = add_link(old, s2, 2)
    new = make_process('WUV06', 2, is_latest=True)
    add_link(new, s1, 1)

    app = make_application('APP-UV-06', old, old_link, position, phone='13930000006')
    ApplicationService.upgrade_workflow_version(app, actor=super_user)

    history = _last_upgrade_history(app)
    assert history.from_stage_id == s2.id
    assert history.to_stage_id == s1.id
    assert history.operator_id == super_user.id


def test_upgrade_fails_loudly_when_target_has_no_live_stage(position, super_user) -> None:
    """目标版本零 live 阶段 → 409，且**一个字段都不许改**（先算后写）。"""
    s1 = make_stage('G1')
    old = make_process('WUV07', 1, is_latest=False)
    old_link = add_link(old, s1, 1)
    new = make_process('WUV07', 2, is_latest=True)
    add_link(new, s1, 1, deleted=True)  # 全删光

    app = make_application('APP-UV-07', old, old_link, position, phone='13930000007')

    with pytest.raises(StateTransitionError) as exc:
        ApplicationService.upgrade_workflow_version(app, actor=super_user)
    assert '目标流程无任何可用阶段' in str(exc.value)

    reloaded = _reload(app)
    assert reloaded.process_id == old.id
    assert reloaded.current_link_id == old_link.id
    assert reloaded.workflow_version == 'V1.0'
    assert not ApplicationHistory.objects.filter(
        application=app, action=ApplicationHistory.ActionType.UPGRADE_VERSION,
    ).exists()


# ============================================================
# 3. 校验四条 —— 全部必须抛 StateTransitionError（view 转 409）
# ============================================================
def test_cross_code_target_is_rejected(position, super_user) -> None:
    s1 = make_stage('H1')
    old = make_process('WUV08', 1, is_latest=False)
    old_link = add_link(old, s1, 1)
    add_link(make_process('WUV08', 2, is_latest=True), s1, 1)

    other_line = make_process('WUV99', 1, is_latest=True)
    add_link(other_line, s1, 1)

    app = make_application('APP-UV-08', old, old_link, position, phone='13930000008')

    with pytest.raises(StateTransitionError) as exc:
        ApplicationService.upgrade_workflow_version(
            app, actor=super_user, target_process=other_line,
        )
    assert '跨流程线' in str(exc.value)
    assert _reload(app).process_id == old.id


def test_non_latest_intermediate_target_is_rejected(position, super_user) -> None:
    s1 = make_stage('I1')
    v1 = make_process('WUV09', 1, is_latest=False)
    v1_link = add_link(v1, s1, 1)
    v2 = make_process('WUV09', 2, is_latest=False)  # 中间版
    add_link(v2, s1, 1)
    add_link(make_process('WUV09', 3, is_latest=True), s1, 1)

    app = make_application('APP-UV-09', v1, v1_link, position, phone='13930000009')

    with pytest.raises(StateTransitionError) as exc:
        ApplicationService.upgrade_workflow_version(app, actor=super_user, target_process=v2)
    assert 'is_latest=False' in str(exc.value)
    assert _reload(app).process_id == v1.id


def test_archived_target_is_rejected(position, super_user) -> None:
    s1 = make_stage('J1')
    old = make_process('WUV10', 1, is_latest=False)
    old_link = add_link(old, s1, 1)
    new = make_process('WUV10', 2, is_latest=True, status='ARCHIVED')
    add_link(new, s1, 1)

    app = make_application('APP-UV-10', old, old_link, position, phone='13930000010')

    with pytest.raises(StateTransitionError) as exc:
        ApplicationService.upgrade_workflow_version(app, actor=super_user)
    assert '已归档' in str(exc.value)
    assert _reload(app).process_id == old.id


def test_downgrade_is_rejected(position, super_user) -> None:
    """禁降版本：显式把一个更老的行当目标传进来也必须被挡住。"""
    s1 = make_stage('K1')
    v1 = make_process('WUV11', 1, is_latest=True)  # 老行，仍是 latest（模拟误操作）
    add_link(v1, s1, 1)
    v2 = make_process('WUV11', 2, is_latest=False)
    v2_link = add_link(v2, s1, 1)

    app = make_application('APP-UV-11', v2, v2_link, position, phone='13930000011')

    with pytest.raises(StateTransitionError) as exc:
        ApplicationService.upgrade_workflow_version(app, actor=super_user, target_process=v1)
    assert '禁止降版本' in str(exc.value)
    assert _reload(app).process_id == v2.id


def test_already_on_latest_is_rejected(position, super_user) -> None:
    s1 = make_stage('L1')
    latest = make_process('WUV12', 1, is_latest=True)
    link = add_link(latest, s1, 1)

    app = make_application('APP-UV-12', latest, link, position, phone='13930000012')

    with pytest.raises(StateTransitionError) as exc:
        ApplicationService.upgrade_workflow_version(app, actor=super_user)
    assert 'already on the latest version' in str(exc.value)


def test_no_latest_row_is_rejected(position, super_user) -> None:
    """整条流程线没有 is_latest=True 的行（历史脏数据）→ 明确报错而不是静默 no-op。"""
    s1 = make_stage('M1')
    v1 = make_process('WUV13', 1, is_latest=False)
    link = add_link(v1, s1, 1)

    app = make_application('APP-UV-13', v1, link, position, phone='13930000013')

    with pytest.raises(StateTransitionError) as exc:
        ApplicationService.upgrade_workflow_version(app, actor=super_user)
    assert 'is_latest=True' in str(exc.value)


def test_soft_deleted_latest_row_is_not_picked(position, super_user) -> None:
    """软删行不得被当成升级目标（``soft_delete()`` 会降 is_latest，这里是双保险）。"""
    s1 = make_stage('N1')
    v1 = make_process('WUV14', 1, is_latest=False)
    link = add_link(v1, s1, 1)
    dead = make_process('WUV14', 2, is_latest=True)
    add_link(dead, s1, 1)
    dead.soft_delete()

    app = make_application('APP-UV-14', v1, link, position, phone='13930000014')

    with pytest.raises(StateTransitionError):
        ApplicationService.upgrade_workflow_version(app, actor=super_user)
    assert _reload(app).process_id == v1.id


# ============================================================
# 4. V5 读后写 —— 审计快照必须在赋值前采集
# ============================================================
def test_audit_from_version_is_not_read_after_write(position, super_user) -> None:
    """死代码的 V5 bug：先赋值再读，使 from_version 恒等于 to_version。

    只要 from_version != to_version 且等于升级前的真实版本号，就说明快照是
    在赋值**之前**采集的。这条断言会在任何人把采集点挪到赋值之后时立刻变红。
    """
    s1 = make_stage('O1')
    old = make_process('WUV15', 1, is_latest=False)
    old_link = add_link(old, s1, 1)
    new = make_process('WUV15', 5, is_latest=True)
    add_link(new, s1, 1)

    app = make_application('APP-UV-15', old, old_link, position, phone='13930000015')
    assert app.workflow_version == 'V1.0'

    ApplicationService.upgrade_workflow_version(app, actor=super_user)

    detail = _last_upgrade_history(app).detail
    assert detail['from_version'] == 'V1.0'
    assert detail['to_version'] == 'V5.0'
    assert detail['from_version'] != detail['to_version']
    assert detail['from_process_id'] == old.id
    assert detail['from_process_id'] != detail['to_process_id']


def test_audit_from_stage_snapshot_taken_before_repoint(position, super_user) -> None:
    """阶段快照同理：回落场景下 from_stage_id 必须是**升级前**的阶段。"""
    s1, s2 = make_stage('P1'), make_stage('P2')
    old = make_process('WUV16', 1, is_latest=False)
    old_link = add_link(old, s2, 2)
    new = make_process('WUV16', 2, is_latest=True)
    add_link(new, s1, 1)

    app = make_application('APP-UV-16', old, old_link, position, phone='13930000016')
    ApplicationService.upgrade_workflow_version(app, actor=super_user)

    detail = _last_upgrade_history(app).detail
    assert detail['from_stage_id'] == s2.id
    assert detail['from_link_id'] == old_link.id
    assert detail['to_stage_id'] == s1.id
    assert detail['from_stage_id'] != detail['to_stage_id']


# ============================================================
# 5. HTTP 端点
# ============================================================
def test_endpoint_returns_200_and_repoints(auth_client, position, super_user) -> None:
    s1 = make_stage('Q1')
    old = make_process('WUV17', 1, is_latest=False)
    old_link = add_link(old, s1, 1)
    new = make_process('WUV17', 2, is_latest=True)
    add_link(new, s1, 1)

    app = make_application('APP-UV-17', old, old_link, position, phone='13930000017')

    resp = auth_client.post(UPGRADE_URL.format(id=app.id))

    assert resp.status_code == 200, resp.content
    assert _reload(app).process_id == new.id


def test_endpoint_returns_409_when_already_latest(auth_client, position, super_user) -> None:
    s1 = make_stage('R1')
    latest = make_process('WUV18', 1, is_latest=True)
    link = add_link(latest, s1, 1)
    app = make_application('APP-UV-18', latest, link, position, phone='13930000018')

    resp = auth_client.post(UPGRADE_URL.format(id=app.id))

    assert resp.status_code == 409, resp.content
    body = resp.json()
    assert body['code'] == 'STATE_TRANSITION_ERROR'


def test_endpoint_returns_409_when_target_archived(auth_client, position, super_user) -> None:
    s1 = make_stage('S1')
    old = make_process('WUV19', 1, is_latest=False)
    old_link = add_link(old, s1, 1)
    new = make_process('WUV19', 2, is_latest=True, status='ARCHIVED')
    add_link(new, s1, 1)
    app = make_application('APP-UV-19', old, old_link, position, phone='13930000019')

    resp = auth_client.post(UPGRADE_URL.format(id=app.id))

    assert resp.status_code == 409, resp.content
    assert _reload(app).process_id == old.id


def test_endpoint_is_detail_route(auth_client, position) -> None:
    """``detail=True`` 透传确认：不带 id 的 collection 路由必须不存在（405/404）。"""
    resp = auth_client.post('/api/v1/applications/upgrade-version/')
    assert resp.status_code in (404, 405), resp.status_code
