# ATS-NEW 前端 UI 设计规范（统一正文 · L2/L3 合并版）
> 最后更新：2026-10-19（合并 `UI_DESIGN_SPEC` + `frontend-layout-standard` + `MODAL_DIVIDER_CONVENTION` + `USE_TABLE_PAGINATION` + 两份功能页专项为单一正文）

> 本文是 ATS-NEW 前端**设计规范统一正文（L2/L3 合并）**，与 `tokens.css` / `glass.css` / `glass-modal.css` 一一对应。任何新增 / 修改 UI 必须以本规范 + 令牌为准，**禁止硬编码颜色、模糊值、圆角、阴影、字号**。
> 📖 **权威层级与统一入口见 `docs/04-ui/README.md`（L0–L5）**：L0 `tokens.css` 是数值唯一真源、L1 `AGENTS.md` 管行为约束、L5 README 是唯一索引。本文为 L2/L3 层级，冲突时按 L0 裁决。
> 相关专项（独立主题，本文不展开）：下拉弹窗 `DROPDOWN_POPOVER_SPEC.md`、naive-ui 踩坑 `NAIVE_UI_PITFALLS.md`、设置页结构 `SETTINGS_PAGE_STRUCTURE.md`、规则索引 `FRONTEND_RULES_CONSOLIDATED.md`。

---

## 1. 设计原则（Principles）

1. **单一事实来源（Single Source of Truth）**：所有颜色 / 间距 / 圆角 / 阴影 / 动效时长均为 CSS 变量，定义在 `tokens.css`。改品牌色只改 `--brand` 一处。
2. **暗色靠变量集切换，不写硬色**：组件 CSS 不出现 `dark` 分支；切 `body.dark` 即整体换肤。
3. **玻璃优先（Glass-first）**：面板 / 卡片 / 弹窗 / 侧栏默认半透明玻璃 + `backdrop-filter`，必须带 `-webkit-` 前缀与**不透明兜底**。
4. **可访问性基线 = WCAG 2.1 AA**：普通文字对比 ≥ 4.5:1，大字 ≥ 3:1，焦点可见，动效可降级。
5. **响应式断点统一**：`sm 480 / md 768 / lg 1024 / xl 1280`；移动端（≤768）侧栏转 Drawer。
6. **语义色只表状态，不表品牌**：success/warning/error/info 与品牌色解耦。

---

## 2. 色彩系统（Color）

### 2.1 品牌色（Brand · 单一输入）
| Token | 值（浅） | 派生方式 | 用途 |
|-------|----------|----------|------|
| `--brand` | `#6366F1` | **唯一手填** | 按钮 / 激活态 / 链接 / 玻璃辉光 / 极光主光斑 |
| `--brand-hover` | — | `color-mix(--brand 80% #fff)` | hover |
| `--brand-pressed` | — | `color-mix(--brand 82% #000)` | pressed |
| `--brand-dark` | — | `color-mix(--brand 66% #000)` | 暗色环境 |
| `--brand-soft` | — | `color-mix(--brand 12% transparent)` | 浅底激活 / hover 行 |
| `--brand-tint` | — | `color-mix(--brand 6% transparent)` | 极浅 hover 行 |
| `--brand-grad-a` | `#A855F7` | 手填（渐变中段） | 标题 / 按钮渐变 |
| `--brand-grad-b` | `#EC4899` | 手填（渐变末段 · 仅装饰） | 标题渐变末段 |

> 腾讯蓝备选：`--brand:#0052D9`。**任何「品牌紫」必须是 `--brand` / `--brand-grad-a` 之一，禁止第 3 个硬编码紫（如曾出现的 `#8B5CF6`）。**

> 🔴 **派生色一律由 `brand-tokens.mjs` 经 OKLCH 自动生成，禁止在 `:root` 手写 `-600`/`-300` 等派生阶或覆盖 `brand-tokens.css` 产物** —— 会绕开 `--ci` 门禁，导致换肤后对比度静默不达标。HSL 的 L 通道非感知均匀，同 L 值下黄与蓝视觉亮度差近一倍，换品牌色后色阶节奏会失衡，故必须用 `oklch`。

#### 品牌文字色（作前景用，与实底色严格分离）

| 角色 | CSS 变量 | 浅色 | 暗色 | 用途 |
|---|---|---|---|---|
| Brand Fg | `--brand-fg` | `--brand-600` `#5050D1` | `--brand-200` `#B9C7FF` | 强调文字 / 图标 / 链接（压普通表面） |
| Brand Fg Hover | `--brand-fg-hover` | `--brand-pressed` | `--brand-100` `#D0DFFF` | 品牌文字 hover 阶，保证 hover 后对比度不下降 |
| Brand Fg On Soft | `--brand-fg-on-soft` | `--brand-fg` | `--brand-100` | 品牌字压品牌半透底（`--brand-soft` / 玻璃面板合成后） |
| Brand Alt Ink | `--brand-alt-ink` | `#5B32C8` | `#C4A6FF` | 派生型 / 次级强调，`--brand-grad-a` 的文字化替身 |
| Warm Ink | `--brand-warm-ink` | `#7C2D12` | `#7C2D12` | 文字压在 `--brand-warm` 实底上 |
| Warm Deep | `--brand-warm-deep` | `#B45309` | `#FCD34D` | 文字压在 `--brand-warm-soft` 半透底上 |
| On Brand | `--on-brand` | `#FFFFFF` | `#111827` | 压在 `--brand-button` 实底上的前景 |

**可自定义机制（白标 / 换肤）**
- 品牌色是**唯一外部输入**：改一处即全站换肤（按钮渐变、激活态、链接、玻璃辉光、极光主光斑联动）。
- `--brand-50…--brand-900` 九阶、`--brand-button`、`--brand-fg`、`--brand-hover/pressed/dark` 全部由 `brand-tokens.mjs` 经 **OKLCH 自动生成**，无需手维护。
- 渐变端 `--brand-grad-a/--brand-grad-b` 提供默认类比色；白标场景可整体覆盖为品牌近似色。
- Naive UI `themeOverrides`（`App.vue`）由**同一品牌值**在 JS 计算 primaryColor/hover/pressed，保证原生组件与玻璃类一致。
- 腾讯 CI 备选：`BRAND_COLOR="#0052D9"`（仅改一处，组件 CSS 不动）。

```bash
# 🚫 不要在 :root 手写派生色 —— 会覆盖 brand-tokens.css 的生成产物，
#    且绕开 --ci 门禁，导致换肤后对比度静默不达标。
# ✅ 只改品牌色这一个输入：
BRAND_COLOR="#0052D9" npm run tokens
```

### 2.2 墨色 / 中性文字（Ink · 必须满足对比度）
| Token | 浅色值 | 暗色值 | 对比（浅 / 白底） | 用途 |
|-------|--------|--------|-----------------|------|
| `--ink` | `#0F172A` | `#E8ECF6` | 15:1 / — | 标题、重要正文 |
| `--ink-soft` | `#475569` | `#AEB8CC` | 7.0:1 / — | 次要正文、标签 |
| `--ink-faint` | **`#5B6B84`**（再修订） | `#94A3B8` | **5.41:1** / 高 | 辅助 / 占位（`#94A3B8` 仅 2.6:1；`#64748B` 压 `--g1` 仅 4.34:1，均已弃用） |
| `--surface` | `#FFFFFF` | `#1E293B` | — | 不透明兜底 |

### 2.3 中性灰阶梯（Neutral Ramp）
onboarding 流程曾引用 `--g1…--g7` 但全仓未定义，导致边框 / 底色 / 文字静默失效。现正式纳入令牌：

| Token | 浅色值 | 暗色值 | 语义 | 原误用位置 |
|-------|--------|--------|------|-----------|
| `--g1` | `#F1F5F9` | `#0B1220` | 最浅填充（disabled 输入框底、弱 hover 底） | Step1Single:89、Step2Assign:278 |
| `--g2` | `#E2E8F0` | `#1E293B` | hover 填充 | Step2Assign:128、Step1Batch:192 |
| `--g3` | `var(--border-hairline)` | `var(--border-hairline)` | 发丝边框 | 全 onboarding `1px solid var(--g3)` |
| `--g4` | `rgba(15,23,42,.16)` | `rgba(255,255,255,.16)` | 较强边框 / 虚线框 | UploadZone:45、Step1Batch:123 |
| `--g5` | **`#5B6B84`** | `#94A3B8` | 辅助文字（**必须 ≥4.5:1**，与 `--ink-faint` 同值） | AddCandidateModal:99、Step1Single:108 |
| `--g6` | `#CBD5E1` | `#334155` | 中间填充（备用） | — |
| `--g7` | `var(--ink-soft)` | `var(--ink-soft)` | 按钮 / 标签文字色 | Step2Assign:321 `.bs color` |

