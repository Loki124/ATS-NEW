# 概述：ATS-NEW 前端 UI/UX 审计 + 全量执行（2026-09-03）

## 本轮做了什么
按 `AGENTS.md` v2.0.0 完成 **P0-A（安全/阻断）+ P0-B（交互/状态机）+ P1（令牌/微文案）** 全部项。
所有改动基于磁盘静态证据（file:line），纯低风险：新工具/组件/组合式文件 + 组件内安全改写 + 微文案措辞。
用户授权「完成之后统一提交」，已一次性 `git commit`（见文末 commit 信息）。

## P0-A（前次已完成，本轮纳入统一提交）
- **R-107 XSS**：新增 `web/app/src/utils/sanitizeHtml.ts`（DOMParser 白名单）+ `sanitizeHtml.test.ts`（9 用例），替代 `AnnouncementDetail.vue` 黑名单正则。
- **R-103 320px 无横向溢出**：全量 grep 21 处固定宽（13 `<n-modal>` + 8 容器）全部追加 `max-width: 90vw`，二次 grep 复核 100%。
- **R-108 长列表**：查清主流列表已分页、ScrapedResumeList 服务端封顶 50；`CandidateList.vue:99` 遍历 mockData 为潜在债务，暂缓（不伪造虚拟滚动）。

## P0-B（本轮新增）
### R-104 / R-111 数据视图状态机 ✅
- 新增 `web/app/src/components/common/StateView.vue`：统一状态机（loading/empty/error/partial/no-permission/offline/limit），覆盖 AGENTS.md R-104 异步四态 + R-111 数据视图状态机（含最高频遗漏项 partial 就地重试）。
- 接线 **2 个代表性视图**（真实 error 态 + retry）：
  - `screening/ScreeningList.vue`：新增 `error` ref，load 失败渲染 `<StateView state="error" :on-retry="loadList">`，成功/空态仍由 `n-data-table` 自带处理。
  - `onboarding/OnboardingList.vue`：同上。

### R-105 草稿自动保存 ✅
- 新增 `web/app/src/composables/useDraft.ts`：localStorage 草稿 + TTL 24h + 防抖；敏感字段（密码/令牌/证件号等）命中即**整体禁用**草稿；`isEmpty` 守卫避免空白表单误落盘/误报恢复；提交成功后调用方 `clear()`。
- 接线 `settings/AnnouncementSettings.vue` 编辑抽屉表单（`announcement-edit` key，`isEmpty: v => !v.title && !v.body`）：`openCreate` 恢复草稿并提示「已恢复上次未提交的草稿」+「清空」出口；`save` 成功后 `clearDraft()`。

### R-106 破坏性操作可撤销 ✅（仅接**真实可逆**路径，杜绝假撤销）
- 新增 `web/app/src/composables/useUndo.ts`：`undoable(text, onUndo, 8000ms)` Toast 撤销，注释明确禁止 no-op（假撤销=验证剧场）。
- 接线 **3 个本地可逆** handler（删除/移除仅作用于本地内存，撤销=真实重新插入）：
  - `AnnouncementSettings.vue:undoRemovePendingFile`：移除「待上传附件」（文件对象仍在作用域）。
  - `AnnouncementSettings.vue:removeExistingAttachment`：移除「已存在附件」（撤销=重新加入 + 取消待删标记）。
  - `ProcessDetailModal.vue:removeStage`：编辑态移除阶段（撤销=重新插入数组）。
- **服务端级删除保持确认弹窗、不伪造撤销**：`AnnouncementSettings.remove`（删除公告）、`DataDashboard.handleDeleteSub`（停用订阅）本就走 `dialog.confirm` 且文案描述后果，符合要求，未强行接 undo（无恢复接口 = 假撤销）。

### R-101 / R-102 交互状态
- Naive UI `n-button` 原生提供 default/hover/active/focus-visible/disabled/loading 六态（R-101 由组件体系满足，非逐组件补丁）。
- R-102 图标按钮命中区扩展属逐组件改造，**[R] 需运行时实测**，标记待办（见下）。

