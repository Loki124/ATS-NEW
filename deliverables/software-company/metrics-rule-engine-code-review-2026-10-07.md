# 指标管理 + 规则引擎 代码审查报告

- **审查日期**：2026-10-07
- **审查范围**：`apps/django/apps/metrics/`（20 测试文件 / 250 用例）、`apps/django/apps/rule_engine/`（36 文件）、前端 `MetricsWorkspace.vue`(2373行) / `RuleAuthoring.vue`(654行) / `locales/metrics.ts`(654行)
- **审查方式**：4 研究员并行覆盖 5 维度 + 主理人**独立运行时核验**关键结论（不采信转述）
- **基准**：`apps/django/tests/test_no_blind_except.py` 实跑 · `apps/metrics/tests/` 实跑 250 passed
- **规范依据**：`AGENTS.md` v2.1.0（R-1xx交互 / R-2xx系统级 / R-215区域滚动）

---

## 摘要

| 等级    | 数量     | 说明                                                                            |
| ----- | ------ | ----------------------------------------------------------------------------- |
| 🔴 严重 | **15** | 4 项已运行时坐实的**级联失效** + 1 项护栏红灯 + 1 项"自己吞自己异常" + 引用悬空 + 零留痕 + 并发 500 + 6 项 UX 阻断 |
| 🟠 中等 | **31** | 含分页规范违反、假撤销、无二次确认、错误信息丢失、N+1、写入校验绕过等                                          |
| 🟡 轻微 | **26** | 死代码、aria 缺失、文案不一致、迁移反向风险等                                                     |

**最重要的发现**：存在一&#x7C7B;**「配置全对、后端校验也过、但实际行为与配置完全无关」**&#x7684;级联失效（严重 #1、#2），而 250 个测试全绿察觉不到——测试直接手搓 dict 调引擎，绕过了出问题的转换层。

**最恶劣的单点缺陷**：`serializers.py:262` 的 `raise ValidationError` 写在 `:258` 的 `try` 块内，被 `:264` 的 `except Exception: pass` 吞掉——**校验代码存在但永不生效**（详见 B-1）。

---

## 🔴 严重（12 项）

### B-1【运行时坐实·最恶劣】`raise ValidationError` 被自己的 `except` 吞掉 → 校验代码永不生效

| 项         | 内容                                                                                        |
| --------- | ----------------------------------------------------------------------------------------- |
| **文件:行号** | `apps/metrics/serializers.py:258-265`（`raise` 在 `:262`，`except Exception: pass` 在 `:264`） |
| **角色/路径** | HR 专员 → 规则编排 → 配「指标对比」→ 左右指标类型不一致（number vs string）→ 保存**成功**                             |

**问题**：类型一致性校验的 `raise serializers.ValidationError(...)` 写在 `try` 块内部，被同函数的 `except Exception: pass` 捕获。**该校验永远不会触发**。

运行时铁证：

```
当前实现（try内raise）: NO_ERROR_RAISED
>>> 结论：:262 的 raise 被 :264 吞掉 → 类型一致性校验 NEVER fires
```

**`:264` noqa 注释的理由站不住**：注释写"类型一致性校验属 best-effort, DB 异常跳过（引擎侧已有类型守卫兜底）"。但引擎守卫（`metric_engine.py:241-246`）在**求值期**，这里丢的是**配置期保存拦截**——两者不互相替代。用户保存时得不到任何提示，直到规则在生产中运行才降级失败。

**影响场景**：HR 配「候选人年龄(number) ≤ 职位薪资(string)」→ 保存成功 → 规则创建 → 每次执行都因类型不匹配降级 FAIL → VETO 类规则**恒定拦截所有人**，且用户完全无法从配置界面发现问题。

**修复建议**：

1. 把 DB 查询（`:259-260`）留在 try 内，**把类型比较与 raise 移出 try**
2. 修法：

```python
lt = rt = None
try:
    lt = MetricTemplate.objects.filter(pk=template_id).first()
    rt = MetricTemplate.objects.filter(pk=right_template_id).first()
except Exception:  # noqa: BLE001 — DB 异常按best-effort 跳过
    pass
if lt and rt and lt.data_type != rt.data_type:
    raise serializers.ValidationError(f'第 {idx} 个条件左右指标类型不一致（{lt.data_type} vs {rt.data_type}）')
```

1. **补测试**：`test_metric_condition_evaluator.py` 缺"serializer 拒绝类型不一致"的用例——这正是它绿灯的原因

---

### S-1【运行时坐实】方案 B「指标 vs 指标」全链路静默失效

| 项         | 内容                                                                                                                                                      |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **文件:行号** | `apps/metrics/models.py:384-389`、`apps/metrics/views.py:484-489`、`apps/metrics/views.py:501-506`（丢弃点）；`apps/metrics/services/metric_engine.py:157`（读取点） |
| **角色/路径** | HR 专员 → 规则配置 → 选「对比指标」模式 → 配「候选人年龄 ≤ 职位薪资上限」→ 保存                                                                                                        |

