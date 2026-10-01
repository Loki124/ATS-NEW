# 指标管理（apps/metrics）可引用位置调研报告

> 调研日期：2026-09-04
> 范围：ATS-NEW 后端 `apps/django/apps/` + 前端 `web/app/src`
> 目标：找出"最近做的指标管理的指标"可以被哪些业务模块引用，典型样本=招聘流程管理的进入条件配置。

---

## TL;DR

- **指标库（metrics）已完整建成但"未通电"**：后端模型/执行引擎/REST API/前端工作台全部就绪，**全仓没有任何业务模块引用它**（除了它自己，以及 `rule_engine` 仅复用其运算符枚举 `UnifiedOperator`）。`evaluate_scene` 只在 API 端点暴露，无内部调用方。
- 系统里其实有 **4 套彼此独立的"指标/条件"子系统**，互不打通：`metrics`（计算型）、`entry_condition`（进入条件，硬编码字段）、`rule_engine`（统一规则引擎，字段为自由文本）、`campus_control`（配额型管控指标）。
- **最对口的引用点 = 进入条件配置（entry_condition）**：它现在把候选维度字段（AGE/GENDER/HIGHEST_EDU/WORK_YEARS…）硬编码在后端 `_get_candidate_value` 和前端条件弹窗里，正该改从指标库拉取。
- **入池 / 筛选 / 评分三个 scene 端点已就绪**，只差在业务触发点调用（`MetricRuleScene.TALENT_POOL/FILTER/SCORING` 已定义但 0 调用）。
- **不建议把 campus_control 的配额指标并入 metrics**——两者抽象不同（配额维度值 vs 计算型取数）。

---

## 一、现状盘点

### 1.1 指标库（apps/metrics）—— 孤立但完整

| 层 | 模型/服务 | 文件:行 | 说明 |
|---|---|---|---|
| 原子指标 | `AtomicMetric`（source_path 点路径） | `metrics/models.py:42` | 如 `candidate.age` / `candidate.workExperience.0.company` |
| 派生指标 | `DerivedMetric`（calc_func + base_path + params） | `metrics/models.py:91` | 如 `MAX_GAP` / `HIGHEST_EDU` / `COUNT_IN_WINDOW`，零代码新增 |
| 指标模板 | `MetricTemplate`（引用一个指标 + 运算符白名单） | `metrics/models.py:137` | 二选一约束：原子或派生 |
| 指标规则 | `MetricRule`（conditions + scene + action_type） | `metrics/models.py:252` | scene=TALENT_POOL/FILTER/SCORING/MANUAL；action=VETO/DEDUCT/BONUS |
| 字段解析 | `ObjectPathResolver` + `FieldResolverRegistry` | `metrics/services/field_resolver.py:93,145` | 点路径+数组下标，拒绝 `__` 穿越 |
| 候选快照 | `build_candidate_snapshot(candidate_id)` | `metrics/services/candidate_snapshot.py` | ORM→嵌套 dict，供 source_path 取值 |
| 执行引擎 | `MetricEngine.execute` / `evaluate_scene` | `metrics/services/metric_engine.py`、`metrics/services/rule_trigger.py:8` | 异常一律 FAIL 不 500 |
| 前端工作台 | `MetricsWorkspace.vue` | `web/app/src/pages/settings/MetricsWorkspace.vue` | 指标管理 UI 已建 |
| 前端 API 客户端 | `api/metrics.ts`（全套端点封装） | `web/app/src/api/metrics.ts` | definitions / candidate-fields / filterByScene / executeRule 等 |

**孤立证据（硬）：**
- 全仓业务 app 对 `apps.metrics` 的 import = 0（grep `from apps.metrics` / `AtomicMetric` / `MetricRule` 排除 metrics 自身与迁移，结果为空）。
- `evaluate_scene` / `filter_candidates_by_scene` 的调用方 = 0（仅在 `metrics/views.py` 的 API 端点暴露）。
- 路由已挂载：`config/urls.py:169` → `path('metrics/', include('apps.metrics.urls'))`，API 可用但无人调用。

### 1.2 进入条件配置（apps/entry_condition）—— 用户举例的样本，硬编码

