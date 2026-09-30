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
>   ⚠️ **模型 A 与「标题栏无底色」不兼容**：header 写在 `.page-body` 滚动容器内，`position:sticky` 冻结时内容会从 header **背后**滚过；若不加底色即出现文字穿透重叠（2026-09-16 截图）。故「冻结标题 + 无底色 + 无穿透」三项只能选 **模型 B**。
> - **模型 B · 固定标题 + 内部滚动三件套（团队规范强制：冻结标题 + 无底色 + 无穿透的唯一正解）**：`.page-container { display:flex; flex-direction:column; height:100%; min-height:0 }`，配合 `.page-header { flex-shrink:0 }` + `.page-body { flex:1; min-height:0; overflow-y:auto; overflow-x:hidden }`。**`.page-header` 必须写在 `.page-body` 滚动容器【之外】，成为 `.page-container` 的兄弟节点**——标题在布局层冻结、内容在下方独立滚动区，永不到标题背后 → 无需任何底色即无穿透。
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

### 2.2 数据列表页：仅表体内部滚动（tab / 筛选 / 标题全固定）

适用：以「单页多 tab + 每个 tab 一个数据表」为主的交互页（如静态数据 / 校招管控-规则配置），产品要求**只滚数据列表行内**，标题行、tab 切换栏、筛选栏在滚动时全部固定不动。

与 §2.1 的区别：§2.1 是「整页内容区（含 tab/筛选/表格）在 `.page-body` 内滚动」；本条款是**更严格**的变体——内层容器自身不滚动，tab 导航与筛选栏固定，仅 `n-data-table` 的表体（`flex-height`）内部滚动。范本 = `CampusControl.vue`（校招管控-规则配置页）。

⚠️ **致命陷阱（实测踩中）**：`SettingsLayout.vue` 用 `.settings-scroll :deep(.page-body){flex:1 1 auto!important; min-height:0!important; overflow-y:auto!important}` 全局强制 `.page-body` 成为滚动容器。任何在 `.page-body` 上写 `overflow:hidden` 的尝试都会被这个 `!important` 覆盖，导致「只滚表格」失效、表体高度塌成 0。**因此本条款的内层容器绝不能用 `.page-body` 类名**，须改用 `.data-body`（透明、避开该 `!important`）或 `.glass-panel`（CampusControl 即此，但本页每 tab 已有 `n-card`，为避免玻璃套玻璃双重边框用透明 `.data-body`）。

```html
<div class="page-container">            <!-- flex column（SettingsLayout :deep 强制 display:flex!important; height:100%） -->
  <div class="page-header"> ... </div>   <!-- flex-shrink:0，固定 -->
  <div class="data-body">               <!-- flex:1; min-height:0; overflow:hidden（不滚动，避开 .page-body 的 !important） -->
    <n-tabs class="data-tabs">           <!-- flex:1; min-height:0，撑满 data-body -->
      <n-tab-pane>
        <n-card class="tab-card">        <!-- flex:1; min-height:0，撑满 -->
          <div class="filter-row"> ... </div>   <!-- flex-shrink:0，固定 -->
          <div class="table-wrap">       <!-- 全局：flex:1; min-height:0 -->
            <n-data-table flex-height .../>      <!-- 表体内部滚动 -->
          </div>
        </n-card>
      </n-tab-pane>
    </n-tabs>
  </div>
</div>
```

scoped 仅需（对齐 `CampusControl.vue`，已在 `CodeTableLibrary.vue` 真机验证 PASS）：

```css
.page-container { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.page-header { flex-shrink: 0; }
/* 内层容器用 .data-body（非 .page-body），避开 SettingsLayout 的 overflow-y:auto!important 强制滚动 */
.data-body { flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
.data-tabs { display: flex; flex-direction: column; flex: 1; min-height: 0; } /* 直接挂在 <n-tabs> 上 */
.data-body :deep(.n-tabs-nav) { background: transparent; flex-shrink: 0; }
.data-body :deep(.n-tabs-pane-wrapper) { flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
.data-body :deep(.n-tab-pane) { flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
.tab-card { flex: 1; min-height: 0; display: flex; flex-direction: column; }
/* ⚠️ naive-ui 该版本 n-card 内容包裹层类名是 .n-card-content（单下划线，非 .n-card__content）；
   其默认 display:block，须改为 flex 列并 min-height:0，内部 .table-wrap(flex:1) 才能撑满卡片高度 */
.tab-card :deep(.n-card-content) { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.filter-row { flex-shrink: 0; }
```

- **滚动链唯一真相**：`.data-body`(overflow:hidden) → `.data-tabs`(flex:1) → `.n-tabs-pane-wrapper`(overflow:hidden) → `.n-tab-pane`(overflow:hidden) → `.tab-card`(flex:1) → `.n-card-content`(flex 列, min-height:0) → `.table-wrap`(flex:1;min-height:0, 全局) → `n-data-table[flex-height]`。任何一层漏写 `min-height:0` 都会让表格被内容撑高、失去内部滚动（naive-ui flex 链陷阱）。
- **`.table-wrap` 必须复用全局类**（glass.css 阶段 F），禁止页面私有重写其 flex 链；`n-data-table` 必须带 `flex-height`，否则 `flex:1` 容器内的表高为 0 或被撑开。
- **分页器保留**：`flex-height` + 内置/远程分页共存（CampusControl 规则表即如此）；分页 UI 仍走 `useTablePagination`（§4 强制外观）。
- **自检**：滚动表格体时，`.page-header` / `.n-tabs-nav` / `.filter-row` 三者 `getBoundingClientRect().top` 恒定不变（不随表体滚动位移）；仅 `.n-data-table-base-table-body` 内部出现滚动条。可用 Playwright 实测：`.data-body` 的 `overflow-y==='hidden'` 且 `scrollTop` 恒为 0；wheel 滚表体后表体 `.n-scrollbar-container` 的 `scrollTop` 增大、上述三者 `top` 不变。

### ⚠️ 强制校验项（红线）

- **`.page-body` 禁止声明 `padding` / `padding-top`**。顶部留白统一由外层 `.settings-scroll` 的 `padding: 20px` 提供（见 §2.1）。在 `.page-body` 上加 `padding-top` 会与 `.settings-scroll` 叠出多余顶部间隙，且与该规范唯一的模型 A 参考页（校招管控）顶部间距不一致。
- 反例：`padding-top: 8px`（commit `12c6ece` 引入，已在 `50c5341` + `7ec00af` 清除，涉及 RecruitmentStage/Process/Round、AccountSettings、DemandConfig、CompanyLibrary、SchoolLibrary、ProcessStageEditor、DataDashboard、CompanySettings、PermissionManagement、FieldAclSettings、DepartmentManagement、MouManagement、DynamicFieldSettings、ProcessStageRules、ScoringRules、UserManagement）。
- header 与首块内容间的 16px 间距**统一由容器 gap 提供**——模型 B 由 `.settings-scroll :deep(.page-container)` 的 `gap`（SettingsLayout.vue）、de-facto 由 `.page-body` 的 `gap`。**禁止**给首块（`.toolbar` / `.glass-panel` / `.page-body` 等 `.page-container` 直接子元素）加 `margin-top`，也**不要**动 `.page-body` 的 `padding`（间距单一来源，杜绝 margin 与 gap 叠加、杜绝按块类型特判，见 §3.2）。
- 自检：新增/修改设置页时，`grep -Pzo '\.page-body[\s\S]*?padding' <file>` 应无命中（`.page-body` 块内不得含任何 `padding` 声明）。

