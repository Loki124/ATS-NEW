/**
 * Plan L Task 8: 流程管理端点角色守卫 测试
 *
 * 验证 requireRole(['SUPER_ADMIN', 'ADMIN', 'HRBP']) 中间件行为:
 *   1. HR 角色 → 403
 *   2. ADMIN 角色 → 200 (通过)
 *
 * 不走真实路由, 直接单测 requireRole 中间件
 */

import { describe, it, expect } from '@jest/globals';
import { requireRole } from '../../middleware/auth.middleware.js';

function callMiddleware(middleware, user) {
  return new Promise((resolve) => {
    const req = { user };
    const res = {
      status(s) { this._status = s; return this; },
      json(d) { this._body = d; resolve({ status: this._status, body: d }); return this; },
    };
    let nextCalled = false;
    middleware(req, res, () => { nextCalled = true; resolve({ status: 200, nextCalled: true }); });
  });
}

describe('Plan L · requireRole 角色守卫: 流程管理写端点', () => {
  it('1. HR 角色访问 POST / 写端点 → 403', async () => {
    const guard = requireRole('SUPER_ADMIN', 'ADMIN', 'HRBP');
    const r = await callMiddleware(guard, { id: 'u1', roleType: 'HR' });
    expect(r.status).toBe(403);
    expect(r.body.message).toMatch(/没有权限/);
  });

  it('2. ADMIN 角色访问 POST / 写端点 → 200 (通过)', async () => {
    const guard = requireRole('SUPER_ADMIN', 'ADMIN', 'HRBP');
    const r = await callMiddleware(guard, { id: 'u2', roleType: 'ADMIN' });
    expect(r.status).toBe(200);
    expect(r.nextCalled).toBe(true);
  });
});
