# 设置页统一页面结构规范（Settings Page Structure Standard）


版本：v1.1 · 生效日期：2026-08-24 · 修订：2026-08-27（补「模型 B 三件套」合法变体，取消 height:100% 禁止；KPI 令牌铁律 + 强调变体）
适用范围：web/app/src/pages/settings/** 下所有页面（含 permission 子模块）
配套文档：UI_DESIGN_SPEC.md（设计令牌）、UI_REMEDIATION_PLAN.md（整改方案）、UI_COMPLIANCE_SELFCHECK.md（审查报告 + 交付前自检矩阵，已合并原 REPORT）
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
|禁止|私有 .cc-page、再包一层 .page-container|破坏外壳间距|

> **布局模型二选一（均为合法，禁止混用同一页的两种滚动职责）**：
> - **模型 A · 默认 block 流（标题→KPI→工具条→表格→弹窗）**：`.page-container` 不写 `height`；整页在 `.settings-scroll` 内滚动，`.page-header` 靠全局 `sticky` 吸顶。
> - **模型 B · 固定标题 + 内部滚动三件套**：`.page-container { display:flex; flex-direction:column; height:100%; min-height:0 }`，配合 `.page-header { flex-shrink:0 }` + `.page-body { flex:1; min-height:0; overflow-y:auto; overflow-x:hidden }`。标题固定不滚，内容区自己滚，与外层 `.settings-scroll` 滚动职责分离。
>
> ⚠️ **历史修订（2026-08-27）**：规范 v1.0 曾把「自写 height:100%」列为禁止项，但模型 B 是 2026-08-24 与 `AccountSettings`/`DemandConfig` 同期落地的成熟模式，已被 17 个设置页采用（视觉/交互均正常）。故取消该禁止，将模型 B 列为合法变体。两种模型下，`.page-header` 的底部分隔线都由全局 `.settings-scroll .page-header`（glass.css sticky 块）提供：`border-bottom: 1px solid var(--glass-border)` + `margin: 0 0 var(--space-4) 0`，无需页面处理。**header 与首块内容的间距唯一来源见下方红线「间距唯一来源」。**

### 2.1 模型 B 三件套（固定标题 + 内部滚动）

适用：内容区需要独立滚动、且希望标题/操作按钮始终可触达的页面（如带多级表单、长列表的 CRUD 页）。

```html
<div class="page-container">          <!-- scoped 补 flex + height:100% -->
  <div class="page-header"> ... </div> <!-- flex-shrink:0，固定 -->
  <div class="page-body">              <!-- flex:1; 自己滚 -->
    <!-- KPI / 工具条 / 表格 / 表单 -->
  </div>
</div>
```

scoped 仅需：

```css
.page-container { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.page-header { flex-shrink: 0; }
.page-body  { flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden;
             display: flex; flex-direction: column; gap: 16px; }
/* 顶部留白由外层 .settings-scroll 的 padding:20px 统一提供，.page-body 不再单独加 padding-top */
```

> 模型 B 下 `.page-header` 是 `flex-shrink:0` 固定（非 sticky），但因为 `.page-body` 自己滚，标题视觉上始终可见，效果等同吸顶。

### ⚠️ 强制校验项（红线）

- **`.page-body` 禁止声明 `padding` / `padding-top`**。顶部留白统一由外层 `.settings-scroll` 的 `padding: 20px` 提供（见 §2.1）。在 `.page-body` 上加 `padding-top` 会与 `.settings-scroll` 叠出多余顶部间隙，且与该规范唯一的模型 A 参考页（校招管控）顶部间距不一致。
- 反例：`padding-top: 8px`（commit `12c6ece` 引入，已在 `50c5341` + `7ec00af` 清除，涉及 RecruitmentStage/Process/Round、AccountSettings、DemandConfig、CompanyLibrary、SchoolLibrary、ProcessStageEditor、DataDashboard、CompanySettings、PermissionManagement、FieldAclSettings、DepartmentManagement、MouManagement、DynamicFieldSettings、ProcessStageRules、ScoringRules、UserManagement）。
- 若某页确实需要在 header 与首块内容间加间距：在 `.page-header` 之下第一块内容（如 `.toolbar` / `.glass-panel`）上加 `margin-top`，**不要**动 `.page-body` 的 `padding`。
- 自检：新增/修改设置页时，`grep -Pzo '\.page-body[\s\S]*?padding' <file>` 应无命中（`.page-body` 块内不得含任何 `padding` 声明）。

### ⚠️ 红线：间距唯一来源（2026-09-18 新增，兵哥反馈「header 与内容间多余空带」）

**header 与首块内容（Tab 导航 / 工具条 / 卡片）之间的间距，只允许有一个来源，禁止 margin 与 flex gap 叠加。**

- **事实结构**：全部设置页的 `.page-header` 都写在 `.page-body` **内部**（de-facto 结构，非 §2.1 模板中的兄弟结构），而 `.page-body` 普遍为 `display:flex; flex-direction:column; gap:16px`。
- **叠加成因**：全局 `.settings-scroll .page-header` 自带 `margin-bottom: var(--space-4)`（16px），与 `.page-body` 的 `gap:16px` 相加 = **32px 空带**（CodeTableLibrary 截图实锤）。
- **根治规则（已落 glass.css，全局单点，禁止页面私有重写）**：

  ```css
  /* header 为 .page-body 直接子元素时，间距由 gap 独家提供，margin-bottom 清零 */
  .settings-scroll .page-body > .page-header { margin-bottom: 0; }
  ```

  兄弟结构（§2.1 标准模板，header 在 `.page-body` 外）无 `.page-body` 父级，仍走全局 margin，不受影响。header 的 `sticky / border-bottom / padding` 均保留，分隔线契约不破坏。
- **页面级红线**：
  - `.page-header` 在 `.page-body` 内时，scoped **禁止**再写 `.page-header { margin-bottom }`（会重新叠加）；
  - 想加大 header 与首块的间距 → 调 `.page-body` 的 `gap` 或给首块加 `margin-top`，**不要**动 header 的 margin。
- **自检**：设置页渲染后，header 底边到首个内容块顶边的实测距离必须等于 `.page-body` 的 `row-gap`（16px），不允许多出任何一个 margin 值。运行时取证：`getComputedStyle(header).marginBottom === '0px'` 且 `getComputedStyle(pageBody).rowGap === '16px'`。
- **反例（已根治）**：CodeTableLibrary.vue 首版 header margin-bottom 16px + gap 16px = 32px 空带（2026-09-18 兵哥截图反馈，glass.css 全局子选择器规则修复，运行时实测 `actualPixelGap=16` 通过）。

DataDictionary 因列表模式需自身纵向滚动，保留了 scoped `.page-container{display:block !important; padding-bottom:120px}` —— 这是模型 A 的特例（block 流 + 自身 overflow），仍复用全局 `.page-container` 类名而非私有类，合规。

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
|位置|页面顶部。模型 A 下靠全局 `sticky` 吸顶；模型 B 下靠 `.page-header{flex-shrink:0}` 固定（视觉等同吸顶）|glass.css sticky / 模型 B flex|
|底部通栏分隔线|由全局 margin: 0 -20px 16px -20px; border-bottom: 1px solid var(--glass-border) 提供（两种模型均生效）|glass.css sticky 规则|
|禁止|scoped 里写 .page-title{font-size:22px}、.page-subtitle{color:#888} 等覆盖|破坏全局渐变规格一致性（DataDictionary 原 bug 已修复）|
|禁止|scoped 里写 .page-header { margin-bottom: 16px }|会覆盖全局负 margin，导致底部分隔线不能通栏（DataDictionary 原 bug 已修复）|


⚠️ 历史债：此前多页在 scoped 里把标题写成 22/24px 纯色，违反统一规格。新增页面一律禁止，存量页按本规范逐步清退。

### 3.1 吸顶 header 玻璃磨砂（禁止纯透明 sticky）

**规则（2026-09-16 兵哥截图复现「滚动穿透重叠」后新增）**：所有设置页的吸顶 header（`.page-header` / `.cc-header` / `.n-page-header` / `.policy-admin__header`，由全局 `.settings-scroll .page-header`（glass.css）统一 sticky 注入），**必须带玻璃磨砂底，禁止纯透明 sticky**。

- **根因**：初版为「让极光直接透出」故意不给背景（纯透明 + sticky）。滚动时下方 `n-tabs` / 筛选行 / 表格内容从 header 背后穿过、与标题文字重叠，视觉错乱（静态数据页截图实锤）。
- **修复（已落 glass.css，全局单点，禁止页面私有重写）**：

  ```css
  .settings-scroll .page-header,
  .settings-scroll .cc-header,
  .settings-scroll .n-page-header,
  .settings-scroll .policy-admin__header {
    position: sticky; top: 0; z-index: 10;
    /* 玻璃磨砂底：极光仍半透透出，但 blur 遮断滚过的文字，杜绝穿透重叠 */
    background: var(--glass-bg-panel);
    -webkit-backdrop-filter: blur(var(--glass-blur-panel));
    backdrop-filter: blur(var(--glass-blur-panel));
    border-bottom: 1px solid var(--glass-border);
    margin: 0 0 var(--space-4) 0;
    padding: var(--space-4) 0 var(--space-1) 0;
  }
  ```

- **玻璃类铁律**：`backdrop-filter` 必须同时带 `-webkit-backdrop-filter` 前缀 + 不透明兜底（`< 1 的 rgba` 已由 `--glass-bg-panel` 提供），三者缺一则 fallback 失效，老 Safari / 部分内核仍会穿透。
- **页面级红线**：
  - scoped **禁止**写 `.page-header { background: transparent }` / 去掉 `backdrop-filter`（会重新触发穿透）；
  - scoped **禁止**把吸顶 header 改成 `position: fixed`（fixed 脱离滚动流，与 `.settings-scroll` 外壳冲突）。
- **自检**：滚动页面后，吸顶 header 下方内容滚过时**不得**出现文字穿透到标题区。运行时取证：吸顶态下 `getComputedStyle(header).backdropFilter` 含 `blur(...)` 且 `backgroundColor` 为半透明 rgba（非 `rgba(0, 0, 0, 0)`）；header 之下首个内容块的 `getBoundingClientRect().top` 必须 `≥` header 底边（无重叠）。
- **反例（已根治）**：静态数据页（CodeTableLibrary）初版纯透明 sticky，滚动时 n-tabs / 筛选行穿透重叠（2026-09-16 兵哥截图反馈，glass.css 玻璃磨砂底修复）。

## 4. KPI / 工具条 / 表格（全局类直接复用）

| | | |
|---|---|---|
|KPI 行|.kpi-row > .kpi-card（全局无边框玻璃卡）|auto-fit 自适应列数，无边框融入玻璃|
|KPI 强调变体（可选）|.kpi-card.kpi-card--accent|需强调的看板卡；**必须用 CSS 变量**（如 `background: linear-gradient(135deg, var(--brand-tint), var(--brand-soft))`），禁止硬编码 hex|
|工具条|`<div class="toolbar">`|flex 行，左控件 + .spacer + 右按钮|
|主按钮渐变|class="gradient-btn" 或 `<n-button type="primary">`|全局 .gradient-btn / .settings-scroll .n-button--primary-type|
|表格容器|`<div class="table-wrap">` 包裹 `<n-data-table>`|全局 .table-wrap 提供 flex 填充 + 滚动链 + 圆角|
|表格滚动|由 .n-scrollbar-container 承担|页面不要给 .table-wrap 再写 scoped 滚动规则（CampusControl 原重复定义已删除）|

> ⚠️ **KPI 令牌铁律**：`.kpi-card` / `.kpi-value` / `.kpi-label` 禁止私有重定义，更禁止硬编码 hex（`#4f46e5` / `#6b7280` 等）——会破坏暗色变量集切换。强调卡只能走 `.kpi-card--accent` + CSS 变量。当前 `DataDashboard.vue` 的渐变 KPI 仍用 `<n-card class="kpi-card" embedded>` + 私有渐变 + 硬编码 hex，已于 2026-08-27 续修复——DataDashboard 改用全局 `.kpi-card.kpi-card--accent`，删除私有 hex，`vite build` 绿灯。

