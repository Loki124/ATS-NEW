# 样式调整与替换表（DESIGN.md v2 → 全站代码）

> 目的：把当前 99 处 Ant Design 硬编码色 + 401 处 font-size + 126 处 padding + 165 处 border-radius 一次性映射到 tokens.css v2 变量。
> 适用：所有 `web/app/src/**/*.vue`（不含 `src/styles/*.css` 与 node_modules）。
> 替换前**先** grep 确认无遗漏；替换后**必须** `npm run build` + `npm run lint:ci` + `localhost:5212` 视觉回归。

---

## 一、颜色替换映射（Ant Design hex → tokens.css v2）

> 替换原则：**状态语义色走 --c-* 变量；品牌语义走 --brand 变量；中灰文字走 --ink-* 三档。**

### 1.1 品牌与中性文字（用得最多）

| 旧值 | 频次 | 新值 | 用法 | 影响文件 |
|---|---|---|---|---|
| `#8c8c8c` | 21 | `var(--ink-faint)` | 标签、占位符、次要时间 | OfferList / OnboardingList / InterviewList / CandidateList / DemandList 等 |
| `#595959` | 6 | `var(--ink-soft)` | 次要正文 | CandidateList L935/L957/L963/L1004 |
| `#262626` | 2 | `var(--ink)` | 重要文字 | CandidateList L961/L992 |
| `#666` | 8 | `var(--ink-soft)` | 表单 label | DemandList L791/L1079 等 |
| `#999` | 4 | `var(--ink-faint)` | 辅助文字 | DemandList L787/L887/L914 等 |
| `#333` | 4 | `var(--ink)` | 标题/正文 | DemandList L770/L812/L870/L893 等 |
| `#bfbfbf` | 1 | `var(--ink-faint)` | 占位 | CandidateList L996 |

### 1.2 状态语义色

| 旧值 | 频次 | 新值 | 用法 |
|---|---|---|---|
| `#1890ff` | 11 | `var(--c-info)` 或 `var(--brand)`（语义判断：信息/链接走 c-info，强调/CTA 走 brand） | OfferList / DemandList / CandidateList / InterviewList 多处 |
| `#52c41a` | 7 | `var(--c-success)` | 成功状态 |
| `#ff4d4f` / `#f5222d` | 14 | `var(--c-error)` | 错误状态 |
| `#fa8c16` | 11 | `var(--c-warning)` | 警告状态 |
| `#722ed1` | 5 | `var(--brand-grad-a)` 或 `var(--c-info)` | OfferList 紫色状态 |

### 1.3 背景与分隔线

| 旧值 | 频次 | 新值 | 用法 |
|---|---|---|---|
| `#fff` / `white` | 7 | `var(--surface)`（兜底）或 `var(--glass-bg-card)`（推荐：透出极光） | DemandList L725 / CandidateList L814/L872 等 |
| `#f0f0f0` | 12 | `var(--border-hairline)` | 分隔线 |
| `#fafafa` | 10 | `var(--glass-bg-input)`（更贴合玻璃）或 `var(--surface)` | DemandList L922/L938 等 |
| `#f0f2f5` | 2 | `transparent`（让极光底透出） | DemandList L698 |
| `#e6f7ff` + `#91d5ff` | 1 | `var(--c-info-soft)` + 取消独立边框 | CandidateList L1086 |

### 1.4 滚动条

| 旧值 | 新值 | 用法 |
|---|---|---|
| `#d9d9d9` | `var(--ink-faint)` | `index.css` 滚动条 |
| `#bfbfbf` | `var(--ink-faint)` | 滚动条 hover |

### 1.5 body 底色（暗色兼容）

```diff
- /* index.css L17-23 */
  body {
    font-family: ...;
    -webkit-font-smoothing: antialiased;
-   background-color: #f5f5f5;
+   background: transparent;   /* 让 tokens.css 的 --aurora-base 生效 */
-   color: rgba(0, 0, 0, 0.88);
+   color: var(--ink);
  }
```

