# 招聘流程 Modal 视觉/交互缺陷诊断报告

> 触发: 用户报障「招聘流程的新增和编辑弹窗样式太乱了体验感极差」
> 截图: `/Users/loki/.workbuddy/clipboard-images/clipboard-2026-08-30T05-17-24-920Z-7dbabc32.png`
> 代码: `web/app/src/pages/settings/ProcessDetailModal.vue`（2291 行）
> 模式: `mode === 'edit' | 'create'`（截图对应）vs `mode === 'view'`（只读，HERO 含编辑按钮）

---

## 1. 设计目标（应有的样子）

招聘流程弹窗是**设置页的复杂表单**，不是 marketing 页。它应该有：
- **A 单一主线**：编辑一个流程（基本信息 → 适用范围 → 阶段流程 → 保存）
- **B 字段节奏统一**：所有单值字段同高 baseline，所有 textarea 同高，section 间同节奏
- **C 视觉权重三段**：HERO（身份）→ field group（操作）→ save bar（兑现）
- **D 320-1280 自适应**：760px 是常见宽度，但内容弹性收放
- **E 微文案符合规范**：动词 + 宾语、无技术参数混排

---

## 2. 硬证据：截图 ↔ 代码对照

### P0-1 「不限」被截断成两行（截图最显眼痛点）

**截图证据**：每张 scope-card 右侧「不限」字样换行成"不\n限"两行。

**根因（CSS 1882-1901）**：
```css
.scope-card__mode {              /* L1893 */
  display: flex;
  align-items: center;
  gap: 6px;                      /* radio group 与 count 之间只 6px */
  font-size: 11px;
}
```
而 `__mode` 内部的 `<n-radio-group>` 是 `inline-block` + 不压缩，紧随其后的 `__count` span 宽度被挤压后浏览器对单个汉字换行。

**修复方向**：
- A: `__mode` 拆成两行（radio 占一行，count 占一行右对齐），完全分离两个控件
- B: `__mode` 保持一行但 radio group `max-width: calc(100% - 50px)` + `__count` 固定 `width: 40px; text-align: right`
- **推荐 B**，更紧凑且不增 card 高度

### P0-2 流程名称 input 出现两次（数据-视觉冗余）

**代码证据**：
- L383-388（HERO 内）：`<n-input v-model:value="editForm.name" size="large" placeholder="流程名称" class="hero__title-input" />`
- L413-416（基础信息 section）：`<div class="field-row"><span class="field-label">流程名称</span><n-input v-model:value="editForm.name" placeholder="..." class="field-input" /></div>`

**两张图互相 sync**（绑同一字段），但用户不知道哪个是"权威"，切换焦点时输入会被滚动打断。

**修复方向**：
- A: 删掉下方"流程名称"行（推荐）—— HERO 标题已经是 name 的 primary 入口
- B: 删掉 HERO 标题 input，统一用基础信息里的一行 —— 但失去 HERO 品牌位

**推荐 A**：保留 HERO 品牌位 + 强焦点体验，下方基础信息只保留"流程说明、适用范围组合、是否启用、校验简历评分、流转异常提示"5 项。

### P1-3 字段垂直基线不齐

**截图证据**：「适用范围组合」radio、「是否启用」tag、「校验简历评分」Switch 三行同样的 field-row，但视觉基线明显跳。

**根因**（CSS 1799-1815）：
```css
.field-row { display:flex; align-items:center; gap:var(--space-3); min-height:36px; padding:6px 0; }
.field-row--block { align-items: flex-start; padding: var(--space-2) 0; }
```
- 同行 radio / tag / switch 高度差：n-radio-group ~28px / n-tag ~22px / n-switch ~16px
- `align-items:center` 虽然垂直居中，但 baseline 不齐 —— 人眼会觉得"靠上 / 靠下"

**修复方向**：
- A: 全部改成 `align-items:flex-start; padding-top:8px` —— baseline 对齐
- B: 用 `<n-form>` + `n-form-item` 替手写 field-row —— Naive 自带 baseline 管理

**推荐 B**：根本解。手写 field-row 灵活但 baseline 难管。但改动面更大，可分两步走（先 A 应急、后 B 治理）。

### P1-4 「全部满足 (AND)」混排英文

**代码证据**：L430-431
```vue
<n-radio value="ALL">全部满足 (AND)</n-radio>
<n-radio value="ANY">任一满足 (OR)</n-radio>
```

**违反 R-204 微文案**：技术参数括号混排。AGENTS.md 没明确禁，但与腾讯系产品文案不一致。

**修复方向**：
- A: 直接去掉 `(AND)` / `(OR)` —— 中文表述够清晰
- B: 改为「组合方式：全部满足」「组合方式：任一满足」section 标题旁以 Radio 小按钮组呈现 —— 信息架构更清晰

**推荐 A**，最低改动。

### P1-5 「已停用（不可改）」用 n-tag 表达

**代码证据**：L434-437
```vue
<div class="field-row">
  <span class="field-label">是否启用</span>
  <n-tag size="small">{{ data.status === 'ACTIVE' ? '启用中' : '已停用' }} (不可改)</n-tag>
</div>
```

**问题**：n-tag 设计为可点的轻量 status badge，但这里它是"被禁用的开关"，视觉上像一个静态标签，违反 n-radio / n-switch 等真实控件的对齐预期。

**修复方向**：
- A: 用 disabled 的 `<n-switch>` 替 n-tag —— 控件矩阵一致：`Radio | Radio | Switch | Switch`
- B: 整行移除"是否启用"——基本信息里"是否启用"是流程级状态，不属于流程本身可编辑字段

