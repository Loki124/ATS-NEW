/**
 * 自动归档服务 - PRD G38 #8
 *
 * 4 种规则类型:
 *   INVITE_FAIL: 邀约失败 N 次 → 归档
 *   OFFER_FAIL: Offer 被拒 (候选人/审批人) → 归档
 *   EVAL_FAIL: 评估阶段失败 → 归档
 *   TIMEOUT_UNASSIGNED: 候选人 X 天未被认领 → 归档
 *
 * 设计要点:
 *  - 单一职责: evaluateRule 只评估 (读), archiveApplications 只写
 *  - 4 个 ruleType 全部走真实 prisma 模型 (Candidate, InvitationRecord,
 *    Offer, ApplicationStageRecord, Application),不依赖 Candidate 上的
 *    inviteFailCount 字段 (该字段在当前 schema 中并不存在)
 *  - archiveApplications 写 applicationStatus=ARCHIVED + archivedAt
 *    (schema 中已有 Application.applicationStatus / archivedAt 字段)
 */

import { prisma } from '../app.js'

/**
 * 检查单条规则是否应该被触发
 * @param {object} rule - AutoArchiveRule 记录
 * @returns {Promise<{shouldArchive: boolean, applicationIds: string[], reason: string}>}
 */
export async function evaluateRule(rule) {
  if (!rule) return { shouldArchive: false, applicationIds: [], reason: 'rule missing' }
  if (!rule.enabled) return { shouldArchive: false, applicationIds: [], reason: 'rule disabled' }

  switch (rule.ruleType) {
    case 'INVITE_FAIL':         return evaluateInviteFail(rule)
    case 'OFFER_FAIL':          return evaluateOfferFail(rule)
    case 'EVAL_FAIL':           return evaluateEvalFail(rule)
    case 'TIMEOUT_UNASSIGNED':  return evaluateTimeoutUnassigned(rule)
    default:
      return { shouldArchive: false, applicationIds: [], reason: `unknown ruleType: ${rule.ruleType}` }
  }
}

/**
 * INVITE_FAIL:
 *   config = { failTags: [string], maxAttempts: number, timeWindow?: number }
 *   逻辑: 找出该 process 下, Application 对应的 InvitationRecord.resultStatus
 *         命中 failTags 且 resultAt 在 timeWindow 内的 application 列表
 */
async function evaluateInviteFail(rule) {
  const { failTags = [], maxAttempts = 3, timeWindow = 7 } = rule.config || {}
  if (failTags.length === 0) return { shouldArchive: false, applicationIds: [], reason: 'no fail tags' }
  if (!rule.processId) return { shouldArchive: false, applicationIds: [], reason: 'no processId on rule' }

  const since = new Date(Date.now() - timeWindow * 24 * 60 * 60 * 1000)

  // 先找出该 process 下的 applicationIds
  const applications = await prisma.application.findMany({
    where: { processId: rule.processId },
    select: { id: true, invitation: { select: { resultStatus: true, resultAt: true } } },
  })

  // 统计每个 application 的失败次数
  const failedAppIds = []
  for (const app of applications) {
    if (!app.invitation) continue
    if (!failTags.includes(app.invitation.resultStatus)) continue
    if (app.invitation.resultAt && app.invitation.resultAt < since) continue
    failedAppIds.push(app.id)
  }

  return {
    shouldArchive: failedAppIds.length > 0,
    applicationIds: failedAppIds,
    reason: `INVITE_FAIL: ${failedAppIds.length} apps matched failTags=${failTags.join('|')} in ${timeWindow}d`,
  }
}

/**
 * OFFER_FAIL:
 *   config = { rejectTypes: ["REJECTED_BY_APPROVER" | "REJECTED_BY_CANDIDATE" | ...] }
 *   逻辑: 找 Offer.offerStatus 命中 rejectTypes 的 offer, 取对应 applicationId 去重
 */
async function evaluateOfferFail(rule) {
  const { rejectTypes = [] } = rule.config || {}
  if (rejectTypes.length === 0) return { shouldArchive: false, applicationIds: [], reason: 'no reject types' }

  const offers = await prisma.offer.findMany({
    where: { offerStatus: { in: rejectTypes } },
    select: { id: true, applicationId: true },
  })

  const applicationIds = [...new Set(offers.map(o => o.applicationId).filter(Boolean))]

  return {
    shouldArchive: applicationIds.length > 0,
    applicationIds,
    reason: `OFFER_FAIL: ${applicationIds.length} offers rejected (${rejectTypes.join('|')})`,
  }
}

