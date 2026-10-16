# ATS-NEW 全局待办台账（TODO）

> **单一事实源（Single Source of Truth）**：本文件是全项目待办事项的**唯一权威台账**。
> **维护纪律**：每完成一项任务，**必须立即**在本文件标记 ✅ 并更新进度统计，禁止只在会话/记忆里口头完成。
> **最后更新**：2026-10-15

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
| S1 审计整改（P2 季度规划） | 1 | 0 | 0 | 10 | 1 |
| S2 前端工程化 | 5 | 0 | 0 | 2 | 0 |
| S3 测试与质量 | 3 | 0 | 0 | 1 | 0 |
| S4 运维与安全 | 2 | 0 | 0 | 0 | 0 |
| **合计** | **10** | **0** | **0** | **56** | **1** |

**完成率**：56 / 67 ≈ **83.6%**

> 📌 每次状态变更须同步更新本表，否则视为台账失效。

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
