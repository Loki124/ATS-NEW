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
const { listUsers } = await import('../users')

describe('listUsers', () => {
  beforeEach(() => {
    mockGet.mockReset()
  })

  it('calls GET /api/users and unwraps { success, data }', async () => {
    mockGet.mockResolvedValue({
      data: {
        success: true,
        data: [
          { id: 'u1', realName: '张三', username: 'zhangsan' },
          { id: 'u2', realName: '李四', username: 'lisi' },
        ],
      },
    })

    const users = await listUsers()

    expect(mockGet).toHaveBeenCalledTimes(1)
    expect(mockGet).toHaveBeenCalledWith('/users')
    expect(users).toHaveLength(2)
    expect(users[0]).toMatchObject({ id: 'u1', realName: '张三', username: 'zhangsan' })
  })

  it('returns empty array on error', async () => {
    mockGet.mockRejectedValue(new Error('network'))

    const users = await listUsers()
    expect(users).toEqual([])
  })
})