---

## 二、尺寸替换映射（硬编码 px → tokens.css v2）

### 2.1 font-size（401 处）

| 旧值 | 新 token | 用法 |
|---|---|---|
| `32px` | `var(--text-h1)` | 页面 H1 |
| `24px` | `var(--text-h2)` | 区块 H2 |
| `22px` | `var(--text-h2)` | StatCard 数值（**注意** StatBar 已用 24/20/16，与 OfferList 22 冲突——统一为 `--text-h2`） |
| `20px` | `var(--text-h3)` | 卡片标题 |
| `18px` | `var(--text-h3)` | 数值/次级标题 |
| `16px` | `var(--text-h4)` | 子标题 |
| `15px` | `var(--text-body)` | 正文（15=0.9375rem） |
| `14px` | `var(--text-body)` | 正文（部分页 14 应统一） |
| `13px` | `var(--text-small)` | 次要文字 |
| `12px` | `var(--text-meta)` | 辅助/标签 |
| `11px` | `var(--text-meta)` | 极小（仅少数） |

### 2.2 padding（126 处）

| 旧值 | 新 token |
|---|---|
| `24px` | `var(--space-6)` |
| `20px` | `var(--space-4)` + `var(--space-2)`（16+4） |
| `16px` | `var(--space-4)` |
| `12px` | `var(--space-3)` |
| `10px` | `var(--space-2)` + `var(--space-1)`（8+2） |
| `8px` | `var(--space-2)` |
| `6px` | `var(--space-1)` + 1px |
| `4px` | `var(--space-1)` |

### 2.3 border-radius（165 处）

| 旧值 | 新 token |
|---|---|
| `9999px` | `var(--radius-pill)` |
| `20px` | `var(--radius-lg)` |
| `16px` | `var(--radius-md)` |
| `12px` | `var(--radius-md)`（**统一为 16px，主圆角**） |
| `10px` | `var(--radius-md)`（同 12，建议并入主圆角） |
| `8px` | `var(--radius-sm)`（6px）或 `var(--radius-md)` |
| `6px` | `var(--radius-sm)` |
| `4px` | `var(--radius-sm)` |
| `3px` | `var(--radius-sm)` + 边框（button kbd-hint） |

### 2.4 box-shadow（散见硬编码）

| 旧值 | 新 token |
|---|---|
| `0 1px 4px rgba(0, 0, 0, 0.04)` | `var(--shadow-xs)` |
| `0 2px 8px rgba(0,0,0,0.06)` | `var(--shadow-sm)` |
| `0 4px 16px rgba(0, 0, 0, 0.06)` | `var(--shadow-card)` |
| `0 8px 24px var(--glow-brand)` | 保留（语义正确） |
| `0 12px 32px var(--glow-brand)` | 保留 |

---

## 三、主按钮字色冲突修复（C2 / P0）

### 3.1 根因
`App.vue` L56-62 通过 `themeOverrides.Button.textColorPrimary: '#ffffff'` 设主按钮白字。
`CandidateList.vue` L856-860 用 `.add-button { color: var(--ink) !important; }` 强行覆盖。

### 3.2 修复方案

**A. 移除所有 `!important` 覆盖**（推荐）

```diff
  // CandidateList.vue L856-860
- .add-button, .batch-notify-btn, .send-btn-primary {
-   background: linear-gradient(135deg, var(--brand) 0%, var(--brand-grad-a) 100%) !important;
-   border: none !important;
-   color: var(--ink) !important;
- }
+ .add-button,
+ .batch-notify-btn,
+ .send-btn-primary {
+   background: linear-gradient(135deg, var(--brand), var(--brand-grad-a));
+   border: 1px solid rgba(255, 255, 255, .35);
+   /* 字色交给 App.vue 的 themeOverrides（#fff） */
+ }
```

