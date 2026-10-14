"""简历操作权守卫（apps/candidate/operation_guard.py）行为测试。

核心验证「只有锁定人能操作简历」这条需求，以及不会把存量业务打死：

- 有锁定人 → **严格**：仅锁定人（含未过期临时锁定人）可操作，创建人/职位权限人都不行；
- 临时锁过期 → 失权（与 lock.py 口径一致）；
- 无锁定人（存量常态）→ 过渡期兜底：职位权限人 ∪ 创建人 ∪ 招聘负责人；
- 无主简历（created_by/recruiter 全 NULL，历史确有其数据）→ 交回角色级写范围，
  未配置写范围则放行 —— 防「新权限上线即全体瘫痪」；
- **列表级 Q 与对象级判定必须逐条一致**（踩过的坑：``legacy | Q()`` 被 Django 化简成
  legacy，兜底形同虚设，整批无主简历被拒 —— 此处用交叉校验把该 bug 钉死）；
- 状态门登记后按门限动作；未登记状态不受约束。
"""
import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.candidate.models import Candidate, CandidateState
from apps.candidate.operation_guard import (
    STATE_ACTION_GATE,
    ensure_operable,
    has_lock,
    is_operable,
    is_position_principal,
    operable_q,
    register_state_gate,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _isole_action_dict_cache():
    """每个用例前后清空动作字典缓存。

    ⚠️ 必须：``is_operable`` 会经 ``action_registry.is_action_enabled`` 写入 **TTL 缓存**，
    若不清理，后续 ``apps/data_permission`` 的用例修改字典表后会读到本用例缓存的旧值
    → 跨 app 顺序污染（实测 29 failed）。data_permission 模块 docstring 亦明确要求
    「用例间必须 invalidate_cache()」。
    """
    from apps.data_permission.action_registry import invalidate_cache

    invalidate_cache()
    yield
    invalidate_cache()


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _user(tag: str = "u"):
    return get_user_model().objects.create_user(username=_uid(tag), password="Test@1234")


def _cand(**kwargs) -> Candidate:
    return Candidate.objects.create(name=kwargs.pop("name", "守卫候选人"), phone=_uid("138"), **kwargs)


def _lock(cand, user, **kwargs):
    cand.formal_locked_by = kwargs.get('formal', None)
    cand.temp_locked_by = kwargs.get('temp', None)
    cand.temp_lock_expires_at = kwargs.get('expires', None)
    cand.save(update_fields=['formal_locked_by', 'temp_locked_by', 'temp_lock_expires_at'])
    return cand


# ============================ 有锁定人：严格 ============================

def test_only_lock_owner_can_operate():
    """有正式锁定人 → 仅锁定人可操作；创建人/无关人都被拒（需求核心）。"""
    owner = _user("owner")
    creator = _user("creator")
    stranger = _user("stranger")
    c = _cand(created_by=creator)
    _lock(c, None, formal=owner)

    assert has_lock(c) is True
    assert is_operable(owner, c, 'recommend') is True
    assert is_operable(creator, c, 'recommend') is False, '有锁定人后，创建人也不再能操作'
    assert is_operable(stranger, c, 'recommend') is False


def test_temp_lock_owner_can_operate_until_expired():
    """临时锁定人在 72h 内可操作，过期即失权。"""
    holder = _user("holder")
    c = _cand()
    _lock(c, None, temp=holder, expires=timezone.now() + timedelta(hours=72))
    assert is_operable(holder, c, 'eliminate') is True

    _lock(c, None, temp=holder, expires=timezone.now() - timedelta(seconds=1))
    assert is_operable(holder, c, 'eliminate') is False


def test_locked_resume_blocks_position_authority():
    """锁定人存在时，职位权限人（负责人）也只有查看权，不能操作。"""
    from apps.application.models import Application
    from apps.core.models import Department
    from apps.position.models import Position
    from apps.process.models import ProcessStageLink, RecruitmentProcess, RecruitmentStage

    owner = _user("owner")
    holder = _user("holder")
    dept = Department.objects.create(id=_uid("dept"), name=_uid("BG"), code=_uid("BGC"))
    process = RecruitmentProcess.objects.create(
        code=_uid("PROC"), name="流程", current_version="V1.0", version_seq=1, is_latest=True,
    )
    stage = RecruitmentStage.objects.create(code=_uid("S"), name=_uid("初评"), stage_type="INTERVIEW")
    link = ProcessStageLink.objects.create(process=process, stage=stage, order=1, is_required=True)
    position = Position.objects.create(
        code=_uid("POS"), title="职位", department=dept,
        hiring_manager=owner, owner=owner, process=process,
    )
    c = _cand()
    Application.objects.create(
        code=_uid("APP"), candidate=c, position=position, process=process,
        workflow_version="V1.0", current_link=link, current_stage=stage,
    )
    _lock(c, None, formal=holder)

    assert is_position_principal(owner, c) is True, '前置：owner 确实是职位权限人'
    assert is_operable(owner, c, 'recommend') is False, '有锁定人 → 职位权限人不可操作'
    assert is_operable(holder, c, 'recommend') is True


# ============================ 无锁定人：过渡期兜底 ============================

def test_unlocked_resume_falls_back_to_creator():
    """无锁定人 → 创建人可操作（过渡期，保证存量业务不断）。

    ⚠️ 刻意**不**断言「陌生人被拒」：无锁定人且不属于任何 legacy 主体时，
    本模块**不表态**，交回角色级写范围（``is_writable``）决定 —— 这是过渡期设计，
    因为存量简历绝大多数没有锁定人，若主体层一律拒绝等于上线即瘫痪。
    测试环境未配置 WRITE 规则时该分支为放行，故此处断言它会随配置而变，
    「陌生人必被拒」由 data_permission 的写范围规则负责，不在本用例职责内。
    """
    creator = _user("creator")
    c = _cand(created_by=creator)

    assert has_lock(c) is False
    assert is_operable(creator, c, 'recommend') is True


def test_unlocked_resume_falls_back_to_recruiter():
    """无锁定人 → 招聘负责人（recruiter）可操作。"""
    recruiter = _user("recruiter")
    c = _cand(recruiter=recruiter)

    assert has_lock(c) is False
    assert is_operable(recruiter, c, 'recommend') is True


def test_ownerless_resume_is_not_blocked_when_no_scope_rule():
    """无主简历（created_by/recruiter 全 NULL）在无写范围规则时应放行。

    这是踩过的坑：把兜底写成 ``legacy | Q()``，空 Q() 被 Django 化简掉，
    兜底形同虚设 → 整批存量简历被拒（上线即瘫痪）。本用例即该 bug 的回归防线。
    """
    user = _user("user")
    c = _cand()  # created_by / recruiter 均为 NULL，无投递、无锁定人

    assert is_operable(user, c, 'recommend') is True, '无主且无写范围规则 → 不得拒绝'
    assert Candidate.objects.filter(operable_q(user, 'recommend'), pk=c.pk).exists()


# ============================ Q 与对象判定一致性（防漂移） ============================

def test_operable_q_matches_is_operable_for_every_resume():
    """列表级 operable_q 与对象级 is_operable 必须逐条一致。

    两者不一致 = 存在「应用层过滤」权限漏洞（漏加 Q 即全量泄露，或多过滤即误拒）。
    """
    me = _user("me")
    other = _user("other")

    c_locked_by_me = _cand(name="我锁定"); _lock(c_locked_by_me, None, formal=me)
    c_locked_by_other = _cand(name="别人锁定"); _lock(c_locked_by_other, None, formal=other)
    c_temp_expired = _cand(name="我的临时锁已过期")
    _lock(c_temp_expired, None, temp=me, expires=timezone.now() - timedelta(seconds=1))
    c_my_creation = _cand(name="我创建的", created_by=me)
    c_others = _cand(name="别人的", created_by=other)
    c_ownerless = _cand(name="无主")

    pool = [c_locked_by_me, c_locked_by_other, c_temp_expired, c_my_creation, c_others, c_ownerless]
    matched = set(Candidate.objects.filter(operable_q(me, 'recommend')).values_list('pk', flat=True))

    for c in pool:
        assert (c.pk in matched) == is_operable(me, c, 'recommend'), \
            f'Q 与对象判定不一致: {c.name}'


# ============================ 动作白名单 / 匿名 / 超管 ============================

def test_unknown_action_is_rejected():
    """未注册动作一律拒绝（fail-closed）。"""
    owner = _user("owner")
    c = _cand()
    _lock(c, None, formal=owner)
    assert is_operable(owner, c, 'no_such_action') is False


def test_anonymous_and_none_instance_are_rejected():
    c = _cand()
    assert is_operable(None, c, 'recommend') is False
    assert is_operable(AnonymousUser(), c, 'recommend') is False
    assert is_operable(_user("u"), None, 'recommend') is False


def test_ensure_operable_raises_permission_denied():
    """ensure_operable 对无权者抛 PermissionDenied（DRF 转 403）。"""
    holder = _user("holder")
    stranger = _user("stranger")
    c = _cand()
    _lock(c, None, formal=holder)

    ensure_operable(holder, c, 'recommend')  # 不抛
    with pytest.raises(PermissionDenied):
        ensure_operable(stranger, c, 'recommend')


# ============================ 状态门 ============================

def test_state_gate_restricts_actions():
    """登记状态门后，该状态下只允许门内动作（本例：人才库状态禁推进、允许转推）。"""
    holder = _user("holder")
    c = _cand()
    _lock(c, None, formal=holder)
    # current_state 是 FSM protected 字段，直接赋值会被 django-fsm 拦截 -> 走 queryset
    Candidate.objects.filter(pk=c.pk).update(current_state=CandidateState.TALENT_POOL.value)
    c.refresh_from_db()

    # 未登记状态门 → 不受约束
    assert is_operable(holder, c, 'transition') is True

    register_state_gate(CandidateState.TALENT_POOL.value, {'recommend', 'talent_pool_add'})
    try:
        assert is_operable(holder, c, 'recommend') is True
        assert is_operable(holder, c, 'transition') is False, '门内未列动作应被拒'
    finally:
        STATE_ACTION_GATE.pop(CandidateState.TALENT_POOL.value, None)


def test_register_state_gate_overwrite_is_idempotent():
    """重复登记以最后一次为准（清理全局表，防污染其他用例）。"""
    register_state_gate('SOME_STATE', {'view'})
    try:
        assert STATE_ACTION_GATE['SOME_STATE'] == {'view'}
        register_state_gate('SOME_STATE', {'view', 'edit'})
        assert STATE_ACTION_GATE['SOME_STATE'] == {'view', 'edit'}
    finally:
        STATE_ACTION_GATE.pop('SOME_STATE', None)
