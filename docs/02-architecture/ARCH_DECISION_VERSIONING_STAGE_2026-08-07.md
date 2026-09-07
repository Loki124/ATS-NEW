# 架构决策与修复规格：流程版本化 + 申请阶段流转

- **文档编号**：ARCH-2026-08-07-01
- **作者**：高见远（架构师 / software-architect）
- **日期**：2026-08-07
- **范围**：`apps/django/apps/process/services/versioning.py`、`apps/django/apps/application/services/stage_transitions.py`
- **基线**：本文档撰写时全量 `518 passed / 8 xfailed / 0 failed`（QA 已新增 D1/D2/D3 xfail 锁定，见 §6.1）
- **本文档未修改任何源码，未 commit**

---

## 0. 执行摘要（TL;DR）

| # | 结论 |
|---|------|
| 1 | **`stage_transitions.py` 是 100% 死代码**——全库零 importer（实测）。S1~S8 八条隐患全部位于该死模块内。本轮处置：**整体删除该文件**，而不是逐条修复。 |
| 2 | **但 S1 的同类缺陷存在于活代码里**：`services/__init__.py:606 / :716` 两处裸赋值 `application.state = ...`，其中 `:716` 由 Celery 任务 `tasks.py:227` 真实调用。此事已被 QA 以 D1/D2/D3 xfail 锁定，**由 FSM transition 补齐方案统一解决**，本文档只做架构裁定不重复出规格。 |
| 3 | **V1 决策：采用方案 A 的强化版「A+」**——`code` 去 unique，改为「同一 `code` 承载多版本行」，并新增 `version_seq`(int) + `is_latest`(bool) 两个字段与 3 条 DB 约束。理由与被否方案代价见 §2。 |
| 4 | A+ 方案**一次性消灭 V1 / V3 / V4 / V9 四条**（版本号不再靠字符串解析产生与排序）。 |
| 5 | 15 条中：**本轮修 9 条**（V1 V2 V3 V4 V5 V6 V7 V8 V9 + 删除 S1~S8 所在文件），**不修 6 条**（S2~S8 随文件删除而消失，不单独修）。工程师静态推断中**有 3 处判断有误**，已在 §3 逐条指出。 |
| 6 | 「31 处 `refresh_from_db` 是 FSM 地雷」传闻**彻底证伪**：剩余 2 处业务代码（`talent_pool/services.py:186`、`talent_pool/views.py:66`）作用于 `TalentPoolEntry`，该模型**根本没有 FSMField**（实测）。零风险，**不修**。 |
| 7 | `Application` **应当**混入 `FSMModelMixin`（实测当前 MRO 无该 mixin），但**不是**因为 `refresh_from_db`（Application 没有 refresh 调用点），而是为了与 `Candidate` 保持一致、防止未来引入同类缺陷。判为 **P2 / 下轮修**。 |

---

## 1. 事实核查方法与证据基础

所有结论均基于以下三类证据，**不接受纯静态推断**：

1. **源码定位**（file:line）
2. **运行时探针**：pytest + `--ds=config.settings.test`，探针文件跑完即删（`tests/test_arch_probe_tmp.py`、`tests/test_arch_probe2_tmp.py`，已删除）
3. **数据库实测**：`apps/django/dev_db.sqlite3` 现存数据抽样

### 1.1 关键探针输出存档

```
--- P1: ApplicationService 属性面 ---
  hasattr(ApplicationService, 'withdraw_application') = False
  hasattr(ApplicationService, 'pause_application')    = False
  hasattr(ApplicationService, 'resume_application')   = False
  hasattr(ApplicationService, 'withdraw')             = True
  hasattr(ApplicationService, 'pause')                = True
  hasattr(ApplicationService, 'resume')               = True

--- P2: bump_version 解析分支 ---
  cur='1.0'          -> '1.0+1'            ← 模型 default 走这里
  cur='V1.0'         -> 'V1.1'             ← 主创建 API 走这里（V 分支可达！）
  cur='V2.3'         -> 'V2.4'
  cur='V1.0-beta'    -> RAISE ValueError: invalid literal for int() with base 10: '0-beta'
  cur=''             -> 'V1.1'
  cur=None           -> 'V1.1'
  cur='V10.9'        -> 'V10.10'
  cur='V1.abc'       -> RAISE ValueError

--- P3: 字典序排序 ---
  sorted(['V1.0','V2.0','V10.0','V1.10','V1.2'])
    = ['V1.0', 'V1.10', 'V1.2', 'V10.0', 'V2.0']    ← V10.0 排在 V2.0 前面

--- P4: FSMField protected 直接赋值 ---
  未持久化新实例赋值: RAISE AttributeError: Direct state modification is not allowed
  已载入实例赋值:     RAISE AttributeError: Direct state modification is not allowed
  Application transition targets = ['ACTIVE','OFFER_ACCEPTED','OFFER_SENT','ONBOARDED','PAUSED','REJECTED']
    → 不含 TIMEOUT / WITHDRAWN

--- P5: Application MRO ---
  ['Application','FullAuditModel','TimestampedModel','SoftDeleteModel','Model','AltersData','object']
  has FSMModelMixin: False

--- P6: RecruitmentProcess 字段元数据 ---
  code.unique = True   max_length = 20
  current_version.default = '1.0'   max_length = 20
  Meta.constraints = []   Meta.unique_together = ()

--- P7: talent_pool refresh_from_db 现场 ---
  L186: entry.refresh_from_db()   （TalentPoolEntry，无 FSMField）

--- V3: '1.0+1+1...' 撑爆 max_length=20 的实际次数 ---
  第8次 -> '1.0+1+1+1+1+1+1+1+1'   len=19
  第9次 -> '1.0+1+1+1+1+1+1+1+1+1' len=21  ⚠超20   ← 第 9 次，不是「约第 7 次」

--- V7: archive_process 返回值类型 ---
  首次归档(正常分支) reference_count=0     type=int    keys=['archived','archived_at','reference_count']
  重复归档(早退分支) reference_count=False type=bool   keys=['archived','reference_count']

--- V8: list_process_versions 软删过滤 ---
  软删该流程后仍返回 1 条

--- V6: ProcessStageLink 反向关系 ---
  stage_rule            -> StageRule              ← clone 复制了
  entry_condition_rules -> EntryConditionRule     ← clone 漏了
  time_limit_rules      -> TimeLimitRule          ← clone 漏了
  application_records   -> ApplicationStageRecord （不应复制）

--- S5: atomic 内吞异常是否触发 TransactionManagementError ---
  TransitionNotAllowed 被吞后仍可正常查询并提交 → 结果 'ok'
  原始 DB OperationalError 被吞后仍可查询      → 结果 'ok'（SQLite）
```

### 1.2 死代码实测

```bash
$ grep -rn "stage_transitions" --include="*.py" . | grep -v "/.venv/"
（无输出，exit 1）
```

全库**零处**引用 `apps/application/services/stage_transitions.py`。真实生效的实现在
`apps/application/services/__init__.py`：

| 死模块函数 | 活代码等价物 | 调用方 |
|---|---|---|
| `advance_application_to_next_stage` (:23) | `ApplicationService.advance_application_to_next_stage` (`__init__.py:254`) | `views.py:183`、`automation/services.py:320` |
| `jump_application_to_stage` (:148) | `ApplicationService.jump_application_to_stage` (`__init__.py:442`) | `views.py:270`、`automation/services.py:359` |
| `pause_application` (:222) | `ApplicationService.pause` (`__init__.py:~630`) | `views.py:352`（**方法名写错，见 §6.1**） |
| `resume_application` (:235) | `ApplicationService.resume` (`__init__.py:652`) | `views.py:368`（**方法名写错**） |
| `timeout_application` (:248) | `ApplicationService.archive_timeout` (`__init__.py:696`) | `tasks.py:227`（Celery） |

「长期 0% 覆盖」的真实原因不是"没写测试"，而是**这个模块从来没被 import 过**。

### 1.3 dev 库现状（迁移风险基础）

```
recruitment_processes: 共 3 行
  code='main'      version='1.0'  status='draft'
  code='t3'        version='1.0'  status='draft'
  code='test_flow' version='1.0'  status='draft'
```

- 3 行，code 互不相同 → 任何 `(code, *)` 组合唯一性天然成立
- `status='draft'` 不在 `STATUS_CHOICES`（`ENABLED`/`ARCHIVED`）内，是 Prisma 时代遗留脏数据（**附带发现，另案**）

---

## 2. V1 决策：`RecruitmentProcess.code` 的业务语义

### 2.1 必答问题 1：`code` 有没有被当外部唯一标识引用？

**结论：没有。`code` 是纯展示型编号，不承担任何标识职责。**