**B. 若确需特殊字色，单独加 modifier 类**（如"暗背景主按钮"）

```css
.btn-primary--on-light {
  color: var(--ink); /* 用于特殊场景：白底突出文字 */
}
```

---

## 四、5 列表页响应式补丁（U1 / P0）

> 共性补丁：每个列表页 `page-container` 加 1024/768 断点。

```css
/* 统一 patch：粘到 OfferList / DemandList / OnboardingList / InterviewList / CandidateList 末尾 */
@media (max-width: 1280px) {
  .page-container { padding: var(--space-4); }
  .page-title { font-size: var(--text-h2); }
  /* 数据表开启横向滚动提示：给 n-card 加 hint */
  :deep(.n-data-table-wrapper) {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
}
@media (max-width: 768px) {
  .page-container { padding: var(--space-3); }
  .page-header { flex-direction: column; align-items: stretch; gap: var(--space-3); }
  .stats-row { grid-template-columns: repeat(2, 1fr) !important; }
  /* 表格列宽自动 */
}
@media (max-width: 480px) {
  .stats-row { grid-template-columns: 1fr !important; }
}
```

> 注：每个页 stats-row 的 `n-grid cols` 不同（4/9/4/3），上面用 `!important` 仅针对 `grid-template-columns`，不影响其他。

### 4.1 顶栏搜索框响应式补丁（PM 反馈）

> 问题：≤1024 时 `.search { flex: 1; max-width: 420px }` 会让搜索框与其他工具按钮挤在一行，触发换行/挤压，视觉混乱。

```css
/* 顶栏搜索框：所有页面统一加这一段 */
.search {
  flex: 1 1 240px;          /* 主轴弹性，基础宽度 240px */
  min-width: 200px;          /* 防止挤压到消失 */
  max-width: 420px;
  white-space: nowrap;       /* 内部文字不换行 */
  overflow: hidden;
  text-overflow: ellipsis;
}
.topbar {
  flex-wrap: wrap;           /* 极窄屏允许 wrap */
}
@media (max-width: 768px) {
  .topbar { padding: 10px var(--space-3); gap: 10px; }
  .search { flex: 1 1 100%; max-width: none; order: 10; }  /* 搜索换到第二行占满 */
  .seg { gap: 4px; }
}
@media (max-width: 480px) {
  .topbar { padding: 8px 10px; gap: 6px; }
  .toggle { font-size: 11px; padding: 4px 6px; }  /* 工具按钮缩字 */
  .seg .sw { width: 14px; height: 14px; }
}
```

### 4.2 弹窗内边距加大（PM 反馈）

> 问题：原 `.modal { padding: var(--space-6) }` (24px) 偏小，标题/正文/按钮挤在一起，视觉局促。**升级到 32px + header/body/footer 三段分区**。

```css
/* 替换 DesignTokens / glass.css 的 .modal 段 */
.modal {
  width: 480px;
  max-width: 92vw;
  padding: var(--space-8) var(--space-8) var(--space-6);   /* 32 32 24 */
  background: var(--glass-bg-elevated);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-elevated);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);                                       /* 段间距 20 */
}
.modal-header { display: flex; flex-direction: column; gap: 10px; }
.modal-body   { display: flex; flex-direction: column; gap: var(--space-4); }
.modal-footer {
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-hairline);              /* 与正文分隔 */
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}
.modal h3 { font-size: var(--text-h3); font-weight: 600; margin: 0; }
.modal p  { color: var(--ink-soft); font-size: var(--text-body); line-height: 1.6; margin: 0; }
```

> **Vue 落地**：把所有 `<n-modal>` 内容拆成 `<header>` / `<main>` / `<footer>` 三个 `<div>`，类名对齐。或在 `App.vue` 的 `n-dialog-provider` 主题 overrides 里把 modal padding 设为 `32px 32px 24px`。

### 4.3 错误页/占位页统一双列布局（PM 反馈 v2.7）