### ⚠️ 红线：间距唯一来源（2026-09-18 新增，兵哥反馈「header 与内容间多余空带」）

**header 与首块内容（Tab 导航 / 工具条 / 卡片）之间的间距，只允许有一个来源，禁止 margin 与 flex gap 叠加。**

- **事实结构**：多数（未迁移的）设置页的 `.page-header` 仍写在 `.page-body` **内部**（de-facto 结构，非 §2.1 模板中的兄弟结构），而 `.page-body` 普遍为 `display:flex; flex-direction:column; gap:16px`；数据列表页等已迁移到 §2.1 模型 B（header 在 `.page-body` 之外，为 `.page-container` 兄弟节点）。本全局规则仅对 de-facto 页生效（兄弟结构页走全局 margin，不受影响）。
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

### 3.1 标题栏无底色 + 模型 B 结构避穿透（禁止给冻结 header 加背景色）

**规则（2026-09-18 兵哥纠正后定稿）**：所有设置页的标题栏（`.page-header` / `.cc-header` / `.n-page-header` / `.policy-admin__header`）**禁止添加任何背景色 / 玻璃磨砂底**（极光与页面背景直接透出）。冻结标题 + 无底色 + 内容不穿透，三者只能靠 **模型 B 结构**（header 写在 `.page-body` 滚动容器之外，成为 `.page-container` 兄弟节点）同时满足；**不得**用底色遮断来「解决」穿透。

- **根因（旧反模式）**：初版为「让极光直接透出」故意不给背景（纯透明 + sticky，de-facto 结构 header 在 `.page-body` 内），滚动时下方 `n-tabs` / 筛选行 / 表格内容从 header 背后穿过、与标题文字重叠（2026-09-16 静态数据页截图实锤）。09-18 曾误用「玻璃磨砂底」做 workaround（极光半透 + blur 遮断），兵哥 09-18 纠正：**标题栏不得加底色**，该 workaround 已撤销（glass.css 恢复无底色）。正确解法是把 header 移出滚动容器（模型 B），从结构上消除穿透，而非用底色遮。
- **强制项**：
  - 需要「冻结标题 + 无底色」的页面，**必须**采用模型 B（§2.1）：`.page-header` 是 `.page-container` 的直接子节点、位于 `.page-body` 之前；scoped 仅需 `.page-container{flex column;height:100%}` + `.page-header{flex-shrink:0}` + `.page-body{flex:1;overflow-y:auto}`。
  - 全局 `.settings-scroll .page-header`（glass.css）保留 `position:sticky; top:0; border-bottom; margin; padding` 仅用于兼容未迁移的 de-facto 页冻结；模型 B 页的 header 在滚动容器之外，`position:sticky` 为 no-op，冻结由 flex 布局提供。
- **页面级红线**：
  - scoped / 内联 **禁止**写 `.page-header { background / background-color / backdrop-filter / -webkit-backdrop-filter }`（任何底色或磨砂底均违规）；
  - **禁止**把冻结 header 改成 `position: fixed`（fixed 脱离滚动流，与 `.settings-scroll` 外壳冲突）；
  - **禁止**用「加底色遮断」替代结构修复（模型 B）来解决穿透。
- **自检**：滚动页面后，吸顶 header **无 background**（透明 / 仅 border-bottom）；header 之下内容滚过时**不得**出现文字穿透到标题区。运行时取证：吸顶态下 `getComputedStyle(header).backgroundColor === 'rgba(0, 0, 0, 0)'`（透明）且 header 之下首个内容块 `getBoundingClientRect().top ≥ header 底边`（无重叠——因模型 B 内容在独立滚动区，根本到不了 header 背后）。
- **反例（已撤销的 workaround）**：静态数据页（CodeTableLibrary）09-18 曾给吸顶 header 加 `background: var(--glass-bg-panel)` + `backdrop-filter: blur(...)` 玻璃磨砂底——兵哥 09-18 纠正「标题栏不应加底色」，已撤销，改用模型 B 结构（header 移出 `.page-body`）。

### 3.2 边距单一来源（顶部 + 底部，2026-09-30 补强）

**规则**：所有设置页标题栏（`.page-header` / `.cc-header` / `.n-page-header` / `.policy-admin__header`）的**顶部与底部 margin 统一为 0**——「header 不带该边距」是硬约束。

- 全局 `.settings-scroll .page-header`（glass.css）已固定 `margin: 0; padding-top: 0`；顶部留白由外壳 `.settings-scroll{padding:20px}` 独家提供，底部间距由下方补偿规则提供，header 自身既不带 margin 也不带顶部内边距。
- scoped / 内联 **禁止**写 `.page-header { margin / margin-top / margin-bottom / padding-top }`；
- scoped **禁止**给 `.page-container` 写 `padding-top`（已被 SettingsLayout `.settings-scroll :deep(.page-container){padding:0!important}` 清零，顶部留白统一由外壳 20px 提供）。
- **顶层块红线（模型 B 必守，2026-09-30 修订）**：`.page-container` 的**直接子元素**（`.page-body` / `.ws-body` / `.data-body` / `.glass-panel` / `<n-card>` / `.kpi-row` / `.toolbar` 等）**禁止**写 `margin-top` / `margin-bottom`。其块间间距与 header→首块间距统一由 `.settings-scroll :deep(.page-container)` 的 `gap: var(--space-4)` 提供（glass.css/SettingsLayout 单一来源），**不得**用 margin 叠加或按块类型特判——原 `.page-container>.page-header+*` 相邻兄弟补偿对「首块是滚动容器（`.ws-body`/`.data-body` 等 `flex:1` 块）」误注 `margin-top`（造成 ws-body 多出边距），已废弃。
- **底部间距补偿（两种结构同一视觉 16px，统一由容器 gap 单一来源，2026-09-30 修订）**：
  · de-facto 页（header 在 `.page-body` 内）：header→首块 16px 由 `.page-body` 的 flex `gap` 独家提供（全局 `.settings-scroll .page-body>.page-header{margin-bottom:0}` 兜底清零 header margin）。
  · 模型 B 页（header 在 `.page-body` 之外，为 `.page-container` 直接子节点）：header→首块 16px 由 `.settings-scroll :deep(.page-container)` 的 `gap: var(--space-4)` 统一提供（定义于 SettingsLayout.vue）。该 gap 作用于 `.page-container` 的 flex 列**全部直接子元素**间留白，对「首块是滚动容器（`.ws-body`/`.data-body` 等 `flex:1` 块）」与普通块**一视同仁、不注入 margin、不按块类型特判**——根除了「武断一刀切」式的块类型特判。
