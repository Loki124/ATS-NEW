/**
 * 评分规则服务测试 - PRD G39
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  scoringRule: {
    findUnique: jest.fn(),
    findMany: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
    count: jest.fn(),
  },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

// Mock evaluator: 模拟具体 condition 行为
// cond-age: 命中 if age > 25
// cond-edu: 命中 if highestEducation === '博士'
jest.unstable_mockModule('../recruitment-condition.service.js', () => ({
  evaluateConditionTree: jest.fn((items, matchType, ctx) => {
    const field = items?.[0]?.field
    const op = items?.[0]?.operator
    const val = items?.[0]?.value
    const actual = ctx.candidate?.[field]
    let passed = false
    if (op === 'GT' && actual > val) passed = true
    if (op === 'EQ' && actual === val) passed = true
    return { passed, failedItems: passed ? [] : items || [] }
  }),
}))

const {
  SCORING_RULE_TYPES,
  evaluateCandidateForRule,
  listScoringRules,
  createScoringRule,
} = await import('../scoring-rule.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('scoring-rule: SCORING_RULE_TYPES', () => {
  it('包含 3 种规则类型', () => {
    expect(Object.keys(SCORING_RULE_TYPES)).toHaveLength(3)
    expect(SCORING_RULE_TYPES.SUM_MATCHED).toBe('SUM_MATCHED')
    expect(SCORING_RULE_TYPES.WEIGHTED_AVERAGE).toBe('WEIGHTED_AVERAGE')
    expect(SCORING_RULE_TYPES.THRESHOLD).toBe('THRESHOLD')
  })
})

describe('scoring-rule: evaluateCandidateForRule', () => {
  const fakeRule = (overrides = {}) => ({
    id: 'rule-1',
    status: 'ACTIVE',
    ruleType: 'SUM_MATCHED',
    conditions: [
      {
        id: 'cond-age',
        name: '年龄条件',
        matchType: 'ALL',
        items: [{ field: 'age', operator: 'GT', value: 25 }],
      },
      {
        id: 'cond-edu',
        name: '学历条件',
        matchType: 'ALL',
        items: [{ field: 'highestEducation', operator: 'EQ', value: '博士' }],
      },
    ],
    results: [
      { conditionId: 'cond-age', matchedScore: 50, unmatchedScore: 0 },
      { conditionId: 'cond-edu', matchedScore: 60, unmatchedScore: 0 },
    ],
    ...overrides,
  })

  it('INACTIVE 规则默认不通过 (skipped)', async () => {
    mockPrisma.scoringRule.findUnique.mockResolvedValue(fakeRule({ status: 'INACTIVE' }))
    const r = await evaluateCandidateForRule('rule-1', { candidate: { age: 30 } })
    expect(r.passed).toBe(false)
    expect(r.skipped).toBe('INACTIVE')
  })

  it('SUM_MATCHED 全部命中 → 高分 + 通过', async () => {
    mockPrisma.scoringRule.findUnique.mockResolvedValue(fakeRule())
    const r = await evaluateCandidateForRule('rule-1', {
      candidate: { age: 30, highestEducation: '博士' },
    })
    expect(r.totalScore).toBe(50 + 60)
    expect(r.passed).toBe(true)
    expect(r.details.every((d) => d.passed)).toBe(true)
  })

  it('SUM_MATCHED 部分命中 → 中等分 (>= 60 通过)', async () => {
    mockPrisma.scoringRule.findUnique.mockResolvedValue(fakeRule())
    const r = await evaluateCandidateForRule('rule-1', {
      candidate: { age: 30, highestEducation: '本科' },
    })
    // 命中 cond-age (50), 未命中 cond-edu (0)
    expect(r.totalScore).toBe(50)
    expect(r.passed).toBe(false)
  })

  it('SUM_MATCHED 全不命中 → 0 分', async () => {
    mockPrisma.scoringRule.findUnique.mockResolvedValue(fakeRule())
    const r = await evaluateCandidateForRule('rule-1', {
      candidate: { age: 20, highestEducation: '本科' },
    })
    expect(r.totalScore).toBe(0)
    expect(r.passed).toBe(false)
  })

  it('THRESHOLD 规则: 80 分阈值', async () => {
    mockPrisma.scoringRule.findUnique.mockResolvedValue(fakeRule({ ruleType: 'THRESHOLD' }))
    const r = await evaluateCandidateForRule('rule-1', {
      candidate: { age: 30, highestEducation: '博士' },
    })
    expect(r.totalScore).toBe(110)
    expect(r.passed).toBe(true)
  })

  it('WEIGHTED_AVERAGE: 50% 命中率通过', async () => {
    mockPrisma.scoringRule.findUnique.mockResolvedValue(fakeRule({ ruleType: 'WEIGHTED_AVERAGE' }))
    const r = await evaluateCandidateForRule('rule-1', {
      candidate: { age: 30, highestEducation: '本科' },
    })
    // 命中 1/2 = 50% ≥ 50% → 通过
    expect(r.passed).toBe(true)
  })

  it('规则不存在 → 抛 404', async () => {
    mockPrisma.scoringRule.findUnique.mockResolvedValue(null)
    await expect(evaluateCandidateForRule('rule-x', {})).rejects.toMatchObject({ statusCode: 404 })
  })
})

describe('scoring-rule: listScoringRules / createScoringRule', () => {
  it('listScoringRules 传 status 过滤', async () => {
    mockPrisma.scoringRule.findMany.mockResolvedValue([])
    mockPrisma.scoringRule.count.mockResolvedValue(0)
    const res = await listScoringRules({ status: 'ACTIVE' })
    expect(res.list).toEqual([])
    expect(mockPrisma.scoringRule.findMany).toHaveBeenCalledWith(
      expect.objectContaining({ where: { status: 'ACTIVE' } }),
    )
  })

  it('createScoringRule 调 prisma.create', async () => {
    mockPrisma.scoringRule.create.mockResolvedValue({ id: 'rule-new', name: 'Test' })
    const r = await createScoringRule({ name: 'Test', code: 'TEST_1', ruleType: 'SUM_MATCHED' })
    expect(mockPrisma.scoringRule.create).toHaveBeenCalledWith(
      expect.objectContaining({ data: expect.objectContaining({ name: 'Test' }) }),
    )
    expect(r.id).toBe('rule-new')
  })
})