> 问题：原错误页垂直堆叠（emoji → 巨大 404 → 标题 → 描述 → 按钮），404 字号 96px + 紫蓝渐变 + emoji 悬空 + 玻璃看不到边，整体显得「飘」且孤立。**改为双列布局：左大数字右说明**，与玻璃风格调和。

```css
/* 错误页 — NotFound.vue / Forbidden.vue / Placeholder.vue 统一 */
.err-page {
  display: flex; align-items: center; justify-content: center;
  min-height: 60vh; padding: var(--space-6); text-align: left;
}
.err-card {
  padding: var(--space-8);
  display: grid; grid-template-columns: auto 1fr;
  gap: var(--space-8); align-items: center;
  max-width: 620px;
  border: 1.5px solid var(--glass-border-strong);   /* 加粗玻璃边框，否则看不到边 */
}
.err-left  { display: flex; flex-direction: column; gap: 6px; min-width: 140px; }
.err-right { display: flex; flex-direction: column; gap: var(--space-3); align-items: flex-start; }
.err-code {
  font-size: 72px; font-weight: 800; line-height: 1; margin: 0;
  letter-spacing: -.04em;
  background: linear-gradient(135deg, var(--brand) 0%,
    color-mix(in srgb, var(--brand) 40%, transparent) 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  font-feature-settings: "tnum";                   /* 等宽数字 */
}
.err-tag {
  font-size: var(--text-meta); color: var(--ink-faint);
  font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
}
.err-title { font-size: var(--text-h2); font-weight: 700; color: var(--ink); margin: 0; line-height: 1.3; }
.err-desc  { color: var(--ink-soft); font-size: var(--text-body); margin: 0; line-height: 1.7; max-width: 36ch; }
.err-actions { display: flex; gap: var(--space-3); margin-top: var(--space-3); flex-wrap: wrap; }
/* ≤560 折叠为单列居中 */
@media (max-width: 560px) {
  .err-card { grid-template-columns: 1fr; gap: var(--space-5); padding: var(--space-6); }
  .err-left, .err-right { align-items: center; text-align: center; }
  .err-code { font-size: 56px; }
}
```

**Vue 落地（NotFound.vue）**：
```vue
<template>
  <div class="err-page">
    <div class="glass-panel err-card">
      <div class="err-left">
        <h1 class="err-code">{{ status }}</h1>          <!-- 404 / 403 -->
        <span class="err-tag">{{ statusTag }}</span>    <!-- PAGE NOT FOUND / ACCESS DENIED -->
      </div>
      <div class="err-right">
        <h2 class="err-title">{{ title }}</h2>
        <p class="err-desc">{{ description }}</p>
        <div class="err-actions">
          <button class="btn btn-primary" @click="$router.replace('/dashboard')">返回工作台</button>
          <button class="btn btn-secondary" @click="$router.back()">返回上一页</button>
        </div>
      </div>
    </div>
  </div>
</template>
```

**占位页（Placeholder.vue）复用同一双列结构**，左侧 emoji + `PLACEHOLDER` tag，右侧标题 + 描述 + 开发中 + ETA + Issue + 按钮。**系统级空状态/异常态视觉一致**。

**禁止**：
- ❌ 404/403 字号超过 80px（视觉太重、与其他页失衡）
- ❌ 紫蓝撞色渐变（如原 `brand → brand-grad-a → brand-grad-b` 三色）—— 错误页必须用「品牌色透明渐变」单色系，不允许引入第二色相
- ❌ 垂直堆叠 emoji + 数字 + 标题（视觉碎片化）
- ❌ 占位页与错误页用不同布局（系统级一致性原则）

---

## 五、侧栏移动折叠（U2 / P0）

### 5.1 方案
- `< 768px` 侧栏默认隐藏
- 顶栏左侧加汉堡按钮 → 触发侧栏滑出（用 `n-drawer placement="left"` 而非 n-layout-sider）

