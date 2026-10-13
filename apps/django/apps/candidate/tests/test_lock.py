"""简历锁定人双轨模型（apps/candidate/lock.py）行为测试。

穿透真实 DB 链路验证，不 mock 模型行为：

- 临时锁定授予为 72h；过期后**不再**是锁定人（但仍保留查看，查看由可见范围控制）；
- 正式锁定人与未过期的临时锁定人**并存且权限同等**；
- 列表级 ``lock_owner_q`` 与对象级 ``is_lock_owner`` 判定结果必须一致
  （两者不一致就说明存在「应用层过滤」权限漏洞）；
- 匿名一律 fail-closed；
- 乐观锁版本冲突拒绝（先到先得）。
"""
import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from apps.application.models import Application
from apps.candidate.lock import (
    TEMP_LOCK_HOURS,
    LockConflict,
    assert_lock_version,
    bump_lock_version,
    grant_temp_lock,
    is_lock_owner,
    is_temp_lock_active,
    lock_owner_q,
    position_authority_q,
    release_expired_temp_locks,
    revoke_temp_lock,
    set_formal_lock,
)
from apps.candidate.models import Candidate
from apps.core.models import Department
from apps.position.models import Position
from apps.process.models import ProcessStageLink, RecruitmentProcess, RecruitmentStage

pytestmark = pytest.mark.django_db


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _user(tag: str = "u"):
    return get_user_model().objects.create_user(username=_uid(tag), password="Test@1234")


def _cand(**kwargs) -> Candidate:
    return Candidate.objects.create(name=kwargs.pop("name", "锁定候选人"), phone=_uid("138"), **kwargs)


# ============================ 临时锁定 ============================

def test_grant_temp_lock_is_72_hours():
    """临时锁定默认 72 小时，授予后立即生效。"""
    u = _user("uploader")
    c = _cand()
    grant_temp_lock(c, u)
    c.refresh_from_db()

    assert c.temp_locked_by_id == u.pk
    assert is_temp_lock_active(c) is True
    delta = c.temp_lock_expires_at - timezone.now()
    assert timedelta(hours=TEMP_LOCK_HOURS - 1) < delta <= timedelta(hours=TEMP_LOCK_HOURS)


def test_expired_temp_lock_loses_operation_right():
    """临时锁定过期 → 不再是锁定人（分配权限被回收）。"""
    u = _user("temp")
    c = _cand()
    grant_temp_lock(c, u)
    assert is_lock_owner(c, u) is True

    # 直接把到期时间拨到过去，模拟 72h 倒计时结束
    c.temp_lock_expires_at = timezone.now() - timedelta(seconds=1)
    c.save(update_fields=['temp_lock_expires_at'])

    assert is_temp_lock_active(c) is False
    assert is_lock_owner(c, u) is False


def test_revoke_temp_lock_clears_both_fields():
    u = _user("temp")
    c = _cand()
    grant_temp_lock(c, u)
    revoke_temp_lock(c)
    c.refresh_from_db()
    assert c.temp_locked_by_id is None
    assert c.temp_lock_expires_at is None
    assert is_lock_owner(c, u) is False


def test_release_expired_temp_locks_only_touches_expired():
    """批量回收只清过期的，未过期的临时锁不受影响。"""
    expired_owner = _user("exp")
    active_owner = _user("act")
    c_expired = _cand(name="已过期")
    c_active = _cand(name="未过期")

    grant_temp_lock(c_expired, expired_owner)
    grant_temp_lock(c_active, active_owner)
    c_expired.temp_lock_expires_at = timezone.now() - timedelta(minutes=1)
    c_expired.save(update_fields=['temp_lock_expires_at'])

    released = release_expired_temp_locks()
    assert released == 1

    c_active.refresh_from_db()
    c_expired.refresh_from_db()
    assert c_expired.temp_locked_by_id is None
    assert c_active.temp_locked_by_id == active_owner.pk
    assert is_lock_owner(c_active, active_owner) is True


# ============================ 正式锁定 + 双轨并存 ============================

def test_formal_lock_owner():
    owner = _user("formal")
    other = _user("other")
    c = _cand()
    set_formal_lock(c, owner)
    c.refresh_from_db()

    assert c.formal_locked_by_id == owner.pk
    assert is_lock_owner(c, owner) is True
    assert is_lock_owner(c, other) is False


