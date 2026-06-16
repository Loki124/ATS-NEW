"""Celery Tasks (PRD v4 §11.5, §13)

定期任务：
- check_stage_timeouts: 阶段超时巡检（每 5 分钟）
- reassign_overdue_grabs: 抢单超时重分配（每 5 分钟）
- check_soft_reject_thresholds: 软拒阈值巡检（每小时）
- check_automation_failure_rate: 自动化失败率告警（每小时）
- daily_active_users_report: 日活统计（每天）
- archive_stale_applications: 长期未推进申请归档（每天）
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List

from celery import shared_task
from django.db.models import Count, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


# ============================================================
# 阶段超时
# ============================================================
@shared_task(
    name='apps.application.tasks.check_stage_timeouts',
    bind=True, max_retries=3, default_retry_delay=60,
)
def check_stage_timeouts(self) -> Dict[str, Any]:
    """巡检所有进行中申请，检查阶段是否超时

    业务规则（PRD v4 §11.5 + §13.2）：
    - 阶段超过 deadline 仍未推进 → 标记 TIMEOUT
    - 触发通知给当前处理人
    - 累计 N 次超时 → 候选人自动入人才库
    """
    from .models import Application, ApplicationState, ApplicationStageRecord
    from .services import ApplicationService

    now = timezone.now()
    # 找到所有超时的当前阶段记录
    overdue_records = ApplicationStageRecord.objects.filter(
        state__in=[
            ApplicationStageRecord.StageState.PENDING,
            ApplicationStageRecord.StageState.PROCESSING,
            ApplicationStageRecord.StageState.TO_BE_SCHEDULED,
        ],
        deadline__lte=now,
        deadline__isnull=False,
        deleted_at__isnull=True,
    ).select_related('application', 'stage')

    archived = 0
    notifications_sent = 0
    for record in overdue_records:
        try:
            app = record.application
            if app.state not in (
                ApplicationState.ACTIVE, ApplicationState.PAUSED,
            ):
                continue
            # 通知处理人
            handlers = record.current_handlers or []
            for uid in handlers:
                try:
                    _send_timeout_notification(app, record, uid)
                    notifications_sent += 1
                except Exception as e:
                    logger.warning('Send timeout notification failed: %s', e)

            # 累计超时次数
            timeout_count = _count_timeouts_for_application(app)
            if timeout_count >= 3:
                # 触发入人才库
                from .services.soft_reject import SoftRejectService
                SoftRejectService.check_threshold_and_pool(
                    app.candidate_id, app.process_id, app.current_stage_id,
                )
            archived += 1
        except Exception as e:
            logger.exception('Stage timeout handling failed for record %s', record.id)

    logger.info('check_stage_timeouts: overdue=%d, notifications=%d', len(overdue_records), notifications_sent)
    return {
        'overdue_count': len(overdue_records),
        'notifications_sent': notifications_sent,
        'checked_at': now.isoformat(),
    }


def _count_timeouts_for_application(app) -> int:
    from .models import ApplicationHistory
    return ApplicationHistory.objects.filter(
        application=app,
        action=ApplicationHistory.ActionType.TIMEOUT,
        deleted_at__isnull=True,
    ).count()


def _send_timeout_notification(app, record, user_id: str):
    from apps.notification.services import send_notification
    send_notification(
        recipient_id=user_id,
        title=f'阶段超时 - {app.candidate.name}',
        content=f'申请 {app.code} 在【{record.stage.name}】阶段已超时，请及时处理',
        link=f'/applications/{app.id}',
        source='STAGE_TIMEOUT',
        source_id=record.id,
    )


# ============================================================
# 抢单超时重分配
# ============================================================
@shared_task(
    name='apps.application.tasks.reassign_overdue_grabs',
    bind=True, max_retries=3, default_retry_delay=60,
)
def reassign_overdue_grabs(self, threshold_minutes: int = 30) -> Dict[str, Any]:
    """抢单超时重分配（PRD v4 §6.4）"""
    from .services.grab import GrabService
    results = GrabService.reassign_overdue(threshold_minutes=threshold_minutes)
    logger.info('reassign_overdue_grabs: reassigned=%d', len(results))
    return {
        'reassigned_count': len(results),
        'threshold_minutes': threshold_minutes,
    }


# ============================================================
# 软拒阈值
# ============================================================
@shared_task(
    name='apps.application.tasks.check_soft_reject_thresholds',
    bind=True, max_retries=2,
)
def check_soft_reject_thresholds(self) -> Dict[str, Any]:
    """巡检软拒阈值"""
    from .services.soft_reject import check_all_soft_reject_thresholds
    return check_all_soft_reject_thresholds()


# ============================================================
# 自动化失败率
# ============================================================
@shared_task(
    name='apps.automation.tasks.check_automation_failure_rate',
    bind=True, max_retries=2,
)
def check_automation_failure_rate(self) -> Dict[str, Any]:
    """检查自动化规则失败率并告警"""
    from apps.automation.models import AutomationLog, AutomationRule

    now = timezone.now()
    window_start = now - timedelta(hours=24)
    rules = AutomationRule.objects.filter(enabled=True, deleted_at__isnull=True)
    alert_count = 0
    for rule in rules:
        logs = AutomationLog.objects.filter(
            rule=rule, trigger_time__gte=window_start, deleted_at__isnull=True,
        )
        total = logs.count()
        if total < 10:
            continue
        failed = logs.filter(
            Q(evaluate_result='ERROR') | ~Q(error_message=''),
        ).count()
        failure_rate = failed / total
        if failure_rate > (rule.failure_rate_threshold or 0.5):
            # 告警
            try:
                _send_failure_alert(rule, failure_rate, total, failed)
                alert_count += 1
            except Exception as e:
                logger.warning('Send failure alert failed: %s', e)
    return {
        'rules_checked': rules.count(),
        'alerts_sent': alert_count,
    }


def _send_failure_alert(rule, failure_rate: float, total: int, failed: int):
    """发送失败率告警"""
    from apps.notification.services import send_notification
    # 通知规则负责人 + HRBP
    recipients = set()
    if rule.owner_id:
        recipients.add(rule.owner_id)
    # TODO: 找 HRBP 列表
    for rid in recipients:
        send_notification(
            recipient_id=rid,
            title=f'自动化规则失败率告警 - {rule.name}',
            content=(
                f'规则 [{rule.name}] 24h 失败率 {failure_rate:.1%} ({failed}/{total})，'
                f'已超过阈值 {(rule.failure_rate_threshold or 0.5):.0%}'
            ),
            link=f'/automation/rules/{rule.id}',
            source='AUTOMATION_ALERT',
            source_id=rule.id,
        )


# ============================================================
# 长期未推进申请归档
# ============================================================
@shared_task(
    name='apps.application.tasks.archive_stale_applications',
    bind=True, max_retries=2,
)
def archive_stale_applications(self, days: int = 90) -> Dict[str, Any]:
    """归档 N 天未推进的申请"""
    from .models import Application, ApplicationState
    from .services import ApplicationService

    cutoff = timezone.now() - timedelta(days=days)
    stale = Application.objects.filter(
        state__in=[ApplicationState.ACTIVE, ApplicationState.PAUSED],
        last_advanced_at__lte=cutoff,
        deleted_at__isnull=True,
    )
    archived = 0
    for app in stale:
        try:
            ApplicationService.archive_timeout(app)
            archived += 1
        except Exception as e:
            logger.warning('Archive stale application %s failed: %s', app.code, e)
    return {
        'archived_count': archived,
        'cutoff_days': days,
    }


# ============================================================
# Beat Schedule (在 settings 中配置)
# ============================================================
CELERY_BEAT_SCHEDULE = {
    'check-stage-timeouts': {
        'task': 'apps.application.tasks.check_stage_timeouts',
        'schedule': 300.0,  # 5 分钟
    },
    'reassign-overdue-grabs': {
        'task': 'apps.application.tasks.reassign_overdue_grabs',
        'schedule': 300.0,  # 5 分钟
    },
    'check-soft-reject-thresholds': {
        'task': 'apps.application.tasks.check_soft_reject_thresholds',
        'schedule': 3600.0,  # 1 小时
    },
    'check-automation-failure-rate': {
        'task': 'apps.automation.tasks.check_automation_failure_rate',
        'schedule': 3600.0,  # 1 小时
    },
    'archive-stale-applications': {
        'task': 'apps.application.tasks.archive_stale_applications',
        'schedule': 86400.0,  # 1 天
        'kwargs': {'days': 90},
    },
}
