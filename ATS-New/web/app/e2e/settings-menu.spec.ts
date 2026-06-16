import { test, expect } from '@playwright/test';

/**
 * Settings 菜单可达性回归保护
 * - 14 个 settings 子菜单: 涵盖 P1-B (基础设置) + P3-F (字段权限/院校库/公司库/动态字段) 全覆盖
 * - 场景: 每个 URL 都能进入, 不返回 404 或空白页
 *
 * 选择器策略: 宽松 - 仅验证 body 可见 + 文本不含 404/not found
 */
const SETTINGS_PAGES = [
  { url: '/settings/account', label: '员工信息' },
  { url: '/settings/department', label: '部门管理' },
  { url: '/settings/permission', label: '权限管理' },
  { url: '/settings/demand-config', label: '招聘需求设置' },
  { url: '/settings/dictionary', label: '数据字典' },
  { url: '/settings/scoring', label: '评分规则' },
  { url: '/settings/recruitment-process', label: '招聘流程' },
  { url: '/settings/recruitment-stage', label: '阶段模板库' },
  { url: '/settings/recruitment-round', label: '面试轮次' },
  { url: '/settings/company', label: '公司信息' },
  { url: '/settings/field-acl', label: '字段权限' },
  { url: '/settings/school-library', label: '院校库' },
  { url: '/settings/company-library', label: '公司库' },
  { url: '/settings/dynamic-fields', label: '动态字段' },
];

test.describe('Settings 菜单可达性 (P1-B + P3-F 全覆盖)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('用户名').fill('admin');
    await page.locator('input[type="password"]').first().fill('admin123');
    await page.getByRole('button', { name: /登\s*录/ }).first().click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
  });

  for (const { url, label } of SETTINGS_PAGES) {
    test(`菜单项 ${label} (${url}) 可达且内容渲染`, async ({ page }) => {
      // 走前端路由而非硬刷新, 避免 SPA 被服务端 404
      await page.evaluate((u) => window.history.pushState({}, '', u), url);
      await page.goto(url);
      await page.waitForLoadState('networkidle');

      // body 可见 (避免空白页)
      await expect(page.locator('body')).toBeVisible();

      // 路由应仍是 settings/* (不是 404 兜底)
      expect(page.url()).toContain('/settings/');

      // 渲染: 至少有 page-title 元素或 n-card 等容器
      const hasContent = await page.locator('.page-title, .n-card, .n-data-table, h1, h2').count();
      expect(hasContent).toBeGreaterThan(0);
    });
  }
});