**问题**：`rightTemplateId` 在进入引擎前有 3 处丢弃点，均只透传 `templateId/operator/value/meta` 4 个键；而引擎 `:157` 读的正是 `cond.get('rightTemplateId')`。

运行时铁证（`config.settings.test` 实跑）：

```
落库 conditions : [{'templateId':'tpl-a','operator':'GTE','value':3,'rightTemplateId':'tpl-b'}]
引擎契约 输出   : [{'templateId':'tpl-a','operator':'GTE','value':3,'meta':{}}]
>>> rightTemplateId 是否存活: False
```

→ 走 `:166` else 常量分支，右值模板从未被访问，条件退化为「指标 >= 常量 3」。

**影响场景**：用户配了、保存成功、后端 `rule_validators` 与 serializer 都校验通过 → 实际行为与配置无关。若`actionType='VETO'`，则所有人被拦，提示文案还显示为与配置无关的话术。

**为何 250 测试全绿**：`tests/test_metric_condition_evaluator.py:184-188` 直接手搓 dict 调 `execute()`，绕过 `to_engine_conditions` 与 View。

**修复建议**：

1. 三处补 `'rightTemplateId': cond.get('rightTemplateId') or cond.get('right_template_id')`（引擎 `:157` 已兼容两种拼写，无需改引擎）
2. 删除死方法 `views.py:501-506` `_to_engine_conditions`（`views.py:457` 实际用 `_normalize`）
3. **必须补穿透测试**：`MetricRule.objects.create(conditions=[{...rightTemplateId}]) → to_engine_conditions() → execute` 断言 `pass is True`。缺这条，回归会再次静默劣化

---

### S-2【运行时坐实】两条求值路径「模板已禁用」判定相反

| 项         | 内容                                                                  |
| --------- | ------------------------------------------------------------------- |
| **文件:行号** | `metric_engine.py:386-394`（有校验）vs `metric_engine.py:117-123`（只判存在性） |
| **角色/路径** | 管理员 → 指标管理 → 禁用某模板（经LIFE-2 受影响规则弹窗）                                 |

**问题**：

- `evaluate_metric_condition`（`:386`，进入条件走）：判 `status != 'enabled' or deleted_at is not None` → FAIL ✅
- `_evaluate_condition`（`:117`，`MetricEngine.execute` → 入池/评分/筛选走）：**只判 `template is None`**，无禁用态校验 ❌

**影响场景**：禁用模板后，进入条件类规则立即失效，但入池/评分/筛选类**继续用已禁用模板求值并阻断业务**——方向危险（该关的没关）。`_resolve_right_side:227` 有校验，说明作者知情，只是漏了主路径。

**修复建议**：抽 `get_enabled_template()` helper，两处统一；`_evaluate_condition` 改用 `filter(pk=..., status='enabled', deleted_at__isnull=True)`

---

### S-3【运行时坐实】BLE001 护栏红灯，主仓当前 3 failed

| 项         | 内容                                                      |
| --------- | ------------------------------------------------------- |
| **文件:行号** | `apps/django/tests/test_no_blind_except.py:43-45`（基线定义） |
| **角色/路径** | 全体开发者 / CI                                              |

**实跑结果**（`.venv/bin/python -m pytest tests/test_no_blind_except.py`）：

```
FAILED test_all_except_exception_have_noqa_license
FAILED test_no_unlicensed_except_exception
       apps/data_permission/attribute_fields.py:118 缺少 # noqa: BLE001 标记
FAILED test_blind_except_below_phase_two_limit
       AssertionError: 阶段二目标未达成: 当前 120, 上限 84
```

**影响场景**：`HISTORICAL_BASELINE=196` 的老用例仍过（120 ≤ 196）→ **粗看是绿的**，但唯一锁定下限的 `HARD_LIMIT` 用例是红的。基线 196→84 之间有 36 的静默漂移空间。metrics 是最大单一来源（36 处）。

**修复建议**（分两步）：

1. **零风险**：`process/services/rule_item_evaluator.py:165/:170` 的 `# noqa: BLE001` 补 ≥5 字符意图说明（`:160` 有说明故豁免）；`data_permission/attribute_fields.py:118` 补 noqa
2. **需专项**：120 → 84。优先降 `metric_engine.py`（9 处，其中 `:419/425/431` 是三处快照构建，可合并为一次 try）

---

### B-2【严重】删除模板无引用保护 → 已启用规则悬空，VETO 恒拦截所有人

| 项         | 内容                                                                                                   |
| --------- | ---------------------------------------------------------------------------------------------------- |
| **文件:行号** | `apps/metrics/views.py:121`（`MetricTemplateViewSet` 未用 `_RefCheckMixin`）vs `views.py:97-106`（指标侧有保护） |
| **角色/路径** | HR 专员/管理员 → 删除被 N 条规则引用的模板 → 规则仍`enabled`                                                            |

**问题**：删**指标**有 `_RefCheckMixin` 保护（实测返回 400 `该指标被 1 个模板引用，无法删除`，行为正确）；删**模板**却完全裸奔。`conditions` 是 JSONField 而非 FK，DB 层无任何约束。

实测：

