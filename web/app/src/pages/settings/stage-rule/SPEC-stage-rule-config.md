# 阶段配置规则组件 — 实现 Spec

> 范围：将独立 HTML 原型 `deepseek_html_20260907_02a9fb.html` 还原为 Vue 组件，**严格还原**字段类型 / 控件 / 布局 / 交互 / 视觉。
> 视觉规范：沿用项目 Liquid Glass v2（`tokens.css` / `glass.css`），不抄原型硬编码 `#4e6bff`。
> 数据规范：字段字典、规则数据**全部从 API 取，不硬编码**。
> 工作目录锁定：`/Users/loki/WorkBuddy/招聘助手/ATS-NEW`（所有改动仅限此目录）。

---

## 0. 原型 ↔ 现状 关键差异速查（贯穿全文）

| 维度 | HTML 原型 | 后端 / 现状 | 处置 |
|---|---|---|---|
| 数据源（source 枚举） | `['需求中','职位中','候选人中','简历中']` 4 个 | `condition_type` 仅 3 种：`STAGE_STATUS` / `CANDIDATE` / `DEMAND` | 见 §1，缺 2 个需决策 |
| 字段字典 | demo 数据（需求部门/能效BG/最高学历/简历来源） | 实际解析字段：`HIRING_MANAGER`/`DEMAND_LEVEL`/`AGE`/`HIGHEST_EDU` 等 | 见 §1，以 API 为准 |
| 进入条件存储 | 条件组（多组 + 组内表达式 + 整体表达式） | `EntryConditionRule`(1 规则 = 1 expression + N item，无嵌套组) | 见 §3，多规则映射 |
| 自动跳过 / 归档 | 带启停 + "查看已停用规则" | `StageRule` 模型无 `skip_rules`/`archive_rules` 子表 | 见 §4，需新增存储 |
| 表达式校验 | 6 规则 + 大括号禁嵌套 + 编号 1-N | 前端 `validateExpression` + 后端 `POST /expressions/validate` | 见 §6.4 |

---

## 1. 字段字典数据源方案

### 决策

**推荐：A（后端新增 `GET /api/v1/entry-condition-fields/` 接口）**
理由：
1. 用户硬性要求"字段数据从 API 取，不硬编码" → 直接排除方案 B（前端常量）。
2. 方案 C（`/dictionary-types/`）与 D（`/dynamic-fields/`）语义不匹配：条件字段（如 `DEMAND_LEVEL`、`HIGHEST_EDU`、`AGE`）不是业务字典值，也不是通用动态字段，而是**后端 `services.py:321-360` 硬编码的解析映射**。用字典 / 动态字段接口取，要么取不到、要么需要前端自己再翻译，反而制造新的硬编码。
3. 方案 A 让**后端作为唯一事实源**：后端已掌握 `condition_type → 字段 → 运算符` 的完整知识，暴露成 catalog 接口，前端只负责渲染。后端字段演进（新增 `POSITION`/`RESUME`、调整运算符）前端零改动。
4. 接口契约建议返回结构（供后端实现参考）：

