"""简历正式锁定人规则引擎（apps/candidate/lock_engine.py）行为测试。

穿透真实 DB 链路验证（不 mock 模型、不手搓 dict 冒充决策结果）：

- PRD 4.2 优先级链逐条命中：分配人 → 继承 → 内推兜底 → HRBP → owner；
- **不变量**：任何分支算出的正式锁定人，必须是目标职位权限人之一
  （负责人 / 共享人 / 抢单人），否则「能操作却看不到」或「看得到不能操作」；
- HRBP 走 Demand 动态字段（resource='Demand', key='hrbp'），存量无值时降级 owner；
- 人才库 pool_kind 六类归属规则（独享/个人/入职=归属人，共享/内推/通用=无锁定人）；
- 写入口幂等 + 审计可追溯（reason 原因码落 CandidateHistory）。
"""
import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.application.models import Application
from apps.candidate.lock_engine import (
    HRBP_FIELD_KEY,
    HRBP_RESOURCE,
    LockReason,
    _coerce_user_id,
    apply_formal_lock,
    apply_pool_lock,
    decide_formal_lock,
    decide_pool_lock,
    is_position_authority,
    maybe_grant_temp_lock,
    position_authority_ids,
    resolve_hrbp,
)
from apps.candidate.models import Candidate, CandidateHistory
from apps.core.models import Department
from apps.demand.models import Demand
from apps.dynamic_field.models import DynamicFieldValue
from apps.position.models import Position
from apps.process.models import ProcessStageLink, RecruitmentProcess, RecruitmentStage
from apps.talent_pool.models import TalentPoolEntry

pytestmark = pytest.mark.django_db


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _user(tag: str = "u"):
    return get_user_model().objects.create_user(username=_uid(tag), password="Test@1234")


def _cand(**kwargs) -> Candidate:
    return Candidate.objects.create(name=kwargs.pop("name", "引擎候选人"), phone=_uid("138"), **kwargs)


def _dept():
    return Department.objects.create(id=_uid("dept"), name=_uid("BG"), code=_uid("BGC"))


def _process():
    process = RecruitmentProcess.objects.create(
        code=_uid("PROC"), name="社招标准流程", current_version="V1.0", version_seq=1, is_latest=True,
    )
    stage = RecruitmentStage.objects.create(code=_uid("S"), name=_uid("初评"), stage_type="INTERVIEW")
    ProcessStageLink.objects.create(process=process, stage=stage, order=1)
    return process


def _demand(dept, process, requester):
    return Demand.objects.create(
        code=_uid("DEM"), title=_uid("需求"), department=dept,
        requested_by=requester, hr=requester, process=process,
        headcount=1, demand_type="新增", priority="中", talent_nature="正式",
    )


def _position(owner, *, assistants=(), demand=None, process=None, dept=None):
    position = Position.objects.create(
        code=_uid("POS"), title="客服专员", department=dept or _dept(),
        hiring_manager=owner, owner=owner, process=process or _process(), demand=demand,
    )
    if assistants:
        position.assistants.add(*assistants)
    return position


def _set_hrbp(demand, user, *, value=None):
    """在 Demand 上写 HRBP 动态字段（真实落 DynamicFieldValue，不走内存假数据）。"""
    DynamicFieldValue.objects.update_or_create(
        resource=HRBP_RESOURCE, entity_id=str(demand.pk), field_key=HRBP_FIELD_KEY,
        defaults={'value': value if value is not None else str(user.pk)},
    )


# ============================ PRD 4.2 优先级链 ============================

def test_assigner_is_authority_wins():
    """L1：分配人是新职位权限人（共享人）→ 分配人成为正式锁定人。"""
    owner, assistant, stranger = _user("owner"), _user("assist"), _user("stranger")
    position = _position(owner, assistants=[assistant])
    c = _cand()

    decision = apply_formal_lock(c, position=position, assigned_by=assistant, actor=stranger)

    c.refresh_from_db()
    assert decision.reason == LockReason.ASSIGNER_IS_AUTHORITY
    assert c.formal_locked_by_id == assistant.pk, '分配人是权限人时应由其锁定'