| 检查面 | 实测结果 | 证据 |
|---|---|---|
| 数据库外键 | **0 处**。7 个反向关系全部 FK 到 PK `id`(nanoid21) | `RecruitmentProcess._meta.related_objects` 运行时枚举：`stage_links`/`candidate_screens`/`candidate_recommendations`/`automation_rules`/`applications`/`demands`/`positions` |
| 跨 app `to_field='code'` | **0 处** | `grep -rn "RecruitmentProcess" ... \| grep ForeignKey` 全部无 `to_field` |
| 后端按 code 查询 | **仅 1 处**：`list_process_versions` `filter(code=...)` | `versioning.py:152` |
| 后端其它 code 用法 | 全是**只读展示/日志/错误文案** | `application/services/__init__.py:113,136,184`、`process/views.py:178`、`models.py:208 __str__` |
| DRF 路由 lookup | 用 `pk`（`id`），不是 `code` | `ProcessViewSet` 无 `lookup_field` 覆盖 |
| 前端路由 | 全部用 `processId`（= `id`） | `web/app/src/api/recruitment-process.ts:85/106/128/160/223/232/244/261/336` 全为 `processId` |
| 前端 code 用途 | 仅类型声明中的展示字段（`code: string`），**零处**用于路由/查找 | `grep "process.code\|processCode"` on `web/app/src` → 无匹配 |
| 前端调用 clone/versions/bump | **零调用**（三个端点前端从未使用） | `grep "clone-version\|/versions\|bump-version"` on `web/app/src` → 无匹配 |
| 导入导出 | 未发现以 code 为键的导入导出 | — |
| code 生成器 | `serializers.py:484` `order_by('-code').first()` + 1；`load_process_templates.py:239` `count()` + 1 | 见 §2.5 风险 |

### 2.2 必答问题 2：`code` 的真实业务语义是什么？

**代码自身给出了 4 条互相印证的证据，指向「`code` = 一条流程线的编号，跨版本共享」：**

1. **克隆代码的自述**：`versioning.py:99` — `code=process.code,  # 编号不变，新版本是同一流程`
2. **查询接口的形状**：`list_process_versions(process_code)` 用 `filter(code=...)` 且返回 `List[dict]`。若 code 全局唯一，这个函数在语义上恒返回 0 或 1 条，配套的 `GET /processes/{id}/versions/` 端点（`views.py:285`）就是纯废设计。**函数签名本身就是「一个 code 对应多行」的设计声明。**
3. **业务规则的结构性要求**：
   - BR-103「历史版本只读」+ BR-104「历史候选人升版本到最新版本」→ **新旧版本必须同时以行的形式存在**（升版本要把 `application.process` 从旧行改指到新行）
   - BR-102「已在跑的候选人走创建时的版本」+ `Application.process` 是 `on_delete=PROTECT` 的 FK → **旧版本行必须永久保留**，不能被覆盖或删除
   - 综合：一条流程线在生命周期里必然产生 N 行，这 N 行需要一个共同标识 → 只能是 `code`
4. **编号格式**：`help_text='W+三位流水号'`，`max_length=20`。流水号是"给人看的业务编号"，天然属于"这条流程"而非"这一行记录"（行标识已经有 nanoid `id` 了）。

**反向验证**：如果 `code` 真的是行标识，那么 `id`(nanoid) 和 `code` 就是两个完全冗余的唯一键，而 `list_process_versions` 是纯死设计。这种解释需要同时假设三处代码都写错，成本更高。

**因此：`unique=True` 是错的一方**（`models.py:172`）。这与主理人的初判一致，但本结论独立成立于上述 4 条证据，而非采信初判。

### 2.3 方案评估

#### 方案 B（clone 生成派生 code，如 `W001-V2`）—— **否决**

| 代价 | 说明 |
|---|---|
| versions 端点实质失效 | `filter(code=...)` 恒返回 1 条。必须改成 `code__startswith='W001'`，而前缀匹配在 `W001` vs `W0011` 上会误命中，本质不可靠 |
| 需要引入 `root_code` 才能修正前缀匹配 | 一旦加了 `root_code`，就是**用两个字段重新发明了方案 A**，还多背一个畸形的对外编号 |
| `max_length=20` 吃紧 | `W001-V2` 尚可，`W001-V10.10` 已接近上限，第 N 次克隆有溢出风险 |
| 人机界面退化 | 用户看到的"流程编号"从 `W001` 变成 `W001-V2/W001-V3`，编号不再稳定，报表、口头沟通、工单引用全部受影响 |
| 不解决根问题 | BR-104 升版本时仍需回答"哪些行属于同一条流程"，方案 B 只是把这个问题从 DB 约束挪到字符串约定上 |

#### 方案 A（`code` 去 unique + `unique_together('code','current_version')`）—— **方向正确但不完整**

**优点**：与代码既有设计意图完全吻合，改动面最小，迁移零风险。

**未覆盖的 3 个缺口**（这也是我不直接采纳 A 的原因）：

| 缺口 | 后果 |
|---|---|
| **"哪一行是当前版本"无法表达** | `GET /processes/` 列表会把 W001 的 3 个版本全部平铺展示；`Demand`/`Position` 新建时不知道该挂哪一行。约束 `(code, current_version)` 不产生"当前行"的概念 |
| **`current_version` 是字符串，不能排序** | 实测 `sorted(['V1.0','V2.0','V10.0']) == ['V1.0','V10.0','V2.0']`（P3）。用它做唯一键的一半，等于把一个排序不可靠的字段抬成主键成分 |
| **版本号仍靠字符串解析生成** | V3/V4 两条缺陷（`'1.0+1+1+1'`、`int('0-beta')` ValueError）的根因是"从旧字符串解析出新字符串"。不改这个机制，V3/V4 只能各打一个补丁 |

#### 方案 A+（**选定**）：`code` 去 unique + `version_seq`(int) + `is_latest`(bool) + 3 条约束

```python
class RecruitmentProcess(FullAuditModel):
    code = models.CharField(max_length=20, verbose_name='流程编号')          # 去掉 unique=True
    current_version = models.CharField(max_length=20, default='V1.0')        # 展示用，default 统一为 'V1.0'
    version_seq = models.PositiveIntegerField(default=1, db_index=True)      # 新增：版本序号，唯一权威来源
    is_latest = models.BooleanField(default=True, db_index=True)             # 新增：是否当前版本

    class Meta:
        constraints = [
            # 同一 code 下版本序号不可重复
            models.UniqueConstraint(fields=['code', 'version_seq'],
                                    name='uniq_process_code_version_seq'),
            # 同一 code 下版本展示串不可重复（防手工传入重复 current_version）
            models.UniqueConstraint(fields=['code', 'current_version'],
                                    name='uniq_process_code_current_version'),
            # 同一 code 下有且仅有一个"当前版本"行（partial unique）
            models.UniqueConstraint(fields=['code'], condition=Q(is_latest=True),
                                    name='uniq_process_one_latest_per_code'),
        ]
```

**为什么加这两个字段是划算的（而不是过度设计）：**

| 收益 | 说明 |
|---|---|
| 一次性关掉 4 条缺陷 | **V1**（唯一键冲突）、**V3**（`'1.0+1+1'` 与 max_length 溢出）、**V4**（`int(minor)` ValueError）、**V9**（字典序排序）。版本号改为 `f'V{version_seq}.0'` 从整数派生，**根本不再解析旧字符串**，V3/V4 的失败模式在结构上不存在了 |
| 保住列表端点语义 | `/processes/` 默认 `filter(is_latest=True)` → 对外行为与今天完全一致（今天每个 code 恰好 1 行），前端零改动 |
| DB 级完整性 | partial unique 保证"每个 code 恰有一个当前版本"，不靠应用层自觉。**同仓已有先例**：`RecruitmentStage` 的 `uniq_only_one_start_stage`/`uniq_only_one_end_stage`（`models.py:102-111`）就是 partial UniqueConstraint，且在 SQLite 测试库上跑通——技术可行性已被本项目自身验证 |
| 排序确定性 | `order_by('code', 'version_seq')` 是整数序，V9 的 `'V10.0' < 'V2.0'` 问题消失 |
| 与 `id` 分工清晰 | `id`=行标识（机器用），`code`=流程线标识（人用），`version_seq`=该流程线内的第几版，`is_latest`=当前版本指针。四者语义不重叠 |

**A+ 的额外代价（诚实列出）：**
- 2 个新字段 + 1 个 migration（含数据回填）
- `clone_process_with_new_version` 需要把旧行 `is_latest` 翻成 `False`（同一事务内）
- `/processes/` list queryset 需加 `is_latest=True` 过滤（1 行代码）
- 若未来要"回滚到旧版本"，需要一个显式的 `set_latest(process)` 服务函数（本轮不做）

**降级预案**：若主理人认为 A+ 超出本轮预算，可退回**纯方案 A**，但必须接受：V3/V4 需各自单独打补丁、列表端点会平铺多版本、V9 仍需一个自定义排序 key。我**不推荐**这个退化路径——省下的工作量小于新增的补丁面积。

#### 方案 C（快照表 `ProcessVersionSnapshot`，保留 `code` unique）—— **记录为长期演进方向，本轮否决**

