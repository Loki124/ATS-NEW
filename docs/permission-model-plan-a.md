# 权限模型统一改造 — 方案 A 实施计划

> 目标：把北森「管理单元 + 数据范围」的精华吸收进 ATS-NEW，但不照搬其全套 HCM 权限（身份版本/管理员委托/动态授权引擎）。
> 定位：**RBAC（RoleV2 + RolePermissionV2） + 组织数据范围（ManagementUnit） + 规则引擎（DataPermissionRule）** 三套收敛到管理单元 UI 一处编排。
> 状态：规划稿（2026-09-15，兵哥确认执行方案 A）。

---

## 0. 范围界定

**纳入（In scope）**
1. `ManagementUnit` 加层级（树）+ 人员范围（动态条件）。
2. `UserRoleV2` 的数据范围从「全局 unit 列表」升级为「按应用/模块分组」。
3. 管理单元 UI 成为 `DataPermissionRule` 的可视化配置入口之一（不另起 runtime）。
4. `scope_resolver` 适配按应用取范围。

**不纳入（Out of scope，避免过度设计）**
- 北森的「身份版本（V1/V2）」「管理员可授权身份委托」「动态授权条件规则引擎」——ATS 单产品暂不需要。
- 新建独立 ABAC 引擎（已有 `DataPermissionRule` 复用）。

**必须先厘清的歧义（风险 0）**
代码里「管理单元」语义有两个来源，方案 A 以 `core.ManagementUnit` 为准：
- `apps/core/models_permission_v2.py:127` `ManagementUnit` —— **被 `scope_resolver` 消费，是数据范围真实载体**，有完整 CRUD（`ManagementUnitViewSet` @ `views_permission_v2.py:197`，路由 `management-units`）。
- `apps/mou/` 桩（`MouAgreement/MouContainer/MutualExclusionGroup/MouAutomationRule`）—— MOU=合作协议语义，**未接入运行时**，前端 `MouManagement.vue` 把两者混在一个页面（MOU 管理 + 权限容器 + 自动化 + 互斥 + 审计）。
  方案 A 期间：数据范围能力只加在 `core.ManagementUnit`；`apps/mou/` 的「合作协议」语义若不使用应标记 deprecated，禁止与管理单元混淆。

---

## 1. 现状基线（已核查文件）

| 层 | 文件 | 现状 |
|---|---|---|
| 模型 | `apps/core/models_permission_v2.py:127` `ManagementUnit` | 扁平表：`system_code/unit_name/unit_type/org_scope(JSON)/include_children/status`，**无 parent_id、无人员范围** |
| 模型 | `:147` `UserRoleV2` | `management_unit_ids = JSONField`（**全局** id 列表，无按应用分组） |
| 序列化 | `serializers_permission_v2.py:45` `ManagementUnitSerializer` | 字段无 parent_id / 人员范围 |
| 序列化 | `:52` `UserRoleSerializer` | `management_unit_ids` 直接 JSONField |
| 接口 | `views_permission_v2.py:197` `ManagementUnitViewSet` | 完整 ModelViewSet，路由 `management-units`（`urls_permission_v2.py:12`） |
| 接口 | `:215` `UserRoleViewSet` | 完整 ModelViewSet，路由 `user-roles`，含 `suggest-scope` action |
| 解析 | `apps/core/scope_resolver.py:12-105` | 4 层 L1(user.management_unit_ids) > L2(role.default) > L3(tenant) > L4(SELF) |
| 规则引擎 | `apps/data_permission/models.py:46` `DataPermissionRule` | ROW/COLUMN 级、ROLE/DEPT/USER 维度、CUSTOM 范围（含 `management_unit_ids`/`department_ids`） |
| 规则执行 | `apps/data_permission/enforcement.py` | `row_filter_q`/`column_permission_for`，与 `scope_resolver`/`FieldAclService` 并存 |
| 前端 | `web/app/src/pages/settings/MouManagement.vue` | MOU/容器/自动化/互斥/审计/角色/功能 多 tab，**混合真实 ManagementUnit 与 apps/mou 桩** |
| 前端 | `settings/permission/UserRoleEditModal.vue` | 编辑 `managementUnitIds`（全局列表） |
| 前端 | `settings/UserManagement.vue` | 「权限模式 MOU/CONTAINER」+ MOU分配弹窗 = **外观桩**（上一轮结论：`serializers.py:87/114` 丢弃、`urls_stubs.py:442` echo） |

