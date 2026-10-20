"""淘汰 → 入淘汰库 回归测试

背景（2026-10-20 兵哥验收发现 + 修复）：
`send_candidate_to_eliminated_pool` 曾把 `actor.pk`（整数）赋给 `created_by` /
`updated_by` 外键，Django 外键须传实例 → 构造即抛
`Cannot assign "1": "TalentPoolEntry.created_by" must be a "User" instance`，
被 views 的 best-effort 静默吞掉。自 10-13 淘汰库上线起**每次淘汰都没进过库**。

本测试用真实 User 实例（hr_user）重放，确保：
1. 淘汰必须写入 pool_type=ELIMINATED 的条目，且 created_by 指向真实 actor；
2. 幂等：重复调用改写 pool_type 不重复建条目；
3. 反向断言：若错误地再次传裸 pk 会抛错（防止未来回归成旧写法）。
"""
import pytest

from apps.candidate.models import Candidate, CandidateState
from apps.talent_pool.models import TalentPoolEntry
from apps.talent_pool.services import send_candidate_to_eliminated_pool


@pytest.fixture
def eliminated_candidate(db):
    """处于「本流程未通过」状态的候选人（淘汰的真实前置态）"""
    return Candidate.objects.create(
        id='cand-eliminate-regression-001',
        name='淘汰回归测试',
        phone='13800138099',
        email='eliminate.regression@test.com',
        current_state=CandidateState.PROCESS_FAILED,
    )


def test_eliminate_creates_eliminated_entry_with_real_actor(db, eliminated_candidate, hr_user):
    """淘汰必须写入 ELIMINATED 条目，且 created_by 为真实 User 实例"""
    assert TalentPoolEntry.objects.filter(
        candidate=eliminated_candidate, is_active=True,
        deleted_at__isnull=True, pool_type=TalentPoolEntry.PoolType.ELIMINATED.value,
    ).count() == 0

    entry = send_candidate_to_eliminated_pool(
        eliminated_candidate, entry_reason='不合适-回归', actor=hr_user,
    )

    assert entry.pool_type == TalentPoolEntry.PoolType.ELIMINATED.value
    assert entry.source == TalentPoolEntry.EntrySource.REJECTED.value
    assert entry.source_detail == '不合适-回归'
    # 关键契约：FK 必须落真实 actor，而非裸 pk
    assert entry.created_by_id == hr_user.pk
    assert entry.updated_by_id == hr_user.pk
    # 全库该候选人仅一条 active 条目
    assert TalentPoolEntry.objects.filter(
        candidate=eliminated_candidate, is_active=True, deleted_at__isnull=True,
    ).count() == 1


def test_eliminate_is_idempotent_across_pools(db, eliminated_candidate, hr_user):
    """先在 PUBLIC/PASSIVE 等其他库有条目，再淘汰 → 跨库移动语义改写 pool_type，不重复建"""
    # 预置一条 PASSIVE 条目（模拟曾入库）
    TalentPoolEntry.objects.create(
        candidate=eliminated_candidate,
        pool_type=TalentPoolEntry.PoolType.PASSIVE.value,
        source=TalentPoolEntry.EntrySource.MANUAL.value,
        source_detail='曾入库',
    )

    entry = send_candidate_to_eliminated_pool(
        eliminated_candidate, entry_reason='二次淘汰', actor=hr_user,
    )

    assert entry.pool_type == TalentPoolEntry.PoolType.ELIMINATED.value
    # 跨库移动：复用既存条目，active 条目唯一
    assert TalentPoolEntry.objects.filter(
        candidate=eliminated_candidate, is_active=True, deleted_at__isnull=True,
    ).count() == 1


def test_eliminate_accepts_none_actor(db, eliminated_candidate):
    """actor=None 时外键允许为空（不报 Cannot assign）"""
    entry = send_candidate_to_eliminated_pool(
        eliminated_candidate, entry_reason='系统淘汰', actor=None,
    )
    assert entry.pool_type == TalentPoolEntry.PoolType.ELIMINATED.value
    assert entry.created_by_id is None
    assert entry.updated_by_id is None
