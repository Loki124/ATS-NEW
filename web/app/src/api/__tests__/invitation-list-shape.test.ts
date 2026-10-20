/**
 * invitation-list-shape.test.ts — 列表客户端返回形状回归（2026-10-20 线上事故锁契约）
 *
 * 背景：
 *   2026-09-30「信封收口 Batch5/6」把 listInterviews / listInvitations 从
 *   `return data`（信封）改成 `return data?.data ?? data`（裸数组），但消费方
 *   InterviewList.vue / InvitationCenter.vue 仍读 `res.data` / `res.pagination`：
 *     - 邀约页 loadClaimPool 把 undefined 写进 claimPool → 模板 claimPool.length
 *       崩溃（用户线上报错：Cannot read properties of undefined (reading 'length')）；
 *     - 两个列表页主表静默空白、分页计数恒 0。
 *   修复：两个 list 客户端归一返回 { data, pagination }（信封/裸数组双兼容），
 *   页面消费代码不变。本测试锁死该契约，防再次单边改动漂移。
 *
 * 覆盖：
 *   1. 信封响应 → { data, pagination } 原样透出（pagination 含 total/totalPages）；
 *   2. 裸数组响应 → { data, pagination: undefined }（不炸、不为 undefined）；
 *   3. getClaimPool 维持裸数组契约（页面侧已做 Array.isArray 归一）。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockGet = vi.fn()

vi.mock('axios', () => ({
  default: {
    create: () => ({
      get: mockGet,
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    }),
  },
}))

const { listInvitations, getClaimPool } = await import('../invitation')
const { listInterviews } = await import('../interview')

describe('listInvitations 返回形状', () => {
  beforeEach(() => mockGet.mockReset())

  it('信封响应 → { data, pagination }（页面读 res.data / res.pagination）', async () => {
    mockGet.mockResolvedValue({
      data: {
        success: true,
        data: [{ id: 'iv1' }, { id: 'iv2' }],
        pagination: { page: 1, pageSize: 50, total: 2, totalPages: 1 },
      },
    })

    const res = await listInvitations({ page: 1, pageSize: 50 })

    expect(res.data).toHaveLength(2)
    expect(res.pagination?.total).toBe(2)
    expect(res.pagination?.totalPages).toBe(1)
  })

  it('裸数组响应 → { data, pagination: undefined }，绝不返回 undefined', async () => {
    mockGet.mockResolvedValue({ data: [{ id: 'iv1' }] })

    const res = await listInvitations()

    expect(res).toBeDefined()
    expect(res.data).toHaveLength(1)
    expect(res.pagination).toBeUndefined()
  })
})

describe('listInterviews 返回形状（同款回归）', () => {
  beforeEach(() => mockGet.mockReset())

  it('信封响应 → { data, pagination }', async () => {
    mockGet.mockResolvedValue({
      data: {
        success: true,
        data: [{ id: 'it1' }],
        pagination: { page: 2, pageSize: 50, total: 30, totalPages: 1 },
      },
    })

    const res = await listInterviews({ page: 2 })

    expect(res.data).toHaveLength(1)
    expect(res.pagination?.total).toBe(30)
  })

  it('裸数组响应 → { data, pagination: undefined }', async () => {
    mockGet.mockResolvedValue({ data: [] })

    const res = await listInterviews()

    expect(res.data).toEqual([])
    expect(res.pagination).toBeUndefined()
  })
})

describe('getClaimPool 返回形状（裸数组契约不变）', () => {
  beforeEach(() => mockGet.mockReset())

  it('信封响应 → 数组', async () => {
    mockGet.mockResolvedValue({ data: { success: true, data: [{ id: 'c1' }] } })

    const res = await getClaimPool()

    expect(Array.isArray(res)).toBe(true)
    expect(res).toHaveLength(1)
  })

  it('裸数组响应 → 数组', async () => {
    mockGet.mockResolvedValue({ data: [{ id: 'c1' }, { id: 'c2' }] })

    const res = await getClaimPool()

    expect(Array.isArray(res)).toBe(true)
    expect(res).toHaveLength(2)
  })
})
