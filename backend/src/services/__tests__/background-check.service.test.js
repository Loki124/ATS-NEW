/**
 * G26 - 手动背调 4 等级 - 服务测试
 *
 * 覆盖:
 *  - BG_CHECK_LEVELS 4 等级定义
 *  - validateLevelTransition 状态机转换
 *  - mapLevelToScore 评分映射
 *  - isPassingLevel 是否通过
 *  - buildReportData 报告数据组装
 *  - listBackgroundChecks / createBackgroundCheck / completeBackgroundCheck CRUD
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  backgroundCheckRecord: {
    findMany: jest.fn(),
    findUnique: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
  },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  BG_CHECK_LEVELS,
  validateLevelTransition,
  mapLevelToScore,
  isPassingLevel,
  buildReportData,
  listBackgroundChecks,
  createBackgroundCheck,
  completeBackgroundCheck,
} = await import('../background-check.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('background-check: BG_CHECK_LEVELS', () => {
  it('4 等级定义', () => {
    expect(Object.keys(BG_CHECK_LEVELS)).toHaveLength(4)
    expect(BG_CHECK_LEVELS.PASS.level).toBe('PASS')
    expect(BG_CHECK_LEVELS.WARN.level).toBe('WARN')
    expect(BG_CHECK_LEVELS.INCONCLUSIVE.level).toBe('INCONCLUSIVE')
    expect(BG_CHECK_LEVELS.FAIL.level).toBe('FAIL')
  })
})

describe('background-check: validateLevelTransition', () => {
  it('ACTIVE→PASS 合法', () => {
    expect(validateLevelTransition('ACTIVE', 'PASS')).toBe(true)
  })

  it('ACTIVE→INCONCLUSIVE 合法', () => {
    expect(validateLevelTransition('ACTIVE', 'INCONCLUSIVE')).toBe(true)
  })

  it('PASS→ACTIVE 非法 (终态)', () => {
    expect(validateLevelTransition('PASS', 'ACTIVE')).toBe(false)
  })

  it('WARN→FAIL 非法 (终态)', () => {
    expect(validateLevelTransition('WARN', 'FAIL')).toBe(false)
  })

  it('未知状态 → false', () => {
    expect(validateLevelTransition('UNKNOWN', 'PASS')).toBe(false)
  })
})

describe('background-check: mapLevelToScore', () => {
  it('PASS=100, WARN=70, INCONCLUSIVE=50, FAIL=0', () => {
    expect(mapLevelToScore('PASS')).toBe(100)
    expect(mapLevelToScore('WARN')).toBe(70)
    expect(mapLevelToScore('INCONCLUSIVE')).toBe(50)
    expect(mapLevelToScore('FAIL')).toBe(0)
  })

  it('未知等级 → null', () => {
    expect(mapLevelToScore('UNKNOWN')).toBeNull()
  })
})

describe('background-check: isPassingLevel', () => {
  it('PASS=true, WARN=true (可接受), FAIL=false, INCONCLUSIVE=false', () => {
    expect(isPassingLevel('PASS')).toBe(true)
    expect(isPassingLevel('WARN')).toBe(true)
    expect(isPassingLevel('FAIL')).toBe(false)
    expect(isPassingLevel('INCONCLUSIVE')).toBe(false)
  })
})

describe('background-check: buildReportData', () => {
  it('汇总 offer + 候选人 + 背调记录', () => {
    const data = buildReportData({
      offer: { id: 'o1', positionName: '工程师' },
      candidate: { name: '张三', phone: '13800138000' },
      record: { level: 'PASS', score: 100, risks: [], completedAt: new Date(), supplier: '内部' },
    })
    expect(data.title).toContain('背调报告')
    expect(data.title).toContain('张三')
    expect(data.sections).toBeDefined()
    expect(data.sections.length).toBeGreaterThanOrEqual(2)
  })

  it('缺少候选人/记录时仍能构建', () => {
    const data = buildReportData({})
    expect(data.title).toContain('背调报告')
    expect(data.sections).toBeDefined()
  })
})

describe('background-check: listBackgroundChecks', () => {
  it('传 offerId 过滤', async () => {
    mockPrisma.backgroundCheckRecord.findMany.mockResolvedValueOnce([])
    await listBackgroundChecks('offer-1')
    const call = mockPrisma.backgroundCheckRecord.findMany.mock.calls[0][0]
    expect(call.where.offerId).toBe('offer-1')
  })
})

describe('background-check: createBackgroundCheck', () => {
  it('默认 status=ACTIVE', async () => {
    mockPrisma.backgroundCheckRecord.create.mockResolvedValueOnce({ id: 'b1', status: 'ACTIVE' })
    const r = await createBackgroundCheck({ offerId: 'o1', checkType: '学历' })
    expect(r.id).toBe('b1')
    const data = mockPrisma.backgroundCheckRecord.create.mock.calls[0][0].data
    expect(data.status).toBe('ACTIVE')
    expect(data.offerId).toBe('o1')
    expect(data.checkType).toBe('学历')
  })
})

describe('background-check: completeBackgroundCheck', () => {
  it('写 level + score + 自动计算', async () => {
    mockPrisma.backgroundCheckRecord.update.mockResolvedValueOnce({ id: 'b1', level: 'PASS', score: 100 })
    const r = await completeBackgroundCheck('b1', { level: 'PASS', risks: [] })
    expect(r.score).toBe(100)
    const data = mockPrisma.backgroundCheckRecord.update.mock.calls[0][0].data
    expect(data.level).toBe('PASS')
    expect(data.score).toBe(100)
  })

  it('非法转换 (ACTIVE→其他非 4 等级) 抛错', async () => {
    await expect(completeBackgroundCheck('b1', { level: 'BOGUS' })).rejects.toThrow()
  })
})
