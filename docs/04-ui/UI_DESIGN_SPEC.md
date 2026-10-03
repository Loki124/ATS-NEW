# ATS-NEW 统一设计规范（Unified Design Spec · v2.3）
> 最后更新：2026-09-20（依据 git 最后提交）

> 本文是 ATS-NEW 前端**唯一权威设计规范**，与 `tokens.css` / `glass.css` / `glass-modal.css` 一一对应。任何新增/修改 UI 必须以本规范 + 令牌为准，**禁止硬编码颜色、模糊值、圆角、阴影、字号**。
> 版本：v2.3（2026-09-20 新增 §5.9 图标规范、§5.10 输入框与表单规范，来自 UI Design Standards 05/06/07）

---

## 1. 设计原则（Principles）

1. **单一事实来源（Single Source of Truth）**：所有颜色/间距/圆角/阴影/动效时长均为 CSS 变量，定义在 `tokens.css`。改品牌色只改 `--brand` 一处。
2. **暗色靠变量集切换，不写硬色**：组件 CSS 不出现 `dark` 分支；切 `body.dark` 即整体换肤。
3. **玻璃优先（Glass-first）**：面板/卡片/弹窗/侧栏默认半透明玻璃 + `backdrop-filter`，必须带 `-webkit-` 前缀与**不透明兜底**。
4. **可访问性基线 = WCAG 2.1 AA**：普通文字对比 ≥ 4.5:1，大字 ≥ 3:1，焦点可见，动效可降级。
5. **响应式断点统一**：`sm 480 / md 768 / lg 1024 / xl 1280`；移动端（≤768）侧栏转 Drawer。
6. **语义色只表状态，不表品牌**：success/warning/error/info 与品牌色解耦。

---

## 2. 色彩系统（Color）

### 2.1 品牌色（Brand · 单一输入）
| Token | 值（浅） | 派生方式 | 用途 |
|-------|----------|----------|------|
| `--brand` | `#6366F1` | **唯一手填** | 按钮/激活态/链接/玻璃辉光/极光主光斑 |
| `--brand-hover` | — | `color-mix(--brand 80% #fff)` | hover |
| `--brand-pressed` | — | `color-mix(--brand 82% #000)` | pressed |
| `--brand-dark` | — | `color-mix(--brand 66% #000)` | 暗色环境 |
| `--brand-soft` | — | `color-mix(--brand 12% transparent)` | 浅底激活/hover 行 |
| `--brand-tint` | — | `color-mix(--brand 6% transparent)` | 极浅 hover 行 |
| `--brand-grad-a` | `#A855F7` | 手填（渐变中段） | 标题/按钮渐变 |
| `--brand-grad-b` | `#EC4899` | 手填（渐变末段·仅装饰） | 标题渐变末段 |

> 腾讯蓝备选：`--brand:#0052D9`。**任何「品牌紫」必须是 `--brand` / `--brand-grad-a` 之一，禁止第 3 个硬编码紫（如曾出现的 `#8B5CF6`，见审查 2.5）。**

### 2.2 墨色 / 中性文字（Ink · 必须满足对比度）
| Token | 浅色值 | 暗色值 | 对比（浅/白底） | 用途 |
|-------|--------|--------|-----------------|------|
| `--ink` | `#0F172A` | `#E8ECF6` | 15:1 / — | 标题、重要正文 |
| `--ink-soft` | `#475569` | `#AEB8CC` | 7.0:1 / — | 次要正文、标签 |
| `--ink-faint` | **`#64748B`**（修订） | `#94A3B8` | **4.8:1** / 高 | 辅助/占位（**旧 `#94A3B8` 仅 2.6:1，已不达标，弃用**） |
| `--surface` | `#FFFFFF` | `#1E293B` | — | 不透明兜底 |

### 2.3 中性灰阶梯（Neutral Ramp · **本次新增，修复 `--g1…--g7` 未定义缺陷**）
onboarding 流程曾引用 `--g1…--g7` 但全仓未定义，导致边框/底色/文字静默失效。现正式纳入令牌：