思路：`RecruitmentProcess` 维持"一 code 一行"，历史版本以不可变 JSON 快照另存一张表。

- **优点**：语义上最贴合 BR-103「历史版本只读」，不需要在业务表里堆版本行
- **否决理由**：`Application.process` / `Demand.process` / `Position.process` 都是指向**行**的 FK，且 `ProcessStageLink`→`StageRule`/`EntryConditionRule`/`TimeLimitRule` 是挂在活行上的三层结构。BR-102 要求在跑的申请继续按**创建时的阶段图**执行，快照方案必须在运行期把 JSON 重新水合成阶段图，波及 `application`/`entry_condition`/`time_limit`/`automation` 四个 app 的执行路径。**这是一次架构级重构，不是一次缺陷修复**，不应塞进本轮
- **保留条件**：若未来版本行数量增长到影响列表查询性能，再评估

### 2.4 必答问题 3：迁移风险

**结论：迁移在任何现存数据库上都不会失败。这是可证明的，不是估计。**

| 迁移动作 | 方向 | 风险 |
|---|---|---|
| `code` 去掉 `unique=True` | **放松约束** | **零风险**。放松约束在任何数据集上都不可能冲突 |
| 新增 `version_seq` (default=1) | 加列带默认值 | 零风险 |
| 新增 `is_latest` (default=True) | 加列带默认值 | 零风险 |
| 加 `UniqueConstraint(code, version_seq)` | 收紧约束 | **可证明安全**：迁移前 `code` 是 UNIQUE，所以所有行 code 两两不同 → `(code, 1)` 组合必然两两不同 |
| 加 `UniqueConstraint(code, current_version)` | 收紧约束 | **同上，可证明安全** |
| 加 partial `UniqueConstraint(code) WHERE is_latest` | 收紧约束 | **同上，可证明安全**（每个 code 只有 1 行，回填后每行 is_latest=True，每个 code 恰好 1 个 True） |

> **关键论证**：迁移前置状态 `code UNIQUE` 蕴含 `(code, X) UNIQUE` 对任意 X 成立。因此三条新约束在**任何**符合旧 schema 的数据库上都成立，不存在"某个环境有脏数据导致迁移失败"的可能。

**dev 库实测佐证**：3 行、code 互异、version 全为 `'1.0'` → 全部约束成立。

**平台兼容性**：
- partial UniqueConstraint 需要 MySQL ≥ 8.0.13 / PostgreSQL ≥ 12 / SQLite ≥ 3.8。
- 本项目**已在生产模型上使用该特性**（`RecruitmentStage.uniq_only_one_start_stage`，`models.py:102`），且 `models.py:99-101` 的注释已显式记录了"部署前确认 MySQL ≥ 8.0.13"这一前置条件。**不引入新的平台要求。**

**唯一真实风险点（必须一并处理）**：
`load_process_templates.py:239` 的 `_next_process_code()` 用 `RecruitmentProcess.objects.filter(code__startswith='W').count() + 1` 生成编号。**去 unique 后，同一 code 的多个版本行会把 count 撑大**，导致新流程跳号甚至撞号（撞号在去 unique 后不再报错，会静默产生两条同 code 不同流程线的行 —— 这是数据污染）。必须改为与 `serializers.py:484` 一致的 `order_by('-code').first()` 取最大值方式，**并加 `.values('code').distinct()`**。见 §4.1-T1。

### 2.5 附带发现（不在 15 条内，供主理人决定是否立项）

| # | 位置 | 问题 |
|---|---|---|
| X1 | `serializers.py:490` vs `models.py:174` vs `load_process_templates.py:127` vs `template_apply.py:49` | `current_version` 初值**四处不一致**：主创建 API 给 `'V1.0'`，模型 default 给 `'1.0'`，模板加载器给 `'1.0'`，模板应用给 `'V1.0'`。这正是 V3 表现分裂的根因（见 §3-V3） |
| X2 | `versioning.py:114` `process.stage_links.all()` | clone 未过滤 `deleted_at__isnull=True`，会把软删的 link 一并克隆进新版本 |
| X3 | `models.py:212` `reference_count = self.demands.count()` | 未过滤 `deleted_at__isnull=True`，而同文件 `is_process_referenced`（`versioning.py:25`）过滤了。同一语义两套口径 |
| X4 | `versioning.py` clone 未复制 `automation_rules` | `AutomationRule.process` 是 CASCADE FK；克隆新版本后自动化规则全丢。是否应复制**需产品确认**（见 §5.2-Q3） |
| X5 | `dev_db.sqlite3` 中 `status='draft'` | 不在 `STATUS_CHOICES` (`ENABLED`/`ARCHIVED`) 内，Prisma 时代遗留脏数据 |

---

## 3. 15 条隐患逐条裁定

**证实等级说明**：
- `实测` = 本次运行时探针或 DB 查询直接观测到
- `静态-确认` = 我复核源码后确认逻辑成立（无需运行即可确定）
- `静态-证伪` = 工程师推断有误，已给出反证
- `静态-修正` = 现象存在但描述不准确，已修正

### 3.1 versioning.py

| 编号 | 文件:行号 | 严重级 | 是否证实 | 建议处置 |
|---|---|---|---|---|
| **V1** | `versioning.py:98-99` ↔ `process/models.py:172` | **P0** | **实测**（主理人探针 `IntegrityError: UNIQUE constraint failed: recruitment_processes.code`） | **本轮修** — 采用方案 A+，见 §4.1-T1/T2 |
| **V2** | `versioning.py:71-72` | **P0 数据损坏** | **实测**（主理人探针：老流程 DB 中 `current_version` 从 `1.0` 被原地改成 `1.0+1+1+1`） | **本轮修** — `bump_version` 拆分为「计算」与「落库」两个职责，clone 路径不得改写老行，见 §4.1-T2 |
| **V3** | `versioning.py:62-69` | **P1** | **实测 + 静态-修正** | **本轮修** — 见下方修正说明 |
| **V4** | `versioning.py:67` `int(minor)` | **P1** | **实测**（`'V1.0-beta'` → `ValueError: invalid literal for int() with base 10: '0-beta'`） | **本轮修** — A+ 后不再解析字符串，缺陷在结构上消失；另加防御性兜底 |
| **V5** | `versioning.py:184/194` | **P1** | **静态-确认** | **本轮修** — 见 §4.1-T3 |
| **V6** | `versioning.py:113-142` | **P1** | **实测**（反向关系枚举证明漏了 `entry_condition_rules` / `time_limit_rules`） | **本轮修** — 见 §4.1-T4 |
| **V7** | `versioning.py:36` vs `:46` | **P2** | **实测**（早退分支 `False`/bool，正常分支 `0`/int，且 key 集合不同） | **本轮修**（顺手，改动 1 行） |
| **V8** | `versioning.py:152`、`models.py:212`、`versioning.py:114` | **P2** | **实测**（软删流程仍被 `list_process_versions` 返回） | **本轮修**（顺手） |
| **V9** | `versioning.py:152,160` | **P3** | **实测**（`sorted` 输出 `['V1.0','V1.10','V1.2','V10.0','V2.0']`；`reference_count` 逐行触发 COUNT → N+1） | **本轮修** — 排序改 `version_seq`（A+ 顺带解决）；N+1 用 `annotate(Count)` |

#### V3 修正说明（**工程师 + 主理人转述均有误，必须纠正**）

> 原描述：「`current_version` 的 `default='1.0'`（不带 V 前缀），**永远走不到** `V{n}.{m+1}` 分支」

**这个"永远"是错的。实测（P2）：**

```
cur='1.0'   -> '1.0+1'    ← 走 else 分支
cur='V1.0'  -> 'V1.1'     ← 走 V 分支，可达
```

真实情况是**初值来源分裂**（附带发现 X1）：

| 创建路径 | 写入的 `current_version` | bump 后 |
|---|---|---|
| `POST /api/v1/processes/`（主创建 API，`serializers.py:490`） | `'V1.0'` | `'V1.1'` ✅ V 分支 |
| `apply_template()`（`template_apply.py:49`） | `'V1.0'` | `'V1.1'` ✅ V 分支 |
| 直接 `RecruitmentProcess.objects.create()`（模型 default，`models.py:174`） | `'1.0'` | `'1.0+1'` ❌ else 分支 |
| `load_process_templates` 命令（`:127`） | `'1.0'` | `'1.0+1'` ❌ else 分支 |
| `clone_process_with_new_version`（`versioning.py:101`） | 继承上游 | 继承上游 |

**所以 V3 是两个独立缺陷，不是一个：**

