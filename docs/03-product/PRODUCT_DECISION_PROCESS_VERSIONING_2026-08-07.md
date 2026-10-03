# 产品裁定：招聘流程版本管理（Q1~Q5）
> 最后更新：2026-09-07（依据 git 最后提交）

- **文档编号**：PROD-2026-08-07-01
- **作者**：许清楚（产品经理 / software-product-manager）
- **日期**：2026-08-07
- **上游**：`docs/ARCH_DECISION_VERSIONING_STAGE_2026-08-07.md` §5.2 Q1~Q5
- **前提**：接受架构师选定的数据模型方案 A+（`code` 去 unique + `version_seq` + `is_latest` + 3 条约束），本文档不推翻技术方案，只裁定业务语义
- **本文档未修改任何源码**

---

## 0. 结论速览

| # | 问题 | 结论 | 需用户确认 | 生效任务 |
|---|---|---|---|---|
| **Q1** | `bump-version` vs `clone-version` | **废弃 `bump-version` 端点**。它不是第二个业务动作，是一个接错线的端点 | 否 | T2 |
| **Q2** | BR-104 升版本三边界 | (a) **只能升到 `is_latest=True`**　(b) **禁止降版本**　(c) **禁止跨 code** | **(c) 是** | T3 |
| **Q3** | 克隆是否复制 `AutomationRule` | **复制**，但只复制新版本仍包含的阶段的规则 | 否 | T4 |
| **Q4** | 新版本生成后 Demand/Position 是否自动改指 | **不自动改指**。新版本只对之后新建的需求生效 | **配套入口优先级 是** | T2/T4 |
| **Q5** | 归档单版本还是整条线 | **归档整条流程线**（与架构师本轮单行语义不一致，需调整规格） | 否 | T5 |

---

## 0.1 两条前提勘误（请架构师先看这段）

裁定前必须先纠正两个事实，否则 Q2、Q4 会答偏。

### 勘误 1：BR-104 的主语是「候选人（Application）」，不是「需求（Demand）」

任务书把 BR-104 描述为「把一个已在跑的招聘需求（Demand）从旧版流程升到新版流程」。**这与代码中唯一存世的 BR-104 表述不符。**

| 出处 | 原文 |
|---|---|
| `versioning.py:7` | BR-104: 支持历史**候选人**"升版本"到最新版本 |
| `models.py:162` | BR-104: 支持历史**候选人**"升版本" |
| `apps/django/README.md:53` | 历史升级：支持历史**候选人**"升版本"到新流程（BR-104） |
| 死代码函数签名 | `upgrade_application_to_latest_version(application, target_process, actor)` |
| 活端点 | `POST /api/v1/applications/{id}/upgrade-version/`（`application/views.py:381`） |

**BR-104 = Application 层面的升版本。Demand/Position 层面的改指属于 Q4，PRD 完全空白。** 本文档 Q2 按 Application 裁定，Q4 按 Demand/Position 裁定。

### 勘误 2：A+ 会让活端点 `POST /applications/{id}/upgrade-version/` 永久失效（架构师未发现的回归）

活实现 `ApplicationService.upgrade_workflow_version`（`services/__init__.py:675`）：

```python
new_version = application.process.current_version
if new_version == application.workflow_version:
    raise StateTransitionError('Application is already on the latest version')
```

它只同步字符串，**不改 `application.process`**。今天之所以能工作，是因为 `bump_version` 会**就地改老行的 `current_version`**，让它跑到 `workflow_version` 前面去。

T2 规格明确要求「老行 `current_version` / `version_seq` 一个字都不许动」（BR-103），再叠加我在 Q1 裁定的废弃 `bump-version` —— **再没有任何代码会改动老行的 `current_version`**。于是 `application.process.current_version` 恒等于 `application.workflow_version`，该端点将**永久返回 409「已是最新版本」**。

风险等级：**这是一个活的 REST 端点，零测试覆盖（已 grep 确认），回归会静默发生。**

**处置要求**：T3 不能只修死代码 `upgrade_application_to_latest_version`，必须把**活实现一并改成改指语义**（把 `application.process` 重新指向同 code 下 `is_latest=True` 的行，并同步 `workflow_version`），即两份实现合并为一份。这正好也是 Q2 的落地载体。

---

## Q1｜废弃 `bump-version` 端点

### 结论

**废弃 `POST /api/v1/processes/{id}/bump-version/`。** 「产生新版本」在产品上有且只有一个动作 = `clone-version`。

### 理由

`bump-version` 不是"另一个业务动作"，而是一个**三重错配的端点**（`process/views.py:294-311`）：

