// G40 - 外部集成适配器接口 (文档, 不导出)
/**
 * 外部集成适配器接口契约:
 *
 * 每个 adapter 必须实现:
 *   - systemName: string                // 唯一系统标识, e.g. 'MOKA' / 'EMAIL'
 *   - async createCompany(company): {externalId, status, raw?}
 *   - async updateCompany(externalId, company): {status, raw?}
 *   - async deleteCompany(externalId): {status, raw?}
 *   - async getCompany(externalId): {exists, data?, raw?}
 *
 * 真实 API 接入时:
 *   1. 创建 backend/src/services/integration/moka.adapter.js 实现上述接口
 *   2. 通过 env var EXTERNAL_INTEGRATION_PROVIDER 切换
 *   3. 保留 MockMokaAdapter 用于本地开发 + 测试
 */

export const ADAPTER_REGISTRY = {};

export function registerAdapter(adapter) {
  ADAPTER_REGISTRY[adapter.systemName] = adapter;
}

export function getAdapter(systemName) {
  const a = ADAPTER_REGISTRY[systemName];
  if (!a) throw new Error(`No adapter for system: ${systemName}`);
  return a;
}
