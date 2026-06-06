/**
 * 职位状态机测试 - PRD G5
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  application: {
    count: jest.fn(),
    updateMany: jest.fn(),
  },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  POSITION_STATUSES,
  canTransitionPosition,
  hasActiveCandidates,
  closePosition,
  isRecruiting,
  canAcceptNewCandidates,
} = await import('../position-state-machine.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('position-state-machine: 3 状态常量', () => {
  it('包含 3 个状态', () => {
    expect(Object.keys(POSITION_STATUSES)).toHaveLength(3)
    expect(POSITION_STATUSES.RECRUITING).toBe('RECRUITING')
    expect(POSITION_STATUSES.PAUSED).toBe('PAUSED')
    expect(POSITION_STATUSES.CLOSED).toBe('CLOSED')
  })
})

describe('position-state-machine: canTransitionPosition', () => {
  it('RECRUITING → PAUSED 合法', () => {
    expect(canTransitionPosition('RECRUITING', 'PAUSED')).toBe(true)
  })
  it('RECRUITING → CLOSED 合法', () => {
    expect(canTransitionPosition('RECRUITING', 'CLOSED')).toBe(true)
  })
  it('PAUSED → RECRUITING 合法 (恢复)', () => {
    expect(canTransitionPosition('PAUSED', 'RECRUITING')).toBe(true)
  })
  it('PAUSED → CLOSED 合法', () => {
    expect(canTransitionPosition('PAUSED', 'CLOSED')).toBe(true)
  })
  it('CLOSED → RECRUITING 合法 (reopen)', () => {
    expect(canTransitionPosition('CLOSED', 'RECRUITING')).toBe(true)
  })
  it('RECRUITING → RECRUITING 非法 (自循环)', () => {
    expect(canTransitionPosition('RECRUITING', 'RECRUITING')).toBe(false)
  })
  it('CLOSED → PAUSED 非法 (不能从关闭直接到暂停)', () => {
    expect(canTransitionPosition('CLOSED', 'PAUSED')).toBe(false)
  })
  it('CLOSED → CLOSED 非法', () => {
    expect(canTransitionPosition('CLOSED', 'CLOSED')).toBe(false)
  })
  it('未知状态 → false', () => {
    expect(canTransitionPosition('UNKNOWN', 'PAUSED')).toBe(false)
  })
})

describe('position-state-machine: hasActiveCandidates', () => {
  it('有 active 候选人 → true', async () => {
    mockPrisma.application.count.mockResolvedValue(3)
    expect(await hasActiveCandidates('pos-1')).toBe(true)
    expect(mockPrisma.application.count).toHaveBeenCalledWith({
      where: { positionId: 'pos-1', applicationStatus: 'ACTIVE' },
    })
  })
  it('无 active 候选人 → false', async () => {
    mockPrisma.application.count.mockResolvedValue(0)
    expect(await hasActiveCandidates('pos-1')).toBe(false)
  })
})

describe('position-state-machine: closePosition (候选人存在保护)', () => {
  it('有 active 候选人 + 不 forceClose → 抛 400 ACTIVE_CANDIDATES_EXIST', async () => {
    mockPrisma.application.count.mockResolvedValue(5)
    await expect(closePosition('pos-1')).rejects.toMatchObject({
      statusCode: 400,
      code: 'ACTIVE_CANDIDATES_EXIST',
    })
  })

  it('无 active 候选人 → 不抛错,不调 updateMany', async () => {
    mockPrisma.application.count.mockResolvedValue(0)
    await closePosition('pos-1')
    expect(mockPrisma.application.updateMany).not.toHaveBeenCalled()
  })

  it('有 active + forceClose=true → 自动归档所有 active 候选人', async () => {
    mockPrisma.application.count.mockResolvedValue(3)
    mockPrisma.application.updateMany.mockResolvedValue({ count: 3 })
    await closePosition('pos-1', { forceClose: true })
    expect(mockPrisma.application.updateMany).toHaveBeenCalledWith({
      where: { positionId: 'pos-1', applicationStatus: 'ACTIVE' },
      data: expect.objectContaining({
        applicationStatus: 'ARCHIVED',
        archiveReason: '职位强制关闭',
        archivedAt: expect.any(Date),
      }),
    })
  })
})

describe('position-state-machine: isRecruiting / canAcceptNewCandidates', () => {
  it('isRecruiting - RECRUITING 状态 true', () => {
    expect(isRecruiting({ positionStatus: 'RECRUITING' })).toBe(true)
  })
  it('isRecruiting - PAUSED 状态 false', () => {
    expect(isRecruiting({ positionStatus: 'PAUSED' })).toBe(false)
  })
  it('isRecruiting - CLOSED 状态 false', () => {
    expect(isRecruiting({ positionStatus: 'CLOSED' })).toBe(false)
  })

  it('canAcceptNewCandidates - 只 RECRUITING 可接收新候选人', () => {
    expect(canAcceptNewCandidates('RECRUITING')).toBe(true)
    expect(canAcceptNewCandidates('PAUSED')).toBe(false)
    expect(canAcceptNewCandidates('CLOSED')).toBe(false)
  })
})
