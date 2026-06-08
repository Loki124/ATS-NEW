/**
 * G40 - 外部集成适配器测试
 */

import { describe, it, expect } from '@jest/globals';
import { MockMokaAdapter } from '../integration/mock-moka.adapter.js';
import { StubEmailAdapter } from '../integration/stub-email.adapter.js';
import { getAdapter } from '../integration/adapter.js';

describe('integration adapters', () => {
  it('MockMokaAdapter 有 systemName', () => {
    const a = new MockMokaAdapter();
    expect(a.systemName).toBe('MOKA');
  });

  it('MockMokaAdapter.createCompany 返回 externalId', async () => {
    const a = new MockMokaAdapter();
    const r = await a.createCompany({ name: 'XX 有限公司', code: 'XX001' });
    expect(r.externalId).toMatch(/^MOKA-/);
    expect(r.status).toBe('SUCCESS');
  });

  it('MockMokaAdapter.updateCompany 幂等', async () => {
    const a = new MockMokaAdapter();
    const r1 = await a.createCompany({ name: 'X', code: 'X' });
    const r2 = await a.updateCompany(r1.externalId, { name: 'X 更新' });
    expect(r2.status).toBe('SUCCESS');
  });

  it('StubEmailAdapter.createDomain 总是 SUCCESS', async () => {
    const a = new StubEmailAdapter();
    const r = await a.createDomain({ domain: 'example.com' });
    expect(r.status).toBe('SUCCESS');
    expect(r.externalId).toBe('example.com');
  });

  it('适配器统一接口契约', () => {
    for (const Cls of [MockMokaAdapter, StubEmailAdapter]) {
      const a = new Cls();
      expect(typeof a.systemName).toBe('string');
      expect(typeof a.createCompany).toBe('function');
      expect(typeof a.updateCompany).toBe('function');
    }
  });

  it('getAdapter 通过 systemName 取得已注册实例', () => {
    const moka = getAdapter('MOKA');
    expect(moka.systemName).toBe('MOKA');
    const email = getAdapter('EMAIL');
    expect(email.systemName).toBe('EMAIL');
  });
});