工具条正确写法（不要再用 `<n-card class="toolbar">` 包裹）：

```html
<div class="toolbar">
  <n-input v-model:value="kw" placeholder="搜索" clearable style="width: 360px" />
  <n-select v-model:value="filter" :options="opts" style="width: 160px" />
  <div class="spacer"></div>
  <n-button type="primary" class="gradient-btn" @click="add">+ 新增</n-button>
</div>
```

### 4.x 表格分页统一组件（useTablePagination）

**规则（2026-09-16 兵哥指令「表格分页统一组件」后新增）**：设置页 / 列表页所有 `n-data-table` 的分页配置，**必须**走 `web/app/src/composables/useTablePagination.ts` 工厂，禁止在页面里手写散落的 inline `{ pageSize: N }` 或各自维护的远程 `computed`。

- **统一来源**：

  ```ts
  import { localPagination, remotePagination, TABLE_PAGE_SIZE } from '@/composables/useTablePagination';

  // 本地分页（一次性取全量，n-data-table 前端切片）
  :pagination="localPagination()"            // 默认每页 TABLE_PAGE_SIZE = 20

  // 远程分页（服务端分页，page / itemCount 由调用方响应式维护）
  const pagination = remotePagination({ page: pageRef, itemCount: totalRef, pageSize: 50 });
  :pagination="pagination"
  :remote="true"
  ```

