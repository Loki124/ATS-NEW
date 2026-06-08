# Plan C: 面试 + Offer 增强 (G19 + G26)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 面试历史评价自动预填 (G19) + Offer 手动背调 4 等级 + 报告 (G26)

**Architecture:**
- **G19**: 在 `InterviewFeedback` 提交时, 自动从该候选人的历史反馈聚合预填 `previousFeedback` 字段, 新增 `interview-history.service.js` 做聚合
- **G26**: 扩展 `BackgroundCheckRecord` (已有表) 加 4 等级 (PASS/WARN/FAIL/INCONCLUSIVE) + PDF 报告生成, 复用 `pdf-generator.service.js`

**Tech Stack:** Prisma 5 + MySQL 9, 复用现有 interview-state-machine + pdf-generator

---

## DoD
- [ ] 2 个新 service: interview-history + background-check
- [ ] G19: ≥ 8 个单测 (历史聚合, 预填逻辑, 边界)
- [ ] G26: ≥ 10 个单测 (4 等级转换, PDF 报告, 报告模板)
- [ ] G26 PDF 服务端生成 (复用 pdf-generator, 不引入新依赖)
- [ ] 6 个新 API: G19 history get + G26 background check CRUD + report download
- [ ] 前端: InterviewFeedbackForm.vue 加历史反馈预览面板 + Offer 详情加背调标签页
- [ ] `npm test` 通过 (310 + 18 = 328+ 测试)

---

## Task 1: G19 interview-history 聚合服务

**Files:**
- Create: `backend/src/services/interview-history.service.js`
- Create: `backend/src/services/__tests__/interview-history.service.test.js`

- [ ] **Step 1.1: 写失败测试 (8 个)**

```js
// backend/src/services/__tests__/interview-history.service.test.js
import { describe, it, expect, vi } from '@jest/globals';

vi.mock('@prisma/client', () => ({
  PrismaClient: class {
    interviewFeedback = { findMany: vi.fn() };
    interview = { findMany: vi.fn() };
  }
}));

import { prisma } from '../../app.js';
import {
  getCandidateHistory,
  aggregateHistory,
  buildPreviousFeedbackString,
  shouldAutoPrefill,
} from '../interview-history.service.js';

describe('interview-history', () => {
  it('aggregateHistory 聚合 3 个反馈, 统计 pass/fail', () => {
    const feedbacks = [
      { result: 'PASS', reason: '技术扎实' },
      { result: 'PASS', reason: '沟通好' },
      { result: 'FAIL', reason: '深度不够' },
    ];
    const summary = aggregateHistory(feedbacks);
    expect(summary.passCount).toBe(2);
    expect(summary.failCount).toBe(1);
    expect(summary.total).toBe(3);
  });

  it('aggregateHistory 空数组 → 全 0', () => {
    const s = aggregateHistory([]);
    expect(s).toEqual({ passCount: 0, failCount: 0, total: 0 });
  });

  it('buildPreviousFeedbackString 中文模板', () => {
    const str = buildPreviousFeedbackString({
      passCount: 2, failCount: 1, total: 3,
      feedbacks: [
        { roundName: 'HR初筛', interviewerName: 'Alice', result: 'PASS', reason: '沟通好' },
        { roundName: '技术一面', interviewerName: 'Bob',   result: 'PASS', reason: '基础扎实' },
        { roundName: '技术二面', interviewerName: 'Carol', result: 'FAIL', reason: '深度不够' },
      ]
    });
    expect(str).toContain('HR初筛');
    expect(str).toContain('PASS');
    expect(str).toContain('深度不够');
  });

  it('shouldAutoPrefill 候选人有 ≥1 历史 → true', () => {
    expect(shouldAutoPrefill({ total: 1 })).toBe(true);
  });

  it('shouldAutoPrefill 无历史 → false', () => {
    expect(shouldAutoPrefill({ total: 0 })).toBe(false);
  });

  it('getCandidateHistory 返回结构化历史', async () => {
    prisma.interviewFeedback.findMany.mockResolvedValueOnce([
      { id: 'f1', result: 'PASS', reason: '好', interview: { roundName: '一面' }, interviewerName: 'A', feedbackAt: new Date() }
    ]);
    const h = await getCandidateHistory('c1');
    expect(h.total).toBe(1);
    expect(h.feedbacks).toHaveLength(1);
  });

  it('getCandidateHistory SQL 包含 candidateId 过滤', async () => {
    await getCandidateHistory('c-123');
    const call = prisma.interviewFeedback.findMany.mock.calls[0][0];
    expect(JSON.stringify(call.where)).toContain('c-123');
  });

  it('历史聚合按时间倒序', async () => {
    prisma.interviewFeedback.findMany.mockResolvedValueOnce([
      { id: '1', result: 'PASS', feedbackAt: new Date('2025-01-01'), interview: { roundName: 'A' }, interviewerName: 'X' },
      { id: '2', result: 'FAIL', feedbackAt: new Date('2025-03-01'), interview: { roundName: 'B' }, interviewerName: 'Y' },
    ]);
    const h = await getCandidateHistory('c1');
    expect(h.feedbacks[0].id).toBe('2');
  });
});
```