> 落地方式：`tokens.css` 的 `:root` 与 `body.dark` 各补一段。**迁移策略 = 先补令牌（零逐页改动），下个迭代再将 `--g*` 逐步替换为语义更明确的 `--border-hairline` / `--brand-soft` 等。**

### 2.4 语义色（Semantic · 仅状态）
| Token | 值 | 浅底 soft | 暗底 soft |
|-------|----|-----------|-----------|
| `--c-success` | `#16A34A` | `.12` | `.22` |
| `--c-warning` | `#F59E0B` | `.14` | `.24` |
| `--c-error` | `#C62828` | `.12` | `.22` |
| `--c-info` | `#3B82F6` | `.12` | `.22` |

每族三个色阶：**主色**（装饰 / 图标 / 图形）→ **`-deep`**（**文字专用**，两模式各自重排）→ **`-soft`**（浅底）。

| 角色 | 主色 | Deep（文字） | 浅色 Deep | 暗色 Deep | 浅底 |
|---|---|---|---|---|---|
| Success | `#16A34A` | `--c-success-deep` | `#065F46` | `#6EE7B7` | `rgba(22,163,74,.12)` |
| Warning | `#F59E0B` | `--c-warning-deep` | `#92400E` | `#FCD34D` | `rgba(245,158,11,.14)` |
| Error | `#C62828` | `--c-error-deep` | `#991B1B` | `#FCA5A5` | `rgba(239,68,68,.12)` |
| Info | `#3B82F6` | `--c-info-deep` | `#1E40AF` | `#93C5FD` | `rgba(59,130,246,.12)` |

**实底之上的前景色**（`--c-*-deep` 作背景时配对使用，如圆点、实底 chip）：

| CSS 变量 | 浅色 | 暗色 | 实底 → 前景对比度 |
|---|---|---|---|
| `--on-c-success-deep` | `#FFFFFF` | `#0F172A` | 7.68:1 / 11.71:1 |
| `--on-c-warning-deep` | `#FFFFFF` | `#0F172A` | 7.09:1 / 12.38:1 |
| `--on-c-error-deep` | `#FFFFFF` | `#0F172A` | 8.31:1 / 9.41:1 |
| `--on-c-info-deep` | `#FFFFFF` | `#0F172A` | 8.72:1 / 9.90:1 |

> 暗色下 `-deep` 是**亮色**，`#FFFFFF` 前景只有 1.80–1.90:1 —— 故暗色一律 `#0F172A` 深字。

> 🚫 **`--c-*` 主色不得当文字色，也不得当实底色。** 主色压自家 `-soft` 底仅约 2.9:1；主色配白字 2.15–4.47:1。文字一律用 `-deep`，实底一律用 `-deep` + `--on-c-*-deep`。

#### 前景色选阶与文字色禁忌（强制）

品牌色与语义色的**主色是为实底 / 装饰设计的，直接当文字用会静默不达标**。

- **前景色策略必须先于阶位决定**。否则亮品牌（黄 / 浅绿）被压成褐色、暗品牌被提亮成反常识配色。
- 明度 `baseL > 0.75` 判为亮色品牌 → 固定**深色字**；常规品牌 → 固定**对比色**（浅色模式白字）。由 `brand-tokens.mjs` 自动完成，`--ci` 门禁失败即退出码非 0。
- 品牌色与语义色色相接近时（如品牌橙 vs error 红）语义系统失效。**消解策略是拉开明度（OKLCH ΔL ≥ 0.20），禁止旋转语义色色相。**

| # | 禁忌 | 为什么 | 改用 |
|---|---|---|---|
| 1 | 禁止 `--brand` / `--brand-500` 直接当实底 | `#3B82F6` 配白字仅 3.68:1 | `--brand-button` + `--on-brand` |
| 2 | 禁止 `--brand-hover` 当文字色 | 两模式都向白偏，浅色实测 3.58:1 | `--brand-fg-hover` |
| 3 | 禁止 `--c-*` 主色当文字色 | 压自家 `-soft` 底约 2.9:1 | `--c-*-deep` |
| 4 | 禁止 `--brand-grad-a` 当文字色 | `#8C63FA` 仅 3.98:1 | `--brand-alt-ink` |
| 5 | 禁止文字压 `--brand-warm` 实底时用 `--brand-warm-deep` | 暗色下两者同为 `#FCD34D` → 1.00:1 | `--brand-warm-ink` |

> ⚠️ 暗色模式下 `-deep` 阶是**亮色**，前景不能再用白色（仅 1.75:1）。改色后必须做全站视觉回归，不得只看单个页面。

### 2.5 玻璃表面（Glass Surfaces）
| Token | 浅 | 暗 |
|-------|----|----|
| `--glass-bg-panel` | `rgba(255,255,255,.55)` | `rgba(30,41,59,.55)` |
| `--glass-bg-card` | `.62` | `.62` |
| `--glass-bg-elevated` | `.72` | `.72`（modal/drawer） |
| `--glass-bg-input` | `.45` | `.45` |
| `--glass-border` | `rgba(255,255,255,.70)` | `rgba(255,255,255,.14)` |
| `--glass-blur-*` | panel 24 / card 16 / input 10 / overlay 6 px | 同 |

### 2.6 极光背景（Aurora）
`--aurora-base` + `--aurora-1/2/3`（靛 / 紫 / 青径向光斑），暗色转深空。由 `.app-aurora` / `.settings-aurora` / `.cc-aurora` 承载，`aria-hidden`。

### 2.7 z-index 比例尺
层级令牌：`--z-sidebar` / `--z-header` / `--z-dropdown` / `--z-drawer` / `--z-modal` / `--z-toast`（数值与顺序见 `tokens.css §7`，此处不复制）。新增浮层时 MUST 取现有档位，禁自造层级数值。

---

## 3. 排版（Typography）

- 字体：正文与 UI 用 `--font-sans`，等宽（代码 / 数字列）用 `--font-mono`。字体族栈与回退顺序见 `tokens.css §9`，此处不复制。
- 字号刻度：七档 `--text-display` / `--text-h1` / `--text-h2` / `--text-h3` / `--text-h4` / `--text-body` / `--text-small` / `--text-meta`（数值见 `tokens.css §7`）。引用前 MUST 读文件确认，禁凭记忆写 px。
- 行高：标题 1.2–1.4，正文 1.6。
- **数字对齐**：统计值用 `font-variant-numeric: tabular-nums`（参考 `StatCard.vue:124`）。
- 页面主标题统一类 `.page-title`（26px / 700 / 渐变），**全站唯一规格**（删除 `ThemeSettings` 32px 覆盖）。

---

## 4. 间距 / 圆角 / 阴影 / 动效

- **间距（4pt）**：`--space-1 4 / 2 8 / 3 8 / 4 16 / 6 24 / 8 32 / 12 48 / 16 64`。
- **圆角**：`--radius-sm 6 / md 16 / lg 20 / pill 9999`。（主圆角 16 与 Naive `borderRadius:16px` 对齐）
- **阴影**：`--shadow-xs/sm/card/panel/elevated/2xl` + `--glow-brand`。暗色下整体转纯黑低透。
- **动效**：`--ease-out cubic-bezier(.16,1,.3,1)`；`--duration-fast 160 / base 240 / slow 320 ms`。
- **动效降级（新增）**：`@media (prefers-reduced-motion: reduce)` 内将 `animation/transition-duration` 降至近 0（见 §10）。

---

## 5. 布局契约（Layout · L3）

> 单一事实来源：`src/styles/tokens.css`（§8.5 布局令牌）+ `src/styles/glass.css`（布局契约）。
> 本规范是所有新页面开发必须遵守的统一标准，禁止页面级 scoped 样式私自覆盖布局边距。
> 适用范围：ATS-NEW 全部前端页面（设置中心 / 招聘主流程 / 校招管控 / 工作台 / 弹窗 / 抽屉）。
> **规范活文档**：`/settings/ui-templates`（设置 → 主题外观 → 前端UI模板）可按分类查看每个范式的渲染效果与代码；「样式文档」页签输出本规范的结构化全文。

### 5.1 问题背景（为什么需要这份契约）

2026-09-14 诊断发现：**所有新页面均出现内容贴边（缺少安全边距与间距）**。

根因不是某个页面写错，而是**设计系统缺少「页面安全边距」的单一强制契约**。页面安全边距由三处互不关联的来源分散提供，且任意页面 scoped 样式都能用更高特异性（`[data-v-x]`）覆盖全局规则：

| 来源 | 提供的值 | 问题 |
| --- | --- | --- |
| 全局 `.page-container`（glass.css） | `padding: var(--page-pad-y) var(--page-pad-x)` | scoped `.page-container{padding:0}` 可直接覆盖（故已加 `!important` 兜底） |
| `.settings-scroll`（SettingsLayout） | `padding: 20px` + 清零 `.page-container` | `.page-body` 仅垂直滚动、无水平 padding；离开该上下文即贴边 |
| 弹窗 `.n-modal .n-card-content`（glass.css） | 隐式依赖 Naive 默认 card padding | header/footer 全局规则只设垂直 padding，水平方向无 token 约束 |

