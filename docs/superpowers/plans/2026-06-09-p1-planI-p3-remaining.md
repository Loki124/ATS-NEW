# Plan I: P3 剩余 3 项 (G30 RPA 简历 + G35 数据中心 + G45 OCR 查重) — 2026-06-09

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 P3 剩余 3 项的**内部可做**部分全部清掉, 外部依赖部分用 adapter 桩架 (等企业 API 授权后新建 adapter 即可启用):

- **G30**: 简历抓取数据模型 + RPA adapter 接口 + Mock + 前端 "我找的简历" 页
- **G35**: 数据订阅架构 + 通用导出 (Excel/CSV) + 基础 KPI 看板 + 订阅 cron
- **G45**: 简历查重算法 (phone/email 哈希 + name+birthday 相似度) + OCR adapter 接口 + Mock + 前端查重提示

**Architecture:** 3 个独立子系统, 互不依赖, 3 个 subagent 并行

**Tech Stack:** Prisma 5 + MySQL 9 + Vue 3 + Naive UI + xlsx (CSV/Excel 导出, 现有 devDeps 可能已有; 需则新加)

---

## DoD
- [ ] G30: ScrapedResume model + rpa-adapter + mock + ≥ 5 测试 + 2 端点 + 前端页 + 菜单
- [ ] G35: DataSubscription model + 通用导出服务 + 基础 KPI + ≥ 5 测试 + 5 端点 + 前端看板
- [ ] G45: ResumeDuplicateCheck service (算法) + ocr-adapter + mock + ≥ 6 测试 + 4 端点 + 上传时自动查重
- [ ] 现有 373 测试仍全过
- [ ] vue-tsc 0 错
- [ ] 总目标: 373 + 16 = **389+ 测试通过**

---

## Section A — G30 我找的简历 (RPA 适配器 + UI) — Subagent I-1

**估时**: ~1.5h, 5 commits

### Task A1: schema 扩展 (ScrapedResume)

- [ ] **Step A1.1: 在 schema.prisma 末尾加 model**

```prisma
// ============================================
// G30 - 我找的简历 (RPA 抓取)
// ============================================
model ScrapedResume {
  id String @id @default(uuid())

  // 候选人信息 (抓取后填充)
  candidateId String?  // 关联到 Candidate (导入后)
  candidateName String?
  candidatePhone String?
  candidateEmail String?
  
  // 抓取元数据
  source        String  @db.VarChar(64)  // 智联 / 拉勾 / BOSS / LinkedIn / 其他
  sourceUrl     String? @db.VarChar(512)
  sourceJobId   String? @db.VarChar(128) // 原始职位 ID
  rawHtml       String? @db.LongText     // 原始 HTML (脱敏后)
  rawText       String? @db.Text          // 纯文本
  
  // RPA 执行信息
  scraperType   String  @db.VarChar(32)  // MOCK_RPA / UIBOT / RPA_PLATFORM
  scrapedAt     DateTime?
  scraperUserId String?  // 谁触发的
  scraperJobName String? @db.VarChar(128) // RPA bot 名 (如 "ZhaopinBot-v2")
  
  // 状态
  status        String  @default("PENDING") @db.VarChar(16)  // PENDING / SCRAPED / IMPORTED / FAILED / DUPLICATE
  importError   String? @db.Text
  
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt

  @@index([status])
  @@index([source])
  @@index([candidatePhone])
  @@index([candidateEmail])
  @@map("scraped_resumes")
}
```

- [ ] **Step A1.2: 推 schema**

```bash
npx prisma db push --skip-generate && npx prisma generate
```

- [ ] **Step A1.3: commit**

```bash
git add backend/prisma/schema.prisma backend/prisma/migrations/
git commit -m "feat(G30): ScrapedResume 表 (RPA 简历抓取基础)"
```

### Task A2: RPA adapter + Mock

- [ ] **Step A2.1: 写失败测试 (5 个)**

