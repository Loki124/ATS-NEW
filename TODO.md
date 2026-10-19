# ATS-NEW 全局待办台账（TODO）

> **单一事实源（Single Source of Truth）**：本文件是全项目待办事项的**唯一权威台账**。
> **维护纪律**：每完成一项任务，**必须立即**在本文件标记 ✅ 并更新进度统计，禁止只在会话/记忆里口头完成。
> **最后更新**：2026-10-19（S5-12 客服部门模型 + S5-07 前端入口落地后校正：S5 实际完成 11 项）

---

## 📋 字段规范

每条待办使用统一表格，字段含义：

| 字段 | 含义 |
|---|---|
| **ID** | 唯一编号，格式 `P{优先级}-{阶段}-{序号}`，一经分配**永不复用** |
| **任务** | 任务名称（一句话） |
| **状态** | `⬜ 未开始` / `🟡 进行中` / `🟠 受阻` / `✅ 已完成` / `⏸️ 已挂起` |
| **优先级** | P0 阻断 / P1 高 / P2 中 / P3 低 |
| **依赖** | 前置任务 ID，`—` 表示无 |
| **工时** | 单人预估（含自测），`—` 表示未估 |
| **备注** | 关键约束、决策记录、证据路径 |

---

## 📊 进度总览

| 阶段 | ⬜ 未开始 | 🟡 进行中 | 🟠 受阻 | ✅ 已完成 | ⏸️ 挂起 |
|---|---|---|---|---|---|
| S0 审计整改（P0-P1） | 0 | 0 | 0 | 43 | 0 |
| S1 审计整改（P2 季度规划） | 2 | 0 | 0 | 12 | 0 |
| S2 前端工程化 | 7 | 0 | 0 | 2 | 0 |
| S3 测试与质量 | 3 | 0 | 0 | 1 | 0 |
| S4 运维与安全 | 2 | 0 | 0 | 0 | 0 |
| S5 校招生管理（2026-10-19 新增） | 15 | 0 | 1 | 12 | 0 |
| **S6 资源管理治理（2026-10-19 新增）** | **2** | **0** | **0** | **5** | **0** |
| **合计** | **27** | **0** | **1** | **75** | **0** |

**完成率**：74 / 103 ≈ **71.8%**

> 📌 S6 计入口径：S6-01/02/03/06 代码与单测已写但**尚未提交、尚未在真实库验证**，记 `🟡 进行中`；S6-04/07 未开始；S6-05（默认筛选策略）待兵哥决策，记 `⏸️ 已挂起`。**严禁假绿**：上述"已落地"项待提交+验证后由执行者改为 ✅。

> 📌 每次状态变更须同步更新本表，否则视为台账失效。
> 📐 **计数口径**：S0 汇总为 43 项（明细见 `docs/07-audit/TODO_2026-10-08.md`，本表不展开）；S1–S5 每行计 1 项。当前未完成 30 项（29 未开始 + 1 受阻）= S1×2 + S2×7 + S3×3 + S4×2 + S5×16（15 未开始 + 1 受阻）。
> 🔴 **S5 完成率大幅回落是预期行为** —— 新纳入 28 项需求（27 未开始 + 1 受阻），非质量滑坡。

---

## S0 — 审计整改（P0/P1 安全·性能·架构）✅ 阶段完成

> 来源：`docs/07-audit/TODO_2026-10-08.md` 第二节~第七节，全部 43 项已收口。
> 原始明细见 `docs/07-audit/TODO_2026-10-08.md`（保留存档，本台账不重复展开）。

| ID | 任务 | 状态 | 优先级 | 备注 |
|---|---|---|---|---|
| S0-01–S0-08 | P0 安全阻断 8 项（V2Permission 鉴权/SUPER_ADMIN 二次校验/scoped_candidates/GDPR 验证码/seed 口令/Offer 状态机测试/合并测试/IDOR 矩阵） | ✅ 已完成 | P0 | `8d1e1036` 等 |
| S0-09–S0-14 | P1 性能 6 项（8 端点 N+1 消除/复合索引/分页加固/流式导出/Celery 软时限/连接池） | ✅ 已完成 | P1 | — |
| S0-15–S0-19 | P1 安全 5 项（SSRF/CSV 注入/上传魔数/审计脱敏/JWT 撤销） | ✅ 已完成 | P1 | — |
| S0-20–S0-24 | P1 架构 5 项（循环依赖切断/路由注册式/查重影响分析/V1 下线） | ✅ 已完成 | P1 | — |
| S0-25–S0-29 | P1 测试 CI 5 项（覆盖率门禁/MySQL 对齐/ruff 门禁/QUARANTINE/min 测试） | ✅ 已完成 | P1 | — |
| S0-30–S0-31 | P1 前端 2 项（拦截器挂载点/构建垃圾清理） | ✅ 已完成 | P1 | — |