| 面 | 实际内容 |
|---|---|
| 路由 | `bump-version` |
| `@extend_schema` description | **`'BR-104: 支持历史候选人升版本到最新版本'`** |
| 声明的请求参数 | `target_version`（目标版本号，如 V1.2） |
| 真实实现 | `bump_version(instance)` —— 改流程行自己的版本号，**与候选人无关**，且**完全忽略 `target_version` 参数** |

它挂着 BR-104 的招牌，干的却是"原地改版本号"的事；而真正的 BR-104 早已在 `POST /applications/{id}/upgrade-version/` 有独立实现。这不是两个业务动作，是**一次接错线**。

更关键的是：它与 BR-101/BR-103 直接冲突 —— 原地改版本号意味着老版本内容被就地覆盖、历史丢失，而 BR-103 要求「历史版本只读」。保留它等于在系统里留一个"合法破坏历史"的后门。

### 用户可见影响

**零。** 前端对 `bump-version` / `clone-version` / `versions` 三个端点**零调用**（架构师 §2.1 已实测）。没有任何用户界面会因此改变。

### 兼容过渡方案

因为前端零调用、无外部集成方，不需要长过渡期。建议**一步到位删除**，而不是留 410 墓碑：

1. 删除 `views.py:294-311` 的 `bump_version_action`
2. 服务层 `bump_version()` 函数**保留但降级为内部函数**（改名 `_bump_version_inplace` 或直接并入 `compute_next_version`）—— 它仍是 T2 拆分后 `compute_next_version` 的组成部分，不对外暴露
3. OpenAPI schema 自动同步，无需手工维护
4. CHANGELOG 记一条 "移除未被使用的 `bump-version` 端点（与 BR-101/BR-103 语义冲突）"

> 若架构师坚持保守，退化方案是保留路由但返回 `410 Gone` + 指向 `clone-version` 的提示。我**不推荐**——零调用的端点不值得为它维护一个墓碑。

### 生效任务

**T2**。原规格「本轮保持行为不变，只补 docstring」作废，改为删除端点。

---

## Q2｜BR-104 升版本的三条边界

裁定对象是 **Application（候选人）**，见勘误 1。三条边界共同的立法背景：BR-102「已在跑的候选人走创建时的版本」+ `workflow_version` help_text「创建时的版本（冻结）」—— **升版本是一个打破冻结的例外动作，例外就应当是窄口径的。**

### (a) 只能升到 `is_latest=True` 的那一版　✅ 只能升到最新

**结论：只能升到 `is_latest=True` 的行。**

**理由**：BR-104 的原文就是「升版本到**最新版本**」（`versioning.py:7`、`README.md:53`），文本本身已经限定了目标。允许升到任意中间版本会引入一个无人能回答的问题："为什么这个候选人跑在 V3 而不是 V5？" —— 招聘流程需要口径一致，中间版本没有业务理由。

**这与架构师 T3 边界表中「目标流程 `is_latest=False` → 允许」相反，请按本裁定收紧。**

**用户可见影响**：升版本按钮不再需要版本选择器，点击即升到当前最新版。目标流程若非最新版 → 抛 `StateTransitionError('只能升级到最新版本')`。

### (b) 允许降版本　❌ 禁止

**结论：禁止降版本。** `target_process.version_seq <= application.process.version_seq` → 抛 `StateTransitionError('不能降版本')`（与架构师 T3 规格一致）。

**理由**：降版本 = 把候选人退回一套已被废弃的评估标准。候选人可能已经跑完了新版本才有的阶段，降版本后这些阶段记录会变成孤儿数据（`ApplicationStageRecord.link` 指向新版本的 link，而 `application.process` 却指回旧行）—— 这是数据不一致，不是业务功能。

**用户可见影响**：无降版本入口。若确需回退，走"撤销申请后重新投递"的既有路径。

### (c) 允许跨 code 升级（换一条流程线）　❌ 禁止　⚠️ **需用户确认**

**结论（推荐）：禁止跨 code。** 保留架构师 T3 规格中的 `target_process.code != application.process.code → StateTransitionError('不能跨流程线升版本')` 校验。

**理由**：`code` 的语义已由架构师锁定为「一条流程线的编号」（§2.2）。跨 code 不是"升版本"，是"换流程"—— 两者的审计语义、候选人体验、阶段记录连续性完全不同，不应共用一个动作名和一个端点。BR-104 叫「升版本」，把换流程塞进来是语义污染。

**⚠️ 为什么标「需用户确认」**：「选错流程模板需要改正」是一个**真实存在的运营诉求**（比如需求方建单时把校招需求挂到了社招流程线上）。禁止跨 code 会堵死这个场景，而目前系统里没有任何替代路径。我无法从代码或现有文档判断该诉求的真实发生频率。