```
DELETE /templates/{id} -> 204
模板还在? False
规则还在? True | conditions.templateId = 'lu-4_eCHWzBjwkFgbij3B'
>>> 悬空: True
```

**影响场景**：模板被删后 `metric_engine.py:120` 报「模板 … 不存在」→ 该步 FAIL → `rule_trigger.py:150-151` 判`blocked=True` → **所有候选人被拒绝入池，且原因显示为一个不存在的模板 id**。保护不对称是设计疏漏。

**修复建议**：`MetricTemplateViewSet.destroy` 覆写，复用现成 `services/template_impact.py:51 get_template_affected_rules`（已实现，覆盖 entry_condition / stage_rules / metric_rules 四层路径，零新增查询逻辑），`total > 0` 时返回 400 + 受影响规则清单。

---

### B-3【严重】模板版本快照无锁，并发更新撞唯一约束 → IntegrityError 逃逸为 500

| 项         | 内容                                                                                                                                   |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **文件:行号** | `services/template_version.py:123-131`（`objects.create`）、`views.py:145-152`（`perform_update`）、`models.py:249`（`uniq_tpl_version` 约束） |
| **角色/路径** | 两名 HR 同时编辑同一模板 → 并发 PATCH                                                                                                            |

**问题**：`perform_update` 先 `instance.version += 1` 再 `save` 再建快照，**无 `transaction.atomic()`、无 `select_for_update()`**。两个并发 PATCH 读到同一 version → 后写者撞 `uniq_tpl_version` → `IntegrityError` 逃逸到全局 handler → **500**，违反项目 FAIL-not-500 约定。

实测：重复写 `version=1` → `IntegrityError: UNIQUE constraint failed`。

**影响场景**：用户看到 500 而非「该模板已被他人修改，请刷新」，且**快照表可能残留孤儿行**。`MetricRule` 无 version 字段，规则更新是last-write-wins（无冲突检测）。

**修复建议**：`perform_update` 包 `transaction.atomic()` + `select_for_update()`，或 `create_version_snapshot` 改 `get_or_create`；捕获 `IntegrityError` 转人话 409提示。

---

### S-4【严重 UX】列表加载失败被误报为「无数据」

| 项         | 内容                                                    |
| --------- | ----------------------------------------------------- |
| **文件:行号** | `MetricsWorkspace.vue:44-58`、`:115-131`、`:1830-1832`  |
| **角色/路径** | HR 专员 → 指标管理 → 后端 500/超时 → 页面显示「没有匹配的指标定义，试试调整关键词或分类」 |

**问题**：`load()` catch 只 `message.error`，**不设错误态标记**，`definitions` 保持空数组 → UI 走 `v-if="!loading && !length"` 分支渲染「无数据」。文案在加载失败语境下是事实性错误，HR 会反复调关键词。违反 R-104（禁止静默失败）+ R-111（「全部失败」独立态）。

**修复建议**：新增 `loadError` ref；空态判定改三分支（loading 骨架屏 / loadError → `n-result status="error"` + 重新加载 / 无数据 → 现有 empty）

---

### S-5【严重 UX】`metrics.msg.updated` 键 ZH/EN 均缺失 → Toast 显示裸键名

| 项         | 内容                                                                                           |
| --------- | -------------------------------------------------------------------------------------------- |
| **文件:行号** | `MetricsWorkspace.vue:1524` 引用；`locales/metrics.ts:115`(ZH 仅 created) / `:439`(EN 仅 created) |
| **角色/路径** | HR 专员 → 指标模板 Tab → 编辑模板 → 保存 → Toast 弹出字面量 `metrics.msg.updated`                             |

**已核实**：`metrics.msg.created` 两侧存在，**`updated` 全库唯一缺失**。vue-i18n 缺键回退渲染 key 本身。

**修复建议**：ZH `:115` 后补 `'metrics.msg.updated': '更新成功'`，EN `:439` 后补 `'metrics.msg.updated': 'Updated'`；**建议加 lint 闸门**防同类复发

---

### S-6【严重 UX】删除模板的「撤销」是假撤销 → 引用规则全部断链

| 项         | 内容                                                                  |
| --------- | ------------------------------------------------------------------- |
| **文件:行号** | `MetricsWorkspace.vue:1556-1594`（`restorePayload` 不含 `id`）          |
| **角色/路径** | HR 专员 → 删除被 N 条规则引用的模板 → 8s 内点「撤销」→ Toast 显示「已恢复」→ 实际所有引用该模板的规则条件失效 |

**问题**：`restorePayload` 无 `id`，`createMetricTemplate` 走 POST 新建 → **全新 id**。而规则条件存的是模板 id 字符串（`services/template_impact.py:83` `filter(field=tid)`），`MetricTemplateVersion.template` 是 `on_delete=CASCADE`（`models.py:249`）历史版本一并消失。违反 R-106「撤销必须回到等价状态」，且属假绿。

**修复建议**（二选一）：

1. 后端补 `POST /metrics/templates/{id}/restore/`（软删恢复原 id + 重建快照）
2. 若不动后端，**至少让文案诚实**：撤销 Toast 明确提示「撤销将新建一个模板，原 ID 已失效，请重新配置引用它的规则」

---

