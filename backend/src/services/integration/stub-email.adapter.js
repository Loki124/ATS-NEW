// G40 - 邮箱同步占位 (StubEmailAdapter)
// 真实 API 接入前用, 等企业邮箱 API 授权后实现

import { registerAdapter } from './adapter.js';

class StubEmailAdapter {
  constructor() {
    this.systemName = 'EMAIL';
  }

  async createCompany(company) {
    console.log(`[StubEmail] createCompany: ${company.name} (待 API 接入)`);
    return { externalId: company.code, status: 'SUCCESS', raw: { stub: true } };
  }

  async updateCompany(externalId, company) {
    console.log(`[StubEmail] updateCompany: ${externalId}`);
    return { status: 'SUCCESS', raw: { stub: true } };
  }

  async deleteCompany(externalId) {
    console.log(`[StubEmail] deleteCompany: ${externalId}`);
    return { status: 'SUCCESS', raw: { stub: true } };
  }

  async getCompany(externalId) {
    return { exists: true, data: { code: externalId }, raw: { stub: true } };
  }

  // 邮箱 adapter 额外提供 createDomain 用于邮箱域名
  async createDomain({ domain }) {
    console.log(`[StubEmail] createDomain: ${domain} (待 API 接入)`);
    return { externalId: domain, status: 'SUCCESS', raw: { stub: true } };
  }
}

const adapter = new StubEmailAdapter();
registerAdapter(adapter);

export { StubEmailAdapter };
export default adapter;
