# 下拉弹窗统一规范（Dropdowns / Selects / Popovers · v1.0）

> **范围**：所有「浮起的菜单型选择器 / 列表 / 面板」，包含 Naive UI 的 `n-dropdown` / `n-select` / `n-cascader` / `n-tree-select` / `n-date-picker` / `n-color-picker` / `n-time-picker`，以及 `n-popover` 的 click 触发型浮层。
> **目的**：终结「外框圆角 + 项目直角」的视觉割裂，以及暗色模式下 Naive 自带 divider 灰线与暗色 token 脱节的色块问题。
> **落地**：本规范的代码实现全部落在 `web/app/src/styles/glass.css` 的 **§下拉弹窗规范** 一节，**禁止任何组件硬编码**圆角/divider 颜色/选项内边距。
> **版本**：v1.0（2026-08-28 兵哥反馈"下拉弹窗圆角和直角混用"后立项）

---

## 1. 三层结构与命名

下拉弹窗在 Naive UI 内部由 **三层 BEM 元素**组成，规范必须穿透到每一层（不要只看外层）：

| 层 | 主要类名 | 管辖内容 | 关联规范 |
|----|---------|---------|---------|
| **外层容器** | `.n-popover`（dropdown 复用 popover 渲染） | 浮起容器 + 阴影 + 圆角 | §1.1 |
| **内层菜单** | `.n-dropdown-menu` / `.n-base-select-menu` | 滚动容器 + 背景 + box-shadow | §1.2 |
| **项目行** | `.n-dropdown-option` / `.n-base-select-option` / `.n-dropdown-divider` / `.n-base-select-option__content` | 单行 + hover 高亮 + 文本 + 分割线 | §1.3 |

> ⚠️ **Naive 内部别名**：`n-dropdown-option-body`、`n-dropdown-option-body::before`（绝对定位的高亮层）、`n-dropdown-option-prefix/label/suffix`、`n-dropdown-group-header`（仅 `type:'group'` 时存在）。

---

## 2. 视觉五件套

### 2.1 外层容器（`.n-popover`）

| 属性 | 规范值 | Token | 备注 |
|------|--------|-------|------|
| 圆角 | 12px | `--radius-lg` | **与 `.glass-panel` / `.glass-card` 一致**，dropdown 不应单独定义 |
| 背景 | 半透明 + 玻璃模糊 | `--glass-bg-elevated` + `blur(var(--glass-blur-panel))` | 沿用既有 §5.6 弹窗规范 |
| 边框 | 1px 玻璃描边 | `--glass-border` | 浅色 0.7 白，暗色 0.14 白 |
| 阴影 | 浮起四级 | `--shadow-elevated` | 与 modal 同源 |
| z-index | 1000 | `--z-dropdown` | 已在 §2.7 定义 |

### 2.2 内层菜单（`.n-dropdown-menu` / `.n-base-select-menu`）

| 属性 | 规范值 | Token | 备注 |
|------|--------|-------|------|
| 背景 | 同外层（不留层次） | `--glass-bg-elevated` | **不**叠加额外半透明层（避免双重透明导致颜色失真） |
| 内容 padding | 8px 垂直 / 0 水平 | `--space-2` | Naive 默认 4px → 升 8px 让分隔更舒展 |
| 滚动 | `contentScrollable` / `n-scrollbar` | — | 改 tokens.css `--scrollbar-*` 而非 Naive 默认 |
| 圆角 | 同外层圆角 | `--radius-lg` | 内层无独立圆角（避免双层圆角错位） |

### 2.3 项目行（`.n-dropdown-option` / `.n-base-select-option`）

| 属性 | 规范值 | Token | 备注 |
|------|--------|-------|------|
| 高度 | 36px（medium 默认） | `--n-option-height-medium` | 与 button/input 高度对齐 |
| 水平 padding | 12px | `--space-3` | Naive 默认 12 ✓，**禁止个别组件覆写** |
| 文字色 | `--ink` / hover `--ink` / active `--brand` | — | 不变色，只换底色 |
| 高亮（hover/pending） | `--brand-tint` + 内 inset 6px + 圆角 6px | `--space-1` + `--radius-sm` | 见下方 §3 |
| 高亮（active 选中） | `--brand-soft` + 同上 inset | `--brand-soft` | 与 active 行视觉一致 |
| 禁用态 | `--ink-faint` + `cursor:not-allowed` | `--n-option-opacity-disabled` | Naive 内置 `opacityDisabled` |
| prefix 图标列宽 | s/m/l/h = 32/32/36/36 px | Naive `--n-option-icon-prefix-width` | 与 icon 同行对齐 |

