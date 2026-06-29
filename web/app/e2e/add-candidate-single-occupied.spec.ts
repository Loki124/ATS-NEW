import { test, expect } from '@playwright/test'
import { injectAuthToken, gotoCandidates } from './_add-candidate-helper'

/**
 * AddCandidateModal V2 - E2E: 单份已占用 (occupied) 流程
 *
 * 流程:
 * 1. 登录态
 * 2. /candidates
 * 3. 上传简历 -> mock occupied
 * 4. 验证 5 个 OccupiedActions 按钮可见
 * 5. 点击 "申请分配" -> ApplyPositionSelector 出现
 * 6. 选择一个职位 -> selected
 */

const SAMPLE_RESUME = Buffer.from(
  '李四\n13900139000\nlisi@example.com\n女\n26\n硕士\n北京大学',
  'utf-8',
)

test('add candidate - single occupied flow with apply-position', async ({ page }) => {
  await page.route('**/api/v1/candidates/add-candidate/upload-and-parse/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ job_ids: ['job_occ_1'], draft_ids: ['draft_occ_1'] }),
    })
  })
  await page.route('**/api/v1/candidates/add-candidate/parse-status/job_occ_1/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        draft_id: 'draft_occ_1',
        status: 'done', phase: null, progress: 100,
        parsed: { name: '李四', phone: '13900139000', email: 'lisi@example.com', gender: '女', age: 26, educations: [], experiences: [], confidence: 0.92 },
        duplicate: {
          status: 'occupied',
          existing_resume_id: 'cand_existing_99',
          created_at: '2024-01-15T08:00:00Z',
          history: '曾应聘: 高级前端工程师',
          cur_status: '面试中',
          active_application_id: 'app_active_99',
        },
      }),
    })
  })
  await page.route('**/api/v1/candidates/add-candidate/bulk-create/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: 'task_occ',
        created_candidate_ids: ['cand_occ_1'],
        route: { draft_occ_1: 'cand_occ_1' },
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
  await hiddenInput.setInputFiles({ name: 'lisi.pdf', mimeType: 'application/pdf', buffer: SAMPLE_RESUME })

  // 验证 OccupiedActions 出现
  const occActions = page.locator('.occ-actions')
  await expect(occActions).toBeVisible({ timeout: 10_000 })
  const occButtons = occActions.locator('.occ-btn')
  await expect(occButtons).toHaveCount(5)

  // 点击 "申请分配"
  await page.getByRole('button', { name: '申请分配' }).click()

  // 等 ApplyPositionSelector 出现
  const posList = page.locator('.apply-pos-list')
  await expect(posList).toBeVisible({ timeout: 5_000 })

  const posItems = posList.locator('.apply-pos-item')
  await expect(posItems).toHaveCount(5)
  await expect(posItems.first()).toContainText('高级前端工程师')

  // 选择第一个职位
  await posItems.first().click()
  await expect(posItems.first()).toHaveClass(/sel/)
})
