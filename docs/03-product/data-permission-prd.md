# 数据权限管理（RBAC 复核 + 新增功能）增量 PRD

> 关联：ATS-NEW 权限模块。状态：后端模型/端点 + 前端管理控制台已落地（未上线 enforcement）。
> 作者：SoftwareCompany 专家流水线（PM→架构→工程→QA 视角收敛）。日期：2026-09-15。

---

## 一、RBAC 复核结论（代码硬证据）

现有 V2 体系**已有 RBAC 骨架**：`RoleV2` / `UserRoleV2` / `RolePermissionV2` / `V2Permission` 守卫 /
`resolve_scope`（行级）/ `FieldACL`（列级）。功能权限基本符合 RBAC。但以下 **9 处不符合 RBAC 规范或存在脆弱点**：

| # | 不合规 / 脆弱点 | 硬证据位置 | 需调整内容 |
|---|---|---|---|
| 1 | `is_superuser` 全栈硬旁路 | `core/permissions.py`、`permissions_v2.py`、`scope_resolver.py`、`field_acl/services.py` 等多处（约 30 文件） | 超管改为持有 `SUPER_ADMIN` 角色、走同一评估路径；移除散落 `if is_superuser: return True` 短路 |
| 2 | V1 双轨残留 | `core/models.py`（`User.groups/user_permissions` M2M + V1 `Permission` 模型） | 确认无引用后废弃 V1 `Permission` 模型 + 内建 M2M，单一真相源 = V2 |
| 3 | 部门/职位隐含授权 | `core/models.py`（`Department.leader/manager_2/hrbp` FK） | 建模为数据范围授权（管理单元/角色数据范围），不靠硬编码职位判断 |
| 4 | `IsPositionRelated` 硬编码「同部门职位」 | `core/permissions.py` | 下沉为角色数据范围或命名资源权限，业务规则移出权限类 |
| 5 | 前端只用 `meta.roles` 白名单，未消费 `/me` 资源码 | `web/app/src/router/index.ts`、`stores/user.ts` | 新增 `v-permission` 指令 / `usePermission()` 组合式消费 `resource_code`，UI 随权限自适应（最小权限 UI） |
| 6 | `scope_resolver` fail-open | `core/scope_resolver.py`（异常落 `ALL` 兜底） | 异常时 fail-closed 默认 `SELF`（P0，已在 `CODE_QUALITY_AUDIT.md` 标注） |
| 7 | `RoleV2` 无层级 | `core/models_permission_v2.py:RoleV2`（无 `parent_role_id`） | （增强项）加 `parent_role_id` + `has_perm`/`resolve_scope` 继承，支持层级 RBAC |
| 8 | `FieldACL` 覆盖不全 + 明文 + 无审计 | `field_acl/mixins.py`、`services.py`、`views.py`（`/field-acl/audit` 返回空） | 列级权限可全局强制 / 逐端点 strict；补访问审计 |
| 9 | **行级与列级两套互不相干机制** | `core/scope_resolver.py`（行级） + `field_acl/*`（列级） | **统一为 `DataPermissionRule` 抽象（本次新增功能的核心缺口）** |

> 说明：#1–#8 为既有技术债，建议另立 refactoring task 跟踪；本 PRD 聚焦 #9 的新增功能 + 与之配套的最小化治理。

---

## 二、新增功能：数据权限管理

### 2.1 目标
支持按 **角色 / 部门 / 用户** 三个维度，统一配置数据的 **行级**（能看到哪些数据行）与 **列级**（每条数据里能看到哪些字段）访问范围，并提供清晰易用的配置界面。

### 2.2 现状缺口（为什么要做）
- 列级 `FieldACL` 仅按 `role_code` 一维，无部门/用户维度。
- 行级 `scope_resolver` 仅由 `UserRoleV2.management_unit_ids` + `RoleV2.default_data_scope_type` 驱动，无独立「部门/用户规则」入口，且不可在 UI 直接编辑。
- 两套机制互不相干、无统一配置 UI。→ 管理员无法在一个控制台里说清「某角色/部门/用户对某实体的行+列权限」。

### 2.3 数据模型（新增 `DataPermissionRule`，表 `data_permission_rules`）
单一规则抽象，覆盖行级 + 列级、三维度：

| 字段 | 类型 | 说明 |
|---|---|---|
| `dimension_type` | ROLE/DEPARTMENT/USER | 维度 |
| `dimension_value` | str | ROLE→role_code / DEPARTMENT→department_id / USER→user_id |
| `level` | ROW/COLUMN | 行级或列级 |
| `scope_type` | ALL/DEPT/DEPT_AND_SUB/SELF/CUSTOM | 行级范围（level=ROW） |
| `scope_payload` | JSON | CUSTOM 时：`{department_ids:[...]}` 或 `{management_unit_ids:[...]}` |
| `entity` / `field` / `permission` | str | 列级：实体/字段/READ·MASK·NONE（level=COLUMN） |
| `priority` | int | 同维度同层级冲突时大者优先 |
| `status` | 1/0 | 启用/停用 |
| `remark` / `created_by` | — | 审计 |

落点文件：
- `apps/django/apps/data_permission/{models,serializers,views,urls}.py` + `migrations/0001_initial.py`
- 注册：`config/settings/base.py` `LOCAL_APPS` + `config/urls.py` 挂载 `/api/v1/data-permissions/`