## 🟠 中等（18 项，节选核心）

| #    | 文件:行号                                                                                                       | 问题                                                                                                                                                                     | 角色/路径 | 修复建议                                                                            |
| ---- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | ------------------------------------------------------------------------------- |
| M-1  | `MetricsWorkspace.vue:963-966`                                                                              | **分页越界不纠正**：纠正逻辑在 `load()` 内（`:1819-1824`）只在数据重拉时跑；`pagedDefinitions` 纯切片无钳制。切 Tab（`activeTab` 无重置逻辑）后停在第 N 页 → 空白表格无提示                                                | HR 专员 | `pagedDefinitions`/`pagedTemplates` 内加 `Math.min` 钳制                            |
| M-2  | `MetricsWorkspace.vue:59-74`                                                                                | **绕过分页唯一真源**：`useTablePagination.ts:19` 明令「禁止手写」，页面手写 n-pagination；计数文案 `共 N 项` ≠ 规范 `共 N 条`                                                                           | 技术运维  | 改用 `remotePagination()`                                                         |
| M-3  | `MetricsWorkspace.vue:45-47`                                                                                | **三态混一**：首次使用 / 搜索无结果 / 筛选无结果共用一条「试试调整关键词」文案，违反 R-111                                                                                                                  | HR 专员 | 派生 `emptyKind` 四态 + 清空筛选 action                                                 |
| M-4  | `RuleAuthoring.vue:580-587`                                                                                 | 删除确认文案「确定删除「XX」吗？」违反 R-204（须说明后果，非询问是否确认）                                                                                                                              | HR 专员 | 改「删除规则「{name}」？该规则已用于 {N} 个触发点，删除后不再自动执行」                                       |
| M-5  | `RuleAuthoring.vue:528-537`                                                                                 | 规则删除/切换**无 loading/disabled** → 连点两次发两次 DELETE；`onToggle` 是取反语义，连点等于没改                                                                                                 | HR 专员 | 加 `busyRuleId` 统一 loading（对齐 MetricsWorkspace:803 模式）                           |
| M-6  | `MetricsWorkspace.vue:1108-1138`                                                                            | 导入 `update` 模式**无预览无确认** → `io_template.py:629-652`逐字段覆盖 + version+1，批量静默覆盖                                                                                            | HR 专员 | update 模式加确认闸门，或加「预检」先跑 `mode=error`                                            |
| M-7  | `MetricsWorkspace.vue:1548-1550`                                                                            | 受影响规则查询失败被**静默吞掉直接删除**——闸门失效应保守阻断而非激进放行                                                                                                                                | 系统管理员 | catch 内阻断 + 提示                                                                  |
| M-8  | `models.py:111` + `metric_engine.py:200`                                                                    | **`params` 指标级全局唯一** → 用户 A 改 `recent_n=3` 污染用户 B 的 5；且 `DerivedMetric` **无版本化**（`template_version.py:29`只含模板），改 params 无审计、回滚不回                                       | HR 专员 | `params` 拆「默认 + 模板级覆盖」（引擎 1 行改动），或至少加乐观锁                                        |
| M-9  | `io_template.py` / `metric_engine.py`                                                                       | **`param_config`/`value_domain`/`param_enums` 是死配置**：全 12 处出现均在 model/serializer/版本/导入，引擎零消费 → 运营配了以为生效                                                                | HR 专员 | 最低成本：`help_text` 标注「不参与服务端求值」；或补 `_expected()` 消费点                              |
| M-10 | `models.py:313` / `views.py:109-121`                                                                        | metrics **未接入双系统硬分区**：4 个 ViewSet 全裸 `queryset = X.objects.all()`；模型无 `recruit_type`（混 mixin 会no-op）→ **社招运营配的规则会作用到校招候选人**                                            | 招聘经理  | 需定性：若刻意全局须在 docstring 写明；若需隔离则加字段（框架已就绪约 20 行）                                  |
| M-11 | `metrics/models.py:26`                                                                                      | 为让 `clean()` 复用校验链，在 models 层制造 models↔services 环，导致 **8 处「自己 import 自己的 models」**                                                                                     | 技术运维  | 删 `models.py:26` 顶层 import，改 `clean()` 内局部导入，可消除 8 处延迟导入                        |
| M-12 | `rule_trigger.py:180`                                                                                       | 批量筛选 N+1：规则列表查询在**候选人循环内**，200 候选人 × 3 规则 × 2 条件 ≈ 2000+ 次 DB round-trip                                                                                               | 技术运维  | 规则列表提到循环外 + 模板级 LRU 缓存                                                          |
| M-13 | `talent_pool/views.py:84-86`                                                                                | 规则求值异常 `except Exception: pass` **连日志都不打** → 规则被跳过、入池成功、无记录                                                                                                            | 技术运维  | 至少补 `logger.exception`                                                          |
| M-14 | `models.py:310-368`                                                                                         | `MetricRule` **无版本化** → 3 月按「年龄>30」拒绝、6 月改成 25、9 月审计无法回答                                                                                                               | 合规/审计 | 加同构 `MetricRuleVersion`                                                         |
| M-15 | `RuleAuthoring.vue:394/:444`                                                                                | `logic: 'AND'` 硬编码 + **无 OR 选择 UI**，但后端 `metric_engine.py:69-72` 有 OR 分支且有测试 → "看起来能配实际不能"                                                                             | HR 专员 | 二选一：补 UI 或删 OR 分支                                                               |
| M-16 | `rule_trigger.py:175` / `views.py:306-357`                                                                  | **FILTER 场景是孤儿**：3 后端端点 + 3 前端 API，**零业务调用方**，但 `MetricRuleScene.FILTER` 是用户可选 → 用户配了永不执行                                                                              | HR 专员 | 接入真实筛选页，或移除枚举值 + 删死端点                                                           |
| M-17 | `rule_validators.py:26-30`                                                                                  | V13–V15 校验是已声明 TODO（`params` 值域无人校验）→ `avg_work_months:347-351` 对非法 `recent_n` 静默回落 0                                                                                  | 技术运维  | 补 V13 参数值域校验                                                                    |
| M-18 | `RuleAuthoring.vue:56`                                                                                      | `v-for` 用数组下标做 key → splice 后 Vue 复用错位实例，`n-select` 展开态串行                                                                                                              | HR 专员 | 改稳定 `_uid`                                                                      |
| M-19 | `apps/metrics/views.py:115` + `MetricsWorkspace.vue`                                                        | **「零代码」承诺 1/2 未闭环**：后端 `DerivedMetricViewSet` 有 create 能力，但前端**无新建派生指标入口** → 新增第 7 个具体指标仍需研发手工 POST（新增「范式」更是纯研发）                                                       | HR 专员 | 加「新建派生指标」表单（`derived-funcs` 已提供 `paramSchema`，`hasEditableParams`逻辑可复用，约 100 行） |
| M-20 | `operator_matrix.py:67`                                                                                     | `data_type or 'string'` 兜底 + `_MATRIX` 裸字符串键 → 静默回落 string 白名单                                                                                                         | 技术运维  | `_MATRIX` 键换 `MetricDataType` 常量                                                |
| M-21 | `serializers.py:186` vs `rule_validators.py:97`                                                             | `METRIC_VS_METRIC_OPS` 两处各定义一份                                                                                                                                         | 技术运维  | 单一真源                                                                            |
| M-22 | `apps/metrics/management/commands/migrate_raw_conditions_to_metric.py`                                      | 一次性迁移命令仍在 `management/commands`，若未加`--dry-run`/幂等标记有误执行风险                                                                                                              | 技术运维  | 加 dry-run 与幂等标记                                                                 |
| M-25 | `apps/metrics/services/rule_validators.py:163-173`                                                          | **VETO 互斥误拦**：只按 `scene + action_type='VETO'` 查已有规则，**不看 `enabled`/`status`** → 一条完全停用的旧规则永久阻止运营重建该 VETO 规则，只能改DB                                                      | HR 专员 | filter 加 `enabled=True, status='enabled', deleted_at__isnull=True`              |
| M-26 | `apps/metrics/serializers.py:39-40,71-72,83` + `views.py:110,116,122`                                       | **列表 N+1**：`template_count`/`version_count` 每行一条 `COUNT(*)`。实测 page_size=20 → 21 次查询（AtomicMetric/DerivedMetric 同）。`select_related` 只省 metric_name，省不掉 count           | 技术运维  | queryset加 `.annotate(_tpl_count=Count(...))`，serializer 读注解                     |
| M-27 | `apps/metrics/models.py:194-203`                                                                            | **`clean()` 二选一约束只在 DRF 路径**：`serializers.py:99`手写等价逻辑**不调 `full_clean()`** → `bulk_create` 可写入双FK 同时非空、空operators、非法运算符。实测 `__bulk_both: atomic=True derived=True` 入库 | 技术运维  | `save()` 加轻量断言（`raw is False` 时校验）；或加 `CheckConstraint` 兜底                      |
| M-28 | `apps/metrics/serializers.py:116-118`                                                                       | `param_config`/`value_domain` **只校验自身形状**，从不校验规则 `value`/`meta.min`/`meta.max` 是否落在域内。实测 `value_domain=[{18,60}]` 下 `GTE 5/999/-1` 全部 `valid=True`                     | HR 专员 | 数值型模板加越界检查，或明确声明「仅前端渲染」                                                         |
| M-29 | `apps/metrics/migrations/0018_seed_safe_set_templates.py:111`、`0020_seed_position_profile_metrics.py:84-87` | 种子**反向 `_unseed` 会误删人工数据**：`name__in=[10个安全集名]).delete()` 不校验 FK/引用/是否人工改过。实测手工建的同名「年龄」模板被一并删                                                                          | 技术运维  | 用已有 `auto_generated=True`（`models.py:75`）作反向删除依据                                |
| M-30 | `apps/metrics/serializers.py:54-57`                                                                         | `validate_calc_func` 只兜 DRF 路径；`bulk_create`/迁移/admin 直写可写入未注册值（实测 `calc_func='OLD_FUNC'` 成功）                                                                          | 技术运维  | 加巡检命令：CI 比对 DB 存量 `calc_func` ⊆ `REGISTRY.keys()`                               |


