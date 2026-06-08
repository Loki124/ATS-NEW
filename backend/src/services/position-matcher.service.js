/**
 * position-matcher.service.js - PRD G31
 * 待入职智能分配职位 (候选人 ↔ 职位双向推荐)
 *
 * 评分维度 (MATCH_WEIGHTS, 总和 = 1.0):
 *   - education  学历  0.25
 *   - experience 经验  0.30
 *   - position   职位意向 0.25
 *   - location   地点  0.20
 */

import { prisma } from '../app.js'

export const MATCH_WEIGHTS = {
  education: 0.25,
  experience: 0.30,
  position: 0.25,
  location: 0.20,
}

const EDU_ORDER = { '不限': 0, '中专': 1, '大专': 2, '本科': 3, '硕士': 4, '博士': 5 }

function parseYears(s) {
  if (!s) return 0
  const m = String(s).match(/(\d+)/)
  return m ? parseInt(m[1]) : 0
}

/**
 * 计算候选人-职位匹配分 (0-1)
 * @param {Object} params
 * @param {Object} params.candidate 候选人 (含 highestEducation, workExperience, expectedPosition, householdLocation)
 * @param {Object} params.position  职位 (含 education, minExperience, maxExperience, title, workLocation)
 * @returns {number} 0-1 的匹配分
 */
export function computeMatchScore({ candidate = {}, position = {} }) {
  let score = 0
  const detail = {}

  // 学历
  const candEdu = EDU_ORDER[candidate.highestEducation] || 0
  const posEdu = EDU_ORDER[position.education] || 0
  detail.education = posEdu === 0 || candEdu >= posEdu
  if (detail.education) score += MATCH_WEIGHTS.education

  // 经验
  const candYears = parseYears(candidate.workExperience)
  const minExp = position.minExperience || 0
  const maxExp = position.maxExperience || 99
  const inRange = candYears >= minExp && candYears <= maxExp
  detail.experience = inRange
  if (inRange) {
    score += MATCH_WEIGHTS.experience
  } else if (candYears > maxExp) {
    // 资深适度扣分
    score += MATCH_WEIGHTS.experience * 0.5
  }

  // 职位意向
  const exp = candidate.expectedPosition || ''
  const ttl = position.title || ''
  detail.position = !exp || !ttl || exp.includes(ttl) || ttl.includes(exp)
  if (detail.position) score += MATCH_WEIGHTS.position

  // 地点
  const loc = candidate.householdLocation || ''
  const workLoc = position.workLocation || ''
  detail.location = !loc || !workLoc || loc === workLoc
  if (detail.location) score += MATCH_WEIGHTS.location

  return Math.round(score * 100) / 100
}

/**
 * 把 4 维度布尔 detail 转成可读原因字符串
 * @param {Object} detail { education, experience, position, location }
 * @returns {string}
 */
export function buildMatchReason(detail) {
  const parts = []
  parts.push(detail.education ? '✅ 学历匹配' : '❌ 学历不符')
  parts.push(detail.experience ? '✅ 经验匹配' : '⚠️ 经验偏离')
  parts.push(detail.position ? '✅ 职位意向匹配' : '⚠️ 职位意向偏离')
  parts.push(detail.location ? '✅ 地点匹配' : '⚠️ 地点不匹配')
  return parts.join(' / ')
}

/**
 * 按 score 倒序排序
 * @param {Array<{score?: number}>} positions
 * @returns {Array}
 */
export function rankPositions(positions) {
  return [...positions].sort((a, b) => (b.score || 0) - (a.score || 0))
}

/**
 * 给定候选人, 推荐 top N 职位
 * @param {string} candidateId
 * @param {Object} opts { limit }
 * @returns {Promise<Array>}
 */
export async function recommendPositionsForCandidate(candidateId, { limit = 10 } = {}) {
  const candidate = await prisma.candidate.findUnique({ where: { id: candidateId } })
  if (!candidate) return []
  const positions = await prisma.position.findMany({
    where: { status: 'ACTIVE' },
    take: 50,
  })
  const scored = positions.map(p => {
    const score = computeMatchScore({ candidate, position: p })
    // 各维度布尔供 reason
    const candEdu = EDU_ORDER[candidate.highestEducation] || 0
    const posEdu = EDU_ORDER[p.education] || 0
    const candYears = parseYears(candidate.workExperience)
    const minExp = p.minExperience || 0
    const maxExp = p.maxExperience || 99
    const detail = {
      education: posEdu === 0 || candEdu >= posEdu,
      experience: candYears >= minExp && candYears <= maxExp,
      position: !candidate.expectedPosition || !p.title ||
        candidate.expectedPosition.includes(p.title) || p.title.includes(candidate.expectedPosition),
      location: !candidate.householdLocation || !p.workLocation ||
        candidate.householdLocation === p.workLocation,
    }
    return { ...p, score, matchReason: buildMatchReason(detail) }
  })
  return rankPositions(scored).slice(0, limit)
}

/**
 * 给定职位, 推荐 top N 候选人
 * @param {string} positionId
 * @param {Object} opts { limit }
 * @returns {Promise<Array>}
 */
export async function recommendCandidatesForPosition(positionId, { limit = 10 } = {}) {
  const position = await prisma.position.findUnique({ where: { id: positionId } })
  if (!position) return []
  const candidates = await prisma.candidate.findMany({
    where: { candidateStatus: 'ACTIVE' },
    take: 50,
  })
  const scored = candidates.map(c => {
    const score = computeMatchScore({ candidate: c, position })
    return { ...c, score }
  })
  return rankPositions(scored).slice(0, limit)
}
