/**
 * 职位状态机 - PRD G5
 *
 * 3 个状态:
 *   RECRUITING  - 招聘中 (默认)
 *   PAUSED      - 已暂停
 *   CLOSED      - 已关闭 (招满/停招)
 *
 * 状态转换图:
 *   RECRUITING → PAUSED  (HR 主动暂停)
 *   RECRUITING → CLOSED  (招满 / 停招)
 *   PAUSED     → RECRUITING (恢复招聘)
 *   PAUSED     → CLOSED  (直接关闭)
 *   CLOSED     → RECRUITING (重新开放,需 SUPER_ADMIN)
 *
 * 业务规则 (PRD G5 "候选人存在保护"):
 *   - CLOSED 时,若仍有 ACTIVE 状态的候选人,应抛 400
 *   - 允许例外: 强制 forceClose=true 跳过保护(管理员场景)
 *
 * 状态字段: Position.positionStatus
 */

import { prisma } from '../app.js'

export const POSITION_STATUSES = {
  RECRUITING: 'RECRUITING',
  PAUSED: 'PAUSED',
  CLOSED: 'CLOSED',
}

const POSITION_TRANSITIONS = {
  RECRUITING: ['PAUSED', 'CLOSED'],
  PAUSED: ['RECRUITING', 'CLOSED'],
  CLOSED: ['RECRUITING'], // reopen 需 super admin
}

/**
 * 检查转换是否合法
 */
export function canTransitionPosition(from, to) {
  const allowed = POSITION_TRANSITIONS[from] || []
  return allowed.includes(to)
}

/**
 * 检查是否有 active 候选人 (候选人存在保护)
 */
export async function hasActiveCandidates(positionId, prismaClient = prisma) {
  const count = await prismaClient.application.count({
    where: { positionId, applicationStatus: 'ACTIVE' },
  })
  return count > 0
}

/**
 * 关闭职位 (含候选人保护检查)
 * @param {string} positionId
 * @param {object} options
 * @param {boolean} options.forceClose - true 跳过候选人保护
 * @throws AppError 400 如果有 active 候选人且未 forceClose
 */
export async function closePosition(positionId, { forceClose = false } = {}) {
  if (!forceClose && await hasActiveCandidates(positionId)) {
    const count = await prisma.application.count({
      where: { positionId, applicationStatus: 'ACTIVE' },
    })
    const err = new Error(`该职位下还有 ${count} 个 ACTIVE 状态的候选人,无法关闭。可传 forceClose=true 强制关闭(会自动归档候选人)。`)
    err.statusCode = 400
    err.code = 'ACTIVE_CANDIDATES_EXIST'
    throw err
  }

  if (forceClose) {
    // 强制关闭: 自动归档所有 active 候选人
    await prisma.application.updateMany({
      where: { positionId, applicationStatus: 'ACTIVE' },
      data: { applicationStatus: 'ARCHIVED', archiveReason: '职位强制关闭', archivedAt: new Date() },
    })
  }
}

/**
 * 检查职位是否处于招聘中
 */
export function isRecruiting(position) {
  return position.positionStatus === POSITION_STATUSES.RECRUITING
}

/**
 * 检查职位是否可接收新候选人
 */
export function canAcceptNewCandidates(positionStatus) {
  return positionStatus === POSITION_STATUSES.RECRUITING
}

export default {
  POSITION_STATUSES,
  canTransitionPosition,
  hasActiveCandidates,
  closePosition,
  isRecruiting,
  canAcceptNewCandidates,
}
