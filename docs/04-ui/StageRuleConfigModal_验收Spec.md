# 阶段配置规则组件（StageRuleConfigModal.vue）完整验收 Spec
> 最后更新：2026-09-23（依据 git 最后提交）

> 角色：software-qa-engineer（ATS-NEW expert）
> 对象：`web/app/src/pages/settings/StageRuleConfigModal.vue`
> 原型：`/Users/loki/Downloads/deepseek_html_20260907_02a9fb.html`
> 工作目录：`/Users/loki/WorkBuddy/招聘助手/ATS-NEW`
> 日期：2026-09-07
> 状态：⚠️ **存在 2 个阻断级视觉/数据冲突，需产品+架构决策后工程方可开工**

---

## 0. 摘要：QA 在开工前必须升级的 6 个硬冲突（证据驱动）

| # | 冲突 | 原型硬编码 | 项目真实 Token / API | 判定 |
|---|------|-----------|---------------------|------|
| C1 | 品牌主色 | `#4e6bff`（蓝） | `--brand` = `#6366F1`（靛紫，brand-tokens.css:10） | ❌ 互斥，需决策 |
| C2 | icon 底色 | `#eef1ff` | `--brand-a12`（12% 靛紫透色） | ✅ 走 token，色相变靛紫 |
| C3 | card 底色 | `#f7f8fa` | `--g1` = `#F1F5F9`（无 `--bg-subtle` 这个 token） | ✅ 近似，用 `--g1` |
| C4 | 弹窗阴影 | `0 20px 60px rgba(0,0,0,.18)` | **不存在 `--shadow-modal`**；仅有 `--shadow-xs/sm/card/panel/elevated/2xl` | ❌ 映射错误 |
| C5 | 圆角 | `16/12/10/8/6` | 仅 `--radius-sm:6px` / `--radius-md:16px` / `--radius-lg:20px`；**无 12/10/8 token，无 `--radius-xs`** | ❌ 映射错误 |
| C6 | 层级 z-index | 主1000/二级1100/三级1050/popup9999 | 项目 z-scale：`--z-dropdown:1000` `--z-drawer:1100` `--z-modal:1200` `--z-toast:1300` | ❌ 不可硬编码 |

**说明**：`tokens.css` 头注释明确写着"任何组件禁止再硬编码品牌色 / 模糊值 / 圆角"，AGENTS.md R-214 规定品牌色只能由 `brand-tokens.mjs` 生成。"严格还原原型"与"全部走 token"在 C1/C4/C5/C6 上**互斥**——QA 立场：**以设计系统 token 为准**，原型字面量偏差列为"视觉偏离"而非"实现错误"。C1 因涉及品牌主色，必须由产品/设计确认是否接受设计系统覆盖原型蓝。

**额外数据冲突（详见 §3/§5/§8）**：现有组件（commit 506a902）仍在读取**旧 schema** 字段（`matchType`/`conditionType`，见 `StageRuleConfigModal.vue:888-889`），而后端 `EntryConditionRule` 模型已是新 schema（`rule_name`/`expression`/`reject_message`/`items[]`/`status`/`rule_seq`）。且现有组件存在**已知丢数据 bug**（`StageRuleConfigModal.vue:986` 注释：进入条件从未被保存）。二者均为 ❌ 阻断项。

---

## 1. 功能矩阵（按 HTML 原型的 4 card + 3 二级 + 1 三级弹窗逐项）

### Card 1 — 进入条件（Entry Condition）

| 字段 | 控件类型 | 数据来源 API | 必填 | 校验 | 保存目标 | 视觉细节 |
|------|----------|-------------|------|------|----------|----------|
| 模块开关 entry.enabled | Naive `n-switch` toggle | `EntryConditionRule.status`（toggle 动作，detail=True POST `/entry-condition-rules/{id}/toggle/`） | 否（默认开） | — | `EntryConditionRule.status` | 右侧；on=var(--brand) |
| 规则配置按钮 | `n-button` text/primary | — | — | — | 打开二级"进入条件编辑"弹窗 | color var(--brand) |
| 规则表：执行条件 列 | 只读文本（表达式摘要） | `GET /api/v1/entry-condition-rules/?link={id}` → `expression` | 是（至少 1 条规则） | 表达式校验器（见 §4） | `EntryConditionRule.expression` | 表格行，分隔线 var(--g3) |
| 规则表：未满足提示 列 | 只读文本 | `reject_message` / `prompt` | 否 | ≤500 字 | `EntryConditionRule.reject_message` | — |
| 添加规则入口 | 文本按钮 + 图标 | — | — | — | 新增 `EntryConditionRule`（status=ENABLED） | + 图标 var(--brand) |
| 整体未满足提示（二级弹窗） | `n-input type=textarea` maxlength 500 | `EntryConditionRule` 顶层（或 link 级 prompt） | 否 | ≤500 | `reject_message`/顶层 prompt | show-count，error 红边 |

