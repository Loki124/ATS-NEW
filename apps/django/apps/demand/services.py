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

from django.db import IntegrityError, transaction

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
    # 2026-10-12 字段结构对齐规范: 新增预置列
    talent_level: str = ''
    talent_nature: str = ''
    date_range: list | None = None
    sharers: list | None = None
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

        # 生成编号 HC + 6 位流水号（取现存 HC 编号最大流水 +1；并发撞 unique 时重试）
        demand = None
        for _attempt in range(5):
            code = DemandService._next_demand_code()
            try:
                with transaction.atomic():
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
                        # 2026-10-12 字段结构对齐规范: 新增预置列 (JSONField 空值归一为 [])
                        talent_level=data.talent_level,
                        talent_nature=data.talent_nature,
                        date_range=data.date_range or [],
                        sharers=data.sharers or [],
                        recruit_type=data.recruit_type,
                        state=DemandState.DRAFT,
                        created_by=data.actor,
                        updated_by=data.actor,
                    )
                break
            except IntegrityError as e:
                # 只重试编号撞 unique（MySQL 1062 / SQLite UNIQUE）；FK 等其他完整性错误原样抛出
                if '1062' not in str(e) and 'UNIQUE' not in str(e):
                    raise
                demand = None
                logger.warning('Demand code %s collided, retrying (%d/5)', code, _attempt + 1)
        if demand is None:
            raise IntegrityError('需求编号生成失败：并发冲突重试耗尽')
        logger.info('Demand created: %s', demand.code)
        return demand

    @staticmethod
    def _next_demand_code() -> str:
        """需求编号：HC + 6 位流水号（按现存 HC 前缀编号的最大流水 +1，不足补零）。"""
        import re

        seq = 0
        for c in Demand.objects.filter(code__startswith='HC').values_list('code', flat=True):
            m = re.fullmatch(r'HC(\d{6})', c or '')
            if m:
                seq = max(seq, int(m.group(1)))
        return f'HC{seq + 1:06d}'

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
    @transaction.atomic
    def rebind_demand_process(
        demand: Demand,
        target_process: RecruitmentProcess,
        actor: User | None = None,
    ) -> tuple[Demand, List[str]]:
        """把需求**改绑**到另一条流程线（与 upgrade_demand_process 的关键区别：跨 code）。

        2026-10-16 新增。此前全仓不存在任何「解绑/改绑」能力（grep unlink/dissociate/
        detach/解除/解绑 零命中），而 ``Demand.process`` 是 NOT NULL + PROTECT FK，
        导致一条需求只要挂过流程就永远删不掉那条流程，用户在流程配置页被
        「被 N 个需求引用，不可删除」彻底堵死（dev 库实测：VERIFY_PROC 引用数恒为 1）。

        与 ``upgrade_demand_process`` 的边界（务必分清，勿混用）：
          - upgrade：同一条 ``code`` 流程线内，从历史版本升到 is_latest，语义是「版本前进」
          - rebind：**跨 code 换一条流程线**，语义是「换流程」，会换掉整套阶段编排
            ——所以这里必须额外拦截「有在跑候选人」的场景（见下）。

        改绑只改指 Demand + 其 **live** Positions，**绝不动 Application**：
        BR-102「已在跑的候选人走创建时的版本」是硬红线，级联改指 Application 属违规。

        Raises:
            StateTransitionError: 目标流程不可用（非 ENABLED / 已软删 / 非最新版本）、
                目标与当前是同一条流程线的同一行（应走 upgrade 而非 rebind）、
                或该需求名下存在非终态的在跑候选人申请。
        """
        if demand.deleted_at is not None:
            raise StateTransitionError('该需求已删除，无法改绑流程')

        if target_process.deleted_at is not None:
            raise StateTransitionError('目标流程已删除，无法绑定')
        if target_process.status != 'ENABLED':
            raise StateTransitionError('目标流程已归档，无法绑定')
        if not target_process.is_latest:
            raise StateTransitionError(
                '目标流程不是最新版版本，无法绑定（请选择该流程的最新版本）',
            )

        # 同 code 同一行 = 幂等，直接返回而不是白跑一遍写入。
        # 注意：同 code **不同**行（历史版本）不是幂等，那属于 upgrade 的活。
        if target_process.id == demand.process_id:
            return demand, []

        # 跨 code 改绑会换掉整套阶段编排，在跑候选人正卡在新流程**不存在**的阶段上。
        # BR-102 要求他们留在原版本继续跑完，所以这里不碰他的 Application，
        # 但也绝不能把整条需求改绑走 —— 否则他的 current_stage 会变成孤儿。
        #
        # Application **不直接挂 demand**，只有 position → demand 这一条路，
        # 故必须经该需求名下 live 职位反查；软删职位上的申请同样要算进来
        # （职位被软删不代表申请也终止了，仍可能是 ACTIVE）。
        from apps.application.models import Application
        blocking_states = ('PENDING', 'ACTIVE', 'PAUSED', 'OFFER_SENT')
        blocking = Application._base_manager.filter(
            position__demand=demand,
            state__in=blocking_states,
        )
        if blocking.exists():
            raise StateTransitionError(
                f'该需求下还有 {blocking.count()} 个在跑的候选人申请，'
                '换流程会导致他们的阶段错乱，请先处理完这些候选人再改绑',
            )

        old_pid = demand.process_id  # 审计快照必须早于赋值
        demand.process = target_process
        demand.process_version = target_process.current_version
        demand.save(update_fields=['process', 'process_version', 'updated_at'])

        moved: List[str] = []
        # 显式过滤软删：与 upgrade_demand_process 同理，.all() 会捞出软删职位一并改指。
        for pos in demand.positions.filter(deleted_at__isnull=True):
            if pos.process_id != target_process.id:
                pos.process = target_process
                pos.process_version = target_process.current_version
                pos.save(update_fields=['process', 'process_version', 'updated_at'])
                moved.append(pos.id)

        logger.info(
            'Demand %s REBOUND process %s → %s (code %s → %s, version=%s) by %s; '
            'moved positions=%s; running applications left untouched',
            demand.code, old_pid, target_process.id,
            demand.process.code, target_process.code, target_process.current_version,
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
