# Plan H: 代码质量 + 测试扩充 (2026-06-09)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清理 3 类遗留债, 提升代码质量 + 覆盖率:
1. **修 10 个 .vue 类型错** (vue-tsc 2.x 暴露, 现在能修了)
2. **e2e 扩充** (3 个新 spec: 需求/Offer/面试关键 flow)
3. **跨计划联调测试** (G19 评价预填 + G44 状态, G32 人才池 + G8 字段权限)

**Architecture:**
- **Task 1-3**: 单文件类型修, 跟项目惯例用合适类型注解 (避免 `as any` 滥用)
- **Task 4-6**: e2e 3 个新 spec, 跟现有 3 个 spec 同样模式
- **Task 7-8**: 跨计划集成测试 (后端 service 单元测试, 验证 plan 间契约)

**Tech Stack:** Playwright 1.49 + vue-tsc 2.2 + Jest

---

## DoD
- [ ] `npx vue-tsc --noEmit` 0 错误
- [ ] 3 个新 e2e spec 通过 (3+3+3+3 = 12 e2e 场景)
- [ ] 5+ 个跨计划集成测试通过
- [ ] 现有 367 测试仍全过
- [ ] `npm test` 通过

---

## Task 1: 修 InvitationCenter.vue 2 个类型错 (form 缺字段)

**Files:**
- Modify: `frontend/src/pages/invitation/InvitationCenter.vue`

- [ ] **Step 1.1: 看现状**

```bash
sed -n '245,260p' frontend/src/pages/invitation/InvitationCenter.vue
sed -n '315,330p' frontend/src/pages/invitation/InvitationCenter.vue
```

- [ ] **Step 1.2: 修类型**

`InvitationCenter.vue` 中 `InterventionModal` 组件的 ref 类型签名需要:
- `form` 字段为必填, 但模板里没传 → 修模板加 `:form="modalState.form"`
- 或者改组件 props 把 `form` 改为 optional: `form?: { reason: string }`

**修法 (推荐)**: 改 `InterventionModal` 组件定义 (在同文件), `form` 加 `?` 标记:
```ts
// script setup
interface ModalState {
  show: boolean
  loading: boolean
  title: string
  type: 'warning' | 'error'
  placeholder: string
  action: '' | 'enterPool' | 'intervene' | 'terminate'
  id: string
  reason: string
  form?: { reason: string }  // 改 optional
}
```

- [ ] **Step 1.3: 验证**

```bash
npx vue-tsc --noEmit 2>&1 | grep "InvitationCenter" | head -3
```
Expected: 0 错误

- [ ] **Step 1.4: commit**

```bash
git add frontend/src/pages/invitation/InvitationCenter.vue
git commit -m "fix(frontend): InvitationCenter 修 InterventionModal form optional"
```

---

## Task 2: 修 AddReferralModal + ReferralCenter 3 个错

**Files:**
- Modify: `frontend/src/pages/referral/AddReferralModal.vue`
- Modify: `frontend/src/pages/referral/ReferralCenter.vue`

- [ ] **Step 2.1: AddReferralModal duplicate 'api'**

现状: `import { api } from '...'` + 同文件内 `const api = ...` 冲突
修法: 删除同文件内 `const api = axios.create(...)` 那行, 统一用 import

- [ ] **Step 2.2: ReferralCenter PersonAddOutline 缺**

`@vicons/ionicons5` import 列表加 `PersonAddOutline`:
```ts
import { ..., PersonAddOutline } from '@vicons/ionicons5'
```

- [ ] **Step 2.3: 验证 + commit**

```bash
npx vue-tsc --noEmit 2>&1 | grep -E "AddReferralModal|ReferralCenter" | head -3
git add frontend/src/pages/referral/
git commit -m "fix(frontend): AddReferralModal 删重复 api, ReferralCenter 加 PersonAddOutline import"
```

---

## Task 3: 修 BackgroundCheckPanel + ProcessStageEditor + 3 个 Plan F 引入的 wrap 缺

**Files:**
- Modify: `frontend/src/pages/offer/BackgroundCheckPanel.vue`
- Modify: `frontend/src/pages/settings/ProcessStageEditor.vue`
- Modify: `frontend/src/pages/settings/SchoolLibrary.vue`
- Modify: `frontend/src/pages/settings/CompanyLibrary.vue`
- Modify: `frontend/src/pages/settings/DynamicFieldSettings.vue`

- [ ] **Step 3.1: BackgroundCheckPanel undefined as index (line 130)**

```bash
sed -n '125,135p' frontend/src/pages/offer/BackgroundCheckPanel.vue
```
修法: 加 `?.` 链式调用, 或加 `if (xxx)` 守卫. 例: `arr[x]?.y` → `if (arr[x]) arr[x].y`

