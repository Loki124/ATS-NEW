import { test, expect } from '@playwright/test';

/**
 * 招聘日程月视图 e2e (Plan T9)
 * - 验证切到月模式后 .month-grid 渲染
 * - 点击某一天打开 .n-drawer 详情
 */
test.describe('Schedule month mode (T9)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('用户名').fill('admin');
    await page.locator('input[type="password"]').first().fill('admin123');
    await page.getByRole('button', { name: /登\s*录/ }).first().click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
  });

  test('切换月模式 + 点击某一天打开抽屉', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // 切到月模式 (WeeklySchedule.vue 提供 data-testid="mode-month")
    await page.click('[data-testid="mode-month"]');

    // 月网格可见
    const monthGrid = page.locator('.month-grid');
    await expect(monthGrid).toBeVisible();

    // 点第一个 .month-grid__cell (可能是 "上个月" 残留, 但仍是 cell)
    await page.locator('.month-grid__cell').first().click();

    // 抽屉打开
    await expect(page.locator('.n-drawer').first()).toBeVisible({ timeout: 5_000 });
  });
});
