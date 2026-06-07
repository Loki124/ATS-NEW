/**
 * 评分规则服务 - PRD G39
 *
 * 复用 recruitment-condition.service 的 evaluateConditionTree
 * 评分流程: 候选人字段 → ScoringCondition 评估 → 命中条件求和 → 最终分数
 *
 * 支持 2 种规则类型 (ruleType):
 *   - SUM_MATCHED:    所有命中条件累加分数
 *   - WEIGHTED_AVERAGE: 命中条件按权重加权平均
 *   - THRESHOLD:      命中条件分数达到阈值则通过
 */

import { prisma } from '../app.js'
import { AppError } from '../middleware/error.middleware.js'
import { evaluateConditionTree } from './recruitment-condition.service.js'

export const SCORING_RULE_TYPES = {
  SUM_MATCHED: 'SUM_MATCHED',
  WEIGHTED_AVERAGE: 'WEIGHTED_AVERAGE',
  THRESHOLD: 'THRESHOLD',
}

export const SCORING_RULE_TYPE_LABEL = {
  SUM_MATCHED: '求和命中',
  WEIGHTED_AVERAGE: '加权平均',
  THRESHOLD: '阈值判定',
}

/**
 * 计算候选人分数
 * @param {string} ruleId 评分规则 ID
 * @param {object} context 候选人上下文 { candidate, stageStatuses }
 * @returns {Promise<{ totalScore: number, passed: boolean, details: Array }>}
 */
export async function evaluateCandidateForRule(ruleId, context = {}) {
  const rule = await prisma.scoringRule.findUnique({
    where: { id: ruleId },
    include: {
      conditions: {
        include: { items: { orderBy: { orderIndex: 'asc' } } },
      },
      results: { orderBy: { createdAt: 'asc' } },
    },
  })
  if (!rule) throw new AppError('评分规则不存在', 404)
  if (rule.status !== 'ACTIVE') {
    return { totalScore: 0, passed: false, details: [], skipped: 'INACTIVE' }
  }

  // 评估每个 condition
  const conditionResults = []
  for (const cond of rule.conditions) {
    const r = evaluateConditionTree(cond.items, cond.matchType, context)
    conditionResults.push({
      conditionId: cond.id,
      name: cond.name,
      passed: r.passed,
      failedItems: r.failedItems,
    })
  }

  // 算总分
  const resultMap = new Map(rule.results.map((r) => [r.conditionId, r]))
  const details = []
  let totalScore = 0
  let matchedCount = 0

  for (const cr of conditionResults) {
    const scoreRule = resultMap.get(cr.conditionId)
    const matchedScore = scoreRule?.matchedScore || 0
    const unmatchedScore = scoreRule?.unmatchedScore || 0
    const score = cr.passed ? matchedScore : unmatchedScore

    totalScore += score
    if (cr.passed) matchedCount++

    details.push({
      ...cr,
      score,
      matchedScore,
      unmatchedScore,
    })
  }

  // 按规则类型计算最终结果
  const passed = computePassedByRuleType(rule, totalScore, matchedCount, conditionResults.length)

  return { totalScore, passed, details, ruleType: rule.ruleType }
}

/**
 * 根据规则类型计算通过性
 */
function computePassedByRuleType(rule, totalScore, matchedCount, totalCount) {
  switch (rule.ruleType) {
    case SCORING_RULE_TYPES.SUM_MATCHED:
      // 所有命中分数求和; 通过阈值在 description 中约定 (MVP: >= 60 算通过)
      return totalScore >= 60
    case SCORING_RULE_TYPES.WEIGHTED_AVERAGE:
      return matchedCount / Math.max(totalCount, 1) >= 0.5
    case SCORING_RULE_TYPES.THRESHOLD:
      return totalScore >= 80
    default:
      return totalScore > 0
  }
}

/**
 * 列出所有评分规则
 */
export async function listScoringRules({ status, page = 1, pageSize = 20 } = {}) {
  const where = {}
  if (status) where.status = status
  const [list, total] = await Promise.all([
    prisma.scoringRule.findMany({
      where,
      orderBy: { createdAt: 'desc' },
      include: { _count: { select: { conditions: true, results: true } } },
      skip: (Number(page) - 1) * Number(pageSize),
      take: Number(pageSize),
    }),
    prisma.scoringRule.count({ where }),
  ])
  return { list, total, page: Number(page), pageSize: Number(pageSize) }
}

export async function getScoringRule(id) {
  return prisma.scoringRule.findUnique({
    where: { id },
    include: {
      conditions: { include: { items: { orderBy: { orderIndex: 'asc' } } } },
      results: { orderBy: { createdAt: 'asc' } },
    },
  })
}

export async function createScoringRule(data) {
  return prisma.scoringRule.create({ data })
}

export async function updateScoringRule(id, data) {
  return prisma.scoringRule.update({ where: { id }, data })
}

export async function deleteScoringRule(id) {
  return prisma.scoringRule.delete({ where: { id } })
}

export default {
  SCORING_RULE_TYPES,
  SCORING_RULE_TYPE_LABEL,
  evaluateCandidateForRule,
  listScoringRules,
  getScoringRule,
  createScoringRule,
  updateScoringRule,
  deleteScoringRule,
}
