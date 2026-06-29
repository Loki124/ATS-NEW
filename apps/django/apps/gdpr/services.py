"""GDPR Services (PRD v4 §4.4) - 个人信息保护"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from apps.candidate.models import Candidate
from apps.common.exceptions import NotFound, PermissionDenied, ValidationError
from apps.core.models import User

from .models import GDPRRequest, GDPRRequestStatus, GDPRRequestType

logger = logging.getLogger(__name__)


class GdprService:
    """GDPR 业务服务"""

    @staticmethod
    @transaction.atomic
    def submit_request(
        candidate_id: str,
        request_type: str,
        submitted_email: str = '',
        verification_code: str = '',
    ) -> GDPRRequest:
        if request_type not in dict(GDPRRequestType.choices):
            raise ValidationError(f'请求类型 {request_type} 非法')
        if not submitted_email:
            raise ValidationError('需提供提交邮箱')
        if not verification_code:
            raise ValidationError('需提供验证码')

        try:
            candidate = Candidate.objects.get(id=candidate_id, deleted_at__isnull=True)
        except Candidate.DoesNotExist as e:
            raise NotFound(f'候选人 {candidate_id} 不存在') from e

        req = GDPRRequest.objects.create(
            candidate=candidate,
            request_type=request_type,
            status=GDPRRequestStatus.PENDING,
            submitted_email=submitted_email,
            verification_code=verification_code,
        )
        return req

    @staticmethod
    @transaction.atomic
    def approve_and_forget(request_id: str, processor: User) -> GDPRRequest:
        """被遗忘权 - 匿名化候选人数据"""
        try:
            req = GDPRRequest.objects.select_for_update().get(id=request_id)
        except GDPRRequest.DoesNotExist as e:
            raise NotFound(f'GDPR 请求 {request_id} 不存在') from e

        if not processor.is_superuser:
            raise PermissionDenied('仅超管可处理 GDPR 请求')

        candidate = req.candidate
        # 匿名化候选人 PII
        from nanoid import generate as nanoid_generate
        anonymized_id = f'ANON-{nanoid_generate(size=16)}'
        candidate.name = f'[匿名-{anonymized_id[:8]}]'
        candidate.phone = ''
        candidate.email = ''
        candidate.soft_delete()

        req.status = GDPRRequestStatus.COMPLETED
        req.processed_by = processor
        req.processed_at = timezone.now()
        req.result = f'已匿名化候选人 {candidate.id}'
        req.save()
        return req

    @staticmethod
    @transaction.atomic
    def approve_and_export(request_id: str, processor: User) -> GDPRRequest:
        """数据导出"""
        try:
            req = GDPRRequest.objects.select_for_update().get(id=request_id)
        except GDPRRequest.DoesNotExist as e:
            raise NotFound(f'GDPR 请求 {request_id} 不存在') from e

        candidate = req.candidate
        # 收集候选人所有 PII 数据
        export_data = {
            'candidate_id': candidate.id,
            'name': candidate.name,
            'phone': candidate.phone,
            'email': candidate.email,
            'exported_at': timezone.now().isoformat(),
        }

        req.status = GDPRRequestStatus.COMPLETED
        req.processed_by = processor
        req.processed_at = timezone.now()
        req.result = f'导出数据：{export_data}'
        req.save()
        return req

    @staticmethod
    @transaction.atomic
    def reject(request_id: str, reason: str, processor: User) -> GDPRRequest:
        try:
            req = GDPRRequest.objects.select_for_update().get(id=request_id)
        except GDPRRequest.DoesNotExist as e:
            raise NotFound(f'GDPR 请求 {request_id} 不存在') from e

        req.status = GDPRRequestStatus.REJECTED
        req.processed_by = processor
        req.processed_at = timezone.now()
        req.reject_reason = reason
        req.save()
        return req

    @staticmethod
    def cleanup_expired() -> int:
        """清理超期未处理的 GDPR 请求（5 年前）"""
        threshold = timezone.now() - timedelta(days=365 * 5)
        return GDPRRequest.objects.filter(
            created_at__lt=threshold,
            status=GDPRRequestStatus.PENDING,
        ).update(status='ARCHIVED')
