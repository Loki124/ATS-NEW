# 前端布局标准规范（Frontend Layout Standard）

> 单一事实来源：`src/styles/tokens.css`（§8.5 布局令牌）+ `src/styles/glass.css`（布局契约）。
> 本文件是所有新页面开发必须遵守的统一标准，禁止页面级 scoped 样式私自覆盖布局边距。
> 适用范围：ATS-NEW 全部前端页面（设置中心 / 招聘主流程 / 校招管控 / 工作台 / 弹窗 / 抽屉）。

---

## 0. 问题背景（为什么需要这份规范）

2026-09-14 诊断发现：**所有新页面均出现内容贴边（缺少安全边距与间距）**。

根因不是某个页面写错，而是**设计系统缺少「页面安全边距」的单一强制契约**。页面安全边距由三处互不关联的来源分散提供，且任意页面 scoped 样式都能用更高特异性（`[data-v-x]`）覆盖全局规则：

| 来源 | 提供的值 | 问题 |
| --- | --- | --- |
| 全局 `.page-container`（glass.css） | `padding: 24px` | scoped `.page-container{padding:0}` 可直接覆盖 |
| `.settings-scroll`（SettingsLayout） | `padding: 20px` + 清零 `.page-container` | `.page-body` 仅垂直滚动、无水平 padding；离开该上下文即贴边 |
| 弹窗 `.n-modal .n-card-content`（glass.css） | 隐式依赖 Naive 默认 card padding | header/footer 全局规则只设垂直 padding，水平方向无 token 约束 |

**结论**：新页面作者只要漏接 / 错接其中一处（最常见是把 `.page-container` 写 `padding:0` 却未包进 `.settings-scroll`），内容就贴边。弹窗则因内边距完全隐式，表单/列表贴边。

**本规范把上述三处收归为 token 化、可强制的契约**，并提供工具类与禁止项。

---

## 1. 核心约束

### 1.1 页面安全边距（Page Safe Margin）

| 令牌 | 值 | 说明 |
| --- | --- | --- |
| `--page-pad-x` | `var(--space-6)` = 24px | 桌面（≥768px）页面水平安全边距 |
| `--page-pad-y` | `var(--space-6)` = 24px | 桌面页面垂直安全边距 |
| `--page-pad-x-sm` | `var(--space-4)` = 16px | 移动端（≤767px）水平安全边距 |
| `--page-pad-y-sm` | `var(--space-4)` = 16px | 移动端垂直安全边距 |

**规则**：
- 直接挂在 Layout 下的页面，根容器使用 `.page-container`，由全局规则统一注入 `padding: var(--page-pad-y) var(--page-pad-x) !important`（防御性 `!important`，禁止 scoped 覆盖）。
- 设置中心页面：安全边距由 `.settings-scroll` 的 `padding:20px` 提供，`.page-container` 被 `:deep` 清零——**这是唯一允许的清零场景**，且由布局层（非页面）控制，页面不得自行清零。
- 移动端（≤767px）安全边距**自动降到 16px**：全局 `.page-container` 已用 `@media (max-width: 767px)` 统一收束，页面无需再写；页面 scoped 不得用 `:deep` 等绕过该值（不得低于 16px）。

### 1.2 容器内边距（Container / Card Padding）

- 玻璃卡片 `.glass-card` 已内置 `padding: var(--space-4)`（16px），直接复用，禁止再手写卡片内边距。
- 表单/列表放进 `n-card` 时，由 `n-card` 内容区承载内边距，**不要再给内部第一层子元素加贴边负 margin**。
- 自定义内容块如需内边距，使用 `--space-4`（16px）/ `--space-6`（24px），禁止裸像素（如 `padding:20px` 应写为 `padding: var(--space-5)`）。

### 1.3 弹窗内边距（Modal / Drawer Inner Padding）⚠️ 重点

弹窗内容区、头部、底部的内边距**已全局 token 化**，禁止任何页面 scoped 清零：

| 区域 | 规则 | 值 |
| --- | --- | --- |
| `.n-modal .n-card-content` | `padding: var(--modal-pad-y) var(--modal-pad-x)` | 20px / 24px |
| `.n-modal .n-card-header` | `padding: var(--modal-pad-y) var(--modal-pad-x) 14px` | 顶 20 / 左右 24 / 底 14（与分隔线留缝） |
| `.n-modal .n-card__footer` | `padding: 14px var(--modal-pad-x) var(--modal-pad-y)` | 顶 14 / 左右 24 / 底 20（"不要贴底"） |

> 令牌：`--modal-pad-x = var(--space-6)`（24px）、`--modal-pad-y = var(--space-5)`（20px）。
> 抽屉（n-drawer）底部操作栏统一用 `.drawer-footer`（已全局 `padding-bottom: var(--space-4)` + 右对齐）。

### 1.4 容器最大宽度（Content Max Width）

- 超宽屏（>1280px）下，长表单 / 单列内容应居中收束，避免被拉伸过宽。
- 工具类 `.content-shell`：`max-width: var(--content-max-width)`（1280px）+ `margin-inline:auto`。
- 页面根容器或主内容外层加 `.content-shell` 即可生效；表格类满宽页面（如院校库 16 列宽表）**不**加，保持满宽。

### 1.5 栅格系统（Grid）

