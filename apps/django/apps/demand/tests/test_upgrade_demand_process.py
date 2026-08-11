"""T9 需求升级入口回归（规格 §4.1 / §4.2 G3 / §4.3）。

⚠️ **本文件全部用例自带非零 seed 数据。** dev 库实测 ``Demand=0`` / ``Position=0``，
任何依赖库内现状的断言都是"空跑必绿"，等于没测。每条用例自建
``RecruitmentProcess`` 版本链 + ``Demand`` + ``Position``（含软删样本）+
``Application``，断言的是真实写入结果而非空集。

覆盖 G3 五条 + BR-102 锁定钉：

1. Demand 指非最新版且其下 ≥2 个 live Position → 三方 process_id 均改指目标版本，
   ``process_version == 'V2.0'``（**断言 V 前缀**），moved 含这些 position id。
2. 目标版本已归档 / 非 latest / 跨流程线 / 流程线无可用最新版 / 需求未关联流程
   → 409，且 Demand/Position **一个字段都没变**（断言回滚）。
3. Demand 下混有**软删** Position → 软删那个不被改指。
4. Demand 无关联 Position → 仅升 Demand，moved == []，不报错。
5. Demand 已在最新版 → 200 幂等，``upgraded == false``，不产生任何写入。
6. BR-102 硬红线：该 Demand 下已有 Application 时，升级后 ``Application.process_id``
   与 ``workflow_version`` **均不得变化**（§4.3，"不级联"不是不可行而是违规故不做）。
"""
from __future__ import annotations

import pytest
from django.utils import timezone

from apps.common.exceptions import StateTransitionError
from apps.demand.models import Demand, DemandState
from apps.demand.services import DemandService
from apps.position.models import Position, PositionState
from apps.process.models import RecruitmentProcess

PROCESS_LINE_CODE = 'W_T9_LINE'


def _reload(obj):
    """从库里重新取一份实例。

    **不要用 ``instance.refresh_from_db()``**：本仓 ``Demand`` / ``Position`` /
    ``Application`` 的 ``state`` 都是 ``FSMField(protected=True)``，而
    ``refresh_from_db()`` 内部是逐字段 ``setattr``，会被 django-fsm 拦成
    ``AttributeError: Direct state modification is not allowed``——报错点在测试代码里，
    与被测逻辑无关，极易误判成产品 bug。
    """
    return type(obj)._default_manager.get(pk=obj.pk)


# ---------------------------------------------------------------------------
# seed helpers —— 一律显式建数据，不依赖库内现状
# ---------------------------------------------------------------------------
def _make_process(
    *,
    suffix: str,
    version_seq: int,
    current_version: str,
    is_latest: bool,
    status: str = 'ENABLED',
    code: str = PROCESS_LINE_CODE,
) -> RecruitmentProcess:
    """建一个流程版本行。

    注意 ``RecruitmentProcess`` 上有三条 DB 约束：``(code, version_seq)`` 唯一、
    ``(code, current_version)`` 唯一、每 code 至多一行 ``is_latest=True``。
    所有 fixture 都必须满足，否则报 IntegrityError 而非业务失败。
    """
    return RecruitmentProcess.objects.create(
        id=f'proc-t9-{suffix}',
        code=code,
        name=f'T9 流程 {suffix}',
        current_version=current_version,
        version_seq=version_seq,
        is_latest=is_latest,
        status=status,
        is_template=False,
        is_enabled=True,
        archived_at=timezone.now() if status == 'ARCHIVED' else None,
    )


def _make_demand(department, requester, hr, process, *, suffix: str = '1') -> Demand:
    return Demand.objects.create(
        id=f'demand-t9-{suffix}',
        code=f'D-T9-{suffix}',
        title=f'T9 测试需求 {suffix}',
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
        id=f'pos-t9-{suffix}',
        code=f'P-T9-{suffix}',
        title=f'T9 测试职位 {suffix}',
        department=department,
        hiring_manager=user,
        owner=user,
        headcount=1,
        process=process,
        process_version=process.current_version,
        demand=demand,
        state=PositionState.DRAFT,
    )


