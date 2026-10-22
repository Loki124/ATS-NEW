# Naive UI 2.44.1 实战坑与 Vue 库联动反模式
> 最后更新：2026-10-21（新增 §9 `n-menu` 折叠态浮出只对根级子菜单生效）

> 适用：ATS-NEW 前端 Vue 3 + Naive UI 2.44.1 + @vicons/ionicons5 + vue-draggable-plus 0.6.x。
> 收录范围：实战中翻车过的组件/API 错用、文档未明示但实际行为不符直觉的坑。

---

## 1. 组件层级

### 1.1 无 `NSegmented`

- 文档里没导出 `NSegmented`，但 vue-tsc 不报错（看着像有）。
- 替代方案：`<n-radio-group>` + `<n-radio-button>`。
- 示例：流程类型筛选、流程内阶段筛选都用此组合。

### 1.2 `<n-card #header-extra>` 无 title 不渲染

```vue
<!-- ❌ 错：以为加 title prop 就有 header -->
<n-card :title="null">
  <template #header-extra>工具按钮</template>
</n-card>
<!-- 实际：整个 header 区域（包括 header-extra）都不渲染 -->

<!-- ✅ 对：工具条放卡片 body 内 -->
<n-card>
  <div class="toolbar">
    <span>标题文字（用 body 自己渲染）</span>
    <n-space><n-button>工具</n-button></n-space>
  </div>
</n-card>
```

### 1.3 `<n-card>` 内滚动约束

- 默认 `<n-card>` 内容溢出时**不会滚动**，需要主动设置滚动容器。
- 模式 A（绝对定位铺满父级）：
  ```css
  .n-card-content { position: absolute; inset: 0; overflow: auto; }
  ```
- 模式 B（flex 列 + min-height:0）：
  ```css
  .tab-card { display: flex; flex-direction: column; min-height: 0; }
  .tab-card .n-card-content { flex: 1; min-height: 0; overflow-y: auto; }
  ```
- 关键：**flex item 必须 `min-height: 0`** 才能让 overflow 生效。

---

## 2. Radio / Checkbox 模型绑定

### 2.1 `n-radio` checked 是 Boolean（commit `e44f4f8` 实证）

```vue
<!-- ❌ 错：直接 v-model:checked 绑字符串模型 -->
<n-radio v-model:checked="condForm.matchType" value="ALL">全部满足</n-radio>
<!-- Vue warn: Invalid prop: type check failed for prop "checked". Expected Boolean, got String -->

<!-- ✅ 对：用 n-radio-group 绑 v-model:value -->
<n-radio-group v-model:value="condForm.matchType" name="matchType">
  <n-space>
    <n-radio value="ALL">全部满足 (AND)</n-radio>
    <n-radio value="ANY">任意满足 (OR)</n-radio>
  </n-space>
</n-radio-group>
```

- `n-radio` 是 leaf 组件，`checked` prop 是 Boolean（这一项是否被选中），不是模型值。`value` 才是它的「当选时是什么」。
- 类比：和 `n-checkbox` 类似——单 `n-checkbox` 也是 Boolean checked；多选才用 `n-checkbox-group + v-model:value`。

### 2.2 决策法门
写 radio 时优先想 `n-radio-group` 而不是直接 `n-radio`。

---

## 3. vue-draggable-plus 0.6.x（标准简历拖拽踩坑实证）

### 3.1 必须 `v-for` + 默认 slot，禁 `#item` slot

```vue
<!-- ❌ 错：写 #item slot -->
<VueDraggable v-model="list" :item-key="id">
  <template #item="{ element }">
    <div>{{ element.name }}</div>
  </template>
</VueDraggable>
<!-- 实际：整片空白（vue-draggable-plus 只渲染 slots.default，源码 e.default.call(e, u)）-->

<!-- ✅ 对：v-for + 默认 slot -->
<VueDraggable v-model="list" handle=".handle">
  <div v-for="item in list" :key="item.id">
    <span class="handle">⋮⋮</span>
    {{ item.name }}
  </div>
</VueDraggable>
```

