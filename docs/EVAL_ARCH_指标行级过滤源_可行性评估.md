# 评估报告：ARCH《指标作为行级过滤源 — 边界红线与统一接入》v1.5 可行性评估

| 项 | 内容 |
|---|---|
| 评估对象 | `ARCH_指标作为行级过滤源_边界红线与统一接入 (1).md`（v1.5 草案） |
| 评估基线 | 工作区 HEAD `ff3aaf43`（2026-10-12），全部现状结论经代码逐条核实（文件:行号见正文） |
| 评估维度 | ① 权限精细化管理能力 ② 指标统一化管理能力 ③ 避免重复造轮子 |
| 结论先行 | **总体可行，建议分批落地**；但文档的问题前提（Q2）与三处现状描述已过时，M03 需改建而非新建，否则将制造本方案铁律明令禁止的「词表漂移」 |

---

## 1. 核心结论摘要

| # | 结论 | 依据 |
|---|---|---|
| **C1** | 方案架构方向正确，与项目现有技术栈（Django+DRF / Vue3+Naive UI）和既有模块（scope_resolver 唯一真相源、expr_compiler 两级表达式、MetricEngine 统一求值器）高度契合，**无架构性冲突** | 全文引用的复用点全部存在且语义吻合（§2.3） |
| **C2** | **文档 Q2 前提已过时**：「CUSTOM 右值全是静态 id 列表、无法表达动态条件」不成立——`valueSource='dynamic'` 动态上下文已于 **2026-10-12 13:35（今日）合入主干**（commit `d2522c7a`），后端 `context_resolvers.py` + 前端 `useRoleDataPerm.ts`/`RuleConfigModal.vue` 全链路已落地 | `data_permission/context_resolvers.py:46-49`；`expr_compiler.py:254-338`；`web/app/src/composables/useRoleDataPerm.ts:55-56` |
| **C3** | 文档 §3 提议新建 `context_vars.py` 与现有 `context_resolvers.py` **构成第二套动态值注册表**，且「负责部门」取值来源存在**语义冲突**（文档裁决取管理单元展开 vs 现状取 `Department.leader`）。照文档实施 = 制造词表漂移，违反其自身铁律 #1 | `context_resolvers.py:60-80` vs 文档 §3.2 |
| **C4** | 文档 §5「三条接入路径并存」已不全：2026-10-08 新增第四条统一路径（`core/entity_scope.py` + `candidate/scope.py`），非 ViewSet 入口（导出/批量）已收口。M02 剩余工作量**小于**文档估算 | `core/entity_scope.py:23-68`；`candidate/scope.py:29-61` |
| **C5** | Q4（可见即可操作、无读写分离、无动作粒度）**完全属实**，是本方案中业务价值最高、安全收益最直接的部分；但 M07 的「逐入口显式接入」是全程最大执行风险（漏接 = 该动作不受限） | `candidate/views.py:158-169`；`candidate/models.py:109`（仅 referrer，无 locked_by/共享人） |
| **C6** | 指标统一化地基已由前置文档（T01–T05）基本建成：`MetricEngine.evaluate_metric_condition`、`EntryConditionFieldCatalogView` METRIC 源、entry_condition 全量模板化（migration 0007）均已落地。本文档 §4（rule_engine 接入）是第三个消费方，**属增量补齐而非从零建设** | `metrics/services/metric_engine.py:367`；`process/views.py:792`；`entry_condition/migrations/0007` |
| **C7** | 工作量修正：P0 约 3–3.5 天（含动态词表对账）、P1 约 3–3.5 天、P2 约 0.75 天，全量约 **7–8 天**（不含 M07 全写入口长尾 2–3 天）。文档 7 天估算在「改建 context_resolvers」前提下基本准确 | §6 |

---

## 2. 文档核心架构与技术选型分析

### 2.1 要解决的四个问题（文档 §0）核对