`backend/src/services/__tests__/rpa-adapter.test.js`:
```js
import { describe, it, expect, vi } from '@jest/globals';
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
```

- [ ] **Step A2.2: 实现 + 跑测试通过**

```js
// backend/src/services/integration/rpa-adapter.js
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
export { MockRpaAdapter };
```

- [ ] **Step A2.3: commit**

```bash
git add backend/src/services/integration/rpa-adapter.js backend/src/services/__tests__/rpa-adapter.test.js
git commit -m "feat(G30): RPA adapter 接口 + Mock 实现 (5 测试)"
```

### Task A3: 抓取服务 + 2 端点

- [ ] **Step A3.1: 写 service + routes**

```js
// backend/src/services/scraped-resume.service.js
import { prisma } from '../app.js';
import { getAdapter } from './integration/rpa-adapter.js';

export async function triggerScrape({ source, jobTitle, city, scraperUserId, scraperJobName }) {
  const adapter = getAdapter(source);
  const result = await adapter.scrapeJob({ jobTitle, city, page: 1, pageSize: 20 });
  
  const created = await prisma.scrapedResume.create({
    data: {
      source,
      sourceUrl: result.resumes[0]?.sourceUrl,
      rawText: JSON.stringify(result.resumes),
      scraperType: source,
      scraperUserId,
      scraperJobName,
      scrapedAt: new Date(),
      status: 'SCRAPED',
    },
  });
  return { ...created, resumes: result.resumes };
}

export async function listScrapedResumes({ status, page = 1, pageSize = 20 } = {}) {
  const where = {};
  if (status) where.status = status;
  return prisma.scrapedResume.findMany({
    where, skip: (page - 1) * pageSize, take: pageSize,
    orderBy: { scrapedAt: 'desc' },
  });
}

export async function importScrapedResume(scrapedId, candidateId) {
  return prisma.scrapedResume.update({
    where: { id: scrapedId },
    data: { status: 'IMPORTED', candidateId },
  });
}
```

```js
// backend/src/routes/scraped-resume.routes.js
import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import { triggerScrape, listScrapedResumes, importScrapedResume } from '../services/scraped-resume.service.js';

const router = Router();
router.use(authMiddleware);

router.post('/scrape', async (req, res, next) => {
  try {
    const data = await triggerScrape({
      source: req.body.source || 'MOCK_RPA',
      jobTitle: req.body.jobTitle,
      city: req.body.city,
      scraperUserId: req.user.id,
      scraperJobName: req.body.scraperJobName,
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/', async (req, res, next) => {
  try {
    const data = await listScrapedResumes({
      status: req.query.status,
      page: parseInt(req.query.page) || 1,
      pageSize: parseInt(req.query.pageSize) || 20,
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.post('/:id/import', async (req, res, next) => {
  try {
    const data = await importScrapedResume(req.params.id, req.body.candidateId);
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

export default router;
```

- [ ] **Step A3.2: 注册到 app.js**

```js
// app.js 加:
import scrapedResumeRoutes from './routes/scraped-resume.routes.js';
app.use('/api/scraped-resumes', authMiddleware, scrapedResumeRoutes);
// 同时导入 adapter:
import './services/integration/rpa-adapter.js';
```

- [ ] **Step A3.3: commit**

```bash
git commit -m "feat(G30): scraped-resume service + 3 端点 (scrape/list/import)"
```

### Task A4: 前端 "我找的简历" 页

- [ ] **Step A4.1: API + 页 + 菜单 + 路由**