- **V3-a**：`'1.0+1+1+...'` 累积（走 else 的两条路径）。**溢出发生在第 9 次 bump**（len=21 > max_length=20），不是工程师说的"约第 7 次"。第 8 次 len=19 仍安全。
- **V3-b**：走 V 分支时，docstring 声称 `V{N+1}.0`（升主版本），实际产出 `V{N}.{M+1}`（升次版本）。**这一条工程师说对了。**
- **V3-c（新增，工程师未发现）**：初值四处不一致本身就是缺陷。同一个系统里两种版本号格式共存，会让 `Application.workflow_version`（`'V1.0'` 或 `'1.0'`）、`Position.process_version`（default `'1.0'`）、`Demand.process_version`（default `'1.0'`）之间的字符串比较不可靠。`ApplicationService.upgrade_workflow_version` 就用 `new_version == application.workflow_version` 做相等判断（`services/__init__.py:677`）——格式不一致会导致该判断误判。

#### V5 复核（工程师判断**正确**，补充一处他未发现的）

`versioning.py:183-196`：

```python
application.workflow_version = target_process.current_version   # ← 184 先覆盖
application.process = target_process
application.save(...)
return {
    'upgraded': True,
    'from_version': application.workflow_version,               # ← 194 读的是已被覆盖的值
    'to_version': target_process.current_version,
}
```

`from_version` 恒等于 `to_version`。**确认。**

**工程师未发现的补充点**：该函数**完全没有 `ApplicationHistory` 写入**，而 `ActionType.UPGRADE_VERSION`（`application/models.py:219`）这个枚举值在全库**只有活代码 `services/__init__.py:684` 一处使用**——即死模块这条路径确实零审计。另外，`from_version` 应该来自 `application.workflow_version` 的**旧值**，但语义上更准确的应是**旧 process 的版本**（因为 `workflow_version` 是冻结值，可能与旧 process 的 `current_version` 不同步）。这一点属产品语义，见 §5.2-Q4。

#### V6 复核（工程师判断**正确**，范围需扩大）

实测 `ProcessStageLink` 的反向关系共 4 个，clone 只处理了 1 个：

| 反向关系 | clone 是否复制 | 应否复制 |
|---|---|---|
| `stage_rule` → `StageRule` | ✅ 已复制 | 应复制 |
| `entry_condition_rules` → `EntryConditionRule`（含二级 `items` → `ConditionItem`） | ❌ **漏** | **应复制（含二级）** |
| `time_limit_rules` → `TimeLimitRule` | ❌ **漏** | **应复制** |
| `application_records` → `ApplicationStageRecord` | ❌ 未复制 | **不应复制**（属运行时数据） |

"悬空表达式"确认：`versioning.py:120` 原样拷贝 `entry_rule_expression`（形如 `(1 AND 2) OR 3`，引用的是 `entry_condition_rules` 的序号），但目标 link 下一条 `EntryConditionRule` 都没有 → 表达式引用空集。同时 `serializers.py:275-288` 显示该字段还可能承载 JSON-encode 的结构化 `entry_condition` —— 两种载荷共用一个字段，克隆时都需要处理。

`RecruitmentProcess` 层面还漏了 `automation_rules`（见 X4，需产品确认）。

### 3.2 stage_transitions.py — **整体处置：删除文件**

> **架构裁定**：该文件全库零引用（§1.2 实测），其 5 个函数在 `services/__init__.py` 中均有正在生效的等价实现，且活实现在多个方面**明显更完善**（有状态校验、有 duration 计算、有完整审计、有软拒联动）。
>
> 逐条修 8 个缺陷会产出一份"修好了但仍然没人调用"的死代码，并制造两套并行实现长期漂移的风险——**这正是它当初被写出来又被遗忘所造成的问题**。
>
> **正确处置是删除整个文件**，并在 CI 里加一条死模块守卫防止复发。

| 编号 | 文件:行号 | 严重级 | 是否证实 | 建议处置 |
|---|---|---|---|---|
| **S1** | `stage_transitions.py:253` | **P0（在死代码中）→ 降为 P3** | **实测**（P4：protected FSMField 裸赋值必抛；P4：transition targets 不含 TIMEOUT） | **不单独修，随文件删除**。⚠️ **但同类缺陷在活代码 `services/__init__.py:606/716` 存在且更严重**，已由 QA D1/D2/D3 锁定，见 §6.1 |
| **S2** | `:148-218` 缺 `select_for_update` | P1 → P3 | **静态-确认**（活实现 `__init__.py:442` 同样没有行锁——**这是活代码的真问题**） | **死码部分随文件删除**；活代码的并发问题另立条目，见 §5.1-N2 |
| **S3** | `:171` 裸调 `evaluate_stage_entry` | P1 → P3 | **静态-确认** | 随文件删除。活实现 `__init__.py:322` 也无 try/except，但它是**故意**抛 `StateTransitionError` 让 view 转 409，语义正确 |
| **S4** | advance/jump 不校验 `application.state` | P2 → P3 | **静态-确认**（死码确实不校验） | 随文件删除。**活实现 `__init__.py:266-269` 有校验**，无问题 |
| **S5** | `:229-230` / `:242-243` atomic 内吞异常 | P2 → **不成立** | **静态-证伪** | **不修。工程师判断有误** — 见下方 |
| **S6** | 不更新 `last_advanced_at` | P3 | **静态-修正** | 随文件删除 — 见下方 |
| **S7** | 审计记录语义混淆 | P3 | **静态-确认** | 随文件删除。活实现同样把 jump 记为 `SKIPPED`，属可接受的语义近似，另案 |
| **S8** | 向后跳转静默失效 | P3 | **静态-修正** | 随文件删除 — 见下方 |

#### S5 证伪（工程师判断**有误**）

> 原推断：「`@transaction.atomic` 内 `except` 后不重抛 → 触发 `TransactionManagementError`」

**实测反证（探针 S5-A / S5-B）：**

```
--- S5-A: TransitionNotAllowed 在 atomic 内被吞后 ---
  内部捕获: TransitionNotAllowed: Can't switch from state 'PENDING' using method 'resume'
  except 后仍可查询, count=0
  结果: ok          ← 事务正常提交，无 TransactionManagementError

--- S5-B: 真 DB OperationalError 在 atomic 内被吞后 ---
  内部捕获: OperationalError
  DB 错误后仍可查询: 未触发 TransactionManagementError
  结果: ok
```

**机理**：`TransactionManagementError: An error occurred in the current transaction. You can't execute queries until the end of the 'atomic' block` 只在 Django 把 `connection.needs_rollback` 置位后才抛。置位发生在**内层 `atomic` 块因异常退出**、或显式 `set_rollback(True)` / `mark_for_rollback_on_error()` 时。

`application.pause()` 抛的 `TransitionNotAllowed` 是**纯 Python 异常，在任何 SQL 发出之前就抛出**，对连接状态零影响。所以 S5 描述的触发链条**根本不存在**。

**但这段代码确实有一个不同的、真实的缺陷**（S5'）：`except Exception` 把**所有**异常（包括真实的 DB 写失败、`IntegrityError`）都翻译成 `{'paused': False, 'reason': 'transition_error: ...'}`，即把"系统故障"伪装成"业务拒绝"，调用方无法区分。这是**过宽捕获**问题，不是事务管理问题。由于位于死代码，随文件删除。

> ⚠️ 这类"机理说得头头是道但实测不成立"的推断，正是要求实测坐实的原因。

#### S6 修正

- **advance**：`:113` 有 `application.last_advanced_at = timezone.now()` 并写入 `update_fields`（`:115`）。**不缺**。
- **jump**：`:200-203` 确实未更新 `last_advanced_at`。**只有 jump 缺**。

工程师说"阶段推进不更新 `last_advanced_at`"，范围说大了。

这个字段是 `tasks.py:220` 的 `archive_stale_applications`（按 `last_advanced_at__lte=cutoff` 筛选长期未推进申请）的筛选依据 —— **jump 不更新它 = 频繁被 jump 推进的申请仍会被误判为"僵尸"并归档**。这在活实现 `__init__.py:442` 中是否也存在，需工程师在做 §5.1-N2 时一并核查（本文档未核到该行，标注**未证实**）。

#### S8 修正

> 原描述：「向后跳转静默失效」

**实际行为**（读 `:180-203`）：目标阶段 `order` 小于当前时，`filter(link__order__gt=current, link__order__lt=target)` 是空区间 → **中间记录不被标 SKIPPED**，但后续的 `ApplicationStageRecord.objects.create(...)` 与 `application.current_link = target_link` **照常执行**。

所以：**跳转本身成功了**，失效的只是"中间阶段清理"。更准确的表述是「**向后跳转时被跳过区间计算方向写死，导致原本应被作废/重置的中间阶段记录保持原状态**」。这比"静默失效"更严重也更隐蔽——用户看到跳转成功，但阶段记录状态是脏的。

### 3.3 额外裁定：`refresh_from_db` / `FSMModelMixin`

