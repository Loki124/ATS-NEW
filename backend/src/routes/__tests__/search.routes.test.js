/**
 * /api/search 路由测试 - Plan T1
 *
 * 覆盖:6 实体命中 / q 边界 / limit 边界 / types 过滤 / 字段脱敏 / 软删除过滤
 *
 * 注:本测试按 mou-scopes.test.js 模式构建最小 app,避免 import 整个 app.js 触发
 *    app.listen / auth 中间件副作用。中间件 (auth + dataPermission) 已用 mock 跳
 *    过,见 supertest 路由前。
 */

import { jest } from '@jest/globals'
import express from 'express'
import request from 'supertest'

// ====== Mock Prisma (6 实体) ======
const mockPrisma = {
  candidate:      { findMany: jest.fn() },
  demand:         { findMany: jest.fn() },
  position:       { findMany: jest.fn() },
  interview:      { findMany: jest.fn() },
  offer:          { findMany: jest.fn() },
  referralRecord: { findMany: jest.fn() },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

// 路由 import 必须在 mock 之后
const { default: searchRoutes } = await import('../search.routes.js')

// 构造最小 app: 跳过真实 auth/data-permission 中间件 (401 占位测试已说明)
function buildApp() {
  const app = express()
  app.use(express.json())
  app.use(
    '/api/search',
    (req, res, next) => {
      req.user = { id: 'u1', role: 'HR' }
      next()
    },
    searchRoutes,
  )
  // 兜底错误处理
  app.use((err, req, res, next) => {
    res.status(500).json({ success: false, message: err.message })
  })
  return app
}

beforeEach(() => {
  jest.clearAllMocks()
  const sample = (where) => {
    const q = where?.OR?.[0]?.contains || 'sample'
    return [{ id: '1', name: `name-${q}`, updatedAt: new Date() }]
  }
  mockPrisma.candidate.findMany.mockImplementation((args) => sample(args?.where))
  mockPrisma.demand.findMany.mockImplementation((args) => sample(args?.where))
  mockPrisma.position.findMany.mockImplementation((args) => sample(args?.where))
  mockPrisma.interview.findMany.mockImplementation((args) => sample(args?.where))
  mockPrisma.offer.findMany.mockImplementation((args) => sample(args?.where))
  mockPrisma.referralRecord.findMany.mockImplementation((args) => sample(args?.where))
})

describe('GET /api/search', () => {
  let app
  beforeAll(() => {
    app = buildApp()
  })

  test('1. 6 实体各能命中', async () => {
    const res = await request(app).get('/api/search?q=张')
    expect(res.status).toBe(200)
    expect(res.body.groups).toHaveLength(6)
    const types = res.body.groups.map((g) => g.type)
    expect(types).toEqual(
      expect.arrayContaining(['candidate', 'demand', 'position', 'interview', 'offer', 'referral']),
    )
  })

  test('2. q 为空 → 400', async () => {
    const res = await request(app).get('/api/search?q=')
    expect(res.status).toBe(400)
  })

  test('3. q 超 64 字符 → 400', async () => {
    const res = await request(app).get('/api/search?q=' + 'a'.repeat(65))
    expect(res.status).toBe(400)
  })

  test('4. limit 边界 (默认 5)', async () => {
    const res = await request(app).get('/api/search?q=张')
    res.body.groups.forEach((g) => {
      expect(g.items.length).toBeLessThanOrEqual(5)
    })
  })

  test('5. types 参数过滤', async () => {
    const res = await request(app).get('/api/search?q=张&types=candidate,demand')
    expect(res.body.groups).toHaveLength(2)
    expect(res.body.groups.map((g) => g.type).sort()).toEqual(['candidate', 'demand'])
  })

  test('6. 软删除过滤由 middleware 接管,service 不再显式传 deletedAt', async () => {
    // Todo #2: 软删除过滤由 soft-delete middleware 在 app.js wire 后自动注入
    // (此测试只验证 service 层不显式传 deletedAt,middleware 自身的注入行为
    //  需在集成测试 / 端到端验证)
    await request(app).get('/api/search?q=张')
    const calls = mockPrisma.candidate.findMany.mock.calls
    expect(calls.length).toBeGreaterThan(0)
    const lastCallWhere = calls[calls.length - 1][0]?.where || {}
    expect(lastCallWhere).not.toHaveProperty('deletedAt')
  })

  test('7. PII 字段在响应中被脱敏', async () => {
    // Override the default mock for candidate to return PII fields
    mockPrisma.candidate.findMany.mockResolvedValueOnce([
      {
        id: 'c1',
        name: '张三',
        phone: '13812345678',
        email: 'zhangsan@example.com',
        updatedAt: new Date(),
      },
    ])

    const res = await request(app).get('/api/search?q=张')
    expect(res.status).toBe(200)
    const candidateGroup = res.body.groups.find((g) => g.type === 'candidate')
    expect(candidateGroup.items[0].phone).toBe('138****5678')
    expect(candidateGroup.items[0].email).toBe('z***@example.com')
  })

  test('8. offer salary 在响应中被脱敏', async () => {
    mockPrisma.offer.findMany.mockResolvedValueOnce([
      {
        id: 'o1',
        lastYearAvgSalary: 250000,  // 真实 schema 的 Decimal 字段,这里 mock 为 number
        offerStatus: 'PENDING',     // 真实 schema 字段(不是 onboardingStatus)
        application: { candidate: { id: 'c1', name: '张三' }, position: { id: 'p1', name: '产品经理' } },
      },
    ])
    const res = await request(app).get('/api/search?q=张')
    const offerGroup = res.body.groups.find((g) => g.type === 'offer')
    expect(offerGroup.items[0].lastYearAvgSalary).toMatch(/万\+/)  // maskSalary 输出 "25万+"
  })

  test('9. referral candidate.phone 在响应中被脱敏', async () => {
    mockPrisma.referralRecord.findMany.mockResolvedValueOnce([
      {
        id: 'r1',
        candidate: { name: '李四', phone: '13987654321' },
        referrer: { id: 'u1', realName: '王五' },
        recommendedAt: new Date(),
      },
    ])
    const res = await request(app).get('/api/search?q=李')
    const refGroup = res.body.groups.find((g) => g.type === 'referral')
    expect(refGroup.items[0].candidate.phone).toBe('139****4321')
  })
})