| 项 | 现状 | 证据 |
|---|---|---|
| 规则/条件模型 | `EntryConditionRule` + `ConditionItem` | `entry_condition/models.py:48,111` |
| 条件类型 | `ConditionFieldType`：STAGE_STATUS / CANDIDATE / DEMAND | `entry_condition/models.py:26` |
| 候选字段取值 | **硬编码 dict**：AGE→算年龄、GENDER→candidate.gender、HIGHEST_EDU、WORK_YEARS、CURRENT_CITY、EXPECTED_CITY | `entry_condition/services.py:321`（`_get_candidate_value`） |
| 运算符 | 自带 `ConditionOperator` 枚举（EQ/NEQ/GT/GTE/LT/LTE/BETWEEN/IN/NOT_IN/IS_EMPTY/IS_NOT_EMPTY，10 种） | `entry_condition/models.py:33` |
| 与 metrics 关系 | **完全没用** metrics；仅存在一条"委托到统一规则引擎"的隐藏路径（`RULE_ENGINE_DISPATCH`，默认 False 走 legacy） | `entry_condition/services.py:86,142` |

### 1.3 统一规则引擎（apps/rule_engine）—— metrics 的设计母体

| 项 | 现状 | 证据 |
|---|---|---|
| 四核心模型 | `Rule` / `Condition` / `Action` / `RuleExecutionLog` | `rule_engine/models.py:122,207,241,264` |
| 条件字段 | `Condition.field` 是**自由文本** `CharField(max_length=64)`，**没有 FK 到 AtomicMetric/DerivedMetric** | `rule_engine/models.py:218` |
| 运算符 | 复用 `UnifiedOperator`（14 种，metrics 也复用同一枚举） | `rule_engine/models.py:57,219` |
| 与 metrics 关系 | 概念上是 metrics 的母体（metrics 注释明确说"本 app 是 rule_engine 的指标层"），但 **Condition 未真正引用指标**，取值仍是自由文本字段名 | `metrics/models.py:1-18` 注释 |

### 1.4 校招管控（apps/campus_control）—— 配额型指标，不同物种

| 项 | 现状 | 证据 |
|---|---|---|
| 模型 | `ControlDimension` / `ControlIndicator` / `ControlRule` | `campus_control/models.py:30,46,66` |
| 指标语义 | **配额型**：指标值如 `985`/`男`/`工学`，配 `target` 占比 + `annual_target` 人数 + 12 月目标 | `campus_control/models.py:66-130` |
| 与 metrics 关系 | 概念有交集（都是"指标"），但抽象不同——metrics 是"计算型取数"，campus 是"配额维度值"，**数据模型独立，不建议合并** | — |

---

## 二、可以"引用指标"的位置（按优先级）

### ★ ① 招聘流程管理 · 进入条件配置（entry_condition）— 最自然、收益最直接

- **现在怎么做**：候选维度字段硬编码在 `entry_condition/services.py:321` 的 dict，前端条件编辑弹窗（`EntryRuleEditModal.vue` 仅一句注释，字段列表在共享常量里）也是写死的；运算符走 entry_condition 自己的 `ConditionOperator`。
- **引用 metrics 的哪一层**：把这些候选/需求维度登记为 `AtomicMetric`（`source_path=candidate.age` / `candidate.highest_education` / `candidate.work_years` …），进入条件配置时从 `GET /metrics/definitions/` 或 `GET /metrics/candidate-fields/` 拉"字段清单 + 运算符白名单（operator_matrix 已按 dataType 算好)"，取代硬编码。`"近 N 年跳槽段数"`/`"最高学历"`/`"最大空窗期"` 这类直接上 `DerivedMetric`，零代码。
- **收益**：进入条件与指标库口径统一；新增候选维度字段零开发；运算符随类型自动收敛。
- **改造量（中）**：
  1. 后端 `EntryConditionEvaluator._get_candidate_value` 的硬编码 dict → 改为"按指标 source_path 走 metrics 的 `FieldResolverRegistry` 解析"。
  2. 前端 `EntryRuleEditModal.vue` 字段下拉 → 从 metrics 接口拉（已有 `listMetricDefinitions` / `listCandidateFields`）。
  3. 保留 STAGE_STATUS（前序阶段状态）与 DEMAND 人员类（metrics 暂未覆盖，需补 AtomicMetric 或保留特例）。

### ★★ ② 统一规则引擎 · Condition.field（rule_engine）— 指标层的"真正落地点"

- **现在怎么做**：`Condition.field` 是自由文本（`rule_engine/models.py:218`），运维手填，无校验、无取数契约。
- **引用 metrics 的哪一层**：给 `Condition` 增加可选 `atomic_metric` / `derived_metric` FK（或把 `field` 改为从指标定义下拉），取值统一走 metrics 的 `field_resolver`。这样 metrics 才是 rule_engine 的"事实指标层"，而不是两套并存字段语义。
- **收益**：终结"自由文本字段名"的脆弱性；metrics 管理后台成为唯一指标真相源。
- **改造量（中—大）**：涉及 `rule_engine` 的 `_resolve_value` 扩展为优先走 metrics 指标 + 新增迁移 + 既有 Condition 数据映射。

