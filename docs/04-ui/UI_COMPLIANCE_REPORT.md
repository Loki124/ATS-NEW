# ATS-NEW 前端 UI 规范符合性审查报告

> 审查范围：`web/app/src`（Vue3 + Naive UI + 自研液态玻璃设计系统）
> 审查基线：`tokens.css`（v2 设计令牌）、`glass.css` / `glass-modal.css`（玻璃原子类）、`stores/theme.ts`、`App.vue` 的 Naive `themeOverrides`
> 对照标准：WCAG 2.1 AA、响应式设计最佳实践、Apple HIG / Material Design 3
> 审查日期：2026-08-24
> 审查人：鹏城信息AI专家（Web 界面设计规范审查）

---

## 0. 总体结论

设计系统的**底座是健康的**：单一品牌输入（`--brand`）、`color-mix` 派生、暗色靠变量集整体切换（`body.dark`）、玻璃原子类、`lang="zh-CN"` 已就位，侧栏 footer / StatCard 等已做 `role`/`tabindex`/`keydown` 适配。

但存在 **1 个致命级（🔴）根因性缺陷 + 1 个致命级交互缺陷 + 6 个重要级（🟡）+ 若干建议级（🔵）**，核心矛盾与历史判断一致——**「4 套视觉语言 / 3 套品牌色」并未真正收敛**：本次发现的新一套灰色令牌 `--g1…--g7` 根本未被定义，说明 onboarding 流程是「用着一套不存在的令牌集在开发」。

| 等级 | 数量 | 说明 |
|------|------|------|
| 🔴 关键 | 2 | 未定义令牌家族（整条 onboarding 链路渲染崩坏）、原生 `confirm()` 阻断式对话框 |
| 🟡 重要 | 6 | 对比度不达标、`overflow-x:hidden` 裁剪宽表、KPI 栅格响应式错位、缺 `<main>` 地标/跳转、硬编码第 3 品牌紫、`page-title` 字号不统一 |
| 🔵 建议 | 7 | 无 `prefers-reduced-motion`、`:focus-visible` 覆盖不足、`100vh` 移动端、暗色对比兜底、`!important` 量过大、禁用态对比、缺 `theme-color` 元信息 |

---

## 1. 🔴 关键问题

### 1.1 未定义的令牌家族 `--g1 … --g7`（整条候选人录入链路渲染崩坏）
- **现象**：`Step1Single.vue`、`Step1Batch.vue`、`Step2Assign.vue`、`ScoringOverlay.vue`、`AsyncResult.vue`、`Stepper.vue`、`UploadZone.vue`、`DirectionPicker.vue`、`OccupiedActions.vue`、`ApplyPositionSelector.vue`、`DuplicateInfoCard.vue`、`PositionChips.vue`、`AddCandidateModal.vue` 大量引用 `var(--g1)`…`var(--g7)`。
- **根因**：全仓 `grep "--g1:"` **零定义**（已确认 `tokens.css` 及整个 `web/` 均无定义）。CSS 自定义属性未定义时，声明在 computed-value 阶段变为 *guaranteed-invalid* → 整条声明失效：
  - `background: var(--g1)`（disabled 输入框底色）→ 透明，禁用态「看起来仍是可编辑白底」。
  - `border: 1px solid var(--g3)`（分隔线 / 输入框描边）→ 整条 border 声明失效 → **无边框**。
  - `color: var(--g5)`（提示文字）→ 继承父级颜色（当前意外显示为深墨色，修好令牌后会变灰或更糟）。
- **证据（file:line）**：
  - `AddCandidateModal.vue:99` `<span style="color:var(--g5)">V2</span>`
  - `Step1Single.vue:89` `background: var(--g1)`（disabled 文件名输入框）
  - `Step1Single.vue:149,169,201,261,264,301,360,374,408,445,470` `var(--g3)` 边框
  - `Step1Batch.vue:35,104,123,129,140,147,156,179,192,197,209,220,225,251,276,287,290,343,369,393,396,427,446,459,510,522,526` 同上
  - `Step2Assign.vue:83,120,128,133,167,178,189,198,205,225,234,249,266,278,280,286,299,320,321,322,324,329` 同上
  - `UploadZone.vue:45,51,58,64`、`DirectionPicker.vue:40,51,55`、`OccupiedActions.vue:22`、`ApplyPositionSelector.vue:38`、`DuplicateInfoCard.vue:42`、`PositionChips.vue:31`
- **规范条款**：项目《DESIGN.md §2 单一事实来源》——「任何组件禁止再硬编码品牌色 / 模糊值 / 圆角，改 `--brand` 一处即可」；未定义令牌违反令牌系统基本契约。
- **修复**：在 `tokens.css` 的 `:root` 与 `body.dark` 内补全中性灰阶梯（见《统一设计规范 §2.3》），或在 onboarding 组件内逐处迁移到既有令牌。推荐**先补全令牌**（改动最小、零逐页风险）。

