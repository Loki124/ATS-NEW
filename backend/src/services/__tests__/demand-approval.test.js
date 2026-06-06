/**
 * 需求审批 service 测试
 *
 * 覆盖: submitForApproval / approveDemand / rejectDemand / cancelApproval
 */

import { jest } from '@jest/globals'

// Mock prisma (含 $transaction 透传)
const txMock = {
  demand: { update: jest.fn(), findUnique: jest.fn() },
  demandApprovalStep: {
    deleteMany: jest.fn(),
    create: jest.fn(),
    findFirst: jest.fn(),
    update: jest.fn(),
    updateMany: jest.fn(),
  },
  operationRecord: { create: jest.fn().mockResolvedValue({}) },
  demandStatusHistory: { create: jest.fn().mockResolvedValue({}) },
}

const mockPrisma = {
  demand: { findUnique: jest.fn() },
  demandApprovalStep: { findMany: jest.fn() },
  operationRecord: { create: jest.fn().mockResolvedValue({}) },
  demandStatusHistory: { create: jest.fn().mockResolvedValue({}) },
  notificationQueue: { create: jest.fn().mockResolvedValue({}) },
  demandApprovalConfig: { findMany: jest.fn().mockResolvedValue([]) },
  $transaction: jest.fn((cb) => cb(txMock)),
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const { submitForApproval, approveDemand, rejectDemand, cancelApproval } =
  await import('../demand-approval.service.js')

beforeEach(() => {
  jest.clearAllMocks()
  mockPrisma.$transaction.mockImplementation((cb) => cb(txMock))
})

// 工具: 构造 demand mock
function makeDemand(overrides = {}) {
  return {
    id: 'demand-1',
    creatorId: 'user-creator',
    managerId: 'user-manager',
    approvalStatus: 'NOT_STARTED',
    demandStatus: 'DRAFT',
    department: {
      id: 'dept-1',
      hrbpId: 'user-hrbp',
      manager2Id: 'user-manager-super',
    },
    ...overrides,
  }
}

describe('demand-approval: submitForApproval', () => {
  it('草稿 + NOT_STARTED 审批 → 创建 3 步 + 切 NOT_STARTED+PENDING', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue(makeDemand())
    txMock.demandApprovalStep.create.mockResolvedValue({ id: 'step-1' })
    txMock.demand.update.mockResolvedValue({ id: 'demand-1', approvalStatus: 'PENDING', demandStatus: 'NOT_STARTED' })

    const result = await submitForApproval('demand-1', 'user-creator')

    // 应清掉旧 steps (重发)
    expect(txMock.demandApprovalStep.deleteMany).toHaveBeenCalledWith({ where: { demandId: 'demand-1' } })
    // 应创建 3 步: HRBP, MANAGER, MANAGER_SUPER
    expect(txMock.demandApprovalStep.create).toHaveBeenCalledTimes(3)
    // 第一步 stepIndex=0 status=PENDING
    expect(txMock.demandApprovalStep.create).toHaveBeenNthCalledWith(1, expect.objectContaining({
      data: expect.objectContaining({
        stepIndex: 0,
        approverRole: 'HRBP',
        approverId: 'user-hrbp',
        status: 'PENDING',
      }),
    }))
    // 第二步 stepIndex=1 status=WAITING
    expect(txMock.demandApprovalStep.create).toHaveBeenNthCalledWith(2, expect.objectContaining({
      data: expect.objectContaining({
        stepIndex: 1,
        approverRole: 'MANAGER',
        status: 'WAITING',
      }),
    }))
    // 切需求状态
    expect(txMock.demand.update).toHaveBeenCalledWith({
      where: { id: 'demand-1' },
      data: { approvalStatus: 'PENDING', demandStatus: 'NOT_STARTED' },
    })
  })

  it('需求不存在 → 抛 404', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue(null)
    await expect(submitForApproval('demand-x', 'user-1')).rejects.toMatchObject({ statusCode: 404 })
  })

  it('需求已审批中 (PENDING) → 抛 400', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue(makeDemand({ approvalStatus: 'PENDING' }))
    await expect(submitForApproval('demand-1', 'user-1')).rejects.toMatchObject({ statusCode: 400 })
  })

  it('需求不是 DRAFT 状态 (如 IN_PROGRESS) → 抛 400', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue(makeDemand({ demandStatus: 'IN_PROGRESS' }))
    await expect(submitForApproval('demand-1', 'user-1')).rejects.toMatchObject({ statusCode: 400 })
  })

  it('部门无 HRBP → 抛 400', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue(makeDemand({
      department: { id: 'dept-1', hrbpId: null, manager2Id: 'user-sup' },
    }))
    await expect(submitForApproval('demand-1', 'user-1')).rejects.toMatchObject({ statusCode: 400 })
  })

  it('需求无 managerId → 抛 400', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue(makeDemand({ managerId: null }))
    await expect(submitForApproval('demand-1', 'user-1')).rejects.toMatchObject({ statusCode: 400 })
  })
})

