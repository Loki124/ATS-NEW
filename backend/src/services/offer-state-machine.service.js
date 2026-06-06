/**
 * Offer 状态机 - PRD G23
 *
 * 9 个状态:
 *   NOT_CREATED      - 未创建 (Offer 记录初始)
 *   DRAFT            - 草稿编辑中
 *   PENDING_APPROVAL - 待审批
 *   APPROVED         - 已通过审批 (可发送)
 *   SENT             - 已发送候选人
 *   ACCEPTED         - 候选人已接受
 *   REJECTED         - 候选人已拒绝
 *   WITHDRAWN        - 用人方撤销
 *   EXPIRED          - 已过期 (候选人长期未回复)
 *
 * 状态转换图:
 *   NOT_CREATED     → DRAFT (HR 开始编辑)
 *   DRAFT           → PENDING_APPROVAL (提交审批)
 *   PENDING_APPROVAL → APPROVED (审批通过) / WITHDRAWN (撤销)
 *   APPROVED        → SENT (发送给候选人)
 *   SENT            → ACCEPTED (候选人接受) / REJECTED (候选人拒绝) / EXPIRED (超时)
 *   ACCEPTED        → ONBOARDING (转 G28 待入职状态机,不在本机)
 *   REJECTED        → DRAFT (可重新编辑,需产品确认)
 *   WITHDRAWN       → 终态
 *   EXPIRED         → DRAFT (可重新发送)
 *
 * 终态: WITHDRAWN (撤销后不再操作)
 * 注: REJECTED / EXPIRED 在某些业务可转 DRAFT 重发,需结合产品确认
 */

export const OFFER_STATUSES = {
  NOT_CREATED: 'NOT_CREATED',
  DRAFT: 'DRAFT',
  PENDING_APPROVAL: 'PENDING_APPROVAL',
  APPROVED: 'APPROVED',
  SENT: 'SENT',
  ACCEPTED: 'ACCEPTED',
  REJECTED: 'REJECTED',
  WITHDRAWN: 'WITHDRAWN',
  EXPIRED: 'EXPIRED',
}

const OFFER_TRANSITIONS = {
  NOT_CREATED: ['DRAFT'],
  DRAFT: ['PENDING_APPROVAL', 'WITHDRAWN'],
  PENDING_APPROVAL: ['APPROVED', 'WITHDRAWN'],
  APPROVED: ['SENT', 'WITHDRAWN'],
  SENT: ['ACCEPTED', 'REJECTED', 'EXPIRED', 'WITHDRAWN'],
  ACCEPTED: [], // 转 G28 待入职
  REJECTED: ['DRAFT'], // 重新编辑
  WITHDRAWN: [], // 终态
  EXPIRED: ['DRAFT', 'WITHDRAWN'], // 重新编辑或放弃
}

/**
 * 检查转换是否合法
 */
export function canTransitionOffer(from, to) {
  const allowed = OFFER_TRANSITIONS[from] || []
  return allowed.includes(to)
}

/**
 * 检查是否为终态
 */
export function isTerminalOffer(status) {
  return (OFFER_TRANSITIONS[status] || []).length === 0
}

/**
 * 检查是否可发送（需要 APPROVED 状态）
 */
export function canSendOffer(status) {
  return status === OFFER_STATUSES.APPROVED
}

/**
 * 检查是否可编辑
 */
export function canEditOffer(status) {
  return [OFFER_STATUSES.NOT_CREATED, OFFER_STATUSES.DRAFT, OFFER_STATUSES.REJECTED, OFFER_STATUSES.EXPIRED].includes(status)
}

/**
 * 检查是否可提交审批
 */
export function canSubmitOfferForApproval(status) {
  return [OFFER_STATUSES.DRAFT, OFFER_STATUSES.REJECTED].includes(status)
}

export default {
  OFFER_STATUSES,
  canTransitionOffer,
  isTerminalOffer,
  canSendOffer,
  canEditOffer,
  canSubmitOfferForApproval,
}
