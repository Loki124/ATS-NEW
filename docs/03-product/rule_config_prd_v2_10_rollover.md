# 校招管控规则配置 v2.10 增量 PRD — 「月度浮动目标（Roll-over）」

> 文档角色：v2.10 增量产品需求文档（非竞品分析，不重写 v2.4 既有 PRD）。语言：简体中文。
> 基线 PRD：`docs/rule_config_prd.md`（v2.4 扁平模型）。基线设计：`docs/rule_config_design.md`。
> 本次为增量章节；既有 P0/P1/P2 列表、Open Questions 全部沿用 v2.4 / 设计文档口径，不重排。
> 配套约束：`docs/ui/SETTINGS_PAGE_STRUCTURE.md`、`web/app/src/styles/tokens.css`、`web/app/src/styles/glass.css`；禁止硬编码 hex；暗色走 `body.dark` 变量集；遵循 UI/UX Pro Max 标准（empty / loading / error 态、focus、键盘可达、对比度）。

---

## 0. 版本元信息

- **版本号**：v2.10
- **PRD 类型**：增量（Incremental；只追加新行为，不重写既有 P0）
- **前置基线**：v2.4 扁平模型（适用范围 + 维度/指标 + 人数目标承载于规则）
- **本次变更主题**：**月度浮动目标（Roll-over）** —— 将「本年度已过去月份的未达成额度」以浮动方式归集到当月可用目标，参与 Offer / 待入职 / 入职 三阶段 4 节点的实时管控与看板展示。
- **决策基线（兵哥 9 月 4 日拍板）**：见第 1 节 7 项 Q1-Q7 决策；本 PRD 全程遵循，**不再二次拍板**。

---

## 1. 7 项拍板决策（硬约束，本 PRD 全程遵循，不重论）

| # | 决策 | 落地位置 |
|---|------|----------|
| Q1-A | 占编状态沿用原 `STATUS = [在职 / 在途Offer / 在途待入职 / 候选池]`；campus 模块不引入新枚举；offer / onboarding 阶段细粒度状态由各业务模块自身字段承载 | 不改 `constants.py:36` |
| Q2-A | 校验节点 **4 个**：`OfferService.submit_approval` + `OfferService.send_to_candidate` + `OnboardingService.create_onboarding` + `OnboardingService.mark_completed` | offer/services.py:127, 153；onboarding/services.py:31, 81 |
| Q3-A | 浮动基数 = `Σ monthly_targets[0..curMonth-2]`（**已过去月份**目标合计；curMonth 为系统当前月） | 看板 / 校验口径 |
| Q4-A | 入职过滤 = `actual_entry_date ∈ [本年 1/1, curMonth-1 月末]`（仅算「已过去月份」入职者） | calc 复用 `_accounting_month` + `_COUNTED_STATUSES` |
| Q5-A | 只算 **已转在职**（`status='在职'`） | `calc.py:98` `_COUNTED_STATUSES` 已含「在职」 |
| Q6-B | 浮动 = `max(0, 浮动基数 − 已入职在职人数)`；负数裁剪为 0 | 公式 §3.3 |
| Q7-A | `ControlRule.rollover_enabled: BooleanField(default=False)`；归入「管控强度」模块 | `models.py` 新字段 |

> 说明：本表为基线事实，PRD 行文中凡涉及上述内容均直接引用本表，不再展开"为什么"。

---

## 2. 产品定义

### 2.1 Product Goals（增量层、正交、可衡量）

> 与 v2.4 G1-G3 正交；本节只列增量目标。

- **G4 历史缺口可结转**：当本年度存在历史月份「目标已下发但入职未达成」的缺口时，将缺口以**浮动目标**形式归集到当月，使 HR 在每月招聘过程中能清晰看到「本月额定 + 历史结转 = 本月实际可用」，避免「达标即超额」误判或「缺额被淹没」失控。
- **G5 双轨展示零歧义**：实时看板与规则列表中"本月目标"统一更名为"本月额定目标"，新增"本月浮动目标"列与其并列；两列口径独立、可叠加；规则列表新增"浮动目标"启用状态 tag，使任一用户进入页面即知道每条规则是否启用浮动转结。
- **G6 4 节点校验与浮动同步**：Offer 提交审批 / Offer 发送候选人 / 创建待入职 / 入职完成 4 个节点上的实时校验均按「本月额定 + 本月浮动」加和判定超标；浮动开关按规则粒度独立，关闭浮动时口径回退至 v2.4 既有逻辑（仅额定目标），**0 业务回归**。

