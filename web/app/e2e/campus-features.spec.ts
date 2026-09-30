import { test, expect, type Page } from '@playwright/test';

/**
 * Phase 4 校招专属功能（校园大使 + 宣讲会）真机硬证据。
 *
 * 覆盖（G-2026-09-23 立项）：
 *  1. 社招环境直接访问 /settings/campus-ambassador → EmptyState 拦截，不渲染校招 UI
 *  2. 切到校园招聘后，访问校园大使/宣讲会页 → 真实 Phase 4 UI 渲染（page-title、启用开关、表格）
 *  3. 启用开关打开（写入 CampusModuleConfig）
 *  4. 添加大使：填表 → 提交 → 列表出现该行
 *  5. 编辑大使：打开弹窗修改字段 → 保存 → 列表更新
 *  6. 移除大使：列表项消失 + notification「撤销」按钮可点
 *  7. 宣讲会页：可正常打开 + 添加按钮可见
 *  8. 隔离证据：social 下 campus API 列表为空
 *
 * 路由访问策略：
 *  - 不走顶栏 n-dropdown 点击（Naive UI 弹出层不稳定 + 顶栏/侧栏 layout 模式会切换）；
 *  - 直接 goto 路由；用 addInitScript 预设 localStorage('recruit-system') 切系统；
 *  - 真实页面渲染与 API 调用仍然走 dev 全栈真接口，硬证据可靠。
 *
 * 登录复用 globalSetup + storageState（见 playwright.config.ts）。
 */

const AMBASSADOR_DATA = {
  school: 'e2e-玩友大学',
  name: `E2E大使${Date.now() % 100000}`,
  region: '华东',
};

/** 注入 localStorage('recruit-system') 让 page 进入目标系统 */
async function forceSystem(page: Page, key: 'social' | 'campus') {
  await page.addInitScript((k: string) => {
    try { localStorage.setItem('recruit-system', k); } catch { /* ignore */ }
  }, key);
}