- **根因（旧反模式，已修）**：
  · 顶部：此前全局 `.settings-scroll .page-header{ padding: var(--space-4) 0 var(--space-1) 0 }` 给 header 加 16px 顶部内边距，叠加外壳 20px → 顶部留白 36px；RecruitmentProcess / RecruitmentRound / RecruitmentStage 三页 scoped `.page-header{padding:0;margin:0 0 8px 0}` 把 16px 清零仅留 20px → 跨页顶部差 16px（「部分有上边距、部分没有」）。2026-09-30 已全局归零 padding-top 并清除三页 scoped 覆盖。
  · 底部：全局 `.settings-scroll .page-header{margin-bottom:16px}` 仅对模型 B 页生效（de-facto 页被 `.page-body>.page-header{margin-bottom:0}` 清零）→ 模型 B 页 16px、de-facto 页 0，「部分页面有额外 margin、部分没有」。2026-09-30 已将全局 margin 归零，模型 B 间距改由 `.settings-scroll :deep(.page-container)` 的 `gap` 提供（原 `.page-container>.page-header+*` 相邻兄弟补偿对滚动容器误注 margin-top，已废弃）；RuleEngine.vue 曾 scoped `.page-header{margin-bottom:var(--space-4)}` 及 `.kpi-row`/`.toolbar` 冗余 `margin-bottom`、DuplicateCandidate.vue `.page-body{margin-top:8px}`（与 gap 叠加）均已清除。
- **自检**：任一设置页渲染后，`getComputedStyle(header).margin === '0px'`（上下左右全 0）且 `paddingTop === '0px'`；header 顶边到外壳顶（含 20px）恒定、header 底边到首块顶（16px）在模型 B 与 de-facto 两结构下恒定一致。运行时取证：遍历所有设置路由，`header.getBoundingClientRect().top` 与 `.settings-scroll` 顶边差恒定 = 20px，`header.getBoundingClientRect().bottom` 到首块 `top` 差恒定 = 16px；模型 B 页首块（含 `.ws-body`/`.data-body` 滚动容器）`getComputedStyle(firstBlock).marginTop === '0px'`（间距由容器 gap 提供，不得自带 margin-top）。

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

**规则（2026-09-16 兵哥指令「表格分页统一组件」后新增，2026-09-18 据截图规范补全外观）**：设置页 / 列表页所有 `n-data-table` 的分页配置，**必须**走 `web/app/src/composables/useTablePagination.ts` 工厂，禁止在页面里手写散落的 inline `{ pageSize: N }` 或各自维护的远程 `computed`。

- **统一来源**：

  ```ts
  import { localPagination, remotePagination, TABLE_PAGE_SIZE } from '@/composables/useTablePagination';

  // 本地分页（一次性取全量，n-data-table 前端切片）
  :pagination="localPagination()"            // 默认每页 TABLE_PAGE_SIZE = 20

  // 远程分页（服务端分页，page / itemCount 由调用方响应式维护；size picker 开启后需把 page_size 透传后端）
  const pagination = remotePagination({
    page: pageRef, itemCount: totalRef,
    showSizePicker: true,
    onPageSizeChange: (s) => { pageRef.value = 1; loadData(); },  // s 已自动写回 pageSizeRef
  });
  :pagination="pagination"
  :remote="true"
  ```

- **统一外观（强制，与团队截图规范一致）**：每个分页器必须呈现
  `共 N 条` &nbsp;|&nbsp; `< 1 2 3 >` &nbsp;|&nbsp; `[20 / 页 ▾]` &nbsp;|&nbsp; `跳至 [__]`
  - `共 N 条`：由 composable 的 `prefix` 渲染（n-data-table / n-pagination 透传 `itemCount`）；
  - `页码`：默认首屏，连续页码 + 前后翻页箭头；
  - `20 / 页`：必须 `showSizePicker: true` + `pageSizes`（下拉可选项 `[10, 20, 50, 100]`）；
  - `跳至`：必须 `showQuickJumper: true`。
  - 上述四项均由 `localPagination()` / `remotePagination()` 统一注入，**业务页不得省略或覆盖**。

- **强制项**：

  | | |
  |---|---|
  |默认每页条数|`TABLE_PAGE_SIZE = 20`（统一，禁止各页自定 15/30/50 等不现值）|
  |pageSize 可选项|`TABLE_PAGE_SIZE_OPTIONS = [10, 20, 50, 100]`（统一，由 composable 注入 `pageSizes`）|
  |每页选择器|`showSizePicker: true`（统一，禁止关掉）|
  |跳至|`showQuickJumper: true`（统一，禁止关掉）|
  |总条数前缀|`prefix: 共 N 条`（统一，由 composable 注入）|
  |本地分页|`localPagination()`，禁止 `{ pageSize: 30 }` 之类 inline 对象|
  |⚠️ 本地分页非受控|`localPagination()` **必须返回 `defaultPage` / `defaultPageSize`（非受控默认值）**，不得写受控 `page` / `pageSize` 固定值。受控写法下 naive-ui 把 `pageSize` 当受控 prop，「N / 页」选择器的 `update:pageSize` 无回写，选择器形同虚设（2026-09-18 实锤：`国家区号` 表选 50 无反应，改 `defaultPageSize` 后 Playwright 验证 20→50 行生效）。|
  |远程分页|`remotePagination({ page, itemCount, ... })`，禁止页面内自写远程 `computed`（`itemCount` 是 n-data-table 远程分页字段，**非** `total`）|
  |远程 `itemCount`|远程分页必须用 `itemCount`（n-data-table 语义），`remotePagination` 已对齐；误用 `total` 会导致分页器总条数缺失|
  |远程 size 透传|远程分页开启 `showSizePicker` 后，必须在 `onPageSizeChange` 里把新 `page_size` 传给后端拉取（否则显示条数与后端返回不一致、itemCount 错位）|

- **页面级红线**：
  - scoped / `<script>` 内**禁止**出现 `{ pageSize: <数字> }` 字面量（grep 自检：`grep -rn 'pageSize:' web/app/src/pages` 仅允许出现在 `useTablePagination.ts` 内部）；
  - **禁止**页面自维护远程分页 `computed`（如旧 `regionPagination = computed(() => ({ page, pageSize:50, itemCount, showSizePicker:false }))`）——收口为 `remotePagination()`；
  - **禁止**在 `n-data-table` 上写 `:pagination="{ pageSize: 20, showSizePicker: ... }"` 散落对象——必须引用 composable 返回值。
- **自检**：设置页 / 列表页分页器实测——① 每页条数 = 20（或显式 `pageSize` 覆盖值）；② `20 / 页` 下拉选项 = `[10,20,50,100]`；③ 含「跳至」输入框；④ 左侧显示「共 N 条」；⑤ **`20 / 页` 选择器实测可切换**（改 50 后实际渲染行数同步变为 50，非仅 UI 数字变化）；⑥ `grep -rn 'pageSize:' web/app/src/pages` 除 `useTablePagination.ts` 外无命中。
- **落地范围（2026-09-16 初建 / 2026-09-18 外观补全）**：CodeTableLibrary（region 远程改 `remotePagination`、5 个本地表改 `localPagination()`）、CompanyLibrary、SchoolLibrary（各 inline `{pageSize:15}` 改 `localPagination()`）；2026-09-18 `useTablePagination` 增补 `showQuickJumper` / `pageSizes` / `prefix(共N条)`，region 远程 `pageSize 50→20` 且 `page_size` 透传后端。

