import { test, expect } from '@playwright/test';
import dayjs from 'dayjs';

/**
 * 招聘日程月视图 e2e (Plan T9)
 *
 * ⚠️ 2026-10-23 (W2) 断言重写 —— 当天的日程面板**已经不是抽屉了**：
 *
 * · web/app/src/components/dashboard/ScheduleDayDrawer.vue:2-13 组件头注释原文：
 *     「2026-10-21 (整改卡 E2 · AGENTS.md R-224): 抽屉回改居中弹窗。
 *       内容区固定高度 (R-223) + 仅内容区滚动 (R-215) + mask-closable=false (防误触丢失)。」
 *   实现是 `<n-modal preset="card">` → 渲染成 `.n-modal`（实测 class = "n-card n-modal"），
 *   **全站不存在 `.n-drawer` 元素**（`src/` 里只剩 `styles/glass-modal.css` 的遗留样式规则）。
 * → 旧断言 `locator('.n-drawer')` 恒为 0 个元素（不是"抽屉没打开"，而是"抽屉这个组件不存在了"）。
 *   （源仓 ATS-NEW 提交 4252f139「抽屉回改居中弹窗」即此改动。）
 *
 * · 真实结构（实测 DOM）：
 *     .n-modal.n-card
 *       └ .n-card-header > .n-card-header__main   ← 标题 = 被点那天的日期
 *            （ScheduleDayDrawer.vue:60-63 `dayjs(date).format('YYYY年M月D日 dddd')`）
 *       └ .n-card-content                        ← naive-ui 2.44.1 的内容容器 class 是
 *            │                                    `n-card-content`（**不是** `n-card__content`）
 *            └ .schedule-drawer__empty > .n-empty > .n-empty__description = 「当天无日程」
 *              （ScheduleDayDrawer.vue:14-16；无日程时）
 *            └ .schedule-drawer__item            （有日程时，每条一个）
 *              （ScheduleDayDrawer.vue:17-30）
 */
test.describe('Schedule month mode (T9)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('用户名').fill('admin');
    await page.locator('input[type="password"]').first().fill('admin123');
    await page.getByRole('button', { name: /登\s*录/ }).first().click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
  });

  test('切换月模式 + 点击某一天打开当天日程弹窗', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // 切到月模式 (WeeklySchedule.vue 提供 data-testid="mode-month")
    await page.click('[data-testid="mode-month"]');

    // 月网格可见
    const monthGrid = page.locator('.month-grid');
    await expect(monthGrid).toBeVisible();

    // 点「今天」那一格 —— WeeklySchedule.vue:79-88 给当天格子打 .month-grid__cell--today（唯一）。
    // （旧版点"第一个 cell"，那是跨月残留格，日期随月份漂移，无法做确定性断言）
    const todayCell = page.locator('.month-grid__cell--today');
    await expect(todayCell).toHaveCount(1);
    await todayCell.click();

    // 【显式缺失断言】当天面板不再是抽屉（依据 ScheduleDayDrawer.vue:2-13 已改为 n-modal preset="card"）
    await expect(page.locator('.n-drawer')).toHaveCount(0);

    // 面板已打开：真实容器是 .n-modal（naive-ui preset="card" → class="n-card n-modal"）
    const panel = page.locator('.n-modal').first();
    await expect(panel).toBeVisible({ timeout: 5_000 });
    await expect(panel).toHaveClass(/n-card/);
    await expect(panel).toHaveClass(/n-modal/);

    // 业务内容 ①：标题就是被点那天的日期（ScheduleDayDrawer.vue:60-63，与组件同一套 dayjs 格式）
    const title = (await panel.locator('.n-card-header__main').first().innerText()).trim();
    expect(title).toBe(dayjs().format('YYYY年M月D日 dddd'));

    // 业务内容 ②：当天内容区必须是「空态」或「日程条目」二者之一（缺一即为面板没渲染）
    const items = panel.locator('.schedule-drawer__item');
    const empty = panel.locator('.schedule-drawer__empty');
    const itemCount = await items.count();
    const emptyCount = await empty.count();
    expect(itemCount + emptyCount, '当天日程面板应渲染「日程条目」或「空态」之一').toBe(1);

    // 当天无排期时，空态文案必须是「当天无日程」（ScheduleDayDrawer.vue:15）
    if (emptyCount === 1) {
      await expect(panel.locator('.n-empty__description')).toHaveText('当天无日程');
    } else {
      // 有排期时：每条条目都要有时间与候选人名（ScheduleDayDrawer.vue:24-27）
      await expect(items.first().locator('.schedule-drawer__time')).not.toBeEmpty();
      await expect(items.first().locator('.schedule-drawer__name')).not.toBeEmpty();
    }
  });
});