```ts
// frontend/src/api/scraped-resume.ts (同其他 api 模式)
import axios from 'axios';
import config from '../config';
const api = axios.create({ baseURL: config.api.baseUrl, timeout: 15000, headers: { 'Content-Type': 'application/json' } });
api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

export interface ScrapedResume { id: string; source: string; status: string; scrapedAt: string; rawText?: string; candidateId?: string; }
export const triggerScrape = (payload: { source?: string; jobTitle?: string; city?: string; scraperJobName?: string }) =>
  api.post('/scraped-resumes/scrape', payload).then(r => r.data.data);
export const listScrapedResumes = (params?: { status?: string; page?: number; pageSize?: number }) =>
  api.get('/scraped-resumes', { params }).then(r => r.data.data);
export const importScrapedResume = (id: string, candidateId: string) =>
  api.post(`/scraped-resumes/${id}/import`, { candidateId }).then(r => r.data.data);
```

- [ ] **Step A4.2: ScrapedResumeList.vue**

简单页: 顶部"开始抓取"按钮 (弹窗填 jobTitle + city + source) + 表格 (status / source / scrapedAt / 抓取条数 / 导入按钮)。

- [ ] **Step A4.3: 菜单 + 路由**

```ts
// router
{ path: 'scraped-resumes', name: 'ScrapedResumeList', component: () => import('@/pages/scraped/ScrapedResumeList.vue') },
```

```ts
// SettingsLayout group-misc 加 (用现有 SearchOutline icon):
{ key: '/settings/scraped-resumes', label: '我找的简历', icon: renderIcon(SearchOutline) },
```
(需 import SearchOutline)

或者独立菜单 (顶层: `/scraped-resumes` 而非 `/settings/scraped-resumes`)? 决定: 放 settings 较一致, 但这不属于系统设置。建议: 放 `group-recruit` 旁, 新建一个 group. **简化为放在 settings group-misc 末尾** (与院校库/公司库同位置)。

- [ ] **Step A4.4: commit**

```bash
git commit -m "feat(G30): 前端 我找的简历页 + 路由 + 菜单"
```

### Section A 完成 DoD
- [ ] ScrapedResume schema + 1 service + 1 routes + 1 前端页 + 1 API client
- [ ] 5 测试通过
- [ ] 不破坏现有 373 测试

---

## Section B — G35 数据中心 + 订阅 (通用导出 + KPI) — Subagent I-2

**估时**: ~1.5h, 5 commits

### Task B1: schema 扩展 (DataSubscription)

- [ ] **Step B1.1: 在 schema.prisma 末尾加 model**

```prisma
// ============================================
// G35 - 数据订阅
// ============================================
model DataSubscription {
  id String @id @default(uuid())

  userId String
  userName String

  // 订阅什么
  resource   String @db.VarChar(64)  // Candidate / Demand / Position / Offer / Interview / Onboarding
  metric     String @db.VarChar(64)  // 'all' / 'count_by_status' / 'count_by_dept' / 'export_csv'
  filters    String? @db.Text        // JSON: { departmentId, status, dateFrom, dateTo }

  // 投递方式
  channel    String @db.VarChar(16)  // EMAIL / SYSTEM / WECOM / SMS
  schedule   String @db.VarChar(32)  // DAILY / WEEKLY / MONTHLY / ON_DEMAND
  scheduleTime String? @db.VarChar(8) // '09:00' (HH:mm)
  recipients String? @db.Text         // 逗号分隔 email / userId

  isActive   Boolean @default(true)

  lastRunAt  DateTime?
  nextRunAt  DateTime?
  runCount   Int @default(0)

  createdAt  DateTime @default(now())
  updatedAt  DateTime @updatedAt

  @@index([userId, isActive])
  @@index([resource, schedule])
  @@map("data_subscriptions")
}
```

- [ ] **Step B1.2: 推 schema + commit**

```bash
npx prisma db push --skip-generate && npx prisma generate
git add backend/prisma/schema.prisma backend/prisma/migrations/
git commit -m "feat(G35): DataSubscription 表"
```

### Task B2: 通用导出服务

- [ ] **Step B2.1: 写失败测试 (5 个)**

