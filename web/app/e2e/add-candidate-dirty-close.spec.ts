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
 * 5. 点击 X (n-modal close) -> 触发确认弹窗
 * 6. 点「取消」-> 弹窗关闭，主弹窗仍打开
 * 7. 再次 X -> 弹窗重现 -> 点「确认关闭」-> 主弹窗关闭
 *
 * ── 2026-10-23 假红修正（W4）────────────────────────────────────────────────────
 * 旧版按 **原生 `window.confirm()`** 语义写的：`page.on('dialog', …)` + `dialog.dismiss()/accept()`。
 * 但前端实现早已改成 **naive-ui `useDialog().warning()`**：
 *   · `src/pages/candidate/AddCandidateModal.vue:49-68`（`tryClose()`）
 *     —— 注释明写「P1 整改：移除原生 confirm()，统一用 useDialog().warning()」
 *     —— title='有未保存的修改' / content='确认关闭？未保存的修改将丢失。'
 *        positiveText='确认关闭' / negativeText='取消'
 *   · `src/composables/useCloseGuard.ts:40-47`（另一条同形守卫，同样是 dialog.warning）
 * ⇒ 浏览器**永远不会再触发原生 dialog 事件**：
 *   - 旧 `page.once('dialog')` handler 永不执行 → 没人去关掉 naive-ui 对话框
 *   - naive-ui 对话框常驻，其 `.n-modal-mask`（`es/modal/src/BodyWrapper.mjs:297`）
 *     拦截第二次点 X 的指针事件 → Playwright 一直 retry actionability → **用例 30s 超时**
 *   这就是本用例此前「假红」的真实成因（与后端无关：本 spec 自己 route-mock 了全部 3 个接口）。
 *
 * 现改为操作 **真实的 naive-ui 对话框**（DOM 契约见 naive-ui 2.44.1 源码）：
 *   · `es/dialog/src/Dialog.mjs` → 根节点 `div.n-dialog[role=dialog]`
 *     └ `div.n-dialog__title`（标题） / `div.n-dialog__content`（正文） / `div.n-dialog__action`（按钮区）
 *   · 按钮文案即实现常量：negativeText='取消'（ghost 按钮） / positiveText='确认关闭'（primary 按钮）
 * 两条语义断言**都保留**：
 *   - 「取消」→ 确认弹窗消失 且 主弹窗仍在
 *   - 「确认关闭」→ 主弹窗关闭
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

  // 修改姓名 (触发 store.isDirty = true —— Step1Single.vue:21-26 → store.updateField)
  await nameField.fill('周九 (改)')
  await nameField.blur()

  // 等 recheck 触发 (800ms debounce)
  await page.waitForTimeout(1500)

  // 主弹窗右上角 X（n-modal preset="card" → .n-card-header__close）
  const closeBtn = modal.locator('.n-base-close, .n-card-header__close').first()

  // naive-ui 确认对话框（useDialog().warning()）—— 用标题文案锁死「脏数据关闭确认」这一个实例
  const confirmDialog = page.locator('.n-dialog').filter({ hasText: '有未保存的修改' })

  // ── 第一次 X：弹出确认框 ──────────────────────────────────────────────────
  await closeBtn.click()

  await expect(confirmDialog).toBeVisible({ timeout: 5_000 })
  // 标题/正文取自 AddCandidateModal.vue:52-56（原文断言 '未保存' 的等价物）
  await expect(confirmDialog.locator('.n-dialog__title')).toHaveText('有未保存的修改')
  await expect(confirmDialog.locator('.n-dialog__content')).toContainText('未保存')

  // ── 语义 1：点「取消」→ 确认框关闭，主弹窗仍在 ────────────────────────────
  await confirmDialog.getByRole('button', { name: '取消' }).click()
  // 等到确认框从 DOM 移除：naive-ui 的 leave 动画结束后 .n-modal-container 连同
  // .n-modal-mask 一起被移除 —— 遮罩不在了，下一次点 X 才不会被拦截。
  await expect(confirmDialog).toHaveCount(0, { timeout: 5_000 })
  await expect(modal).toBeVisible()

  // ── 第二次 X：确认框再次弹出 ─────────────────────────────────────────────
  await closeBtn.click()
  await expect(confirmDialog).toBeVisible({ timeout: 5_000 })

  // ── 语义 2：点「确认关闭」→ 主弹窗关闭 ───────────────────────────────────
  await confirmDialog.getByRole('button', { name: '确认关闭' }).click()
  // 确认框自身也要消失（naive-ui hide() → leave 动画 → container 移除）
  await expect(confirmDialog).toHaveCount(0, { timeout: 5_000 })
  // 主弹窗关闭（弹窗卡随 .n-modal-container 一起从 DOM 移除）
  await expect(modal).not.toBeVisible({ timeout: 5_000 })
})
