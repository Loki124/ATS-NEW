"""方案 A：需求跨流程线改绑回归（2026-10-16）。

背景：兵哥反馈「验收流程已从关联的需求与职位剔除，但仍不能删除」。实测后端返回
``403 流程「验收流程」被 1 个需求引用，不可删除``，而 dev 库里那条需求的
``updated_at`` 停在前一天 —— 剔除动作**根本没发生**。全仓 grep
``unlink/dissociate/detach/解除/解绑`` 零命中：系统从来没有「解绑/改绑」这个能力，
``Demand.process`` 又是 NOT NULL + PROTECT FK，于是任何挂过流程的需求都会把那条
流程永久钉死，用户在流程配置页彻底堵死。

本文件钉住 ``rebind_demand_process`` 的全部边界，与
``test_upgrade_demand_process.py``（同 code 线内版本前进）严格分工、互不越界。

⚠️ 与同目录 upgrade 用例同款纪律：**全部用例自带非零 seed 数据**，断言的是真实
写入结果而非空集（dev 库实测 ``Demand=0``，依赖库内现状必然"空跑必绿"）。

覆盖：

1. 主路径：Demand + 其 live Position 一起改指到**另一条 code** 的流程，
   ``process_version`` 跟随目标 ``current_version``（断言 V 前缀）。
2. 软删 Position 不被改指（``_base_manager`` 不兜底的老陷阱）。
3. 跨线且存在**在跑**申请（ACTIVE/PENDING/PAUSED/OFFER_SENT）→ 409，
   Demand/Position 一个字段都不能变（断言回滚）。
4. 跨线但申请已是**终态**（REJECTED/WITHDRAWN/TIMEOUT/ONBOARDED）→ 放行。
5. 目标已归档 / 非 latest / 已软删 / 不存在 → 409 或 404，且原数据零变更。
6. 幂等：目标与当前已是同一行 → ``(demand, [])``，不产生任何写入。
7. BR-102 锁定钉：改绑**绝不**级联改指在跑的 Application（这里是"拒绝改绑"，
   与 upgrade 的"照改不误但不动 Application"是两种不同的保命方式）。
8. API 契约：``POST /demands/{id}/rebind-process/`` 返回
   ``rebound`` / ``moved_position_ids`` / ``previous_process_id``。
"""
from __future__ import annotations

from django.utils import timezone

import pytest

from apps.common.exceptions import StateTransitionError
from apps.demand.models import Demand, DemandState
from apps.demand.services import DemandService
from apps.position.models import Position, PositionState
from apps.process.models import RecruitmentProcess

REBIND_URL = '/api/v1/demands/{id}/rebind-process/'


def _reload(obj):
    """从库里重新取一份实例（避开 FSMField protected=True，见 upgrade 文件同款说明）。"""
    return type(obj)._default_manager.get(pk=obj.pk)


# ---------------------------------------------------------------------------
# seed helpers —— 两条**不同 code** 的流程线，各一个 ENABLED + latest 行
# ---------------------------------------------------------------------------
def _make_process(*, suffix: str, code: str, version: str = 'V1.0',
                  status: str = 'ENABLED', is_latest: bool = True,
                  deleted: bool = False, version_seq: int = 1) -> RecruitmentProcess:
    """建流程版本行。

    ``version_seq`` 必须显式传：``(code, version_seq)`` 与 ``(code, current_version)``
    都是 DB 唯一约束，同一 code 下建第二行时默认的 1 会直接 IntegrityError。
    """
    return RecruitmentProcess.objects.create(
        id=f'proc-rb-{suffix}',
        code=code,
        name=f'改绑流程 {suffix}',
        current_version=version,
        version_seq=version_seq,
        is_latest=is_latest,
        status=status,
        is_template=False,
        is_enabled=True,
        archived_at=timezone.now() if status == 'ARCHIVED' else None,
        deleted_at=timezone.now() if deleted else None,
    )


def _make_demand(department, requester, hr, process, *, suffix: str = '1') -> Demand:
    return Demand.objects.create(
        id=f'demand-rb-{suffix}',
        code=f'D-RB-{suffix}',
        title=f'改绑测试需求 {suffix}',
        department=department,
        requested_by=requester,
        hr=hr,
        headcount=3,
        process=process,
        process_version=process.current_version,
        state=DemandState.DRAFT,
    )


def _make_position(department, user, process, *, suffix: str, demand=None) -> Position:
    return Position.objects.create(
        id=f'pos-rb-{suffix}',
        code=f'P-RB-{suffix}',
        title=f'改绑测试职位 {suffix}',
        department=department,
        hiring_manager=user,
        owner=user,
        headcount=1,
        process=process,
        process_version=process.current_version,
        demand=demand,
        state=PositionState.DRAFT,
    )


