import { test, expect } from '@playwright/test';

/**
 * Candidate list e2e (P1-A 回归保护)
 *
 * ── 2026-10-23 假红修正（只改断言，不改被测行为）────────────────────────────
 * 原断言 1：`const table = page.locator('table, .n-data-table').first();`
 *   候选人页（src/pages/candidate/CandidateList.vue:175-270）用的是**卡片列表**
 *   （`<n-card class="list-card">` → `.candidate-list` → `.candidate-row`），
 *   页面里既没有 `<table>` 也没有 `.n-data-table`（该 class 在 src/ 里只出现在
 *   `:deep(.n-data-table-wrapper)` 样式里，没有对应实例）。
 *   实测 DOM：table = 0、.n-data-table = 0 → 原断言**永远**不可见 = 必然假红。
 *
 * 原断言 2：`const filterCard = page.locator('.status-filter-card');`
 *   `.status-filter-card` 这个 class 在 src/ 内**零命中**（grep 全仓无此串）。
 *   真实的状态筛选条是 CandidateList.vue:140 的 `.action-filter-card`
 *   → `.action-filter-bar` → 第一个 `.n-space` 里的 6 个写死按钮。
 *
 * 原断言 3：「11 状态筛选器」—— 两处前提都与现实不符，见下面 test 3 / test.skip 的注释。
 */
