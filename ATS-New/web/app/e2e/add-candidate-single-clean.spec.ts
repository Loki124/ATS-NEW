import { test, expect } from '@playwright/test'
import { injectAuthToken, gotoCandidates } from './_add-candidate-helper'

/**
 * AddCandidateModal V2 - E2E: 单份无重复 (clean) 流程
 *
 * 流程:
 * 1. 登录态 (token 注入)
 * 2. /candidates
 * 3. 点击 "新增候选人"
 * 4. Mock upload-and-parse -> parse-status (clean)
 * 5. 进入 step2: 待分配 + async
 * 6. 提交 -> AsyncResult -> close-async
 */

const SAMPLE_RESUME = Buffer.from(
  '张伟\n13800138000\nzhangwei@example.com\n男\n28\n本科\n清华大学\n计算机科学',
  'utf-8',
)

test('add candidate - single clean flow', async ({ page }) => {
  let callCount = 0
  await page.route('**/api/v1/candidates/add-candidate/upload-and-parse/', async (route) => {
    callCount += 1
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ job_ids: ['job_clean_1'], draft_ids: ['draft_clean_1'] }),
    })
  })
  await page.route('**/api/v1/candidates/add-candidate/parse-status/job_clean_1/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        draft_id: 'draft_clean_1',
        status: 'done',
        phase: null,
        progress: 100,
        parsed: {
          name: '张伟', phone: '13800138000', email: 'zhangwei@example.com',
          gender: '男', age: 28, educations: [], experiences: [], confidence: 0.95,
        },
        duplicate: { status: 'clean' },
      }),
    })
  })
  await page.route('**/api/v1/candidates/add-candidate/bulk-create/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: 'task_async_clean',
        created_candidate_ids: ['cand_clean_1'],
        route: { draft_clean_1: 'cand_clean_1' },
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
  await hiddenInput.setInputFiles({ name: 'zhangwei.pdf', mimeType: 'application/pdf', buffer: SAMPLE_RESUME })

  const nextBtn = page.getByTestId('next-step-btn')
  await expect(nextBtn).toBeVisible({ timeout: 10_000 })
  await expect(nextBtn).toBeEnabled()
  expect(callCount).toBeGreaterThanOrEqual(1)

  await nextBtn.click()

  // Step2: 选 "待分配"
  await page.locator('.dopt').filter({ hasText: '待分配' }).click()
  // 选 async
  await page.locator('.sc-opt').filter({ hasText: '提交后通知我' }).click()

  const submitBtn = page.getByTestId('submit-btn')
  await expect(submitBtn).toBeEnabled()
  await submitBtn.click()

  // 验证 AsyncResult 出现
  const closeAsync = page.getByTestId('close-async')
  await expect(closeAsync).toBeVisible({ timeout: 5_000 })

  // 关闭
  await closeAsync.click()
  await expect(modal).not.toBeVisible({ timeout: 5_000 })
})