- [ ] **Step 1.2: 跑测试, 确认失败**

```bash
npm test -- interview-history
```
Expected: FAIL

- [ ] **Step 1.3: 实现服务**

```js
// backend/src/services/interview-history.service.js
// G19 - 面试历史评价自动预填

import { prisma } from '../app.js';

export function aggregateHistory(feedbacks) {
  if (!feedbacks?.length) return { passCount: 0, failCount: 0, total: 0 };
  return {
    passCount: feedbacks.filter(f => f.result === 'PASS').length,
    failCount: feedbacks.filter(f => f.result === 'FAIL').length,
    total: feedbacks.length,
  };
}

export function shouldAutoPrefill(summary) {
  return summary.total > 0;
}

export function buildPreviousFeedbackString({ passCount, failCount, total, feedbacks }) {
  if (total === 0) return '';
  const lines = [
    `【历史评价汇总】共 ${total} 次面试, ${passCount} 次通过, ${failCount} 次未通过`,
    '',
  ];
  for (const f of feedbacks) {
    const tag = f.result === 'PASS' ? '✅' : '❌';
    const reason = f.reason ? ` - ${f.reason}` : '';
    lines.push(`${tag} ${f.interview?.roundName || f.roundName || '面试'} · ${f.interviewerName} · ${f.result}${reason}`);
  }
  return lines.join('\n');
}

/**
 * 获取候选人所有历史面试反馈
 */
export async function getCandidateHistory(candidateId) {
  const feedbacks = await prisma.interviewFeedback.findMany({
    where: { interview: { application: { candidateId } } },
    include: { interview: { include: { interview: { include: { round: true } } } } },
    orderBy: { feedbackAt: 'desc' },
  });
  // 标准化: roundName 取 interview.roundName
  const normalized = feedbacks.map(f => ({
    id: f.id,
    result: f.result,
    reason: f.reason,
    interviewerName: f.interviewerName,
    feedbackAt: f.feedbackAt,
    roundName: f.interview?.roundName || '面试',
  }));
  const summary = aggregateHistory(normalized);
  const previousFeedback = buildPreviousFeedbackString({ ...summary, feedbacks: normalized });
  return { ...summary, previousFeedback, feedbacks: normalized };
}
```

- [ ] **Step 1.4: 跑测试通过**

```bash
npm test -- interview-history
```
Expected: 8 passed

- [ ] **Step 1.5: commit**

```bash
git add backend/src/services/interview-history.service.js backend/src/services/__tests__/interview-history.service.test.js
git commit -m "feat(G19): 面试历史评价聚合服务 (8 测试)"
```

---

## Task 2: G19 提交反馈时自动预填

**Files:**
- Modify: `backend/src/routes/interview.routes.js`

- [ ] **Step 2.1: 在 feedback 提交前注入 history**

定位 `POST /api/interviews/:id/feedback` 端点 (现有), 在 handler 中先调 `getCandidateHistory` 再合并到 req.body.previousFeedback:

