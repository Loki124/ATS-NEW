"""GDPR Celery tasks (PRD v4 §4.4)"""
import logging
from typing import Dict

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='apps.gdpr.tasks.run_retention_cleanup')
def run_retention_cleanup() -> Dict:
    """GDPR 数据保留期清理（每日）"""
    from .services import GdprService

    archived = GdprService.cleanup_expired()
    return {
        'cleaned_at': timezone.now().isoformat(),
        'archived_requests': archived,
    }