### 🟠 M-23【中等·前端】双视图双写漂移：列表是`MetricDefinitionViewSet` 拼装视图，编辑走单表 ViewSet

| 项         | 内容                                                                                                                                                                                                 |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **文件:行号** | `MetricsWorkspace.vue:47`(列表 `:columns="defColumns"` `:data="pagedDefinitions"`) vs `:46`(`@row-click="openDetail"`)；后端 `views.py:559`（`MetricDefinitionViewSet`）vs `:115`（`DerivedMetricViewSet`） |
| **角色/路径** | HR 专员 → 指标管理 → 派生指标 Tab → 点「查看」                                                                                                                                                                    |

**问题**：`MetricDefinitionViewSet` 是把atomic + derived 两张表**拼装**成统一 `MetricDefinition` 返回的只读视图（`views.py:559`），而编辑/参数保存走的是 `DerivedMetricViewSet`（`views.py:115`）。两套 shape 各自演进：`defRowProps.onClick` 传的是拼装行的字段，`saveDerivedParams` 用 `detailRow.id` 调 `updateDerivedMetric` —— 若两边 ID 语义或字段名漂移，会出现「详情显示 A、保存写到 B」的静默错位。

**影响场景**：派生指标详情弹窗改参数 → 保存 → 刷新后参数丢失或写错字段（当前 `:821-825openDetail` 每次重置 `detailParams`，掩盖了潜在的 shape 不一致）。

