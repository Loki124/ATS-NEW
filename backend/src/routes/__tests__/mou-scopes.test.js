/**
 * MOU 权限范围 (scopes) 端点测试
 * - POST /mou 带 scopes → DB 存 JSON 字符串
 * - PUT /mou/:id 更新 scopes → 覆盖
 * - GET /mou/:id/scopes → 返回解析后对象
 * - GET /mou/:id/scopes 不存在 → 404
 */
import { jest } from '@jest/globals';
import express from 'express';
import request from 'supertest';

// mock prisma (在 import 路由前)
const mockMou = {
  findUnique: jest.fn(),
  findMany: jest.fn(),
  create: jest.fn(),
  update: jest.fn(),
  delete: jest.fn(),
  count: jest.fn(),
};

jest.unstable_mockModule('@prisma/client', () => ({
  PrismaClient: jest.fn(() => ({
    mou: mockMou,
  })),
}));

// 路由 import 必须在 mock 之后
const { default: permissionV2Routes } = await import('../permission-v2.routes.js');

// 构造一个最小化 app，挂载该路由（不走 auth 中间件，直接测路由逻辑）
function buildApp() {
  const app = express();
  app.use(express.json());
  app.use('/api/permissions-v2', permissionV2Routes);
  // 兜底错误处理
  app.use((err, req, res, next) => {
    res.status(500).json({ success: false, message: err.message });
  });
  return app;
}

describe('MOU scopes 端点', () => {
  let app;

  beforeAll(() => {
    app = buildApp();
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('POST /mou 带 scopes 后, DB 存 JSON 字符串, 响应 parse 回对象', async () => {
    const code = `T_MOU_${Date.now()}`;
    const scopesInput = {
      menu: ['user:list', 'demand:list'],
      function: ['demand:create'],
      data: { scope: 'DEPT' },
    };

    const storedMou = {
      id: 'mou-1',
      name: 'TestMou',
      code,
      type: 'BUSINESS',
      description: null,
      parentMouId: null,
      level: 1,
      path: code,
      scopes: JSON.stringify(scopesInput),
      metadata: null,
      status: 'ACTIVE',
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    mockMou.findUnique.mockResolvedValue(null); // 编码不重复
    mockMou.create.mockResolvedValue(storedMou);

    const res = await request(app)
      .post('/api/permissions-v2/mou')
      .send({ name: 'TestMou', code, type: 'BUSINESS', scopes: scopesInput });

    expect(res.status).toBe(201);
    expect(res.body.success).toBe(true);
    // 传给 prisma 的 data 应该是 JSON 字符串
    const createCall = mockMou.create.mock.calls[0][0];
    expect(createCall.data.scopes).toBe(JSON.stringify(scopesInput));
    // 响应里 parse 回对象
    expect(res.body.data.scopes).toEqual(scopesInput);
  });

  it('PUT /mou/:id 传 scopes 后, scopes 被覆盖 (JSON 字符串)', async () => {
    const updatedScopes = {
      menu: ['a:list'],
      function: [],
      data: { scope: 'ALL' },
    };

    const updatedMou = {
      id: 'mou-1',
      name: 'TestMou',
      code: 'T_MOU',
      type: 'BUSINESS',
      description: null,
      parentMouId: null,
      level: 1,
      path: 'T_MOU',
      scopes: JSON.stringify(updatedScopes),
      metadata: null,
      status: 'ACTIVE',
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    mockMou.update.mockResolvedValue(updatedMou);

    const res = await request(app)
      .put('/api/permissions-v2/mou/mou-1')
      .send({ scopes: updatedScopes });

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    const updateCall = mockMou.update.mock.calls[0][0];
    expect(updateCall.data.scopes).toBe(JSON.stringify(updatedScopes));
    expect(res.body.data.scopes).toEqual(updatedScopes);
  });

  it('GET /mou/:id/scopes 返回解析后对象', async () => {
    const scopes = {
      menu: ['user:list'],
      function: ['demand:create'],
      data: { scope: 'DEPT' },
    };

    mockMou.findUnique.mockResolvedValue({
      id: 'mou-1',
      scopes: JSON.stringify(scopes),
    });

    const res = await request(app).get('/api/permissions-v2/mou/mou-1/scopes');

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data).toEqual(scopes);
  });

  it('GET /mou/:id/scopes MOU 不存在 → 404', async () => {
    mockMou.findUnique.mockResolvedValue(null);

    const res = await request(app).get('/api/permissions-v2/mou/non-exist/scopes');

    expect(res.status).toBe(404);
    expect(res.body.success).toBe(false);
    expect(res.body.message).toMatch(/MOU不存在/);
  });
});
