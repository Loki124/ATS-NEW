"""审批独占 + 审批流唯一性（兵哥 2026-10-14 口径）行为测试。

口径原文：
- 「同一个简历同时只能有一个审批」→ 重复发起必须被拒；
- 「审批中时仅发起人可以处理」→ 有在途审批时，**只有该审批的 created_by**
  能操作该简历，连正式锁定人也不放行（独占优先于锁定）。

验证重点是 **列表级 operable_q 与对象级 is_operable 逐条一致** ——
两者不一致即为权限漏洞（漏加 Q 即批量场景越权）。
"""
import json
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from apps.candidate.models import Candidate
from apps.candidate.operation_guard import (
    ensure_operable,
    in_flight_approval,
    is_approval_owner,
    is_operable,
    operable_q,
)
from apps.data_permission.action_registry import invalidate_cache
from apps.resume_flow.models import ApprovalFlow

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _isolate_action_dict_cache():
    invalidate_cache()
    yield
    invalidate_cache()


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _user(tag: str = "u"):
    return get_user_model().objects.create_user(username=_uid(tag), password="Test@1234")


def _cand(**kwargs) -> Candidate:
    return Candidate.objects.create(name=kwargs.pop("name", "审批候选人"), phone=_uid("138"), **kwargs)


def _flow(candidate, creator, status='PENDING'):
    return ApprovalFlow.objects.create(
        candidate=candidate,
        created_by=creator,
        status=status,
        current_node_id='n1',
        nodes=[{'nodeId': 'n1', 'role': 'HRBP'}],
    )


def _lock(cand, user):
    cand.formal_locked_by = user
    cand.save(update_fields=['formal_locked_by'])
    return cand


# ============================ 审批独占 ============================

def test_only_initiator_can_operate_during_approval():
    """审批中：仅发起人可操作，锁定人与创建人都被拒。"""
    initiator = _user("initiator")
    lock_holder = _user("holder")
    creator = _user("creator")
    c = _cand(created_by=creator)
    _lock(c, lock_holder)
    _flow(c, initiator, status='IN_PROGRESS')

    assert in_flight_approval(c) is not None
    assert is_approval_owner(initiator, c) is True
    assert is_operable(initiator, c, 'recommend') is True
    assert is_operable(lock_holder, c, 'recommend') is False, '审批独占优先于锁定人'
    assert is_operable(creator, c, 'recommend') is False


def test_pending_also_blocks_others():
    """PENDING（刚发起未批）同样算在途，独占生效 —— 否则发起后到首节点有人能插队。"""
    initiator = _user("initiator")
    other = _user("other")
    c = _cand()
    _flow(c, initiator, status='PENDING')

    assert is_operable(initiator, c, 'eliminate') is True
    assert is_operable(other, c, 'eliminate') is False


@pytest.mark.parametrize('terminal', ['APPROVED', 'REJECTED', 'CANCELLED'])
def test_terminal_status_frees_operations(terminal):
    """终态（通过/驳回/取消）解除独占，操作权回归锁定人。"""
    initiator = _user("initiator")
    holder = _user("holder")
    c = _cand()
    _lock(c, holder)
    _flow(c, initiator, status=terminal)

    assert in_flight_approval(c) is None
    assert is_operable(holder, c, 'recommend') is True, '终态后锁定人恢复操作权'


def test_ensure_operable_blocked_by_approval():
    initiator = _user("initiator")
    other = _user("other")
    c = _cand()
    _flow(c, initiator, status='IN_PROGRESS')

    ensure_operable(initiator, c, 'recommend')  # 发起人不抛
    with pytest.raises(PermissionDenied):
        ensure_operable(other, c, 'recommend')


# ============================ Q 与对象判定一致（防越权） ============================

def test_operable_q_matches_is_operable_with_approval():
    """审批独占下，Q 与对象判定必须逐条一致（含被独占排除的锁定人）。"""
    me = _user("me")
    other_initiator = _user("other")

    # 我是审批发起人 → 可操作
    c_mine = _cand(name="我的审批"); _lock(c_mine, other_initiator); _flow(c_mine, me, 'IN_PROGRESS')
    # 别人发起审批 → 我被独占（即便我是锁定人）
    c_theirs = _cand(name="别人的审批"); _lock(c_theirs, me); _flow(c_theirs, other_initiator, 'IN_PROGRESS')
    # 审批已终结 → 恢复常规锁定人判定
    c_done = _cand(name="审批已完成"); _lock(c_done, me); _flow(c_done, other_initiator, 'APPROVED')
    # 无审批
    c_free = _cand(name="无审批", created_by=me)

    pool = [c_mine, c_theirs, c_done, c_free]
    matched = set(Candidate.objects.filter(operable_q(me, 'recommend')).values_list('pk', flat=True))

    for c in pool:
        assert (c.pk in matched) == is_operable(me, c, 'recommend'), f'Q 与对象判定不一致: {c.name}'

    assert c_mine.pk in matched
    assert c_theirs.pk not in matched, '被他人审批独占的简历不得出现在可操作集'
    assert c_done.pk in matched


# ============================ 唯一性：同一简历仅一个在途审批 ============================

def test_duplicate_in_flight_approval_is_rejected(api_client, hr_user):
    """同一简历已有在途审批时，重复发起被拒（400 + 明确提示）。"""
    c = _cand()
    url = '/api/v1/resumes/approval-flows/'
    payload = {'candidate': c.id, 'resume_id': 'r1', 'nodes': [{'nodeId': 'n1', 'role': 'HRBP'}]}

    first = api_client.post(url, payload, format='json')
    assert first.status_code == 201, first.json()

    second = api_client.post(url, payload, format='json')
    assert second.status_code == 400, f'重复发起应被拒: {second.json()}'
    # 全局异常处理器把 DRF 校验错误包成信封，字段级明细在 errors 里
    body = second.json()
    detail = json.dumps(body, ensure_ascii=False)
    assert '在途审批' in detail, f'应提示在途审批: {body}'


def test_new_approval_allowed_after_terminal(api_client, hr_user):
    """原审批进入终态后，可再次发起。"""
    c = _cand()
    url = '/api/v1/resumes/approval-flows/'
    payload = {'candidate': c.id, 'resume_id': 'r1', 'nodes': [{'nodeId': 'n1', 'role': 'HRBP'}]}

    assert api_client.post(url, payload, format='json').status_code == 201
    flow = ApprovalFlow.objects.get(candidate=c)
    flow.status = 'APPROVED'
    flow.save(update_fields=['status'])

    assert api_client.post(url, payload, format='json').status_code == 201


@pytest.fixture
def api_client(hr_user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=hr_user)
    return client


def test_in_flight_approval_none_for_unrelated_candidate():
    """无审批的候选人 → in_flight_approval 返回 None（不进独占分支）。"""
    initiator = _user("initiator")
    c1 = _cand()
    _flow(initiator and c1, initiator, 'IN_PROGRESS')
    c2 = _cand()
    assert in_flight_approval(c1) is not None
    assert in_flight_approval(c2) is None