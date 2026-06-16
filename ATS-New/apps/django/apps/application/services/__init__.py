"""Application Services (PRD v4 §6, §13, §14.4)

申请生命周期：
- 创建申请（绑定候选人 + 职位 + 流程版本冻结）
- 启动申请 (PENDING → ACTIVE)
- 推进到下一阶段
- 跳过到指定阶段 (SKIP_TO)
- 暂停 / 恢复
- 软拒（保留所有历史记录）
- 撤回
- 超时归档
- 抢单认领 / 释放
- 升版本

所有状态转换都通过 `ApplicationHistory` 留下审计记录。
"""
from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import (
    NotFound,
    PermissionDenied,
    StateTransitionError,
)
from apps.process.models import ProcessStageLink, RecruitmentProcess
from apps.process.services.sequential_invitation import get_next_sequential_processor as _get_next_processor
from apps.time_limit.services import calc_time_limit
from apps.core.models import User
from apps.position.models import Position

from ..models import Application, ApplicationHistory, ApplicationState, ApplicationStageRecord

logger = logging.getLogger(__name__)


@dataclass
class ApplicationCreateData:
    """创建申请入参"""
    candidate_id: str
    position_id: str
    process_id: Optional[str] = None  # 不传则用 position.process
    initial_stage_id: Optional[str] = None  # 不传则用流程首个必经阶段
    actor: Optional[User] = None
    extra: Optional[Dict[str, Any]] = None


@dataclass
class AdvanceResult:
    """推进结果"""
    application: Application
    from_stage_id: Optional[str]
    to_stage_id: Optional[str]
    to_stage_name: str
    record: ApplicationStageRecord
    matched_rule_id: Optional[str] = None
    automation_triggered: bool = False


def _gen_application_code() -> str:
    """生成申请编号：A + yyyymmdd + 6位"""
    return f'A{timezone.now().strftime("%Y%m%d")}{secrets.token_hex(3).upper()}'


