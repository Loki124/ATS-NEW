"""Soft Reject Service (PRD v4 §6.3, §10)

软拒规则（PRD v4 §10 业务规则）：
- 同一流程同阶段累计 3 次软拒 → 自动入人才库
- 软拒记录保留全部历史
- 软拒原因可作为人才库标签
- 二次投递限制：候选人 X 在 N 天内对同职位再次投递，自动跳过最近软拒的阶段

实际实现：
- 软拒计数器（基于 ApplicationHistory）
- 自动触发入人才库
- 二次投递时跳过被软拒过的阶段
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Count, Q
from django.utils import timezone

from apps.common.exceptions import StateTransitionError
from apps.core.models import User

from ..models import Application, ApplicationHistory, ApplicationState

logger = logging.getLogger(__name__)


# ============================================================
# 配置常量
# ============================================================
SOFT_REJECT_THRESHOLD = 3  # 同一阶段累计 3 次软拒触发入人才库
REAPPLY_COOLDOWN_DAYS = 90  # 二次投递冷却期


class SoftRejectService:
    """软拒服务"""

    @staticmethod
    def count_soft_rejects(application: Application) -> int:
        """统计当前申请累计软拒次数"""
        return ApplicationHistory.objects.filter(
            application=application,
            action=ApplicationHistory.ActionType.REJECTED,
            detail__soft=True,
            deleted_at__isnull=True,
        ).count()

    @staticmethod
    def count_soft_rejects_by_stage(candidate_id: str, stage_id: str,
                                    process_id: Optional[str] = None,
                                    days: int = 365) -> int:
        """统计候选人在某阶段累计软拒次数（跨申请）"""
        cutoff = timezone.now() - timedelta(days=days)
        qs = ApplicationHistory.objects.filter(
            application__candidate_id=candidate_id,
            to_stage_id=stage_id,
            action=ApplicationHistory.ActionType.REJECTED,
            detail__soft=True,
            created_at__gte=cutoff,
            deleted_at__isnull=True,
        )
        if process_id:
            qs = qs.filter(application__process_id=process_id)
        return qs.count()

    @staticmethod
    def check_threshold_and_pool(candidate_id: str, process_id: str,
                                  stage_id: str, actor: Optional[User] = None) -> bool:
        """达到阈值则自动入人才库

        返回：是否触发了入人才库
        """
        count = SoftRejectService.count_soft_rejects_by_stage(
            candidate_id, stage_id, process_id,
        )
        if count >= SOFT_REJECT_THRESHOLD:
            logger.info(
                'Candidate %s soft-rejected %d times at stage %s, moving to talent pool',
                candidate_id, count, stage_id,
            )
            from apps.candidate.services import CandidateService
            from apps.talent_pool.services import move_candidate_to_pool
            try:
                candidate = Application.objects.filter(
                    candidate_id=candidate_id, deleted_at__isnull=True,
                ).first().candidate
                CandidateService.move_to_talent_pool(
                    candidate,
                    entry_source='SOFT_REJECT_THRESHOLD',
                    reason=f'累计软拒 {count} 次',
                    actor=actor,
                )
                move_candidate_to_pool(
                    candidate_id=candidate_id,
                    entry_source='SOFT_REJECT_THRESHOLD',
                    entry_reason=f'累计软拒 {count} 次',
                    actor=actor,
                )
                return True
            except Exception as e:
                logger.exception('Auto pool failed: %s', e)
        return False

    @staticmethod
    def get_rejected_stages(candidate_id: str, position_id: str,
                            days: int = REAPPLY_COOLDOWN_DAYS) -> List[str]:
        """获取候选人对某职位在冷却期内被软拒过的阶段 ID 列表"""
        cutoff = timezone.now() - timedelta(days=days)
        rejected = ApplicationHistory.objects.filter(
            application__candidate_id=candidate_id,
            application__position_id=position_id,
            action=ApplicationHistory.ActionType.REJECTED,
            detail__soft=True,
            created_at__gte=cutoff,
            deleted_at__isnull=True,
        ).values_list('to_stage_id', flat=True).distinct()
        return [s for s in rejected if s]

    @staticmethod
    def suggest_reapply_initial_stage(candidate_id: str, position_id: str,
                                      process_stage_links: List) -> Optional[Any]:
        """建议二次投递的初始阶段（跳过最近软拒阶段）

        process_stage_links: QuerySet/列表 of ProcessStageLink，按 order 排序
        返回：推荐的 ProcessStageLink 或 None
        """
        rejected_stages = SoftRejectService.get_rejected_stages(
            candidate_id, position_id,
        )
        if not rejected_stages:
            return process_stage_links[0] if process_stage_links else None
        for link in process_stage_links:
            if link.stage_id not in rejected_stages:
                return link
        # 全部阶段都被软拒过 → 返回首个
        return process_stage_links[0] if process_stage_links else None

    @staticmethod
    def get_soft_reject_stats(candidate_id: str) -> Dict[str, Any]:
        """候选人软拒统计"""
        from django.db.models import Count
        stats = ApplicationHistory.objects.filter(
            application__candidate_id=candidate_id,
            action=ApplicationHistory.ActionType.REJECTED,
            detail__soft=True,
            deleted_at__isnull=True,
        ).values('to_stage__name').annotate(
            count=Count('id'),
        ).order_by('-count')
        return {
            'total': sum(s['count'] for s in stats),
            'by_stage': list(stats),
        }

    @staticmethod
    def get_position_soft_reject_list(candidate_id: str, position_id: str,
                                      days: int = REAPPLY_COOLDOWN_DAYS) -> List[Dict[str, Any]]:
        """获取候选人对某职位的软拒明细"""
        cutoff = timezone.now() - timedelta(days=days)
        records = ApplicationHistory.objects.filter(
            application__candidate_id=candidate_id,
            application__position_id=position_id,
            action=ApplicationHistory.ActionType.REJECTED,
            detail__soft=True,
            created_at__gte=cutoff,
            deleted_at__isnull=True,
        ).select_related('to_stage', 'application').order_by('-created_at')
        return [
            {
                'application_code': r.application.code,
                'stage': r.to_stage.name if r.to_stage else None,
                'reason': (r.detail or {}).get('reason', ''),
                'rejected_at': r.created_at.isoformat(),
            }
            for r in records
        ]


# ============================================================
# Celery 入口
# ============================================================
def check_all_soft_reject_thresholds() -> Dict[str, int]:
    """巡检所有候选人是否触发了软拒阈值"""
    # 找出所有 REJECTED + soft 的候选人 × 阶段 × 流程组合
    combos = ApplicationHistory.objects.filter(
        action=ApplicationHistory.ActionType.REJECTED,
        detail__soft=True,
        deleted_at__isnull=True,
    ).values(
        'application__candidate_id', 'application__process_id', 'to_stage_id',
    ).annotate(
        count=Count('id'),
    ).filter(count__gte=SOFT_REJECT_THRESHOLD)

    triggered = 0
    for combo in combos:
        try:
            if SoftRejectService.check_threshold_and_pool(
                combo['application__candidate_id'],
                combo['application__process_id'],
                combo['to_stage_id'],
            ):
                triggered += 1
        except Exception as e:
            logger.warning('Threshold check failed: %s', e)
    return {
        'checked': combos.count(),
        'triggered': triggered,
    }