| 编号 | 对象 | 结论 | 证据 |
|---|---|---|---|
| R1 | `talent_pool/services.py:186`、`talent_pool/views.py:66` | **零风险，不修** | 两处作用于 `TalentPoolEntry`。实测该模型**无任何 FSMField**（`grep FSMField apps/talent_pool/models.py` 无输出）。`refresh_from_db` 的 FSM 问题只在模型含 protected FSMField 时出现 |
| R2 | `Application` 是否该混入 `FSMModelMixin` | **应该，但判 P2 / 下轮修** | 实测 MRO 无 `FSMModelMixin`（P5）。但全库**没有任何一处对 `Application` 调 `refresh_from_db`**（`grep` 已确认 31 处中 29 处在测试、2 处在 talent_pool），当前**不构成活跃缺陷**。加它的价值是防御性对齐（`Candidate` 已加），不是止血。放在下轮与 §6.1 的 FSM transition 补齐一起做，避免本轮同时改 `Application` 模型的两个方面造成回归面重叠 |

> **传闻处置**：「全库 31 处 `refresh_from_db` 都是 FSM 地雷」——**彻底证伪**。29 处在测试代码，剩余 2 处作用于无 FSMField 的模型。真实风险为 **0 处**。建议主理人在团队内明确撤回该传闻。

### 3.4 裁定汇总

| 处置 | 条目 | 数量 |
|---|---|---|
| **本轮修** | V1, V2, V3, V4, V5, V6, V7, V8, V9 | **9** |
| **本轮修（整体删除文件）** | S1~S8 所在的 `stage_transitions.py` | **1 个文件 / 覆盖 8 条** |
| **不修（已证伪）** | S5（机理不成立）、R1（无 FSMField） | 2 |
| **下轮修** | R2（`Application` 加 `FSMModelMixin`）、N1~N3（§5.1） | 4 |
| **需产品确认** | Q1~Q5（§5.2） | 5 |

---

## 4. 修复规格（供工程师直接执行）

> **总体约束**：本轮**不得**改动 `apps/application/services/__init__.py` 中与 FSM 状态相关的代码（`:305 / :355 / :606 / :716`）——那部分由 QA 的 D1/D2/D3 修复统一处理，两边同时改会造成冲突。见 §6.1。

### 4.1 任务分解与依赖

```
T1 (模型 + migration)  ──┬──> T2 (bump_version + clone)  ──> T4 (clone 补全关联)
                         ├──> T3 (upgrade + 审计)
                         └──> T5 (list_versions + archive 返回值)
T6 (删除 stage_transitions.py + 加守卫)   [独立，无依赖]
```

**建议实施顺序**：T6 → T1 → T2 → T4 → T3 → T5
（T6 先做，因为它零依赖且能立刻把 8 条隐患移出代码库，缩小后续改动的心智负担。）

---

### T1 — 数据模型：`code` 去 unique + 版本序号 + 当前版本标记

**优先级**：P0　**依赖**：无　**需要 migration**：是

#### 文件与行号

| 文件 | 行号 | 动作 |
|---|---|---|
| `apps/django/apps/process/models.py` | `172` | `code` 去掉 `unique=True`，加 `db_index=True` |
| `apps/django/apps/process/models.py` | `174` | `current_version` 的 `default` 从 `'1.0'` 改为 `'V1.0'` |
| `apps/django/apps/process/models.py` | `174` 后 | 新增 `version_seq` / `is_latest` 两字段 |
| `apps/django/apps/process/models.py` | `201-205` (`class Meta`) | 新增 `constraints` 三条 |
| `apps/django/apps/process/models.py` | `210-212` | `reference_count` 补 `deleted_at__isnull=True` 过滤（顺带修 V8/X3） |
| `apps/django/apps/process/migrations/0005_*.py` | 新建 | 见下 |
| `apps/django/apps/process/management/commands/load_process_templates.py` | `239-241` | `_next_process_code` 改 distinct-max 算法（**必改**，见 §2.4） |
| `apps/django/apps/process/management/commands/load_process_templates.py` | `127` | `'current_version': '1.0'` → `'V1.0'` |
| `apps/django/apps/process/serializers.py` | `482-486` | code 自动生成改 distinct-max；**新增显式 code 唯一性校验**（见下） |
| `apps/django/apps/process/views.py` | `220-223` (`get_queryset`) | 加 `is_latest=True` 过滤 |

#### 目标行为

**模型字段**

```python
code            = CharField(max_length=20, db_index=True)        # 不再 unique
current_version = CharField(max_length=20, default='V1.0')       # 展示串，格式统一 V{seq}.{minor}
version_seq     = PositiveIntegerField(default=1, db_index=True) # 同 code 内单调递增，权威版本序
is_latest       = BooleanField(default=True, db_index=True)      # 同 code 内有且仅一个 True
```

**约束**（三条，名称固定以便迁移可回溯）

| 名称 | 定义 |
|---|---|
| `uniq_process_code_version_seq` | `UniqueConstraint(fields=['code','version_seq'])` |
| `uniq_process_code_current_version` | `UniqueConstraint(fields=['code','current_version'])` |
| `uniq_process_one_latest_per_code` | `UniqueConstraint(fields=['code'], condition=Q(is_latest=True))` |

**边界情况处置表**

| 场景 | 目标行为 |
|---|---|
| 已有 3 行 dev 数据（code 互异、version `'1.0'`） | 回填 `version_seq=1, is_latest=True`；`current_version` **保持原值不动**（不要在 migration 里改写业务数据，见下） |
| 现存 `current_version='1.0'`（无 V 前缀）的行 | migration **不改写**。由 T2 的 bump 逻辑在下次 bump 时统一产出 `V{seq}.0` 收敛格式 |
| API 显式传入已存在的 `code` | serializer 必须报 400 `'流程编号 {code} 已存在'`。**去 unique 后 DB 不再兜底，serializer 是唯一防线** |
| API 不传 `code` | 自动生成 `W{n:03d}`，n = `max(distinct code)` + 1 |
| 同一 code 已有 3 个版本，再新建同 code 流程 | 拒绝（400）。新建流程只能用新 code；同 code 的新行只能由 clone 产生 |

**`_next_process_code` / serializer code 生成的正确算法**（两处必须一致）

```
取 RecruitmentProcess.objects.filter(code__regex=r'^W\d{3}$')
      .values_list('code', flat=True).distinct()          # distinct 是关键
最大值的数字部分 + 1，格式化为 W{n:03d}；无匹配则 W001
```
- **必须 `distinct()`**：否则同 code 多版本行会让 count/max 计算失真
- **必须用 regex 而非 `startswith('W')`**：避免手工录入的 `WORKFLOW_X` 之类污染序号计算
- 建议抽成 `apps/process/services/coding.py::next_process_code()` 供两处复用，消除重复实现

#### Migration 要点

```
0005_process_versioning.py
  operations = [
    AlterField(model_name='recruitmentprocess', name='code',
               field=CharField(max_length=20, db_index=True, ...)),         # 去 unique
    AlterField(model_name='recruitmentprocess', name='current_version',
               field=CharField(max_length=20, default='V1.0', ...)),        # 只改 default，不动存量数据
    AddField(... 'version_seq', PositiveIntegerField(default=1, db_index=True)),
    AddField(... 'is_latest',   BooleanField(default=True, db_index=True)),
    # 无需 RunPython 数据回填：AddField 的 default 已把存量行填成 (1, True)，
    # 而迁移前 code UNIQUE 保证每个 code 恰好 1 行 → 三条约束天然成立
    AddConstraint(... uniq_process_code_version_seq),
    AddConstraint(... uniq_process_code_current_version),
    AddConstraint(... uniq_process_one_latest_per_code),
  ]
```

**明确不做的事**：
- ❌ 不在 migration 里把 `'1.0'` 改写成 `'V1.0'`（改写业务数据会让 `Position.process_version` / `Demand.process_version` / `Application.workflow_version` 三张表的冻结快照与流程表脱钩，属数据破坏）
- ❌ 不加 `RunPython` 回填（`AddField` 的 default 已覆盖，多一步就多一份 reverse 风险）
- ✅ 三条 `AddConstraint` 必须放在两条 `AddField` **之后**

#### 配套回归测试点（QA 撰写，此处只描述断言目标）

1. 同一 `code` 可以插入多行（不同 `version_seq`）而不抛 `IntegrityError`
2. 同一 `(code, version_seq)` 重复插入 → 抛 `IntegrityError`
3. 同一 `(code, current_version)` 重复插入 → 抛 `IntegrityError`
4. 同一 `code` 下出现第二个 `is_latest=True` → 抛 `IntegrityError`
5. `POST /api/v1/processes/` 传入已存在 code → 400，且响应含明确文案（不是 500）
6. `POST /api/v1/processes/` 不传 code：在库里已存在 `W001` 的 3 个版本行时，生成的仍是 `W002`（验证 distinct 生效），不是 `W004`
7. `GET /api/v1/processes/` 在同 code 有 3 个版本时只返回 `is_latest=True` 的 1 条
8. `migrate` 在含存量数据的库上正向执行成功；`migrate process 0004` 反向回滚成功
9. `load_process_templates` 命令在已存在多版本行的库上执行，不产生重复 code

---

### T2 — `bump_version` 拆分职责 + `clone` 修复（V1 / V2 / V3 / V4）

**优先级**：P0　**依赖**：T1　**需要 migration**：否

