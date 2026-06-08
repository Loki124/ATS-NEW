import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { fieldAcl } from '../field-acl.middleware.js';

function makeRes() {
  let lastJsonBody = null;
  const jsonFn = jest.fn((body) => {
    lastJsonBody = body;
    return body;
  });
  return {
    json: jsonFn,
    getLastJsonBody: () => lastJsonBody,
  };
}

const MOCK_RULES = [
  { resource: 'Candidate', field: 'phone', action: 'MASK' },
  { resource: 'Candidate', field: 'email', action: 'HIDE' },
];

describe('field-acl middleware', () => {
  beforeEach(() => jest.clearAllMocks());

  it('SUPER_ADMIN 跳过', async () => {
    const req = { user: { id: 'u1', roleType: 'SUPER_ADMIN' }, originalUrl: '/api/candidates' };
    const next = jest.fn();
    await fieldAcl('Candidate', { rules: MOCK_RULES })(req, {}, next);
    expect(next).toHaveBeenCalled();
    // 不应设置 fieldAclRules
    expect(req.fieldAclRules).toBeUndefined();
  });

  it('加载规则并附加到 req', async () => {
    const req = { user: { id: 'u1', roleType: 'HR' }, originalUrl: '/api/candidates' };
    const next = jest.fn();
    await fieldAcl('Candidate', { rules: MOCK_RULES })(req, {}, next);
    expect(req.fieldAclRules).toBeDefined();
    expect(req.fieldAclRules).toHaveLength(2);
    expect(next).toHaveBeenCalled();
  });

  it('applyToResponse 包装 res.json, 自动应用规则', async () => {
    const req = {
      user: { id: 'u1', roleType: 'HR' },
      originalUrl: '/api/candidates',
    };
    const res = makeRes();
    const next = jest.fn();
    await fieldAcl('Candidate', { rules: MOCK_RULES })(req, res, next);
    // 模拟路由 handler 调用了 res.json
    res.json({ success: true, data: { name: 'Alice', phone: '13800138000', email: 'a@b.com' } });
    const out = res.getLastJsonBody();
    expect(out.data.phone).toBe('138****8000');
    expect(out.data.name).toBe('Alice');
    expect(out.data.email).toBeNull();
  });

  it('数组 data 递归应用', async () => {
    const req = {
      user: { id: 'u1', roleType: 'HR' },
      originalUrl: '/api/candidates',
    };
    const res = makeRes();
    const next = jest.fn();
    await fieldAcl('Candidate', { rules: [{ resource: 'Candidate', field: 'phone', action: 'MASK' }] })(req, res, next);
    res.json({ success: true, data: [{ phone: '13800138000' }, { phone: '13900139000' }] });
    const out = res.getLastJsonBody();
    expect(out.data[0].phone).toBe('138****8000');
    expect(out.data[1].phone).toBe('139****9000');
  });

  it('审计记录 MASK/HIDE 行为', async () => {
    const req = {
      user: { id: 'u1', name: 'HR-Alice', roleType: 'HR' },
      originalUrl: '/api/candidates',
    };
    const res = makeRes();
    const next = jest.fn();
    const auditFn = jest.fn();
    await fieldAcl('Candidate', {
      rules: [{ resource: 'Candidate', field: 'phone', action: 'MASK' }],
      auditFn,
    })(req, res, next);
    res.json({ success: true, data: { phone: '13800138000' } });
    // 等待微任务
    await new Promise(r => setImmediate(r));
    expect(auditFn).toHaveBeenCalled();
    const call = auditFn.mock.calls[0][0];
    expect(call.userId).toBe('u1');
    expect(call.userName).toBe('HR-Alice');
    expect(call.resource).toBe('Candidate');
    expect(call.field).toBe('phone');
    expect(call.action).toBe('MASK');
  });
});