---

## 2. 表结构改动

### 2.1 `ManagementUnit` 增强（`models_permission_v2.py:127`）
```python
parent_id = models.BigIntegerField(null=True, blank=True, db_index=True, verbose_name='上级管理单元ID')  # 树形
personnel_scope = models.JSONField(null=True, blank=True, verbose_name='人员范围条件(JSON谓词)')
# 谓词语义（对齐北森图5）：
# { "op": "or"/"and",
#   "rules": [
#     {"dimension":"employment","field":"department","op":"eq","value":"<dept_id>","include_sub":true},
#     {"dimension":"employment","field":"position","op":"eq","value":"<position_id>"},
#     {"dimension":"user","field":"id","op":"in","value":[1,2,3]}
#   ] }
```
- 保留 `org_scope` / `include_children`（组织范围，与北森图4 对应）。
- 新增 `idx_mgmt_unit_parent (parent_id)`。

### 2.2 `UserRoleV2` 数据范围按应用分组（`:147`）
推荐**新增关联表**而非改 JSON schema，保持 `UserRoleV2` 干净、便于索引与迁移：
```python
class UserAppDataScope(models.Model):
    """用户-角色-应用 的数据范围（管理单元）绑定，对齐北森图12 按应用管理单元。"""
    user_id = models.BigIntegerField(db_index=True)
    role_code = models.CharField(max_length=64)
    system_code = models.CharField(max_length=32, default='recruit')
    app_code = models.CharField(max_length=32, verbose_name='应用/模块编码')  # recruit/social/campus/referral...
    management_unit_ids = models.JSONField(null=True, blank=True)
    granted_by_id = models.BigIntegerField(null=True, blank=True)
    class Meta:
        db_table = 'user_app_data_scope'
        constraints = [UniqueConstraint(fields=['user_id','role_code','app_code'], name='uk_user_role_app')]
```
- `UserRoleV2.management_unit_ids` 保留为「默认/兼容」字段（非空时对所有 app 兜底），新写入走 `UserAppDataScope`。
- 若不想加表，退路：把 `management_unit_ids` 升级为 `{"recruit":[1,2], "campus":[3]}`，但 JSON 内查询不便，不推荐。

### 2.3 `DataPermissionRule` 复用（不新建表）
管理单元 UI 保存「组织范围/人员范围」时，由后端 action 同步生成/更新 `data_permission_rules`（dimension=ROLE 或 USER/DEPT，scope_type=CUSTOM，scope_payload 含 `management_unit_ids`）。**管理单元是配置面，DataPermissionRule 是执行面。**

### 2.4 Migration
- 在 `migrations/0004_v2_apply_schema.py` 之后新建 `0005_mgmt_unit_hierarchy_and_app_scope.py`：
  - `ManagementUnit` add `parent_id` + `personnel_scope` + index。
  - 新建 `UserAppDataScope` 表。
  - 数据迁移（RunPython，幂等）：`UserRoleV2.management_unit_ids` 非空且有 role 的场景 → 写入 `UserAppDataScope(app_code='recruit', management_unit_ids=原值)`。

---

## 3. 后端 API 改动

