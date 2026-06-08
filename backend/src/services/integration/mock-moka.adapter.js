// G40 - 本地 Mock 摩卡 People 适配器
// 模拟摩卡 People HTTP API 行为, 用于本地开发 + 测试

import crypto from 'crypto';
import { registerAdapter } from './adapter.js';

class MockMokaAdapter {
  constructor() {
    this.systemName = 'MOKA';
    this._store = new Map(); // externalId → company
  }

  _genId(company) {
    return 'MOKA-' + crypto.createHash('md5').update(company.code).digest('hex').slice(0, 8);
  }

  async createCompany(company) {
    const externalId = this._genId(company);
    this._store.set(externalId, { ...company });
    console.log(`[MockMoka] createCompany: ${company.name} → ${externalId}`);
    return { externalId, status: 'SUCCESS', raw: { mock: true } };
  }

  async updateCompany(externalId, company) {
    if (!this._store.has(externalId)) {
      console.log(`[MockMoka] updateCompany: ${externalId} NOT FOUND`);
      return { status: 'FAILED', error: 'Not found', raw: { mock: true } };
    }
    this._store.set(externalId, { ...this._store.get(externalId), ...company });
    console.log(`[MockMoka] updateCompany: ${externalId} → ${company.name}`);
    return { status: 'SUCCESS', raw: { mock: true } };
  }

  async deleteCompany(externalId) {
    this._store.delete(externalId);
    console.log(`[MockMoka] deleteCompany: ${externalId}`);
    return { status: 'SUCCESS', raw: { mock: true } };
  }

  async getCompany(externalId) {
    const data = this._store.get(externalId);
    return { exists: !!data, data, raw: { mock: true } };
  }
}

const adapter = new MockMokaAdapter();
registerAdapter(adapter);

export { MockMokaAdapter };
export default adapter;
