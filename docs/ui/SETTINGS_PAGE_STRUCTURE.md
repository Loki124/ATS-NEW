# 设置页统一页面结构规范（Settings Page Structure Standard）


版本：v1.0 · 生效日期：2026-08-24
适用范围：web/app/src/pages/settings/** 下所有页面（含 permission 子模块）
配套文档：UI_DESIGN_SPEC.md（设计令牌）、UI_REMEDIATION_PLAN.md（整改方案）、UI_COMPLIANCE_REPORT.md（审查报告）
范本来源：本次 CampusControl.vue 与 DataDictionary.vue 对齐统一后的产物

## 0. 一句话原则

外壳（Shell）由 SettingsLayout.vue 统一注入，页面只写内容。任何设置页不得自绘极光、不得私有覆盖 .page-title/.page-subtitle、不得持有与 glass.css 重复的视觉定义。

## 1. 页面外壳（已经由框架提供，页面无需关心）

SettingsLayout.vue
├── .settings-aurora        ← 极光光斑背景（全局唯一，暗色同步）
└── .settings-scroll        ← 内容容器（padding 20px，承载所有页面）
    └── <router-view/>      ← 你的页面根
        └── .page-container ← 页面自身根（padding 由外壳清零，见 §2）

- 极光：全局 .settings-aurora 注入，页面内禁止再写 .cc-aurora / .blob-* 之类的私有极光。
- 滚动：由 .settings-scroll 外层 + .n-scrollbar-container 内层承担，页面根不要自己 overflow-y:auto 抢滚动（除非确有局部滚动需求，如 DataDictionary 的列表模式）。

## 2. 页面根：.page-container

| | |
|---|---|
|根元素|`<div class="page-container">`|全局类，已定义 padding:24px; min-height:100%|
|在 .settings-scroll 内|padding 被清零（SettingsLayout.vue:269 :deep(.page-container){padding:0}）|间距由外壳 20px 提供，无需页面再补|
|布局模式|默认 block 流（标题→KPI→工具条→表格→弹窗）|多 tab 看板等需要纵向撑满的，见 §5|
|禁止|自写 height:100%、私有 .cc-page、再包一层 .page-container|破坏外壳间距|


DataDictionary 因列表模式需自身纵向滚动，保留了 scoped .page-container{display:block !important; padding-bottom:120px} —— 这是唯一允许的例外，且仍复用全局 .page-container 类名而非私有类。

## 3. 标题区：.page-header > .page-title + .page-subtitle

```html
<div class="page-header">
  <div>
    <h1 class="page-title">页面名称</h1>
    <p class="page-subtitle">一句话说明本页用途 / 关键约束</p>
  </div>
  <!-- 右上角主操作按钮（可选） -->
  <n-button type="primary" @click="...">主操作</n-button>
</div>
```

| | | |
|---|---|---|
|.page-title|26px 渐变标题（background-clip:text + --brand 渐变）|glass.css .page-title { font-size:26px !important; ... }|
|.page-subtitle|--ink-soft 次级文字，无需私有覆盖|glass.css .page-subtitle|
|位置|页面顶部，吸顶（.settings-scroll .page-header 已 sticky）|glass.css sticky 规则|
|底部通栏分隔线|由全局 margin: 0 -20px 16px -20px; border-bottom: 1px solid var(--glass-border) 提供|glass.css sticky 规则|
|禁止|scoped 里写 .page-title{font-size:22px}、.page-subtitle{color:#888} 等覆盖|破坏全局渐变规格一致性（DataDictionary 原 bug 已修复）|
|禁止|scoped 里写 .page-header { margin-bottom: 16px }|会覆盖全局负 margin，导致底部分隔线不能通栏（DataDictionary 原 bug 已修复）|


⚠️ 历史债：此前多页在 scoped 里把标题写成 22/24px 纯色，违反统一规格。新增页面一律禁止，存量页按本规范逐步清退。

## 4. KPI / 工具条 / 表格（全局类直接复用）

| | | |
|---|---|---|
|KPI 行|.kpi-row > .kpi-card|auto-fit 自适应列数，无边框融入玻璃|
|工具条|`<div class="toolbar">`|flex 行，左控件 + .spacer + 右按钮|
|主按钮渐变|class="gradient-btn" 或 `<n-button type="primary">`|全局 .gradient-btn / .settings-scroll .n-button--primary-type|
|表格容器|`<div class="table-wrap">` 包裹 `<n-data-table>`|全局 .table-wrap 提供 flex 填充 + 滚动链 + 圆角|
|表格滚动|由 .n-scrollbar-container 承担|页面不要给 .table-wrap 再写 scoped 滚动规则（CampusControl 原重复定义已删除）|

工具条正确写法（不要再用 `<n-card class="toolbar">` 包裹）：

```html
<div class="toolbar">
  <n-input v-model:value="kw" placeholder="搜索" clearable style="width: 360px" />
  <n-select v-model:value="filter" :options="opts" style="width: 160px" />
  <div class="spacer"></div>
  <n-button type="primary" class="gradient-btn" @click="add">+ 新增</n-button>
</div>
```

## 5. 多 tab 看板（CampusControl 范式）

当页面是「一个玻璃面板内嵌 n-tabs，每个 tab 各自滚动」时：

```html
<div class="page-container">
  <div class="page-header"> ... </div>
  <div class="glass-panel">                <!-- 全局玻璃类 + scoped 仅补 flex 撑满 -->
    <n-tabs v-model:value="active" type="line" class="cc-tabs">
      <n-tab-pane name="a" tab="看板 A">
        <div class="toolbar"> ... </div>
        <div class="kpi-row"> ... </div>
        <div class="table-wrap"> <n-data-table .../> </div>
      </n-tab-pane>
      ...
    </n-tabs>
  </div>
</div>
```

scoped 仅需保留三条布局链（视觉全走全局）：

```css
/* 页面根必须是 flex 列，否则 .glass-panel 的 flex:1 无法撑高，表格会折叠 */
.page-container { display: flex; flex-direction: column; min-height: 100%; }

