import { describe, it, expect } from '@jest/globals';
import { MockRpaAdapter, registerAdapter, getAdapter } from '../integration/rpa-adapter.js';

describe('RPA adapter', () => {
  it('MockRpaAdapter systemName = MOCK_RPA', () => {
    expect(new MockRpaAdapter().systemName).toBe('MOCK_RPA');
  });

  it('MockRpaAdapter.scrapeJob 返回 mock 简历列表', async () => {
    const a = new MockRpaAdapter();
    const r = await a.scrapeJob({ jobTitle: '前端工程师', city: '北京' });
    expect(r.success).toBe(true);
    expect(r.resumes).toBeInstanceOf(Array);
    expect(r.resumes.length).toBeGreaterThan(0);
    expect(r.resumes[0]).toHaveProperty('name');
    expect(r.resumes[0]).toHaveProperty('phone');
  });

  it('getAdapter 注册后能取到', () => {
    const a = new MockRpaAdapter();
    registerAdapter(a);
    expect(getAdapter('MOCK_RPA')).toBe(a);
  });

  it('getAdapter 未注册抛错', () => {
    expect(() => getAdapter('NONEXISTENT')).toThrow('No RPA adapter');
  });

  it('MockRpaAdapter.scrapeJob 自定义 mock 数据', async () => {
    const a = new MockRpaAdapter();
    a.setMockData([{ name: '张三', phone: '13800138000', source: 'TEST' }]);
    const r = await a.scrapeJob({});
    expect(r.resumes[0].name).toBe('张三');
  });
});
