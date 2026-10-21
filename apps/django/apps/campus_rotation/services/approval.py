"""轮岗变更审批服务（需求 5-5 / S5-17）。

职责边界：
- 兼岗记录创建**免审**（本模块不介入）。
- 更换带教导师 `mentor` / 直接上级 `direct_manager` **需审批**：申请阶段只写
  `RotationApproval` 申请单，**不动** `RotationArrangement.mentor/direct_manager`。
- 审批通过（`approve`）后，才由本模块在同一事务内把新值落到
  `RotationArrangement`，并写 **两条** AuditLog（审批动作 + 字段变更）。
- 审批驳回（`reject`）只记录状态与驳回原因，**不落字段**。

🔴 事务纪律：落字段与写审计日志必须在同一 `transaction.atomic` 内 ——
否则会出现「字段已改但审计缺失」或「审计已写但字段回滚」的不可审计状态。
"""
import logging

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# 变更类型 → RotationArrangement 上的目标字段
CHANGE_TYPE_FIELD = {
    'MENTOR_CHANGE': 'mentor',
    'MANAGER_CHANGE': 'direct_manager',
}


class ApprovalError(Exception):
    """审批动作非法（状态不对 / 目标字段缺失 / 目标人员不存在）。"""


def create_approval_request(*, arrangement, change_type: str, new_user_id, reason: str = ''):
    """创建变更申请单（不落业务字段）。

    Args:
        arrangement: RotationArrangement 实例。
        change_type: 'MENTOR_CHANGE' | 'MANAGER_CHANGE'。
        new_user_id: 目标人员 user id（int 或 str）。
        reason: 变更原因（建议必填，便于审批人判断）。

    Returns:
        RotationApproval 实例（status='PENDING'）。

    🔴 旧值从 arrangement 当前值快照读取（不在事务外预读，避免读到过期值）。
    """
    field_name = CHANGE_TYPE_FIELD.get(change_type)
    if not field_name:
        raise ApprovalError(f'不支持的变更类型：{change_type}')

    if arrangement is None:
        raise ApprovalError('轮岗安排不存在')

    current_user_id = getattr(arrangement, f'{field_name}_id', None)
    new_id = str(new_user_id) if new_user_id is not None else ''

    if str(current_user_id or '') == new_id and new_id:
        raise ApprovalError('新值与当前值相同，无需提交变更申请')

    return arrangement.approvals.create(
        change_type=change_type,
        old_value=str(current_user_id or ''),
        new_value=new_id,
        reason=reason or '',
        status='PENDING',
    )


@transaction.atomic
def approve(approval, *, approver=None) -> None:
    """审批通过：落业务字段 + 写两条 AuditLog。

    Args:
        approval: RotationApproval 实例（status 应为 'PENDING'）。
        approver: 审批人 User 实例。

    Raises:
        ApprovalError: 状态非 PENDING / 安排已被删除 / 目标人员不存在。
    """
    from apps.audit.services import AuditService

    if approval.status != 'PENDING':
        raise ApprovalError(f'当前审批状态为 {approval.status}，不可审批')

    field_name = CHANGE_TYPE_FIELD.get(approval.change_type)
    if not field_name:
        raise ApprovalError(f'不支持的变更类型：{approval.change_type}')

    arrangement = approval.arrangement
    if arrangement is None:
        raise ApprovalError('关联的轮岗安排已不存在，无法落字段')

    new_value = (approval.new_value or '').strip()
    if not new_value:
        raise ApprovalError('申请单未填写新值，无法落字段')

    # 目标人员必须存在（避免落一个指向已删用户的 FK）
    from apps.core.models import User
    try:
        target = User.objects.get(id=int(new_value))
    except (User.DoesNotExist, ValueError, TypeError):
        raise ApprovalError(f'目标人员不存在：{new_value}')

    old_user_id = getattr(arrangement, f'{field_name}_id', None)

    # ① 落业务字段
    setattr(arrangement, field_name, target)
    arrangement.save(update_fields=[field_name, 'updated_at'])

    # ② 落审批单状态
    approval.status = 'APPROVED'
    approval.approver = approver
    approval.approved_at = timezone.now()
    approval.save(update_fields=['status', 'approver', 'approved_at', 'updated_at'])

    # ③ 同事务写两条 AuditLog
    #   3-1 审批动作本身
    AuditService.record(
        user=approver,
        action='approve',
        entity='RotationApproval',
        entity_id=str(approval.pk),
        field=approval.change_type,
        old_value=approval.old_value,
        new_value=approval.new_value,
    )
    #   3-2 业务字段实际变更
    AuditService.record(
        user=approver,
        action='update',
        entity='RotationArrangement',
        entity_id=str(arrangement.pk),
        field=field_name,
        old_value=str(old_user_id or ''),
        new_value=str(target.pk),
    )
    logger.info(
        '轮岗变更审批通过 approval=%s arrangement=%s field=%s %s→%s',
        approval.pk, arrangement.pk, field_name, old_user_id, target.pk,
    )


@transaction.atomic
def reject(approval, *, approver=None, reason: str = '') -> None:
    """审批驳回：仅记录状态与原因，**不落业务字段**。"""
    from apps.audit.services import AuditService

    if approval.status != 'PENDING':
        raise ApprovalError(f'当前审批状态为 {approval.status}，不可驳回')

    approval.status = 'REJECTED'
    approval.approver = approver
    approval.approved_at = timezone.now()
    approval.reject_reason = reason or ''
    approval.save(update_fields=[
        'status', 'approver', 'approved_at', 'reject_reason', 'updated_at',
    ])

    AuditService.record(
        user=approver,
        action='reject',
        entity='RotationApproval',
        entity_id=str(approval.pk),
        field=approval.change_type,
        old_value=approval.old_value,
        new_value=approval.new_value,
    )
    logger.info('轮岗变更审批驳回 approval=%s reason=%s', approval.pk, reason)