```jsonc
// GET /api/v1/entry-condition-fields/
{
  "sources": [
    {
      "source": "DEMAND",            // condition_type
      "label": "需求中",             // UI 展示名（由后端 i18n 决定）
      "fields": [
        { "field": "DEMAND_LEVEL", "label": "需求职级", "operators": ["EQ","NEQ","IN","NOT_IN","IS_EMPTY","IS_NOT_EMPTY"] },
        { "field": "HIRING_MANAGER", "label": "用人经理", "operators": ["EQ","NEQ","IN"], "auto_filter_inactive_users": true },
        { "field": "DEPARTMENT", "label": "需求部门", "operators": ["EQ","IN","NOT_IN"] }
        // …其余 HIRING_MANAGER_SUPER/BU_PRESIDENT/SOLID_VP/DOTTED_VP
      ]
    },
    {
      "source": "CANDIDATE",
      "label": "候选人中",
      "fields": [
        { "field": "AGE", "label": "年龄", "operators": ["EQ","GT","GTE","LT","LTE","BETWEEN"] },
        { "field": "GENDER", "label": "性别", "operators": ["EQ","NEQ","IN"] },
        { "field": "HIGHEST_EDU", "label": "最高学历", "operators": ["EQ","NEQ","IN","NOT_IN"] },
        { "field": "WORK_YEARS", "label": "工作年限", "operators": ["EQ","GT","GTE","LT","LTE","BETWEEN"] },
        { "field": "CURRENT_CITY", "label": "当前城市", "operators": ["EQ","IN","NOT_IN"] },
        { "field": "EXPECTED_CITY", "label": "期望城市", "operators": ["EQ","IN","NOT_IN"] }
      ]
    },
    {
      "source": "STAGE_STATUS",
      "label": "阶段状态",
      "fields": [
        { "field": "stage_name", "label": "阶段名称", "operators": ["EQ","NEQ","IN"] },
        { "field": "stage_statuses", "label": "阶段状态", "operators": ["IN","NOT_IN"], "is_array": true }
      ]
    }
  ],
  "operators": { "EQ":"等于", "NEQ":"不等于", "GT":"大于", "GTE":"大于等于", "LT":"小于", "LTE":"小于等于", "BETWEEN":"区间", "IN":"属于", "NOT_IN":"不属于", "IS_EMPTY":"为空", "IS_NOT_EMPTY":"不为空" }
}
```

### source → condition_type 映射规则（**必填项**）

| 原型 source | condition_type | 后端解析字段（services.py） | 状态 |
|---|---|---|---|
| `需求中` | `DEMAND` | `HIRING_MANAGER` / `HIRING_MANAGER_SUPER` / `BU_PRESIDENT` / `SOLID_VP` / `DOTTED_VP` / `DEMAND_LEVEL` / `DEPARTMENT` | ✅ 支持 |
| `候选人中` | `CANDIDATE` | `AGE` / `GENDER` / `HIGHEST_EDU` / `WORK_YEARS` / `CURRENT_CITY` / `EXPECTED_CITY` | ✅ 支持 |
| `阶段状态`（原型未显式列出，建议补充） | `STAGE_STATUS` | `stage_name`(str) / `stage_statuses`(数组) | ✅ 支持（后端有，原型 UI 缺，建议补为第 3 个 source） |
| `职位中` | **无** | 后端无对应 `condition_type` | ❌ **缺口** |
| `简历中` | **无** | 后端无对应 `condition_type` | ❌ **缺口** |

**缺口决策（推荐）**：
- v1 **不渲染"职位中"/"简历中"**。UI 的 source 选择器由 §1 接口返回的 `sources` 驱动，后端未返回的 source 前端不出现，天然规避硬编码与缺口。
- 若产品坚持保留 4 个 source，则**后端必须新增** `POSITION` / `RESUME` 两个 `condition_type` 并在 `services.py` 补充解析逻辑（属于后端改造，本组件 spec 仅预留 UI 渲染位，不假定其存在）。
- 原型 demo 字段（需求部门/能效BG/最高学历/简历来源）**一律丢弃**，全部以 §1 接口返回为准。

---

## 2. 进入条件 schema 切换

### 决策

**推荐：A（切换至新 `EntryConditionRuleViewSet`）**
理由：
1. 后端 `EntryConditionRuleViewSet`（`apps/django/apps/entry_condition/views.py:39`）已具备完整能力：CRUD + `SoftDelete` + 按规则 `status`(ENABLED/DISABLED) 启停 + `rule_seq` 排序 + 自定义 `evaluate`/`logs`/`toggle`/`reorder` actions。老 `PATCH /process-stage-links/{id}/` 的 `entry_condition` JSON 是遗留结构，无法支撑"多规则 + 启停 + 已停用查看 + 评估日志"。
2. 切换后，原型 Card 1 的"规则配置 / 启停 / 查看"全部有后端支撑，无需前端伪状态。

### 具体调用路径（替换现有 `upsertEntryCondition` / `listEntryConditions`）