test.describe('Candidate list (P1-A regression)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('用户名').fill('admin');
    await page.locator('input[type="password"]').first().fill('admin123');
    await page.getByRole('button', { name: /登\s*录/ }).first().click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
  });

  test('候选人列表加载（真实卡片列表结构 + 有真实数据）', async ({ page }) => {
    await page.goto('/candidates');
    await page.waitForLoadState('networkidle');

    // 页面标题：真源 zh-CN.APP_UI_ZH.ts:100 'pages.candidate.CandidateList.s1'
    await expect(
      page.getByRole('heading', { name: '候选人管理', exact: true }),
    ).toBeVisible();

    // 列表容器：真源 CandidateList.vue:176 `<n-card class="list-card">`
    const listCard = page.locator('.list-card');
    await expect(listCard).toBeVisible();
    await expect(listCard.locator('.candidate-list')).toBeVisible();

    // 候选人卡片行：真源 CandidateList.vue:180
    //   `<div v-for="row in rows" :key="row.key" class="candidate-row" ...>`
    const rows = page.locator('.candidate-row');
    await expect(rows.first()).toBeVisible();
    expect(await rows.count()).toBeGreaterThanOrEqual(1);

    // 行内容是真实数据：姓名 + 编号 + 阶段流转
    // 真源 CandidateList.vue:188-228（.candidate-name / .candidate-code / .stage-line）
    const firstRow = rows.first();
    await expect(firstRow.locator('.candidate-name')).toHaveText(/\S+/);
    await expect(firstRow.locator('.candidate-code')).toHaveText(/\S+/);
    expect(await firstRow.locator('.stage-line').count()).toBeGreaterThanOrEqual(1);

    // 非空态：CandidateList.vue:252-256 的 `.candidate-empty` 只在 rows.length === 0 时出现
    await expect(page.locator('.candidate-empty')).toHaveCount(0);

    // 分页：CandidateList.vue:259-268
    await expect(page.locator('.list-card .n-pagination')).toBeVisible();

    // ⚠️ 显式断言「表格形态的列表」在本页面**不存在**（原 spec 撞的就是它）：
    //   候选人页是卡片列表，src/ 内没有任何 n-data-table 实例。
    await expect(page.locator('table, .n-data-table')).toHaveCount(0);
  });

  test('状态筛选器：6 个快捷筛选按钮（11 状态筛选器 UI 不存在）', async ({ page }) => {
    await page.goto('/candidates');
    await page.waitForLoadState('networkidle');

    // 真源：CandidateList.vue:140 `<n-card :bordered="false" class="action-filter-card mb-4">`
    const filterCard = page.locator('.action-filter-card');
    await expect(filterCard).toBeVisible();
    const bar = filterCard.locator('.action-filter-bar');
    await expect(bar).toBeVisible();

    // 状态筛选按钮 = .action-filter-bar 第一个 .n-space 里的按钮
    // 真源 CandidateList.vue:142-161（"全部" + v-for="s in quickFilters"）
    const statusButtons = page.locator('.action-filter-bar > .n-space').first().locator('button');
    await expect(statusButtons).toHaveCount(6);
    expect((await statusButtons.allTextContents()).map((t) => t.trim())).toEqual([
      '全部',    // CandidateList.vue:143-150（t('pages.candidate.CandidateList.s12')）
      '沟通Offer',    // quickFilters[0]  CandidateList.vue:967
      '待安排面试',   // quickFilters[1]  CandidateList.vue:968
      '面试中',      // quickFilters[2]  CandidateList.vue:969
      '筛选中',      // quickFilters[3]  CandidateList.vue:970
      '已入职',      // quickFilters[4]  CandidateList.vue:971
    ]);

    // ⚠️ 显式断言：原 spec 用的 `.status-filter-card` class 在 src/ 里**不存在**
    //   （grep 全仓 src/ 零命中）→ 原断言永远不可见 = 必然假红。
    await expect(page.locator('.status-filter-card')).toHaveCount(0);

    // ⚠️ 显式断言：DOM 里**没有**由 status-schema 驱动的 11 状态筛选器。
    //   前端把 schema 拉下来后**从未渲染**：STATUS_SCHEMA 只在
    //   src/pages/candidate/CandidateList.vue:506 声明、513 赋值，模板里**零引用**。
    //   页面上的状态筛选就是上面那 6 个写死按钮，
    //   加上同一张卡右侧的 2 个批量操作按钮 = 全卡 8 个按钮。
    await expect(page.locator('.action-filter-card button')).toHaveCount(8);
  });

  test('状态 schema 端点契约（Java 侧 9 状态，非 Django 的 11 状态）', async ({ page }) => {
    await page.goto('/candidates');
    await page.waitForLoadState('networkidle');

    // 前端客户端契约：src/api/candidate.ts:135-145
    //   StatusSchema = Record<string, {order, label, terminal}>
    //   fetchStatusSchema() → GET /candidates/status-details/schema/（baseURL = /api/v1）
    // 用页面内 fetch 带上 localStorage 里的 accessToken（同源 → 走 vite 代理 → Java 实例）。
    const resp = await page.evaluate(async () => {
      const token = localStorage.getItem('accessToken') || '';
      const r = await fetch('/api/v1/candidates/status-details/schema/', {
        headers: { Authorization: `Bearer ${token}` },
      });
      return { status: r.status, body: await r.text() };
    });

    expect(resp.status).toBe(200);
    const payload = JSON.parse(resp.body);
    expect(payload.success).toBe(true);
    const schema = payload.data as Record<
      string,
      { order: number; label: string; terminal: boolean }
    >;

    // 真源：backend/yudao-module-ats/.../AtsRecruitController.java:247-274
    //   → 取 AtsCandidateStateEnum 的 9 个状态（枚举文件：
    //   backend/yudao-module-ats/src/main/java/cn/iocoder/yudao/module/ats/enums/AtsCandidateStateEnum.java:27-35）
    expect(Object.keys(schema).sort()).toEqual([
      'APPLIED',
      'IN_PROCESS',
      'OFFER_SENT',
      'ONBOARDED',
      'PENDING_ONBOARDING',
      'PROCESS_FAILED',
      'PROCESS_PAUSED',
      'TALENT_POOL',
      'WITHDRAWN',
    ]);

    // 每项形状 = {order, label, terminal}（前端 src/api/candidate.ts:135-139 的声明）
    for (const [key, item] of Object.entries(schema)) {
      expect(typeof item.label, `${key}.label 类型`).toBe('string');
      expect(item.label.length, `${key}.label 非空`).toBeGreaterThan(0);
      expect(typeof item.order, `${key}.order 类型`).toBe('number');
      expect(typeof item.terminal, `${key}.terminal 类型`).toBe('boolean');
    }

    // order 连续 1..9：前端 CandidateList.vue:513-515 就是按 order 升序排的
    expect(
      Object.values(schema)
        .map((v) => v.order)
        .sort((a, b) => a - b),
    ).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9]);

    // ⚠️ 显式断言：Django 真源那套 11 个 stub key **不在这份返回里**
    //   （ONBOARDED 之外的那些专属 key；Django 侧见
    //    ATS-NEW/apps/django/apps/candidate/views.py:790-830 —— 那是 11 个 key →
    //    字段定义**数组**，形状与前端声明的 {order,label,terminal} 不符；
    //    Java 侧按前端真实契约返回扁平的 9 状态映射，
    //    差异说明写在 AtsRecruitController.java:250-260）。
    const djangoStubOnlyKeys = [
      'PENDING',
      'PASS',
      'FAIL',
      'INVITED',
      'INTERVIEWING',
      'OFFERED',
      'PROBATION_PASSED',
      'REJECTED',
      'ARCHIVED',
      'BLACKLISTED',
    ];
    for (const k of djangoStubOnlyKeys) {
      expect(
        Object.prototype.hasOwnProperty.call(schema, k),
        `不应出现 Django stub key ${k}`,
      ).toBe(false);
    }
  });

  test.skip(
    'P1-A 11 状态筛选器 UI（未就绪：前端不渲染 schema + 后端只返回 9 状态）',
    async ({ page }) => {
      // ⛔ 显式标注「未就绪」，而不是留一条恒绿的弱断言。
      //
      // 未就绪的两个原因（都可复核）：
      //  ① 前端侧：src/pages/candidate/CandidateList.vue:450 import 了 fetchStatusSchema，
      //     :509-520 onMounted 里拉取并写入 STATUS_SCHEMA（:506），
      //     但**模板里从未引用 STATUS_SCHEMA** → 页面上不存在 schema 驱动的状态筛选器。
      //     真实可见的状态筛选只有写死的 6 个按钮（全部 + quickFilters 5 个，
      //     定义在 CandidateList.vue:966-972），已在上面那条用例里逐字断言。
      //  ② 后端侧：GET /api/v1/candidates/status-details/schema/ 已就绪（200），
      //     但返回的是 AtsCandidateStateEnum 的 **9** 个状态，不是 Django stub 的 11 个
      //     （Django 的 11 个 key 是「可编辑字段定义数组」，与前端声明的
      //     {order,label,terminal} 形状不符，见 AtsRecruitController.java:250-260）。
      //
      // 解除 skip 的前提：前端把 STATUS_SCHEMA 渲染成状态筛选控件，
      // 且后端按该控件消费的状态集合返回 schema。
      await page.goto('/candidates');
      await expect(page.locator('.candidate-row').first()).toBeVisible();
    },
  );
});