### Card 2 — 默认处理人（Default Processor）

| 字段 | 控件类型 | 数据来源 API | 必填 | 校验 | 保存目标 | 视觉细节 |
|------|----------|-------------|------|------|----------|----------|
| 数据来源 | `n-select` | 静态 4 项：需求中/职位中/候选人中/简历中（**前端常量，非 API**，需确认后端枚举 `PROCESSOR_SOURCE`） | 是 | 切换即重置下游 | `StageRule.processor_source` | 选项 padding var(--space-2) |
| 取值字段 | `n-select`（**依赖联动**） | 字段字典：14 组 `AR_FIELD_OPTIONS` 来自 `GET /api/v1/dictionary-items/?type_code=...` | 是 | 数据来源变更→清空重置 | `StageRule.processor_field` | 联动禁用态 var(--g1) 底 |
| 处理规则 | `n-select` | 静态：按顺序/按角色/指定人 等 | 是 | — | `StageRule.processor_rule` | — |

### Card 3 — 面试配置（Interview Config）

| 字段 | 控件类型 | 数据来源 API | 必填 | 校验 | 保存目标 | 视觉细节 |
|------|----------|-------------|------|------|----------|----------|
| 面试轮次（5 项：联合/综合/初试/复试/终试） | `option-grid`（多选标签+×删除+ +N 超额） | `GET /api/v1/dictionary-items/?type_code=interview_round` | 否 | 多选上限（见 §4 +N） | `StageRule.interview_rounds[]` | 选中态 var(--brand-soft) 底 + var(--brand) 文字 |
| 面试形式（4 项：现场/电话/视频/AI） | `option-grid`（同上） | `GET /api/v1/dictionary-items/?type_code=interview_mode` | 否 | 同上 | `StageRule.interview_modes[]` | 同上 |

### Card 4 — 流程自动化（Flow Automation，4 个 flow-block）

| 字段 | 控件类型 | 数据来源 API | 必填 | 校验 | 保存目标 | 视觉细节 |
|------|----------|-------------|------|------|----------|----------|
| 自动评估 · N+2 推荐免筛选 | `n-checkbox` | `StageRule.auto_eval_n2` | 否 | — | `StageRule.auto_eval_n2` | flow-block 白底（var(--surface)）radius var(--radius-sm) |
| 自动评估 · 引用前序双 A 一致意见 | `n-checkbox` | `StageRule.auto_eval_prev_aa` | 否 | — | `StageRule.auto_eval_prev_aa` | 同上 |
| 自动流转 · 条件 | `n-select` | 静态：满足下阶段进入条件(推荐)/不自动流转/无视下阶段进入条件/条件4/5/6 | 是（默认推荐） | — | `StageRule.auto_advance_type` | — |
| 自动流转 · 执行时机 | `n-select` | 静态：立即执行(默认)/不执行/延迟 1-20 工作日 | 是 | 选"延迟"时数字 1-20 | `StageRule.auto_advance_delay` | 联动数字 input |
| 自动跳过 · 模块开关 | `n-switch` | `StageRule.auto_skip_enabled`（或 `AutomationRule` 模型，见 §8） | 否 | — | 开关位 | 切换显隐规则表（max-height 动画，见 §4） |
| 自动跳过 · 规则表（规则名70/执行条件/执行动作120/操作140） | 表格 + 添加规则按钮 | `GET /api/v1/entry-condition-rules/` 或 `AutomationRule`（⚠️ 待定） | 否 | 每行表达式校验 | `AutomationRule[]` | 列宽用 token 间距 |
| 自动归档 · 模块开关 | `n-switch` | 同跳过 | 否 | — | 开关位 | 同上 |
| 自动归档 · 规则表（规则名/执行条件/执行动作150/操作140） | 表格 + 添加规则 + **查看已停用规则** 按钮 | 同上 | 否 | 同上 | `AutomationRule[]` | "查看已停用"开三级弹窗 |

