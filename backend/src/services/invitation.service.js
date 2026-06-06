/**
 * 邀约服务 - PRD G14 + G15 + G16
 *
 * 核心业务:
 *   - 入抢单池: PENDING_ASSIGN → PENDING_CLAIM, 设置 48h 倒计时
 *   - 抢单: PENDING_CLAIM → PENDING_INVITE, 记录 claimedBy
 *   - 标记联系: PENDING_INVITE → INVITING, 增加 contactAttempts
 *   - 标记结果: INVITING → SUCCESS / FAILED
 *   - 干预: 任何活跃状态 → INTERVENED, 记录 interventionBy
 *   - 终止: 任何状态 → TERMINATED
 *
 * 抢单失败 3 次 → 强制 TERMINATED
 * 上下级流转: 邀约人 → 所属人 → 职位负责人 → 需求负责人 → CHO
 */

import { prisma } from '../app.js'
import { AppError } from '../middleware/error.middleware.js'
import {
  INVITATION_STATUSES,
  CLAIM_TIMEOUT_HOURS,
  MAX_CLAIM_ATTEMPTS,
  canTransitionInvitation,
  isClaimable,
  canContactCandidate,
} from './invitation-state-machine.service.js'

/**
 * 入抢单池
 * 状态: PENDING_ASSIGN → PENDING_CLAIM
 * 设置 timeoutAt = now + 48h
 */
export async function enterClaimPool(invitationId, { reason } = {}) {
  return prisma.$transaction(async (tx) => {
    const inv = await tx.invitationRecord.findUnique({ where: { id: invitationId } })
    if (!inv) throw new AppError('邀约记录不存在', 404)
    if (inv.invitationStatus !== INVITATION_STATUSES.PENDING_ASSIGN) {
      throw new AppError(`当前状态 ${inv.invitationStatus} 不可入池`, 400)
    }
    const timeoutAt = new Date(Date.now() + CLAIM_TIMEOUT_HOURS * 3600 * 1000)
    return tx.invitationRecord.update({
      where: { id: invitationId },
      data: {
        invitationStatus: INVITATION_STATUSES.PENDING_CLAIM,
        timeoutAt,
        note: reason ? `入池: ${reason}` : inv.note,
      },
    })
  })
}

/**
 * 抢单
 * 状态: PENDING_CLAIM → PENDING_INVITE
 */
export async function claimInvitation(invitationId, claimerId, claimerName) {
  return prisma.$transaction(async (tx) => {
    const inv = await tx.invitationRecord.findUnique({ where: { id: invitationId } })
    if (!inv) throw new AppError('邀约记录不存在', 404)
    if (!isClaimable(inv.invitationStatus)) {
      throw new AppError(`当前状态 ${inv.invitationStatus} 不可抢单`, 400)
    }
    if (inv.timeoutAt && inv.timeoutAt < new Date()) {
      throw new AppError('抢单已超时', 400)
    }
    return tx.invitationRecord.update({
      where: { id: invitationId },
      data: {
        invitationStatus: INVITATION_STATUSES.PENDING_INVITE,
        claimedAt: new Date(),
        claimedById: claimerId,
        claimedByName: claimerName,
        inviterId: claimerId,
        inviterName: claimerName,
      },
    })
  })
}

/**
 * 标记联系候选人
 * PENDING_INVITE → INVITING
 */
export async function markContacted(invitationId, { note } = {}) {
  return prisma.$transaction(async (tx) => {
    const inv = await tx.invitationRecord.findUnique({ where: { id: invitationId } })
    if (!inv) throw new AppError('邀约记录不存在', 404)
    if (!canContactCandidate(inv.invitationStatus)) {
      throw new AppError(`当前状态 ${inv.invitationStatus} 不可标记联系`, 400)
    }
    return tx.invitationRecord.update({
      where: { id: invitationId },
      data: {
        invitationStatus: INVITATION_STATUSES.INVITING,
        lastContactAt: new Date(),
        contactAttempts: { increment: 1 },
        note: note || inv.note,
      },
    })
  })
}

/**
 * 标记结果
 * INVITING → SUCCESS / FAILED
 */
export async function markResult(invitationId, { success, reason } = {}) {
  const target = success ? INVITATION_STATUSES.SUCCESS : INVITATION_STATUSES.FAILED
  return prisma.$transaction(async (tx) => {
    const inv = await tx.invitationRecord.findUnique({ where: { id: invitationId } })
    if (!inv) throw new AppError('邀约记录不存在', 404)
    if (!canTransitionInvitation(inv.invitationStatus, target)) {
      throw new AppError(`状态转移非法: ${inv.invitationStatus} → ${target}`, 400)
    }
    return tx.invitationRecord.update({
      where: { id: invitationId },
      data: {
        invitationStatus: target,
        resultStatus: success ? 'PASS' : 'FAIL',
        resultReason: reason,
        resultAt: new Date(),
      },
    })
  })
}