| Token | 浅色值 | 暗色值 | 语义 | 原误用位置 |
|-------|--------|--------|------|-----------|
| `--g1` | `#F1F5F9` | `#0B1220` | 最浅填充（disabled 输入框底、弱 hover 底） | Step1Single:89、Step2Assign:278 |
| `--g2` | `#E2E8F0` | `#1E293B` | hover 填充 | Step2Assign:128、Step1Batch:192 |
| `--g3` | `var(--border-hairline)` | `var(--border-hairline)` | 发丝边框 | 全 onboarding `1px solid var(--g3)` |
| `--g4` | `rgba(15,23,42,.16)` | `rgba(255,255,255,.16)` | 较强边框 / 虚线框 | UploadZone:45、Step1Batch:123 |
| `--g5` | **`#64748B`** | `#94A3B8` | 辅助文字（**必须 ≥4.5:1**） | AddCandidateModal:99、Step1Single:108 |
| `--g6` | `#CBD5E1` | `#334155` | 中间填充（备用） | — |
| `--g7` | `var(--ink-soft)` | `var(--ink-soft)` | 按钮/标签文字色 | Step2Assign:321 `.bs color` |

> 落地方式：`tokens.css` 的 `:root` 与 `body.dark` 各补一段（见《技术实施方案》Phase 0）。**迁移策略 = 先补令牌（零逐页改动），下个迭代再将 `--g*` 逐步替换为语义更明确的 `--border-hairline` / `--brand-soft` 等。**

### 2.4 语义色（Semantic · 仅状态）
| Token | 值 | 浅底 soft | 暗底 soft |
|-------|----|-----------|-----------|
| `--c-success` | `#16A34A` | `.12` | `.22` |
| `--c-warning` | `#F59E0B` | `.14` | `.24` |
| `--c-error` | `#EF4444` | `.12` | `.22` |
| `--c-info` | `#3B82F6` | `.12` | `.22` |

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
`--aurora-base` + `--aurora-1/2/3`（靛/紫/青径向光斑），暗色转深空。由 `.app-aurora` / `.settings-aurora` / `.cc-aurora` 承载，`aria-hidden`。

### 2.7 z-index 比例尺
`--z-sidebar:10 / --z-header:20 / --z-dropdown:1000 / --z-drawer:1100 / --z-modal:1200 / --z-toast:1300`

---

## 3. 排版（Typography）

- 字体：`--font-sans: "PingFang SC","Microsoft YaHei",-apple-system,…`；等宽 `--font-mono`。
- 字号刻度（已定义）：`--text-display 40 / h1 32 / h2 24 / h3 20 / h4 18 / body 15 / small 13 / meta 12`。
- 行高：标题 1.2–1.4，正文 1.6。
- **数字对齐**：统计值用 `font-variant-numeric: tabular-nums`（参考 `StatCard.vue:124`）。
- 页面主标题统一类 `.page-title`（26px / 700 / 渐变），**全站唯一规格**（修订审查 2.6，删除 `ThemeSettings` 32px 覆盖）。

---

## 4. 间距 / 圆角 / 阴影 / 动效

- **间距（4pt）**：`--space-1 4 / 2 8 / 3 12 / 4 16 / 6 24 / 8 32 / 12 48 / 16 64`。
- **圆角**：`--radius-sm 6 / md 16 / lg 20 / pill 9999`。（主圆角 16 与 Naive `borderRadius:16px` 对齐）
- **阴影**：`--shadow-xs/sm/card/panel/elevated/2xl` + `--glow-brand`。暗色下整体转纯黑低透（§14 已定义）。
- **动效**：`--ease-out cubic-bezier(.16,1,.3,1)`；`--duration-fast 160 / base 240 / slow 320 ms`。
- **动效降级（新增）**：`@media (prefers-reduced-motion: reduce)` 内将 `animation/transition-duration` 降至近 0（见 §7）。

---

## 5. 组件规范（Component Specs）

### 5.1 按钮

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

每个按钮 MUST 实现完整 7 态：default、hover、active、focus-visible、selected（切换/激活态）、loading、disabled。危险按钮 MUST 额外保持 danger 视觉区分。

