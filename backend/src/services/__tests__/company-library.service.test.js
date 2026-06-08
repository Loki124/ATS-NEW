/**
 * company-library 服务测试 - G41 公司信息库
 * 4 测试: 搜索 (关键词/行业), getById, listIndustries, filterByScale
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  company: {
    findMany: jest.fn(),
    findUnique: jest.fn(),
  },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  searchCompanies,
  getCompanyById,
  listIndustries,
  filterByScale,
} = await import('../company-library.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('company-library: searchCompanies', () => {
  it('searchCompanies 关键词模糊匹配 name/code', async () => {
    mockPrisma.company.findMany.mockResolvedValueOnce([{ id: 'c1', name: '华为', code: 'HW001' }])
    const r = await searchCompanies('华为')
    expect(r).toHaveLength(1)
    const call = mockPrisma.company.findMany.mock.calls[0][0]
    expect(JSON.stringify(call.where.OR)).toContain('华为')
  })

  it('searchCompanies 接受 industry 筛选', async () => {
    mockPrisma.company.findMany.mockResolvedValueOnce([])
    await searchCompanies('', { industry: '互联网' })
    const call = mockPrisma.company.findMany.mock.calls[0][0]
    expect(call.where.industry).toBe('互联网')
  })
})

describe('company-library: getCompanyById', () => {
  it('getCompanyById 返回 company', async () => {
    mockPrisma.company.findUnique.mockResolvedValueOnce({ id: 'c1', name: 'X' })
    const s = await getCompanyById('c1')
    expect(s.id).toBe('c1')
  })
})

describe('company-library: listIndustries', () => {
  it('listIndustries 聚合所有不重复行业', async () => {
    mockPrisma.company.findMany.mockResolvedValueOnce([
      { industry: '互联网' }, { industry: '金融' }, { industry: '互联网' },
    ])
    const p = await listIndustries()
    expect(p.sort()).toEqual(['互联网', '金融'])
  })
})

describe('company-library: filterByScale', () => {
  it('filterByScale 按规模过滤', async () => {
    mockPrisma.company.findMany.mockResolvedValueOnce([{ id: 'c1', scale: '10000+' }])
    const r = await filterByScale('10000+')
    expect(r).toHaveLength(1)
    const call = mockPrisma.company.findMany.mock.calls[0][0]
    expect(call.where.scale).toBe('10000+')
  })
})
