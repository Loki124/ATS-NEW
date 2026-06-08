/**
 * school-library 服务测试 - G41 院校信息库
 * 4 测试: 搜索 (关键词/教育层次), getById, listProvinces
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  school: {
    findMany: jest.fn(),
    findUnique: jest.fn(),
  },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  searchSchools,
  getSchoolById,
  listProvinces,
  filterByLevel,
} = await import('../school-library.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('school-library: searchSchools', () => {
  it('searchSchools 关键词模糊匹配 name/code', async () => {
    mockPrisma.school.findMany.mockResolvedValueOnce([{ id: 's1', name: '清华大学', code: '10003' }])
    const r = await searchSchools('清华')
    expect(r).toHaveLength(1)
    const call = mockPrisma.school.findMany.mock.calls[0][0]
    expect(JSON.stringify(call.where.OR)).toContain('清华')
  })

  it('searchSchools 接受 educationLevel 筛选', async () => {
    mockPrisma.school.findMany.mockResolvedValueOnce([])
    await searchSchools('', { educationLevel: '本科' })
    const call = mockPrisma.school.findMany.mock.calls[0][0]
    expect(call.where.educationLevel).toBe('本科')
  })
})

describe('school-library: getSchoolById', () => {
  it('getSchoolById 返回 school', async () => {
    mockPrisma.school.findUnique.mockResolvedValueOnce({ id: 's1', name: 'X' })
    const s = await getSchoolById('s1')
    expect(s.id).toBe('s1')
  })
})

describe('school-library: listProvinces', () => {
  it('listProvinces 聚合所有不重复省份', async () => {
    mockPrisma.school.findMany.mockResolvedValueOnce([
      { province: '北京' }, { province: '上海' }, { province: '北京' },
    ])
    const p = await listProvinces()
    expect(p.sort()).toEqual(['上海', '北京'])
  })
})

describe('school-library: filterByLevel', () => {
  it('filterByLevel 按教育层次过滤', async () => {
    mockPrisma.school.findMany.mockResolvedValueOnce([{ id: 's1', educationLevel: '本科' }])
    const r = await filterByLevel('本科')
    expect(r).toHaveLength(1)
    const call = mockPrisma.school.findMany.mock.calls[0][0]
    expect(call.where.educationLevel).toBe('本科')
  })
})