| 端点 | 改动 |
|---|---|
| `GET /api/v1/management-units/` | 返回支持树（`parent_id` 嵌套或扁平+parent 字段）；新增 `personnel_scope` 字段 |
| `POST/PUT /api/v1/management-units/` | 接受 `parent_id` + `personnel_scope`；校验 parent 不形成环 |
| `ManagementUnitViewSet` 新增 action `sync-data-rules` | 把该单元的 org/personnel scope 同步为 `DataPermissionRule`（CUSTOM + management_unit_ids） |
| `GET/POST /api/v1/user-app-data-scopes/` | 新增 ViewSet：按 (user_id, role_code, app_code) 读写数据范围 |
| `UserRoleViewSet.suggest-scope` | 改为按 `app_code` 参数返回对应 unit 候选（`views_permission_v2.py:232`） |
| `scope_resolver.py:20` L1 | `explicit_units` 取值改为「当前请求 app_code 对应的 `UserAppDataScope.management_unit_ids`，缺则回退 `UserRoleV2.management_unit_ids`」；需把 `app_code` 透传进 `resolve_scope(user, resource_code, app_code=...)` |
| `permissions_v2.py` / `role_v2_query.py` | 资源校验与角色查询保持，不破坏 |

---

## 4. 前端页面调整

| 页面 | 改动 |
|---|---|
| `settings/MouManagement.vue` | ① 管理单元列表改树形（依 `parent_id`，对齐北森图1/2）；② 详情加「管理组织范围」（org 树勾选 + 含下级，对齐图4）与「管理人员范围」（条件构建器，对齐图5）；③ 按应用 tab 配管理单元（对齐图3 公共/社保/审批中心/360）；④ 保存时调用 `sync-data-rules`；⑤ **移除与 `apps/mou/` 桩的混淆**，页面只编排 `core.ManagementUnit` |
| `settings/permission/UserRoleEditModal.vue` | `managementUnitIds` 改为「按应用分组多选」（recruit/campus/social/referral… 各一组），写入 `user-app-data-scopes`（对齐北森图12） |
| `settings/PermissionManagement.vue` ↔ `UserRolesTab.vue` | 适配 per-app scope 展示与保存 |
| `settings/UserManagement.vue` | 上一轮结论落地：移除「权限模式 MOU/CONTAINER」外观桩（或标注「待上线」）；其「用户授权/角色」真实部分保留；MOU分配入口统一跳 `MouManagement.vue` 真实管理单元 |
| `settings/DataPermissionSettings.vue` | 与管理单元 UI 合并/对齐，避免 `DataPermissionRule` 与 `ManagementUnit` 两套并行配置面 |
| 通用 | 前端统一走 camelCase，序列化器全 snake_case（项目铁律：camelCase 反模式会假绿，必须以运行中服务端 POST 实测验证） |

---

## 5. 数据迁移与种子

- **旧数据**：`UserRoleV2.management_unit_ids` 全局列表 → `UserAppDataScope(app_code='recruit', ...)`。脚本幂等、支持 `--if-empty`。
- **层级**：已有 `ManagementUnit` 记录 `parent_id=null`（根）；`seed_v2_init.py` 补「集团/子公司/部门」示例层级。
- **环校验**：`parent_id` 保存时禁止指向自身或后代。
- 迁移在 compose 后端启动链 migrate 之后自动跑，失败仅告警不阻断（沿用院校库/专业库策略）。

---

## 6. 测试点（兵哥要求：运行服务端实测，非 shell `is_valid` 假绿）

**单元/集成**
- `test_models_v2.py`：新增 `parent_id` 树、personnel_scope 写入。
- `test_api_v2_user_role.py`：补 `UserAppDataScope` 按应用范围读写断言（参考现有 `:29/:36` 写法）。
- `test_scope_v2_regression.py`：新增「per-app 取范围」用例，验证 `app_code` 透传后 L1 命中正确 unit。
- `data_permission/tests/test_enforcement.py`：补「管理单元 sync → DataPermissionRule → row_filter_q 生效」链路（`enforcement.py:95` `row_filter_q`）。

**运行时实测（必做）**
- 启后端 `:8000` + 前端 `:5212`，浏览器/Playwright 真实 POST `/api/v1/management-units/`、`/api/v1/user-app-data-scopes/`、`/api/v1/management-units/{id}/sync-data-rules/`。
- `getComputedStyle` + 列表数据核对管理单元树/人员范围/按应用范围真实落库。

**回归**
- `scope_resolver` 4 层不退化（尤其 R8 部门越权修复，`:77/:83`）。
- `DataPermissionRule` 列级脱敏（`enforcement.py:150`）与 `FieldAclService` 叠加仍取最严。
- 软删 `deleted_at` 跨表覆盖（P0 铁律）+ 变异测试守卫。

