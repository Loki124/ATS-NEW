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
from .stage_mapping import StageMappingError, resolve_stage_mapping

logger = logging.getLogger(__name__)

# 可被"超时归档"处理的状态集合。
# 必须与 Application.timeout_archive 的 @transition source 保持一致 ——
# 前者是业务前置判断（不满足则幂等返回），后者是状态机的硬约束。
# 已发 Offer（OFFER_SENT / OFFER_ACCEPTED）属结果待定，不做自动超时归档；
# ONBOARDED / REJECTED / WITHDRAWN / TIMEOUT 是终态。
TIMEOUT_ARCHIVABLE_STATES: Tuple[str, ...] = (
    ApplicationState.PENDING,
    ApplicationState.ACTIVE,
    ApplicationState.PAUSED,
)

# 必须与 Application.withdraw 的 @transition source 一致 ——
# 前者是业务前置判断（不满足则直接 409），后者是状态机的硬约束。
# 已发 Offer（OFFER_SENT / OFFER_ACCEPTED）仍属"入职前可反悔"区间，允许撤回；
# ONBOARDED / REJECTED / TIMEOUT / WITHDRAWN 是终态，不允许撤回。
WITHDRAWABLE_STATES: Tuple[str, ...] = (
    ApplicationState.PENDING,
    ApplicationState.ACTIVE,
    ApplicationState.PAUSED,
    ApplicationState.OFFER_SENT,
    ApplicationState.OFFER_ACCEPTED,
)


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
            total_time_limit_days=tl.total_lock_days,
            stage_entered_at=timezone.now(),
            stage_deadline=timezone.now() + timedelta(days=tl.total_lock_days) if tl.total_lock_days else None,
        )

        # 创建初始 stage_record
        record = ApplicationStageRecord.objects.create(
            application=application,
            link=first_link,
            stage=first_link.stage,
            state=ApplicationStageRecord.StageState.PENDING,
            entered_at=timezone.now(),
            time_limit_rule_id=tl.rule_id,
            total_time_limit_days=tl.total_lock_days,
            deadline=timezone.now() + timedelta(days=tl.total_lock_days) if tl.total_lock_days else None,
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
                'time_limit_days': tl.total_lock_days,
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
        except Exception as e:  # noqa: BLE001 — django-fsm-2 TransitionNotAllowed 等会抛 Exception 子类, 统一包成 StateTransitionError
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
        except Exception as e:  # noqa: BLE001 — 自动化触发失败不应阻断主流程 (start 历史/状态机已写入, automation 是 best-effort)
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
            # 状态机拒绝转换时**不得**裸赋值绕过（state 是 protected FSMField，
            # 裸赋值必抛 AttributeError；即便不抛也属于 fail-open）。
            # 统一转成项目既有的 StateTransitionError，view 层会返 409。
            try:
                application.send_offer_state()
            except Exception as e:  # noqa: BLE001 — django-fsm-2 转换异常统一包成 StateTransitionError, view 层返 409
                raise StateTransitionError(
                    f'Cannot mark application {application.code} as OFFER_SENT '
                    f'from state {application.state}: {e}',
                ) from e
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
                except Exception as e:  # noqa: BLE001 — 候选人入池失败不应阻断 reject (reject 状态机是主路径, 入池是 best-effort)
                    logger.warning('Candidate move to pool failed: %s', e)
                try:
                    move_candidate_to_pool(
                        candidate_id=application.candidate_id,
                        entry_source='ENTRY_CONDITION_FAIL',
                        entry_reason=cond_result.reject_message or 'Entry condition not met',
                        actor=actor,
                    )
                except Exception as e:  # noqa: BLE001 — 同上, 池条目写入失败不应阻断主 reject 流程
                    logger.warning('Pool entry create failed: %s', e)
                # 同上：不允许用裸赋值绕过状态机。
                # mark_rejected 的 source 是 [ACTIVE, PAUSED]，若当前是 PENDING
                # 则转换会被拒绝 —— 明确抛错，而不是静默带病继续。
                try:
                    application.mark_rejected()
                except Exception as e:  # noqa: BLE001 — django-fsm-2 转换异常统一包成 StateTransitionError, view 层返 409
                    raise StateTransitionError(
                        f'Entry condition not met ({cond_result.reject_message}), '
                        f'and application {application.code} cannot transition to '
                        f'REJECTED from state {application.state}: {e}',
                    ) from e
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
            total_time_limit_days=tl.total_lock_days,
            deadline=now + timedelta(days=tl.total_lock_days) if tl.total_lock_days else None,
        )

        # 处理人初始化
        #
        # P0 修复（2026-08-10）：原为
        #     handlers = SequentialInvitationService.get_initial_handlers(next_link, application)
        # 而 SequentialInvitationService 在**全仓零定义、零导入**，仅此一处使用，
        # 且自仓库初始 commit（b0fd6ad，2026-06-29）起就是这副样子。也就是说
        # advance_application_to_next_stage 只要「存在下一阶段」，走到这里必抛
        # NameError —— 这条核心推进路径从来没有真正跑通过。这是一段写了调用、
        # 没写实现的占位代码。
        #
        # 现处置：不臆造业务语义。current_handlers 走模型默认值（空列表），
        # 语义为「新阶段暂无预设处理人，等待抢单/指派」，与 services/grab.py
        # 的认领流程（抢单时把 user.id 追加进 current_handlers）自洽。
        #
        # TODO(产品确认)：顺序邀约（SequentialInvitation）的初始处理人规则若确有需求，
        #   须先补产品规格再单独实现，不得再以裸调用形式挂在主链路上。

        # 更新 application
        old_stage = application.current_stage
        application.current_link = next_link
        application.current_stage = next_link.stage
        application.last_advanced_at = now
        application.stage_entered_at = now
        application.stage_deadline = new_record.deadline
        application.time_limit_rule_id = tl.rule_id
        application.total_time_limit_days = tl.total_lock_days
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
                'time_limit_days': tl.total_lock_days,
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
        except Exception as e:  # noqa: BLE001 — 阶段推进时的 automation 触发失败不应阻断主流程 (advance 已落库, automation 是 best-effort)
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
            total_time_limit_days=tl.total_lock_days,
            deadline=now + timedelta(days=tl.total_lock_days) if tl.total_lock_days else None,
        )

        old_stage = application.current_stage
        application.current_link = target_link
        application.current_stage = target_link.stage
        application.last_advanced_at = now
        application.stage_entered_at = now
        application.stage_deadline = new_record.deadline
        application.time_limit_rule_id = tl.rule_id
        application.total_time_limit_days = tl.total_lock_days
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
        if application.state not in WITHDRAWABLE_STATES:
            raise StateTransitionError(
                f'Cannot withdraw in state {application.state}',
            )
        from apps.candidate.services import CandidateService
        CandidateService.withdraw(application.candidate, reason, actor=actor)
        # state 是 protected FSMField，只能走 @transition 方法（Application.withdraw）。
        # 转换被拒绝时统一转成 StateTransitionError，view 层返 409。
        try:
            application.withdraw()
        except Exception as e:  # noqa: BLE001 — django-fsm-2 转换异常统一包成 StateTransitionError, view 层返 409
            raise StateTransitionError(
                f'Cannot withdraw application {application.code} '
                f'in state {application.state}: {e}',
            ) from e
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
        except Exception as e:  # noqa: BLE001 — django-fsm-2 转换异常统一包成 StateTransitionError, view 层返 409
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
        except Exception as e:  # noqa: BLE001 — django-fsm-2 转换异常统一包成 StateTransitionError, view 层返 409
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
    def upgrade_workflow_version(
        application: Application,
        actor: Optional[User] = None,
        target_process: Optional[RecruitmentProcess] = None,
    ) -> Application:
        """把申请升到同一流程线（``code``）的最新版本行（BR-104 / §1.3）。

        T3 之前这里只改了一个 ``workflow_version`` 字符串：``application.process``
        仍指向旧版本行，``current_link`` 仍指向**旧流程的**关联。也就是说"升版本"
        只是把一个展示用的版本号刷新了一下，候选人实际跑的还是老流程 —— 而且
        ``workflow_version`` 与 ``process.current_version`` 从此可能不一致，
        后续任何按版本号做的判断都会读到自相矛盾的数据。

        现在做的是真升版本：

        1. **解析目标**：默认取同 ``code`` 且 ``is_latest=True`` 的 live 行
           （T1 的 C3' 表达式唯一索引保证这样的行至多一条）；
        2. **校验**：禁跨 code / 禁升到非最新的中间版 / 禁升到归档版 / 禁降版本；
        3. **算落点**：调 T7 的 :func:`resolve_stage_mapping`（纯函数，先算后写）；
        4. **改指**：``process`` + ``workflow_version`` + ``current_link`` +
           ``current_stage`` 四个字段一起落库，不留半截状态；
        5. **写审计**：``detail`` 含 ``stage_remapped``，``from_*`` 全部取自
           **赋值前**采集的快照。

        ⚠️ 审计快照必须在改指**之前**采集（§1.3.2）。被删除的死代码
        ``versioning.upgrade_application_to_latest_version`` 正是先写
        ``application.workflow_version = ...`` 再在 return 里读它当 ``from_version``
        （V5 读后写 bug），使审计里的 ``from_version`` 恒等于 ``to_version``——
        审计看上去有记录，实际上永远查不出"从哪升上来的"。

        Args:
            application: 待升版本的申请。
            actor: 操作人，写进审计。
            target_process: 显式指定目标版本行。不传则自动解析同 code 的最新版。
                传了也必须通过全部校验（同 code + is_latest + 未归档 + 不降版本），
                它只是省掉一次查询，**不是**绕过校验的后门。

        Returns:
            改指后的 ``application``（已落库）。

        Raises:
            StateTransitionError: 任一校验不通过，或目标流程没有可落脚的阶段。
                view 层统一转 409。
        """
        current_process = application.process

        # ---------- 1. 解析目标版本行 ----------
        if target_process is None:
            target_process = RecruitmentProcess.objects.filter(
                code=current_process.code,
                is_latest=True,
                deleted_at__isnull=True,
            ).first()
            if target_process is None:
                raise StateTransitionError(
                    f'流程线 {current_process.code} 没有 is_latest=True 的最新版本行，无法升版本',
                )

        # ---------- 2. 校验 ----------
        # 2.1 禁跨 code：换流程线是 change-process 的语义，不能借升版本的壳偷偷做掉
        if target_process.code != current_process.code:
            raise StateTransitionError(
                f'禁止跨流程线升版本：当前 {current_process.code} → 目标 {target_process.code}；'
                f'如需更换流程请走换流程接口',
            )

        # 2.2 目标必须是最新版：升到中间版本会让 is_latest 失去"大家都在最新版上"的含义，
        #     且下次再升时无从判断该不该动
        if not target_process.is_latest:
            raise StateTransitionError(
                f'目标版本 {target_process.current_version} 不是最新版（is_latest=False），'
                f'不允许升到中间版本',
            )
        if target_process.deleted_at is not None:
            raise StateTransitionError(
                f'目标版本 {target_process.current_version} 已被删除，不允许升版本',
            )

        # 2.3 禁归档
        if target_process.status == 'ARCHIVED':
            raise StateTransitionError(
                f'目标版本 {target_process.current_version} 已归档，不允许升版本',
            )

        # 2.4 已在目标行上 → 幂等地拒绝（保持既有 409 语义，避免刷出无意义的审计）
        if target_process.id == current_process.id:
            raise StateTransitionError('Application is already on the latest version')

        # 2.5 禁降版本
        if target_process.version_seq < current_process.version_seq:
            raise StateTransitionError(
                f'禁止降版本：当前 V{current_process.version_seq} → '
                f'目标 V{target_process.version_seq}',
            )

        # ---------- 3. 先算落点（纯函数，算不出来就在写库之前失败） ----------
        try:
            mapping = resolve_stage_mapping(application, target_process)
        except StageMappingError as e:
            raise StateTransitionError(
                f'无法升级到版本 {target_process.current_version}：{e}',
            ) from e

        # ---------- 4. 采集快照（必须早于任何赋值，§1.3.2） ----------
        old_process_id = current_process.id
        old_process_version = current_process.current_version
        old_workflow_version = application.workflow_version
        old_stage = application.current_stage
        old_stage_id = application.current_stage_id
        old_link_id = application.current_link_id

        # ---------- 5. 真正改指 ----------
        application.process = target_process
        application.workflow_version = target_process.current_version
        application.current_link = mapping.link
        application.current_stage = mapping.stage
        application.save(update_fields=[
            'process', 'workflow_version', 'current_link', 'current_stage', 'updated_at',
        ])

        # ---------- 6. 审计 ----------
        detail = mapping.as_audit_detail()
        detail.update({
            'from_version': old_workflow_version,
            'to_version': target_process.current_version,
            'from_process_id': old_process_id,
            'to_process_id': target_process.id,
            'from_process_version': old_process_version,
            'to_process_version': target_process.current_version,
            'process_code': target_process.code,
        })
        # mapping 的 from_* 快照在「current_link 为空」时是 None，用申请自身的
        # 残留字段补齐，保证审计里"从哪来"永远可追
        detail['from_link_id'] = detail['from_link_id'] or old_link_id
        detail['from_stage_id'] = detail['from_stage_id'] or old_stage_id

        ApplicationHistory.objects.create(
            application=application,
            action=ApplicationHistory.ActionType.UPGRADE_VERSION,
            from_stage=old_stage,
            to_stage=mapping.stage,
            detail=detail,
            operator=actor,
        )

        logger.info(
            'Application %s upgraded: process %s(%s) -> %s(%s), stage %s -> %s (remapped=%s)',
            application.code, old_process_id, old_workflow_version,
            target_process.id, target_process.current_version,
            old_stage_id, mapping.link.stage_id, mapping.remapped,
        )
        return application

    # ----------------------------------------------------------
    # 跨流程线迁移
    # ----------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def change_process(
        application: Application,
        target_process: RecruitmentProcess,
        target_stage_link: ProcessStageLink,
        actor: Optional[User] = None,
        reason: str = '',
    ) -> Application:
        """跨流程线迁移（决策 2 / §3.2）。

        与 :meth:`upgrade_workflow_version` 的区别有两点，都是本质区别：

        1. **跨 code**：upgrade 明确禁跨 code（换流程线得走这里）；这里则相反，
           同一行流程会被当成无意义操作直接拒。
        2. **落点由操作员显式指定**：不调 :func:`resolve_stage_mapping` 的
           "最近前序"算法。两条流程线的 ``order`` 编号体系彼此独立（社招线
           INTERVIEW=3、校招线 INTERVIEW=2），数值无可比性；硬套 order 会得到
           "看起来有、实则错"的落点，比让 HR 自己选更危险（§3.3）。
           服务端只做合法性校验，不猜。

        历史 ``ApplicationStageRecord`` 保留指向旧流程的 link（冻结审计）。
        跨线后阶段记录混合两条线的 link，是 correction 操作的正常结果。

        Args:
            application: 待迁移的申请。
            target_process: 目标流程线的版本行。
            target_stage_link: 目标流程内的落点关联（``ProcessStageLink``），
                必须属于 ``target_process``。
            actor: 操作人，写进审计。
            reason: 变更理由（端点层已强制必填，审计完整性 / 防滥用）。

        Returns:
            改指后的 ``application``（已落库）。

        Raises:
            StateTransitionError: 任一校验不通过。view 层统一转 409。
        """
        # ---------- 1. 校验（全部先于任何写入） ----------
        if target_process.id == application.process_id:
            raise StateTransitionError('目标流程与当前流程相同')
        if target_process.status != 'ENABLED':
            raise StateTransitionError('目标流程不可用（已归档或非启用）')
        if getattr(target_process, 'deleted_at', None) is not None:
            raise StateTransitionError('目标流程不可用（已删除）')
        if target_stage_link.process_id != target_process.id:
            raise StateTransitionError('目标阶段不属于目标流程')
        if getattr(target_stage_link, 'deleted_at', None) is not None:
            raise StateTransitionError('目标阶段已删除')

        # ---------- 2. 采集审计快照 ----------
        # §1.3.2 硬约定：快照必须早于任何赋值。死代码
        # ``versioning.upgrade_application_to_latest_version`` 的 V5 bug 就是先写
        # ``application.workflow_version = ...`` 再读它当 ``from_version``，
        # 使审计里"从哪来"恒等于"到哪去"—— 有记录，但永远查不出真相。
        old_process = application.process
        old_stage = application.current_stage
        old_link = application.current_link
        old_version = application.workflow_version

        # ---------- 3. 真正改指（四件套一起落库，不留半截状态） ----------
        application.process = target_process
        application.workflow_version = target_process.current_version
        application.current_link = target_stage_link
        application.current_stage = target_stage_link.stage
        application.save(update_fields=[
            'process', 'workflow_version', 'current_link', 'current_stage', 'updated_at',
        ])

        # ---------- 4. 审计 ----------
        # from_stage / to_stage 两个 **FK 列** 必须与 detail 里的 code 字符串并存：
        # 规格 §3.2 的伪代码只写了 detail，照抄会让这两列全 NULL，与
        # UPGRADE_VERSION 的审计形态分叉，前端时间线渲染会缺阶段信息。
        ApplicationHistory.objects.create(
            application=application,
            action=ApplicationHistory.ActionType.CHANGE_PROCESS,
            from_stage=old_stage,
            to_stage=target_stage_link.stage,
            detail={
                'from_process_id': old_process.id if old_process else None,
                'to_process_id': target_process.id,
                'from_process_code': old_process.code if old_process else None,
                'to_process_code': target_process.code,
                'from_version': old_version,
                'to_version': target_process.current_version,
                'from_link_id': old_link.id if old_link else None,
                'to_link_id': target_stage_link.id,
                'from_stage': old_stage.code if old_stage else None,
                'to_stage': target_stage_link.stage.code,
                'reason': reason,
            },
            operator=actor,
        )

        logger.info(
            'Application %s changed process: %s(%s) -> %s(%s), stage %s -> %s',
            application.code,
            old_process.code if old_process else None, old_version,
            target_process.code, target_process.current_version,
            old_stage.code if old_stage else None, target_stage_link.stage.code,
        )
        return application

    # ----------------------------------------------------------
    # 超时归档
    # ----------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def timeout_archive(application: Application) -> Application:
        """超时归档（Celery 调用）

        幂等：状态不在 ``TIMEOUT_ARCHIVABLE_STATES`` 内时原样返回、不做任何写入。
        调用方（tasks.archive_stale_applications）据返回值的 state 判定是否真的归档。
        """
        if application.state not in TIMEOUT_ARCHIVABLE_STATES:
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

        # 同 withdraw：protected FSMField 只能走 @transition（Application.timeout_archive）。
        try:
            application.timeout_archive()
        except Exception as e:  # noqa: BLE001 — django-fsm-2 转换异常统一包成 StateTransitionError, view 层返 409
            raise StateTransitionError(
                f'Cannot archive application {application.code} as TIMEOUT '
                f'from state {application.state}: {e}',
            ) from e
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


def upgrade_workflow_version(
    application: Application,
    actor: Optional[User] = None,
    target_process: Optional[RecruitmentProcess] = None,
) -> Application:
    return ApplicationService.upgrade_workflow_version(application, actor, target_process)