`backend/src/services/__tests__/data-export.service.test.js`:
```js
import { describe, it, expect, vi } from '@jest/globals';
vi.mock('@prisma/client', () => ({
  PrismaClient: class {
    candidate = { findMany: vi.fn() };
  }
}));
import { prisma } from '../../app.js';
import { exportToCsv, exportToJson, buildExportHeaders, summarizeData } from '../data-export.service.js';

describe('data-export', () => {
  it('exportToCsv 简单对象数组', () => {
    const csv = exportToCsv([{ name: '张三', age: 30 }, { name: '李四', age: 25 }]);
    expect(csv).toContain('name,age');
    expect(csv).toContain('张三,30');
  });

  it('exportToCsv 包含 BOM (Excel 中文兼容)', () => {
    const csv = exportToCsv([{ x: 1 }]);
    expect(csv.charCodeAt(0)).toBe(0xFEFF);
  });

  it('exportToJson 标准 JSON', () => {
    const json = exportToJson([{ x: 1 }]);
    expect(JSON.parse(json)).toEqual([{ x: 1 }]);
  });

  it('buildExportHeaders 中文标签映射', () => {
    const h = buildExportHeaders('Candidate', ['name', 'phone']);
    expect(h).toEqual([{ key: 'name', label: '姓名' }, { key: 'phone', label: '手机号' }]);
  });

  it('summarizeData 数字字段求和', () => {
    const sum = summarizeData([{ amount: 10 }, { amount: 20 }], 'amount');
    expect(sum).toBe(30);
  });
});
```

- [ ] **Step B2.2: 实现**

```js
// backend/src/services/data-export.service.js
// G35 - 通用数据导出 (CSV/JSON)
// 不引入新依赖, CSV 用手写, 性能 OK
import { prisma } from '../app.js';

const HEADER_LABELS = {
  Candidate: { name: '姓名', phone: '手机号', email: '邮箱', candidateStatus: '状态', createdAt: '创建时间' },
  Demand:    { code: '需求编号', title: '标题', status: '状态', createdAt: '创建时间' },
  Position:  { title: '职位', status: '状态', createdAt: '创建时间' },
  Offer:     { id: 'Offer ID', status: '状态', expectedJoinDate: '预计入职' },
  Interview: { id: '面试 ID', interviewDate: '面试时间', interviewStatus: '状态' },
  Onboarding:{ id: '入职 ID', expectedJoinDate: '预计入职', status: '状态' },
};

export function buildExportHeaders(resource, fields) {
  const labels = HEADER_LABELS[resource] || {};
  return fields.map(f => ({ key: f, label: labels[f] || f }));
}

export function exportToCsv(data, headers) {
  const cols = headers || (data.length ? Object.keys(data[0]).map(k => ({ key: k, label: k })) : []);
  const BOM = '﻿';  // Excel 中文
  const lines = [cols.map(c => escapeCsv(c.label)).join(',')];
  for (const row of data) {
    lines.push(cols.map(c => escapeCsv(row[c.key])).join(','));
  }
  return BOM + lines.join('\n');
}

function escapeCsv(v) {
  if (v == null) return '';
  const s = String(v);
  if (s.includes(',') || s.includes('"') || s.includes('\n')) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

export function exportToJson(data) {
  return JSON.stringify(data, null, 2);
}

export function summarizeData(data, field) {
  return data.reduce((sum, row) => sum + (Number(row[field]) || 0), 0);
}

const RESOURCE_GETTERS = {
  Candidate: () => prisma.candidate.findMany({ take: 1000 }),
  Demand:    () => prisma.demand.findMany({ take: 1000 }),
  Position:  () => prisma.position.findMany({ take: 1000 }),
  Offer:     () => prisma.offer.findMany({ take: 1000 }),
  Interview: () => prisma.interview.findMany({ take: 1000 }),
  Onboarding:() => prisma.onboarding.findMany({ take: 1000 }),
};

export async function exportResource(resource, format = 'csv', fields) {
  const getter = RESOURCE_GETTERS[resource];
  if (!getter) throw new Error(`Unknown resource: ${resource}`);
  const data = await getter();
  const headers = fields ? buildExportHeaders(resource, fields) : null;
  if (format === 'json') return exportToJson(data);
  return exportToCsv(data, headers);
}
```