| # | 文档主张 | 代码核实结果 | 判定 |
|---|---|---|---|
| Q1 | `AtomicMetric` 无 `filterable` 标记，派生指标可被误配进行级过滤导致性能灾难 | `metrics/models.py:76-132` 确认无该字段；`_op_to_q()` 仅支持标量 Q 下推（`expr_compiler.py:182-240`） | ✅ 属实 |
| Q2 | CUSTOM 右值全静态、无动态上下文；关系维度不含管理单元 | **前半句已过时**：`valueSource='dynamic'` + `dynamicKey` 今日合入（`expr_compiler.py:337-338`、`context_resolvers.py:46-49`）；后半句属实：`field_map.py:19-50` 确无 `unit` 维度 | ⚠️ 部分过时 |
| Q3 | `rule_engine` 的 `Condition.field` 裸字符串与指标词表脱钩；行级接入三路径并存 | 前半句属实但**影响被高估**：entry_condition 已用「预解析进 context.extra」工作流使 METRIC 条件在 rule_engine 中可求值（`entry_condition/services.py:277-288`，键为模板 UUID）；后半句已变为四路径（C4） | ⚠️ 部分高估/过时 |
| Q4 | 行级仅「可见范围」单一语义，可见即可操作，无查看/操作分离 | 完全属实：`candidate/views.py:158-169`（update 仅读范围 + V2Permission）；`models.py:59-65`（RowScopeType 无 OWNER）；`models.py:74-110`（无 row_access 字段）；无独立锁定字段（`candidate/models.py:109`） | ✅ 属实 |

### 2.2 设计铁律评价（文档 §1）

| 铁律 | 评价 |
|---|---|
| 单一词表（AtomicMetric 唯一真相源） | 方向正确，且前置文档已按此建成三消费方中的两个（data_permission / entry_condition）。**但文档自身 §3 的 context_vars 方案违反了该铁律在「动态值」域的投影**（C3） |
| 场景二分红线（可下推→行级 / 计算型→点评估） | 技术判断准确。派生指标逐行 Python 求值确实无法服务于分页/导出；`filterable` 元数据 + 保存期拦截（而非运行期静默降级）的时机选择正确 |
| 不重复造轮子（委托 `MetricEngine.evaluate_metric_condition`） | 引用属实（`metric_engine.py:367` 存在），委托设计零改动复用 `_compare`/`_resolve_metric_value`，选型合理 |
| 降维原则（配置界面只见条件项） | 与项目现有配置 UI 形态一致（`RuleConfigModal.vue` 维度卡驱动），认知负荷控制到位 |
| fail-safe 与既有约定一致 | 与 `expr_compiler` 现状（编译失败 no-op）及 scope_resolver fail-closed 基调吻合；动态解析失败比静态更严（`_deny_all`）的处理与 `context_resolvers.py:41-43` 的 `ContextResolveError` 约定一致 |
| 最小改动 | 全部模型改动为可空外键 / 带默认值字段，天然回滚开关，迁移风险低 |

### 2.3 实现机制要点

1. **filterable 红线（§2）**：`AtomicMetric.filterable` + `DerivedMetric` 一律 False + 内省回填迁移。机制干净；v1.4 将数据权限目录收窄为「维度 + 布尔组合」是合理的性能边界守护（JSON 路径/正则/负向操作符的全表扫描隐患确实存在）。
2. **context 右值三形态（§3.1）**：静态 / 上下文变量 / 属性条件（下线保留代码）。形态设计合理，但与现有 `valueSource: 'static'|'dynamic'` + `relation` 四档（exact/in_subtree/contains/overlap）**是两套并行的值形态词汇**（详见 §5.1 差距 G1）。
3. **unit 复合维度（§3.3）**：复用 `iter_unit_scopes`（`scope_resolver.py:414-444`）单一实现点、`Q(dept__in) | Q(creator__in)` 与默认 scope 同构、引用语义（非快照）——设计质量高，是全文档最见功力的部分。
4. **空范围单元三层护栏（§3.3.4）**：静态检测 warnings / 范围完整度标识 / 零命中引导。「空集不放行、永不兜底放宽」原则正确。
5. **读写分离 + 动作注册表（§6）**：WRITE ⊆ READ 不变式由执行链自然保证的论证成立；动作集合资源级全局、拒绝行×动作笛卡尔积的防过度设计边界清醒。

---

## 3. 与现状代码的核对总表（文档准确性审计）

