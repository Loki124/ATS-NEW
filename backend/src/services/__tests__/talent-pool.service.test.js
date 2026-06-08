/**
 * talent-pool 服务测试 - PRD G32
 * 6 子库完整 CRUD + 跨池移动 (审计)
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  candidate: {
    count: jest.fn(),
    findMany: jest.fn(),
    update: jest.fn(),
  },
  operationRecord: {
    create: jest.fn(),
  },
  $transaction: jest.fn(),
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  TALENT_POOL_TYPES,
  listPoolStats,
  listCandidatesInPool,
  moveCandidateToPool,
  countByPool,
} = await import('../talent-pool.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('talent-pool: 6 子库定义', () => {
  it('包含 6 个子库', () => {
    expect(Object.keys(TALENT_POOL_TYPES)).toHaveLength(6)
  })

  it('包含所有 PRD G32 子库码', () => {
    const codes = Object.keys(TALENT_POOL_TYPES)
    expect(codes).toEqual(
      expect.arrayContaining(['PASSIVE', 'ACTIVE', 'HIRED', 'REJECTED', 'BLACKLIST', 'GENERAL'])
    )
  })
})

describe('talent-pool: listPoolStats', () => {
  it('聚合 6 个子库', async () => {
    mockPrisma.candidate.count.mockResolvedValue(10)
    const stats = await listPoolStats()
    expect(Object.keys(stats)).toHaveLength(6)
    expect(stats.PASSIVE).toBe(10)
    expect(stats.ACTIVE).toBe(10)
  })

  it('countByPool 别名返回一致结果', async () => {
    mockPrisma.candidate.count.mockResolvedValue(5)
    const a = await countByPool()
    const b = await listPoolStats()
    expect(a).toEqual(b)
  })
})

describe('talent-pool: listCandidatesInPool', () => {
  it('分页查询子库候选人', async () => {
    mockPrisma.candidate.findMany.mockResolvedValueOnce([{ id: 'c1' }, { id: 'c2' }])
    const list = await listCandidatesInPool('PASSIVE', { page: 1, pageSize: 20 })
    expect(list).toHaveLength(2)
    expect(mockPrisma.candidate.findMany).toHaveBeenCalledWith(
      expect.objectContaining({
        where: expect.objectContaining({ archiveToPool: 'PASSIVE' }),
        skip: 0,
        take: 20,
      })
    )
  })

  it('page 2 时 skip 正确', async () => {
    mockPrisma.candidate.findMany.mockResolvedValueOnce([{ id: 'c3' }])
    await listCandidatesInPool('ACTIVE', { page: 2, pageSize: 10 })
    expect(mockPrisma.candidate.findMany).toHaveBeenCalledWith(
      expect.objectContaining({ skip: 10, take: 10 })
    )
  })
})

describe('talent-pool: moveCandidateToPool', () => {
  it('更新候选人的 archiveToPool + 写审计', async () => {
    const tx = {
      candidate: { update: jest.fn().mockResolvedValue({ id: 'c1', archiveToPool: 'BLACKLIST' }) },
      operationRecord: { create: jest.fn().mockResolvedValue({}) },
    }
    mockPrisma.$transaction.mockImplementationOnce(async (fn) => fn(tx))
    const r = await moveCandidateToPool('c1', 'BLACKLIST', '品德问题', 'u1')
    expect(r.id).toBe('c1')
    expect(tx.candidate.update).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { id: 'c1' },
        data: expect.objectContaining({ archiveToPool: 'BLACKLIST', candidateStatus: 'ARCHIVED' }),
      })
    )
    expect(tx.operationRecord.create).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          action: 'MOVE_TO_POOL',
          resource: 'Candidate',
          resourceId: 'c1',
          operatorId: 'u1',
        }),
      })
    )
  })

  it('非法 pool 抛错', async () => {
    await expect(moveCandidateToPool('c1', 'INVALID', 'r', 'u1'))
      .rejects.toThrow('Unknown pool')
  })

  it('审计中包含 fromPool / toPool / reason', async () => {
    const tx = {
      candidate: { update: jest.fn().mockResolvedValue({ id: 'c1', archiveToPool: 'GENERAL' }) },
      operationRecord: { create: jest.fn().mockResolvedValue({}) },
    }
    mockPrisma.$transaction.mockImplementationOnce(async (fn) => fn(tx))
    await moveCandidateToPool('c1', 'GENERAL', '重新归档', 'u1')
    expect(tx.operationRecord.create).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          details: expect.objectContaining({ toPool: 'GENERAL', reason: '重新归档' }),
        }),
      })
    )
  })
})
