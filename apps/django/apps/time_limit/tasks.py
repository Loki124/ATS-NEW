"""Time Limit Celery tasks (PRD v4 §6.5)

P0-2 修复: 所有调度任务用 @retryable_scheduled_task
(DB 抖动自动重试 + 连续失败告警)
"""
import logging
from datetime import timedelta
from typing import Dict

from django.db import DatabaseError
from django.utils import timezone

from apps.common.celery_utils import retryable_scheduled_task

from .services import (
    get_remaining_days,
    is_time_exceeded,
)

logger = logging.getLogger(__name__)


@retryable_scheduled_task(
    name='apps.time_limit.tasks.check_stage_time_limit',
    max_retries=3,
    retry_backoff=60,
)
def check_stage_time_limit() -> Dict:
    """检查所有进行中申请是否超时（每 30 分钟）"""
    from apps.application.models import Application, ApplicationState

    now = timezone.now()
    expired = []
    near_deadline = []
    # P1-3: 改用 .iterator() 流式查询,避免 10k+ 申请时一次性加载到内存 OOM
    in_progress = Application.objects.filter(
        state__in=[ApplicationState.ACTIVE, ApplicationState.PAUSED],
        deleted_at__isnull=True,
        stage_deadline__isnull=False,
    ).select_related('candidate', 'position', 'current_stage').iterator(chunk_size=500)

    total_checked = 0
    for app in in_progress:
        total_checked += 1
        if not app.stage_deadline:
            continue
        # 实参错位修复（P0，2026-08-11）：签名是 is_time_exceeded(locked_until, now=None)，
        # 原调用传的是 (stage_entered_at, stage_deadline) —— 等价于在问
        # "stage_deadline > stage_entered_at 吗"，而截止时间当然晚于进入时间，
        # 于是**每一条有 deadline 的进行中申请都被判为超时**，下面的 elif
        # 近超时分支则永远走不到（near_deadline 恒为空）。
        if is_time_exceeded(app.stage_deadline, now=now):
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
        'total_checked': total_checked,
    }


@retryable_scheduled_task(
    name='apps.time_limit.tasks.send_deadline_warnings',
    max_retries=3,
    retry_backoff=60,
)
def send_deadline_warnings() -> Dict:
    """给接近超时的申请发送提醒（每 6 小时）"""
    from apps.application.models import Application, ApplicationState
    from apps.notification.services import NotificationService

    now = timezone.now()
    soon_deadline = now + timedelta(hours=24)
    # P1-3: 同样改用 .iterator() 流式查询
    apps = Application.objects.filter(
        state=ApplicationState.ACTIVE,
        deleted_at__isnull=True,
        stage_deadline__lte=soon_deadline,
        stage_deadline__gt=now,
    # P0 修复（2026-08-10）：原先 select_related(..., 'hr')，但 Application 根本没有
    # hr 字段（运行时内省：candidate/position/process/current_link/current_stage/
    # grabbed_by/offer/created_by/updated_by）。select_related 的非法字段在 queryset
    # **迭代时**才抛 FieldError，且该异常发生在下面 try 之外 —— 整个任务当场崩掉。
    # 此前 celery_utils 的 bind 透传 bug 让本函数根本进不来，所以这行从未暴露过。
    ).select_related(
        'candidate', 'position', 'current_stage',
        'grabbed_by', 'position__owner', 'position__hiring_manager',
    ).iterator(chunk_size=500)

    sent = 0
    skipped_no_recipient = 0
    for app in apps:
        try:
            # 同一处实参错位：签名是 get_remaining_days(locked_until, now=None)。
            # 原调用 (stage_entered_at, stage_deadline) 算出的是
            # stage_entered_at - stage_deadline —— 恒为负 → max(0, …) → 恒为 0，
            # 提醒邮件里永远写"剩余 0 天"。
            remaining = get_remaining_days(app.stage_deadline, now=now)

            # 收件人回退链。原代码写的是 app.hr —— 该字段不存在，全仓仅此一处误用。
            # 「阶段超时」催的是当前负责推进这条申请的人，故：
            #   grabbed_by（已抢单，谁抢谁负责）
            #   → position.owner（职位负责人）
            #   → position.hiring_manager（对齐 talent_pool/tasks.py:45 的同类惯例）
            # TODO(产品确认)：此链条为依据现有字段语义的推定，需产品复核优先级顺序。
            recipient = (
                app.grabbed_by
                or app.position.owner
                or app.position.hiring_manager
            )
            if recipient is None:
                # 宁可显式跳过并留痕，也不要把 None 塞进通知服务里假装发过了。
                skipped_no_recipient += 1
                logger.warning(
                    'Deadline warning skipped: no recipient for application %s', app.id,
                )
                continue

            NotificationService.send_notification(
                recipient=recipient,
                event='application.deadline_warning',
                context={
                    'application': app,
                    'remaining_days': remaining,
                },
                channels=['IN_APP'],
            )
            sent += 1
        except (DatabaseError, ValueError, TypeError, AttributeError, OSError) as e:  # Celery 截止日告警批处理, 单条 application 发送失败不影响其他 application
            logger.exception(f'Deadline warning failed for {app.id}: {e}')

    return {
        'warnings_sent': sent,
        'skipped_no_recipient': skipped_no_recipient,
        'checked_at': now.isoformat(),
    }
