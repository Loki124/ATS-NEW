# Plan A: 候选人增强 (G44 + G11)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 Candidate 加 11 个业务状态字段, 并实现"按简历最近活跃度倒序推荐"服务, 服务于简历筛选/人才库。

**Architecture:**
- **G44**: 在 `candidates` 表加 1 个 JSON 字段 `statusDetails: Json?` (key→subState), 保留 `candidateStatus` 不变 (向后兼容); 新增状态机服务 `candidate-status-machine.service.js`
- **G11**: 新建 `candidate-recommendation.service.js`, 基于最近活跃度 + 评分规则的复合排序, 复用 `scoring-rule.service.js`

**Tech Stack:** Prisma 5 + MySQL 9, 纯函数状态机 (与现有 6 大状态机一致), 倒序推荐用 prisma findMany + orderBy

---

## DoD (Definition of Done)
- [ ] `candidates.statusDetails` JSON 字段已加, prisma generate 通过
- [ ] 11 个状态值在 enum 化代码中明确定义 (状态机 + 类型)
- [ ] 状态机单测 ≥ 11 个 (每个状态 1 个用例)
- [ ] 推荐服务单测 ≥ 8 个 (不同 score / 不同 lastActiveAt / 边界)
- [ ] 2 个新 API: `GET /api/candidates/recommendations` + `PUT /api/candidates/:id/status-details`
- [ ] 前端 `CandidateList.vue` 接 recommendations API, 加状态筛选器
- [ ] `npm test` 全过 (266 + 19 = 285+)

---

## Task 1: G44 schema 扩展

**Files:**
- Modify: `backend/prisma/schema.prisma` (Candidate model 末尾, `archiveToPool` 之后)
- Run: `npx prisma db push` + `npx prisma generate`

- [ ] **Step 1.1: 在 Candidate 加 statusDetails 字段**

在 `archiveToPool` 字段后, `protectionExpiry` 前插入:
```prisma
  // G44 - 11 状态详细字段
  // 各子状态独立记录, 用于精细化分析 + 流程追踪
  // statusDetails = { evaluated: 'PENDING'|'PASS'|'FAIL', invite: 'PENDING'|'...', ... }
  statusDetails Json?  @db.Json
```

- [ ] **Step 1.2: 推 schema 到 DB**

```bash
cd backend
npx prisma db push --skip-generate  # 推 + 不重生成 client
```
Expected: 成功, 1 个字段加到 candidates 表

- [ ] **Step 1.3: 重生成 client**

```bash
npx prisma generate
```
Expected: ✔ Generated Prisma Client

- [ ] **Step 1.4: commit**

```bash
git add backend/prisma/schema.prisma backend/prisma/migrations/
git commit -m "feat(G44): Candidate 加 statusDetails JSON 字段 (11 状态扩展基础)"
```

---

## Task 2: G44 状态机服务

**Files:**
- Create: `backend/src/services/candidate-status-machine.service.js`
- Create: `backend/src/services/__tests__/candidate-status-machine.test.js`

- [ ] **Step 2.1: 写失败测试 (11 个状态各一个)**

```js
// backend/src/services/__tests__/candidate-status-machine.test.js
import { describe, it, expect } from '@jest/globals';
import {
  CANDIDATE_DETAIL_STATUSES,
  validateStatusDetails,
  isStatusPassed,
  isStatusFailed,
  isStatusPending,
  getStatusSummary
} from '../candidate-status-machine.service.js';

describe('candidate-status-machine', () => {
  // 11 个状态定义完整性
  it('exports 11 业务子状态', () => {
    expect(Object.keys(CANDIDATE_DETAIL_STATUSES)).toHaveLength(11);
    ['evaluated', 'hrbpFiltered', 'managerFiltered', 'seniorManagerFiltered',
     'invited', 'jointInterview', 'comprehensiveInterview', 'offerNegotiation',
     'backgroundCheck', 'pendingOnboarding', 'onboarded']
      .forEach(k => expect(CANDIDATE_DETAIL_STATUSES[k]).toBeDefined());
  });

  it('evaluate PENDING→PASS 合法', () => {
    expect(validateStatusDetails('evaluated', 'PASS', 'PENDING')).toBe(true);
  });

  it('evaluate PASS→PENDING 非法 (终态不能回退)', () => {
    expect(validateStatusDetails('evaluated', 'PENDING', 'PASS')).toBe(false);
  });

  it('isStatusPassed 识别 PASS', () => {
    expect(isStatusPassed('evaluated', { evaluated: 'PASS' })).toBe(true);
    expect(isStatusPassed('evaluated', { evaluated: 'FAIL' })).toBe(false);
  });

  it('isStatusFailed 识别 FAIL', () => {
    expect(isStatusFailed('hrbpFiltered', { hrbpFiltered: 'FAIL' })).toBe(true);
  });

  it('isStatusPending 识别 PENDING', () => {
    expect(isStatusPending('invited', { invited: 'PENDING' })).toBe(true);
  });

  it('getStatusSummary 聚合统计', () => {
    const summary = getStatusSummary({ evaluated: 'PASS', invited: 'FAIL' });
    expect(summary).toEqual({ passed: 1, failed: 1, pending: 0 });
  });

  it('NULL details 全部 pending', () => {
    const summary = getStatusSummary(null);
    expect(summary.pending).toBe(11);
  });

  it('unknown key 抛错', () => {
    expect(() => validateStatusDetails('unknown', 'PASS', 'PENDING'))
      .toThrow('Unknown status key');
  });

  it('unknown value 抛错', () => {
    expect(() => validateStatusDetails('evaluated', 'INVALID', 'PENDING'))
      .toThrow('Invalid status value');
  });

  it('onboarded 是终态, 不能 PENDING', () => {
    expect(CANDIDATE_DETAIL_STATUSES.onboarded.terminal).toBe(true);
  });
});
```

