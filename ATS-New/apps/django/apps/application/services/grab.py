"""Invitation & Grab Mode Services (PRD v4 §6.4, §11.4, §14.5)

抢单模式（GRAB）：
- 候选人进入抢单型阶段后，进入"抢单池"
- 所有有权限的 HR 可"认领"
- 30 分钟（可配）内未认领 → 重分配
- SEQUENTIAL 模式下按 processor_order 推进
- ROUND_ROBIN 模式下按"上次分配时间升序"轮询

邀请（Invitation）：
- 模板邀请：链接生成、二维码
- 邮件/短信/企微通道
- 邀请状态：PENDING/SENT/OPENED/ACCEPTED/REJECTED/EXPIRED
"""
from __future__ import annotations

import logging
import secrets
import string
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import NotFound, StateTransitionError
from apps.core.models import User
from apps.position.models import Position

from ..models import Application, ApplicationStageRecord

logger = logging.getLogger(__name__)


# ============================================================
# 数据类
# ============================================================
@dataclass
class GrabResult:
    """抢单结果"""
    application: Application
    record: ApplicationStageRecord
    grabbed_by: User
    next_assignee: Optional[User] = None
    reassigned: bool = False


@dataclass
class InvitationCreateData:
    """创建邀请入参"""
    application_id: str
    channel: str = 'EMAIL'  # EMAIL/SMS/WECOM
    template_code: Optional[str] = None
    sender_id: Optional[str] = None
    custom_message: Optional[str] = None
    expires_hours: int = 72


@dataclass
class InvitationResult:
    invitation_id: str
    code: str
    url: str
    expires_at: str