## 4.y 卡选择决策树（玻璃面板 vs n-card，2026-09-30 落地）

## 4.y 卡选择决策树（玻璃面板 vs n-card，2026-09-30 落地）

**规则**：所有设置页的卡型容器**必须**按以下决策树选择，**禁止**散落私有 `<n-card>` 或私有玻璃样式。

| 场景 | 推荐形态 | 模板写法 |
|---|---|---|
| **无标题的卡**（如空状态、表格/表单的根容器） | `.glass-panel`（裸玻璃类） | `<div class="glass-panel">...内容...</div>`；如需内边距，scoped 补 `.glass-panel { padding: var(--space-4) }` |
| **带标题的卡**（如「需求规则设置」「联系信息」分段） | `.glass-panel--card` 变体（带 title 容器） | `<div class="glass-panel glass-panel--card"><div class="glass-panel__title">{{ title }}</div><div class="glass-panel__body">...内容...</div></div>` |
| **带标题 + 右侧操作**（如「条件编辑区」标题旁的「添加条件」按钮） | `.glass-panel--card` + `.glass-panel__title-extra` | 标题双层：`<div class="glass-panel__title"><span>{{ title }}</span><div class="glass-panel__title-extra"><button>添加条件</button></div></div>` |
| **多 tab 内的卡片**（如 CodeTableLibrary 静态数据页 tab 内） | `<n-card class="tab-card">` 保留（§2.2 已规范 flex 链） | `.tab-card` 走 §2.2 的 `.tab-card :deep(.n-card-content)` 链 |
| **子卡**（如 `.batch-modal` / `.lib-card` / `.policy-table-card` / `.stage-card` / `.config-card` / `.settings-section` / `.ra-card` / `.cs-card` / `.ca-card`） | 保留 `<n-card>` 或局部玻璃变体（按子卡语义保留） | 命名空间独立，不属于页面根容器范畴 |

### 4.y.1 `.glass-panel--card` 变体 API（glass.css 全局定义）

```css
.glass-panel--card { display: flex; flex-direction: column; }
/* 标题区：14px 加粗 + 16px padding + 底部分隔线 + flex 让标题内联 tag 右对齐 */
.glass-panel__title {
  padding: var(--space-4);
  font-size: var(--fs-14, 14px);
  font-weight: 600;
  color: var(--ink);
  border-bottom: 1px solid var(--glass-border);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
/* 标题右侧操作区（替代 <template #header-extra>）：用 margin-left:auto 推到最右 */
.glass-panel__title-extra { margin-left: auto; display: flex; align-items: center; gap: var(--space-2); }
/* 正文区：16px padding + flex:1 撑满剩余空间 */
.glass-panel__body { padding: var(--space-4); flex: 1; min-height: 0; }
```

### 4.y.2 `n-card` → `.glass-panel--card` 迁移模板

| 原生（naive-ui） | 玻璃面板变体 |
|---|---|
| `<n-card :title="..." class="config-card">...</n-card>` | `<div class="glass-panel glass-panel--card config-card"><div class="glass-panel__title">{{ title }}</div><div class="glass-panel__body">...内容...</div></div>` |
| `<n-card><template #header>...</template>...</n-card>` | `<div class="glass-panel glass-panel--card"><div class="glass-panel__title">...header 内容...</div><div class="glass-panel__body">...</div></div>` |
| `<n-card :title="..."><template #header-extra><button>...</button></template>...</n-card>` | `<div class="glass-panel glass-panel--card"><div class="glass-panel__title"><span>{{ title }}</span><div class="glass-panel__title-extra"><button>...</button></div></div><div class="glass-panel__body">...</div></div>` |

### 4.y.3 强制项

- **禁止页面私有定义与 `.glass-panel--card` 等价的卡样式**（如私有 `.config-card :deep(.n-card-header)` 等）——必须用全局变体。
- **禁止写 `<n-card class="config-card">` 等带 class 但仍用 n-card 渲染的卡**——`<n-card>` 的默认 border/box-shadow 与玻璃设计冲突，迁移到 `.glass-panel--card` 后视觉与 n-card 行为一致（标题 / 副标题 / 底部分隔线 / 右侧 header-extra）但走全局设计系统。
- 迁移后必须删除 scoped 中所有 `:deep(.n-card-header / .n-card-header__main / .n-card__content / .n-card-content)` 等死代码（n-card 已移除，:deep 选择器命中 0 行）。
- 迁移后必须删除 `import { NCard } from 'naive-ui'`（若仅作卡渲染用）。
- 保留 `class="config-card"` 等原业务 class 名——scoped `.config-card { animation: card-in ... }` / `.config-card { border-radius: 8px }`（紧凑配置面板设计选择）等仍作用于 `.glass-panel--card` div。
- **暗色自动跟随**：`.glass-panel__title { color: var(--ink) }` 走全局暗色变量集，无需额外样式。

### 4.y.4 自检

