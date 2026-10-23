import { test, expect } from '@playwright/test';

/**
 * Login flow e2e
 * - 场景 1: 正确密码 (admin/admin123) -> 跳转 dashboard
 * - 场景 2: 错误密码 -> 提示失败
 *
 * 选择器策略: 优先 placeholder + role/text (Naive UI 组件的 class 难稳定)
 *
 * ── 2026-10-23 假红修正（只改断言，不改被测行为）────────────────────────────
 * 原第 15 行：`await expect(page.getByText('ATS招聘管理系统')).toBeVisible();`
 *
 * 该期望值与真实渲染不符（**无空格**），真实文案是**有空格**的：
 *   · 文案真源：src/locales/domains/zh-CN.APP_UI_ZH.ts:72
 *       'pages.Login.s1': "ATS 招聘管理系统"        ← ATS 与 招聘 之间有空格
 *   · 渲染点：src/pages/Login.vue:30
 *       <h1 class="brand-title gradient-title">{{ t('pages.Login.s1') }}</h1>
 *   · 「无空格」那一份来自 **web/app/index.html:10 的 <title>**（= 浏览器**标签页标题**，
 *     不是页面可见文案）。实测（2026-10-23 03:4x，vite 5215）：
 *         document.title                          = "ATS招聘管理系统"
 *         getByText('ATS招聘管理系统').count()     = 0   ← 原断言永远匹配不到
 *         getByText('ATS 招聘管理系统').count()    = 1   ← 真实可见文案
 *     Playwright 的文本匹配只作用于**已渲染元素**；<title> 在 <head> 里、不可见
 *     （locator('title').count() = 1 但 isVisible() = false）→ 不会被 getByText 命中。
 *     （另一处同名字符串 src/config/index.ts:10 `appName` 在 src/ 内零引用，同样不是渲染源。）
 *
 * 后果：场景 1 在**第一行断言**就 10s 超时 → 登录链路
 *      （填表 → 提交 → 跳离 /login）**从未被执行** → 假红掩盖了真实链路。
 */
test.describe('Login flow', () => {
  test('admin 正确密码登录后跳转 dashboard', async ({ page }) => {
    await page.goto('/login');

    // 登录卡片标题：真源 zh-CN.APP_UI_ZH.ts:72 → 由 Login.vue:30 渲染为 h1.brand-title
    // 这条断言同时充当「Vue 已挂载」门槛：标题可见 ⇒ 事件处理器已绑定，
    // 后续点登录按钮才不会被原生 form submit 吞掉（见 e2e/auth.setup.ts:21-33 的实测记录）。
    await expect(
      page.getByRole('heading', { name: 'ATS 招聘管理系统', exact: true }),
    ).toBeVisible();

    // 用户名输入框 (placeholder="用户名")
    const usernameInput = page.getByPlaceholder('用户名');
    await usernameInput.fill('admin');

    // 密码输入框 (placeholder="密码", type=password)
    const passwordInput = page.locator('input[type="password"]').first();
    await passwordInput.fill('admin123');

    // 登录按钮 (n-button "登 录")
    const loginButton = page.getByRole('button', { name: /登\s*录/ }).first();
    await expect(loginButton).toBeEnabled();
    await loginButton.click();

    // 等待跳转离开 /login
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });

    // 登录成功落点固定为 /dashboard（src/pages/Login.vue:245 `router.replace('/dashboard')`）
    // ⚠️ 若后端角色码断裂（返回 roles=["super_admin"] 之类），路由守卫会把登录态用户
    //    弹到 /forbidden（src/router/index.ts:329 `return next('/forbidden')`）
    //    → 下面这条路径断言会当场变红，而不是像原来那样在第一行就假红。
    expect(new URL(page.url()).pathname).toBe('/dashboard');

    // 工作台**真的渲染出来了**（不是错误页 / 空白页）
    // 真源：src/pages/Dashboard.vue:9 `<h1 class="hero-title">{{ greeting }}, {{ userName }}</h1>`
    await expect(page.locator('h1.hero-title')).toBeVisible();
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