| 操作 | Method & Path | 前端封装 |
|---|---|---|
| 列表 | `GET /api/v1/entry-condition-rules/?link_id={id}` | `listEntryConditions({linkId})` → 改走 viewset |
| 详情 | `GET /api/v1/entry-condition-rules/{ruleId}/` | `getEntryCondition(ruleId)`（新增） |
| 新建 | `POST /api/v1/entry-condition-rules/` | `createEntryCondition(payload)`（新增；payload 含 `link_id`/`rule_name`/`rule_seq`/`status`/`expression`/`reject_message`/`items[]`） |
| 更新 | `PUT /api/v1/entry-condition-rules/{ruleId}/` | `updateEntryCondition(ruleId, payload)` |
| 删除 | `DELETE /api/v1/entry-condition-rules/{ruleId}/` | `deleteEntryCondition(ruleId)` |
| 启停 | `POST /api/v1/entry-condition-rules/{ruleId}/toggle/` | `toggleEntryCondition(ruleId)` |
| 重排 | `POST /api/v1/entry-condition-rules/reorder/` | `reorderEntryConditions([{id,rule_seq}])` |
| 评估 | `POST /api/v1/entry-condition-rules/evaluate/`（`detail=False`，收 `candidate_id`+`link_id?`+`demand_id?`）| `evaluateEntryConditionRule({ candidate_id, link_id?, demand_id? })` |
| 日志 | `GET /api/v1/entry-condition-rules/{ruleId}/logs/` | `getEntryConditionLogs(ruleId)` |

> 兼容性见 §6.2：旧 `entry_condition` JSON 需迁移脚本转为 `EntryConditionRule` 行；切换期间前端保留双读兼容层（优先读 viewset，回退读旧字段），迁移完成后删除兼容层（见 §7 commit 9）。

---

## 3. 条件组 UI 概念映射（核心）

### 问题
- 后端模型：**1 个 `EntryConditionRule` = 1 个 `expression`（如 `"1 and 2"`） + N 个 `ConditionItem`**，扁平，**无嵌套组**。
- 原型 UI：**条件组容器（可加多个组）**，每组有 `innerExpression` + `innerPrompt`；整体还有 `groupExpression` + `overallPrompt`。

### 决策

**推荐：方案 (a) 多规则列表 —— "1 个条件组 = 1 个 EntryConditionRule"**
理由：
1. 后端无 group 子模型，若强行用单规则 + 嵌套组，需把组信息塞进 `expression` 字符串（如 `(1 or 2) and (3 or 4)`），`innerPrompt`/`overallPrompt` 无处存放，违反后端 schema。
2. 多规则映射与后端 `rule_seq` / `status` / `toggle` / `logs` 天然契合：原型"规则配置"按钮 → 打开编辑单条规则；Card 1 表格每行 = 一条规则（= 一个条件组）；"整体未满足提示" = 该规则的 `reject_message`；"组内表达式" = 该规则的 `expression`。
3. 牺牲点：原型"在一个规则里套多个组并有一个总表达式"的嵌套概念被扁平化。但这是**唯一后端兼容**的形态，且产品语义（多条独立进入条件规则）反而更清晰。

### 数据结构转换示例

```jsonc
// 后端 EntryConditionRule（= 原型 1 个条件组）
{
  "id": "r-102",
  "rule_name": "P6及以上需求",          // ← 原型"组名"
  "rule_seq": 1,
  "status": "ENABLED",
  "expression": "1 and 2",             // ← 原型 innerExpression（组内条件组合）
  "reject_message": "不满足职级要求",    // ← 原型 innerPrompt / 整体未满足提示
  "items": [
    { "condition_type": "DEMAND", "field": "DEMAND_LEVEL", "operator": "GTE", "value": "P6" },
    { "condition_type": "CANDIDATE", "field": "HIGHEST_EDU", "operator": "IN", "value": ["本科","硕士"] }
  ]
}
```