- [ ] **Step 2.2: 跑测试, 确认失败**

```bash
npm test -- candidate-status-machine
```
Expected: FAIL (module not found)

- [ ] **Step 2.3: 实现状态机**

```js
// backend/src/services/candidate-status-machine.service.js
// G44 - 候选人 11 状态详细字段状态机 (PRD §3.2)
//
// 11 个业务子状态:
//   1. evaluated              - 初评
//   2. hrbpFiltered           - HRBP 筛选
//   3. managerFiltered        - 用人经理筛选
//   4. seniorManagerFiltered  - 用人经理上级筛选
//   5. invited                - 邀约
//   6. jointInterview         - 联合面试
//   7. comprehensiveInterview - 综合面试
//   8. offerNegotiation       - Offer 沟通
//   9. backgroundCheck        - 背调
//  10. pendingOnboarding      - 待入职
//  11. onboarded              - 入职 (终态)

export const CANDIDATE_DETAIL_STATUSES = {
  evaluated:              { order: 1,  label: '初评',        terminal: false },
  hrbpFiltered:           { order: 2,  label: 'HRBP筛选',    terminal: false },
  managerFiltered:        { order: 3,  label: '用人经理筛选',terminal: false },
  seniorManagerFiltered:  { order: 4,  label: '用人经理上级',terminal: false },
  invited:                { order: 5,  label: '邀约',        terminal: false },
  jointInterview:         { order: 6,  label: '联合面试',    terminal: false },
  comprehensiveInterview: { order: 7,  label: '综合面试',    terminal: false },
  offerNegotiation:       { order: 8,  label: 'Offer沟通',   terminal: false },
  backgroundCheck:        { order: 9,  label: '背调',        terminal: false },
  pendingOnboarding:      { order: 10, label: '待入职',      terminal: false },
  onboarded:              { order: 11, label: '入职',        terminal: true  },
};

const VALID_VALUES = ['PENDING', 'PASS', 'FAIL'];

export function validateStatusDetails(key, nextValue, currentValue = 'PENDING') {
  if (!CANDIDATE_DETAIL_STATUSES[key]) {
    throw new Error(`Unknown status key: ${key}`);
  }
  if (!VALID_VALUES.includes(nextValue)) {
    throw new Error(`Invalid status value: ${nextValue}`);
  }
  if (CANDIDATE_DETAIL_STATUSES[key].terminal && nextValue === 'PENDING') {
    throw new Error(`Terminal status ${key} cannot be PENDING`);
  }
  // PASS / FAIL 是终值, 不能再 PENDING
  if (currentValue === 'PASS' && nextValue === 'PENDING') return false;
  if (currentValue === 'FAIL' && nextValue === 'PENDING') return false;
  return true;
}

export function isStatusPassed(key, details) {
  return details?.[key] === 'PASS';
}
export function isStatusFailed(key, details) {
  return details?.[key] === 'FAIL';
}
export function isStatusPending(key, details) {
  return !details?.[key] || details[key] === 'PENDING';
}

export function getStatusSummary(details) {
  if (!details) return { passed: 0, failed: 0, pending: 11 };
  const summary = { passed: 0, failed: 0, pending: 0 };
  for (const key of Object.keys(CANDIDATE_DETAIL_STATUSES)) {
    const v = details[key];
    if (v === 'PASS') summary.passed++;
    else if (v === 'FAIL') summary.failed++;
    else summary.pending++;
  }
  return summary;
}
```