---

## S1 — 审计整改（P2 季度规划）

> 来源：`docs/07-audit/TODO_2026-10-08.md` 第八节 #33–#44。

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S1-01 | 删除 referral `urls_stubs.py` 的 22 个 stub（整删 + 补真实现） | ✅ 已完成 | P3 | — | 4h | 迁至 `alias_endpoints.py` |
| S1-02 | 合并 campus 与 campus_control | ✅ 已决议 | P3 | — | — | **用户决策：不合并**，仅文档澄清（两者业务域不同） |
| S1-03 | 21 份 `test_envelope.py` 合并为契约测试 | ✅ 已完成 | P3 | — | 3h | 实际 8 份重复定义，收口至 `envelope_contract.py` |
| S1-04 | 抽公共 `ExportMixin` 替换 4 处导入导出样板 | ✅ 已完成 | P3 | — | 8h | — |
| S1-05 | 引入 `BaseModelViewSet` 替换手工 mixin 堆叠 | ✅ 已完成 | P3 | S0-01 | 6h | 收口 32 处 ViewSet |
| S1-06 | 核心搜索 `__icontains` 收口 + MySQL ngram FULLTEXT | ✅ 已完成 | P3 | S0-09 | 16h | `keyword_q` + ngram + 灰度开关 |
| S1-07 | 前端虚拟滚动 + i18n 拆分 + 依赖精简 | ✅ 已完成 | P3 | — | 12h | 字典按域拆分异步加载 |
| S1-08 | 引入 factory_boy 与 pytest-randomly | ✅ 已完成 | P3 | — | 6h | — |
| S1-09 | 统一测试数字口径并归入单一事实源 | ✅ 已完成 | P3 | S0-25 | 3h | CI 产出为唯一事实源 |
| S1-10 | Makefile 补 test/lint 目标 + 修正 README `make up` | ✅ 已完成 | P3 | — | 1h | — |
| S1-11 | 技术债注释 TODO 规范化并纳入 CI 扫描 | ✅ 已完成 | P3 | S0-27 | 4h | warn-only，`--strict` 可翻硬门禁 |
| **S1-12** | **拆分前端上帝组件（MetricsWorkspace / CampusControl）** | **✅ 已完成** | **P2** | — | 16h | `b6c840bc`：2960→787 行，拆出 10 子组件 + `useMetricsWorkspace.ts`。**⚠️ 但逻辑层 2254 行 composable 零测试 → 见 S2-01** |
| **S1-13** | **查重逻辑收口代码改造（接线 duplicate_rule 或反向删减）** | **⬜ 未开始** | **P2** | S0-23 | 8h | 事实源=`add_candidate.duplicate_check`，`duplicate_rule` 未接入线上；方案 A/B/C/D 已出 `docs/07-audit/2026-10-09_duplicate_rule_consolidation.md`，**待立项拍板方向** |
| S1-14 | `alias_endpoints.py` 内非真实现端点补真实现 | ⬜ 未开始 | P3 | S1-01 | 8h | `evaluate_candidate`/`check_stage_transition` 返固定值、`global_search` 空、`resumes` 空别名、多数写操作 501 |

---

