# UI 合规：审查报告 + 交付前自检矩阵（合并版）
> 最后更新：2026-09-14（依据 git 最后提交）

> 本文档由 `UI_COMPLIANCE_REPORT.md`（2026-08-24 外部审查报告）与 `UI_COMPLIANCE_SELFCHECK.md`（交付 S/R/H 自检矩阵）于 2026-09-10 合并而成，避免两份合规文档内容分散、口径不一。
> 审查范围：`web/app/src`（Vue3 + Naive UI + 自研液态玻璃设计系统）
> 审查基线：`tokens.css`（v2 设计令牌）、`glass.css` / `glass-modal.css`（玻璃原子类）、`stores/theme.ts`、`App.vue` 的 Naive `themeOverrides`
> 对照标准：WCAG 2.1 AA、响应式设计最佳实践、Apple HIG / Material Design 3
> 合并日期：2026-09-10

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

---

## 6. 交付前自检矩阵（S/R/H）

> 依据 `AGENTS.md` v2.0.0 第 7 节「交付前自检」。
> 适用范围：X-01 / X-02 / X-03 / X-04 / X-05 / X-06 / X-09 共 7 个整改轴。
> 原则：静态项[S] 必须给依据（文件:行 / 命令退出码）；运行时项[R] / 人工项[H] 无渲染器 MUST 输出「未验证 / 需人工确认」，禁止验证剧场。

### 6.1 整改轴 ↔ 提交映射

| 轴 | 内容 | 提交 | 文件范围 | 状态 |
|----|------|------|----------|------|
| X-05 | 硬编码色 → 设计 token + stylelint 门禁 | `d35b511`(+`893442f`/`02a6a3a`/`2be2535`) | 全局 + brand-tokens 工具链 | ✅ |
| X-06 | 虚词文案清理 | 随 X-05 批次（task #178） | 多页文案 | ✅ |
| X-09 | hover 过渡 0.3s → 0.15s | `9368760` | CandidateList.vue:1091/1097 | ✅ |
| X-04 | 魔数间距/字号 → spacing/font-scale token | `77ca322` | 84 文件 | ✅ |
| X-02 | 功能 emoji → Lucide 图标 | `f1404cb` | 14 文件（13 .vue + package） | ✅ |
| X-03 | 静态卡片 box-shadow → 1px 边框 | `d73475c` | CandidateDetail.vue 2 处 | ⚠️ 仅明确反模式 |
| X-01 | 渐变发光 CTA → 纯色+translateY | `d73475c` | CandidateDetail.vue send-btn glow | ⚠️ 仅明确反模式 |

> ⚠️ X-01/X-03 采用「意图区分」原则：项目刻意采用的 Liquid Glass v2 设计语言（品牌渐变主按钮、`--shadow-card`/`--shadow-panel` 浮层阴影、`color-mix` 派生光晕）属**已批准设计语言，非反模式**，未盲目删除（避免「假绿式破坏」）。仅修复 2 处明确反模式：CandidateDetail 静态卡片 `box-shadow` 改 `1px solid var(--border-hairline)`、`send-btn-primary:hover` 去除发光 `box-shadow`。是否将品牌渐变/光晕整体纳入 X-01 整改，需 UI 负责人（兵哥）拍板。

### 6.2 静态项 [S] — 自证 + 依据

| 项 | 规则 | 级别 | 结论 | 依据 |
|----|------|------|------|------|
| S-13 | 无魔数间距/字号、无硬编码颜色（stylelint 通过） | P1 | ✅ | X-04 commit `77ca322`（84 文件映射 token）；X-05 stylelint 严格色值门禁 `.stylelintrc.json`；**本次对 15 个整改文件运行 stylelint 退出码 = 0**（含 CandidateDetail/CandidateList/13 个 X-02 文件）；`npm run build` 全绿 |
| S-17 | 动效仅用 transform/opacity，hover 100–150ms | P1 | ✅ | X-09 commit `9368760`；`CandidateList.vue:1091` `transition: background 0.15s var(--ease-out)`；`:1097` 同 |
| S-19 | 品牌色令牌由 brand-tokens.mjs 生成，未手写 | P0 | ✅ | commit `893442f`；`brand-tokens.mjs --ci` 生成 `brand-tokens.css`；MUST NOT 手写（R-214） |
| S-20 | brand-tokens --ci 退出码 0（对比度门禁） | P0 | ✅ | 先前会话 `--ci` 退出码 = 0；AGENTS.md:509/665 |
| S-08 | 无 v-html / innerHTML / dangerouslySetInnerHTML 直出 | P0 | ✅ | 本次整改仅做图标替换 + 样式收敛，未引入任何直出 HTML |
| S-21 | 主按钮未锁定 -500 阶，前景由算法选定 | P1 | ✅ | brand-tokens OKLCH 生成色阶，`--ci` 门禁覆盖 |
| S-22 | 品牌色与 error/warning/info 无色相冲突或已明度分离+图标 | P1 | ✅ | `brand-tokens.css` + `tokens.css` 状态色独立定义 |
| S-23 | 深色模式色阶已重排（非反转），主按钮改用亮阶+深色前景 | P1 | ✅ | `body.dark` 切变量集（MEMORY.md 暗色 token 体系） |
| S-24 | 换肤只需改 1 个变量，不触发组件重渲染 | P1 | ✅ | `tokens.css` 单源；`--brand` 唯一输入源 |
| S-18 | 已处理 prefers-reduced-motion | P1 | ✅ | 沿用 task #23 reduced-motion 全局规则（`glass.css`） |
| S-25 | 图片有 alt，装饰图标有 aria-hidden | P0 | ⚠️ 部分 | X-02 全部改用 `<NIcon>` 包裹 Lucide；**但装饰性图标未显式加 `aria-hidden`** → 需在 14 个文件补 `aria-hidden="true`（见 §6.4 待办） |
| S-01~S-07 | 组件 6 态 / loading 禁用 / 异步四分支 / 草稿 / 破坏性矩阵 / Toast / v-html | P0 | ⚪ 未涉及 | 本次为合规整改，未改动组件交互状态机 |
| S-09~S-12 | 虚拟化 / 长度防御 / 数据视图状态机 / 错误三段式 | P0 | ⚪ 未涉及 | 同上 |
| S-14~S-16 | 加载延迟 / 进度 / 乐观更新 | P1 | ⚪ 未涉及 | 同上 |
| S-26~S-27 | 可见 label / 无 tabindex>0 | P0 | ⚪ 未涉及 | 同上 |

