/**
 * data-export 服务测试 - G35 通用导出 (CSV/JSON)
 * 5 测试: exportToCsv / BOM / exportToJson / buildExportHeaders / summarizeData
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  candidate: { findMany: jest.fn() },
  demand:    { findMany: jest.fn() },
  position:  { findMany: jest.fn() },
  offer:     { findMany: jest.fn() },
  interview: { findMany: jest.fn() },
  onboarding:{ findMany: jest.fn() },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  exportToCsv,
  exportToJson,
  buildExportHeaders,
  summarizeData,
} = await import('../data-export.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('data-export: exportToCsv', () => {
  it('简单对象数组 -> 头部+数据行', () => {
    const csv = exportToCsv([{ name: '张三', age: 30 }, { name: '李四', age: 25 }])
    expect(csv).toContain('name,age')
    expect(csv).toContain('张三,30')
  })

  it('包含 BOM (Excel 中文兼容)', () => {
    const csv = exportToCsv([{ x: 1 }])
    expect(csv.charCodeAt(0)).toBe(0xFEFF)
  })
})

describe('data-export: exportToJson', () => {
  it('标准 JSON 字符串', () => {
    const json = exportToJson([{ x: 1 }])
    expect(JSON.parse(json)).toEqual([{ x: 1 }])
  })
})

describe('data-export: buildExportHeaders', () => {
  it('中文标签映射', () => {
    const h = buildExportHeaders('Candidate', ['name', 'phone'])
    expect(h).toEqual([{ key: 'name', label: '姓名' }, { key: 'phone', label: '手机号' }])
  })
})

describe('data-export: summarizeData', () => {
  it('数字字段求和', () => {
    const sum = summarizeData([{ amount: 10 }, { amount: 20 }], 'amount')
    expect(sum).toBe(30)
  })
})
