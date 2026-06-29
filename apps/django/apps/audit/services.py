"""Audit Services (PRD v4 §13) - 审计日志业务"""
from __future__ import annotations

import logging
from typing import List, Optional

from django.db.models import Q
from django.utils import timezone

from apps.core.models import User

from .models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """审计日志服务"""

    @staticmethod
    def record(
        user: Optional[User],
        action: str,
        entity: str,
        entity_id: str = '',
        field: str = '',
        old_value: str = '',
        new_value: str = '',
        ip: str = '',
        user_agent: str = '',
        request_id: str = '',
    ) -> AuditLog:
        """记录一条审计日志"""
        log = AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            field=field,
            old_value=old_value[:1000],
            new_value=new_value[:1000],
            ip=ip,
            user_agent=user_agent[:500],
            request_id=request_id,
        )
        return log

    @staticmethod
    def query(
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        entity: Optional[str] = None,
        entity_id: Optional[str] = None,
        from_date=None,
        to_date=None,
        limit: int = 100,
    ):
        """查询审计日志"""
        qs = AuditLog.objects.all()
        if user_id:
            qs = qs.filter(user_id=user_id)
        if action:
            qs = qs.filter(action=action)
        if entity:
            qs = qs.filter(entity=entity)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        if from_date:
            qs = qs.filter(created_at__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__lte=to_date)
        return qs.order_by('-created_at')[:limit]

    @staticmethod
    def get_entity_history(entity: str, entity_id: str) -> List[AuditLog]:
        """获取实体的完整变更历史"""
        return list(AuditLog.objects.filter(
            entity=entity, entity_id=entity_id,
        ).order_by('-created_at'))

    @staticmethod
    def cleanup_old_logs(retention_days: int = 365 * 3) -> int:
        """清理过期日志"""
        from datetime import timedelta
        threshold = timezone.now() - timedelta(days=retention_days)
        count, _ = AuditLog.objects.filter(created_at__lt=threshold).delete()
        logger.info(f'Cleaned {count} old audit logs')
        return count
