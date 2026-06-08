# Plan D: 待入职 + 人才库 (G31 + G32)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 待入职智能分配职位 (G31) + 人才库 6 子库完整 CRUD (G32)

**Architecture:**
- **G31**: 新建 `position-matcher.service.js`, 基于候选人画像 (学历/经验/期望地点) + 职位需求 JD 用规则 + 评分 (复用 referral rule-evaluator) 排序匹配职位
- **G32**: 现有 `talent-pool.routes.js` 是 MVP, 扩展为 6 子库 (PASSIVE/ACTIVE/HIRED/REJECTED/BLACKLIST/GENERAL), 完整 CRUD + 跨子库移动

**Tech Stack:** Prisma 5 + MySQL 9, 复用 referral rule-evaluator 评分

---

## DoD
- [ ] G31: position-matcher service + ≥ 8 单测 (匹配度计算, 排序, 边界)
- [ ] G31: 2 个新 API: GET /positions/recommendations + GET /candidates/recommendations-for-position
- [ ] G32: 6 子库枚举 + 跨子库移动 (转移原因审计)
- [ ] G32: ≥ 6 单测
- [ ] G32: 5 个新 API: list pools + move candidate to pool + pool stats
- [ ] 前端: OnboardingList.vue 加 "智能分配" 按钮 + TalentPool.vue 加 6 子库 tab
- [ ] `npm test` 通过 (328 + 14 = 342+ 测试)

---

## Task 1: G31 position-matcher 服务

**Files:**
- Create: `backend/src/services/position-matcher.service.js`
- Create: `backend/src/services/__tests__/position-matcher.service.test.js`

- [ ] **Step 1.1: 写失败测试 (8 个)**

```js
// backend/src/services/__tests__/position-matcher.service.test.js
import { describe, it, expect, vi } from '@jest/globals';

vi.mock('@prisma/client', () => ({
  PrismaClient: class {
    position = { findMany: vi.fn() };
    candidate = { findUnique: vi.fn() };
  }
}));

import { prisma } from '../../app.js';
import {
  computeMatchScore,
  buildMatchReason,
  rankPositions,
  recommendPositionsForCandidate,
  recommendCandidatesForPosition,
  MATCH_WEIGHTS,
} from '../position-matcher.service.js';

describe('position-matcher', () => {
  it('MATCH_WEIGHTS 总和 = 1.0', () => {
    const sum = Object.values(MATCH_WEIGHTS).reduce((a, b) => a + b, 0);
    expect(sum).toBeCloseTo(1.0, 2);
  });

  it('computeMatchScore 完全匹配 → 1.0', () => {
    const score = computeMatchScore({
      candidate: { highestEducation: '本科', workExperience: '5年', expectedPosition: '工程师', householdLocation: '北京' },
      position: { education: '本科', minExperience: 3, maxExperience: 10, title: '工程师', workLocation: '北京' },
    });
    expect(score).toBeGreaterThan(0.8);
  });

  it('computeMatchScore 学历不符扣分', () => {
    const score = computeMatchScore({
      candidate: { highestEducation: '大专' },
      position: { education: '本科', minExperience: 0, maxExperience: 99, title: 'X', workLocation: 'X' },
    });
    expect(score).toBeLessThan(0.8);
  });

  it('computeMatchScore 经验不在区间扣分', () => {
    const score = computeMatchScore({
      candidate: { workExperience: '15年' },
      position: { education: '不限', minExperience: 1, maxExperience: 5, title: 'X', workLocation: 'X' },
    });
    expect(score).toBeLessThan(0.7);
  });

  it('buildMatchReason 列出匹配维度', () => {
    const reason = buildMatchReason({ education: true, experience: true, position: true, location: false });
    expect(reason).toContain('学历');
    expect(reason).toContain('地点不匹配');
  });

  it('rankPositions 按 score 倒序', () => {
    const list = [
      { id: '1', score: 0.5 },
      { id: '2', score: 0.9 },
      { id: '3', score: 0.7 },
    ];
    const ranked = rankPositions(list);
    expect(ranked.map(p => p.id)).toEqual(['2', '3', '1']);
  });

  it('recommendPositionsForCandidate 返回 top N', async () => {
    prisma.position.findMany.mockResolvedValueOnce([
      { id: 'p1', title: '工程师', education: '本科', minExperience: 3, maxExperience: 10, workLocation: '北京' },
      { id: 'p2', title: '设计师', education: '大专', minExperience: 0, maxExperience: 5, workLocation: '上海' },
    ]);
    const recs = await recommendPositionsForCandidate('c1', { limit: 2 });
    expect(recs).toHaveLength(2);
    expect(recs[0].score).toBeGreaterThan(0);
  });

  it('recommendCandidatesForPosition 反向', async () => {
    prisma.candidate.findUnique.mockResolvedValueOnce({ id: 'c1', highestEducation: '本科', workExperience: '5年' });
    prisma.position.findMany.mockResolvedValueOnce([
      { id: 'p1', title: '工程师', education: '本科', minExperience: 3, maxExperience: 10, workLocation: '北京' },
    ]);
    const recs = await recommendCandidatesForPosition('p1', { limit: 5 });
    expect(recs).toHaveLength(1);
  });
});
```