def test_formal_and_temp_lock_coexist_with_equal_right():
    """正式锁定人与未过期的临时锁定人并存，权限同等。"""
    formal = _user("formal")
    temp = _user("temp")
    c = _cand()
    set_formal_lock(c, formal)
    grant_temp_lock(c, temp)

    assert is_lock_owner(c, formal) is True
    assert is_lock_owner(c, temp) is True


# ============================ 双形态一致性（防权限漏洞） ============================

def test_lock_owner_q_matches_is_lock_owner():
    """列表级 Q 与对象级判定必须完全一致 —— 不一致即存在越权/漏权。"""
    me = _user("me")
    c_formal = _cand(name="我正式锁定")
    c_temp = _cand(name="我临时锁定")
    c_expired_temp = _cand(name="我临时锁定已过期")
    c_other = _cand(name="别人的")

    set_formal_lock(c_formal, me)
    grant_temp_lock(c_temp, me)
    grant_temp_lock(c_expired_temp, me)
    c_expired_temp.temp_lock_expires_at = timezone.now() - timedelta(seconds=1)
    c_expired_temp.save(update_fields=['temp_lock_expires_at'])

    matched = set(Candidate.objects.filter(lock_owner_q(me)).values_list('pk', flat=True))
    assert matched == {c_formal.pk, c_temp.pk}, '过期的临时锁不得再命中'

    # 逐条交叉校验：Q 命中 <-> is_lock_owner 为真
    for c in (c_formal, c_temp, c_expired_temp, c_other):
        assert (c.pk in matched) == is_lock_owner(c, me)


def test_lock_owner_q_anonymous_fails_closed():
    """匿名 / 未认证用户一律空集，绝不退化成放行。"""
    c = _cand()
    set_formal_lock(c, _user("someone"))
    assert Candidate.objects.filter(lock_owner_q(None)).exists() is False
    assert Candidate.objects.filter(lock_owner_q(AnonymousUser())).exists() is False
    assert is_lock_owner(c, AnonymousUser()) is False


# ============================ 职位权限人 ============================

def _make_position_chain():
    """造 职位(负责人+共享人) → 流程 → 投递(抢单人) 链。"""
    User = get_user_model()
    owner = User.objects.create_user(username=_uid("owner"), password="Test@1234")
    assistant = User.objects.create_user(username=_uid("assist"), password="Test@1234")
    grabber = User.objects.create_user(username=_uid("grab"), password="Test@1234")

    dept = Department.objects.create(id=_uid("dept"), name=_uid("BG"), code=_uid("BG"))
    process = RecruitmentProcess.objects.create(
        code=_uid("PROC"), name="社招标准流程", current_version="V1.0", version_seq=1, is_latest=True,
    )
    stage = RecruitmentStage.objects.create(code=_uid("P"), name=_uid("初评"), stage_type="INTERVIEW")
    link = ProcessStageLink.objects.create(process=process, stage=stage, order=1)
    position = Position.objects.create(
        code=_uid("POS"), title="客服专员", department=dept,
        hiring_manager=owner, owner=owner, process=process,
    )
    position.assistants.add(assistant)
    candidate = _cand(name="权限链候选人")
    Application.objects.create(
        code=_uid("APP"), candidate=candidate, position=position,
        process=process, workflow_version="V1.0",
        current_stage=link.stage, is_grabbed=True, grabbed_by=grabber,
    )
    return candidate, owner, assistant, grabber


def test_position_authority_q_covers_owner_assistant_and_grabber():
    """职位权限人 = 职位负责人 ∪ 职位共享人(assistants) ∪ 简历抢单人(grabbed_by)。"""
    candidate, owner, assistant, grabber = _make_position_chain()
    stranger = _user("stranger")

    for u in (owner, assistant, grabber):
        assert Candidate.objects.filter(position_authority_q(u)).filter(pk=candidate.pk).exists(), \
            f'{u.username} 应能命中该简历'

    assert Candidate.objects.filter(position_authority_q(stranger)).filter(pk=candidate.pk).exists() is False
    assert Candidate.objects.filter(position_authority_q(None)).exists() is False


# ============================ 乐观锁 ============================

def test_optimistic_lock_version_conflict():
    """版本号不一致 → 拒绝（先到先得），一致 → 通过。"""
    c = _cand()
    assert c.lock_version == 0

    assert_lock_version(c, 0)           # 当前版本一致，放行
    new_ver = bump_lock_version(c)
    assert new_ver == 1

    with pytest.raises(LockConflict):
        assert_lock_version(c, 0)       # 陈旧版本 → 拒绝
    assert_lock_version(c, 1)           # 新版本 → 放行
