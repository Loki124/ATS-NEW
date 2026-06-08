// G11 - 倒序推荐
// 综合排序 = matchScore * 0.7 + 活跃度因子 * 0.3
// 活跃度因子 = max(0, 1 - lastActiveDaysAgo/365) * 100  // 1 年前归零
//             然后按 0-30 的权重折算

import { prisma } from '../app.js'

const DAY_MS = 86400000

export function computeRecommendationScore(candidate) {
  const scorePart = (candidate.matchScore || 0) * 0.7
  const daysAgo = candidate.lastActiveDaysAgo ?? 9999
  // 活跃度因子: 0~1 折算 0~30 分 (0.3 权重)
  const activityPart = Math.max(0, 1 - daysAgo / 365) * 30
  return Math.round(scorePart + activityPart)
}

export function buildRecommendationQuery({ positionId, keyword, limit = 20 } = {}) {
  const where = { candidateStatus: 'ACTIVE' }
  if (positionId) where.applications = { some: { positionId } }
  if (keyword) {
    where.OR = [
      { name: { contains: keyword } },
      { code: { contains: keyword } },
    ]
  }
  return { where, take: limit }
}

export function rankCandidates(candidates, options = {}) {
  const { sortBy = 'composite', limit } = options
  if (!candidates?.length) return []
  let ranked = [...candidates]
  if (sortBy === 'score') {
    ranked.sort((a, b) => (b.score || 0) - (a.score || 0))
  } else if (sortBy === 'lastActiveAt') {
    ranked.sort((a, b) => new Date(b.lastActiveAt) - new Date(a.lastActiveAt))
  } else {
    // composite - 按 computeRecommendationScore 综合分排序
    ranked.sort((a, b) => {
      const sa = computeRecommendationScore({
        matchScore: a.matchScore ?? a.score,
        lastActiveDaysAgo: a.lastActiveDaysAgo ?? daysSince(a.lastActiveAt),
      })
      const sb = computeRecommendationScore({
        matchScore: b.matchScore ?? b.score,
        lastActiveDaysAgo: b.lastActiveDaysAgo ?? daysSince(b.lastActiveAt),
      })
      return sb - sa
    })
  }
  if (limit) ranked = ranked.slice(0, limit)
  return ranked
}

function daysSince(date) {
  if (!date) return 9999
  return Math.floor((Date.now() - new Date(date).getTime()) / DAY_MS)
}

export async function getRecommendations({ userId, positionId, keyword, sortBy, limit = 20 }) {
  const q = buildRecommendationQuery({ positionId, keyword, limit })
  const list = await prisma.candidate.findMany({
    ...q,
    include: {
      resumes: { orderBy: { updatedAt: 'desc' }, take: 1 },
      applications: { include: { position: true } },
    },
  })
  // 计算每条 score + daysAgo
  const enriched = list.map(c => {
    const lastResume = c.resumes?.[0]
    const lastActiveAt = lastResume?.updatedAt || c.updatedAt
    const lastActiveDaysAgo = Math.floor((Date.now() - new Date(lastActiveAt).getTime()) / DAY_MS)
    const score = computeRecommendationScore({ matchScore: 50, lastActiveDaysAgo })
    return { ...c, score, lastActiveAt, lastActiveDaysAgo }
  })
  return rankCandidates(enriched, { sortBy, limit })
}
