"""Invitation Services (PRD v4 §14.6 邀约业务)"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import NotFound
from apps.core.models import User

from .models import Invitation, InvitationState

logger = logging.getLogger(__name__)


@dataclass
class InvitationCreateData:
    application_id: str
    inviter_id: str
    expire_at: str
    is_grab_pool: bool = False
    actor: Optional[User] = None


class InvitationService:
    @staticmethod
    @transaction.atomic
    def create_invitation(data: InvitationCreateData) -> Invitation:
        from apps.application.models import Application
        try:
            Application.objects.get(id=data.application_id, deleted_at__isnull=True)
        except Application.DoesNotExist as e:
            raise NotFound(f'申请 {data.application_id} 不存在') from e

        inv = Invitation.objects.create(
            application_id=data.application_id,
            inviter_id=data.inviter_id,
            expire_at=data.expire_at,
            is_grab_pool=data.is_grab_pool,
            state=InvitationState.PENDING,
            created_by=data.actor,
            updated_by=data.actor,
        )
        return inv

    @staticmethod
    def start_inviting(invitation_id: str) -> Invitation:
        inv = Invitation.objects.get(id=invitation_id, deleted_at__isnull=True)
        inv.start_inviting()
        inv.save()
        return inv

    @staticmethod
    def succeed(invitation_id: str) -> Invitation:
        inv = Invitation.objects.get(id=invitation_id, deleted_at__isnull=True)
        inv.succeed()
        inv.save()
        return inv

    @staticmethod
    def fail(invitation_id: str, response: str = '', note: str = '') -> Invitation:
        inv = Invitation.objects.get(id=invitation_id, deleted_at__isnull=True)
        inv.fail(response=response, note=note)
        inv.save()
        return inv

    @staticmethod
    def timeout(invitation_id: str) -> Invitation:
        inv = Invitation.objects.get(id=invitation_id, deleted_at__isnull=True)
        inv.timeout()
        inv.save()
        return inv

    @staticmethod
    @transaction.atomic
    def grab(invitation_id: str, user: User) -> Invitation:
        inv = Invitation.objects.select_for_update().get(id=invitation_id, deleted_at__isnull=True)
        if not inv.is_grab_pool:
            from apps.common.exceptions import ValidationError
            raise ValidationError('该邀约不是抢单池模式')
        if inv.state != InvitationState.INVITING:
            from apps.common.exceptions import ValidationError
            raise ValidationError(f'当前状态 {inv.state} 不可抢单')
        inv.grabbed_by = user
        inv.grabbed_at = timezone.now()
        inv.save()
        return inv