# ============================================================
# 抢单服务
# ============================================================
class GrabService:
    """抢单服务"""

    @staticmethod
    def get_pool(stage_id: Optional[str] = None,
                 position_id: Optional[str] = None,
                 limit: int = 50) -> List[Application]:
        """获取抢单池（候选人已到抢单阶段但未被认领的申请）"""
        from apps.process.models import ProcessStageLink
        qs = Application.objects.filter(
            state=Application.ApplicationState.ACTIVE,
            is_grabbed=False,
            deleted_at__isnull=True,
        ).select_related('current_link', 'current_stage', 'candidate', 'position')
        if stage_id:
            qs = qs.filter(current_stage_id=stage_id)
        if position_id:
            qs = qs.filter(position_id=position_id)
        return list(qs.order_by('stage_entered_at')[:limit])

    @staticmethod
    @transaction.atomic
    def grab(application: Application, user: User) -> GrabResult:
        """认领申请（抢单）"""
        if application.is_grabbed:
            if application.grabbed_by_id == user.id:
                # 同一用户重复抢：返回成功
                sr = application.stage_records.filter(
                    link=application.current_link, deleted_at__isnull=True,
                ).order_by('-entered_at').first()
                return GrabResult(application=application, record=sr, grabbed_by=user)
            raise StateTransitionError(
                f'Application already grabbed by {application.grabbed_by_id}',
            )
        if application.state != Application.ApplicationState.ACTIVE:
            raise StateTransitionError(
                f'Cannot grab application in state {application.state}',
            )

        # 更新认领人
        application.is_grabbed = True
        application.grabbed_by = user
        application.grabbed_at = timezone.now()
        application.save()

        # 更新当前 record
        sr = application.stage_records.filter(
            link=application.current_link, deleted_at__isnull=True,
        ).order_by('-entered_at').first()
        if sr:
            handlers = sr.current_handlers or []
            if user.id not in handlers:
                handlers.append(user.id)
            sr.current_handlers = handlers
            sr.state = ApplicationStageRecord.StageState.PROCESSING
            sr.save()

        from .models import ApplicationHistory
        ApplicationHistory.objects.create(
            application=application,
            action=ApplicationHistory.ActionType.GRABBED,
            detail={'grabbed_by': user.id, 'grabbed_at': application.grabbed_at.isoformat()},
            operator=user,
        )

        logger.info('Application %s grabbed by %s', application.code, user.username)
        return GrabResult(application=application, record=sr, grabbed_by=user)

    @staticmethod
    @transaction.atomic
    def release(application: Application, user: User, reason: str = '') -> Application:
        """释放抢单（HR 主动放弃）"""
        if not application.is_grabbed:
            return application
        if application.grabbed_by_id and application.grabbed_by_id != user.id:
            # 仅超级管理员可强制释放
            if not user.is_superuser:
                raise StateTransitionError(
                    'Only the grabber or superuser can release the grab',
                )
        application.is_grabbed = False
        application.grabbed_by = None
        application.grabbed_at = None
        application.save()

        from .models import ApplicationHistory
        ApplicationHistory.objects.create(
            application=application,
            action=ApplicationHistory.ActionType.ADVANCED,
            detail={'event': 'release_grab', 'reason': reason, 'released_by': user.id},
            operator=user,
        )
        return application

    @staticmethod
    @transaction.atomic
    def reassign_overdue(threshold_minutes: int = 30,
                        limit: int = 100) -> List[GrabResult]:
        """重分配超时未认领的申请"""
        from .models import ApplicationHistory
        cutoff = timezone.now() - timedelta(minutes=threshold_minutes)
        overdue = Application.objects.filter(
            state=Application.ApplicationState.ACTIVE,
            is_grabbed=False,
            stage_entered_at__lte=cutoff,
            deleted_at__isnull=True,
        ).order_by('stage_entered_at')[:limit]

        results: List[GrabResult] = []
        for app in overdue:
            try:
                # 找下一可用 HR（按"上次分配时间升序"轮询）
                next_user = GrabService._pick_next_assignee(app)
                if not next_user:
                    logger.warning('No assignee available for %s', app.code)
                    continue
                result = GrabService.grab(app, next_user)
                result.reassigned = True
                results.append(result)
            except Exception as e:
                logger.warning('Failed to reassign %s: %s', app.code, e)
        return results

    @staticmethod
    def _pick_next_assignee(application: Application) -> Optional[User]:
        """ROUND_ROBIN: 选上次分配最早的活跃 HR"""
        from apps.process.models import StageRule
        link = application.current_link
        if not link:
            return None
        try:
            stage_rule = link.stage_rule
        except StageRule.DoesNotExist:
            stage_rule = None
        if not stage_rule or not stage_rule.processor_order:
            # 默认：所有 HR 角色
            from apps.core.models import Role
            hr_role = Role.objects.filter(code='HR').first()
            if not hr_role:
                return None
            user_ids = list(hr_role.user_roles.filter(
                user__is_active=True, deleted_at__isnull=True,
            ).values_list('user_id', flat=True))
        else:
            user_ids = stage_rule.processor_order

        # 排除离职人员
        active_users = User.objects.filter(id__in=user_ids, is_active=True)
        # 按"上次分配时间"升序（最久未分配的优先）
        users = list(active_users.order_by('last_assignment_at'))
        return users[0] if users else None

    @staticmethod
    def get_grab_pool_summary() -> Dict[str, Any]:
        """抢单池汇总统计"""
        from django.db.models import Count
        pool = Application.objects.filter(
            state=Application.ApplicationState.ACTIVE,
            is_grabbed=False,
            deleted_at__isnull=True,
        )
        by_stage = list(pool.values('current_stage__name').annotate(
            count=Count('id'),
        ).order_by('-count'))
        total = pool.count()
        oldest = pool.order_by('stage_entered_at').first()
        return {
            'total': total,
            'by_stage': by_stage,
            'oldest_entered_at': oldest.stage_entered_at.isoformat() if oldest and oldest.stage_entered_at else None,
        }