**结论**：新页面作者只要漏接 / 错接其中一处（最常见是把 `.page-container` 写 `padding:0` 却未包进 `.settings-scroll`），内容就贴边。弹窗则因内边距完全隐式，表单 / 列表贴边。

**本规范把上述三处收归为 token 化、可强制的契约**，并提供工具类与禁止项。

### 5.2 页面安全边距（Page Safe Margin）

| 令牌 | 值 | 说明 |
| --- | --- | --- |
| `--page-pad-x` | `var(--space-4)` = 16px | 桌面（≥768px）页面水平安全边距 |
| `--page-pad-y` | `var(--space-4)` = 16px | 桌面页面垂直安全边距 |
| `--page-pad-x-sm` | `var(--space-2)` = 8px | 移动端（≤767px）水平安全边距 |
| `--page-pad-y-sm` | `var(--space-2)` = 8px | 移动端垂直安全边距 |

**规则**：
- 直接挂在 Layout 下的页面，根容器使用 `.page-container`，由全局规则统一注入 `padding: var(--page-pad-y) var(--page-pad-x) !important`（防御性 `!important`，禁止 scoped 覆盖）。
- 设置中心页面：安全边距由 `.settings-scroll` 的 `padding:20px` 提供，`.page-container` 被 `:deep` 清零——**这是唯一允许的清零场景**，且由布局层（非页面）控制，页面不得自行清零。
- 移动端（≤767px）安全边距**自动降到 8px**：全局 `.page-container` 已用 `@media (max-width: 767px)` 统一收束，页面无需再写；页面 scoped 不得用 `:deep` 等绕过该值（不得低于 8px）。

### 5.3 容器内边距（Container / Card Padding）

- 玻璃卡片 `.glass-card` 已内置 `padding: var(--space-4)`（16px），直接复用，禁止再手写卡片内边距。
- 表单 / 列表放进 `n-card` 时，由 `n-card` 内容区承载内边距，**不要再给内部第一层子元素加贴边负 margin**。
- 自定义内容块如需内边距，使用 `--space-4`（16px）/ `--space-6`（24px），禁止裸像素（如 `padding:20px` 应写为 `padding: var(--space-5)`）。
- **弹窗内边距一律 16px**（2026-10-19 兵哥定调），走 `--modal-pad-x/y`，禁页面自定义。

### 5.4 弹窗内边距（Modal / Drawer Inner Padding）⚠️ 重点

弹窗内容区、头部、底部的内边距**已全局 token 化**，禁止任何页面 scoped 清零：

| 区域 | 规则 |
| --- | --- |
| `.n-modal .n-card-content` | `padding: var(--modal-pad-y) var(--modal-pad-x)` |
| `.n-modal .n-card-header` | `padding: var(--modal-pad-y) var(--modal-pad-x) var(--space-3)`（底边留分隔线缝） |
| `.n-modal .n-card__footer` | `padding: var(--space-3) var(--modal-pad-x) var(--modal-pad-y)`（"不要贴底"） |

> 令牌：`--modal-pad-x` / `--modal-pad-y` 均 = `var(--space-5)`，**即 16px（2026-10-19 兵哥定调：弹窗内边距统一 16px）**，数值真源见 `tokens.css §8.5`，此处不复制。
> 🔴 历史上本节曾写「24px / 20px」而真源实为 16px，属文档漂移；现改为只引用令牌名，由 `npm run tokens:audit` 防回归。
> 抽屉（n-drawer）底部操作栏统一用 `.drawer-footer`（已全局 `padding-bottom: var(--space-4)` + 右对齐）。

### 5.5 容器最大宽度（Content Max Width）

- 超宽屏（>1280px）下，长表单 / 单列内容应居中收束，避免被拉伸过宽。
- 工具类 `.content-shell`：`max-width: var(--content-max-width)`（1280px）+ `margin-inline:auto`。
- 页面根容器或主内容外层加 `.content-shell` 即可生效；表格类满宽页面（如院校库 16 列宽表）**不**加，保持满宽。

### 5.6 栅格系统（Grid）

- **禁止**手写固定列数 + 媒体查询（如 `grid-template-columns: repeat(4, 1fr)` + `@media 1024/480`）。
- **统一**用自适应栅格工具类 `.grid-auto`：`repeat(auto-fit, minmax(var(--col-min), 1fr))`，`--col-min = 280px`，间距 `--space-4`。
- KPI 卡片区 `.kpi-row` 已用同款 `auto-fit + minmax(180px,1fr)`，保持一致。
- 复杂二维布局（如表单两列）可用 `display:grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-4)`，窄屏（≤767px）折叠为单列——但列数语义固定（非统计卡），属例外允许。

### 5.7 响应式断点（Breakpoints）

| 令牌 | 值 | 语义 |
| --- | --- | --- |
| `--breakpoint-sm` | 768px | 平板及以下（移动优先改点） |
| `--breakpoint-md` | 1024px | 笔记本 |
| `--breakpoint-lg` | 1280px | 桌面 |

- JS 媒体查询、UnoCSS 断点、CSS 媒体查询**必须**对齐这三档，禁止发明 480/920/1100 等散断点。
- 桌面端页面安全边距 16px，移动端（≤767px）进一步收敛到 8px（见 5.2）。

### 5.8 间距阶梯（Spacing Scale）

全部走 `--space-*`：1=4 / 2=8 / 3=8 / 4=16 / 5=16 / 6=24 / 8=32 / 12=48 / 16=64（px）。（注：`--space-3`/`--space-5` 为兼容档位，取值已向下取整到 8 的倍数：3=8、5=16，详见 tokens.css §8。）
- 区块间距：`--space-6`（24px）；卡片内：`--space-4`（16px）；表单项间距：`--space-3`（8px）；紧密元素：`--space-2`（8px）。
- 禁止裸像素间距（如 `margin-top:20px` → `margin-top: var(--space-5)`）。

### 5.9 组件级 UI 规范（按钮 / 卡片 / Tab 间距 / 圆角）

**5.9.1 按钮统一性**（表格操作列 / 工具栏 / 卡片头按钮）
- **同组按钮必须全有 icon 或全无 icon**。禁止「管理权限 / 编辑 / 停用 / 删除」一类 4 按钮中 2 带 icon、2 不带。
- 优先全部带 icon（14–16px outline），用语义化命名（@vicons/ionicons5）：
  - 管理权限 → `ShieldCheckmarkOutline` / `KeyOutline`
  - 编辑 → `CreateOutline` / `PencilOutline`
  - 停用 → `BanOutline` / `StopCircleOutline`；启用 → `PlayOutline` / `CheckmarkOutline`
  - 删除 → `TrashOutline` / `TrashBinOutline`
- size 统一 `small`（quaternary），代码常量 `OP_ACTION_BUTTON_SIZE = 'small'`（`useTableColumns.ts`）为唯一真源，操作列一律引用该常量、禁写字面量。
  - **2026-10-18 修订**：原文写「默认 tiny」，与代码常量 `small` 矛盾，且 tiny(12px) 比表格正文(14px)小一档、视觉矮一截（兵哥纠偏原话：「文字和 icon 太小了，感觉就不是一个层级的」）。以代码为准，规范同步改为 `small`。
  - ⚠️ `glass.css` 仍保留 `.n-button--tiny-type` 的 14px 兜底补丁，属过渡期保险；待全站 tiny 清零后评估废弃。
- 颜色语义：默认 / 主操作 `default` 或 `primary`；停用 / 启用反转为 `primary`（启用态视觉更突出）；删除 `type="error"`。
- 表格操作列 `NSpace` 必须 `wrap:false` + 列宽足够容纳所有按钮（4 个 small 按钮 + icon 推荐 ≥280px）。

**5.9.2 卡片内边距**（自定义分组卡片 / 容器）
- 卡片内 padding **不得低于 16px**（`--space-4`）。
- 信息密集型（多行表单 / 嵌套列表 / 字段分组）用 `--space-5`（20px）更舒展。
- 卡片外间距 `gap`：`--space-4`（紧凑）/`--space-5`（舒展），禁止 8/12px 异常紧贴。

**5.9.3 页面顶部留白**
- 页面级 `page-header` 与下方的 `n-tabs`/`n-data-table`/卡片墙之间**禁止**额外声明 `margin-top`/`padding-top` 制造留白带。
- 间距由全局契约（`.page-container` 24px + 元素自身间距）自动控制。
- 例外：仅在 Tabs 自身无下边距时，Tabs 容器用 `margin-top: var(--space-3)`（12px）做视觉过渡；禁止用 8/16/24px 等非阶梯值。