### 1.2 原生 `confirm()` 阻断式对话框
- **file:line**：
  - `AddCandidateModal.vue:26` `if (!confirm('有未保存的修改，确认关闭？')) return`
  - `AddCandidateModal.vue:37` 同上（`closeModal`）
  - `DynamicFieldSettings.vue:270` `if (!confirm(`确认删除字段 "${row.label}" 吗?`)) return;`
- **问题**：
  1. 阻塞 JS 主线程、样式不可控、无法与 Naive 的 `n-dialog` / `useDialog` 焦点栈协同（已有 `App.vue` 注入 `n-dialog-provider`）；
  2. 在部分 WebView / 自动化环境行为不稳定；
  3. 不符合 WCAG 2.1.1（键盘可达）与 2.4.3（焦点顺序）的最佳实践——原生 `confirm` 跳出时焦点被困在浏览器级对话框。
- **修复**：改用 `useDialog().warning({ title, content, positiveText, negativeText, onPositiveClick })`，与项目既有 `CampusControl.vue` 的 `dialog.warning(...)` 写法一致。

---

## 2. 🟡 重要问题

### 2.1 文字对比度 `--ink-faint` 不达 WCAG AA
- **计算**：`--ink-faint: #94A3B8`（浅色）对白底对比度 ≈ **2.6:1**，远低于 WCAG 2.1 AA 普通文字要求的 **4.5:1**（1.4.3 Contrast Minimum）。
- **受影响 file:line**：
  - `StatCard.vue:132` `.stat-card__suffix`（12px `--ink-faint`）
  - `StatCard.vue:169` `.stat-card__meta-text`
  - `Layout.vue:524` `.kbd-hint`（`--ink-faint`）
  - `glass.css:408` `.err-tag` 等
  - 各类 `text-ink-faint` 辅助文字
- **修复**：将用于文字的灰降至 `#64748B`（对白底 ≈ 4.8:1，达标）；或仅允许在 ≥18px / 非必要信息处使用浅灰。注意 1.1 修复后 `--g5` 若映射为浅灰用于文字，须同步满足 4.5:1。

### 2.2 数据表格 `overflow-x: hidden !important` 裁剪宽表
- **file:line**：
  - `glass.css:676` `.table-wrap .n-scrollbar-container { overflow-x: hidden !important; }`
  - `glass.css:709` `.settings-scroll … { overflow-x: hidden !important; }`
- **问题**：校招管控 `mergedColumns` 有 **17 列**（其中 `适用范围/维度/指标` 三列 `fixed:'left'`），`CandidateList` 等也是宽表。窄屏（平板 / 手机）下横向滚动被强制关闭 → 列被裁切、固定列与滚动列重叠错位。
- **规范**：响应式数据表格应保证窄屏可横向滚动或改卡片布局（Apple HIG / Material 响应式表格）。
- **修复**：仅在 `md` 及以上保留 `overflow-x:hidden`（配合 `min-width` 表头同步），`sm` 以下改为 `overflow-x:auto`；或给 `.n-data-table` 设 `min-width` 让容器自然出现横向滚动条。

### 2.3 KPI 栅格响应式错位（全局 4 列 vs 校招管控 5 列打架）
- **file:line**：
  - 全局 `glass.css:522-527` `.kpi-row { grid-template-columns: repeat(4,1fr) }` + `:563`(1024→2 列) + `:564`(480→1 列)
  - 校招管控 `CampusControl.vue:1367` scoped `.kpi-row { grid-template-columns: repeat(5,1fr) }`
- **问题**：scoped 选择器 `(0,2,0)` 特异性高于全局 `(0,1,0)`，把全局的 4 列与响应式断点全部覆盖 → 校招管控 KPI **始终 5 列**，平板/手机上 5 卡挤压溢出，不触发 2/1 列收缩。
- **修复**：全局改为 `repeat(auto-fit, minmax(180px, 1fr))` 自适应；或在校招管控同步使用 4 列并复用全局媒体查询，移除 scoped 覆盖。

### 2.4 缺 `<main>` 地标与跳转链接（Skip Link）
- **file:line**：`Layout.vue:159` `n-layout-content` 渲染为普通 `<div>`，内容区无 `role="main"` / `<main>`；全仓无 skip-to-content 链接。
- **规范**：WCAG 1.3.1（Info & Relationships）、2.4.1（Bypass Blocks）。
- **修复**：在 `Layout.vue` 的 `content-wrapper` 外包 `<main id="main">`，或在 `n-layout-content` 加 `role="main"`；在 `<body>` 顶部加 `.skip-link`（`:focus` 时可见）跳转至 `#main`。

### 2.5 硬编码「第 3 品牌紫」`#8B5CF6`
- **file:line**：
  - `Step1Single.vue:478` `.pfill.pu { background: #8B5CF6; }`
  - `Step1Batch.vue:454` `.pfill.pu { background: #8B5CF6; }`