#### 文件与行号

| 文件 | 行号 | 动作 |
|---|---|---|
| `apps/process/services/versioning.py` | `51-74` | `bump_version` 重写 |
| `apps/process/services/versioning.py` | `77-145` | `clone_process_with_new_version` 重写版本与 code 处理 |
| `apps/process/views.py` | `301-311` | `bump_version_action` 语义澄清（见下） |

#### 目标行为

**拆成两个函数，职责分离（这是 V2 的根治手段）：**

```
compute_next_version(process) -> tuple[int, str]        # 纯计算，零副作用
    seq = (同 code 下 max(version_seq) 或 0) + 1
    return seq, f'V{seq}.0'

bump_version(process, new_version=None) -> str          # 显式"就地升级当前流程版本号"
    在 select_for_update 下重算 seq
    只改 process 自身，语义即"这条流程原地升版"
```

**关键：`clone_process_with_new_version` 不得调用 `bump_version`**（这是 V2 的直接原因）。改为调用 `compute_next_version`，老行只翻 `is_latest=False`，`current_version` / `version_seq` **一个字都不许动**（BR-103 历史版本只读）。

**边界情况处置表（V3/V4 的验收口径）**

| 输入 `current_version` | 同 code 下 max(version_seq) | `compute_next_version` 输出 | 说明 |
|---|---|---|---|
| `'1.0'` | 1 | `(2, 'V2.0')` | 旧格式自动收敛到 V 前缀 |
| `'V1.0'` | 1 | `(2, 'V2.0')` | 与 docstring 声明的"升主版本"一致 |
| `'V2.3'` | 2 | `(3, 'V3.0')` | 不再解析 minor |
| `'V1.0-beta'` | 1 | `(2, 'V2.0')` | **不再抛 ValueError**（V4 消失：根本不解析字符串） |
| `''` / `None` | 1 | `(2, 'V2.0')` | 不再依赖 `or 'V1.0'` 兜底 |
| 同 code 下 `version_seq` 最大为 9 | 9 | `(10, 'V10.0')` | `len('V10.0')=5`，距 max_length=20 极远，**溢出风险消失** |
| 显式传 `new_version='V9.9'` | 5 | `version_seq=6`, `current_version='V9.9'` | 允许自定义展示串，但 seq 仍单调（若 `(code,'V9.9')` 已存在则 DB 约束报错，serializer 应转 400） |
| 同 code 无任何行（异常情况） | None | `(1, 'V1.0')` | 兜底 |

**`clone` 的事务内必须完成的 5 件事（顺序固定）**

1. `select_for_update` 锁住同 `code` 的所有行（防并发 clone 产生重复 seq / 双 latest）
2. `compute_next_version(process)` 取 `(seq, version_str)`
3. `RecruitmentProcess.objects.filter(code=process.code, is_latest=True).update(is_latest=False)`
4. 创建新行：`code=process.code`（**保持不变，这是 A+ 的核心**）、`version_seq=seq`、`current_version=version_str`、`is_latest=True`
5. 深拷贝下级配置（T4）

**`bump_version_action` 端点语义澄清**（`views.py:301`）：当前该端点只改版本号不产生新行，与 BR-101「配置修改生成新版本」语义冲突。本轮**保持行为不变**但补 docstring 说明它是"原地改版本号"而非"生成新版本"；是否应废弃改为只保留 `clone-version`，见 §5.2-Q1。

#### 配套回归测试点

1. **V1 红线**：连续 `clone` 同一流程 3 次全部成功，DB 中同 code 出现 4 行，**零 IntegrityError**
2. **V2 红线**：clone 后，**老行**的 `current_version` 与 `version_seq` 与 clone 前逐字节相同（这是 BR-103 的核心断言）
3. clone 后老行 `is_latest=False`、新行 `is_latest=True`，且同 code 下 `is_latest=True` 计数恒为 1
4. **V3-a**：连续 clone 12 次，每次 `current_version` 长度 ≤ 20，且序列为 `V2.0, V3.0, ..., V13.0`
5. **V3-b**：`current_version='V2.3'` 的流程 clone 后得 `V3.0`（升主版本，与 docstring 一致），不是 `V2.4`
6. **V4**：`current_version='V1.0-beta'` / `''` / `'1.0'` 的流程 clone 均不抛 `ValueError`
7. `compute_next_version` 是纯函数：调用 10 次，DB 中该流程行的任何字段都不变
8. 并发 clone（两个线程同时 clone 同一流程）：一个成功一个抛 IntegrityError 或串行成功，**不产生重复 version_seq，不产生双 is_latest**
9. `POST /api/v1/processes/{id}/clone-version/` 返回 201 且 `data.current_version` 为新版本（该端点当前**零测试覆盖**，需从 0 建）

---

### T3 — `upgrade_application_to_latest_version` 修复（V5）

**优先级**：P1　**依赖**：T1　**需要 migration**：否

#### 文件与行号

`apps/process/services/versioning.py:166-196`

#### 目标行为

| 问题 | 修法 |
|---|---|
| `from_version` 恒等于 `to_version` | **在赋值前**先把旧值存入局部变量 `from_version = application.workflow_version`（`:184` 之前） |
| 零 `ApplicationHistory` 写入 | 补写一条 `action=ApplicationHistory.ActionType.UPGRADE_VERSION`，`detail={'from_version':..., 'to_version':..., 'from_process_id':..., 'to_process_id':...}`，`operator=actor` |
| 未校验目标流程合法性 | 新增：`target_process.code != application.process.code` → 抛 `StateTransitionError('不能跨流程线升版本')`（**这是产品语义，见 §5.2-Q2；若产品说允许跨流程线迁移，则改为不校验**） |
| 未校验申请状态 | 终态申请（`ONBOARDED`/`REJECTED`/`WITHDRAWN`/`TIMEOUT`）不应升版本 → 抛 `StateTransitionError` |
| 未校验目标版本方向 | `target_process.version_seq <= application.process.version_seq` → 抛 `StateTransitionError('不能降版本')`（**降版本是否允许，见 §5.2-Q2**） |

**边界情况**

| 场景 | 目标行为 |
|---|---|
| `application.process_id == target_process.id` | 保持现状：返回 `{'upgraded': False, 'reason': 'application already on this process version'}`，**不写 history** |
| 目标流程 `status='ARCHIVED'` | 抛 `StateTransitionError('目标流程已归档')` |
| 目标流程 `is_latest=False`（升到中间版本） | 允许（BR-104 说"升版本"，未强制必须是最新）。**需产品确认，见 Q2** |
| `application.workflow_version` 与 `application.process.current_version` 不一致 | `from_version` 取 `application.workflow_version`（冻结值才是这条申请实际在跑的版本）；同时在 `detail` 里额外记录 `from_process_version` 便于排查 |

#### 配套回归测试点

1. 升版本后返回的 `from_version != to_version`，且 `from_version` 等于升版本**之前**的 `application.workflow_version`
2. 升版本后恰好新增 1 条 `ApplicationHistory`，`action == 'UPGRADE_VERSION'`，`detail` 含 from/to 两个版本
3. 同流程同版本重复调用：返回 `upgraded=False` 且 **history 条数不增加**
4. 跨 code 的目标流程 → 抛 `StateTransitionError`
5. 终态申请（如 `ONBOARDED`）升版本 → 抛 `StateTransitionError`
6. 已归档目标流程 → 抛 `StateTransitionError`
7. 升版本后 `application.process_id` 确实指向新行，且 `workflow_version` 等于新行的 `current_version`

---

### T4 — `clone` 深拷贝补全（V6）

**优先级**：P1　**依赖**：T2　**需要 migration**：否

#### 文件与行号

`apps/process/services/versioning.py:113-142`

#### 目标行为

**每个 `ProcessStageLink` 的拷贝清单**

| 关系 | 动作 |
|---|---|
| `stage_rule` (OneToOne → `StageRule`) | 已有，保留。但需检查是否漏字段（见下） |
| `entry_condition_rules` (FK → `EntryConditionRule`) | **新增拷贝**，并**递归拷贝二级 `items` (`ConditionItem`)** |
| `time_limit_rules` (FK → `TimeLimitRule`) | **新增拷贝** |
| `application_records` | **不拷贝**（运行时数据） |

**`entry_rule_expression` 悬空表达式处置**（`versioning.py:120`）

该字段有两种载荷（`serializers.py:275-288`）：
- **形态 A**：序号表达式 `(1 AND 2) OR 3` → 引用 `entry_condition_rules` 的序号。**只要 T4 把规则按原顺序完整拷贝，序号对应关系自动保持，表达式无需改写**
- **形态 B**：JSON-encode 的结构化 `entry_condition` → 自包含，原样拷贝即可

**结论**：拷贝规则后表达式不再悬空，**不需要改写表达式本身**。但必须保证拷贝时**保持原有顺序**（`order_by('id')` 或原有排序字段），否则序号会错位——这一点必须在实现和测试里显式锁定。

