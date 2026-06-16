"""Offer Services (PRD v4 §6.6, §14.5) - Offer 业务逻辑"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import NotFound
from apps.core.models import User

from .models import Offer, OfferState

logger = logging.getLogger(__name__)


@dataclass
class OfferCreateData:
    application_id: str
    candidate_id: str
    position_id: str
    salary: float
    start_date: str  # ISO date
    expire_date: str
    level: str = ''
    position_title: str = ''
    actor: Optional[User] = None


class OfferService:
    @staticmethod
    @transaction.atomic
    def create_offer(data: OfferCreateData) -> Offer:
        from nanoid import generate as nanoid_generate
        from apps.application.models import Application
        from apps.candidate.models import Candidate
        from apps.position.models import Position

        try:
            application = Application.objects.get(id=data.application_id, deleted_at__isnull=True)
            candidate = Candidate.objects.get(id=data.candidate_id, deleted_at__isnull=True)
            position = Position.objects.get(id=data.position_id, deleted_at__isnull=True)
        except (Application.DoesNotExist, Candidate.DoesNotExist, Position.DoesNotExist) as e:
            raise NotFound(str(e))

        code = f'OFR{timezone.now().strftime("%Y%m%d")}{nanoid_generate(size=4).upper()}'
        offer = Offer.objects.create(
            code=code,
            application=application,
            candidate=candidate,
            position=position,
            salary=data.salary,
            start_date=data.start_date,
            expire_date=data.expire_date,
            level=data.level,
            position_title=data.position_title,
            state=OfferState.DRAFT,
            created_by=data.actor,
            updated_by=data.actor,
        )
        return offer

    @staticmethod
    def submit_approval(offer_id: str, actor: User) -> Offer:
        offer = Offer.objects.get(id=offer_id, deleted_at__isnull=True)
        offer.submit_approval()
        offer.save()
        return offer

    @staticmethod
    def approve(offer_id: str, actor: User) -> Offer:
        offer = Offer.objects.get(id=offer_id, deleted_at__isnull=True)
        offer.approver = actor
        offer.approve()
        offer.save()
        return offer

    @staticmethod
    def reject(offer_id: str, reason: str, actor: User) -> Offer:
        offer = Offer.objects.get(id=offer_id, deleted_at__isnull=True)
        offer.reject()
        offer.save()
        return offer

    @staticmethod
    def send_to_candidate(offer_id: str, actor: User) -> Offer:
        offer = Offer.objects.get(id=offer_id, deleted_at__isnull=True)
        offer.send()
        offer.save()
        # 触发通知
        try:
            from apps.notification.services import NotificationService
            NotificationService.send_notification(
                recipient=offer.candidate,
                event='offer.sent',
                context={'offer': offer},
                channels=['IN_APP', 'EMAIL'],
            )
        except Exception as e:
            logger.warning('Offer notification failed: %s', e)
        return offer

    @staticmethod
    def candidate_accept(offer_id: str, actor: User) -> Offer:
        offer = Offer.objects.get(id=offer_id, deleted_at__isnull=True)
        offer.accept()
        offer.save()
        return offer

    @staticmethod
    def candidate_reject(offer_id: str, reason: str, actor: User) -> Offer:
        offer = Offer.objects.get(id=offer_id, deleted_at__isnull=True)
        offer.candidate_reject(reason=reason)
        offer.save()
        return offer

    @staticmethod
    def mark_onboarded(offer_id: str, actor: User) -> Offer:
        offer = Offer.objects.get(id=offer_id, deleted_at__isnull=True)
        offer.onboarded()
        offer.save()
        return offer