### 2.2 User Stories（增量场景）

- **US6（HR / 招聘官）**：作为规则维护者，我要点开任一规则弹窗查看其月度目标拆解，并在「管控强度」模块看到「启用本月浮动目标」开关，以便为不同业务线差异化配置是否启用浮动转结。
- **US7（HR / 招聘官）**：作为看板使用者，我要看到"本月额定目标"与"本月浮动目标"并列的两列数据，并能在列头 tooltip 看到浮动基数的计算口径，以便自助理解数字来源、不必再问 IT。
- **US8（HR / 招聘官）**：作为规则列表使用者，我要快速识别每条规则是否启用了浮动目标（通过「浮动目标」列的启用 / 未启用 tag），以便在跨业务线审查时一眼筛出浮动规则做重点复核。
- **US9（HR / 招聘官）**：作为业务负责人，我要理解浮动目标如何叠加：当月超额校验按「本月额定 + 本月浮动」加和判定；浮动目标被使用掉后不重复计入（已入职在职计数），以便业务侧对每月招聘节奏有数。
- **US10（业务主管）**：作为用人方，我发起的每个 Offer / 待入职 / 入职在 4 个节点上均能看到浮动目标的扣减提示（例如"已使用浮动额度 5 / 本月可用浮动 8"），以便在月度结转内完成招聘目标。
- **US11（HR 负责人）**：作为政策制定者，我希望浮动开关按规则粒度生效（全局 / 部门 / 职务 / 职级均允许差异化），以便按业务线节奏做差异化管控，而不影响其他规则。

---

## 3. 技术规范（增量）

### 3.1 需求池（Requirements Pool）

#### P0（Must have — 本次增量核心）

- **P0-11 数据模型新增字段**：`ControlRule` 增加 `rollover_enabled: BooleanField(default=False, verbose_name='启用本月浮动目标')`。迁移为 `AddField`（无 default 变更；存量行默认 `False` = 不启用浮动，保持 v2.4 行为零回归）。**字段语义**：单条规则的"是否启用月度浮动目标（roll-over）"开关。
- **P0-12 浮动基数计算（calc 复用 + 新增函数）**：
  - 新增 `calc.compute_rollover_target(rule_dict, persons, today=None) -> int`
  - **浮动基数** = `Σ monthly_targets[0..curMonth-2]`（按 Q3-A；`curMonth = today.month`，单位：人）
  - **已入职在职人数** = 命中规则适用范围 + `status='在职'`（Q5-A）+ `actual_entry_date ∈ [本年 1/1, curMonth-1 月末]`（Q4-A） 的 Person 数。
  - 函数须复用 `_accounting_month` / `_COUNTED_STATUSES` / `rule_matches` / `_indicator_filter`，**禁止另写一套计数逻辑**（与 v2.4 `calc.py` 铁律保持一致）。
  - 函数返回 `int`，由调用方按 Q6-B 公式合成"本月浮动目标"。
- **P0-13 当月可用浮动目标合成公式**：当且仅当 `rule.rollover_enabled == True` 时：
  - `rollover = max(0, 浮动基数 − 已入职在职人数)`（Q6-B，负数裁剪为 0）
  - `month_available_target = rule.monthly_targets[curMonth-1] + rollover`
  - 关闭时（`rollover_enabled=False`）：`month_available_target = rule.monthly_targets[curMonth-1]`（与 v2.4 行为一致）