- **问题**：项目已有 `--brand #6366F1` 与 `--brand-grad-a #A855F7`，此处又出现第 3 个紫 `#8B5CF6`（「3 套冲突品牌色」的具象残留），且硬编码不随主题换肤。
- **修复**：抽为令牌 `--c-category-purple`（或复用 `--brand-grad-a`），走 `tokens.css` 单来源。

### 2.6 页面标题 `page-title` 字号不统一
- **file:line**：
  - 全局 `glass.css:463` `.page-title { font-size: 26px !important; …渐变 }`
  - `ThemeSettings.vue:275-280` scoped `.page-title { font-size: var(--text-h1) /*32px*/ … }`（无渐变、字号不同）
- **问题**：设置中心标题在「校招管控 / 数据中心」等页是 26px 渐变，在「主题外观」页是 32px 纯墨，**同一 shell 内视觉语言分裂**。
- **修复**：统一为单一 `page-title` 规格（建议 26px 渐变），删除 `ThemeSettings.vue` 的 scoped 覆盖。

---

## 3. 🔵 建议级问题

| # | 问题 | file:line | 建议 |
|---|------|-----------|------|
| 3.1 | 全仓无 `prefers-reduced-motion` |（grep 零命中）| 在 `tokens.css` 末尾加 `@media (prefers-reduced-motion: reduce){ .workbench-card, *{animation-duration:.001ms!important;transition-duration:.001ms!important} }`，覆盖 hover `translateY`、入场动画 |
| 3.2 | `:focus-visible` 仅 `Layout.vue` 一处 | `Layout.vue:739` | 在 `glass.css` 加全局 `:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px }`，覆盖原生按钮（如 `ThemeSettings.vue:46` `.preset-swatch`）、自定义可点元素 |
| 3.3 | `100vh` 移动端地址栏问题 | `Layout.vue:618` `.app-layout{height:100vh}`、`AddCandidateModal.vue:103` `height:80vh` | 改用 `100dvh` / `min(80vh, …)` |
| 3.4 | 禁用按钮对比风险 | `glass.css:208` `.btn-primary:disabled{opacity:.5}` | 白字 + 0.5 透明度叠品牌渐变，对比可能 < 4.5:1；改用 `--g2` 底 + `--ink-faint` 字或保留实色降饱和，并用对比工具复核 |
| 3.5 | `App.vue` 语义色硬编码 hex | `App.vue:54-57` `successColor:'#16A34A'` 等 | 值虽与 `tokens.css` 一致，但双源易漂；建议注释「与 §4 令牌同步」或运行时由令牌注入 |
| 3.6 | `!important` 与 `:deep` 过量 | `glass.css` 全篇、`Layout.vue`、`CampusControl.vue` | 维护性 + Windows 高对比模式（forced-colors）风险；下轮审计 HCM 兼容性，逐步收敛 `!important` |
| 3.7 | 缺 `theme-color` / `color-scheme` 元信息 | `index.html:3-7` | 加 `<meta name="theme-color" content="#EEF1FB">` 与 `<meta name="color-scheme" content="light dark">`，移动端浏览器外壳随主题变色 |

---

## 4. 合规亮点（值得保留）

- ✅ `tokens.css` 单一品牌输入 + `color-mix` 派生，主题换肤零改组件（§1、§14）。
- ✅ 暗色模式变量集整体切换（`body.dark`），组件 CSS 不变（§14）。
- ✅ 玻璃原子类强制 `-webkit-backdrop-filter` 前缀 + 不透明兜底（glass.css 注释明确）。
- ✅ `aria-hidden="true"` 用于装饰性极光层（`Layout.vue:3-5`、`SettingsLayout.vue:41`、`CampusControl.vue:4`）。
- ✅ 侧栏 footer `role="button" tabindex="0" @keydown.enter`（`Layout.vue:45-49`）；StatCard `role`/`tabindex`/`@keydown.enter`（`StatCard.vue:8-11`）。
- ✅ `lang="zh-CN"` 已设（`index.html:2`）；面包屑组件已挂载（`Layout.vue:154`）。
- ✅ 路由切换乐观高亮 + 菜单 `transition:none` 消除闪烁（`Layout.vue:584-595`）——细节打磨到位。

---

## 5. 问题汇总

- 🔴 关键：**2**
- 🟡 重要：**6**
- 🔵 建议：**7**
- **主要改进方向**：① 补齐并锁定令牌家族（先解决 `--g1…--g7` 致命缺陷）；② 全链路可访问性（对比度、地标、焦点、动效降级）；③ 响应式一致性（宽表滚动、KPI 栅格、断点）；④ 去硬编码、收敛品牌色与 `!important`。

> 下一页见《ATS-NEW 统一设计规范》与《技术实施方案》。