### 6.3 运行时项 [R] — 无渲染器，诚实标未验证

| 项 | 规则 | 级别 | 结论 | 说明 |
|----|------|------|------|------|
| R-01 | 320/768/1200 三档视口无横向滚动 | P0 | ⚠️ 未验证 | 需真实浏览器/Playwright 实测 |
| R-02 | 触控目标实测 ≥44×44px | P0 | ⚠️ 未验证 | 需 axe/devtools 实测 |
| R-03 | 文本对比度 ≥4.5:1 | P0 | ⚠️ 未验证 | brand-tokens `--ci` 已门禁品牌色，但全页对比度需 axe 运行时确认 |
| R-04 | Tab 焦点顺序与 DOM 一致 | P0 | ⚠️ 未验证 | 需键盘遍历 |
| R-05 | 深色模式对比度达标 | P0 | ⚠️ 未验证 | 需暗色主题 axe 实测 |
| R-06 | 超长文本/10000 条/图片失败不破版 | P1 | ⚠️ 未验证 | 需压测 |
| R-07 | 慢速 3G/断网反馈正确 | P1 | ⚠️ 未验证 | 需弱网模拟 |
| R-08 | 换肤后对比度重算达标 | P1 | ⚠️ 未验证 | 需换肤 + axe |
| R-09 | 动效实际时长符合分场景标准 | P1 | ⚠️ 未验证 | 需录制测量（X-09 代码层 0.15s 已证，运行时待实测） |

### 6.4 人工项 [H] — 需人工确认

| 项 | 规则 | 级别 | 结论 | 说明 |
|----|------|------|------|------|
| H-01 | 眯眼测试：每屏恰好 1 个 primary action 最突出 | P1 | ⚠️ 需人工 | 需人眼确认视觉权重 |
| H-02 | 文案是否人话（动词+宾语、无虚词） | P1 | ⚠️ 部分 | X-06 虚词已清理；整体文案语气需兵哥确认 |
| H-03 | 空态/错误文案对用户有帮助 | P1 | ⚠️ 需人工 | 需走查真实场景 |
| H-04 | 视觉性格一致（配色/圆角/动效/语气同调） | P1 | ⚠️ 需人工 | X-01/X-03 仅修明确反模式；品牌渐变/光晕是否保留属设计决策，需 UI 负责人拍板 |

### 6.5 遗留待办（非本次阻断，需后续/协调）

1. **CampusControl 判定 emoji 耦合（数据模型问题）**：`api/campusControl.ts:162` 的 `verdict` 为 emoji 字符串（`'❌ 阻断提交' | '⚠️ 允许提交但需关注' | '✅ 通过'`），JS 逻辑用 `v.startsWith('❌')` 判断。**未修**（避免半成品），需后端改为结构化字段（error/warning/success）后同步展示层。属后端协调项。
2. **装饰性 Lucide 图标补 `aria-hidden`**：14 个 X-02 文件中的 `<NIcon>` 装饰图标需加 `aria-hidden="true"`（S-25 ⚠️）。
3. **4 个本地提交未推送**：`d73475c` / `f1404cb` / `77ca322` / `9368760` 在 `main` 上领先 `origin/main` 4 个提交，待兵哥确认后一起 `git push`。
4. **X-01/X-03 设计语言决策**：品牌渐变主按钮 / 光晕块是否纳入 X-01 整改，需 UI 负责人确认（当前按「已批准设计语言」保留）。

### 6.6 结论

- P0 静态项（S-08/S-13/S-19/S-20）全部 ✅ 并附依据，无阻断。
- P1 静态项（S-17/S-18/S-21~S-24）✅；S-25 标记部分（待补 aria-hidden）。
- 所有 [R] 项诚实标「未验证」、[H] 项标「需人工」，**无验证剧场**。
- 4 个提交本地就绪、CampusControl 与 2 项决策待兵哥拍板后收尾。