class ApplicationService:
    """申请服务"""

    # ----------------------------------------------------------
    # 创建申请
    # ----------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def create_application(data: ApplicationCreateData) -> Application:
        """创建申请

        - 流程版本冻结（BR-102）
        - 初始 stage_record 状态为 PENDING
        - 抢单模式下 stage_record 不立即分配
        """
        from apps.candidate.models import Candidate

        # 校验候选人
        try:
            candidate = Candidate.objects.get(id=data.candidate_id, deleted_at__isnull=True)
        except Candidate.DoesNotExist as e:
            raise NotFound(f'Candidate {data.candidate_id} not found') from e

        # 校验职位
        try:
            position = Position.objects.get(id=data.position_id, deleted_at__isnull=True)
        except Position.DoesNotExist as e:
            raise NotFound(f'Position {data.position_id} not found') from e

        # 流程：优先用入参，否则用 position 关联
        process = None
        if data.process_id:
            try:
                process = RecruitmentProcess.objects.get(id=data.process_id, deleted_at__isnull=True)
            except RecruitmentProcess.DoesNotExist as e:
                raise NotFound(f'Process {data.process_id} not found') from e
        else:
            process = position.process

        # 校验：未归档的流程
        if process.status == 'ARCHIVED':
            raise StateTransitionError(f'Process {process.code} is archived')

        # 校验：同一候选人同一职位未结束的申请不重复
        existing = Application.objects.filter(
            candidate=candidate,
            position=position,
            state__in=[
                ApplicationState.PENDING, ApplicationState.ACTIVE,
                ApplicationState.PAUSED, ApplicationState.OFFER_SENT,
                ApplicationState.OFFER_ACCEPTED,
            ],
            deleted_at__isnull=True,
        ).first()
        if existing:
            raise StateTransitionError(
                f'Application already exists: {existing.code} (state={existing.state})',
            )

        # 解析初始阶段
        first_link = process.stage_links.filter(
            is_required=True, deleted_at__isnull=True,
        ).order_by('order').first()
        if not first_link:
            raise StateTransitionError(f'Process {process.code} has no required stage')
        if data.initial_stage_id and data.initial_stage_id != first_link.stage_id:
            # 允许从非首阶段开始（如人才库二次投递）
            target_link = process.stage_links.filter(
                stage_id=data.initial_stage_id, deleted_at__isnull=True,
            ).first()
            if not target_link:
                raise NotFound(f'Stage {data.initial_stage_id} not in process')
            first_link = target_link

        # 计算限时
        tl = calc_time_limit(first_link, candidate)

        # 创建申请
        application = Application.objects.create(
            code=_gen_application_code(),
            candidate=candidate,
            position=position,
            process=process,
            workflow_version=process.current_version,
            current_link=first_link,
            current_stage=first_link.stage,
            state=ApplicationState.PENDING,
            time_limit_rule_id=tl.rule_id,
            total_time_limit_days=tl.total_days,
            stage_entered_at=timezone.now(),
            stage_deadline=timezone.now() + timedelta(days=tl.total_days) if tl.total_days else None,
        )

        # 创建初始 stage_record
        record = ApplicationStageRecord.objects.create(
            application=application,
            link=first_link,
            stage=first_link.stage,
            state=ApplicationStageRecord.StageState.PENDING,
            entered_at=timezone.now(),
            time_limit_rule_id=tl.rule_id,
            total_time_limit_days=tl.total_days,
            deadline=timezone.now() + timedelta(days=tl.total_days) if tl.total_days else None,
        )

        # 写历史
        ApplicationHistory.objects.create(
            application=application,
            action=ApplicationHistory.ActionType.CREATED,
            from_stage=None,
            to_stage=first_link.stage,
            detail={
                'process_code': process.code,
                'process_version': process.current_version,
                'initial_stage': first_link.stage.name,
                'time_limit_days': tl.total_days,
            },
            operator=data.actor,
        )

        logger.info(
            'Application created: %s candidate=%s position=%s stage=%s',
            application.code, candidate.id, position.code, first_link.stage.name,
        )
        return application

    # ----------------------------------------------------------
    # 启动申请 (PENDING → ACTIVE)
    # ----------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def start_application(application: Application,
                          actor: Optional[User] = None) -> Application:
        """启动申请"""
        if application.state != ApplicationState.PENDING:
            raise StateTransitionError(
                f'Cannot start application in state {application.state}',
            )
        try:
            application.start()
        except Exception as e:
            raise StateTransitionError(str(e)) from e
        application.last_advanced_at = timezone.now()
        application.save()

        # 候选人联动
        if application.candidate.current_state == 'APPLIED':
            from apps.candidate.services import CandidateService
            CandidateService.enter_process(
                application.candidate, actor=actor, application_id=application.id,
            )

        # 触发自动化
        try:
            from apps.automation.services import run_automation_for_trigger, TriggerContext
            ctx = TriggerContext(
                trigger_type='STAGE_ENTERED',
                candidate_id=application.candidate_id,
                application_id=application.id,
                stage_id=application.current_stage_id,
                extra={
                    'position_id': application.position_id,
                    'process_id': application.process_id,
                },
            )
            run_automation_for_trigger(ctx)
        except Exception as e:
            logger.warning('Automation trigger on application start failed: %s', e)

        ApplicationHistory.objects.create(
            application=application,
            action=ApplicationHistory.ActionType.ADVANCED,
            detail={'event': 'start', 'stage': application.current_stage.name if application.current_stage else None},
            operator=actor,
        )
        return application

    # ----------------------------------------------------------
    # 推进到下一阶段
    # ----------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def advance_application_to_next_stage(
        application: Application,
        actor: Optional[User] = None,
        skip_entry_condition: bool = False,
        reason: str = '',
    ) -> AdvanceResult:
        """推进到下一阶段

        - 校验通过当前阶段
        - 写入 record.exited_at / duration
        - 创建下一阶段 record
        - 若已是终阶段，触发 OFFER_SENT 状态机
        """
        if application.state not in (ApplicationState.ACTIVE, ApplicationState.PENDING):
            raise StateTransitionError(
                f'Cannot advance application in state {application.state}',
            )

        current_link = application.current_link
        if not current_link:
            raise StateTransitionError('Application has no current link')

        # 找到当前 record
        current_record = application.stage_records.filter(
            link=current_link, deleted_at__isnull=True,
        ).order_by('-entered_at').first()
        if not current_record:
            raise StateTransitionError('Current stage record not found')

        # 标记当前 record 为 PASSED
        now = timezone.now()
        current_record.state = ApplicationStageRecord.StageState.PASSED
        current_record.exited_at = now
        if current_record.entered_at:
            duration = now - current_record.entered_at
            current_record.duration_days = max(0, duration.days)
        current_record.auto_promoted = actor is None  # 无 actor 表示自动
        current_record.save()

        # 找到下一必经阶段
        next_link = application.process.stage_links.filter(
            order__gt=current_link.order,
            is_required=True,
            deleted_at__isnull=True,
        ).order_by('order').first()

        if not next_link:
            # 已到终阶段 → OFFER_SENT
            try:
                application.send_offer_state()
            except Exception:
                application.state = ApplicationState.OFFER_SENT
                application.save()
            ApplicationHistory.objects.create(
                application=application,
                action=ApplicationHistory.ActionType.OFFER_SENT,
                from_stage=current_link.stage,
                to_stage=None,
                detail={'reason': reason or 'reached_terminal_stage'},
                operator=actor,
            )
            return AdvanceResult(
                application=application,
                from_stage_id=current_link.stage_id,
                to_stage_id=None,
                to_stage_name='OFFER',
                record=current_record,
            )

        # 进入条件检查
        if not skip_entry_condition:
            from apps.entry_condition.services import evaluate_stage_entry
            cond_result = evaluate_stage_entry(next_link, application.candidate, {
                'demand': getattr(application.position, 'demand', None),
                'position': application.position,
            })
            if not cond_result.overall_passed:
                # 软拒：把候选人送回人才库
                from apps.candidate.services import CandidateService
                from apps.talent_pool.services import move_candidate_to_pool
                try:
                    CandidateService.move_to_talent_pool(
                        application.candidate,
                        entry_source='ENTRY_CONDITION_FAIL',
                        reason=cond_result.reject_message or 'Entry condition not met',
                        actor=actor,
                    )
                except Exception as e:
                    logger.warning('Candidate move to pool failed: %s', e)
                try:
                    move_candidate_to_pool(
                        candidate_id=application.candidate_id,
                        entry_source='ENTRY_CONDITION_FAIL',
                        entry_reason=cond_result.reject_message or 'Entry condition not met',
                        actor=actor,
                    )
                except Exception as e:
                    logger.warning('Pool entry create failed: %s', e)
                try:
                    application.mark_rejected()
                except Exception:
                    application.state = ApplicationState.REJECTED
                application.save()
                raise StateTransitionError(
                    f'Entry condition not met: {cond_result.reject_message}',
                )

        # 限时计算
        tl = calc_time_limit(next_link, application.candidate)

        # 创建下一阶段 record
        new_record = ApplicationStageRecord.objects.create(
            application=application,
            link=next_link,
            stage=next_link.stage,
            state=(
                ApplicationStageRecord.StageState.TO_BE_SCHEDULED
                if next_link.stage.supports_to_be_scheduled
                else ApplicationStageRecord.StageState.PENDING
            ),
            entered_at=now,
            time_limit_rule_id=tl.rule_id,
            total_time_limit_days=tl.total_days,
            deadline=now + timedelta(days=tl.total_days) if tl.total_days else None,
        )

        # 处理人初始化
        handlers = SequentialInvitationService.get_initial_handlers(next_link, application)
        if handlers:
            new_record.current_handlers = handlers
            new_record.save(update_fields=['current_handlers'])

        # 更新 application
        old_stage = application.current_stage
        application.current_link = next_link
        application.current_stage = next_link.stage
        application.last_advanced_at = now
        application.stage_entered_at = now
        application.stage_deadline = new_record.deadline
        application.time_limit_rule_id = tl.rule_id
        application.total_time_limit_days = tl.total_days
        application.save()

        # 写历史
        ApplicationHistory.objects.create(
            application=application,
            action=ApplicationHistory.ActionType.ADVANCED,
            from_stage=old_stage,
            to_stage=next_link.stage,
            detail={
                'reason': reason,
                'from_stage': old_stage.name if old_stage else None,
                'to_stage': next_link.stage.name,
                'time_limit_days': tl.total_days,
            },
            operator=actor,
        )

        # 触发自动化
        try:
            from apps.automation.services import run_automation_for_trigger, TriggerContext
            ctx = TriggerContext(
                trigger_type='STAGE_ENTERED',
                candidate_id=application.candidate_id,
                application_id=application.id,
                stage_id=next_link.stage_id,
                extra={
                    'position_id': application.position_id,
                    'process_id': application.process_id,
                },
            )
            run_automation_for_trigger(ctx)
        except Exception as e:
            logger.warning('Automation trigger on stage advance failed: %s', e)

        return AdvanceResult(
            application=application,
            from_stage_id=old_stage.id if old_stage else None,
            to_stage_id=next_link.stage_id,
            to_stage_name=next_link.stage.name,
            record=new_record,
        )

    # ----------------------------------------------------------
    # 跳过到指定阶段 (SKIP_TO)
    # ----------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def jump_application_to_stage(
        application: Application,
        target_stage_id: str,
        actor: Optional[User] = None,
        skip_entry_condition: bool = False,
        reason: str = '',
    ) -> AdvanceResult:
        """跳到指定阶段（中间阶段也走 PASSED 状态）"""
        if application.state not in (ApplicationState.ACTIVE, ApplicationState.PENDING):
            raise StateTransitionError(
                f'Cannot jump application in state {application.state}',
            )

        # 找到目标 link
        target_link = application.process.stage_links.filter(
            stage_id=target_stage_id, deleted_at__isnull=True,
        ).first()
        if not target_link:
            raise NotFound(f'Stage {target_stage_id} not in process')

        # 关闭中间所有 stage_record 为 PASSED/SKIPPED
        now = timezone.now()
        intermediate_records = application.stage_records.filter(
            link__order__lt=target_link.order, deleted_at__isnull=True,
        ).exclude(state=ApplicationStageRecord.StageState.PASSED)
        for rec in intermediate_records:
            rec.state = ApplicationStageRecord.StageState.SKIPPED
            rec.exited_at = now
            if rec.entered_at:
                duration = now - rec.entered_at
                rec.duration_days = max(0, duration.days)
            rec.save()

        # 关闭当前 record
        current_record = application.stage_records.filter(
            link=application.current_link, deleted_at__isnull=True,
        ).order_by('-entered_at').first()
        if current_record and current_record.state not in (
            ApplicationStageRecord.StageState.PASSED,
            ApplicationStageRecord.StageState.SKIPPED,
        ):
            current_record.state = ApplicationStageRecord.StageState.SKIPPED
            current_record.exited_at = now
            if current_record.entered_at:
                duration = now - current_record.entered_at
                current_record.duration_days = max(0, duration.days)
            current_record.save()

        # 进入条件
        if not skip_entry_condition:
            from apps.entry_condition.services import evaluate_stage_entry
            cond_result = evaluate_stage_entry(target_link, application.candidate, {
                'position': application.position,
            })
            if not cond_result.overall_passed:
                raise StateTransitionError(
                    f'Entry condition not met: {cond_result.reject_message}',
                )

        # 创建新 record
        tl = calc_time_limit(target_link, application.candidate)
        new_record = ApplicationStageRecord.objects.create(
            application=application,
            link=target_link,
            stage=target_link.stage,
            state=(
                ApplicationStageRecord.StageState.TO_BE_SCHEDULED
                if target_link.stage.supports_to_be_scheduled
                else ApplicationStageRecord.StageState.PENDING
            ),
            entered_at=now,
            time_limit_rule_id=tl.rule_id,
            total_time_limit_days=tl.total_days,
            deadline=now + timedelta(days=tl.total_days) if tl.total_days else None,
        )

        old_stage = application.current_stage
        application.current_link = target_link
        application.current_stage = target_link.stage
        application.last_advanced_at = now
        application.stage_entered_at = now
        application.stage_deadline = new_record.deadline
        application.time_limit_rule_id = tl.rule_id
        application.total_time_limit_days = tl.total_days
        application.save()

        ApplicationHistory.objects.create(
            application=application,
            action=ApplicationHistory.ActionType.ADVANCED,
            from_stage=old_stage,
            to_stage=target_link.stage,
            detail={'reason': reason, 'jump': True, 'from_stage': old_stage.name if old_stage else None},
            operator=actor,
        )

        return AdvanceResult(
            application=application,
            from_stage_id=old_stage.id if old_stage else None,
            to_stage_id=target_link.stage_id,
            to_stage_name=target_link.stage.name,
            record=new_record,
        )

    # ----------------------------------------------------------
    # 软拒（保留所有历史）
    # ----------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def soft_reject(application: Application, reason: str,
                    actor: Optional[User] = None) -> Application:
        """软拒当前阶段（PRD §6.3 规则1：保留所有历史记录）

        - 当前 record 标记 REJECTED
        - 不自动跳到下一阶段
        - 候选人保持 IN_PROCESS（由业务决定后续）
        """
        if application.state not in (ApplicationState.ACTIVE, ApplicationState.PENDING):
            raise StateTransitionError(
                f'Cannot soft reject in state {application.state}',
            )

        current_record = application.stage_records.filter(
            link=application.current_link, deleted_at__isnull=True,
        ).order_by('-entered_at').first()
        if not current_record:
            raise StateTransitionError('Current stage record not found')

        now = timezone.now()
        current_record.state = ApplicationStageRecord.StageState.REJECTED
        current_record.exited_at = now
        if current_record.entered_at:
            duration = now - current_record.entered_at
            current_record.duration_days = max(0, duration.days)
        current_record.note = (current_record.note or '') + f'\n[SOFT REJECTED] {reason}'
        current_record.save()

        # 写历史（不切换 application 状态）
        ApplicationHistory.objects.create(
            application=application,
            action=ApplicationHistory.ActionType.REJECTED,
            from_stage=application.current_stage,
            to_stage=application.current_stage,
            detail={'reason': reason, 'soft': True, 'stage': application.current_stage.name},
            operator=actor,
        )
        return application

    # ----------------------------------------------------------
    # 撤回
    # ----------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def withdraw(application: Application, reason: str,
                 actor: Optional[User] = None) -> Application:
        """候选人主动撤回"""
        if application.state in (
            ApplicationState.ONBOARDED,
            ApplicationState.WITHDRAWN,
        ):
            raise StateTransitionError(
                f'Cannot withdraw in state {application.state}',
            )
        from apps.candidate.services import CandidateService
        CandidateService.withdraw(application.candidate, reason, actor=actor)
        application.state = ApplicationState.WITHDRAWN
        application.save()
        # 关闭所有未完结记录
        now = timezone.now()
        application.stage_records.filter(
            state__in=[
                ApplicationStageRecord.StageState.PENDING,
                ApplicationStageRecord.StageState.PROCESSING,
                ApplicationStageRecord.StageState.TO_BE_SCHEDULED,
            ],
            deleted_at__isnull=True,
        ).update(state=ApplicationStageRecord.StageState.ARCHIVED, exited_at=now)
        ApplicationHistory.objects.create(
            application=application,
            action=ApplicationHistory.ActionType.REJECTED,
            detail={'reason': reason, 'withdraw': True},
            operator=actor,
        )
        return application

    # ----------------------------------------------------------
    # 暂停 / 恢复
    # ----------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def pause(application: Application, reason: str,
              actor: Optional[User] = None) -> Application:
        if application.state != ApplicationState.ACTIVE:
            raise StateTransitionError(
                f'Cannot pause in state {application.state}',
            )
        try:
            application.pause()
        except Exception as e:
            raise StateTransitionError(str(e)) from e
        application.save()
        ApplicationHistory.objects.create(
            application=application,
            action=ApplicationHistory.ActionType.PAUSED,
            detail={'reason': reason},
            operator=actor,
        )
        return application

    @staticmethod
    @transaction.atomic
    def resume(application: Application, actor: Optional[User] = None) -> Application:
        if application.state != ApplicationState.PAUSED:
            raise StateTransitionError(
                f'Cannot resume in state {application.state}',
            )
        try:
            application.resume()
        except Exception as e:
            raise StateTransitionError(str(e)) from e
        application.save()
        ApplicationHistory.objects.create(
            application=application,
            action=ApplicationHistory.ActionType.RESUMED,
            detail={},
            operator=actor,
        )
        return application

    # ----------------------------------------------------------
    # 升版本
    # ----------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def upgrade_workflow_version(application: Application, actor: Optional[User] = None) -> Application:
        """升版本（BR-104）"""
        new_version = application.process.current_version
        if new_version == application.workflow_version:
            raise StateTransitionError('Application is already on the latest version')
        old_version = application.workflow_version
        application.workflow_version = new_version
        application.save()
        ApplicationHistory.objects.create(
            application=application,
            action=ApplicationHistory.ActionType.UPGRADE_VERSION,
            detail={'from_version': old_version, 'to_version': new_version},
            operator=actor,
        )
        return application

    # ----------------------------------------------------------
    # 超时归档
    # ----------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def archive_timeout(application: Application) -> Application:
        """超时归档（Celery 调用）"""
        if application.state in (
            ApplicationState.ONBOARDED, ApplicationState.WITHDRAWN, ApplicationState.TIMEOUT,
        ):
            return application

        # 关闭当前 record
        current_record = application.stage_records.filter(
            link=application.current_link, deleted_at__isnull=True,
        ).order_by('-entered_at').first()
        if current_record and current_record.state not in (
            ApplicationStageRecord.StageState.PASSED,
            ApplicationStageRecord.StageState.FAILED,
            ApplicationStageRecord.StageState.ARCHIVED,
        ):
            current_record.state = ApplicationStageRecord.StageState.TIMEOUT
            current_record.exited_at = timezone.now()
            current_record.save()

        application.state = ApplicationState.TIMEOUT
        application.save()
        ApplicationHistory.objects.create(
            application=application,
            action=ApplicationHistory.ActionType.TIMEOUT,
            detail={'stage': application.current_stage.name if application.current_stage else None},
            operator=None,
        )
        return application


