import { test, expect } from '@playwright/test';

/**
 * 招聘流程详情弹窗 e2e (Plan T9)
 * - 验证 ProcessDetailModal 打开后渲染阶段卡片
 * - 验证 "前往编辑" 按钮可用 (data-testid="btn-go-edit")
 */
test.describe('Process detail modal (T9)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('用户名').fill('admin');
    await page.locator('input[type="password"]').first().fill('admin123');
    await page.getByRole('button', { name: /登\s*录/ }).first().click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
  });

  test('点击详情按钮打开弹窗 + 阶段卡片可见', async ({ page }) => {
    // 招聘流程设置页 (router path: /settings/recruitment-process)
    await page.goto('/settings/recruitment-process');
    await page.waitForLoadState('networkidle');

    // 点击第一个 "详情" 按钮
    await page.locator('button:has-text("详情")').first().click();

    // 阶段卡片应在 n-modal 内可见
    const stageCard = page.locator('.n-modal').locator('.stage-card').first();
    await expect(stageCard).toBeVisible({ timeout: 5_000 });
  });

  test('前往编辑按钮可点击', async ({ page }) => {
    await page.goto('/settings/recruitment-process');
    await page.waitForLoadState('networkidle');

    await page.locator('button:has-text("详情")').first().click();

    // 等待弹窗渲染
    await expect(page.locator('.n-modal').first()).toBeVisible({ timeout: 5_000 });

    // 点击 前往编辑 (data-testid="btn-go-edit" 由 ProcessDetailModal 提供)
    // 行为: 可能关闭当前 modal + 打开编辑 modal, 也可能跳路由 — 实现以 T7 为准。
    const goEdit = page.locator('[data-testid="btn-go-edit"]');
    await expect(goEdit).toBeVisible();
    await goEdit.click();
    // 不强断言后续 modal 出现 (依赖实现细节), 至少保证按钮可点击不报错
  });
});