### ★ ③ 入池筛选（talent_pool）/ 智能筛选（FILTER scene）— 端点已就绪，只差接线

- **现在怎么做**：`metrics` 已预留 `MetricRuleScene.TALENT_POOL` / `FILTER`（`metrics/models.py:228`），以及 `evaluate_scene` / `filter_by_scene` 端点（`metrics/views.py:108,194`），但**零调用**。需确认 `talent_pool` 当前是否有自己的筛选逻辑。
- **引用 metrics 的哪一层**：直接把 `/metrics/rules/filter/`（批量）+ `/metrics/rules/evaluate-scene/`（单条）挂到入池/筛选触发点，复用"指标规则 + 动作类型 VETO/DEDUCT/BONUS"。
- **改造量（小—中）**：纯接线，把 `evaluate_scene` 调用挂到入池/筛选业务动作。

### ★ ④ 评分（SCORING scene）

- **现在怎么做**：metrics 已有 `SCORING` scene 与 `MetricRule.action_type=BONUS`（`metrics/models.py:236`）。`process` 评分子模块现状待确认。
- **引用 metrics 的哪一层**：若评分已有独立打分维度，可把"加分项"类维度登记为 `DerivedMetric` + `MetricRule(scene=SCORING, action=BONUS)`。
- **改造量（待确认）**：先查清 `process` 评分现状。

### ○ ⑤ campus_control 管控指标 — 概念重叠，建议不强行合并

- **判断**：`ControlIndicator` 是配额维度值（985/男/工学 + 目标占比），与 metrics 计算型取数（candidate.age 取数、MAX_GAP 计算）是不同抽象。**不建议把 ControlIndicator 改成 AtomicMetric**。
- **可选联动**：若要把"候选人实际属性"喂给管控判定，可仅在 `ControlRule` 判定时调用 metrics 的快照/派生计算，保持两张表独立。

### ○ ⑥ duplicate_rule / automation / time_limit / reason_library 等条件类模块

- 这些模块若各自维护"候选人字段 + 运算符"硬编码（类似 entry_condition），都是潜在引用点；需逐一审视字段语义后再列改造清单。

---

## 三、可复用的技术契约（已在位，直接调用即可）

| 能力 | 位置 | 用途 |
|---|---|---|
| 字段取值 | `metrics/services/field_resolver.py` `ObjectPathResolver` + `FieldResolverRegistry` | 点路径+数组下标解析，拒绝 `__` 穿越；可扩展 source_type |
| 运算符 | `rule_engine.UnifiedOperator`（14 种，metrics 复用）；`metrics/services/operator_matrix.operators_for(data_type, is_enum)` | 按指标类型算白名单 |
| 候选快照 | `metrics/services/candidate_snapshot.py` `build_candidate_snapshot(candidate_id)` | ORM→嵌套 dict 供 source_path 取值；demand/position 同理 |
| 目录接口 | `GET /metrics/definitions/`（原子+派生合并，含 valueMode/dataSource/supportedOperators/paramSchema） | 配置页拉指标清单 |
| 字段路径清单 | `GET /metrics/candidate-fields/`（`list_candidate_paths`） | 配置原子指标时下拉选路径 |
| 运算符/函数目录 | `GET /metrics/operators/`、`GET /metrics/derived-funcs/` | 下拉渲染 |
| 执行 | `MetricEngine.execute(conditions, data, logic)` / `evaluate_scene(scene, candidate_id)` / `filter_candidates_by_scene` | 业务触发点调用 |
| 安全 | 解析失败/异常一律 FAIL 不 500；BETWEEN 用 `meta_json` 承载 min/max | 不阻断业务 |

---

## 四、结论与下一步

1. **指标库是"建好未通电"**——最对口的引用点是 **① 进入条件配置** 与 **② 统一规则引擎 Condition**，前者改动可控、收益直接（消灭硬编码字段表）。
2. **入池/筛选/评分三个 scene 端点已就绪**，只差在业务触发点调用（③ 接线即可）。
3. **campus_control 配额指标不并入 metrics**。

**待确认后再定优先级（影响改造排序）：**
- [ ] `process` 是否有独立评分模块？现状如何？（决定 ④）
- [ ] `entry_condition` 前端字段常量具体在哪个文件/常量？（决定 ① 前端改造面）
- [ ] `talent_pool` 当前筛选实现是自研还是已接 metrics？（决定 ③ 接线点）
- [ ] 既有 `rule_engine.Condition`（自由文本 field）存量数据规模？（决定 ② 迁移成本）
