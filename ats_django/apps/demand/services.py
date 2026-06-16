"""Demand Services (PRD v4 §14.1) - 需求业务逻辑

需求状态机：
DRAFT → PENDING → APPROVED → RECRUITING → COMPLETED
                ↘ REJECTED ↗
                ↘ PAUSED ↗
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import NotFound, PermissionDenied, StateTransitionError
from apps.core.models import User

from .models import Demand, DemandApproval, DemandState

logger = logging.getLogger(__name__)


@dataclass
class DemandCreateData:
    """创建需求入参"""
    title: str
    department_id: str
    requested_by_id: str
    hr_id: str
    headcount: int
    process_id: str
    level: str = ''
    position_title: str = ''
    jd: str = ''
    requirements: str = ''
    priority: str = 'P1'
    actor: Optional[User] = None


class DemandService:
    """需求业务服务"""

    @staticmethod
    @transaction.atomic
    def create_demand(data: DemandCreateData) -> Demand:
        """创建需求 (DRAFT 状态)"""
        from apps.process.models import RecruitmentProcess
        from apps.core.models import Department

        try:
            process = RecruitmentProcess.objects.get(id=data.process_id, deleted_at__isnull=True)
        except RecruitmentProcess.DoesNotExist as e:
            raise NotFound(f'流程 {data.process_id} 不存在') from e

        try:
            department = Department.objects.get(id=data.department_id)
        except Department.DoesNotExist as e:
            raise NotFound(f'部门 {data.department_id} 不存在') from e

        # 生成编号 D + yyyymmdd + 4位
        from nanoid import generate as nanoid_generate
        code = f'D{timezone.now().strftime("%Y%m%d")}{nanoid_generate(size=4).upper()}'

        demand = Demand.objects.create(
            code=code,
            title=data.title,
            department=department,
            requested_by_id=data.requested_by_id,
            hr_id=data.hr_id,
            headcount=data.headcount,
            filled_count=0,
            level=data.level,
            position_title=data.position_title,
            process=process,
            process_version=process.current_version,
            jd=data.jd,
            requirements=data.requirements,
            priority=data.priority,
            state=DemandState.DRAFT,
            created_by=data.actor,
            updated_by=data.actor,
        )
        logger.info('Demand created: %s', demand.code)
        return demand

    @staticmethod
    @transaction.atomic
    def submit_for_approval(demand_id: str, actor: User) -> Demand:
        """提交审批 (DRAFT → PENDING)"""
        demand = Demand.objects.filter(id=demand_id, deleted_at__isnull=True).first()
        if not demand:
            raise NotFound(f'需求 {demand_id} 不存在')
        if demand.requested_by_id != actor.id and not actor.is_superuser:
            raise PermissionDenied('仅需求提出人可提交审批')
        demand.submit()
        demand.save()
        # 创建默认审批步骤
        DemandApproval.objects.create(
            demand=demand, approver=demand.hr, level=1, result='PENDING',
        )
        return demand

    @staticmethod
    @transaction.atomic
    def approve(demand_id: str, approver_id: str, comment: str = '', actor: User = None) -> Demand:
        """审批通过 (PENDING → APPROVED)"""
        demand = Demand.objects.select_for_update().get(id=demand_id, deleted_at__isnull=True)
        approval = demand.approvals.filter(level=demand.approvals.count(), result='PENDING').first()
        if not approval:
            raise NotFound('无待审批项')
        approval.result = 'APPROVED'
        approval.comment = comment
        approval.save()
        demand.approve()
        demand.save()
        return demand

    @staticmethod
    @transaction.atomic
    def reject(demand_id: str, approver_id: str, reason: str, actor: User = None) -> Demand:
        """审批驳回 (PENDING → REJECTED)"""
        demand = Demand.objects.select_for_update().get(id=demand_id, deleted_at__isnull=True)
        approval = demand.approvals.filter(result='PENDING').order_by('-level').first()
        if approval:
            approval.result = 'REJECTED'
            approval.comment = reason
            approval.save()
        demand.reject()
        demand.save()
        return demand

    @staticmethod
    @transaction.atomic
    def start_recruiting(demand_id: str, actor: User) -> Demand:
        """开始招聘 (APPROVED → RECRUITING)"""
        demand = Demand.objects.get(id=demand_id, deleted_at__isnull=True)
        demand.start_recruiting()
        demand.save()
        return demand

    @staticmethod
    def cancel(demand_id: str, reason: str, actor: User) -> Demand:
        """取消需求 (任意 → CANCELLED)"""
        demand = Demand.objects.get(id=demand_id, deleted_at__isnull=True)
        demand.cancel()
        demand.save()
        return demand

    @staticmethod
    def update_filled_count(demand_id: str) -> Demand:
        """从职位同步 filled_count"""
        from apps.position.models import Position
        demand = Demand.objects.get(id=demand_id)
        demand.filled_count = sum(
            p.filled_count for p in demand.positions.filter(deleted_at__isnull=True)
        )
        demand.save(update_fields=['filled_count', 'updated_at'])
        return demand