- **禁止**手写固定列数 + 媒体查询（如 `grid-template-columns: repeat(4, 1fr)` + `@media 1024/480`）。
- **统一**用自适应栅格工具类 `.grid-auto`：`repeat(auto-fit, minmax(var(--col-min), 1fr))`，`--col-min = 280px`，间距 `--space-4`。
- KPI 卡片区 `.kpi-row` 已用同款 `auto-fit + minmax(180px,1fr)`，保持一致。
- 复杂二维布局（如表单两列）可用 `display:grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-4)`，窄屏（≤767px）折叠为单列——但列数语义固定（非统计卡），属例外允许。

### 1.6 响应式断点（Breakpoints）

| 令牌 | 值 | 语义 |
| --- | --- | --- |
| `--breakpoint-sm` | 768px | 平板及以下（移动优先改点） |
| `--breakpoint-md` | 1024px | 笔记本 |
| `--breakpoint-lg` | 1280px | 桌面 |

- JS 媒体查询、UnoCSS 断点、CSS 媒体查询**必须**对齐这三档，禁止发明 480/920/1100 等散断点。
- 间距/边距在 ≤767px 下从 24px 收敛到 16px（见 1.1）。

### 1.7 间距阶梯（Spacing Scale）

全部走 `--space-*`：1=4 / 2=8 / 3=12 / 4=16 / 5=20 / 6=24 / 8=32 / 12=48 / 16=64（px）。
- 区块间距：`--space-6`（24px）；卡片内：`--space-4`（16px）；表单项间距：`--space-3`（12px）；紧密元素：`--space-2`（8px）。
- 禁止裸像素间距（如 `margin-top:20px` → `margin-top: var(--space-5)`）。

---

## 2. 已落地的强制实现（Implementation）

修改文件：`src/styles/tokens.css`、`src/styles/glass.css`。

1. **tokens.css §8.5**：新增 `--page-pad-*` / `--modal-pad-*` / `--content-max-width` / `--col-min` / `--breakpoint-*` 共 13 个布局令牌。
2. **glass.css `.page-container`**：`padding: var(--page-pad-y) var(--page-pad-x) !important`——防御性 `!important` 兜底页面 scoped 覆盖。设置页由 `.settings-scroll :deep(.page-container){padding:0!important}`（更高特异性）仍可取零。
3. **glass.css 弹窗三区**：header/content/footer 内边距显式 token 化（不再隐式依赖 Naive 默认）。
4. **glass.css 工具类**：`.content-shell`（最大宽度收束）、`.grid-auto`（自适应栅格）。

---

## 3. 禁止项（Anti-Patterns）

| 反模式 | 后果 | 正确做法 |
| --- | --- | --- |
| 页面 scoped 写 `.page-container{padding:0}` | 内容贴边（scoped 覆盖全局） | 不碰 `.page-container` 边距；满宽需求用内部子元素 |
| 弹窗 scoped 清零 `.n-card-content` / `.n-card__footer` padding | 弹窗表单/按钮贴边 | 交给全局 token，不写 |
| 卡片内手写像素 padding（如 `padding:20px`） | 与 token 漂移、暗色不同步 | 用 `.glass-card` 或 `var(--space-5)` |
| 固定 4 列 + `@media 1024/480` 栅格 | 窄屏挤压、断点散乱 | 用 `.grid-auto`（`auto-fit + minmax`） |
| 发明 920/1100 等非标断点 | 媒体查询不统一 | 只用 `--breakpoint-sm/md/lg` |
| 长表单在 >1280px 屏满宽拉伸 | 可读性差 | 根容器加 `.content-shell` |

---

## 4. 校验门禁（Gate）

- **stylelint**：禁止裸像素 color（已有）；布局改动后必须 `npm run lint:style` 通过。
- **构建**：`npm run build:nocheck` 通过（vue-tsc 由 vite build 替代，避免 OOM）。
- **磁盘核查**：改动后 `grep -rn "padding: 0" src/pages/**/*.vue` 确认无 `.page-container` 裸清零（设置页除外，但须确认在 `.settings-scroll` 上下文内）。
- **真实浏览器复测**：弹窗/页面边距须用 `getComputedStyle` 硬证据确认（`.page-container` 解析 padding = 24px；`.n-modal .n-card-content` = 20px 24px），不靠目测。

---

## 5. 迁移清单（后续逐页收口）

- [ ] 全量 `grep ".page-container { padding: 0 }"` 的页面：确认均在 `.settings-scroll` 上下文；非设置页改为复用全局 `.page-container`（删掉 scoped 清零）。
- [ ] 长表单页面（新增院校、流程配置、规则编辑等弹窗）加 `.content-shell` 收束。
- [ ] 统计卡以外的固定列栅格改为 `.grid-auto`。
- [ ] **设置页把 `.glass-panel` 套在 `.page-body` 上时**（如 ThemeSettings），玻璃面板自身只管外观（背景/模糊/圆角/边框）**无内部 padding**，必须在该页 scoped `.page-body` 显式声明内边距（如 `padding: var(--space-5) var(--space-6)`），否则区块贴面板内边缘（违反 §1.2）。裸 `<div class="page-body">` 的设置页由 `.settings-scroll` 的 20px 外层 padding 兜底，无需额外声明。
- [ ] 暗色模式抽查：边距 token 随 `body.dark` 自动联动，无硬编码色。