| 状态 | 说明 |
|------|------|
| 默认 | 静止基础样式 |
| 悬停 | 轻微视觉反馈（颜色加深 / 描边变品牌色 / `translateY(-1px)`） |
| 按下 | 点击瞬间反馈（压缩 / 变暗 / 波纹） |
| 选中 | 切换或激活状态下明确区分，通常用品牌色填充 |
| 加载 | 显示加载状态并禁用重复提交（`loading` + `disabled` 同时置位） |
| 禁用 | 视觉降级但保持可读性，禁用 `opacity` 伪透明 |
| 危险 | 删除/清空/退出等高风险操作使用错误色，与主按钮形成明显区分 |

#### 按钮使用原则

1. **同一页面主按钮数量不宜过多**：每屏建议只保留 1 个最突出的 primary action。
2. **重要操作层级最清晰**：最重要操作用主按钮，次要用次按钮或文字按钮，形成清晰层级。
3. **按钮文案简短明确，优先使用动词**：中文 2–6 字，使用「保存」「删除」「查看详情」等具体动作；MUST NOT 使用「提交/确定/是/否/OK」（见 R-204）。
4. **重要操作与危险操作应明显区分**：主按钮用品牌色，危险按钮用错误色，避免误操作。
5. **按钮尺寸统一，点击区域足够**：图标按钮视觉 28–32px，命中区 MUST ≥ 44×44px；主按钮 44–48px。
6. **对齐统一，间距保持一致**：同一页面按钮对齐方式、按钮间距遵循统一规范。
7. **加载与禁用状态清晰可见**：帮助用户理解当前状态，避免重复点击。
8. **表单提交按钮位置应清晰可见**：放在内容区域底部或右下方，移动端保持可见。

### 5.2 卡片 / 面板
- `.glass-panel`（大块容器）、`.glass-card`（统计/列表卡）、`.n-card.n-card`（全局玻璃化）。
- KPI：`.kpi-card`——玻璃底 + 无边框 + hover 品牌浅底上浮；**栅格统一 `repeat(auto-fit,minmax(180px,1fr))`**（修订审查 2.3，去 4/5 列分裂）。

### 5.3 标签 / 徽标
`.glass-tag` + `--brand/success/warning/error/info` 变体；文字用 `--ink-soft`（非 `--ink-faint`）。

### 5.4 输入框
`.glass-input`——玻璃底 + focus 3px 品牌辉光环（`box-shadow:0 0 0 3px var(--brand-tint)`）；disabled 用 `--g1` 底（修订 1.1）。

### 5.5 数据表格
- 玻璃表头（`.glass-table` / `.settings-scroll .n-data-table` 已全局化）；hover 行 `--brand-tint`。
- **横向滚动策略（修订 2.2）**：`md+` 可 `overflow-x:hidden` 配合 `min-width`；`sm-` 必须 `overflow-x:auto`，禁止 `!important` 永久隐藏横向滚动。
- 真实滚动职责归还 `.n-scrollbar-container`（`overflow-y:auto`，绝不可 `overflow:hidden` 吞 wheel 事件——见工程铁律）。

### 5.6 弹窗 / 抽屉
- `.n-modal` / `.n-drawer` 玻璃化（`glass-modal.css`）；遮罩 `.n-modal-mask` 毛玻璃。
- 居中 + `max-height:90vh` + 内部滚动（`.n-card__content` `max-height:calc(90vh-110px)`）。
- **确认类弹窗统一用 `useDialog().warning(...)`（修订审查 1.2），禁用原生 `confirm()`**。

### 5.7 导航 / 页面 Shell
- 侧栏 `.glass-sidebar`：透明 + 极光透出（Layout.vue 已改）；激活项 `--brand-soft` 底 + 3px 品牌 accent bar。
- 页面根：`.page-container`(24px) / `.cc-page` / `.settings-scroll`(20px)。
- 页头吸顶：`.page-header` `position:sticky; top:0`（设置页已全局化）。
- **语义地标（修订 2.4）：内容区包 `<main id="main">`；加 skip-link。**

### 5.8 下拉弹窗（Dropdowns / Selects / Popovers · **新增 v2.2**）

