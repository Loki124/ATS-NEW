# PRD：「指标管理」接入「阶段规则」——「指标作为条件源」通用能力

| 项 | 内容 |
|---|---|
| 文档类型 | 产品需求文档（PRD，简单版） |
| 系统 | ATS-NEW（Django + Vue3/Naive UI 招聘管理系统） |
| 作者 | 许清楚（产品经理） |
| 版本 | v1.0（草案，待兵哥评审） |
| 语言 | 简体中文 |
| 关联模块 | `apps/metrics`（指标管理）、`apps/process`（阶段规则：skip_rules/archive_rules）、`apps/entry_condition`（进入条件）、`apps/rule_engine`（统一运算符/求值）、`apps/metrics/services`（取值引擎） |

---

## 1. 产品目标

把「指标管理」中的**原子指标与派生指标**作为**一等条件源**，接入阶段规则的「自动跳过」「自动归档」以及系统其它规则驱动场景。定位不是一次性的「跳过/归档专属」功能，而是系统级的**「指标作为条件源」通用能力**：运营在「指标管理」里定义的任何指标（含派生指标如跳槽频率、工作时长），都能被所有规则消费方（阶段进入条件、自动跳过、自动归档，以及未来任意规则场景）以**统一、可复用**的方式引用，无需在每个消费方里各造一套字段映射、运算符词表与取值逻辑。

---

## 2. 产品原则

### 2.1 原则一：全局通用（系统级抽象，而非消费方专属）

- 把「指标作为条件」抽象为**一个通用的条件源（condition source）**，与既有的「候选人 / 需求中 / 职位中 / 阶段状态」并列，成为第 5 类条件来源 `METRIC`（指标）。
- 该能力由**通用抽象层**提供，所有「规则驱动」消费方通过**接入**而非**重新实现**来使用它（见 §4 的分层结构）。
- 严禁把实现耦合进某个具体消费方（例如只在 skip/archive 里写死指标逻辑）。未来新增规则场景（如自动推进、定时巡检、约束校验）只需「接入」该通用源，不再重复开发。

### 2.2 原则二：不重复造轮子（复用既有资产，禁新建平行体系）

- 系统已具备可直接复用的资产，**本次不新建**第三套规则引擎、不新造运算符词表、不新造指标取值机制、不新造「条件模板」概念、不新造前端控件。
- 既有的 `MetricTemplate`、`MetricEngine._resolve_metric_value`、`UnifiedOperator`、三类快照、`EntryConditionFieldCatalogView` 目录契约、`FieldDef` 编辑器组件，必须被直接复用。

### 2.3 复用清单（复用 X / 不新建 Y）

**✅ 复用（直接套用，不重写）**

| 复用资产 | 位置 | 复用方式 |
|---|---|---|
| `MetricTemplate`（指标模板） | `apps/metrics/models.py:137` | 作为「指标条件字段」的**唯一定义来源**。`operators`（UnifiedOperator 白名单）+ `value_domain` + `param_enums` + `param_allow_null` + `param_config` 天然等价于现有 `FieldDef`，直接驱动下拉/运算符/值控件。**不另造条件字段配置表**。 |
| `MetricEngine._resolve_metric_value` | `apps/metrics/services/metric_engine.py:180` | 作为**指标取值唯一入口**：原子走 `FieldResolverRegistry.resolve`，派生走 `derived_compute`。所有消费方统一经此取值，不各写取值逻辑。 |
| `UnifiedOperator` | `apps/rule_engine/models.py:57` | 作为**运算符词表唯一真相源**（当前 14 种，含 `CONTAINS/NOT_CONTAINS/REGEX_MATCH`）。 |
| 三类快照 | `apps/metrics/services/candidate_snapshot.py` | `build_candidate_snapshot` / `build_demand_snapshot` / `build_position_snapshot` 作为**数据上下文**，已共用，不重建。 |
| `EntryConditionFieldCatalogView` | `apps/process/views.py:723` | 复用 `source→field→operator→value` 字典树契约，仅**新增一个 METRIC source 分支**，不另起目录端点。 |
| 前端 `FieldDef` / `ConditionItem` 编辑器 | `web/app/src/pages/settings/stage-rule/*` | 直接复用现有下拉、运算符、值控件（枚举下拉 / 数字步进 / 区间双输入 / 空值 checkbox），**不新增控件**。 |
| `StageRule.skip_rules` / `archive_rules` | `apps/process/models.py:453/458` | 复用既有 JSON 结构（items 含 `condition_type/field/operator/value`），仅扩展 `condition_type` 取值，不新建存储。 |

**🚫 不新建（明确禁止）**

