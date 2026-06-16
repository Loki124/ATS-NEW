import { test, expect } from '@playwright/test';

/**
 * GlobalSearch ⌘K / Ctrl+K e2e (Plan T9)
 * - 验证 GlobalSearch 模态框可被快捷键唤起
 * - 使用 Control+k 保证 headless Chromium 兼容
 *
 * Note: ⌘K 在 macOS 桌面端通常用 Meta+K, 但 Playwright 默认 headless
 * Chromium 没有 Meta 映射. 这里优先 Control+k, 并在断言失败时
 * 提示用真实浏览器手动验证。
 */
test.describe('GlobalSearch ⌘K (T9)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('用户名').fill('admin');
    await page.locator('input[type="password"]').first().fill('admin123');
    await page.getByRole('button', { name: /登\s*录/ }).first().click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
  });

  test('Ctrl/⌘K 唤起 GlobalSearch 模态框', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // 按 Ctrl+k 唤起 (headless 兼容)
    await page.keyboard.press('Control+k');

    // n-modal 包裹 .global-search
    const modal = page.locator('.n-modal').locator('.global-search');
    await expect(modal).toBeVisible({ timeout: 5_000 });
  });
});