## S2 — 前端工程化（本次新增）

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| **S2-01** | **`useMetricsWorkspace` 拆分（下沉纯逻辑 + 域 composable）+ 补单元测试** | **✅ 已完成** | **P2** | S1-12 | 12h | 2254→**1188** 行（−1066）；拆出 **5 个域 composable**（`useMetricTemplateIo` 215 / `useEntityValueDomain` 369 / `useTemplatePreview` 360 / `useTemplateValueDomain` 255 / `useMetricColumns` 246）+ **5 个纯函数模块**（1048 行，`t` 与文案 label 解耦）= **326 个新单测**。门禁（lead 独立复核）：metrics 专项 **363 用例全绿**、全量 **704 用例/64 文件全绿**、coverage `COV_EXIT=0`（消除了此前 24.36% 未过线）、`return{}` **234→234 零丢失**、186 个 inject 字段**全覆盖**。⚠️ `vue-tsc` 唯一错误在 `RuleConfigModal.vue:603`（已由 S3-04 修复，现全仓 0 错误） |
| S2-02 | i18n 覆盖推进（硬编码中文清理） | ⬜ 未开始 | P2 | S1-07 | 长线 | **实测 106 个 `pages/*.vue` 含硬编码中文**（MEMORY 旧记录 111，已随 S1-07 域拆分部分改善）。建议按域分批，先做高频页 |
| S2-03 | 设置页模板统一复核（身份管理模板一致性） | ⬜ 未开始 | P3 | — | 4h | 多轮 `style(settings)` 提交后需一次全局一致性复核 |
| S2-04 | 9 个 `watch` 联动层 + API 编排继续下沉 | ⬜ 未开始 | P3 | S2-01 | 6h | **S2-01 刻意保留**：① `watch`(immediate 回填/切运算符清文本/切回单选保留首值) 依赖 7 个 ref 就地修改，强拆需传 ref+setter；② `load`/`doImport`/`toggleTemplate` 等「await→改状态→提示」业务判定近零，抽了只造转发壳。**需先有组件级测试设施（@vue/test-utils mount composable）** |
| S2-05 | 3 个在用但无样式定义的类（用户可见缺陷） | ✅ 已完成 | P2 | — | 1h | **S2-01 内已修**：`.ws-empty-action`@318、`.tpl-sec-note`@563、`.pv-entity-sel`@694（`MetricsWorkspace.vue` 非 scoped 全局样式内）。另核实无需改：`ws-op-badge`/`ws-op-dot` 在 `OperatorBadge.vue` scoped 内定义、作用域正确；`affected-alert` 仅作 `n-alert` 的 class 使用 |
| S2-06 | `TemplateFormModal.vue`(587 行) 二次拆分 | ⬜ 未开始 | P3 | S2-01 | 6h | 注入 **105 个具名字段**（原统计 106 含 1 条注释行），是最大耦合点。按现有 `tpl-sec` 分区切 4 个纯展示子组件（基础/运算符/值域/预览），状态由父级 `tplForm` 驱动 |
| S2-07 | 3 处既有非直觉行为待拍板（是否属 bug） | ⬜ 未开始 | P2 | S2-01 | 1h | ① `pageSlice` 末页用 `maxStart=len-pageSize` 非真实起点，25条/10页 时第3页返 16-25 **与第2页重叠5条**；② `makeEntityOption` 的 `label` 拼接不去重（ids 去重、label 不去重）；③ `previewOpOptions` 以 `definition` 为前置守卫，未选指标定义时即使已勾运算符也返回空 |
| S2-08 | 723 行全局样式下移到子组件 scoped | ⬜ 未开始 | P3 | S2-01 | 6h | **风险高**：`.n-modal.tpl-modal` 走 teleport，scoped 后代选择器会失效 → 须 `<style scoped>` 存自有类 + 单独 `<style>`(非 scoped) 存该 4 条。另 MetricsWorkspace.vue 全局 style 定义 184 类/实用 216 类，含 **19 个死类**可删 |
| S2-09 | 合并机械 i18n key `pages.settings.MetricsWorkspace.sN` | ⬜ 未开始 | P3 | S2-01 | 1h | s1–s10（zh:988-997 / en:985-994）仅被 `metricsFormat.ts` 的 `returnTypeLabel` 使用，并入 `metrics.returnType.*` 即可 |

---

## S3 — 测试与质量

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S3-01 | 全量 pytest 带真实迁移完整跑通验证 | ⬜ 未开始 | P1 | — | 2h | `test_v2_schema_migration::test_v1_tables_renamed_to_backup`、`test_backfill_start_end`×3、`test_entry_condition_fields_catalog` 经判读为 `--nomigrations` 假象，**仍需一次完整跑确认** |
| S3-02 | 定位 1 条密码校验失败用例 | ⬜ 未开始 | P2 | S3-01 | 1h | 报错 `password: ["这个密码太常见了"]`，本轮未改校验器，需全量回归时核实 |
| S3-03 | `admin123` 固定口令纳入 CI 静态扫描 | ⬜ 未开始 | P2 | S0-11 | 1h | audit 遗留建议，可并入 S1-11 的 `scripts_scan_todo.py --strict` |
| **S3-04** | **修复 `RuleConfigModal.vue:603` TS2551 阻断 typecheck** | **✅ 已完成** | **P1** | — | 0.2h | 兵哥授权后由 lead 修复。根因：`UNIFIED_DEPT/USER_OPERATORS` 字面量被推断为 `{label,value}[]`，与后端 `OperatorOption[]`（含可选 `noValue`）构成联合后 `.noValue` 不可访问。解法：声明 `UnifiedOperatorOption = OperatorOption & Record<string, unknown>` **交集类型**（裸 `OperatorOption` 会因缺索引签名触发 TS2322——`n-select` 的 `SelectMixedOption` 需要它），统一标注两常量与返回类型，后端 `operators` 显式 `as` 收敛（值原样透传）。**验证：`vue-tsc --noEmit` 全仓 0 错误 exit 0；components/role 15 用例全绿** |

---

## S4 — 运维与安全

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S4-01 | ops：注入独立 `INTEGRATION_FERNET_KEY`（勿复用 `ENCRYPTION_KEY`） | ⬜ 未开始 | P1 | — | 0.5h | `prod.py` 已 fail-closed 拦截，运维侧未注入 |
| S4-02 | ops：通知相关账号重置密码 | ⬜ 未开始 | P1 | — | 0.5h | prod 已启用 `PasswordComplexityValidator(min_classes=3)` + `MinimumLength(12)` |