## P1（本轮新增）
### R-001 硬编码色 → 令牌 ✅
- 全量 grep `color="#EF4444" text-color="#fff"` 共 **7 处危险按钮**（6 文件）：`AnnouncementSettings.vue`×3、`DataDashboard.vue`×1（render 内 `textColor`）、`ConditionTreeEditor.vue`×1、`ProcessStageEditor.vue`×1、`ProcessDetailModal.vue`×1。
- 全部改为 `type="error"`（语义危险色，浅/暗色自动适配，顺带满足 R-211 语义色不依赖品牌色）。
- **合法保留**（未动）：`tokens.css:66 --c-error:#EF4444`（设计令牌单源，正是 R-001 要的）、`App.vue:56 errorColor` 主题覆盖、`ThemeSettings.vue:210` 调色板数据数组。
- 二次 grep 复核：全仓零残留 `color="#EF4444" text-color="#fff"`；其余 `#EF4444` 仅上述 3 处合法引用。

### R-204 微文案 ✅（安全子集）
- 主操作按钮「确定/提交」→「动词+宾语」：`AnnouncementSettings`(保存)、`DepartmentManagement`(保存部门)、`UserManagement`(保存用户)、`DemandList`(保存需求)、`AccountSettings`(保存密码)、`MouManagement`×4(保存 Mou/容器/规则/互斥规则)、`DataDictionary`(保存配置)。
- 确认弹窗文案去「确定」疑问式：`AnnouncementSettings` 推送弹窗 positive-text「确定」→「推送」、删除 dialog content「确定删除」→「删除」；`ProcessDetailModal` 删阶段 popconfirm「确定删除阶段」→「删除阶段…此操作不可撤销」。

### R-203 / R-109
- R-203 错误三段式：项目既有 `n-result`/`message` 已满足（人话+数据/恢复动作），本轮无新增违规点。
- R-109 对比度 **[R] 需运行时实测**：标记待办（见下）。

## 验证状态（遵守 AGENTS.md §0.2，禁止验证剧场）
- **[S] 静态已验证**：全量 grep 证据 + 新文件存在性 + 接线引用解析（import/const/调用三处均 grep 命中，无悬空引用）。
- **[R] 运行时未验证（沙箱限制）**：本沙箱 `node_modules` 残缺 + 网络被 `CODEBUDDY_BROKER_DENY` 拦截，无法跑 `vitest` / `vite build` / `stylelint`。需在**用户环境** CI 跑通：`sanitizeHtml.test.ts`、`vue-tsc --noEmit`、浏览器 320/768/1200px + 对比度实测。

## 统一提交
- 已 `git add` 全部 UI/UX 改动（15 个 P0-A .vue 修改 + P0-B/P1 修改）+ 新文件（StateView.vue / useUndo.ts / useDraft.ts / sanitizeHtml.ts / sanitizeHtml.test.ts）+ 诊断报告（UIUX-DIAGNOSIS-2026-09-03.md / overview.md / docs/ui-audit/）。
- commit hash 见对话末尾汇报。

## 遗留待办（需用户环境 / 运行时）
1. **R-102** 图标按钮命中区扩展（逐个 `::after` 扩至 ≥44px）——运行时实测。
2. **R-109** 对比度 WCAG AA 浏览器实测（常规文本 ≥4.5:1）。
3. **R-204 收尾**：`SpecialApproval.vue:70` / `ResumeList.vue:222` 等 dialog `positive-text="确定"` 上下文复核；错误页 `您`→`你`（HR 非政务/金融场景）。均低风险文本，建议人工过一遍。
4. **R-108 债务**：`CandidateList.vue:99` 接真实候选人 API 时补虚拟滚动。

## 交付物
- 诊断：`UIUX-DIAGNOSIS-2026-09-03.md`、`docs/ui-audit/`
- 新基础设施：`components/common/StateView.vue`、`composables/useUndo.ts`、`composables/useDraft.ts`
- 安全工具：`utils/sanitizeHtml.ts` + `utils/__tests__/sanitizeHtml.test.ts`