### 3.2 props 仅 `modelValue/tag/target`

- `item-key` 是脏属性，传了无效且不会报错但误导。
- `handle=".handle"` 指定拖拽手柄。

### 3.3 回滚必须 snapshot 双份

- 详见 `docs/06-runbook/ENGINEERING_RULES.md` §10。

---

## 4. 图标（@vicons/ionicons5）

### 4.1 存在性先查再 import

```bash
# 先查是否存在
ls node_modules/@vicons/ionicons5/ | grep -i <关键词>
```

- `FastForwardOutline` **不存在**（最接近的是 `PlaySkipForwardOutline`）。
- 引入任何图标前先 `ls` 确认存在——未确认会 Vite 编译错误而非运行时缺失。

---

## 5. 浮层背景透明 / 关闭后残留根因

### 5.1 Naive UI 1.x 浮层 stack

```
body > .v-binder-follower-container
  > .v-binder-follower-content (transform: translate) ← 真实浮层根
    > .n-dropdown-menu.n-popover-shared
      > .n-dropdown-option
```

- 没有 `.n-popover` wrapper——`.n-popover { background: ... }` 实际从未命中过。
- 浮层 backdrop-filter 必须配 **alpha ≥ .96 + blur ≥ 24px + saturate 150-200%** 三件套。
- 浮层必加 **`isolation: isolate`**（防 transform 父级截断 backdrop-filter）+ **`overflow: hidden`**（让 border-radius 干净裁切）。

### 5.2 关闭后残留「白带/多一块」

- vueuc-popper 用 **v-show 而非 v-if** 控制浮层显隐 → 关闭后 wrapper `.v-binder-follower-content` 子节点状态分两种：
  - (a) **n-dropdown submenu**：Vue 卸载子节点 → wrapper 内只剩注释 `<!---->`
  - (b) **n-select dropdown**：子 n-base-select-menu 保留但 `style="display: none"`
- 无论哪种 wrapper 自身仍 `display:block; visibility:visible; opacity:1` → 上层 CSS 的 `box-shadow` 渲成肉眼可见色块。
- 修法：CSS `:has()` 反向检测 wrapper「无可视子节点」→ 整体 `display:none`：
  ```css
  .v-binder-follower-content:not(:has(> *:not(#comment):not([style*="display: none"]))) {
    display: none !important;
  }
  ```

### 5.3 「两层结构」消除

- L1 wrapper 加视觉样式（bg + backdrop-filter + border + box-shadow + padding）会撑出 padding + shadow 像"外框"，L2 menu 是"内容"，**视觉上双层结构**。
- 修法：L1 wrapper **移除所有视觉样式**（仅保留 border-radius 让 L2 box-shadow 不溢出），所有视觉下移到 L2 menu。

### 5.4 决策法门（按优先级）
1. 不靠 grep / 推测，**第一动作 Playwright `getComputedStyle + outerHTML` 看真实结构层级**。
2. CSS 修法优先级：移除样式 > 转移样式 > 兜底隐藏。**优先移除/转移**比"加兜底"更优雅。
3. L1 wrapper vs L2 menu 职责分离：wrapper = transform anchor（无视觉），menu = 唯一视觉。

---

## 6. n-modal 遮罩关闭与 dialog-preset 自动关闭竞态（2026-10-08）

### 6.1 `mask-closable` 默认 true 静默丢草稿

- `<n-modal>` 的 `mask-closable` 默认 `true`。含可编辑表单的弹窗若不动它，**点遮罩直接关闭且丢弃未保存草稿**，无任何二次确认。
- 修法（方案 B，见 `SETTINGS_PAGE_STRUCTURE.md` §6.1）：抽 `web/app/src/composables/useCloseGuard.ts`，`requestClose()` 脏检查 + 二次确认；card-preset 受控、dialog-preset 保留 `v-model:show`。

### 6.2 dialog-preset `@positive-click`/`@negative-click` 是钩子，返回真值会触发自动关闭（竞态坑）