# ============================================================
# 邀请服务
# ============================================================
class InvitationService:
    """邀请服务"""

    @staticmethod
    @transaction.atomic
    def create_invitation(data: InvitationCreateData) -> InvitationResult:
        """创建邀请（生成唯一码）"""
        from apps.invitation.models import Invitation, InvitationChannel, InvitationStatus

        try:
            application = Application.objects.get(id=data.application_id, deleted_at__isnull=True)
        except Application.DoesNotExist as e:
            raise NotFound(f'Application {data.application_id} not found') from e

        # 生成 8 位 code
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        expires_at = timezone.now() + timedelta(hours=data.expires_hours)

        invitation = Invitation.objects.create(
            application=application,
            candidate=application.candidate,
            channel=data.channel,
            status=InvitationStatus.PENDING,
            code=code,
            template_code=data.template_code or '',
            custom_message=data.custom_message or '',
            sender_id=data.sender_id,
            expires_at=expires_at,
        )

        return InvitationResult(
            invitation_id=invitation.id,
            code=code,
            url=f'/invitation/{code}',
            expires_at=expires_at.isoformat(),
        )

    @staticmethod
    @transaction.atomic
    def send_invitation(invitation_id: str) -> Dict[str, Any]:
        """发送邀请（按 channel 路由）"""
        from apps.invitation.models import Invitation, InvitationStatus
        try:
            inv = Invitation.objects.get(id=invitation_id, deleted_at__isnull=True)
        except Invitation.DoesNotExist as e:
            raise NotFound(f'Invitation {invitation_id} not found') from e

        if inv.status not in (InvitationStatus.PENDING,):
            raise StateTransitionError(
                f'Cannot send invitation in status {inv.status}',
            )

        # 实际发送由 Notification 模块处理
        from apps.notification.services import send_notification
        candidate = inv.candidate
        message = inv.custom_message or f'【ATS系统】邀请您面试，链接：/invitation/{inv.code}'
        send_notification(
            recipient_id=candidate.id,  # 候选人作为接收人
            title='面试邀请',
            content=message,
            link=f'/invitation/{inv.code}',
            source='INVITATION',
            source_id=inv.id,
            channel=inv.channel,
        )

        inv.status = InvitationStatus.SENT
        inv.sent_at = timezone.now()
        inv.save()
        return {'invitation_id': inv.id, 'status': inv.status, 'sent_at': inv.sent_at.isoformat()}

    @staticmethod
    def get_invitation_by_code(code: str) -> Dict[str, Any]:
        """按 code 查询邀请（候选人点击链接时调用）"""
        from apps.invitation.models import Invitation, InvitationStatus
        try:
            inv = Invitation.objects.get(code=code, deleted_at__isnull=True)
        except Invitation.DoesNotExist as e:
            raise NotFound(f'Invitation code {code} not found') from e

        if inv.status == InvitationStatus.PENDING:
            inv.status = InvitationStatus.OPENED
            inv.opened_at = timezone.now()
            inv.save()
        elif inv.status == InvitationStatus.SENT:
            inv.status = InvitationStatus.OPENED
            inv.opened_at = timezone.now()
            inv.save()

        return {
            'invitation_id': inv.id,
            'status': inv.status,
            'application_code': inv.application.code,
            'candidate_name': inv.candidate.name,
            'position_title': inv.application.position.title,
            'expires_at': inv.expires_at.isoformat(),
        }

    @staticmethod
    @transaction.atomic
    def respond_invitation(code: str, accept: bool, note: str = '') -> Dict[str, Any]:
        """候选人响应邀请"""
        from apps.invitation.models import Invitation, InvitationStatus
        try:
            inv = Invitation.objects.get(code=code, deleted_at__isnull=True)
        except Invitation.DoesNotExist as e:
            raise NotFound(f'Invitation code {code} not found') from e

        if inv.status in (InvitationStatus.EXPIRED,):
            raise StateTransitionError(f'Invitation is {inv.status}')

        if inv.expires_at and inv.expires_at < timezone.now():
            inv.status = InvitationStatus.EXPIRED
            inv.save()
            raise StateTransitionError('Invitation expired')

        inv.status = InvitationStatus.ACCEPTED if accept else InvitationStatus.REJECTED
        inv.responded_at = timezone.now()
        inv.response_note = note
        inv.save()
        return {
            'invitation_id': inv.id,
            'status': inv.status,
            'application_id': inv.application_id,
        }