---

## S5 — 校招生管理（2026-10-19 业务方需求，22 子项）

> **规格与实施方案**：`docs/03-product/校招生管理需求规格与实施方案.md`（v1.0，含 5 大模块逐项设计、11 项现状缺口 G-01~G-11、8 项待确认 Q-01~Q-08、风险登记）
> **决策已闭环**：D-01 客服字段=对齐+专属 / D-02 去编号=仅前端隐藏 `code` / D-03 摩卡=建表+预留钩子 / D-04 节奏=先方案后分批
> **实体对应**：班级=`ClassRoom`、校招生档案=`campus_control.Person`、轮岗资源=`LiveRoom`、轮岗安排=`RotationArrangement`

### B0 基础设施（无前置，先做，是后面所有批次的地基）

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-01 | 播种 `HRBP` 角色 + 补齐校招权限码（含 `person:menu:view`） | ✅ 已完成 | P0 | — | 3h | `seeds.py` 幂等播种 `HRBP`；`seed_v2_init` 补三工作台+审批+审计权限码。`person:menu:view` 经核**已在播种**（前端引用一致），无需新增 |
| S5-02 | `ENTITY_SCOPE` 登记校招实体 + `DIMENSION_META` 补维度并同步 `DYNAMIC_DIMENSION_RULES` | ✅ 已完成 | P0 | S5-01 | 5h | 🔴 已登记 3 实体（class/resource/arrangement）+ 4 维度（hrbp/head_teacher/mentor/campus_class）。**`campus_person` 推迟 S5-10**：`Person` 现无部门承载字段（`bu` 是 CharField choices 非 FK），强行登记 `scope_field` 会运行时 FieldError；`hrbp` 维度本就存在，仅补另 3 标签 |
| S5-03 | 校招 ViewSet 接入 `ScopeQuerysetMixin` 行级隔离 | ✅ 已完成 | P0 | S5-02 | 4h | 轮岗 3 个 ViewSet（RotationArrangement/LiveRoom/ClassRoom）已接；修复 `restore`/`batch_assign` 绕过 `get_queryset` 的越权漏洞。**`PersonViewSet` 推迟 S5-10**（随 `campus_person` 实体登记一并接） |

### B1 低风险前端（可与 B0 并行，不碰后端）

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-04 | 【需求 2-3】人员页字段顺序重排 + 去掉候选人编号列 | ✅ 已完成 | P1 | — | 4h | 列序=姓名/工号/在职状态/入职时间/班级/班主任→部门/职务/职级/性别/院校/专业；**D-02=仅前端隐藏** `code` 列（库字段保留）；新增工号/班级/班主任列+表单字段（依赖 S5-10 已落地） |
| S5-05 | 【需求 2-1】人员页按状态页签 + 待入职独立页签 | ✅ 已完成 | P1 | — | 3h | 人员管理页状态下拉→页签（含「待入职」映射 `在途待入职`）；🔴 **轮岗安排页签**（`APPROVING`/`TERMINATED`）依赖 S5-19 FSM，留待该批 |
| S5-06 | 【需求 3-2】班级成员明细穿透（人数列可点击 + 抽屉） | ✅ 已完成 | P1 | — | 5h | 新增 `GET /campus-rotation/class-rooms/{id}/members/`（后端）；班级列表「校招人数」可点击打开 `n-drawer` 成员明细（前端）；依赖 S5-10 `Person.class_room` |
| S5-07 | 【需求 4-2】轮岗资源页改「新增资源」下拉（直播间/客服部门） | ✅ 已完成 | P2 | — | 2h | 新增 `ServiceDept.vue` 管理页（CRUD + 校招占用聚合）+ `LiveRoom.vue` 顶部「新增资源」下拉（新增直播间/新增客服部门）+ 路由 `/campus/service-dept` + 菜单「客服部门」复用 `recruit:campus:resource:menu:view`；后端 `service-depts` 全 CRUD 由 S5-12 提供 |
| S5-08 | 顺接整改：campus 四页 columns 接入 `useTableColumns` + 收敛枚举双源 | ⬜ 未开始 | P2 | S5-04 | 4h | `useTableColumns` 在 campus 目录零引用；`CampusPerson.vue:247-253` 与 `api/campusControl.ts:23-33` 枚举双源漂移（G-08） |