- `preset="dialog"` 的 `@positive-click` / `@negative-click` 是**钩子函数**而非纯事件——处理函数返回真值（包括 `async` 函数返回 Promise，Promise 恒为真）时，Naive UI 会**自动关闭弹窗并 emit `update:show(false)`**。
- 受控写法 `:show="x"` + `@update:show` 下，若钩子返回真值，Naive 自动关 + emit，与你的 `:show` 受控值产生竞态（成功关闭反而误触 `requestClose` 二次确认，或关闭状态不一致）。
- **正确接法**：dialog-preset 表单弹窗**保留 `v-model:show`**（规避竞态），并让 `requestClose` **恒返 `false`**——`isSaving` 时 `message.warning` 返 `false`；`isDirty` 时弹 `dialog.warning` 二次确认（确认后 `onClose()`），返 `false`；都不满足也返 `false` 并直接 `onClose()`。返回 `false` 阻止 Naive 自动关闭，把关闭权完全交给守卫逻辑。
- ❌ 反例：`requestClose` 在「无脏数据」分支返回 `true` 或 `void`（async 隐式 Promise 真）→ Naive 自动关 + emit，与受控 `:show` 打架。
- ✅ 正例：`useCloseGuard.ts` 的 `requestClose` 所有分支 `return false`（见源码）。
- 验证：`vite build --mode nocheck` 通过；21 文件 +300/−40（commit a9e85bb6，已推送 origin/main）。

---

## 7. n-modal / Dialog 浮层穿透与嵌套（2026-10-19 新增，源自 TDesign 组件库研究对照）

### 7.1 `:deep()` 对 Teleport 渲染的 Dialog 内容**无效**

- naive `n-modal`（preset="card" / "dialog"）自 1.0.8 起用 Vue3 `Teleport` 重构 `attach`（默认挂到 `body`）。
- `Teleport` 把弹窗 DOM 移到组件 DOM 树**之外**，scoped 的 `:deep()` 作用域选择器无法跨 Teleport 命中弹窗内部节点。
- ❌ 错：在 scoped `<style>` 里用 `.abc :deep(.n-radio-button__label) { color: red }` 想改弹窗内样式 —— 不生效。
- ✅ 对：① 单独建一个**非 scoped** 的 `<style>` 块写全局规则；② 或在本组件用 `:global(.abc .n-radio-button__label)` 伪类。
- 本项目现有做法：`styles/glass-modal.css` 是**独立非 scoped** 文件，已正确绕过此坑，无需改。

### 7.2 多层 Dialog 嵌套：除最内层外，外层必须 `lazy: true`

- 多层 `n-modal` 嵌套，且最外层开了 `destroy-on-close` 时，会抛运行时错误：
  `Uncaught (in promise) NotFoundError: Failed to execute 'insertBefore' on 'Node': The node before which the new node is to be inserted is not a child of this node.`
- 修法：除最内层 Dialog 外，外层所有 Dialog 设 `lazy: true`。
- 详见 TDesign issue 同源问题（naive 行为一致）：嵌套弹窗必须惰性渲染外层。

### 7.3 `attach` 挂载目标节点必须在 Teleport 挂载**之前**已存在于 DOM

- `attach` 用 Teleport 实现，Teleport 的 `to` 目标在挂载时必须已存在于 DOM（理想是 Vue 应用 DOM 树外部的元素）。
- 若目标元素也由 Vue 渲染，必须确保**先**挂载该元素，**再**挂载 Teleport。
- 踩坑表现：attach 到某个动态生成节点时第一次打开正常、后续报目标不存在 / 样式错位。

### 7.4 🔴 `scoped` 样式对 **列 `render` 里 `h()` 动态渲染的元素**不命中（2026-10-22 实测）

**结论：表格列 `render: (row) => h('div', { class: 'xxx' }, ...)` 造出来的元素，`<style scoped>` 里的 `.xxx` 规则对它完全不生效。**

- Vue 的 scoped 依赖**编译期给模板里的元素**注入 `data-v-xxx`；
  `h()` 造的 VNode **没有这个属性** → 选择器 `.xxx[data-v-xxx]` 匹配不上。
