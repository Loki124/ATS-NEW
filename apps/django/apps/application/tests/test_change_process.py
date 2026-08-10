"""T8 回归：跨流程线迁移 ``change_process`` 服务 + ``change-process`` 端点（§3）。

这条链路和 upgrade-version 长得像，但语义相反，两个方向都要钉死
================================================================
``upgrade_workflow_version`` **禁跨 code**（换流程线得走这里）；``change_process``
则要求**必须跨行**，同一行直接 409。落点算法也刻意不共用：

- upgrade 走 :func:`resolve_stage_mapping` 的"最近前序"算法 —— 同 code 的两个版本
  order 编号同源，可比；
- change-process 由操作员显式指定 ``target_stage_id`` —— 两条线的 order 编号体系
  彼此独立（社招线 INTERVIEW=3、校招线 INTERVIEW=2），数值无可比性。硬套 order
  会得到"看起来有、实则错"的落点（§3.3），所以服务端**不猜**，只校验。

本文件的覆盖面
==============
- 正路：process / workflow_version / current_link / current_stage 四件套全改 +
  写入 ``CHANGE_PROCESS``（**不是** UPGRADE_VERSION，§3.4）；
- 审计 FK 列 ``from_stage`` / ``to_stage`` 非空且指向正确 —— 规格 §3.2 的伪代码
  只写了 detail，照抄会让这两列全 NULL，与 UPGRADE_VERSION 的审计形态分叉；
- 审计快照不得读后写（V5 同款陷阱）：``detail.from_version`` 必须是**旧**版本号；
- 校验四条：阶段不属于目标流程 / 同流程 / 目标已归档 / 目标已软删 → 409；
- 入参形态：缺 reason / 缺 target_stage_id / reason 空白 → 400；
- 不存在的 target_process_id / target_stage_id → 404。

⚠️ dev 库 ``Application=0``（事实 4），本文件所有数据自建，不依赖任何 dev 现状。
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
from apps.common.exceptions import StateTransitionError
from apps.position.models import Position, PositionState
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageType,
)

pytestmark = pytest.mark.django_db

CHANGE_URL = '/api/v1/applications/{id}/change-process/'


# ============================================================
# Seed 工具（dev 库 Application=0，一切自建）
# ============================================================
def make_stage(key: str) -> RecruitmentStage:
    """阶段库是全局共享的，两条流程线可以引用同一个 stage。"""
    stage, _ = RecruitmentStage.objects.get_or_create(
        code=f'CP{key}',
        defaults={'name': f'换流程线测试阶段-{key}', 'stage_type': StageType.SCREEN},
    )
    return stage


def make_process(
    code: str, seq: int = 1, *, is_latest: bool = True, status: str = 'ENABLED',
) -> RecruitmentProcess:
    return RecruitmentProcess.objects.create(
        code=code,
        name=f'{code} 换流程线测试流程 V{seq}',
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
    """一个招聘中的职位。process 字段随便挂一个，换流程线只看 application.process。"""
    holder = make_process('WCPPOS')
    add_link(holder, make_stage('POS'), 1)
    pos = Position.objects.create(
        code='P_CHANGE_PROC',
        title='换流程线回归职位',
        description='T8 回归用',
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


def _last_change_history(application: Application) -> ApplicationHistory:
    history = ApplicationHistory.objects.filter(
        application=application,
        action=ApplicationHistory.ActionType.CHANGE_PROCESS,
    ).order_by('-created_at').first()
    assert history is not None, '跨流程线迁移必须留下 CHANGE_PROCESS 审计'
    return history


# ============================================================
# 1. 正路：四件套真的都改了 + 写 CHANGE_PROCESS
# ============================================================
def test_change_process_repoints_all_four_fields(position, super_user) -> None:
    """跨 code 成功改指：process / workflow_version / current_link / current_stage 全变。"""
    s_old, s_new = make_stage('A1'), make_stage('A2')

    old = make_process('WCP01', 1)
    old_link = add_link(old, s_old, 1)

    target = make_process('WCP02', 3)
    target_link = add_link(target, s_new, 2)

    app = make_application('APP-CP-01', old, old_link, position, phone='13940000001')
    assert app.workflow_version == 'V1.0'

    ApplicationService.change_process(
        app, target_process=target, target_stage_link=target_link,
        actor=super_user, reason='候选人转投校招线',
    )

    reloaded = _reload(app)
    assert reloaded.process_id == target.id, 'process 必须真的改指另一条流程线'
    assert reloaded.workflow_version == 'V3.0', 'workflow_version 必须跟着目标行走'
    assert reloaded.current_link_id == target_link.id, 'current_link 必须是操作员指定的落点'
    assert reloaded.current_stage_id == s_new.id, 'current_stage 必须同步'


def test_change_process_writes_change_process_action_not_upgrade(position, super_user) -> None:
    """§3.4：跨 code 是独立审计动作，**不得**复用 UPGRADE_VERSION。"""
    s_old, s_new = make_stage('B1'), make_stage('B2')
    old = make_process('WCP03', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP04', 1)
    target_link = add_link(target, s_new, 1)

    app = make_application('APP-CP-02', old, old_link, position, phone='13940000002')
    ApplicationService.change_process(
        app, target_process=target, target_stage_link=target_link,
        actor=super_user, reason='流程线选错了，纠正',
    )

    history = _last_change_history(app)
    assert history.action == ApplicationHistory.ActionType.CHANGE_PROCESS
    assert history.operator_id == super_user.id
    assert history.detail['reason'] == '流程线选错了，纠正'
    assert history.detail['from_process_code'] == 'WCP03'
    assert history.detail['to_process_code'] == 'WCP04'
    assert not ApplicationHistory.objects.filter(
        application=app, action=ApplicationHistory.ActionType.UPGRADE_VERSION,
    ).exists(), '跨流程线不得混写成升版本审计'


# ============================================================
# 2. 审计 FK 列（规格 §3.2 伪代码漏填，这里钉死）
# ============================================================
def test_audit_from_to_stage_fk_columns_are_not_null(position, super_user) -> None:
    """审计的 ``from_stage`` / ``to_stage`` 两个 **FK 列** 必须非空且指向正确。

    §3.2 的伪代码只填了 ``detail``，照抄会让这两列全 NULL —— 与 UPGRADE_VERSION
    的审计形态分叉，前端时间线渲染会缺阶段信息。这条断言在任何人把 FK 参数
    删掉时立刻变红。
    """
    s_old, s_new = make_stage('C1'), make_stage('C2')
    old = make_process('WCP05', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP06', 1)
    target_link = add_link(target, s_new, 1)

    app = make_application('APP-CP-03', old, old_link, position, phone='13940000003')
    ApplicationService.change_process(
        app, target_process=target, target_stage_link=target_link,
        actor=super_user, reason='FK 列回归',
    )

    history = _last_change_history(app)
    assert history.from_stage_id is not None, 'from_stage FK 列不得为 NULL'
    assert history.to_stage_id is not None, 'to_stage FK 列不得为 NULL'
    assert history.from_stage_id == s_old.id
    assert history.to_stage_id == s_new.id
    # detail 里的 code 字符串与 FK 列并存，两者都要对得上
    assert history.detail['from_stage'] == s_old.code
    assert history.detail['to_stage'] == s_new.code


# ============================================================
# 3. V5 读后写 —— 审计快照必须在赋值前采集
# ============================================================
def test_audit_from_version_is_not_read_after_write(position, super_user) -> None:
    """``detail.from_version`` 必须是**旧**版本号。

    死代码 ``versioning.upgrade_application_to_latest_version`` 的 V5 bug 就是
    先写 ``application.workflow_version = ...`` 再读它当 ``from_version``，
    使审计里"从哪来"恒等于"到哪去"。只要把快照采集挪到赋值之后，这条必红。
    """
    s_old, s_new = make_stage('D1'), make_stage('D2')
    old = make_process('WCP07', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP08', 7)  # 版本号刻意拉开，读后写会一眼看穿
    target_link = add_link(target, s_new, 1)

    app = make_application('APP-CP-04', old, old_link, position, phone='13940000004')
    assert app.workflow_version == 'V1.0'

    ApplicationService.change_process(
        app, target_process=target, target_stage_link=target_link,
        actor=super_user, reason='读后写回归钉',
    )

    detail = _last_change_history(app).detail
    assert detail['from_version'] == 'V1.0', 'from_version 必须是迁移前的版本号'
    assert detail['to_version'] == 'V7.0'
    assert detail['from_version'] != detail['to_version']
    # process / link / stage 三组快照同理，全部必须是旧值
    assert detail['from_process_id'] == old.id
    assert detail['from_process_id'] != detail['to_process_id']
    assert detail['from_link_id'] == old_link.id
    assert detail['from_link_id'] != detail['to_link_id']
    assert detail['from_stage'] == s_old.code
    assert detail['from_stage'] != detail['to_stage']


# ============================================================
# 4. 业务校验 —— 全部 StateTransitionError（view 转 409）
# ============================================================
def test_stage_link_from_other_process_is_rejected(position, super_user) -> None:
    """``target_stage_id`` 属于第三条流程线 → 409，且一个字段都不许改。"""
    s_old, s_new, s_alien = make_stage('E1'), make_stage('E2'), make_stage('E3')
    old = make_process('WCP09', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP10', 1)
    add_link(target, s_new, 1)
    alien = make_process('WCP11', 1)
    alien_link = add_link(alien, s_alien, 1)  # 落点来自**第三条**线

    app = make_application('APP-CP-05', old, old_link, position, phone='13940000005')

    with pytest.raises(StateTransitionError) as exc:
        ApplicationService.change_process(
            app, target_process=target, target_stage_link=alien_link,
            actor=super_user, reason='落点串线',
        )
    assert '目标阶段不属于目标流程' in str(exc.value)

    reloaded = _reload(app)
    assert reloaded.process_id == old.id
    assert reloaded.current_link_id == old_link.id
    assert reloaded.workflow_version == 'V1.0'
    assert not ApplicationHistory.objects.filter(
        application=app, action=ApplicationHistory.ActionType.CHANGE_PROCESS,
    ).exists(), '校验失败不得留下审计'


def test_same_process_is_rejected(position, super_user) -> None:
    """目标就是当前流程行 → 409（换流程线换了个寂寞，且会刷出无意义审计）。"""
    s1 = make_stage('F1')
    current = make_process('WCP12', 1)
    link = add_link(current, s1, 1)
    other_link = add_link(current, make_stage('F2'), 2)

    app = make_application('APP-CP-06', current, link, position, phone='13940000006')

    with pytest.raises(StateTransitionError) as exc:
        ApplicationService.change_process(
            app, target_process=current, target_stage_link=other_link,
            actor=super_user, reason='同流程',
        )
    assert '目标流程与当前流程相同' in str(exc.value)
    assert _reload(app).current_link_id == link.id


def test_archived_target_process_is_rejected(position, super_user) -> None:
    """目标流程已归档 → 409。归档版本只读（BR-103），不许往里塞活候选人。"""
    s_old, s_new = make_stage('G1'), make_stage('G2')
    old = make_process('WCP13', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP14', 1, status='ARCHIVED')
    target_link = add_link(target, s_new, 1)

    app = make_application('APP-CP-07', old, old_link, position, phone='13940000007')

    with pytest.raises(StateTransitionError) as exc:
        ApplicationService.change_process(
            app, target_process=target, target_stage_link=target_link,
            actor=super_user, reason='迁到归档线',
        )
    assert '目标流程不可用' in str(exc.value)
    assert _reload(app).process_id == old.id


def test_soft_deleted_target_process_is_rejected(position, super_user) -> None:
    """目标流程已软删 → 409（端点层的 deleted_at 过滤之外的服务层兜底）。"""
    s_old, s_new = make_stage('H1'), make_stage('H2')
    old = make_process('WCP15', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP16', 1)
    target_link = add_link(target, s_new, 1)
    target.soft_delete()  # 同步降 is_latest 并置 deleted_at（in-memory 也已更新）
    assert target.deleted_at is not None

    app = make_application('APP-CP-08', old, old_link, position, phone='13940000008')

    with pytest.raises(StateTransitionError) as exc:
        ApplicationService.change_process(
            app, target_process=target, target_stage_link=target_link,
            actor=super_user, reason='迁到已删线',
        )
    assert '已删除' in str(exc.value)
    assert _reload(app).process_id == old.id


def test_soft_deleted_target_stage_link_is_rejected(position, super_user) -> None:
    """落点 link 已软删 → 409。"""
    s_old, s_new = make_stage('I1'), make_stage('I2')
    old = make_process('WCP17', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP18', 1)
    target_link = add_link(target, s_new, 1, deleted=True)

    app = make_application('APP-CP-09', old, old_link, position, phone='13940000009')

    with pytest.raises(StateTransitionError) as exc:
        ApplicationService.change_process(
            app, target_process=target, target_stage_link=target_link,
            actor=super_user, reason='落点已删',
        )
    assert '目标阶段已删除' in str(exc.value)
    assert _reload(app).current_link_id == old_link.id


# ============================================================
# 5. HTTP 端点：200 / 400 / 404 / 409
# ============================================================
def test_endpoint_returns_200_and_repoints(auth_client, position, super_user) -> None:
    s_old, s_new = make_stage('J1'), make_stage('J2')
    old = make_process('WCP19', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP20', 2)
    target_link = add_link(target, s_new, 1)

    app = make_application('APP-CP-10', old, old_link, position, phone='13940000010')

    resp = auth_client.post(
        CHANGE_URL.format(id=app.id),
        {
            'target_process_id': target.id,
            'target_stage_id': target_link.id,
            'reason': '端点正路',
        },
        format='json',
    )

    assert resp.status_code == 200, resp.content
    reloaded = _reload(app)
    assert reloaded.process_id == target.id
    assert reloaded.current_link_id == target_link.id
    assert reloaded.workflow_version == 'V2.0'
    assert _last_change_history(app).detail['reason'] == '端点正路'


def test_endpoint_returns_400_when_reason_missing(auth_client, position) -> None:
    """``reason`` 缺省 → 400（入参形态，走 serializer）。"""
    s_old, s_new = make_stage('K1'), make_stage('K2')
    old = make_process('WCP21', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP22', 1)
    target_link = add_link(target, s_new, 1)

    app = make_application('APP-CP-11', old, old_link, position, phone='13940000011')

    resp = auth_client.post(
        CHANGE_URL.format(id=app.id),
        {'target_process_id': target.id, 'target_stage_id': target_link.id},
        format='json',
    )

    assert resp.status_code == 400, resp.content
    assert _reload(app).process_id == old.id, '400 不得产生任何写入'


def test_endpoint_returns_400_when_reason_blank(auth_client, position) -> None:
    """``reason`` 传空白串同样 400 —— 审计里没有理由等于没有审计。"""
    s_old, s_new = make_stage('L1'), make_stage('L2')
    old = make_process('WCP23', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP24', 1)
    target_link = add_link(target, s_new, 1)

    app = make_application('APP-CP-12', old, old_link, position, phone='13940000012')

    resp = auth_client.post(
        CHANGE_URL.format(id=app.id),
        {
            'target_process_id': target.id,
            'target_stage_id': target_link.id,
            'reason': '   ',
        },
        format='json',
    )

    assert resp.status_code == 400, resp.content
    assert _reload(app).process_id == old.id


def test_endpoint_returns_400_when_target_stage_id_missing(auth_client, position) -> None:
    """``target_stage_id`` 缺省 → 400。落点不允许由服务端猜（§3.3）。"""
    s_old = make_stage('M1')
    old = make_process('WCP25', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP26', 1)
    add_link(target, make_stage('M2'), 1)

    app = make_application('APP-CP-13', old, old_link, position, phone='13940000013')

    resp = auth_client.post(
        CHANGE_URL.format(id=app.id),
        {'target_process_id': target.id, 'reason': '不给落点'},
        format='json',
    )

    assert resp.status_code == 400, resp.content
    assert _reload(app).process_id == old.id


def test_endpoint_returns_404_for_unknown_target_process(auth_client, position) -> None:
    s_old, s_new = make_stage('N1'), make_stage('N2')
    old = make_process('WCP27', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP28', 1)
    target_link = add_link(target, s_new, 1)

    app = make_application('APP-CP-14', old, old_link, position, phone='13940000014')

    resp = auth_client.post(
        CHANGE_URL.format(id=app.id),
        {
            'target_process_id': 'no-such-process-id',
            'target_stage_id': target_link.id,
            'reason': '目标不存在',
        },
        format='json',
    )

    assert resp.status_code == 404, resp.content
    assert _reload(app).process_id == old.id


def test_endpoint_returns_404_for_unknown_target_stage(auth_client, position) -> None:
    s_old, s_new = make_stage('O1'), make_stage('O2')
    old = make_process('WCP29', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP30', 1)
    add_link(target, s_new, 1)

    app = make_application('APP-CP-15', old, old_link, position, phone='13940000015')

    resp = auth_client.post(
        CHANGE_URL.format(id=app.id),
        {
            'target_process_id': target.id,
            'target_stage_id': 'no-such-link-id',
            'reason': '落点不存在',
        },
        format='json',
    )

    assert resp.status_code == 404, resp.content
    assert _reload(app).process_id == old.id


def test_endpoint_returns_404_for_soft_deleted_target_stage(auth_client, position) -> None:
    """软删的 link 在端点层就被 ``deleted_at__isnull=True`` 挡掉 → 404（§1.5）。"""
    s_old, s_new = make_stage('P1'), make_stage('P2')
    old = make_process('WCP31', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP32', 1)
    dead_link = add_link(target, s_new, 1, deleted=True)

    app = make_application('APP-CP-16', old, old_link, position, phone='13940000016')

    resp = auth_client.post(
        CHANGE_URL.format(id=app.id),
        {
            'target_process_id': target.id,
            'target_stage_id': dead_link.id,
            'reason': '落点已软删',
        },
        format='json',
    )

    assert resp.status_code == 404, resp.content
    assert _reload(app).process_id == old.id


def test_endpoint_returns_409_when_stage_not_in_target_process(
    auth_client, position,
) -> None:
    s_old, s_new, s_alien = make_stage('Q1'), make_stage('Q2'), make_stage('Q3')
    old = make_process('WCP33', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP34', 1)
    add_link(target, s_new, 1)
    alien = make_process('WCP35', 1)
    alien_link = add_link(alien, s_alien, 1)

    app = make_application('APP-CP-17', old, old_link, position, phone='13940000017')

    resp = auth_client.post(
        CHANGE_URL.format(id=app.id),
        {
            'target_process_id': target.id,
            'target_stage_id': alien_link.id,
            'reason': '端点串线',
        },
        format='json',
    )

    assert resp.status_code == 409, resp.content
    assert resp.json()['code'] == 'STATE_TRANSITION_ERROR'
    assert _reload(app).process_id == old.id


def test_endpoint_returns_409_when_same_process(auth_client, position) -> None:
    s1, s2 = make_stage('R1'), make_stage('R2')
    current = make_process('WCP36', 1)
    link = add_link(current, s1, 1)
    other_link = add_link(current, s2, 2)

    app = make_application('APP-CP-18', current, link, position, phone='13940000018')

    resp = auth_client.post(
        CHANGE_URL.format(id=app.id),
        {
            'target_process_id': current.id,
            'target_stage_id': other_link.id,
            'reason': '端点同流程',
        },
        format='json',
    )

    assert resp.status_code == 409, resp.content
    assert _reload(app).current_link_id == link.id


def test_endpoint_returns_409_when_target_archived(auth_client, position) -> None:
    s_old, s_new = make_stage('S1'), make_stage('S2')
    old = make_process('WCP37', 1)
    old_link = add_link(old, s_old, 1)
    target = make_process('WCP38', 1, status='ARCHIVED')
    target_link = add_link(target, s_new, 1)

    app = make_application('APP-CP-19', old, old_link, position, phone='13940000019')

    resp = auth_client.post(
        CHANGE_URL.format(id=app.id),
        {
            'target_process_id': target.id,
            'target_stage_id': target_link.id,
            'reason': '端点归档线',
        },
        format='json',
    )

    assert resp.status_code == 409, resp.content
    assert _reload(app).process_id == old.id


def test_endpoint_is_detail_route(auth_client, position) -> None:
    """``detail=True`` 透传确认：不带 id 的 collection 路由必须不存在（405/404）。"""
    resp = auth_client.post('/api/v1/applications/change-process/')
    assert resp.status_code in (404, 405), resp.status_code