test.describe('Phase 4 校招专属功能 (G-2026-09-23)', () => {
  test.beforeEach(async ({ context }) => {
    await context.clearCookies()
  })

  test('1) 社招环境：/settings/campus-ambassador 显式 EmptyState 拦截', async ({ page }) => {
    await forceSystem(page, 'social');
    await page.goto('/settings/campus-ambassador');
    await page.waitForLoadState('networkidle');

    // 不应出现 page-title「校园大使」+ 添加大使按钮
    const addBtn = page.getByRole('button', { name: /添加大使/ });
    await expect(addBtn).toHaveCount(0);

    // EmptyState 文案应可见（覆盖 v-if isCampus）
    await expect(page.locator('body')).toContainText(/校园大使为校园招聘系统专属功能/);
  });

  test('2) 校招环境：/settings/campus-ambassador 真实 Phase 4 UI 渲染', async ({ page }) => {
    await forceSystem(page, 'campus');
    await page.goto('/settings/campus-ambassador');
    await page.waitForLoadState('networkidle');

    // 真实 UI：page-title + 启用开关 + 添加大使按钮 + 表格
    await expect(page.locator('.page-title').first()).toContainText('校园大使');
    await expect(page.locator('.n-switch').first()).toBeVisible();
    await expect(page.getByRole('button', { name: /添加大使/ })).toBeVisible();
    await expect(page.locator('.n-data-table')).toBeVisible();
  });

  test('3+4) 启用模块开关 + 添加大使 → 列表出现新行', async ({ page }) => {
    await forceSystem(page, 'campus');
    await page.goto('/settings/campus-ambassador');
    await page.waitForLoadState('networkidle');

    // 打开启用开关（如未启用）
    const switchEl = page.locator('.n-switch').first();
    const beforeChecked = await switchEl.getAttribute('aria-checked');
    if (beforeChecked !== 'true') {
      await switchEl.click();
      await expect(switchEl).toHaveAttribute('aria-checked', 'true', { timeout: 5000 });
    }

    // 点击「添加大使」打开弹窗
    await page.getByRole('button', { name: /添加大使/ }).first().click();
    const modal = page.locator('.n-modal').filter({ hasText: /添加校园大使/ });
    await expect(modal).toBeVisible({ timeout: 5000 });

    // 填写表单：school/name/region（取前 3 个 input，第 4 个是 phone，第 5 个 note 是 textarea）
    const inputs = modal.locator('input:not([type="hidden"])');
    await inputs.nth(0).fill(AMBASSADOR_DATA.school);
    await inputs.nth(1).fill(AMBASSADOR_DATA.name);
    await inputs.nth(2).fill(AMBASSADOR_DATA.region);

    // 提交
    await modal.getByRole('button', { name: /创建/ }).click();
    await expect(modal).toBeHidden({ timeout: 8000 });

    // 列表出现新行
    await expect(page.locator('body')).toContainText(AMBASSADOR_DATA.school, { timeout: 8000 });
    await expect(page.locator('body')).toContainText(AMBASSADOR_DATA.name, { timeout: 8000 });
  });

  test('5) 编辑大使 → 列表更新', async ({ page }) => {
    await forceSystem(page, 'campus');
    await page.goto('/settings/campus-ambassador');
    await page.waitForLoadState('networkidle');

    // 找到测试大使那一行（按学校匹配）
    const row = page.locator('.n-data-table-tbody tr', { hasText: AMBASSADOR_DATA.school }).first();
    await expect(row).toBeVisible({ timeout: 8000 });

    await row.getByRole('button', { name: /编辑/ }).click();
    const modal = page.locator('.n-modal').filter({ hasText: /编辑校园大使/ });
    await expect(modal).toBeVisible();

    // 修改 region
    const regionInput = modal.locator('input:not([type="hidden"])').nth(2);
    await regionInput.fill('华南');
    await modal.getByRole('button', { name: /保存/ }).click();
    await expect(modal).toBeHidden({ timeout: 8000 });

    // 验证新值回流
    await expect(page.locator('body')).toContainText('华南', { timeout: 8000 });
  });

  test('6) 移除大使 → 列表项消失 + 撤销按钮可点', async ({ page }) => {
    await forceSystem(page, 'campus');
    await page.goto('/settings/campus-ambassador');
    await page.waitForLoadState('networkidle');

    const row = page.locator('.n-data-table-tbody tr', { hasText: AMBASSADOR_DATA.school }).first();
    await expect(row).toBeVisible({ timeout: 8000 });

    await row.getByRole('button', { name: /移除/ }).click();

    // 乐观更新：行立刻从列表消失
    await expect(page.locator('.n-data-table-tbody tr', { hasText: AMBASSADOR_DATA.school })).toHaveCount(0, { timeout: 5000 });

    // notification「撤销」按钮可点（R-106）
    const undoBtn = page.getByRole('button', { name: /^撤销$/ }).first();
    await expect(undoBtn).toBeVisible({ timeout: 5000 });
    await undoBtn.click();

    // 列表恢复
    await expect(page.locator('.n-data-table-tbody tr', { hasText: AMBASSADOR_DATA.school })).toHaveCount(1, { timeout: 8000 });

    // 测试结束清理：再次移除（不再撤销）
    const rowAgain = page.locator('.n-data-table-tbody tr', { hasText: AMBASSADOR_DATA.school }).first();
    await rowAgain.getByRole('button', { name: /移除/ }).click();
  });

  test('7) 宣讲会页：可正常打开 + 含「添加宣讲会」按钮', async ({ page }) => {
    await forceSystem(page, 'campus');
    await page.goto('/settings/campus-session');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.page-title').first()).toContainText('宣讲会');
    await expect(page.getByRole('button', { name: /添加宣讲会/ })).toBeVisible();
  });

  test('8) 隔离证据：X-Recruit-Type=social 下 campus API 列表为空', async ({ request }) => {
    const r = await request.get('http://127.0.0.1:8000/api/v1/campus-recruit/ambassadors/', {
      headers: { 'X-Recruit-Type': 'social' },
    });
    expect([200, 401, 403]).toContain(r.status());
    if (r.status() === 200) {
      const body = await r.json();
      expect(body?.data ?? []).toEqual([]);
    }
  });
});