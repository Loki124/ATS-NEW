"""Talent Pool Celery tasks (PRD v4 §14.7)"""
import logging
from datetime import timedelta
from typing import Dict, List

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='apps.talent_pool.tasks.recommend_candidates')
def recommend_candidates() -> Dict:
    """智能推荐人才库候选人给开放职位（每小时）"""
    from .models import TalentPoolEntry
    from apps.position.models import Position, PositionState
    from apps.notification.services import NotificationService

    open_positions = Position.objects.filter(
        state=PositionState.RECRUITING,
        deleted_at__isnull=True,
    ).select_related('department', 'hiring_manager')

    active_pool = TalentPoolEntry.objects.filter(
        is_active=True,
    ).select_related('candidate', 'last_position', 'last_stage')

    recommendations: List[Dict] = []

    for pos in open_positions:
        for entry in active_pool[:5]:
            if entry.last_position and entry.last_position.department_id == pos.department_id:
                recommendations.append({
                    'position_id': pos.id,
                    'position_title': pos.title,
                    'candidate_id': entry.candidate_id,
                    'candidate_name': entry.candidate.name,
                    'match_score': 0.7,
                    'source': entry.source,
                })

    for pos in open_positions[:10]:
        try:
            NotificationService.send_notification(
                recipient=pos.hiring_manager,
                event='talent_pool.recommendations',
                context={
                    'position': pos,
                    'count': len([r for r in recommendations if r['position_id'] == pos.id]),
                },
                channels=['IN_APP'],
            )
        except Exception as e:
            logger.exception(f'Talent pool notification failed: {e}')

    return {
        'recommendations': recommendations[:50],
        'total': len(recommendations),
        'generated_at': timezone.now().isoformat(),
    }


@shared_task(name='apps.talent_pool.tasks.cleanup_inactive_entries')
def cleanup_inactive_entries() -> Dict:
    """清理长期未激活的人才库条目（每日）"""
    from .models import TalentPoolEntry

    threshold = timezone.now() - timedelta(days=730)
    count = TalentPoolEntry.objects.filter(
        is_active=True,
        last_activated_at__lt=threshold,
    ).update(is_active=False)

    return {'deactivated': count}