### 5.2 实现要点（Layout.vue）

```diff
  <template>
    <div class="app-layout">
+     <!-- 移动端汉堡按钮 -->
+     <button
+       v-if="isMobile"
+       class="hamburger-btn glass-input"
+       aria-label="打开菜单"
+       @click="mobileMenuOpen = true"
+     >☰</button>
+
-     <n-layout-sider v-if="menuLayout === 'side'" ...>
+     <!-- 桌面端：n-layout-sider 玻璃侧栏 -->
+     <n-layout-sider v-if="menuLayout === 'side' && !isMobile" ...>
        ...
      </n-layout-sider>
+
+     <!-- 移动端：n-drawer 侧栏 -->
+     <n-drawer
+       v-if="menuLayout === 'side'"
+       v-model:show="mobileMenuOpen"
+       :width="280"
+       placement="left"
+     >
+       <n-menu :options="menuOptions" :value="selectedKey" @update:value="onDrawerMenu" />
+     </n-drawer>
```

```ts
// script
const isMobile = ref(window.innerWidth < 768)
const mobileMenuOpen = ref(false)
function onDrawerMenu(key: string) {
  router.push(key)
  mobileMenuOpen.value = false
}
window.addEventListener('resize', () => {
  isMobile.value = window.innerWidth < 768
})
```

```css
<style scoped>
.hamburger-btn {
  position: fixed;
  top: var(--space-3);
  left: var(--space-3);
  z-index: var(--z-header);
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  backdrop-filter: blur(var(--glass-blur-input));
  cursor: pointer;
}
</style>
```

---

## 六、暗色模式硬编码清扫（U4-U5 / P0）

> 策略：**只删不改**：把硬编码色删掉，依赖 `.n-card.n-card` / `.glass-*` / tokens.css 变量自动接管。
> 唯一例外：业务页内手工绘制的「次要容器」（如 DemandList `.demand-card` 白色背景）需换成 `var(--glass-bg-card)`。

```diff
  /* DemandList.vue L725 */
- .demand-card { background: white; ... }
+ .demand-card { background: var(--glass-bg-card); border: 1px solid var(--glass-border); ... }
```

```diff
  /* CandidateList.vue L872 */
- .candidate-row { background: #fff; ... }
+ .candidate-row { background: var(--glass-bg-card); border: 1px solid var(--glass-border); ... }
```

```diff
  /* DemandList.vue L698 */
- .demand-container { background: #f0f2f5; ... }
+ .demand-container { background: transparent; ... } /* 让极光透出 */
```

---

## 七、404 错误页 + 错误态兜底（U11 / P0）

### 7.1 新增 `pages/NotFound.vue`

```vue
<template>
  <div class="not-found">
    <div class="app-aurora"><div class="aurora-spot"></div></div>
    <div class="glass-panel nf-card">
      <div class="nf-emoji">🗺️</div>
      <h1 class="gradient-title">404</h1>
      <p class="nf-text">您访问的页面不存在或已被移除</p>
      <div class="nf-actions">
        <button class="btn-primary" @click="$router.replace('/dashboard')">返回首页</button>
        <button class="btn-secondary" @click="$router.back()">返回上一页</button>
      </div>
    </div>
  </div>
</template>
```

### 7.2 router/index.ts

```diff
+ {
+   path: '/404',
+   name: 'NotFound',
+   component: () => import(/* webpackChunkName: '404' */ '../pages/NotFound.vue')
+ },
  {
    path: '/:pathMatch(.*)*',
-   redirect: '/dashboard'
+   redirect: '/404'
  }
```

### 7.3 API 错误兜底（main.ts）

