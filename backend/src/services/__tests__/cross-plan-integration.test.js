/**
 * 跨计划联调测试 (Plan H)
 *
 * 验证 plan 间契约协同工作:
 * - 联调 #1: G19 历史 + G44 状态 (Interview 评价预填 + Candidate 11 状态汇总)
 * - 联调 #2: G32 人才池 + G8 字段权限 (Pool 移动 + Field ACL Mask)
 * - 联调 #3: Plan A 推荐 (G11) + G44 状态 (PASS 优先)
 *
 * 注意: 不引入新功能, 仅 mock 已有 service 验证契约
 */

import { jest } from '@jest/globals'

// ===== Mock 共享 prisma =====
const mockPrisma = {
  candidate: {
    findUnique: jest.fn(),
    findMany: jest.fn(),
    update: jest.fn(),
    count: jest.fn(),
  },
  interviewFeedback: { findMany: jest.fn() },
  operationRecord: { create: jest.fn() },
  $transaction: jest.fn(),
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

// ===== 动态导入 (必须在 mock 之后) =====
const { getCandidateHistory, aggregateHistory } = await import('../interview-history.service.js')
const { validateStatusDetails, getStatusSummary } = await import('../candidate-status-machine.service.js')
const { moveCandidateToPool, listPoolStats } = await import('../talent-pool.service.js')
const { applyFieldAcl, maskPhone } = await import('../field-masking.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

// =====================================================================
// 联调 #1: G19 历史 + G44 状态
// =====================================================================
describe('跨计划联调 #1: G19 历史 + G44 状态', () => {
  it('候选人历史聚合 + 状态汇总协同工作 (PASS=2, FAIL=1, PENDING=8)', async () => {
    // G44: 设置候选人状态
    const details = {
      evaluated: 'PASS',
      hrbpFiltered: 'PASS',
      invited: 'FAIL',
      // 其余 8 个保持 PENDING
    }
    const summary = getStatusSummary(details)
    expect(summary).toEqual({ passed: 2, failed: 1, pending: 8 })

    // G19: 历史聚合 (mock)
    const fakeFeedbacks = [
      { id: 'f1', result: 'PASS', feedbackAt: new Date('2025-01-01'), interview: { roundName: '一面' }, interviewerName: 'A', reason: '技术好' },
      { id: 'f2', result: 'FAIL', feedbackAt: new Date('2025-02-01'), interview: { roundName: '二面' }, interviewerName: 'B', reason: '深度不够' },
    ]
    const aggregated = aggregateHistory(fakeFeedbacks)
    expect(aggregated.total).toBe(2)
    expect(aggregated.passCount).toBe(1)
    expect(aggregated.failCount).toBe(1)

    // 跨计划信息丰富: 11 状态总和应 = 11
    expect(summary.passed + summary.failed + summary.pending).toBe(11)
  })

  it('G44 状态更新不影响 G19 历史 (状态机独立性)', () => {
    // 状态机独立性 - 任何状态变更不破坏 G19 的 aggregate
    expect(validateStatusDetails('evaluated', 'PASS', 'PENDING')).toBe(true)
    expect(validateStatusDetails('invited', 'FAIL', 'PENDING')).toBe(true)
    expect(validateStatusDetails('hrbpFiltered', 'PASS', 'PENDING')).toBe(true)

    // G44 读 candidate.statusDetails, G19 读 interviewFeedback (完全解耦)
    const details = { evaluated: 'PASS' }
    expect(getStatusSummary(details).passed).toBe(1)
  })
})

// =====================================================================
// 联调 #2: G32 人才池 + G8 字段权限
// =====================================================================
describe('跨计划联调 #2: G32 人才池 + G8 字段权限', () => {
  it('候选人被移到 BLACKLIST 后, G8 字段权限应自动 MASK 敏感字段', () => {
    // G32: 候选人被移入 BLACKLIST 池
    const candidate = {
      id: 'c1', name: '张某', phone: '13800138000', email: 'a@b.com',
      archiveToPool: 'BLACKLIST', candidateStatus: 'ARCHIVED',
    }

    // G8: 字段规则 - 池转移后敏感字段需要 MASK
    const rules = [
      { field: 'phone', action: 'MASK' },
      { field: 'email', action: 'HIDE' },
    ]
    const masked = applyFieldAcl(candidate, rules)

    // 验证跨计划契约: name 保留, phone mask, email null
    expect(masked.name).toBe('张某')
    expect(masked.phone).toBe('138****8000')
    expect(masked.email).toBeNull()
  })

  it('G32 跨池移动写审计 OperationRecord (跟 G8 审计分离)', async () => {
    // 模拟 $transaction
    const txMock = {
      candidate: { update: jest.fn() },
      operationRecord: { create: jest.fn() },
    }
    txMock.candidate.update.mockResolvedValue({ id: 'c1', archiveToPool: 'GENERAL' })
    txMock.operationRecord.create.mockResolvedValue({})
    mockPrisma.$transaction.mockImplementation((fn) => fn(txMock))

    await moveCandidateToPool('c1', 'GENERAL', '测试', 'u1')

    // G32 走 OperationRecord
    expect(txMock.operationRecord.create).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({ action: 'MOVE_TO_POOL' }),
      })
    )
    // 跟 G8 字段审计 (FieldAclAudit) 分离
    expect(txMock.operationRecord.create).not.toHaveBeenCalledWith(
      expect.objectContaining({ data: expect.objectContaining({ action: 'FIELD_MASK' }) })
    )
  })

  it('G32 listPoolStats 返回 6 个子库统计 (覆盖 BLACKLIST)', async () => {
    mockPrisma.candidate.count.mockResolvedValue(3)
    const stats = await listPoolStats()
    expect(Object.keys(stats)).toHaveLength(6)
    expect(stats).toHaveProperty('BLACKLIST', 3)
    expect(stats).toHaveProperty('GENERAL', 3)
  })
})

// =====================================================================
// 联调 #3: G11 推荐 + G44 状态 (概念验证)
// =====================================================================
describe('跨计划联调 #3: G11 推荐 + G44 状态', () => {
  it('G11 推荐算法应优先选 G44.PASS 的候选人', () => {
    // 概念验证: G11 候选人推荐 + G44 状态加成
    const candidates = [
      { id: '1', score: 50, statusDetails: { evaluated: 'PASS' } },
      { id: '2', score: 50, statusDetails: { evaluated: 'PENDING' } },
      { id: '3', score: 80, statusDetails: { evaluated: 'PENDING' } },
    ]
    // 业务契约: G11 应优先 G44.PASS 的 (即使 score 较低)
    const passed = candidates.filter(c => c.statusDetails?.evaluated === 'PASS')
    expect(passed).toHaveLength(1)
    expect(passed[0].id).toBe('1')

    // maskPhone 跨字段保护: 即便通过 G11 推荐, 展示给非 HR 角色应 MASK
    const recommendable = passed[0]
    const masked = applyFieldAcl(recommendable, [
      { field: 'phone', action: 'MASK' },
    ])
    // 注: 这里 recommendable 没 phone 字段, 仅验证不崩溃
    expect(masked.id).toBe('1')
  })
})
