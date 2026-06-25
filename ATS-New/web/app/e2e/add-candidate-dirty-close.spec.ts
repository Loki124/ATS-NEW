import { test, expect } from '@playwright/test'
import { injectAuthToken, gotoCandidates } from './_add-candidate-helper'

/**
 * AddCandidateModal V2 - E2E: 脏数据关闭确认
 *
 * 流程:
 * 1. 登录态
 * 2. 上传 1 份简历 -> Step1Single
 * 3. 修改 field-name (触发 isDirty)
 * 4. 等 recheck 完成
 * 5. 点击 X (n-modal close) -> 触发 confirm
 * 6. dismiss -> modal 仍打开
 * 7. 再次 X, accept -> modal 关闭
 */

const SAMPLE_RESUME = Buffer.from('周九\n13300133000\nzhoujiu@example.com\n', 'utf-8')

test('add candidate - dirty close confirms', async ({ page }) => {
  await page.route('**/api/v1/candidates/add-candidate/upload-and-parse/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ job_ids: ['job_d1'], draft_ids: ['draft_d1'] }),
    })
  })
  await page.route('**/api/v1/candidates/add-candidate/parse-status/job_d1/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        draft_id: 'draft_d1',
        status: 'done', phase: null, progress: 100,
        parsed: { name: '周九', phone: '13300133000', email: 'zhoujiu@example.com', educations: [], experiences: [], confidence: 0.9 },
        duplicate: { status: 'clean' },
      }),
    })
  })
  await page.route('**/api/v1/candidates/add-candidate/duplicate-check/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'clean' }),
    })
  })

  await injectAuthToken(page)
  await gotoCandidates(page)
  await expect(page.getByTestId('add-candidate-btn')).toBeVisible({ timeout: 5_000 })
  await page.getByTestId('add-candidate-btn').click()

  const modal = page.getByTestId('add-candidate-modal')
  await expect(modal).toBeVisible()

  const hiddenInput = page.getByTestId('hidden-file-input')
  await hiddenInput.setInputFiles({ name: 'zhoujiu.pdf', mimeType: 'application/pdf', buffer: SAMPLE_RESUME })

  const nameField = page.getByTestId('field-name')
  await expect(nameField).toBeVisible({ timeout: 10_000 })
  await expect(nameField).toHaveValue('周九')

  // 修改姓名 (触发 isDirty = true)
  await nameField.fill('周九 (改)')
  await nameField.blur()

  // 等 recheck 触发 (800ms debounce)
  await page.waitForTimeout(1500)

  // 第一次: dismiss dialog
  page.once('dialog', async (dialog) => {
    expect(dialog.type()).toBe('confirm')
    expect(dialog.message()).toContain('未保存')
    await dialog.dismiss()
  })

  // 点击 X (n-modal 的关闭按钮)
  await modal.locator('.n-base-close, .n-card-header__close').first().click()
  await page.waitForTimeout(500)
  await expect(modal).toBeVisible()

  // 第二次: accept dialog
  page.once('dialog', async (dialog) => {
    expect(dialog.type()).toBe('confirm')
    await dialog.accept()
  })

  await modal.locator('.n-base-close, .n-card-header__close').first().click()
  await expect(modal).not.toBeVisible({ timeout: 5_000 })
})