# ============================================================
# 便捷函数
# ============================================================
def create_application(data: ApplicationCreateData) -> Application:
    return ApplicationService.create_application(data)


def start_application(application: Application, actor: Optional[User] = None) -> Application:
    return ApplicationService.start_application(application, actor)


def advance_application_to_next_stage(
    application: Application, actor: Optional[User] = None,
    skip_entry_condition: bool = False, reason: str = '',
) -> AdvanceResult:
    return ApplicationService.advance_application_to_next_stage(
        application, actor, skip_entry_condition, reason,
    )


def jump_application_to_stage(
    application: Application, target_stage_id: str,
    actor: Optional[User] = None, skip_entry_condition: bool = False, reason: str = '',
) -> AdvanceResult:
    return ApplicationService.jump_application_to_stage(
        application, target_stage_id, actor, skip_entry_condition, reason,
    )


def soft_reject(application: Application, reason: str, actor: Optional[User] = None) -> Application:
    return ApplicationService.soft_reject(application, reason, actor)


def withdraw_application(application: Application, reason: str,
                         actor: Optional[User] = None) -> Application:
    return ApplicationService.withdraw(application, reason, actor)


def pause_application(application: Application, reason: str,
                      actor: Optional[User] = None) -> Application:
    return ApplicationService.pause(application, reason, actor)


def resume_application(application: Application, actor: Optional[User] = None) -> Application:
    return ApplicationService.resume(application, actor)