- **P0-14 4 节点校验接入**（Q2-A）：
  - **节点 1**：`OfferService.submit_approval(offer_id, actor)`（offer/services.py:127）— 校验当前月是否超 `month_available_target`（硬约束→抛 `ControlRuleViolation`，软约束→warnings 放行）。
  - **节点 2**：`OfferService.send_to_candidate(offer_id, actor)`（offer/services.py:153）— 同上。
  - **节点 3**：`OnboardingService.create_onboarding(data)`（onboarding/services.py:31）— 同上。
  - **节点 4**：`OnboardingService.mark_completed(onboarding_id, actor)`（onboarding/services.py:81）— 同上。
  - 4 个节点复用同一服务函数 `campus_control.services.validate_offer_against_rules_v2_10(...)`（v2.4 的 `validate_offer_against_rules` 升级版），口径与 v2.4 唯一差异：**额定 → `month_available_target`**。
  - 闭包语义：硬约束命中阻断并抛错回滚事务；软约束命中仅 `logger.warning` 放行（沿用 v2.4 处理方式）。
- **P0-15 看板双轨展示（ratio 端点 + 前端列）**：
  - 后端 `/campus/rules/ratio/` 端点在每条 `rows[i]` 中新增字段：
    - `monthTarget`（本月额定目标）— 沿用 v2.4 语义不变。
    - `monthRollBase`（本月浮动基数，int）— 仅当 `rollover_enabled=True` 时返回 > 0 的值，否则为 0。
    - `monthRollActual`（已入职在职人数，用于扣减；int）— 同上。
    - `monthRollover`（本月浮动目标 = `max(0, monthRollBase − monthRollActual)`，int）— 同上。
    - `monthAvailableTarget`（本月可用目标 = `monthTarget + monthRollover`，int）— 校验口径与判定列使用。
  - 前端 `web/app/src/pages/settings/CampusControl.vue` 的 `ratioColumns`：
    - 原「本月目标」列 `title` 改名为「**本月额定目标**」，`key` 保留 `monthTarget`（不破坏现有断言）。
    - 在其后**新增**「本月浮动目标」列 `key='monthRollover'`，列宽 110px，渲染 `(r.monthRollover || 0)`。
    - 在其后**新增**「本月可用目标」列 `key='monthAvailableTarget'`，列宽 110px，渲染 `r.monthAvailableTarget` 并按 `>= monthAvailableTarget` 打 success tag（用于"超标预警"语义统一）。
    - 列头加 tooltip：浮动目标 = 截止当前月份以前的本年度目标合计 − 截止当前月份以前的本年度入职且在职（口径与 §3.3 一致）。
- **P0-16 规则列表新增「浮动目标」列**：
  - `ruleColumns` 在「控制强度」列之后、操作列之前新增「**浮动目标**」列：
    - `key='rolloverEnabled'`（接口字段透传驼峰）
    - 渲染：`r.rolloverEnabled ? h(NTag, { type: 'info', bordered: false, size: 'small' }, { default: () => '启用' }) : h(NTag, { type: 'default', bordered: false, size: 'small' }, { default: () => '未启用' })`
  - 后端 `ControlRuleSerializer` 增加 `rollover_enabled` 字段（read/write），前端 `ControlRule` 类型同步加 `rolloverEnabled: boolean`。
- **P0-17 规则弹窗「管控强度」新增开关**：
  - `RuleConfigDrawer.vue` 「模块三：管控强度」内，在「控制强度」`n-select` **下方**新增：
    - `<n-form-item label="启用本月浮动目标"><n-switch v-model:value="form.rolloverEnabled" /> …</n-form-item>`
    - 仅 `editing === true` 时可编辑；查看态只读显示开关状态。
    - 开关下方加 `n-text depth="3"` 说明：「开启后，本月目标 = 本月额定目标 + 浮动目标（= 已过去月份目标合计 − 已过去月份入职且在职，负数裁 0）。」
  - 保存时随 `strength` 一并 `PUT /campus/rules/{id}/`，字段名 `rollover_enabled`（蛇形）。