@pytest.fixture
def version_line(db):
    """同一流程线的两个版本：V1.0（旧，非 latest）+ V2.0（新，latest）。"""
    old = _make_process(suffix='v1', version_seq=1, current_version='V1.0', is_latest=False)
    new = _make_process(suffix='v2', version_seq=2, current_version='V2.0', is_latest=True)
    return old, new


# ---------------------------------------------------------------------------
# G3-1：主路径 —— Demand + 其 ≥2 个 live Position 一起改指，且带 V 前缀
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_upgrade_moves_demand_and_all_live_positions(
    department, hr_user, hrbp_user, version_line,
):
    old, new = version_line
    demand = _make_demand(department, hr_user, hrbp_user, old)
    pos_a = _make_position(department, hr_user, old, suffix='a', demand=demand)
    pos_b = _make_position(department, hr_user, old, suffix='b', demand=demand)

    # 前置事实：seed 确实非空且都在旧版本上（防"空跑必绿"）
    assert demand.positions.filter(deleted_at__isnull=True).count() == 2
    assert demand.process_id == old.id
    assert demand.process_version == 'V1.0'

    _upgraded, moved = DemandService.upgrade_demand_process(demand, actor=hr_user)

    fresh_demand = _reload(demand)
    fresh_a = _reload(pos_a)
    fresh_b = _reload(pos_b)

    assert fresh_demand.process_id == new.id
    assert fresh_a.process_id == new.id
    assert fresh_b.process_id == new.id

    # V 前缀是 G2 的核心诉求：time_limit 按字符串精确匹配时格式漂移会静默落空
    assert fresh_demand.process_version == 'V2.0'
    assert fresh_a.process_version == 'V2.0'
    assert fresh_b.process_version == 'V2.0'

    assert sorted(moved) == sorted([pos_a.id, pos_b.id])


# ---------------------------------------------------------------------------
# G3-3：软删 Position 不得被改指（_live_children 同款陷阱，本仓惯犯）
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_upgrade_skips_soft_deleted_positions(
    department, hr_user, hrbp_user, version_line,
):
    old, new = version_line
    demand = _make_demand(department, hr_user, hrbp_user, old)
    live = _make_position(department, hr_user, old, suffix='live', demand=demand)
    dead = _make_position(department, hr_user, old, suffix='dead', demand=demand)
    dead.soft_delete()
    assert _reload(dead).deleted_at is not None

    _, moved = DemandService.upgrade_demand_process(demand, actor=hr_user)

    fresh_live = _reload(live)
    fresh_dead = _reload(dead)

    assert fresh_live.process_id == new.id
    assert fresh_live.process_version == 'V2.0'
    # 软删职位必须原封不动
    assert fresh_dead.process_id == old.id, '软删 Position 被改指了——遍历漏了 deleted_at 过滤'
    assert fresh_dead.process_version == 'V1.0'
    assert moved == [live.id]
    assert dead.id not in moved


# ---------------------------------------------------------------------------
# G3-4：无关联 Position → 仅升 Demand，不报错
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_upgrade_demand_without_positions(
    department, hr_user, hrbp_user, version_line,
):
    old, new = version_line
    demand = _make_demand(department, hr_user, hrbp_user, old)
    # 建一个**不属于该需求**的孤儿职位，验证不会被误伤（跨需求污染防线）
    orphan = _make_position(department, hr_user, old, suffix='orphan', demand=None)

    _upgraded, moved = DemandService.upgrade_demand_process(demand, actor=hr_user)

    fresh_demand = _reload(demand)
    fresh_orphan = _reload(orphan)

    assert fresh_demand.process_id == new.id
    assert fresh_demand.process_version == 'V2.0'
    assert moved == []
    assert fresh_orphan.process_id == old.id, '不属于该需求的职位被改指了——遍历用错了过滤条件'