**5.9.4 圆角**（border-radius）
- 卡片：`var(--radius-md)`（12px，项目统一，不混用 8/10/14）。
- 小元素（tag/徽标/code）：`var(--radius-sm)`（6–8px）即可。
- 弹窗 / 抽屉：跟随 Naive UI 主题默认（勿手写）。
- **禁止**手写 `border-radius: 8px`、`border-radius: 10px` 等硬编码值。

**5.9.5 多选框溢出折叠（`max-tag-count`）**

所有多选 `<n-select multiple>` 在**选项值总宽度超过选择框宽度**时，必须自动折叠为 `+1`、`+2` 样式，禁止标签换行撑破布局或截断不可读。

| 场景 | 规则 |
| --- | --- |
| 宽度自适应折叠 | `max-tag-count="responsive"`（Naive UI 按容器宽度自动计算并显示 `+N`） |
| 固定数量折叠 | 仅在设计稿明确要求固定显示 N 个标签时使用 `max-tag-count="N"`（N 为数字） |
| 不换行 | 禁止手写 `white-space: nowrap` + 省略号冒充折叠；统一走 Naive UI 原生 `+N` |
| 小尺寸多选 | size="small" 与 `max-tag-count="responsive"` 可同时使用 |

**示例**：
```vue
<n-select
  v-model:value="selectedIds"
  :options="options"
  size="small"
  multiple
  filterable
  clearable
  max-tag-count="responsive"
/>
```

**已落地检查点**：RuleConfigModal 的条件值 / 属性条件多选均已配置 `max-tag-count="responsive"`。新增多选框时必须遵守本条；Code Review 把 `multiple` 缺少 `max-tag-count` 视为阻塞项。

### 5.10 页面结构范式（列表页统一乙系）

**兵哥拍板：列表页统一「乙系」（独立设置页列表）为全站唯一标准**，「甲系」（Tab 内嵌列表）降为存量形态。

| 范式 | 结构 | 适用范围 |
| --- | --- | --- |
| 乙系（唯一标准） | `.page-container > .page-header + .page-body > .glass-panel.panel-shell > .toolbar + .table-wrap` | 所有新列表页 |
| 甲系（存量） | 根节点 flex 列 + `.toolbar + .table-wrap`，无页头、无玻璃面板 | 仅存量 4 页（RolesTab / ResourcesTab / reason-library 两页），随迭代收口，新页面禁用 |

规则：
- 乙系页头只放标题 + 副标题，操作控件一律移入面板内 `.toolbar`；页头与内容区间禁加额外 margin 制造留白带。
- `n-data-table` 必须包 `.table-wrap` 并加 `flex-height`，否则面板下方留白、表体不滚动。
- 确有 tab 嵌入场景时，应由父页直接渲染乙系结构，不再新起甲系根节点。
- 各范式骨架、约束与渲染效果以 `/settings/ui-templates`（模板中心）为准，两处必须同步。

### 5.11 列表模板皮肤规范（v2 · 2026-10-18，方案待兵哥确认）

页面骨架（§5.10）之上的**视觉皮肤**七条。当前**仅落地在模板中心**（`ui-templates/templates/ListTemplate.vue` scoped 局部），业务页面仍是全局玻璃外观；兵哥确认后把 `.stpl-*` 样式搬入 `glass.css` 即完成全局推行，结构零改动。

| # | 规范 | 落地写法 |
| --- | --- | --- |
| 1 | 背景一律纯色 | 分区三级：页底 < 内嵌 < 面板；禁渐变、禁 backdrop 模糊 |
| 2 | 无投影 | 按钮与组件 box-shadow 一律清除 |
| 3 | 无边框分区 | 不用边框线分隔区块，只用背景色差异 |
| 4 | 间距 8px 对齐 | 只用 `--space-*`；容器边距成对（上下、左右各自对称） |
| 5 | 按钮四态 | 主 = `--brand` 实色 / 次 = 内嵌底实色 / 幽灵 = 透明 / 危险 = `--c-error` 实色 |
| 6 | 同上边距规则 | padding 成对出现，禁单边值 |
| 7 | 图标文字间距 4px | `--n-icon-margin: var(--space-1)` |

实现要点：按钮基于 **quaternary 基底**（不渲染 `__border`，天然避开 `.settings-scroll` 全局渐变注入规则），皮肤用 `.stpl-btn--*` 类自绘，与全局规则零冲突；令牌全部从现有语义色 `color-mix` 派生，不新增设计令牌、不硬编码 hex。

### 5.12 已落地的强制实现（Implementation）

修改文件：`src/styles/tokens.css`、`src/styles/glass.css`。

1. **tokens.css §8.5**：新增 `--page-pad-*` / `--modal-pad-*` / `--content-max-width` / `--col-min` / `--breakpoint-*` 共 13 个布局令牌。
2. **glass.css `.page-container`**：`padding: var(--page-pad-y) var(--page-pad-x) !important`——防御性 `!important` 兜底页面 scoped 覆盖。设置页由 `.settings-scroll :deep(.page-container){padding:0!important}`（更高特异性）仍可取零。
3. **glass.css 弹窗三区**：header/content/footer 内边距显式 token 化（不再隐式依赖 Naive 默认）。
4. **glass.css 工具类**：`.content-shell`（最大宽度收束）、`.grid-auto`（自适应栅格）。

### 5.13 禁止项（Anti-Patterns）

| 反模式 | 后果 | 正确做法 |
| --- | --- | --- |
| 页面 scoped 写 `.page-container{padding:0}` | 内容贴边（scoped 覆盖全局） | 不碰 `.page-container` 边距；满宽需求用内部子元素 |
| 弹窗 scoped 清零 `.n-card-content` / `.n-card__footer` padding | 弹窗表单 / 按钮贴边 | 交给全局 token，不写 |
| 卡片内手写像素 padding（如 `padding:20px`） | 与 token 漂移、暗色不同步 | 用 `.glass-card` 或 `var(--space-5)` |
| 固定 4 列 + `@media 1024/480` 栅格 | 窄屏挤压、断点散乱 | 用 `.grid-auto`（`auto-fit + minmax`） |
| 发明 920/1100 等非标断点 | 媒体查询不统一 | 只用 `--breakpoint-sm/md/lg` |
| 长表单在 >1280px 屏满宽拉伸 | 可读性差 | 根容器加 `.content-shell` |
| 卡片加 `border-left` 状态色条（如 `border-left: 3px solid var(--c-error)`） | 颜色成唯一状态通道（违反 R-109）、同视图卡片语言分裂 | 状态用「标签 / 徽标 / 图标 + 文字」表达，卡片只留 1px 统一描边（X-20） |

### 5.14 校验门禁（Gate）

- **stylelint**：禁止裸像素 color（已有）；布局改动后必须 `npm run lint:style` 通过。
- **stylelint（X-20，硬门禁）**：`no-left-border/no-left-border` 显式 `severity=error`，命中 `border-left*` 即阻断 CI；非卡片场景须在 `web/app/stylelint-plugin-no-left-border.cjs` 的 `ALLOWLIST` 登记 `{ file, selector, reason }`。
- **构建**：`npm run build:nocheck` 通过（vue-tsc 由 vite build 替代，避免 OOM）。
- **磁盘核查**：改动后 `grep -rn "padding: 0" src/pages/**/*.vue` 确认无 `.page-container` 裸清零（设置页除外，但须确认在 `.settings-scroll` 上下文内）。
- **真实浏览器复测**：弹窗 / 页面边距须用 `getComputedStyle` 硬证据确认（`.page-container` 解析 padding 应等于 `--page-pad-x/y`；`.n-modal .n-card-content` 应等于 `--modal-pad-y` `--modal-pad-x`），不靠目测、不写死数值。

### 5.15 迁移清单（后续逐页收口）

- [ ] 全量 `grep ".page-container { padding: 0 }"` 的页面：确认均在 `.settings-scroll` 上下文；非设置页改为复用全局 `.page-container`（删掉 scoped 清零）。
- [ ] 长表单页面（新增院校、流程配置、规则编辑等弹窗）加 `.content-shell` 收束。
- [ ] 统计卡以外的固定列栅格改为 `.grid-auto`。
- [ ] **设置页把 `.glass-panel` 套在 `.page-body` 上时**（如 ThemeSettings），玻璃面板自身只管外观（背景 / 模糊 / 圆角 / 边框）**无内部 padding**，必须在该页 scoped `.page-body` 显式声明内边距（如 `padding: var(--space-5) var(--space-6)`），否则区块贴面板内边缘（违反 §5.3）。裸 `<div class="page-body">` 的设置页由 `.settings-scroll` 的 20px 外层 padding 兜底，无需额外声明。
- [ ] 暗色模式抽查：边距 token 随 `body.dark` 自动联动，无硬编码色。
- [x] 卡片左侧边框线全量收口（2026-10-21，X-20）：需求列表 / 简历卡 / 评分卡 / 阶段选择项 / 指标详情分区 / 抢单池共 7 处已改为「1px 描边 + 标签/图标/文字」表达状态；门禁 `no-left-border/no-left-border` 已接入 `.stylelintrc.json`（severity=error）。