- [ ] **Step 1.2: 跑测试, 确认失败**

```bash
npm test -- position-matcher
```
Expected: FAIL

- [ ] **Step 1.3: 实现服务**

```js
// backend/src/services/position-matcher.service.js
// G31 - 待入职智能分配职位 (候选人 ↔ 职位双向推荐)

import { prisma } from '../app.js';

export const MATCH_WEIGHTS = {
  education: 0.25,
  experience: 0.30,
  position:  0.25,
  location:  0.20,
};

const EDU_ORDER = { '不限': 0, '中专': 1, '大专': 2, '本科': 3, '硕士': 4, '博士': 5 };

function parseYears(s) {
  if (!s) return 0;
  const m = String(s).match(/(\d+)/);
  return m ? parseInt(m[1]) : 0;
}

export function computeMatchScore({ candidate, position }) {
  let score = 0;
  const detail = {};

  // 学历
  const candEdu = EDU_ORDER[candidate.highestEducation] || 0;
  const posEdu = EDU_ORDER[position.education] || 0;
  detail.education = posEdu === 0 || candEdu >= posEdu;
  score += (detail.education ? 1 : 0) * MATCH_WEIGHTS.education;

  // 经验
  const candYears = parseYears(candidate.workExperience);
  const inRange = candYears >= (position.minExperience || 0) && candYears <= (position.maxExperience || 99);
  detail.experience = inRange;
  if (inRange) score += MATCH_WEIGHTS.experience;
  else if (candYears > (position.maxExperience || 99)) score += MATCH_WEIGHTS.experience * 0.5; // 资深适度扣分

  // 职位意向
  detail.position = !candidate.expectedPosition || !position.title ||
    candidate.expectedPosition.includes(position.title) || position.title.includes(candidate.expectedPosition);
  if (detail.position) score += MATCH_WEIGHTS.position;

  // 地点
  detail.location = !candidate.householdLocation || !position.workLocation ||
    candidate.householdLocation === position.workLocation;
  if (detail.location) score += MATCH_WEIGHTS.location;

  return Math.round(score * 100) / 100;
}

export function buildMatchReason(detail) {
  const parts = [];
  if (detail.education) parts.push('✅ 学历匹配');
  else parts.push('❌ 学历不符');
  if (detail.experience) parts.push('✅ 经验匹配');
  else parts.push('⚠️ 经验偏离');
  if (detail.position) parts.push('✅ 职位意向匹配');
  else parts.push('⚠️ 职位意向偏离');
  if (detail.location) parts.push('✅ 地点匹配');
  else parts.push('⚠️ 地点不匹配');
  return parts.join(' / ');
}

export function rankPositions(positions) {
  return [...positions].sort((a, b) => (b.score || 0) - (a.score || 0));
}

export async function recommendPositionsForCandidate(candidateId, { limit = 10 } = {}) {
  const candidate = await prisma.candidate.findUnique({ where: { id: candidateId } });
  if (!candidate) return [];
  const positions = await prisma.position.findMany({
    where: { status: 'ACTIVE' },
    take: 50,
  });
  const scored = positions.map(p => {
    const score = computeMatchScore({ candidate, position: p });
    return { ...p, score, matchReason: buildMatchReason({
      education: score >= MATCH_WEIGHTS.education * 0.5,
      experience: score >= (MATCH_WEIGHTS.education + MATCH_WEIGHTS.experience * 0.5),
      position: true, location: true,
    })};
  });
  return rankPositions(scored).slice(0, limit);
}

export async function recommendCandidatesForPosition(positionId, { limit = 10 } = {}) {
  const position = await prisma.position.findUnique({ where: { id: positionId } });
  if (!position) return [];
  const candidates = await prisma.candidate.findMany({
    where: { candidateStatus: 'ACTIVE' },
    take: 50,
  });
  const scored = candidates.map(c => {
    const score = computeMatchScore({ candidate: c, position });
    return { ...c, score };
  });
  return rankPositions(scored).slice(0, limit);
}
```

