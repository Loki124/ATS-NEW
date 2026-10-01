"""Audit log 清理 Celery 任务 (P1-4)

按 settings.ATS_BASE['AUDIT_LOG_RETENTION_DAYS'] (默认 3 年) 清理过期审计日志。
使用 bulk 分批删除避免长事务 / 长锁 / 大回滚段。

设计要点:
- 不使用 @retryable_scheduled_task:
  - 清理任务失败应立刻显式抛出,由 Celery beat 重试 (max_retries=0 + autoretry_for=空)
  - 运营场景下清理失败应让人看见,而非静默
- 每批 BATCH_SIZE 行,用 IN 子句 + 事务包裹,降低行锁持续时间
- 任务幂等: 多次执行结果一致
"""
from django.db import DatabaseError
import logging
from datetime import timedelta
from typing import Dict

from celery import shared_task
from django.conf import settings
from django.db import OperationalError, InterfaceError, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# 每批删除行数
# 设小一点 (5000) 是因为 audit_log 行包含 TextField(old_value/new_value),
# 1000 行可能就有几 MB,避免长事务
BATCH_SIZE = 5000

# 最大连续批次数 (防止死循环: 业务持续写入老数据,清理永远跑不完)
MAX_BATCHES = 1000  # 1000 * 5000 = 5,000,000 行上限,够用


# 这些异常应该触发整次任务重试
DB_RETRY_EXCEPTIONS = (OperationalError, InterfaceError, ConnectionError, TimeoutError)


@shared_task(
    bind=True,
    name='apps.audit.tasks.cleanup_old_audit_logs',
    autoretry_for=DB_RETRY_EXCEPTIONS,
    retry_backoff=300,         # 5 分钟起步
    retry_backoff_max=3600,    # 最长 1 小时
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
)
def cleanup_old_audit_logs(self) -> Dict:
    """清理超过保留期的 audit log (每日 03:00 由 beat 触发)

    保留期: settings.ATS_BASE['AUDIT_LOG_RETENTION_DAYS'] (默认 3 年)

    Returns:
        包含 cutoff / retention_days / deleted / batches 字段
    """
    from .models import AuditLog

    retention_days = settings.ATS_BASE.get('AUDIT_LOG_RETENTION_DAYS', 365 * 3)
    cutoff = timezone.now() - timedelta(days=retention_days)

    total_deleted = 0
    batches = 0

    while batches < MAX_BATCHES:
        with transaction.atomic():
            # 找出本批要删的 id
            ids = list(
                AuditLog.objects
                .filter(created_at__lt=cutoff)
                .values_list('id', flat=True)[:BATCH_SIZE]
            )
            if not ids:
                break

            deleted, _ = AuditLog.objects.filter(id__in=ids).delete()
            total_deleted += deleted
            batches += 1

            # 每 10 批输出一次进度,避免高频日志
            if batches % 10 == 0:
                logger.info(
                    'audit cleanup: 已处理 %d 批,删除 %d 行 (cutoff=%s)',
                    batches, total_deleted, cutoff.isoformat(),
                )

    if total_deleted:
        logger.info(
            'audit cleanup: 共删除 %d 条超过 %d 天的记录 (cutoff=%s)',
            total_deleted, retention_days, cutoff.isoformat(),
        )
    else:
        logger.debug('audit cleanup: 无需清理 (cutoff=%s)', cutoff.isoformat())

    return {
        'cutoff': cutoff.isoformat(),
        'retention_days': retention_days,
        'deleted': total_deleted,
        'batches': batches,
    }


@shared_task(
    bind=True,
    name='apps.audit.tasks.audit_cleanup_healthcheck',
    max_retries=0,
)
def audit_cleanup_healthcheck(self) -> Dict:
    """清理任务健康检查 (每小时) — 监控保留期/总量是否异常

    触发告警的场景:
    - audit_log 总行数超过 1,000,000 (容量告警)
    - 老于 1 年的行数占比超过 80% (清理未跑)
    """
    from django.db import connection
    from .models import AuditLog

    total = AuditLog.objects.count()
    old_count = AuditLog.objects.filter(
        created_at__lt=timezone.now() - timedelta(days=365)
    ).count()

    old_ratio = (old_count / total) if total else 0
    alerts = []

    if total > 1_000_000:
        alerts.append({
            'level': 'WARNING',
            'message': f'audit_log 总行数 {total:,} 超过 100 万,检查清理任务',
        })
    if old_ratio > 0.8 and total > 10_000:
        alerts.append({
            'level': 'WARNING',
            'message': f'超过 1 年的 audit_log 占比 {old_ratio:.1%},清理任务可能未跑',
        })

    if alerts:
        try:
            from apps.notification.services import NotificationService
            from apps.core.models import User

            admins = User.objects.filter(is_superuser=True, is_active=True)[:5]
            for admin in admins:
                NotificationService.send_notification(
                    recipient=admin,
                    event='audit.cleanup_alert',
                    context={'alerts': alerts, 'total': total, 'old_count': old_count},
                    channels=['IN_APP'],
                )
        except (DatabaseError, ValueError, TypeError, AttributeError, OSError) as exc:  # Celery 清理批处理, 告警发送失败不影响清理主流程
            logger.exception('audit cleanup 告警发送失败: %s', exc)

    return {
        'total': total,
        'old_count': old_count,
        'old_ratio': round(old_ratio, 4),
        'alerts': alerts,
    }