---

## 6. 弹窗分隔线规范（Modal Divider Convention）

> 适用范围：所有 `preset="card"` 的 `<n-modal>`（含 `<n-drawer>` 同理）。
> 关联代码：`web/app/src/styles/glass.css` 的「弹窗统一」段 + 本规范。

### 6.1 结论（一句话）

**每个弹窗的顶部、底部各处，只能有「一条」分隔线。** 顶部 = header 底边线；底部 = footer 顶边线。

### 6.2 根因（为什么会出现「两条线」）

本项目的 `glass.css` 为所有 `.n-modal` 统一提供：

- `.n-modal .n-card-header { border-bottom: 1px solid var(--border-hairline); }`  ← 顶部第 1 条
- `.n-modal .n-card__footer { border-top: 1px solid var(--border-hairline); }`   ← 底部第 1 条

而 Naive UI 的 `:segmented="{ content: 'soft', footer: 'soft' }"` 会在卡片根元素上加 `n-card--content-soft-segmented` / `n-card--footer-soft-segmented` 修饰类，其 cssr 规则（naive `card/src/styles/index.cssr.mjs`）会**再**给 `.n-card-content:not(:first-child)` 和 `.n-card__footer:not(:first-child)` 各加一条 `border-top`。

结果：

- **顶部**：header 的 `border-bottom` + content 的 `border-top`（content 是 header 之后的非首个子元素，二者为**相邻两个元素**）→ **双线**。这是真实出现的「弹窗顶部分割线两条线」问题，必须修。
- **底部**：footer 的 `border-top` 来自「全局 `.n-modal .n-card__footer`」与「footer-segmented cssr」**两条规则，但指向同一元素的同一 `border-top` 属性** → 最终只渲染为**一条线**，天生不会叠成双线。故底部**不需要**中和；若误对 footer 也设 `border-top:none`，反而会把这唯一的分隔线整条删掉（实测 `footerBorderTop=0px` 即为此误修，已回退）。

### 6.3 修复手段（已落地，勿回退）

在 `glass.css` 中**只**中和 Naive 加在 `content` 上的那一条 `border-top`（顶部双线的来源）：

```css
.n-card.n-modal.n-card--content-segmented        > .n-card-content,
.n-card.n-modal.n-card--content-soft-segmented   > .n-card-content {
  border-top: none;
}
```

- 顶部：中和后只剩 header 的 `border-bottom` 一条线。
- 底部：**保留** `glass.css` 的 `.n-card__footer { border-top }` 作为 footer 唯一分隔线（不动 footer）。
选择器特异性 `(0,4,0)` 高于 Naive `(0,2,0)`，不依赖样式注入顺序。

### 6.4 防回归守则（新增 / 修改弹窗时必读）

1. **不要**再为「分隔线」新增 `border`。`glass.css` 已对 `.n-modal` 全局兜底。
2. 弹窗可以继续用 `:segmented="{ content:'soft', footer:'soft' }"`（其 soft 仅调整 padding/margin，不再贡献额外边框线）——但**不要**为了「加一条线」而引入 segmented，也**不要**手写 border 去叠。
3. 若某弹窗需要「无顶 / 无底分隔线」的特殊版式，在该弹窗作用域内**显式覆盖**（特指名 selector），而不是改全局规则。
4. 验收红线：**真机截图**里每个弹窗顶部 / 底部只能看到一条线；若看到两条，先查：
   - 是否给弹窗加了 `:segmented` 且上面这条中和规则被更高特异性覆盖；
   - 是否在组件 scoped 样式里手动加了 `border-top/bottom` 与全局线重叠。

### 6.5 真机验收方法

用 `ats-new-ui-runtime-verify` 技能取浏览器实测：

```js
const r = await page.evaluate(() => {
  const m = [...document.querySelectorAll('.n-modal')].pop()
  const cs = el => el ? getComputedStyle(el) : null
  const header = m.querySelector('.n-card-header')
  const content = m.querySelector('.n-card-content')
  const footer  = m.querySelector('.n-card__footer')
  return {
    headerBorderBottom: cs(header)?.borderBottomWidth + ' ' + cs(header)?.borderBottomColor,
    contentBorderTop:   cs(content)?.borderTopWidth + ' ' + cs(content)?.borderTopColor,
    footerBorderTop:    cs(footer)?.borderTopWidth + ' ' + cs(footer)?.borderTopColor,
  }
})
// 期望: headerBorderBottom=1px、contentBorderTop=0px、footerBorderTop=1px
```

判读：

| 字段 | 期望 | 异常含义 |
|---|---|---|
| `headerBorderBottom` | `1px` | 顶部分隔线存在 |
| `contentBorderTop` | `0px` | 中和生效，无第二条顶线 |
| `footerBorderTop` | `1px` | 底部分隔线存在且唯一 |

---

## 7. 组件规范（Component Specs）

### 7.1 按钮

#### 按钮类型

| 类型 | 类 / Naive | 用途 | 规范 |
|------|-----------|------|------|
| 主按钮 | `.btn-primary` / `.gradient-btn` / `n-button--primary-type` | 页面最重要操作 | 品牌渐变 + 白字 + 辉光；hover `translateY(-1px)` + 更强辉光；`:disabled` **禁用 `opacity`（改用 `--g2` 底 + `--ink-faint` 字，保对比）** |
| 次按钮 | `.btn-secondary` | 次级操作 | 玻璃底 + 描边；hover 描边变品牌色 |
| 文字按钮 | `.btn-text` | 低强调操作 / 链接化行为 | 透明底；文字用品牌色；hover 用 `--brand-tint` 底或下划线 |
| 幽灵 | `.btn-ghost` | 工具栏、卡片内辅助 | 透明；hover `--brand-tint` 底 |
| 图标按钮 | `.btn-icon` / `n-button` circle | 工具栏、快捷操作 | **视觉 28–32px；命中区 MUST ≥ 44×44px**（用 padding 或伪元素扩展，见 R-102） |
| 危险 | `.btn-danger` | 删除、退出等高风险操作 | `--c-error-soft` 底；hover 实色 `--c-error` + 白字 |
| 设置页主按钮 | `.settings-scroll .n-button--primary-type` | 全局化渐变，零逐页改动 | 同主按钮 |

#### 按钮尺寸

Web 端高度 MUST 按三档使用，禁止无级缩放：

| 尺寸 | 高度 | 场景 |
|------|------|------|
| 小 | 28–32 px | 表格内、工具栏紧凑按钮、图标按钮 |
| 中 | 36–40 px | **默认推荐**，大多数表单 / 弹窗操作 |
| 大 | 44–48 px | 表单提交、主要操作、移动端主按钮 |

移动端常见高度：32px（小）、40px（普通）、44–48px（主要操作）。

按钮左右内边距通常为 **12–24 px**，根据文字长度适当调整；**图标按钮优先用等宽高 + 扩展命中区**，不依赖文字内边距撑开。

#### 按钮状态

每个按钮 MUST 实现完整 7 态：default、hover、active、focus-visible、selected（切换 / 激活态）、loading、disabled。危险按钮 MUST 额外保持 danger 视觉区分。

| 状态 | 说明 |
|------|------|
| 默认 | 静止基础样式 |
| 悬停 | 轻微视觉反馈（颜色加深 / 描边变品牌色 / `translateY(-1px)`） |
| 按下 | 点击瞬间反馈（压缩 / 变暗 / 波纹） |
| 选中 | 切换或激活状态下明确区分，通常用品牌色填充 |
| 加载 | 显示加载状态并禁用重复提交（`loading` + `disabled` 同时置位） |
| 禁用 | 视觉降级但保持可读性，禁用 `opacity` 伪透明 |
| 危险 | 删除 / 清空 / 退出等高风险操作使用错误色，与主按钮形成明显区分 |

#### 按钮使用原则

1. **同一页面主按钮数量不宜过多**：每屏建议只保留 1 个最突出的 primary action。
2. **重要操作层级最清晰**：最重要操作用主按钮，次要用次按钮或文字按钮，形成清晰层级。
3. **按钮文案简短明确，优先使用动词**：中文 2–6 字，使用「保存」「删除」「查看详情」等具体动作；MUST NOT 使用「提交 / 确定 / 是 / 否 / OK」（见 R-204）。
4. **重要操作与危险操作应明显区分**：主按钮用品牌色，危险按钮用错误色，避免误操作。
5. **按钮尺寸统一，点击区域足够**：图标按钮视觉 28–32px，命中区 MUST ≥ 44×44px；主按钮 44–48px。
6. **对齐统一，间距保持一致**：同一页面按钮对齐方式、按钮间距遵循统一规范。
7. **加载与禁用状态清晰可见**：帮助用户理解当前状态，避免重复点击。
8. **表单提交按钮位置应清晰可见**：放在内容区域底部或右下方，移动端保持可见。