- ❌ 不新建第三套规则引擎 / 求值器（沿用 `rule_engine` 体系 + 现有 skip/archive 求值链路）。
- ❌ 不新造运算符词表（统一用 `UnifiedOperator`，废弃各消费方各自定义 operator 枚举的倾向）。
- ❌ 不新造「指标条件模板」概念（直接用 `MetricTemplate`）。
- ❌ 不新造指标取值机制（直接用 `MetricEngine._resolve_metric_value`）。
- ❌ 不新造前端控件（复用现有控件族）。

> ⚠️ **已知同构偏离（须 §6 第 5 条拍板）**：`UnifiedOperator` 已于 2026-09-29 扩至 **14** 种（新增 `CONTAINS/NOT_CONTAINS/REGEX_MATCH`），但 `entry_condition` 的 `ConditionOperator`（`models.py:34`）与前端 `OperatorKey`（`types.ts:11`）仍为 **11** 种。本次 METRIC 源**以 `UnifiedOperator` 为唯一真相源**，并推动 entry_condition / 前端回填至 14，消除三套词表分裂。

---

## 3. 用户故事

| 角色 | 用户故事 |
|---|---|
| **指标管理员** | 作为指标管理员，我希望把派生指标（如跳槽频率、工作时长）配置为「可参与规则的条件模板」，以便流程 HR 无需懂计算逻辑即可直接引用。 |
| **指标管理员** | 作为指标管理员，我希望在「指标管理」里定义指标的运算符白名单与值域/枚举，以便规则配置界面自动按模板渲染出合法的运算符与值控件，减少误配。 |
| **指标管理员** | 作为指标管理员，我希望禁用/软删某个指标模板时，系统能明确提示其对存量规则的影响，以便我评估变更风险。 |
| **流程配置 HR** | 作为流程配置 HR，我希望在配置「自动跳过 / 自动归档」规则时，从「指标」来源里直接选用已定义的指标模板并填值，以便用「跳槽频率 > 3 次」这类派生指标做条件。 |
| **流程配置 HR** | 作为流程配置 HR，我希望配置指标条件时的运算符与值控件和配置普通字段时完全一致（同源下拉/步进/区间），以便零学习成本、不担心配错类型。 |
| **流程配置 HR** | 作为流程配置 HR，我希望阶段进入条件也能用同一套指标源，以便跳过/归档/进入条件三处语义与体验统一。 |
| **系统（平台）** | 作为平台，我希望所有规则消费方经过同一个「指标条件求值器」取值与判定，以便运算符语义、空值处理、异常降级全局一致、可统一审计。 |
| **系统（平台）** | 作为平台，我希望新增规则场景（如自动推进、定时巡检）时只需接入既有的 METRIC 源，以便不重复开发取值与求值逻辑。 |

---

## 4. 需求池（P0 / P1 / P2）

> **分层说明（贯彻「全局通用」）**：先建设 **通用抽象层（基础设施）**，再让各**具体消费方接入**。基础设施只做一遍；消费方仅做「允许 `condition_type=METRIC` + 委托统一求值器」。

### 4.0 通用抽象层（基础设施，所有消费方共用）

| 编号 | 优先级 | 需求（作为<角色>，我希望<能力>，以便<价值>） |
|---|---|---|
| INF-1 | **P0** | 作为平台，我希望新增一个通用条件来源 `METRIC`（指标），与候选人/需求中/职位中/阶段状态并列，以便所有规则消费方都能以统一方式引用指标。 |
| INF-2 | **P0** | 作为平台，我希望在 `EntryConditionFieldCatalogView` 目录中新增 METRIC source 分支，其 `fields` 直接来自 `MetricTemplate`（原子+派生统一列出），以便目录自动随指标管理增删改而同步，无需改代码。 |
| INF-3 | **P0** | 作为平台，我希望 METRIC 源的每个字段直接映射 `MetricTemplate` 的 `operators`/`value_domain`/`param_enums`/`param_allow_null`/`param_config` 作为 `FieldDef`，以便复用现有下拉/运算符/值控件、不再造控件。 |
| INF-4 | **P0** | 作为平台，我希望提供一个**统一的指标条件求值器**（封装 `MetricEngine._resolve_metric_value` + `UnifiedOperator` 比较），输入 `(metric_template_id, context, operator, value)` 返回判定结果，以便所有消费方共用、运算符语义与空值处理一致。 |
| INF-5 | **P0** | 作为指标管理员，我希望 METRIC 源既能引用原子指标也能引用派生指标（如跳槽频率/工作时长），以便派生指标（原本引用不到）现在也可作为规则条件。 |
| INF-6 | **P0** | 作为平台，我希望 METRIC 条件项的存储统一为 `condition_type='METRIC'` + `field='<metric_template_id>'` + `operator` + `value`，以便与既有的 `ConditionItem` / skip/archive JSON schema 兼容、不新建存储结构。 |

