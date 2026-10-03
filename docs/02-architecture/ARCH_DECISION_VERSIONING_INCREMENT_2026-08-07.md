# 架构增量规格：流程版本化 + 阶段映射回落 + 跨流程线迁移 + 需求升级入口
> 最后更新：2026-09-07（依据 git 最后提交）

- **文档编号**：ARCH-2026-08-07-02（增量，对 ARCH-2026-08-07-01 的修订与扩充）
- **作者**：高见远（架构师 / software-architect）
- **日期**：2026-08-07
- **上游**：
  - `docs/ARCH_DECISION_VERSIONING_STAGE_2026-08-07.md`（原规格，本文档部分推翻）
  - `docs/PRODUCT_DECISION_PROCESS_VERSIONING_2026-08-07.md`（产品裁定 Q1~Q5，全部生效）
  - team-lead 增量指令（含用户三条决策 + 假实现回归风险）
- **本文档未修改任何源码，未 commit**
- **范围变动提示**：原规格仅覆盖 versioning.py 缺陷修复 + 删除 stage_transitions.py。本增量因用户三条决策（阶段映射 / 跨流程线迁移 / 需求升级入口）显著扩大范围，并因 team-lead 核验坐实一条"活端点假实现"回归而新增处置方案与数据订正脚本。

---

## 0. 执行摘要（TL;DR）

| # | 结论 |
|---|------|
| 1 | **活端点 `upgrade_workflow_version`（`application/services/__init__.py:675`）是假实现**：它只改字符串字段 `workflow_version`，从不改指 `application.process`。今天能返 200 全靠 `bump_version` 原地改写老行 `current_version`（V2 bug）撑着。A+ 落地 + 废弃 bump-version 后该端点将**永久 409**。§1 给出合并活/死两份实现、真正改指的修复方案。 |
| 2 | **历史"假升级"审计数据不可信**。该端点零测试覆盖、且写 `UPGRADE_VERSION` 审计。需一个**只读诊断脚本**（§1.4 / T10）识别这些记录；**不自动改写**历史数据（无法反推正确目标）。 |
| 3 | **决策 1（阶段映射回落）**：同 code 升版本时，按 `ProcessStageLink.order` 找"新版最近的前序阶段"；阶段被删且无前序则回落到新版最早阶段（通常是 `is_start`）；新版零阶段则硬报错。算法 + 边界表见 §2。 |
| 4 | **决策 2（跨流程线迁移）**：本轮就做，形态为 `POST /applications/{id}/change-process/`，**必须显式传入 `target_stage_id`**。纯"按 order 自动找前序"在两条无关流程线间**技术上不可行**（无共享语义）——本文档明确标注为不可行子场景，改用"操作员指定落点阶段"规则。见 §3。 |
| 5 | **决策 3（需求升级入口）**：本轮就做，`POST /demands/{id}/upgrade-process-version/` 把 Demand 及其 Positions 改指到同 code 的 `is_latest=True` 版本；**不级联**在跑候选人（BR-102 硬红线）。见 §4。 |
| 6 | **更新任务清单 T1~T10**（原 T1~T6 修订 + 新增 T7~T10），每条精确到 `文件:行号 → 改成什么`。执行顺序见 §5。 |
| 7 | **本轮不可行部分**：跨流程线"按 order 自动映射阶段落点"不可行（§3.3）；"级联迁移在跑候选人"不可行且违规（BR-102，§4.3）。其余均可本轮交付。 |
| 8 | **路径勘误**：上轮回报我把 `stage_transitions.py` 写成 `apps/process/services/` 下，**实际全仓只有一个，在 `apps/application/services/stage_transitions.py`**（即将由工程师删除，本文档不再引用它）。 |
| 9 | **【2026-08-10 终裁修订】C3'（每 code 至多一行 `is_latest=True`）改用方案 (d) 表达式唯一索引，推翻中间稿的 (a) 冗余列 `latest_key`。** 决定性理由：(a) 的"不依赖调用方自律"不成立——`latest_key` 与 `is_latest` 的一致性靠每一处写路径手工维护，`.update()` / `bulk_update` / 原生 SQL 三种旁路均可**静默**造出同 code 两行 `is_latest=True`（team-lead dev MySQL A/B 实测坐实）；(d) 把唯一性收回 DB 现算，三种旁路**全部**被 `IntegrityError` 拦下，且**零冗余列**。附带收益：SQLite 测试库与 MySQL **行为完全一致**（双库实测），本轮一直在治理的"CI 绿证明不了生产"假绿闭环在此项上被彻底关闭。详见 §5-T1 的 C3' 段与「代价与边界」表。 |

---

## 1. 活端点假实现问题（upgrade_workflow_version）处置方案

### 1.1 问题定性（含 team-lead 核验结论）

活端点 `POST /applications/{id}/upgrade-version/` → `ApplicationService.upgrade_workflow_version`（`application/services/__init__.py:673-689`）：

```python
new_version = application.process.current_version      # 读的是 application.process 当前指向那一行
if new_version == application.workflow_version:
    raise StateTransitionError('Application is already on the latest version')
old_version = application.workflow_version
application.workflow_version = new_version             # 只改字符串字段
application.save()                                      # application.process 从头到尾没动过
```

**team-lead 核验结论（比产品经理更严重，以本条为准）**：这不是"A+ 方案会让它失效"，而是**它本来就是个假实现**。`application.process` 永远不变，候选人从未真正切换到新版流程；今天能返 200 唯一因为 `bump_version`（`versioning.py:71-72`）会原地改老行 `current_version`（V2 数据损坏缺陷），让两个字符串暂时对不上而已。**一个假实现，靠另一个 bug 撑着，看起来是好的。**

对照死代码 `upgrade_application_to_latest_version`（`versioning.py:166-196`）—— 它**正确**地写了 `application.process = target_process`（:185），但 V5 bug 把 `from_version` 读在了赋值之后（:194）。所以"正确改指"的逻辑其实存在于死代码里，活代码反而丢了。

**已查证事实**：
- 该端点零测试覆盖（grep 确认）。
- `Application.process` 是独立 FK（`application/models.py:49`，related_name='applications'），`current_link`/`current_stage` 是 FK→`ProcessStageLink`/`RecruitmentStage`（:56/:60，SET_NULL）。
- 它写 `ApplicationHistory.ActionType.UPGRADE_VERSION`（:219）。

### 1.2 影响面

| 面 | 影响 |
|---|---|
| 功能 | 候选人"升版本"从未真正生效，流程一步没挪 |
| 审计 | 生产库可能已有一批"升级成功"的 `UPGRADE_VERSION` 记录，而对应候选人 `process` 未变 → **审计数据不可信** |
| 回归（A+ 后） | T1 让 `code` 去 unique、T2 让 `bump_version` 不再改老行 `current_version`、且废弃 bump-version 端点 → 再无任何代码改动老行 `current_version` → 活端点将**永久返回 409「已是最新版本」**，且这次是真的失效（不是假的好） |

### 1.3 修复方案（合并活/死两份实现，真正改指）

**核心**：删除死代码 `upgrade_application_to_latest_version`（`versioning.py:166-196`），把其"改指 process"的正确逻辑并入活实现 `upgrade_workflow_version`，并接入阶段映射（§2 / T7）。单一职责落在一个函数上。

规格（伪代码，供工程师实现，**不在此轮手改 application/ 文件**）：

```python
# ApplicationService.upgrade_workflow_version(application, actor=None, target_process=None)
# BR-104：把候选人改指到同 code 下 is_latest=True 的版本，并映射阶段
with transaction.atomic():
    if target_process is None:
        target_process = (RecruitmentProcess.objects
            .filter(code=application.process.code, status='ENABLED',
                    is_latest=True, deleted_at__isnull=True).first())
    if target_process is None:
        raise StateTransitionError('该流程线没有可用的目标版本')
    if target_process.id == application.process_id:
        raise StateTransitionError('Application is already on the latest version')
    if target_process.version_seq <= application.process.version_seq:
        raise StateTransitionError('不能降版本')              # Q2(b)
    if target_process.status == 'ARCHIVED':
        raise StateTransitionError('目标流程已归档')           # Q5 / BR-106
    old_version = application.workflow_version
    old_stage = application.current_stage
    target_link, remapped = resolve_target_link(application, target_process)  # §2 / T7
    application.process = target_process
    application.workflow_version = target_process.current_version
    application.current_link = target_link
    if target_link is not None:
        application.current_stage = target_link.stage
    application.save(update_fields=['process','workflow_version','current_link','current_stage','updated_at'])
    ApplicationHistory.objects.create(
        application=application,
        action=ApplicationHistory.ActionType.UPGRADE_VERSION,
        detail={
            'from_version': old_version,
            'to_version': target_process.current_version,
            'from_stage': old_stage.code if old_stage else None,
            'to_stage': target_link.stage.code if target_link else None,
            'stage_remapped': remapped,           # 阶段被回落时标记，供前端提示
        },
        operator=actor,
    )
```

- 跨 code 升版本**在 upgrade-version 端点禁止**（保留 `target_process.code != application.process.code` 校验；跨 code 走独立的 change-process，见 §3）。
- 历史 `ApplicationStageRecord` 保持指向旧流程 link（冻结审计，BR-102）；仅 `current_link`/`current_stage` 切到新版。

### 1.3.1 死代码 `from_version` 读后写 bug（合并时严禁照搬）

死代码 `upgrade_application_to_latest_version`（`versioning.py:184-196`）除"零调用"外，还有**第三个 bug（V5）**：它在 `application.workflow_version = target_process.current_version`（:184）**赋值之后**才读取 `from_version = application.workflow_version`（:194），导致返回值里 `from_version` **恒等于 `to_version`**，审计一直在撒谎。未被发现同样因为零调用。

**合并铁律**：把死代码逻辑并入活实现（T3）时，**严禁照搬这段读后写**。`from_version` / `old_version` / `old_stage` / `old_process` 等"变更前快照"必须在**任何赋值语句之前**存入局部变量，再用于返回值与 `ApplicationHistory.detail`。上面 §1.3 的伪代码已遵守（`old_version = application.workflow_version` 在 :84、`old_stage` 在 :85，均早于 :87-91 的赋值）。

### 1.3.2 审计快照采集约定（贯穿 T3 / T8 / T9）

**约定（强制）**：任何写 `ApplicationHistory` 或需求审计的操作，其"变更前快照"必须在**状态变更（save）之前**采集。违反此约定的代码即便功能正确，也会产出"从 X 升到 X"式的假审计——正是本轮要终结的病灶（见 §1 假实现回归风险）。

逐任务核对（均已遵守，列此备查）：

| 任务 | 快照变量 | 采集位置（变更前） | 状态变更位置 |
|---|---|---|---|
| T3 `upgrade_workflow_version` | `old_version`, `old_stage` | §1.3 :84-85 | §1.3 :87-92 |
| T8 `change_process` | `old_process`, `old_stage` | §3.2 :228 | §3.2 :229-233 |
| T9 `upgrade_demand_process` | `old_pid`（Demand） | §4.2 :283 | §4.2 :284-286 |

补充：
- T9 若后续补充**逐 Position**审计，每个 position 的 `old_position_pid` 也必须在对应 `pos.process = ...`（§4.2 :290）之前采集，不得读后写。
- 约定同时覆盖"返回给调用方的响应体"——若响应回显 from/to，同样用变更前快照，禁止回显已 save 后的实例字段。

### 1.4 是否需要数据订正脚本

**需要，但仅做只读诊断，不自动改写。** 理由：

1. 由于活实现**从不**改 `application.process`，历史上每一条 `UPGRADE_VERSION` 记录都对应一个 `process` 未变的候选人 → 全部"假升级"，审计不可信。
2. 但**无法反推正确目标**：我们不知道当时"应该"升到哪个版本行（老行 `current_version` 已被 V2 bug 污染，且 `is_latest` 概念当时不存在）。自动改写历史数据是危险且不可验证的。
3. 因此脚本定位为**数据质量诊断**，输出受影响记录清单供人工审计，而非修复工具。

**脚本规格（T10，Django management command，如 `manage.py audit_fake_upgrades`）**：