| 文档断言 | 核实结果 | 位置 |
|---|---|---|
| `expr_compiler._op_to_q()` 只支持标量 Q 下推 | ✅ 属实 | `expr_compiler.py:182-240` |
| `attribute_fields.py` 复用 AtomicMetric 但无 filterable 约束 | ✅ 属实 | `attribute_fields.py:103-107` |
| `field_map.py` 维度表无 unit | ✅ 属实 | `field_map.py:19-58` |
| `scope_resolver` 旧预设仅 SELF/DEPT、无法与表达式组合 | ✅ 属实 | `scope_resolver.py:12-123` |
| `iter_unit_scopes` 可复用 | ✅ 存在且语义吻合 | `scope_resolver.py:414-444` |
| 行级接入三条路径 | ⚠️ 实为**四条**（新增 `entity_scope_q`/`scoped_candidates`） | `core/entity_scope.py`、`candidate/scope.py`（2026-10-08） |
| `process/views.py:270` 直调绕过默认 scope 回退 | ✅ 属实，但系**有意为之**（process 无 scope_field，注释明示） | `process/views.py:264-273` |
| `clear_column_cache` 硬编码三 entity | ✅ 属实 | `enforcement.py:96-103` |
| `ManagementUnitMember.PERSON` 「仅存储展示，执行面待补」 | ❌ **已过时**：PERSON→User 映射 2026-09-16 已实现（模型注释 stale） | `scope_resolver.py:295-322` vs `models_permission_v2.py:177` |
| CUSTOM 右值全是静态 id 列表 | ❌ **已过时**：动态上下文今日 13:35 合入 | `context_resolvers.py`、commit `d2522c7a` |
| `rule_engine` `Condition.field` 裸字符串致 METRIC 条件断裂 | ⚠️ 高估：预解析工作流已使其可求值 | `entry_condition/services.py:277-288` |
| 前置文档 T01–T05 迁移中/待接 | ❌ 已基本完成：求值器、目录 METRIC 源、entry_condition METRIC + 0007 均已落地 | `metric_engine.py:367`、`process/views.py:792`、migration `0007` |
| `candidate` update 仅 V2Permission 无 object 级写拦截 | ✅ 属实 | `candidate/views.py:158-169` |
| 归属字段 referrer、无独立锁定字段 | ✅ 属实 | `candidate/models.py:109` |

**审计结论**：文档对 Q1/Q4 及执行链路的现状描述精确到行号，质量很高；但 **Q2 前提、PERSON 现状、接入路径数、前置文档进度** 四项需修订。另有两个文档未覆盖的现状事实直接影响方案设计（见 §5 差距 G2、G5）。

---

## 4. 三维度可行性评估

### 4.1 维度一：权限精细化管理能力 —— 可行，价值最高，执行风险集中在 M07

**适配度：高。** 文档直击本项目行级权限的三个真实缺口：

| 缺口 | 现状证据 | 方案对应 | 评价 |
|---|---|---|---|
| 可见即可操作（越权写） | `candidate/views.py:158` update 仅读范围+功能权限 | WRITE 行范围 + `ensure_writable` | 直接闭合安全缺口；「非锁定人可看、仅锁定人可操作」是招聘域高频真实需求 |
| 动作无粒度 | V2Permission 仅 list/create/edit/delete 四后缀（`permissions_v2.py:17-25`） | `ACTION_REGISTRY` 注册制 + 预设包 | 「锁定人可编辑但不可删除/导出」无法被现有四后缀表达，确需补充 |
| 管理单元无法进行级表达式 | `field_map.py` 无 unit | unit 复合维度 + `user.managed_units` | 管理单元是行级可见范围核心载体（`models_permission_v2.py:133`），补上它后 CUSTOM 表达力才完整 |

**灵活性配置能力**：两级布尔表达式（组内/组间，6 条语法约束）+ 维度卡 + 上下文快捷主体 + 动作预设包，配置模型扁平且防爆炸（拒绝行×动作笛卡尔积）。对 B 端权限管理而言，表达能力与认知负荷的平衡点选择得当。

**主要制约**：
- `ensure_writable(obj, action)` 逐入口显式接入，candidate 写面广（update/transition/claim/merge/批量/feedback/export/delete），**漏接即失效**——文档待明确 #7 已自识，grep 守卫测试是必要非充分条件；
- 示例配置中「共享人」维度在系统中无任何承载（模型无 share 字段、field_map 无维度），**该条示例条件无法 1:1 落地**，需产品侧先明确共享人的业务建模，不能仅靠权限层表达。

### 4.2 维度二：指标统一化管理能力 —— 可行，地基已由前置文档建成，本文档属增量补齐

**适配度：高（剩余工作量小）。** 「指标作为唯一词表」的三消费方格局：

| 消费方 | 状态 | 证据 |
|---|---|---|
| data_permission（属性条件目录） | ✅ 已接 | `attribute_fields.py:103`（AtomicMetric 驱动，还附带了 templateId/metricKind） |
| entry_condition（进入条件 METRIC 源） | ✅ 已接（全量模板化） | `models.py:33` + migration `0007`（field 统一存模板 id） |
| rule_engine（TCA/POLICY 条件） | ⬜ 本文档 §4 目标 | `rule_engine/models.py:211-243`（Condition 无 FK） |