新增/重构带标题卡时：
1. `grep -n "<n-card" <file>.vue` 在模板中**只允许出现在 `<n-modal>` 内（弹窗用）+ 子卡保留命名空间（`.tab-card`/`.lib-card`/`.config-card`/`.ra-card`/`.settings-section`/`.cs-card`/`.ca-card` 等已规范化）**——页面根内容卡必须为 0。
3. 每个 `n-data-table` 必须包在 `<div class="glass-panel__body">` 或 `<div class="glass-panel">` 内。
5. 暗色模式下 `.glass-panel__title` 自动反色（`getComputedStyle(title).color !== '#000'`，因 `var(--ink)` 切换）。

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
- [ ] 布局模型二选一（同一页不混用）：模型 A（block 流 + sticky 吸顶，注：无底色会穿透，故需冻结+无底色必选模型 B）/ 模型 B（`.page-container{height:100%;display:flex}` + `.page-header` 在 `.page-body` 之外 + `.page-body` 内部滚动三件套）
- [ ] 页面内没有 .cc-aurora / .blob-* 极光（由外壳提供）
- [ ] 标题用 .page-header > .page-title + .page-subtitle，scoped 无 .page-title/.page-subtitle 字号/颜色覆盖
- [ ] 标题底部分隔线由全局 `.settings-scroll .page-header` 提供，**scoped 不得写 `.page-header{margin-bottom}`**
- [ ] **间距唯一来源**：header 在 `.page-body` 内时，header→首块间距 = `.page-body` gap（16px）独家提供（全局 `.settings-scroll .page-body > .page-header{margin-bottom:0}` 已兜底）；模型 B 页 header→首块间距 = `.settings-scroll :deep(.page-container)` gap（16px）独家提供（SettingsLayout）。两种结构下 **`.page-container` 直接子元素（首块/各块）scoped 均不写 margin-top/margin-bottom**，不按块类型特判（滚动容器与普通块一视同仁），禁止与 gap 叠加。
- [ ] **标题栏无底色 + 模型 B 冻结**：标题栏 scoped 未写任何 `background` / `backdrop-filter`；滚动后 header 透明、下方内容不穿透（header 为 `.page-body` 兄弟节点，模型 B）；未改 `position:fixed`（§3.1）
- [ ] **分页统一组件**：所有 `n-data-table` 分页走 `useTablePagination`（`localPagination()` / `remotePagination()`），无 inline `{pageSize:N}`、无页面自维护远程 `computed`（§4.x）
- [ ] 工具条是 `<div class="toolbar">`（非 `<n-card class="toolbar">`）
- [ ] 表格包在 `<div class="table-wrap">` 内，scoped 无 .table-wrap 重复定义
- [ ] **数据列表页「仅表体内部滚动」**：多 tab + 每 tab 一表的页，`.page-body` 为 `overflow:hidden` 的 flex 列（非整页滚）；`:deep(.n-tabs-nav)`/`.filter-row` 加 `flex-shrink:0` 固定；`n-data-table` 带 `flex-height`、外层 `.table-wrap`（flex:1;min-height:0）。滚动时 `.page-header`/tab 导航/筛选栏 `top` 恒定（§2.2）
- [ ] 弹窗用 n-modal preset="card" + :bordered="false"，scoped 无居中/滚动重复定义
- [ ] KPI 用 .kpi-row > .kpi-card；强调卡用 .kpi-card--accent（CSS 变量）；**不得私有重定义 .kpi-* 或硬编码 hex**
- [ ] 主按钮用 gradient-btn 或 type="primary"，未私有重定义渐变
- [ ] **卡选择决策树（§4.y）**：页面根内容容器用 `.glass-panel` / `.glass-panel--card` 变体；模板 `<n-card>` 只允许出现在 `<n-modal>` 内 + 子卡命名空间（`.tab-card` / `.lib-card` / `.config-card` / `.ra-card` / `.settings-section` / `.cs-card` / `.ca-card` / `.policy-table-card` / `.stage-card` 等）。带标题的卡用 `<div class="glass-panel glass-panel--card">` + `<div class="glass-panel__title">` + `<div class="glass-panel__body">`，右侧操作放 `.glass-panel__title-extra`。
- [ ] **n-card 迁移后清理**：迁移到 `.glass-panel--card` 后必须删除 scoped `:deep(.n-card-header / .n-card-header__main / .n-card__content / .n-card-content)` 死代码 + 删除 `NCard` import（仅作卡渲染用）。
- [ ] 暗色验证：切换 body.dark，极光/玻璃/标题渐变/表格滚动/KPI 强调卡/`.glass-panel__title` 均正常（变量集切换，title 自动反色）

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

## 8.4 规范修订记录（2026-09-18，标题栏无底色 + 模型 B 避穿透）

- **背景**：兵哥复核静态数据 / 动态数据 / 公司库 / 院校库四页，指出两条团队统一规范必须严格执行：① 标题行必须固定（吸顶/冻结），滚动时始终可见；② 顶部主标题栏**不得添加底色**（极光直接透出）。此前 09-18 为「解决」de-facto 结构滚动穿透而加的玻璃磨砂底，属错误 workaround，已撤销。
- **根因澄清**：「冻结标题 + 无底色 + 内容不穿透」三者**只能**靠模型 B 结构同时满足——`.page-header` 写在 `.page-body` 滚动容器之外，成为 `.page-container` 兄弟节点（布局层冻结，内容在独立滚动区，永不到标题背后）。de-facto 结构（header 在 `.page-body` 内 + sticky）下，无底色必穿透，加底色只是遮断而非根治。
- **代码（glass.css）**：撤销吸顶 header 的玻璃磨砂底（`background` / `-webkit-backdrop-filter` / `backdrop-filter` 全部移除），恢复无底色；保留 `position:sticky; top:0; border-bottom; margin; padding` 仅兼容未迁移的 de-facto 页冻结。注释更新为「无穿透依赖模型 B 结构，而非底色遮断」。
- **模板（4 页）**：CodeTableLibrary / CompanyLibrary / SchoolLibrary 将 `.page-header` 从 `.page-body` 内移到 `.page-container` 兄弟节点（模型 B）；DynamicDataLibrary 补冻结「动态数据」标题（模型 B，此前无主标题栏）。scoped 布局逻辑（`.page-container{flex column;height:100%}` / `.page-header{flex-shrink:0}` / `.page-body{flex:1;overflow-y:auto}`）本就 model-B-ready，仅移动 DOM 层级。
- **§2 修订**：模型选择说明补充「模型 A 与无底色不兼容，冻结+无底色必选模型 B」；间距唯一来源「事实结构」改为「多数未迁移页仍 de-facto，数据列表页已迁移模型 B」。
- **§3.1 重写**：由「吸顶 header 玻璃磨砂（禁止纯透明 sticky）」改为「标题栏无底色 + 模型 B 结构避穿透（禁止给冻结 header 加背景色）」——撤销玻璃磨砂红线，改红线为「禁写任何 background / backdrop-filter」「禁 position:fixed」「禁用底色遮断替代结构修复」。
- **§7 修订**：自检清单「模型二选一」「吸顶 header 玻璃磨砂」两项更新为「冻结+无底色必选模型 B」「标题栏无底色 + 模型 B 冻结」。
- **影响**：四数据列表页即时合规（冻结+无底色+无穿透）。其余未迁移的 de-facto 页在迁移到模型 B 前，无底色下仍会有穿透（已知待办，建议后续批量迁移）。

## 8.5 规范修订记录（2026-09-18，分页统一组件外观补全）

- **背景**：兵哥截图指定统一分页器外观——`共 N 条` | `< 1 2 >` | `[20 / 页 ▾]` | `跳至 [__]`。此前 `useTablePagination` 仅给 `showSizePicker` + 错误 prop 名 `pageSizeOptions`，缺 `showQuickJumper` 与「共 N 条」前缀，且与截图不一致。
- **代码（useTablePagination.ts）**：① 修正 prop 名 `pageSizeOptions` → `pageSizes`（naive-ui 正确字段）；② 统一注入 `showQuickJumper: true`；③ 新增 `prefix: 共 N 条` 渲染函数；④ 本地/远程两工厂均带上述三项。
- **接线（CodeTableLibrary region 远程表）**：`pageSize` 由 50 统一为 20（`TABLE_PAGE_SIZE`）；`showSizePicker: true` + `onPageSizeChange` 开启每页选择器；`loadRegions` 透传 `page_size: regionPageSize.value`（否则显示条数与 `itemCount` 错位）；`@update:page="onRegionPageChange"` 已就绪，分页可控。
- **§4.x 重写**：增「统一外观（强制）」段（含截图四要素说明）、强制项表补 `每页选择器 / 跳至 / 总条数前缀` 三项、页面级红线补「禁散落 `:pagination="{pageSize:20,...}"` 对象」、自检补 `跳至输入框 + 共N条` 两项、落地范围补 09-18 外观补全记录。
- **影响**：CodeTableLibrary / CompanyLibrary / SchoolLibrary / DynamicDataLibrary 内嵌表全部呈现统一分页器（共N条 + 20/页 + 跳至）。其余散落 inline `pageSize` 的设置页后续按 §4.x 批量迁移。