- **P0-18 状态与可访问性**：复用 v2.4 P0-10 既有规范；新增列 / 开关均需 `n-empty` / `loading` / `n-alert` 覆盖；focus 可见、键盘可达；切换 `body.dark` 变量集正常；禁止硬编码 hex。
- **P0-19 即时失效与零回归**：
  - 关闭浮动（`rollover_enabled=False`）时，4 节点校验与看板口径**严格等于 v2.4**（不允许任何数值漂移）。
  - 校验函数每次实时查 `is_active=True` 与 `rollover_enabled` 字段（不缓存），与 v2.4 "停用即失效" 口径一致。
  - 服务层异常 `ControlRuleViolation` 的 status_code / message 兼容 v2.4 调用方（offer.services.create_offer 现有 try/except 仍能透传 400）。

#### P1（Should have — 体验增强）

- **P1-6 浮动基数提示气泡**：规则详情（`n-drawer` 或弹窗只读态）显示 `monthRollBase` / `monthRollActual` / `monthRollover` 三项明细（折叠面板 / `n-descriptions`），让 HR 看清浮动数字的来源分解。
- **P1-7 看板 KPI 行新增"浮动规则数"卡片**：在"硬约束年度未达标 / 软约束年度未达标"之后新增第 5 张 KPI 卡片 `浮动规则数 = rows.filter(r => r.rolloverEnabled).length`，配色用 `info`。
- **P1-8 4 节点阻断文案增强**：当阻断原因为"浮动超额"（即 `monthActual > monthTarget + monthRollover` 且 `monthRollover > 0`）时，detail 追加一行：`「其中浮动超额 X 人（本月可用 Y = 额定 A + 浮动 B）」`，便于业务侧理解为何阻断。
- **P1-9 录入校验页同步**：录入校验（`/campus/rules/validate/`）前端"按人数校验"区同步展示"本月额定 / 本月浮动 / 本月可用"三栏（仅当 `rollover_enabled=True` 时显示浮动与可用列），保持口径一致。

#### P2（Nice to have — 后续）

- **P2-5 浮动目标导出**：规则导出 xlsx / csv 新增 `rollover_enabled` 列；看板导出（如未来支持）含浮动与可用目标。
- **P2-6 浮动规则切换审计**：在 `AuditLog` 增记 `entity='ControlRule', action='TOGGLE_ROLLOVER', new_value=old/new rollover_enabled`，便于追溯谁在何时开启了浮动。
- **P2-7 浮动跨年提示**：当规则年度 != 系统年度时（跨年场景），看板 / 弹窗显示 `n-alert type='warning'`「该规则年度（YYYY）与系统当前年度（ZZZZ）不一致，浮动目标按 Q3-A 仍以系统当前年度计算」，帮助用户理解边界。
- **P2-8 历史月份结转回溯**：提供一次性"重新计算浮动基数"运营入口（仅 Admin 可见），用于历史数据回溯（如批量补录 7 月入职后想重算 8 月浮动）。

---

### 3.2 关键交互（前端落点）

#### 3.2.1 规则弹窗 `RuleConfigDrawer.vue`「模块三：管控强度」新增区

```
┌──────────────────── 管控强度 ────────────────────┐
│  控制强度        [硬约束 ▼]                       │
│                                                    │
│  启用本月浮动目标  [ ○ 开关 ]                      │
│  开启后，本月目标 = 本月额定目标 + 浮动目标         │
│  （= 已过去月份目标合计 − 已过去月份入职且在职，    │
│   负数裁 0）                                        │
└────────────────────────────────────────────────────┘
```

- 编辑态开关可切换；查看态只读显示开关 on/off（`n-switch :disabled="true"`）。
- 开关 OFF：保存后行为与 v2.4 完全一致（仅本月额定目标），**零回归**。

#### 3.2.2 实时看板 `CampusControl.vue`「实时看板」tab 列顺序

| 列序 | 原列名 | v2.10 列名 | key |
|---|---|---|---|
| ... | ... | ... | ... |
| 6 | 本月目标 | **本月额定目标** | monthTarget |
| **+1** | — | **本月浮动目标** | monthRollover |
| **+2** | — | **本月可用目标** | monthAvailableTarget |
| ... | ... | ... | ... |