- 症状极具迷惑性：**源码规则完全正确、lint / 编译 / 单测全绿，渲染却是裸的**。
- 2026-10-22 实测踩了三次：两行日期被排成两**列**（`grid-template-columns: auto auto` 是行优先填充）、
  图标越出 hover 高亮块、日期在「/」处折行把图标甩到上一行 —— **连续三轮改 CSS 都没生效**，
  根因是规则压根没命中（`getComputedStyle` 读出来是 `display: block`，而规则写的是 `display: flex`）。

**修法**：
1. 这类样式放**非 scoped** 的 `<style>` 块（类名要够独特，或挪进 `glass.css`）；
2. 或改用 naive 组件自带的 class（自带样式，不依赖 scope）；
3. 验证：`getComputedStyle(el).display` 是不是你以为的那个值。

**扫描器**（已入库）：`web/app/scripts/check-h-render-scope.mjs`（`npm run check:render-scope`）
→ 用 `@vue/compiler-sfc` 解析每个 SFC 的 style 块归属，列出「scoped 块里有、但元素只由 h() 渲染」的类。
**当前基线：23 处失效**（设置中心若干页 + DemandList + GlobalSearch），均为既有遗留。

> 与 §7.1 是同一族问题（scoped 打不中「不在自己模板里的节点」），只是触发方式不同：
> §7.1 是 **Teleport**，这里是 **`h()` 动态渲染**。

### 7.5 🔴 HTML 注释写在**组件标签的属性列表中间**会打断模板属性解析（2026-10-22 实测）

- 在 `<n-modal ... :style="..." <!-- 注释 --> :content-style="...">` 这种写法里，
  Vue 模板编译器会把注释当成属性解析的中断点 → **后面的属性被当成正文渲染**
  （截图里弹窗内容直接显示 `:content-style="{ height: 'min(220px, ...)' }"` 这段源码文本）。
- **注释一律放在标签之外**（`<n-modal>` 之前），别塞进属性列表中间。

### 7.6 🔴 `h(组件, { class })` **同样不命中** scoped（2026-10-22 浏览器实测）

§7.4 的结论对**原生标签**成立，对**组件**同样成立 —— 但这一条最初漏了，因为当时的
扫描器正则只匹配 `h('小写标签', { class: 'x' })`，漏掉 `h(NTag, { class: 'x' })` 形态。

**浏览器实测证据**（Chrome，`RotationResourcePanel.vue` 的 `.saturation-cell`）：

| 检查项 | 实测值 |
|---|---|
| 编译后规则选择器 | `.saturation-cell[data-v-ba9f44de]` |
| 元素实际属性 | **无任何 `data-v-*` 属性**（`h(NTag, ...)` 渲染的组件根元素也不带） |
| 结论 | 选择器不匹配 → **scoped 规则根本不命中** |

⚠️ **判据必须用「非继承属性」**——否则会得到假阳性：
`.saturation-cell` 声明的是 `font-variant-numeric: tabular-nums`，
computed 里看着「生效了」，其实是**父级 `.n-data-table-table` 继承来的**
（实测 `parentTableFV = "tabular-nums"`）。若拿继承属性当判据，会误判成「规则命中」。

> 结论：**任何在 `render` 里用 `h()` 造的元素，都拿不到父组件的 scope id**，
> 无论它是原生标签还是组件。所以这类样式一律放非 scoped 块。

### 7.7 🟡 静态门禁对「样式是否生效」**零信号**（2026-10-22 复盘）

这是「同一个样式问题反复返工」的**根本原因**，不是某个 CSS 写法的错。

| 门禁 | 能发现「规则没命中」吗 |
|---|---|
| `eslint` / `vue-tsc` / `stylelint` / `vitest` | ❌ 全绿 —— 它们只验证**源码**，不验证**渲染** |
| 源码评审（读 CSS 语义） | ❌ 「规则写得对」≠「规则命中」 |

所以会出现「**代码看着完全正确、lint/编译/单测全绿、渲染却是裸的**」。
连续三轮改 CSS 都没生效，正是因为三轮都在调一个**从未生效的规则的数值**。

