/**
 * 邀约状态机 - PRD G14 + G15
 *
 * 8 个状态:
 *   PENDING_ASSIGN  - 待分配 (HR 创建后初始,需分配给邀约人)
 *   PENDING_CLAIM   - 待领取 (入抢单池, 邀约人可抢)
 *   PENDING_INVITE  - 待邀约 (已领取, 尚未联系候选人)
 *   INVITING        - 邀约中 (已联系候选人)
 *   SUCCESS         - 已成功 (候选人接受)
 *   FAILED          - 已失败 (候选人拒绝/失联)
 *   TERMINATED      - 已终止 (HR 主动终止)
 *   INTERVENED      - 被干预 (上级接手)
 *
 * 抢单规则 (PRD G14):
 *   - 入池 (PENDING_CLAIM) 时设置 48h 倒计时 (timeoutAt)
 *   - 抢单成功 → 状态切到 PENDING_INVITE, claimedById 记录
 *   - 超时未领取 → 自动归档 (archiveAttempts + 1, 达 3 次强制终止)
 *   - 抢单失败 (timeout) → 重置 24h, 再次入池, 累计 3 次失败 → TERMINATED
 *
 * 上下级流转 (PRD G16):
 *   - 邀约人 → 所属人 → 职位负责人 → 需求负责人 → CHO
 *   - 超时未响应, 自动向上 ping (每 12h)
 *   - 干预次数 > 3 → 标记 INTERVENED
 */

export const INVITATION_STATUSES = {
  PENDING_ASSIGN: 'PENDING_ASSIGN',
  PENDING_CLAIM: 'PENDING_CLAIM',
  PENDING_INVITE: 'PENDING_INVITE',
  INVITING: 'INVITING',
  SUCCESS: 'SUCCESS',
  FAILED: 'FAILED',
  TERMINATED: 'TERMINATED',
  INTERVENED: 'INTERVENED',
}

// 转换图
const INVITATION_TRANSITIONS = {
  PENDING_ASSIGN: ['PENDING_CLAIM', 'PENDING_INVITE', 'TERMINATED'], // 可指派或入池
  PENDING_CLAIM: ['PENDING_INVITE', 'TERMINATED'], // 抢到 或 终止
  PENDING_INVITE: ['INVITING', 'INTERVENED', 'TERMINATED'], // 联系 / 被干预 / 终止
  INVITING: ['SUCCESS', 'FAILED', 'INTERVENED', 'TERMINATED'], // 结果 / 干预 / 终止
  SUCCESS: [], // 终态
  FAILED: ['PENDING_CLAIM', 'TERMINATED'], // 可重新入池 或 终止
  TERMINATED: [], // 终态
  INTERVENED: ['INVITING', 'TERMINATED', 'SUCCESS', 'FAILED'], // 上级处理后流转
}

// 抢单默认时长 (小时)
export const CLAIM_TIMEOUT_HOURS = 48
// 抢单失败次数上限 (PRD G14: 3 次后自动归档)
export const MAX_CLAIM_ATTEMPTS = 3
// 上下级流转间隔 (小时)
export const ESCALATION_INTERVAL_HOURS = 12

export function canTransitionInvitation(from, to) {
  const allowed = INVITATION_TRANSITIONS[from] || []
  return allowed.includes(to)
}

export function isTerminalInvitation(status) {
  return (INVITATION_TRANSITIONS[status] || []).length === 0
}

/**
 * 检查是否在抢单池 (可被抢)
 */
export function isClaimable(status) {
  return status === INVITATION_STATUSES.PENDING_CLAIM
}

/**
 * 检查是否可联系候选人
 */
export function canContactCandidate(status) {
  return [INVITATION_STATUSES.PENDING_INVITE, INVITATION_STATUSES.INVITING].includes(status)
}

export default {
  INVITATION_STATUSES,
  CLAIM_TIMEOUT_HOURS,
  MAX_CLAIM_ATTEMPTS,
  ESCALATION_INTERVAL_HOURS,
  canTransitionInvitation,
  isTerminalInvitation,
  isClaimable,
  canContactCandidate,
}
