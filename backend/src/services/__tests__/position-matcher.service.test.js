/**
 * position-matcher 服务测试 - PRD G31
 * 待入职智能分配职位 (候选人 ↔ 职位双向推荐)
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  position: {
    findMany: jest.fn(),
    findUnique: jest.fn(),
  },
  candidate: {
    findMany: jest.fn(),
    findUnique: jest.fn(),
  },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  computeMatchScore,
  buildMatchReason,
  rankPositions,
  recommendPositionsForCandidate,
  recommendCandidatesForPosition,
  MATCH_WEIGHTS,
} = await import('../position-matcher.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('position-matcher: 权重配置', () => {
  it('MATCH_WEIGHTS 总和 = 1.0', () => {
    const sum = Object.values(MATCH_WEIGHTS).reduce((a, b) => a + b, 0)
    expect(sum).toBeCloseTo(1.0, 2)
  })
})

describe('position-matcher: computeMatchScore', () => {
  it('完全匹配 → 接近 1.0', () => {
    const score = computeMatchScore({
      candidate: { highestEducation: '本科', workExperience: '5年', expectedPosition: '工程师', householdLocation: '北京' },
      position: { education: '本科', minExperience: 3, maxExperience: 10, title: '工程师', workLocation: '北京' },
    })
    expect(score).toBeGreaterThan(0.8)
  })

  it('学历不符扣分', () => {
    const score = computeMatchScore({
      candidate: { highestEducation: '大专' },
      position: { education: '本科', minExperience: 0, maxExperience: 99, title: 'X', workLocation: 'X' },
    })
    expect(score).toBeLessThan(0.8)
  })

  it('经验超出上限适度扣分 (资深仍给 0.5 部分分)', () => {
    const score = computeMatchScore({
      candidate: { workExperience: '15年' },
      position: { education: '不限', minExperience: 1, maxExperience: 5, title: 'X', workLocation: 'X' },
    })
    // 学历/职位/地点都通过, 经验 0.5 部分分 → 0.25 + 0.15 + 0.25 + 0.2 = 0.85
    expect(score).toBeLessThan(0.9)
    expect(score).toBeGreaterThan(0.8)
  })

  it('经验低于下限直接 0 分 (无部分分)', () => {
    const score = computeMatchScore({
      candidate: { workExperience: '0年' },
      position: { education: '本科', minExperience: 5, maxExperience: 10, title: 'X', workLocation: 'X' },
    })
    // 学历+经验0+职位+地点 = 0.7
    expect(score).toBeLessThan(0.8)
  })
})

describe('position-matcher: buildMatchReason', () => {
  it('列出匹配维度', () => {
    const reason = buildMatchReason({ education: true, experience: true, position: true, location: false })
    expect(reason).toContain('学历')
    expect(reason).toContain('地点不匹配')
  })
})

describe('position-matcher: rankPositions', () => {
  it('按 score 倒序', () => {
    const list = [
      { id: '1', score: 0.5 },
      { id: '2', score: 0.9 },
      { id: '3', score: 0.7 },
    ]
    const ranked = rankPositions(list)
    expect(ranked.map(p => p.id)).toEqual(['2', '3', '1'])
  })
})

describe('position-matcher: recommendPositionsForCandidate', () => {
  it('返回 top N 职位 (按匹配分倒序)', async () => {
    mockPrisma.candidate.findUnique.mockResolvedValueOnce({
      id: 'c1', highestEducation: '本科', workExperience: '5年', expectedPosition: '工程师', householdLocation: '北京',
    })
    mockPrisma.position.findMany.mockResolvedValueOnce([
      { id: 'p1', title: '工程师', education: '本科', minExperience: 3, maxExperience: 10, workLocation: '北京' },
      { id: 'p2', title: '设计师', education: '大专', minExperience: 0, maxExperience: 5, workLocation: '上海' },
    ])
    const recs = await recommendPositionsForCandidate('c1', { limit: 2 })
    expect(recs).toHaveLength(2)
    expect(recs[0].score).toBeGreaterThanOrEqual(recs[1].score)
  })
})

describe('position-matcher: recommendCandidatesForPosition (反向)', () => {
  it('返回 top N 候选人', async () => {
    mockPrisma.position.findUnique.mockResolvedValueOnce({
      id: 'p1', title: '工程师', education: '本科', minExperience: 3, maxExperience: 10, workLocation: '北京',
    })
    mockPrisma.candidate.findMany.mockResolvedValueOnce([
      { id: 'c1', highestEducation: '本科', workExperience: '5年', expectedPosition: '工程师', householdLocation: '北京' },
      { id: 'c2', highestEducation: '中专', workExperience: '1年', expectedPosition: '助理', householdLocation: '深圳' },
    ])
    const recs = await recommendCandidatesForPosition('p1', { limit: 5 })
    expect(recs).toHaveLength(2)
    expect(recs[0].score).toBeGreaterThanOrEqual(recs[1].score)
  })
})
