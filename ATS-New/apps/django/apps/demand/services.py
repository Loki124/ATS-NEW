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
        """审批通过 (PENDING → APPROVED)

        P0-3 修复:
        1. select_for_update 已锁住 demand 行,防止并发审批覆盖
        2. approvals 子查询用 select_for_update(of=('self',)) 也锁住,
           避免 count() 与 find PENDING 之间被新插入的 approval 干扰
        3. 改用 max('level') 替代 count(),语义更明确
        """
        demand = Demand.objects.select_for_update().get(id=demand_id, deleted_at__isnull=True)

        # 锁住所有 PENDING 审批行,防止"取 max level → 处理"之间被插入新 approval
        pending_approvals = list(
            demand.approvals.select_for_update().filter(result='PENDING').order_by('-level')
        )
        if not pending_approvals:
            raise NotFound('无待审批项')
        approval = pending_approvals[0]  # 最高 level 的 PENDING 项

        approval.result = 'APPROVED'
        approval.approver_id = approver_id
        approval.comment = comment
        approval.save()
        demand.approve()
        demand.save()
        return demand

    @staticmethod
    @transaction.atomic
    def reject(demand_id: str, approver_id: str, reason: str, actor: User = None) -> Demand:
        """审批驳回 (PENDING → REJECTED)

        P0-3 修复: 同 approve(),锁住 PENDING 审批行
        """
        demand = Demand.objects.select_for_update().get(id=demand_id, deleted_at__isnull=True)
        pending_approvals = list(
            demand.approvals.select_for_update().filter(result='PENDING').order_by('-level')
        )
        if pending_approvals:
            approval = pending_approvals[0]
            approval.result = 'REJECTED'
            approval.approver_id = approver_id
            approval.comment = reason
            approval.save()
        demand.reject()
        demand.save()
        return demand

    @staticmethod
    @transaction.atomic
    def start_recruiting(demand_id: str, actor: User) -> Demand:
        """开始招聘 (APPROVED → RECRUITING)

        P0-3 修复: 加 select_for_update() 防止两个管理员同时操作同一需求
        (一个可能在调用 approve(),另一个在 start_recruiting())
        """
        demand = Demand.objects.select_for_update().get(id=demand_id, deleted_at__isnull=True)
        demand.start_recruiting()
        demand.save()
        return demand

    @staticmethod
    @transaction.atomic
    def cancel(demand_id: str, reason: str, actor: User) -> Demand:
        """取消需求 (任意 → CANCELLED)

        P0-3 修复: 之前没有 @transaction.atomic 也没有 select_for_update,
        存在两个问题:
        1. cancel 过程中如果 DB 异常,状态可能半变更
        2. 多个操作者同时取消,可能产生脏状态
        """
        demand = Demand.objects.select_for_update().get(id=demand_id, deleted_at__isnull=True)
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