def test_previous_lock_owner_inherits_when_assigner_is_stranger():
    """L2：分配人是陌生人（非权限人）→ 原锁定人是权限人则继承，不被陌生人抢走。"""
    owner, previous = _user("owner"), _user("prev")
    stranger = _user("stranger")
    position = _position(owner, assistants=[previous])
    c = _cand()
    c.formal_locked_by = previous
    c.save(update_fields=['formal_locked_by'])

    decision = apply_formal_lock(c, position=position, assigned_by=stranger, actor=stranger)

    c.refresh_from_db()
    assert decision.reason == LockReason.PREVIOUS_IS_AUTHORITY
    assert c.formal_locked_by_id == previous.pk, '陌生人分配不得夺走锁定权'


def test_fallback_to_owner_when_hrbp_missing():
    """L5：无人符合条件且 HRBP 未录（存量真实情况）→ 回退职位负责人 owner。"""
    owner = _user("owner")
    stranger = _user("stranger")
    position = _position(owner)          # 无 demand → HRBP 必然取不到
    c = _cand()

    decision = apply_formal_lock(c, position=position, assigned_by=stranger, actor=stranger)

    c.refresh_from_db()
    assert decision.reason == LockReason.POSITION_OWNER
    assert c.formal_locked_by_id == owner.pk


def test_hrbp_wins_over_owner_when_authority():
    """L4：HRBP 已录且是职位权限人 → HRBP 优先于 owner 兜底。"""
    owner, hrbp_user = _user("owner"), _user("hrbp")
    requester = _user("req")
    dept, process = _dept(), _process()
    demand = _demand(dept, process, requester)
    _set_hrbp(demand, hrbp_user)
    position = _position(owner, assistants=[hrbp_user], demand=demand, process=process, dept=dept)
    c = _cand()

    decision = apply_formal_lock(c, position=position, actor=requester)

    c.refresh_from_db()
    assert resolve_hrbp(position).pk == hrbp_user.pk, 'HRBP 必须能从 Demand 动态字段读出'
    assert decision.reason == LockReason.POSITION_HRBP
    assert c.formal_locked_by_id == hrbp_user.pk


def test_hrbp_not_authority_degrades_to_owner():
    """关键：HRBP 不是权限人 → 降级 owner，绝不把操作权给看不到该职位的人。"""
    owner, hrbp_user = _user("owner"), _user("hrbp")
    requester = _user("req")
    dept, process = _dept(), _process()
    demand = _demand(dept, process, requester)
    _set_hrbp(demand, hrbp_user)
    # 刻意**不**把 hrbp_user 加进 assistants —— 他是权限人之外的人
    position = _position(owner, demand=demand, process=process, dept=dept)
    c = _cand()

    decision = apply_formal_lock(c, position=position, actor=requester)

    c.refresh_from_db()
    assert resolve_hrbp(position).pk == hrbp_user.pk
    assert is_position_authority(position, hrbp_user) is False
    assert decision.reason == LockReason.POSITION_OWNER
    assert c.formal_locked_by_id == owner.pk


@pytest.mark.parametrize('scenario', [
    'assigner_assistant', 'assigner_owner', 'assigner_grabber',
    'inherit_previous', 'hrbp', 'owner_fallback',
])
def test_invariant_decision_is_always_position_authority(scenario):
    """不变量：任何场景算出的锁定人都必须 ∈ 职位权限人集合（防权限链断裂）。"""
    owner = _user("owner")
    assistant = _user("assist")
    grabber = _user("grab")
    hrbp_user = _user("hrbp")
    stranger = _user("stranger")
    requester = _user("req")

    dept, process = _dept(), _process()
    demand = _demand(dept, process, requester)
    _set_hrbp(demand, hrbp_user)
    position = _position(owner, assistants=[assistant, hrbp_user], demand=demand, process=process, dept=dept)

    c = _cand()
    # 抢单人通过真实投递落库（position_authority_ids 会查 Application.grabbed_by）
    Application.objects.create(
        code=_uid("APP"), candidate=c, position=position, process=process,
        workflow_version="V1.0", is_grabbed=True, grabbed_by=grabber,
    )
    c.refresh_from_db()

    # 默认：陌生人来分配 → L1/L2 均落空，逼出兜底链
    assigned_by = stranger
    if scenario == 'inherit_previous':
        c.formal_locked_by = assistant
        c.save(update_fields=['formal_locked_by'])
    elif scenario == 'assigner_assistant':
        assigned_by = assistant
    elif scenario == 'assigner_owner':
        assigned_by = owner
    elif scenario == 'assigner_grabber':
        assigned_by = grabber
    elif scenario == 'owner_fallback':
        # 把 HRBP 移出权限人 → 让 HRBP 分支落空，真正逼出 owner 兜底
        position.assistants.remove(hrbp_user)

    decision = decide_formal_lock(c, position=position, assigned_by=assigned_by)

    assert decision.user is not None, f'{scenario} 必须算出锁定人'
    authority = position_authority_ids(position)
    assert str(decision.user.pk) in authority, \
        f'{scenario} 违反不变量：{decision.user.pk} 不在职位权限人 {authority} 内'
    if scenario == 'hrbp':
        assert decision.reason == LockReason.POSITION_HRBP
    if scenario == 'owner_fallback':
        assert decision.reason == LockReason.POSITION_OWNER
        assert decision.user.pk == owner.pk


