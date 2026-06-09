/**
 * 简历查重服务测试 - G45
 * 6 测试: hashPhone / hashEmail / normalizeName / computeSimilarity / isExactDuplicate / findDuplicates
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  candidate: {
    findMany: jest.fn(),
  },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  hashPhone,
  hashEmail,
  normalizeName,
  computeSimilarity,
  findDuplicates,
  isExactDuplicate,
} = await import('../resume-duplicate-check.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('resume-duplicate-check: hashPhone', () => {
  it('hashPhone 去除所有非数字字符', () => {
    expect(hashPhone('138-0013-8000')).toBe('13800138000')
    expect(hashPhone('+86 138 0013 8000')).toBe('13800138000')
    expect(hashPhone('(138) 0013-8000')).toBe('13800138000')
  })

  it('hashPhone 空值返回空串', () => {
    expect(hashPhone('')).toBe('')
    expect(hashPhone(null)).toBe('')
    expect(hashPhone(undefined)).toBe('')
  })
})

describe('resume-duplicate-check: hashEmail', () => {
  it('hashEmail 标准化为 lowercase + trim', () => {
    expect(hashEmail('A@B.COM')).toBe('a@b.com')
    expect(hashEmail('  Foo@Bar.com  ')).toBe('foo@bar.com')
  })

  it('hashEmail 空值返回空串', () => {
    expect(hashEmail('')).toBe('')
    expect(hashEmail(null)).toBe('')
  })
})

describe('resume-duplicate-check: normalizeName', () => {
  it('normalizeName 去空格', () => {
    expect(normalizeName('  张三  ')).toBe('张三')
    expect(normalizeName('张 三')).toBe('张三')
  })

  it('normalizeName 空值返回空串', () => {
    expect(normalizeName('')).toBe('')
    expect(normalizeName(null)).toBe('')
  })
})

describe('resume-duplicate-check: computeSimilarity', () => {
  it('computeSimilarity 完全相同 = 1.0', () => {
    expect(computeSimilarity('张三', '张三')).toBeCloseTo(1, 2)
  })

  it('computeSimilarity 不同名 < 0.5', () => {
    expect(computeSimilarity('张三', '李四')).toBeLessThan(0.5)
  })

  it('computeSimilarity 单字符差异约 0.5 (1 char diff / 2 chars)', () => {
    // "张三" vs "张四" -> 1 dist / 2 max = 0.5
    expect(computeSimilarity('张三', '张四')).toBeCloseTo(0.5, 2)
  })

  it('computeSimilarity 空串返回 0', () => {
    expect(computeSimilarity('', '张三')).toBe(0)
    expect(computeSimilarity('张三', '')).toBe(0)
  })
})

describe('resume-duplicate-check: isExactDuplicate', () => {
  it('isExactDuplicate 同 phone 即重复', () => {
    expect(isExactDuplicate({ phone: '13800138000' }, { phone: '13800138000' })).toBe(true)
  })

  it('isExactDuplicate 不同 phone 不重复', () => {
    expect(isExactDuplicate({ phone: '13800138000' }, { phone: '13900139000' })).toBe(false)
  })

  it('isExactDuplicate 不同格式但相同 phone 视为重复', () => {
    expect(isExactDuplicate({ phone: '138 0013 8000' }, { phone: '13800138000' })).toBe(true)
  })

  it('isExactDuplicate 同 email 即重复', () => {
    expect(isExactDuplicate({ email: 'A@b.com' }, { email: 'a@B.COM' })).toBe(true)
  })
})

describe('resume-duplicate-check: findDuplicates', () => {
  it('findDuplicates 返回相似候选人列表 (按相似度倒序)', async () => {
    mockPrisma.candidate.findMany.mockResolvedValueOnce([
      { id: 'c1', name: '张三', phone: '13800138000', email: 'a@b.com' },
      { id: 'c2', name: '张三', phone: '13900139000', email: null },
    ])
    const dupes = await findDuplicates({ name: '张三', phone: '13900139000' })
    expect(dupes).toHaveLength(2)
    // 应按 score 倒序
    expect(dupes[0].score).toBeGreaterThanOrEqual(dupes[1].score)
  })

  it('findDuplicates 返回的候选含 matchType 字段', async () => {
    mockPrisma.candidate.findMany.mockResolvedValueOnce([
      { id: 'c1', name: '张三', phone: '13800138000', email: null },
    ])
    const dupes = await findDuplicates({ name: '张三', phone: '13800138000' })
    expect(dupes[0]).toHaveProperty('matchType')
    expect(dupes[0].matchType).toBe('phone')
  })

  it('findDuplicates 无匹配返回空数组', async () => {
    mockPrisma.candidate.findMany.mockResolvedValueOnce([
      { id: 'c1', name: '王五', phone: '13700137000', email: 'w@x.com' },
    ])
    const dupes = await findDuplicates({ name: '张三', phone: '13800138000' })
    expect(dupes).toHaveLength(0)
  })
})