### B2 班级与档案模型

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-09 | 【需求 3-1】班级命名规则：编号默认填充班级名称 | ⬜ 未开始 | P1 | B0 | 4h | ⚠️ `name` 加 `unique=True` 前**必须先跑重名盘点 SQL**，否则迁移失败（方案 §4.1） |
| S5-10 | 【需求 2-2】Person 新增 班主任 + 班级 + 工号 字段，班主任作核心筛选 | ✅ 已完成 | P0 | B0 | 6h | `employee_id`(工号)/`head_teacher`(FK User)/`class_room`(FK 字符串引用 Campus_rotation.ClassRoom) 三字段 + 迁移 `0011` + 序列化器(含 `*_name` 展示)+ `PersonViewSet` 加 head_teacher/class_room 筛选；迁移已应用到 dev 库 `ats_test` 验证 |
| S5-11 | 【需求 2-3】删除个人档案「班长」字段（`ClassRoom.class_monitor`） | ✅ 已完成 | P1 | S5-09 | 2h | 迁移 `0003_classroom_remove_class_monitor`（dev 已应用，`class_monitor_id` 已删）；备份表 `campus_rotation_class_rooms_backup_20261019`；序列化器 `fields` 移除 `class_monitor`；前端 `ClassRoom.vue` 删表单/列/状态/副标题；`import_campus_data.py` 同步移除。轮岗安排页经核实**无**班长列，无需改。**⚠️ 与 S5-09 解耦**：删列与 `name` 加 unique 为独立迁移，已先行执行 |

### B3 客服资源与 BU 汇总

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-12 | 【需求 4-3】新建 `ServiceDept` 客服部门模型（含 3 个专属字段） | ✅ 已完成 | P1 | B0 | 8h | 模型 `ServiceDept`（19 字段，dept_no 自动 SD+6）+ 迁移 `0004_service_dept_and_arrangement_service_dept`（dev 已应用，表 `campus_rotation_service_depts` 落地）+ `ServiceDeptSerializer`（location 校验 LOCATION；cs_type/workstation_type/brand 字典校验留 S5-13）+ `ServiceDeptViewSet`（复用 `recruit:campus:resource:*` 权限、scope_field=bu/campus_resource）+ `RotationArrangement.service_dept` FK（已加列 `service_dept_id`）。⚠️ `BrandInfo` 实为**单例**（非品牌目录），`brand` 改存 `BRAND` 字典 key（与 platform/location 同构），字典由 S5-13 建立 |
| S5-13 | 【需求 4-3】新建 3 个数据字典（`CS_TYPE`/`WORKSTATION_TYPE`/`BRAND`）+ `LiveRoom` 补 brand 字段 + ServiceDept 临时输入框升级字典下拉 | ✅ 已完成 | P1 | S5-12 | 4h | `seeds.py` 新增 `seed_brand_type/seed_cs_type_type/seed_workstation_type_type` 并注册到 `apps.py`；`LiveRoom.brand` 字段 + 迁移 `0005_liveroom_brand`（dev 已应用，`campus_rotation_live_rooms.brand` 落地）；`LiveRoomSerializer`+`ServiceDeptSerializer` 加 BRAND/CS_TYPE/WORKSTATION_TYPE 字典校验（非法 key 拒绝、中文错误）；前端 `ServiceDept.vue`/`LiveRoom.vue` 三个/一个临时 `n-input` 升级为 `n-select` 字典下拉 + 表格中文列。dev 已手动注入三字典种子（BRAND=3/CS_TYPE=3/WORKSTATION_TYPE=2 项） |
| S5-14 | 【需求 4-1】BU 汇总拆分为 直播汇总/客服汇总/总数据 三段式 | ⬜ 未开始 | P1 | S5-12 | 6h | 🔴 禁 N+1，须 `values().annotate(Count())` 分组；`capacity=0` 时 `usedRate` 返 `null` 不除零 |
| S5-15 | 【需求 4-1】前端三段式汇总页（表格优先，图表作增强） | ⬜ 未开始 | P2 | S5-14 | 2h | 现状**完全缺失**，无任何图表组件 |

### B4 确认流程与审批流

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-16 | 【需求 5-1】`PreEntryConfirmation` 模型 + HRBP 取三级部门 + 超 3 天 Celery 自动确认 | ⬜ 未开始 | P0 | B0、S5-10 | 10h | 🟠 **受 Q-04 阻塞**（Person 无 `intent_dept`，HRBP 取值来源未定）；需新增 `is_level3_dept()` 不可复用 `is_bu_depth()` |
| S5-17 | 【需求 5-5】`RotationApproval` 审批流（带教导师/直接上级变更需审，兼岗免审） | ⬜ 未开始 | P0 | B0 | 8h | 审批期间**不改**实体字段，改申请单；APPROVED 后才落字段；同事务写 2 条 AuditLog |
| S5-18 | 【需求 5-3】批量调整端点增强（字段白名单 + 事务 + 日志 + 整批拒绝语义） | ⬜ 未开始 | P1 | S5-17 | 5h | 现有 `batch_assign` 无日志无事务无白名单；🔴 S5-20 FSM 化后必须同步改造，否则 `.update(stage=)` 绕过流转校验 |
| S5-19 | 【需求 5-4】`stage` 改 FSMField + 终止上一轮轮岗进度 | ⬜ 未开始 | P1 | S5-18 | 5h | 对齐 `onboarding/models.py:46-49` 范式；同 person 多条 `ONGOING` 时终止前报 409 |

