# ATS-NEW UI 规范整改技术实施方案
> 最后更新：2026-09-07（依据 git 最后提交）

> 对应《UI 规范符合性审查报告》与《统一设计规范 v2.1》。按「致命优先、可访问性其次、一致性收口」顺序分阶段推进。**本方案只改前端样式/交互，不动后端契约。**

---

## 阶段总览

| Phase | 目标 | 等级 | 改动文件 | 验收 |
|-------|------|------|----------|------|
| **P0** | 补齐中性灰令牌 `--g1…--g7` | 🔴 | `tokens.css` | onboarding 流程边框/底色/文字恢复 |
| **P1** | 移除原生 `confirm()` | 🔴 | `AddCandidateModal.vue`、`DynamicFieldSettings.vue` | 改用 `useDialog().warning` |
| **P2** | 对比度达标 | 🟡 | `tokens.css`、`StatCard.vue`、`Layout.vue` | 全站文字 ≥4.5:1 |
| **P3** | 响应式一致性 | 🟡 | `glass.css`、`CampusControl.vue` | 宽表可滚、KPI 自适应 |
| **P4** | 无障碍地标 / 焦点 / 动效 | 🟡 | `Layout.vue`、`glass.css`、`tokens.css` | 地标+skip+focus+reduced-motion |
| **P5** | 视觉语言收敛 | 🟡 | `ThemeSettings.vue`、`App.vue`、`Step1*.vue` | 标题统一、去第 3 紫 |
| **P6** | 验证与防回归 | — | 新增对比/视觉回归检查 | CI 门禁 |

---

## P0 · 补齐中性灰令牌（修复致命缺陷 1.1）

**只改 1 个文件，零逐页风险。** 在 `tokens.css` 的 `:root` 与 `body.dark` 各加一段。

`:root` 内（建议插在 §2 墨色之后）：
```css
/* ===== §2.3 中性灰阶梯（修复 onboarding 流程未定义 --g* 缺陷）===== */
--g1: #F1F5F9;                                   /* 最浅填充：disabled 输入框底 */
--g2: #E2E8F0;                                   /* hover 填充 */
--g3: var(--border-hairline);                    /* 发丝边框（与 §2 同源） */
--g4: rgba(15, 23, 42, .16);                      /* 较强边框 / 虚线框 */
--g5: #64748B;                                   /* 辅助文字（对白底 4.8:1，达 AA） */
--g6: #CBD5E1;                                   /* 中间填充（备用） */
--g7: var(--ink-soft);                            /* 按钮/标签文字色 */
```

`body.dark` 内（插在墨色反转之后）：
```css
/* 中性灰阶梯·暗色（与 §2 暗色同源） */
--g1: #0B1220;
--g2: #1E293B;
--g3: var(--border-hairline);
--g4: rgba(255, 255, 255, .16);
--g5: #94A3B8;                                   /* 暗底上高对比，达标 */
--g6: #334155;
--g7: var(--ink-soft);
```

**验收**：
- `Step1Single.vue:89` 的 disabled 文件名输入框出现浅灰底；
- `Step1Batch.vue:123` 等 `var(--g3)` 边框可见；
- 浏览器 DevTools 检查 `--g1`…`--g7` 在 `:root` / `body.dark` 均有解析值（非 `unset`）。

---

## P1 · 移除原生 `confirm()`（修复致命缺陷 1.2）

**`AddCandidateModal.vue`**：`showModal` setter 与 `closeModal` 内两处 `confirm(...)`。改用 `useDialog()`：
```ts
import { useDialog } from 'naive-ui'
const dialog = useDialog()
function tryClose() {
  if (store.isDirty) {
    dialog.warning({
      title: '有未保存的修改',
      content: '确认关闭？未保存的修改将丢失。',
      positiveText: '确认关闭', negativeText: '取消',
      onPositiveClick: () => { store.closeStream(); store.reset(); emit('update:show', false) },
    })
    return
  }
  store.closeStream(); store.reset(); emit('update:show', false)
}
```
`showModal` setter 与 `closeModal` 统一调用 `tryClose()`。

**`DynamicFieldSettings.vue:270`**：
```ts
import { useDialog } from 'naive-ui'
const dialog = useDialog()
// 原：if (!confirm(`确认删除字段 "${row.label}" 吗?`)) return;
dialog.warning({ title:'删除字段', content:`确认删除字段 "${row.label}"？`, positiveText:'删除', negativeText:'取消', onPositiveClick: () => doDelete(row) })
```

**验收**：关闭未保存弹窗 / 删除字段时，出现 Naive 风格对话框（与 `CampusControl` 既有 `dialog.warning` 一致），焦点锁在弹窗内；无原生浏览器 `confirm` 弹层。

---

## P2 · 对比度达标（修复 2.1 + 2.4 禁用态）

1. `tokens.css` `--ink-faint` 浅色值由 `#94A3B8` 改为 `#64748B`（已写入 §2.2）。
2. 全仓排查 `--ink-faint` 用于 ≤13px 文字处：`StatCard.vue:132,169`、`Layout.vue:524`、各 `text-ink-faint`——改值后即达标（4.8:1）。
3. 禁用按钮（审查 3.4）：`glass.css:208` `.btn-primary:disabled` 弃用 `opacity:.5`，改为：
```css
.btn-primary:disabled {
  background: var(--g2);
  color: var(--ink-faint);
  box-shadow: none;
  cursor: not-allowed;
  transform: none;
}
```
（白字 0.5 透明叠品牌渐变对比不足，改用灰底+达标字色。）

