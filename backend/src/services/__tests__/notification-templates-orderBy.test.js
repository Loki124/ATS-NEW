/**
 * 通知模板 orderBy 回归测试
 *
 * 历史 bug: orderBy: { category: 'asc', templateKey: 'asc' } 在 Prisma 5.x 不支持多字段对象形式
 * 修复: 改为数组形式 orderBy: [{ category: 'asc' }, { templateKey: 'asc' }]
 *
 * 此测试通过 mock prisma 验证 listTemplates 调用的 orderBy 是数组形式
 */

import { jest } from '@jest/globals'

// Mock prisma - 验证调用时的 orderBy 参数
const findManyMock = jest.fn().mockResolvedValue([])
const mockPrisma = {
  notificationTemplate: { findMany: findManyMock },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const { listTemplates } = await import('../notification.service.js')

beforeEach(() => {
  findManyMock.mockClear()
})

describe('notification-templates: listTemplates orderBy 回归', () => {
  it('orderBy 必须是数组形式 (Prisma 5.x 多字段要求)', async () => {
    await listTemplates({})
    const callArgs = findManyMock.mock.calls[0][0]
    expect(Array.isArray(callArgs.orderBy)).toBe(true)
    expect(callArgs.orderBy).toEqual([
      { category: 'asc' },
      { templateKey: 'asc' },
    ])
  })

  it('不传任何过滤参数, 应查全部并带分页', async () => {
    await listTemplates({})
    const callArgs = findManyMock.mock.calls[0][0]
    expect(callArgs.where).toEqual({})
    expect(callArgs.take).toBe(100)
  })

  it('传 category 过滤时正确拼到 where', async () => {
    await listTemplates({ category: 'APPROVAL' })
    const callArgs = findManyMock.mock.calls[0][0]
    expect(callArgs.where).toEqual({ category: 'APPROVAL' })
  })

  it('传 isActive=false 时, where 应是 isActive: false (非默认 true)', async () => {
    await listTemplates({ isActive: false })
    const callArgs = findManyMock.mock.calls[0][0]
    expect(callArgs.where).toEqual({ isActive: false })
  })

  it('limit 可被覆盖', async () => {
    await listTemplates({ limit: 5 })
    const callArgs = findManyMock.mock.calls[0][0]
    expect(callArgs.take).toBe(5)
  })
})
