/**
 * 候选人倒序推荐服务测试 - PRD G11
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals'

const mockPrisma = {
  candidate: {
    findMany: jest.fn(),
  },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  rankCandidates,
  buildRecommendationQuery,
  computeRecommendationScore,
  getRecommendations,
} = await import('../candidate-recommendation.service.js')

describe('candidate-recommendation', () => {
  beforeEach(() => {
    mockPrisma.candidate.findMany.mockReset()
  })

  it('rankCandidates 按 score 倒序', () => {
    const list = [
      { id: '1', score: 50, lastActiveAt: new Date() },
      { id: '2', score: 90, lastActiveAt: new Date() },
      { id: '3', score: 70, lastActiveAt: new Date() },
    ]
    const ranked = rankCandidates(list, { sortBy: 'score' })
    expect(ranked.map(c => c.id)).toEqual(['2', '3', '1'])
  })

  it('rankCandidates 按 lastActiveAt 倒序', () => {
    const now = Date.now()
    const list = [
      { id: '1', score: 50, lastActiveAt: new Date(now - 86400000 * 3) },
      { id: '2', score: 50, lastActiveAt: new Date(now) },
      { id: '3', score: 50, lastActiveAt: new Date(now - 86400000) },
    ]
    const ranked = rankCandidates(list, { sortBy: 'lastActiveAt' })
    expect(ranked.map(c => c.id)).toEqual(['2', '3', '1'])
  })

  it('rankCandidates 综合分 (composite = score*0.7 + activity*0.3)', () => {
    const now = Date.now()
    const list = [
      { id: '1', score: 100, lastActiveAt: new Date(now - 86400000 * 365) }, // 1 年前
      { id: '2', score: 60,  lastActiveAt: new Date(now) },                    // 刚活跃
    ]
    const ranked = rankCandidates(list, { sortBy: 'composite' })
    // id=1: 100*0.7 + 0 * 0.3 = 70
    // id=2: 60*0.7 + 100 * 0.3 = 42 + 30 = 72
    expect(ranked[0].id).toBe('2')
  })

  it('rankCandidates 默认按 composite', () => {
    const list = [{ id: '1', score: 50, lastActiveAt: new Date() }]
    const ranked = rankCandidates(list, {})
    expect(ranked[0].id).toBe('1')
  })

  it('rankCandidates 空数组返回空', () => {
    expect(rankCandidates([], {})).toEqual([])
  })

  it('buildRecommendationQuery 包含 candidateStatus=ACTIVE', () => {
    const q = buildRecommendationQuery({ positionId: 'p1' })
    expect(q.where.candidateStatus).toBe('ACTIVE')
  })

  it('computeRecommendationScore 0-100 区间', () => {
    const score = computeRecommendationScore({ matchScore: 50, lastActiveDaysAgo: 0 })
    expect(score).toBeGreaterThan(0)
    expect(score).toBeLessThanOrEqual(100)
  })

  it('rankCandidates limit 截断', () => {
    const list = Array.from({ length: 100 }, (_, i) => ({
      id: `${i}`, score: i, lastActiveAt: new Date()
    }))
    const ranked = rankCandidates(list, { limit: 10 })
    expect(ranked).toHaveLength(10)
  })
})
