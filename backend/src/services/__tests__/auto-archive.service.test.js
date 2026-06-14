/**
 * auto-archive.service 测试 - PRD G38 #8
 *
 * 覆盖 4 个 ruleType + archiveApplications + runAutoArchiveCheck
 * (9 个用例, mirror invitation.test.js 的 jest.unstable_mockModule 模式)
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  autoArchiveRule: { findMany: jest.fn() },
  candidate:       { findMany: jest.fn() },
  offer:           { findMany: jest.fn() },
  application:     { findMany: jest.fn(), updateMany: jest.fn() },
  applicationStageRecord: { findMany: jest.fn() },
  invitation: { findMany: jest.fn() },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  evaluateRule,
  archiveApplications,
  runAutoArchiveCheck,
} = await import('../auto-archive.service.js')

describe('evaluateRule - INVITE_FAIL', () => {
  beforeEach(() => jest.clearAllMocks())

  it('returns shouldArchive:false when rule disabled', async () => {
    const result = await evaluateRule({ enabled: false, ruleType: 'INVITE_FAIL', config: {} })
    expect(result.shouldArchive).toBe(false)
    expect(result.reason).toContain('disabled')
  })

  it('returns shouldArchive:false when no fail tags in config', async () => {
    const result = await evaluateRule({ enabled: true, ruleType: 'INVITE_FAIL', config: {}, processId: 'p1' })
    expect(result.shouldArchive).toBe(false)
    expect(result.reason).toContain('no fail tags')
  })

  it('returns shouldArchive:true with applicationIds matching failTags', async () => {
    mockPrisma.application.findMany.mockResolvedValueOnce([
      { id: 'a1', invitation: { resultStatus: 'FAILED', resultAt: new Date() } },
      { id: 'a2', invitation: { resultStatus: 'FAILED', resultAt: new Date() } },
      { id: 'a3', invitation: { resultStatus: 'SUCCESS', resultAt: new Date() } }, // 不命中
      { id: 'a4', invitation: null },                                                // 无邀约
    ])
    const result = await evaluateRule({
      enabled: true, ruleType: 'INVITE_FAIL', processId: 'p1',
      config: { failTags: ['FAILED'], maxAttempts: 3, timeWindow: 7 },
    })
    expect(result.shouldArchive).toBe(true)
    expect(result.applicationIds).toEqual(['a1', 'a2'])
  })
})

describe('evaluateRule - OFFER_FAIL', () => {
  beforeEach(() => jest.clearAllMocks())

  it('returns shouldArchive:false when no reject types in config', async () => {
    const result = await evaluateRule({ enabled: true, ruleType: 'OFFER_FAIL', config: {}, processId: 'p1' })
    expect(result.shouldArchive).toBe(false)
    expect(result.reason).toContain('no reject types')
  })

  it('returns shouldArchive:true with dedup applicationIds', async () => {
    mockPrisma.offer.findMany.mockResolvedValueOnce([
      { id: 'o1', applicationId: 'a1' },
      { id: 'o2', applicationId: 'a2' },
      { id: 'o3', applicationId: 'a1' }, // dup applicationId
    ])
    const result = await evaluateRule({
      enabled: true, ruleType: 'OFFER_FAIL', processId: 'p1',
      config: { rejectTypes: ['REJECTED_BY_CANDIDATE'] },
    })
    expect(result.shouldArchive).toBe(true)
    expect(result.applicationIds).toEqual(['a1', 'a2']) // dedup
  })
})

describe('evaluateRule - EVAL_FAIL', () => {
  beforeEach(() => jest.clearAllMocks())

  it('returns shouldArchive:false when stageId or failTags missing', async () => {
    const r1 = await evaluateRule({ enabled: true, ruleType: 'EVAL_FAIL', config: { failTags: ['FAIL'] }, processId: 'p1' })
    expect(r1.shouldArchive).toBe(false)
    expect(r1.reason).toContain('missing stageId')
    const r2 = await evaluateRule({ enabled: true, ruleType: 'EVAL_FAIL', config: { stageId: 's1' }, processId: 'p1' })
    expect(r2.shouldArchive).toBe(false)
  })

  it('returns shouldArchive:true with dedup applicationIds from stageRecords', async () => {
    mockPrisma.applicationStageRecord.findMany.mockResolvedValueOnce([
      { applicationId: 'a1' },
      { applicationId: 'a2' },
      { applicationId: 'a1' }, // dup
    ])
    const result = await evaluateRule({
      enabled: true, ruleType: 'EVAL_FAIL', processId: 'p1',
      config: { stageId: 's1', failTags: ['FAIL'], executeTiming: 'IMMEDIATE' },
    })
    expect(result.shouldArchive).toBe(true)
    expect(result.applicationIds).toEqual(['a1', 'a2'])
  })
})

describe('evaluateRule - TIMEOUT_UNASSIGNED', () => {
  beforeEach(() => jest.clearAllMocks())

  it('returns shouldArchive:true with applicationIds for unassigned candidates', async () => {
    const since = new Date(Date.now() - 8 * 24 * 60 * 60 * 1000) // 8 天前
    mockPrisma.application.findMany.mockResolvedValueOnce([
      { id: 'a1', candidate: { assignedUserId: null, createdAt: since } },
      { id: 'a2', candidate: { assignedUserId: 'u1', createdAt: since } }, // 已认领, 不命中
      { id: 'a3', candidate: { assignedUserId: null, createdAt: new Date() } }, // 太新, 不命中
    ])
    const result = await evaluateRule({
      enabled: true, ruleType: 'TIMEOUT_UNASSIGNED', processId: 'p1',
      config: { timeoutDays: 7 },
    })
    expect(result.shouldArchive).toBe(true)
    expect(result.applicationIds).toEqual(['a1'])
  })
})

describe('evaluateRule - unknown ruleType', () => {
  it('returns shouldArchive:false with reason containing "unknown"', async () => {
    const result = await evaluateRule({ enabled: true, ruleType: 'BOGUS', processId: 'p1' })
    expect(result.shouldArchive).toBe(false)
    expect(result.reason).toContain('unknown')
  })
})

describe('archiveApplications', () => {
  it('returns archivedCount:0 for empty array', async () => {
    const result = await archiveApplications([])
    expect(result.archivedCount).toBe(0)
  })

  it('returns count from updateMany', async () => {
    mockPrisma.application.updateMany.mockResolvedValueOnce({ count: 5 })
    const result = await archiveApplications(['a1', 'a2', 'a3'])
    expect(result.archivedCount).toBe(5)
  })
})

describe('runAutoArchiveCheck', () => {
  it('skips rules with no matches and reports totals', async () => {
    mockPrisma.autoArchiveRule.findMany.mockResolvedValueOnce([
      { id: 'r1', enabled: true, ruleType: 'TIMEOUT_UNASSIGNED', processId: 'p1', config: { timeoutDays: 7 } },
    ])
    mockPrisma.application.findMany.mockResolvedValueOnce([])
    const result = await runAutoArchiveCheck(mockPrisma)
    expect(result.total).toBe(1)
    expect(result.archived).toBe(0)
    expect(result.skipped).toBe(1)
  })

  it('archives matched applicationIds', async () => {
    mockPrisma.autoArchiveRule.findMany.mockResolvedValueOnce([
      { id: 'r1', enabled: true, ruleType: 'OFFER_FAIL', processId: 'p1', config: { rejectTypes: ['REJECTED_BY_CANDIDATE'] } },
    ])
    mockPrisma.offer.findMany.mockResolvedValueOnce([
      { id: 'o1', applicationId: 'a1' },
      { id: 'o2', applicationId: 'a2' },
    ])
    mockPrisma.application.updateMany.mockResolvedValueOnce({ count: 2 })
    const result = await runAutoArchiveCheck(mockPrisma)
    expect(result.total).toBe(1)
    expect(result.archived).toBe(2)
    expect(result.skipped).toBe(0)
  })
})
