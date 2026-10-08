"""Demand Services (PRD v4 §14.1) - 需求业务逻辑

需求状态机：
DRAFT → PENDING → APPROVED → RECRUITING → COMPLETED
                ↘ REJECTED ↗
                ↘ PAUSED ↗
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import NotFound, PermissionDenied, StateTransitionError
from apps.core.models import User
from apps.core.role_v2_query import is_super_admin
from apps.process.models import RecruitmentProcess

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
    demand_type: str = 'SOCIAL'
    recruit_type: str = 'social'
    actor: User | None = None


class DemandService:
    """需求业务服务"""

    @staticmethod
    @transaction.atomic
    def create_demand(data: DemandCreateData) -> Demand:
        """创建需求 (DRAFT 状态)"""
        from apps.core.models import Department
        from apps.process.models import RecruitmentProcess

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
            demand_type=data.demand_type,
            recruit_type=data.recruit_type,
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
        if demand.requested_by_id != actor.id and not is_super_admin(actor):
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
    @transaction.atomic
    def upgrade_demand_process(
        demand: Demand,
        actor: User | None = None,
        target_process: RecruitmentProcess | None = None,
    ) -> tuple[Demand, List[str]]:
        """需求升级到最新流程版本（决策 3 / §4.2）。

        只改指 Demand 本体 + 其 **live** Positions（``Position.demand == demand`` 且
        ``deleted_at IS NULL``），**不改指 Application**——BR-102「已在跑的候选人走创建
        时的版本」是硬红线（§4.3），级联改指 Application 属违规。

        Args:
            demand: 待升级的需求实例。
            actor: 操作人，仅用于审计日志。
            target_process: 可选的显式目标版本；不传则自动取同 ``code`` 下
                ``is_latest=True`` 且 ``status='ENABLED'`` 的 live 版本。

        Returns:
            ``(demand, moved_position_ids)``。已在最新版时幂等返回 ``(demand, [])``。

        Raises:
            StateTransitionError: 需求未关联流程 / 该流程线无可用最新版 /
                显式目标版本跨流程线、已归档、已软删或不是最新版。
        """
        if demand.process_id is None:
            # 无此守卫，下一行 demand.process.code 会 AttributeError（500 而非 409）
            raise StateTransitionError('该需求未关联流程，无法升级')

        if target_process is None:
            target_process = (
                RecruitmentProcess.objects
                .filter(
                    code=demand.process.code,
                    status='ENABLED',
                    is_latest=True,
                    deleted_at__isnull=True,
                )
                .first()
            )
        else:
            # 显式指定目标时同样要过校验，否则等于给了绕过归档限制的后门
            if target_process.code != demand.process.code:
                raise StateTransitionError('目标流程与当前流程不属于同一流程线')
            if target_process.status != 'ENABLED' or target_process.deleted_at is not None:
                raise StateTransitionError('目标流程版本不可用（已归档或已删除）')
            if not target_process.is_latest:
                raise StateTransitionError('目标流程版本不是最新版')

        if target_process is None:
            # 不能静默 return：「流程线整条被归档」与「已是最新版」是两种完全不同的
            # 情况，混成同一个返回值即 fail-silent。
            raise StateTransitionError('该流程线下没有可用的最新版本')

        if target_process.id == demand.process_id:
            return demand, []  # 幂等：已在最新版，不产生任何写入

        old_pid = demand.process_id  # §1.3.2：审计快照必须早于赋值
        demand.process = target_process
        demand.process_version = target_process.current_version
        demand.save(update_fields=['process', 'process_version', 'updated_at'])

        moved: List[str] = []
        # 必须显式过滤软删：本方法 docstring 承诺只改指 **live** Positions，而
        # SoftDeleteModel（apps/common/models.py）并未重写默认 manager，
        # `.all()` 会把已软删职位一并捞出来改指，与承诺不符。
        # 该行为由 demand/tests/test_upgrade_demand_process.py::
        # test_upgrade_skips_soft_deleted_positions 钉住。
        for pos in demand.positions.filter(deleted_at__isnull=True):
            if pos.process_id != target_process.id:
                pos.process = target_process
                pos.process_version = target_process.current_version
                pos.save(update_fields=['process', 'process_version', 'updated_at'])
                moved.append(pos.id)

        logger.info(
            'Demand %s upgraded process %s → %s (version=%s) by %s; moved positions=%s',
            demand.code, old_pid, target_process.id,
            target_process.current_version,
            getattr(actor, 'username', None), moved,
        )
        return demand, moved

    @staticmethod
    def update_filled_count(demand_id: str) -> Demand:
        """从职位同步 filled_count"""
        demand = Demand.objects.get(id=demand_id)
        demand.filled_count = sum(
            p.filled_count for p in demand.positions.filter(deleted_at__isnull=True)
        )
        demand.save(update_fields=['filled_count', 'updated_at'])
        return demand
