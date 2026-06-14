/**
 * 招聘流程自动流转服务测试 - PRD G38 #11
 *   - checkN2Skip: 3 cases
 *   - checkDoubleASkip: 5 cases
 *   - shouldAutoAdvance: 6 cases
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  applicationStageRecord: {
    findFirst: jest.fn(),
    findMany: jest.fn(),
  },
  processStageLink: {
    findMany: jest.fn(),
    findUnique: jest.fn(),
  },
  candidate: {
    findUnique: jest.fn(),
  },
  entryCondition: {
    findUnique: jest.fn(),
  },
}

jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const { checkN2Skip, checkDoubleASkip, shouldAutoAdvance } = await import(
  '../recruitment-auto-advance.service.js'
)

describe('checkN2Skip', () => {
  beforeEach(() => jest.clearAllMocks())

  it('returns pass:true for N+2 candidate (has recommenderName)', async () => {
    mockPrisma.processStageLink.findMany.mockResolvedValue([])
    mockPrisma.candidate.findUnique.mockResolvedValue({ id: 'c1', recommenderName: '上级' })
    const result = await checkN2Skip('c1', 'p1')
    expect(result.pass).toBe(true)
  })

  it('returns pass:false for non-N+2 candidate', async () => {
    mockPrisma.processStageLink.findMany.mockResolvedValue([])
    mockPrisma.candidate.findUnique.mockResolvedValue({ id: 'c1', recommenderName: null })
    const result = await checkN2Skip('c1', 'p1')
    expect(result.pass).toBe(false)
  })

  it('returns pass:false if candidate not found', async () => {
    mockPrisma.processStageLink.findMany.mockResolvedValue([])
    mockPrisma.candidate.findUnique.mockResolvedValue(null)
    const result = await checkN2Skip('c1', 'p1')
    expect(result.pass).toBe(false)
  })
})

describe('checkDoubleASkip', () => {
  beforeEach(() => jest.clearAllMocks())

  it('returns pass:true for same-dept 2 evaluators both pass', async () => {
    mockPrisma.applicationStageRecord.findFirst.mockResolvedValue({
      applicationId: 'a1',
      linkId: 'l1',
      stage: { stageType: 'EVALUATE' },
    })
    mockPrisma.applicationStageRecord.findMany.mockResolvedValue([
      { toStatus: 'PASS', decider: { departmentId: 'd1', department: { name: '技术部' } } },
      { toStatus: 'PASS', decider: { departmentId: 'd1', department: { name: '技术部' } } },
    ])
    const result = await checkDoubleASkip('c1')
    expect(result.pass).toBe(true)
    expect(result.decision).toBe('PASS')
  })

  it('returns pass:true for same-dept 2 evaluators both fail', async () => {
    mockPrisma.applicationStageRecord.findFirst.mockResolvedValue({
      applicationId: 'a1',
      linkId: 'l1',
      stage: { stageType: 'EVALUATE' },
    })
    mockPrisma.applicationStageRecord.findMany.mockResolvedValue([
      { toStatus: 'FAIL', decider: { departmentId: 'd1', department: { name: '技术部' } } },
      { toStatus: 'FAIL', decider: { departmentId: 'd1', department: { name: '技术部' } } },
    ])
    const result = await checkDoubleASkip('c1')
    expect(result.pass).toBe(true)
    expect(result.decision).toBe('FAIL')
  })

  it('returns pass:false for different departments', async () => {
    mockPrisma.applicationStageRecord.findFirst.mockResolvedValue({
      applicationId: 'a1',
      linkId: 'l1',
      stage: { stageType: 'EVALUATE' },
    })
    mockPrisma.applicationStageRecord.findMany.mockResolvedValue([
      { toStatus: 'PASS', decider: { departmentId: 'd1', department: { name: '技术部' } } },
      { toStatus: 'PASS', decider: { departmentId: 'd2', department: { name: '产品部' } } },
    ])
    const result = await checkDoubleASkip('c1')
    expect(result.pass).toBe(false)
    expect(result.reason).toContain('非同一部门')
  })

  it('returns pass:false for 1 evaluator', async () => {
    mockPrisma.applicationStageRecord.findFirst.mockResolvedValue({
      applicationId: 'a1',
      linkId: 'l1',
      stage: { stageType: 'EVALUATE' },
    })
    mockPrisma.applicationStageRecord.findMany.mockResolvedValue([
      { toStatus: 'PASS', decider: { departmentId: 'd1', department: { name: '技术部' } } },
    ])
    const result = await checkDoubleASkip('c1')
    expect(result.pass).toBe(false)
    expect(result.reason).toContain('需 2 人')
  })

  it('returns pass:false for no recent record', async () => {
    mockPrisma.applicationStageRecord.findFirst.mockResolvedValue(null)
    const result = await checkDoubleASkip('c1')
    expect(result.pass).toBe(false)
  })

  it('returns pass:false for excluded department (客服直播中心)', async () => {
    mockPrisma.applicationStageRecord.findFirst.mockResolvedValue({
      applicationId: 'a1',
      linkId: 'l1',
      stage: { stageType: 'EVALUATE' },
    })
    mockPrisma.applicationStageRecord.findMany.mockResolvedValue([
      { toStatus: 'PASS', decider: { departmentId: 'd1', department: { name: '客服直播中心' } } },
      { toStatus: 'PASS', decider: { departmentId: 'd1', department: { name: '客服直播中心' } } },
    ])
    const result = await checkDoubleASkip('c1')
    expect(result.pass).toBe(false)
    expect(result.reason).toContain('不在双 A 开放名单')
  })

  it('returns pass:false for inconsistent decisions', async () => {
    mockPrisma.applicationStageRecord.findFirst.mockResolvedValue({
      applicationId: 'a1',
      linkId: 'l1',
      stage: { stageType: 'EVALUATE' },
    })
    mockPrisma.applicationStageRecord.findMany.mockResolvedValue([
      { toStatus: 'PASS', decider: { departmentId: 'd1', department: { name: '技术部' } } },
      { toStatus: 'FAIL', decider: { departmentId: 'd1', department: { name: '技术部' } } },
    ])
    const result = await checkDoubleASkip('c1')
    expect(result.pass).toBe(false)
    expect(result.reason).toContain('不一致')
  })
})

describe('shouldAutoAdvance', () => {
  beforeEach(() => jest.clearAllMocks())

  it('returns shouldAdvance:false for no rule', async () => {
    const result = await shouldAutoAdvance({ rule: null }, 'c1', {})
    expect(result.shouldAdvance).toBe(false)
  })

  it('returns shouldAdvance:false for NONE type', async () => {
    const result = await shouldAutoAdvance({ rule: { autoAdvanceType: 'NONE' } }, 'c1', {})
    expect(result.shouldAdvance).toBe(false)
  })

  it('IGNORE_NEXT returns shouldAdvance:true', async () => {
    const result = await shouldAutoAdvance(
      { rule: { autoAdvanceType: 'IGNORE_NEXT' } },
      'c1',
      {},
    )
    expect(result.shouldAdvance).toBe(true)
  })

  it('N1_ALL_PASS returns shouldAdvance:true if context.n1Status.allPass', async () => {
    const result = await shouldAutoAdvance(
      { rule: { autoAdvanceType: 'N1_ALL_PASS' } },
      'c1',
      { n1Status: { allPass: true } },
    )
    expect(result.shouldAdvance).toBe(true)
  })

  it('N1_ALL_PASS returns shouldAdvance:false if no context', async () => {
    const result = await shouldAutoAdvance(
      { rule: { autoAdvanceType: 'N1_ALL_PASS' } },
      'c1',
      {},
    )
    expect(result.shouldAdvance).toBe(false)
  })

  it('DELAYED timing returns shouldAdvance:false (cron handles)', async () => {
    const result = await shouldAutoAdvance(
      { rule: { autoAdvanceType: 'IGNORE_NEXT', autoAdvanceTiming: 'DELAYED' } },
      'c1',
      {},
    )
    expect(result.shouldAdvance).toBe(false)
    expect(result.reason).toContain('delayed')
  })

  it('NONE timing returns shouldAdvance:false', async () => {
    const result = await shouldAutoAdvance(
      { rule: { autoAdvanceType: 'IGNORE_NEXT', autoAdvanceTiming: 'NONE' } },
      'c1',
      {},
    )
    expect(result.shouldAdvance).toBe(false)
    expect(result.reason).toContain('timing disabled')
  })

  it('unknown autoAdvanceType returns shouldAdvance:false', async () => {
    const result = await shouldAutoAdvance(
      { rule: { autoAdvanceType: 'UNKNOWN_TYPE' } },
      'c1',
      {},
    )
    expect(result.shouldAdvance).toBe(false)
    expect(result.reason).toContain('unknown')
  })
})