**机制评价**：`Condition.metric_template` 可空外键 = 天然回滚开关；双读兼容不强制迁移存量；派生指标在点评估场景天然合法（`filterable=False` 不拦 evaluation）——红线互补面论证成立。

**需要修正的认知**：M04 不是「修复一条断裂的链路」。现状下 entry_condition 的 METRIC 条件经 `sync_entry_condition_rule_to_unified` 镜像进 rule_engine 后，靠调用方把指标值预解析进 `context.extra`（键=模板 UUID）完成求值（`entry_condition/services.py:277-288`）。该工作流的两个隐患是 M04 的真实价值：① 任何不做预解析的 rule_engine 消费方（含 rule_engine 自身配置界面直配的规则）拿到模板 UUID 当 field 名必然落空；② 预解析把「指标口径」的解析责任推给了每个调用方。M04 应定位为**让 METRIC 条件在 rule_engine 内自描述**，优先级维持 P1 合理，但不宜按「救火」排期。

### 4.3 维度三：避免重复造轮子 —— 复用纪律总体优秀，但 §3 自身构成最大的重复造轮子风险

**复用点全部核实存在**：`scope_filter_q`（`scope_resolver.py:461`）、`iter_unit_scopes`（:414）、`evaluate_metric_condition`（`metric_engine.py:367`）、`UnifiedOperator`（`rule_engine/models.py:56`）、`EntryConditionFieldCatalogView`（`process/views.py:792`）、`expr_compiler` 两级表达式、`FieldDef` 前端控件族。「委托而非重写、单一实现点、引用语义非快照」等原则执行到位。

**但存在三处内生的轮子重复风险**：

| # | 风险 | 说明 |
|---|---|---|
| R1 | **`context_vars.py` vs `context_resolvers.py` 双注册表** | 两套 key 词汇（`user.managed_depts` vs `currentUser.departments`）、两套值形态（`valueType:'context'` vs `valueSource:'dynamic'+relation`）、两套维度支持（owner/dept/unit vs 仅 dept）、**两套互相冲突的「负责部门」解析源**（管理单元展开 vs `Department.leader`）。这正是文档铁律 #1「单一词表」要消灭的漂移，且前端已按旧词汇实现（`useRoleDataPerm.ts:55-56`），新表上线即三处词汇分裂（后端编译/后端校验/前端标签） |
| R2 | `write_scope_q` 与 `role_entity_scope_q` 并行 | 文档自称「对称」尚可接受，但两者共享 RBAC 并集/优先级消解逻辑，需确认不产生第二套组合语义 |
| R3 | `attribute_fields_for(entity, scenario)` 场景参数 | 小改动，无实质重复风险 |

**另有两个文档未覆盖、但直接影响「不重复造轮子」的现状事实**：

- **`ScopeQuerysetMixin.scope_queryset()` 与 `scope_filter_q()` 是两套并行实现且语义分叉**（差距 G2）：mixin 只用 `unit_ids_to_dept_ids`（仅部门），缺失成员 USER 的 `created_by__in` OR 分支与 data_range AND 限制（`permissions_v2.py:215-233` vs `scope_resolver.py:514-539`）。同一用户经 candidate 列表（scope_filter_q）可见的「单元 USER 成员创建的候选人」，经 demand/position 等 9 个走 mixin 的 ViewSet 看不到。**这是比文档 Q3 更实体的口径漂移**，M02 的「mixin 吸收 scope_filter_q 全语义」应据此扩容并补回归测试。
- **rule_engine 是活跃的规则中台**：`bridge.py` 已将 entry_condition / mou / time_limit / campus_control / offer 五类领域规则镜像入统一引擎（`rule_engine/bridge.py:224+`）。M04 加 FK 后需评估 bridge 的 Condition 创建是否同步携带 metric_template（至少 entry_condition 分支应携带），否则镜像规则仍是「裸 field + 预解析」旧模式。

---

## 5. 适配差距清单（Gap Analysis）

