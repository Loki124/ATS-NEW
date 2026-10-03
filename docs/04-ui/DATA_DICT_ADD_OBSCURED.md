# 数据字典「新增内容被遮挡」诊断报告
> 最后更新：2026-09-07（依据 git 最后提交）

> 触发: 用户报障「数据字典中, 新增内容时被遮挡, 无法填写」
> 截图: `/Users/loki/.workbuddy/clipboard-images/clipboard-2026-08-30T05-22-50-740Z-154730e6.jpg`
> 代码: `web/app/src/pages/settings/DataDictionary.vue`(1032 行)

---

## 1. 设计目标(应有的样子)

新增一行元素后, 用户应能:
- **A** 看到新行编辑器完整可见(input + 操作按钮)
- **B** 输入不被打断(滚动到位、焦点不丢)
- **C** 行内"取消"(撤销这一行)与底部"取消"(离开页面)从视觉上分离

---

## 2. 硬证据: 截图 ↔ 代码对照

### P0-1 新行 input 下半截被遮挡(用户痛点根因)

**截图证据**:
- 行内 input(代码 / 英文 / 描述)只能看到 placeholder **上半截**, 下半截消失
- 行内 "保存 取消" 按钮与底部 sticky `提交栏` 的 "取消 提交" 按钮**几乎水平对齐** → 两个"取消"重叠

**根因链路**:
- `.section--elements` (L928-935) `max-height: calc(100vh - 360px)` 限定 elements 卡的最大高度
- `.el-table-scroll` (L978-983) `position: absolute; inset: 12px 16px; overflow: auto` 表格滚动容器填满 elements 卡
- `.submit-bar` (L1022-1030) `position: sticky; bottom: 16px; z-index: 10` 黏在视口底部, 高度 ~64px
- **未给 `.el-table-scroll` 预留底部 padding** → 滚动到底的最后一行(包括新加的 editing 行)被 sticky submit-bar 覆盖约 64px

**修复方向**:
- A: `.el-table-scroll { padding-bottom: 80px; }` —— 仅一行业务 CSS, 零行为变化(推荐)
- B: 把 sticky submit-bar 改成 `position: fixed; z-index: 100` + 给 `.page-container` 配套 `padding-bottom: 80px`
- C: 新行从 inline 改为卡片展开式(重, 不推荐)

**推荐 A**: 最小风险、零行为变化.

### P0-2 行内「取消」按钮 vs 底部「取消」按钮冲突

**代码证据**:
- L222 行内 editing 态: `<n-button size="tiny" @click="cancelRow">取消</n-button>`
- L270 底部 sticky: `<n-button size="large" @click="backToList">取消</n-button>`

**截图证据**: 当新行在最后一行 inline 编辑时, 行内"取消"和 sticky 栏"取消"**横坐标重叠, 看起来像一个按钮**.

**视觉层级污染**: 两个同义不同作用域的按钮挨在一起, 用户认知负担陡升.

**修复方向**:
- A: 行内 editing 态的"取消"改成 × icon button(放在行首, 与 sticky 栏分隔开)。hover 提示"撤销" (推荐)
- B: 行内 editing 态只保留"保存", "取消"改为 Esc 键盘事件(架构性改, 风险高)

**推荐 A**: 改 `cancelRow` 按钮为 n-icon + text, 与 sticky 栏完全不同的视觉权重.

### P1-3 sticky submit-bar 无背景穿透防护

**代码证据**: L1025 `background: var(--glass-bg-card)` -- 不透明卡片背景, 但**滚动时一旦 z-index 飘移, 内容仍可能透出**.

**修复方向**:
- `.submit-bar` 加 `backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px)` -- 滚动时内容被柔和模糊
- 现有 `box-shadow: 0 6px 24px var(--overlay-scrim-weak)` 是 elevation 信号, 与 backdrop-filter 互补

---

## 3. 修复方案(按执行顺序, 单原子提交)

| Phase | 内容 | 行数 | 风险 |
|---|---|---|---|
| P0-A | `.el-table-scroll` 加 `padding-bottom: 80px` | 1 行 | 低(零行为变化) |
| P0-B | 行内 editing 态"取消"按钮 → × icon button(行首, hover 提示"撤销") | 5-8 行 | 低 |
| P1 | `.submit-bar` 加 backdrop-filter blur | 2 行 | 低 |
| 验证 | grep `.el-table-scroll / .submit-bar / cancelRow` + build | -- | -- |

### 验证清单
1. **静态 [S]**:
   - `grep -n "el-table-scroll" web/app/src/pages/settings/DataDictionary.vue` 应至少 3 处(定义 + 引用 + padding-bottom)
   - `grep -n "backdrop-filter" web/app/src/pages/settings/DataDictionary.vue` 应至少 2 处(顺带沿用习惯)
2. **构建 [S]**: `npm run build:nocheck` 必须 green(先 `mv dist dist_old_*` 避 safe-delete guard)
3. **dev-server [R]**: 硬刷新 localhost:5212
4. **人眼 [H]**:
   - 任意加一行新元素, 滚动到底 → 应能**完整看到 input** + 行内 ×icon
   - 行内 ×icon 应在行首(元素名称列), 不与底部 sticky 栏的"取消"重叠
   - 拖动滚动时, sticky 栏柔和模糊, 不挡内容
5. **回归 [R]**: 字典头信息编辑 / 字典列表 / 新增字典弹窗 全部不变

---

## 4. 风险标注(指挥官规则)

### 4.1 不动范围
- view 模式不动(本文件只有 edit 模式, 整页就是 edit 状态)
- `submit-bar` 内部按钮不变(只改样式)
- `.el-table` / `.el-row / .el-cell` 都不动(只动 .el-table-scroll)
- 新增字典弹窗(L278)不动

### 4.2 已知可行的低风险
- `padding-bottom` + `backdrop-filter` 是设计系统约定的(.toolbar、.glass-panel 都已用到)
- icon button 替换文本按钮是 Naive UI 推荐做法

### 4.3 不在范围
- 把 inline edit 改为卡片 modal(重写, 不推荐)
- 改元素树多级嵌套逻辑(用户没报障)
- 提交栏的设计位置变更(顶部 toolbar？已有)

---

## 5. 状态

- [x] 诊断报告(本文档)
- [ ] 等用户拍板(按 A 全做 / 按 B 仅 P0-1 / 按 C 先看预览)
- [ ] 实施 + 提交 + 推送
- [ ] dev-server / 用户硬刷新确认

---

_生成于 2026-08-30 13:22 GMT+8(兵哥指令触发)_
