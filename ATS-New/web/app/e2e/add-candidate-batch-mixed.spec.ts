import { test, expect } from '@playwright/test'
import { injectAuthToken, gotoCandidates } from './_add-candidate-helper'

/**
 * AddCandidateModal V2 - E2E: 批量混合 (3 份) 流程
 *
 * 流程:
 * 1. 登录态
 * 2. /candidates
 * 3. 一次性上传 3 份简历 (clean / unocc / occupied)
 * 4. 验证 3 张 ResumeCard + 状态摘要
 * 5. 展开每张卡片
 * 6. 验证 occupied 导致 next-step-btn 不可用
 */

const SAMPLE_A = Buffer.from('王五\n13700137000\nwangwu@example.com\n', 'utf-8')
const SAMPLE_B = Buffer.from('赵六\n13600136000\nzhaoliu@example.com\n', 'utf-8')
const SAMPLE_C = Buffer.from('孙七\n13500135000\nsunqi@example.com\n', 'utf-8')

test('add candidate - batch (3 resumes) mixed flow', async ({ page }) => {
  await page.route('**/api/v1/candidates/add-candidate/upload-and-parse/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        job_ids: ['job_b1', 'job_b2', 'job_b3'],
        draft_ids: ['draft_b1', 'draft_b2', 'draft_b3'],
      }),
    })
  })
  await page.route('**/api/v1/candidates/add-candidate/parse-status/job_b1/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        draft_id: 'draft_b1',
        status: 'done', phase: null, progress: 100,
        parsed: { name: '王五', phone: '13700137000', email: 'wangwu@example.com', educations: [], experiences: [], confidence: 0.9 },
        duplicate: { status: 'clean' },
      }),
    })
  })
  await page.route('**/api/v1/candidates/add-candidate/parse-status/job_b2/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        draft_id: 'draft_b2',
        status: 'done', phase: null, progress: 100,
        parsed: { name: '赵六', phone: '13600136000', email: 'zhaoliu@example.com', educations: [], experiences: [], confidence: 0.88 },
        duplicate: { status: 'unocc' },
      }),
    })
  })
  await page.route('**/api/v1/candidates/add-candidate/parse-status/job_b3/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        draft_id: 'draft_b3',
        status: 'done', phase: null, progress: 100,
        parsed: { name: '孙七', phone: '13500135000', email: 'sunqi@example.com', educations: [], experiences: [], confidence: 0.85 },
        duplicate: { status: 'occupied', existing_resume_id: 'cand_99' },
      }),
    })
  })
  await page.route('**/api/v1/candidates/add-candidate/bulk-create/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: 'task_batch',
        created_candidate_ids: ['cand_b1', 'cand_b2', 'cand_b3'],
        route: { draft_b1: 'cand_b1', draft_b2: 'cand_b2', draft_b3: 'cand_b3' },
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
  await hiddenInput.setInputFiles([
    { name: 'wangwu.pdf', mimeType: 'application/pdf', buffer: SAMPLE_A },
    { name: 'zhaoliu.pdf', mimeType: 'application/pdf', buffer: SAMPLE_B },
    { name: 'sunqi.pdf', mimeType: 'application/pdf', buffer: SAMPLE_C },
  ])

  const cards = page.locator('.card-item')
  await expect(cards).toHaveCount(3, { timeout: 10_000 })

  // 验证状态摘要
  await expect(page.locator('.status-summary')).toContainText('1 份无重复')
  await expect(page.locator('.status-summary')).toContainText('1 份未占用')
  await expect(page.locator('.status-summary')).toContainText('1 份需处理')

  // 展开每张卡片
  for (let i = 0; i < 3; i += 1) {
    await cards.nth(i).locator('.c-header').click()
    await expect(cards.nth(i)).toHaveClass(/expanded/)
  }

  // has occupied -> canGoStep2 = false -> next-step-btn disabled
  const nextBtn = page.getByTestId('next-step-btn')
  await expect(nextBtn).toBeDisabled()
})