- 列头 `tooltip`：浮动目标 = 截止当前月份以前的本年度目标合计 − 截止当前月份以前的本年度入职且在职。
- KPI 行新增第 5 卡片"浮动规则数"（P1-7）。

#### 3.2.3 规则列表 `CampusControl.vue`「规则配置」tab 列顺序

| 列序 | 原列名 | v2.10 列名 | 渲染 |
|---|---|---|---|
| 1 | 规则编号 | 规则编号 | G0001 |
| ... | ... | ... | ... |
| 6 | 控制强度 | 控制强度 | n-tag（error/warning） |
| **+1** | — | **浮动目标** | n-tag（info=启用 / default=未启用） |
| ... | 操作 | 操作 | 复制/编辑/停用启用/删除 |

---

### 3.3 计算公式与口径（精度 0.0001 防毛刺）

```
curMonth      = today.month            // 1..12
monthTarget   = rule.monthly_targets[curMonth - 1]      // 本月额定目标

rollover_enabled = rule.rollover_enabled                // 开关

// 仅当 rollover_enabled == True 时计算浮动基数与已入职在职人数
rollBase = Σ rule.monthly_targets[i]   for i in [0, curMonth - 2]
         // = Σ 已过去月份 (1月..curMonth-1) 的月度目标合计（Q3-A）

rollActual = COUNT( Person
                    WHERE status == '在职'                                       // Q5-A
                      AND actual_entry_date ∈ [本年 1/1, curMonth-1 月末]          // Q4-A
                      AND rule_matches(Person, rule)                              // 适用范围命中
                      AND indicator == rule.indicator                             // 指标命中
                      AND counted == True                                         // 计入核算
                )

rollover = max(0, rollBase − rollActual)         // Q6-B 负数裁 0

monthRollover        = rollover_enabled ? rollover : 0
monthAvailableTarget = monthTarget + monthRollover
```

**一致性约束**：上述所有计数谓词（`status` / `actual_entry_date` / `rule_matches` / `counted` / 指标匹配）必须复用 `calc.py:rule_matches` / `_indicator_filter` / `_COUNTED_STATUSES` 与 `_accounting_month`（在职→actual；其他→expected）的现有口径，**不允许另写一套**（与 v2.4 服务层铁律一致）。

---

### 3.4 边界场景与预期行为

| 场景 | 输入条件 | 期望行为 |
|------|----------|----------|
| B1 | **浮动基数 = 0**（如规则 `monthly_targets` 1..curMonth-1 全部为 0） | `rollBase = 0`；`rollover = max(0, 0 − rollActual) = 0`（只要 rollActual ≥ 0 恒为 0；rollActual 实际不会为负）；`monthRollover = 0`；与 v2.4 完全一致。 |
| B2 | **浮动基数 > 月度目标**（如 1-7 月合计 30、当月额定 5） | `rollover` 可能远大于 `monthTarget`；`monthAvailableTarget` 大于当月目标；**这是产品预期**——历史大量缺口允许当月突击完成。 |
| B3 | **当月入职**（`actual_entry_date` 落在 curMonth 内） | 不计入 `rollActual`（Q4-A 仅算 curMonth-1 月末前的入职者）；即当月入职者**不影响当月浮动**，仅影响下月。 |
| B4 | **历史月份无人入职**（1-7 月目标 20，0 入职） | `rollActual = 0`；`rollover = rollBase`；浮动全额保留到当月。 |
| B5 | **历史月份超额入职**（1-7 月目标 20，已入职 25） | `rollover = max(0, 20 − 25) = 0`（Q6-B 裁剪）；浮动被吃掉为 0；当月仅以额定目标为准。 |
| B6 | **规则停用**（`is_active=False`） | 4 节点校验与看板均不命中该规则；浮动列在看板显示为"—"或 0（与现有停用规则同等处理）。 |
| B7 | **规则跨年**（如规则 `year=2025`，当前 2026 年） | 浮动基数仍按系统当前年度（2026）计算 `Σ monthly_targets`——但规则 `monthly_targets` 仍属于 2025 年度，**口径冲突**。看板列显示"—"并提示 P2-7 跨年告警；4 节点校验时浮动列禁用（按规则 `rollover_enabled` 仍生效，但 `rollBase` 取 0，避免误叠加）。 |
| B8 | **curMonth = 1**（系统当前为 1 月，无过去月份） | `rollBase = Σ empty = 0`；`rollover = max(0, 0 − rollActual) = 0`；浮动天然为 0；与 v2.4 完全一致。 |
| B9 | **规则未启用浮动**（`rollover_enabled=False`） | 4 节点校验与看板列均退化为 v2.4 行为（仅 `monthTarget`）；浮动列展示 0；零回归。 |
| B10 | **规则浮动了但当期超额阻断后被回滚** | `monthActual` 不被累计（事务回滚）；后续节点再次校验仍以原始 `rollActual` 为准（不会出现"负浮动"）；与 v2.4 阻断语义一致。 |