**推荐 B**：是否启用是流程级生效开关，应该与"保存后立即生效吗？"解耦。不在 form 里展示反而合理。

### P1-6 4 个 scope-card 在 760px 弹窗挤

**截图证据**：每张 scope-card 里 `<n-select>` 的 placeholder 「留空 = 不约束」会被垂直挤压（虽然此刻是占位）。

**根因**：
- `:cols="4"` 在 760-popup(含 ~28px padding) → 每列 `(760-28*2-30)/4 ≈ 168px`
- 168px 减去 `padding: 10px var(--space-3)` ≈ 内宽 144px
- n-select 单行最少需要 ~120px 容纳 placeholder —— 危险边缘

**修复方向**：
- A: 改为 `:cols="2"` 两行两列（推荐）—— 弹窗宽变为 760 时，4 个 card 排 2×2，每列 ~360px，select 宽松
- B: 弹窗宽度从 760 → 880（在 1280 屏上仍能容）

**推荐 A+B**：宽到 880，列变 2，节奏更稳。

### P1-7 textarea 高度不一致

**代码证据**：L419（rows=2）vs L444（rows=3）—— 流程说明 2 行、流转异常提示 3 行。

**截图证据**：流程说明 2 行 + 边框 = 视觉到 textarea 底边比下面"流转异常提示"少一行，引起不必要的视觉跳动。

**修复方向**：统一 `:rows="3"`（推荐）。

### P2-8 页面式 modal 反模式

整个 form ≈ 900px 高，但截图只看到顶部 ~600px，弹窗**没有 `max-height: 90vh` + 内滚动**收口，导致用户必须滚浏览器才能看「保存」按钮（footer）。

**修复方向**：n-modal 增加 `:style="{ maxHeight: '90vh' }"` + body `overflow-y:auto`。

---

## 3. 修复方案（按执行顺序）

### 单个原子提交（推荐）：PROCESS_MODAL_V3_REDESIGN

| Phase | 内容 | 文件 | 风险 |
|---|---|---|---|
| P0-1 | 修 `.scope-card__count` 不换行（推荐 B） | ProcessDetailModal.vue:1893-1901 | 低 |
| P0-2 | 删除基础信息 section 里"流程名称"行 | ProcessDetailModal.vue:413-416 | 低 |
| P1-3 (A) | `.field-row{align-items:center}` → `flex-start; padding-top:8px` | ProcessDetailModal.vue:1799-1815 | 低 |
| P1-4 | radio label 去 `(AND)/(OR)` | ProcessDetailModal.vue:430-431 | 零 |
| P1-5 | 移除"是否启用"行（基础信息里） | ProcessDetailModal.vue:434-437 | 低 |
| P1-6 | `:cols="4"` → `:cols="2"` + 弹窗宽 760→880 | ProcessDetailModal.vue:21, 461 | 中（视觉重排） |
| P1-7 | `:rows="2"` → `:rows="3"` | ProcessDetailModal.vue:422 | 零 |
| P2-8 | n-modal 加 `max-height: 90vh` + `overflow-y:auto` | 同上 + n-modal preset | 低 |
| - | 单测契约保留（4 条不变量：.stage-card / .stage-card__system-badge / data-testid=btn-enter-edit / emitted('enterEdit')）—— Phase1 完成后必须跑测试 | `__tests__` | — |

### 验证（必做）
1. **静态 [S]**：grep 验证 4 条不变量都在；grep 验证 `_field-row` / `_scope-card` 结构未破
2. **构建 [S]**：`npm run build:nocheck` 必须 green
3. **dev-server [R]**：localhost:5212 必须能打开
4. **人眼 [H]**：硬刷新后看：
   - 编辑弹窗：基础信息只剩 5 行，"流程名称"不再重复
   - scope-card：4 个变 2×2，每张里"不限"不换行
   - 弹窗 880 宽，footer 不被截断
5. **回归 [R]**：view 模式（HERO 编辑按钮 + 字段行 label:value）保持不变

---

## 4. 风险标注（指挥官规则）

### 4.1 单测契约
`ProcessDetailModal.vue` 头注释（L11-15）明示 4 条不变量，**任何修改 MUST 保留**：
- `.stage-card` = 每 link 一个根容器
- `.stage-card__system-badge` = 首末 2 个
- `[data-testid=btn-enter-edit]` = view 态 HERO 编辑按钮
- `emitted('enterEdit')` = 点击编辑触发

### 4.2 View 模式不能动
本报告所有修复只针对 edit/create 模式（line 376+）。View 模式（line 28-375）用户没报障，**禁止顺手改**。

### 4.3 其他 modal 类比
`StageRuleConfigModal.vue` 可能有相同 scope-card 模式（如共用 .scope-card 样式是 scoped 则独立）。**本次只改 ProcessDetailModal 一处**；其他 modal 需独立报障。

### 4.4 不在本次范围
- `RecruitmentStage.vue` / `RecruitmentRound.vue` 上轮已修，本轮不动
- 阶段流程 section（编辑）—— 用户截图未到，不动

---

## 5. 状态

- [x] 诊断报告（本文档）
- [ ] 等用户拍板（按 A 全做 / 按 B 仅 P0 / 按 C 出修复预览图）
- [ ] 实施 + 提交 + 推送
- [ ] dev-server / 用户硬刷新确认

---

_生成于 2026-08-30 13:17 GMT+8（兵哥指令触发）_