- **强制项**：

  | | |
  |---|---|
  |默认每页条数|`TABLE_PAGE_SIZE = 20`（统一，禁止各页自定 15/30/50 等不现值）|
  |pageSize 可选项|`TABLE_PAGE_SIZE_OPTIONS = [10, 20, 50, 100]`（统一，由 composable 注入）|
  |本地分页|`localPagination()`，禁止 `{ pageSize: 30 }` 之类 inline 对象|
  |远程分页|`remotePagination({ page, itemCount, ... })`，禁止页面内自写远程 `computed`（`itemCount` 是 n-data-table 远程分页字段，**非** `total`）|
  |远程 `itemCount`|远程分页必须用 `itemCount`（n-data-table 语义），`remotePagination` 已对齐；误用 `total` 会导致分页器总条数缺失|

- **页面级红线**：
  - scoped / `<script>` 内**禁止**出现 `{ pageSize: <数字> }` 字面量（grep 自检：`grep -n 'pageSize:' <file>` 仅允许出现在 `useTablePagination.ts` 内部）；
  - **禁止**页面自维护远程分页 `computed`（如旧 `regionPagination = computed(() => ({ page, pageSize:50, itemCount, showSizePicker:false }))`）——收口为 `remotePagination()`。
- **自检**：设置页 / 列表页分页器每页条数实测 = 20（或显式 `pageSize` 覆盖值），pageSize 下拉选项 = `[10,20,50,100]`；`grep -rn 'pageSize:' web/app/src/pages` 除 `useTablePagination.ts` 外无命中。
- **落地范围（2026-09-16）**：CodeTableLibrary（region 远程改 `remotePagination`、5 个本地表改 `localPagination()`）、CompanyLibrary、SchoolLibrary（各 inline `{pageSize:15}` 改 `localPagination()`）。

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
- [ ] 布局模型二选一（同一页不混用）：模型 A（block 流 + sticky 吸顶）/ 模型 B（`.page-container{height:100%;display:flex}` + `.page-body` 内部滚动三件套）
- [ ] 页面内没有 .cc-aurora / .blob-* 极光（由外壳提供）
- [ ] 标题用 .page-header > .page-title + .page-subtitle，scoped 无 .page-title/.page-subtitle 字号/颜色覆盖
- [ ] 标题底部分隔线由全局 `.settings-scroll .page-header` 提供，**scoped 不得写 `.page-header{margin-bottom}`**
- [ ] **间距唯一来源**：header 在 `.page-body` 内时，header→首块间距 = `.page-body` gap（16px）独家提供（全局 `.settings-scroll .page-body > .page-header{margin-bottom:0}` 已兜底）；scoped 不写 header margin-bottom、不给首块加与 gap 叠加的 margin
- [ ] **吸顶 header 玻璃磨砂**：滚动后吸顶 header 下方内容不得穿透重叠；scoped 未写 `background:transparent` / 未去 `backdrop-filter` / 未改 `position:fixed`（§3.1）
- [ ] **分页统一组件**：所有 `n-data-table` 分页走 `useTablePagination`（`localPagination()` / `remotePagination()`），无 inline `{pageSize:N}`、无页面自维护远程 `computed`（§4.x）
- [ ] 工具条是 `<div class="toolbar">`（非 `<n-card class="toolbar">`）
- [ ] 表格包在 `<div class="table-wrap">` 内，scoped 无 .table-wrap 重复定义
- [ ] 弹窗用 n-modal preset="card" + :bordered="false"，scoped 无居中/滚动重复定义
- [ ] KPI 用 .kpi-row > .kpi-card；强调卡用 .kpi-card--accent（CSS 变量）；**不得私有重定义 .kpi-* 或硬编码 hex**
- [ ] 主按钮用 gradient-btn 或 type="primary"，未私有重定义渐变
- [ ] 暗色验证：切换 body.dark，极光/玻璃/标题渐变/表格滚动/KPI 强调卡均正常（变量集切换）