### 二级弹窗 1 — 进入条件编辑

| 字段 | 控件类型 | 数据来源 | 必填 | 校验 | 保存目标 | 视觉细节 |
|------|----------|----------|------|------|----------|----------|
| 条件组容器（可加条件组，≤10） | 动态区块 | 本地 state | 是（≥1 组，每组≥1 条件） | 组内独立 `innerExpression`+`innerPrompt` | `EntryConditionRule.items[]`/表达式结构 | 区块分隔 var(--g3) |
| 条件组表达式 | `n-input` + popover 帮助 | 本地 | 是 | `(1 or 2) and (3 or 4)` 6 规则 + 禁止大括号嵌套 + 编号 1-N | `EntryConditionRule.expression` | 错误红边 var(--c-error)；popover 图标 hover |
| 整体未满足提示 | `n-input textarea` maxlength 500 | 本地 | 否 | ≤500 | `reject_message` | show-count |

### 二级弹窗 2 — 自动跳过编辑

| 字段 | 控件类型 | 数据来源 | 必填 | 校验 | 保存目标 | 视觉细节 |
|------|----------|----------|------|------|----------|----------|
| 规则名称 | `n-input` maxlength 50 | 本地 | 是 | ≤50，非空 | `rule_name` | 计数器 |
| 条件设置（多条件 + 表达式 + 弹窗） | 同二级弹窗1 | 本地 | 是 | 同表达式校验器 | `expression` / `items[]` | — |
| 执行设置 · 执行动作 | `n-radio-group` | 静态：跳过本阶段/直接通过/直接拒绝 | 是 | — | `action` | — |

### 二级弹窗 3 — 自动归档编辑

| 字段 | 控件类型 | 数据来源 | 必填 | 校验 | 保存目标 | 视觉细节 |
|------|----------|----------|------|------|----------|----------|
| 规则名称 | `n-input` maxlength 50 | 本地 | 是 | ≤50 | `rule_name` | — |
| 条件设置 | 同二级弹窗2 | 本地 | 是 | 同 | `expression` | — |
| 执行设置 · 锁定时长 | `n-input-number` | 本地 | 是 | >0 整数 | `lock_duration` | — |
| 执行设置 · 加时规则 | `n-input-number` | 本地 | 是 | ≥0 | `extend_rule` | — |
| 执行设置 · 生效方式 | `n-radio-group` | 静态：全部候选人/新进入候选人 | 是 | — | `effect_scope` | — |

### 三级弹窗 — 已停用规则（z-index 介于二级与主之间）

| 字段 | 控件类型 | 数据来源 API | 必填 | 校验 | 保存目标 | 视觉细节 |
|------|----------|-------------|------|------|----------|----------|
| 已停用规则表 | 表格 + 重新启用操作 | `GET /api/v1/entry-condition-rules/?link={id}&status=DISABLED`（或 `AutomationRule` 停用集） | — | — | 行内 `POST .../toggle/` 重新启用 | 关闭按钮（footer 或 header ×） |
| 关闭按钮 | `n-button` | — | — | — | 关闭三级弹窗 | — |

---

## 2. 视觉一致性验收清单

### 2.1 与 HTML 原型逐项比对