## 8.6 规范修订记录（2026-09-18，数据列表页仅表体内部滚动）

- **背景**：兵哥要求静态数据页（CodeTableLibrary）滚动「只滚数据列表行内」，参照校招管控-规则配置页（CampusControl）的列表交互形式。原模型 B 是「整页内容区（含 tab/筛选/表格）在 `.page-body` 内滚动」，与「表格体内部滚动」不符——tab 导航、筛选栏会随内容一起滚动走。
- **代码（CodeTableLibrary.vue）**：① 内层容器由 `.page-body` **改名为 `.data-body`**（透明 flex 列 `overflow:hidden`）——根因是 `SettingsLayout.vue` 用 `.settings-scroll :deep(.page-body){overflow-y:auto!important}` 全局强制 `.page-body` 滚动，任何 `overflow:hidden` 尝试都被覆盖，故必须避开该类名（CampusControl 用 `.glass-panel` 同理避开）；② `<n-tabs>` 直接挂 `.data-tabs`（`flex:1;min-height:0`）撑满链；③ 新增 `.data-body :deep(.n-tabs-nav / .n-tabs-pane-wrapper / .n-tab-pane)` 链（flex:1;min-height:0;overflow:hidden；tab 导航 `flex-shrink:0` 固定），pane 自身不滚；④ 每个 tab-pane 的 `n-card` 加 `tab-card`（`flex:1;min-height:0`），并对 naive-ui 该版本真实内容层 `.n-card-content`（单下划线，非 `.n-card__content`）设 `flex:1;min-height:0;flex 列`——否则其内部 `.table-wrap` 的 `flex:1` 因 `display:block` 父级失效、表体高度塌成 0；⑤ `.filter-row` 加 `flex-shrink:0` 固定；⑥ 6 个 `n-data-table` 全部包入全局 `.table-wrap` 并加 `flex-height`（表体内部滚动）。脚本逻辑（远程/本地分页、加载）零改动。
- **验证**：另起独立 vite（端口 5277，避开 launchd 托管的 :5212 的 HMR 缓存）跑 Playwright 真机——`.data-body` 的 `overflow-y==='hidden'` 且 `scrollTop` 恒 0；滚轮滚表体后表体 `.n-scrollbar-container.scrollTop` 增大、`.page-header`/`.n-tabs-nav`/`.filter-row` 三者 `top` 恒定；ALL_PASS=true（2026-09-18）。
- **§2.2 新增**：「数据列表页：仅表体内部滚动」条款，给出与 CampusControl 对齐的 DOM 模板 + scoped flex 链 + 红线（滚动链唯一真相、`min-height:0` 不可漏、`.table-wrap` 与 `flex-height` 必复用/必带、分页器保留）、自检（滚动时 header/tab 导航/筛选栏 `top` 恒定）。§7 自检清单补对应勾项。
- **影响**：静态数据页标题/tab/筛选固定，仅表格行内滚动，与校招管控-规则配置页交互一致。其余多 tab 数据列表页（如需同交互）后续按 §2.2 迁移。

## 8.7 规范修订记录（2026-09-18，「N / 页」每页选择器失效修复）

- **背景**：兵哥截图实锤静态数据页「国家区号」表「20 / 页」选择器改了没反应。根因 = `localPagination()` 原返回受控写法 `page:1, pageSize:N` 固定值，naive-ui 把 `pageSize` 当受控 prop，「N / 页」选择器的 `update:pageSize` 无回写、`pageSize` 恒为初值，选择器形同虚设；且模板内 `localPagination()` 每次渲染新建对象，内部状态被反复打回。
- **代码（useTablePagination.ts）**：`localPagination()` 改为非受控默认值 `defaultPage:1` / `defaultPageSize:pageSize`，naive-ui 自管页码与每页条数、本地切片自动跟随。`remotePagination()`（regions 远程表）保持受控 `page`/`pageSize` 不变（远程需回写后端）。
- **验证**：另起独立 vite（5277）+ Playwright 真机——`国家区号`(本地 250 行) 默认渲染 20 行，点开 size picker 选「50」后渲染行数变为 50、trigger 显示「50 / 页」、prefix 仍「共 250 条」；ALL_PASS=true（2026-09-18）。一处修改，5 个本地表（国家区号/民族/语言/币种/行业）及 Company/School/DynamicData 内嵌表全部修复。
- **§4.x 增补**：强制项表新增「⚠️ 本地分页非受控」红线（禁受控 `page`/`pageSize` 固定值）；自检项 ⑤ 新增「`20 / 页` 选择器实测可切换」（改 50 后实际渲染行数同步变为 50，非仅 UI 数字变化）——作为防回归硬门槛。
- **影响**：所有走 `localPagination()` 的本地表「每页条数」选择器恢复可用。远程表（regions）本就经 `onPageSizeChange` 回写后端，不受影响。

## 8.8 规范修订记录（2026-09-18，动态数据页 3-tab 拆分 + 嵌入页「只滚表格行内」）

- **背景**：兵哥要求 ① 动态数据（院校/公司信息库）的数据列表也按「只滚表格行内」规则调整（对齐 CodeTableLibrary）；② 把「院校库」下的二级页签（院校 / 专业）拆分出来，成为 3 个一级 tab：院校库 / 专业库 / 公司库。经确认采用「聚合页内 3 个一级 tab」方案（保留 DynamicDataLibrary，菜单仍指向它）。
- **代码**：
  - 新增 `MajorLibrary.vue`（专业库）：从 `SchoolLibrary` 的「专业」二级 tab 整段抽取（kpi-row + n-card(filter + table-wrap + flex-height) + 详情抽屉 + 编辑弹窗），独立路由 `major-library`。
  - `SchoolLibrary.vue` 删除「专业」tab 与全部 majors 相关脚本/列/状态，仅留「院校」视图（kpi-row + n-card + 详情抽屉 + 编辑弹窗），作为「院校库」tab 内容。
  - `CompanyLibrary.vue` / `SchoolLibrary.vue` / `MajorLibrary.vue` 三者统一：`.page-body` → `.data-body`（`overflow:hidden` 填高，规避 SettingsLayout 对 `.page-body` 的 `!important` 强制）；kpi-row `flex-shrink:0` 固定；n-card 加 `.lib-card`（`flex:1;min-height:0`）并对 naive-ui `.n-card-content`（单下划线）设 flex 列；filter-row `flex-shrink:0`；`n-data-table` 包 `.table-wrap` + `flex-height`（表体内部滚动）。即每页自身即「只滚表格行内」，standalone 与嵌入态通用。
  - `DynamicDataLibrary.vue` 改为 3 个一级 tab（院校库 / 专业库 / 公司库）分别嵌入上述三页；`.page-body` → `.data-body`，`<n-tabs>` 挂 `.data-tabs`，补 `.data-tabs :deep(.n-tabs-nav / .n-tabs-pane-wrapper / .n-tab-pane)` flex 链（tab 导航固定、pane 不滚、嵌入页 `.page-container` 撑满）；嵌入页 `.page-header` 隐藏（tab 已承担标题）。
