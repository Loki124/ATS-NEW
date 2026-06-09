// G30 - RPA 适配器接口 + Mock 实现
// 真实 RPA 平台 (UiBot/影刀/来也) 接入时新建 uibot-adapter.js 实现同一接口

const ADAPTER_REGISTRY = {};

export function registerAdapter(adapter) {
  ADAPTER_REGISTRY[adapter.systemName] = adapter;
}

export function getAdapter(systemName) {
  const a = ADAPTER_REGISTRY[systemName];
  if (!a) throw new Error(`No RPA adapter for system: ${systemName}`);
  return a;
}

/**
 * RPA 适配器接口契约:
 *   - systemName: string ('MOCK_RPA' / 'UIBOT' / ...)
 *   - async scrapeJob({ jobTitle, city, page, pageSize }): { success, resumes: [...], raw? }
 *   - async getScraperStatus(scraperJobName): { status, progress, lastRun }
 */
export class MockRpaAdapter {
  constructor() {
    this.systemName = 'MOCK_RPA';
    this._mockData = null;
  }

  setMockData(data) {
    this._mockData = data;
  }

  async scrapeJob({ jobTitle = '', city = '', page = 1, pageSize = 20 } = {}) {
    const defaultMock = [
      { name: '张三', phone: '13800138001', email: 'zhangsan@example.com', source: 'MOCK_智联', sourceUrl: 'https://example.com/r/1' },
      { name: '李四', phone: '13800138002', email: 'lisi@example.com', source: 'MOCK_拉勾', sourceUrl: 'https://example.com/r/2' },
      { name: '王五', phone: '13800138003', email: 'wangwu@example.com', source: 'MOCK_BOSS', sourceUrl: 'https://example.com/r/3' },
    ];
    const resumes = this._mockData || defaultMock;
    return { success: true, resumes: resumes.slice((page - 1) * pageSize, page * pageSize), total: resumes.length };
  }

  async getScraperStatus(scraperJobName) {
    return { status: 'IDLE', progress: 0, lastRun: new Date() };
  }
}

// 注册默认 adapter
const defaultAdapter = new MockRpaAdapter();
registerAdapter(defaultAdapter);