**修复建议**：在 `openDetail` 入口加运行时断言（`derivedMetric` 存在时 `id` 与 `kind==='derived'` 一致），或让列表直接返回两表各自的真实 id 字段（`atomicId`/`derivedId`）避免复用一个 `id`。

### 🟠 M-24【中等·前端】两系统切换不清：指标全局共享但候选人强分区，作用域是隐式的

| 项         | 内容                                                                               |
| --------- | -------------------------------------------------------------------------------- |
| **文件:行号** | 后端 `apps/metrics/models.py:109-121`（4 个 ViewSet 全裸 `queryset = X.objects.all()`） |
| **角色/路径** | 招聘经理 → 分别配置社招规则与校招规则                                                             |

**问题**：`metrics` 4 个 ViewSet **无任何 scope 过滤**（`grep scope_filter_q` 零命中）。根因是 `ScopeQuerysetMixin.recruit_type_field` 默认 `'recruit_type'`，而 `MetricTemplate`/`AtomicMetric`/`DerivedMetric`/`MetricRule` **确实没有 `recruit_type` 字段** → 混 mixin 会自动 no-op。所以「指标库全局共享」是自洽的。

**但未被记录的后果**：`MetricRule` 用于真实候选人筛选（`MetricRuleScene.FILTER`/`TALENT_POOL`），而候选人本身按 `recruit_type` 硬分区 → **社招运营配的规则会作用到校招候选人身上**。跨系统隔离在「指标定义」层是通的，在「规则实例」层断了。

**修复建议**（需主理人先定性，我不擅自认定这是 bug）：

- 若刻意全局 →在 `models.py` 模块 docstring 写明这个决定与理由，并说明 `MetricRule` 无 `recruit_type` 是设计选择
- 若需分区 → 给 `MetricRule` 加 `recruit_type` + 混 `ScopeQuerysetMixin`（框架已就绪，约 20 行）
- 无论哪种，确认 `rule_trigger.default_candidate_ids`/`count_candidates` 是否按 `request.recruit_type` 过滤候选人，**否则规则作用域是隐式的**（待确认）

---

## 🟡 轻微（13 项，节选）

