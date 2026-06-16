"""Position Services (PRD v4 §14.2) - 职位业务逻辑"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import NotFound, PermissionDenied
from apps.core.models import User

from .models import Position, PositionState

logger = logging.getLogger(__name__)


@dataclass
class PositionCreateData:
    title: str
    department_id: str
    hiring_manager_id: str
    owner_id: str
    headcount: int
    process_id: str
    level: str = ''
    location: str = ''
    salary_min: float = 0
    salary_max: float = 0
    description: str = ''
    requirements: str = ''
    actor: Optional[User] = None


class PositionService:
    @staticmethod
    @transaction.atomic
    def create_position(data: PositionCreateData) -> Position:
        from nanoid import generate as nanoid_generate
        from apps.core.models import Department
        from apps.process.models import RecruitmentProcess

        try:
            department = Department.objects.get(id=data.department_id)
            process = RecruitmentProcess.objects.get(id=data.process_id, deleted_at__isnull=True)
        except (Department.DoesNotExist, RecruitmentProcess.DoesNotExist) as e:
            raise NotFound(str(e))

        code = f'P{timezone.now().strftime("%Y%m%d")}{nanoid_generate(size=4).upper()}'
        pos = Position.objects.create(
            code=code,
            title=data.title,
            department=department,
            hiring_manager_id=data.hiring_manager_id,
            owner_id=data.owner_id,
            headcount=data.headcount,
            filled_count=0,
            level=data.level,
            location=data.location,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            description=data.description,
            requirements=data.requirements,
            process=process,
            process_version=process.current_version,
            state=PositionState.DRAFT,
            created_by=data.actor,
            updated_by=data.actor,
        )
        return pos

    @staticmethod
    @transaction.atomic
    def publish(position_id: str, actor: User) -> Position:
        pos = Position.objects.get(id=position_id, deleted_at__isnull=True)
        pos.publish()
        pos.published_at = timezone.now()
        pos.save()
        return pos

    @staticmethod
    @transaction.atomic
    def start_recruiting(position_id: str, actor: User) -> Position:
        pos = Position.objects.get(id=position_id, deleted_at__isnull=True)
        pos.start_recruiting()
        pos.save()
        return pos

    @staticmethod
    @transaction.atomic
    def pause(position_id: str, actor: User) -> Position:
        pos = Position.objects.get(id=position_id, deleted_at__isnull=True)
        pos.pause()
        pos.save()
        return pos

    @staticmethod
    @transaction.atomic
    def resume(position_id: str, actor: User) -> Position:
        pos = Position.objects.get(id=position_id, deleted_at__isnull=True)
        pos.resume()
        pos.save()
        return pos

    @staticmethod
    @transaction.atomic
    def close(position_id: str, actor: User) -> Position:
        pos = Position.objects.get(id=position_id, deleted_at__isnull=True)
        pos.close()
        pos.closed_at = timezone.now()
        pos.save()
        return pos
