import { test, expect } from '@playwright/test';

/**
 * Login flow e2e
 * - 场景 1: 正确密码 (admin/admin123) -> 跳转 dashboard
 * - 场景 2: 错误密码 -> 提示失败
 *
 * 选择器策略: 优先 placeholder + role/text (Naive UI 组件的 class 难稳定)
 */
test.describe('Login flow', () => {
  test('admin 正确密码登录后跳转 dashboard', async ({ page }) => {
    await page.goto('/login');

    // 等登录卡片渲染
    await expect(page.getByText('ATS招聘管理系统')).toBeVisible();

    // 用户名输入框 (placeholder="用户名")
    const usernameInput = page.getByPlaceholder('用户名');
    await usernameInput.fill('admin');

    // 密码输入框 (placeholder="密码", type=password)
    const passwordInput = page.locator('input[type="password"]').first();
    await passwordInput.fill('admin123');

    // 登录按钮 (n-button "登 录")
    await page.getByRole('button', { name: /登\s*录/ }).first().click();

    // 等待跳转离开 /login
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
    expect(page.url()).not.toContain('/login');
  });

  test('错误密码显示失败提示', async ({ page }) => {
    await page.goto('/login');

    const usernameInput = page.getByPlaceholder('用户名');
    await usernameInput.fill('admin');

    const passwordInput = page.locator('input[type="password"]').first();
    await passwordInput.fill('wrong_password_xyz');

    await page.getByRole('button', { name: /登\s*录/ }).first().click();

    // 期待错误信息 (n-message / n-notification 显示"登录失败"或类似)
    // Naive UI message 默认 ~3.5s 自动消失, 5s 内能看到
    const errorToast = page.locator('.n-message').first();
    await expect(errorToast).toBeVisible({ timeout: 5_000 });

    // URL 仍应在 /login
    expect(page.url()).toContain('/login');
  });
});