### 4.1 具体消费方接入

| 编号 | 优先级 | 消费方 | 需求（作为<角色>，我希望<能力>，以便<价值>） |
|---|---|---|---|
| CON-1 | **P0** | 阶段·自动跳过（skip_rules） | 作为流程配置 HR，我希望在「自动跳过规则」的条件项里选择「指标」来源并引用指标模板，以便用派生指标（如跳槽频率>3 次）触发自动跳过。 |
| CON-2 | **P0** | 阶段·自动归档（archive_rules） | 作为流程配置 HR，我希望在「自动归档规则」的条件项里选择「指标」来源并引用指标模板，以便用指标条件驱动自动归档。 |
| CON-3 | **P1** | 阶段进入条件（entry_condition） | 作为流程配置 HR，我希望阶段进入条件也能从同一 METRIC 源引用指标模板，以便进入条件/跳过/归档三处语义与体验统一（现有 CANDIDATE/DEMAND/POSITION 内联原子指标可保留兼容，新能力统一走 METRIC 源）。 |
| CON-4 | **P1** | 统一求值器归属 | 作为平台，我希望 skip/archive 与 entry_condition 三处共用 §4.0 INF-4 的统一求值器（当前 skip/archive 求值器与 `EntryConditionEvaluator` 同构但分裂），以便消除重复、统一异常降级与日志。 |
| CON-5 | **P2** | 未来消费方（预留） | 作为平台，我希望自动推进/定时巡检/约束校验等未来规则场景仅需接入 METRIC 源即可引用指标，以便不重复开发取值与求值。 |

### 4.2 体验 / 治理（P1）

| 编号 | 优先级 | 需求（作为<角色>，我希望<能力>，以便<价值>） |
|---|---|---|
| EXP-1 | **P1** | 作为流程配置 HR，我希望指标模板下拉按「原子/派生」分组并显示类型标签，以便快速区分并理解取值含义。 |
| EXP-2 | **P1** | 作为流程配置 HR，我希望勾选空值类运算符（IS_EMPTY/IS_NOT_EMPTY）时值控件自动隐藏，以便避免无效输入。 |
| EXP-3 | **P1** | 作为流程配置 HR，我希望支持批量勾选指标模板做规则项复制/批量应用，以便高效配置多条件。 |
| EXP-4 | **P1** | 作为平台，我希望每次指标条件求值写入统一执行日志（命中/未命中/实际值/耗时/异常），以便审计与排障。 |
| EXP-5 | **P1** | 作为指标管理员，我希望引用了被禁用/软删模板的规则在界面给出显眼提示并阻止启用，以便防止「引用失效」的静默假绿。 |

### 4.3 生命周期与存量影响（P2）

| 编号 | 优先级 | 需求（作为<角色>，我希望<能力>，以便<价值>） |
|---|---|---|
| LIFE-1 | **P2** | 作为指标管理员，我希望指标模板版本变更（运算符/值域调整）对存量规则的影响可评估，以便变更可追溯。 |
| LIFE-2 | **P2** | 作为指标管理员，我希望模板禁用/软删时，系统给出受影响的规则清单与处理建议（置灰/跳过该条件/人工复核），以便安全治理。 |
| LIFE-3 | **P2** | 作为平台，我希望对既有「裸路径」指标条件（如 `candidate.age`）提供可选的迁移到 METRIC 源（引用对应模板），以便统一到一套引用方式。 |

---

## 5. UI / 交互设计稿（文字描述）

### 5.1 指标源在条件项编辑器中的呈现（四步）

在现有的「条件项编辑器」（SkipRuleEditModal / ArchiveRuleEditModal / 进入条件编辑器）中，指标源**完全复用**现有「来源 → 字段 → 运算符 → 值」的四个步骤，仅新增一个来源选项，不新增任何控件：