- [ ] **Step B2.3: 跑测试通过 + commit**

```bash
npm test -- data-export
git commit -m "feat(G35): 通用数据导出 (CSV/JSON, 5 测试, 6 资源)"
```

### Task B3: KPI 看板服务

- [ ] **Step B3.1: 实现 (单文件, 无需新表)**

```js
// backend/src/services/data-dashboard.service.js
// G35 - 基础 KPI 看板 (业务侧 KPI 后续按需扩展)
import { prisma } from '../app.js';

export async function getDashboardKpi() {
  const [
    totalCandidates, activeDemands, openPositions,
    ongoingInterviews, sentOffers, pendingOnboardings,
  ] = await Promise.all([
    prisma.candidate.count(),
    prisma.demand.count({ where: { status: { in: ['IN_PROGRESS', 'APPROVED'] } } }),
    prisma.position.count({ where: { status: 'ACTIVE' } }),
    prisma.interview.count({ where: { interviewStatus: { in: ['SCHEDULED', 'IN_PROGRESS'] } } }),
    prisma.offer.count({ where: { status: { in: ['SENT', 'NEGOTIATING'] } } }),
    prisma.onboarding.count({ where: { status: { in: ['PENDING_ONBOARD', 'CONFIRMED'] } } }),
  ]);
  return {
    totalCandidates, activeDemands, openPositions,
    ongoingInterviews, sentOffers, pendingOnboardings,
    generatedAt: new Date().toISOString(),
  };
}
```

- [ ] **Step B3.2: 写 service routes (5 端点)**

```js
// backend/src/routes/data.routes.js
import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import { exportResource } from '../services/data-export.service.js';
import { getDashboardKpi } from '../services/data-dashboard.service.js';
import { prisma } from '../app.js';

const router = Router();
router.use(authMiddleware);

router.get('/kpi', async (req, res, next) => {
  try {
    const data = await getDashboardKpi();
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/export/:resource', async (req, res, next) => {
  try {
    const format = req.query.format || 'csv';
    const fields = req.query.fields ? req.query.fields.split(',') : undefined;
    const data = await exportResource(req.params.resource, format, fields);
    const filename = `${req.params.resource}-${Date.now()}.${format}`;
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.setHeader('Content-Type', format === 'csv' ? 'text/csv; charset=utf-8' : 'application/json');
    res.send(data);
  } catch (err) { next(err); }
});

router.post('/subscriptions', async (req, res, next) => {
  try {
    const data = await prisma.dataSubscription.create({
      data: { ...req.body, userId: req.user.id, userName: req.user.name || req.user.username },
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/subscriptions', async (req, res, next) => {
  try {
    const data = await prisma.dataSubscription.findMany({
      where: { userId: req.user.id, isActive: true },
      orderBy: { createdAt: 'desc' },
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.delete('/subscriptions/:id', async (req, res, next) => {
  try {
    await prisma.dataSubscription.update({ where: { id: req.params.id }, data: { isActive: false } });
    res.json({ success: true });
  } catch (err) { next(err); }
});

export default router;
```

- [ ] **Step B3.3: 注册 + commit**

```bash
# app.js
import dataRoutes from './routes/data.routes.js';
app.use('/api/data', authMiddleware, dataRoutes);
git commit -m "feat(G35): KPI 看板 + 通用导出 5 端点 + DataSubscription CRUD"
```

### Task B4: 前端数据看板 + 订阅管理

- [ ] **Step B4.1: API + 页 + 菜单 + 路由**