| #    | 文件:行号                                           | 问题                                                                                                                                                    |
| ---- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| L-1  | `locales/metrics.ts:305`                        | `rollbackConfirm` 键存在但**零引用**；`confirmRollback`（`:1702`）函数名叫 confirm 却**无任何确认框**直接执行破坏性回滚 → 接上已备好的键                                                   |
| L-2  | 12 处 `error?.response?.data?.error`             | 与全局异常处理器返回体不符（`apps/common/exceptions.py:137-144` 返回 `message`/`errors`，**无 `error` 键**）→ 字段级校验原因丢失，只显示「保存失败」，违反 R-203                                |
| L-3  | `operator_matrix.py:25-59`                      | `_MATRIX` 用裸字符串 `'number'` 而非 `MetricDataType.NUMBER`；`operators_for` 的 else 兜底回落 `_MATRIX['string']` → 若枚举增删，number 指标会拿到 string 白名单（丢 GT/LT）        |
| L-4  | `serializers.py:185` vs `rule_validators.py:97` | `METRIC_VS_METRIC_OPS` 两处各定义一份字面量相同的集合 → 改一处忘另一处即漂移                                                                                                   |
| L-5  | `MetricsWorkspace.vue:1743-1745`                | `fmtParamConfig` 硬编码中文（`前缀「${c.prefix}」`等）不在 `t()` 内 → EN 语言下版本历史混中文                                                                                  |
| L-6  | `MetricsWorkspace.vue:887-894`                  | `sourceModuleKey` 未知前缀静默归「其他/全局」；建议后端直接返回 `sourceModule`，避免前后端两处规则漂移                                                                                  |
| L-7  | `MetricsWorkspace.vue:791-794`                  | `atomicList`/`derivedList`/`fieldPaths` 三个 ref **只赋值无读取**（`fieldPaths` 完全未使用）→ 每次 `load()` 白拉 3 个接口                                                   |
| L-8  | `OperatorBadge.vue:2`                           | `trigger="hover"` + `<span>` 无 `tabindex` → 触屏/键盘不可达，违反 R-109                                                                                         |
| L-9  | `KindIcon.vue:6`                                | 表格类型列（`:1194`，width 72）只有图标无文字，列内无文本 → 读屏用户只听到列头重复；建议补文字标签                                                                                            |
| L-10 | `locales/metrics.ts:96`                         | 文案仍写「指标库」，但页面已改名「指标管理」（`:9`）→ 用户找不到入口                                                                                                                 |
| L-11 | `MetricsWorkspace.vue:1295-1318`                | 操作列 `width:320` 塞 4 按钮 + `flex-wrap:nowrap` → EN 语言下「Version History」必然撑破                                                                             |
| L-12 | `candidate_snapshot.py:13-17`                   | `workExperience` 只能从 `candidate.extra` 来；空列表时 `max_gap`/`avg_work_months` 返回 **0**（非 None）→「空窗期≤6月」规则对**零经历候选人恒通过**（实习/应届生被当 0 个月，比无数据更宽松）→ **需产品决策** |
| L-13 | `MetricsWorkspace.vue:311-336`                  | 详情弹窗参数面板无脏检查，`mask-closable=true` → 改了不保存直接关闭，静默丢失（违反 R-105）                                                                                          |

---

## ✅ 审查确认的扎实设计（正面项）

| 位置                                          | 做法                                                                                                     |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `metric_engine.py:126-131`                  | 运算符白名单**后端强校验**（拒绝模板不支持的运算符，PRD AC-04）                                                                 |
| `metric_engine.py:143/:179`                 | FAIL-not-500 降级贯彻，注释明确声明该原则                                                                            |
| `metric_engine.py:227`                      | 方案B 右值解析**有**禁用态校验                                                                                     |
| `metric_engine.py:273`                      | 正则**预编译校验**（避免比较阶段才抛错）                                                                                 |
| `metric_engine.py:241-246`                  | 方案B 左右 `data_type` 类型守卫                                                                                |
| `io_template.py:505/543`                    | 导入 mode 白名单 + `mode=error` **整批拒绝**不写库                                                                 |
| `derived_registry.py:8-12`                  | 开闭原则：`calc_func` 刻意不设 choices，新增范式零迁移不改引擎                                                              |
| `models.py:249` / `template_version.py:3-4` | 版本快照 **INSERT ONLY**，规避 JSONField 原地更新的审计盲区                                                            |
| `rule_engine/services.py:12`                | 注释坦承「`RuleEngine.dispatch` 仅被单测驱动」——**注释与实际一致**，未夸大                                                    |
| `agent` 核实的负向结论                             | 迁移演进路径正确（9 个 seed 迁移全走 RunPython forward+reverse，**未发现历史迁移被就地修改**）；裸 `except:` 零处；metrics 出向依赖**无反向环** |

---

## 🔍 修正审查过程中我自身的三处判断错误

按项目纪律"不信任自述、独立查码"，记录我自己的纠错：

| # | 我先前的说法                                     | 实际（已运行时/读码核实）                                                               |
| - | ------------------------------------------ | --------------------------------------------------------------------------- |
| 1 | 「方案 B 已落地可用（commit fcfb7aaf + 250 passed）」 | **生产路径 100% 失效**。3 处透传丢弃 `rightTemplateId`，250 测试绕过转换层全绿                    |
| 2 | 「分页越界已修复（`:1819-1823`）」                    | **错**。该纠正逻辑在 `load()` 内，只在数据重拉时跑；纯客户端筛选/切 Tab 不触发，`pagedDefinitions` 纯切片无钳制 |
| 3 | 「`params` 挂指标级是设计权衡，可接受」                   | **低估**。叠加 `DerivedMetric` **无版本化**，改 params 无审计、模板回滚也回滚不了→ 配置污染 + 审计断链      |

---

## 📋 改进清单（按优先级排序）

### P0 — 立即修（低风险高收益，合计约 40 行）

| 序 | 项                  | 改动                                                                         |
| - | ------------------ | -------------------------------------------------------------------------- |
| 1 | **B-1** 方案B 类型守卫失效 | `serializers.py:262` 的 raise 移出 try（DB 查询留 try 内，比较移出）                     |
| 2 | **S-1** 方案B 透传修复   | 3 处各加 1 行 + 删死方法 + **补穿透测试**                                               |
| 3 | **S-3** 修护栏红灯      | `rule_item_evaluator.py:165/:170` 补意图说明 + `attribute_fields.py:118` 补 noqa |
| 4 | **S-5** 补 i18n 键   | ZH/EN 各 1 行                                                                |
| 5 | **L-1** 回滚接确认框     | `confirmRollback` 用已备好的 `rollbackConfirm` 键                                |