1. **选来源**：来源下拉新增「指标」一项，与「候选人中 / 需求中 / 职位中 / 阶段状态」并列（对应 `SourceKey` 新增 `'METRIC'`）。
2. **选指标模板**：二级下拉列出所有 `status=enabled` 的 `MetricTemplate`，按「原子指标 / 派生指标」分组，每项显示「名称 + 类型标签」（如 `跳槽频率〔派生〕`）。`field` 取值为该模板 id。
3. **选运算符**：运算符下拉选项由该模板的 `operators` 白名单驱动，渲染逻辑与现有 `OperatorKey` 控件完全一致（复用 `AR_OPERATOR_LABELS`）。
4. **填值**：值控件由模板的 `value_type` / `param_enums` / `value_domain` / `param_config` 驱动，复用现有控件族：
   - 数值型（`number`）→ 数字步进 / 区间双输入（`BETWEEN` 时）；
   - 枚举型（`enum`）→ 枚举下拉（`param_enums`）；
   - 字符串型（`string`）→ 文本框；
   - 布尔型（`boolean`）→ 是/否下拉；
   - 空值类运算符（`IS_EMPTY` / `IS_NOT_EMPTY`）→ 不显示值控件，仅展示「为空 / 不为空」文案（受 `param_allow_null` 约束是否允许）。

### 5.2 复用控件对照

| 模板属性 | 驱动的前端控件（复用，不新建） |
|---|---|
| `operators`（白名单） | 现有运算符下拉（同 `FieldDef.operators`） |
| `param_enums` | 现有枚举下拉 `options` |
| `value_domain` / `param_config`（min/max/step） | 现有数字步进 / 区间双输入 |
| `param_allow_null` | 现有「空值」判定（控制是否可配 `IS_EMPTY`） |

### 5.3 示例

> 来源 = **指标** → 指标模板 = **跳槽频率〔派生〕** → 运算符 = **大于** → 值 = **3**（次）
> 语义："`跳槽频率 > 3 次`" → 命中则该自动跳过/归档规则的条件项满足。

### 5.4 校验规则（复用现有校验框架）

- 必选指标模板；运算符必须落在模板 `operators` 白名单内；
- 值类型须与模板 `value_type` 匹配；`BETWEEN` 须 `min ≤ max`；
- 空值类运算符不要求填值；
- 引用了被禁用/软删模板的条件项在保存/启用时拦截并提示（呼应 EXP-5）。

---

## 6. 待确认问题（Open Questions，须兵哥拍板）

| # | 问题 | 选项 / 建议 |
|---|---|---|
| 1 | **派生指标在无底层经历数据时的行为**：跳槽频率/工作时长依赖 `workExperience`/`education`，而项目目前**无独立的工作经历/教育经历结构化模型**（`candidate_snapshot.py` 2026-09-25 勘察结论），派生指标此时 `resolve` 为 `None`。 | 建议默认：**派生指标算不出 → 该条件按运算符判定**（仅 `IS_EMPTY` 类可命中，其余判「未命中」），且不在规则级报错（降级为未命中并记日志）。最终语义须拍板。 |
| 2 | **指标模板禁用 / 软删对存量规则的影响**：`MetricTemplate` 外键为 `PROTECT`（防物理删），但软删/禁用后存量规则引用即失效。影响范围与处理策略（置灰 / 跳过该条件 / 人工复核）需先定。 | 建议：禁用→规则该条件判「未命中」并前端显眼提示；软删→规则保存/启用拦截（EXP-5）。 |
| 3 | **entry_condition 与 skip/archive 是否统一一套求值器**：当前 skip/archive 的 JSON 条件项求值器与 `EntryConditionEvaluator` 同构但分裂；指标条件求值器应归属统一求值器还是各消费方各接。 | 建议：统一到 §4.0 INF-4 的「统一指标条件求值器」，并推动三处共用（CON-4）。 |
| 4 | **condition_type 命名与存储迁移策略**：新增枚举值命名（`METRIC` 还是 `INDICATOR`？），以及存量 skip/archive JSON 中 `condition_type` 仅 4 值的兼容；是否对既有「裸路径」指标条件做迁移到 METRIC 源。 | 建议：命名 `METRIC`；存量 JSON 向后兼容（未知 source 视为「未命中」）；迁移列为 P2（LIFE-3）。 |
| 5 | **运算符三套词表分裂**：`UnifiedOperator`=14 种，`ConditionOperator`(entry_condition)=11 种，前端 `OperatorKey`=11 种，已不同构。METRIC 源以哪个为准？ | 建议：**以 `UnifiedOperator`(14) 为唯一真相源**，回填 entry_condition `ConditionOperator` 与前端 `OperatorKey` 至 14 种，消除分裂。 |

---

## 7. 验收口径（概要）

- **P0 可验收**：目录新增 METRIC 源并列于四类来源；指标模板（含派生）可被 skip/archive 规则引用并正确求值；统一取值入口与求值器落地；不新建存储/控件/运算符词表。
- **非目标（本版不做）**：未来消费方实际接入（P2）、模板版本治理（P2）、存量「裸路径」迁移（P2）不在 P0 交付范围。
