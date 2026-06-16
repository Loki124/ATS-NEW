"""Notification Celery tasks (PRD v4 §14.10)"""
import logging
from typing import Dict

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='apps.notification.tasks.send_pending_reminders')
def send_pending_reminders() -> Dict:
    """发送未发送的通知（每 1 小时重试）"""
    from .models import NotificationLog

    pending = NotificationLog.objects.filter(
        sent_at__isnull=True,
        failed_reason='',
    )
    sent = 0
    failed = 0

    for log in pending:
        try:
            from .services import NotificationService
            if log.channel == 'EMAIL':
                from apps.integration.services import send_email
                success = send_email(
                    to=log.recipient.email or '',
                    subject=log.subject,
                    body=log.content,
                )
            elif log.channel == 'WECOM':
                from apps.integration.services import send_wecom_message
                success = send_wecom_message(
                    user_id=getattr(log.recipient, 'moka_user_id', '') or '',
                    content=log.content,
                    title=log.subject,
                )
            elif log.channel == 'SMS':
                from apps.integration.services import send_sms
                success = send_sms(
                    phone=log.recipient.phone or '',
                    content=log.content,
                )
            else:
                success = True  # IN_APP 视为已送达

            if success:
                log.sent_at = timezone.now()
                log.save(update_fields=['sent_at'])
                sent += 1
            else:
                log.failed_reason = '发送失败'
                log.save(update_fields=['failed_reason'])
                failed += 1
        except Exception as e:
            logger.exception(f'Notification {log.id} retry failed: {e}')
            log.failed_reason = str(e)
            log.save(update_fields=['failed_reason'])
            failed += 1

    return {
        'checked_at': timezone.now().isoformat(),
        'total_pending': pending.count(),
        'sent': sent,
        'failed': failed,
    }
