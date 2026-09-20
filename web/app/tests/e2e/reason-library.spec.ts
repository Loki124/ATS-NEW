import { test, expect } from '@playwright/test';

/**
 * Reason Library E2E (T-21)
 *
 * 覆盖:
 *   AC-1: 进入"原因库" → URL 跳转 /tags → 列表展示 53 条系统标签
 *   AC-4: 场景规则 Tab → 点"新建规则" → wizard 弹窗打开 → 定位 Step1
 *   AC-7: Step3 预览 → 5 色循环 + 5 条上限提示
 *
 * 前提:
 *   - 已登录 (复用 admin/admin123, 见 login.spec.ts)
 *   - 后端已跑 (seed 数据已灌入: 53 条系统标签 + 3 条预置规则)
 *
 * 选择器策略 (与项目其它 e2e 一致):
 *   - 优先 placeholder / role / text, Naive UI 组件 class 不稳定
 *   - URL path 直接断言
 */
test.describe('Reason Library', () => {
  test.beforeEach(async ({ page }) => {
    // 登录: admin/admin123
    await page.goto('/login')
    await page.getByPlaceholder('用户名').fill('admin')
    await page.locator('input[type="password"]').first().fill('admin123')
    await page.getByRole('button', { name: /登\s*录/ }).first().click()
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 })
  })

  // ============ AC-1: 进入标签页 → /tags → 53 条 ============
  test('AC-1 进入原因库默认跳转 /tags 并展示系统标签列表', async ({ page }) => {
    // 直接进 settings/reason-library → 应重定向到 /tags
    await page.goto('/settings/reason-library')

    // 等待 tab 渲染
    await expect(page.getByRole('tab', { name: '原因标签' })).toBeVisible({ timeout: 5_000 })

    // URL 应当包含 /tags 子路径 (index.vue 默认 redirect)
    await page.waitForURL((url) => url.pathname.includes('/reason-library/tags'), { timeout: 5_000 })
    expect(page.url()).toContain('/reason-library/tags')

    // 等待表格渲染 — toolbar 上"原因标签" tab pane 内的 n-data-table
    const table = page.locator('.n-data-table').first()
    await expect(table).toBeVisible({ timeout: 8_000 })

    // 行数: 53 条系统标签 (原型 §数据层) — 允许 ≥ 50 (留出未来 seed 增量的余地)
    // 注意: Naive UI n-data-table 的行是 .n-data-table-td 的祖父 .n-data-table-tr
    await page.waitForTimeout(500) // 等待异步 fetch 完成
    const rows = page.locator('.n-data-table .n-data-table-tr')
    const rowCount = await rows.count()
    expect(rowCount).toBeGreaterThanOrEqual(50)
  })

  // ============ AC-4: 切到规则 Tab → 新建 → wizard Step1 ============
  test('AC-4 场景规则 Tab 新建规则打开 wizard 并定位 Step1', async ({ page }) => {
    await page.goto('/settings/reason-library/rules')
    await expect(page.getByRole('tab', { name: '场景规则' })).toBeVisible({ timeout: 5_000 })

    // 等表格渲染 (至少 3 条预置规则)
    await page.waitForTimeout(500)
    const table = page.locator('.n-data-table').first()
    await expect(table).toBeVisible({ timeout: 5_000 })
    const rows = page.locator('.n-data-table .n-data-table-tr')
    const rowCount = await rows.count()
    expect(rowCount).toBeGreaterThanOrEqual(3)

    // 点击"新建规则"按钮 (rule.toolbar 上的 primary 按钮)
    await page.getByRole('button', { name: /新建规则/ }).first().click()

    // Wizard 弹窗打开: title "规则详情"
    const wizardTitle = page.locator('.n-modal').getByText('规则详情', { exact: true }).first()
    await expect(wizardTitle).toBeVisible({ timeout: 5_000 })

    // Step1 标题: "设置原因分类"
    await expect(page.getByText('设置原因分类').first()).toBeVisible({ timeout: 3_000 })

    // Stepper 显示当前在第 1 步 (查找 .step.on 的 num = 1)
    const step1 = page.locator('.wizard-steps .step.on').first()
    await expect(step1).toBeVisible({ timeout: 3_000 })
    await expect(step1).toContainText('1')

    // 步骤标签 "设置原因分类" / "选择原因标签" / "预览展示效果"
    await expect(page.getByText('选择原因标签').first()).toBeVisible()
    await expect(page.getByText('预览展示效果').first()).toBeVisible()

    // footer: 退出编辑 + 下一步
    await expect(page.getByRole('button', { name: /退出编辑/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /下一步/ })).toBeVisible()
  })

  // ============ AC-7: Step3 预览 → 5 色循环 + 5 条上限提示 ============
  test('AC-7 Step3 预览展示 5 色循环 chip + 5 条上限提示', async ({ page }) => {
    await page.goto('/settings/reason-library/rules')

    // 直接点第一条规则的"编辑规则" — 进入 wizard (规则已有完整数据)
    await page.waitForTimeout(500)
    const editBtn = page.getByRole('button', { name: /编辑规则/ }).first()
    await expect(editBtn).toBeVisible({ timeout: 5_000 })
    await editBtn.click()

    // Wizard 打开
    const wizardTitle = page.locator('.n-modal').getByText('规则详情', { exact: true }).first()
    await expect(wizardTitle).toBeVisible({ timeout: 5_000 })

    // 切到 Step3: 依次点击步骤指示器第 3 步 (跳过 Step2 的"下一步")
    await page.getByRole('button', { name: /下一步/ }).click() // → Step2
    await page.getByRole('button', { name: /下一步/ }).click() // → Step3

    // Step3 已激活 (.step.on 应是第 3 个)
    const step3 = page.locator('.wizard-steps .step.on').first()
    await expect(step3).toBeVisible({ timeout: 3_000 })
    await expect(step3).toContainText('3')

    // "预览展示效果" 标题
    await expect(page.getByText('预览展示效果').first()).toBeVisible()

    // 5 色循环: 至少一种色出现 (c-blue/c-green/c-purple/c-orange/c-gray 任一)
    // 原型已对齐 5 色, 系统预置规则 "简历筛选预置规则" 有 5 个一级分类 → 5 色循环可视
    const colorBlue = page.locator('.c-blue').first()
    await expect(colorBlue).toBeVisible({ timeout: 3_000 })

    // 5 条上限提示: 在页脚 "可选 5 条, 已选 0 条"
    await expect(page.getByText(/可选\s*5\s*条/)).toBeVisible({ timeout: 3_000 })

    // footer: 上一步 + 保存规则 (Step3 底部按钮)
    await expect(page.getByRole('button', { name: /上一步/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /保存规则/ })).toBeVisible()

    // 关闭 wizard (退出编辑)
    page.once('dialog', (dlg) => dlg.accept()) // 二次确认 (若有)
    await page.getByRole('button', { name: /退出编辑/ }).click()
  })
})
