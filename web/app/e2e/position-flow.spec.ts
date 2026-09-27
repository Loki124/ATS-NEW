import { test, expect } from '@playwright/test'
import { fileURLToPath } from 'url'
import path from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const RESUME = path.join(__dirname, 'fixtures', 'sample-resume.txt')

/**
 * 职位管理「整体接真实 API」e2e 验收 (覆盖用户原始投诉: 职位管理有职位但创建候选人 Step2 选不到)。
 *
 * 依赖:
 * - 全局 globalSetup (auth.setup.ts) 已登录并落盘 storageState，本 spec 复用，不再各自登录(避免 429)。
 * - dev server 5212 (vite, 代理 /api → 8000) 与后端 8000 均已启动。
 *
 * 选择器策略:
 * - Naive UI n-select 无稳定 data-testid; 改为按「表单字段 label」定位其内部的 `.n-base-selection`。
 * - 简历解析接口用 route 拦截返回 mock 解析结果(参考 add-candidate-single-clean.spec.ts),
 *   避免依赖 dev mock 解析服务的时序抖动; 但 /positions/ 必须走真实库(证明 Step2 读真实职位)。
 */

// 在指定表单字段(label)的下拉里选第一个选项。
// 注意: 每个 n-select 有各自 teleport 出的 .n-select-menu, 已选过的下拉菜单会留在 DOM 里保持 hidden,
// 故必须定位「当前可见」的那个 menu, 否则会命中上一个隐藏菜单导致等不到可见。
async function pickSelectByLabel(page: import('@playwright/test').Page, label: string) {
  const fi = page.locator('.n-form-item', { hasText: label }).first()
  await fi.locator('.n-base-selection').first().click()
  const menu = page.locator('.n-select-menu:visible').first()
  await menu.waitFor({ state: 'visible', timeout: 8000 })
  await menu.locator('.n-base-select-option').first().click()
  await menu.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
}

async function createPositionViaUI(page: import('@playwright/test').Page, title: string) {
  await page.goto('/positions')
  await page.getByRole('button', { name: '创建职位' }).click()
  await page.getByPlaceholder('请输入职位名称').fill(title)
  await pickSelectByLabel(page, '所属部门')
  await pickSelectByLabel(page, '招聘流程')
  await pickSelectByLabel(page, '职位负责人')
  await pickSelectByLabel(page, '用人经理')
  await page.getByRole('button', { name: '保存' }).click()
  // 等待列表出现该职位
  await expect(page.getByText(title).first()).toBeVisible({ timeout: 10000 })
}

test.describe('职位管理 → 真实 API', () => {
  test('创建职位落库并出现在列表', async ({ page }) => {
    const title = `E2E职位_${Date.now()}`
    await createPositionViaUI(page, title)
    // 截图留证
    await page.screenshot({ path: 'e2e/__shots__/position-created.png', fullPage: false })
    // 断言：列表里确实能看到这条真实创建记录
    await expect(page.locator('.n-data-table-tr', { hasText: title })).toHaveCount(1, { timeout: 5000 })
  })

  test('创建候选人 Step2 能选到该职位 (闭合原始投诉链路)', async ({ page }) => {
    const title = `E2E职位_S2_${Date.now()}`
    // 1) 先真实创建职位
    await createPositionViaUI(page, title)

    // 2) 拦截简历解析接口，返回 mock 解析结果（不拦截 /positions/ —— Step2 必须读真实库）
    await page.route('**/api/v1/candidates/add-candidate/upload-and-parse/', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ job_ids: ['job_s2_1'], draft_ids: ['draft_s2_1'] }),
      })
    })
    await page.route('**/api/v1/candidates/add-candidate/parse-status/job_s2_1/', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          draft_id: 'draft_s2_1',
          status: 'done',
          phase: null,
          progress: 100,
          parsed: {
            name: '张三', phone: '13900000000', email: 'zhangsan@example.com',
            gender: '男', age: 30, educations: [], experiences: [], confidence: 0.9,
          },
          duplicate: { status: 'clean' },
        }),
      })
    })

    // 3) 打开创建候选人向导（真实按钮文案为「新增候选人」）
    await page.goto('/candidates')
    await page.getByTestId('add-candidate-btn').click()
    const modal = page.getByTestId('add-candidate-modal')
    await expect(modal).toBeVisible({ timeout: 8000 })

    // 4) Step1 上传简历（route 拦截 → mock 解析立即完成）
    const hiddenInput = page.getByTestId('hidden-file-input')
    await hiddenInput.setInputFiles(RESUME)

    // 5) 等待「下一步」按钮可用
    const nextBtn = page.getByTestId('next-step-btn')
    await expect(nextBtn).toBeEnabled({ timeout: 20000 })

    // 6) 进入 Step2
    await nextBtn.click()

    // 7) Step2 选择「职位」去向 —— 触发真实职位下拉渲染
    await page.locator('.dopt').filter({ hasText: '职位' }).click()

    // 8) 真实职位下拉里应出现刚创建的职位（证明 Step2 读真实 /positions/）
    const step2 = page.locator('.right-panel')
    await expect(step2).toBeVisible({ timeout: 8000 })
    await expect(step2.locator('.pos-item', { hasText: title })).toBeVisible({ timeout: 8000 })
    await page.screenshot({ path: 'e2e/__shots__/step2-shows-position.png', fullPage: false })
  })
})
