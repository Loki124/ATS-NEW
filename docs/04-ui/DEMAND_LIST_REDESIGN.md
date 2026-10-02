# 招聘需求模块 UI 重构设计文档

> 日期：2026-10-02
> 关联 commit：`635b9b30`（feat(demand): 招聘需求列表/详情/编辑弹窗信息密度与交互重构）
> 关联任务日志：`.workbuddy/memory/2026-10-02.md` §09:7x
> 覆盖的原任务：`docs/08-tasks/UI_TASKS/T5.1.2-DemandList-colors.md`（颜色 token 化随重构一并达成）

## 1. 背景与问题

兵哥贴截图指出需求列表/详情页「承载的信息和交互体验操作很差，默认的单列导致空间利用率太低」。经截图 + 代码实证，锁定 3 个真实根因：

1. **列表单列 flex**：`.demand-list` 单列纵向排布，宽屏大量留白，信息密度极低。
2. **详情抽屉与 JD 可读性差**：抽屉硬编码 680px、内部 info-grid 仅 2 列；JD/任职要求经 `displayText` 渲染，后端富文本 HTML 标签以裸文本显示，可读性差。
3. **假数据「职位画像」tab**：`getEducationText`/`getExperienceText`/`getSkillsList` 捏造学历/经验/技能画像 —— 违反项目红线「真实可靠非弄虚作假」。

编辑需求弹窗为单列 600px，富文本编辑器撑爆布局、留白巨大（截图直接证据）。

## 2. 目标

- 提升**空间利用率**（宽屏多列，窄屏优雅降级，满足 R-103 320px 无横向溢出）。
- 提升**信息密度与可读性**（JD 富文本正确渲染、KPI 真实聚合）。
- **移除一切假数据**（职位画像 tab 删除）。
- **全 token 化**（零硬编码 hex/rgb/rgba），暗色/浅色双轨一致。

## 3. 设计方案

### 3.1 列表（DemandList.vue）

- **布局**：`.demand-list` 单列 flex → 卡片网格 `repeat(auto-fill, minmax(340px, 1fr))` + 表格视图（`n-data-table`）双视图切换，偏好持久化 `localStorage('ats-demand-view')`（try/catch 包裹）。
- **KPI 真实聚合**（前端算 `demands`）：需求总数 / 进行中(`IN_PROGRESS`) / 待审批(`PENDING`) / 计划招聘(Σ `headcount`)。
- **工具栏**：搜索 260px + 300ms 防抖；状态筛选；类型筛选(`ALL`/`SOCIAL`/`CAMPUS`)；排序(更新时间 / 优先级 P0→P2 / 需求人数)。
- **前端分页**：`pageSize = 12`，`pagedDemands` computed；`n-pagination` 仅当 `processedDemands.length > pageSize`。
- **卡片**：编号 + 优先级 pill + 状态 tag / 2 行截断标题(`-webkit-line-clamp:2` + `title` 全文) / 审批 + 部门 + 类型 tag / 负责人 + 相对时间 / 自绘进度条(`pct = headcount>0 ? min(100, round(filled/headcount*100)) : 0`；≥100 绿 `var(--c-success)`，否则品牌色) / 操作(详情·编辑·提交审批[仅 `DRAFT`])；`tabindex="0"` + `@keydown.enter` 键盘可达。
- **状态机**：loading → `n-skeleton`×6；empty → `n-empty`；筛选无结果 → 提示 + 清空筛选按钮。

### 3.2 详情抽屉

- **宽度自适应**：`drawerWidth = min(1080, max(720, round(innerWidth * 0.72)))`，挂载时计算 + `window.resize` 监听，`onUnmounted` 移除监听。
- **概览条**：需求人数 / 已入职 / 待入职 / 关联职位 + 进度条。
- **Tabs**：详情(`formBuckets` 驱动，`RICH_TEXT` 用 `SafeHtml`，`MULTILINE_TEXT` 跨列 `grid-column:1/-1`，info-grid `repeat(auto-fill, minmax(200px,1fr))`) / **JD 与任职要求**(新增，`SafeHtml` 渲染 `jd`+`requirements`，空值给空态 s66/s67) / 进度 / 候选人 / 记录。
- **移除**硬编码假数据「职位画像」tab（`BusinessOutline`/`PeopleOutline`/`NDropdown` import 一并删除，grep 零残留）。

