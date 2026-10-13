"""简历锁定人（双轨模型）判定与服务原语。

依据《简历模块及特殊简历审批流程调整需求说明》(2026-10-14)：

- **正式锁定人** ``formal_locked_by``：对简历拥有永久分配操作权、是最终责任人；
  由锁定引擎按规则自动确定与流转，**任何角色不可手动变更**
  （故 ``set_formal_lock`` 仅允许锁定引擎调用，序列化器不暴露该字段）。
- **临时锁定人** ``temp_locked_by``：特定场景下被授予有时效（默认 72h）的分配操作权，
  与正式锁定人**并存且权限同等**；到期自动回收分配权限（查看权限不受影响，
  查看由可见范围控制）。
- 两者并发执行分配时采用**乐观锁**（``lock_version``）先到先得。

权限判定恒为两者并集，且临时锁必须校验未过期：

    Q(formal_locked_by=me) | Q(temp_locked_by=me, temp_lock_expires_at__gt=now)

对外一律提供**两种形态**，缺一不可（只做对象级判定会退化成「先查出来再应用层过滤」，
那是权限漏洞 —— 忘记加 Q 即全量泄露）：

- ``*_q(user)``  → 供列表 / 查询在 **SQL 层**过滤的 Django ``Q``；
- ``is_*(obj, user)`` → 供对象级守卫（``ensure_writable``）判定的 ``bool``。
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

#: 临时锁定有效时长（小时）。PRD 定义为 72 小时。
TEMP_LOCK_HOURS = 72


class LockConflict(Exception):
    """乐观锁版本冲突。

    分配 / 转推等变更操作提交时，若携带的 ``lock_version`` 与库中当前值不一致，
    说明期间已被其他锁定人（正式或临时）操作过 —— 按 PRD「先到先得」直接拒绝。
    """


def _anon(user) -> bool:
    """匿名 / 空用户一律视为无权限（fail-closed）。"""
    return user is None or not getattr(user, 'is_authenticated', False)


# ============================ 临时锁定 ============================

def is_temp_lock_active(candidate, now=None) -> bool:
    """临时锁当前是否生效（有临时锁定人且未过期）。"""
    if not candidate.temp_locked_by_id or not candidate.temp_lock_expires_at:
        return False
    return (now or timezone.now()) < candidate.temp_lock_expires_at


def grant_temp_lock(candidate, user, *, hours: int = TEMP_LOCK_HOURS, now=None):
    """授予临时锁定（默认 72h）。

    适用场景（PRD）：① 上传时上传人 ≠ 提供人 → 上传人；
    ② 从人才库重新激活时激活人 ≠ 提供人 → 激活操作人。
    """
    base = now or timezone.now()
    candidate.temp_locked_by = user
    candidate.temp_lock_expires_at = base + timedelta(hours=hours)
    candidate.save(update_fields=['temp_locked_by', 'temp_lock_expires_at', 'updated_at'])
    return candidate


def revoke_temp_lock(candidate):
    """回收临时锁定。保留查看 —— 查看由可见范围控制，与本函数无关。"""
    candidate.temp_locked_by = None
    candidate.temp_lock_expires_at = None
    candidate.save(update_fields=['temp_locked_by', 'temp_lock_expires_at', 'updated_at'])
    return candidate


def release_expired_temp_locks(now=None) -> int:
    """批量回收所有已过期的临时锁（定时任务 / Redis 过期事件调用）。返回回收条数。"""
    from .models import Candidate

    return (
        Candidate.objects
        .filter(temp_locked_by__isnull=False, temp_lock_expires_at__lt=(now or timezone.now()))
        .update(temp_locked_by=None, temp_lock_expires_at=None)
    )


# ============================ 正式锁定 ============================

def set_formal_lock(candidate, user):
    """写入正式锁定人 —— **仅锁定引擎可调用**。

    PRD：正式锁定人由系统按规则自动确定与流转，不可人为手动变更。
    因此业务 view / serializer 不得调用本函数，也不得暴露该字段为可写。
    """
    candidate.formal_locked_by = user
    candidate.save(update_fields=['formal_locked_by', 'updated_at'])
    return candidate


# ============================ 锁定人判定（双形态） ============================

def is_lock_owner(candidate, user, now=None) -> bool:
    """对象级：``user`` 是否为该简历的当前锁定人（正式锁定人 或 未过期的临时锁定人）。"""
    if _anon(user):
        return False
    if candidate.formal_locked_by_id and candidate.formal_locked_by_id == user.pk:
        return True
    if candidate.temp_locked_by_id and candidate.temp_locked_by_id == user.pk:
        return is_temp_lock_active(candidate, now)
    return False


def lock_owner_q(user, now=None) -> Q:
    """列表级：锁定人过滤 Q，供 SQL 层使用。匿名一律返回空集（fail-closed）。"""
    if _anon(user):
        return Q(pk__in=[])
    return Q(formal_locked_by=user) | Q(
        temp_locked_by=user, temp_lock_expires_at__gt=(now or timezone.now()),
    )


def position_authority_q(user) -> Q:
    """列表级：职位权限人过滤 Q —— 职位负责人 ∪ 职位共享人 ∪ 简历抢单人。

    - 职位负责人  ``Position.owner``
    - 职位共享人  ``Position.assistants``（M2M，即需求文档中的「职位共享人」，已核实复用）
    - 简历抢单人  ``Application.grabbed_by``（投递级，由抢单服务写入）
    """
    if _anon(user):
        return Q(pk__in=[])
    return (
        Q(applications__position__owner=user)
        | Q(applications__position__assistants=user)
        | Q(applications__grabbed_by=user)
    )


# ============================ 乐观锁 ============================

def bump_lock_version(candidate) -> int:
    """递增并返回乐观锁版本号（变更操作成功后调用）。"""
    candidate.lock_version = (candidate.lock_version or 0) + 1
    candidate.save(update_fields=['lock_version', 'updated_at'])
    return candidate.lock_version


def assert_lock_version(candidate, expected) -> None:
    """乐观锁校验：提交变更时版本号必须一致，否则抛 :class:`LockConflict`。

    先到先得 —— 正式锁定人与临时锁定人并发操作时，后提交者被拒绝。
    """
    try:
        expected_int = int(expected)
    except (TypeError, ValueError):
        raise LockConflict('缺少或非法的 lock_version') from None
    if expected_int != int(candidate.lock_version or 0):
        raise LockConflict(
            f'简历 {candidate.pk} 锁定版本已变更（期望 {expected_int}，'
            f'当前 {candidate.lock_version}），请刷新后重试'
        )