### 7.2 卡片 / 面板
- `.glass-panel`（大块容器）、`.glass-card`（统计 / 列表卡）、`.n-card.n-card`（全局玻璃化）。
- KPI：`.kpi-card`——玻璃底 + 无边框 + hover 品牌浅底上浮；**栅格统一 `repeat(auto-fit,minmax(180px,1fr))`**（去 4/5 列分裂）。
- **禁止左侧边框线（X-20）**：卡片一律 `1px` 统一描边（`var(--glass-border)` / `var(--border-hairline)`），状态靠「标签 / 徽标 / 图标 + 文字」表达，不靠 `border-left` 色条。已收口页面见 §5.15。

### 7.3 标签 / 徽标
`.glass-tag` + `--brand/success/warning/error/info` 变体；文字用 `--ink-soft`（非 `--ink-faint`）。

### 7.4 输入框
`.glass-input`——玻璃底 + focus 3px 品牌辉光环（`box-shadow:0 0 0 3px var(--brand-tint)`）；disabled 用 `--g1` 底。

### 7.5 数据表格
- 玻璃表头（`.glass-table` / `.settings-scroll .n-data-table` 已全局化）；hover 行 `--brand-tint`。
- **横向滚动策略**：`md+` 可 `overflow-x:hidden` 配合 `min-width`；`sm-` 必须 `overflow-x:auto`，禁止 `!important` 永久隐藏横向滚动。
- 真实滚动职责归还 `.n-scrollbar-container`（`overflow-y:auto`，绝不可 `overflow:hidden` 吞 wheel 事件——见工程铁律）。

### 7.6 弹窗 / 抽屉
- `.n-modal` / `.n-drawer` 玻璃化（`glass-modal.css`）；遮罩 `.n-modal-mask` 毛玻璃。
- 居中 + `max-height:90vh` + 内部滚动（`.n-card__content` `max-height:calc(90vh-110px)`）。
- **确认类弹窗统一用 `useDialog().warning(...)`（禁用原生 `confirm()`）**。
- 弹窗内边距 / 分隔线见 §5.4 与 §6。

### 7.7 导航 / 页面 Shell
- 侧栏 `.glass-sidebar`：透明 + 极光透出（Layout.vue 已改）；激活项 `--brand-soft` 底 + 3px 品牌 accent bar。
- 页面根：`.page-container` / `.cc-page` / `.settings-scroll`。
- 页头吸顶：`.page-header` `position:sticky; top:0`（设置页已全局化）。
- **语义地标**：内容区包 `<main id="main">`；加 skip-link。

### 7.8 下拉弹窗（Dropdowns / Selects / Popovers）

> 详细规范见 [`DROPDOWN_POPOVER_SPEC.md`](./DROPDOWN_POPOVER_SPEC.md)（独立专项，L4）；本节为指针 + 关键规则摘要。

**适用对象**：`n-dropdown` / `n-select` / `n-cascader` / `n-tree-select` / `n-date-picker` / `n-color-picker` / `n-time-picker` / `n-popover`（click 触发型）。

**三层结构**（必须穿透覆写，**不能只改外层**）：

| 层 | 类名 | 关键规则 |
|----|------|---------|
| 外层容器 | `.n-popover` | 圆角 = `--radius-lg`；背景 = `--glass-bg-elevated` + `blur(--glass-blur-panel)`；边框 = `--glass-border`；阴影 = `--shadow-elevated`；z-index = `--z-dropdown` |
| 内层菜单 | `.n-dropdown-menu` / `.n-base-select-menu` | 圆角同外层（不留独立圆角）；padding = `var(--space-2)` 垂直 |
| 项目行 | `.n-dropdown-option` / `.n-base-select-option` | 高度 36px（中等）；水平 padding = `var(--space-3)`（12px）；hover 高亮 = `var(--brand-tint)` + inset `0 var(--space-1)`（6px）+ `border-radius: var(--radius-sm)` |
| 分割线 | `.n-dropdown-divider` | 颜色 **`var(--border-hairline)`**（覆写 Naive 默认 `--n-divider-color`，避免暗色下仍浅灰）；上下间距 = `var(--space-2)`；水平缩进 = `var(--space-2)` |

**「层叠圆角」原则**：外框圆角 12 / 内部高亮圆角 6 / 高亮 inset 6px —— 视觉上像 macOS 列表高亮（外大内小），是消除"圆角 + 直角混用"的唯一可靠手段。

**暗色模式**：所有 token 在 `body.dark` 自动切换（`--glass-bg-elevated` / `--border-hairline` / `--brand-tint` / `--brand-soft` / `--ink`）；divider 的 `--border-hairline` 是跨明暗统一的唯一可靠锚点。

**禁止**：
- ❌ 任何组件硬编码圆角（必须 `--radius-lg` / `--radius-sm`）
- ❌ divider 用 Naive 默认 `--n-divider-color`
- ❌ 对 popover 单独再设 `border-radius` 与外框不联动
- ❌ 高亮层用 100% 通铺圆角（视觉上"吞掉"外框）

**已知陷阱**：中间无 icon 项的"被矩形包围"错觉 —— 修法是给所有选项统一补 icon prefix，或统一用 `var(--space-3)` 让 padding 锚对齐。

### 7.9 图标（Icons）

> 图标 MUST 与按钮、表单、表格保持同一设计语言，禁止同一视图混用不同来源 / 风格的图标。

#### 图标尺寸

同一界面图标尺寸 MUST 控制在固定等级内，避免无级缩放：

| 尺寸 | 用途 |
|------|------|
| 14–16 px | 表格、输入框辅助图标 |
| 18–20 px | 普通操作图标（按钮内、菜单项、列表行） |
| 24 px | 导航和工具栏图标 |
| 32 px 以上 | 功能入口、空态插画 |

> 同一界面中图标尺寸应尽量控制在少数几个固定等级内。**先建立统一尺寸等级，再根据功能重要性选择对应图标大小。**

#### 图标设计要求

1. **统一线性或面性风格**：同一组图标 MUST 全部线性或全部面性，MUST NOT 混用。
2. **保持相同线条粗细**：同一组图标的线条粗细应保持一致。
3. **保持相同圆角语言**：同一组图标的直角或圆角半径应保持一致。
4. **图标视觉重量需平衡**：同一组图标视觉重量应大致平衡，避免某个图标显得过重或过轻。
5. **同一组图标使用相同画布**：在相同尺寸画布中设计，保持对齐与比例。
6. **避免混用不同来源的图标**：不同风格或来源的图标混合使用会破坏整体一致性。
7. **图标与文字间距通常为 4–8 px**：图标与文字之间保持 4–8 px 间距，确保阅读舒适。
8. **小图标需进行光学尺寸调整**：相同几何尺寸的图标，因形状不同视觉大小可能不同，MUST 通过调整留白让视觉大小一致。

#### 图标状态

图标 MUST 根据交互状态给出视觉反馈：

| 状态 | 说明 |
|------|------|
| 默认 | 中性色，表示可交互但未被关注 |
| 悬停 | 颜色变化或背景高亮，让用户感知可点击 |
| 选中 | 品牌色高亮填充，明确当前所选或激活功能 |
| 点击 | 压缩、变暗或波纹反馈，提示操作已被响应 |
| 禁用 | 低饱和度灰色，表示不可用 |
| 错误或警告 | 红色 / 橙色警示色，传达异常或需注意状态 |

> 无文字图标 MUST 确保用户可以理解其含义；陌生功能建议搭配文字或提示气泡。

### 7.10 输入框与表单（Inputs & Forms）

#### 输入框结构

一个完整输入框通常由以下部分组成：标签（Label）、必填标识、输入区域、前缀图标、占位文字（Placeholder）、后缀图标（清空 / 校验）、字数统计、辅助说明。

#### 输入框尺寸

Web 端常用高度 MUST 按三档使用：

| 高度 | 场景 |
|------|------|
| 28–32 px | 紧凑布局、表格内嵌入 |
| 36–40 px | 大多数场景，推荐使用 |
| 48 px | 重要表单或提升可操作性 |

其他尺寸规范：
- 标签与输入框间距：**4–8 px**
- 输入框左右内边距：**12–16 px**
- 输入框高度：32–48 px（配合按钮尺寸保持一致）

#### 输入框状态

MUST 实现以下状态，并提供明确视觉反馈：