def test_no_position_keeps_existing_lock():
    """未分配至职位（position=None）→ 决策为 None，且**不清空**已生效的锁定人。"""
    someone = _user("someone")
    c = _cand()
    c.formal_locked_by = someone
    c.save(update_fields=['formal_locked_by'])

    decision = apply_formal_lock(c, position=None, actor=someone)

    c.refresh_from_db()
    assert decision.reason == LockReason.NO_POSITION_NO_LOCK
    assert c.formal_locked_by_id == someone.pk, '无法保证不变量时不得清空锁定人'


def test_apply_is_idempotent_no_audit_noise():
    """同一结果重复 apply → applied=False，不产生重复审计（防操作记录噪声）。"""
    owner, assistant = _user("owner"), _user("assist")
    position = _position(owner, assistants=[assistant])
    c = _cand()

    first = apply_formal_lock(c, position=position, assigned_by=assistant, actor=assistant)
    second = apply_formal_lock(c, position=position, assigned_by=assistant, actor=assistant)

    assert first.applied is True
    assert second.applied is False
    histories = CandidateHistory.objects.filter(candidate=c, action='LOCK_CHANGED')
    assert histories.count() == 1, '重复决策不得重复落审计'


def test_lock_change_audit_records_reason_and_both_ends():
    """锁定人变更审计：记录 from/to 与 reason 原因码（事后可追溯"凭什么是他"）。"""
    owner, assistant, grabber = _user("owner"), _user("assist"), _user("grab")
    position = _position(owner, assistants=[assistant])
    c = _cand()
    c.formal_locked_by = assistant
    c.save(update_fields=['formal_locked_by'])

    apply_formal_lock(c, position=position, assigned_by=grabber, actor=grabber)
    # grabber 非权限人 → 继承 assistant；再让 grabber 成为权限人后重算应换人
    Application.objects.create(
        code=_uid("APP"), candidate=c, position=position, process=position.process,
        workflow_version="V1.0", is_grabbed=True, grabbed_by=grabber,
    )
    c.refresh_from_db()
    decision = apply_formal_lock(c, position=position, assigned_by=grabber, actor=grabber)

    assert decision.applied is True
    history = CandidateHistory.objects.filter(candidate=c, action='LOCK_CHANGED').order_by('-seq').first()
    assert history is not None
    assert history.detail['reason'] == decision.reason
    assert history.detail['kind'] == 'FORMAL'
    assert history.detail['from']['id'] == str(assistant.pk)
    assert history.detail['to']['id'] == str(grabber.pk)


# ============================ 人才库锁定联动 ============================

def test_pool_exclusive_owner_becomes_lock():
    """独享库 → 库归属人为正式锁定人。"""
    holder = _user("holder")
    c = _cand()
    entry = TalentPoolEntry.objects.create(
        candidate=c, source='MANUAL',
        pool_kind=TalentPoolEntry.PoolKind.CAMPUS_EXCLUSIVE, pool_owner=holder,
    )

    decision = apply_pool_lock(c, entry, actor=holder)

    c.refresh_from_db()
    assert decision.reason == LockReason.POOL_EXCLUSIVE_OWNER
    assert c.formal_locked_by_id == holder.pk