- **§2.2 关系**：本变更是 §2.2「仅表体内部滚动」在「聚合页嵌入子页」场景的延展——聚合页 `.data-body` 不滚、tab 固定，子页 `.data-body` 同样不滚、仅表体内部滚，双重 `.data-body` 形成嵌套填高链，无 `.page-body` 的 `!important` 干扰。
- **影响**：动态数据页 tab 固定、仅表体内部滚动；院校库/专业库/公司库 3 个一级 tab 切换正常；专业库独立可访问（`/settings/major-library`）。路由 `major-library` 与既有 `school-library`/`company-library` 一致。

## 9. 数据列表页统一数据规范（2026-09-19 新增）

## 8.9 规范修订记录（2026-09-30，卡选择决策树 + `.glass-panel--card` 变体）

- **背景**：本会话扫到 18 个含 `<n-card>` 的设置页，其中 14 个是子卡（保留 `<n-card>`），4 个多卡页（AccountSettings / CompanyBrand / DemandConfig / RuleAuthoring）带 `:title` 或 `<template #header>` slot——简单替换 `.glass-panel` 会丢标题视觉。
- **走法决策**：不采用走法 A（接受视觉降级，丢 title），采用走法 B（设计系统演进）——扩展 `.glass-panel` 体系新增 `.glass-panel--card` 变体（带 title 容器）+ `.glass-panel__title` / `.glass-panel__body` / `.glass-panel__title-extra` 子元素类。走法 A 与 B 在用户体验上的差异见走法 B 提交说明。
- **代码（glass.css 阶段 G）**：新增 30 行 CSS 定义 `.glass-panel--card` / `.glass-panel__title` / `.glass-panel__title-extra` / `.glass-panel__body` 四个全局类；`.glass-panel--card` 是 flex 列布局，标题子元素含 padding+14px 加粗+`var(--ink)` 暗色自动跟随+`border-bottom` 分隔线，标题右侧 `__title-extra` 用 `margin-left:auto` 推到最右（与 naive-ui `<template #header-extra>` 行为一致）。
- **落地（4 个 commit 2026-09-30 推送）**：
  · `c263307f` AccountSettings（3 张卡，含 `<template #header>` slot）+ glass.css 变体定义
  · `4b675a62` CompanyBrand（6 张卡，纯 `:title`）
  · `1f6f72b1` RuleAuthoring（4 张卡，2 含 `<template #header-extra>`）+ glass.css `__title-extra`
  · `9356175a` DemandConfig（10 张卡，纯 `:title`，保留 scoped `.config-card { border-radius: 8px }` 紧凑配置面板设计选择）
  · 累计 23 张多卡全部迁移，n-card 全部清零；Playwright 真机：`nCardCount=0` / `cardCount=23` / `backdrop=blur(28px)` / `borderRadius=20px`（DemandConfig 8px）/ `consoleErrCount=0`；截图视觉确认玻璃面板呈现正确。
- **§4.y 新增**：卡选择决策树 + `.glass-panel--card` 变体 API + `n-card` → `.glass-panel--card` 迁移模板（含 `:title` / `<template #header>` / `<template #header-extra>` 三种场景）+ 强制项（禁私设等价样式 / 禁带 class 的 `<n-card>` / 删 `:deep(.n-card-*)` 死代码 / 删 `NCard` import / 暗色自动跟随）+ 自检（模板 `n-card` 仅出现在 `<n-modal>` 内或子卡命名空间 + 表格包在 `glass-panel__body` 内 + 暗色 `var(--ink)` 反色）。
- **影响**：未来新增带标题卡**零成本**复用 `.glass-panel--card`（无需每次重写）；存量债（18 个含 n-card 页面）的 4 个多卡页已迁移，14 个子卡（含 `<n-modal>` 内 n-card 与功能性子卡）按命名空间保留——**甄别规则见 §4.y 决策树**，避免误迁。

---

> 前置说明：`SETTINGS_PAGE_STRUCTURE.md` 前文已覆盖页面外壳、布局模型、标题区、KPI/工具条、弹窗、分页统一组件。本节补齐**数据语义规范**——字段命名、展示顺序、筛选/排序、状态标识。若数据语义不统一，页面再多布局统一也会显得信息混乱。

### 9.1 字段命名（FIELD NAMING）

#### 9.1.1 列标题用词

| 场景 | 推荐用词 | 反例 |
|---|---|---|
| 业务编码（roleCode / templateCode / code） | **编码** | ❌ 代码（仅技术内部用）、❌ 编号（用于流水号） |
| 业务流水号/人员号（candidate / person） | **编号** | ❌ 编码 |
| 布尔状态列 | 直接用状态语义名词：「启用」「计入核算」「可见」 | ❌「是否启用」（口语，列宽浪费） |
| 日期时间 | 「创建时间」「更新时间」；格式由后端决定，前端不自行截断 | — |

- **列 `key` 一律用后端 camelCase 输出字段名**（与 `djangorestframework-camel-case` 全局转换对齐），禁止在列定义里手写 `source='snake_name'` 映射。

#### 9.1.2 默认兜底

单元格内容为空时统一渲染 `—`（中间长破折号），使用 `<span class="muted">—</span>`；禁止留空或写 `-` / `/`。

### 9.2 展示顺序（DISPLAY ORDER）

数据表列序按以下优先级从左到右排列：

1. **标识列**（编码/编号）：通常 `fixed: 'left'`，可点击打开详情/抽屉。
2. **名称列**（角色名称 / 姓名 / 规则名称）：紧随标识列。
3. **分类/来源列**（模板来源 / 默认数据范围 / 部门 / 职务）。
4. **状态列**（启用/停用、计入核算、流程状态）：见 §9.4。
5. **计数/度量列**（权限码数 / 年度目标 / 达成率 / 人数）。
6. **时间列**（创建时间 / 更新时间）：靠右展示，除非业务需要前置。
7. **操作列**（编辑 / 删除 / 启停）：`fixed: 'right'`。

> 示例：`角色编码 → 角色名称 → 模板来源 → 默认数据范围 → 状态 → 来源 → 权限码数 → 操作`

### 9.3 筛选与排序（FILTER & SORT）

#### 9.3.1 工具条控件顺序

`<div class="toolbar">` 内从左到右：

1. **搜索框**（最左，模糊匹配主标识/名称，带 `clearable`，回车触发或即时过滤）。
2. **状态筛**（紧邻搜索框右侧，三态：全部 / 启用 / 停用）。
3. **其他精确筛**（维度 / 指标 / 范围 / 部门等，按需）。
4. `<div class="spacer"></div>`
5. **次要操作**（刷新 / 导出 / 导入 / 克隆）。
6. **主操作**（新增 / 新建，`type="primary" class="gradient-btn"`）。

#### 9.3.2 服务端筛选 vs 客户端筛选