| 状态 | 说明 |
|------|------|
| 默认 | 初始状态 |
| 聚焦 | 用户点击或聚焦时，突出显示（品牌辉光环） |
| 已填写 | 用户输入内容后，显示后缀清空 / 校验图标 |
| 禁用 | 不可编辑，视觉降级 |
| 只读 | 不可编辑，但可复制 |
| 错误 | 输入内容不符合规则，错误色 + 图标 + 文字提示 |
| 成功 | 输入内容正确，成功色图标 + 文字提示 |

#### 表单使用原则

1. **标签位置统一**：所有表单标签位置保持一致，建议左对齐或顶部对齐。
2. **必填项标识统一**：使用统一的必填标识（如 `*`），并在表单中保持一致说明。
3. **同类输入框宽度一致**：同一类表单输入框保持相同宽度，提升界面整洁性。
4. **错误信息靠近对应字段**：错误提示应紧靠对应输入框，便于用户快速定位和修改。
5. **不只依赖红色表示错误**：除颜色外，结合文本或图标提示，确保信息传达清晰。
6. **长表单进行分组**：表单内容较多时，使用分组和标题进行区分，降低认知负担。
7. **输入格式及时提示**：在用户输入时提供格式提示（如手机号、邮箱格式），减少错误。
8. **减少不必要的字段**：只收集必要信息，避免让用户填写无关或可选内容。
9. **提交按钮位置明确**：提交按钮应放在表单明显位置，文案清晰，便于操作。
10. **移动端考虑键盘遮挡**：在移动端避免输入框被键盘遮挡，必要时自动滚动或调整布局。

> 好的表单设计，不只是让用户"能填写"，而是让用户更快、更少出错地完成填写。

---

## 8. 表格与分页（Tables & Pagination）

### 8.1 表格通用规范
- 玻璃表头（`.glass-table` / `.settings-scroll .n-data-table` 已全局化）；hover 行 `--brand-tint`（见 §7.5）。
- 列对齐唯一真源 `useTableColumns.ts`；表头居中用 `buildTitle()` 块级 span（全局 CSS 翻不动行内 style）。
- 横向滚动：`md+` 可 `overflow-x:hidden` 配合 `min-width`；`sm-` 必须 `overflow-x:auto`，禁止 `!important` 永久隐藏。

### 8.2 `useTablePagination` — 列表分页统一组件

> 适用：ATS-NEW 前端所有 `<n-data-table>` 远程分页场景。
> 状态：2026-09-16 立项，2026-09-18 收口为统一 composable。

#### 为什么需要统一
- 多个列表页（候选 / 标量 / 需求 / 部门 / 字段 / 流程 / 院校 / 等等）分页器外观 / 行为不一致。
- 远程分页数据源有的是 `total`、有的是 `count`、有的是 `itemCount`，与 naive-ui `pagination` 字段名冲突。
- 多次复盘发现：reactive pagination 对象含 `pageSize` 字段时，naive-ui 内部受控失效（点 `50/页` 永远卡在初始值）。

#### 用法

```ts
import { useTablePagination } from '@/composables/useTablePagination'

const { pagination, queryParams, reset } = useTablePagination()

const { data, pending, refresh } = await useApiList('/api/v1/xxx/', {
  ...queryParams,  // 自动透传 page / page_size
})

// 在 <n-data-table> 上：
<n-data-table :pagination="pagination" :data="data" />
```

#### 默认参数

| 参数 | 值 |
|------|----|
| `TABLE_PAGE_SIZE` | 20 |
| `pageSizeOptions` | `[10, 20, 50, 100]` |

#### 强制外观

```
共 N 条 | [页码] | 20 / 页 [下拉] | 跳至 [输入框]
```

具体实现：`<n-pagination show-size-picker show-quick-jumper />` + `item-count` 绑定总条数 + `prefix` slot 渲染「共 N 条」。

#### 反模式（避免踩）

**8.2.1 受控失效坑（commit `53c9624` 实证）**

```ts
// ❌ 错：reactive 里含 pageSize 字段
const pagination = reactive({ page: 1, pageSize: 20, showSizePicker: true, ... })
```

Naive UI 内部：
```ts
const controlledPageSizeRef = computed(() => pagination.pageSize)
const mergedPageSizeRef = useMergedState(controlledPageSizeRef, uncontrolledPageSizeRef)
```

当 `:pagination` 传 reactive 对象且含 `pageSize` 时，`controlledPageSizeRef` 始终等于外部 reactive 的 pageSize；内置分页器的 `onUpdate:pageSize` 仅写入 `uncontrolledPageSizeRef`，**不写回外部 reactive** → pageSize 永远卡在初始值。

```ts
// ✅ 对：用 defaultPageSize（只设初始值）
const pagination = reactive({
  page: 1,
  // 没有 pageSize！
  showSizePicker: true,
  'onUpdate:page': (p) => { page = p; refresh() },
  'onUpdate:page-size': (s) => { pageSize.value = s; page = 1; refresh() },
})
```

**8.2.2 字段名错用**

| 错 | 对 |
|----|----|
| `pagination.total` | `pagination.itemCount` |
| 后端字段 `total` | 后端字段 `count` |
| naive-ui `pageSizeOptions` | naive-ui `pageSizes` |
| `?pageSize=20`（参数） | `?page_size=20`（DRF 透传） |

#### 关联文档
- 设置页滚动契约 → `SETTINGS_PAGE_STRUCTURE.md`（分页器嵌在 `.page-body` 内）
- 标准简历设置（三层结构 + 拖拽） → 本文附录 B

---

## 9. 响应式（Responsive）

| 断点 | 值 | 规则 |
|------|----|------|
| `sm` | 480 | KPI 1 列；错误页单列 |
| `md` | 768 | 侧栏转 Drawer；表格允许横向滚动 |
| `lg` | 1024 | KPI 2 列 |
| `xl` | 1280 | KPI 4 列；双列表单 |

- 主布局：`height:100dvh`（弃 `100vh`）；内容区 `overflow:auto` 内部滚，header `position:fixed`。
- 栅格：表单用 `n-grid` `item-responsive`；KPI 用 `auto-fit`。

---

## 10. 可访问性基线（Accessibility · WCAG 2.1 AA）

1. **对比度**：普通文字 ≥ 4.5:1（`--ink-faint` 已降至 `#5B6B84`，白底 5.41 / `--g1` 4.94:1）；大字号(≥18px/14px粗) ≥ 3:1。禁用态文字同样达标。
2. **焦点可见**：全局 `:focus-visible { outline:2px solid var(--brand); outline-offset:2px }`。
3. **键盘**：可点元素 `role="button"` + `tabindex=0` + `keydown.enter`（StatCard / 侧栏 footer 已遵）；**补充 `keydown.space` 以符合按钮语义**。
4. **地标**：`<main>` + 跳转链接；`aria-hidden` 用于装饰。
5. **动效降级**：`prefers-reduced-motion` 关闭非必要动画。
6. **替代文本**：`img`/`svg` 装饰用 `aria-hidden`；信息型图标配 `aria-label` / `title`。
7. **高对比模式**：下轮审计 `forced-colors`，确保 `!important` 不破坏 HCM。

---

## 11. Do / Don't（强制约束）

**Do**
- 颜色 / 间距 / 圆角 / 阴影 / 时长一律走 `tokens.css` 变量。
- 暗色只切 `body.dark`，组件不加 `dark` 分支。
- 玻璃元素必带 `-webkit-backdrop-filter` + 不透明兜底。
- 新组件复用 `.glass-*` / `.btn-*` / `.kpi-*` / `.toolbar` / `.page-header` 全局类。

**Don't**
- ❌ 硬编码 hex / rgb / 模糊值 / 圆角（除非一次性装饰且注释备案）。
- ❌ 引用未定义令牌（如历史 `--g1…--g7` 在补全前）。
- ❌ 用原生 `confirm()` / `alert()`。
- ❌ 用 `overflow:hidden` 吞掉表格 / 滚动容器真实滚动。
- ❌ 第 3 个品牌紫（只能 `--brand` / `--brand-grad-a`）。
- ❌ 卡片加 `border-left` 状态色条（X-20）——状态改用标签 / 徽标 / 图标 + 文字。
- ❌ 滥用 `!important`（仅玻璃覆盖 Naive 必要处保留，并加注释）。

---

## 12. 文件映射（规范 → 实现）

| 规范章节 | 落地文件 |
|----------|----------|
| §2 色彩 / §3 排版 / §4 间距圆角阴影 | `web/app/src/styles/tokens.css` |
| §5 布局契约 / §7 组件原子类 | `web/app/src/styles/glass.css` + `glass-modal.css` + `App.vue` themeOverrides + `lucide-vue-next` 图标库 |
| §6 弹窗分隔线 / §5.4 弹窗内边距 | `web/app/src/styles/glass.css` 弹窗段 |
| §7.8 下拉弹窗 | `glass.css` 下拉弹窗规范 + [`DROPDOWN_POPOVER_SPEC.md`](./DROPDOWN_POPOVER_SPEC.md) |
| §8.2 分页 | `web/app/src/composables/useTablePagination.ts` |
| §10 主题换肤 / 暗色 | `web/app/src/stores/theme.ts` + `App.vue` `themeOverrides` |
| §2.1 Naive 组件色 | `App.vue` `themeOverrides.common` |