@pytest.mark.parametrize('kind,expected_reason', [
    (TalentPoolEntry.PoolKind.CAMPUS_EXCLUSIVE, LockReason.POOL_EXCLUSIVE_OWNER),
    (TalentPoolEntry.PoolKind.PERSONAL, LockReason.POOL_PERSONAL_OWNER),
    (TalentPoolEntry.PoolKind.ONBOARD, LockReason.POOL_ONBOARD_OWNER),
])
def test_pool_kinds_with_owner_lock_to_owner(kind, expected_reason):
    """独享 / 个人 / 入职 三类库 → 锁定到 pool_owner。"""
    holder = _user("holder")
    entry = TalentPoolEntry.objects.create(candidate=_cand(), source='MANUAL', pool_kind=kind, pool_owner=holder)
    decision = decide_pool_lock(entry)
    assert decision.reason == expected_reason
    assert decision.user.pk == holder.pk


@pytest.mark.parametrize('kind', [
    TalentPoolEntry.PoolKind.CAMPUS_SHARED,
    TalentPoolEntry.PoolKind.REFERRAL,
    TalentPoolEntry.PoolKind.GENERAL,
])
def test_pool_public_kinds_have_no_lock_owner(kind):
    """共享 / 内推 / 通用 三类公共资源池 → 无锁定人（PRD 明确规定）。"""
    holder = _user("holder")
    entry = TalentPoolEntry.objects.create(candidate=_cand(), source='MANUAL', pool_kind=kind, pool_owner=holder)
    decision = decide_pool_lock(entry)
    assert decision.user is None
    assert decision.reason == LockReason.POOL_NO_LOCK


def test_pool_shared_clears_existing_lock():
    """进共享库 → 已生效的正式锁定人应被**清空**（与分配场景的策略差异点）。"""
    someone = _user("someone")
    c = _cand()
    c.formal_locked_by = someone
    c.save(update_fields=['formal_locked_by'])
    entry = TalentPoolEntry.objects.create(
        candidate=c, source='MANUAL', pool_kind=TalentPoolEntry.PoolKind.CAMPUS_SHARED,
    )

    decision = apply_pool_lock(c, entry, actor=someone)

    c.refresh_from_db()
    assert decision.applied is True
    assert c.formal_locked_by_id is None
    assert CandidateHistory.objects.filter(candidate=c, action='LOCK_CHANGED').count() == 1


def test_pool_owner_missing_means_no_lock():
    """库归属人缺失（数据不全）→ 视为无锁定人，绝不退回"随便一个人"。"""
    entry = TalentPoolEntry.objects.create(
        candidate=_cand(), source='MANUAL', pool_kind=TalentPoolEntry.PoolKind.PERSONAL,
    )
    decision = decide_pool_lock(entry)
    assert decision.user is None


# ============================ 临时锁场景 ============================

def test_temp_lock_granted_when_uploader_is_not_referrer():
    """上传时上传人 ≠ 提供人 → 上传人获 72h 临时锁定。"""
    referrer = _user("referrer")
    uploader = _user("uploader")
    c = _cand(referrer=referrer)

    assert maybe_grant_temp_lock(c, uploader) is True
    c.refresh_from_db()
    assert c.temp_locked_by_id == uploader.pk
    assert c.temp_lock_expires_at is not None


def test_temp_lock_skipped_when_uploader_is_referrer():
    """上传人 == 提供人 → 不授予（本来就是他的简历，无需临时锁）。"""
    referrer = _user("referrer")
    c = _cand(referrer=referrer)
    assert maybe_grant_temp_lock(c, referrer) is False
    c.refresh_from_db()
    assert c.temp_locked_by_id is None


def test_temp_lock_skipped_without_referrer():
    """无提供人 → 无"抢别人简历"风险，不授予临时锁。"""
    c = _cand()
    assert maybe_grant_temp_lock(c, _user("uploader")) is False


# ============================ PERSON 值解析容错 ============================

@pytest.mark.parametrize('raw,expected', [
    ('42', '42'),
    (42, '42'),
    (['42'], '42'),
    ({'id': '42'}, '42'),
    ({'user_id': 42}, '42'),
    ({'value': '42'}, '42'),
    (None, None),
    ('', None),
    ({}, None),
    ([], None),
])
def test_coerce_user_id_tolerates_shapes(raw, expected):
    """PERSON 动态字段值结构无生产样例 → 容错解析多种形态，解析不出返回 None 而非臆造。"""
    assert _coerce_user_id(raw) == expected
