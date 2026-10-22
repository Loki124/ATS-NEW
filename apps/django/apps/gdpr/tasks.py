"""GDPR Celery tasks (PRD v4 §4.4)"""
import logging
from typing import Dict

from celery import shared_task
from django.db import OperationalError
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='apps.gdpr.tasks.run_retention_cleanup', max_retries=3, default_retry_delay=5, autoretry_for=(OperationalError,))
def run_retention_cleanup() -> Dict:
    """GDPR 数据保留期清理（每日）"""
    from .services import GdprService

    archived = GdprService.cleanup_expired()
    # 2026-10-21 卡 C1: 顺手擦掉超期未下载的导出件密文 (PII 不该无限期留在库里)
    purged_exports = GdprService.cleanup_expired_exports()
    return {
        'cleaned_at': timezone.now().isoformat(),
        'archived_requests': archived,
        'purged_exports': purged_exports,
    }
