/**
 * 邀约服务测试 - PRD G14 + G15 + G16
 */

import { jest } from '@jest/globals'

// tx 透传给 callback
const txMock = {
  invitationRecord: {
    findUnique: jest.fn(),
    update: jest.fn(),
    findMany: jest.fn(),
  },
}
const mockPrisma = {
  invitationRecord: {
    findUnique: jest.fn(),
    update: jest.fn(),
    findMany: jest.fn(),
  },
  $transaction: jest.fn((cb) => cb(txMock)),
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  INVITATION_STATUSES,
  CLAIM_TIMEOUT_HOURS,
  MAX_CLAIM_ATTEMPTS,
  canTransitionInvitation,
  isClaimable,
  canContactCandidate,
  isTerminalInvitation,
} = await import('../invitation-state-machine.service.js')

const {
  enterClaimPool,
  claimInvitation,
  markContacted,
  markResult,
  intervene,
  terminate,
  processExpiredInvitations,
} = await import('../invitation.service.js')

beforeEach(() => {
  jest.clearAllMocks()
  mockPrisma.$transaction.mockImplementation((cb) => cb(txMock))
})

describe('invitation-state-machine: 8 状态常量', () => {
  it('包含 8 个状态', () => {
    expect(Object.keys(INVITATION_STATUSES)).toHaveLength(8)
  })
  it('CLAIM_TIMEOUT_HOURS = 48', () => {
    expect(CLAIM_TIMEOUT_HOURS).toBe(48)
  })
  it('MAX_CLAIM_ATTEMPTS = 3', () => {
    expect(MAX_CLAIM_ATTEMPTS).toBe(3)
  })
})

describe('invitation-state-machine: canTransitionInvitation', () => {
  it('PENDING_ASSIGN → PENDING_CLAIM 合法', () => {
    expect(canTransitionInvitation('PENDING_ASSIGN', 'PENDING_CLAIM')).toBe(true)
  })
  it('PENDING_CLAIM → PENDING_INVITE 合法 (抢单成功)', () => {
    expect(canTransitionInvitation('PENDING_CLAIM', 'PENDING_INVITE')).toBe(true)
  })
  it('PENDING_INVITE → INVITING 合法 (开始联系)', () => {
    expect(canTransitionInvitation('PENDING_INVITE', 'INVITING')).toBe(true)
  })
  it('INVITING → SUCCESS 合法', () => {
    expect(canTransitionInvitation('INVITING', 'SUCCESS')).toBe(true)
  })
  it('INVITING → FAILED 合法', () => {
    expect(canTransitionInvitation('INVITING', 'FAILED')).toBe(true)
  })
  it('FAILED → PENDING_CLAIM 合法 (重新入池)', () => {
    expect(canTransitionInvitation('FAILED', 'PENDING_CLAIM')).toBe(true)
  })
  it('SUCCESS 是终态', () => {
    expect(isTerminalInvitation('SUCCESS')).toBe(true)
    expect(canTransitionInvitation('SUCCESS', 'INVITING')).toBe(false)
  })
  it('TERMINATED 是终态', () => {
    expect(isTerminalInvitation('TERMINATED')).toBe(true)
  })
  it('PENDING_CLAIM → SUCCESS 非法 (不能跳过邀约)', () => {
    expect(canTransitionInvitation('PENDING_CLAIM', 'SUCCESS')).toBe(false)
  })
})

describe('invitation-state-machine: isClaimable / canContactCandidate', () => {
  it('isClaimable 只 PENDING_CLAIM 可抢', () => {
    expect(isClaimable('PENDING_CLAIM')).toBe(true)
    expect(isClaimable('PENDING_ASSIGN')).toBe(false)
    expect(isClaimable('PENDING_INVITE')).toBe(false)
  })
  it('canContactCandidate PENDING_INVITE / INVITING 可联系', () => {
    expect(canContactCandidate('PENDING_INVITE')).toBe(true)
    expect(canContactCandidate('INVITING')).toBe(true)
    expect(canContactCandidate('PENDING_CLAIM')).toBe(false)
  })
})

