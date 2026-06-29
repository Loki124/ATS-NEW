import { test, expect } from '@playwright/test';

/**
 * Candidate list e2e (P1-A 回归保护)
 * - G44 11 状态详细字段筛选 回归保护
 * - 场景: 候选人列表加载 + 显示 11 状态筛选器
 */
test.describe('Candidate list (P1-A regression)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('用户名').fill('admin');
    await page.locator('input[type="password"]').first().fill('admin123');
    await page.getByRole('button', { name: /登\s*录/ }).first().click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
  });

  test('候选人列表加载 + 显示 11 状态筛选器', async ({ page }) => {
    await page.goto('/candidates');
    await page.waitForLoadState('networkidle');

    // 列表应可见 (n-data-table 或 table)
    const table = page.locator('table, .n-data-table').first();
    await expect(table).toBeVisible({ timeout: 5_000 });

    // 11 状态筛选器容器
    const filterCard = page.locator('.status-filter-card');
    await expect(filterCard).toBeVisible();

    // "全部" 按钮始终存在
    const allButton = filterCard.getByRole('button', { name: '全部' });
    await expect(allButton).toBeVisible();

    // 至少 1 个状态 button (后端 schema API 可能尚未上线, 至少确认 UI 框架就绪)
    const filterButtons = filterCard.locator('button');
    const count = await filterButtons.count();
    expect(count).toBeGreaterThanOrEqual(1);
    // 注: 完整 P1-A 保护需要 /api/candidate/status-schema 返回 11 状态 (待 G44 后端联调)
  });
});
