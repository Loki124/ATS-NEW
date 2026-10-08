# Naive UI 2.44.1 实战坑与 Vue 库联动反模式
> 最后更新：2026-10-08（依据 git 最后提交）

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

## 7. 关联文档

- 设置页滚动契约（`.page-body` 滚动链） → `docs/04-ui/SETTINGS_PAGE_STRUCTURE.md`
- 表单弹窗遮罩关闭守卫（useCloseGuard 接法） → `docs/04-ui/SETTINGS_PAGE_STRUCTURE.md` §6.1
- 标准简历三层结构 + 拖拽 → `docs/04-ui/STANDARD_RESUME_SETTINGS.md`
- 分页统一组件 → `docs/04-ui/USE_TABLE_PAGINATION.md`
- 工程铁律（CSV BOM/PATCH 500/序列化器） → `docs/06-runbook/ENGINEERING_RULES.md`