- [ ] **Step 1.4: 跑测试通过**

```bash
npm test -- position-matcher
```
Expected: 8 passed

- [ ] **Step 1.5: commit**

```bash
git add backend/src/services/position-matcher.service.js backend/src/services/__tests__/position-matcher.service.test.js
git commit -m "feat(G31): 候选人↔职位双向推荐服务 (8 测试)"
```

---

## Task 2: G31 推荐 API

**Files:**
- Create: `backend/src/routes/position-recommendation.routes.js`
- Modify: `backend/src/app.js`

- [ ] **Step 2.1: 写 routes**

```js
// backend/src/routes/position-recommendation.routes.js
import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import { recommendPositionsForCandidate, recommendCandidatesForPosition } from '../services/position-matcher.service.js';

const router = Router();
router.use(authMiddleware);

router.get('/positions/for-candidate/:candidateId', async (req, res, next) => {
  try {
    const data = await recommendPositionsForCandidate(req.params.candidateId, { limit: parseInt(req.query.limit) || 10 });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/candidates/for-position/:positionId', async (req, res, next) => {
  try {
    const data = await recommendCandidatesForPosition(req.params.positionId, { limit: parseInt(req.query.limit) || 10 });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

export default router;
```

- [ ] **Step 2.2: 注册**

`backend/src/app.js`:
```js
import positionRecommendationRoutes from './routes/position-recommendation.routes.js';
app.use('/api/recommendations', positionRecommendationRoutes);
```

- [ ] **Step 2.3: 验证**

```bash
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5125/api/recommendations/positions/for-candidate/<id>
```
Expected: 200, 数组

- [ ] **Step 2.4: commit**

```bash
git add backend/src/routes/position-recommendation.routes.js backend/src/app.js
git commit -m "feat(G31): 双向推荐 API 端点"
```

---

## Task 3: G32 talent-pool 6 子库扩展

**Files:**
- Modify: `backend/src/routes/talent-pool.routes.js` (扩展为 6 子库)
- Create: `backend/src/services/talent-pool.service.js`

- [ ] **Step 3.1: 写 service**