```js
import { getCandidateHistory } from '../services/interview-history.service.js';

router.post('/:id/feedback', async (req, res, next) => {
  try {
    const { id } = req.params;
    const interview = await prisma.interview.findUnique({
      where: { id },
      include: { application: true },
    });
    if (!interview) throw new AppError('面试不存在', 404);

    // G19: 自动预填历史反馈 (如果前端没传)
    if (!req.body.previousFeedback) {
      const history = await getCandidateHistory(interview.application.candidateId);
      if (history.total > 0) {
        req.body.previousFeedback = history.previousFeedback;
        req.body.viewedPrevious = false;
      }
    }

    // ... 现有 feedback 创建逻辑 ...
    res.json({ success: true, data: createdFeedback, prefilled: !!req.body.previousFeedback });
  } catch (err) { next(err); }
});
```

- [ ] **Step 2.2: 加 GET /history/:candidateId 端点 (供前端预览)**

```js
router.get('/history/:candidateId', async (req, res, next) => {
  try {
    const history = await getCandidateHistory(req.params.candidateId);
    res.json({ success: true, data: history });
  } catch (err) { next(err); }
});
```

- [ ] **Step 2.3: 验证**

```bash
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5125/api/interviews/history/<candidateId>
```
Expected: 返回 history 对象 (即使 total=0)

- [ ] **Step 2.4: commit**

```bash
git add backend/src/routes/interview.routes.js
git commit -m "feat(G19): 提交反馈时自动预填历史 (新增 GET /history/:candidateId)"
```

---

## Task 3: G26 schema 扩展 (4 等级 + 报告)

**Files:**
- Modify: `backend/prisma/schema.prisma` (BackgroundCheckRecord 加 level + 附件字段)

- [ ] **Step 3.1: 加字段**

`BackgroundCheckRecord` model 中追加 (在 status 之后):
```prisma
  // G26 - 4 等级背调
  // PASS  通过 / WARN  有小问题但可接受 / FAIL 不通过 / INCONCLUSIVE 资料不足
  level   String?  @db.VarChar(16)

  // 报告附件 (PDF, 存服务器路径, 不放二进制)
  reportPath String?  @db.VarChar(255)
  reportUrl  String?  @db.VarChar(255)
  reportSize Int?     // bytes

  // 评分 (0-100, 自动按 level 映射)
  score    Int?

  // 风险项 (JSON 数组: [{category, severity, description}])
  risks    Json?    @db.Json
```

- [ ] **Step 3.2: 推 schema**

```bash
cd backend
npx prisma db push --skip-generate
npx prisma generate
```

- [ ] **Step 3.3: commit**

```bash
git add backend/prisma/schema.prisma backend/prisma/migrations/
git commit -m "feat(G26): BackgroundCheckRecord 加 4 等级 level + 报告字段"
```

---

## Task 4: G26 background-check 服务

**Files:**
- Create: `backend/src/services/background-check.service.js`
- Create: `backend/src/services/__tests__/background-check.service.test.js`

- [ ] **Step 4.1: 写失败测试 (10 个)**