```diff
  axios.interceptors.response.use(
    (resp) => resp,
    (err) => {
      const status = err?.response?.status
      const url = err?.config?.url ?? '<unknown>'
+     const message = useMessage()
      if (status === 404) {
        console.warn(`[API 404] ${url}`)
+       message?.warning(`接口不存在：${url.split('?')[0]}`)
      } else if (status === 500) {
        console.error(`[API 500] ${url}`, err?.response?.data)
+       message?.error('服务异常，请稍后再试')
      } else if (status === 401) {
+       // 触发 logout（已有逻辑，保留）
      }
      return Promise.reject(err)
    }
  )
```

> 注：useMessage 需在 axios 拦截器外层提前创建 —— 推荐改为：在 main.ts 创建独立的 `discreteApi` 工具，全局可用。

---

## 八、强调色规范统一（I2 / P1）

```diff
  /* I2: StatBar 的 4 色是好的范例（语义四态）。
     Dashboard matter-tab__count 走 brand 不一致——改成 brand-soft 只用于"通用未读"，状态计数走 --c-* */
- .matter-tab__count {
-   background: var(--brand-soft);
-   color: var(--brand);
- }
+ .matter-tab__count {
+   background: var(--c-info-soft);  /* 信息/未读 = info */
+   color: var(--c-info);
+ }
+ .matter-tab__count--urgent {
+   background: var(--c-error-soft);
+   color: var(--c-error);
+ }
```

---

## 九、空状态与加载态收口（I5 / U9 / P1）

```vue
<!-- 推荐统一 EmptyState 用法 -->
<EmptyState
  icon="📋"  <!-- 后续替换为 <n-icon :component="..."/> -->
  title="暂无候选人"
  description="当前筛选下没有匹配的候选人，您可以尝试调整筛选条件"
  actionLabel="清除筛选"
  @action="clearFilters"
/>
```

```diff
  /* 散落的 n-empty 替换为 EmptyState 组件 */
- <n-empty description="暂无需求数据">
-   <template #extra><n-button type="primary">创建需求</n-button></template>
- </n-empty>
+ <EmptyState
+   icon="📋"
+   title="暂无需求数据"
+   description="创建第一个需求开始招聘流程"
+   actionLabel="创建需求"
+   @action="handleCreate"
+ />
```

---

## 十、关键操作二次确认（U12 / P1）

```diff
  /* OfferList.vue handleTransition() L255 */
- async function handleTransitionSubmit() {
-   if (...) { message.warning('请填写原因'); return }
-   transitionModal.value.loading = true
-   try {
-     await transitionOffer(...)
-     message.success('状态已更新')
-     ...
+ async function handleTransitionSubmit() {
+   if (...) { message.warning('请填写原因'); return }
+   // ★ 二次确认：危险状态（REJECTED / WITHDRAWN / EXPIRED / CANCELLED）
+   const dangerStates = ['REJECTED', 'WITHDRAWN', 'EXPIRED']
+   if (dangerStates.includes(transitionModal.value.form.to)) {
+     try {
+       await dialog.warning({
+         title: '确认操作',
+         content: `将 Offer 状态变更为「${OFFER_STATUS_LABEL[transitionModal.value.form.to]}」，是否继续？`,
+         positiveText: '确认',
+         negativeText: '取消',
+       })
+     } catch { return } // 用户取消
+   }
+   transitionModal.value.loading = true
    ...
  }
```

> `useDialog` 已在 App.vue 的 `n-dialog-provider` 注册，直接 `import { useDialog } from 'naive-ui'` 即可。

---

## 十一、占位页差异化（I7 / F1 / P1）