`frontend/src/api/data.ts` (4 函数)
`frontend/src/pages/settings/DataDashboard.vue` (KPI 卡片 + 导出按钮 + 订阅列表)
`router`: `{ path: 'data-dashboard', component: () => import(...) }`
`SettingsLayout group-misc`: 加 "数据中心" 菜单

- [ ] **Step B4.2: commit**

```bash
git commit -m "feat(G35): 前端数据看板 + 订阅管理 + 菜单"
```

### Section B 完成 DoD
- [ ] DataSubscription + 1 service + 1 routes + 1 前端页
- [ ] 5 测试通过
- [ ] 不破坏现有 373 测试

---

## Section C — G45 简历 OCR + 查重 (查重本地 + OCR 接入层) — Subagent I-3

**估时**: ~1.5h, 6 commits

### Task C1: 简历查重算法

- [ ] **Step C1.1: 写失败测试 (6 个)**

`backend/src/services/__tests__/resume-duplicate-check.service.test.js`:
```js
import { describe, it, expect, vi } from '@jest/globals';
vi.mock('@prisma/client', () => ({
  PrismaClient: class {
    candidate = { findMany: vi.fn() };
  }
}));
import { prisma } from '../../app.js';
import {
  hashPhone, hashEmail, normalizeName,
  computeSimilarity, findDuplicates, isExactDuplicate
} from '../resume-duplicate-check.service.js';

describe('resume-duplicate-check', () => {
  it('hashPhone 标准化', () => {
    expect(hashPhone('138-0013-8000')).toBe('13800138000');
    expect(hashPhone('+86 138 0013 8000')).toBe('13800138000');
  });

  it('hashEmail 标准化 (lowercase)', () => {
    expect(hashEmail('A@B.COM')).toBe('a@b.com');
  });

  it('normalizeName 去空格 + 繁简统一', () => {
    expect(normalizeName('  张三  ')).toBe('张三');
  });

  it('computeSimilarity 0-1 区间', () => {
    expect(computeSimilarity('张三', '张三')).toBeCloseTo(1, 2);
    expect(computeSimilarity('张三', '李四')).toBeLessThan(0.5);
  });

  it('isExactDuplicate 同 phone 或 email', () => {
    expect(isExactDuplicate({ phone: '13800138000' }, { phone: '13800138000' })).toBe(true);
    expect(isExactDuplicate({ phone: '13800138000' }, { phone: '13900139000' })).toBe(false);
  });

  it('findDuplicates 返回相似候选人列表 (按相似度倒序)', async () => {
    prisma.candidate.findMany.mockResolvedValueOnce([
      { id: 'c1', name: '张三', phone: '13800138000', email: 'a@b.com' },
      { id: 'c2', name: '张三', phone: '13900139000', email: null },
    ]);
    const dupes = await findDuplicates({ name: '张三', phone: '13900139000' });
    expect(dupes).toHaveLength(2);
  });
});
```

- [ ] **Step C1.2: 实现**