```ts
// 前端类型（types/stage-rule.ts）
interface ConditionItemDTO {
  condition_type: 'STAGE_STATUS' | 'CANDIDATE' | 'DEMAND';
  field: string;
  operator: 'EQ'|'NEQ'|'GT'|'GTE'|'LT'|'LTE'|'BETWEEN'|'IN'|'NOT_IN'|'IS_EMPTY'|'IS_NOT_EMPTY';
  value: string | string[] | number | null;
  auto_filter_inactive_users?: boolean;
}
interface EntryConditionRuleDTO {
  id?: string;
  link_id: string;
  rule_name: string;          // 30 字限制（后端校验）
  rule_seq: number;
  status: 'ENABLED' | 'DISABLED';
  expression: string;         // 默认 '1'
  reject_message: string;
  items: ConditionItemDTO[];
}
```

> 若产品后续坚持"单规则多嵌套组"，则需在后端新增 `ConditionGroup` 子模型（不在本 spec v1 范围，仅记录为扩展点）。

---

## 4. 自动跳过 / 自动归档规则存储方案

### 问题
- 后端 `StageRule` 模型**无** `skip_rules` / `archive_rules` 子表。
- 原型需要：规则 CRUD + 每条启停 + "查看已停用规则" + 评估。必须持久化。

### 决策

**推荐：A（新增持久化存储）的轻量版 —— 在 `StageRule` 模型上新增 `skip_rules` / `archive_rules` 两个 JSON 字段（而非独立 sub-table）**
理由：
1. 原型规则结构扁平（规则名/执行条件/执行动作/状态），无需复杂关联查询，JSON 字段一次 migration 即可满足，避免 `StageSkipRule`/`StageArchiveRule` 两张子表 + 各自 serializer + viewset 的过重成本。
2. 仍需后端 migration（在 `StageRule` 上加 `skip_rules = JSONField(default=list)` / `archive_rules = JSONField(default=list)`），以及 `StageRuleSerializer` 暴露这两个字段。
3. 每条规则本地结构（前端视角）：

```ts
interface SkipRuleDTO {
  id: string;                 // 前端生成 uuid，存于 JSON 数组
  name: string;               // 规则名称
  expression: string;         // 执行条件（同表达式校验器）
  action: 'SKIP' | 'PASS' | 'REJECT';   // 执行动作：跳过/通过/拒绝
  status: 'ENABLED' | 'DISABLED';
}
interface ArchiveRuleDTO {
  id: string;
  name: string;
  expression: string;
  lock_duration: number;      // 锁定时长
  extend_rule: string;        // 加时规则
  effective_scope: 'ALL' | 'NEW_ENTrants'; // 生效方式：全部 / 新进入
  status: 'ENABLED' | 'DISABLED';
}
```

- "查看已停用规则"三级弹窗：对 `archive_rules` 中 `status==='DISABLED'` 的行做过滤展示，操作列"启用" → 改 `status` 后 `PUT /api/v1/stage-rules/{id}/`。
- 若后端排期不允许：降级方案为 §4 选项 C（仅前端暂存），但**不推荐**，因为会丢失启停/已停用语义与跨端一致性。

---

## 5. 文件结构拆分

当前 `StageRuleConfigModal.vue` 1511 行 → 拆为**主 modal + 4 卡片 + 4 二级/三级弹窗 + 2 复用组件 + 3 composable + 1 类型文件**。