def _make_application(position, process, *, suffix: str, state: str):
    from apps.application.models import Application, ApplicationState
    from apps.candidate.models import Candidate, CandidateState

    # 手机号按 nanoid 后缀派生唯一值：Candidate.phone 唯一，重复会 IntegrityError。
    # 不能 int(suffix) —— 参数化传进来的是 'finTI' / 'runAC' 这类字母前缀。
    uniq = abs(hash(suffix)) % 10_000_000
    candidate = Candidate.objects.create(
        id=f'cand-rb-{suffix}',
        name=f'改绑候选人 {suffix}',
        phone=f'137{uniq:07d}',
        current_state=CandidateState.APPLIED,
    )
    return Application.objects.create(
        id=f'app-rb-{suffix}',
        code=f'APP-RB-{suffix}',
        candidate=candidate,
        position=position,
        process=process,
        workflow_version=process.current_version,
        state=ApplicationState(state),
    )


@pytest.fixture
def two_lines(db):
    """两条不同 code 的流程线（源 / 目标），各自 ENABLED + is_latest。"""
    src = _make_process(suffix='src', code='RB_SRC', version='V1.0')
    dst = _make_process(suffix='dst', code='RB_DST', version='V3.0')
    return src, dst


# ---------------------------------------------------------------------------
# 1. 主路径：跨 code 改绑，Demand + live Position 一起换，版本号跟随目标
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_rebind_moves_demand_and_live_positions_to_other_code(
    department, hr_user, hrbp_user, two_lines,
):
    src, dst = two_lines
    demand = _make_demand(department, hr_user, hrbp_user, src)
    pos_a = _make_position(department, hr_user, src, suffix='a', demand=demand)
    pos_b = _make_position(department, hr_user, src, suffix='b', demand=demand)

    assert demand.process_id == src.id
    assert src.code != dst.code  # 前置：必须是两条不同流程线

    _demand, moved = DemandService.rebind_demand_process(demand, target_process=dst, actor=hr_user)

    fresh_demand = _reload(demand)
    assert fresh_demand.process_id == dst.id
    assert fresh_demand.process_version == 'V3.0'   # 跟随目标 current_version，带 V 前缀
    assert _reload(pos_a).process_id == dst.id
    assert _reload(pos_a).process_version == 'V3.0'
    assert _reload(pos_b).process_id == dst.id
    assert sorted(moved) == sorted([pos_a.id, pos_b.id])

    # 源流程引用数归零 —— 这正是「流程终于能删了」的落点
    assert src.reference_count == 0


# ---------------------------------------------------------------------------
# 2. 软删 Position 不被改指
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_rebind_skips_soft_deleted_positions(
    department, hr_user, hrbp_user, two_lines,
):
    from django.utils import timezone as tz
    src, dst = two_lines
    demand = _make_demand(department, hr_user, hrbp_user, src)
    alive = _make_position(department, hr_user, src, suffix='alive', demand=demand)
    dead = _make_position(department, hr_user, src, suffix='dead', demand=demand)
    dead.deleted_at = tz.now()
    dead.save(update_fields=['deleted_at', 'updated_at'])

    _demand, moved = DemandService.rebind_demand_process(demand, target_process=dst, actor=hr_user)

    assert _reload(alive).process_id == dst.id
    assert _reload(dead).process_id == src.id, '软删职位不得被改指'
    assert moved == [alive.id]


# ---------------------------------------------------------------------------
# 3. 跨线 + 在跑申请 → 409，且原数据零变更（回滚）
# ---------------------------------------------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize('live_state', ['PENDING', 'ACTIVE', 'PAUSED', 'OFFER_SENT'])
def test_rebind_rejected_when_running_application_exists(
    department, hr_user, hrbp_user, two_lines, live_state,
):
    src, dst = two_lines
    demand = _make_demand(department, hr_user, hrbp_user, src)
    pos = _make_position(department, hr_user, src, suffix='run', demand=demand)
    app = _make_application(pos, src, suffix=f'run{live_state[:2]}', state=live_state)

    with pytest.raises(StateTransitionError) as exc:
        DemandService.rebind_demand_process(demand, target_process=dst, actor=hr_user)
    assert '在跑' in str(exc.value) or '候选人' in str(exc.value)

    # 回滚：Demand / Position / Application 三方都不得变
    assert _reload(demand).process_id == src.id
    assert _reload(demand).process_version == 'V1.0'
    assert _reload(pos).process_id == src.id
    assert _reload(app).process_id == src.id
    assert _reload(app).workflow_version == 'V1.0'