**验收**：用对比工具（如 axe / 在线 contrast checker）抽测 `--ink-faint` 文字与 disabled 按钮，均 ≥4.5:1。

---

## P3 · 响应式一致性（修复 2.2 + 2.3）

### 3.1 KPI 栅格自适应（替换全局 `.kpi-row`）
`glass.css:522` 改为：
```css
.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
```
删除 `glass.css:563-564` 的 1024/480 媒体查询（不再需要）。**同步删除 `CampusControl.vue:1367` 的 scoped `repeat(5,1fr)` 覆盖**，让校招管控与全局同款自适应。

### 3.2 宽表横向滚动（替换 `overflow-x:hidden!important`）
`glass.css:676` 与 `:709` 的 `.n-scrollbar-container { overflow-x: hidden !important }`：
- `md+`（≥768）：保留 `overflow-x:hidden`（配合固定列 + `min-width` 表头同步）；
- `sm-`（<768）：改为 `overflow-x:auto`。
实现：
```css
@media (max-width: 767px) {
  .table-wrap .n-scrollbar-container,
  .settings-scroll .n-scrollbar-container { overflow-x: auto !important; }
}
```
并给宽表（如 `CampusControl` `mergedColumns`）的 `.n-data-table` 在 `sm-` 设 `min-width: 960px`，让横向滚动自然出现而非裁切。

**验收**：浏览器 DevTools 切 375px 宽 → 校招管控 KPI 一行 1–2 卡、表格可横向滑动无裁切；1024px 以上 KPI 多列、表格锁列正常。

---

## P4 · 无障碍地标 / 焦点 / 动效（修复 2.4 + 3.1 + 3.2）

1. **`<main>` 地标 + skip-link**：`Layout.vue:159` 的 `content-wrapper` 外包：
```html
<a class="skip-link" href="#main">跳到主内容</a>
<main id="main" class="content-wrapper"> …router-view… </main>
```
`glass.css` 加：
```css
.skip-link { position:absolute; left:-9999px; top:8px; z-index:var(--z-toast);
  background:var(--surface); color:var(--brand); padding:8px 12px; border-radius:var(--radius-sm); }
.skip-link:focus { left:8px; }
```

2. **全局焦点环**：`glass.css` 末尾加：
```css
:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; }
```
（覆盖 `ThemeSettings.vue:46` 等原生 `<button>` 缺焦点样式问题。）

3. **动效降级**：`tokens.css` 末尾加：
```css
@media (prefers-reduced-motion: reduce) {
  .workbench-card, .btn-primary, .btn-secondary, .kpi-card, * {
    animation-duration: .001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .001ms !important;
    scroll-behavior: auto !important;
  }
}
```

**验收**：屏幕阅读器/键盘 Tab 可经 skip-link 直达主区；Tab 焦点有品牌色环；系统开「减少动态效果」后 hover/入场动画静止。

---

## P5 · 视觉语言收敛（修复 2.5 + 2.6 + 3.3 + 3.7）

1. **去第 3 品牌紫**：`Step1Single.vue:478` 与 `Step1Batch.vue:454` 的 `.pfill.pu { background:#8B5CF6 }` 改为 `background: var(--brand-grad-a)`（或新增 `--c-category-purple` 令牌）。
2. **`page-title` 统一**：删除 `ThemeSettings.vue:275-280` 的 scoped `.page-title` 字号覆盖，复用全局 26px 渐变（审查 2.6）。
3. **`100vh`→`100dvh`**：`Layout.vue:618` `.app-layout{height:100vh}` → `height:100dvh`；`AddCandidateModal.vue:103` `height:80vh` → `height:min(80vh,700px)`。
4. **`index.html` 补元信息**：加 `<meta name="theme-color" content="#EEF1FB">` 与 `<meta name="color-scheme" content="light dark">`（审查 3.7）。
5. **`App.vue` 语义色注释**：在 `App.vue:54-57` 上方加注释「与 tokens.css §4 语义色同步，改令牌需同步此处」。

**验收**：设置中心所有页标题字号/渐变一致；无第 3 紫；移动端主区高度贴合视口（地址栏不裁切）。

---

## P6 · 验证与防回归

1. **对比度自动检查**：在 `qa-final*.mjs` 系列中追加 axe-core 扫描（或独立 `npm script`），对 `Dashboard` / `CampusControl` / `AddCandidateModal` / `ThemeSettings` 跑 WCAG AA，门禁失败则 CI 红。
2. **视觉回归**：对暗色 / 浅色 / `prefers-reduced-motion` 三态截图对比（校招管控、录入弹窗、设置中心）。
3. **令牌完整性单测**：脚本断言 `:root` 与 `body.dark` 下 `--brand/--ink*/--glass-*/--g1…--g7/--c-*` 均有定义值（防再次出现未定义令牌）。
4. **手动走查清单**：键盘全 Tab 一遍（焦点环 + 顺序）、窄屏（375/768）各页、暗色切换品牌色、关闭未保存弹窗走 `useDialog`。

---

## 风险与注意

- **P0 改动最小但影响面最大**：先合 P0 单独验证 onboarding 流程渲染，再推后续阶段，避免一次大改难以 bisect。
- **`!important` 收敛（审查 3.6）** 不在本方案强控，留作下轮 HCM（forced-colors）专项；本次仅新增焦点环/reduced-motion 时谨慎用 `!important`。
- **Naive `themeOverrides` 不解析 `var()`**：品牌/语义色仍用 hex 字面量（已在 `App.vue` 注释备案），与令牌值保持手动同步即可。
- 所有样式改动遵循项目既有工作流：定位根因 → diff → commit → push（feat/ui-v2-reconciliation 分支）。
