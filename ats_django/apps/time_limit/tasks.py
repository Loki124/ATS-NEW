"""Time Limit Celery tasks (PRD v4 §6.5)"""
import logging
from datetime import timedelta
from typing import Dict, List

from celery import shared_task
from django.utils import timezone

from .services import (
    TimeLimitCalcResult,
    calc_time_limit,
    compute_locked_until,
    is_time_exceeded,
    get_remaining_days,
)

logger = logging.getLogger(__name__)


@shared_task(name='apps.time_limit.tasks.check_stage_time_limit')
def check_stage_time_limit() -> Dict:
    """检查所有进行中申请是否超时（每 30 分钟）"""
    from apps.application.models import Application, ApplicationState

    now = timezone.now()
    expired = []
    near_deadline = []
    in_progress = Application.objects.filter(
        state__in=[ApplicationState.ACTIVE, ApplicationState.PAUSED],
        deleted_at__isnull=True,
        stage_deadline__isnull=False,
    ).select_related('candidate', 'position', 'current_stage')

    for app in in_progress:
        if not app.stage_deadline:
            continue
        if is_time_exceeded(app.stage_entered_at, app.stage_deadline):
            expired.append({
                'application_id': app.id,
                'application_code': app.code,
                'candidate': app.candidate.name,
                'position': app.position.title,
                'stage': app.current_stage.name if app.current_stage else 'N/A',
                'overdue_by': (now - app.stage_deadline).total_seconds() / 3600,
            })
        elif (app.stage_deadline - now).total_seconds() < 24 * 3600:  # 1 day
            near_deadline.append({
                'application_id': app.id,
                'application_code': app.code,
                'remaining_hours': (app.stage_deadline - now).total_seconds() / 3600,
            })

    if expired:
        logger.warning(f'Found {len(expired)} expired applications')

    return {
        'checked_at': now.isoformat(),
        'expired': expired,
        'near_deadline': near_deadline,
        'total_checked': in_progress.count(),
    }


@shared_task(name='apps.time_limit.tasks.send_deadline_warnings')
def send_deadline_warnings() -> Dict:
    """给接近超时的申请发送提醒（每 6 小时）"""
    from apps.application.models import Application, ApplicationState
    from apps.notification.services import NotificationService

    now = timezone.now()
    soon_deadline = now + timedelta(hours=24)
    apps = Application.objects.filter(
        state=ApplicationState.ACTIVE,
        deleted_at__isnull=True,
        stage_deadline__lte=soon_deadline,
        stage_deadline__gt=now,
    ).select_related('candidate', 'position', 'current_stage', 'hr')

    sent = 0
    for app in apps:
        try:
            remaining = get_remaining_days(app.stage_entered_at, app.stage_deadline)
            NotificationService.send_notification(
                recipient=app.hr,
                event='application.deadline_warning',
                context={
                    'application': app,
                    'remaining_days': remaining,
                },
                channels=['IN_APP'],
            )
            sent += 1
        except Exception as e:
            logger.exception(f'Deadline warning failed for {app.id}: {e}')

    return {'warnings_sent': sent, 'checked_at': now.isoformat()}
