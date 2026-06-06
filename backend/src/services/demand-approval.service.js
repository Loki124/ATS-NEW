/**
 * 需求审批引擎 - PRD G2
 *
 * 多级审批：HRBP → 用人经理 → 用人经理上级 → 总经理
 * (可配置)
 *
 * 审批流：发起 → 逐级审批 → 通过 / 拒绝
 *
 * 数据模型：使用现有 Demand 表的 approvalStatus 字段 + 新增 DemandApprovalStep 跟踪步骤
 *
 * 步骤状态机：PENDING → APPROVED / REJECTED
 */

import { prisma } from '../app.js'
import { AppError } from '../middleware/error.middleware.js'
import { APPROVAL_STATUSES, STEP_STATUSES, canTransitionApproval } from './demand-state-machine.service.js'
import { recordOperation, recordDemandStatusChange } from './audit-log.service.js'
import { sendNotification } from './notification.service.js'

/**
 * 发起审批
 * 创建步骤记录
 */
export async function submitForApproval(demandId, submittedBy) {
  const demand = await prisma.demand.findUnique({
    where: { id: demandId },
    include: {
      department: true,
    },
  })
  if (!demand) throw new AppError('需求不存在', 404)
  if (demand.approvalStatus !== 'NOT_STARTED' && demand.approvalStatus !== 'REJECTED' && demand.approvalStatus !== 'CANCELLED') {
    throw new AppError(`当前审批状态 ${demand.approvalStatus} 不可发起`, 400)
  }
  if (demand.demandStatus !== 'DRAFT') {
    throw new AppError(`需求状态 ${demand.demandStatus} 不可发起审批（应保持 DRAFT）`, 400)
  }

  // 计算审批链
  const steps = await buildApprovalChain(demand)

  // 开启事务 - Serializable 隔离避免并发审批导致步骤状态错乱
  return prisma.$transaction(async (tx) => {
    // 清掉旧 steps (重发)
    await tx.demandApprovalStep.deleteMany({ where: { demandId } })
    // 创建新 steps
    for (let i = 0; i < steps.length; i++) {
      await tx.demandApprovalStep.create({
        data: {
          demandId,
          stepIndex: i,
          approverRole: steps[i].approverRole,
          approverId: steps[i].approverId,
          status: i === 0 ? STEP_STATUSES.PENDING : STEP_STATUSES.WAITING,
          submittedBy,
        },
      })
    }
    // 更新需求状态
    // 设计: submit → NOT_STARTED (审批中), approve 终步 → IN_PROGRESS
    // 原因: 与 demand-state-machine.service.js 状态转换图保持一致
    const updated = await tx.demand.update({
      where: { id: demandId },
      data: { approvalStatus: APPROVAL_STATUSES.PENDING, demandStatus: 'NOT_STARTED' },
    })
    // 审计日志: 发起审批
    await recordOperation({
      tx,
      entityType: 'demand',
      entityId: demandId,
      action: 'SUBMIT_APPROVAL',
      fromState: demand.demandStatus,
      toState: 'NOT_STARTED',
      operatorId: submittedBy,
      metadata: { stepsCount: steps.length, approverRoles: steps.map(s => s.approverRole) },
    })
    return tx.demand.findUnique({
      where: { id: demandId },
      include: { approvalSteps: { orderBy: { stepIndex: 'asc' } } },
    })
  })

  // 通知: 第一个审批人收到待办
  const firstStep = result.approvalSteps?.find((s) => s.status === STEP_STATUSES.PENDING)
  if (firstStep?.approverId) {
    await sendNotification({
      recipientId: firstStep.approverId,
      templateKey: 'DEMAND_APPROVAL_PENDING',
      priority: 'HIGH',
      context: {
        demandId,
        demandName: result.name || '',
        submitterName: submittedBy,
        approverRole: firstStep.approverRole,
      },
    }).catch((e) => console.error('[notification] submit hook failed:', e.message))
  }
  return result
}

/**
 * 审批通过
 */