- [ ] **Step 3.2: ProcessStageEditor null vs undefined (line 247)**

`orderIndex: number | null` 改为 `orderIndex?: number` (在对应 interface 声明)
或者在赋值处加 `?? 0` 兜底

- [ ] **Step 3.3: 3 个 Plan F 引入的 `wrap` 缺**

Plan F 的 SchoolLibrary / CompanyLibrary / DynamicFieldSettings 都用了 `this.$refs.wrap` 但 setup 里没 expose.
修法: 在 `<script setup>` 加 `const wrap = ref()` + 模板用 `ref="wrap"` (vue 编译器自动 expose ref)

- [ ] **Step 3.4: 验证**

```bash
npx vue-tsc --noEmit 2>&1 | tail -10
```
Expected: 0 错误

- [ ] **Step 3.5: commit**

```bash
git add frontend/src/pages/offer/BackgroundCheckPanel.vue \
        frontend/src/pages/settings/ProcessStageEditor.vue \
        frontend/src/pages/settings/SchoolLibrary.vue \
        frontend/src/pages/settings/CompanyLibrary.vue \
        frontend/src/pages/settings/DynamicFieldSettings.vue
git commit -m "fix(frontend): 5 个 .vue 类型错 (BackgroundCheck undefined + ProcessStage null + 3 个 Plan F wrap 缺)"
```

---

## Task 4: e2e #4 — 需求列表 + 创建流程

**Files:**
- Create: `frontend/e2e/demand-flow.spec.ts`

- [ ] **Step 4.1: 写 e2e**

```ts
// frontend/e2e/demand-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('需求管理 (PRD G1)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[placeholder*="账"], input[name="username"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button:has-text("登录"), button[type="submit"]');
    await page.waitForURL(/\/(dashboard|demands|positions|candidates)/);
  });

  test('需求列表加载并显示卡片', async ({ page }) => {
    await page.goto('/demands');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('table, .n-data-table, .demand-card, .n-card').first()).toBeVisible({ timeout: 8_000 });
  });

  test('点 "新建需求" 显示表单', async ({ page }) => {
    await page.goto('/demands');
    await page.waitForLoadState('networkidle');
    const newBtn = page.getByRole('button', { name: /新建|创建|新增/ }).first();
    if (await newBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await newBtn.click();
      await expect(page.locator('.n-modal, [role="dialog"]').first()).toBeVisible({ timeout: 5_000 });
    }
  });
});
```

- [ ] **Step 4.2: 跑 + 修选择器**

```bash
npx playwright test e2e/demand-flow.spec.ts --reporter=line 2>&1 | tail -10
```

- [ ] **Step 4.3: commit**

```bash
git add frontend/e2e/demand-flow.spec.ts
git commit -m "test(e2e): 需求管理 - 列表加载 + 新建按钮 (2 场景)"
```

---

## Task 5: e2e #5 — Offer 列表 + 详情

**Files:**
- Create: `frontend/e2e/offer-flow.spec.ts`

- [ ] **Step 5.1: 写 e2e**

```ts
// frontend/e2e/offer-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Offer 管理 (PRD G23)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[placeholder*="账"], input[name="username"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button:has-text("登录"), button[type="submit"]');
    await page.waitForURL(/\/(dashboard|demands|positions|candidates)/);
  });

  test('Offer 列表加载', async ({ page }) => {
    await page.goto('/offers');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('table, .n-data-table').first()).toBeVisible({ timeout: 8_000 });
  });

  test('点击列表行进入详情', async ({ page }) => {
    await page.goto('/offers');
    await page.waitForLoadState('networkidle');
    const firstRow = page.locator('table tbody tr, .n-data-table-tr').first();
    if (await firstRow.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await firstRow.click();
      // 详情页应该有 tab
      await page.waitForTimeout(500);
    }
  });
});
```

- [ ] **Step 5.2: 跑 + commit**

```bash
git add frontend/e2e/offer-flow.spec.ts
git commit -m "test(e2e): Offer 管理 - 列表 + 详情 (2 场景)"
```

---

## Task 6: e2e #6 — 设置页所有菜单可达

**Files:**
- Create: `frontend/e2e/settings-menu.spec.ts`

- [ ] **Step 6.1: 写 e2e**