# ---------------------------------------------------------------------------
# G3-5：已在最新版 → 幂等，无任何写入
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_upgrade_is_idempotent_when_already_latest(
    department, hr_user, hrbp_user, version_line,
):
    _old, new = version_line
    demand = _make_demand(department, hr_user, hrbp_user, new)
    pos = _make_position(department, hr_user, new, suffix='latest', demand=demand)
    before_updated_at = _reload(demand).updated_at

    _upgraded, moved = DemandService.upgrade_demand_process(demand, actor=hr_user)

    fresh_demand = _reload(demand)
    fresh_pos = _reload(pos)

    assert fresh_demand.process_id == new.id
    assert moved == []
    # 幂等 = 一次写入都不许有，updated_at (auto_now) 是最灵敏的探针
    assert fresh_demand.updated_at == before_updated_at
    assert fresh_pos.process_id == new.id


# ---------------------------------------------------------------------------
# G3-2：非法目标一律 409，且 Demand / Position 一个字段都不许变
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_upgrade_rejects_archived_target_and_rolls_back(
    department, hr_user, hrbp_user, version_line,
):
    old, _new = version_line
    archived = _make_process(
        suffix='v3-archived', version_seq=3, current_version='V3.0',
        is_latest=False, status='ARCHIVED',
    )
    demand = _make_demand(department, hr_user, hrbp_user, old)
    pos = _make_position(department, hr_user, old, suffix='arch', demand=demand)

    with pytest.raises(StateTransitionError) as exc:
        DemandService.upgrade_demand_process(demand, actor=hr_user, target_process=archived)
    assert exc.value.status_code == 409

    fresh_demand = _reload(demand)
    fresh_pos = _reload(pos)
    assert fresh_demand.process_id == old.id
    assert fresh_demand.process_version == 'V1.0'
    assert fresh_pos.process_id == old.id
    assert fresh_pos.process_version == 'V1.0'


@pytest.mark.django_db
def test_upgrade_rejects_non_latest_target(
    department, hr_user, hrbp_user, version_line,
):
    """显式传一个 ENABLED 但 is_latest=False 的版本 → 拒绝（不能倒退/横跳）。"""
    old, new = version_line
    demand = _make_demand(department, hr_user, hrbp_user, new)
    pos = _make_position(department, hr_user, new, suffix='nonlatest', demand=demand)

    with pytest.raises(StateTransitionError) as exc:
        DemandService.upgrade_demand_process(demand, actor=hr_user, target_process=old)
    assert exc.value.status_code == 409
    assert '最新版' in exc.value.message

    assert _reload(demand).process_id == new.id
    assert _reload(pos).process_id == new.id


@pytest.mark.django_db
def test_upgrade_rejects_cross_process_line_target(
    department, hr_user, hrbp_user, version_line,
):
    """目标属于另一条流程线（不同 code）→ 拒绝。跨线迁移是 T8 的独立动作。"""
    old, _new = version_line
    other_line = _make_process(
        suffix='other', version_seq=1, current_version='V1.0',
        is_latest=True, code='W_T9_OTHER_LINE',
    )
    demand = _make_demand(department, hr_user, hrbp_user, old)

    with pytest.raises(StateTransitionError) as exc:
        DemandService.upgrade_demand_process(demand, actor=hr_user, target_process=other_line)
    assert exc.value.status_code == 409
    assert '同一流程线' in exc.value.message

    assert _reload(demand).process_id == old.id


@pytest.mark.django_db
def test_upgrade_rejects_when_line_has_no_available_latest(
    department, hr_user, hrbp_user,
):
    """整条流程线没有可用最新版 → 抛 409，**不得静默返回 (demand, [])**。

    静默返回会把"流程线整条被归档"和"已是最新"混成同一个返回值（fail-silent），
    调用方无法区分，UI 会显示"升级成功"而实际什么都没发生。
    """
    lonely = _make_process(
        suffix='lonely', version_seq=1, current_version='V1.0',
        is_latest=False, code='W_T9_NO_LATEST',
    )
    demand = _make_demand(department, hr_user, hrbp_user, lonely)

    with pytest.raises(StateTransitionError) as exc:
        DemandService.upgrade_demand_process(demand, actor=hr_user)
    assert exc.value.status_code == 409
    assert '没有可用的最新版本' in exc.value.message

    assert _reload(demand).process_id == lonely.id