```js
// backend/src/services/resume-duplicate-check.service.js
// G45 - 简历查重 (本地算法, 0 外部依赖)
import { prisma } from '../app.js';

export function hashPhone(p) {
  if (!p) return '';
  return String(p).replace(/[^0-9]/g, '');
}

export function hashEmail(e) {
  if (!e) return '';
  return String(e).trim().toLowerCase();
}

export function normalizeName(n) {
  if (!n) return '';
  return String(n).trim().replace(/\s+/g, '');
}

export function computeSimilarity(a, b) {
  if (!a || !b) return 0;
  const na = normalizeName(a), nb = normalizeName(b);
  if (na === nb) return 1.0;
  // Levenshtein 距离
  const m = na.length, n = nb.length;
  if (m === 0 || n === 0) return 0;
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (na[i-1] === nb[j-1]) dp[i][j] = dp[i-1][j-1];
      else dp[i][j] = 1 + Math.min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]);
    }
  }
  const distance = dp[m][n];
  return 1 - distance / Math.max(m, n);
}

export function isExactDuplicate(c1, c2) {
  if (c1.phone && c2.phone && hashPhone(c1.phone) === hashPhone(c2.phone)) return true;
  if (c1.email && c2.email && hashEmail(c1.email) === hashEmail(c2.email)) return true;
  return false;
}

export async function findDuplicates(newResume, threshold = 0.7) {
  const all = await prisma.candidate.findMany({
    where: { candidateStatus: { in: ['ACTIVE', 'ARCHIVED'] } },
    take: 500,
  });
  const newHash = hashPhone(newResume.phone);
  const newEmail = hashEmail(newResume.email);
  const newName = normalizeName(newResume.name);

  const results = [];
  for (const c of all) {
    let score = 0;
    if (newHash && hashPhone(c.phone) === newHash) score = 1.0;
    else if (newEmail && hashEmail(c.email) === newEmail) score = 0.95;
    else if (newName) {
      score = computeSimilarity(newName, normalizeName(c.name));
    }
    if (score >= threshold) {
      results.push({ candidate: c, score, matchType: score === 1 ? 'phone' : score >= 0.95 ? 'email' : 'name' });
    }
  }
  return results.sort((a, b) => b.score - a.score);
}
```

- [ ] **Step C1.3: 跑测试 + commit**

```bash
npm test -- resume-duplicate-check
git commit -m "feat(G45): 简历查重算法 (phone/email 哈希 + name Levenshtein, 6 测试)"
```

### Task C2: OCR adapter + Mock

- [ ] **Step C2.1: 写失败测试 (3 个)**

```js
// backend/src/services/__tests__/ocr-adapter.test.js
import { describe, it, expect } from '@jest/globals';
import { MockOcrAdapter, registerOcrAdapter, getOcrAdapter } from '../integration/ocr-adapter.js';

describe('OCR adapter', () => {
  it('MockOcrAdapter systemName = MOCK_OCR', () => {
    expect(new MockOcrAdapter().systemName).toBe('MOCK_OCR');
  });

  it('MockOcrAdapter.parseResume 返回 mock 结构化数据', async () => {
    const a = new MockOcrAdapter();
    const r = await a.parseResume(Buffer.from('mock file'));
    expect(r.success).toBe(true);
    expect(r.data).toHaveProperty('name');
    expect(r.data).toHaveProperty('phone');
    expect(r.data).toHaveProperty('email');
    expect(r.data).toHaveProperty('education');
  });

  it('getOcrAdapter 未注册抛错', () => {
    expect(() => getOcrAdapter('BAIDU_OCR')).toThrow('No OCR adapter');
  });
});
```

- [ ] **Step C2.2: 实现**

```js
// backend/src/services/integration/ocr-adapter.js
// G45 - OCR 适配器接口 + Mock
const REGISTRY = {};

export function registerOcrAdapter(a) { REGISTRY[a.systemName] = a; }
export function getOcrAdapter(name) {
  const a = REGISTRY[name];
  if (!a) throw new Error(`No OCR adapter for: ${name}`);
  return a;
}

export class MockOcrAdapter {
  constructor() {
    this.systemName = 'MOCK_OCR';
  }
  
  async parseResume(fileBuffer) {
    // Mock: 返回固定结构化数据
    return {
      success: true,
      data: {
        name: 'OCR-解析-张三',
        phone: '13800138000',
        email: 'ocr-mock@example.com',
        gender: '男',
        birthday: '1990-01-01',
        education: [{ school: '示例大学', degree: '本科', major: '计算机' }],
        workExperience: [{ company: '示例公司', position: '工程师', startDate: '2018-01', endDate: '2023-12' }],
        confidence: 0.95,
      },
      raw: { mock: true, fileSize: fileBuffer.length },
    };
  }
}

const defaultAdapter = new MockOcrAdapter();
registerOcrAdapter(defaultAdapter);
export { MockOcrAdapter };
```