# ---------------------------------------------------------------------------
# 4. 跨线但申请已终态 → 放行
# ---------------------------------------------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize('final_state', ['REJECTED', 'WITHDRAWN', 'TIMEOUT', 'ONBOARDED'])
def test_rebind_allowed_when_applications_all_final(
    department, hr_user, hrbp_user, two_lines, final_state,
):
    src, dst = two_lines
    demand = _make_demand(department, hr_user, hrbp_user, src)
    pos = _make_position(department, hr_user, src, suffix='fin', demand=demand)
    _make_application(pos, src, suffix=f'fin{final_state[:2]}', state=final_state)

    _demand, moved = DemandService.rebind_demand_process(demand, target_process=dst, actor=hr_user)

    assert _reload(demand).process_id == dst.id
    assert moved == [pos.id]


# ---------------------------------------------------------------------------
# 5. 目标不可用 → 拒绝，原数据零变更
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_rebind_rejects_archived_target(department, hr_user, hrbp_user, db):
    src = _make_process(suffix='ar-src', code='RB_AR_SRC')
    bad = _make_process(suffix='ar-dst', code='RB_AR_DST', status='ARCHIVED')
    demand = _make_demand(department, hr_user, hrbp_user, src)

    with pytest.raises(StateTransitionError, match='归档'):
        DemandService.rebind_demand_process(demand, target_process=bad, actor=hr_user)
    assert _reload(demand).process_id == src.id


@pytest.mark.django_db
def test_rebind_rejects_non_latest_target(department, hr_user, hrbp_user, db):
    src = _make_process(suffix='nl-src', code='RB_NL_SRC')
    # 同 code 下先建 latest 行再建非 latest 行，避开 uniq_one_latest_per_code 约束；
    # version_seq 也必须错开，否则撞 (code, version_seq) 唯一键。
    _make_process(suffix='nl-dst-latest', code='RB_NL_DST', version='V2.0', is_latest=True, version_seq=2)
    old = _make_process(suffix='nl-dst-old', code='RB_NL_DST', version='V1.0', is_latest=False, version_seq=1)
    demand = _make_demand(department, hr_user, hrbp_user, src)

    with pytest.raises(StateTransitionError, match='最新版'):
        DemandService.rebind_demand_process(demand, target_process=old, actor=hr_user)
    assert _reload(demand).process_id == src.id


@pytest.mark.django_db
def test_rebind_rejects_soft_deleted_target(department, hr_user, hrbp_user, db):
    src = _make_process(suffix='sd-src', code='RB_SD_SRC')
    dead = _make_process(suffix='sd-dst', code='RB_SD_DST', deleted=True)
    demand = _make_demand(department, hr_user, hrbp_user, src)

    with pytest.raises(StateTransitionError, match='已删除'):
        DemandService.rebind_demand_process(demand, target_process=dead, actor=hr_user)
    assert _reload(demand).process_id == src.id


# ---------------------------------------------------------------------------
# 6. 幂等：目标与当前已是同一行 → 无写入
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_rebind_is_idempotent_when_same_process(department, hr_user, hrbp_user, two_lines):
    src, _dst = two_lines
    demand = _make_demand(department, hr_user, hrbp_user, src)

    same, moved = DemandService.rebind_demand_process(demand, target_process=src, actor=hr_user)

    assert moved == []
    assert _reload(demand).process_id == src.id


# ---------------------------------------------------------------------------
# 7. API 契约
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_rebind_api_returns_contract(auth_client, department, hr_user, hrbp_user, two_lines):
    src, dst = two_lines
    demand = _make_demand(department, hr_user, hrbp_user, src)
    pos = _make_position(department, hr_user, src, suffix='api', demand=demand)

    resp = auth_client.post(REBIND_URL.format(id=demand.id), {'targetProcessId': dst.id}, format='json')

    assert resp.status_code == 200, resp.data
    data = resp.data['data']
    assert data['rebound'] is True
    assert data['previous_process_id'] == src.id
    assert data['moved_position_ids'] == [pos.id]
    assert data['demand']['process'] == dst.id
    assert src.reference_count == 0


@pytest.mark.django_db
def test_rebind_api_rejects_running_application_with_409(
    auth_client, department, hr_user, hrbp_user, two_lines,
):
    src, dst = two_lines
    demand = _make_demand(department, hr_user, hrbp_user, src)
    pos = _make_position(department, hr_user, src, suffix='api409', demand=demand)
    _make_application(pos, src, suffix='api409', state='ACTIVE')

    resp = auth_client.post(REBIND_URL.format(id=demand.id), {'targetProcessId': dst.id}, format='json')

    assert resp.status_code == 409, resp.data
    assert _reload(demand).process_id == src.id


@pytest.mark.django_db
def test_rebind_api_unknown_target_returns_404(
    auth_client, department, hr_user, hrbp_user, two_lines,
):
    src, _dst = two_lines
    demand = _make_demand(department, hr_user, hrbp_user, src)

    resp = auth_client.post(REBIND_URL.format(id=demand.id), {'targetProcessId': 'no-such-id'}, format='json')

    assert resp.status_code == 404, resp.data
    assert _reload(demand).process_id == src.id
