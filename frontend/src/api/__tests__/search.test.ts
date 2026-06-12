/**
 * search.test.ts - 全局搜索 API 客户端测试 (Plan T3)
 *
 * 覆盖:
 *  - searchApi() 调 /search + 正确的 q/types/limit 参数
 *  - q 截断到 64 字符
 *  - types 缺省时不传
 *  - 多 types 用逗号拼接
 *  - entityLabel() 6 类型中文标签
 *  - routeForEntity() 6 类型详情页路由
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

// Capture the mockGet from axios.create() so we can assert against it
const mockGet = vi.fn()
const mockInterceptorsUse = vi.fn()

vi.mock('axios', () => ({
  default: {
    create: () => ({
      get: mockGet,
      interceptors: { request: { use: mockInterceptorsUse } },
    }),
  },
}))

// Now import the module under test (must come AFTER vi.mock)
const { searchApi, entityLabel, routeForEntity } = await import('../search')

describe('searchApi', () => {
  beforeEach(() => {
    mockGet.mockReset()
    mockGet.mockResolvedValue({ data: { groups: [] } })
  })

  it('calls /api/search with q + types + limit', async () => {
    await searchApi({ q: '张', types: ['candidate'], limit: 5 })

    expect(mockGet).toHaveBeenCalledTimes(1)
    expect(mockGet).toHaveBeenCalledWith(
      '/search',
      expect.objectContaining({
        params: expect.objectContaining({ q: '张', types: 'candidate', limit: 5 }),
      }),
    )
  })

  it('truncates q to 64 chars', async () => {
    const longQ = 'a'.repeat(100)
    await searchApi({ q: longQ, limit: 5 })

    const callArgs = mockGet.mock.calls[0]
    expect(callArgs[1].params.q).toHaveLength(64)
  })

  it('omits types when not provided', async () => {
    await searchApi({ q: '张', limit: 5 })

    const callArgs = mockGet.mock.calls[0]
    expect(callArgs[1].params.types).toBeUndefined()
  })

  it('joins multiple types with comma', async () => {
    await searchApi({ q: '张', types: ['candidate', 'demand'], limit: 5 })

    const callArgs = mockGet.mock.calls[0]
    expect(callArgs[1].params.types).toBe('candidate,demand')
  })
})

describe('entityLabel', () => {
  it('returns Chinese label for each type', () => {
    expect(entityLabel('candidate')).toBe('候选人')
    expect(entityLabel('demand')).toBe('招聘需求')
    expect(entityLabel('position')).toBe('职位')
    expect(entityLabel('interview')).toBe('面试')
    expect(entityLabel('offer')).toBe('Offer')
    expect(entityLabel('referral')).toBe('内推')
  })
})

describe('routeForEntity', () => {
  it('returns correct route for each type', () => {
    expect(routeForEntity('candidate', 'c1')).toBe('/candidate/detail/c1')
    expect(routeForEntity('demand', 'd1')).toBe('/demand/detail/d1')
    expect(routeForEntity('position', 'p1')).toBe('/position/detail/p1')
    expect(routeForEntity('interview', 'i1')).toBe('/interview/detail/i1')
    expect(routeForEntity('offer', 'o1')).toBe('/offer/detail/o1')
    expect(routeForEntity('referral', 'r1')).toBe('/referral/detail/r1')
  })
})