**其它必须一并处理的拷贝缺陷**

| 位置 | 问题 | 修法 |
|---|---|---|
| `versioning.py:114` `process.stage_links.all()` | 未过滤软删（X2） | 改 `.filter(deleted_at__isnull=True).order_by('order')` |
| `versioning.py:125` `if hasattr(link, 'stage_rule')` | `hasattr` 对 OneToOne 反向会吞掉真实异常 | 改用 `getattr(link, 'stage_rule', None)` 或显式 `try/except StageRule.DoesNotExist` |
| `versioning.py:127-142` `StageRule` 字段清单 | 硬编码 17 个字段，而模型有 `auto_advance_type`/`auto_advance_timing`/`auto_advance_days`/`default_handler_type`/`default_handler_fields`/`default_handler_user_ids`/`time_limit`/`time_limit_scope`/`interview_round_ids`/`legacy_*` 等（`models.py:300-353`）**未被拷贝** | **改为字段自省拷贝**：遍历 `StageRule._meta.concrete_fields`，排除 `id`/`link`/`created_at`/`updated_at`/`created_by`/`updated_by`/`deleted_at`，其余全拷（JSONField 走 `deepcopy`）。这样将来加字段不会再漏 |
| `automation_rules` | 未拷贝（X4） | **需产品确认后再定**，见 Q3。本轮**先不做**，但在代码里留 `# TODO(Q3)` 注释 |

> **架构提示**：硬编码字段清单是这个函数的系统性弱点——`StageRule` 在 2026-07-03 扩了 9 个字段（`models.py:319-353` 的注释可证），clone 从未同步。改成自省式拷贝是本任务最有价值的部分，比补 3 个关联更重要。

#### 配套回归测试点

1. clone 一个含 2 个 link、每 link 各 1 条 `StageRule` + 2 条 `EntryConditionRule`（每条 3 个 `ConditionItem`）+ 1 条 `TimeLimitRule` 的流程；断言新流程下三类对象的**数量**与原流程逐一相等
2. **字段级断言**：新 `StageRule` 的**每一个** concrete field（除 id/link/审计字段外）与原对象相等 —— 用 `_meta.concrete_fields` 遍历断言，而不是列举字段名（这样新增字段时测试会自动覆盖）
3. `EntryConditionRule.items` 的顺序与原顺序一致（锁定 `entry_rule_expression` 序号对应关系）
4. 新旧对象的 `id` 互不相同，且新对象的 FK 全部指向**新** link（不能有任何一条指回旧 link）
5. 原流程含 1 个软删 link 时，新流程不包含该 link
6. `StageRule` 中的 JSONField（`processor_order`/`default_handler_fields`/`default_handler_user_ids`/`interview_round_ids`）是深拷贝：修改新对象的该字段，原对象不受影响
7. link 无 `stage_rule` 时 clone 不抛异常

---

### T5 — `list_process_versions` + `archive_process` 返回值（V7 / V8 / V9）

**优先级**：P2　**依赖**：T1　**需要 migration**：否

#### 文件与行号

| 文件 | 行号 | 动作 |
|---|---|---|
| `versioning.py:148-163` | `list_process_versions` | 加软删过滤、改按 `version_seq` 排序、`annotate` 消 N+1、增加 `is_latest`/`version_seq` 字段 |
| `versioning.py:35-48` | `archive_process` | 统一返回值形状 |
| `process/models.py:210-212` | `reference_count` | 补软删过滤 |

#### 目标行为

**`list_process_versions`**

```
filter(code=process_code, deleted_at__isnull=True)
  .annotate(ref_count=Count('demands', filter=Q(demands__deleted_at__isnull=True)))
  .order_by('version_seq')          # 整数序，V9 解决
```
返回字典新增 `'version_seq'` 与 `'is_latest'` 两个键（前端未使用该端点，加字段无破坏性）。

**`archive_process` 返回值统一**（V7）

两个分支必须返回**相同的 key 集合与相同的类型**：

| key | 类型 | 早退分支（已归档） | 正常分支 |
|---|---|---|---|
| `archived` | bool | `True` | `True` |
| `reference_count` | **int** | `process.reference_count` | `process.reference_count` |
| `archived_at` | str \| None | `process.archived_at.isoformat() if ... else None` | `process.archived_at.isoformat()` |

即：把 `:36` 的 `is_process_referenced(process)`（返回 bool）改成 `process.reference_count`（返回 int），并补上 `archived_at` 键。

**`reference_count` 属性**（`models.py:212`）：`self.demands.count()` → `self.demands.filter(deleted_at__isnull=True).count()`，与 `is_process_referenced`（`versioning.py:25`）口径对齐。

**边界情况**

| 场景 | 目标行为 |
|---|---|
| `code` 在库中不存在 | 返回 `[]`（不抛异常） |
| 该 code 全部行都被软删 | 返回 `[]` |
| 同 code 有 `version_seq` 1/2/10 三行 | 排序为 1, 2, 10（**不是** 1, 10, 2） |
| 归档一个已归档流程 | `archived=True`，`reference_count` 是 int，`archived_at` 是首次归档时间的 ISO 串 |

#### 配套回归测试点

1. 同 code 下建 `version_seq` = 1/2/10 三行，`list_process_versions` 返回顺序为 `[1, 2, 10]`
2. 软删其中一行后，返回条数 -1
3. 用 `django_assert_num_queries` 断言 `list_process_versions` 对 N 行只发**常数条**查询（当前是 1 + N）
4. 返回的每条含 `version_seq` 与 `is_latest` 键，且恰有一条 `is_latest=True`
5. `archive_process` 的两个分支（首次归档 / 重复归档）返回的 **key 集合相同**，且 `type(reference_count) is int`
6. 一个有 2 个 demand（其中 1 个软删）的流程，`reference_count == 1`

---

### T6 — 删除 `stage_transitions.py` + 死模块守卫（S1~S8）

**优先级**：P1　**依赖**：无　**需要 migration**：否

#### 文件与行号

| 文件 | 动作 |
|---|---|
| `apps/django/apps/application/services/stage_transitions.py` | **整文件删除**（263 行） |
| `apps/django/tests/test_no_dead_service_modules.py` | **新建**守卫测试 |

#### 删除前必须完成的验证清单（工程师执行，缺一不可）

```bash
cd apps/django
# 1) 静态引用检查（含字符串形式的动态 import）
grep -rn "stage_transitions" --include="*.py" . | grep -v "/.venv/"        # 必须无输出
grep -rn "stage_transitions" --include="*.cfg" --include="*.toml" --include="*.ini" --include="*.yaml" --include="*.yml" . | grep -v "/.venv/"
# 2) Celery 任务注册名检查
grep -rn "stage_transitions" config/ | grep -v "/.venv/"
# 3) 删除后必须绿
rm apps/application/services/stage_transitions.py
.venv/bin/python -m pytest --ds=config.settings.test -q -p no:cacheprovider > /tmp/after.txt 2>&1; tail -5 /tmp/after.txt
# 4) 系统检查
.venv/bin/python manage.py check --settings=config.settings.test
```

**若第 1 步有任何输出 → 停止删除，回报主理人。**

#### 守卫测试的目标行为

新建一条通用守卫，防止"死服务模块"复发：

- 扫描 `apps/*/services/` 下的所有 `.py`（排除 `__init__.py`）
- 对每个模块，检查是否存在**任何**其它文件 import 它（`from .X import` / `from apps.a.services.X import` / `import apps.a.services.X`）
- 无引用者 → 失败，报出模块路径
- 采用**债务台账（ratchet）**模式：若当前还有其它已知死模块，登记进 `KNOWN_DEAD` 白名单，断言"实际死模块 ⊆ 白名单"，这样新增死模块立刻红，同时不阻塞本轮合入
  - （与 QA 已建的 `tests/test_fsm_state_reachability_guard.py` 用的是同一套 ratchet 模式，保持团队一致）

#### 配套回归测试点

1. 删除后全量测试**不少于**删除前的通过数（518 passed / 8 xfailed 是红线）
2. `manage.py check` 零 error
3. 守卫测试在 `apps/application/services/` 下人为放入一个无引用模块时**变红**（QA 可用 monkeypatch 造场景，或参考已有的 `test_fsm_reachability_guard_mutation.py` 的变异测试写法）
4. 守卫测试对现存的 `grab.py`（被 `views.py:69` 引用）、`soft_reject.py`（被 `views.py:70` 引用）判定为**活模块**，不误报

---

## 5. 风险、红线与待确认项

### 5.1 本文档范围外、但已核实存在的问题（建议另立条目）