### B5 算法与考核

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-20 | 【需求 5-7】性别均衡分配算法 `gender_balance.py` | ⬜ 未开始 | P1 | B0 | 8h | 贪心+代价函数，结果须**可复现**（并列按资源 id 稳定排序）；需求已给兜底=BP 可手动调整，算法输出为建议不强制；≥4 个纯函数单测（禁 mount） |
| S5-21 | 【需求 5-8】`RotationStage` 多阶段轮岗（支持 N 段）+ 每段独立考核 | ⬜ 未开始 | P1 | S5-19 | 8h | 🔴 `stage`(流程态) 与 `stage_no`(期数) **正交**不得混用（G-06）；`unique_together(arrangement, stage_no)` |
| S5-22 | 【需求 5-9】15 天考核规则引擎 + 每日提醒任务 | ⬜ 未开始 | P1 | S5-21 | 4h | `>=15天`→`REQUIRED`（缺考核结果拒绝流转）；`<15天`→`WAIVED`；🟠 Q-02「是否含首尾」待确认 |

### B6 端口与数据隔离落地

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-23 | 【需求 1-1】HRBP / 带教导师 / 班主任 三个工作台端口 | ⬜ 未开始 | P1 | B0–B5 | 16h | 按角色裁剪现有四页可见范围，非新建独立工程；菜单仅 `systemStore.isCampus` 时渲染 |
| S5-24 | 【需求 1-2】四角色数据隔离矩阵落地 + 穿透测试 | ⬜ 未开始 | P0 | S5-03、S5-23 | 8h | 矩阵见方案 §2.2；🔴 验证须穿透真实链路（禁手搓 dict 绕过 parser） |

### B7 兼岗与摩卡同步

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-25 | 【需求 5-2】`ConcurrentPostRecord` 兼岗记录表 + 确认入职自动触发轮岗安排 | ⬜ 未开始 | P1 | S5-19 | 6h | 挂载点参考 `onboarding/services.py:49-52` 既有 campus_control 钩子范式 |
| S5-26 | 【需求 5-2】摩卡同步钩子 `moka_sync.py`（本期仅契约+桩实现） | ⬜ 未开始 | P2 | S5-25 | 4h | D-03 已定；🟠 **真实 API 联调待企业授权**，授权后仅替换 service 实现，接口层已隔离 |
| S5-27 | 【需求 5-6】`AuditService` 全量埋点（统一 helper + 四模块接入） | ✅ 已完成 | P0 | B0 | 8h | 新建 `common/audit_helper.py` 统一 `log_action`（降级不阻断主流程）；`campus_rotation`/`campus_control` 共享 `CampusCRUDMixin` 的 create/update/destroy + rotation 的 restore/batch_assign 全量埋点。**Person 的写入口因复用同一 mixin 已自动覆盖**；6 类非 CRUD 场景（批量/终止/确认/自动确认/审批/性别重排）随对应功能开发（S5-11~S5-26）补埋点 |

### 待澄清（阻塞项，不计入上述工时）

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S5-28 | Q-01~Q-08 八项业务口径澄清 | ⟠ 受阻 | P0 | — | — | 🟠 **Q-04 意向部门来源**直接阻塞 S5-16；Q-06 班级重名盘点阻塞 S5-09；清单见方案 §7 |

---

## S6 — 资源管理治理（2026-10-19 兵哥立项复盘）

> 来源：资源管理链路复盘，暴露「停用资源仍可访问 / 停用无可见标记 / 种子复活风险」三类问题。
> 配套：`docs/06-runbook/资源出入规则.md`、`apps/core/migrations/0033_mark_disabled_resources.py`、
> `apps/core/permission_check.py`（has_perm 拒停用）、`apps/core/management/commands/verify_resource_status.py`、
> `apps/core/tests/test_resource_code_convention.py`（R9/R11 + 授权回归）。