### P1 — 本迭代（正确性/阻断）

| 序  | 项                            | 理由                            |
| -- | ---------------------------- | ----------------------------- |
| 6  | **B-2** 模板删除引用保护             | 复用现成 `template_impact`，消除规则悬空 |
| 7  | **S-2** 禁用态判定统一              | 该关的没关，方向危险                    |
| 8  | **S-4** 列表错误态 + 重试           | R-104/R-111 强制                |
| 9  | **M-1** 分页钳制                 | 用户可见空白表格                      |
| 10 | **M-3** 空态四态分离               | R-111 强制                      |
| 11 | **M-4/M-5** 规则删除确认 + loading | 防误操作                          |
| 12 | **M-6** 导入 update 加闸门        | R-106 强制                      |
| 13 | **B-3** 版本快照并发锁              | 500 + 孤儿行                     |

### P2 — 下迭代（架构/协作）

| 序  | 项                              | 理由                |
| -- | ------------------------------ | ----------------- |
| 14 | **M-8** params 下沉到模板           | 多人协作阻塞项（引擎 1 行改动） |
| 15 | **M-9/M-28** 死配置标注或补消费点        | "看起来工作"比没有更危险     |
| 16 | **S-6** 撤销语义（后端 restore）       | 需立项，含审计           |
| 17 | **M-14** MetricRule 版本化        | 合规审计硬需求           |
| 18 | **M-10/M-24** 双系统隔离定性          | 社招规则作用到校招候选人      |
| 19 | **M-2** 分页 composable 收口       | 6 个页面同病，需统一批次     |
| 20 | **M-11** 消除 models↔services 环  | 消除 8 处延迟导入        |
| 21 | **M-25** VETO 互斥误拦             | 停用规则永久阻塞新建        |
| 22 | **M-26/M-27** N+1 + clean() 收口 | 性能 + 写入约束         |

### P3 — 清理 + 需产品决策

| 序  | 项                                                       | 需谁拍板                         |
| -- | ------------------------------------------------------- | ---------------------------- |
| 23 | **L-12** 零经历候选人派生指标返 0                                  | **产品**：无经历的候选人该被规则管还是不管      |
| 24 | **M-15** `logic` OR 分支                                  | **产品**：补 UI 还是删能力            |
| 25 | **M-16** FILTER 孤儿场景                                    | **产品**：接入筛选页还是删枚举            |
| 26 | **S-3** 盲 except 120→84 专项收敛                            | 技术负责人                        |
| 27 | **M-29** 种子反向 `_unseed` 误删人工数据                          | 技术运维（改用 `auto_generated` 标记） |
| 28 | L-2/L-3/L-4/L-5/L-7/L-8/L-9/L-10/L-13/L-20/L-22/L-23 清理 | 开发者                          |

### ❓ 需主理人/产品决策的 3 个问题

1. **M-10 双系统隔离**：指标库刻意全局共享，还是必须按 `recruit_type` 隔离？现状是社招运营配的规则会作用到校招候选人。
2. **L-12 零经历候选人**：派生指标对无经历返回 0，「空窗期 ≤ 6 月」恒通过 —— 应改为返回 None（可判空），还是维持 0？
3. **M-15 / M-16**：OR 分支与 FILTER 场景是「补入口」还是「删能力」？当前都是「占位即承诺」。

---

## 整体结论

**工程质量评价：良好，但存在一类系统性测试盲区。**

**做得好**：FAIL-not-500 降级贯穿执行层、运算符白名单后端强校验、正则预编译、导入 mode=error 整批拒绝、开闭原则（`calc_func` 不设 choices）、版本快照 INSERT ONLY、注释与实际一致（未夸大 legacy 引擎状态）、迁移演进规范（无就地修改）。

**核心问题**：**「配置 → 存储 → 执行」的转换层缺乏测试覆盖**。`to_engine_conditions` / `_normalize` 这类函数把持久化数据翻译成引擎契约，但所有测试都直接手搓 dict 调引擎，绕过了这一层。于是出现「250 测试全绿 + 生产 100% 失效」的反差。**这类缺陷只有契约测试（穿透真实链路）能防**。

**第二类问题**：**「看起来在工作」的字段比没有更危险**。`param_config`/`value_domain`/`param_enums` 三个 JSONField 从 model 到 serializer 到版本快照到导入导出全都齐全，只缺引擎消费；`rollbackConfirm` 确认文案备好了却零引用；删除模板的「撤销」Toast 显示「已恢复」实际新建了记录。它们消除了「功能没做」的可发现性。

**建议**：优先执行 P0 四项（约 30 行，含方案 B 的穿透测试），并在项目规范中补一条硬性要求——**任何改条件/参数透传链路的改动，必须补「落库→转换→执行」穿透测试**，函数级单测通过不等于功能可达。

---

*本报告由 4 研究员并行审查 + 主理人独立运行时核验生成。所有严重项均有 file:line 硬证据，A1/A2/S-3/S-5/S-6/M-1 已由主理人实跑核实。*