| # | 位置 | 问题 | 证实等级 | 建议 |
|---|---|---|---|---|
| **N1** | `application/services/__init__.py:305`、`:355` | `try: application.send_offer_state() except Exception: application.state = ...` —— **兜底分支本身必抛 `AttributeError`**（protected FSMField）。正常路径不受影响，只在状态机拒绝转移时炸，属"错误处理路径自身出错" | **实测**（P4 证明任何裸赋值必抛） | 下轮，与 QA 的 D1/D2/D3 一起修（同一类根因） |
| **N2** | `application/services/__init__.py:442` `jump_application_to_stage` | 活实现同样**没有 `select_for_update`**，而 `advance` 也没有（活实现 `:254` 无行锁——死码 `:38` 反而有）。并发推进/跳转同一 application 存在双记录风险 | **静态-确认**（读源码） | 下轮。另需核查 jump 是否更新 `last_advanced_at`（本文档**未证实**） |
| **N3** | `process/serializers.py:490` 等四处 | `current_version` 初值四处不一致（X1）。T1 只统一了 model default 与 `load_process_templates`，`serializers.py:490` 的 `'V1.0'` 与新 default 已一致，但 `Position.process_version` / `Demand.process_version` 的 default 仍是 `'1.0'` | **实测** | 下轮统一。注意这三张表存的是**冻结快照**，不能盲改存量数据 |

### 5.2 需产品经理确认（代码无法自证，工程师**不得**自行拍板）

| # | 问题 | 为什么代码答不了 | 影响的任务 |
|---|---|---|---|
| **Q1** | `POST /processes/{id}/bump-version/` 与 `POST /processes/{id}/clone-version/` 是两个不同的业务动作，还是历史遗留的重复实现？前者只改版本号不产生新行，与 BR-101「配置修改生成新版本」矛盾。**是否应废弃 bump-version 端点？** | PRD BR-101~BR-106 没有区分"改版本号"与"生成新版本"两种动作 | T2 |
| **Q2** | BR-104「升版本」的三个边界：<br>(a) 只能升到 `is_latest=True` 的那一版，还是可以升到任意中间版本？<br>(b) 允许**降**版本吗？<br>(c) 允许跨 `code`（换一条流程线）吗？ | 代码里三种都没校验，无法从实现反推意图 | T3 |
| **Q3** | 克隆新版本时，`AutomationRule`（`automation.AutomationRule`，CASCADE FK 到 process）应否一并复制？不复制 = 新版本自动化能力归零；复制 = 规则可能引用已变更的阶段 | 属业务策略，无代码线索 | T4 |
| **Q4** | BR-101 说"流程被引用后配置修改将生成新版本"。生成新版本后，**已引用该流程的 `Demand` / `Position` 是否自动改指到新版本行？** 当前 `clone` 完全不处理它们，两者的 FK 仍指向旧行 —— 结果是"生成了新版本但没人用它" | BR-102 只规定了 Application（候选人）层面，对 Demand/Position 层面完全空白。**这是 BR-101 能否真正生效的关键前提** | T2/T4 |
| **Q5** | 归档一个流程时，是归档**这一个版本行**，还是归档**整条流程线的所有版本**？当前 `archive_process` 只改单行 | `archive_process` 只有单行语义，PRD BR-106 只说"流程只能归档" | T5（本轮保持单行语义，仅记录该歧义） |

### 5.3 对现有 518 passed / 8 xfailed 基线的影响评估

| 任务 | 是否影响现有测试 | 理由 |
|---|---|---|
| **T1** | **极低风险** | ① 全库**零测试**依赖 `RecruitmentProcess.code` 的唯一性（`grep IntegrityError\|unique` on tests 无命中）；② `is_latest` default=True，所有现存 fixture 创建的流程自动满足过滤条件，list 端点行为不变；③ `current_version` default 从 `'1.0'` 改 `'V1.0'` **有 1 处需留意**：`apps/add_candidate/tests/conftest.py:24` 显式传 `current_version='1.0'` 并注释「与 Position.process_version 默认值一致」—— 该 fixture 显式传值，不受 default 变更影响，**但工程师改完必须复跑 add_candidate 全套确认** |
| **T2** | **零风险** | `clone_process_with_new_version` / `bump_version` 在全库**零测试覆盖**（`grep "clone-version\|clone_process\|bump-version"` on tests 无命中）。改动无处可退 |
| **T3** | **零风险** | `upgrade_application_to_latest_version` **零调用方、零测试**。注意勿与活代码的 `ApplicationService.upgrade_workflow_version`（`views.py:386` 在用）混淆 |
| **T4** | **零风险** | 同 T2 |
| **T5** | **低风险** | `archive_process` 被 `views.py:255` 的 `archive` 端点调用，返回值进 `extra` 字段。若有测试断言 `extra.reference_count is False` 会红——已 grep 确认**无此断言** |
| **T6** | **零风险** | 全库零引用（已实测）。删除后 `manage.py check` 与全量测试必须仍绿，这是删除的验收条件 |

**红线（不可退让）**：
1. 全量 `pytest --ds=config.settings.test` 必须 ≥ **518 passed / 8 xfailed / 0 failed**
2. 8 条 xfail **不得**在本轮变成 pass 或 fail —— 它们属于 QA 的 D1/D2/D3 领域，本轮改动若碰到它们说明越界了
3. `manage.py check` 零 error
4. migration 必须可逆（`migrate process 0004` 能成功回滚）

### 5.4 与 QA 工作面的边界（重要）

QA 已提交 3 个未跟踪测试文件锁定 FSM 缺陷：
- `tests/test_application_state_transition_defects.py`（D1/D2）
- `tests/test_fsm_state_reachability_guard.py`（D3，含 `KNOWN_UNREACHABLE` 债务台账）
- `tests/test_fsm_reachability_guard_mutation.py`

**分工红线**：

| 归属 | 内容 |
|---|---|
| **QA/D 系列（不属本文档）** | `views.py:331/352/368` 方法名错误；`services/__init__.py:606/716` 裸赋值；为 `ApplicationState.WITHDRAWN`/`TIMEOUT` 补 `@transition`；`KNOWN_UNREACHABLE` 台账中另外 5 个模型的死枚举 |
| **本文档（V/T 系列）** | `versioning.py` 全部；`stage_transitions.py` 的删除 |
| **交叉点** | S1 与 D2 是同一根因的死码/活码两面。**处置约定**：S1 随文件删除，D2 由 QA 方案修复。工程师做 T6 时**不要**顺手去改 `services/__init__.py:716` |

---

## 6. 附录

### 6.1 活代码 FSM 缺陷现状（仅存档，处置权在 QA/D 系列）

| ID | 位置 | 实测现象 |
|---|---|---|
| D1 | `views.py:331/352/368` | `ApplicationService.withdraw_application`/`pause_application`/`resume_application` **不存在**（P1 实测 `hasattr=False`）。同名函数只在 `services/__init__.py:760/765/770` 的**模块级**。三个端点稳定 500 |
| D1' | `services/__init__.py:606` | `application.state = WITHDRAWN` 裸赋值，被 D1 掩盖，**从未执行过**。修 D1 后会立刻暴露 |
| D2 | `services/__init__.py:716` | `application.state = TIMEOUT` 裸赋值必炸；唯一调用方 `tasks.py:227` 的 `except Exception: logger.warning` 把它吞了 → 任务返回 `archived_count=0` 且不告警（**静默失败**） |
| D3 | `application/models.py` | `ApplicationState` 9 个枚举，`@transition` 只覆盖 6 个 target（P4 实测），`WITHDRAWN`/`TIMEOUT` 运行期不可写 —— D1'/D2 的根因 |

### 6.2 关键证据索引

| 结论 | 证据 |
|---|---|
| `stage_transitions.py` 零引用 | `grep -rn "stage_transitions" --include="*.py" . \| grep -v "/.venv/"` → exit 1，无输出 |
| `code` 无 FK 引用 | `RecruitmentProcess._meta.related_objects` 运行时枚举，7 个关系全部 FK 到 `id` |
| 前端不用 `code` | `grep "process.code\|processCode\|process_code" web/app/src` → 无匹配 |
| 前端不调 clone/versions/bump | `grep "clone-version\|/versions\|bump-version" web/app/src` → 无匹配 |
| 三端点零测试覆盖 | `grep "clone-version\|clone_process\|list_versions\|bump-version\|/versions" tests/ apps/*/tests/` → 无匹配 |
| partial UniqueConstraint 在本项目可行 | `apps/process/models.py:102-111` 已在用，测试库 SQLite 上通过 |
| 迁移可证明安全 | 迁移前 `code UNIQUE` ⟹ `(code, X) UNIQUE` 对任意 X 成立 |
| dev 库现状 | 3 行、code 互异、version 全 `'1.0'` |
| `TalentPoolEntry` 无 FSMField | `grep FSMField apps/talent_pool/models.py` → 无输出 |
| `Application` 无 `FSMModelMixin` | MRO 实测：`['Application','FullAuditModel','TimestampedModel','SoftDeleteModel','Model','AltersData','object']` |

### 6.3 探针文件

`tests/test_arch_probe_tmp.py`、`tests/test_arch_probe2_tmp.py` —— **已于本文档定稿前删除**，输出全文归档于 §1.1。

---

*本文档由架构师高见远（software-architect）产出。未修改任何源码，未 commit。*