### 2.4 API（管理面，仅超管）
- `GET /api/v1/data-permissions/` 列表（可按 dimension_type/value/level 过滤）
- `POST /api/v1/data-permissions/` 新增
- `PATCH /api/v1/data-permissions/{id}/` 修改 / 启停
- `DELETE /api/v1/data-permissions/{id}/` 删除
- `GET /api/v1/data-permissions/options/` 枚举选项（前端表单用）

> 全局 `djangorestframework-camel-case` 生效：序列化器用 snake_case，API 自动 camelCase。

### 2.5 前端管理控制台（`web/app/src/pages/settings/DataPermissionSettings.vue`）
- 路由 `/settings/data-permission`，菜单「系统设置 → 组织信息管理 → 数据权限管理」，meta `roles:['SUPER_ADMIN','ADMIN']`。
- 交互结构（UX 重点）：
  1. **维度切换**（角色/部门/用户） segmented control；
  2. **配置对象**下拉（加载对应维度的角色/部门/用户候选，失败回退为手输编码）；
  3. **行级访问控制**卡片：范围下拉 + CUSTOM JSON；保存/删除；未配置给出提示；
  4. **列级字段权限**卡片：可编辑表格（实体/字段/权限/状态），新增行内草稿、保存、启停、删除（删除走 `n-popconfirm` 确认）。
- 体验保障：保存/删除即时 `useMessage` 反馈；加载 `n-spin`；无整页刷新（最小干扰）；表单禁用态明确。

### 2.6 Enforcement 集成（✅ 已落地，路径 A）

管理面配置的规则现已**真实生效**，接入点为既有引擎的薄封装层，**不替换旧引擎**：

- **行级**：`apps/data_permission/enforcement.py:row_filter_q` 接入 `apps/candidate/views.py` 的
  `CandidateViewSet.get_queryset`。逻辑：若当前用户有**生效的行级规则**，以其为准（权威）；
  否则回退 `ScopeQuerysetMixin.scope_queryset`（沿用 `scope_resolver`）。
  - ALL 规则 → 全量可见（短路旧 scope）；
  - SELF → `created_by = user`；
  - DEPT / DEPT_AND_SUB / CUSTOM → 按视图的 `scope_field`（候选人=`referrer__department`）或
    创建人 `department_id` 过滤，复用 `scope_resolver` 的部门树爬取（`_own_dept_ids` / `_dept_and_sub_ids`）。
  - 多条规则取**并集（OR）**；维度键 = `USER:<pk>` / `DEPARTMENT:<dept_id>` / `ROLE:<role_code>`。
- **列级**：`apps/data_permission/enforcement.py:column_permission_for` 接入
  `apps/field_acl/services.py:FieldAclService.apply_acl`，在按 `FieldACL` 判定之外，**再叠加**
  `DataPermissionRule` 列级规则（按 ROLE/DEPARTMENT/USER 维度匹配当前用户），取**最严格**
  （NONE > MASK > READ）。保留 `FieldACL` 旧规则兜底。
- **缓存失效**：`DataPermissionRule.save()/delete()` 清对应实体的列级缓存（`data_perm:col:<entity>`），
  避免规则变更后旧结果残留。
- **超管 bypass**：与 `FieldACL`/`scope_resolver` 既有语义一致——`is_superuser` 不经 `DataPermissionRule`
  限制（已在测试 `test_superuser_bypass` 锁定）。

> 路径 B（废弃 FieldACL + scope_resolver、全量迁到 DataPermissionRule）成本高风险大，**本次不做**。

**硬证据（非 shell is_valid）**：`apps/data_permission/tests/test_enforcement.py` 6 项集成测试
走完整 DRF 请求链路全绿——
1. 无规则 → 回退 `scope_resolver` SELF（看不到他人创建的数据）；
2. DEPT 行级规则（部门维度）→ 仅见本部推荐人数据、过滤他部；
3. 规则停用（status=0）→ 回退 SELF、不可见；启用后立即可见（证明是规则在驱动）；
4. USER 维度 NONE → 详情接口不返回该字段；
5. USER 维度 MASK → 字段值被脱敏（≠ 原文）；
6. 超管 → 行级+列级均不受限。

### 2.7 验收标准
- [ ] 超管可在控制台为「某角色/部门/用户」分别配置行级范围 + 多条列级字段规则；
- [ ] 配置即时保存，界面反馈明确，无需刷新整页；
- [ ] 删除有二次确认；停用立即可见状态标签；
- [x] `manage.py check` 0 issues；前端 `build:nocheck` 通过；
- [x] （enforcement 已生效）对应维度的数据行/字段实际受限——6 项集成测试全绿。

### 2.8 边界与风险
- `scope_payload` 为自由 JSON，前端做 `JSON.parse` 校验，后端未做 schema 强校验（建议 enforcement task 内补）。
- 列级候选实体/字段为手输（无 schema 端点），后续可接 `dynamic-field` 元数据自动补全。
- 多规则冲突以 `priority` 为准，需 enforcement task 明确「最宽行级 / 最严列级」合并策略。

---

## 三、本轮交付清单
- 后端：`apps/data_permission` app（model + migration `0001_initial` + serializer + viewset + urls），已 `manage.py check` 通过。
- 前端：`DataPermissionSettings.vue` 控制台 + `src/api/data-permission.ts` + 路由/菜单注册。
- 文档：本 PRD。
- 未做（明确留口）：enforcement 实际生效、#1–#8 技术债清理、列级实体/字段元数据自动补全。