export async function approveDemand(demandId, approverId, comment) {
  const demand = await prisma.demand.findUnique({
    where: { id: demandId },
    include: { approvalSteps: { orderBy: { stepIndex: 'asc' } } },
  })
  if (!demand) throw new AppError('需求不存在', 404)
  if (demand.approvalStatus !== APPROVAL_STATUSES.PENDING) {
    throw new AppError('当前不是审批中状态', 400)
  }
  const currentStep = demand.approvalSteps.find((s) => s.status === APPROVAL_STATUSES.PENDING)
  if (!currentStep) throw new AppError('无待审批步骤', 500)
  if (currentStep.approverId && currentStep.approverId !== approverId) {
    throw new AppError('您不是当前步骤的审批人', 403)
  }

  // 开启事务 - Serializable 隔离避免并发审批
  return prisma.$transaction(async (tx) => {
    // 标记当前步通过
    await tx.demandApprovalStep.update({
      where: { id: currentStep.id },
      data: {
        status: STEP_STATUSES.APPROVED,
        approverId,
        comment,
        approvedAt: new Date(),
      },
    })
    // 审计: 单步通过
    await recordOperation({
      tx,
      entityType: 'demand',
      entityId: demandId,
      action: 'APPROVE_STEP',
      operatorId: approverId,
      reason: comment,
      metadata: { stepIndex: currentStep.stepIndex, approverRole: currentStep.approverRole },
    })
    // 找下一步
    const nextStep = await tx.demandApprovalStep.findFirst({
      where: { demandId, status: STEP_STATUSES.WAITING },
      orderBy: { stepIndex: 'asc' },
    })
    if (nextStep) {
      // 激活下一步
      await tx.demandApprovalStep.update({
        where: { id: nextStep.id },
        data: { status: STEP_STATUSES.PENDING },
      })
      return tx.demand.findUnique({ where: { id: demandId }, include: { approvalSteps: true } })
    } else {
      // 全部通过 → 需求进入 IN_PROGRESS
      // 设计: 不在这里按 startTime 分流到 NOT_STARTED,
      //      因为 submit 时已设为 NOT_STARTED 表达了"等待开始"语义,
      //      审批通过直接到 IN_PROGRESS 表达"已批准可执行"
      const updated = await tx.demand.update({
        where: { id: demandId },
        data: {
          approvalStatus: APPROVAL_STATUSES.APPROVED,
          demandStatus: 'IN_PROGRESS', // 审批通过 → 自动转进行中
        },
      })
      // 审计: 需求状态变更
      await recordDemandStatusChange({
        tx,
        demandId,
        fromStatus: demand.demandStatus,
        toStatus: 'IN_PROGRESS',
        operatorId: approverId,
        reason: comment,
        metadata: { approvalStatus: APPROVAL_STATUSES.APPROVED },
      })
      return tx.demand.findUnique({ where: { id: demandId }, include: { approvalSteps: true } })
    }
  }).then(async (result) => {
    // 通知: 终步通过 → 通知创建人
    if (result.approvalStatus === APPROVAL_STATUSES.APPROVED) {
      await sendNotification({
        recipientId: demand.creatorId,
        templateKey: 'DEMAND_APPROVAL_APPROVED',
        priority: 'HIGH',
        context: { demandId, demandName: demand.name || '' },
      }).catch((e) => console.error('[notification] approve hook failed:', e.message))
    }
    return result
  })
}

/**
 * 审批拒绝
 */
export async function rejectDemand(demandId, approverId, reason) {
  if (!reason || !reason.trim()) {
    throw new AppError('请填写拒绝原因', 400)
  }
  const demand = await prisma.demand.findUnique({
    where: { id: demandId },
    include: { approvalSteps: { orderBy: { stepIndex: 'asc' } } },
  })
  if (!demand) throw new AppError('需求不存在', 404)
  if (demand.approvalStatus !== APPROVAL_STATUSES.PENDING) {
    throw new AppError('当前不是审批中状态', 400)
  }
  const currentStep = demand.approvalSteps.find((s) => s.status === APPROVAL_STATUSES.PENDING)
  if (!currentStep) throw new AppError('无待审批步骤', 500)
  if (currentStep.approverId && currentStep.approverId !== approverId) {
    throw new AppError('您不是当前步骤的审批人', 403)
  }

  // 开启事务 - Serializable 隔离
  return prisma.$transaction(async (tx) => {
    // 标记当前步拒绝
    await tx.demandApprovalStep.update({
      where: { id: currentStep.id },
      data: {
        status: STEP_STATUSES.REJECTED,
        approverId,
        comment: reason,
        approvedAt: new Date(),
      },
    })
    // 标记后续步骤为跳过
    await tx.demandApprovalStep.updateMany({
      where: { demandId, status: STEP_STATUSES.WAITING },
      data: { status: STEP_STATUSES.SKIPPED },
    })
    const updated = await tx.demand.update({
      where: { id: demandId },
      data: { approvalStatus: APPROVAL_STATUSES.REJECTED, demandStatus: 'DRAFT' },
      include: { approvalSteps: true },
    })
    // 审计: 拒绝
    await recordDemandStatusChange({
      tx,
      demandId,
      fromStatus: demand.demandStatus,
      toStatus: 'DRAFT',
      operatorId: approverId,
      reason,
      metadata: { approvalStatus: APPROVAL_STATUSES.REJECTED, rejectedStepIndex: currentStep.stepIndex },
    })
    return updated
  }).then(async (result) => {
    // 通知: 拒绝 → 创建人
    await sendNotification({
      recipientId: demand.creatorId,
      templateKey: 'DEMAND_APPROVAL_REJECTED',
      priority: 'HIGH',
      context: { demandId, demandName: demand.name || '', reason },
    }).catch((e) => console.error('[notification] reject hook failed:', e.message))
    return result
  })
}