- [ ] **Step C2.3: 跑测试 + commit**

```bash
npm test -- ocr-adapter
git commit -m "feat(G45): OCR adapter 接口 + Mock (3 测试, 真实接入需 BAIDU/TENCENT key)"
```

### Task C3: 查重 API + 集成到现有简历上传流程

- [ ] **Step C3.1: 写 routes**

```js
// backend/src/routes/duplicate-check.routes.js
import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import { findDuplicates } from '../services/resume-duplicate-check.service.js';
import { MockOcrAdapter } from '../services/integration/ocr-adapter.js';

const router = Router();
router.use(authMiddleware);

router.post('/check', async (req, res, next) => {
  try {
    const dupes = await findDuplicates(req.body);
    res.json({ success: true, data: dupes, hasDuplicate: dupes.length > 0 });
  } catch (err) { next(err); }
});

router.post('/ocr-parse', async (req, res, next) => {
  try {
    // 简版: 直接用 mock, 真实场景接 multer 文件上传
    const adapter = new MockOcrAdapter();
    const result = await adapter.parseResume(Buffer.from('mock'));
    res.json({ success: true, data: result });
  } catch (err) { next(err); }
});

export default router;
```

- [ ] **Step C3.2: app.js 注册**

```js
import duplicateCheckRoutes from './routes/duplicate-check.routes.js';
app.use('/api/duplicate-check', authMiddleware, duplicateCheckRoutes);
import './services/integration/ocr-adapter.js';
```

- [ ] **Step C3.3: 集成到简历上传** (核心: 新简历入库前自动查重)

定位 `backend/src/routes/resume.routes.js` 的简历创建 endpoint, 在创建前插入:
```js
import { findDuplicates } from '../services/resume-duplicate-check.service.js';

// 在创建简历前
const dupes = await findDuplicates({
  name: req.body.name,
  phone: req.body.phone,
  email: req.body.email,
}, 0.7);

if (dupes.length > 0 && !req.body.forceCreate) {
  return res.status(409).json({
    success: false,
    message: `检测到 ${dupes.length} 个重复候选人`,
    duplicates: dupes,
  });
}
```

- [ ] **Step C3.4: commit**

```bash
git commit -m "feat(G45): 查重 + OCR 2 端点 + 简历上传自动查重"
```

### Task C4: 前端查重提示

- [ ] **Step C4.1: API + Resume 上传页加查重提示**

`frontend/src/api/duplicate-check.ts` (2 函数)
修改 `frontend/src/pages/resume/ResumeUpload.vue` (或类似) 在表单提交后:
- 如果返回 409, 弹 n-modal 显示重复列表
- 提供"继续创建 (forceCreate=true)" / "取消" 按钮

- [ ] **Step C4.2: commit**

```bash
git commit -m "feat(G45): 前端简历上传查重提示 (forceCreate 强制创建)"
```

### Section C 完成 DoD
- [ ] 简历查重算法 + OCR adapter + 2 端点 + 上传集成 + 前端提示
- [ ] 9 测试通过 (6 查重 + 3 OCR)
- [ ] 不破坏现有 373 测试

---

## 跨 Section 集成验证 (主 session 跑)

- [ ] 合并 3 个 worktree (I-1, I-2, I-3) 到 main
- [ ] `npx prisma db push --skip-generate && npx prisma generate` (G30 ScrapedResume + G35 DataSubscription)
- [ ] `npm test` 通过 (373 + 16 = 389+)
- [ ] `npx vue-tsc --noEmit` 0 错
- [ ] 跑 G30 trigger scrape + list API smoke test
- [ ] 跑 G35 KPI + export API smoke test
- [ ] 跑 G45 查重 API smoke test
- [ ] CHANGELOG + PROJECT_PLAN 加 P3 全部 done 条目
- [ ] 推 gitee