describe('demand-approval: approveDemand', () => {
  it('有下一步 → 激活下一步,需求状态不变', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue({
      ...makeDemand({ approvalStatus: 'PENDING' }),
      approvalSteps: [
        { id: 'step-0', stepIndex: 0, status: 'PENDING', approverId: 'user-1' },
        { id: 'step-1', stepIndex: 1, status: 'WAITING', approverId: 'user-2' },
      ],
    })
    txMock.demandApprovalStep.findFirst.mockResolvedValue({ id: 'step-1' })
    txMock.demand.findUnique.mockResolvedValueOnce({ id: 'demand-1', approvalSteps: [] })

    await approveDemand('demand-1', 'user-1', 'OK')

    expect(txMock.demandApprovalStep.update).toHaveBeenCalledWith({
      where: { id: 'step-0' },
      data: expect.objectContaining({ status: 'APPROVED', approverId: 'user-1', comment: 'OK' }),
    })
    expect(txMock.demandApprovalStep.update).toHaveBeenCalledWith({
      where: { id: 'step-1' },
      data: { status: 'PENDING' },
    })
  })

  it('最后一步 → 全部 APPROVED,需求 → APPROVED+IN_PROGRESS', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue({
      ...makeDemand({ approvalStatus: 'PENDING' }),
      approvalSteps: [
        { id: 'step-0', stepIndex: 0, status: 'PENDING', approverId: 'user-1' },
      ],
    })
    txMock.demandApprovalStep.findFirst.mockResolvedValue(null) // 无下一步
    txMock.demand.update.mockResolvedValue({ id: 'demand-1' })
    txMock.demand.findUnique.mockResolvedValue({ id: 'demand-1', approvalStatus: 'APPROVED', approvalSteps: [] })

    await approveDemand('demand-1', 'user-1', 'final')

    expect(txMock.demand.update).toHaveBeenCalledWith({
      where: { id: 'demand-1' },
      data: { approvalStatus: 'APPROVED', demandStatus: 'IN_PROGRESS' },
    })
  })

  it('非当前步骤审批人 → 抛 403', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue({
      ...makeDemand({ approvalStatus: 'PENDING' }),
      approvalSteps: [
        { id: 'step-0', stepIndex: 0, status: 'PENDING', approverId: 'user-correct' },
      ],
    })
    await expect(approveDemand('demand-1', 'user-wrong', 'x')).rejects.toMatchObject({ statusCode: 403 })
  })

  it('非 PENDING 审批状态 → 抛 400', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue(makeDemand({ approvalStatus: 'NOT_STARTED' }))
    await expect(approveDemand('demand-1', 'user-1')).rejects.toMatchObject({ statusCode: 400 })
  })
})

describe('demand-approval: rejectDemand', () => {
  it('需要 reason → 抛 400 if empty', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue(makeDemand({ approvalStatus: 'PENDING' }))
    await expect(rejectDemand('demand-1', 'user-1', '')).rejects.toMatchObject({ statusCode: 400 })
  })

  it('拒绝 → 当前步 REJECTED + 后续 SKIPPED + 需求回 DRAFT', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue({
      ...makeDemand({ approvalStatus: 'PENDING' }),
      approvalSteps: [
        { id: 'step-0', stepIndex: 0, status: 'PENDING', approverId: 'user-1' },
        { id: 'step-1', stepIndex: 1, status: 'WAITING', approverId: 'user-2' },
      ],
    })
    txMock.demand.update.mockResolvedValue({ id: 'demand-1' })

    await rejectDemand('demand-1', 'user-1', '不通过')

    expect(txMock.demandApprovalStep.update).toHaveBeenCalledWith({
      where: { id: 'step-0' },
      data: expect.objectContaining({ status: 'REJECTED', comment: '不通过' }),
    })
    expect(txMock.demandApprovalStep.updateMany).toHaveBeenCalledWith({
      where: { demandId: 'demand-1', status: 'WAITING' },
      data: { status: 'SKIPPED' },
    })
    expect(txMock.demand.update).toHaveBeenCalledWith({
      where: { id: 'demand-1' },
      data: { approvalStatus: 'REJECTED', demandStatus: 'DRAFT' },
      include: { approvalSteps: true },
    })
  })
})

describe('demand-approval: cancelApproval', () => {
  it('非 PENDING 状态 → 抛 400', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue(makeDemand({ approvalStatus: 'NOT_STARTED' }))
    await expect(cancelApproval('demand-1', 'user-1')).rejects.toMatchObject({ statusCode: 400 })
  })

  it('非创建人撤销 → 抛 403', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue(makeDemand({ approvalStatus: 'PENDING', creatorId: 'user-creator' }))
    await expect(cancelApproval('demand-1', 'user-other')).rejects.toMatchObject({ statusCode: 403 })
  })

  it('创建人撤销 → 所有 PENDING/WAITING 步骤 SKIPPED + 需求 CANCELLED+DRAFT', async () => {
    mockPrisma.demand.findUnique.mockResolvedValue(makeDemand({ approvalStatus: 'PENDING' }))
    txMock.demand.update.mockResolvedValue({ id: 'demand-1' })

    await cancelApproval('demand-1', 'user-creator')

    expect(txMock.demandApprovalStep.updateMany).toHaveBeenCalledWith({
      where: { demandId: 'demand-1', status: { in: ['PENDING', 'WAITING'] } },
      data: { status: 'SKIPPED' },
    })
    expect(txMock.demand.update).toHaveBeenCalledWith({
      where: { id: 'demand-1' },
      data: { approvalStatus: 'CANCELLED', demandStatus: 'DRAFT' },
    })
  })
})