## 8. 本次落地改动（2026-08-24）

| | |
|---|---|
|CampusControl.vue|模板：.cc-page→.page-container、删 .cc-aurora 极光块、.cc-header/title/subtitle→.page-header/title/subtitle；scoped：删 .cc-page/.cc-aurora/.blob*/.cc-header/.cc-title/.cc-subtitle、删与全局重复的 .table-wrap/.toolbar/.gradient-btn/.kpi-*、删 .import/.dim/.rule-modal 冗余弹窗规则；保留 .glass-panel flex 撑满 + .cc-tabs 布局链 + .batch-modal 紧凑微调 + .drawer-footer|
|DataDictionary.vue|模板：`<n-card class="toolbar">`→`<div class="toolbar">`；scoped：删 .page-title{22px} / .page-subtitle{#888} 覆盖以复用全局渐变规格；保留 .page-container 列表模式自身滚动例外|
|glass.css（已在前期阶段 F 落地）|.table-wrap、.n-modal .n-card 居中滚动、.settings-scroll 表格玻璃化等全局化，作为本规范的单一事实来源|

## 8.1 规范修订记录（2026-08-27，仅改规范不改码）

- **背景**：静态合规审查（见 `SETTINGS_PAGE_COMPLIANCE_CHECK.md`）发现规范 v1.0 与代码存在漂移——17 个设置页采用「`.page-container{height:100%;display:flex}` + `.page-body` 内部滚动」三件套，而 v1.0 误将 `height:100%` 列为禁止项。
- **§2 修订**：取消「禁止自写 height:100%」，改为「布局模型二选一」——模型 A（默认 block 流 + sticky 吸顶）/ 模型 B（固定标题 + 内部滚动三件套，新增 §2.1）。两种模型下 `.page-header` 底部分隔线均靠全局负 margin 通栏。
- **§3 修订**：标题「位置」说明补充模型 B 下靠 `flex-shrink:0` 固定（视觉等同吸顶）。
- **§4 修订**：KPI 增加「强调变体 `.kpi-card--accent`（必须 CSS 变量）」；新增 KPI 令牌铁律——禁止私有重定义 `.kpi-*` 与硬编码 hex（暗色不跟随）。标注 `DataDashboard.vue` 当前渐变 KPI 为已知偏差，待迁移。
- **§7 修订**：自检清单增补「模型二选一」「标题分隔线不得写 margin-bottom」「KPI 强调卡变量化」三条。
- **影响**：修订后 17 个既存页面（三件套）与 DataDashboard 之外的页面均**即刻合规**；仅 DataDashboard 的 KPI 仍属已知偏差（代码未改，待后续迁移）。纯文档修订，零代码改动。

## 8.2 规范修订记录（2026-09-18，间距唯一来源红线）

- **背景**：兵哥截图反馈 CodeTableLibrary header 与 Tab 导航间 32px 空带。根因——全部设置页 header 均在 `.page-body` 内部（de-facto 结构），全局 `.settings-scroll .page-header{margin-bottom:16px}` 与 `.page-body` 的 `gap:16px` 叠加。
- **代码（glass.css）**：新增 `.settings-scroll .page-body > .page-header { margin-bottom: 0 }`（特异性 0,3,0），header 在 page-body 内时间距由 gap 独家提供；兄弟结构不受影响。运行时硬证据：CodeTableLibrary 实测 `headerMarginBottom=0px`、`actualPixelGap=16px`、sticky/分隔线保留、console 0 错误。
- **§2 修订**：修正历史注释中已过时的「负 margin 通栏」描述为当前 `margin: 0 0 var(--space-4) 0`。
- **§2 红线新增**：「间距唯一来源」——header→首块间距只允许一个来源，页面 scoped 禁写 header margin-bottom（header 在 page-body 内时），加大间距走 gap 或首块 margin-top。
- **§7 修订**：自检清单更新分隔线条目 + 新增「间距唯一来源」检查项。

## 8.3 规范修订记录（2026-09-16，吸顶玻璃磨砂 + 分页统一组件）

- **背景**：兵哥截图反馈静态数据页（CodeTableLibrary）滚动时吸顶 header 纯透明，下方 `n-tabs` / 筛选行 / 表格内容穿透重叠；同时各设置页分页写法散落（`{pageSize:30}` / `{pageSize:15}` / 自维护远程 `computed`），每页自定页面大小，违反一致性。
- **代码（glass.css）**：吸顶 header 规则由「纯透明」改为「玻璃磨砂底」——`background: var(--glass-bg-panel)` + `-webkit-backdrop-filter` + `backdrop-filter` 双写 `blur(var(--glass-blur-panel))`；极光仍半透透出，但 blur 遮断滚过的文字，杜绝穿透重叠。暗色各自 `--glass-bg-panel` token 覆盖。
- **新增 `web/app/src/composables/useTablePagination.ts`**：导出 `TABLE_PAGE_SIZE=20` / `TABLE_PAGE_SIZE_OPTIONS=[10,20,50,100]` / `localPagination()` / `remotePagination()`（远程分页对齐 n-data-table `itemCount` 语义）。
- **接线（3 页）**：CodeTableLibrary（region 远程 `computed` → `remotePagination({page:regionPage,itemCount:regionTotal,pageSize:50})`；5 个本地表 `{pageSize:20/30}` → `localPagination()`）、CompanyLibrary、SchoolLibrary（各 `{pageSize:15}` → `localPagination()`）。
- **§3 修订**：新增 §3.1「吸顶 header 玻璃磨砂（禁止纯透明 sticky）」——玻璃类铁律（`-webkit-` 前缀 + 不透明兜底）、页面级红线（禁 `background:transparent` / 去 `backdrop-filter` / `position:fixed`）、运行时取证项。
- **§4 修订**：新增 §4.x「表格分页统一组件（useTablePagination）」——统一来源、强制项表、`pageSize:` 字面量禁令、运行时自检 grep。
- **§7 修订**：自检清单新增「吸顶 header 玻璃磨砂」「分页统一组件」两项检查。
