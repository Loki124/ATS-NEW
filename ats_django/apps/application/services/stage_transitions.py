"""Application Stage Services

提供：
- advance_application_to_next_stage: 推进到下一阶段
- jump_application_to_stage: 跳到指定阶段
- pause_application / resume_application
- timeout_application
"""
from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.entry_condition.services import evaluate_stage_entry

logger = logging.getLogger(__name__)


@transaction.atomic
def advance_application_to_next_stage(
    application,
    actor=None,
    skip_entry_condition: bool = False,
    reason: str = '',
) -> dict:
    """推进申请到下一阶段"""
    from .models import Application, ApplicationStageRecord
    from apps.process.models import ProcessStageLink

    if not application.current_link:
        return {
            'advanced': False,
            'reason': 'no current link',
        }

    # 找下一阶段
    next_link = ProcessStageLink.objects.filter(
        process=application.process,
        order__gt=application.current_link.order,
        deleted_at__isnull=True,
    ).order_by('order').first()

    if not next_link:
        return {
            'advanced': False,
            'reason': 'no next stage',
        }

    # 标记当前阶段完成
    current_sr = ApplicationStageRecord.objects.filter(
        application=application,
        stage=application.current_stage,
        state__in=[ApplicationStageRecord.StageState.NOT_STARTED,
                   ApplicationStageRecord.StageState.PENDING,
                   ApplicationStageRecord.StageState.PROCESSING,
                   ApplicationStageRecord.StageState.TO_BE_SCHEDULED],
        deleted_at__isnull=True,
    ).order_by('-entered_at').first()
    if current_sr:
        current_sr.state = ApplicationStageRecord.StageState.PASSED
        current_sr.exited_at = timezone.now()
        current_sr.save(update_fields=['state', 'exited_at', 'updated_at'])

    # 进入条件评估
    if not skip_entry_condition:
        try:
            entry_result = evaluate_stage_entry(next_link, application.candidate)
            if not entry_result.overall_passed:
                return {
                    'advanced': False,
                    'reason': 'entry_condition_not_met',
                    'reject_message': entry_result.reject_message,
                }
        except Exception as e:
            logger.exception('Entry condition evaluation failed: %s', e)
            return {
                'advanced': False,
                'reason': f'entry_condition_error: {e}',
            }

    # 创建下一阶段记录
    next_sr = ApplicationStageRecord.objects.create(
        application=application,
        stage=next_link.stage,
        link=next_link,
        state=ApplicationStageRecord.StageState.PENDING,
        entered_at=timezone.now(),
        created_by=actor,
        updated_by=actor,
    )

    # 更新 application
    application.current_link = next_link
    application.current_stage = next_link.stage
    application.stage_entered_at = timezone.now()
    application.last_advanced_at = timezone.now()
    application.save(update_fields=[
        'current_link', 'current_stage', 'stage_entered_at', 'last_advanced_at', 'updated_at',
    ])

    # 写 history
    from .models import ApplicationHistory
    ApplicationHistory.objects.create(
        application=application,
        action=ApplicationHistory.ActionType.ADVANCED,
        from_stage=current_sr.stage if current_sr else None,
        to_stage=next_link.stage,
        detail={'reason': reason, 'next_stage_record_id': next_sr.id},
        operator=actor,
        is_auto=bool(reason and 'AUTO' in reason.upper()),
    )

    logger.info(
        'Application %s advanced: %s -> %s by %s',
        application.id,
        current_sr.stage.name if current_sr else 'N/A',
        next_link.stage.name, actor,
    )

    return {
        'advanced': True,
        'from_stage_id': current_sr.stage_id if current_sr else None,
        'from_stage_name': current_sr.stage.name if current_sr else None,
        'next_stage_id': next_link.stage_id,
        'next_stage_name': next_link.stage.name,
        'next_stage_record_id': next_sr.id,
    }


@transaction.atomic
def jump_application_to_stage(
    application,
    target_stage_id: str,
    actor=None,
    skip_entry_condition: bool = False,
    reason: str = '',
) -> dict:
    """跳转到指定阶段"""
    from .models import Application, ApplicationStageRecord, ApplicationHistory
    from apps.process.models import ProcessStageLink

    target_link = ProcessStageLink.objects.filter(
        process=application.process,
        stage_id=target_stage_id,
        deleted_at__isnull=True,
    ).first()
    if not target_link:
        return {
            'jumped': False,
            'reason': 'target_stage_not_in_process',
        }

    if not skip_entry_condition:
        entry_result = evaluate_stage_entry(target_link, application.candidate)
        if not entry_result.overall_passed:
            return {
                'jumped': False,
                'reason': 'entry_condition_not_met',
                'reject_message': entry_result.reject_message,
            }

    # 跳过中间阶段
    if application.current_link:
        ApplicationStageRecord.objects.filter(
            application=application,
            link__order__gt=application.current_link.order,
            link__order__lt=target_link.order,
            deleted_at__isnull=True,
        ).update(state=ApplicationStageRecord.StageState.SKIPPED, exited_at=timezone.now())

    # 创建目标阶段记录
    sr = ApplicationStageRecord.objects.create(
        application=application,
        stage=target_link.stage,
        link=target_link,
        state=ApplicationStageRecord.StageState.PENDING,
        entered_at=timezone.now(),
        created_by=actor,
        updated_by=actor,
    )
    application.current_link = target_link
    application.current_stage = target_link.stage
    application.stage_entered_at = timezone.now()
    application.save(update_fields=[
        'current_link', 'current_stage', 'stage_entered_at', 'updated_at',
    ])

    ApplicationHistory.objects.create(
        application=application,
        action=ApplicationHistory.ActionType.SKIPPED,
        to_stage=target_link.stage,
        detail={'reason': reason, 'target_stage_record_id': sr.id},
        operator=actor,
        is_auto=bool(reason and 'AUTO' in reason.upper()),
    )

    return {
        'jumped': True,
        'stage_id': target_link.stage_id,
        'stage_name': target_link.stage.name,
    }


@transaction.atomic
def pause_application(application, reason: str = '', actor=None) -> dict:
    """暂停申请"""
    if application.state == 'PAUSED':
        return {'paused': False, 'reason': 'already paused'}
    try:
        application.pause()
        application.save(update_fields=['state', 'updated_at'])
    except Exception as e:
        return {'paused': False, 'reason': f'transition_error: {e}'}
    return {'paused': True}


@transaction.atomic
def resume_application(application, actor=None) -> dict:
    """恢复申请"""
    if application.state != 'PAUSED':
        return {'resumed': False, 'reason': 'not paused'}
    try:
        application.resume()
        application.save(update_fields=['state', 'updated_at'])
    except Exception as e:
        return {'resumed': False, 'reason': f'transition_error: {e}'}
    return {'resumed': True}


@transaction.atomic
def timeout_application(application, reason: str = '', actor=None) -> dict:
    """超时归档"""
    from .models import ApplicationHistory
    if application.state in ('ONBOARDED', 'REJECTED', 'WITHDRAWN', 'TIMEOUT'):
        return {'timed_out': False, 'reason': 'final state'}
    application.state = 'TIMEOUT'
    application.save(update_fields=['state', 'updated_at'])
    ApplicationHistory.objects.create(
        application=application,
        action=ApplicationHistory.ActionType.TIMEOUT,
        detail={'reason': reason},
        operator=actor,
        is_auto=True,
    )
    return {'timed_out': True, 'reason': reason}