| 数据规模 | 推荐方式 | 分页 |
|---|---|---|
| 全量 ≤ 500 条 | 客户端 `filteredXxx` computed（与 CampusControl rules 一致） | `localPagination()` |
| 全量 > 500 条或后端聚合 | 服务端筛选（API 参数 `search/status/...`） | `remotePagination()` |

- 后端已提供筛选参数的接口（如 `listRoles({search,status,isSystem})`），优先走服务端；若当前迭代未接后端筛，可先用客户端兜底，但需在注释标注 `TODO: migrate to server-side filtering when data grows`。

#### 9.3.3 排序与 fixed 列

- 标识列默认 `sortable: true`，默认升序。
- 名称列、时间列默认 `sortable: true`。
- 操作列、状态列、计数列通常不排序。
- **标识列 `fixed: 'left'`，操作列 `fixed: 'right'`** 为强制项；其他列 fixed 按需。

### 9.4 状态标识（STATUS IDENTIFIER）

> 本项目状态存在 3 种写法，本节统一约定。

#### 9.4.1 渲染组件选型

| 状态可写性 | 组件 | 示例 |
|---|---|---|
| **可写**（用户能直接切换启用/停用） | `NSwitch` 内联 | 角色「启用」列、指标管理「启用」列 |
| **只读**（流程/系统状态） | `n-tag` | 人员「计入核算」、流程状态 |
| 不建议 | 操作列按钮切换「启用/停用」 | 规则表旧写法，新页禁用 |

#### 9.4.2 颜色/类型语义

| 状态 | `n-tag type` / `NSwitch` | 文本 |
|---|---|---|
| 启用/是/正常 | `success` | 启用 / 是 / 正常 |
| 停用/否/中立 | `default` | 停用 / 否 |
| 告警/待处理 | `warning` | 待确认 / 部分生效 |
| 异常/阻断 | `error` | 异常 / 失败 |

- 状态列统一放在 §9.2 所述「分类列之后、计数列之前」。
- **内联切换交互范式**：

```ts
h(NSwitch, {
  value: r.status === 1, // 或 r.isActive
  size: 'small',
  'onUpdate:value': async (v: boolean) => {
    const next = v ? 1 : 0;
    try {
      await updateRole(r.id, { status: next });
      r.status = next;
      message.success(v ? '已启用' : '已停用');
    } catch (e: any) {
      message.error('切换失败: ' + (e?.response?.data?.message ?? e?.message ?? e));
    }
  },
});
```

#### 9.4.3 状态值映射

- `status: 1` = 启用，`status: 0` = 停用。
- `isSystem: 1` = 预置，`isSystem: 0` = 自定义。
- 新增业务状态字段时，必须在本规范补充一行映射，禁止在代码里硬编码 `1/0` 而不注释含义。

### 9.5 自检清单（§7 增补）

在 §7 基础上追加：

- [ ] 列标题符合 §9.1 用词约定（编码/编号/启用等）。
- [ ] 列序符合 §9.2 优先级（标识→名称→分类→状态→计数→时间→操作）。
- [ ] 搜索框最左，状态筛第二，主操作最右，使用 `spacer` 分隔。
- [ ] 状态列使用 `NSwitch`（可写）或 `n-tag`（只读），颜色语义符合 §9.4.2。
- [ ] 标识列 `fixed: 'left'`，操作列 `fixed: 'right'`。
- [ ] 空状态区分「暂无数据」和「当前筛选下无数据」。

### 9.6 规范修订记录（2026-09-19，数据语义规范补齐）

- **背景**：身份管理（RolesTab）参照校招管控-规则配置页做一致性调整时，发现各数据列表页在字段命名、列序、筛选/排序、状态标识上无统一标准，导致跨页信息呈现混乱。
- **新增 §9**：字段命名（§9.1）、展示顺序（§9.2）、筛选与排序（§9.3）、状态标识（§9.4，重点统一 NSwitch/n-tag 选型与颜色语义）、状态值映射、自检清单增补。
- **代码同步**：`RolesTab.vue` 按 §9 落地（工具条/状态列/来源 tag/分页/fixed 操作列）；`PermissionManagement.vue` 修复 `.n-card-content` flex 链，解决表格 body 高度塌陷。
- **影响**：后续新增/重构数据列表页可直接引用 §9，不再依赖口口相传；存量债（编号/编码混用、状态 3 种写法）后续按 §9 批量整改。

---

## 10. 滚动契约（模型 B 详解，2026-09-18 收口，commit `077c469`）

### 10.1 滚动链（C 位：layout `.settings-scroll`）

```
SettingsLayout.vue (.settings-scroll)
  └─ .page-container { display: flex; flex-direction: column; height: 100%; }
       ├─ .page-header { /* 标题冻结，不参与滚动 */ }
       └─ .page-body { flex: 1; min-height: 0; overflow-y: auto; }
            └─ 页面内容
```

### 10.2 模型 B 红线（不破任何一条）

1. **标题行冻结**：`.page-header` 必须出现在 `.page-body` **之外**（否则滚走）。
2. **标题栏禁底色**：标题栏背景透明，极光透出；底部禁止阴影/分隔线（会被误读成"被滚走"）。
3. **唯一正解**：`.page-header` 写在 `.page-container` 兄弟、`.page-body` 之外。
4. **顶部留白来源**：`.settings-scroll` 已统一 `padding: 20px`，组件 `.page-body` **禁止再写 `padding-top`**（避免双重间距，commit `50c5341` / `7ec00af` 实证）。
5. **强制校验项**：`grep -rn 'padding-top: 8px' web/app/src/pages/settings/`，命中 `.page-body { padding-top: 8px }` 即违规（提交前必 grep 自检）。

### 10.3 「仅表体内部滚动」变体

不能复用 `.page-body` 类名——那是设置页专属约定，外层页面用不同容器类：

```vue
<!-- ❌ 错：列表页用 .page-body 会继承模型 B 滚动契约 -->
<div class="page-body">
  <n-tabs v-model:value="tab">
    <n-tab-pane name="list" tab="列表">
      <div class="data-body">  <!-- 必须用 .data-body -->
        <n-data-table :data="list" />
      </div>
    </n-tab-pane>
  </n-tabs>
</div>

<!-- ✅ 对：内部滚动独立容器 -->
<style scoped>
.data-body { flex: 1; min-height: 0; overflow-y: auto; }
.data-tabs { flex: 1; }
.tab-card .n-card-content { flex: 1; min-height: 0; overflow-y: auto; }
</style>
```

### 10.4 Playwright 验证纪律

- launchd `:5212` HMR 陈旧 → 验证时**另起独立 vite `:5277`**。
- JWT 短效（默认 1h），跑测试前重新 `curl login` 取新 token。旧 token 过期会被 auth guard 重定向 → `.n-data-table` 永不出现（`waitForSelector` 假象"组件渲染好了"）。
- 沙箱可用 Playwright + 缓存 Chromium（CommonJS）：
  ```js
  import pkg from 'playwright';
  const { chromium } = pkg;
  const browser = await chromium.launch({ headless: true });
  ```