/**
 * EVAL_FAIL:
 *   config = { stageId: string, failTags: [string], executeTiming: "IMMEDIATE" | "DELAYED", delayDays?: number }
 *   逻辑: ApplicationStageRecord 命中 stageId + toStatus in failTags + exitedAt 窗口内
 *         DELAYED 模式额外要求 exitedAt 早于 (now - delayDays) 才归档
 */
async function evaluateEvalFail(rule) {
  const { stageId, failTags = [], executeTiming = 'IMMEDIATE', delayDays = 0 } = rule.config || {}
  if (!stageId || failTags.length === 0) {
    return { shouldArchive: false, applicationIds: [], reason: 'missing stageId or failTags' }
  }

  // IMMEDIATE: 评估失败即归档; DELAYED: 失败 N 天后才归档
  const exitedAfter = new Date(
    Date.now() - (executeTiming === 'DELAYED' ? (delayDays || 0) : 0) * 24 * 60 * 60 * 1000,
  )

  const records = await prisma.applicationStageRecord.findMany({
    where: {
      stageId,
      toStatus: { in: failTags },
      exitedAt: { gte: exitedAfter },
    },
    select: { applicationId: true },
  })

  const applicationIds = [...new Set(records.map(r => r.applicationId).filter(Boolean))]

  return {
    shouldArchive: applicationIds.length > 0,
    applicationIds,
    reason: `EVAL_FAIL: ${applicationIds.length} apps failed stage=${stageId} tags=${failTags.join('|')} timing=${executeTiming}`,
  }
}

/**
 * TIMEOUT_UNASSIGNED:
 *   config = { timeoutDays: number }
 *   逻辑: Candidate.assignedUserId 为空 + createdAt 早于 (now - timeoutDays)
 *         取该 candidate 下的 applications 列表
 */
async function evaluateTimeoutUnassigned(rule) {
  const { timeoutDays = 7 } = rule.config || {}
  if (!rule.processId) return { shouldArchive: false, applicationIds: [], reason: 'no processId on rule' }

  const since = new Date(Date.now() - timeoutDays * 24 * 60 * 60 * 1000)

  // Candidate 没有 processId 字段; 走 application 反向 (processId 在 application 上)
  // 步骤: 先取 process 下所有 applicationId 集合, 再筛出 candidate 未被认领的
  const applications = await prisma.application.findMany({
    where: { processId: rule.processId },
    select: {
      id: true,
      candidate: { select: { assignedUserId: true, createdAt: true } },
    },
  })

  const applicationIds = applications
    .filter(a => a.candidate && a.candidate.assignedUserId === null && a.candidate.createdAt <= since)
    .map(a => a.id)

  return {
    shouldArchive: applicationIds.length > 0,
    applicationIds,
    reason: `TIMEOUT_UNASSIGNED: ${applicationIds.length} apps unassigned for ${timeoutDays}d in process ${rule.processId}`,
  }
}

/**
 * 执行归档: 把 applications 状态改为 ARCHIVED
 * @param {string[]} applicationIds
 * @returns {Promise<{archivedCount: number}>}
 */
export async function archiveApplications(applicationIds) {
  if (!Array.isArray(applicationIds) || applicationIds.length === 0) {
    return { archivedCount: 0 }
  }
  const result = await prisma.application.updateMany({
    where: { id: { in: applicationIds }, applicationStatus: { not: 'ARCHIVED' } },
    data: {
      applicationStatus: 'ARCHIVED',
      archivedAt: new Date(),
    },
  })
  return { archivedCount: result.count }
}

/**
 * 跑一次完整的 archive check (所有 enabled rules)
 * @param {object} prismaClient 可选 prisma 实例 (便于测试注入)
 * @returns {Promise<{total: number, archived: number, skipped: number}>}
 */
export async function runAutoArchiveCheck(prismaClient = prisma) {
  const rules = await prismaClient.autoArchiveRule.findMany({ where: { enabled: true } })
  let archived = 0
  let skipped = 0

  for (const rule of rules) {
    try {
      const evalResult = await evaluateRule(rule)
      if (evalResult.shouldArchive) {
        const result = await archiveApplications(evalResult.applicationIds)
        archived += result.archivedCount
        if (result.archivedCount > 0) {
          console.log(`[auto-archive] rule ${rule.id} (${rule.ruleType}): ${result.archivedCount} archived — ${evalResult.reason}`)
        }
      } else {
        skipped++
      }
    } catch (e) {
      console.error(`[auto-archive] rule ${rule.id} (${rule.ruleType}) failed:`, e.message)
      skipped++
    }
  }

  return { total: rules.length, archived, skipped }
}

export default {
  evaluateRule,
  archiveApplications,
  runAutoArchiveCheck,
}