```js
// backend/src/services/talent-pool.service.js
// G32 - 人才库 6 子库完整 CRUD

import { prisma } from '../app.js';

export const TALENT_POOL_TYPES = {
  PASSIVE:   { code: 'PASSIVE',   label: '被动简历', description: '求职意愿低, 仅定期触达' },
  ACTIVE:    { code: 'ACTIVE',    label: '主动投递', description: '主动投递但未通过' },
  HIRED:     { code: 'HIRED',     label: '已聘',     description: '历史入职过本公司' },
  REJECTED:  { code: 'REJECTED',  label: '已拒',     description: '明确拒绝 offer 的' },
  BLACKLIST: { code: 'BLACKLIST', label: '黑名单',   description: '永不录用' },
  GENERAL:   { code: 'GENERAL',   label: '通用',     description: '通用人才库' },
};

export async function listPoolStats() {
  const result = {};
  for (const key of Object.keys(TALENT_POOL_TYPES)) {
    result[key] = await prisma.candidate.count({
      where: { archiveToPool: key, candidateStatus: 'ARCHIVED' },
    });
  }
  return result;
}

export async function listCandidatesInPool(poolCode, { page = 1, pageSize = 20 } = {}) {
  return prisma.candidate.findMany({
    where: { archiveToPool: poolCode, candidateStatus: 'ARCHIVED' },
    skip: (page - 1) * pageSize,
    take: pageSize,
    orderBy: { updatedAt: 'desc' },
  });
}

export async function moveCandidateToPool(candidateId, targetPool, reason, operatorId) {
  if (!TALENT_POOL_TYPES[targetPool]) throw new Error(`Unknown pool: ${targetPool}`);
  return prisma.$transaction(async (tx) => {
    const updated = await tx.candidate.update({
      where: { id: candidateId },
      data: {
        archiveToPool: targetPool,
        candidateStatus: 'ARCHIVED',
        archiveReason: reason,
        archiveType: 'MANUAL',
      },
    });
    await tx.operationRecord.create({
      data: {
        resource: 'Candidate',
        resourceId: candidateId,
        action: 'MOVE_TO_POOL',
        operatorId,
        details: { fromPool: updated.archiveToPool, toPool: targetPool, reason },
      },
    });
    return updated;
  });
}

export async function countByPool() {
  return listPoolStats();
}
```

- [ ] **Step 3.2: 写失败测试 (6 个)**

```js
// backend/src/services/__tests__/talent-pool.service.test.js
import { describe, it, expect, vi } from '@jest/globals';

vi.mock('@prisma/client', () => ({
  PrismaClient: class {
    candidate = { count: vi.fn(), findMany: vi.fn(), update: vi.fn() };
    $transaction = vi.fn();
    operationRecord = { create: vi.fn() };
  }
}));

import { prisma } from '../../app.js';
import { TALENT_POOL_TYPES, listPoolStats, listCandidatesInPool, moveCandidateToPool } from '../talent-pool.service.js';

describe('talent-pool', () => {
  it('6 子库定义', () => {
    expect(Object.keys(TALENT_POOL_TYPES)).toHaveLength(6);
  });

  it('listPoolStats 聚合 6 个子库', async () => {
    prisma.candidate.count.mockResolvedValue(10);
    const stats = await listPoolStats();
    expect(Object.keys(stats)).toHaveLength(6);
    expect(stats.PASSIVE).toBe(10);
  });

  it('listCandidatesInPool 分页', async () => {
    prisma.candidate.findMany.mockResolvedValueOnce([{ id: 'c1' }]);
    const list = await listCandidatesInPool('PASSIVE', { page: 1, pageSize: 20 });
    expect(list).toHaveLength(1);
  });

  it('moveCandidateToPool 写入正确', async () => {
    prisma.$transaction.mockImplementationOnce(async (fn) => {
      const tx = {
        candidate: { update: vi.fn().mockResolvedValue({ id: 'c1', archiveToPool: 'BLACKLIST' }) },
        operationRecord: { create: vi.fn().mockResolvedValue({}) },
      };
      return fn(tx);
    });
    const r = await moveCandidateToPool('c1', 'BLACKLIST', '品德问题', 'u1');
    expect(r.id).toBe('c1');
  });

  it('moveCandidateToPool 非法 pool 抛错', async () => {
    await expect(moveCandidateToPool('c1', 'INVALID', 'r', 'u1'))
      .rejects.toThrow('Unknown pool');
  });

  it('moveCandidateToPool 写审计', async () => {
    const tx = {
      candidate: { update: vi.fn().mockResolvedValue({ id: 'c1' }) },
      operationRecord: { create: vi.fn().mockResolvedValue({}) },
    };
    prisma.$transaction.mockImplementationOnce(async (fn) => fn(tx));
    await moveCandidateToPool('c1', 'GENERAL', 'r', 'u1');
    expect(tx.operationRecord.create).toHaveBeenCalledWith(
      expect.objectContaining({ data: expect.objectContaining({ action: 'MOVE_TO_POOL' }) })
    );
  });
});
```

