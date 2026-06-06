/**
 * 候选人阶段进入条件服务 - PRD G10 + G1.5
 *
 * 复用 recruitment-condition.service.js 的 evaluateConditionTree
 * 唯一差异: 构造候选人上下文 (candidate 字段 + 历史阶段状态)
 *
 * 典型用法:
 *   const ctx = await buildCandidateContext(candidateId, applicationId)
 *   const result = await evaluateCandidateForStage(candidateId, entryConditionId)
 *
 * 入参 candidate: { age, gender, marriage, highestEducation, ... }
 * 入参 stageStatuses: { [stageId]: 'PASS' | 'FAIL' | 'PENDING' }
 */

import { prisma } from '../app.js'
import { evaluateConditionTree, buildFailedPrompt } from './recruitment-condition.service.js'

/**
 * 构造候选人上下文
 * @param {string} candidateId
 * @param {string} applicationId - 用于收集历史阶段状态
 * @returns {Promise<{ candidate: object, stageStatuses: object }>}
 */
export async function buildCandidateContext(candidateId, applicationId = null) {
  const candidate = await prisma.candidate.findUnique({
    where: { id: candidateId },
    select: {
      id: true, name: true, age: true, gender: true,
      marriage: true, highestEducation: true, firstEducation: true,
      currentCompany: true, currentPosition: true, workYears: true,
      email: true, phone: true, source: true,
    },
  })
  if (!candidate) throw new Error(`候选人不存在: ${candidateId}`)

  // 收集 application 的所有历史阶段状态
  let stageStatuses = {}
  if (applicationId) {
    const applications = await prisma.application.findMany({
      where: { candidateId },
      select: { id: true, currentStageId: true, currentStageStatus: true },
    })
    for (const app of applications) {
      if (app.currentStageId) {
        stageStatuses[app.currentStageId] = app.currentStageStatus || 'PENDING'
      }
    }
  }

  return {
    candidate: {
      age: candidate.age,
      gender: candidate.gender,
      marriage: candidate.marriage,
      highestEducation: candidate.highestEducation,
      firstEducation: candidate.firstEducation,
      currentCompany: candidate.currentCompany,
      currentPosition: candidate.currentPosition,
      workYears: candidate.workYears,
      email: candidate.email,
      phone: candidate.phone,
      source: candidate.source,
    },
    stageStatuses,
  }
}

/**
 * 评估候选人是否满足某条 EntryCondition
 * @param {string} candidateId
 * @param {string} entryConditionId
 * @param {string} applicationId - 可选, 用于收集阶段状态
 */
export async function evaluateCandidateForStage(candidateId, entryConditionId, applicationId = null) {
  const cond = await prisma.entryCondition.findUnique({
    where: { id: entryConditionId },
    include: { items: { orderBy: { orderIndex: 'asc' } } },
  })
  if (!cond) throw new Error(`进入条件不存在: ${entryConditionId}`)
  if (!cond.isActive) return { passed: true, failedItems: [], prompt: null, skipped: 'INACTIVE' }

  const context = await buildCandidateContext(candidateId, applicationId)
  const result = evaluateConditionTree(cond.items, cond.matchType, context)
  return {
    passed: result.passed,
    failedItems: result.failedItems,
    prompt: result.passed ? null : buildFailedPrompt(cond.items, result.failedItems, context, cond.prompt),
    context, // 回传便于前端展示
  }
}

/**
 * 批量评估: 一个候选人对多条 EntryCondition
 * 用于"评估该候选人能否进入任意阶段"
 */
export async function evaluateCandidateForStages(candidateId, entryConditionIds, applicationId = null) {
  const results = await Promise.all(
    entryConditionIds.map(async (eid) => ({
      entryConditionId: eid,
      ...(await evaluateCandidateForStage(candidateId, eid, applicationId)),
    }))
  )
  return results
}

/**
 * 应用阶段转移前校验
 * @returns {Promise<{ allowed: boolean, reason?: string, prompt?: string }>}
 */
export async function checkStageTransitionAllowed(applicationId, entryConditionId = null) {
  const app = await prisma.application.findUnique({ where: { id: applicationId } })
  if (!app) throw new Error(`申请不存在: ${applicationId}`)

  // 1. 用 application 自带的 entryConditionId (从 link 取)
  let condId = entryConditionId
  if (!condId && app.currentStageId) {
    const link = await prisma.processStageLink.findFirst({
      where: { processId: app.processId, stageId: app.currentStageId },
    })
    condId = link?.entryConditionId
  }
  if (!condId) return { allowed: true, reason: '无关联进入条件,默认放行' }

  const result = await evaluateCandidateForStage(app.candidateId, condId, applicationId)
  return {
    allowed: result.passed,
    reason: result.passed ? null : '不满足进入条件',
    prompt: result.prompt,
  }
}

export default {
  buildCandidateContext,
  evaluateCandidateForStage,
  evaluateCandidateForStages,
  checkStageTransitionAllowed,
}