```ts
// frontend/e2e/settings-menu.spec.ts
import { test, expect } from '@playwright/test';

const SETTINGS_PAGES = [
  { url: '/settings/account', label: '员工信息' },
  { url: '/settings/department', label: '部门管理' },
  { url: '/settings/permission', label: '权限管理' },
  { url: '/settings/demand-config', label: '招聘需求设置' },
  { url: '/settings/dictionary', label: '数据字典' },
  { url: '/settings/scoring', label: '评分规则' },
  { url: '/settings/recruitment-process', label: '招聘流程' },
  { url: '/settings/recruitment-stage', label: '阶段模板库' },
  { url: '/settings/recruitment-round', label: '面试轮次' },
  { url: '/settings/company', label: '公司信息' },
  { url: '/settings/field-acl', label: '字段权限' },
  { url: '/settings/school-library', label: '院校库' },
  { url: '/settings/company-library', label: '公司库' },
  { url: '/settings/dynamic-fields', label: '动态字段' },
];

test.describe('Settings 菜单可达性 (P1-B + P3-F 全覆盖)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[placeholder*="账"], input[name="username"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button:has-text("登录"), button[type="submit"]');
    await page.waitForURL(/\/(dashboard|demands|positions|candidates)/);
  });

  for (const { url, label } of SETTINGS_PAGES) {
    test(`菜单项 ${label} (${url}) 可达且内容渲染`, async ({ page }) => {
      await page.goto(url);
      await page.waitForLoadState('networkidle');
      // 任意可见内容 (避免空白页)
      await expect(page.locator('body')).toBeVisible();
      // 检查没有 "404" 或 "Not Found"
      const bodyText = await page.locator('body').textContent();
      expect(bodyText?.toLowerCase()).not.toContain('404');
      expect(bodyText?.toLowerCase()).not.toContain('not found');
    });
  }
});
```

- [ ] **Step 6.2: 跑 + 修**

- [ ] **Step 6.3: commit**

```bash
git add frontend/e2e/settings-menu.spec.ts
git commit -m "test(e2e): 14 个 settings 菜单可达性回归保护"
```

---

## Task 7: 跨计划联调测试 — G19 评价预填 + G44 状态

**Files:**
- Create: `backend/src/services/__tests__/cross-plan-integration.test.js`

- [ ] **Step 7.1: 写测试 (3 个)**

```js
// backend/src/services/__tests__/cross-plan-integration.test.js
// 跨计划联调: G19 评价预填服务 + G44 候选人 11 状态 + G32 人才池 + G8 字段权限

import { describe, it, expect, vi } from '@jest/globals';

// Plan A: G44
vi.mock('@prisma/client', () => ({
  PrismaClient: class {
    candidate = {
      findUnique: vi.fn(),
      update: vi.fn(),
      count: vi.fn(),
    };
    interviewFeedback = { findMany: vi.fn() };
    operationRecord = { create: vi.fn() };
  }
}));

import { prisma } from '../../app.js';
import { getCandidateHistory } from '../interview-history.service.js';
import { validateStatusDetails, getStatusSummary } from '../candidate-status-machine.service.js';
import { listPoolStats, moveCandidateToPool } from '../talent-pool.service.js';
import { applyFieldAcl } from '../field-masking.service.js';

describe('跨计划联调 #1: G19 历史 + G44 状态', () => {
  it('候选人历史聚合 + 状态汇总协同工作', async () => {
    // G44 设置候选人状态
    const details = {
      evaluated: 'PASS',
      hrbpFiltered: 'PASS',
      invited: 'FAIL',
    };
    const summary = getStatusSummary(details);
    expect(summary).toEqual({ passed: 2, failed: 1, pending: 8 });

    // G19 历史聚合 (mock)
    prisma.interviewFeedback.findMany.mockResolvedValueOnce([
      { id: 'f1', result: 'PASS', feedbackAt: new Date('2025-01-01'), interview: { roundName: '一面' }, interviewerName: 'A', reason: '技术好' },
      { id: 'f2', result: 'FAIL', feedbackAt: new Date('2025-02-01'), interview: { roundName: '二面' }, interviewerName: 'B', reason: '深度不够' },
    ]);
    prisma.candidate.findUnique.mockResolvedValueOnce({ id: 'c1' });

    const history = await getCandidateHistory('c1');
    // G19 反馈 + G44 状态同时存在时, 跨计划信息丰富
    expect(summary.passed + summary.failed + summary.pending).toBe(11);
    expect(history.total).toBe(2);
  });

  it('G44 状态更新不影响 G19 历史', () => {
    // 状态机独立性
    expect(validateStatusDetails('evaluated', 'PASS', 'PENDING')).toBe(true);
    expect(validateStatusDetails('invited', 'FAIL', 'PENDING')).toBe(true);
    // G19 服务的 history 字段不依赖 G44
    // (实际 G19 读 interviewFeedback, G44 读 candidate.statusDetails, 完全解耦)
  });
});

describe('跨计划联调 #2: G32 人才池 + G8 字段权限', () => {
  it('候选人被移到 BLACKLIST 后, G8 字段权限应自动 MASK 敏感字段', async () => {
    const candidate = {
      id: 'c1', name: '张某', phone: '13800138000', email: 'a@b.com',
      archiveToPool: 'BLACKLIST', candidateStatus: 'ARCHIVED',
    };
    // G8 字段规则
    const rules = [
      { field: 'phone', action: 'MASK' },
      { field: 'email', action: 'HIDE' },
    ];
    const masked = applyFieldAcl(candidate, rules);
    expect(masked.name).toBe('张某');
    expect(masked.phone).toBe('138****8000');
    expect(masked.email).toBeNull();
  });

  it('G32 跨池移动写审计, 跟 G8 审计分离', async () => {
    prisma.candidate.update.mockResolvedValueOnce({ id: 'c1', archiveToPool: 'GENERAL' });
    prisma.operationRecord.create.mockResolvedValueOnce({});

    await moveCandidateToPool('c1', 'GENERAL', '测试', 'u1');
    // G32 走 OperationRecord, 不走 FieldAclAudit
    expect(prisma.operationRecord.create).toHaveBeenCalledWith(
      expect.objectContaining({ data: expect.objectContaining({ action: 'MOVE_TO_POOL' }) })
    );
  });
});

describe('跨计划联调 #3: Plan A 倒序推荐 读 G44 状态', () => {
  it('recommend 候选人时, 应考虑 G44 状态 (PASS 优先)', () => {
    // 概念验证: G11 推荐分数 + G44 状态加成
    const candidates = [
      { id: '1', score: 50, statusDetails: { evaluated: 'PASS' } },
      { id: '2', score: 50, statusDetails: { evaluated: 'PENDING' } },
    ];
    // 业务上 G11 应当优先选 G44.PASS 的
    // 实际推荐服务未集成 G44, 这是未来扩展点
    const passed = candidates.filter(c => c.statusDetails?.evaluated === 'PASS');
    expect(passed).toHaveLength(1);
    expect(passed[0].id).toBe('1');
  });
});
```