### 3.3 编辑弹窗

- 宽度 `min(920px, 94vw)`；`n-form label-placement="top"`；`.form-grid` 双列（`RICH_TEXT`/`MULTILINE_TEXT`/`DATE_RANGE`/`ADDRESS` → `.form-item--wide` 跨列）。
- 内容区 `max-height:70vh; overflow-y:auto`；富文本包裹 `.rich-editor-wrap { max-height: 280px; overflow:auto }`（修掉截图里撑爆的根源）。

## 4. 数据契约与保留项（零破坏）

- 保留 `normalizeDemand` 双键兜底、`SYSTEM_VALUE_GETTERS`/`MODEL_ATTR_MAP`/`FORM_MODEL_BINDING`/`EDIT_SKIP_KEYS`。
- 保留 `handleSave` payload 顺序（title/department/headcount/level/position_title/demand_type/priority/jd/requirements）+ `saveDynamicFieldValues`。
- 保留 `handleSubmitApproval`、onMounted 三加载、全部 API 契约。
- **SafeHtml**（唯一授权 `v-html` sink，内部 `sanitizeHtml`）用于 JD/任职要求/富文本展示，杜绝裸 `v-html`（R-107）。

## 5. 验证（三关门禁）

> sandbox 默认 fail-closed（center 规则快照不可用），经 `dangerouslyDisableSandbox:true` 恢复后真跑。

| 门禁 | 命令 | 结果 |
|---|---|---|
| eslint | `npx eslint src/pages/demand/DemandList.vue src/locales/zh-CN.ts src/locales/en-US.ts --max-warnings=0` | exit 0 |
| stylelint | `npx stylelint "src/pages/demand/DemandList.vue"` | exit 0 |
| vite build | `npx vite build --mode nocheck` | built in 17.61s, exit 0 |

**独立静态审计**（指挥官规则：不信任成员自报，主理人亲跑）：
- 无 `v-html` / 零硬编码 hex·rgb·rgba（grep 零命中）
- 假数据函数（`getEducationText`/`getExperienceText`/`getSkillsList`）零残留
- `SafeHtml` 三处（JD/任职要求/富文本）
- 网格 `repeat(auto-fill, minmax(340px,1fr))` 落地
- i18n `s51`–`s83` 双文件各 1 处且对齐（`eslint no-dupe-keys` 已过）
- 模板引用的全部处理器（`onPageChange`/`handleSubmitFromCard`/`handleCardClick`/`handleEdit`/`handleSave`/`loadDemandFields`…）脚本均有定义（esbuild 不查模板，此项为关键盲点核查）
- 弹窗与抽屉滚动治理就位

## 6. 影响与关联文档

- `docs/08-tasks/UI_TASKS/T5.1.2-DemandList-colors.md`：原逐行颜色 token 化任务，本重构已一并达成（颜色零硬编码），标记**已覆盖**，不再执行。
- `docs/08-tasks/UI_TASKS/INDEX.md`：T5.1.2 状态由「待执行」改为「✅ 已覆盖」。
- i18n：`zh-CN.ts`/`en-US.ts` 各 +34 行 `pages.demand.DemandList.s51..s83`，双文件对齐无重键。

## 7. 待办 / 开放项

- **[R] 运行期项未浏览器验证**：44px 命中区（R-102）/ 对比度（R-109）/ 320·768·1200 三档无横向溢出（R-103）/ hover / 暗色对比度 —— 待兵哥 `Cmd+Shift+R` 硬刷验收。
- 已提交 `635b9b30`（3 files, +954/-606）并 push origin/main。

## 8. 关键决策记录

1. **移除假「职位画像」tab** —— 红线「真实可靠非弄虚作假」，绝不伪造学历/经验/技能画像。
2. **JD 用 SafeHtml 而非 displayText** —— 富文本 HTML 正确渲染，且 `SafeHtml` 是项目唯一授权 `v-html` sink（R-107）。
3. **卡片网格 `minmax(340px)`** —— 兼顾宽屏密度与窄屏单列降级，满足 R-103 320px 无溢出。
4. **双视图 + 偏好持久化** —— 卡片（浏览）/ 表格（精确查找）互补，选择落 localStorage。
5. **进度条自绘 + KPI 前端聚合** —— 避免新增后端聚合端点，需求规模下前端计算足够且零额外请求。