| 文件 | 职责 | 类型 | 行数 |
|---|---|---|---|
| `stage-rule/StageRuleConfigModal.vue` | 主壳：header / 4 卡片容器 / footer（取消+保存）/ 数据加载编排 / 关闭守卫 / teleport 二级弹窗挂载 | 主（保留） | ~400 |
| `stage-rule/cards/EntryConditionCard.vue` | Card1：规则表格(执行条件/未满足提示) + "规则配置"按钮 + 模块开关 + 走 §2 API | 新增 | ~250 |
| `stage-rule/cards/DefaultHandlerCard.vue` | Card2：3 select（数据来源/取值字段/处理规则）→ `defaultHandlerType`/`defaultHandlerFields`/`defaultHandlerUserIds` | 新增 | ~120 |
| `stage-rule/cards/InterviewConfigCard.vue` | Card3：2 option-grid（面试轮次/面试形式）→ `interviewRoundIds`/`interviewFormat` | 新增 | ~120 |
| `stage-rule/cards/FlowAutomationCard.vue` | Card4：编排 4 个 flow-block（评估/流转/跳过/归档） | 新增 | ~200 |
| `stage-rule/flowblocks/SkipRuleBlock.vue` | 自动跳过：模块开关 + 规则表 + 添加规则 → 走 §4 | 新增 | ~150 |
| `stage-rule/flowblocks/ArchiveRuleBlock.vue` | 自动归档：模块开关 + 规则表 + 添加 + 查看已停用 → 走 §4 | 新增 | ~150 |
| `stage-rule/modals/EntryConditionEditModal.vue` | 二级：编辑单条进入条件规则（= 一个条件组），内嵌 `ConditionGroupEditor` + `ExpressionInput` | 新增 | ~300 |
| `stage-rule/modals/SkipRuleEditModal.vue` | 二级：基础设置 + 条件设置 + 执行设置(跳过/通过/拒绝) | 新增 | ~250 |
| `stage-rule/modals/ArchiveRuleEditModal.vue` | 二级：基础设置 + 条件设置 + 执行设置(锁定时长/加时/生效方式) | 新增 | ~250 |
| `stage-rule/modals/DisabledRulesModal.vue` | 三级：已停用规则表格 + 启用操作 | 新增 | ~120 |
| `stage-rule/components/ConditionGroupEditor.vue` | 复用：条件项增删 + source/field/operator/value 联动（数据来自 §1 接口） | 新增 | ~200 |
| `stage-rule/components/ExpressionInput.vue` | 复用：表达式输入 + 6 规则校验 + popover 帮助 | 新增 | ~120 |
| `stage-rule/composables/useStageRuleDraft.ts` | 草稿态管理：初始加载、脏检查、保存、撤销(useUndo)、防抖自动保存 | 新增 | ~150 |
| `stage-rule/composables/useEntryConditionRules.ts` | §2 API 封装（list/create/update/delete/toggle/reorder/evaluate/logs） | 新增 | ~180 |
| `stage-rule/composables/useSkipArchiveRules.ts` | §4 规则读写（基于 StageRule JSON 字段） | 新增 | ~150 |
| `stage-rule/types/stage-rule.ts` | 所有 TS 接口（§3 / §4 DTO + StageRule 字段映射） | 新增 | ~100 |
| `src/api/recruitment-process.ts` | **改**：`upsertEntryCondition`/`listEntryConditions` 改走 `EntryConditionRuleViewSet`；新增 `toggle/reorder/evaluate/logs` 封装 | 改 | +60 / -40 |
| `src/pages/settings/StageRuleConfigModal.vue` | **删 1511 行**，替换为新主壳（或重命名为 `stage-rule/StageRuleConfigModal.vue` 后删旧文件） | 删/改 | -1511 / +400 |

> 是否拆 Pinia store：**不拆独立 Pinia store**。理由：规则数据强绑定单个 `linkId` + 弹窗生命周期，用 `useStageRuleDraft` composable（含 `ref` 草稿 + 提交）足够，避免全局 store 污染。若后续多页共享，再升级。

---

## 6. 关键风险点（按优先级）

