# 查重逻辑收口影响分析（#23）

> 结论先行：**本轮仅出影响分析文档**。具体代码改造（把 `duplicate_rule` 接入线上，或反向删减）留待后续单独立项拍板。
> 当前**线上实时查重的事实源是 `add_candidate.duplicate_check`**；`duplicate_rule` 是配置/试算层，**未接入线上链路**（有源码注释为证）。

---

## 1. 问题背景

审计 CODE_REVIEW 指出「查重逻辑散落、事实源不清」：`duplicate_rule` 与 `duplicate_check` 都能判断「是否同一候选人」，但职责与接线状态不同，存在双份逻辑与潜在行为分歧。

---

## 2. 两套系统剖析

### 2.1 `add_candidate.duplicate_check`（线上事实源）

| 项 | 内容 |
|---|---|
| 位置 | `apps/add_candidate/services/duplicate_check.py` |
| 入口 | `DuplicateCheckService.find(phone, email, id_card, moka_id) -> DuplicateInfo` |
| 匹配算法 | 委托 `apps/candidate/services.py:235 CandidateService._find_duplicate`，**硬编码 4 字段精确匹配**：Moka ID / 证件号 / 手机号 / 邮箱 |
| 状态判定 | 命中后按 active 申请（`ApplicationState` ∈ PENDING/ACTIVE/PAUSED/OFFER_SENT/OFFER_ACCEPTED）区分 `OCCUPIED`（已占用·不可合并）/ `UNOCC`（未占用·可合并）/ `CLEAN`（无重复） |
| 接线状态 | **在用**：每次创建候选人触发 |
| 调用方 | `apps/add_candidate/views.py:161, 281`（2 个视图入口，候选人创建 / 简历上传）、`apps/add_candidate/tasks.py:41`（异步任务） |
| 测试 | `apps/add_candidate/tests/test_duplicate_check.py`（7 例）、`test_tasks.py` |

### 2.2 `duplicate_rule`（配置 / 试算层）

| 项 | 内容 |
|---|---|
| 位置 | `apps/duplicate_rule/`（models / services / views / urls / catalog / serializers / migrations） |
| 数据模型 | `DuplicateConfig`（单例 JSON：`merge` 合并规则 + `application` 重复申请窗口 `window_months`）、`DuplicateRule`（多套规则，系统内置 + 用户自定义，`condition_logic`=ALL/ANY，`items`=查重项+强度） |
| 判定算法 | `services.compare()` / `rule_matches()` / `field_matches()`：按强(证件/渠道ID/AI查疑) / 中(手机/邮箱) / 弱(姓名/性别/生日/经历) 三档字段做归一化比对，支持 ALL(全中) / ANY(任意 N 项中) |
| 接线状态 | **未接入线上**：`services.py:8-10` 原文「`compare()` 目前是配置侧参考实现，供单测与前端试算复用，**尚未接入** `DuplicateCheckService.find()` 的线上链路（接管实时查重属独立改造，需单独拍板）」 |
| API 面 | `apps/duplicate_rule/urls.py` → `/api/v1/duplicate-rules/`：`catalog/`（字段目录）、`config/`（读写合并+重复申请配置）、`rules/`（CRUD + `reset/` + `<pk>/toggle/`） |
| 消费方 | 前端「候选人查重规则」管理页 + 试算抽屉（走 `compare` 做离线试算，不落线上判定） |
| 测试 | `apps/duplicate_rule/tests/test_api.py`、`test_engine.py` |

---

## 3. 当前事实源结论

- **实时查重（创建候选人 / 简历上传 / 异步任务）的唯一事实源 = `add_candidate.duplicate_check`**（4 字段硬编码 + active 申请占用判定）。
- **`duplicate_rule` 不作用于线上判定**：它提供「可配置规则 + 合并配置 + 重复申请窗口」的管理与试算能力，但 `compare()` 从未进入 `find()` 调用链。
- 因此「双份逻辑」的**实际运行时风险当前为零**——两条路径在线上并不重叠；风险在于（a）未来误以为规则已生效、（b）维护两份语义相近代码导致演进分叉。

---

## 4. 收口方案对比（供后续立项拍板）

| 方案 | 描述 | 收益 | 风险 / 成本 |
|---|---|---|---|
| **A. 线上接入规则引擎** | `find()` 内部改用 `duplicate_rule.compare()`（规则真正生效，替掉硬编码 4 字段） | 查重策略可配、可灰度、贴合产品「查重规则」UI 心智 | **行为变更大**：每个候选人创建判定会变；需完整回归 + 灰度开关；占用判定(active 申请)需与规则引擎融合设计 |
| **B. `duplicate_check` 为唯一线上源** | 保留硬编码 4 字段，明确 `duplicate_rule` 仅配置/试算参考，非线上 | 零行为变更，事实源一句话说清 | 需「降级」或移除 `duplicate_rule` 中暗示「将接管线上」的暗示文案；前端若已按「规则生效」宣传需对齐 |
| **C. 并存但明确边界** | 两套保留：`duplicate_rule`=配置管理+试算 UI，`duplicate_check`=实时判定；仅做文档/接口对齐，不改运行时 | 不动行为，先止血「事实源不清」 | 双份代码长期维护成本仍在；需明确「规则改了不会变线上判定」的产品/前端共识 |
| **D. 先只出影响分析（本轮所选）** | 固化本结论 + 明确事实源，代码改造留待后续 | 低风险、可立刻交付、不阻塞主线 | 双份代码短期继续并存 |

---

## 5. 后续立项建议（代码改造拆分）

若最终选 A：建议拆为独立项，且**先加灰度开关**（`settings` 控制 `find()` 走 `compare` 还是旧 4 字段），配套：
- 改造 `DuplicateCheckService.find` 调用 `duplicate_rule.services.compare`，并保留 active 申请占用判定语义；
- 迁移/对齐 `duplicate_rule.tests` 与 `duplicate_check.tests` 为同一契约；
- 前端「查重规则」页确认规则确实生效的端到端验证。

若选 B/C：仅需文档与最小代码注释/接口对齐，**不涉及运行时行为改动**。

---

## 6. 附录：关键代码入口（供实施参考）

- 线上判定：`apps/add_candidate/services/duplicate_check.py:80-127`（`find`）
- 底层匹配：`apps/candidate/services.py:235`（`_find_duplicate`）
- 规则引擎：`apps/duplicate_rule/services.py:218`（`compare`）、`:187`（`rule_matches`）、`:169`（`field_matches`）
- 规则数据：`apps/duplicate_rule/models.py`、`apps/duplicate_rule/catalog.py`（`DEFAULT_RULES` 5 条）
- API：`apps/duplicate_rule/urls.py`、`apps/duplicate_rule/views.py`
- 调用方：`apps/add_candidate/views.py:161,281`、`apps/add_candidate/tasks.py:41`
- 测试：`apps/add_candidate/tests/test_duplicate_check.py`、`apps/duplicate_rule/tests/test_engine.py`、`test_api.py`
