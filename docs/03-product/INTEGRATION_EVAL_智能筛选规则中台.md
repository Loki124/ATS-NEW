# 智能筛选规则中台（规格书 + PRD）与 ATS-NEW 的适配性评估与集成建议

> 评估基线：基于附带的两份文档——《技术实现规格书》与《产品需求文档 PRD V1.0》——的章节、不变量（INV）、契约（§3）、运算符（§4）、校验器（V01–V16）、引擎（§6）、API（§8）、模型（§9）、缓存（§10）、禁用项（§14），以及 PRD 的 4 场景 / 三前端 / 15 互斥校验 / 三级指标 / 模板函数 / NL2Rule（二期）/ 实时命中预览等要求。
> 说明：`@skill:frontend-design-3` 本次未能加载（"Can not find skill"），故 UI 设计层建议结合 `ui-ux-pro-max` 框架思路与项目既有 Naive UI 体系给出。评估以文档明确列出的内容为准。

## 0. 结论先行（Verdict）

规格书描述的「智能筛选规则中台」是一套**从零设计的独立系统**（Django 4.2 + Pydantic v2 + MySQL 8 + Redis + Vue3 + Element Plus + Pinia），与 ATS-NEW **已经上线运行的 2 层指标/规则层（AtomicMetric / DerivedMetric / MetricTemplate / MetricRule）高度重叠但多处背离**。

核心结论：
- **不是「开箱即用」的适配**——它是平行/竞争设计，不是我们的补丁。
- **不推荐推倒重写（rip-and-replace）**：我们的指标层已能跑、已具备 fail-loud、Celery 异步、统一 UI；重写风险高、收益低。
- **推荐「借鉴式渐进集成」**：把规格书的优秀点（类型化 `param_schema`、Decimal-only、AST 白名单表达式、16 校验门、VETO→DEDUCT→BONUS 动作分级、业务语言映射、指标注册表）作为**增量增强**落到现有层；我们刚落地的 `derived_registry` 元数据（`input_kind`/`output_type`/`unit`/`param_schema` + fail-loud）已经与规格书 §3/§7 思路**收敛**，是天然起点。
- **必须先澄清一个意图问题**：这份规格书到底是打算（A）替换我们的指标层、（B）作为独立中台并存、（C）仅作设计参考？不同意图决定不同路线；下文按「参考+渐进增强」给出方案，并在末尾给出 A/B 的取舍。

## 1. 方案适配性评估（规格书 vs ATS-NEW 技术栈）

| 维度 | 规格书方案 | ATS-NEW 现状 | 适配结论 |
|---|---|---|---|
| 后端框架 | Django 4.2 + DRF 3.14 | Django + DRF | ✅ 一致 |
| 契约层 | **Pydantic v2 作为单一真相源** | DRF Serializer | ❌ 范式冲突（见 §4.5） |
| 数据库 | MySQL 8.0 | MySQL（ats_dev） | ✅ 一致 |
| 缓存/消息 | Redis + Pub/Sub 失效 | Redis（cache/broker/result） | 🔶 缺 Pub/Sub 失效 |
| 前端框架 | Vue 3.4 | Vue 3 + TS + Vite | ✅ 一致 |
| UI 组件库 | **Element Plus 2.x** | **Naive UI** | ❌ 组件库冲突（见 §4.1） |
| 状态管理 | Pinia | ref/computed（无 Pinia） | 🔶 轻冲突 |
| 异步任务 | **禁用 Celery（F-12），queue.Queue + 守护线程** | **已用 Celery** | ❌ 冲突（见 §4.6） |
| 规则引擎 | 自研 Evaluator + AST 白名单 | rule_engine + derived_registry + condition_expression | 🔶 重叠，需统一 |
| 指标模型 | **3 层（RAW/COMPUTED/COMPOSITE_TEMPLATE）** | **2 层（Atomic/Derived）+ MetricTemplate** | ❌ 模型冲突（见 §4.2） |
| 条件结构 | **INV-1：禁止 AND/OR 树，仅单指标三元组** | MetricRule.logic 支持 AND/OR | ❌ 冲突（见 §4.3） |
| 数值精度 | **INV-9：Decimal-only，JSON 存字符串** | 部分用 float | ❌ 精度风险（见 §4.4） |

## 2. 概念映射表（规格书概念 → ATS-NEW 现状 → 缺口/动作）