1. **【P0】字段枚举与后端 schema 差异**：原型 4 source vs 后端 3 `condition_type`；"职位中/简历中"无后端支持。→ 决策见 §1：v1 仅渲染后端返回的 source，缺口暂隐；产品强需求则后端加 `POSITION`/`RESUME`。**不得前端硬编码补齐**。
2. **【P0】进入条件 schema 切换兼容性 / 旧数据迁移**：老 `entry_condition` JSON → `EntryConditionRule` 行需 migration 脚本；切换期需双读兼容层，避免老数据丢失。→ 见 §2 / §7 commit 9。
3. **【P0】自动跳过/归档后端模型缺失**：`StageRule` 无对应子表，必须后端 migration（§4 的 JSON 字段方案）。**本组件无法独立闭环，需后端排期**。
4. **【P1】表达式校验器移植**：需核对 `src/utils/condition-expression` 现有 `validateExpression` 是否覆盖原型 6 规则（括号配对 / `and`·`or` 连接 / 编号 1-N / 大括号禁嵌套 / 运算符合法性 / 空表达式）。若不足，以 `POST /api/v1/expressions/validate` 为权威兜底。→ 见 §7 commit 7。
5. **【P1】二级/三级弹窗样式作用域**：`n-modal` teleport 到 `body`，`scoped` 样式不穿透。→ 用 `:deep()` 或非 scoped + 仅用 CSS 变量（`--brand`/`--brand-a12` 等），禁止硬编码色值；弹窗 `z-index` 需高于主 modal（原型 1100）。
6. **【P2】数据加载失败空状态**：§1 字段 catalog / §2 规则列表 API 失败时，卡片需 empty / error state + 重试，禁用「保存」按钮（失败时）。
7. **【P2】保存期间关闭守卫**：保存（PUT/POST）进行中禁用关闭按钮 + `beforeClose` 确认（有未保存草稿时提示）。
8. **【P2】条件组→规则语义偏差**：`reject_message` ↔ 原型 `innerPrompt`/`overallPrompt`、`expression` ↔ `innerExpression` 必须一致；组合语义需与后端 `services.py` 对齐（AND/OR 解析）。
9. **【P3】字段字典 API 选型未定导致阻塞**：若后端 §1 接口排期晚于前端，可临时用 §1 JSON 结构做 mock，但**交付时务必替换为真实接口**，禁止固化为常量文件。
10. **【P3】`rule_name` 30 字限制**：后端 `EntryConditionRule.rule_name` 限 30 字，前端输入需加 `maxlength` + 校验提示。

---

## 7. 完整实施步骤（commit 拆分）

| # | commit | 做什么 | 为什么独立 |
|---|---|---|---|
| 1 | `chore(stage-rule): scaffold component tree` | 仅拆文件骨架（§5 全部空壳组件 + 类型文件），不改逻辑 | 先把 1511 行单文件拆开，降低后续改动冲突与 review 风险，可独立合并 |
| 2 | `feat(stage-rule): switch entry-condition to EntryConditionRuleViewSet` | `recruitment-process.ts` 改 `listEntryConditions`/`upsertEntryCondition` 走新 viewset + 双读兼容层 | API 切换是其他功能地基，先落地便于增量验证 |
| 3 | `feat(stage-rule): entry-condition edit modal + condition group editor` | 二级弹窗 + `ConditionGroupEditor` + `ExpressionInput`，实现 §3 多规则映射 | 进入条件是原型最复杂交互，独立交付便于聚焦测试 |
| 4 | `feat(stage-rule): field dictionary via /entry-condition-fields/` | 接入 §1 接口驱动 source/field/operator 联动，移除任何 demo 数据 | 数据来源独立演进，与 UI 解耦 |
| 5 | `feat(stage-rule): default-handler & interview-config cards` | Card2/Card3 接 `StageRule` 字段（`upsertStageRule`） | 相对独立，验证 StageRule 主链路 |
| 6 | `feat(stage-rule): skip/archive rules persistence` | §4 JSON 字段读写 + `SkipRuleBlock`/`ArchiveRuleBlock` + `DisabledRulesModal` | 依赖后端 migration 就绪后落地 |
| 7 | `fix(stage-rule): align expression validator to 6 rules` | 增强 `validateExpression` 或接 `POST /expressions/validate` | 校验规则独立可单测 |
| 8 | `test(stage-rule): empty states / close guard / error handling` | 健壮性：加载失败、保存守卫、未保存提示 | 收尾质量保障，可独立回归 |
| 9 | `chore(stage-rule): remove legacy entry_condition PATCH path` | 迁移完成后删双读兼容层 + 旧 `upsertEntryCondition` 老路径 | 最后清理，需确认旧数据已全量迁移 |

---

## 8. 完整文件改动列表（行数预估）

### 新增文件（前端，共 ~18 个，约 3360 行）