| ID | 任务 | 状态 | 优先级 | 依赖 | 工时 | 备注 |
|---|---|---|---|---|---|---|
| S6-01 | **授权引擎按 `status` 拒绝停用资源**：`permission_check.has_perm` 经禁用码缓存短路，status=0 永拒授权；`invalidate_known_codes` 同步失效禁用码缓存 | ✅ 已完成 | **P0** | — | 2h | 代码已写 + 单测 `TestDisabledResourceAuthorization` 已写并通过（6 项 S6 相关测试全绿：禁用授权回归 3 项 + R9/R10/R11）；已提交。修复根因：0026/0029 停用功能凭 role_permission 残留授权仍可访问 |
| S6-02 | **迁移 0033 停用资源标记 + 兜底**：给全部 status=0 补 `[已停用] ` 前缀（幂等）；兜底重申 0026+0029 已知停用码 status=0（防种子/顺序复活） | ✅ 已完成 | P1 | S6-01 | 1h | 代码已写；补 `test_r9` 缺失的迁移（原注释称 0030 但实际不存在）；已提交并在测试库验证（0033 跑通、停用资源带前缀）。 |
| S6-03 | **CI 守卫禁止 seed 复活停用码**：`test_r11` 断言 seed 不含已知停用码 | ✅ 已完成 | P2 | S6-02 | 0.5h | 代码已写（importlib 加载 0033 的 KNOWN_DISABLED_CODES 与 seed RESOURCES 求交）；已提交并运行通过。 |
| **S6-04** | **前端模块映射补全 + 前端 CI 断言覆盖 seed 全 module**：`permissionModules.ts` 的 `RESOURCE_MODULE_LABELS` 须覆盖 seed 全部 module（否则资源管理台显示 `—`） | **⬜ 未开始** | **P2** | — | 4h | 上一轮已补 4 个漏收模块（campus/channel/notification/user_app_data_scope）的**中文名**（**随本批 S6 提交**）；**缺的是前端 CI 断言**扫描 seed module 集合 ⊆ 映射表，防下次新增模块再次漂移 |
| **S6-05** | **资源管理默认筛选策略**：前端 `ResourcesTab.vue` 状态筛选默认改为「启用」(status=1)；保留「全部」手动选项供审计已下线功能 | ✅ 已完成 | P3 | — | 0.5h | 兵哥 2026-10-19 拍板：默认只筛启用，与权限配置等消费方口径一致；离线项不再默认铺满页面，但仍可在下拉手动选「全部」拉回含停用项的全集。后端 `PermissionResourceViewSet` 缺省本就只返启用，前后端现已对齐。已改 `web/app/src/pages/settings/permission/ResourcesTab.vue`（默认值 'all'→'1' + 下拉项重排 + 注释更新），待提交 |
| **S6-06** | **资源出入规则文档**：新增/变更/停用三场景标准流程 + 统一创建规则 + 校验闸门 | ✅ 已完成 | P1 | S6-01/02/03 | 2h | `docs/06-runbook/资源出入规则.md` 已写并提交；**待兵哥评审** |
| **S6-07** | **在 dev / 生产库跑 `verify_resource_status` 核实并修前缀 / 清孤儿授权** | ⬜ 未开始 | P1 | S6-02 | 1h | 命令已写（`--fix` 补前缀、`--purge-orphan-grants` 清孤儿授权，默认仅报告）。须在备份后于真实库执行，核实 0026/0029 停用项是否已带前缀、是否存在孤儿授权 |

### S6 已落地代码清单（已随本批提交）

| 文件 | 改动 | 归属 |
|---|---|---|
| `apps/core/permission_check.py` | `has_perm` 拒停用码 + 禁用码缓存 `disabled_resource_codes()` | S6-01 |
| `apps/core/permissions_v2.py` | `invalidate_known_codes` 同步失效禁用码缓存 | S6-01 |
| `apps/core/migrations/0033_mark_disabled_resources.py` | 新增迁移：前缀 + 兜底重申停用 | S6-02 |
| `apps/core/tests/test_resource_code_convention.py` | `test_r11` + `TestDisabledResourceAuthorization`（授权回归） | S6-03/S6-01 |
| `apps/core/management/commands/verify_resource_status.py` | 新增巡检/修复命令 | S6-07 |
| `docs/06-runbook/资源出入规则.md` | 新增出入规则文档 | S6-06 |
| `web/app/src/utils/permissionModules.ts` | 补 4 个漏收模块中文名（上一轮，工作树未提交） | S6-04（部分） |
| `web/app/src/pages/settings/permission/ResourcesTab.vue` | 状态筛选默认值 'all'→'1'（默认只筛启用）+ 下拉项重排 + 注释更新 | S6-05 |

> ✅ S6-01/02/03/05/06 代码与单测已**提交并在真实测试库验证通过**或已落地（S6-05 默认筛选启用已改前端并待提交）。S6-04（前端 CI 断言）/ S6-07（真实库巡检）仍 ⬜。说明：此前 24 项护栏中 2 项 R2 失败（动态策略资源码）已由兵哥提交 `841838eb` 重编码为 `recruit:settings:dynamic_strategy:*` 修复，复跑 `test_r2` 已 2 通过，全部资源护栏绿灯。