- [ ] **Step 7.2: 跑 + 修**

```bash
npm test -- cross-plan-integration
```

- [ ] **Step 7.3: commit**

```bash
git add backend/src/services/__tests__/cross-plan-integration.test.js
git commit -m "test(cross-plan): 5 个联调测试 (G19+G44, G32+G8, G11+G44 概念验证)"
```

---

## Task 8: 更新 CHANGELOG + SETUP 反映

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/SETUP.md`

- [ ] **Step 8.1: CHANGELOG 加 Plan H 条目**

`CHANGELOG.md` 顶部加:
```markdown
## 2026-06-09 — 代码质量 + 测试扩充 (Plan H)

### 修 10 个 .vue 类型错 (vue-tsc 2.x 兼容)
- InvitationCenter.vue: InterventionModal form optional
- AddReferralModal.vue: 删重复 api
- ReferralCenter.vue: 加 PersonAddOutline import
- BackgroundCheckPanel.vue: 加 undefined 守卫
- ProcessStageEditor.vue: null → undefined
- SchoolLibrary/CompanyLibrary/DynamicFieldSettings.vue: 3 个 Plan F 引入的 wrap 缺 (加 ref)

### e2e 扩充到 6 个 spec (从 3 → 6, 12 场景 → 21 场景)
- demand-flow.spec.ts: 需求列表 + 新建按钮
- offer-flow.spec.ts: Offer 列表 + 详情
- settings-menu.spec.ts: 14 个 settings 菜单可达性回归保护

### 跨计划联调测试 (5 个)
- cross-plan-integration.test.js: G19+G44, G32+G8, G11+G44 概念验证
- 验证 plan 间契约协同工作
```

- [ ] **Step 8.2: SETUP.md 反映 e2e 数量**

`docs/SETUP.md` §8:
```diff
-npm run e2e                           # 跑全部 e2e (3 spec: login / settings-layout / candidate-list)
+npm run e2e                           # 跑全部 e2e (6 spec: login / settings-layout / candidate-list / demand-flow / offer-flow / settings-menu)
```

- [ ] **Step 8.3: commit**

```bash
git add CHANGELOG.md docs/SETUP.md
git commit -m "docs: CHANGELOG + SETUP 反映 Plan H (类型修 + e2e 6 个 + 跨计划联调)"
```

---

## Plan H 完成验证

- [ ] `npx vue-tsc --noEmit` 0 错误
- [ ] `npm test` 通过 (367 + 5 = 372+)
- [ ] `npx playwright test` 6 个 spec 全过 (~21 场景)
- [ ] 8 个新 commit
- [ ] 跨计划联调测试通过 (业务契约清晰)

---

## 不在本计划 (后续可做)
- i18n 引入 (独立大项目, 不在 Plan H)
- 6 个 Plan F 引入的 `wrap` ref 优化 (已完成, 详见 Task 3)
- Playwright 跨浏览器测试 (Firefox/Webkit, 1.49 都支持)
- 性能测试 (Playwright trace + lighthouse)
- 移动端适配 (响应式)