/**
 * 干预 (上级接手)
 * 任何活跃状态 → INTERVENED
 */
export async function intervene(invitationId, { operatorId, operatorName, reason } = {}) {
  return prisma.$transaction(async (tx) => {
    const inv = await tx.invitationRecord.findUnique({ where: { id: invitationId } })
    if (!inv) throw new AppError('邀约记录不存在', 404)
    if (inv.invitationStatus === INVITATION_STATUSES.SUCCESS ||
        inv.invitationStatus === INVITATION_STATUSES.FAILED ||
        inv.invitationStatus === INVITATION_STATUSES.TERMINATED) {
      throw new AppError(`终态不可干预`, 400)
    }
    return tx.invitationRecord.update({
      where: { id: invitationId },
      data: {
        invitationStatus: INVITATION_STATUSES.INTERVENED,
        interventionCount: { increment: 1 },
        lastInterventionBy: operatorName || operatorId,
        inviterId: operatorId,
        inviterName: operatorName,
        note: reason ? `干预: ${reason}` : inv.note,
      },
    })
  })
}

/**
 * 终止
 * 任何状态 → TERMINATED
 */
export async function terminate(invitationId, { reason, operatorId } = {}) {
  return prisma.invitationRecord.update({
    where: { id: invitationId },
    data: {
      invitationStatus: INVITATION_STATUSES.TERMINATED,
      note: reason ? `终止: ${reason} (by ${operatorId || 'system'})` : undefined,
    },
  })
}

/**
 * 处理超时 (cron 调用)
 *  - PENDING_CLAIM 超时: 失败次数 + 1, < 3 次重置 24h 重入池, >= 3 次 → TERMINATED
 *  - PENDING_INVITE 超时: 上下级流转 (escalation)
 *
 * @returns {Promise<{ processed: number, claimed: number, escalated: number, terminated: number }>}
 */
export async function processExpiredInvitations() {
  const now = new Date()
  const expired = await prisma.invitationRecord.findMany({
    where: {
      invitationStatus: { in: [INVITATION_STATUSES.PENDING_CLAIM, INVITATION_STATUSES.PENDING_INVITE] },
      timeoutAt: { lt: now, not: null },
    },
  })

  const stats = { processed: 0, requeued: 0, escalated: 0, terminated: 0 }
  for (const inv of expired) {
    stats.processed++
    try {
      if (inv.invitationStatus === INVITATION_STATUSES.PENDING_CLAIM) {
        // 抢单超时: 累计失败次数
        const attempts = (inv.contactAttempts || 0) + 1
        if (attempts >= MAX_CLAIM_ATTEMPTS) {
          await prisma.invitationRecord.update({
            where: { id: inv.id },
            data: {
              invitationStatus: INVITATION_STATUSES.TERMINATED,
              contactAttempts: attempts,
              note: `抢单失败 ${attempts} 次, 强制终止`,
            },
          })
          stats.terminated++
        } else {
          // 重入池, 24h 倒计时
          await prisma.invitationRecord.update({
            where: { id: inv.id },
            data: {
              invitationStatus: INVITATION_STATUSES.PENDING_CLAIM,
              contactAttempts: attempts,
              timeoutAt: new Date(Date.now() + 24 * 3600 * 1000),
              note: `第 ${attempts} 次重入池`,
            },
          })
          stats.requeued++
        }
      } else if (inv.invitationStatus === INVITATION_STATUSES.PENDING_INVITE) {
        // PENDING_INVITE 超时: 升级到上级
        await escalate(inv.id)
        stats.escalated++
      }
    } catch (e) {
      console.error(`[invitation-cron] 处理 ${inv.id} 失败:`, e.message)
    }
  }
  return stats
}

/**
 * 升级到上一级处理人 (PRD G16)
 * 邀约人 → 所属人 → 职位负责人 → 需求负责人 → CHO
 *
 * MVP 简化: 只记录 escalation, 不做实际切换人
 */
async function escalate(invitationId) {
  return prisma.invitationRecord.update({
    where: { id: invitationId },
    data: {
      interventionCount: { increment: 1 },
      lastInterventionBy: 'ESCALATION_SYSTEM',
      note: '超时自动升级',
    },
  })
}

export default {
  enterClaimPool,
  claimInvitation,
  markContacted,
  markResult,
  intervene,
  terminate,
  processExpiredInvitations,
}