```
输入：无（或 --since 日期）
逻辑（只读）：
  SELECT h FROM ApplicationHistory h
    WHERE h.action = 'UPGRADE_VERSION'
    JOIN Application a ON h.application_id = a.id
    -- 关键判据：该 action 发生时 process 是否真的变了。
    -- 由于活实现从不改 process，等价于：所有 UPGRADE_VERSION 记录均"未真正改指"。
    -- 为稳妥，额外比对 a.process_id 与 h.detail->>'from_version' 对应的历史 process（无可考，故只列记录）
输出：
  - 受影响 ApplicationHistory 条数
  - CSV：application_id, history_id, from_version, to_version, operator, created_at
  - 提示：这些记录的 process 字段在写入时未被改动，审计口径存疑
副作用：无（只读，不 UPDATE 任何行）
```

**⚠️ 必须在有真实数据的 fresh DB 上验证**：该项目踩过 `:memory:` 空库让 RunPython 的 bug 完全不显形、生产一跑就 `AttributeError` 的坑（team-lead 明示）。此脚本虽不改写，但其查询涉及的 `ApplicationHistory.detail` JSON 字段在生产数据上的形态需在真实数据上核验（如 `detail` 为 None / 旧格式）。

### 1.5 跨模块约定：process 模块凡区分 live / 软删一律显式 filter（发现 5）

**约定（强制，发现 5 实证）**：`RecruitmentProcess.objects` 与 `ProcessStageLink.objects` 均为原生 `django.db.models.manager.Manager`，**默认查询不过滤软删**。本项目**没有自定义 `SoftDeleteManager`**。

