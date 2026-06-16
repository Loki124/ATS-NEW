"""Talent Pool Services (PRD v4 §14.7)

人才库业务：
- 公共人才库 (Public) + 部门人才库 (Private)
- 入库：候选人 × 阶段软拒 / 主动撤回 / 自动化 / 业务失败
- 出库：从人才库"重新激活"并投递
- 标签分类
- 检索与匹配
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.candidate.models import Candidate, CandidateState
from apps.common.exceptions import NotFound
from apps.core.models import User

from .models import TalentPoolEntry, EntrySource

logger = logging.getLogger(__name__)


# ============================================================
# 数据类
# ============================================================
@dataclass
class PoolEntryData:
    """入库入参"""
    candidate_id: str
    entry_source: str = 'MANUAL'
    entry_reason: str = ''
    target_pool_code: str = 'PUBLIC'
    tags: Optional[List[str]] = None
    notes: str = ''
    operator_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass
class MoveToPoolResult:
    """入库结果"""
    candidate: Candidate
    entry: TalentPoolEntry
    is_new_entry: bool


# ============================================================
# 人才库服务
# ============================================================
class TalentPoolService:
    """人才库服务"""

    @staticmethod
    @transaction.atomic
    def move_candidate_to_pool(
        candidate_id: str,
        entry_source: str = 'MANUAL',
        entry_reason: str = '',
        target_pool_code: str = 'PUBLIC',
        actor: Optional[User] = None,
        tags: Optional[List[str]] = None,
        notes: str = '',
    ) -> MoveToPoolResult:
        """候选人入库

        - 重复入库：更新 entry 的 reason/tags
        - 候选人状态 → TALENT_POOL
        - 触发候选人侧状态机
        """
        try:
            candidate = Candidate.objects.get(id=candidate_id, deleted_at__isnull=True)
        except Candidate.DoesNotExist as e:
            raise NotFound(f'Candidate {candidate_id} not found') from e

        # 校验 entry_source
        valid_sources = [s[0] for s in EntrySource.choices]
        if entry_source not in valid_sources:
            entry_source = 'MANUAL'

        # 找/创建入库记录
        entry, is_new = TalentPoolEntry.objects.get_or_create(
            candidate=candidate,
            is_active=True,
            deleted_at__isnull=True,
            defaults={
                'source': entry_source,
                'source_detail': entry_reason or '',
                'tags': tags or [],
            },
        )
        if not is_new:
            # 更新已有 entry
            entry.source_detail = (entry.source_detail or '') + f'\n[RE-ENTRY] {entry_reason}'
            entry.tags = list(set((entry.tags or []) + (tags or [])))
            entry.save()

        # 触发候选人状态机（如果还没在人才库）
        if candidate.current_state != CandidateState.TALENT_POOL:
            from apps.candidate.services import CandidateService
            try:
                CandidateService.move_to_talent_pool(
                    candidate,
                    entry_source=entry_source,
                    reason=entry_reason,
                    actor=actor,
                )
            except Exception as e:
                logger.warning('Candidate state transition to pool failed: %s', e)

        logger.info(
            'Candidate %s moved to pool (new=%s, source=%s)',
            candidate.id, is_new, entry_source,
        )

        return MoveToPoolResult(
            candidate=candidate, entry=entry, is_new_entry=is_new,
        )

    @staticmethod
    def search_pool(
        pool_code: str = 'PUBLIC',
        keyword: Optional[str] = None,
        entry_source: Optional[str] = None,
        tag: Optional[str] = None,
        entry_from: Optional[Any] = None,
        entry_to: Optional[Any] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[TalentPoolEntry]:
        """人才库检索"""
        qs = TalentPoolEntry.objects.filter(
            is_active=True, deleted_at__isnull=True,
        ).select_related('candidate')

        if keyword:
            qs = qs.filter(
                Q(candidate__name__icontains=keyword) |
                Q(candidate__phone__icontains=keyword) |
                Q(candidate__email__icontains=keyword) |
                Q(candidate__current_company__icontains=keyword) |
                Q(candidate__current_position__icontains=keyword),
            )
        if entry_source:
            qs = qs.filter(source=entry_source)
        if tag:
            qs = qs.filter(tags__contains=[tag])
        if entry_from:
            qs = qs.filter(created_at__gte=entry_from)
        if entry_to:
            qs = qs.filter(created_at__lte=entry_to)
        return list(qs.order_by('-created_at')[offset:offset + limit])

    @staticmethod
    @transaction.atomic
    def reactivate_from_pool(
        entry_id: str,
        actor: Optional[User] = None,
        notes: str = '',
    ) -> TalentPoolEntry:
        """从人才库重新激活

        - 标记 entry.is_active = False
        - 不自动改候选人状态（由调用方决定：投递新职位 / 二次激活）
        """
        try:
            entry = TalentPoolEntry.objects.get(
                id=entry_id, is_active=True, deleted_at__isnull=True,
            )
        except TalentPoolEntry.DoesNotExist as e:
            raise NotFound(f'Pool entry {entry_id} not found') from e

        entry.is_active = False
        entry.last_activated_at = timezone.now()
        entry.activated_count = (entry.activated_count or 0) + 1
        if notes:
            entry.source_detail = (entry.source_detail or '') + f'\n[REACTIVATED] {notes}'
        entry.save()

        logger.info('Pool entry %s reactivated by %s', entry.id, actor.id if actor else 'system')
        return entry

    @staticmethod
    def get_pool_stats(pool_code: str = 'PUBLIC') -> Dict[str, Any]:
        """人才库统计"""
        from django.db.models import Count
        qs = TalentPoolEntry.objects.filter(
            is_active=True, deleted_at__isnull=True,
        )
        total = qs.count()
        by_source = list(qs.values('source').annotate(
            count=Count('id'),
        ).order_by('-count'))
        return {
            'pool_code': pool_code,
            'total': total,
            'by_source': by_source,
        }

    @staticmethod
    def get_candidate_pool_history(candidate_id: str) -> List[Dict[str, Any]]:
        """候选人人才库历史"""
        entries = TalentPoolEntry.objects.filter(
            candidate_id=candidate_id, deleted_at__isnull=True,
        ).select_related('candidate').order_by('-created_at')
        return [
            {
                'id': e.id,
                'source': e.source,
                'source_detail': e.source_detail,
                'entry_time': e.created_at.isoformat(),
                'is_active': e.is_active,
                'last_activated_at': e.last_activated_at.isoformat() if e.last_activated_at else None,
                'activated_count': e.activated_count,
                'tags': e.tags or [],
            }
            for e in entries
        ]


# ============================================================
# 便捷函数
# ============================================================
def move_candidate_to_pool(
    candidate_id: str, entry_source: str = 'MANUAL',
    entry_reason: str = '', actor: Optional[User] = None,
    target_pool_code: str = 'PUBLIC',
) -> MoveToPoolResult:
    """便捷函数"""
    return TalentPoolService.move_candidate_to_pool(
        candidate_id=candidate_id,
        entry_source=entry_source,
        entry_reason=entry_reason,
        target_pool_code=target_pool_code,
        actor=actor,
    )


def search_pool(**kwargs) -> List[TalentPoolEntry]:
    return TalentPoolService.search_pool(**kwargs)