| 选项 | 取舍 |
|---|---|
| **推荐：禁止跨 code** | 语义干净、审计清晰、实现即 T3 现有规格（零额外成本）。代价：选错流程线只能撤销申请重投，候选人已跑的阶段记录丢失 |
| **备选：允许跨 code** | 能救回选错流程的场景。代价：① 需要独立端点 `POST /applications/{id}/change-process/` 与独立审计动作（不能复用 `UPGRADE_VERSION`）；② 必须定义"旧流程已跑阶段如何映射到新流程"的规则 —— 这是一个独立需求，不是一行校验能解决的；③ 工作量远超本轮技术债治理范围 |

**我的建议**：本轮**先禁止**（按推荐选项实现，零成本），把「换流程线」作为独立需求另立条目排期。这样既不阻塞 T3，也不会把一个半成品能力塞进升版本动作里。请业务方确认是否接受。

### 生效任务

**T3**。注意 T3 必须同时改活实现（见勘误 2），三条校验对活/死两份实现统一生效。

---

## Q3｜克隆新版本时复制 `AutomationRule`

### 结论

**复制。** 但只复制「新版本仍包含该阶段」的规则，并保持 `enabled` 原值。

### 理由

**1. 不复制 = 静默的能力归零。** `AutomationRule.process` 是 CASCADE FK 指向**具体行**（`automation/models.py:50-53`）。克隆出的新版本行天然没有任何规则 —— 用户改了一个阶段配置、系统生成新版本，结果这条流程线上所有自动推进、超时提醒、自动入池规则**全部停止工作，且没有任何提示**。这是产品事故，不是可选项。

**2. `AutomationRule` 语义上属于「流程配置」，不属于「运营侧独立配置」。** 判据：

| 证据 | 说明 |
|---|---|
| `process` FK 是 **CASCADE** | 流程删则规则删 —— 数据模型已经声明它是流程的从属物，而非独立实体 |
| `stage` FK 必填 | 每条规则必须绑定一个阶段，脱离流程的阶段图它没有意义 |
| `AutomationRule` 无软删（继承 `TimestampedModel`） | 不是需要长期留痕的独立业务对象 |
| `Meta.indexes` 首条即 `['process', 'stage']` | 主查询路径就是"某流程某阶段的规则" |

四条证据一致指向：它是流程配置的一部分，理应随流程版本一起走。

**3. 架构师顾虑的「规则可能引用已变更的阶段」不成立（重要）。** `AutomationRule.stage` 和 `next_stage` 都 FK 到 **`RecruitmentStage`（全局阶段字典）**，**不是** FK 到 `ProcessStageLink`。所以复制到新版本行之后，这两个 FK 依然指向有效的全局阶段，**不存在悬空引用**。

唯一的真实边界是：如果新版本**删掉了**某个阶段，那么复制过来的、绑定该阶段的规则会变成永不触发的哑规则（不报错，但也不工作）。

**处置**：复制时按新版本实际包含的阶段集合过滤 ——
- `rule.stage` 不在新版本的 `stage_links` 阶段集合内 → **跳过不复制**
- `rule.next_stage` 不在集合内 → 复制规则但把 `next_stage` 置空并 `enabled=False`，同时在返回体里给出提示（让用户知道有规则需要重配）

### 用户可见影响

- **正向**：克隆新版本后自动化规则继续生效，用户无感知——这才是符合直觉的行为
- **新增提示**：若因阶段删除导致规则被跳过或禁用，`clone-version` 响应中返回受影响规则列表，前端可提示「N 条自动化规则因阶段变更需要重新配置」
- 不复制的方案会让用户遭遇"改了个小配置，第二天发现自动提醒全停了"——这是必须避免的

### 生效任务

**T4**。原规格「本轮先不做，留 `# TODO(Q3)`」作废，改为本轮实现。建议与 `StageRule` 一样采用**字段自省拷贝**（排除 `id`/`process`/`created_at`/`updated_at`），避免未来加字段再漏。

---

## Q4｜新版本生成后，Demand / Position 不自动改指

### 结论

**不自动改指。** 已有 Demand/Position 的 `process` FK 保持指向旧版本行；新版本只对**此后新建**的 Demand/Position 生效。

### 理由

**1. 自动改指会让 BR-101 自我否定。** BR-101 的立法目的是「流程被需求引用后，配置修改**不能就地生效**，必须生成新版本」—— 它保护的正是**正在被引用的配置的稳定性**。如果生成新版本后立刻把所有引用方改指过去，那么"生成新版本"和"就地修改"的最终效果完全一样，BR-101 等于没写。