> **2026-08-28 兵哥反馈"下拉弹窗圆角和直角混用"立项。** 详细规范见 [`docs/ui/DROPDOWN_POPOVER_SPEC.md`](./DROPDOWN_POPOVER_SPEC.md)；本节为指针 + 关键规则摘要。

**适用对象**：`n-dropdown` / `n-select` / `n-cascader` / `n-tree-select` / `n-date-picker` / `n-color-picker` / `n-time-picker` / `n-popover`（click 触发型）。

**三层结构**（必须穿透覆写，**不能只改外层**）：

| 层 | 类名 | 关键规则 |
|----|------|---------|
| 外层容器 | `.n-popover` | 圆角 = `--radius-lg`（12）；背景 = `--glass-bg-elevated` + `blur(--glass-blur-panel)`；边框 = `--glass-border`；阴影 = `--shadow-elevated`；z-index = `--z-dropdown` |
| 内层菜单 | `.n-dropdown-menu` / `.n-base-select-menu` | 圆角同外层（不留独立圆角）；padding = `var(--space-2)` 垂直 |
| 项目行 | `.n-dropdown-option` / `.n-base-select-option` | 高度 36px（中等）；水平 padding = `var(--space-3)`（12px）；hover 高亮 = `var(--brand-tint)` + inset `0 var(--space-1)`（6px）+ `border-radius: var(--radius-sm)` |
| 分割线 | `.n-dropdown-divider` | 颜色 **`var(--border-hairline)`**（覆写 Naive 默认 `--n-divider-color`，避免暗色下仍浅灰）；上下间距 = `var(--space-2)`；水平缩进 = `var(--space-2)` |

**「层叠圆角」原则**：外框圆角 12 / 内部高亮圆角 6 / 高亮 inset 6px —— 视觉上像 macOS 列表高亮（外大内小），是消除"圆角+直角混用"的唯一可靠手段。

**暗色模式**：所有 token 在 `body.dark` 自动切换（`--glass-bg-elevated` / `--border-hairline` / `--brand-tint` / `--brand-soft` / `--ink`）；divider 的 `--border-hairline` 是跨明暗统一的唯一可靠锚点。

**禁止**：
- ❌ 任何组件硬编码圆角（必须 `--radius-lg` / `--radius-sm`）
- ❌ divider 用 Naive 默认 `--n-divider-color`
- ❌ 对 popover 单独再设 `border-radius` 与外框不联动
- ❌ 高亮层用 100% 通铺圆角（视觉上"吞掉"外框）