| 原型元素 | 原型样式 | 项目实现要求 | 标记 |
|----------|----------|--------------|------|
| 主弹窗尺寸 | 840×90vh | Naive `n-modal preset="card"` + `style="width:840px;max-height:90vh"` | ✅ 可达成 |
| 主弹窗圆角 | 16px | `var(--radius-md)` | ✅ |
| 主弹窗阴影 | `0 20px 60px rgba(0,0,0,.18)` | **无 `--shadow-modal`** → 用 `var(--shadow-2xl)`（0 28px 72px /.16）或新增 token（见 C4） | ❌ 待决策 |
| 主弹窗背景模糊 | glass | `var(--glass-bg-elevated)` + `backdrop-filter: blur(28px)`（--glass-blur-panel） | ✅ |
| Header 左侧 icon 32×32 | bg `#eef1ff` | `width/height:32px; background: var(--brand-a12)` | ✅（靛紫透，非蓝） |
| Header h2 标题 | "配置阶段规则 —— 阶段名" | `var(--text-h3)` + `var(--ink)` | ✅ |
| sub-tip "即时生效" | 圆角16 padding 2×10 color `#4e6bff` | `border-radius: var(--radius-pill)`（或 `--radius-sm`），`color: var(--brand)`，`padding: var(--space-1) var(--space-3)` | ❌ C1：色为靛紫 |
| close-btn 30×30 | — | 30px 方；hover `var(--brand-soft)` | ✅ |
| config-card | bg `#f7f8fa` radius 12 padding 14×16 | `background: var(--g1)`；radius **无 12 token → `--radius-md`(16) 或新增**（C5）；`padding: var(--space-3) var(--space-4)` | ❌ C5 半径 |
| flow-block | 白底 radius 10 padding 10×14 | `background: var(--surface)`；radius **无 10 token**（C5）；`padding: var(--space-2) var(--space-3)` | ❌ C5 半径 |
| switch 开关 | on/off | Naive `n-switch`；`--brand` 激活轨 | ✅ |
| 主按钮 | 确定/取消 | `n-button` type=primary（on-brand 前景 `var(--on-brand)`）；右侧 `justify-content:flex-end; gap: var(--space-2)` | ✅ |
| input.error 红边 | 红边 | `border-color: var(--c-error)` | ✅ |
| error-msg 红字 | 红字 | `color: var(--c-error)`；小字 `var(--text-small)` | ✅ |
| popover 帮助 | hover 触发 | Naive `n-popover` / `n-tooltip` | ✅ |

### 2.2 必须走的 token 路径（逐值映射，已用真实文件核对）

| 原型硬编码 | ❌ 用户给的映射 | ✅ QA 修正映射（依据 tokens.css / brand-tokens.css） | 备注 |
|-----------|---------------|---------------------------------------------|------|
| `#4e6bff` | `var(--brand)` | `var(--brand)`（实际 `#6366F1`） | C1：色相不同，需决策 |
| `#eef1ff` | `var(--brand-a12)` | `var(--brand-a12)`（brand-tokens.css:42） | ✅ |
| `#f7f8fa` | `var(--g1)` 或 `var(--bg-subtle)` | `var(--g1)`（#F1F5F9）；**`--bg-subtle` 不存在** | ✅ 用 --g1 |
| `0 20px 60px rgba(0,0,0,.18)` | `var(--shadow-modal)` | 无此 token → `var(--shadow-2xl)` 或新增 `--shadow-modal` | ❌ C4 |
| 16px | `var(--radius-lg)` | `var(--radius-md)`（16px，tokens.css:172） | ❌ 用户误标 lg |
| 12px | `var(--radius-md)` | **无 token**（closest `--radius-md` 16px） | ❌ C5 |
| 10px | `var(--radius-sm)` | **无 token**（closest 6/16） | ❌ C5 |
| 8px | `var(--radius-xs)` | **无 token，且 `--radius-xs` 不存在** | ❌ C5 |
| 6px | `var(--radius-xs)` | `var(--radius-sm)`（6px，tokens.css:171） | ❌ 用户误标 xs |
| 主 z 1000 | — | `var(--z-modal)`（1200） | ❌ C6 |
| 二级 z 1100 | — | `var(--z-drawer)`（1100） | ❌ C6 |
| 三级 z 1050 | — | **无 token**（介于 dropdown1000/drawer1100）→ 需新增 `--z-modal-nested` 或复用 | ❌ C6 |
| popup z 9999 | — | `var(--z-toast)`（1300）或新增 `--z-popup` | ❌ C6 |

> 任何 varent 未列于 tokens.css 的硬编码 hex/rgba/px 圆角，stylelint 应按 AGENTS.md 规则拦截（见 §7）。工程侧须先就 C4/C5/C6 三种"缺 token"情形给出统一方案（**建议**：在 tokens.css 补 `--shadow-modal`、`--radius-12/10/8`、z 层级 `--z-modal-nested`/`--z-popup`），否则验收无法"零硬编码"。

