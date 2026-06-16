import { test, expect } from '@playwright/test';

/**
 * Workbench stat-bar e2e (Plan T9)
 * - 验证 dashboard 顶部 4 合 1 StatBar 渲染正确
 * - 1 个 .stat-bar 容器 + 4 个 .stat-bar__item
 *
 * Note: T9 标记为 OPTIONAL, 测试不强制 CI 运行. 本地手动跑需要
 * 后端 :5125 + 前端 :5212 + `npx playwright install chromium`。
 */
test.describe('Workbench stat-bar (T9)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('用户名').fill('admin');
    await page.locator('input[type="password"]').first().fill('admin123');
    await page.getByRole('button', { name: /登\s*录/ }).first().click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
  });

  test('dashboard 顶部 1 个 stat-bar + 4 个 item', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // 合并后只有 1 个 stat-bar
    const statBar = page.locator('.stat-bar');
    await expect(statBar).toHaveCount(1);

    // 4 个指标项
    const items = page.locator('.stat-bar__item');
    await expect(items).toHaveCount(4);
  });
});
