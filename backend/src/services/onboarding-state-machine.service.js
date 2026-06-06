/**
 * 待入职状态机 - PRD G28
 *
 * 8 个状态:
 *   NOT_STARTED     - 未开始 (Offer 已发, 候选人未确认入职日期)
 *   PENDING_CONFIRM - 待确认 (候选人收到入职提醒, 需确认)
 *   CONFIRMED       - 已确认 (候选人确认入职日期)
 *   PENDING_ONBOARD - 待入职 (已确认, 等入职日)
 *   ONBOARDING      - 入职中 (入职流程办理中)
 *   ONBOARDED       - 已入职 (成功入职, 同步摩卡 People)
 *   PENDING_REJECT  - 待拒绝 (候选人拒入职, HR 决定处理)
 *   CANCELLED       - 已取消 (候选人/HR 取消入职)
 *
 * 状态转换图:
 *   NOT_STARTED → PENDING_CONFIRM (HR 提醒候选人)
 *   PENDING_CONFIRM → CONFIRMED / PENDING_REJECT
 *   CONFIRMED → PENDING_ONBOARD
 *   PENDING_ONBOARD → ONBOARDING (到入职日)
 *   ONBOARDING → ONBOARDED (完成入职流程)
 *   PENDING_REJECT → CANCELLED
 *   任何状态 → CANCELLED (HR 强制取消)
 *
 * 终态: ONBOARDED / CANCELLED
 */

export const ONBOARDING_STATUSES = {
  NOT_STARTED: 'NOT_STARTED',
  PENDING_CONFIRM: 'PENDING_CONFIRM',
  CONFIRMED: 'CONFIRMED',
  PENDING_ONBOARD: 'PENDING_ONBOARD',
  ONBOARDING: 'ONBOARDING',
  ONBOARDED: 'ONBOARDED',
  PENDING_REJECT: 'PENDING_REJECT',
  CANCELLED: 'CANCELLED',
}

const ONBOARDING_TRANSITIONS = {
  NOT_STARTED: ['PENDING_CONFIRM', 'CANCELLED'],
  PENDING_CONFIRM: ['CONFIRMED', 'PENDING_REJECT', 'CANCELLED'],
  CONFIRMED: ['PENDING_ONBOARD', 'CANCELLED'],
  PENDING_ONBOARD: ['ONBOARDING', 'CANCELLED'],
  ONBOARDING: ['ONBOARDED', 'CANCELLED'],
  ONBOARDED: [], // 终态
  PENDING_REJECT: ['CANCELLED', 'CONFIRMED'], // 可重确认
  CANCELLED: [], // 终态
}

/**
 * 检查转换是否合法
 */
export function canTransitionOnboarding(from, to) {
  const allowed = ONBOARDING_TRANSITIONS[from] || []
  return allowed.includes(to)
}

/**
 * 检查是否终态
 */
export function isTerminalOnboarding(status) {
  return (ONBOARDING_TRANSITIONS[status] || []).length === 0
}

/**
 * 检查是否在办理中 (从 PENDING_ONBOARD 到 ONBOARDED)
 */
export function isInProgress(status) {
  return ['PENDING_CONFIRM', 'CONFIRMED', 'PENDING_ONBOARD', 'ONBOARDING'].includes(status)
}

/**
 * 检查是否可同步摩卡 People (仅 ONBOARDED 后)
 */
export function canSyncToPeople(status) {
  return status === ONBOARDING_STATUSES.ONBOARDED
}

export default {
  ONBOARDING_STATUSES,
  canTransitionOnboarding,
  isTerminalOnboarding,
  isInProgress,
  canSyncToPeople,
}