| # | 差距 | 性质 | 影响面 | 处置建议 |
|---|---|---|---|---|
| **G1** | 动态值双注册表 + 「负责部门」两套解析源（管理单元展开 vs `Department.leader`） | 词汇/语义冲突 | 后端编译与校验、前端标签、存量已存规则的行为 | **M03 改建**：扩展 `context_resolvers.py` 新增 `user.pk`/`user.managed_units` 键与 owner/creator 维度支持，不新建文件；「负责部门」取源做显式裁决（建议采纳 v1.5 管理单元口径，但以新 key 或带迁移的语义切换落地，**禁止静默改变存量 key 语义**） |
| **G2** | `scope_queryset` 与 `scope_filter_q` 语义分叉（成员 USER/data_range 缺失） | 行为不一致（现存缺陷） | 9 个走 mixin 的 ViewSet | M02 委托化时一并修复；行为变更（部分用户可见行变多）需回归 + 发布说明 |
| **G3** | process 路径③删除后的默认回退 | 行为收窄风险 | process 列表可见性 | process 无 scope_field，mixin 回退 SELF 会把「无 CUSTOM 规则用户看全量」收紧为「仅自己创建」。需产品确认预期，或为 process 显式声明 creator-only 默认 |
| **G4** | 「共享人」维度无业务承载 | 需求缺口 | 示例配置 1:1 落地 | 权限层无法独立解决；需产品明确共享建模（新维度 or 新字段），文档应将其移出「权限配置可表达」范围 |
| **G5** | PERSON 执行面已实现（模型注释 stale） | 文档事实错误 | 无功能影响 | 修正模型注释与文档待明确 #6；`collect_unit_member_users` 已是单一实现点，unit 维度上线自动获益 |
| **G6** | M07 写入口全覆盖长尾 | 工作量缺口 | candidate 全部写路径 | 文档 2 天为「样板」口径；全量覆盖需另列 2–3 天并按守卫测试分批推进 |
| **G7** | bridge 未携带 metric_template | 一致性缺口 | rule_engine 镜像规则 | M04 顺带评估 entry_condition 分支携带 FK 的可行性 |

---

## 6. 潜在风险与改造工作量评估

### 6.1 风险登记册（按 severity 排序）

| # | 风险 | 等级 | 触发条件 | 缓解措施 |
|---|---|---|---|---|
| V1 | 动态词表三处分裂（后端编译/校验/前端） | **高** | 按文档新建 `context_vars.py` | 改建 `context_resolvers.py`；新增 key 前后端同步注册；守卫测试断言两处 key 集合一致 |
| V2 | 存量「我的负责部门」规则语义被静默切换 | **高** | 直接改 `responsible_department_ids` 取源 | 新 key（如 `currentUser.managedDepartments`）+ 旧 key 保留；或带数据迁移与发布说明的显式切换；二选一，不留中间态 |
| V3 | WRITE 执行链漏接导致动作不受限 | **高** | 新增动作未接 `ensure_writable` | grep 守卫测试（文档待明确 #7 已提出）+ candidate 写面安全评审清单 + 灰度期审计日志 |
| V4 | mixin 委托化引入可见性回归 | 中 | 9 个 ViewSet 行为变更 | 委托前后对同一 fixture 跑 SQL 断言对比；补 `test_scope_wiring.py` 遍历全部 entity |
| V5 | process 可见性意外收窄 | 中 | 路径③删除 + SELF 回退 | 与产品确认后显式声明默认 scope；或保留 process 特例并注释理由 |
| V6 | filterable 回填迁移误标 | 低 | 内省规则覆盖不全 | 迁移后抽样审计；派生指标一律 False 的硬约束兜底 |
| V7 | context 编译不缓存带来的查询放大 | 低 | 每请求编译 | 文档 §3.4 决策正确（≤ 十几条条件、<1ms）；组织范围变更为低频事件，可接受 |

### 6.2 工作量修正（对比文档 §8）