```js
// backend/src/services/__tests__/background-check.service.test.js
import { describe, it, expect, vi } from '@jest/globals';

vi.mock('@prisma/client', () => ({
  PrismaClient: class {
    backgroundCheckRecord = {
      findMany: vi.fn(),
      findUnique: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
    };
  }
}));

import { prisma } from '../../app.js';
import {
  BG_CHECK_LEVELS,
  validateLevelTransition,
  mapLevelToScore,
  isPassingLevel,
  buildReportData,
  listBackgroundChecks,
  createBackgroundCheck,
  completeBackgroundCheck,
} from '../background-check.service.js';

describe('background-check', () => {
  it('4 等级定义', () => {
    expect(Object.keys(BG_CHECK_LEVELS)).toHaveLength(4);
    expect(BG_CHECK_LEVELS.PASS.level).toBe('PASS');
  });

  it('validateLevelTransition ACTIVE→PASS 合法', () => {
    expect(validateLevelTransition('ACTIVE', 'PASS')).toBe(true);
  });

  it('validateLevelTransition ACTIVE→INCONCLUSIVE 合法', () => {
    expect(validateLevelTransition('ACTIVE', 'INCONCLUSIVE')).toBe(true);
  });

  it('validateLevelTransition PASS→ACTIVE 非法 (终态)', () => {
    expect(validateLevelTransition('PASS', 'ACTIVE')).toBe(false);
  });

  it('mapLevelToScore PASS=100, WARN=70, INCONCLUSIVE=50, FAIL=0', () => {
    expect(mapLevelToScore('PASS')).toBe(100);
    expect(mapLevelToScore('WARN')).toBe(70);
    expect(mapLevelToScore('INCONCLUSIVE')).toBe(50);
    expect(mapLevelToScore('FAIL')).toBe(0);
  });

  it('isPassingLevel PASS=true, WARN=true (可接受), FAIL=false', () => {
    expect(isPassingLevel('PASS')).toBe(true);
    expect(isPassingLevel('WARN')).toBe(true);
    expect(isPassingLevel('FAIL')).toBe(false);
    expect(isPassingLevel('INCONCLUSIVE')).toBe(false);
  });

  it('buildReportData 汇总 offer + 候选人 + 背调记录', () => {
    const data = buildReportData({
      offer: { id: 'o1', positionName: '工程师' },
      candidate: { name: '张三', phone: '13800138000' },
      record: { level: 'PASS', risks: [], completedAt: new Date() },
    });
    expect(data.title).toContain('背调报告');
    expect(data.sections).toBeDefined();
  });

  it('listBackgroundChecks 传 offerId 过滤', async () => {
    await listBackgroundChecks('offer-1');
    const call = prisma.backgroundCheckRecord.findMany.mock.calls[0][0];
    expect(call.where.offerId).toBe('offer-1');
  });

  it('createBackgroundCheck 默认 status=ACTIVE', async () => {
    prisma.backgroundCheckRecord.create.mockResolvedValueOnce({ id: 'b1', status: 'ACTIVE' });
    const r = await createBackgroundCheck({ offerId: 'o1', checkType: '学历' });
    expect(r.id).toBe('b1');
  });

  it('completeBackgroundCheck 写 level + score + 自动计算', async () => {
    prisma.backgroundCheckRecord.update.mockResolvedValueOnce({ id: 'b1', level: 'PASS', score: 100 });
    const r = await completeBackgroundCheck('b1', { level: 'PASS', risks: [] });
    expect(r.score).toBe(100);
  });
});
```

- [ ] **Step 4.2: 跑测试, 确认失败**

```bash
npm test -- background-check
```
Expected: FAIL

- [ ] **Step 4.3: 实现服务**

```js
// backend/src/services/background-check.service.js
// G26 - Offer 手动背调 (4 等级 + 报告)

import { prisma } from '../app.js';

export const BG_CHECK_LEVELS = {
  PASS:         { label: '通过',          color: 'success',  terminal: true,  riskAllowed: 0 },
  WARN:         { label: '有保留通过',    color: 'warning',  terminal: true,  riskAllowed: 3 },
  INCONCLUSIVE: { label: '资料不足',      color: 'info',     terminal: true,  riskAllowed: 0 },
  FAIL:         { label: '不通过',        color: 'error',    terminal: true,  riskAllowed: 999 },
};

const TRANSITIONS = {
  ACTIVE: ['PASS', 'WARN', 'INCONCLUSIVE', 'FAIL'],
  PASS: [],
  WARN: [],
  INCONCLUSIVE: [],
  FAIL: [],
};

export function validateLevelTransition(from, to) {
  return (TRANSITIONS[from] || []).includes(to);
}

export function mapLevelToScore(level) {
  return { PASS: 100, WARN: 70, INCONCLUSIVE: 50, FAIL: 0 }[level] ?? null;
}

export function isPassingLevel(level) {
  return level === 'PASS' || level === 'WARN';
}

export function buildReportData({ offer, candidate, record, supplier }) {
  return {
    title: `背调报告 - ${candidate?.name || ''}`,
    sections: [
      { heading: '基本信息', content: [
        { label: '候选人', value: candidate?.name },
        { label: 'Offer ID', value: offer?.id },
        { label: '背调供应商', value: supplier || record?.supplier || '内部' },
      ]},
      { heading: '背调结论', content: [
        { label: '等级', value: BG_CHECK_LEVELS[record.level]?.label || record.level },
        { label: '评分', value: record.score ?? '-' },
        { label: '完成时间', value: record.completedAt },
      ]},
      { heading: '风险项', content: record.risks || [] },
    ],
  };
}

export async function listBackgroundChecks(offerId) {
  return prisma.backgroundCheckRecord.findMany({
    where: { offerId, status: 'ACTIVE' },
    orderBy: { createdAt: 'desc' },
  });
}

export async function createBackgroundCheck({ offerId, checkType, supplier, note }) {
  return prisma.backgroundCheckRecord.create({
    data: { offerId, checkType, supplier, note, status: 'ACTIVE' },
  });
}

export async function completeBackgroundCheck(id, { level, risks, reportPath, reportUrl, reportSize }) {
  if (!validateLevelTransition('ACTIVE', level)) {
    throw new Error(`Invalid level transition to ${level}`);
  }
  return prisma.backgroundCheckRecord.update({
    where: { id },
    data: {
      level,
      score: mapLevelToScore(level),
      risks: risks || [],
      reportPath,
      reportUrl,
      reportSize,
      completedAt: new Date(),
    },
  });
}
```