**必须先判「命中」再调数值**：

```js
// ① 规则命中了吗？—— 不命中就别谈调数值
getComputedStyle(el).display   // 写的 display:flex，读出来是 block → 规则压根没命中

// ② 几何对吗？—— 用 getBoundingClientRect 量，别靠目测
el.getBoundingClientRect()    // 实际 top/height/width
```

**门禁已入库**（见 §7.4 + 本节）：

- `npm run check:render-scope` —— 扫「scoped 块里有、但元素只由 `h()` 渲染」的类；
  已覆盖 `h('div', ...)` / `h(NTag, ...)` / `class` 数组三种形态。
- 基线机制：`scripts/render-scope-baseline.txt` 登记存量（当前 32 处），
  `--strict` **只拦新增**（与仓库既有「只许减少、不许新增」门禁同源思路）；
  存量清完后基线清空即自动变严格门禁。
- CI 已接独立 job `ui-render-scope`（硬门禁）。
- 运行时自证：`npm run shot`（截图）+ `getComputedStyle` 量几何 —— 见
  `web/app/e2e/README-shot.md`。

---

## 8. 🔴 内嵌媒体预览（iframe）被 `X-Frame-Options` 静默拦截（2026-10-21 实证，commit `1a43ee37`）

**结论：后端对 media 响应下发 `X-Frame-Options: DENY` 时，`curl` 能取到 200 字节完整，浏览器却拒绝渲染 iframe → 用户看到「预览失败」。这是「链路全通但页面报错」的典型形态。**

### 8.1 复现与判定

| 检查项 | 现象 |
|---|---|
| `curl -s -D - -o /dev/null <pdf_url>` | `200`、`content-type: application/pdf`、`content-length` 正常 |
| 同响应头 | **含 `x-frame-options: DENY`** ← 真凶 |
| 页面 `<iframe :src="pdfUrl">` | 浏览器原生「预览失败 / 无法加载」 |

根因链：

1. `config/settings/base.py` 的 `X_FRAME_OPTIONS = 'DENY'` + `XFrameOptionsMiddleware` 对**所有**响应（含 `/media/`）加该头。
2. dev 页面在 `:5212`，Vite 把 `/media` 代理到 `:8000` —— **端口不同即跨源**，`DENY` 无条件禁止任何 framing（`SAMEORIGIN` 也只允许同源）。
3. `curl` 不执行 framing 检查，故 200；浏览器渲染即被拦截。

> 判定要点：**只要 `curl` 200 但浏览器报预览失败，第一件事查 `x-frame-options` 与 CSP `frame-src`**，不要反复怀疑路径/权限/Content-Type。

### 8.2 修法（前端 blob 方案，推荐）

不动全局安全头（`DENY` 对其他端点仍是正确配置），改由前端经鉴权 `fetch` 取为 blob，用**同源** `objectURL` 内嵌：

```ts
const resumeObjectUrl = ref('')
async function loadResumePreview() {
  const url = resumeFileUrl.value
  if (!url) return
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token')
  const resp = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  resumeObjectUrl.value = URL.createObjectURL(await resp.blob())
}
// 模板：<iframe :src="resumeObjectUrl" />
onBeforeUnmount(() => { if (resumeObjectUrl.value) URL.revokeObjectURL(resumeObjectUrl.value) })
```

优点：① `blob:` URL 属同源，不受 `X-Frame-Options` 约束；② 自动携带 `Authorization`（`SECURE_MEDIA_DOWNLOAD` 的 `/api/v1/media/secure/...` 端点同样可用）；③ 前端可感知失败并回退为「下载」引导，避免浏览器原生白屏报错。

### 8.3 配套必做

- **必须 `URL.revokeObjectURL` 释放**（`onBeforeUnmount` + URL 变更时先 revoke），否则反复切换候选人会持续占用内存。
- **必须有失败态**：`fetch` 失败时展示「加载失败 + 下载按钮」，不许留空白或让浏览器原生错误页常驻。
- ⚠️ 若后端改用 `SAMEORIGIN` 且前端与后端**同源**（生产环境 Django 同时 serve 前端与 media），可省掉 blob 层；但 dev 跨端口形态下 `SAMEORIGIN` 依然会被拦，故 blob 方案通用性更好。
- ⚠️ 排查时顺手确认无 CSP 限制：`grep -rn "content-security-policy\|frame-src\|default-src"`，`blob:` 需被 `frame-src`/`default-src` 允许。