---

## 7. 里程碑与门禁

**里程碑**
- M1 表结构 + migration + 种子（后端，不碰运行时）。
- M2 API：ManagementUnit 树/人员范围 + UserAppDataScope + sync-data-rules + scope_resolver 适配。
- M3 前端：MouManagement 树/组织范围/人员范围/按应用；UserRoleEditModal per-app。
- M4 联调 + 运行实测 + 测试 + 清理 `apps/mou/` 桩混淆。

**提交门禁（兵哥铁律）**：每改完一个 bug/功能点 → `stylelint` → `npm run build:nocheck` → 磁盘 grep 验证落盘 → `git add` 逐路径（**禁止 `git add -A`**）→ commit → 写日志。系统级操作先列选项拍板。

**主要风险**
1. `ManagementUnit`（真实）vs `apps/mou/`（桩）语义混淆——先做风险 0 厘清。
2. per-app scope 改造触及 `scope_resolver` 所有调用点（CandidateViewSet 等），回归面大。
3. 两套数据范围配置面（ManagementUnit UI vs DataPermissionSettings）——必须合并，否则运营混乱。

---

## 8. 执行记录（里程碑状态）

| 里程碑 | 状态 | 提交 | 关键交付 |
|---|---|---|---|
| M1 表结构 + migration + 种子 | ✅ 完成 | `5bc9c4e` | `ManagementUnit.parent_id`+`personnel_scope`、`UserAppDataScope` 表、`0008` 迁移 + 幂等回填、模型测试 7 passed |
| M2 后端 API | ✅ 完成 | `df3bf46` | `ManagementUnitSerializer`(parent/personnel + 防环)、`EnvelopeWriteMixin`(补写接口 `{success,data}` 信封)、`tree`+`sync-data-rules` action、`UserAppDataScopeViewSet`+upsert、`suggest_scope` 透传 `app_code`、`scope_resolver` L1 per-app 优先；运行中服务端实测 8 项全过 + pytest 12 passed |
| M3 前端 | ✅ 完成 | 本提交 | `MouManagement.vue` 重写为聚焦的「管理单元」页（树形层级 + 组织范围 orgScope + 人员范围 personnelScope + 按应用数据范围 UserAppDataScope + 同步到 DataPermissionRule 按钮），删除 apps/mou 桩 tab 与重复的 RBAC tab（roles/functions/menus 已在 PermissionManagement 存在）；`UserRoleEditModal` 改为按应用(recruit/campus/social/referral)分组多选写入 UserAppDataScope，全局 managementUnitIds 取 recruit 兜底；移除 `UserManagement` MOU 外观桩（权限模式字段 + MOU分配弹窗 + 假 /permissions/user-mous/ 调用）。新增 `user-app-data-scope.ts` API 客户端、`management-unit.ts` 扩展 tree/sync。eslint 0 error + `build:nocheck` 通过 + 运行中服务端 user-app-data-scopes 生命周期实测全过 |
| M4 联调 + 测试 + 清理 | ⏳ 待开始 | — | 运行实测；`sync-data-rules` 落地的 `management_unit_ids` 接进 `enforcement.row_filter_q`(当前 `row_filter_q` 只消费 `department_ids`)；清理 `apps/mou/` 桩混淆；两套配置面合并 |

**M2 关键坑（已修）**：
- `ManagementUnitViewSet` 原 create/update/delete **未包 `{success,data}` 信封** → 前端 `r.data.data` 为 undefined（假绿陷阱），已用 `EnvelopeWriteMixin` 统一。
- `@action` 默认 `url_path` = 方法名下划线（`sync_data_rules`），与全站 hyphen 风格 action 不一致 → 显式 `url_path='sync-data-rules'`。
- `scope_resolver.resolve_scope` 新增 `app_code` 参数**必须置于 `resource_code` 之后**，旧 10+ 调用点（均 `resolve_scope(user)` 或 `resolve_scope(user, code)`）才无感兼容。