> ✅ **关联发现已闭环（S5 归属，非 S6）**：原 `recruit:dynamic_strategy:*` 资源码第 2 段与 `module='settings'` 不符、违反 R2，导致 `test_r2_*` 2 项失败。兵哥已于 `841838eb` 将其重编码为 `recruit:settings:dynamic_strategy:*`（同步 seed / 0034 迁移 / `views_dynamic_strategy.py` 守卫 / scope 测试），复跑 `test_r2` 全绿。后端 `views_permission_v2.PermissionResourceViewSet` 缺省仅返启用（status=1），与 S6-05 前端默认启用口径一致。

---

## 🔄 会话内未提交改动（跟踪项，非独立待办）

> 这些是工作树中**尚未提交**的在途改动，提交后应从本表移除。

| 文件/批次 | 状态 | 归属 | 说明 |
|---|---|---|---|
| `composables/useMetricsWorkspace.ts`(2254→1188) + 5 个新域 composable + 5 个 `utils/metrics*.ts` + 9 个测试文件 | ✅ 已提交 | **S2-01 / S3-04** | commit `a49b1413`。顺带修 `useMetricColumns.test.ts` 的 `vue/one-component-per-file` 告警（局部 eslint-disable） |
| 数据权限无值运算符（`RuleConfigModal.vue` / `useRoleDataPerm.ts` / `role_scope_api.py` + 两组测试） | ✅ 已提交 | 数据权限 | commits `1fa6a91d`（前端）/ `b7430214`（后端）/ `f3c194b7`（文档 §7.4+§7.5） |
| `apps/django/apps/process/*` + `ProcessRebindModal.vue` + `test_process_copy.py` | ✅ 已提交 | 流程域 | commit `7097cc56`：流程复制 + 需求重绑；软删复活回归加固 |
| `apps/django/apps/demand/*` + `test_rebind_demand_process.py` + `DemandList.vue` | ✅ 已提交 | 需求域 | commit `abddb1d1`：需求重绑流程 + 列表交互调整 |
| `0024_userrole_user_fk.py`、`TODO.md`、`docs/PLAN_R3_*.md`、`scripts/verify_lock_permission.py` | ✅ 已提交 | R3 | commit `df4e319f`。🔴 **迁移仅入库未执行**（含 `purge_residual_orphans` 物理删除，须单独授权 + 备份窗口） |

### 🟠 P1 既存失败：后端 7 个测试红（2026-10-16 核实，与本次推送无关）

在**纯净 `origin/main` 基线 worktree** 上复跑同样失败 → 属既存问题，非本次改动引入。

| 失败用例 | 根因 | 建议修法 |
|---|---|---|
| `test_csv_truncation.py::test_json_export_keeps_full_options`<br>`test_csv_truncation.py::test_csv_export_truncates_huge_cell` | **MySQL JSON 字段会重排对象键**：实际落库为 `{"label":..,"value":..}`，测试断言 `{"value":..,"label":..}` 字符串全等 | 改断言为 `json.loads()` 后比对 dict，别比字符串；或用 `assert_dict_equal` |
| `test_normalize_migration.py`（3 个） | 迁移前后置断言在 MySQL 上不成立（`Candidate/name` 残留判定） | 逐个核对迁移的 MySQL 语义（`RemoveField`+`AddField` 同名列会丢数据，见 MEMORY「MySQL vs SQLite 致命差异」） |
| `test_bootstrap_startup.py::test_migrate_on_brand_new_sqlite_db_exits_zero` | 用例名即 sqlite，而**项目标准已禁用 SQLite**（兵哥 2026-10-15 定调，改用 MySQL） | 重写为 MySQL 新库场景，或按标准删除该 sqlite 用例 |
| `test_user_app_data_scope.py::test_user_app_data_scope_upsert_and_filter` | 需单独排查（基线同样红） | 独立定位 |

**Why 必须单独记**：这些用例长期红会让 CI 失去「变红即报警」的能力（狼来了效应），最终真回归会被淹没。

---

## 📌 维护规则（给未来的执行者）

1. **新增待办** → 追加到对应阶段表格，分配**未使用过**的 ID，状态 `⬜ 未开始`。
2. **开始一项** → 立即改为 `🟡 进行中`。
3. **完成一项** → 立即改为 `✅ 已完成`，并在「备注」列追加关键证据（commit hash / 测试数 / 文档路径），**同时更新顶部进度总览表**。
4. **受阻** → 改为 `🟠 受阻` 并在备注写明阻塞原因与所需决策。
5. **挂起** → 改为 `⏸️ 已挂起`（如需用户拍板、需基建决策）。
6. **不要**在本文件堆砌长篇技术细节 → 细节归 `docs/`，本文件只做**索引 + 状态**。
7. 与 `docs/07-audit/TODO_2026-10-08.md` 的关系：后者是**历史存档**（含每项改动明细），本文件是**活台账**。状态冲突时**以本文件为准**。
