"""锁定引擎**接线穿透**测试 —— 证明引擎真的接进了业务链路，不是"装好了没通电"。

教训来源（项目铁律）：曾出现「三处参数透传被丢，测试手搓 dict 绕过 → 250 passed 全绿
但生产 100% 失效」。故本文件**刻意不走**「直接调引擎函数」的捷径，而是从业务入口
（投递创建服务 / 批量导入服务）发起，断言落库结果 —— 接线断了这里必然红。

覆盖三个真实入口：
1. ``ApplicationService.create_application``（简历分配至职位）
2. ``BulkCreateService.create_batch`` position 方向（新增候选人直接分配职位）
3. ``BulkCreateService.create_batch`` talent 方向（新增候选人直接入库）
"""
import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.add_candidate.services.bulk_create import BulkCreateDraft, BulkCreateService
from apps.application.services import ApplicationCreateData, ApplicationService
from apps.candidate.models import Candidate, CandidateHistory
from apps.core.models import Department
from apps.position.models import Position
from apps.process.models import ProcessStageLink, RecruitmentProcess, RecruitmentStage
from apps.talent_pool.models import TalentPoolEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client(hr_user):
    """已认证客户端（hr_user 来自 tests/fixtures_common.py）。"""
    client = APIClient()
    client.force_authenticate(user=hr_user)
    return client


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _user(tag: str = "u"):
    return get_user_model().objects.create_user(username=_uid(tag), password="Test@1234")


def _cand(**kwargs) -> Candidate:
    return Candidate.objects.create(name=kwargs.pop("name", "接线候选人"), phone=_uid("138"), **kwargs)


def _process_with_required_stage():
    """建流程 + 一个**必经**阶段（create_application 要求首个必经阶段存在）。"""
    process = RecruitmentProcess.objects.create(
        code=_uid("PROC"), name="社招标准流程", current_version="V1.0", version_seq=1, is_latest=True,
    )
    stage = RecruitmentStage.objects.create(code=_uid("S"), name=_uid("初评"), stage_type="INTERVIEW")
    ProcessStageLink.objects.create(process=process, stage=stage, order=1, is_required=True)
    return process


def _position(owner, *, assistants=(), process=None):
    dept = Department.objects.create(id=_uid("dept"), name=_uid("BG"), code=_uid("BGC"))
    position = Position.objects.create(
        code=_uid("POS"), title="客服专员", department=dept,
        hiring_manager=owner, owner=owner, process=process or _process_with_required_stage(),
    )
    if assistants:
        position.assistants.add(*assistants)
    return position


# ============================ 1. 投递创建（分配至职位） ============================

def test_create_application_locks_to_assigner_when_he_is_authority():
    """分配人是职位共享人 → 分配后他就是正式锁定人，且分配人/分配状态同步落库。"""
    owner, assistant = _user("owner"), _user("assist")
    position = _position(owner, assistants=[assistant])
    c = _cand()

    ApplicationService.create_application(ApplicationCreateData(
        candidate_id=c.pk, position_id=position.pk, actor=assistant,
    ))

    c.refresh_from_db()
    assert c.assigned_by_id == assistant.pk, '职位分配人必须落库'
    assert c.assign_state == Candidate.AssignState.ASSIGNED.value, '分配后不再是待分配'
    assert c.formal_locked_by_id == assistant.pk, '分配人是权限人 → 由其锁定'


def test_create_application_falls_back_to_owner_for_stranger_assigner():
    """陌生人来分配 → 锁定人回退职位负责人（守住"锁定人必为权限人"不变量）。"""
    owner, stranger = _user("owner"), _user("stranger")
    position = _position(owner)
    c = _cand()

    ApplicationService.create_application(ApplicationCreateData(
        candidate_id=c.pk, position_id=position.pk, actor=stranger,
    ))

    c.refresh_from_db()
    assert c.assigned_by_id == stranger.pk, '分配人如实记录（他确实执行了分配）'
    assert c.formal_locked_by_id == owner.pk, '但锁定权不给无关人员'