```vue
<!-- Placeholder.vue 改造 -->
<template>
  <div class="placeholder-page">
    <div class="glass-panel placeholder-card">
      <div class="placeholder-icon">{{ icon }}</div>
      <h2 class="placeholder-title">{{ title }}</h2>
      <p class="placeholder-desc">{{ description }}</p>
      <div class="placeholder-meta">
        <n-tag type="info" size="small">开发中</n-tag>
        <span class="placeholder-eta">{{ eta }}</span>
      </div>
      <n-button type="primary" @click="$router.replace('/dashboard')">返回工作台</n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
const meta = computed(() => ({
  '/settings/onboarding': { icon: '👋', title: '入职设置', desc: '员工入职流程配置', eta: '预计 Q4 上线' },
  '/settings/approval': { icon: '📋', title: '审批设置', desc: '审批流配置', eta: '预计 Q4 上线' },
  '/settings/external': { icon: '🔌', title: '对外接口', desc: '第三方系统对接配置', eta: '待规划' },
  '/settings/public': { icon: '🌐', title: '公共设置', desc: '公开页面配置', eta: '待规划' },
  '/report': { icon: '📊', title: '数据中心', desc: '招聘数据报表与分析', eta: '规划中' },
}[route.path] || { icon: '🚧', title: '页面建设中', desc: '', eta: '待规划' }))
</script>
```

---

## 十二、入场动效扩展（I4 / P1）

```diff
  /* tokens.css 已有 wb-fade-up 动画 + .workbench-card 类（6 级 stagger）。
     给所有 List 页 .page-container 加 fade-up：*/
+ .page-container {
+   animation: wb-fade-up var(--duration-slow) var(--ease-out) both;
+ }
```

---

## 十三、面包屑（F6 / P1）

```vue
<!-- 新增 components/common/Breadcrumb.vue -->
<template>
  <n-breadcrumb v-if="crumbs.length > 1" class="ats-breadcrumb">
    <n-breadcrumb-item v-for="c in crumbs" :key="c.path" @click="$router.push(c.path)">
      {{ c.label }}
    </n-breadcrumb-item>
  </n-breadcrumb>
</template>
```

挂到 Layout.vue 顶栏 `Header` 下沿（route 变化时 `crumbs` 自动重算）。

---

## 十四、表格行键盘可达（I1 / P1）

```vue
<!-- n-data-table 自定义 row-class + @row-props -->
<n-data-table
  :columns="columns"
  :data="dataSource"
  :row-props="rowProps"
/>

<script setup>
function rowProps(row: any) {
  return {
    tabindex: 0,
    role: 'button',
    'aria-label': `${row.name} 详情`,
    onKeydown: (e: KeyboardEvent) => {
      if (e.key === 'Enter') router.push(`/candidates/${row.id}`)
    },
    style: 'cursor: pointer',
    onClick: () => router.push(`/candidates/${row.id}`),
  }
}
</script>
```

---

## 十五、键盘快捷键扩展（I10 / P2）

```ts
// composables/useShortcuts.ts（新增）
export function useShortcuts() {
  const router = useRouter()
  const onKey = (e: KeyboardEvent) => {
    // '/' 聚焦搜索
    if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) {
      e.preventDefault()
      document.querySelector<HTMLElement>('.layout-header__search-trigger')?.click()
    }
    // 'g d' 跳工作台（g 后 1.5s 内按 d）
    // '?' 打开帮助
  }
  onMounted(() => window.addEventListener('keydown', onKey))
  onUnmounted(() => window.removeEventListener('keydown', onKey))
}
```

---

## 十六、滚动条暗色样式（U7 / P2）

```diff
  /* index.css L38-51 */
- ::-webkit-scrollbar-thumb {
-   background: #d9d9d9;
- }
- ::-webkit-scrollbar-thumb:hover {
-   background: #bfbfbf;
- }
+ ::-webkit-scrollbar-thumb {
+   background: var(--ink-faint);
+ }
+ ::-webkit-scrollbar-thumb:hover {
+   background: var(--ink-soft);
+ }
+ body.dark ::-webkit-scrollbar-thumb {
+   background: rgba(255, 255, 255, .18);
+ }
+ body.dark ::-webkit-scrollbar-thumb:hover {
+   background: rgba(255, 255, 255, .28);
+ }
```

---

## 十七、SettingsLayout 去 hack（F4 / P1）