| 任务 | 文档估算 | 修正估算 | 修正理由 |
|---|---|---|---|
| M01 filterable + 回填 | 0.25d | 0.25d | 准确 |
| M02 接入收敛 + 守卫测试 | 1d | 0.75–1d | entity_scope.py 已完成非 ViewSet 收口；剩余 candidate:133、process:270、mixin 委托；但需补 G2 语义对齐回归 |
| M03 context + unit + 护栏 | 1.5d | **2–2.5d** | 若新建 context_vars.py 另加 V1/V2 风险；改建 context_resolvers 含：新 key×2 + 维度扩展 + unit 复合展开 + 前端卡片与快捷主体 + 护栏一 warnings |
| M04 rule_engine 接入 | 1d | 1d | 准确（FK + 委托 + 双读 + 单测） |
| M05 entry_condition 收尾 | 0.5d | ≈0.1d | migration 0007 与 METRIC 求值均已落地，仅验证性收尾 |
| M06 预览 + 完整度标识 | 0.75d | 0.75d | 准确 |
| M07 读写分离 + 动作 | 2d | 2d（样板）+ **2–3d（全写入口长尾）** | 模型/执行层/样板入口 2d 合理；candidate 全写面覆盖需单列 |
| **文档未列新增** | — | **+0.5–1d** | 动态词表对账与切换（V1/V2 处置）、PERSON 注释修正、bridge 携带 FK 评估 |
| **合计** | ≈7d | **P0 ≈ 3–3.5d；P1 ≈ 3–3.5d；P2 ≈ 0.75d；全量 ≈ 7–8d（不含 M07 长尾）** | 文档总量估算在「改建而非新建」前提下基本可信；真正的偏差在结构（M03 变重、M02/M05 变轻、M07 有隐藏长尾） |

---

## 7. 落地建议

### 7.1 批次路线（建议顺序）

**第一批（P0，约 3–3.5 天）——先修口径，再开新维度**
1. **M02 先行**：mixin 委托 `scope_filter_q` 全语义（含 G2 修复）+ candidate/process 直调收敛 + `test_scope_wiring.py` 守卫测试。理由：unit 维度编译与读写分离都骑在统一执行链上，口径不先收口，后面全是重复返工。
2. **M03 改建**：扩展 `context_resolvers.py`（新增 `user.pk`、`user.managed_units` 键，维度从 dept 扩到 owner/creator）+ unit 复合维度编译 + 前端 unit 卡片与快捷主体 + 空壳护栏一。**不新建 `context_vars.py`**。
3. **M01 随行**：成本仅 0.25 天，为评估场景元数据与未来开口子留边界，无理由割裂。

**第二批（P1，约 3–3.5 天）——补齐词表统一与安全缺口**
4. **M04**：rule_engine `metric_template` FK + 委托 + 双读；顺带评估 bridge 携带 FK（G7）。
5. **M07 样板**：row_access + OWNER + `write_scope_q` + `ACTION_REGISTRY` + candidate 主写入口（update/transition）+ grep 守卫测试。**全写入口长尾单列任务、按守卫测试分批推进**，不堵在主线。
6. **M05**：验证性收尾（≈0.1d）。

**第三批（P2，约 0.75 天）——体验护栏**
7. **M06**：预览可见范围（与列表同源调 `scope_filter_q`）+ 零命中排查引导 + 管理单元范围完整度标识。

### 7.2 对文档的修订请求（合并进 v1.6）

| # | 修订项 |
|---|---|
| D1 | Q2 前提改写：动态上下文已存在（`context_resolvers.py`，2026-10-12 合入），本文档 §3 应定位为「扩展」而非「从无到有」 |
| D2 | §3 落点从「新建 `context_vars.py`」改为「扩展 `context_resolvers.py`」；新 key 与存量 key 的关系、切换策略显式成文 |
| D3 | 「负责部门」取源裁决（v1.5）需补充与存量 `currentUser.departments`（leader 口径）的迁移/兼容方案 |
| D4 | §5 现状表更新为四路径，纳入 `core/entity_scope.py`/`candidate/scope.py`；文件清单 §7 补充这两个文件 |
| D5 | PERSON 现状按 `scope_resolver.py:295-322` 更正（执行面已生效），并修正 `models_permission_v2.py:177` 的 stale 注释 |
| D6 | §5.2 补充 G2：mixin 与 `scope_filter_q` 的语义分叉（成员 USER / data_range）及委托化回归要求 |
| D7 | 「共享人」示例条件移出权限层可表达范围，转产品需求（G4） |
| D8 | M07 拆分「样板」与「全写入口覆盖」两个任务，后者单列估算 |

### 7.3 一句话结论

该方案在架构方向、红线划分与复用纪律上质量很高，**建议立项**；但实施时必须把 M03 从「新建第二套动态值体系」纠正为「扩展现有体系」，并先完成 M02 的执行链口径收口——否则将以每日数行的"小改动"为代价，换来三处词汇分裂和两个隐性行为变更，恰是本方案铁律所要避免的结局。

---

*评估方法说明：本报告全部现状结论均通过对工作区 HEAD（ff3aaf43）源码逐条核实得出，引用以 `文件:行号` 标注；凡与文档断言不符处均已在 §3 审计总表中标明「属实/过时/高估」。*
