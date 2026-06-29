# Plan E: 外部集成脚手架 (G40)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 法人公司同步 (摩卡 People + 邮箱) 的脚手架 — schema + 适配器模式 + 本地可用的 Mock 实现, 等企业 API 授权后只需替换 adapter

**Architecture:**
- 新建 `LegalCompanySync` 表 (存同步状态 + 外部 ID)
- 新建 `ExternalIntegrationAdapter` 接口 + 2 个实现: `MockMokaAdapter` (本地模拟) + `StubEmailAdapter` (空操作)
- 同步任务可手动触发 (admin 按钮), 也预留 cron hook
- 真实 API 接入等企业授权后, 添加 `MokaAdapter` (真实 HTTP) 即可

**Tech Stack:** Prisma 5 + MySQL 9, 适配器模式, console 模拟

---

## DoD
- [ ] 1 张新表: `LegalCompanySync` (含 companyId + externalSystem + externalId + lastSyncAt + status)
- [ ] ≥ 5 单测: 适配器接口契约 + Mock 实现行为
- [ ] 4 个新 API: 手动触发同步 + 查询同步状态 + 重试失败
- [ ] Admin UI 入口: /settings/external 加 "同步" 按钮
- [ ] 0 个外部依赖 (完全本地可跑)
- [ ] `npm test` 通过 (342 + 5 = 347+ 测试)

---

## Task 1: schema 扩展

**Files:**
- Modify: `backend/prisma/schema.prisma` (末尾追加 2 个 model)

- [ ] **Step 1.1: 加 LegalCompanySync + ExternalSyncLog**

```prisma
// ============================================
// G40 - 法人公司同步 (摩卡 People + 邮箱)
// ============================================
model LegalCompanySync {
  id String @id @default(uuid())

  companyId String
  // 关联 Company (法人公司)

  externalSystem String  @db.VarChar(32)  // MOKA / EMAIL
  externalId     String? @db.VarChar(128) // 摩卡侧公司 ID / 邮箱域名

  lastSyncAt   DateTime?
  lastSyncBy   String?   // userId
  syncStatus   String    @default("PENDING") @db.VarChar(16) // PENDING / SUCCESS / FAILED / RETRY

  lastError   String?   @db.Text
  retryCount  Int       @default(0)

  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  company Company @relation(fields: [companyId], references: [id], onDelete: Cascade)

  @@unique([companyId, externalSystem])
  @@index([syncStatus])
  @@map("legal_company_syncs")
}

model ExternalSyncLog {
  id String @id @default(uuid())

  syncId    String   // 关联 LegalCompanySync.id
  companyId String
  system    String   @db.VarChar(32)

  action   String  @db.VarChar(32) // SYNC / RETRY / RECONCILE
  status   String  @db.VarChar(16) // SUCCESS / FAILED
  message  String? @db.Text
  payload  String? @db.Text       // JSON, 同步的字段

  createdAt DateTime @default(now())

  @@index([syncId, createdAt])
  @@index([companyId, system])
  @@map("external_sync_logs")
}
```

`Company` model 末尾加反向:
```prisma
  syncs LegalCompanySync[]
```

- [ ] **Step 1.2: 推 schema**

```bash
cd backend
npx prisma db push --skip-generate
npx prisma generate
```

- [ ] **Step 1.3: commit**

```bash
git add backend/prisma/schema.prisma backend/prisma/migrations/
git commit -m "feat(G40): LegalCompanySync + ExternalSyncLog 表 (脚手架基础)"
```

---

## Task 2: 适配器接口 + Mock 实现

**Files:**
- Create: `backend/src/services/integration/` 目录
- Create: `backend/src/services/integration/adapter.js`
- Create: `backend/src/services/integration/mock-moka.adapter.js`
- Create: `backend/src/services/integration/stub-email.adapter.js`
- Create: `backend/src/services/__tests__/integration.test.js`

- [ ] **Step 2.1: 写失败测试 (5 个)**