---

### 3.5 数据契约（接口字段透传）

#### 后端 → 前端（增量字段）

| 端点 | 字段 | 类型 | 出现条件 |
|------|------|------|----------|
| `GET /campus/rules/` 列表 | `rollover_enabled` | bool | 全部规则（启用 / 停用 / 未启用副本均有） |
| `GET /campus/rules/{id}/` 详情 | `rollover_enabled` | bool | 同上 |
| `GET /campus/rules/ratio/` 看板 | `monthRollBase` | int | rollover_enabled=True |
| `GET /campus/rules/ratio/` 看板 | `monthRollActual` | int | rollover_enabled=True |
| `GET /campus/rules/ratio/` 看板 | `monthRollover` | int | 全部（False 时为 0） |
| `GET /campus/rules/ratio/` 看板 | `monthAvailableTarget` | int | 全部（False 时等于 monthTarget） |
| `POST /campus/rules/` 新建 | `rollover_enabled` | bool | 写入字段，默认 false |
| `PUT /campus/rules/{id}/` 编辑 | `rollover_enabled` | bool | 可写 |

#### 前端 → 后端（增量字段）

| API | 字段 | 类型 | 默认 |
|-----|------|------|------|
| `createRule(payload)` / `updateRule(id, payload)` | `rolloverEnabled` | boolean | false |

#### TS 类型扩展（`web/app/src/api/campusControl.ts`）

```ts
export interface ControlRule {
  // ... 既有字段 ...
  rolloverEnabled: boolean   // v2.10 增量
}

export interface RatioRow {
  // ... 既有字段 ...
  monthRollBase?: number     // v2.10 增量（仅 rolloverEnabled=True 时有值）
  monthRollActual?: number   // v2.10 增量
  monthRollover: number      // v2.10 增量（False 时为 0）
  monthAvailableTarget: number  // v2.10 增量（False 时等于 monthTarget）
}
```

---

### 3.6 与既有 v2.4 行为的兼容性

- **零回归保证**：当 `rollover_enabled=False` 时：
  - 4 节点校验口径 = v2.4（仅 `monthTarget` 判定）
  - 看板 `monthAvailableTarget` = `monthTarget`（无浮动叠加）
  - 列表 / 弹窗 / 录入校验行为完全一致
- **数据迁移兼容**：新增 `rollover_enabled` 字段 `default=False`，存量数据全部回填为 False（不启用浮动）；迁移后系统行为与 v2.4 一致；用户按需逐条开启。
- **异常兼容**：`ControlRuleViolation.status_code` / `message` 不变；`offer.services.create_offer` 既有 try/except 仍可透传 400 给前端。
- **API 兼容**：`ControlRuleSerializer` 仅追加字段，未删除 / 重命名既有字段；前端未传 `rollover_enabled` 时按 `False` 处理。

---

## 4. 待确认（Open Questions）

> 本节列出本 PRD 落地过程中需主理人 / 上下游确认的细节，避免在对话中 Q&A；按优先级排序。