describe('invitation.service: enterClaimPool', () => {
  it('PENDING_ASSIGN → PENDING_CLAIM, 设置 48h 倒计时', async () => {
    txMock.invitationRecord.findUnique.mockResolvedValue({
      id: 'i-1', invitationStatus: 'PENDING_ASSIGN', note: '原 note',
    })
    txMock.invitationRecord.update.mockResolvedValue({ id: 'i-1', invitationStatus: 'PENDING_CLAIM' })

    await enterClaimPool('i-1', { reason: '自动入池' })

    expect(txMock.invitationRecord.update).toHaveBeenCalledWith({
      where: { id: 'i-1' },
      data: expect.objectContaining({
        invitationStatus: 'PENDING_CLAIM',
        note: '入池: 自动入池',
        timeoutAt: expect.any(Date),
      }),
    })
  })

  it('非 PENDING_ASSIGN → 抛 400', async () => {
    txMock.invitationRecord.findUnique.mockResolvedValue({
      id: 'i-1', invitationStatus: 'PENDING_CLAIM',
    })
    await expect(enterClaimPool('i-1')).rejects.toMatchObject({ statusCode: 400 })
  })
})

describe('invitation.service: claimInvitation', () => {
  it('PENDING_CLAIM → PENDING_INVITE, 记录 claimedBy', async () => {
    txMock.invitationRecord.findUnique.mockResolvedValue({
      id: 'i-1', invitationStatus: 'PENDING_CLAIM', timeoutAt: new Date(Date.now() + 86400000),
    })
    txMock.invitationRecord.update.mockResolvedValue({ id: 'i-1' })
    await claimInvitation('i-1', 'user-x', 'X')
    expect(txMock.invitationRecord.update).toHaveBeenCalledWith({
      where: { id: 'i-1' },
      data: expect.objectContaining({
        invitationStatus: 'PENDING_INVITE',
        claimedById: 'user-x',
        claimedByName: 'X',
        inviterId: 'user-x',
        inviterName: 'X',
      }),
    })
  })

  it('已超时 → 抛 400', async () => {
    txMock.invitationRecord.findUnique.mockResolvedValue({
      id: 'i-1', invitationStatus: 'PENDING_CLAIM', timeoutAt: new Date(Date.now() - 1000),
    })
    await expect(claimInvitation('i-1', 'u', 'n')).rejects.toMatchObject({ statusCode: 400 })
  })

  it('非 PENDING_CLAIM 状态 → 抛 400', async () => {
    txMock.invitationRecord.findUnique.mockResolvedValue({
      id: 'i-1', invitationStatus: 'INVITING', timeoutAt: new Date(Date.now() + 86400000),
    })
    await expect(claimInvitation('i-1', 'u', 'n')).rejects.toMatchObject({ statusCode: 400 })
  })
})

describe('invitation.service: markContacted', () => {
  it('PENDING_INVITE → INVITING, contactAttempts + 1', async () => {
    txMock.invitationRecord.findUnique.mockResolvedValue({
      id: 'i-1', invitationStatus: 'PENDING_INVITE',
    })
    txMock.invitationRecord.update.mockResolvedValue({ id: 'i-1' })
    await markContacted('i-1', { note: '已联系' })
    expect(txMock.invitationRecord.update).toHaveBeenCalledWith({
      where: { id: 'i-1' },
      data: expect.objectContaining({
        invitationStatus: 'INVITING',
        contactAttempts: { increment: 1 },
        note: '已联系',
      }),
    })
  })
})

describe('invitation.service: markResult', () => {
  it('INVITING → SUCCESS', async () => {
    txMock.invitationRecord.findUnique.mockResolvedValue({ id: 'i-1', invitationStatus: 'INVITING' })
    txMock.invitationRecord.update.mockResolvedValue({ id: 'i-1' })
    await markResult('i-1', { success: true, reason: '同意入职' })
    expect(txMock.invitationRecord.update).toHaveBeenCalledWith({
      where: { id: 'i-1' },
      data: expect.objectContaining({
        invitationStatus: 'SUCCESS',
        resultStatus: 'PASS',
        resultReason: '同意入职',
      }),
    })
  })

  it('INVITING → FAILED', async () => {
    txMock.invitationRecord.findUnique.mockResolvedValue({ id: 'i-1', invitationStatus: 'INVITING' })
    txMock.invitationRecord.update.mockResolvedValue({ id: 'i-1' })
    await markResult('i-1', { success: false, reason: '不接受' })
    expect(txMock.invitationRecord.update).toHaveBeenCalledWith({
      where: { id: 'i-1' },
      data: expect.objectContaining({ invitationStatus: 'FAILED', resultStatus: 'FAIL' }),
    })
  })

  it('SUCCESS 终态 → 抛 400', async () => {
    txMock.invitationRecord.findUnique.mockResolvedValue({ id: 'i-1', invitationStatus: 'SUCCESS' })
    await expect(markResult('i-1', { success: true })).rejects.toMatchObject({ statusCode: 400 })
  })
})