---

## 9. 🔴 `n-menu` 折叠态浮出**只对根级子菜单生效**（2026-10-21 实证）

**结论：菜单里若用 `type:'group'` 分组，组内的「可展开父项」在折叠态永远浮不出二级菜单 —— 不是样式问题，是 naive 的浮出载体只挂在根级子菜单上。**

### 9.1 症状

折叠成 64px 后，「公司信息管理 / 组织管理 / 权限管理 / 候选人信息 …」这些图标：

- hover **不弹**二级菜单；
- 点击也**没反应**（父项 key 不是路由，`handleMenuClick` 只处理 `/` 开头的 key）。

现象上就是「一排死图标」。**同一套代码在主侧栏却是好的** —— 差别只在主侧栏没有分组层。

### 9.2 根因（源码两行）

```
menu/src/utils.mjs   itemRenderer:  root: level === 0
menu/src/Submenu.mjs render:        this.root ? h(NDropdown, …) : h('div', …)
```

- 浮出载体 `NDropdown`（`trigger:'hover'`）**只在 `root === true` 时才挂**；
- `root` 由 `level === 0` 决定 —— 即**只有菜单根级的子菜单**才有浮出；
- 分组（`type:'group'`）的子项 `level` 是 1 → `root === false` → 走普通 `div` 分支 → 没有浮出载体。

另：`dropdownEnabled` 还要求 `mergedCollapsedRef`（菜单整体折叠）为真 —— 所以**只有折叠态**才有浮出，展开态是就地展开。

### 9.3 修法

**折叠态把分组打平**，组内条目提升为根级 → 父项回到 `level 0` → 原生浮出直接生效：

```ts
// 折叠态：分组打平 + 组间补 divider（保留视觉分组）
const subMenuOptions = computed(() => {
  const filtered = filterMenuByPermission(rawOptions, canAccess)
  return collapsed.value ? buildCollapsedMenuOptions(filtered) : filtered
})
```

- 展开态**保持分组结构不变**（分组标题往往是主要导航线索，不能丢）；
- 组间用 `type:'divider'` 补分隔线（折叠态看不到组标题了）；
- 兜底：折叠态点父级图标 → 展开侧栏 + 展开该分组及其祖先，避免仍是死路。

本项目落点：`web/app/src/utils/settingsMenu.ts`（`buildCollapsedMenuOptions`）+ `pages/settings/SettingsLayout.vue`。

> ⚠️ 别用「自己写 hover 浮层」去补：naive 的原生浮出已经够用，问题只在**层级**不在样式。
> 同理，也别指望改 CSS 能救 —— 非根级分支根本没有 `NDropdown` 可挂。

---

## 10. 关联文档

- 设置页滚动契约（`.page-body` 滚动链） → `docs/04-ui/SETTINGS_PAGE_STRUCTURE.md`
- **UI 改动的截图自证工具链**（系统 Chrome + 后端签发 token + 路由直截） → `web/app/e2e/README-shot.md`
- 设置侧栏折叠态悬浮浮出（分组打平 → 父项回根级） → 本文 §9
- 后端序列化器字段类型陷阱（同批实证） → `docs/06-runbook/ENGINEERING_RULES.md` §15
- 表单弹窗遮罩关闭守卫（useCloseGuard 接法） → `docs/04-ui/SETTINGS_PAGE_STRUCTURE.md` §6.1
- 标准简历三层结构 + 拖拽 → `docs/04-ui/UI_STANDARD.md` 附录 B
- 分页统一组件 → `docs/04-ui/UI_STANDARD.md` §8.2
- 工程铁律（CSV BOM/PATCH 500/序列化器） → `docs/06-runbook/ENGINEERING_RULES.md`