**2. 数据模型已经表态。** `Demand.process_version` 与 `Position.process_version`（两处均 `default='1.0'`）是**冻结快照字段**，与 `Application.workflow_version`（help_text 明写「创建时的版本（冻结）」）同构。三张表用同一套设计说同一件事：**引用方记录的是"我当初选的那一版"**。

**3. 架构师指出的「生成了新版本但没人用它」是真问题，但答案不是自动改指。** 在 A+ 模型下，`/processes/` 列表默认 `filter(is_latest=True)`，所以**之后新建**的 Demand/Position 选到的自然就是新版本。新版本不是"没人用"，是"从下一单开始用"。这正是版本化应有的行为。

### 「正在进行中的招聘（已有候选人在流程中）」如何处理

这里必须区分**两层引用**，它们是相互独立的 FK：

| 层 | 字段 | 生成新版本时 | 改指 Demand 时 |
|---|---|---|---|
| 需求层 | `Demand.process` / `Position.process` | 不变 | 改指新版本 |
| 候选人层 | `Application.process` + `workflow_version`（冻结） | 不变 | **仍然不变** |

**关键结论：即使用户显式把 Demand 升级到新版本，已在跑的候选人也完全不受影响** —— `Application.process` 是独立 FK，只有 BR-104 的升版本动作才会改它。BR-102「已在跑的候选人走创建时的版本」由此得到保证。

所以：
- **在跑的候选人**：继续跑旧版本流程直到走完，任何情况下都不被动迁移。这是硬红线
- **该需求之后新投递的候选人**：走 Demand 当前指向的版本
- 副作用：同一个 Demand 下会出现新老候选人跑不同版本流程的情况。这在业务上可接受（招聘流程本就是滚动调整的），但**必须在候选人详情页展示其 `workflow_version`**，让面试官知道对比口径。这一点建议记入前端待办

### ⚠️ 需用户确认：配套的显式升级入口做不做、什么时候做

「不自动改指」定了之后，逻辑上需要一个**显式**的「把这个需求升级到最新流程版本」入口，否则老需求永远停在旧版本、无法主动跟进流程改进。

| 选项 | 取舍 |
|---|---|
| **推荐：本轮不做，下轮立项（P1）** | 本轮是技术债治理，不夹带新功能；且 A+ 落地后才有 `is_latest` 可用，做这个入口才有正确的目标可指。代价：老需求在下轮之前无法升级流程版本（现状本来也不能，**不构成回退**） |
| 备选：本轮一并做 | 好处是 BR-101 闭环一次做完。代价：新增端点 + 前端改动 + 权限设计（谁有权升级他人需求的流程），会把 T2/T4 的范围撑开，且与"零用户可见影响"的本轮定位冲突 |

**我的建议**：本轮不做。因为现状同样没有这个能力，不做不构成功能回退；而本轮的价值主张是"改动对现有用户零可见影响"，夹带新入口会破坏这个定位。请业务方确认是否接受"老需求暂时无法主动升级流程版本"。

### 生效任务

**T2 / T4**。具体到实现：`clone_process_with_new_version` **不得**触碰 `demands` / `positions` / `applications` 三个反向关系，保持现状即为正确。建议在函数 docstring 中显式写明「按 Q4 裁定，克隆不改指任何引用方」，防止后人误以为是遗漏而"修复"。

---

## Q5｜归档 = 归档整条流程线

### 结论

**归档整条流程线的所有版本行，不是单个版本行。** 与架构师本轮「保持单行语义」不一致，**请调整 T5 规格**。

### 理由

**1. 用户心智里只有"一条流程"，没有"版本行"。** A+ 落地后 `/processes/` 列表 `filter(is_latest=True)`，用户在界面上看到的 W001 就是一条记录。他点「归档」，预期是"W001 这条流程以后不能用了"，绝不会理解成"我只归档了 W001 的第 3 版，前两版还是启用状态"。

**2. 单行归档会产生一个自相矛盾的状态。** 若只归档 `is_latest=True` 那行，则这条 code 下**当前版本已归档、历史版本仍 ENABLED**。此时：
- 列表页因为 `is_latest=True` 过滤，会显示一条"已归档"的流程
- 而 `list_process_versions` 返回的历史版本却是 ENABLED
- 新建 Demand 时该选哪一行？无法回答

这不是一个可以对用户解释的状态。

