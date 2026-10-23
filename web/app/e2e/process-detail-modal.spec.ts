import { test, expect } from '@playwright/test';

/**
 * 招聘流程详情弹窗 e2e (Plan T9)
 *
 * ⚠️ 2026-10-23 (W2) 断言重写 —— 旧断言依赖**当前前端根本不存在**的两个契约：
 *
 * 1) 「详情」按钮不存在
 *    · web/app/src/pages/settings/RecruitmentProcess.vue:142-176 —— 操作列只渲染
 *      「编辑」(i18n s15) 与「删除」(i18n s16)；被需求引用时把删除换成「改绑引用」(s26)。
 *      整个 `RecruitmentProcess` i18n 命名空间里**没有**「详情」这一条文案。
 *    · 实测（DOM 探针）：`.n-data-table button` 文本 = ["编辑","删除","编辑","删除","编辑","删除"]。
 *    → 旧断言 `button:has-text("详情")` 永远等不到元素 → 30s 超时（假红）。
 *
 * 2) `data-testid="btn-go-edit"`（前往编辑）不存在
 *    · web/app/src/pages/settings/ProcessDetailModal.vue:18 组件头注释原文：
 *      「旧契约 btn-enter-edit / enterEdit 已移除: 统一后不再有 view→edit 切换」。
 *    · 全仓 `src/` grep `btn-go-edit` = 0 命中；实测 `locator('[data-testid="btn-go-edit"]').count()` = 0。
 *    → 旧断言等一个已废弃契约，必然红。
 *
 * 真实入口（统一入口）：操作列的「编辑」按钮 → RecruitmentProcess.vue:147 `openProcessModal(row)`
 *   → :228-232 置 `showDetail=true` + `detailDefaultMode='edit'`
 *   → ProcessDetailModal.vue:690-704 打开即进编辑态（编辑态 = 展示态，单一模板）
 *   → 弹窗根节点 class = `n-card n-card--content-segmented n-card--footer-segmented n-modal process-detail-modal`
 *   → 阶段卡片 `.stage-card` 由 `v-for="stage in editForm.stages"` 渲染（ProcessDetailModal.vue:139-148），
 *     editForm.stages 来自 `GET /process-stage-links/?processId=`（ProcessDetailModal.vue:651-679, 799-812）。
 */
test.describe('Process detail modal (T9)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('用户名').fill('admin');
    await page.locator('input[type="password"]').first().fill('admin123');
    await page.getByRole('button', { name: /登\s*录/ }).first().click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
  });

  test('点操作列「编辑」打开统一弹窗 + 阶段卡片可见', async ({ page }) => {
    // 招聘流程设置页 (router path: /settings/recruitment-process)
    await page.goto('/settings/recruitment-process');
    await page.waitForLoadState('networkidle');

    // 【显式缺失断言】操作列没有「详情」按钮（依据 RecruitmentProcess.vue:142-176 + i18n 无该文案）
    // 先证明选择器命中了真实按钮（否则「没有详情」会变成空断言），再断言其中不含「详情」
    const actionBtnTexts = (await page.locator('.n-data-table button').allInnerTexts()).map((t) => t.trim());
    expect(actionBtnTexts, '操作列应含「编辑」按钮').toContain('编辑');
    expect(actionBtnTexts.filter((t) => t === '详情'), '操作列不应存在「详情」按钮').toHaveLength(0);

    // 统一入口 = 操作列「编辑」按钮（详情与编辑是同一个弹窗）
    const editBtn = page.locator('.n-data-table button', { hasText: '编辑' }).first();
    await expect(editBtn).toBeVisible();
    await editBtn.click();

    // 弹窗本体（ProcessDetailModal.vue:21-31 的 class="process-detail-modal"）
    const modal = page.locator('.n-modal.process-detail-modal').first();
    await expect(modal).toBeVisible({ timeout: 10_000 });

    // 阶段卡片应在弹窗内可见（ProcessDetailModal.vue:139-148）
    const stageCards = modal.locator('.stage-card');
    await expect(stageCards.first()).toBeVisible({ timeout: 10_000 });

    // 弹窗标题自称的阶段数 == 实际渲染的阶段卡片数
    // 标题来源 ProcessDetailModal.vue:571-576 modalTitle（stageCount = editForm.stages.length）
    // 文案 i18n: zh 'pages.settings.ProcessDetailModal.s91' = 编辑流程-「{nameTag}」-「{n} 个阶段」
    const title = (await modal.locator('.n-card-header__main').first().innerText()).trim();
    const stageCountInTitle = Number(/(\d+)\s*(?:个阶段|stages)/.exec(title)?.[1] ?? 0);
    expect(stageCountInTitle, `弹窗标题应含阶段数，实际标题: ${title}`).toBeGreaterThan(0);
    await expect(stageCards).toHaveCount(stageCountInTitle);

    // 首张阶段卡要有真实阶段名（不能是空壳）
    await expect(stageCards.first().locator('.stage-name')).not.toBeEmpty();

    // 弹窗确实回填了被点击行的流程（流程名称输入框非空）
    await expect(modal.locator('input[placeholder="流程名称"]')).toHaveValue(/.+/);
  });

  test('弹窗直接进编辑态（无「前往编辑」入口）+ 复制按钮存在 + 取消可关闭', async ({ page }) => {
    await page.goto('/settings/recruitment-process');
    await page.waitForLoadState('networkidle');

    await page.locator('.n-data-table button', { hasText: '编辑' }).first().click();

    const modal = page.locator('.n-modal.process-detail-modal').first();
    await expect(modal).toBeVisible({ timeout: 10_000 });

    // 【显式缺失断言】「前往编辑」契约已移除（依据 ProcessDetailModal.vue:18 组件头注释；
    //   全仓 src grep btn-go-edit = 0 命中，实测 count = 0）
    //   同一 data-testid 机制在本弹窗里是通的（btn-copy-process 能取到 1 个），故此处 0 是真缺失
    await expect(modal.locator('[data-testid="btn-copy-process"]')).toHaveCount(1);
    await expect(page.locator('[data-testid="btn-go-edit"]')).toHaveCount(0);

    // 统一入口打开即编辑态：流程名称输入框 + 「保存」都在
    await expect(modal.locator('input[placeholder="流程名称"]')).toBeVisible();
    await expect(modal.locator('.dp-modal-footer button', { hasText: '保存' })).toBeVisible();

    // 弹窗里唯一存活的 data-testid：「复制此流程」（ProcessDetailModal.vue:271）
    await expect(modal.locator('[data-testid="btn-copy-process"]')).toBeVisible();

    // 「取消」在未改动时直接关闭弹窗（ProcessDetailModal.vue cancelEdit：dirty=false → exitEditMode + update:show=false），
    // 不触发二次确认 → 证明交互链路真的通（该路径不写任何数据）
    await modal.locator('.dp-modal-footer button', { hasText: '取消' }).click();
    await expect(modal).toBeHidden({ timeout: 5_000 });
  });
});