- [ ] **Step 4.4: 跑测试通过**

```bash
npm test -- background-check
```
Expected: 10 passed

- [ ] **Step 4.5: commit**

```bash
git add backend/src/services/background-check.service.js backend/src/services/__tests__/background-check.service.test.js
git commit -m "feat(G26): 手动背调 4 等级服务 (10 测试)"
```

---

## Task 5: G26 PDF 报告生成 + API

**Files:**
- Modify: `backend/src/services/pdf-generator.service.js` (加 renderBackgroundCheckReport 函数)
- Modify: `backend/src/routes/offer.routes.js` (加 4 个端点)

- [ ] **Step 5.1: 复用 pdf-generator 加背调报告模板**

定位 pdf-generator.service.js, 添加:
```js
/**
 * G26 背调报告 PDF
 */
export function renderBackgroundCheckReport({ offer, candidate, record, supplier }) {
  const data = buildReportData({ offer, candidate, record, supplier });
  return renderPdf({
    title: data.title,
    sections: data.sections,
    watermark: '背调报告 - 内部使用',
  });
}
```

(`buildReportData` 从 background-check.service 导入; 如果 pdf-generator 是独立模块不互相 import, 直接复制 buildReportData 实现到 pdf-generator)

- [ ] **Step 5.2: 加 routes**

```js
// backend/src/routes/offer.routes.js
import {
  listBackgroundChecks, createBackgroundCheck,
  completeBackgroundCheck, buildReportData
} from '../services/background-check.service.js';
import { renderBackgroundCheckReport } from '../services/pdf-generator.service.js';
import fs from 'fs/promises';
import path from 'path';

// 列表
router.get('/:id/background-checks', async (req, res, next) => {
  try {
    const data = await listBackgroundChecks(req.params.id);
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

// 创建
router.post('/:id/background-checks', async (req, res, next) => {
  try {
    const data = await createBackgroundCheck({
      offerId: req.params.id,
      checkType: req.body.checkType,
      supplier: req.body.supplier,
      note: req.body.note,
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

// 完成 (写等级)
router.put('/:id/background-checks/:bid/complete', async (req, res, next) => {
  try {
    const data = await completeBackgroundCheck(req.params.bid, req.body);
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

// 下载报告 PDF
router.get('/:id/background-checks/:bid/report', async (req, res, next) => {
  try {
    const record = await prisma.backgroundCheckRecord.findUnique({ where: { id: req.params.bid } });
    if (!record?.level) throw new AppError('背调未完成', 400);
    const offer = await prisma.offer.findUnique({ where: { id: req.params.id }, include: { application: { include: { candidate: true } } } });
    const pdf = await renderBackgroundCheckReport({
      offer,
      candidate: offer.application.candidate,
      record,
    });
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `attachment; filename="bg-check-${req.params.bid}.pdf"`);
    res.send(pdf);
  } catch (err) { next(err); }
});
```

- [ ] **Step 5.3: 验证 PDF 端点**

```bash
curl -H "Authorization: Bearer $TOKEN" -o /tmp/test.pdf "http://127.0.0.1:5125/api/offers/<id>/background-checks/<bid>/report"
file /tmp/test.pdf
```
Expected: `PDF document, ...`

- [ ] **Step 5.4: commit**

```bash
git add backend/src/services/pdf-generator.service.js backend/src/routes/offer.routes.js
git commit -m "feat(G26): 背调 4 端点 + PDF 报告生成"
```