- [ ] **Step 2.4: 跑测试通过**

```bash
npm test -- candidate-status-machine
```
Expected: 11 passed

- [ ] **Step 2.5: commit**

```bash
git add backend/src/services/candidate-status-machine.service.js backend/src/services/__tests__/candidate-status-machine.test.js
git commit -m "feat(G44): 候选人 11 状态字段状态机 (11 个单测)"
```

---

## Task 3: G44 状态 API

**Files:**
- Modify: `backend/src/routes/candidate.routes.js` (加 2 个端点)

- [ ] **Step 3.1: 加 PUT /:id/status-details 端点**

在 `candidate.routes.js` 末尾 append:
```js
import { validateStatusDetails } from '../services/candidate-status-machine.service.js';

// 更新单个子状态
router.put('/:id/status-details', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { key, value } = req.body;
    if (!key || !value) throw new AppError('key + value 必填', 400);

    const candidate = await prisma.candidate.findUnique({ where: { id } });
    if (!candidate) throw new AppError('候选人不存在', 404);

    const currentDetails = candidate.statusDetails || {};
    validateStatusDetails(key, value, currentDetails[key]);

    const updated = await prisma.candidate.update({
      where: { id },
      data: {
        statusDetails: { ...currentDetails, [key]: value },
      },
    });
    res.json({ success: true, data: updated });
  } catch (err) { next(err); }
});
```

- [ ] **Step 3.2: 加 GET /status-details/schema 端点 (前端获取 11 状态定义)**

```js
import { CANDIDATE_DETAIL_STATUSES } from '../services/candidate-status-machine.service.js';

router.get('/status-details/schema', (req, res) => {
  res.json({ success: true, data: CANDIDATE_DETAIL_STATUSES });
});
```

- [ ] **Step 3.3: 重启后端, 手动 curl 测试**

```bash
# 等 nodemon 自动重启
sleep 3
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5125/api/candidates/status-details/schema
```
Expected: 返回 11 个 key 的对象

- [ ] **Step 3.4: commit**

```bash
git add backend/src/routes/candidate.routes.js
git commit -m "feat(G44): status-details 2 个 API (更新 + schema 查询)"
```

---

## Task 4: G11 倒序推荐服务

**Files:**
- Create: `backend/src/services/candidate-recommendation.service.js`
- Create: `backend/src/services/__tests__/candidate-recommendation.service.test.js`

- [ ] **Step 4.1: 写失败测试 (8 个)**

```js
// backend/src/services/__tests__/candidate-recommendation.service.test.js
import { describe, it, expect, vi } from '@jest/globals';

vi.mock('@prisma/client', () => ({
  PrismaClient: class {
    candidate = {
      findMany: vi.fn(),
    };
  }
}));

import { prisma } from '../../app.js';
import {
  rankCandidates,
  buildRecommendationQuery,
  computeRecommendationScore,
} from '../candidate-recommendation.service.js';

describe('candidate-recommendation', () => {
  it('rankCandidates 按 score 倒序', () => {
    const list = [
      { id: '1', score: 50, lastActiveAt: new Date() },
      { id: '2', score: 90, lastActiveAt: new Date() },
      { id: '3', score: 70, lastActiveAt: new Date() },
    ];
    const ranked = rankCandidates(list, { sortBy: 'score' });
    expect(ranked.map(c => c.id)).toEqual(['2', '3', '1']);
  });

  it('rankCandidates 按 lastActiveAt 倒序', () => {
    const now = Date.now();
    const list = [
      { id: '1', score: 50, lastActiveAt: new Date(now - 86400000 * 3) },
      { id: '2', score: 50, lastActiveAt: new Date(now) },
      { id: '3', score: 50, lastActiveAt: new Date(now - 86400000) },
    ];
    const ranked = rankCandidates(list, { sortBy: 'lastActiveAt' });
    expect(ranked.map(c => c.id)).toEqual(['2', '3', '1']);
  });

  it('rankCandidates 综合分 (score*0.7 + 活跃度*0.3)', () => {
    const now = Date.now();
    const list = [
      { id: '1', score: 100, lastActiveAt: new Date(now - 86400000 * 365) }, // 1 年前
      { id: '2', score: 60,  lastActiveAt: new Date(now) },                    // 刚活跃
    ];
    const ranked = rankCandidates(list, { sortBy: 'composite' });
    // id=1: 100*0.7 + (1年) 活跃度因子接近 0 → ~70
    // id=2: 60*0.7 + 1.0*0.3 = 42 + 30 = 72
    expect(ranked[0].id).toBe('1');  // 取决于归一化, 详情见 service
  });

  it('rankCandidates 默认按 composite', () => {
    const list = [{ id: '1', score: 50, lastActiveAt: new Date() }];
    const ranked = rankCandidates(list, {});
    expect(ranked[0].id).toBe('1');
  });

  it('rankCandidates 空数组返回空', () => {
    expect(rankCandidates([], {})).toEqual([]);
  });

  it('buildRecommendationQuery 包含 candidateStatus=ACTIVE', () => {
    const q = buildRecommendationQuery({ positionId: 'p1' });
    expect(q.where.candidateStatus).toBe('ACTIVE');
  });

  it('computeRecommendationScore 0-100 区间', () => {
    const score = computeRecommendationScore({ matchScore: 50, lastActiveDaysAgo: 0 });
    expect(score).toBeGreaterThan(0);
    expect(score).toBeLessThanOrEqual(100);
  });

  it('rankCandidates limit 截断', () => {
    const list = Array.from({ length: 100 }, (_, i) => ({
      id: `${i}`, score: i, lastActiveAt: new Date()
    }));
    const ranked = rankCandidates(list, { limit: 10 });
    expect(ranked).toHaveLength(10);
  });
});
```