策略：把 `:deep` 一次性覆盖的样式下沉到 `glass.css` 的 `.n-card.n-card` 全局规则（已落）+ 各子页面 header 渐变用 `glass.css` 提供 `.gradient-title`（已落）。

```diff
  /* SettingsLayout.vue L391-515 整段删除 */
- /* ① page-title 渐变文字 ... */
- .settings-content :deep(.page-title),
- .settings-content :deep(.page-header h2),
- .settings-content :deep(.policy-admin__title) { ... }
- /* ② n-card 卡片头玻璃化 ... */
- /* ③ n-tabs 透明导航 ... */
- /* ④ filter-row / stats-row 玻璃面板 ... */
- /* ⑤ n-button type="primary" 升级为渐变按钮 ... */
```

保留 `.settings-sider` / `.settings-menu` / `.menu-item` 自身导航样式（这部分是功能代码不是 hack）。

---

## 十八、Mock 数据真实性（U10 / P1）

```diff
  /* CandidateList.vue L644-647 */
- { key: '4', name: '张三', id: 'CDD005878', gender: '男', age: 8, education: '本科', experience: '1年', ... }
+ { key: '4', name: '张三', id: 'CDD005878', gender: '男', age: 28, education: '本科', experience: '5年', ... }
```

---

## 十九、完整改造顺序（与 V2 诊断报告 §七 一一对应）

| 阶段 | 工作量 | 解决问题 | 关键 commit |
|---|---|---|---|
| **1** 全局 token 强制 | 0.5 人日 | U6/C4/U7 | `fix(global): body 透极光 · 滚动条 token化` |
| **2** 业务页硬编码颜色全替换 | 0.5 人日 | C1/C14/U4/U5/A1 | `refactor(list): 99 处 Ant 色 → tokens v2` |
| **3** 列表页响应式 + 侧栏移动折叠 | 1.0 人日 | U1/U2/U3 | `feat(responsive): 5 列表页 1024/768 断点 + 移动侧栏 drawer` |
| **4** 框架组件对齐 | 1.0 人日 | C2/C3/C11/I2/I3 | `refactor(button): 主按钮字色修复 · 表头玻璃 · 操作列瘦身` |
| **5** 交互增强 | 1.0 人日 | F1/F6/I1/I4/I7/U12/A5 | `feat(ux): 面包屑+入场动效+键盘+占位差异化+二次确认` |
| **6** 错误态与 a11y | 0.5 人日 | F2/F3/U11/A1/A4 | `feat(error): NotFound页 + 全局 axios message` |
| **7** SettingsLayout 去 hack | 0.5 人日 | F4/F5/C12 | `refactor(settings): 去 :deep 注入 · 弹窗 token化` |
| **8** 持续打磨 | 持续 | P2 | `chore: a11y/快捷键/toast 规范` |

**总计：5–6 人日可解 9 个 P0 + 11 个 P1（占 64%）**。

---

## 二十、验证清单

每个阶段交付前必跑：

```bash
cd /Users/loki/WorkBuddy/招聘助手/ATS-NEW/web/app

# 1. 类型 + 构建
npm run build

# 2. ESLint 零警告
npm run lint:ci

# 3. 单元测试
npm run test

# 4. 启动 dev，访问 http://localhost:5212
npm run dev
# - 工作台 / 候选人列表 / Offer / 需求 / 面试 / 待入职 / 设置 7 个页面逐一视觉回归
# - 切换暗色模式，5 列表页不能出现"白色卡片漂浮"
# - 切换品牌色（ThemeSettings 取色器），所有页面联动
# - 移动端 DevTools（<768px）侧栏折叠为 drawer
# - 模拟输错 URL（如 /xxx）跳 404 页而非 dashboard

# 5. e2e
npm run e2e
```

**禁止**：
- 直接 `git push --force`
- 提交未跑 `npm run build` 的代码
- 在 SettingsLayout 重新加 `:deep` 注入（已记录的 hack）