### 2.4 分割线（`.n-dropdown-divider`）

| 属性 | 规范值 | Token | 备注 |
|------|--------|-------|------|
| 高度 | 1px | — | 永远 1px |
| 颜色 | `--border-hairline` | `--border-hairline` | **覆盖 Naive 默认 `--n-divider-color`（浅灰 0.09）**，避免暗色下仍渲浅灰 |
| 上下间距 | 8px | `--space-2` | Naive 默认 4px → 升 8px 配合 padding |
| 水平缩进 | 8px（与 padding 同行） | `--space-2` | 行内留白与行 padding 对齐 |

### 2.5 滚动条（popover/menu 内部滚动时）

走全局 §6 滚动条规范，不单独覆写。`pointer-events:none` 确保 thumb 不吞相邻小点击目标。

---

## 3. 高亮层「层叠圆角」实现

### 3.1 原理

```
┌──────── n-popover ──────┐     外层圆角 = --radius-lg (12)
│                       │
│  ┌─ n-dropdown-menu ─┐│     内层无独立圆角
│  │                  ││
│  │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒ ││     hover 高亮 = inset 6px + --radius-sm (6)
│  │ ▒  菜单：左 侧 ▒ ││     "外框大圆角 + 内部圆角小 = 层叠" 视觉
│  │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒ ││     （类似 macOS 列表高亮）
│  └──────────────────┘│
└──────────────────────┘
```

**核心规则**：
- 外层大圆角 `--radius-lg`（12）
- 内部高亮小圆角 `--radius-sm`（6）
- inset 水平 6px、垂直 0（让高亮贴近上下边界更"贴肉"）
- **不**用 100% 通铺圆角高亮（视觉上会"吞掉"弹层外框圆角）

### 3.2 CSS 实现（落地在 `glass.css`）

```css
/* 高亮层（hover / pending / selected 共享） */
.n-dropdown-option-body::before,
.n-base-select-option::before {
  inset: 0 6px !important;          /* 水平 inset 6px，垂直满铺 */
  border-radius: var(--radius-sm) !important;  /* 6px 小圆角 */
  background-color: transparent !important;
  transition: background-color .15s var(--ease-out) !important;
}
.n-dropdown-option:hover .n-dropdown-option-body::before,
.n-dropdown-option--pending .n-dropdown-option-body::before,
.n-base-select-option:hover::before,
.n-base-select-option--pending::before {
  background-color: var(--brand-tint) !important;  /* hover */
}
.n-dropdown-option--selected .n-dropdown-option-body::before,
.n-dropdown-option--active .n-dropdown-option-body::before,
.n-base-select-option--selected::before,
.n-base-select-option--checked::before {
  background-color: var(--brand-soft) !important;  /* 选中 */
}
```

---

## 4. 暗色模式（`body.dark` 联动）

### 4.1 自动覆盖（无需组件改 dark 分支）

Naive 的 popover/dropdown 全用 CSS 变量 `--glass-bg-elevated` / `--glass-border` / `--border-hairline` / `--brand-tint` / `--brand-soft`。这些 token 在 `body.dark` 已自动切换：

| Token | 浅色 | 暗色 | 行为 |
|-------|------|------|------|
| `--glass-bg-elevated` | `rgba(255,255,255,.72)` | `rgba(30,41,59,.72)` | 浅色白玻璃 → 暗色深玻璃 |
| `--glass-border` | `.7` 白 | `.14` 白 | 浅色亮边 → 暗色淡边 |
| `--border-hairline` | `rgba(15,23,42,.08)` | `rgba(255,255,255,.08)` | 浅色微黑 → 暗色微白 |
| `--brand-tint` | `6%` brand | `14%` brand（自适应提升可视度） | 暗色下加深 |
| `--brand-soft` | `12%` brand | `18%` brand | 暗色下加深 |
| `--ink` | `#0F172A` | `#E8ECF6` | 浅色墨 → 暗色亮 |

### 4.2 显式覆盖（避免 Naive 默认色在暗色下冲突）

| 元素 | 浅色 | 暗色 |
|------|------|------|
| `.n-dropdown-option` 文字色 | `var(--n-option-text-color)` (继承 `textColor2`) | 同 |
| `.n-popover` 阴影 | `var(--shadow-elevated)` | 暗色加深（已在 tokens §14） |
| `.n-dropdown-divider` 颜色 | **`var(--border-hairline)` 覆写 `--n-divider-color`** | 同（暗色下由 `--border-hairline` 自动转白） |

