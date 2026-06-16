"""Invitation Celery tasks (PRD v4 §14.6)"""
import logging
from datetime import timedelta
from typing import Dict

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='apps.invitation.tasks.cleanup_expired')
def cleanup_expired() -> Dict:
    """清理已超期且未响应的邀约（每小时）"""
    from .models import Invitation, InvitationState
    from .services import InvitationService

    now = timezone.now()
    expired_pending = Invitation.objects.filter(
        expire_at__lt=now,
        state__in=[InvitationState.PENDING, InvitationState.INVITING],
        deleted_at__isnull=True,
    )
    count = 0
    for inv in expired_pending:
        try:
            InvitationService.timeout(inv.id)
            count += 1
        except Exception as e:
            logger.exception(f'Timeout failed for {inv.id}: {e}')

    return {
        'cleaned_at': now.isoformat(),
        'expired_count': count,
    }


@shared_task(name='apps.invitation.tasks.send_invitation_reminders')
def send_invitation_reminders() -> Dict:
    """给快过期的邀约发送提醒（每 6 小时）"""
    from .models import Invitation, InvitationState
    from apps.notification.services import NotificationService

    now = timezone.now()
    threshold = now + timedelta(hours=4)
    invs = Invitation.objects.filter(
        state=InvitationState.INVITING,
        expire_at__lte=threshold,
        expire_at__gt=now,
        deleted_at__isnull=True,
    ).select_related('application', 'inviter')

    sent = 0
    for inv in invs:
        try:
            NotificationService.send_notification(
                recipient=inv.inviter,
                event='invitation.expiring_soon',
                context={
                    'invitation': inv,
                    'hours_left': (inv.expire_at - now).total_seconds() / 3600,
                },
                channels=['IN_APP'],
            )
            sent += 1
        except Exception as e:
            logger.exception(f'Reminder failed for {inv.id}: {e}')

    return {'reminders_sent': sent, 'checked_at': now.isoformat()}
