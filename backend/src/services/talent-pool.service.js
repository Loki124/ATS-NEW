/**
 * talent-pool.service.js - PRD G32
 * 人才库 6 子库完整 CRUD + 跨池移动 (审计)
 *
 * 6 子库: PASSIVE/ACTIVE/HIRED/REJECTED/BLACKLIST/GENERAL
 * 数据模型: 复用 Candidate.archiveToPool + candidateStatus='ARCHIVED' 表示归档入池
 */

import { prisma } from '../app.js'

export const TALENT_POOL_TYPES = {
  PASSIVE:   { code: 'PASSIVE',   label: '被动简历', description: '求职意愿低, 仅定期触达' },
  ACTIVE:    { code: 'ACTIVE',    label: '主动投递', description: '主动投递但未通过' },
  HIRED:     { code: 'HIRED',     label: '已聘',     description: '历史入职过本公司' },
  REJECTED:  { code: 'REJECTED',  label: '已拒',     description: '明确拒绝 offer 的' },
  BLACKLIST: { code: 'BLACKLIST', label: '黑名单',   description: '永不录用' },
  GENERAL:   { code: 'GENERAL',   label: '通用',     description: '通用人才库' },
}

/**
 * 6 子库候选人数统计
 * @returns {Promise<Object>} { PASSIVE: n, ACTIVE: n, ... }
 */
export async function listPoolStats() {
  const result = {}
  for (const key of Object.keys(TALENT_POOL_TYPES)) {
    result[key] = await prisma.candidate.count({
      where: { archiveToPool: key, candidateStatus: 'ARCHIVED' },
    })
  }
  return result
}

/**
 * 别名: countByPool = listPoolStats
 */
export async function countByPool() {
  return listPoolStats()
}

/**
 * 分页查询指定子库候选人
 * @param {string} poolCode
 * @param {Object} opts { page, pageSize }
 * @returns {Promise<Array>}
 */
export async function listCandidatesInPool(poolCode, { page = 1, pageSize = 20 } = {}) {
  return prisma.candidate.findMany({
    where: { archiveToPool: poolCode, candidateStatus: 'ARCHIVED' },
    skip: (page - 1) * pageSize,
    take: pageSize,
    orderBy: { updatedAt: 'desc' },
  })
}

/**
 * 把候选人移动到目标子库 (写审计)
 * @param {string} candidateId
 * @param {string} targetPool 必须 ∈ TALENT_POOL_TYPES
 * @param {string} reason 转移原因
 * @param {string} operatorId 操作人 user id
 * @returns {Promise<Object>} 更新后的 candidate
 */
export async function moveCandidateToPool(candidateId, targetPool, reason, operatorId) {
  if (!TALENT_POOL_TYPES[targetPool]) {
    throw new Error(`Unknown pool: ${targetPool}`)
  }
  return prisma.$transaction(async (tx) => {
    const updated = await tx.candidate.update({
      where: { id: candidateId },
      data: {
        archiveToPool: targetPool,
        candidateStatus: 'ARCHIVED',
        archiveReason: reason,
        archiveType: 'MANUAL',
      },
    })
    await tx.operationRecord.create({
      data: {
        resource: 'Candidate',
        resourceId: candidateId,
        action: 'MOVE_TO_POOL',
        operatorId,
        details: {
          fromPool: updated.archiveToPool,
          toPool: targetPool,
          reason,
        },
      },
    })
    return updated
  })
}
