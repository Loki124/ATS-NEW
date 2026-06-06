/**
 * 候选人阶段进入条件测试 - PRD G10 + G1.5
 *
 * 复用 recruitment-condition.service 的 evaluator
 * 测试 buildCandidateContext + evaluateCandidateForStage 包装
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  candidate: { findUnique: jest.fn() },
  application: { findMany: jest.fn(), findUnique: jest.fn() },
  entryCondition: { findUnique: jest.fn() },
  processStageLink: { findFirst: jest.fn() },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

// 同时 mock 评估器,确保隔离
jest.unstable_mockModule('../recruitment-condition.service.js', () => ({
  evaluateConditionTree: jest.fn((items, matchType, ctx) => {
    // 简化: 全部 items 视为通过
    return { passed: true, failedItems: [] }
  }),
  buildFailedPrompt: jest.fn(() => '未满足条件'),
}))

const {
  buildCandidateContext,
  evaluateCandidateForStage,
  evaluateCandidateForStages,
  checkStageTransitionAllowed,
} = await import('../candidate-condition.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

const fakeCandidate = {
  id: 'c-1', name: '张三', age: 28, gender: 'M',
  marriage: 'NO', highestEducation: 'BACHELOR', firstEducation: 'BACHELOR',
  currentCompany: 'Acme', currentPosition: 'Engineer', workYears: 5,
  email: 'a@b.com', phone: '12345', source: 'BOSS',
}

describe('candidate-condition: buildCandidateContext', () => {
  it('无 applicationId → 只取 candidate 字段, stageStatuses 为空', async () => {
    mockPrisma.candidate.findUnique.mockResolvedValue(fakeCandidate)
    const ctx = await buildCandidateContext('c-1')
    expect(ctx.candidate).toMatchObject({
      age: 28, gender: 'M', highestEducation: 'BACHELOR',
    })
    expect(ctx.stageStatuses).toEqual({})
  })

  it('有 applicationId → 收集所有 application 的阶段状态', async () => {
    mockPrisma.candidate.findUnique.mockResolvedValue(fakeCandidate)
    mockPrisma.application.findMany.mockResolvedValue([
      { id: 'a-1', currentStageId: 'stage-A', currentStageStatus: 'PASS' },
      { id: 'a-2', currentStageId: 'stage-B', currentStageStatus: 'PENDING' },
    ])
    const ctx = await buildCandidateContext('c-1', 'a-1')
    expect(ctx.stageStatuses).toEqual({ 'stage-A': 'PASS', 'stage-B': 'PENDING' })
  })

  it('候选人不存在 → 抛错', async () => {
    mockPrisma.candidate.findUnique.mockResolvedValue(null)
    await expect(buildCandidateContext('c-x')).rejects.toThrow(/候选人不存在/)
  })
})

describe('candidate-condition: evaluateCandidateForStage', () => {
  const fakeCond = {
    id: 'cond-1',
    isActive: true,
    matchType: 'ALL',
    items: [{ id: 'i-1', field: 'age', operator: 'GT', value: 18 }],
  }

  it('inactive 条件默认放行', async () => {
    mockPrisma.entryCondition.findUnique.mockResolvedValue({ ...fakeCond, isActive: false })
    const r = await evaluateCandidateForStage('c-1', 'cond-1')
    expect(r.passed).toBe(true)
    expect(r.skipped).toBe('INACTIVE')
  })

  it('条件不存在 → 抛错', async () => {
    mockPrisma.entryCondition.findUnique.mockResolvedValue(null)
    await expect(evaluateCandidateForStage('c-1', 'cond-x')).rejects.toThrow(/进入条件不存在/)
  })

  it('构造 context 并调 evaluator', async () => {
    mockPrisma.entryCondition.findUnique.mockResolvedValue(fakeCond)
    mockPrisma.candidate.findUnique.mockResolvedValue(fakeCandidate)
    mockPrisma.application.findMany.mockResolvedValue([])
    const r = await evaluateCandidateForStage('c-1', 'cond-1', 'a-1')
    expect(r.passed).toBe(true)
    expect(r.context.candidate.age).toBe(28)
  })
})

describe('candidate-condition: evaluateCandidateForStages', () => {
  it('批量评估多条', async () => {
    mockPrisma.entryCondition.findUnique.mockResolvedValue({
      id: 'cond-x', isActive: true, matchType: 'ALL', items: [],
    })
    mockPrisma.candidate.findUnique.mockResolvedValue(fakeCandidate)
    mockPrisma.application.findMany.mockResolvedValue([])
    const results = await evaluateCandidateForStages('c-1', ['c-1', 'c-2'])
    expect(results).toHaveLength(2)
    expect(results[0].entryConditionId).toBe('c-1')
  })
})

describe('candidate-condition: checkStageTransitionAllowed', () => {
  it('application 不存在 → 抛错', async () => {
    mockPrisma.application.findUnique.mockResolvedValue(null)
    await expect(checkStageTransitionAllowed('a-x')).rejects.toThrow(/申请不存在/)
  })

  it('无 link 上的 entryConditionId → 默认放行', async () => {
    mockPrisma.application.findUnique.mockResolvedValue({
      id: 'a-1', candidateId: 'c-1', processId: 'p-1', currentStageId: null,
    })
    const r = await checkStageTransitionAllowed('a-1')
    expect(r.allowed).toBe(true)
  })

  it('显式传 entryConditionId → 评估', async () => {
    mockPrisma.application.findUnique.mockResolvedValue({
      id: 'a-1', candidateId: 'c-1', processId: 'p-1', currentStageId: 's-1',
    })
    mockPrisma.entryCondition.findUnique.mockResolvedValue({
      id: 'cond-1', isActive: true, matchType: 'ALL', items: [],
    })
    mockPrisma.candidate.findUnique.mockResolvedValue(fakeCandidate)
    mockPrisma.application.findMany.mockResolvedValue([])
    const r = await checkStageTransitionAllowed('a-1', 'cond-1')
    expect(r.allowed).toBe(true)
  })

  it('从 link 取 entryConditionId → 评估', async () => {
    mockPrisma.application.findUnique.mockResolvedValue({
      id: 'a-1', candidateId: 'c-1', processId: 'p-1', currentStageId: 's-1',
    })
    mockPrisma.processStageLink.findFirst.mockResolvedValue({ entryConditionId: 'cond-1' })
    mockPrisma.entryCondition.findUnique.mockResolvedValue({
      id: 'cond-1', isActive: true, matchType: 'ALL', items: [],
    })
    mockPrisma.candidate.findUnique.mockResolvedValue(fakeCandidate)
    mockPrisma.application.findMany.mockResolvedValue([])
    const r = await checkStageTransitionAllowed('a-1')
    expect(r.allowed).toBe(true)
    expect(mockPrisma.processStageLink.findFirst).toHaveBeenCalledWith({
      where: { processId: 'p-1', stageId: 's-1' },
    })
  })
})