**3. BR-106「流程无停用态，只能归档」的立法目的是"让这条流程不再被新需求选用"**，作用对象天然是整条线。归档单版本在业务上不解决任何问题——历史版本本来就因为 `is_latest=False` 而不会被新需求选到，单独归档它是无意义操作。

### 归档的精确语义（供 T5 实现）

归档**不影响**在跑的业务，只关闭入口：

| 面 | 归档后行为 |
|---|---|
| 该 code 下所有版本行 | `status='ARCHIVED'`，`archived_at` 统一置为本次操作时间 |
| 新建 Demand/Position 选流程 | 该流程线不再出现在可选列表 |
| 已引用该流程的 Demand/Position | **不受影响**，继续正常运行（`on_delete=PROTECT` 也保证行不会消失） |
| 在跑的 Application | **不受影响**，继续跑完（BR-102 红线） |
| 流程配置编辑 | 只读（BR-106「归档后只读」） |
| `clone-version` | 归档流程不允许克隆新版本 → 抛 `StateTransitionError` |
| BR-104 升版本的目标流程 | 已归档 → 抛 `StateTransitionError`（架构师 T3 已有此规格，保持） |

### 用户可见影响

**当前为零**（前端未调用 archive 端点，架构师已实测）。但这是**未来正确性**的关键——一旦前端接入归档功能，单行语义会立刻暴露成用户可见的 bug。现在改成本最低。

### 实现提示（成本很小，不应成为拒绝理由）

`archive_process` 从「改一行」变成「改一批」：

```
RecruitmentProcess.objects.filter(
    code=process.code, deleted_at__isnull=True,
).exclude(status='ARCHIVED').update(status='ARCHIVED', archived_at=now)
```

配合 V7 的返回值统一（`archived` / `reference_count`:int / `archived_at`），建议返回体额外加一个 `archived_version_count`（本次归档了几个版本行），便于前端提示「已归档 W001 的全部 3 个版本」。

`views.py:251` 的早退判断 `if instance.status == 'ARCHIVED': raise` 需相应调整为「该 code 下已无 ENABLED 行」才算重复归档。

### 生效任务

**T5**。优先级可维持 P2，但**语义必须按整条线实现**，不要先做单行再改——那会多一次迁移和一次回归。

---

## 附：裁定对架构师规格的净变更清单

| 任务 | 原规格 | 本裁定后 |
|---|---|---|
| **T2** | 保留 `bump-version`，补 docstring | **删除该端点**；`bump_version` 降级为内部函数 |
| **T3** | 目标 `is_latest=False` 时允许 | **收紧为只允许 `is_latest=True`** |
| **T3** | 只修死代码 `upgrade_application_to_latest_version` | **必须同时改活实现 `ApplicationService.upgrade_workflow_version`**，否则活端点永久 409（见勘误 2） |
| **T3** | 跨 code 校验（待产品确认） | **保持禁止**（标记需用户确认，推荐禁止） |
| **T4** | `automation_rules` 本轮不做，留 TODO | **本轮实现复制**，按新版本阶段集合过滤 |
| **T2/T4** | Demand/Position 改指待确认 | **确认不改指**，docstring 写明是有意为之 |
| **T5** | 归档单行 | **归档整条 code 线**；返回体加 `archived_version_count` |

**新增回归测试建议**（供 QA 参考）：
1. clone 后调用 `POST /applications/{id}/upgrade-version/` 应成功改指新行，**不得**返回 409（锁定勘误 2）
2. clone 后新版本行的 `automation_rules` 数量与旧行相等（阶段未变更时）
3. clone 后 `Demand.process_id` / `Position.process_id` / `Application.process_id` 与 clone 前**逐一相同**（锁定 Q4）
4. 归档后同 code 下 `status='ENABLED'` 的行数为 0（锁定 Q5）
5. 升版本到 `is_latest=False` 的中间版本 → 抛 `StateTransitionError`（锁定 Q2-a）

---

## 待业务方确认清单（2 项）

| # | 事项 | 我的推荐 | 若业务方选备选的影响 |
|---|---|---|---|
| **C1** | Q2(c) 是否需要「跨流程线迁移」能力 | **本轮禁止**，另立独立需求 | 选允许 → T3 范围外扩，需新端点 + 阶段映射规则设计，本轮无法交付 |
| **C2** | Q4 配套的「需求升级到最新流程版本」入口是否本轮做 | **本轮不做，下轮 P1** | 选本轮做 → T2/T4 范围外扩，破坏"零用户可见影响"定位 |

两项**均不阻塞** T1~T6 开工：C1 按推荐选项实现即为架构师现有规格（零改动），C2 是"不做"（零改动）。业务方若改选备选项，再另立条目排期即可。
