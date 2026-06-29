import { test, expect } from '@playwright/test'
import { injectAuthToken, gotoCandidates } from './_add-candidate-helper'

/**
 * AddCandidateModal V2 - E2E: 替换简历 (replace-file) 流程
 *
 * 流程:
 * 1. 登录态
 * 2. 上传 1 份简历 (mocked)
 * 3. Step1Single 出现 "更换简历" 按钮
 * 4. 点击 replace -> file chooser 弹出
 * 5. setInputFiles -> 触发 replace-file API
 * 6. 验证 field-name 包含新名字
 */

const OLD_RESUME = Buffer.from('钱八\n13400134000\nqianba@example.com\n', 'utf-8')
const NEW_RESUME = Buffer.from('钱八 (新版)\n13400134000\nqianba2@example.com\n', 'utf-8')

test('add candidate - replace file flow', async ({ page }) => {
  let replaceCallCount = 0

  await page.route('**/api/v1/candidates/add-candidate/upload-and-parse/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ job_ids: ['job_r1'], draft_ids: ['draft_r1'] }),
    })
  })
  await page.route('**/api/v1/candidates/add-candidate/parse-status/job_r1/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        draft_id: 'draft_r1',
        status: 'done', phase: null, progress: 100,
        parsed: { name: '钱八', phone: '13400134000', email: 'qianba@example.com', educations: [], experiences: [], confidence: 0.9 },
        duplicate: { status: 'clean' },
      }),
    })
  })
  await page.route('**/api/v1/candidates/add-candidate/replace-file/draft_r1/', async (route) => {
    replaceCallCount += 1
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ job_id: 'job_r2', draft_id: 'draft_r1' }),
    })
  })
  await page.route('**/api/v1/candidates/add-candidate/parse-status/job_r2/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        draft_id: 'draft_r1',
        status: 'done', phase: null, progress: 100,
        parsed: { name: '钱八 (新版)', phone: '13400134000', email: 'qianba2@example.com', educations: [], experiences: [], confidence: 0.95 },
        duplicate: { status: 'clean' },
      }),
    })
  })

  await injectAuthToken(page)
  await gotoCandidates(page)
  await expect(page.getByTestId('add-candidate-btn')).toBeVisible({ timeout: 5_000 })
  await page.getByTestId('add-candidate-btn').click()

  const modal = page.getByTestId('add-candidate-modal')
  await expect(modal).toBeVisible()

  const hiddenInput = page.getByTestId('hidden-file-input')
  await hiddenInput.setInputFiles({ name: 'qianba.pdf', mimeType: 'application/pdf', buffer: OLD_RESUME })

  const replaceBtn = page.getByTestId('replace-file')
  await expect(replaceBtn).toBeVisible({ timeout: 10_000 })

  // 监听 file chooser
  const fileChooserPromise = page.waitForEvent('filechooser', { timeout: 5_000 })
  await replaceBtn.click()
  const fileChooser = await fileChooserPromise
  await fileChooser.setFiles({ name: 'qianba_new.pdf', mimeType: 'application/pdf', buffer: NEW_RESUME })

  // 验证 replace-file API 被调用
  await expect.poll(() => replaceCallCount, { timeout: 5_000 }).toBe(1)

  // 验证重新解析完成 - field-name 更新
  const nameField = page.getByTestId('field-name')
  await expect(nameField).toHaveValue('钱八 (新版)', { timeout: 10_000 })
})