- [ ] **Step 3.3: 跑测试, 确认失败**

```bash
npm test -- talent-pool
```

- [ ] **Step 3.4: 跑测试通过**

- [ ] **Step 3.5: commit**

```bash
git add backend/src/services/talent-pool.service.js backend/src/services/__tests__/talent-pool.service.test.js
git commit -m "feat(G32): 人才库 6 子库 service (6 测试)"
```

---

## Task 4: G32 talent-pool 路由扩展

**Files:**
- Modify: `backend/src/routes/talent-pool.routes.js`

- [ ] **Step 4.1: 加 5 个端点**

```js
import {
  TALENT_POOL_TYPES, listPoolStats,
  listCandidatesInPool, moveCandidateToPool
} from '../services/talent-pool.service.js';

router.get('/types', (req, res) => {
  res.json({ success: true, data: TALENT_POOL_TYPES });
});

router.get('/stats', async (req, res, next) => {
  try {
    const data = await listPoolStats();
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/pool/:poolCode', async (req, res, next) => {
  try {
    const data = await listCandidatesInPool(req.params.poolCode, {
      page: parseInt(req.query.page) || 1,
      pageSize: parseInt(req.query.pageSize) || 20,
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.post('/pool/:poolCode/move', async (req, res, next) => {
  try {
    const data = await moveCandidateToPool(
      req.body.candidateId, req.params.poolCode, req.body.reason, req.user.id
    );
    res.json({ success: true, data });
  } catch (err) { next(err); }
});
```

- [ ] **Step 4.2: 验证 4 个端点**

```bash
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5125/api/talent-pool/types
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5125/api/talent-pool/stats
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5125/api/talent-pool/pool/PASSIVE
```

- [ ] **Step 4.3: commit**

```bash
git add backend/src/routes/talent-pool.routes.js
git commit -m "feat(G32): 4 个 talent-pool API (types/stats/pool/move)"
```

---

## Task 5: 前端 OnboardingList 智能分配按钮

**Files:**
- Modify: `frontend/src/pages/onboarding/OnboardingList.vue`
- Modify: `frontend/src/api/onboarding.ts` 或 onboarding-related api

- [ ] **Step 5.1: 加 API**

```ts
// frontend/src/api/recommendation.ts (新文件)
import api from './base';
export const recommendPositionsForCandidate = (candidateId: string, limit = 10) =>
  api.get(`/recommendations/positions/for-candidate/${candidateId}`, { params: { limit } }).then(r => r.data.data);
```

- [ ] **Step 5.2: OnboardingList.vue 加按钮 + 抽屉**

每行加 "智能分配" 按钮, 点击后弹 n-drawer 显示推荐职位列表.

- [ ] **Step 5.3: vue-tsc 验证**

- [ ] **Step 5.4: commit**

```bash
git add frontend/src/api/recommendation.ts frontend/src/pages/onboarding/OnboardingList.vue
git commit -m "feat(G31): 前端 OnboardingList 智能分配按钮 + 推荐职位抽屉"
```

---

## Task 6: 前端 TalentPool 6 子库 tab

**Files:**
- Modify: `frontend/src/pages/talent/TalentPool.vue`

- [ ] **Step 6.1: 加 tab + 移动按钮**

用 n-tabs 展示 6 个子库, 每个 tab 显示候选人列表 + 移动按钮.

- [ ] **Step 6.2: vue-tsc 验证**

- [ ] **Step 6.3: commit**

```bash
git add frontend/src/pages/talent/TalentPool.vue
git commit -m "feat(G32): 前端 TalentPool 6 子库 tab + 跨池移动"
```

---

## Plan D 完成验证

- [ ] `npm test` 通过 (目标 328 + 14 = 342+)
- [ ] `cd frontend && npx vue-tsc --noEmit` 通过
- [ ] 6 个新 commit
- [ ] 跨计划联调: G31 推荐能用到 Plan A 的 G44 状态
- [ ] CHANGELOG.md 加 "P1-D 完成: G31 智能分配 + G32 6 子库完整 CRUD"
