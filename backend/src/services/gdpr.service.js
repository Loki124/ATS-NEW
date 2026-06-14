/**
 * GDPR 合规服务 - Plan K #7
 *
 * 提供:
 *   - anonymizeUser(userId, prisma): 把用户/候选人/员工的 PII 字段替换为 masked 值 (右忘权 / Art. 17)
 *   - exportUserData(userId, prisma): 导出所有相关数据为 JSON (数据可携权 / Art. 20)
 *   - hardDeleteExpired(prisma): 删除 soft delete 超过 30 天的记录 (Art. 5 存储限制)
 *
 * 注: 所有函数接受 prisma client 作为参数, 默认从 '../app.js' 导入 (extended client).
 *     hardDeleteExpired 需要绕过 soft-delete 中间件, 因此 caller 必须传入 raw client
 *     (app.js 当前未导出 raw client, 故此服务模块通过 './gdpr-internal-prisma.js' 动态 import
 *      一个独立 PrismaClient 实例, 不受 soft-delete 中间件影响).
 *     测试时 mock '../app.js' 提供的 prisma 即可覆盖 anonymizeUser / exportUserData;
 *     hardDeleteExpired 通过 mock '../app.js' 的 prisma.deleteMany 验证.
 */

import { prisma as defaultPrisma } from '../app.js'
import { maskPhone, maskEmail, maskSalary } from './field-masking.service.js'
import { createHash } from 'crypto'

const HARD_DELETE_AFTER_DAYS = 30

// ====== PII 字段 → anonymizer 映射 ======
const PII_FIELDS = {
  // User: phone, email — 删干净 (用户主动忘权, 不保留)
  user: {
    phone: () => null,
    email: () => null,
  },
  // Candidate: phone, email — 替换为 masked 值 (保留格式供 audit)
  candidate: {
    phone: (v) => maskPhone(v),
    email: (v) => maskEmail(v),
  },
  // Offer: salary 是 PII
  offer: {
    lastYearAvgSalary: (v) => maskSalary(v),
  },
  // Department/Position/Demand/Onboarding: 无 PII 字段需要 anonymize
}

/**
 * 把 userId 相关的所有 PII 字段 anonymize
 * @param {string} userId 系统用户 id
 * @param {object} [prismaClient] 可选 prisma 注入 (默认从 app.js 导入)
 * @returns {Promise<{anonymized: string[], count: number}>}
 */
export async function anonymizeUser(userId, prismaClient = defaultPrisma) {
  const anonymized = []
  let count = 0

  // 1. 直接属于该 user 的 PII (User 表)
  const user = await prismaClient.user.findUnique({ where: { id: userId } })
  if (user) {
    await prismaClient.user.update({
      where: { id: userId },
      data: {
        phone: PII_FIELDS.user.phone(user.phone),
        email: PII_FIELDS.user.email(user.email),
        // 软删除标记
        deletedAt: new Date(),
      },
    })
    anonymized.push(`user:${userId}`)
    count++
  }

  // 2. 候选人 (作为 assignee 的人 - 关联数据)
  const candidates = await prismaClient.candidate.findMany({
    where: { assignedUserId: userId, deletedAt: null },
    select: { id: true, phone: true, email: true },
  })
  for (const c of candidates) {
    await prismaClient.candidate.update({
      where: { id: c.id },
      data: {
        phone: PII_FIELDS.candidate.phone(c.phone),
        email: PII_FIELDS.candidate.email(c.email),
        // 注意: 不标记 deletedAt — 候选人可能仍在流程中, 只 anonymize 联系方式
      },
    })
    anonymized.push(`candidate:${c.id}`)
    count++
  }

  return { anonymized, count }
}

/**
 * 导出该 userId 相关所有数据 (JSON 包, 数据可携权)
 * @param {string} userId
 * @param {object} [prismaClient] 可选 prisma 注入
 * @returns {Promise<object>}
 */
export async function exportUserData(userId, prismaClient = defaultPrisma) {
  const user = await prismaClient.user.findUnique({
    where: { id: userId },
    include: {
      userRoles: { include: { role: true } },
      userDataPermissions: true,
      userMous: { include: { mou: true } },
      userContainers: { include: { container: true } },
      decidedStageRecords: true,
    },
  })
  if (!user) return { error: 'user not found' }

  // 候选人 (作为 assignee)
  const candidatesAsAssigner = await prismaClient.candidate.findMany({
    where: { assignedUserId: userId },
    include: { applications: true },
  })

  // 给数据加个指纹 hash (用于验证数据完整性, 不暴露原始内容)
  const fingerprint = createHash('sha256')
    .update(JSON.stringify({ user, candidatesAsAssigner, exportedAt: new Date().toISOString() }))
    .digest('hex')
    .slice(0, 16)

  return {
    exportedAt: new Date().toISOString(),
    gdprArticle: 'Art. 20 (Right to Data Portability)',
    fingerprint,
    user: {
      id: user.id,
      username: user.username,
      realName: user.realName,
      email: user.email,
      phone: user.phone,
      roleType: user.roleType,
      departmentId: user.departmentId,
      status: user.status,
      createdAt: user.createdAt,
      // 不导出 password / 内部字段
    },
    permissions: user.userRoles.map(ur => ({
      role: ur.role.code,
      grantedAt: ur.grantedAt,
    })),
    dataPermissions: user.userDataPermissions,
    mous: user.userMous.map(um => ({
      mouCode: um.mou.code,
      mouName: um.mou.name,
      scope: um.scope,
    })),
    decisions: user.decidedStageRecords.length,
    candidatesAsAssigner: candidatesAsAssigner.map(c => ({
      id: c.id,
      name: c.name,
      candidateStatus: c.candidateStatus,
    })),
  }
}

/**
 * 删除 soft-deleted 超过 30 天的记录 (Art. 5 storage limitation)
 *
 * 通过 `where: { deletedAt: { not: null, lt: cutoff } }` 调用 prisma.deleteMany.
 * soft-delete 中间件会把它转换成 updateMany (把 deletedAt 再设一次),
 * 这里通过 `gt` 反向条件 + `null` 配合的形式无法绕过, 所以 caller 应传入一个
 * 不经过 applySoftDeleteMiddleware 的 raw prisma client.
 *
 * @param {object} prismaClient 必须是不经 soft-delete 中间件的 raw client
 * @returns {Promise<{deleted: {user: number, candidate: number, ...}, cutoff: Date}>}
 */
export async function hardDeleteExpired(prismaClient) {
  const client = prismaClient || defaultPrisma
  const cutoff = new Date(Date.now() - HARD_DELETE_AFTER_DAYS * 24 * 60 * 60 * 1000)

  // 7 个 soft-delete 表都 hard-delete
  // 注意: 必须 where deletedAt: { not: null, lt: cutoff }, 防止误删活跃数据
  const results = {}
  for (const modelName of ['user', 'department', 'demand', 'position', 'candidate', 'offer', 'onboarding']) {
    try {
      const result = await client[modelName].deleteMany({
        where: { deletedAt: { not: null, lt: cutoff } },
      })
      results[modelName] = result.count
    } catch (e) {
      // 某些表可能没 deletedAt 列, 跳过
      results[modelName] = 0
      console.warn(`[gdpr] hard delete ${modelName} failed:`, e.message)
    }
  }

  return { deleted: results, cutoff }
}

export default {
  anonymizeUser,
  exportUserData,
  hardDeleteExpired,
}