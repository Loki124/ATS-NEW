"""Referral Services (PRD v4 §6.4 N+1/N+2 推荐)"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import NotFound, ValidationError
from apps.core.models import User

from .models import Referral, ReferralStatus, ReferralType

logger = logging.getLogger(__name__)


@dataclass
class ReferralCreateData:
    referrer_id: str
    candidate_id: str
    position_id: str
    referral_type: str
    note: str = ''
    actor: Optional[User] = None


class ReferralService:
    @staticmethod
    @transaction.atomic
    def create_referral(data: ReferralCreateData) -> Referral:
        from apps.candidate.models import Candidate
        from apps.position.models import Position

        try:
            Candidate.objects.get(id=data.candidate_id, deleted_at__isnull=True)
            Position.objects.get(id=data.position_id, deleted_at__isnull=True)
        except (Candidate.DoesNotExist, Position.DoesNotExist) as e:
            raise NotFound(str(e))

        if data.referral_type not in dict(ReferralType.choices):
            raise ValidationError(f'推荐类型 {data.referral_type} 非法')

        # 自动检测 N+1/N+2
        detected_type = ReferralService._auto_detect_type(
            data.referrer_id, data.candidate_id, data.position_id,
        )

        referral = Referral.objects.create(
            referrer_id=data.referrer_id,
            candidate_id=data.candidate_id,
            position_id=data.position_id,
            referral_type=data.referral_type,
            detected_type=detected_type,
            detection_detail={'auto': True, 'method': 'dept_match'},
            status=ReferralStatus.SUBMITTED,
            note=data.note,
            created_by=data.actor,
            updated_by=data.actor,
        )
        return referral

    @staticmethod
    def _auto_detect_type(referrer_id: str, candidate_id: str, position_id: str) -> str:
        """自动检测 N+1/N+2：基于推荐人/候选人/职位的部门层级关系"""
        try:
            from apps.candidate.models import Candidate
            from apps.position.models import Position
            from apps.core.models import User

            referrer = User.objects.only('id', 'department_id').get(id=referrer_id)
            position = Position.objects.only('id', 'department_id').get(id=position_id)
            referrer_dept_id = referrer.department_id

            if not referrer_dept_id or not position.department_id:
                return ReferralType.SOCIAL

            if referrer_dept_id == position.department_id:
                return ReferralType.N_PLUS_1

            # 检查 N+2：推荐人部门是职位部门的父部门
            from apps.core.models import Department
            try:
                position_dept = Department.objects.only('id', 'parent_id').get(id=position.department_id)
                if position_dept.parent_id == referrer_dept_id:
                    return ReferralType.N_PLUS_2
            except Department.DoesNotExist:
                pass

            return ReferralType.SOCIAL
        except Exception:
            return ReferralType.SOCIAL

    @staticmethod
    def mark_hired(referral_id: str, bonus_amount: float, actor: User) -> Referral:
        referral = Referral.objects.get(id=referral_id, deleted_at__isnull=True)
        referral.status = ReferralStatus.HIRED
        referral.bonus_amount = bonus_amount
        referral.bonus_paid_at = timezone.now()
        referral.save()
        return referral

    @staticmethod
    def mark_failed(referral_id: str, actor: User) -> Referral:
        referral = Referral.objects.get(id=referral_id, deleted_at__isnull=True)
        referral.status = ReferralStatus.FAILED
        referral.save()
        return referral