### 4.3 测试要求

任何 dropdown 在 PR 前必须用浏览器**手动 / Playwright headless** 双模式（浅色 + `body.dark`）截图，目检：
- 暗色下弹层文字 ≥ 4.5:1
- divider 在两种模式下都不与背景粘死/过亮
- hover 高亮不会"穿透"暗色极光底

---

## 5. Do / Don't

### Do

- ✅ 三层结构一并穿透覆写（外 + 内 + 项目 + divider），不要只改外层
- ✅ divider 颜色一律走 `--border-hairline`，**禁止** `var(--n-divider-color)`（暗色脱节）
- ✅ 高亮层 inset 用 `0 6px`，**禁止** Naive 默认 `0 4px`（与外层圆角咬不紧）
- ✅ hover 高亮与外层圆角形成"层叠圆角"（外大 12 / 内小 6）
- ✅ 弹层内文字色用 `--ink` / 激活态 `--brand`，**禁止**写死色
- ✅ 暗色不加 dark 分支，全部由 token 集联动

### Don't

- ❌ 不要在 dropdown 内嵌独立 `<div class="...">` 制造"分组容器"——靠 `type:'divider'` 实现分组，让 Naive 渲染统一
- ❌ 不要对 `.n-popover` / `.n-dropdown-menu` 单独设 border-radius（让它们继承 `--radius-lg`）
- ❌ 不要写死 `background: white` / `background: #fff` —— 用 `--glass-bg-elevated`
- ❌ 不要在 dropdown option 内用 `padding-left != --space-3` —— 统一 12px 视觉锚
- ❌ 不要让 divider 跨「整行」—— 水平 8px 缩进与 padding 对齐

---

## 6. 已知视觉陷阱（已踩坑）

| 陷阱 | 现象 | 修法 |
|------|------|------|
| 「外圆内方」 | 弹层外框 12px 圆角，内行无圆角无高亮 = 直角感 | hover 高亮必须圆形 `--radius-sm` |
| 中间无 icon 项被"矩形包围"错觉 | 选项混有/无 icon，无 icon 项视觉缩窄像嵌独立容器 | **统一补 icon prefix** 或统一用同字号 left padding 让锚点对齐 |
| Naive 默认 divider 灰在暗色仍浅灰 | 暗色下弹层里 divider 像一条白线刺眼 | 覆写 `--n-divider-color → var(--border-hairline)` |
| 高亮层 border-radius 与外框错位 | 高亮是大圆角 + 内嵌到小圆角容器 = 视觉空隙 | 外大内小（12 / 6）+ inset 6px |
| z-index 错层 | dropdown 被 modal 遮罩挡掉 | `--z-dropdown:1000 < --z-modal:1200`，不要再单独设 |
| 空 option 在 select 中漂白 | select 的 empty 状态没有显式样式 | 沿用 option 样式，仅文字色降为 `--ink-faint` |
| 多列 dropdown 行被切成多列 | Naive 多列渲染有列分隔线 | 用 `columns` / `grid` 而非表格；分隔线统一用 `--border-hairline` |

---

## 7. 移动端（≤768）

- dropdown 弹层占据 ≥80vw，最大宽度等同 desktop（不缩窄）
- 选项高度保持 36px，触控目标 ≥44×44 通过 inset + 8px 上下 padding 实现
- 抽屉式 dropdown 不要用——直接转 n-drawer bottom placement（沿用 §5.6 抽屉规范）

---

## 8. 文件映射

| 规范章节 | 落地文件 |
|---------|---------|
| §2 视觉五件套 / §3 高亮层 / §4 暗色 | `web/app/src/styles/glass.css` §下拉弹窗规范 |
| §3 inset 实现细节（Naive BEM 内层类名） | `glass.css` 注释备案 |
| §6 已知陷阱 | `docs/ui/UI_DESIGN_SPEC.md` §5.8（指针 + 摘要） |

---

> **关联规范**：
> - §5.6 弹窗 / 抽屉（modal / drawer）：`glass-modal.css` —— dropdown 复用 popover，与 modal 共享「外层容器」规则
> - §6 滚动条：`--scrollbar-*` token，下拉弹层内部滚动共享
> - §7 a11y：键盘 ⬆⬇⬅➡ Enter Esc 操作已由 Naive 原生支持，不另行加规则；仅需 `:focus-visible` 焦点环统一