```js
// backend/src/services/__tests__/integration.test.js
import { describe, it, expect, vi } from '@jest/globals';
import { MockMokaAdapter } from '../integration/mock-moka.adapter.js';
import { StubEmailAdapter } from '../integration/stub-email.adapter.js';

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
});
```

- [ ] **Step 2.2: 跑测试, 确认失败**

```bash
npm test -- integration
```
Expected: FAIL

- [ ] **Step 2.3: 实现 adapter 接口文档**

```js
// backend/src/services/integration/adapter.js
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
```

- [ ] **Step 2.4: 实现 MockMokaAdapter**

```js
// backend/src/services/integration/mock-moka.adapter.js
// 本地 Mock, 模拟摩卡 People HTTP API 行为

import { registerAdapter } from './adapter.js';
import crypto from 'crypto';

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
    this._store.set(externalId, company);
    console.log(`[MockMoka] createCompany: ${company.name} → ${externalId}`);
    return { externalId, status: 'SUCCESS', raw: { mock: true } };
  }

  async updateCompany(externalId, company) {
    if (!this._store.has(externalId)) {
      return { status: 'FAILED', error: 'Not found', raw: { mock: true } };
    }
    this._store.set(externalId, { ...this._store.get(externalId), ...company });
    console.log(`[MockMoka] updateCompany: ${externalId} → ${company.name}`);
    return { status: 'SUCCESS', raw: { mock: true } };
  }

  async deleteCompany(externalId) {
    this._store.delete(externalId);
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
```

- [ ] **Step 2.5: 实现 StubEmailAdapter**

```js
// backend/src/services/integration/stub-email.adapter.js
// 邮箱同步占位 — 等企业邮箱 API 授权后实现

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
    return { status: 'SUCCESS', raw: { stub: true } };
  }
  async getCompany(externalId) {
    return { exists: true, data: { code: externalId }, raw: { stub: true } };
  }
}

const adapter = new StubEmailAdapter();
registerAdapter(adapter);
export { StubEmailAdapter };
export default adapter;
```

- [ ] **Step 2.6: 跑测试通过**

```bash
npm test -- integration
```
Expected: 5 passed

- [ ] **Step 2.7: commit**

```bash
git add backend/src/services/integration/ backend/src/services/__tests__/integration.test.js
git commit -m "feat(G40): 外部集成适配器接口 + Mock/Stub 实现 (5 测试)"
```

---

## Task 3: 同步服务

**Files:**
- Create: `backend/src/services/external-sync.service.js`

- [ ] **Step 3.1: 实现 service**

```js
// backend/src/services/external-sync.service.js
// G40 - 法人公司同步服务

import { prisma } from '../app.js';
import { getAdapter } from './integration/adapter.js';

export async function syncCompany(companyId, system, operatorId) {
  const company = await prisma.company.findUnique({ where: { id: companyId } });
  if (!company) throw new Error('公司不存在');

  const adapter = getAdapter(system);
  const result = await adapter.createCompany(company);

  const sync = await prisma.legalCompanySync.upsert({
    where: { companyId_externalSystem: { companyId, externalSystem: system } },
    create: {
      companyId, externalSystem: system,
      externalId: result.externalId,
      lastSyncAt: new Date(),
      lastSyncBy: operatorId,
      syncStatus: result.status,
      lastError: result.error || null,
    },
    update: {
      externalId: result.externalId,
      lastSyncAt: new Date(),
      lastSyncBy: operatorId,
      syncStatus: result.status,
      lastError: result.error || null,
      retryCount: { increment: result.status === 'SUCCESS' ? 0 : 1 },
    },
  });

  await prisma.externalSyncLog.create({
    data: {
      syncId: sync.id, companyId, system,
      action: 'SYNC', status: result.status,
      message: result.error, payload: JSON.stringify({ externalId: result.externalId }),
    },
  });

  return sync;
}

export async function listSyncs({ system, status } = {}) {
  const where = {};
  if (system) where.externalSystem = system;
  if (status) where.syncStatus = status;
  return prisma.legalCompanySync.findMany({
    where, include: { company: true },
    orderBy: { updatedAt: 'desc' },
  });
}

export async function retryFailed(syncId, operatorId) {
  const sync = await prisma.legalCompanySync.findUnique({ where: { id: syncId } });
  if (!sync) throw new Error('Sync 不存在');
  if (sync.syncStatus !== 'FAILED') throw new Error('只能重试 FAILED 状态');

  return syncCompany(sync.companyId, sync.externalSystem, operatorId);
}
```