describe('invitation.service: intervene / terminate', () => {
  it('PENDING_INVITE → INTERVENED, interventionCount + 1', async () => {
    txMock.invitationRecord.findUnique.mockResolvedValue({ id: 'i-1', invitationStatus: 'PENDING_INVITE' })
    txMock.invitationRecord.update.mockResolvedValue({ id: 'i-1' })
    await intervene('i-1', { operatorId: 'admin-1', operatorName: '管理员', reason: '需要上级介入' })
    expect(txMock.invitationRecord.update).toHaveBeenCalledWith({
      where: { id: 'i-1' },
      data: expect.objectContaining({
        invitationStatus: 'INTERVENED',
        interventionCount: { increment: 1 },
        lastInterventionBy: '管理员',
        inviterId: 'admin-1',
      }),
    })
  })

  it('SUCCESS 终态不可干预', async () => {
    txMock.invitationRecord.findUnique.mockResolvedValue({ id: 'i-1', invitationStatus: 'SUCCESS' })
    await expect(intervene('i-1', { operatorId: 'a', operatorName: 'A' })).rejects.toMatchObject({ statusCode: 400 })
  })

  it('terminate 任意状态可终止', async () => {
    mockPrisma.invitationRecord.update.mockResolvedValue({ id: 'i-1' })
    await terminate('i-1', { reason: 'test', operatorId: 'u' })
    expect(mockPrisma.invitationRecord.update).toHaveBeenCalledWith({
      where: { id: 'i-1' },
      data: expect.objectContaining({ invitationStatus: 'TERMINATED' }),
    })
  })
})

describe('invitation.service: processExpiredInvitations', () => {
  it('PENDING_CLAIM 超时 attempts < 3 → 重入池 24h', async () => {
    mockPrisma.invitationRecord.findMany.mockResolvedValue([
      { id: 'i-1', invitationStatus: 'PENDING_CLAIM', contactAttempts: 0 },
    ])
    mockPrisma.invitationRecord.update.mockResolvedValue({ id: 'i-1' })

    const stats = await processExpiredInvitations()
    expect(stats.requeued).toBe(1)
    expect(stats.terminated).toBe(0)
    expect(mockPrisma.invitationRecord.update).toHaveBeenCalledWith({
      where: { id: 'i-1' },
      data: expect.objectContaining({
        invitationStatus: 'PENDING_CLAIM',
        contactAttempts: 1,
        timeoutAt: expect.any(Date),
      }),
    })
  })

  it('PENDING_CLAIM 超时 attempts >= 3 → TERMINATED', async () => {
    mockPrisma.invitationRecord.findMany.mockResolvedValue([
      { id: 'i-1', invitationStatus: 'PENDING_CLAIM', contactAttempts: 2 },
    ])
    mockPrisma.invitationRecord.update.mockResolvedValue({ id: 'i-1' })

    const stats = await processExpiredInvitations()
    expect(stats.terminated).toBe(1)
    expect(mockPrisma.invitationRecord.update).toHaveBeenCalledWith({
      where: { id: 'i-1' },
      data: expect.objectContaining({
        invitationStatus: 'TERMINATED',
        contactAttempts: 3,
      }),
    })
  })

  it('PENDING_INVITE 超时 → escalate (interventionCount + 1)', async () => {
    mockPrisma.invitationRecord.findMany.mockResolvedValue([
      { id: 'i-1', invitationStatus: 'PENDING_INVITE', contactAttempts: 0 },
    ])
    mockPrisma.invitationRecord.update.mockResolvedValue({ id: 'i-1' })

    const stats = await processExpiredInvitations()
    expect(stats.escalated).toBe(1)
    expect(mockPrisma.invitationRecord.update).toHaveBeenCalledWith({
      where: { id: 'i-1' },
      data: expect.objectContaining({
        interventionCount: { increment: 1 },
        lastInterventionBy: 'ESCALATION_SYSTEM',
      }),
    })
  })

  it('无过期记录 → 全部 0', async () => {
    mockPrisma.invitationRecord.findMany.mockResolvedValue([])
    const stats = await processExpiredInvitations()
    expect(stats.processed).toBe(0)
    expect(stats.requeued).toBe(0)
    expect(stats.escalated).toBe(0)
    expect(stats.terminated).toBe(0)
  })
})