def test_create_application_inherits_lock_when_previous_owner_is_authority():
    """原锁定人是新职位权限人 → 转推后继承，不被执行转推的人抢走。"""
    owner, holder, mover = _user("owner"), _user("holder"), _user("mover")
    position = _position(owner, assistants=[holder])
    c = _cand()
    c.formal_locked_by = holder
    c.save(update_fields=['formal_locked_by'])

    ApplicationService.create_application(ApplicationCreateData(
        candidate_id=c.pk, position_id=position.pk, actor=mover,
    ))

    c.refresh_from_db()
    assert c.formal_locked_by_id == holder.pk
    assert c.assigned_by_id == mover.pk


# ============================ 2/3. 批量导入（新增候选人） ============================

def _draft(direction: str, **kwargs):
    return BulkCreateDraft(
        draft_id=_uid("draft"), direction=direction,
        name=kwargs.get('name', '批量候选人'), phone=_uid('139'),
        email=f'{uuid.uuid4().hex[:8]}@example.com', parsed_data={}, **kwargs,
    )


def test_bulk_create_position_direction_wires_lock():
    """批量导入直分职位 → 与投递创建同一口径：分配人（共享人）成为锁定人。"""
    owner, assistant = _user("owner"), _user("assist")
    position = _position(owner, assistants=[assistant])

    result = BulkCreateService.create_batch(
        [_draft('position', position_id=position.pk)], actor=assistant,
    )

    cand = Candidate.objects.get(pk=result.created_candidate_ids[0])
    assert cand.assigned_by_id == assistant.pk
    assert cand.assign_state == Candidate.AssignState.ASSIGNED.value
    assert cand.formal_locked_by_id == assistant.pk


def test_bulk_create_talent_direction_leaves_public_pool_unlocked():
    """批量导入直接入人才库 → 默认通用库（公共资源池）→ 按 PRD 无正式锁定人。"""
    owner = _user("owner")
    actor = _user("actor")

    result = BulkCreateService.create_batch([_draft('talent')], actor=actor)

    cand = Candidate.objects.get(pk=result.created_candidate_ids[0])
    entry = TalentPoolEntry.objects.get(candidate=cand)
    assert entry.pool_kind == TalentPoolEntry.PoolKind.GENERAL
    assert cand.formal_locked_by_id is None, '通用库属公共资源池，不得私自锁定'
    assert cand.assign_state == Candidate.AssignState.PENDING.value, '入库不等于已分配职位'


# ============================ 4. 手动放入人才库（HTTP 全链路） ============================

def test_talent_pool_add_api_clears_lock_for_public_pool(api_client, hr_user):
    """「放入人才库」API（HTTP 全链路）：通用/共享库属公共资源池 → 入库后清空锁定人。

    刻意先分配职位让简历被 owner 锁定，再入库 —— 若 views 里的联动调用被摘掉，
    ``formal_locked_by`` 会**停在 owner**，断言必红；不存在"碰巧也绿"的旁路。
    """
    owner = _user("owner")
    position = _position(owner)
    c = _cand()

    ApplicationService.create_application(ApplicationCreateData(
        candidate_id=c.pk, position_id=position.pk, actor=hr_user,
    ))
    c.refresh_from_db()
    assert c.formal_locked_by_id == owner.pk, '前置条件：分配后由职位负责人锁定'

    resp = api_client.post(
        '/api/v1/talent-pool/pool/PASSIVE/add/', {'candidateId': c.pk}, format='json',
    )
    assert resp.status_code == 200, f'入库失败: {resp.data}'

    c.refresh_from_db()
    entry = TalentPoolEntry.objects.get(candidate=c, pool_type='PASSIVE')
    assert entry.pool_kind == TalentPoolEntry.PoolKind.GENERAL.value
    assert c.formal_locked_by_id is None, '通用库属公共资源池，入库后不得保留私人锁定'
    assert CandidateHistory.objects.filter(candidate=c, action='LOCK_CHANGED').exists()
