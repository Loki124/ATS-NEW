import { test, expect } from '@playwright/test';

/**
 * Settings layout e2e
 * - 防止 4-commit 反复改的 settings layout 回归
 * - 场景 1: 子页内容高度不超出 viewport + 一点容差
 * - 场景 2: 切换 settings 菜单不破布局
 */
test.describe('Settings layout (regression guard)', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.getByPlaceholder('用户名').fill('admin');
    await page.locator('input[type="password"]').first().fill('admin123');
    await page.getByRole('button', { name: /登\s*录/ }).first().click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
  });

  test('settings 子页内容填满, 不超出 viewport', async ({ page }) => {
    await page.goto('/settings/account');
    await page.waitForLoadState('networkidle');

    // .settings-content 是子页内容容器
    const content = page.locator('.settings-content').first();
    await expect(content).toBeVisible();

    const viewport = page.viewportSize();
    const contentBox = await content.boundingBox();

    // 内容高度不应超出 viewport + 50px 容差
    expect(viewport, 'viewport should be defined').not.toBeNull();
    expect(contentBox, 'content should have a bounding box').not.toBeNull();
    if (viewport && contentBox) {
      expect(contentBox.height).toBeLessThanOrEqual(viewport.height + 50);
    }
  });

  test('切换 settings 菜单不破布局', async ({ page }) => {
    await page.goto('/settings/account');
    await page.waitForLoadState('networkidle');

    // 切到权限管理 (route: /settings/permission)
    await page.getByText('权限管理').first().click();
    await page.waitForURL(/permission/);
    await page.waitForLoadState('networkidle');

    // 再切到公司信息 (route: /settings/company)
    await page.getByText('公司信息').first().click();
    await page.waitForURL(/company/);
    await page.waitForLoadState('networkidle');

    // 仍可见内容
    await expect(page.locator('.settings-content').first()).toBeVisible();

    // 容器高度仍不超出 viewport
    const viewport = page.viewportSize();
    const contentBox = await page.locator('.settings-content').first().boundingBox();
    if (viewport && contentBox) {
      expect(contentBox.height).toBeLessThanOrEqual(viewport.height + 50);
    }
  });
});
