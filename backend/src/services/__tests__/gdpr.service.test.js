/**
 * GDPR 服务测试 - Plan K #7
 *
 * 覆盖:
 *   - anonymizeUser: 3 cases (user PII, candidate PII, no user)
 *   - exportUserData: 2 cases (success, not found)
 *   - hardDeleteExpired: 1 case (7 tables)
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  user: { findUnique: jest.fn(), update: jest.fn(), deleteMany: jest.fn() },
  candidate: { findMany: jest.fn(), update: jest.fn(), deleteMany: jest.fn() },
  department: { deleteMany: jest.fn() },
  demand: { deleteMany: jest.fn() },
  position: { deleteMany: jest.fn() },
  offer: { deleteMany: jest.fn() },
  onboarding: { deleteMany: jest.fn() },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const { anonymizeUser, exportUserData, hardDeleteExpired } = await import('../gdpr.service.js')

describe('anonymizeUser', () => {
  beforeEach(() => jest.clearAllMocks())

  it('anonymizes user PII and marks deletedAt', async () => {
    mockPrisma.user.findUnique.mockResolvedValueOnce({
      id: 'u1', phone: '13800138000', email: 'a@b.com',
    })
    mockPrisma.candidate.findMany.mockResolvedValueOnce([])

    const result = await anonymizeUser('u1')

    expect(mockPrisma.user.update).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { id: 'u1' },
        data: expect.objectContaining({
          phone: null,
          email: null,
          deletedAt: expect.any(Date),
        }),
      }),
    )
    expect(result.count).toBe(1)
  })

  it('anonymizes assigned candidates (keeps them in flow, just masks PII)', async () => {
    mockPrisma.user.findUnique.mockResolvedValueOnce({ id: 'u1' })
    mockPrisma.candidate.findMany.mockResolvedValueOnce([
      { id: 'c1', phone: '13987654321', email: 'x@y.com' },
    ])

    await anonymizeUser('u1')

    expect(mockPrisma.candidate.update).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { id: 'c1' },
        data: expect.objectContaining({
          phone: '139****4321',     // masked, not null
          email: 'x***@y.com',
        }),
      }),
    )
    // candidate 不应被标记 deletedAt (还在流程中)
    const updateCall = mockPrisma.candidate.update.mock.calls[0][0]
    expect(updateCall.data.deletedAt).toBeUndefined()
  })

  it('handles no user found gracefully', async () => {
    mockPrisma.user.findUnique.mockResolvedValueOnce(null)
    mockPrisma.candidate.findMany.mockResolvedValueOnce([])

    const result = await anonymizeUser('u999')
    expect(result.count).toBe(0)
  })
})

describe('exportUserData', () => {
  beforeEach(() => jest.clearAllMocks())

  it('exports user + permissions + relations as JSON', async () => {
    mockPrisma.user.findUnique.mockResolvedValueOnce({
      id: 'u1', username: 'admin', realName: 'Admin', email: 'a@b.com',
      phone: '13800138000', roleType: 'SUPER_ADMIN', departmentId: 'd1',
      status: 'ACTIVE', createdAt: new Date(),
      userRoles: [{ role: { code: 'SUPER_ADMIN' }, grantedAt: new Date() }],
      userDataPermissions: [],
      userMous: [{ mou: { code: 'MOU1', name: 'Test' }, scope: 'GLOBAL' }],
      userContainers: [],
      decidedStageRecords: [{}, {}],
    })
    mockPrisma.candidate.findMany.mockResolvedValueOnce([
      { id: 'c1', name: '张三', candidateStatus: 'PENDING' },
    ])

    const data = await exportUserData('u1')

    expect(data.gdprArticle).toContain('Art. 20')
    expect(data.fingerprint).toMatch(/^[a-f0-9]{16}$/)
    expect(data.user.id).toBe('u1')
    expect(data.permissions).toHaveLength(1)
    expect(data.mous).toHaveLength(1)
    expect(data.decisions).toBe(2)
    expect(data.candidatesAsAssigner).toHaveLength(1)
  })

  it('returns error for non-existent user', async () => {
    mockPrisma.user.findUnique.mockResolvedValueOnce(null)
    const data = await exportUserData('u999')
    expect(data.error).toBe('user not found')
  })
})

describe('hardDeleteExpired', () => {
  beforeEach(() => jest.clearAllMocks())

  it('deletes expired soft-deleted records from all 7 core tables', async () => {
    mockPrisma.user.deleteMany.mockResolvedValueOnce({ count: 3 })
    mockPrisma.department.deleteMany.mockResolvedValueOnce({ count: 0 })
    mockPrisma.demand.deleteMany.mockResolvedValueOnce({ count: 1 })
    mockPrisma.position.deleteMany.mockResolvedValueOnce({ count: 0 })
    mockPrisma.candidate.deleteMany.mockResolvedValueOnce({ count: 5 })
    mockPrisma.offer.deleteMany.mockResolvedValueOnce({ count: 0 })
    mockPrisma.onboarding.deleteMany.mockResolvedValueOnce({ count: 0 })

    const result = await hardDeleteExpired(mockPrisma)

    expect(result.deleted.user).toBe(3)
    expect(result.deleted.demand).toBe(1)
    expect(result.deleted.candidate).toBe(5)
    expect(result.cutoff).toBeInstanceOf(Date)
  })
})