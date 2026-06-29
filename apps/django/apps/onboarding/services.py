"""Onboarding Services (PRD v4 §6.7) - 入职流程"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from django.db import transaction

from apps.common.exceptions import NotFound
from apps.core.models import User

from .models import Onboarding, OnboardingState

logger = logging.getLogger(__name__)


@dataclass
class OnboardingCreateData:
    offer_id: str
    candidate_id: str
    position_id: str
    start_date: str
    todo_list: List[str] = None
    actor: Optional[User] = None


class OnboardingService:
    @staticmethod
    @transaction.atomic
    def create_onboarding(data: OnboardingCreateData) -> Onboarding:
        from apps.offer.models import Offer
        from apps.candidate.models import Candidate
        from apps.position.models import Position
        try:
            offer = Offer.objects.get(id=data.offer_id, deleted_at__isnull=True)
            candidate = Candidate.objects.get(id=data.candidate_id, deleted_at__isnull=True)
            position = Position.objects.get(id=data.position_id, deleted_at__isnull=True)
        except (Offer.DoesNotExist, Candidate.DoesNotExist, Position.DoesNotExist) as e:
            raise NotFound(str(e))

        # 默认入职待办清单
        default_todo = data.todo_list or [
            '提交身份证复印件', '提交学历证明', '提交体检报告',
            '签订劳动合同', '办理社保转移', '领取办公设备',
            '完成入职培训', '加入部门群组',
        ]

        ob = Onboarding.objects.create(
            offer=offer,
            candidate=candidate,
            position=position,
            start_date=data.start_date,
            todo_list=default_todo,
            todo_completed={item: False for item in default_todo},
            state=OnboardingState.PENDING,
            created_by=data.actor,
            updated_by=data.actor,
        )
        return ob

    @staticmethod
    def start_preparing(onboarding_id: str, actor: User) -> Onboarding:
        ob = Onboarding.objects.get(id=onboarding_id, deleted_at__isnull=True)
        ob.start_preparing()
        ob.save()
        return ob

    @staticmethod
    def complete_item(onboarding_id: str, item: str, actor: User) -> Onboarding:
        ob = Onboarding.objects.get(id=onboarding_id, deleted_at__isnull=True)
        ob.todo_completed[item] = True
        ob.save(update_fields=['todo_completed', 'updated_at'])
        return ob

    @staticmethod
    def mark_completed(onboarding_id: str, actor: User) -> Onboarding:
        ob = Onboarding.objects.get(id=onboarding_id, deleted_at__isnull=True)
        ob.complete()
        ob.save()
        return ob

    @staticmethod
    def delay(onboarding_id: str, new_date: str, reason: str, actor: User) -> Onboarding:
        ob = Onboarding.objects.get(id=onboarding_id, deleted_at__isnull=True)
        from datetime import datetime
        new_start = datetime.strptime(new_date, '%Y-%m-%d').date()
        ob.delay(new_start)
        ob.save()
        return ob

    @staticmethod
    def enter_probation(onboarding_id: str, actor: User) -> Onboarding:
        ob = Onboarding.objects.get(id=onboarding_id, deleted_at__isnull=True)
        ob.enter_probation()
        ob.save()
        return ob

    @staticmethod
    def regularize(onboarding_id: str, result: str, actor: User) -> Onboarding:
        ob = Onboarding.objects.get(id=onboarding_id, deleted_at__isnull=True)
        ob.regularize(result=result)
        ob.save()
        return ob