因此，process 模块内**任何**需要"只看 live 行"的查询，必须显式 `filter(deleted_at__isnull=True)**，不得假设 Manager 会替你处理软删。本轮已踩中该陷阱的三处（须全部点名）：

| 位置 | 原写法 | 后果 | 修正 |
|---|---|---|---|
| `versioning.py:114` clone 遍历 | `process.stage_links.all()` | 复活软删阶段成新流程正常阶段（实证：Yw9GBzXA4rJT8348AthR2 8 条含 4 软删） | `.filter(deleted_at__isnull=True)`（T4） |
| `versioning.py:148-163` `list_process_versions` | `process.stage_links`（不过滤） | 版本视图混入软删阶段，误导升级落点 | `.filter(deleted_at__isnull=True)`（T5） |
| T7 `stage_mapping.py` | `new_process.stage_links`（见 §2.2） | 映射算法在含软删的错误数据上运算 | `.filter(deleted_at__isnull=True)`（已写死，§2.2 :178） |

**增补要求**：
- 代码评审（review）与 QA 测试须检查 process 模块所有"取阶段/流程"路径是否显式过滤软删；新增的 soft-delete 相关查询不得裸用 `.all()` / 裸关系遍历。
- **自定义 `SoftDeleteManager` 不塞进本轮 T3/T4**：引入全局 Manager 改写属独立重构，会改变全仓默认查询语义、波及大量存量测试，风险超出本轮范围。须**单开任务**评估（不在 T1~T11 内），本轮仅以"显式 filter"约定兜底。

---

## 2. 阶段映射回落算法（决策 1）

### 2.1 字段依据（已核实）

- `ProcessStageLink.order`：`PositiveIntegerField(default=0, db_index=True)`，`Meta.ordering = ['process','order']`，`unique_together=[('process','stage')`（`process/models.py:236-250`）。**"前序"判定依据就是 `order` 数值，不是"sequence"字段（模型里没有该字段）。**
- **`order` 绝对值无业务语义**（事实 2，dev 实测）：断号是软删常态（非脏数据）、起始值任意（实测见过 0/1/2/4）、跨软删可重复（同 process 内 `order=4` 出现 live+软删各一次）。**只有同一 process 内 live 行之间的相对顺序（按 `order` 排序后的位置）有意义。** 本算法只在 live 集内按相对位置运算，不依赖 order 连续、不从固定值起算、不要求 order 唯一。
- 同 code 克隆出的新版本**保留同一批 `RecruitmentStage`** 且**沿用旧版 `order` 数值**（阶段是全局字典，`ProcessStageLink.stage` FK→`RecruitmentStage`），所以升级时候选人的当前阶段通常在新版里仍存在（精确匹配即可，无需回落）；仅当某阶段在新版被删时才触发回落。也正因为同 code 克隆沿用 order 数值，跨版本按 `order` 比较对**同 code 升版本**有效。**跨流程线（change-process）走操作员显式指定 `target_stage_id`，不调用本算法。**
- `Application.current_link`（FK→`ProcessStageLink`，SET_NULL）、`Application.current_stage`（FK→`RecruitmentStage`，SET_NULL）。软删字段为 `deleted_at`（`ProcessStageLink` 继承 `FullAuditModel`）；"live 行" = `deleted_at__isnull=True`。

### 2.2 算法（伪代码，落点为 T7 共享函数 `resolve_target_link`）

```python
def resolve_target_link(application, new_process) -> (ProcessStageLink | None, bool):
    """返回 (目标 link, 是否发生了回落)。仅用于同 code 升版本（upgrade-version）。
    跨流程线（change-process）走操作员显式指定 target_stage，不调用本函数。"""
    # 只在新版【live 行】内运算（软删 link 不参与前序比较；dev 实测同 order 可 live+软删并存）
    live_links = new_process.stage_links.filter(deleted_at__isnull=True)
    cur_link = application.current_link
    # 情况 0：候选人尚无当前阶段（刚创建未推进）→ 落新版最早 live 阶段
    if cur_link is None:
        first = live_links.order_by('order').first()
        return first, (first is not None)

    cur_stage = cur_link.stage
    cur_order = cur_link.order

    # 情况 1：当前阶段在新版 live 集里仍存在 → 精确匹配，无回落
    same = live_links.filter(stage=cur_stage).first()
    if same is not None:
        return same, False

    # 情况 2：当前阶段在新版被删 → 取 live 集里 order 严格小于当前、最大者（最近前序，按相对位置）
    predecessor = (live_links
                   .filter(order__lt=cur_order)
                   .order_by('-order').first())
    if predecessor is not None:
        return predecessor, True

    # 情况 3：无前序（候选人在旧版最前 / 新版所有 live 阶段 order 都更大）
    #         → 落新版最早 live 阶段（is_start 优先）
    first = live_links.order_by('order').first()
    if first is not None:
        return first, True

    # 情况 4：新版零 live 阶段 → 无法落点，硬报错（数据完整性问题，正常克隆不应出现）
    raise StateTransitionError('目标流程版本没有可用阶段，无法升级')
```

### 2.3 边界表（均限定在目标流程 live 集内）

| 候选当前状态 | 新版 live 阶段集 | 落点 | 回落? | 说明 |
|---|---|---|---|---|
| 在阶段 S（order=5） | 含 S 的 live link | 新版 S 的 link | 否 | 精确匹配 |
| 在阶段 S（order=5），S 被删 | live 中有 order<5 的 stages | 其中 order 最大的 | 是 | 最近前序（相对位置） |
| 在阶段 S（order=5），S 被删 | 所有 live stage order≥5 | 新版最早 live stage | 是 | 无前序，回落到起点 |
| 候选当前 order < 目标所有 live order | 任意非空 live 集 | 新版最早 live stage | 是 | 无前序可回落，落到相对起点（事实 2 边界） |
| 目标流程 live 阶段仅 1 个 | 1 个 live link | 该唯一 live stage | 视是否精确匹配 | 无论精确/前序/回落，最终均落该唯一阶段（事实 2 边界，dev 真有 min=1） |
| 无 current_link（刚创建） | 任意非空 | 新版最早 live stage | 否（视为初始落点） | 非"回落"，是正常初始化 |
| 任意 | 空（0 个 live link） | 报错 | — | 数据完整性异常，`StateTransitionError` |
| 落在 `is_start` 阶段 | 新版含该 start stage | 该 start stage | 否 | 保持起点 |

### 2.4 审计与通知

- **审计**：升级的 `UPGRADE_VERSION` 记录 `detail` 含 `from_stage`/`to_stage`/`stage_remapped`（§1.3）。`stage_remapped=True` 时前端应提示"候选人阶段已从 X 回落到 Y（前序阶段）"。
- **通知面试官**：**本轮不做自动通知**（IM/邮件属前端/异步范畴，超出本轮后端规格）。回落事实已写入审计并可经 API 暴露，前端可选择性展示 banner。列为前端待办，不阻塞本轮。

---

## 3. 跨流程线迁移（决策 2）

### 3.1 端点设计

- **路由**：`POST /api/v1/applications/{id}/change-process/`（新增于 `application/views.py` 的 ApplicationViewSet）
- **入参（required）**：
  - `target_process_id`：目标流程（RecruitmentProcess）id
  - `target_stage_id`：目标流程内的 `ProcessStageLink` id（候选人落点阶段）
  - `reason`：变更理由（必填，审计完整性，防滥用）
- **权限**：HR 角色或该需求负责 HR（复用现有权限类；无则新增 `IsHRorProcessAdmin`）。跨流程线是 correction 操作，必须鉴权。
- **返回**：更新后的 `Application` 详情 + 本次 `CHANGE_PROCESS` 审计 id。

### 3.2 阶段落点规则（与决策 1 的关系：两套算法）

**同 code 升版本（upgrade-version）用 §2 的"最近前序"算法；跨流程线（change-process）用"操作员指定落点"规则。两者不共用自动 order 映射。**

`change-process` 落点由 `target_stage_id` 显式决定，服务端只做校验：

```python
def change_process(application, target_process, target_stage_link, actor, reason):
    if target_process.id == application.process_id:
        raise StateTransitionError('目标流程与当前流程相同')
    if target_process.status != 'ENABLED':
        raise StateTransitionError('目标流程不可用（已归档或非启用）')
    if target_stage_link.process_id != target_process.id:
        raise StateTransitionError('目标阶段不属于目标流程')
    old_process, old_stage = application.process, application.current_stage
    application.process = target_process
    application.workflow_version = target_process.current_version
    application.current_link = target_stage_link
    application.current_stage = target_stage_link.stage
    application.save(update_fields=['process','workflow_version','current_link','current_stage','updated_at'])
    ApplicationHistory.objects.create(
        application=application,
        action=ApplicationHistory.ActionType.CHANGE_PROCESS,   # 新增枚举，见 §6.2
        detail={'from_process_id': old_process.id, 'to_process_id': target_process.id,
                'from_stage': old_stage.code if old_stage else None,
                'to_stage': target_stage_link.stage.code, 'reason': reason},
        operator=actor)
```

- 历史 `ApplicationStageRecord` 保留指向旧流程 link（冻结审计）。跨线后候选人的阶段记录混合两条线的 link，属 correction 审计的正常结果，可接受。
- 为降低操作员负担，可选提供 `GET /applications/{id}/change-process-preview/?target_process_id=X`（T11，P2）：对两条线做 `RecruitmentStage` 精确匹配，返回"建议落点阶段"与"无对应阶段的旧阶段清单"，但**最终落点仍以 POST 的 `target_stage_id` 为准**。

### 3.3 可行性判断（明确不可行子场景）

| 子场景 | 结论 | 理由 |
|---|---|---|
| 跨线"按 order 自动找最近前序阶段" | **不可行（本轮不做）** | 两条流程线的 `order` 编号体系彼此独立（如社招线 SCREEN=1,INTERVIEW=3；校招线 SCREEN=1,INTERVIEW=2,ASSESS=4），数值无可比性；且阶段集合完全不同，无共享 `RecruitmentStage` 可对齐。硬套 order 会得到"看起来有、实则错"的落点，比人工指定更危险。 |
| 跨线"按 stage_type 自动对齐" | 不采用（脆弱） | `StageType` 只有 4 类（SCREEN/INVITATION/INTERVIEW/OFFER），多条线同类型阶段多个，对齐歧义大，且无法表达"面试官/轮次"差异。 |
| 跨线"操作员指定落点阶段" | **可行，本轮采用** | 由最了解两条线的 HR 显式选落点，系统只校验合法性。语义清晰、零歧义、审计完整。 |
| 跨线后自动复制 AutomationRule | 不做 | 规则归属原流程（`AutomationRule.process` CASCADE FK），换流程线后原规则留在原流程，新流程用自己的规则集。这是正确行为，不跨线搬规则。 |

**综上**：跨流程线迁移**本轮可交付**，但前提是落点由操作员显式指定（`target_stage_id` required），**不提供跨线自动阶段映射**。若产品坚持"零输入自动落点"，则该子场景本轮不可行，需另立需求做阶段语义对齐（如引入跨流程线阶段映射表）。

### 3.4 审计动作

新增 `ApplicationHistory.ActionType.CHANGE_PROCESS = 'CHANGE_PROCESS', '更换流程线'`（§6.2）。**不得复用 `UPGRADE_VERSION`**（产品裁定：跨 code 是独立动作、独立审计语义）。

---

## 4. 需求升级到最新流程版本入口（决策 3）

### 4.1 端点设计

- **路由**：`POST /api/v1/demands/{id}/upgrade-process-version/`（新增于 `demand/views.py` 的 DemandViewSet）
- **入参**：可选 `target_process_id`（不传则自动取同 code 的 `is_latest=True` 且 `status=ENABLED` 版本）
- **返回**：更新后的 Demand + 受影响 Positions 列表（前后 `process_id` 对比）

### 4.2 可升级范围

"可升级"判据：Demand 当前 `process.code` 存在 `is_latest=True` 且 `status=ENABLED` 的版本，且该版本 `id != demand.process_id`。

**G1 修正（Demand 与 Position 无外键关联）**：运行时内省确认 `Demand` 反向关系仅 `approvals`、`Position` 无 `demand` 字段；`positions` 是 `process.positions`（`Position.process` 的反向名），**不是** `demand.positions`。原伪代码 `demand.positions.all()` 执行即 `AttributeError`。
**裁定：采用路径 (c) 新增 `Position.demand` 外键**（见 §5 T9 标注升级为需 migration）。理由：Decision 3（§0 行 5，PM 已裁定）明确要求"升级 Demand **及其 Positions**"——(a) 只升 Demand 会违背已裁定范围；(b) 按 `process_id` 反查会把**其他需求**的职位一并改指（跨需求污染、且违背 BR-102 精神）；唯 (c) 让"该需求的职位"有确定定义且不波及其他需求。
- `Position.demand`：`ForeignKey(Demand, null=True, on_delete=SET_NULL, related_name='positions')`（可空：职位可脱离需求独立存在；存量职位 `demand_id` 一律置 NULL，归属无法反推）。
- 升级只遍历 `demand.positions.filter(deleted_at__isnull=True)`（即 `Position.demand == demand` 的 live 职位），不动其他需求的职位。
- 存量归属订正超出本轮范围，登记为独立数据治理项（业务若提供"需求↔职位"映射再回填）。

**G2 修正（process_version 格式双轨）**：`RecruitmentProcess.current_version` 默认 `'V1.0'`，`Demand/Position.process_version` 默认 `'1.0'`（无 V），但 `demand/services.py`/`position/services.py` 实际写入 `'V1.0'`——默认与写入自相矛盾；且 `time_limit/services.py:57` 用**精确字符串匹配** `workflow_version=process_version`，格式不一致即静默匹配空集、时限规则全失效（不抛异常）。
**裁定：统一到 V 前缀格式 `'V{n}.0'`**（与 `RecruitmentProcess.current_version` 单一事实源及 service 层写入一致；T9 写 `demand.process_version = target_process.current_version` 即 `'V2.0'`）。
- `Demand/Position.process_version` 的 `default` 由 `'1.0'` 改 `'V1.0'`（仅影响新行，无需 migration；但库内若存在 `'1.0'` 残行须一次性 `UPDATE` 为 `'V1.0'`——G3 实测两表均 0 行，暂无需订正，规则须固化）。
- `time_limit` 匹配逻辑**改为按 `process_id`（FK）匹配，不再按版本字符串精确比**——版本字符串格式漂移本就脆弱（即本次 fail-silent 根因）。该改动属 `time_limit` 应用，不归 T9，列为**配套必做项**（否则升级对时限规则无意义），由工程师单独派活，不得静默留旧。
- 测试 fixture `add_candidate/tests/conftest.py:24` 硬编码 `'1.0'`，default 翻转后须同步改为 `'V1.0'`（测试改动，工程师任务）。

```python
def upgrade_demand_process(demand, actor, target_process=None):
    if target_process is None:
        target_process = (RecruitmentProcess.objects
            .filter(code=demand.process.code, status='ENABLED',
                    is_latest=True, deleted_at__isnull=True).first())
    if target_process is None or target_process.id == demand.process_id:
        return demand, []   # 无更新
    old_pid = demand.process_id
    demand.process = target_process
    demand.process_version = target_process.current_version   # 写入 'V{n}.0'
    demand.save(update_fields=['process','process_version','updated_at'])
    moved = []
    for pos in demand.positions.filter(deleted_at__isnull=True):   # (c) Position.demand 反向名
        if pos.process_id != target_process.id:
            pos.process = target_process
            pos.process_version = target_process.current_version   # 同写入 'V{n}.0'
            pos.save(update_fields=['process','process_version','updated_at'])
            moved.append(pos.id)
    return demand, moved
```

- 批量形态（可选 P2）：`POST /demands/bulk-upgrade-process-version/` 接收 `[demand_ids]`，内部循环调用上述逻辑。本轮以单 Demand 入口为准，批量作为可选扩展。
- **不改指 Application**（见 4.3）。

**G3 验收（必须自带非零 seed 数据，dev 两表均 0 行，空跑必绿无意义）**：
1. Demand 指向非最新版（`process_version='V1.0'`）且其下 ≥2 个 live Position（`Position.demand==demand`）→ 升级后 Demand 与这些 Position 的 `process_id` 均为目标 `is_latest=True` 版本、`process_version=='V2.0'`（V 前缀）；返回 `moved` 含这些 Position id。
2. 目标版本已归档（`is_latest=False` 或 `status≠ENABLED`）→ 升级被拒（400/409），Demand/Position 不变。
3. 升级后 `process_version` 为 V 前缀，且 `time_limit` 按 `process_id` 匹配能命中规则（若 time_limit 已改 (G2)，断言规则解析非空；未改前至少断言格式为 `'V{n}.0'`）。
4. Demand 无任何关联 Position（`demand.positions` 为空）→ 仅升级 Demand，返回 `moved=[]`，不报错。
5. Demand 已在最新版 → 幂等返回（空或 409），不重复改指。

### 4.3 在跑候选人处理（不级联，BR-102 硬红线）

**明确不级联触发候选人的阶段映射。** 依据：
- `Demand.process` / `Position.process` 与 `Application.process` 是**相互独立的 FK**（`add_candidate` 创建 Application 时读取当时的 Demand/Position.process 并冻结到 `Application.process` + `workflow_version`）。
- BR-102「已在跑的候选人走创建时的版本」是硬红线。升级 Demand 后，**已在跑的候选人继续跑旧版本直到走完**，绝不被动迁移。
- 该 Demand 之后新投递的候选人，因创建时读取的是 Demand 当前指向的新版本，自然走新版本。
- **结论**：Decision 3 只改指 Demand + Positions；候选人的显式升级仍走 BR-104（upgrade-version）或跨线走 change-process，均为独立、显式动作。此"不级联"**不是不可行，而是违规故不做**。

### 4.4 与 Q4 的关系（不矛盾）

产品裁定 Q4「不自动改指」与 Decision 3「提供手动升级入口」是互补而非冲突：**不自动**（生成新版本时旧需求不动），**但提供手动入口**让运营主动跟进流程改进。Decision 3 正是 Q4 配套的"显式升级入口"，与 Q4 的"有意为之，不自动"完全一致。

审计：本轮以 `logging.info` + 响应返回前后 `process_id` 为主；若项目已有 Demand 操作历史表则写入，否则不引入新表（避免过度设计）。

---

## 5. 更新的任务清单 T1~T10

> 原 T1~T6 已按产品裁定（Q1~Q5）修订；新增 T7~T10 承载用户三条决策。
> 每条：`文件:行号 → 改成什么`。**application/ 应用下的改动（T3 活实现部分、T8 的 ActionType）须排在工程师 FSM 批次之后执行**（team-lead 明示 application/ 当前被工程师占用）。

### T1 — RecruitmentProcess 模型 + migration（P0，依赖：无，需 migration）
- `process/models.py:172` `code = CharField(max_length=20, unique=True)` → 去掉 `unique=True`（保留 `max_length=20`）
- `process/models.py` 在 `RecruitmentProcess` 新增两字段：
  - `version_seq = models.PositiveIntegerField(default=1, db_index=True, verbose_name='版本序号')`
  - `is_latest = models.BooleanField(default=False, db_index=True, verbose_name='是否最新版')`
- `process/models.py:201` `Meta` 新增 3 条约束（**均作用于 `RecruitmentProcess.code`，不涉及 `ProcessStageLink.order`**）：
  - **C1** `UniqueConstraint(fields=['code','version_seq'], name='uniq_process_code_version_seq')`：同 code 内版本序号唯一。
  - **C2** `UniqueConstraint(fields=['code','current_version'], name='uniq_process_code_current_version')`：同 code 内版本字符串唯一（回填后统一为 `V{n}.0`，见 §6.3）。
  - **C3'（终裁 2026-08-10：采用方案 (d) 表达式唯一索引。原 C3 partial unique 在 MySQL 静默失效；中间稿的 (a) 冗余列方案已被 A/B 实测推翻，见下方对比表）**

    唯一性由 DB 直接从 `is_latest` + `code` **现算**，**不引入任何冗余列**：

    ```python
    from django.db.models import UniqueConstraint, Case, When, F, Value

    UniqueConstraint(
        Case(When(is_latest=True, then=F('code')), default=Value(None)),
        name='uniq_one_latest_per_code',
        violation_error_message='同一流程线（code）只能有一个最新版本（is_latest=True）',
    )
    ```

    - **语义**：`is_latest=True` 的行贡献键值 `code`，其余行贡献 `NULL`；两库唯一索引均允许多个 NULL → **每 code 至多 1 行 `is_latest=True`**。
    - **生成的 DDL**（MySQL 9.6.0 dev 实测原文）：

      ```sql
      CREATE UNIQUE INDEX `uniq_one_latest_per_code` ON `recruitment_processes`
        ((CASE WHEN `is_latest` = 1 THEN `code` ELSE NULL END));
      ```

      SQLite 测试库对应产出：`CREATE UNIQUE INDEX "uniq_one_latest_per_code" ON "recruitment_processes" ((CASE WHEN "is_latest" THEN "code" ELSE NULL END))`
    - **无需 `latest_key` 字段、无需 `save()` 同步、无需 `update_fields` 记得带字段、无需调用方自律。**

    **三方案对比（证据来源：team-lead dev MySQL A/B 临时表实测 + 架构师 2026-08-10 双库复测，残留 0）**

    | 维度 | (a) 冗余列 `latest_key` | (b) `select_for_update`+事务翻转 | **(d) 表达式唯一索引（采用）** |
    |---|---|---|---|
    | 索引在 MySQL 真实存在 | ✅ | —（无 DB 约束） | ✅ `information_schema.STATISTICS` 可查，`EXPRESSION` 列有值 |
    | 正常路径（经 `save()`）拦截重复 | ✅ | ✅ | ✅ |
    | **`.update(is_latest=True)` 绕过 `save()`** | ❌ **失守，静默污染** | ❌ 失守 | ✅ **IntegrityError** |
    | **`bulk_update` / 原生 SQL 绕过** | ❌ 失守 | ❌ 失守 | ✅ **IntegrityError**（原生 SQL 亦实测被拦） |
    | 并发窗口 | 无（DB 级） | **有**（应用层互斥） | 无（DB 级） |
    | 冗余列 | +1 列 `latest_key` | 0 | **0** |
    | 需调用方自律 | **是**（每处写路径都要同步 `latest_key`） | 是 | **否** |

    **(a) 被淘汰的决定性理由**：其"不依赖调用方自律"的论断**不成立**。`latest_key` 与 `is_latest` 的一致性完全由应用层维护，一旦有写路径绕过 `save()`，DB 拿到的 `latest_key` 就是陈旧值，唯一约束形同虚设——实测中同 code 出现 2 行 `is_latest=True` 且**无任何报错**。风险面是真实的：全仓非 test / 非 migration 代码中有 **18 处 `QuerySet.update()`**（team-lead 报 31 处，含 `dict.update` / `hashlib.update` / DRF `serializer.update`，实际 ORM 写路径 18 处），全部绕过 `save()`；更有力的反证是 `apps/process/migrations/0002_stage_start_end.py:9-10` 就是 `Stage.objects.filter(code='P001').update(is_start=True)`——**本项目历史上已经这样写过**。且本规格 `:401` 的原子翻转、§6.3 的 `bulk_update` 回填，两处都必须"人工记得"补写 `latest_key`，正是自律写法。(a) 把约束正确性外包给每一处写路径，而 (d) 把它完全收回 DB。

    **(b) 被淘汰的理由**：`select_for_update`+事务翻转属应用层互斥，须显式承认并发下有窗口、非终极防线，且同样挡不住 `.update()` 旁路。仅作为友好错误信息的前置校验保留，不作为不变量保证。

  - **C3'-代价与边界（采用 (d) 必须知悉，全部经双库实测）**

    | # | 项 | 结论 |
    |---|---|---|
    | 1 | **MySQL 版本下限** | Django `mysql/features.py` 门槛为 `not mariadb and storage_engine != 'MyISAM' and mysql_version >= (8, 0, 13)`。本项目实测 `mysql_version=(9, 6, 0)`、`mysql_is_mariadb=False`、`storage_engine=InnoDB` → `supports_expression_indexes=True`，**远超门槛，无版本风险**。⚠️ 但这是**软门槛**：若未来迁 MariaDB 或把表引擎改成 MyISAM，Django 会**静默跳过**该约束（与 partial index 同款陷阱）→ 故 §6.3 / T1 的「MySQL 真实索引核对」检查**必须保留**，它同时兜住了这个退化场景。 |
    | 2 | **SQLite 测试库支持** | `supports_expression_indexes=True`（sqlite3 3.53.3）。**端到端实测：索引真建（`sqlite_master` 可查）、正常路径与 `.update()` 旁路均抛 `IntegrityError`**。→ **不会静默跳过、不会报错**，测试库与生产**行为一致**。这是 (d) 相对原 C3 partial unique 的关键优势：C3 在 SQLite 真建 / MySQL 静默跳过，制造"假绿"；(d) 两库都真建，**CI 绿 == 生产绿**。 |
    | 3 | **测试策略影响** | 因两库行为一致，C3' 的唯一性拦截测试**可以在默认 SQLite 测试库上写并可信**。但 §1 中「约束是否真建」的核对仍须在 MySQL 上做一次（防第 1 行的退化场景），保留 T1 的 `information_schema.STATISTICS` 检查。 |
    | 4 | **`makemigrations` 产出** | `deconstruct()` / `MigrationWriter` 序列化正常，migration 文件仅需 `from django.db import models`，无额外 import：`models.UniqueConstraint(models.Case(models.When(is_latest=True, then=models.F('code')), default=models.Value(None)), name='uniq_one_latest_per_code')`。`constraint.contains_expressions=True`。 |
    | 5 | **`sqlmigrate` / `AddConstraint` 行为** | 对**已有数据**的表执行 `AddConstraint` 实测成功；若存量数据违反不变量（同 code 两行 `is_latest=True`），**`AddConstraint` 明确抛 `IntegrityError` 让 migration 变红，不静默通过** → 回填顺序错误会被立刻发现。 |
    | 6 | **是否仍需 `is_latest` 普通索引** | **需要，且应改为复合索引。** 表达式索引**不能**服务普通查询：MySQL `EXPLAIN` 实测 `WHERE is_latest=1 AND code='W001'` 在只有表达式索引时是 `Table scan`；加 `(code, is_latest)` 复合索引后变为 `Covering index lookup`。→ 建议 `is_latest` **去掉** `db_index=True`（低基数布尔单列索引近乎无用），改在 `Meta.indexes` 加 `models.Index(fields=['code', 'is_latest'], name='idx_process_code_latest')`，服务 §1.3/§4.2 的主力查询 `filter(code=..., is_latest=True, status=..., deleted_at__isnull=True)`。 |
    | 7 | **`full_clean()` 友好报错** | Django 的 `UniqueConstraint.validate()` **支持 expressions**（实测：重复 latest 抛 `ValidationError`；历史版本 / 不同 code / 自身重存**均无误报**）。配合上方 `violation_error_message`，serializer 层可直接给出中文提示，无需自行写校验。 |
    | 8 | **翻转顺序（硬约束）** | 双库实测：**先升后降必炸**（`IntegrityError`），**必须先降后升**。见 T2 `:401` 已按此写。 |
    | 9 | **在线 DDL / 锁** | MySQL 函数索引以隐藏虚拟生成列实现，建索引需扫表。`recruitment_processes` 当前仅 7 行，**本项目无实际影响**；若未来表增大，走标准 `ALTER TABLE` 在线 DDL 评估即可。 |
    | 10 | **未采用 `deleted_at` 感知型表达式** | 备选写法 `Case(When(Q(is_latest=True) & Q(deleted_at__isnull=True), then=F('code')), ...)` 实测两库均可建且生效，可让软删行自动退出约束。**但不采用**：它允许"1 个软删 latest + 1 个 live latest"共存，任何忘记 `deleted_at__isnull=True` 的查询（§1.5 已实证本仓惯犯）会取回 2 行。当前简单式更严格——全表每 code 至多 1 行 `is_latest=True`，即便查询写漏软删过滤也不可能取到 2 行。 |
- **soft_delete / restore 与 is_latest 的交互（发现，必须处理）**：`apps/common/models.py` 的 `soft_delete()` 只置 `deleted_at`、**不动 `is_latest`** → 软删流程行保留 `is_latest=True`，之后同 code 新建/clone 行也置 `is_latest=True` → 同 code 出现两行 `is_latest=True`。该破坏**与约束是否真建无关**（约束真建→ IntegrityError 炸正常业务；约束没建→ 不变量静默腐化），两条路都不可接受。
  - **落点：模型层 override（不放 service）**。`RecruitmentProcess` 重写 `soft_delete()`：调 `super().soft_delete()` 前先 `self.is_latest = False`。（采用 (d) 后**无 `latest_key` 需要同步**，只需这一个语义动作。）
  - **`restore()` 对称行为**：恢复旧版本**不得无条件抢回 `is_latest=True`**——`restore()` 只清 `deleted_at`，不触碰 `is_latest`（旧版本保持 `is_latest=False`），除非显式 promote。
  - ✅ **(d) 下该场景是"响亮失败 + 可自愈"，非静默腐化（双库实测）**：即便有人绕过 override 用 `.update(deleted_at=...)` 软删、令软删行滞留 `is_latest=True`，(d) 的表现是——① 直接提升新行会抛 `IntegrityError`（**暴露问题，不静默**）；② T2 `:451` 的翻转语句 `filter(code=...)` 不过滤软删（§1.5：`RecruitmentProcess.objects` 是原生 Manager），会**连软删行一并降级** → **自动自愈**，实测翻转后 latest 数恰为 1。三重覆盖：`soft_delete()` override + T2 翻转自愈 + DB 兜底。
  - ⚠️ **回填脚本注意（已随 (d) 简化）**：§6.3 `bulk_update` 只需写 `is_latest`，**不再有 `latest_key` 需要人工记得同步**——这正是 (a) 被淘汰的自律缺口之一。
  - **数据对照结论（事实 1）**：dev `RecruitmentProcess` 7 行（code 互异，W001-W007），`current_version` 分布 `'1.0'×4` / `'V1.0'×3`。**3 条约束全部基于 `code`，与 `ProcessStageLink.order` 完全无关** → 在现有 `ProcessStageLink` 数据（含软删导致的 order 断号、同 order 重复）上**不受影响、migration 通过**。
  - **明确不采用任何 `(process, order)` 唯一约束**：软删机制使 `order` 不可靠（dev 实测同 process 内 `order=4` 出现 live+软删各一次，断号/起始任意为常态）。即便改用 partial-live 写法 `UniqueConstraint(fields=['process','order'], condition=Q(deleted_at__isnull=True))`，虽在**当前** dev 数据上 live 集内 order 各自唯一（live=[1,4] 与 [4,8,9,10]）而"恰好通过"，但属脆弱约束（"软删旧 link 后用相同 order 重建"行为可随时打破），且版本化模型根本不需要它 → **一律不加**。
  - ⚠️ **「同仓已有先例」论证作废（发现，实证）**：原稿引用 `RecruitmentStage` 的两个 partial unique 作为"技术可行性已被本项目验证"的依据——**该先例本身在生产 MySQL 上同样失效**。全仓仅 `RecruitmentStage.uniq_only_one_start_stage` / `uniq_only_one_end_stage` 两个带 `condition` 的 `UniqueConstraint`；经查 MySQL `information_schema.STATISTICS`，二者**均不存在**（Django 在 `supports_partial_indexes=False` 后端**静默跳过**——migrate 不报错、不建索引、不留痕迹）。故 partial unique 在本项目生产环境**从未生效过**，不可作为可行性依据（详见 §8 遗留缺陷条目）。**C3' 表达式唯一索引方案 (d)（见上）才是两库均真实生效的设计。** 侧证（架构师 2026-08-10 实测）：在 SQLite 测试库上建同名探针索引时报 `index uniq_only_one_start_stage already exists`——**反向坐实该 partial index 在测试库确实真建、而在生产 MySQL 不存在**，"假绿"闭环得到双向证明。测试库=SQLite（`supports_partial_indexes=True`）→ 约束真建、CI 全绿；生产=MySQL→ 约束不存在：这正是本轮一直在治理的"测的不是生产路径"假绿闭环，须用 T1 回归测试点 / §6.3 的 MySQL 真实索引核对打破。
  - **索引调整（随 (d) 一并落地，见 C3'-代价与边界 #6）**：`is_latest` **去掉** `db_index=True`，改为 `is_latest = models.BooleanField(default=False, verbose_name='是否最新版')`；在 `Meta.indexes` 新增 `models.Index(fields=['code', 'is_latest'], name='idx_process_code_latest')`。理由：表达式索引不服务普通查询（MySQL `EXPLAIN` 实测为 `Table scan`），复合索引后为 `Covering index lookup`；低基数布尔单列索引近乎无用。
- `process/models.py:174` `current_version` default `'1.0'` → 改为 `'V1.0'`（与 `serializers.py:490` 一致；消除 X1 不一致）
- **V3 严重度上调（事实 3）**：原"else 分支撑爆 `max_length` 的边缘问题"定性**错误**。`bump_version` 的 else 分支（`versioning.py:67` `f'{cur}+1'`）是**主路径**——dev 7 行里 `'1.0'`（走模型 default，W001-W004）占 4 行，**首次升版即产出垃圾版本号 `1.0+1` 并直接展示在 UI**（`__str__` 带出）；递推长度每次 +2，`1.0`→`1.0+1`→…→第 9 次 bump 超 `max_length=20` 才炸，前 8 次静默污染。故 V3 由"边缘溢出"上调为 **P0 用户可见数据污染**（6 个 live 流程里 4 个的默认行为）。T1 backfill（§6.3）必须规范化 `current_version`，吃下 `'1.0'`/`'V1.0'`/`'1.0+1'` 全部形态，解析失败显式处理（不静默兜底）。
- **RunPython 回填**（§6.3）：按 `code` 分组、`order_by('created_at')` 赋 `version_seq`；每组仅 `is_latest=True` 的那一行（max version_seq / max created_at）。
- `load_process_templates.py:239` `_next_process_code()` 改用 `RecruitmentProcess.objects.filter(code__startswith='W').values('code').distinct().order_by('-code').first()` 取最大，避免去 unique 后 count 撑大/撞号。
- **工厂更新**：`RecruitmentProcess` 测试工厂加 `is_latest=True`（默认 False 会让依赖 `is_latest=True` 过滤的查询落空）；并 audit 是否有测试同 code 建多行（会触发 `uniq_one_latest_per_code` 唯一约束冲突——每组至多 1 行 `is_latest=True`）。
- 回归测试点（随 (d) 终裁更新）：
  1. 同 code 建多版本行（`is_latest=False`）不报 IntegrityError。
  2. 同 code 插入第 2 行 `is_latest=True` → `IntegrityError`（正常路径）。
  3. **`RecruitmentProcess.objects.filter(...).update(is_latest=True)` 绕过 `save()` 造第 2 个 latest → 同样 `IntegrityError`**（这是 (d) 相对 (a) 的核心收益，**必须有此用例**；(a) 在此处会静默污染）。
  4. `bulk_update(['is_latest'])` 造第 2 个 latest → `IntegrityError`。
  5. 翻转顺序：**先升后降必炸、先降后升成功**（双库实测已确认，锁死 T2 `:451` 写法）。
  6. 软删某流程后（`soft_delete()` 置 `is_latest=False`），同 code 其他 live 行可正常置 latest 不冲突；另补一例：绕过 override 直接 `.update(deleted_at=...)` 使软删行滞留 `is_latest=True` 时，T2 翻转语句能自愈（翻转后 latest 数 == 1）。
  7. `full_clean()` 对重复 latest 抛 `ValidationError`，且对历史版本 / 不同 code / 自身重存**无误报**。
  8. `list_process_versions` 默认 `is_latest=True` 过滤仍正确。
- **⚠️ DB 约束验收（随 (d) 终裁大幅简化，但 MySQL 核对不取消）**：
  - **好消息**：(d) 在 **SQLite 与 MySQL 上行为完全一致**（均真建索引、均拦截 `.update()` 旁路，架构师双库实测）→ 上述 1~8 号功能性用例**可以在默认 SQLite 测试库上写，且结论对生产可信**。这正是 (d) 相对原 C3 partial unique 的关键价值：**不再需要"CI 绿但生产未必"的免责声明**。
  - **仍须保留的 MySQL 检查**：`supports_expression_indexes` 是**软门槛**（依赖 `非 MariaDB + 非 MyISAM + >=8.0.13`）。若未来换库/换引擎，Django 会**静默跳过**该约束。故仍须一条在 MySQL 上核对 `information_schema.STATISTICS` 真实索引存在性的检查——建议二选一：(1) 一个 pytest 用例（MySQL 测试库）断言 `uniq_one_latest_per_code` 存在于 `STATISTICS` 且其 `EXPRESSION` 列非空；(2) 一个 CI 步骤，migrate 后 `SELECT` 该索引名，缺失即失败。**推荐同时核对 `connection.features.supports_expression_indexes is True`，一旦退化立即红。**
- **⚠️ 硬前置依赖边（发现 6，实证）**：本任务「去 `code` unique + 建 3 约束」是 **T3 clone 跑通的硬前置**。`clone_process_with_new_version` 第一步即 `versioning.py:98` `code=process.code` 创建新行；而当前 `code` 仍 `unique=True`，dev 实时复现 `IntegrityError: Duplicate entry 'W001' for key 'recruitment_processes.code'`，**未去 unique 前 clone 根本无法执行**。故 migration 执行顺序**必须 T1 先于 T3**，依赖图「T1→T3」边画实（非虚）。反向坐实：clone 路径此前**从未被真实执行**（零测试覆盖 + 实测必炸），故 T3/T4 测试**必须端到端覆盖 clone→upgrade 全链路**，不能只做单测（见 T3 / T4）。

### T2 — 废弃 bump-version 端点 + bump_version 降级 + clone 不改动老行（P0，依赖：T1，需 migration：否）
- `process/views.py:294-311` 删除 `bump_version_action` 端点（Q1：三重错配，零前端调用）。
- `versioning.py:51-74` `bump_version` → 改名 `_compute_next_version(process)`，返回值基于 `process.version_seq`（`f'V{process.version_seq}.0'`），**不再 `process.save()` 改老行**（修 V2/V3/V4）。
- `versioning.py:95` `new_version = bump_version(process)` → 改为 `new_version = _compute_next_version(process)`（不再污染老行）。
- `versioning.py:98-111` 新行 `code=process.code` 现在合法（T1 已去 unique）。新增 `is_latest=False` 显式写入。
- **is_latest 原子翻转（顺序是硬约束：必须先降后升）**：clone 提交前，须在事务内（建议 `select_for_update` 锁同 code 行防并发）：

  ```python
  # ① 先降级：filter(code=...) 刻意不过滤软删，一并降级软删行（自愈，见 C3' soft_delete 条）
  RecruitmentProcess.objects.filter(code=new_process.code).exclude(id=new_process.id).update(is_latest=False)
  # ② 后升级
  new_process.is_latest = True
  new_process.save(update_fields=['is_latest'])
  ```

  - **顺序不可颠倒**：双库实测「先升后降」必抛 `IntegrityError`（同 code 瞬时存在 2 行 `is_latest=True`）。
  - 采用 (d) 后**不再需要写 `latest_key=None`、也不需要在 `update_fields` 里带 `'latest_key'`**——原 (a) 方案此处正是必须"人工记得"的自律缺口。
- `versioning.py` `clone_process_with_new_version` docstring 写明「按 Q4 裁定，克隆不改指任何 Demand/Position/Application」（有意为之）。

### T3 — 合并升版本实现 + 阶段映射 + 校验（P0，依赖：T1、T7；application/ 部分待工程师 FSM 批次后）
- `versioning.py:166-196` 删除死代码 `upgrade_application_to_latest_version`（其"改指 process"逻辑已并入活实现；注意该死代码含 V5 `from_version` 读后写 bug：`versioning.py:184` 赋值、`:194` 读，使 `from_version` 恒等于 `to_version`——合并时**只取"改指"逻辑，严禁照搬读后写**，须在赋值前存 `old_version`/`old_stage`（见 §1.3.1 / §1.3.2 约定））。
- `application/services/__init__.py:673-689` 活 `upgrade_workflow_version` 重写为 §1.3 规格：解析 `is_latest=True` 目标、校验（禁降版本 / 禁归档 / 禁跨 code）、调用 `resolve_target_link`（T7）、真正改指 `process`+`current_link`+`current_stage`、写含 `stage_remapped` 的审计。（此文件属 application/，排在工程师 FSM 批次后。）
- `application/views.py:381-394` `upgrade_version` 端点基本不变（已正确捕获 `StateTransitionError`→409），仅确认 `detail=True` 透传。
- 回归测试点（锁定勘误 2）：clone 后调 upgrade-version 应成功改指新行且**不**返回 409；升到 `is_latest=False` 中间版 → 409；跨 code → 409；阶段被删触发回落且 `stage_remapped=True`。
- **⚠️ clone 只遍历 live 阶段（发现 5，实证）**：克隆阶段遍历原 `versioning.py:114` `for link in process.stage_links.all():` 会**把软删阶段复活**成新流程的正常阶段（实测 1：`RecruitmentProcess.objects` / `ProcessStageLink.objects` 均为原生 `django.db.models.manager.Manager`，**不过滤软删**；实测 2：流程 `Yw9GBzXA4rJT8348AthR2` 的 `stage_links.all()` 返回 8 条，其中 4 条软删，`orders=[2,3,4,4,5,8,9,10]`）。**改为只遍历 live 行**：`for link in process.stage_links.filter(deleted_at__isnull=True):`（具体代码改动在 T4 的 V6 补全段，此处为强制约束）。复活软删阶段会污染新版本的阶段集合，进而使 T7 映射算法在错误数据上运算。
- **⚠️ 端到端测试（发现 6）**：clone 路径此前从未真实执行，本任务测试**必须端到端**覆盖 `clone → upgrade-version（含阶段回落）→ list_process_versions`，断言新流程阶段集合不含任何软删阶段、且升级后审计正确；不能只做 `upgrade_workflow_version` 单测。

### T4 — clone 深拷贝补全 + AutomationRule 复制（P1，依赖：T2，需 migration：否）
- `versioning.py:113-142` clone 补全（修 V6）：
  - **阶段遍历只取 live（发现 5）**：原 `versioning.py:114` `for link in process.stage_links.all():` 返回含软删行，会把软删阶段**复活**成新流程正常阶段。改为 `for link in process.stage_links.filter(deleted_at__isnull=True):`。实证：流程 `Yw9GBzXA4rJT8348AthR2` 的 `stage_links.all()` = 8 条（4 软删，`orders=[2,3,4,4,5,8,9,10]`）；原生 `Manager` 不过滤软删，故**必须显式 `filter(deleted_at__isnull=True)`**。
  - 复制 `EntryConditionRule`（`entry_condition_rules` 反向关系，漏拷）
  - 复制 `TimeLimitRule`（`time_limit_rules` 反向关系，漏拷）
  - 采用字段自省拷贝（排除 `id`/`link`/`process`/`created_at`/`updated_at`），避免未来加字段再漏。
- `AutomationRule` 复制（Q3）：对旧行每条 `AutomationRule`，按"新版本阶段集合"过滤后复制：
  - `rule.stage` 不在新版本 `stage_links` 的 `stage` 集合 → **跳过不复制**
  - `rule.next_stage` 不在集合 → 复制规则但 `next_stage=None`、`enabled=False`，响应体返回受影响规则清单
  - `AutomationRule.stage`/`next_stage` 均 FK→`RecruitmentStage`（全局字典），复制 **不产生悬空引用**（已核实 `automation/models.py:54,73`）。
- 回归测试点：阶段未变时克隆后新行 `automation_rules` 数量 == 旧行；删阶段后对应规则被跳过/禁用；`Demand.process_id`/`Position.process_id`/`Application.process_id` clone 前后逐一相同（锁定 Q4）。

### T5 — list_process_versions + archive_process 整条线（P2，依赖：T1，需 migration：否）
- `versioning.py:148-163` `list_process_versions`：
  - 加 `deleted_at__isnull=True` 过滤软删（修 V8）。**根因（发现 5）**：`versioning.py:148-163` `list_process_versions` 原 `process.stage_links.all()` / `process.stage_links` 不过滤软删——与 T3/T4 clone 同款病灶（原生 `Manager` 不过滤软删）。未修前会把软删阶段也列进版本视图，误导升级落点选择。
  - 排序改 `order_by('version_seq')`（修 V9 字典序；依赖 T1 的 `version_seq`）
  - 用 `prefetch_related('stage_links')` 或 `annotate` 消除 N+1（修 V9）
  - 返回体含 `version_seq`/`is_latest`，且恰一行 `is_latest=True`
- `versioning.py:28-48` `archive_process`：
  - 改为归档**整条 code 线**：`RecruitmentProcess.objects.filter(code=process.code, deleted_at__isnull=True).exclude(status='ARCHIVED').update(status='ARCHIVED', archived_at=now)`
  - 返回值统一（`archived`/`reference_count`:int/`archived_at`）+ 新增 `archived_version_count`（本次归档行数）（修 V7 + Q5）
  - `views.py:251` 早退判断改为「该 code 下已无 ENABLED 行」才算重复归档
- 回归测试点：归档后同 code `ENABLED` 行数=0；返回值两类分支 key 集合相同且 `type(reference_count) is int`；含 2 demand（1 软删）时 `reference_count==1`。

### T6 — 删除 stage_transitions.py + 守卫测试（P1，依赖：无）
- 由工程师执行（application/ 当前被占用）。本文档不重复规格，原 §4-T6 维持：`apps/application/services/stage_transitions.py` 整文件删除 + 新建 `tests/test_no_dead_service_modules.py` ratchet 守卫。**本文档不再引用该文件**（路径勘误见 §0-8）。

### T7 — 阶段映射共享服务 `resolve_target_link`（P1，依赖：T1，需 migration：否）
- 新增 `apps/django/apps/application/services/stage_mapping.py`（或并入 `application/services/__init__.py`）：实现 §2.2 算法。纯函数、无副作用（只查询 new_process.stage_links）。
- 被 T3（upgrade）与 T8（change-process）共用。
- 回归测试点（边界表 §2.3 全覆盖）：精确匹配 / 前序回落 / 无前序回落起点 / 无 current_link 落起点 / 新版零阶段报错。
- ⚠️ **测试必须自带 seed 数据**：dev 库 `Application=0`、`Demand=0`（事实 4），阶段映射与升级测试不得依赖 dev 现状；此库吃过 RunPython 空表空循环的亏。

### T8 — 跨流程线迁移 change-process 端点（P1，依赖：T1、T7；ActionType 改动需工程师 FSM 批次后）
- `application/views.py` ApplicationViewSet 新增 `@action(detail=True, methods=['post'], url_path='change-process')`：校验入参 → 调 `ApplicationService.change_process`（§3.2 规格）。
- `application/services/__init__.py` 新增 `change_process(application, target_process, target_stage_link, actor, reason)` 静态方法（§3.2）。审计快照 `old_process`/`old_stage` 按 §1.3.2 约定在变更前采集（§3.2 :228，早于 :229-233 赋值），`from_process_id`/`from_stage` 不得读后写。
- `application/models.py:209-221` `ApplicationHistory.ActionType` 新增 `CHANGE_PROCESS = 'CHANGE_PROCESS', '更换流程线'`（**此改动在 application/，须工程师 FSM 批次后**；TextChoices 加值无需 migration）。
- 权限：复用/新增 HR 鉴权。
- 回归测试点：跨 code 成功改指 + 写 CHANGE_PROCESS；`target_stage_id` 不属于目标流程 → 409；同流程 → 409；`reason` 缺省 → 400。
- ⚠️ **测试必须自带 seed 数据**：dev 库 `Application=0`（事实 4），change-process 测试须自建 process + application + stage_links，不得依赖 dev 现状。

### T9 — 需求升级入口（P1，依赖：T1，需 migration：是；改 demand/position 应用，含 Position.demand 外键 migration）
- `demand/views.py` DemandViewSet 新增 `@action(detail=True, methods=['post'], url_path='upgrade-process-version')` → 调 `DemandService.upgrade_demand_process`（§4.2）。审计快照 `old_pid` 按 §1.3.2 约定在 Demand 改指前采集；若补逐 Position 审计，须在 `pos.process = ...` 赋值前采集，不得读后写（见 §4.2 升级伪代码）。
- `demand/services.py`（或新建）实现 `upgrade_demand_process`：改指 Demand + 其 Positions 到同 code `is_latest=True` 版本（**遍历 `demand.positions`，即 G1 路径 (c) 新增的 `Position.demand` 反向名**）；**不改指 Application**。
- **需 migration：是**——新增 `Position.demand` 外键（`ForeignKey(Demand, null=True, on_delete=SET_NULL, related_name='positions')`，`AddField` + 存量 `demand_id=NULL`）。与 T1 同属 process/demand/position 模型层，须同批或紧邻 migration，避免顺序冲突。
- **process_version 格式**：统一 V 前缀 `'V{n}.0'`（G2）；`Demand/Position.process_version` default 由 `'1.0'` 改 `'V1.0'`。`time_limit` 匹配逻辑改按 `process_id` 为**配套必做项**（独立派活，不归 T9）。
- 回归测试点（须自带 seed 数据，dev 两表均 0 行）：Demand+其 Positions `process_id` 变新版本且 `process_version` 为 `'V{n}.0'`；已有 Application `process_id` **不变**（锁定 BR-102）；无新版时幂等；目标版本已归档时拒绝。

### T10 — 历史假升级审计脚本（P2，依赖：无，独立）
- 新增 `apps/django/apps/application/management/commands/audit_fake_upgrades.py`（§1.4 规格）：只读诊断，输出受影响 `UPGRADE_VERSION` 记录清单（CSV），**不自动改写**。
- **⚠️ 须在 fresh 真实数据 DB 验证** `ApplicationHistory.detail` JSON 形态。

### T11（可选 P2）— change-process 预览端点
- `GET /applications/{id}/change-process-preview/?target_process_id=X`：两线 `RecruitmentStage` 精确匹配，返回建议落点 + 无对应阶段清单（§3.1）。最终落点仍以 POST `target_stage_id` 为准。

### 依赖与执行顺序

```
T1(模型+migration+回填)
   ├──> T7(resolve_target_link)
   ├──> T2(废弃端点+clone不污染老行)
   │        └──> T4(clone补全+AutomationRule复制)
   ├──> T3(合并升版本实现)        ← application/ 部分待工程师 FSM 批次后；**⚠️ 硬前置（发现 6）：T1 去 code unique 是 clone 跑通前提，T1 必须先于 T3，此边画实**
   ├──> T5(list+archive整条线)
   ├──> T8(change-process)        ← ActionType 改动待工程师 FSM 批次后
   └──> T9(需求升级入口)           ← demand/position，独立可并行
T10(审计脚本) 独立，随时可做
T6(删死代码) 由工程师执行，独立
```

**建议执行顺序**：`T1 → T7 → T2 → T4 → T5 →（工程师 FSM 批次完成）→ T3(app部分) → T8 → T9 → T10`。
（T1 是公共地基；T7 早做供 T3/T8 复用；application/ 改动排在工程师 FSM 批次之后，避免文件冲突。）

---

## 6. Migration 方案

### 6.1 RecruitmentProcess 字段/约束变更（T1，已按 C3' 终裁 (d) 更新）
- `AlterField`：`code` 去 `unique=True`。
- `AddField` ×2（**不再有 `latest_key`**）：
  - `version_seq` (PositiveIntegerField, default=1, db_index=True)
  - `is_latest` (BooleanField, default=False)　← **不加 `db_index=True`**，改由下方复合索引服务（见 C3'-代价与边界 #6）
- `AlterField`：`current_version` default `'1.0'`→`'V1.0'`。
- `AddIndex` ×1：`models.Index(fields=['code', 'is_latest'], name='idx_process_code_latest')`。
- `AddConstraint` ×3：
  - `uniq_process_code_version_seq`：`UniqueConstraint(fields=['code','version_seq'], ...)`
  - `uniq_process_code_current_version`：`UniqueConstraint(fields=['code','current_version'], ...)`
  - `uniq_one_latest_per_code`：**C3' 表达式唯一索引**
    `UniqueConstraint(Case(When(is_latest=True, then=F('code')), default=Value(None)), name='uniq_one_latest_per_code', violation_error_message=...)`
    序列化后 migration 文件仅需 `from django.db import models`，无额外 import。
- `RunPython` 回填（§6.3）。

**操作顺序（重要）**：`AddField(is_latest, default=False)` → 存量行全部 `is_latest=False` → 表达式全为 NULL → `AddConstraint` **不会**因存量数据失败。之后 `RunPython` 每 code 只置 1 行为 True，亦不冲突。
**若存量数据违反不变量**（同 code 已有 2 行 `is_latest=True`），`AddConstraint` 会**明确抛 `IntegrityError` 让 migration 变红**（双库实测），不会静默通过——这是期望行为，便于在部署时立刻发现脏数据。

### 6.2 ApplicationHistory 新 ActionType（T8）
- `application/models.py:209` `ActionType` 增加 `CHANGE_PROCESS`。TextChoices 加值，**无需 schema migration**（CharField）。但改 `application/models.py` 属 application/，须在工程师 FSM 批次后执行。

### 6.3 RunPython 回填（⚠️ 必须 fresh 真实数据 DB 验证）

```python
import re
CLEAN_VERSION = re.compile(r'^(V)?(\d+)\.(\d+)$')   # 1.0 / V1.0
CORRUPT_VERSION = re.compile(r'\+')                # 1.0+1 等拼接态

def normalize_current_version(raw, seq):
    """current_version → 规范化 'V{seq}.0'。解析失败不静默兜底：强制归一 + 返回告警串。"""
    raw = raw or ''
    if CLEAN_VERSION.match(raw):
        return f'V{seq}.0', None                      # 1.0 / V1.0 → 统一重写为 V{seq}.0
    # 已污染（'1.0+1'）或不可识别：无法反推真实版本，按 seq 强制归一，显式告警（非静默）
    return f'V{seq}.0', f'current_version={raw!r} coerced to V{seq}.0 (was not clean)'

def backfill_version_fields(apps, schema_editor):
    RecruitmentProcess = apps.get_model('process', 'RecruitmentProcess')
    warnings = []
    for code in RecruitmentProcess.objects.values_list('code', flat=True).distinct():
        rows = list(RecruitmentProcess.objects.filter(code=code).order_by('created_at', 'id'))
        if not rows:
            continue
        # version_seq 按 created_at 递增赋（克隆行创建更晚 → seq 更大）；id 二次排序兜底平局
        for i, r in enumerate(rows, start=1):
            r.version_seq = i
            norm, warn = normalize_current_version(r.current_version, i)
            r.current_version = norm                          # 规范化，吃下 1.0/V1.0/1.0+1
            if warn:
                warnings.append((code, r.id, warn))
        # is_latest 只在 live 行里选——软删行永不为 latest，与 soft_delete() 的 is_latest=False 保持同一不变量
        live_rows = [r for r in rows if r.deleted_at is None]
        latest_id = live_rows[-1].id if live_rows else None
        for r in rows:
            r.is_latest = (latest_id is not None and r.id == latest_id)
        if latest_id is None:
            warnings.append((code, '-', f'code={code} 全部行已软删，该 code 无 live 最新版本（预期行为，仅记录）'))
        RecruitmentProcess.objects.bulk_update(rows, ['version_seq', 'is_latest', 'current_version'])
    if warnings:
        # 显式输出，不静默：migrate 时打印到 stdout，供人工复核污染范围
        for code, rid, w in warnings:
            print(f'[backfill WARNING] code={code} id={rid} {w}')

```
> **回填后断言（fresh DB + 真实数据）**：对每个 code，`is_latest=True 且 deleted_at IS NULL` 的行数必须为 1（该 code 至少有一条 live 行时）或 0（全部软删时）；`is_latest=True 且 deleted_at IS NOT NULL` 必须为 0。dev 现网预期：W001-W006 各 1 条 live latest，W007 为 0（全软删）。

```python
def reverse(apps, schema_editor):
    # 回滚：is_latest/version_seq 置默认（字段仍在，仅清语义）
    # 注意：此 update 把所有行 is_latest 置 False → 表达式全为 NULL → 不违反 C3'
    # 注意：current_version 规范化不可逆——forward 把 '1.0' 重写为 'V1.0'，reverse 不回滚版本号（保持 V 前缀形态）；见 §7 红线 4 例外。
    RecruitmentProcess = apps.get_model('process', 'RecruitmentProcess')
    RecruitmentProcess.objects.update(is_latest=False, version_seq=1)
```

**⚠️ 回填期间的约束交互（(d) 特有，须知悉）**：`bulk_update` 生成单条 `UPDATE ... SET is_latest = CASE WHEN id=... END`，同 code 内**每行只会被赋值一次**，且回填前所有行均为 `is_latest=False`（AddField default），故**不存在瞬态双 latest**，不会误触发约束。反之，任何"先把新行置 True 再降级老行"的写法都会炸——见 T2 `:451` 的先降后升硬约束。

**⚠️ 必须在有真实数据的 fresh DB 上验证**：
1. 本项目踩过 `:memory:` 空库让 RunPython 的 bug 完全不显形、生产一跑就 `AttributeError` 的坑。空测试库 `backfill` 直接 no-op，无法暴露真实数据异常（如 `code` 为 None、同 `created_at` 多行、`current_version` 格式异常）。
2. 验证步骤（强制）：用 `dev_db.sqlite3`（3 行、code 互异）或生产脱敏 dump 灌入 fresh DB → 跑 migration → 断言：
   - 每个 `code` 恰 1 行 `is_latest=True`
   - `version_seq` 全局唯一（per code）
   - `current_version` 全部规范为 `V{n}.0` 形态；若有 coerced 告警，记录于 migration 日志并人工复核（见 §6.3 回填）
3. 若真实数据出现 `created_at` 相同导致 seq 平局，按 `id` 二次排序兜底（脚本中已实现 `order_by('created_at')`，如需再加 `.order_by('created_at','id')`）。

### 6.4 数据订正脚本（T10，独立，非 migration）
- 见 §1.4。只读诊断，**不**进 migration，避免在生产 migration 中做不可逆改写。

### 6.5 软删占位（故障 A）—— 与 clone 复活同根

**故障 A（与 故障 B「clone 复活软删 link」同根：均因原生 Manager 不过滤软删 + 硬唯一约束不认 `deleted_at`）**：
`process/models.py:250` `unique_together=[('process','stage')]` 是 DB 硬索引，**不含 `deleted_at`**；而 `views.py:482` `perform_destroy` 走 `soft_delete()`（仅置 `deleted_at`，不真删）。
→ **阶段从流程移除（软删）后，永远无法再加回同一 (process, stage) 组合**。
team-lead 事务内实跑（已回滚）：W007×P002 软删后重加即 `IntegrityError (1062) Duplicate entry '...-stg_002_resume_eval' for key 'process_stage_links_process_id_stage_id_42071938_uniq'`。
现网 **17 个 (process,stage) 组合已被软删行永久占位**（live=0 且 dead>0）；「live+软删并存=0」反证该硬约束确在生效（软删行仍占坑）。

**裁定：本批次【不修】，登记为已知遗留**（与 §8 RecruitmentStage 两条 partial unique 同属范围外、同根假绿，留待统一治理）。理由：
- 本增量主题是 `RecruitmentProcess` 版本化 + 阶段**映射回落**，不触及 `ProcessStageLink` 增删生命周期；故障 A 修复需改 `ProcessStageLink.Meta` 约束 + 可能数据订正 + 回归，属独立变更，塞入本批次会稀释版本化主题并扩大 migration 面。
- 未来若修，机制**必须与 C3' 同源用表达式唯一索引**：`UniqueConstraint(Case(When(deleted_at__isnull=True, then=Concat(F('process_id'), Value('|'), F('stage_id'))), default=Value(None)), name='uniq_live_process_stage')`（或等价写法），**严禁用带 `condition=` 的 partial UniqueConstraint**——MySQL `supports_partial_indexes=False`、SQLite=True 会让 CI 全绿而生产静默跳过，与 §8 已记 RecruitmentStage 两条是同一个坑，不许踩第二次。
- **分隔符必须用 `'|'`，不得用 `'-'`**：nanoid 字母表含 `-`/`_`，现网 id 实有连字符（`W3XPXHbtkU-ltnDoTjKa2` / `aeH-SWipX7mMGD90thDFY`）；用 `-` 时正确性依赖「process_id 恒 21 位」这条隐式不变量，换生成器或数据导入即静默引入歧义。`|`、`:`、`#`、`$` 经实测均不出现在现网任何 process_id / stage_id 中。
- **前提：两列必须 NOT NULL**。Django `Concat` 编译为 `CONCAT_WS`，而 `CONCAT_WS` **跳过 NULL 参数**（原生 `CONCAT` 是任一参数 NULL 即返回 NULL）。当前 `process_id`/`stage_id` 均为 NOT NULL 外键，行为等价；若将来任一列改 nullable，表达式会静默塌缩成「只剩另一列」，唯一性语义被悄悄改写。
- **机制可行性已实测坐实（team-lead，dev MySQL 9.6.0 临时表，8/8 PASS，残留 0，脚本 `/tmp/probe_expr_twocol.py`）**：① 索引可创建；② `information_schema.statistics` 命中，真实存在非假绿；③ 同 (p,s) 两条 live 被 `IntegrityError` 拦截；④ **软删后重加同一阶段放行（故障 A 解除）**；⑤ 反复删加 4 轮后 live 恰 1 行；⑥ **`UPDATE SET deleted_at=NULL` 旁路复活软删行被 DB 拦截**（与 C3'(d) 同样不依赖调用方自律）；⑦ 跨组合互不干扰；⑧ Django ORM 生成真实 SQL 非 None。未来治理时**沿用同一份 MySQL `information_schema.STATISTICS` 索引存在性核对清单**（与 C3' 共用），防 `supports_expression_indexes` 软门槛在换库/降版时静默跳过。
- 现网 17 条历史占位数据：判定**保留并记为已知遗留**（不选 `0005` RunPython 硬删）。理由：硬删动生产数据、需 DBA 评审；且这 17 个组合当前业务上"已移除且不再需要"，保留占位仅意味"将来也加不回"，不造成新损坏；统一治理时一并决定（届时表达式唯一索引使 live 唯一、dead 不占位）。

**影响（已知遗留，须明示）**：这 17 个 (process,stage) 组合的阶段**永久无法恢复**——任何"重新把该阶段加回该流程"的操作都会 `IntegrityError`。若未来业务确需恢复，须先物理删除对应软删行（绕过 ORM 的 DB 级操作）或待统一治理修复约束后再加回。

---

## 7. 风险评估（对 557 passed / 0 xfailed 基线，team-lead 2026-08-10 10:20 实测三次确认）

| 任务 | 对现有测试影响 | 说明 |
|---|---|---|
| **T1** | **中**（原评估"极低"，本增量上调；C3' 终裁 (d) 后**较 (a) 稿下降**） | 风险不在测试本身，而在：① `is_latest` default=False → 依赖 `is_latest=True` 过滤的查询会落空；已要求工厂加 `is_latest=True` + audit 同 code 多行测试。② **C3' 采用表达式唯一索引 (d)：SQLite 与 MySQL 行为一致（双库实测均真建、均拦截 `.update()` 旁路）→ 原 (a) 稿"CI 绿证明不了生产"的风险已消除**，功能性用例可在 SQLite 测试库上写且结论可信；但 `supports_expression_indexes` 是软门槛（非 MariaDB / 非 MyISAM / ≥8.0.13），仍保留 MySQL `information_schema.STATISTICS` 真实索引核对以防未来退化（"同仓已有先例"已证伪，见 §8）。③ **(a) 稿遗留的"`bulk_update`/`.update()` 须人工记得同步 `latest_key`"风险随 (d) 一并消除**（无冗余列）；RunPython 回填仍须真实数据验证（见 §6.3）。④ 新增硬约束：is_latest 翻转**必须先降后升**，否则 `IntegrityError`（T2 `:451` 已锁写法）。⑤ `is_latest` 去 `db_index=True` 改复合索引 `idx_process_code_latest`，属纯性能变更，无行为影响。⑥ `current_version` default 改 `'V1.0'`：`add_candidate/conftest.py:24` 显式传 `'1.0'` 不受影响，但须复跑 `add_candidate` 全套。 |
| **T2** | 零 | `bump_version`/`clone` 零测试覆盖（grep 确认）；删 bump-version 端点零前端调用。 |
| **T3** | 零（活实现）/ 低风险（死代码删） | 死代码 `upgrade_application_to_latest_version` 零调用零测试，删除安全；活实现改动落在 application/（工程师批次后），届时需复跑 application 全套。 |
| **T4** | 零 | 同 T2。 |
| **T5** | 低 | `archive_process` 返回值进 `extra`；已 grep 确认无测试断言 `reference_count is False`。 |
| **T6** | 零 | 全库零引用（已实测），删除后 `manage.py check`+全量须仍绿。 |
| **T7** | 零 | 新增纯函数 + 新测试，不影响存量。 |
| **T8** | 零 | 新增端点（零存量测试）；ActionType 加值无 migration。 |
| **T9** | 低 | 新增端点 + service；须确认无 Demand/Position 测试断言 `process_id` 不变——升级逻辑只在新端点触发，不影响存量创建路径。 |
| **T10** | 零 | 只读 management command，不触测试。 |

**红线（不可退让）**：
1. 全量 `pytest --ds=config.settings.test` 必须满足**双向守卫**：`passed >= 557` **且** `failed == 0` **且** `errors == 0`。
   「不得低于 557」是防回归掉测试，「不得靠新增 xfail/skip 达标」是防放水——二者缺一即为假绿。
2. 当前基线 **xfailed == 0 / skipped 以 CI 现值为准**。本批次**不得新增任何 xfail 或 skip**；
   确有必要时须在交付报告中逐条列出（测试 nodeid + 原因 + 解除条件 + 负责人），未列出的一律判不通过。
   （原「8 条 xfail 锁定」台账已失效：实测 xfailed=0，该台账是陈旧记录。）
3. `manage.py check` 零 error。
4. migration 必须可逆（`migrate process <prev>` 能回滚；§6.3 `reverse` 已实现）——**例外**：`current_version` 规范化（`'1.0'`→`'V1.0'`）为单向，reverse 不回滚版本号，回滚后保持 V 前缀形态，交付报告须注明此不可逆点。
5. **application/ 改动（T3 活实现、T8 ActionType）须待工程师 FSM 批次完成后再合入**，避免文件冲突与基线抖动。

---

## 8. 遗留缺陷（本轮范围外）：RecruitmentStage partial unique 在生产 MySQL 失效

**发现来源**：team-lead 在 dev 真实 MySQL 库运行时内省，核验本增量文档 C3 可行性时连带挖出。与 T1~T11 版本化批次**正交**（作用于 `RecruitmentStage`，非 `RecruitmentProcess`），但属同类型"假绿"缺陷，严重度不低，单列于此。

### 8.1 现象（实证）
- `RecruitmentStage.Meta.constraints` 含两个 partial `UniqueConstraint`：
  - `uniq_only_one_start_stage`：`fields=['is_start'], condition=Q(is_start=True)`
  - `uniq_only_one_end_stage`：`fields=['is_end'], condition=Q(is_end=True)`
- 业务语义 = BR-001「全局仅 1 个起始阶段、1 个结束阶段」。
- MySQL `information_schema.STATISTICS` 实测：上述两索引**均不存在**。Django 在 `supports_partial_indexes=False` 后端**静默跳过** partial index——migrate 不报错、不建索引、不留痕迹。故 BR-001 的"DB 约束终极防线"在生产上是空头支票（与 C3 原案同病）。

### 8.2 根因
`apps/process/models.py` `RecruitmentStage.Meta.constraints` 上方注释**写反了支持关系**：
```
# partial UniqueConstraint: MySQL 8.0.13+ / PostgreSQL 12+ 支持 (SQLite 早期版本会抛 NotSupportedError).
# ... 项目用 MySQL, 部署前确认 ≥ 8.0.13.
```
真实情况：SQLite 支持 partial index、MySQL **任意版本均不支持**（MySQL 8.0.13 引入的是函数索引/降序索引，不是 partial index）。错误注释让所有 reviewer 相信"部署前确认版本号即可"，无人去查真实索引，缺陷潜伏至今。

### 8.3 严重度评级
- **P1（高）**。BR-001 是明确的业务不变量，生产上无任何 DB 层保证；当前依赖 `serializer validate` + `select_for_update` 应用层互斥，并发下有窗口可插入第二个 start/end 阶段。当前数据干净（dev 实测 is_start=1、is_end=1、共 12 阶段），尚未造成污染，但属"随时可能破"的隐患。

### 8.4 是否纳入本批次的建议
- **建议：本批次顺带修，但独立成任务（不塞进 T1~T11）**。
  - 理由 1：根因同源（MySQL 不支持 partial index），修法与 C3' 终裁一致——**改用表达式唯一索引 (d)，不引入任何冗余列**（详见 8.6 修复范本）。**数据窗口还在**：dev 当前 is_start=1、is_end=1、12 阶段，数据干净，现在补真实约束不会炸存量、不需回填订正。
  - 理由 2：修法轻、收益高、与本轮"治理假绿"主题一致，且能一并修正那条写反的注释。
  - 风险：改动 `RecruitmentStage` 属 process 模型，与 T1 同文件（`process/models.py`），须与 T1 同一 migration 或紧邻 migration 合并，避免字段/约束迁移顺序冲突。
- 反对推迟到下一轮：同类缺陷已在本轮暴露两次（RecruitmentStage 先例 + C3 原案），每次都靠 dev 实测才发现，推迟只会让"测的不是生产路径"循环继续。

### 8.6 修复范本（随 C3' 终裁 (d) 改写；原"冗余列范本"作废）

**⚠️ 语义先澄清（读源码确认，此前未明确）**：`RecruitmentStage` 是**全局阶段字典表**（`process/models.py:59-60` 类 docstring：「阶段（阶段库，全局共享）」），`is_start`/`is_end` 是**全表级**标志，不隶属任何流程。BR-001 原文（`process/models.py:63`）：「**is_start/is_end 全局各只允许 1 个**」，`clean()`（`:124-134`）也是全表 `filter(is_start=True)` 无 process 维度。
→ 故约束语义是「**全表至多 1 行 `is_start=True`**」，**不是**"每流程至多一个"。`RecruitmentStage` 表上根本没有 `process` 外键（流程与阶段经 `ProcessStageLink` 多对多关联），"每流程至多一个"在此表上无法表达也不需要。

**(d) 写法（全局单例 → 表达式产出常量哨兵，而非 `code`）**：

```python
from django.db.models import UniqueConstraint, Case, When, Value, IntegerField

class Meta:
    constraints = [
        # BR-001: 全表仅 1 个起始阶段 / 1 个结束阶段。
        # MySQL 任意版本均不支持 partial index（8.0.13 引入的是函数索引，不是 partial index），
        # 原 condition= 写法在 MySQL 被静默跳过；改用表达式唯一索引，MySQL/SQLite 均真实生效。
        UniqueConstraint(
            Case(When(is_start=True, then=Value(1)), default=None, output_field=IntegerField()),
            name='uniq_only_one_start_stage',
            violation_error_message='全局只能有 1 个起始阶段',
        ),
        UniqueConstraint(
            Case(When(is_end=True, then=Value(1)), default=None, output_field=IntegerField()),
            name='uniq_only_one_end_stage',
            violation_error_message='全局只能有 1 个结束阶段',
        ),
    ]
```

- **与 C3' 的差异**：C3' 是"每 code 至多一个"，故表达式产出 `F('code')`（分组键）；此处是"**全表**至多一个"，故表达式产出**常量哨兵 `Value(1)`**——所有 `is_start=True` 的行都产出同一个键值 `1`，第二行即冲突。`output_field=IntegerField()` 必须显式给出（`Case` 的分支类型无法自动推断）。
- **双库实测结论（架构师 2026-08-10，残留 0）**：
  - MySQL 9.6.0：索引真建，`information_schema.STATISTICS` 中 `EXPRESSION = (case when (`is_start` = 1) then 1 else NULL end)`；插入第 2 个 `is_start=True` → `Duplicate entry '1' for key 'uniq_only_one_start_stage'`；**`.update(is_start=True)` 旁路同样被拦截**。
  - SQLite：`CREATE UNIQUE INDEX ... ((CASE WHEN "is_start" THEN 1 ELSE NULL END))` 真建，行为一致。
  - 常量哨兵表达式**未触发** MySQL「函数索引不得为常量表达式」限制——因表达式引用了 `is_start` 列，非常量表达式。
- **迁移可行性**：dev 现状 is_start=1 / is_end=1，数据干净，`AddConstraint` 可直接通过；若某环境存量脏（2 个 start），`AddConstraint` 会**明确报错让 migration 变红**，不静默。
- **旁证（假绿闭环双向证明）**：在 SQLite 测试库上尝试建同名探针索引时报 `index uniq_only_one_start_stage already exists` → 证明该 partial index 在**测试库确实存在**；而 MySQL `STATISTICS` 查无此索引 → 证明**生产不存在**。同一份代码两库两种结果，正是本轮治理的核心病灶。
- **配套**：`clean()`（`:124-134`）的应用层校验**保留**（提供友好错误信息 + 早失败）；同时 Django 的 `UniqueConstraint.validate()` 支持 expressions，`full_clean()` 亦会给出 `violation_error_message`。并**务必修正** `:99-101` 那条写反的注释。

### 8.5 与本批次的接口
- 不阻塞 T1~T11 任何任务；**T1 的 C3' 表达式唯一索引方案 (d) 可直接作为 RecruitmentStage 修复的范本**——但需注意语义差异：C3' 是"每 code 至多一个"（表达式产出 `F('code')`），RecruitmentStage 是"**全表**至多一个"（表达式产出常量哨兵 `Value(1)`）。完整范本见 **§8.6**。
- 若 team-lead 决定纳入，应在 §5 任务清单追加一条独立任务（如 T12），并在 §7 风险评估补一行；并同样适用 §6.3 / T1 回归测试点的「MySQL 真实索引核对」要求。

## 9. 与各方工作边界（重要）

| 归属 | 内容 |
|---|---|
| **本文档（架构增量）** | T1~T10 规格；假实现处置；三条用户决策设计；migration + 回填；风险评估 |
| **工程师（application/ 批次，已在进行）** | views.py 三端点方法名、models.py 补 WITHDRAWN/TIMEOUT transition、删除 `stage_transitions.py`（T6）。本文档 T3 活实现 / T8 ActionType 排在其后 |
| **QA（D 系列）** | 原「8 条 xfail 锁定」台账已失效（实测 xfailed=0）；D 系列仅保留 FSM 缺陷测试。本文档不碰 D 系列 |
| **PM** | Q1~Q5 已裁定并全部生效；用户三条决策为对 PM 两项"下轮做"推荐的推翻（C1 跨线、C2 需求入口） |

---

## 附录 A：证据索引

| 结论 | 证据（file:line） |
|---|---|
| 活端点假实现不改指 process | `application/services/__init__.py:677-682`（只改 `workflow_version`，无 `application.process=`） |
| 死代码正确改指 process | `versioning.py:185` `application.process = target_process` |
| 死代码 V5 from_version 读在赋值后 | `versioning.py:184` 赋值、`194` 读 |
| bump_version 原地改老行 | `versioning.py:71-72` |
| 排序字段是 `order` 非 sequence | `process/models.py:236` `order = PositiveIntegerField`；`unique_together=[('process','stage')]` :250 |
| is_latest 翻转必须先降后升（否则瞬态双 latest 冲突） | `process/models.py` 拟新增 `uniq_one_latest_per_code`（C3' 终裁 (d)：表达式唯一索引）；双库实测「先升后降」抛 IntegrityError |
| MySQL 不支持 partial index、partial 约束静默跳过 | Django `DatabaseFeatures.supports_partial_indexes`：sqlite3=True / mysql=False；`information_schema.STATISTICS` 查 `RecruitmentStage` 两约束均不存在（team-lead dev MySQL 实测） |
| (a) 冗余列方案挡不住 `.update()` 旁路（终裁改 (d) 的决定性证据） | team-lead dev MySQL A/B 临时表实测：`UPDATE ... SET is_latest=1` 未带 `latest_key` → 同 code 出现 2 行 `is_latest=True` 且无报错；(d) 同场景抛 IntegrityError |
| (d) 表达式唯一索引在 MySQL 真实生效 | dev MySQL 9.6.0 实测：`STATISTICS.EXPRESSION = (case when (`is_latest` = 1) then `code` else NULL end)`；ORM create / `.update()` / 原生 SQL 三种旁路均抛 `Duplicate entry` |
| (d) 在 SQLite 测试库同样真建并生效（无假绿） | `config.settings.test` 实测：`supports_expression_indexes=True`；`sqlite_master` 可查该 UNIQUE INDEX；正常路径与 `.update()` 旁路均抛 `UNIQUE constraint failed` |
| Django 表达式索引的 MySQL 版本门槛 | `django/db/backends/mysql/features.py`：`not mariadb and storage_engine != 'MyISAM' and mysql_version >= (8, 0, 13)`；本项目 `(9, 6, 0)` / InnoDB / 非 MariaDB → True |
| 表达式索引不服务普通查询，仍需复合索引 | dev MySQL `EXPLAIN`：仅表达式索引时 `WHERE is_latest=1 AND code='W001'` 为 `Table scan`；加 `(code,is_latest)` 后为 `Covering index lookup` |
| `.update()` 旁路风险面（(a) 的自律缺口） | 全仓非 test / 非 migration 的 `QuerySet.update()` 共 **18 处**；`process/migrations/0002_stage_start_end.py:9-10` 即 `.update(is_start=True)`，历史先例坐实 |
| RecruitmentStage is_start/is_end 是**全表**单例而非每流程 | `process/models.py:59-60` 类 docstring「阶段库，全局共享」；`:63` BR-001「全局各只允许 1 个」；`:124-134` `clean()` 全表 filter，无 process 维度；该表无 process FK |
| AutomationRule.stage/next_stage FK→RecruitmentStage | `automation/models.py:54,73` |
| Application.workflow_version 冻结 | `application/models.py:53` |
| Application.current_link/current_stage FK | `application/models.py:56,60` |
| UPGRADE_VERSION 审计动作 | `application/models.py:219` |
| Demand/Position.process/process_version | `demand/models.py:48,52`；`position/models.py:58,62` |
| upgrade-version 端点零测试覆盖 | grep `upgrade-version` 仅 `application/views.py:381` 定义，无测试引用 |
| 前端零调用 bump-version/clone/versions | 原规格 §2.1 已实测 |

## 附录 B：对上一轮回报的路径勘误

上轮回报误将 `stage_transitions.py` 写作 `apps/process/services/stage_transitions.py`。全仓仅一个该文件，位于 `apps/application/services/stage_transitions.py`（全库零 importer 死代码，将由工程师按 T6 删除）。本增量文档不再引用它。

## 附录 C：全仓同类隐患清单（软删占位，team-lead 2026-08-10 全仓扫描实测）

软删模型上「不认 `deleted_at`」的硬唯一约束共 **19 处**，散落 11 个 app。已产生实际占位 3 处：
- `ProcessStageLink(process,stage)` 17/33
- `DynamicField(resource,field_key)` 5/7
- `RecruitmentProcess.code` 1（W007）

**高危潜伏（表当前 0 行，键值天然复用，上线即爆）**：`Offer.application`（offer 撤销后无法重发）、`Onboarding.offer`、`TalentPoolTag.name`、`InterviewEvaluation(interview,interviewer)`、`RecruitmentStage.name`、`User.employee_id`。

**低危**：各表纯流水号 `code`。

**判据（写死）**：风险 = 约束缺陷 × 键值复用概率，与当前行数无关；**0 行不是安全，是尚未开始**。

**病根可追溯**：早在 `dynamic_field/views.py:122-123` 的注释里被准确诊断过（原文「软删记录仍然占着 unique_together 的坑位 (DB 约束不认 deleted_at)」），但修复只落在单模块 view 层、未抽公共机制也未扫其余 18 处 → 本清单即为该缺口的正式登记。

**处置**：本清单**范围外、不在本批次修**，仅登记为独立治理项（与 §6.5 / §8 同源）。

---

**附：工程教训（隔离台账必须配双向守卫）**：xfail / skip / deselect 类隔离台账必须配**双向守卫**——既防新增，也防陈旧。本项目已第二次踩此坑：前一次是 `add_candidate` 的 6 条 deselect 早已自愈却仍在跳过；本轮 `518 passed / 8 xfailed` 基线数字双错（实测 `557 passed / 0 xfailed`，回归掉 39 个测试仍判通过）。台账不配双向守卫即等于没有台账。

## 附录 D：主理人核验补丁 —— §4.2 G2「无需 migration」断言证伪（team-lead 2026-08-10 实测）

**架构师原文（§4.2 G2）**：

> `Demand/Position.process_version` 的 `default` 由 `'1.0'` 改 `'V1.0'`（**仅影响新行，无需 migration**）

**该断言为假。** `default` 参与 `Field.deconstruct()`，autodetector 必然产出 `AlterField`。实测（改 default → 跑真实命令 → `git checkout` 还原，工作树已复原）：

```
$ python manage.py makemigrations --check --dry-run --settings=config.settings.test
Migrations for 'demand':
  apps/demand/migrations/0002_alter_demand_process_version.py
    ~ Alter field process_version on demand
Migrations for 'position':
  apps/position/migrations/0002_alter_position_process_version.py
    ~ Alter field process_version on position
```

**T9 migration 清单（以此为准，跨 2 个 app、共 2 个文件）**：

| app | 操作 |
|---|---|
| `position` | `AddField(Position.demand, FK→Demand, null=True, on_delete=SET_NULL, related_name='positions')` + `AlterField(process_version default='V1.0')`（同 app 两操作合并进同一 migration 文件） |
| `demand` | `AlterField(process_version default='V1.0')` |

**配套基线（已验证，供实现者放心生成 migration）**：项目当前 migration 状态**干净**——`makemigrations --check` 在 `config.settings.test` 与 `config.settings.dev` 两个 settings 下均返回 `No changes detected`（退出码 0）。故上述新增为纯增量，不会裹挟任何历史漂移。

**方法论留痕（主理人自我纠正）**：核验此条时曾手写脚本直调 `MigrationAutodetector(loader.project_state(), ProjectState.from_apps(apps), ...)`，输出一屏假阳性（含 `analytics: DeleteModel DataSubscription` 及数十条第三方 app 的 `AlterField`），据此一度误判"项目 migration 严重漂移"。官方命令全部证伪。**结论：判定 migration 漂移只认 `manage.py makemigrations --check`，不得手写 API 复现其逻辑**——框架命令内部的 loader/questioner/trim 构造细节无法手工等价复现，手写版几乎必然多报或少报。

**顺带登记的技术债（非本批次处理）**：`apps/analytics/models_data.py` 定义 stub 模型 `DataSubscription`，但 `analytics/models.py` **未 import 它**，仅 `analytics/serializers.py` 有 `from .models_data import DataSubscription`。该模型是否注册进 app registry 取决于 serializers 的加载时机，属**加载顺序依赖的幽灵模型**。官方命令下当前未报异常，但结构脆弱，登记为独立治理项。