| # | 问题 | 推荐方案 | 影响 |
|---|------|----------|------|
| Q-A1 | **浮动按"已过去月份"还是"已过去月份+当月已入职"？** | 严格按 Q4-A = `actual_entry_date ≤ curMonth-1 月末`；当月入职者**不影响当月浮动**（避免"当月入职 → 当月浮动减少 → 进一步阻断"的死循环）。 | 边界 B3、B10；已在 §3.4 标注。 |
| Q-A2 | **Offer 阶段的"在途Offer"是否计入 rollActual？** | 不计入。Q5-A + Q4-A 仅算"在职"且"已入职"——即 `status='在职' && actual_entry_date ≤ curMonth-1 月末`。在途 Offer / 在途待入职均**不计入 rollActual**。 | 边界 B5；与 v2.4 `_COUNTED_STATUSES` 中"在职"严格对齐。 |
| Q-A3 | **浮动开关在 4 个节点之间是否需要"原子"语义？** | 否。4 节点各自独立校验（事务各自独立），与 v2.4 一致；阻断后事务回滚、计数不累计；与 v2.4 阻断语义 100% 对齐。 | 边界 B10。 |
| Q-A4 | **当 curMonth > 12 或 curMonth < 1（如历史数据回放）** | `rollBase` / `rollActual` 计算前必须 `if not (1 ≤ curMonth ≤ 12): return 0`；避免数组越界。 | calc 函数入口防御。 |
| Q-A5 | **跨年规则（rule.year ≠ 当前年度）的浮动语义** | 推荐：浮动基数仍按"系统当前年度的 `rule.monthly_targets`"计算，但跨年时 `rule.monthly_targets` 数组属于历史年度——为避免误叠加，跨年规则 `monthRollover` 一律返回 0 并在看板提示告警（P2-7）。 | 边界 B7；避免数据歧义。 |
| Q-A6 | **看板 `monthAvailableTarget` 与"年度达成 / 年度在途"列的关系** | `monthAvailableTarget` 仅参与"本月"列系（本月达标判定）；与"年度"列系（`annualTarget` / `annualAchieved` / `annualRate`）相互独立——后者仍按 `annualTarget`（不变）。 | 看板列语义零冲突。 |
| Q-A7 | **录入校验页（`/validate/`）是否需要双轨展示？** | 推荐：P1-9 已建议同步展示"本月额定 / 本月浮动 / 本月可用"三栏；本 PRD 仅占位，最终前端实装由前端工程师按 P1-9 落地。 | 不影响 P0。 |
| Q-A8 | **前端 `ruleColumns` 操作列宽度** | 现 260px；新增"浮动目标"列后总宽增加 ~110px；如需调整，操作列同步收缩至 230px（避免总宽溢出）。 | 前端 UI 细节调整。 |
| Q-A9 | **Audit 字段命名一致性** | `rollover_enabled`（DB / 序列化器 / 迁移）→ `rolloverEnabled`（前端驼峰）→ `rollover_enabled`（API 文档 / 错误消息）。已与现有 v2.4 `is_active` / `isActive` 风格一致。 | 命名规范。 |
| Q-A10 | **P0-14 中 4 节点校验与 v2.4 `validate_offer_against_rules` 函数签名兼容** | 推荐升级为 `validate_offer_against_rules_v2_10(...)` 新函数；保留 v2.4 旧函数不动（向后兼容）；`offer/services.py::create_offer` 仍调用旧函数不升级（v2.4 入口保留），新 4 节点调用新函数。如需后续统一，由架构师拍板。 | 函数版本管理。 |

---

## 5. 文档附录（不构成新需求）

- **既有 v2.4 PRD**：`docs/rule_config_prd.md`（保留原貌，本次不重写）
- **既有 v2.4 设计文档**：`docs/rule_config_design.md`（保留原貌，架构师按需在本文基础上增量更新）
- **既有 v2.9 迁移**：`apps/django/apps/campus_control/migrations/0007_alter_controlrule_strength_choices.py`（strength choices 收敛先例）
- **后端铁律引用**：`calc.py:88-98`（rule_matches / _COUNTED_STATUSES）；`services.py:130-261`（v2.4 Offer 钩子实现）

---

> 本文档仅定义 v2.10 增量产品需求；不重复 v2.4 既有 P0/P1/P2 与 Open Questions；既有 v2.4 PRD 保持稳定。