---

## Task 6: 前端 G19 历史预览面板

**Files:**
- Modify: `frontend/src/pages/interview/` (假设有 InterviewFeedbackForm.vue, 若无则新建)

- [ ] **Step 6.1: 找现有 feedback form 组件**

```bash
ls /Users/loki/VScodeWorkspace/frontend/src/pages/interview/
```

- [ ] **Step 6.2: 加历史预览面板**

在 form 上方加:
```vue
<n-card v-if="history && history.total > 0" title="历史评价预览" class="mb-4">
  <n-alert type="info" :show-icon="false">
    <pre>{{ history.previousFeedback }}</pre>
  </n-alert>
  <n-checkbox v-model:checked="viewedPrevious">
    我已阅读历史评价
  </n-checkbox>
</n-card>
```

script 部分:
```ts
import { getInterviewHistory } from '@/api/interview';
const history = ref<any>(null);
const viewedPrevious = ref(false);

onMounted(async () => {
  const candidateId = route.query.candidateId;
  if (candidateId) {
    history.value = await getInterviewHistory(candidateId);
  }
});
```

- [ ] **Step 6.3: 前端 API 加 getInterviewHistory**

```ts
// frontend/src/api/interview.ts
export const getInterviewHistory = (candidateId: string) =>
  api.get(`/interviews/history/${candidateId}`).then(r => r.data.data);
```

- [ ] **Step 6.4: vue-tsc 验证**

```bash
cd frontend && npx vue-tsc --noEmit
```

- [ ] **Step 6.5: commit**

```bash
git add frontend/src/pages/interview/ frontend/src/api/interview.ts
git commit -m "feat(G19): 前端历史评价预览面板"
```

---

## Task 7: 前端 G26 背调标签页

**Files:**
- Modify: `frontend/src/pages/offer/OfferDetail.vue` (或 OfferList.vue 加标签页入口)
- Modify: `frontend/src/api/offer.ts` (加 4 个函数)

- [ ] **Step 7.1: offer.ts API**

```ts
export const listBackgroundChecks = (offerId: string) =>
  api.get(`/offers/${offerId}/background-checks`).then(r => r.data.data);

export const createBackgroundCheck = (offerId: string, payload: any) =>
  api.post(`/offers/${offerId}/background-checks`, payload).then(r => r.data.data);

export const completeBackgroundCheck = (offerId: string, bid: string, payload: any) =>
  api.put(`/offers/${offerId}/background-checks/${bid}/complete`, payload).then(r => r.data.data);

export const downloadBackgroundCheckReport = (offerId: string, bid: string) =>
  api.get(`/offers/${offerId}/background-checks/${bid}/report`, { responseType: 'blob' });
```

- [ ] **Step 7.2: OfferDetail.vue 加 n-tabs**

```vue
<n-tabs default-value="info">
  <n-tab-pane name="info" tab="基本信息"> ... </n-tab-pane>
  <n-tab-pane name="bg-check" tab="背调">
    <BackgroundCheckPanel :offer-id="offerId" />
  </n-tab-pane>
</n-tabs>
```

`BackgroundCheckPanel.vue` 组件:
- 列表 + 4 等级选择器 (NSelect)
- "新建背调" 按钮 → 弹窗 (checkType + supplier)
- "完成" 按钮 → 弹窗 (level + risks JSON)
- "下载报告" 链接

- [ ] **Step 7.3: vue-tsc 验证**

- [ ] **Step 7.4: commit**

```bash
git add frontend/src/pages/offer/ frontend/src/api/offer.ts
git commit -m "feat(G26): 前端 Offer 详情 + 背调标签页 + 4 等级选择"
```

---

## Plan C 完成验证

- [ ] `npm test` 通过 (目标 310 + 18 = 328+)
- [ ] `cd frontend && npx vue-tsc --noEmit` 通过
- [ ] 7 个新 commit
- [ ] 跨计划接口联调: G19 评价预填能用 G44 状态 (Plan A 完成是前提)
- [ ] G26 PDF 文件 `file` 命令验证是 PDF
- [ ] CHANGELOG.md 加 "P1-C 完成: G19 历史评价 + G26 手动背调 4 等级"