**已知陷阱**（详见 [DROPDOWN_POPOVER_SPEC §6](./DROPDOWN_POPOVER_SPEC.md#6-已知视觉陷阱已踩坑)）：中间无 icon 项的"被矩形包围"错觉 —— 修法是给所有选项统一补 icon prefix，或统一用 `var(--space-3)` 让 padding 锚对齐。

### 5.9 图标（Icons · 新增 v2.3）

> 图标 MUST 与按钮、表单、表格保持同一设计语言，禁止同一视图混用不同来源/风格的图标。

#### 图标尺寸

同一界面图标尺寸 MUST 控制在固定等级内，避免无级缩放：

**Web 端常用尺寸**

| 尺寸 | 用途 |
|------|------|
| 14–16 px | 表格、输入框辅助图标 |
| 18–20 px | 普通操作图标（按钮内、菜单项、列表行） |
| 24 px | 导航和工具栏图标 |
| 32 px 以上 | 功能入口、空态插画 |

**移动端常用尺寸**

| 尺寸 | 用途 |
|------|------|
| 16×16 px | 辅助图标 |
| 20×20 px | 表单、标签图标 |
| 24×24 px | 导航和操作图标 |
| 32×32 px | 功能入口 |
| 40–48 px | 大功能图标 |

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
| 错误或警告 | 红色/橙色警示色，传达异常或需注意状态 |

> 无文字图标 MUST 确保用户可以理解其含义；陌生功能建议搭配文字或提示气泡。

### 5.10 输入框与表单（Inputs & Forms · 新增 v2.3）

#### 输入框结构

一个完整输入框通常由以下部分组成：标签（Label）、必填标识、输入区域、前缀图标、占位文字（Placeholder）、后缀图标（清空/校验）、字数统计、辅助说明。

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
| 已填写 | 用户输入内容后，显示后缀清空/校验图标 |
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

## 6. 响应式（Responsive）

| 断点 | 值 | 规则 |
|------|----|------|
| `sm` | 480 | KPI 1 列；错误页单列 |
| `md` | 768 | 侧栏转 Drawer；表格允许横向滚动 |
| `lg` | 1024 | KPI 2 列 |
| `xl` | 1280 | KPI 4 列；双列表单 |

- 主布局：`height:100dvh`（修订 3.3，弃 `100vh`）；内容区 `overflow:auto` 内部滚，header `position:fixed`。
- 栅格：表单用 `n-grid` `item-responsive`；KPI 用 `auto-fit`。

---

## 7. 可访问性基线（Accessibility · WCAG 2.1 AA）

1. **对比度**：普通文字 ≥ 4.5:1（`--ink-faint` 已降至 `#64748B`）；大字号(≥18px/14px粗) ≥ 3:1。禁用态文字同样达标。
2. **焦点可见**：全局 `:focus-visible { outline:2px solid var(--brand); outline-offset:2px }`（修订 3.2）。
3. **键盘**：可点元素 `role="button"` + `tabindex=0` + `keydown.enter`（StatCard/侧栏 footer 已遵）；**补充 `keydown.space` 以符合按钮语义**。
4. **地标**：`<main>` + 跳转链接；`aria-hidden` 用于装饰。
5. **动效降级**：`prefers-reduced-motion` 关闭非必要动画（修订 3.1）。
6. **替代文本**：`img`/`svg` 装饰用 `aria-hidden`；信息型图标配 `aria-label` / `title`。
7. **高对比模式**：下轮审计 `forced-colors`，确保 `!important` 不破坏 HCM。

---

## 8. Do / Don't（强制约束）

**Do**
- 颜色/间距/圆角/阴影/时长一律走 `tokens.css` 变量。
- 暗色只切 `body.dark`，组件不加 `dark` 分支。
- 玻璃元素必带 `-webkit-backdrop-filter` + 不透明兜底。
- 新组件复用 `.glass-*` / `.btn-*` / `.kpi-*` / `.toolbar` / `.page-header` 全局类。

**Don't**
- ❌ 硬编码 hex / rgb / 模糊值 / 圆角（除非一次性装饰且注释备案）。
- ❌ 引用未定义令牌（如历史 `--g1…--g7` 在补全前）。
- ❌ 用原生 `confirm()` / `alert()`。
- ❌ 用 `overflow:hidden` 吞掉表格/滚动容器真实滚动。
- ❌ 第 3 个品牌紫（只能 `--brand` / `--brand-grad-a`）。
- ❌ 滥用 `!important`（仅玻璃覆盖 Naive 必要处保留，并加注释）。

---

## 9. 文件映射（规范 → 实现）

| 规范章节 | 落地文件 |
|----------|----------|
| §2 色彩 / §3 排版 / §4 间距圆角阴影 | `web/app/src/styles/tokens.css` |
| §5.1–5.10 组件原子类（按钮 / 图标 / 输入框 / 表单 / 卡片 / 表格 / 弹窗 / 下拉） | `web/app/src/styles/glass.css` + `glass-modal.css` + `App.vue` themeOverrides + `lucide-vue-next` 图标库 |
| §5.6 弹窗玻璃 / §2.5 | `web/app/src/styles/glass-modal.css` |
| §5.8 下拉弹窗（dropdown / select / popover） | `web/app/src/styles/glass.css` §下拉弹窗规范 + [`docs/ui/DROPDOWN_POPOVER_SPEC.md`](./DROPDOWN_POPOVER_SPEC.md) |
| §7 主题换肤 / 暗色 | `web/app/src/stores/theme.ts` + `App.vue` `themeOverrides` |
| §2.1 Naive 组件色 | `App.vue` `themeOverrides.common` |