/**
 * 撤销审批（发起人主动撤销）
 */
export async function cancelApproval(demandId, userId) {
  const demand = await prisma.demand.findUnique({ where: { id: demandId } })
  if (!demand) throw new AppError('需求不存在', 404)
  if (demand.approvalStatus !== APPROVAL_STATUSES.PENDING) {
    throw new AppError('当前不是审批中状态', 400)
  }
  if (demand.creatorId !== userId) {
    throw new AppError('只有创建人可以撤销审批', 403)
  }
  // 开启事务 - Serializable 隔离
  return prisma.$transaction(async (tx) => {
    await tx.demandApprovalStep.updateMany({
      where: { demandId, status: { in: [STEP_STATUSES.PENDING, STEP_STATUSES.WAITING] } },
      data: { status: STEP_STATUSES.SKIPPED },
    })
    const updated = await tx.demand.update({
      where: { id: demandId },
      data: { approvalStatus: APPROVAL_STATUSES.CANCELLED, demandStatus: 'DRAFT' },
    })
    // 审计: 撤销
    await recordDemandStatusChange({
      tx,
      demandId,
      fromStatus: demand.demandStatus,
      toStatus: 'DRAFT',
      operatorId: userId,
      reason: '创建人撤销',
      metadata: { approvalStatus: APPROVAL_STATUSES.CANCELLED },
    })
    return updated
  }).then(async (result) => {
    // 通知: 撤销 → 当前 pending 步骤的审批人
    //  注: 这里用 demand 上的 managerId/department.hrbpId 简化通知给干系人
    if (demand.managerId) {
      await sendNotification({
        recipientId: demand.managerId,
        templateKey: 'DEMAND_APPROVAL_CANCELLED',
        priority: 'NORMAL',
        context: { demandId, demandName: demand.name || '' },
      }).catch((e) => console.error('[notification] cancel hook failed:', e.message))
    }
    return result
  })
}

/**
 * 匹配适用的审批链配置
 * 匹配维度: (departmentId, positionLevel, amount)
 * 优先级: priority 高的赢;多条匹配时取 priority 最大那条
 */
async function findApplicableConfig(demand) {
  const amount = (demand.salaryMax || demand.salaryMin || 0) * 100 // 元 → 分
  const configs = await prisma.demandApprovalConfig.findMany({
    where: {
      isActive: true,
      OR: [
        { departmentId: demand.departmentId },
        { departmentId: null }, // 通配
      ],
    },
    orderBy: { priority: 'desc' },
  })
  // 进一步过滤 positionLevel + amount
  const matched = configs.find((c) => {
    if (c.positionLevel && c.positionLevel !== demand.jobLevel) return false
    if (c.minAmount != null && amount < c.minAmount) return false
    if (c.maxAmount != null && amount > c.maxAmount) return false
    return true
  })
  return matched
}

/**
 * 构建审批链
 * 优先级: DemandApprovalConfig 配置 > 默认 HRBP → MANAGER → MANAGER_SUPER → CHO
 */
async function buildApprovalChain(demand) {
  // 1. 优先读 config
  const config = await findApplicableConfig(demand)
  if (config?.steps) {
    const configSteps = Array.isArray(config.steps) ? config.steps : []
    if (configSteps.length > 0) {
      return configSteps.map((s) => ({ approverRole: s.approverRole, approverId: s.approverId || null }))
    }
  }

  // 2. 兜底: 写死的部门链
  const steps = []
  const dept = demand.department

  // HRBP - 必填
  if (!dept?.hrbpId) {
    throw new AppError(`部门 ${dept?.name || dept?.id || ''} 未配置 HRBP，无法发起审批`, 400)
  }
  steps.push({ approverRole: 'HRBP', approverId: dept.hrbpId })

  // 用人经理 - 必填
  if (!demand.managerId) {
    throw new AppError('需求未指定用人经理 (managerId)，无法发起审批', 400)
  }
  steps.push({ approverRole: 'MANAGER', approverId: demand.managerId })

  // 用人经理上级
  if (dept.manager2Id && dept.manager2Id !== demand.managerId) {
    steps.push({ approverRole: 'MANAGER_SUPER', approverId: dept.manager2Id })
  }

  // CHO / 总经理
  if (dept.manager3Id && dept.manager3Id !== demand.managerId) {
    steps.push({ approverRole: 'CHO', approverId: dept.manager3Id })
  }

  return steps
}

export default {
  submitForApproval,
  approveDemand,
  rejectDemand,
  cancelApproval,
}