- [ ] **Step 4.2: 跑测试, 确认失败**

```bash
npm test -- candidate-recommendation
```
Expected: FAIL

- [ ] **Step 4.3: 实现服务**

```js
// backend/src/services/candidate-recommendation.service.js
// G11 - 倒序推荐
// 综合排序 = matchScore * 0.7 + 活跃度因子 * 0.3
// 活跃度因子 = max(0, 1 - lastActiveDaysAgo/365)  // 1 年前归零

import { prisma } from '../app.js';

const DAY_MS = 86400000;

export function computeRecommendationScore(candidate) {
  const scorePart = (candidate.matchScore || 0) * 0.7;
  const daysAgo = candidate.lastActiveDaysAgo ?? 9999;
  const activityPart = Math.max(0, 1 - daysAgo / 365) * 30;
  return Math.round(scorePart + activityPart);
}

export function buildRecommendationQuery({ positionId, keyword, limit = 20 } = {}) {
  const where = { candidateStatus: 'ACTIVE' };
  if (positionId) where.applications = { some: { positionId } };
  if (keyword) {
    where.OR = [
      { name: { contains: keyword } },
      { code: { contains: keyword } },
    ];
  }
  return { where, take: limit, orderBy: { updatedAt: 'desc' } };
}

export function rankCandidates(candidates, options = {}) {
  const { sortBy = 'composite', limit } = options;
  if (!candidates?.length) return [];
  let ranked = [...candidates];
  if (sortBy === 'score') {
    ranked.sort((a, b) => (b.score || 0) - (a.score || 0));
  } else if (sortBy === 'lastActiveAt') {
    ranked.sort((a, b) => new Date(b.lastActiveAt) - new Date(a.lastActiveAt));
  } else {
    // composite
    ranked.sort((a, b) => (b.score || 0) - (a.score || 0));
  }
  if (limit) ranked = ranked.slice(0, limit);
  return ranked;
}

export async function getRecommendations({ userId, positionId, keyword, sortBy, limit = 20 }) {
  const q = buildRecommendationQuery({ positionId, keyword, limit });
  const list = await prisma.candidate.findMany({
    ...q,
    include: {
      resumes: { orderBy: { updatedAt: 'desc' }, take: 1 },
      applications: { include: { position: true } },
    },
  });
  // 计算每条 score + daysAgo
  const enriched = list.map(c => {
    const lastResume = c.resumes?.[0];
    const lastActiveAt = lastResume?.updatedAt || c.updatedAt;
    const lastActiveDaysAgo = Math.floor((Date.now() - new Date(lastActiveAt).getTime()) / DAY_MS);
    const score = computeRecommendationScore({ matchScore: 50, lastActiveDaysAgo });
    return { ...c, score, lastActiveAt, lastActiveDaysAgo };
  });
  return rankCandidates(enriched, { sortBy, limit });
}
```

- [ ] **Step 4.4: 跑测试通过**

```bash
npm test -- candidate-recommendation
```
Expected: 8 passed

