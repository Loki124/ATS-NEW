"""Notification Celery tasks (PRD v4 §14.10)"""
import logging
from typing import Dict

from celery import shared_task
from django.db import OperationalError
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.notification.tasks.send_notification_log_task',
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(OperationalError,),
)
def send_notification_log_task(log_id: str) -> Dict:
    """投递单条通知（由 `NotificationService.send_notification` 入队调用）。

    2026-10-21 卡 F3：外部通道调用移出请求路径 —— 本任务在 worker 里做实际的
    邮件/短信/企微投递，请求侧立即返回。
    实际投递逻辑与每小时重试任务共用 `NotificationDispatcher.deliver_log`
    （含「先标记后发」的抢占 → 两条路径不会对同一条通知重复发送）。
    """
    from .models import NotificationLog
    from .services import NotificationDispatcher

    log = NotificationLog.objects.filter(id=log_id, deleted_at__isnull=True).first()
    if log is None:
        # 日志不存在: 可能事务尚未提交, 或已被删除 —— 交给每小时重试任务兜底
        logger.warning('通知日志不存在, 跳过投递 log=%s', log_id)
        return {'log_id': log_id, 'status': 'missing'}
    status = NotificationDispatcher.deliver_log(log)
    return {'log_id': log_id, 'status': status}


@shared_task(
    name='apps.notification.tasks.send_pending_reminders',
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(OperationalError,),
)
def send_pending_reminders() -> Dict:
    """发送未发送的通知（每 1 小时重试）—— 同时是 F3 入队失败 / 进程崩溃的兜底。"""
    from .models import NotificationLog
    from .services import NotificationDispatcher

    pending = NotificationLog.objects.filter(
        sent_at__isnull=True,
        failed_reason='',
    )
    sent = 0
    failed = 0
    skipped = 0

    for log in pending:
        # 2026-10-21 卡 F1: **先标记后发**（抢占逻辑在 deliver_log 内）。
        #   原实现是「发 → 记 sent_at」: 若外部通道已收到、但落 sent_at 前进程崩溃,
        #   下一轮会**重发** (重复通知)。现改为发送前先用条件 UPDATE 抢占本行:
        #     · 抢到 (sending_at 由 NULL 置为 now) 才真正发送;
        #     · 抢不到 (别人正在发 / 上一轮刚发过) → 跳过, 不会重复发;
        #     · 抢占超过 5 分钟视为上一轮崩溃 → 允许重新抢占 (既不重复也不漏发)。
        status = NotificationDispatcher.deliver_log(log)
        if status == 'sent':
            sent += 1
        elif status == 'failed':
            failed += 1
        else:
            skipped += 1

    return {
        'checked_at': timezone.now().isoformat(),
        'total_pending': pending.count(),
        'sent': sent,
        'failed': failed,
        'skipped_locked': skipped,
    }