/* .glass-panel 作为内容根时撑满高度（全局类无 flex，这里补布局） */
.glass-panel { display: flex; flex-direction: column; flex: 1; min-height: 0; padding: var(--space-4); }

/* tabs 在玻璃面板内纵向撑满，每个 pane 内部自行滚动 */
.cc-tabs { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.cc-tabs :deep(.n-tabs-nav) { background: transparent; }
.cc-tabs :deep(.n-tabs-pane-wrapper),
.cc-tabs :deep(.n-tab-pane) { flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
```


⚠️ 坑点：.page-container 全局默认是 block 流。多 tab 玻璃面板页若不补 display:flex; flex-direction:column，.glass-panel flex:1 会失效，导致 .table-wrap 及 n-data-table body 高度塌陷，数据行被"折叠"。

## 6. 弹窗（全局类统一，页面零样式）

所有 n-modal（preset="card"）自动获得：页面居中、最大高度 90vh、超出内部滚动、去边框。

```html
<n-modal
  v-model:show="show"
  preset="card"
  title="标题"
  :bordered="false"
  :segmented="{ content: true, footer: true }"
  style="width: 620px; max-width: 94vw"
>
  ... 表单 ...
</n-modal>
```

- 禁止页面再写 .rule-modal/.import-modal/.dim-modal 之类的居中/滚动 scoped 规则（CampusControl 原重复定义已删除）。
- 仅「密集表单的紧凑间距微调」允许保留（如 CampusControl 的 .batch-modal 紧凑 padding），且不得改变玻璃/圆角/滚动语义。

## 7. 自检清单（新增/修改设置页必过）

- [ ] 根元素是 `<div class="page-container">`（非私有 .cc-page/.xxx-page）
- [ ] 页面内没有 .cc-aurora / .blob-* 极光（由外壳提供）
- [ ] 标题用 .page-header > .page-title + .page-subtitle，scoped 无 .page-title/.page-subtitle 字号/颜色覆盖
- [ ] 工具条是 `<div class="toolbar">`（非 `<n-card class="toolbar">`）
- [ ] 表格包在 `<div class="table-wrap">` 内，scoped 无 .table-wrap 重复定义
- [ ] 弹窗用 n-modal preset="card" + :bordered="false"，scoped 无居中/滚动重复定义
- [ ] KPI 用 .kpi-row > .kpi-card，未私有重定义无边框样式
- [ ] 主按钮用 gradient-btn 或 type="primary"，未私有重定义渐变
- [ ] 暗色验证：切换 body.dark，极光/玻璃/标题渐变/表格滚动均正常

## 8. 本次落地改动（2026-08-24）

| | |
|---|---|
|CampusControl.vue|模板：.cc-page→.page-container、删 .cc-aurora 极光块、.cc-header/title/subtitle→.page-header/title/subtitle；scoped：删 .cc-page/.cc-aurora/.blob*/.cc-header/.cc-title/.cc-subtitle、删与全局重复的 .table-wrap/.toolbar/.gradient-btn/.kpi-*、删 .import/.dim/.rule-modal 冗余弹窗规则；保留 .glass-panel flex 撑满 + .cc-tabs 布局链 + .batch-modal 紧凑微调 + .drawer-footer|
|DataDictionary.vue|模板：`<n-card class="toolbar">`→`<div class="toolbar">`；scoped：删 .page-title{22px} / .page-subtitle{#888} 覆盖以复用全局渐变规格；保留 .page-container 列表模式自身滚动例外|
|glass.css（已在前期阶段 F 落地）|.table-wrap、.n-modal .n-card 居中滚动、.settings-scroll 表格玻璃化等全局化，作为本规范的单一事实来源|


验证：vite build 通过（exit 0），dev server localhost:5212 返回 200，HMR 已生效。