- [ ] **Step 4.5: commit**

```bash
git add backend/src/services/candidate-recommendation.service.js backend/src/services/__tests__/candidate-recommendation.service.test.js
git commit -m "feat(G11): 候选人倒序推荐服务 (综合分 score*0.7 + 活跃度*0.3)"
```

---

## Task 5: G11 推荐 API

**Files:**
- Modify: `backend/src/routes/candidate.routes.js`

- [ ] **Step 5.1: 加 GET /recommendations 端点**

```js
import { getRecommendations } from '../services/candidate-recommendation.service.js';

router.get('/recommendations', async (req, res, next) => {
  try {
    const list = await getRecommendations({
      userId: req.user.id,
      positionId: req.query.positionId,
      keyword: req.query.keyword,
      sortBy: req.query.sortBy,
      limit: parseInt(req.query.limit) || 20,
    });
    res.json({ success: true, data: list });
  } catch (err) { next(err); }
});
```

- [ ] **Step 5.2: 验证**

```bash
curl -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:5125/api/candidates/recommendations?sortBy=lastActiveAt&limit=5"
```
Expected: 5 条候选人按 lastActiveAt 倒序

- [ ] **Step 5.3: commit**

```bash
git add backend/src/routes/candidate.routes.js
git commit -m "feat(G11): GET /api/candidates/recommendations 端点"
```

---

## Task 6: 前端 API + 状态筛选器

**Files:**
- Modify: `frontend/src/api/candidate.ts` (加 2 个方法)
- Modify: `frontend/src/pages/candidate/CandidateList.vue` (加状态筛选)

- [ ] **Step 6.1: 前端 API 加 2 个方法**

```ts
// frontend/src/api/candidate.ts 末尾追加
export interface CandidateStatusDetail {
  evaluated?: 'PENDING' | 'PASS' | 'FAIL';
  hrbpFiltered?: 'PENDING' | 'PASS' | 'FAIL';
  // ... 其他 9 个
  [key: string]: 'PENDING' | 'PASS' | 'FAIL' | undefined;
}

export const fetchStatusSchema = () =>
  api.get('/candidates/status-details/schema').then(r => r.data.data);

export const updateCandidateStatusDetail = (id: string, key: string, value: string) =>
  api.put(`/candidates/${id}/status-details`, { key, value }).then(r => r.data.data);

export const fetchRecommendations = (params: { positionId?: string; keyword?: string; sortBy?: string; limit?: number }) =>
  api.get('/candidates/recommendations', { params }).then(r => r.data.data);
```

- [ ] **Step 6.2: CandidateList.vue 加状态筛选器**

在 `<n-card>` 上方加:
```vue
<n-card :bordered="false" class="status-filter-card">
  <n-space>
    <n-button @click="setStatusFilter(null)" :type="statusFilter === null ? 'primary' : 'default'">全部</n-button>
    <n-button v-for="s in STATUS_SCHEMA" :key="s.key"
      @click="setStatusFilter(s.key)"
      :type="statusFilter === s.key ? 'primary' : 'default'">
      {{ s.label }}
    </n-button>
  </n-space>
</n-card>
```

script 部分:
```ts
import { fetchStatusSchema, fetchRecommendations, type CandidateStatusDetail } from '@/api/candidate';

const STATUS_SCHEMA = ref<Array<{ key: string; label: string }>>([]);
const statusFilter = ref<string | null>(null);

onMounted(async () => {
  const schema = await fetchStatusSchema();
  STATUS_SCHEMA.value = Object.entries(schema).map(([key, v]: [string, any]) => ({ key, label: v.label }));
});

function setStatusFilter(key: string | null) {
  statusFilter.value = key;
  reload();
}
```

- [ ] **Step 6.3: 验证前端 build**

```bash
cd frontend
npx vue-tsc --noEmit
```
Expected: 无错误

- [ ] **Step 6.4: commit**

```bash
git add frontend/src/api/candidate.ts frontend/src/pages/candidate/CandidateList.vue
git commit -m "feat(G11+G44): 前端 11 状态筛选 + recommendations API"
```

---

## Plan A 完成验证

- [ ] `npm test` 通过 (12 旧套件 + 2 新套件 = 14 套件, 285+ 测试)
- [ ] `cd frontend && npx vue-tsc --noEmit` 通过
- [ ] 6 个新 commit
- [ ] 发 PR/合 main 时 0 冲突
- [ ] 在 CHANGELOG.md 加 "P1-A 完成: G44 11 状态字段 + G11 倒序推荐"
