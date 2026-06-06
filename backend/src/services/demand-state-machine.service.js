/**
 * 需求状态机 - PRD G1
 *
 * 需求状态 demandStatus (8):
 *   DRAFT      - 草稿
 *   NOT_STARTED - 未进行 (首次审批通过但未到开始时间)
 *   IN_PROGRESS - 进行中
 *   COMPLETED   - 已完成
 *   PAUSED      - 已暂停
 *   STOPPED     - 已停招 (终止态)
 *   EXPIRED     - 已超期
 *
 * 审批状态 approvalStatus (5):
 *   NOT_STARTED  - 未发起
 *   PENDING      - 审批中
 *   APPROVED     - 已通过
 *   REJECTED     - 已拒绝
 *   CANCELLED    - 已撤销
 *
 * 状态转换规则 (PRD G1):
 *   DRAFT → submit → NOT_STARTED (启动 PENDING)
 *   PENDING → approve → APPROVED (需求进入 NOT_STARTED 或 IN_PROGRESS)
 *   PENDING → reject → REJECTED (需求回到 DRAFT)
 *   PENDING → cancel → CANCELLED (需求回到 DRAFT)
 *   APPROVED → start → IN_PROGRESS (到达开始时间)
 *   NOT_STARTED → start → IN_PROGRESS
 *   IN_PROGRESS → pause → PAUSED
 *   IN_PROGRESS → complete → COMPLETED
 *   PAUSED → resume → IN_PROGRESS
 *   IN_PROGRESS → stop → STOPPED (终止态)
 *   IN_PROGRESS → expire → EXPIRED (超期未完成)
 *   NOT_STARTED → expire → EXPIRED
 *
 * 业务规则：
 *   - demandStatus 是需求自身状态，approvalStatus 是审批流状态
 *   - 首次审批通过后，才能 NOT_STARTED/IN_PROGRESS
 *   - 进行中的需求可以创建/编辑职位；已停招/已完成的不能
 *   - 关联职位的招聘完成后，IN_PROGRESS → COMPLETED
 */

export const DEMAND_STATUSES = {
  DRAFT: 'DRAFT',
  NOT_STARTED: 'NOT_STARTED',
  IN_PROGRESS: 'IN_PROGRESS',
  COMPLETED: 'COMPLETED',
  PAUSED: 'PAUSED',
  STOPPED: 'STOPPED',
  EXPIRED: 'EXPIRED',
}

export const APPROVAL_STATUSES = {
  NOT_STARTED: 'NOT_STARTED',
  PENDING: 'PENDING',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
  CANCELLED: 'CANCELLED',
}

// 步骤状态机 - WAITING 是步骤级独有(等待轮到),与 demand 级的 APPROVAL_STATUSES 不同
export const STEP_STATUSES = {
  WAITING: 'WAITING',
  PENDING: 'PENDING',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
  SKIPPED: 'SKIPPED',
}

// 需求状态转换图 (合法 next states)
const DEMAND_TRANSITIONS = {
  DRAFT: ['NOT_STARTED', 'STOPPED'],
  NOT_STARTED: ['IN_PROGRESS', 'PAUSED', 'STOPPED', 'EXPIRED'],
  IN_PROGRESS: ['COMPLETED', 'PAUSED', 'STOPPED', 'EXPIRED'],
  PAUSED: ['IN_PROGRESS', 'STOPPED', 'EXPIRED'],
  COMPLETED: ['IN_PROGRESS', 'STOPPED'], // 已完成后可恢复为进行中（新增空缺）
  STOPPED: [], // 终止态
  EXPIRED: ['IN_PROGRESS', 'STOPPED'],
}

// 审批状态转换图
const APPROVAL_TRANSITIONS = {
  NOT_STARTED: ['PENDING', 'CANCELLED'],
  PENDING: ['APPROVED', 'REJECTED', 'CANCELLED'],
  APPROVED: [], // 终态
  REJECTED: ['PENDING', 'CANCELLED'], // 可重发审批
  CANCELLED: ['PENDING'], // 可重发审批
}

/**
 * 检查转换是否合法
 */
export function canTransitionDemand(from, to) {
  const allowed = DEMAND_TRANSITIONS[from] || []
  return allowed.includes(to)
}

export function canTransitionApproval(from, to) {
  const allowed = APPROVAL_TRANSITIONS[from] || []
  return allowed.includes(to)
}

/**
 * 检查需求是否可创建/编辑职位
 */
export function canAttachPosition(demandStatus) {
  return ['NOT_STARTED', 'IN_PROGRESS'].includes(demandStatus)
}

/**
 * 检查需求是否可发起审批
 */
export function canSubmitForApproval(approvalStatus, demandStatus) {
  // 草稿可以发起审批
  if (approvalStatus !== 'NOT_STARTED' && approvalStatus !== 'REJECTED' && approvalStatus !== 'CANCELLED') {
    return { ok: false, reason: `当前审批状态 ${approvalStatus} 不可发起` }
  }
  if (demandStatus !== 'DRAFT') {
    return { ok: false, reason: `需求状态 ${demandStatus} 不可发起审批（应保持 DRAFT）` }
  }
  return { ok: true }
}

export default {
  DEMAND_STATUSES,
  APPROVAL_STATUSES,
  STEP_STATUSES,
  canTransitionDemand,
  canTransitionApproval,
  canAttachPosition,
  canSubmitForApproval,
}