@pytest.mark.django_db
def test_upgrade_rejects_demand_without_process(
    department, hr_user, hrbp_user, version_line,
):
    """需求未关联流程 → 409，而不是 ``demand.process.code`` 的 AttributeError(500)。"""
    old, _new = version_line
    demand = _make_demand(department, hr_user, hrbp_user, old)
    demand.process_id = None  # 内存态模拟（DB 层 process 非空，此守卫防的是 500）

    with pytest.raises(StateTransitionError) as exc:
        DemandService.upgrade_demand_process(demand, actor=hr_user)
    assert exc.value.status_code == 409
    assert '未关联流程' in exc.value.message


# ---------------------------------------------------------------------------
# §1.3.2：审计快照必须早于赋值
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_audit_log_snapshots_old_process_id_before_reassignment(
    caplog, department, hr_user, hrbp_user, version_line,
):
    """审计日志里的"旧 process id"必须是**改指前**的值。

    ``old_pid`` 只进日志、不进返回值。若不显式断言，把快照挪到
    ``demand.process = target_process`` **之后**（读后写）不会被任何用例发现——
    审计从此永远记录"从新版升到新版"，且静默无痕。§1.3.2 要求快照早于赋值，
    这条用例就是那条规则的执行力。
    """
    old, new = version_line
    demand = _make_demand(department, hr_user, hrbp_user, old)

    with caplog.at_level('INFO', logger='apps.demand.services'):
        DemandService.upgrade_demand_process(demand, actor=hr_user)

    messages = [r.getMessage() for r in caplog.records]
    upgrade_logs = [m for m in messages if 'upgraded process' in m]
    assert upgrade_logs, f'未记录升级审计日志，实际日志：{messages}'
    entry = upgrade_logs[0]
    assert f'{old.id} → {new.id}' in entry, (
        f'审计日志的旧 process id 不是改指前的值（快照晚于赋值？）：{entry}'
    )


# ---------------------------------------------------------------------------
# BR-102 锁定钉：升级 Demand **绝不**级联改指在跑的 Application（§4.3 硬红线）
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_upgrade_does_not_touch_running_applications(
    department, hr_user, hrbp_user, version_line,
):
    from apps.application.models import Application, ApplicationState
    from apps.candidate.models import Candidate, CandidateState

    old, new = version_line
    demand = _make_demand(department, hr_user, hrbp_user, old)
    pos = _make_position(department, hr_user, old, suffix='br102', demand=demand)
    candidate = Candidate.objects.create(
        id='cand-t9-br102',
        name='BR102 候选人',
        phone='13700001102',
        current_state=CandidateState.APPLIED,
    )
    app = Application.objects.create(
        id='app-t9-br102',
        code='APP-T9-BR102',
        candidate=candidate,
        position=pos,
        process=old,
        workflow_version=old.current_version,
        state=ApplicationState.ACTIVE,
    )
    assert app.process_id == old.id and app.workflow_version == 'V1.0'

    _upgraded, moved = DemandService.upgrade_demand_process(demand, actor=hr_user)

    fresh_demand = _reload(demand)
    fresh_pos = _reload(pos)
    fresh_app = _reload(app)

    # Demand + Position 改指了
    assert fresh_demand.process_id == new.id
    assert fresh_pos.process_id == new.id
    assert moved == [pos.id]
    # Application 一动不动 —— BR-102「已在跑的候选人走创建时的版本」
    assert fresh_app.process_id == old.id, 'BR-102 被破坏：升级 Demand 级联改指了在跑 Application'
    assert fresh_app.workflow_version == 'V1.0', 'BR-102 被破坏：在跑 Application 的冻结版本号被改写'