- [ ] **Step 3.2: commit**

```bash
git add backend/src/services/external-sync.service.js
git commit -m "feat(G40): 法人公司同步 service (含 retry)"
```

---

## Task 4: 同步 API

**Files:**
- Create: `backend/src/routes/external-sync.routes.js`
- Modify: `backend/src/app.js`

- [ ] **Step 4.1: 写 routes**

```js
// backend/src/routes/external-sync.routes.js
import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import { syncCompany, listSyncs, retryFailed } from '../services/external-sync.service.js';

const router = Router();
router.use(authMiddleware);

router.post('/sync/:companyId/:system', async (req, res, next) => {
  try {
    const data = await syncCompany(req.params.companyId, req.params.system, req.user.id);
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/syncs', async (req, res, next) => {
  try {
    const data = await listSyncs({ system: req.query.system, status: req.query.status });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.post('/syncs/:id/retry', async (req, res, next) => {
  try {
    const data = await retryFailed(req.params.id, req.user.id);
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

export default router;
```

- [ ] **Step 4.2: 注册**

```js
import externalSyncRoutes from './routes/external-sync.routes.js';
app.use('/api/external-sync', externalSyncRoutes);
```

- [ ] **Step 4.3: 验证**

```bash
# 注册 adapter
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  http://127.0.0.1:5125/api/external-sync/sync/<companyId>/MOKA
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5125/api/external-sync/syncs
```

- [ ] **Step 4.4: commit**

```bash
git add backend/src/routes/external-sync.routes.js backend/src/app.js
git commit -m "feat(G40): 同步 API 3 个端点"
```

---

## Task 5: 前端 API 客户端 + Settings 入口

**Files:**
- Create: `frontend/src/api/external-sync.ts`
- Modify: `frontend/src/pages/settings/CompanySettings.vue` (加同步按钮)

- [ ] **Step 5.1: API**

```ts
// frontend/src/api/external-sync.ts
import api from './base';

export const triggerCompanySync = (companyId: string, system: 'MOKA' | 'EMAIL') =>
  api.post(`/external-sync/sync/${companyId}/${system}`).then(r => r.data.data);

export const fetchSyncs = (params?: { system?: string; status?: string }) =>
  api.get('/external-sync/syncs', { params }).then(r => r.data.data);

export const retrySync = (syncId: string) =>
  api.post(`/external-sync/syncs/${syncId}/retry`).then(r => r.data.data);
```

- [ ] **Step 5.2: CompanySettings.vue 加按钮**

每行加 n-button "同步摩卡" / "同步邮箱", 调用 triggerCompanySync, 显示 n-message 反馈.

- [ ] **Step 5.3: vue-tsc 验证**

- [ ] **Step 5.4: commit**

```bash
git add frontend/src/api/external-sync.ts frontend/src/pages/settings/CompanySettings.vue
git commit -m "feat(G40): 前端 CompanySettings 同步按钮 + 同步 API"
```

---

## Plan E 完成验证

- [ ] `npm test` 通过 (目标 342 + 5 = 347+)
- [ ] `cd frontend && npx vue-tsc --noEmit` 通过
- [ ] 5 个新 commit
- [ ] `node -e "import('./src/services/integration/mock-moka.adapter.js').then(m => console.log(m.default.systemName))"` 输出 `MOKA`
- [ ] docs/CHANGELOG.md 加 "P1-E 完成: G40 法人公司同步脚手架 (等待企业 API 授权)"