| 文件 | 增 | 说明 |
|---|---|---|
| `stage-rule/StageRuleConfigModal.vue` | +400 | 主壳 |
| `stage-rule/cards/EntryConditionCard.vue` | +250 | |
| `stage-rule/cards/DefaultHandlerCard.vue` | +120 | |
| `stage-rule/cards/InterviewConfigCard.vue` | +120 | |
| `stage-rule/cards/FlowAutomationCard.vue` | +200 | |
| `stage-rule/flowblocks/SkipRuleBlock.vue` | +150 | |
| `stage-rule/flowblocks/ArchiveRuleBlock.vue` | +150 | |
| `stage-rule/modals/EntryConditionEditModal.vue` | +300 | |
| `stage-rule/modals/SkipRuleEditModal.vue` | +250 | |
| `stage-rule/modals/ArchiveRuleEditModal.vue` | +250 | |
| `stage-rule/modals/DisabledRulesModal.vue` | +120 | |
| `stage-rule/components/ConditionGroupEditor.vue` | +200 | |
| `stage-rule/components/ExpressionInput.vue` | +120 | |
| `stage-rule/composables/useStageRuleDraft.ts` | +150 | |
| `stage-rule/composables/useEntryConditionRules.ts` | +180 | |
| `stage-rule/composables/useSkipArchiveRules.ts` | +150 | |
| `stage-rule/types/stage-rule.ts` | +100 | |
| 本 SPEC 文档（参考用，不计入组件） | — | — |

**前端小计**：+~3360 行。

### 修改文件（前端）

| 文件 | 增 | 删 | 说明 |
|---|---|---|---|
| `src/api/recruitment-process.ts` | +60 | -40 | 改 `upsertEntryCondition`/`listEntryConditions` 走 viewset；新增 toggle/reorder/evaluate/logs |
| `src/pages/settings/StageRuleConfigModal.vue` | +400（移至新路径后） | -1511 | 旧 1511 行整体删除，主壳迁至 `stage-rule/` |
| `src/utils/condition-expression.ts` | +40 | -10 | 增强 6 规则（若采用前端校验） |

**前端净变化**：约 +3360（新）+ ~460（改） - 1511（删旧） ≈ **+2300 行**。

### 需后端配合（非本仓库前端改动，列出以明确依赖）

| 后端文件 / 位置 | 改动 | 行数 | 对应章节 |
|---|---|---|---|
| `apps/django/apps/entry_condition/`（新增 view / serializer） | 新增 `GET /api/v1/entry-condition-fields/` 接口 + catalog 序列化 | +120 | §1 |
| `apps/django/apps/process/models.py`（`StageRule`） | 新增 `skip_rules` / `archive_rules` JSONField | +10 | §4 |
| `apps/django/apps/process/migrations/` | 上述字段 migration | +30 | §4 |
| `apps/django/apps/entry_condition/migrations/` | 旧 `entry_condition` JSON → `EntryConditionRule` 迁移脚本 | +60 | §2/§6.2 |
| `apps/django/apps/process/serializers.py` | `StageRuleSerializer` 暴露 `skip_rules`/`archive_rules` | +20 | §4 |

---

## 9. 视觉还原映射（速查，避免抄 #4e6bff）

| 原型硬编码 | Liquid Glass v2 映射 |
|---|---|
| `#4e6bff`（主色） | `var(--brand)`（#6366F1）+ `gradient-btn` 渐变 |
| `#eef1ff`（浅底） | `var(--brand-a12)` |
| modal 阴影 `0 20px 60px rgba(0,0,0,.18)` | `var(--shadow-card)`（或微调） |
| config-card 底 `#f7f8fa` / 边 `#e5e6eb` | `var(--g1)` / `var(--border-hairline)` |
| switch 40×24 on `#4e6bff` | `var(--brand)`；off `var(--g3)` |
| btn-outline 虚线 `#b3b8c2` hover 实线 `#4e6bff` | `var(--border-hairline)` + hover `var(--brand)` |
| radius 16/12/10/8/6 | `var(--radius-lg/md/sm/xs)` |
| 间距 4/8/12/16 | `var(--space-1/2/3/4)` |
| 图标 | `@vicons/ionicons5`（禁 Font Awesome） |
| 动画 | `var(--duration-fast)` + `var(--ease-out)` |

> 所有颜色 / 间距 / 圆角 **一律走 CSS 变量**，组件内禁止出现任何 `#xxxxxx` 字面量（AGENTS.md X-01~X-06 合规）。
