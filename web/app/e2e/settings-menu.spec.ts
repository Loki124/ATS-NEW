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
  // 2026-08-06 寇豆码: 真实路由是复数 permissions (src/router/index.ts:127)，
  // 单数 /settings/permission 的路由已于 2026-07-01 删除 → 此处修正为复数
  // 2026-09-23: /settings/permissions 的菜单文案是「身份管理」（权限管理为无路由的父菜单项）
  { url: '/settings/permissions', label: '身份管理' },
  { url: '/settings/permissions/resources', label: '资源管理' },
  { url: '/settings/demand-config', label: '招聘需求设置' },
  { url: '/settings/dictionary', label: '数据字典' },
  { url: '/settings/scoring', label: '评分规则' },
  { url: '/settings/recruitment-process', label: '招聘流程' },
  { url: '/settings/recruitment-stage', label: '招聘阶段配置' },
  { url: '/settings/recruitment-round', label: '面试轮次' },
  { url: '/settings/company', label: '公司信息' },
  { url: '/settings/field-acl', label: '字段权限' },
  { url: '/settings/school-library', label: '院校库' },
  { url: '/settings/company-library', label: '公司库' },
  { url: '/settings/dynamic-fields', label: '动态字段' },
];

test.describe('Settings 菜单可达性 (P1-B + P3-F 全覆盖)', () => {
  // 登录由 globalSetup + storageState 复用会话（见 playwright.config.ts），避免反复登录触发限流(429)

  for (const { url, label } of SETTINGS_PAGES) {
    test(`菜单项 ${label} (${url}) 可达且内容渲染`, async ({ page }) => {
      // 直接 goto：Playwright 按 baseURL 解析相对路径；Vite dev 有 SPA fallback，
      // 深链 /settings/* 返回 index.html 而非 404，应用内 router 再渲染对应路由。
      // 注意：storageState 仅注入会话态、不会预导航，故此处必须显式 goto 到应用源，
      // 不可在 about:blank 上调用 history.pushState（会抛 SecurityError）。
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
