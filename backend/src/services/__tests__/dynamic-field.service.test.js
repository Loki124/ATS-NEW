/**
 * dynamic-field 服务测试 - G42 动态字段定义
 * 6 测试: 列表/详情/upsert/校验 (TEXT/NUMBER/SELECT)
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  fieldDefinition: {
    findMany: jest.fn(),
    findUnique: jest.fn(),
    upsert: jest.fn(),
    update: jest.fn(),
    deleteMany: jest.fn(),
  },
  fieldOption: {
    findMany: jest.fn(),
    create: jest.fn(),
    deleteMany: jest.fn(),
  },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  listFieldsForResource,
  getFieldByKey,
  getFieldWithOptions,
  upsertField,
  validateFieldValue,
  reorderFields,
} = await import('../dynamic-field.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('dynamic-field: listFieldsForResource', () => {
  it('listFieldsForResource 按 orderIndex 升序', async () => {
    mockPrisma.fieldDefinition.findMany.mockResolvedValueOnce([{ orderIndex: 2 }, { orderIndex: 1 }])
    const list = await listFieldsForResource('Candidate')
    expect(list[0].orderIndex).toBe(1)
  })
})

describe('dynamic-field: getFieldByKey', () => {
  it('getFieldByKey 包含 options', async () => {
    mockPrisma.fieldDefinition.findUnique.mockResolvedValueOnce({ id: 'f1', fieldKey: 'k1', options: [] })
    const f = await getFieldByKey('Candidate', 'k1')
    expect(f.fieldKey).toBe('k1')
  })
})

describe('dynamic-field: upsertField', () => {
  it('upsertField 创建新字段', async () => {
    mockPrisma.fieldDefinition.upsert.mockResolvedValueOnce({ id: 'f1' })
    const r = await upsertField({ resource: 'Candidate', fieldKey: 'k1', label: 'L1', fieldType: 'TEXT' })
    expect(r.id).toBe('f1')
  })
})

describe('dynamic-field: validateFieldValue', () => {
  it('validateFieldValue TEXT 必填校验', () => {
    expect(validateFieldValue({ fieldType: 'TEXT', isRequired: true }, '')).toBe(false)
    expect(validateFieldValue({ fieldType: 'TEXT', isRequired: true }, 'v')).toBe(true)
  })

  it('validateFieldValue NUMBER 数值校验', () => {
    expect(validateFieldValue({ fieldType: 'NUMBER' }, 'abc')).toBe(false)
    expect(validateFieldValue({ fieldType: 'NUMBER' }, '123')).toBe(true)
  })

  it('validateFieldValue SELECT 选项值必须存在', () => {
    const f = { fieldType: 'SELECT', options: [{ value: 'a' }, { value: 'b' }] }
    expect(validateFieldValue(f, 'a')).toBe(true)
    expect(validateFieldValue(f, 'c')).toBe(false)
  })
})