---

## 附录 A. 功能页专项 — 数据字典「新增内容被遮挡」诊断

> 触发：用户报障「数据字典中，新增内容时被遮挡，无法填写」。
> 代码：`web/app/src/pages/settings/DataDictionary.vue`（1032 行）。

### A.1 设计目标（应有的样子）
新增一行元素后，用户应能：
- **A** 看到新行编辑器完整可见（input + 操作按钮）
- **B** 输入不被打断（滚动到位、焦点不丢）
- **C** 行内"取消"（撤销这一行）与底部"取消"（离开页面）从视觉上分离

### A.2 硬证据：截图 ↔ 代码对照

**P0-1 新行 input 下半截被遮挡（用户痛点根因）**
- 行内 input（代码 / 英文 / 描述）只能看到 placeholder **上半截**，下半截消失
- 行内 "保存 取消" 按钮与底部 sticky `提交栏` 的 "取消 提交" 按钮**几乎水平对齐** → 两个"取消"重叠

**根因链路**：
- `.section--elements` (L928-935) `max-height: calc(100vh - 360px)` 限定 elements 卡的最大高度
- `.el-table-scroll` (L978-983) `position: absolute; inset: 12px 16px; overflow: auto` 表格滚动容器填满 elements 卡
- `.submit-bar` (L1022-1030) `position: sticky; bottom: 16px; z-index: 10` 黏在视口底部，高度 ~64px
- **未给 `.el-table-scroll` 预留底部 padding** → 滚动到底的最后一行（包括新加的 editing 行）被 sticky submit-bar 覆盖约 64px

**修复方向**：
- A: `.el-table-scroll { padding-bottom: 80px; }` —— 仅一行业务 CSS，零行为变化（推荐）
- B: 把 sticky submit-bar 改成 `position: fixed; z-index: 100` + 给 `.page-container` 配套 `padding-bottom: 80px`
- C: 新行从 inline 改为卡片展开式（重，不推荐）

**推荐 A**：最小风险、零行为变化。

**P0-2 行内「取消」按钮 vs 底部「取消」按钮冲突**
- L222 行内 editing 态：`<n-button size="tiny" @click="cancelRow">取消</n-button>`
- L270 底部 sticky：`<n-button size="large" @click="backToList">取消</n-button>`
- 当新行在最后一行 inline 编辑时，行内"取消"和 sticky 栏"取消"**横坐标重叠，看起来像一个按钮**。
- **推荐 A**：行内 editing 态的"取消"改成 × icon button（放在行首，与 sticky 栏分隔开）。hover 提示"撤销"。

**P1-3 sticky submit-bar 无背景穿透防护**
- L1025 `background: var(--glass-bg-card)` —— 不透明卡片背景，但滚动时一旦 z-index 飘移，内容仍可能透出。
- **修复方向**：`.submit-bar` 加 `backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px)`。

### A.3 修复方案（按执行顺序，单原子提交）

| Phase | 内容 | 行数 | 风险 |
|---|---|---|---|
| P0-A | `.el-table-scroll` 加 `padding-bottom: 80px` | 1 行 | 低（零行为变化） |
| P0-B | 行内 editing 态"取消"按钮 → × icon button（行首，hover 提示"撤销"） | 5-8 行 | 低 |
| P1 | `.submit-bar` 加 backdrop-filter blur | 2 行 | 低 |
| 验证 | grep `.el-table-scroll / .submit-bar / cancelRow` + build | -- | -- |

### A.4 风险标注（不动范围 / 已知可行 / 不在范围）
- 不动：view 模式、submit-bar 内部按钮、`.el-table` / `.el-row` / `.el-cell`、新增字典弹窗。
- 可行：padding-bottom + backdrop-filter 是设计系统约定；icon button 替换文本按钮是 Naive UI 推荐做法。
- 不在范围：把 inline edit 改为卡片 modal、改元素树多级嵌套逻辑、提交栏设计位置变更。

---

## 附录 B. 功能页专项 — 标准简历设置（三层结构 + 双层拖拽）

> 适用：ATS-NEW 候选人资源（`Candidate`）的标准简历字段配置页 `web/app/src/pages/settings/StandardResumeSettings.vue`。

### B.1 模型链
```
FieldModule（模块）
  └─ FieldGroup（分组，FK → FieldModule）
       └─ DynamicField（字段，FK → FieldModule + FieldGroup）
```
**三者均有 `order_index`**。拖拽改序即改 `order_index`。

### B.2 Candidate 资源实际结构

| 层级 | 数量 | 说明 |
|------|------|------|
| `FieldModule` | **1** | `code='candidate'` / 「候选人信息」 |
| `FieldGroup`（在 candidate 模块下） | **9** | introduction / qiuzhi / basic / WorkExperience / ProjectExperience / InternshipExperience（0 字段）/ Education / Awards / LanguageSkills |
| `DynamicField` | **65** | 在 9 个分组下 |
| `DynamicField.group=None`（无分组字段） | **12** | 仍属 candidate 模块 |
| 合计 | 65 + 12 = **77**（部分隐藏字段） | |

⚠️ InternshipExperience 当前 0 字段——是结构预留，非空分组。

### B.3 页面结构（已去掉模块层）
- **不再有「模块层」拖拽**（一个资源就一个模块，模块层拖拽没意义）。
- **分组层拖拽**：用 `config.groupOrder` 存分组序。
- **字段层拖拽**：复用 `DynamicField.order_index`（步长 10，便于插入）。
- **双层拖拽 + 失败双回滚**（详见 §B.6）。

### B.4 端点

| 操作 | 端点 |
|------|------|
| 改单个分组顺序 | `PATCH /api/v1/dynamic-fields/Candidate/groups/<id>/` |
| 改单个字段顺序 | `PATCH /api/v1/dynamic-fields/Candidate/fields/<id>/` |
| 批量字段重排 | `POST /api/v1/dynamic-fields/Candidate/fields/reorder/ { orderedIds: [...] }` |

### B.5 🔴 隐藏字段（`isVisible=false`）也必须可拖

- Candidate 资源 66 字段中 **52 个 `isVisible=false`**（占 79%）。
- 拖拽手柄曾按 `v-if="!isVisible"` 条件渲染 → 79% 字段**拖不动**。
- **修法**：手柄**绝不按 `isVisible` 条件渲染**；隐藏行视觉弱化（`opacity:.55` 标签 / 类型，手柄与开关不降透明度）；隐藏行加「定义层隐藏」tag。
- 设计意图：字段是否启用 = 一等公民；字段是否可见 = 二等公民；两者解耦后，拖拽始终可用。

### B.6 拖拽失败双回滚

回滚**必须 snapshot 双份状态**，且在 mutation 之前：

```ts
async function onFieldDrop(targetIndex: number, fieldId: number) {
  // ① 双份 snapshot
  const beforeOrder = [...fieldOrder]         // DB 侧（DynamicField.order_index）
  const beforeGroupOrder = [...groupOrder]    // config 侧（field 在分组内的视觉位置）

  // ② mutation（乐观更新）
  const newOrder = reorder(beforeOrder, targetIndex, fieldId)
  fieldOrder.splice(0, fieldOrder.length, ...newOrder)

  try {
    // ③ 持久化
    await api.reorderFields({ orderedIds: newOrder })
  } catch (e) {
    // ④ 双回滚（先回 DB 侧，再回 config 侧；config 才是展示顺序的权威）
    fieldOrder.splice(0, fieldOrder.length, ...beforeOrder)
    groupOrder.splice(0, groupOrder.length, ...beforeGroupOrder)
    toast.error('排序失败，已回滚')
  }
}
```

**为什么必须 snapshot 两份**：`config.groupOrder` 是 UI 实际渲染顺序的权威（视觉上一眼可见）。仅回滚 DB 侧 → 「提示已回滚但界面顺序仍是新的」（界面与 DB 不一致，比报错还糟）。

详见 `docs/06-runbook/ENGINEERING_RULES.md` §10。

### B.7 存量数据质量（已知风险）
- 66 字段中 **52 个 `order_index=0`** 并列——初始顺序依赖并列稳定排序（脆弱）。
- 建议：一次性重排步长值（如 0/10/20/30/...），让 `order_index` 单调递增、便于后续插入。
- 不阻塞功能，但是后续维护成本。

### B.8 关联文档
- 拖拽库底层坑（vue-draggable-plus 0.6.x slot 写法） → `NAIVE_UI_PITFALLS.md` §3
- 分页（候选人列表） → 本文 §8.2
- 字段定义后端 → `apps/dynamic_field/models.py`