| 规格书概念 | ATS-NEW 对应物 | 缺口 / 动作 |
|---|---|---|
| `IndicatorRegistry`（数据驱动注册） | `derived_registry.py`（**代码级**注册）+ `field_resolver` | 缺口：规格书要 DB 化注册（`IndicatorMeta` 模型）；建议保留 computed 代码注册，RAW 指标走模型配置 |
| RAW indicator | `AtomicMetric`（source_path） | ✅ 近等价，直接映射 |
| COMPUTED indicator | `DerivedMetric`（calc_func + base_path + params） | ✅ 近等价；我们的 `param_schema`/`input_kind` 已对齐 |
| COMPOSITE_TEMPLATE | `MetricTemplate`（atomic/derived + 运算符白名单） | 🔶 需增强：规格书把「指标模板」与「规则」分离更严格；建议新增 `CompositeMetric` 或扩展 MetricTemplate 支持嵌套 |
| Rule（scene + conditions + **VETO/DEDUCT/BONUS 三动作**） | `MetricRule`（scene/conditions/logic/**blocking 布尔**） | ❌ 缺口：需把单一 `blocking` 升级为动作类型枚举（veto/deduct/bonus） |
| Fact | `candidate_snapshot`（ORM→dict 三层叠加） | ✅ 意图等价 |
| Decision | `rule_trigger.evaluate_scene` 结果（passed/filtered） | 🔶 部分；需补充决策明细（命中项/动作） |
| `ParamField` / `param_schema` | `DerivedFuncItem.paramSchema`（刚落地） | ✅ **已收敛** |
| `input_kind` / `output_type` / `unit` | `derived_registry` 元数据（刚落地） | ✅ **已收敛** |
| `OperatorEvaluator` + `legal_operators()` 矩阵 | `UnifiedOperator`（11 种）+ `condition_expression` | 🔶 重叠；规格书新增 `SATISFY`/`NOT_SATISFY`（对 computed 断言），我们可能缺 |
| Validators V01–V16 | 现有 field_acl + 后端校验（零散） | ❌ 缺口：缺显式 16 门链；建议实现 `validation/` 校验链 |
| AST 白名单表达式 `expr.py` | `condition_expression` | 🔶 需审计是否用 `eval`；若是→替换为 AST 白名单 |
| Decimal-only | 数值比较多处 float | ❌ 缺口：Decimal 化 + JSON 字符串存储 |
| `RuleCache` + Redis Pub/Sub 失效 | Redis 缓存（无 Pub/Sub 失效） | 🔶 缺口：加失效机制（版本号或 Pub/Sub） |
| NL2Rule | 无 | ⏸ 二期，独立服务 |
| 三前端 F1/F2/F3（开发工作台/运营配置台/画像编辑器） | 统一 `MetricsWorkspace.vue` | 🔶 方向相反但同源；可保留统一页 + 角色入口 |

## 3. PRD 需求覆盖矩阵

| PRD 需求 | 满足度 | 说明 / 动作 |
|---|---|---|
| 80+ 指标注册 | 🔶 需改造 | 我们已有 atomic/derived + 注册表，工作量在「注册 80 个指标」而非框架；可行 |
| 4 业务场景（招聘流程/自动归档/评分规则/职位画像） | 🔶 需改造 | `SceneRecruitPair` 已覆盖 scene 维度；需把 4 流分别接入触发点 |
| 三套用户前端 F1/F2/F3 | 🔶 需改造 | 我们统一页可加角色/入口；不强拆三套 |
| 15 项互斥校验（mutex） | ❌ 缺口 | 实现 V01–V16 校验链（保存前服务端） |
| 三级指标注册（RAW/COMPUTED/COMPOSITE） | ❌ 冲突 | 见 §4.2，映射而非重写 |
| 模板函数 F1–F3（跳槽窗口/平均司龄/目标司龄） | ✅ 可直接 | 注册进 `derived_registry` 作为 COMPUTED 模板 |
| 实时命中预览 ≤500ms | ✅ 可直接 | 我们已有 `POST /metrics/rules/execute/`，SLA 可达 |
| 业务语言映射（VETO→必须满足…） | ✅ 可直接 | 加 i18n 标签即可 |
| NL2Rule 自然语言建规则 | ⏸ 二期 | 独立服务，API 对接 |
| Decimal 精度 / 表达式安全 | ❌ 缺口 | 见 §4.4 / §4.7 |
| 命中统计 / 审计日志 | 🔶 部分 | 我们有 `RuleExecutionLog`；规格书 `DecisionLog`/`RuleHitStat` 可对齐 |

## 4. 冲突与难落地项的处理建议

### 4.1 UI 组件库（Element Plus vs Naive UI）—— 不建议切换
切换成本极高、破坏现有设计一致性、且纯属沉没成本。把规格书的 `RuleWizard`/`ParamPanel`/`MutexResult` 交互逻辑用 **Naive UI 组件重写**（n-steps / n-form / n-alert），而不是引入 Element Plus。

### 4.2 指标模型（3 层 vs 2 层）—— 映射而非重写
- RAW → `AtomicMetric`（直接）
- COMPUTED → `DerivedMetric`（直接）
- COMPOSITE_TEMPLATE → 新增 `CompositeMetric` 模型（组合多个 atomic/derived + 运算符），或扩展 `MetricTemplate` 支持嵌套引用。
保留现有 2 层，只补第 3 层，避免动已运行的代码。

### 4.3 AND/OR 树（INV-1 禁止 vs 我们的 logic）—— 关键冲突，建议不采纳 INV-1
规格书 INV-1 把规则限制为「单指标三元组」，表达力不足。我们 `MetricRule.logic` 的 AND/OR 是真实业务需要（多条件组合筛选）。**建议**：保留 AND/OR 能力，不采纳 INV-1；若要坚持规格书一致性，仅在「单一指标阈值规则」场景遵循 INV-1，复杂规则走我们的 logic。

### 4.4 Decimal / 浮点精度 —— 采纳，高收益
把数值比较改为 `Decimal`，JSON 中以字符串存储（INV-11 防精度丢失）。中等工作量，直接消除一类隐蔽 bug。

### 4.5 Pydantic v2 作为「单一真相源」—— 不建议替换 DRF
DRF 已深度集成（序列化、权限、分页、CamelCase 渲染）。可在**校验层局部**用 Pydantic 做 Fact 组装契约校验，但主序列化保持 DRF，避免双序列化体系分裂。

### 4.6 Celery（F-12 禁用 vs 我们已用）—— 保留 Celery
规格书禁用 Celery 是因其一期无异步需求，其 `queue.Queue`+守护线程方案弱于 Celery。我们的异步解析/打分已依赖 Celery，**不应拆掉**。

### 4.7 表达式引擎安全（F-01 禁 eval/exec）—— 高优审计
必须确认 `condition_expression` 不用 `eval`/`exec`/`pickle`。若用，替换为 AST 白名单（规格书 `expr.py` 思路）。这是我们与规格书共同的红线。

### 4.8 缓存失效 —— 采纳增量
在现有 Redis 缓存上加失效机制：简单做法是用规则版本号/ETag，或按规格书做 Redis Pub/Sub 广播失效。P95 ≤5s 目标易达成。

## 5. 推荐的渐进式集成路线（结合方式）

- **Phase 0（待你确认）**：澄清规格书意图——替换 / 并存 / 仅参考。
- **Phase 1（低风险，立即）**：吸收规格书优秀点进现有层
  - 落地 16 校验门（validators）为保存前服务端链；
  - 数值比较 Decimal 化 + JSON 字符串存储；
  - 审计并 AST 白名单化条件表达式（消除 eval 风险）；
  - `MetricRule` 增加动作类型枚举（veto/deduct/bonus）替代单一 blocking；
  - 业务语言映射走 i18n。
- **Phase 2（中风险）**：指标模型扩展——新增 `CompositeMetric`，把规格书 RAW/COMPUTED/COMPOSITE 映射到我们的 3 层。
- **Phase 3（按需）**：实时命中预览 500ms（已具备）；模板函数 F1–F3 注册进 `derived_registry`。
- **Phase 4（二期）**：NL2Rule 独立服务，API 对接。

## 6. 收敛点（我们已做的正好对齐规格书）

- `param_schema` / `input_kind` / `output_type` / `unit`（`derived_registry` 刚落地）≈ 规格书 §3 `ParamField` + §7 元数据——**零成本对齐**。
- fail-loud（刚做）= 规格书「纯函数 + 异常降级 FAIL」哲学（INV-3）。
- 统一 `MetricsWorkspace` ≈ 规格书想把 dev/ops/portrait 收敛的思路（方向相反但同源）。

## 7. 待你决策的两个问题
1. 这份规格书是**替换 / 并存 / 仅参考**？决定 Phase 0 走向。
2. 是否同意「保留 AND/OR（不采纳 INV-1）」与「保留 Celery（不采纳 F-12）」两项偏离？这两项若强行对齐规格书会削弱我们现有能力。
