"""Interview Services (PRD v4 §14.5) - 面试业务"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import NotFound, ValidationError
from apps.core.models import User

from .models import Interview, InterviewEvaluation, InterviewStatus

logger = logging.getLogger(__name__)


@dataclass
class InterviewCreateData:
    application_id: str
    stage_record_id: str
    round_number: int
    format: str
    scheduled_at: str
    duration_minutes: int
    location: str = ''
    meeting_url: str = ''
    interviewer_ids: List[str] = None
    actor: Optional[User] = None


class InterviewService:
    @staticmethod
    @transaction.atomic
    def create_interview(data: InterviewCreateData) -> Interview:
        from nanoid import generate as nanoid_generate
        from apps.application.models import Application, ApplicationStageRecord
        try:
            application = Application.objects.get(id=data.application_id, deleted_at__isnull=True)
            stage_record = ApplicationStageRecord.objects.get(id=data.stage_record_id)
        except (Application.DoesNotExist, ApplicationStageRecord.DoesNotExist) as e:
            raise NotFound(str(e))

        if not data.interviewer_ids:
            raise ValidationError('至少指定 1 个面试官')

        code = f'I{timezone.now().strftime("%Y%m%d%H%M%S")}{nanoid_generate(size=3).upper()}'
        interview = Interview.objects.create(
            code=code,
            application=application,
            stage_record=stage_record,
            round_number=data.round_number,
            format=data.format,
            scheduled_at=data.scheduled_at,
            duration_minutes=data.duration_minutes,
            location=data.location,
            meeting_url=data.meeting_url,
            status=InterviewStatus.SCHEDULED,
            created_by=data.actor,
            updated_by=data.actor,
        )
        interview.interviewers.set(data.interviewer_ids)
        return interview

    @staticmethod
    def submit_evaluation(
        interview_id: str,
        interviewer_id: str,
        scores: dict,
        overall_score: float,
        recommendation: str,
        comment: str,
        actor: User,
    ) -> InterviewEvaluation:
        interview = Interview.objects.get(id=interview_id, deleted_at__isnull=True)
        evaluation, _ = InterviewEvaluation.objects.update_or_create(
            interview=interview,
            interviewer_id=interviewer_id,
            defaults={
                'scores': scores,
                'overall_score': overall_score,
                'recommendation': recommendation,
                'comment': comment,
            },
        )
        return evaluation

    @staticmethod
    def mark_completed(interview_id: str, actor: User) -> Interview:
        interview = Interview.objects.get(id=interview_id, deleted_at__isnull=True)
        interview.status = InterviewStatus.COMPLETED
        interview.save()
        return interview

    @staticmethod
    def cancel(interview_id: str, reason: str, actor: User) -> Interview:
        interview = Interview.objects.get(id=interview_id, deleted_at__isnull=True)
        interview.status = InterviewStatus.CANCELLED
        interview.save()
        return interview

    @staticmethod
    def mark_no_show(interview_id: str, actor: User) -> Interview:
        interview = Interview.objects.get(id=interview_id, deleted_at__isnull=True)
        interview.status = InterviewStatus.NO_SHOW
        interview.save()
        return interview