# ---------------------------------------------------------------------------
# HTTP 契约（§4.1 + 裁决 4）
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestUpgradeProcessVersionEndpoint:
    """``POST /api/v1/demands/{id}/upgrade-process-version/`` 的状态码与响应体契约。"""

    def test_success_returns_200_with_moved_ids(
        self, auth_client, department, hr_user, hrbp_user, version_line,
    ):
        old, new = version_line
        demand = _make_demand(department, hr_user, hrbp_user, old)
        pos = _make_position(department, hr_user, old, suffix='http-ok', demand=demand)

        resp = auth_client.post(
            f'/api/v1/demands/{demand.id}/upgrade-process-version/', {}, format='json',
        )

        assert resp.status_code == 200, resp.content
        payload = resp.data['data']
        assert payload['upgraded'] is True
        assert payload['moved_position_ids'] == [pos.id]
        assert payload['previous_process_id'] == old.id
        assert payload['demand']['process'] == new.id
        assert payload['demand']['process_version'] == 'V2.0'

    def test_idempotent_returns_200_upgraded_false(
        self, auth_client, department, hr_user, hrbp_user, version_line,
    ):
        """已在最新版是**正常状态而非冲突** → 200，与 archive/clone 的 409 语义不同。"""
        _old, new = version_line
        demand = _make_demand(department, hr_user, hrbp_user, new)

        resp = auth_client.post(
            f'/api/v1/demands/{demand.id}/upgrade-process-version/', {}, format='json',
        )

        assert resp.status_code == 200, resp.content
        payload = resp.data['data']
        assert payload['upgraded'] is False
        assert payload['moved_position_ids'] == []

    def test_archived_target_returns_409(
        self, auth_client, department, hr_user, hrbp_user, version_line,
    ):
        old, _new = version_line
        archived = _make_process(
            suffix='v3-http-archived', version_seq=3, current_version='V3.0',
            is_latest=False, status='ARCHIVED',
        )
        demand = _make_demand(department, hr_user, hrbp_user, old)

        resp = auth_client.post(
            f'/api/v1/demands/{demand.id}/upgrade-process-version/',
            {'target_process_id': archived.id}, format='json',
        )

        assert resp.status_code == 409, resp.content
        assert resp.data['code'] == 'state_transition_error'
        assert _reload(demand).process_id == old.id

    def test_unknown_target_process_returns_404(
        self, auth_client, department, hr_user, hrbp_user, version_line,
    ):
        old, _new = version_line
        demand = _make_demand(department, hr_user, hrbp_user, old)

        resp = auth_client.post(
            f'/api/v1/demands/{demand.id}/upgrade-process-version/',
            {'target_process_id': 'no-such-process'}, format='json',
        )

        assert resp.status_code == 404, resp.content
        assert _reload(demand).process_id == old.id

    def test_requires_authentication(self, api_client, department, hr_user, hrbp_user, version_line):
        old, _new = version_line
        demand = _make_demand(department, hr_user, hrbp_user, old)

        resp = api_client.post(
            f'/api/v1/demands/{demand.id}/upgrade-process-version/', {}, format='json',
        )

        assert resp.status_code == 401
        assert _reload(demand).process_id == old.id


# ---------------------------------------------------------------------------
# G2 default 翻转的直接锁定（防有人把 default 改回 '1.0'）
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_process_version_defaults_use_v_prefix():
    """``Demand`` / ``Position`` 的 ``process_version`` default 必须是 ``'V1.0'``。

    旧 default ``'1.0'`` 与 service 层实际写入的 ``process.current_version``（``'V1.0'``）
    自相矛盾；``time_limit`` 按版本字符串精确匹配时，格式不一致会**静默**匹配空集、
    限时规则全失效且不抛异常。
    """
    assert Demand._meta.get_field('process_version').default == 'V1.0'
    assert Position._meta.get_field('process_version').default == 'V1.0'