### 2.3 暗色模式覆盖验证（`body.dark`）
- ✅ 所有颜色走 token 后，`body.dark` 自动重排（tokens.css §14）——组件 CSS 不变即为合规。
- ⚠️ 但需实测复核：icon 底 `--brand-a12` 在 dark 下为 `color-mix(...brand-300 18% transparent)`（brand-tokens.css:76），淡靛紫在深玻璃上需肉眼确认对比度达标。
- ⚠️ `--g1` dark = `#0B1220`（极深），card 底色在 dark 下变深填充，需确认与 flow-block `--surface`(#1E293B) 的层级区分仍可见。
- ❌ 若工程为 C4/C5/C6 采用"新增 token"方案，新增 token **必须**在 `body.dark` 段同步重排，否则暗色破图。

### 2.4 响应式断点（HTML 原型有 768px / 480px 两段）
| 断点 | 预期行为 | 标记 |
|------|----------|------|
| ≥1024（桌面默认） | 840px 宽弹窗，4 card 竖向堆叠 | ✅ |
| ≤768px | 弹窗宽度→100vw（或 ≥calc(100vw-32px)）；card 内部字段单列；option-grid 换行 | ⚠️ 原型有 @media 但组件需显式实现 |
| ≤480px | 进一步压缩 padding 至 `--space-2`；按钮组纵向（取消/确定 仍 justify-end 但可换行）；表格允许横向滚动 | ⚠️ |
| 必跑 viewport | 1440×900 / 768×1024 / 375×667（见 §9） | ✅ |

### 2.5 嵌套弹窗 z-index 顺序
| 层级 | 原型硬编码 | 项目 token | 标记 |
|------|-----------|-----------|------|
| 主弹窗 | 1000 | `var(--z-modal)`=1200 | ❌ C6 |
| 二级弹窗（3 个） | 1100 | `var(--z-drawer)`=1100 | ❌ C6（命名应为 modal-nested） |
| 三级弹窗（已停用） | 1050 | 需新增（介于 dropdown/drawer） | ❌ C6 |
| popup / popover / tooltip | 9999 | `var(--z-toast)`=1300 或新增 `--z-popup` | ❌ C6 |

---

## 3. 数据动态化验收清单

| 数据项 | 是否走 API | 端点 / 来源 | 标记 |
|--------|-----------|-------------|------|
| 4 个 source（需求中/职位中/候选人中/简历中） | ⚠️ 待定 | 前端常量 or 后端枚举 `PROCESSOR_SOURCE`；若后端有枚举则走 API，否则静态常量（需在 spec 中决策） | ⚠️ |
| 字段字典 14 组 `AR_FIELD_OPTIONS` | ✅ 应走 API | `GET /api/v1/dictionary-items/?type_code=...`（dictionary/urls.py:7-8 已挂载） | ✅ |
| 阶段名（关联阶段 `STAGE_STATUS`） | ✅ | `GET /api/v1/stages/?status=ENABLED`（listStages 已支持 status 过滤，recruitment-process.ts:211） | ✅ |
| 字典值（如"能效BG 共89项"） | ✅ | `GET /api/v1/dictionary-types/{code}/` + `dictionary-items`（config/urls.py:120 已挂载） | ✅ |
| 处理人列表 | ⚠️ | `GET /api/v1/users/`（core/urls.py 已挂载）存在，但 `?role=` 过滤**未确认**——需验证 UserViewSet 是否支持 role 过滤 | ⚠️ |
| 面试轮次 5 项 | ✅ | `dictionary-items?type_code=interview_round` | ✅ |
| 面试形式 4 项 | ✅ | `dictionary-items?type_code=interview_mode` | ✅ |
| 进入条件规则集 | ✅ | `GET /api/v1/entry-condition-rules/?link={id}`（EntryConditionRuleViewSet，views.py:39） | ✅ |
| 表达式校验 | ✅ | `POST /api/v1/expressions/validate`（ExpressionValidationView，urls.py:88） | ✅ |

> ⚠️ **关键不匹配**：现有前端 `listEntryConditions`（recruitment-process.ts:313）与 `upsertEntryCondition` 返回/提交的字段仍是**旧 schema**（`matchType`/`conditionType`/`prompt`/`items`，见 `StageRuleConfigModal.vue:888-889`）。后端 `EntryConditionRule` 已是新 schema（`rule_name`/`expression`/`reject_message`/`items[]`/`status`/`rule_seq`）。**组件必须重写数据层映射**，否则读取 `conds[0].matchType` 为 `undefined` → 进入条件无法回填（见 §5、§8）。

---

## 4. 交互验收清单（边界场景）

| 场景 | 预期行为 | 标记 |
|------|----------|------|
| 模块开关切换（entry/skip/archive） | 规则表显隐用 `max-height: 0 ↔ 2000px` 过渡（`var(--duration-base)` 缓动） | ✅ |
| 模块关闭时规则是否保留 | 关闭 toggle **不删除**规则数据，仅隐藏；重开仍可见（state 保留，非清空） | ⚠️ 必须验证，禁止"关闭即丢" |
| 条件组：每组≥1 条件 | 删除最后一条条件时禁用"删除"或自动保留 1 条 | ✅ |
| 条件组上限 | 添加第 11 个条件组被拦截，提示"最多 10 个条件组"（`AR_MAX_CONDITIONS=10`） | ✅ |
| 表达式校验失败 | input 加 `.error` 红边（`var(--c-error)`）+ 下方 `.error-msg` 红字（`var(--c-error)`）+ **确定按钮 disabled** | ✅ |
| 表达式校验通过 | 清空 `.error` 与 `.error-msg`，恢复可保存 | ✅ |
| 表达式 6 规则 | `(1 or 2) and (3 or 4)` 合法；非法运算符/括号不匹配报错 | ✅ |
| 大括号嵌套禁止 | 含 `{` `}` 直接报错（原型规则） | ✅ |
| 编号范围 1-N | 引用未定义编号（如 5 但仅 3 条件）报错 | ✅ |
| 多选标签超额 +N | 超出可视数量显示 `+N` 折叠提示；点击展开 | ✅ |
| 标签删除 | 选中标签显示 × 图标，点击移除 | ✅ |
| 已停用规则重新启用 | 三级弹窗内行操作 → `POST /entry-condition-rules/{id}/toggle/` → 状态回 ENABLED 并从列表移除 | ✅ |
| 保存中（saving=true） | 禁止关闭弹窗（拦截 ESC / 遮罩点击 / 取消按钮置灰） | ✅ |
| ESC 关闭最顶层 | 仅关闭当前最顶层弹窗（三级→二级→主），逐层关闭 | ✅ |
| 全局点击关闭 popup | 点击空白处关闭所有 popover/tooltip（不关弹窗） | ✅ |
| modal 关闭复位 | `resetTransient()` 清空所有临时 state（表达式草稿、error、+N 展开、popup 打开态） | ✅ |
| 数据来源切换联动 | 切换"数据来源" → "取值字段"重置并重新拉字典（依赖联动） | ⚠️ 必须验证无残留旧值 |

---

## 5. 数据完整性验收

| 项 | 要求 | 标记 |
|----|------|------|
| 加载（opening） | `listEntryConditions` + `listStageRules` + `listStages` **并发**拉取，全部 resolve 才解除 loading（禁止部分就绪即渲染） | ✅ |
| 编辑模式回填 | 重新打开已配置 modal，所有 card 数据**无损回填**（进入条件规则集、处理人、面试配置、4 个 flow-block） | ❌ 现有组件有丢数据 bug（:986） |
| 已知丢数据 bug | `StageRuleConfigModal.vue:986` 注释明确："tab 切换 UI → activeTab 恒为 'auto' → 进入条件从未被保存"。**必须修复**：保存时遍历所有 card，而非只保存 activeTab | ❌ 阻断 |
| 保存原子性 | 全部子请求成功才关闭；任一失败 → toast 报错 **且不关闭**弹窗 | ✅ |
| 字段联动 | "数据来源"切换 → "取值字段"重置 | ✅（见 §4） |
| 数据回写一一对应 | `ruleName↔rule_name` / `expression↔expression` / `reject_message↔reject_message`（或 `prompt`）schema 字段对齐，无错位 | ❌ 旧→新 schema 映射待工程实现 |
| 进入条件 schema 迁移 | 旧 `matchType/conditionType/prompt/items` → 新 `EntryConditionRule[]{rule_name,expression,reject_message,items[],status,rule_seq}` | ❌ 待工程 |

---

## 6. 验收用例（QA 重点，≥15 个）

| # | 场景 | 前置 | 步骤 | 预期 | 视觉检查点 |
|---|------|------|------|------|-----------|
| 1 | Happy：完整配置并保存 | 已登录，进入某阶段设置 | 填 4 card → 确定 | 成功 toast，弹窗关闭，数据落库 | 主色为靛紫（非原型蓝，C1 偏离可接受） |
| 2 | 进入条件添加规则 | 打开二级"进入条件编辑" | 添加条件组→填条件→填表达式→填提示→保存 | 规则入表（执行条件/未满足提示列） | 表格分隔 var(--g3) |
| 3 | 表达式非法 | 同上 | 输入 `1 and (` 保存 | 红边+error-msg，确定禁用 | `var(--c-error)` 红边 |
| 4 | 表达式大括号 | 同上 | 输入 `{1 or 2}` | 报错"不允许大括号" | error-msg 显示 |
| 5 | 编号越界 | 3 条件引用 5 | 输入 `(1 or 5)` | 报错"编号超出范围" | — |
| 6 | 模块关闭保留 | 已配 skip 规则 | 关 skip 开关→重开 | 规则仍在（仅隐藏） | max-height 动画 |
| 7 | 条件组上限 | 二级编辑 | 连续添加至第 11 组 | 第 11 被拦截+提示"最多10" | — |
| 8 | 空条件组拦截 | 二级编辑 | 删光组内条件 | 禁用删除保留 1 条 / 提示 | — |
| 9 | 标签 +N | Card3 选超可视数 | 选 6+ 轮次 | 显示 `+N` | +N 折叠样式 var(--brand-soft) |
| 10 | 标签删除 | 已选轮次 | 点 × | 移除该项 | × 图标 hover |
| 11 | 数据来源联动 | Card2 | 切"数据来源" | "取值字段"清空并重拉 | 重置无残留 |
| 12 | 已停用重启用 | 有停用规则 | 开三级弹窗→点重启用 | 状态回 ENABLED，列表移除 | toast 成功 |
| 13 | ESC 逐层关 | 三层全开 | 连按 ESC | 三级→二级→主依次关 | 仅关最顶 |
| 14 | 保存中防关 | saving=true | 按 ESC/点遮罩 | 不关闭 | 取消按钮置灰 |
| 15 | 回填无损 | 已配置后关闭再开 | 重开 modal | 全部字段回填一致 | 无空字段 |
| 16 | 暗色回归 | body.dark | 全用例重跑 | 颜色随 token 重排，对比度达标 | 暗底可读 |
| 17 | 响应式 768 | viewport 768 | 打开 modal | 宽满屏，card 单列 | 无横向溢出 |
| 18 | 响应式 375 | viewport 375 | 配置+保存 | 按钮纵向，表格可横滚 | 无破图 |
| 19 | 字典动态 | 后端字典变更 | 拉面试轮次 | 展示最新字典项 | 非硬编码 |
| 20 | 表达式校验 API | 联网 | 输入合法式保存 | `POST /expressions/validate` 200 | 无 500 |

---

## 7. 硬证据清单（QA 必须产出）

| 证据 | 命令 / 方法 | 通过标准 |
|------|------------|----------|
| stylelint 零违例 | `./node_modules/.bin/stylelint "src/pages/settings/StageRuleConfigModal.vue"` | exit 0，无 `no-hardcoded-color` / `no-hardcoded-radius` 类告警 |
| vite 编译 | `vite dev` → curl `http://localhost:5173` | HTTP 200，终端无 `transform error` / `[vue/compiler]` 报错 |
| vitest（若有单测） | `vitest run StageRuleConfigModal` | 全部 pass（表达式校验器 6 规则、+N、上限边界须有单测） |
| e2e（agent-browser 真实交互） | auth 登录 → 打开 modal → 配置 4 card → 保存 → 重开回填 | 端到端无 console error，回填字段一致 |
| getComputedStyle 硬证据 | 对关键元素 `getComputedStyle(el)` 取实际值：主色 `rgb(99,102,241)`（#6366F1）、card 底 `rgb(241,245,249)`（#F1F5F9）、阴影含 `28px 72px`、圆角 16px | 每个 token 实际渲染值 = 设计系统定义值，**且 ≠ 原型硬编码值**（C1/C4 偏离需截图留档） |
| 暗色 getComputedStyle | `document.body.classList.add('dark')` 后复测 | 主色/底色随 `body.dark` 重排，无裸 hex 残留 |

> ⚠️ 若工程采用"新增 token"方案解决 C4/C5/C6，则 stylelint 通过标准改为"仅允许走 token"，新增 token 必须已登记于 tokens.css 且暗色段同步。

---

## 8. 已知风险与遗留项

| 风险 | 说明 | 责任方 | 标记 |
|------|------|--------|------|
| R1 品牌色冲突 C1 | 原型蓝 `#4e6bff` ≠ 系统靛紫 `#6366F1`。是否以设计系统为准？ | 产品/设计决策 | ❌ 阻断 |
| R2 阴影 token 缺失 C4 | 无 `--shadow-modal`，需新增或用 `--shadow-2xl` | 架构/工程 | ❌ 待决策 |
| R3 圆角 token 缺失 C5 | 无 12/10/8 token，需扩展 tokens.css | 架构/工程 | ❌ 待决策 |
| R4 z-index 冲突 C6 | 原型 1000/1100/1050/9999 违背项目 z-scale，须改 token | 架构/工程 | ❌ 待决策 |
| R5 schema 迁移 | 旧 `matchType/conditionType` → 新 `EntryConditionRule`（`rule_name/expression/reject_message/items[]/status/rule_seq`） | 工程 | ❌ 阻断 |
| R6 丢数据 bug | `StageRuleConfigModal.vue:986` 进入条件从未保存 | 工程 | ❌ 阻断 |
| R7 自动跳过/归档模型 | `versioning.py` 提及 `AutomationRule`/`TimeLimitRule` 继承体系——skip/archive 规则是否落到 `AutomationRule`？需工程确认后端模型，否则新增 | 工程+后端 | ⚠️ |
| R8 字段字典接口 | 14 组 `AR_FIELD_OPTIONS` 是否全部有 `dictionary-items` type_code？缺则后端补 | 后端 | ⚠️ |
| R9 处理人 role 过滤 | `GET /api/v1/users/` 是否支持 `?role=`？不支持则加过滤或走部门/角色接口 | 后端 | ⚠️ |
| R10 e2e 自动化 | 是否需要 playwright/agent-browser 自动化用例纳入 CI？建议至少 1 条 happy path + 1 条回填 | QA+工程 | ⚠️ |
| R11 数据来源枚举 | Card2 4 source 走 API 还是常量？决定是否动态 | 工程 | ⚠️ |

---

## 9. 工作流建议

### 工程交付后 QA 验证顺序
1. **静态检查**：stylelint exit 0 → vite dev HTTP 200 无 transform error →（若有）vitest pass。
2. **真实交互**（agent-browser）：登录 → 打开 modal → 配置 4 card（含二级/三级弹窗）→ 保存 → 重开回填核对（覆盖 R6）。
3. **视觉对比**：getComputedStyle 取主色/底色/阴影/圆角实际值，对照 §7 硬证据表；截图与原型并排，标注 C1/C4/C5/C6 的"预期偏离"。
4. **数据回写**：确认 `ruleName/expression/reject_message` 与 schema 字段一一对应（R5）；验证加载并发、保存原子性、模块关闭保留（§4/§5）。

### 必跑浏览器 viewport
| viewport | 覆盖点 |
|----------|--------|
| 1440×900 | 桌面默认，全功能 + 暗色回归 |
| 768×1024 | 平板/@media 768 断点，card 单列 |
| 375×667 | 手机/@media 480 断点，按钮纵向 + 表格横滚 |

### 决策门（开工前必须关闭）
- ❌ C1/R1 品牌色：产品/设计书面确认"以设计系统靛紫为准"。
- ❌ C4/C5/C6/R2/R3/R4 token 扩展：架构确认 tokens.css 增补方案并落地。
- ❌ R5/R6 schema 与丢数据：工程排期修复。
- ⚠️ R7/R8/R9/R11：后端接口确认。

> 以上 ❌ 项未关闭前，组件"严格还原原型"在视觉与数据两层均无法达成；QA 验收以"符合设计系统 token"为合格线，原型字面偏差作为 known deviation 记录而非 fail。
