# ATS-NEW 侧事实侦察报告（迁移「校招生管理助手」）

> 侦察员：at-scout ｜ 只读记录，**不含方案建议**
> 宿主根：`/Users/loki/WorkBuddy/Worktrees/ATS-NEW/main-333116a0`
> 约定：「事实」= 有代码依据（含文件绝对路径 + 行号）；「未找到」= 已检索但无。

---

## 一、菜单体系

### 1.1 事实：菜单是**前端硬编码数组**，不是后端菜单表

主导航侧边栏：`web/app/src/pages/Layout.vue:372-423`（`menuOptions` computed）

```ts
// Layout.vue:372-423
const menuOptions = computed(() => {
  const base = [
    { key: '/dashboard', label: '工作台', icon: renderIcon(SpeedometerOutline) },
    { key: 'demand-position', label: '需求与职位', icon: ..., children: [
      { key: '/demands', label: '需求管理' },
      { key: '/positions', label: '职位管理' },
    ]},
    { key: 'candidate', label: '候选人', ..., children: [
      { key: '/candidates' }, { key: '/screenings' }, { key: '/talent-pool' },
      { key: '/my-resumes' }, { key: '/onboardings', label: '待入职' },
    ]},
    { key: 'interview', label: '面试管理', ..., children: [
      { key: '/interviews' }, { key: '/invitations' },
    ]},
    { key: '/report', label: '数据中心' },
  ]
  if (systemStore.isCampus) {
    base.push({
      key: 'campus', label: '校招专属', icon: renderIcon(PeopleOutline),
      children: [
        { key: '/settings/campus-ambassador', label: '校园大使' },
        { key: '/settings/campus-session',      label: '宣讲会' },
      ],
    })
  }
  // G4: 按功能权限裁剪菜单（fail-open）
  return filterMenuByPermission(base as MenuOption[], canAccess) as any[]
})
```

设置中心二级菜单：`web/app/src/pages/settings/SettingsLayout.vue:96-305`（`rawSubMenuOptions`）
5 个 `type:'group'` 分组：`g-basic`(基本信息) / `g-process`(过程管理) / `g-speedup`(招聘提速) / `g-content`(内容管理) / `g-misc`(其他)；
可展开父项（非 group）如 `g-company` / `g-org` / `g-user` / `g-permission` / `g-candidate-info` / `g-demand` / `g-position-info` / `g-basic-data`。
设置菜单同样经 `filterMenuByPermission` 裁剪（`SettingsLayout.vue:307-310`）。

### 1.2 事实：菜单 key 约定

| 层级 | 约定 | 依据 |
|---|---|---|
| 一级分组 | 非 `/` 开头，如 `demand-position`、`g-basic` | `Layout.vue:376` / `SettingsLayout.vue:97` |
| 叶子 | **必须以 `/` 开头且等于路由 path** | `Layout.vue:578` `handleMenuClick` 只处理 `key.startsWith('/')`；`permissionMenu.ts:141` 同款判定 |
| 图标 | `@vicons/ionicons5` + `renderIcon()` → `() => h(NIcon, null, {default: () => h(icon)})` | `Layout.vue:442-444` |
| label | `Layout.vue` 主菜单为**中文硬编码字面量**；`SettingsLayout.vue` 全量走 `t('pages.settings.SettingsLayout.sXX')` | 两者不一致，是既有事实 |

### 1.3 事实：**没有后端菜单表**

- 未找到任何 `Menu` / `MenuItem` Django 模型。
- 菜单相关的后端概念只有 `PermissionResource`，`resource_type` 枚举含 `'MENU'`（`apps/django/apps/core/models_permission_v2.py:33-39`），但**不含 path 字段**（字段：`system_code`/`resource_code`/`resource_name`/`resource_type`/`parent_code`/`module`/`sort_order`/`status`/`ext_fields`/`created_at`）。
- 前后端关联靠**前端 `utils/permissionMenu.ts` 里的路径→资源码静态表**，不是 DB 驱动。

### 1.4 事实：「校园招聘」现有菜单长什么样

| 位置 | 内容 |
|---|---|
| `Layout.vue:410-420` | 仅当 `systemStore.isCampus` 时追加分组「校招专属」，含 2 项：校园大使 / 宣讲会 |
| `permissionMenu.ts:81-83` | 三条前缀均映射到同一码 `recruit:settings:campus-control:menu:view`：`/settings/campus-control`、`/settings/campus-ambassador`、`/settings/campus-session` |
| `SettingsLayout.vue:227` | `/settings/campus-control`（校招管控）是「过程管理」组下的**平级叶子项**（不在校招专属组内） |
| `router/index.ts:152-155` | 4 条 campus 相关 settings 路由：`campus-control` / `campus-ambassador` / `campus-session`（后两者 `meta.roles=[SUPER_ADMIN,ADMIN,HRBP]`） |

**未找到**：独立的 `/campus/*` 前端路由组；校招专属分组当前只有 2 个节点，且都是 settings 配置页。

---

## 二、权限体系

### 2.1 事实：数据模型（V2，唯一真相源）

`apps/django/apps/core/models_permission_v2.py`

| 模型 | 行 | db_table | 关键字段 | 唯一约束 |
|---|---|---|---|---|
| `PermissionResource` | :28 | `permission_resources` | `system_code`(默认 recruit)、`resource_code`、`resource_name`、`resource_type`(MENU/BUTTON/FIELD/API)、`parent_code`、`module`、`sort_order`、`status`、`ext_fields` | `resource_code` unique |
| `PermissionTemplate` | :59 | `permission_templates` | `template_code`、`template_name`、`permission_codes`(JSON list)、`is_system`、`status` | `template_code` unique |
| `RoleV2` | :80 | `roles` | `system_code`、`role_code`、`role_name`、`template_code`、`default_data_scope_type`、`is_system`、`status` | `(system_code, role_code)` |
| `RolePermissionV2` | :111 | `role_permission` | `role_code`(str 非 FK)、`resource_code`(str 非 FK)、`system_code` | `(role_code, resource_code)` |
| `ManagementUnit` | :133 | `management_units` | `unit_name`、`unit_type`、`parent_id`、`code`、`org_scope`、`data_range`、`person_data_range`、`include_children`、`status` | — |
| `ManagementUnitMember` | :171 | `management_unit_members` | `member_type`(DEPT/USER/PERSON)、`department_id`、`user_id`、`person_id`、`app_code`、`include_children` | — |
| `UserRoleV2` | :211 | `user_roles` | **`user` FK→core.User**（db_column='user_id'）、`role_code`(str)、`system_code`、`management_unit_ids`、`app_data_scopes`、`valid_from`/`valid_to`、`granted_by_id`、`granted_at` | `(user, role_code)` |
| `TenantConfig` | :261 | `tenant_configs` | `system_code`、`config_key`、`config_value`(JSON)、`description` | `(system_code, config_key)` |

V1 的 `Role` / `UserRole` / `RolePermission` / `Permission` 模型**已于 2026-08/09 删除**（`core/models.py:6-9` 注释）。

### 2.2 事实：权限码命名规范与真实样例

格式：`recruit:{模块}:{资源}:{动作}`，动作后缀 `list|create|edit|delete|export|menu:view`。

来源：`apps/django/apps/core/management/commands/seed_v2_init.py:14` 起 `RESOURCES` 四元组 `(resource_code, resource_name, resource_type, module)`。

真实样例（seed_v2_init.py 行号）：
```
224: ('recruit:settings:campus-control:menu:view', '校招管控菜单', 'MENU', 'settings'),
225: ('recruit:settings:campus-control:edit',      '编辑校招管控',   'BUTTON','settings'),
15 : ('recruit:candidate:menu:view', '候选人菜单', 'MENU', 'candidate')
16 : ('recruit:candidate:list',     '候选人列表', 'BUTTON','candidate')
17 : ('recruit:candidate:create',   '新增候选人', 'BUTTON','candidate')
364: ('recruit:settings:dictionary:menu:view', '数据字典', 'MENU','settings')
390: ('recruit:settings:job_title:menu:view',  '职务菜单', 'MENU','settings')
146(views.py): 'recruit:settings:department:create' / ':edit' / ':delete'
```
模板常量 `CONFIG_CODES`（`seed_v2_init.py:~355-420`）承载全部 settings 类权限码；`TEMPLATES`（:421+）定义 `TMPL_ADMIN` / `TMPL_DIRECTOR` / `TMPL_SPECIALIST` / …

⚠️ **事实**：模板里目前**没有 campus 相关码**（:393-394 仅 `campus-control` 三个码挂在某模板 codes 中）；且 `campus`（大使/宣讲会）**没有独立权限码**，复用 `campus-control`。

### 2.3 事实：后端校验机制

`apps/django/apps/core/permissions_v2.py`
- `V2Permission(BasePermission)`（:61）——主守卫。三种声明形态（优先级递减）：
  1. `permission_required_map: {action: code}`
  2. `v2_self_service_actions: (action, ...)` 白名单
  3. `permission_required = [codes]` 原样校验 / `= 'code'` 按 action 派生后缀（`ACTION_SUFFIX` :16-23，`CUSTOM_ACTION_SUFFIX='edit'`）
- **未声明任何码时**：读放行、写**拒绝**（`_reject_undeclared_write` :151，受 `settings.V2_STRICT_WRITE_GUARD` 开关控制）
- 派生码若不在 `PermissionResource` 中 → 回退原码 + warning（`_derive` :132-149）
- `ScopeQuerysetMixin`（:170）——数据行级过滤 + `recruit_type` 写侧强制注入（`perform_create`/`perform_update` :245-259）
- 底层判定：`apps/core/permission_check.py:9` `has_perm(user, resource_code)`（无缓存，每次重查，多角色 UNION）
- 角色工具：`apps/core/role_v2_query.py`，`is_super_admin` / `user_has_role` / `user_has_any_role`；层级常量 `HRBP_TIER=('SUPER_ADMIN','HRBP')`、`HR_TIER=('SUPER_ADMIN','HRBP','HR')`（:22-24）

`apps/django/apps/core/permissions.py`（V1 遗留 + 通用类）
`IsAuthenticatedDenyByDefault`(:20，**全局默认**，`config/settings/base.py:360-362`) / `ResourceScoped`(:42) / `IsAuthenticated`(:86) / `IsSuperAdmin`(:91) / `IsHRBP`(:99) / `IsHROrAbove`(:107) / `HasProcessPermission`(:115) / `UserViewPermission`(:207) / `MOUVIEWSetPermission`(:228) / `ScopedQuerysetMixin`(:163，已被 V2 版取代)

数据权限（行/列级）：`apps/data_permission/`（`models.py` 有 `DataPermissionRule` / `DataPermTemplate` / `DataPermissionAction` / `DataPermissionActionPreset` / `ColumnPermission` 等 10 个模型；`enforcement.py` 的 `ensure_writable()` / `role_entity_scope_q()`；`action_registry.py` 带 5 分钟 TTL 缓存）

实体→scope 字段映射表：`apps/core/entity_scope.py:23-33`（`ENTITY_SCOPE`），已登记 10 个 entity（candidate/application/demand/position/offer/interview/onboarding/invitation/talent_pool/referral），ViewSet 的 `scope_field`/`scope_creator_field` 必须与之保持一致。

### 2.4 事实：前端权限控制

| 机制 | 文件 | 说明 |
|---|---|---|
| 菜单/路由级 | `web/app/src/utils/permissionMenu.ts` | `MENU_PERMISSION_RULES`（:26-102，静态 `{prefix, code}` 数组）+ `permissionForPath()`（最长前缀）+ `filterMenuByPermission()`（:128） |
| 路由守卫 | `web/app/src/router/index.ts:248-322` `routeGuard` | ① token ② `await userStore.ensureReady()` ③ `meta.roles` 白名单 ④ `meta.permission ?? permissionForPath(path)` |
| 元素级指令 | `web/app/src/directives/permission.ts` | `v-permission="'recruit:x:edit'"` 隐藏；`v-permission.disable` 置灰；数组=任一命中 |
| 组合式 | `web/app/src/composables/usePermission.ts` | `canAccess`(fail-open) / `hasPermission` / `hasAnyPermission` / `hasAllPermissions` / `isPermissionConfigured` |
| 角色常量 | `web/app/src/utils/role.ts` | `ROLE`(:53)、`ROLE_GROUPS`(:61)、`ROLE_PRIORITY`(:38)、`deriveRoleType()`(:84) |

**fail-open 是硬约定**：`/me.permissions` 为空数组 = 「从未配置功能权限」→ 前端全部可见，交由后端 403 兜底（`permissionMenu.ts:9-13`、`usePermission.ts:38-45`）。

**权限来源**：`GET /api/v1/auth/me`（`apps/django/apps/core/views_auth.py:208-316`）
返回 `roles: string[]`、`permissions: string[]`（超管取全部 `PermissionResource`）、`management_unit_ids`、`department_ids`、`data_scope`、`uiSettings`。

`UserRoleV2._apply_role_type` 写入路径：`apps/django/apps/core/serializers.py:127-149`（覆盖式，先删后建，`transaction.atomic`）。

**未找到**：后端菜单 CRUD API（`/menus` 之类）。

---

## 三、用户与部门模型（迁移关键）

### 3.1 事实：`User` — `apps/django/apps/core/models.py:39-177`

`class User(AbstractUser)`，**表名沿用 Django 默认 `auth_user`**（`:154` 注释明确：`AUTH_USER_MODEL` 未设置，MUST NOT 重命名）。

| 字段 | 行 | 类型 | 说明 |
|---|---|---|---|
| `employee_id` | :55 | Char(50) unique null | 工号 |
| `phone` | :56 | Char(20) index null | 手机号 |
| `avatar` | :57 | URL(500) null | |
| **`department`** | **:59** | **FK→Department**, SET_NULL, related_name=`members` | ✅ 有部门外键 |
| **`direct_manager`** | **:66** | **FK→self**, SET_NULL, related_name=`subordinates`, verbose_name=「直接上级」 | ✅ 有直属上级 |
| `position_title` | :75 | Char(100) null | 职务 |
| `level` | :76 | Char(50) index null | 职级 |
| `bu_president` / `solid_vp` / `dotted_vp` | :79/:86/:93 | FK→self | BU 总裁 / 实线 VP / 虚线 VP |
| `moka_user_id` | :102 | Char(100) index | 摩卡同步 |
| **`user_type`** | **:105** | choices `INTERNAL`(内部员工)/`EXTERNAL`(外部用户)，默认 INTERNAL，index | 唯一枚举字段 |
| `uuid` | :114 | UUIDField unique default=uuid4 editable=False | 对外稳定 ID |
| `last_assignment_at` | :123 | DateTime null index | 抢单用 |
| **`deleted_at`** | :126 | DateTime null index | 软删 |
| `last_login_at` / `created_at` / `updated_at` | :129-131 | | |
| `token_version` | :135 | PositiveInteger default 0 index | 改密/禁用即撤销 refresh |

继承自 AbstractUser：`username` / `password` / `first_name` / `last_name` / `email` / `is_active` / `is_staff` / `is_superuser` / `is_superuser` 等。

方法：`is_deleted`(property :167) / `full_name`(property :171, `get_full_name() or username`) / `soft_delete()`(:174，同时置 `is_active=False`)
`Meta.indexes`：`(department, is_active)`、`(level)`

**结论**：用户模型**已有**「部门外键」+「直属上级」，**已有**一个身份枚举字段 `user_type`（INTERNAL/EXTERNAL，语义是「内部员工/外部用户」，**不是**导师/班主任这类业务身份）。业务身份承载者是 `UserRoleV2.role_code`。

### 3.2 事实：`Department` — `apps/django/apps/core/models.py:180-279`

`class Department(models.Model)`，`db_table='departments'`（:229）

| 字段 | 行 | 说明 |
|---|---|---|
| `id` | :182 | **Char(32) PK**，nanoid(21) |
| `name` | :183 | Char(100) |
| `code` | :184 | Char(50) unique，**自动生成 `D%06d`**（`_next_department_code` :249） |
| `parent` | :185 | **FK→self**，related_name=`children` ✅ 树形 |
| `path` | :192 | Char(500) 形如 `/root/dept1/dept2/` |
| `sort_order` | :193 | Integer |
| `leader` / `manager_2` / `manager_3` / `hrbp` | :195/:202/:209/:216 | 4 个 FK→User：部门负责人 / 负责人2 / 分管VP / HRBP |
| `is_active` | :224 | Boolean index |
| `created_at` / `updated_at` | :225-226 | |

`save()`(:237) 自动补 id/code/path；`get_ancestors()`(:264) / `get_descendants()`(:273)；`ordering=['sort_order','name']`。
**注意**：Department **没有 `deleted_at`**（硬删）。

### 3.3 事实：`UserPreference` — `models.py:283-311`
`user` OneToOne → `settings` JSONField；`get_for_user()`(:304) 取或建；`get_menu_layout()`(:309) 读 `menu_layout`（`side`|`top`）。

### 3.4 事实：用户列表 API

路由：`apps/django/apps/core/urls.py:19-23` → `router.register(r'users', UserViewSet)` + `router.register(r'departments', DepartmentViewSet)`；FE 兼容 alias `/users/departments/`（:31）。

`UserViewSet`（`apps/django/apps/core/views.py:40-130`）：

| 项 | 行 | 值 |
|---|---|---|
| 基类 | :40 | `EnvelopeModelViewSet`（`EnvelopeWriteMixin + ModelViewSet`，**不含 ScopeQuerysetMixin**） |
| queryset | :42 | `User.objects.filter(deleted_at__isnull=True).select_related('department','direct_manager')` |
| serializer_class | :43 | `UserSerializer`；但 `list()`(:100-103) **实际换成 `UserMinimalSerializer`（脱敏）** |
| permission_classes | :44 | `[UserViewPermission]`（不是 V2Permission） |
| pagination_class | :45 | `StandardResultsSetPagination` |
| filter_backends | :46 | DjangoFilterBackend + SearchFilter + OrderingFilter |
| **filterset_fields** | **:47** | **`['department', 'level', 'is_active']`** ← **无 `direct_manager`、无 `user_type`** |
| search_fields | :48 | `username, employee_id, phone, email, first_name, last_name` |
| ordering_fields / ordering | :49-50 | `created_at, username` / `['username']` |
| 额外筛选 | :56-58 | `?user_type=INTERNAL|EXTERNAL`（手写，非 filterset） |
| 行级可见性 | :60-62 | 超管 / `HRBP_TIER` → 全量；其他角色 → 仅自己 |
| 自定义 action | :105-117 | `GET /users/active/`（在职，脱敏）；`POST /users/{id}/soft_delete/`（`permission_classes=[IsSuperAdmin]`） |
| destroy | :119-130 | 统一改软删（因大量 FK `on_delete=PROTECT`，硬删会 ProtectedError 500） |

`UserSerializer`（`apps/django/apps/core/serializers.py:32-190`）`fields`（:57-74）：
`id, username, first_name, last_name, employee_id, phone, avatar, full_name, email, department, department_name, direct_manager, position_title, level, bu_president, solid_vp, dotted_vp, moka_user_id, user_type, uuid, is_active, last_login_at, created_at, updated_at` + write_only: `real_name, role_type, permission_mode, wechat_work_*, mocha_*, status`
→ `to_representation`(:77) 派生 camelCase：`realName`、`status`(ACTIVE/LOCKED/INACTIVE)、`roleType`(:85，读 `UserRoleV2.role_code` 首值，兜底 `'HR'`)、`permissionMode='MOU'` 等。
→ `to_internal_value`(:98) 收 FE camelCase 并映射（`real_name`→first/last_name；`status=='ACTIVE'`→`is_active`）。

`UserMinimalSerializer`（:193-240）`fields`：`id, username, full_name, email, phone, employee_id, department, moka_user_id, is_active, created_at`
派生：`realName`、`status`、`roleType`（读 `context['role_map']`）、`roleNames`(:229，读 `context['role_names_map']`)、`userType`(:231)、`uuid`、`permissionMode`、`wechatWork*`、`mocha*`
⚠️ **无 `direct_manager`**（列表页看不到上级）。

`DepartmentViewSet`（`views.py:133-209`）：`permission_classes=[V2Permission]`，`permission_required_map`(:146-151) 显式 create/edit/delete；`filterset_fields=['parent','is_active']`、`search_fields=['name','code']`；action `GET /departments/{id}/members/`(:184)、`GET /departments/{id}/tree/`(:195)。
`DepartmentSerializer`（`serializers.py:243-297`）`fields`：`id, name, code, parent_id, parent_name, path, sort_order, manager_id, manager_2_id, manager_3_id, hrbp_id, is_active, status, children_count, created_at, updated_at`

**前端部门 store**：`web/app/src/stores/department.ts`（Pinia，5 分钟 TTL 缓存，`GET /departments/`，接口 `getById`/`getByCode`/`invalidate`）

**未找到**：任何「按 direct_manager 查询下属」的接口或前端使用（全前端 0 处 `directManager`）。

---

## 四、数据字典模型（apps/dictionary）

### 4.1 事实：模型 — `apps/django/apps/dictionary/models.py`

`DictionaryType(FullAuditModel, UUIDModel)`（:18）
| 字段 | 行 | 说明 |
|---|---|---|
| `code` | :21 | Char(64) **unique** |
| `name` | :22 | Char(128) |
| `english_name` | :23 | Char(128) default='' |
| `description` | :24 | Text default='' |
| `dict_number` | :25 | Char(32)，**自动 `D{n+1}`**（`_next_dict_number` :47，软删行不计数） |
| `is_system` | :26 | Boolean，系统预置 |
| `is_enabled` | :27 | Boolean default True |
+ 继承：`id`(nanoid 21 PK)、`created_at`、`updated_at`、`deleted_at`、`created_by`、`updated_by`
+ `save()`(:37)：种子期 `is_seed_active()` 自动 `is_system=True`
+ `CODE_PATTERN = ^[A-Za-z0-9_]+$`

`DictionaryItem(FullAuditModel, UUIDModel)`（:60）
| 字段 | 行 | 说明 |
|---|---|---|
| `type` | :63 | FK→DictionaryType, CASCADE, related_name=`items` |
| `parent` | :69 | FK→self, CASCADE, related_name=`children` ✅ 树形 |
| `key` | :76 | Char(64) |
| `value` | :77 | Char(128) |
| `english_name` | :78 | Char(128) |
| `description` | :79 | Text |
| `sort_order` | :80 | Integer |
| `is_active` | :81 | Boolean |
| `is_system` | :83 | Boolean index（预置项不可改/不可停用） |
+ `unique_together = [('type','key')]`(:89)，`ordering=['type__code','sort_order','key']`

### 4.2 事实：注册 / seed 机制

- `apps/dictionary/registry.py`：`SEED_REGISTRY = []`(:8)、`register_dictionary_seed(seeder)`(:11，去重)、`run_dictionary_seeds()`(:17，`set_seed_active(True)` 包裹，finally 复位)
- `apps/dictionary/apps.py`：`DictionaryConfig.ready()`(:21) import `apps.dictionary.seeds` 的 8 个 seed 函数 → 逐个 `register_dictionary_seed` → `post_migrate.connect(_seed_dictionary_on_post_migrate, sender=self, weak=False)`(:48)
- `apps/dictionary/seed_context.py`：`is_seed_active()` / `set_seed_active()`
- `apps/dictionary/seeds.py`：元组列表常量 + `_seed_type(code, name, english_name, description, items)`(:98) 幂等（`update_or_create`）
  现有 8 类：`EDUCATION` / `JOB_CATEGORY` / `RECRUIT_CHANNEL` / `OFFBOARD_REASON` / `CONTRACT_TYPE` / `POSITION_FAMILY` / `POSITION_CATEGORY` / `POSITION_SUBCATEGORY`
- 另一注册方：`apps/channel/apps.py`（也调 `register_dictionary_seed`）

### 4.3 事实：新增一类字典项需动的文件

1. `apps/django/apps/dictionary/seeds.py` —— 加 `XXX_ITEMS = [(key, 名称, 英文名, sort_order), ...]` + `def seed_xxx_type(): _seed_type('XXX_CODE', '中文名', 'English', '描述', XXX_ITEMS)`
2. `apps/dictionary/apps.py:28-46` —— 在 `ready()` 的 import 元组加 `seed_xxx_type`，并加一行 `register_dictionary_seed(seed_xxx_type)`
3. 业务模型字段用 `choices` 或存 key，展示时读字典（既有范式：`DictionaryItem.__str__` = `{type.code}.{key} · {value}`）
4. **dictionary 模块本身零改动**（registry/模型/views 均不用动）
5. 若要走管理页：新建视图无需改动，`/api/v1/dictionary-types/` + `/api/v1/dictionary-items/` 通用可用

### 4.4 事实：字典 API
`apps/dictionary/urls.py:7-10`：`dictionary-types`（`lookup_field='code'`）、`dictionary-items`
`DictionaryTypeViewSet`（`apps/dictionary/views.py:65`）：`permission_required='recruit:settings:dictionary:list'`、`permission_required_map` create/edit/delete(:71-76)、查询参数 `q/search`、`type=system|custom`、`is_enabled=true|false`(:101-116)；系统预置字典**不可删除**(:85)、**不可停用**(:90)

---

## 五、系统设置 / 系统配置

**事实：ATS 有 3 类并存配置载体**（不是单一真相源）：

| 载体 | 位置 | 用途 |
|---|---|---|
| Django settings | `apps/django/config/settings/{base,dev,prod,test}.py` | 部署级常量（DB、REST_FRAMEWORK、MIDDLEWARE、CORS…） |
| `TenantConfig`（DB 表） | `core/models_permission_v2.py:261`，`db_table='tenant_configs'` | 键值对（`system_code` + `config_key` + `config_value` JSON）。仅在 `seed_v2_init.py:546` 写入，**无 CRUD 视图**，业务代码零引用 |
| 「单体 JSON 配置」范式 | 各业务 app 自建 `*Setting`/`*Config` 模型 + 单 key APIView | **主流范式**，例：`DemandSetting`(key='demand') + `DemandConfigView`（`apps/demand/views.py:226-251`，挂 `system/config/demand`）；`CampusModuleConfig`(key='ambassador'/'session') + `CampusModuleConfigView`（`campus/views.py:110-138`） |

- 用户级 UI 偏好：`UserPreference`（`core/models.py:283`）→ 经 `GET/PATCH /api/v1/auth/me` 的 `uiSettings` 下发（`views_auth.py:227-248, 314`）
- 前端配置常量：`web/app/src/config/index.ts`（appName / 端口 / apiPrefix / 分页 / 日期格式，硬编码）
- 双系统当前值：`web/app/src/stores/system.ts` → **localStorage** key `recruit-system`（`'social'|'campus'`），不是后端配置
- 前端拿配置方式：`utils/request.ts:39` 每次请求读 `useSystemStore().current` 注入 `X-Recruit-Type` 头

---

## 六、工程约定

| 项 | 事实 | 路径 |
|---|---|---|
| pytest settings module | `config.settings.test` | `apps/django/pytest.ini:2` |
| pytest 收集范围 | `testpaths = tests apps`（基线 2256 用例，2026-10-09 实测） | `pytest.ini` |
| 其他 pytest 选项 | `--reuse-db --create-db`、`--strict-markers`、`--basetemp=/tmp/ats_pytest_bt` | `pytest.ini` |
| marker | `v2_permission` / `idor` / `quarantine` | `pytest.ini` |
| ruff | `apps/django/ruff.toml`：`target-version=py314`、`line-length=100`、`select=["F","E9","I"]`、`ignore=["E402"]`、`**/tests/**` 免 F401/F811/F841 | — |
| 迁移命名 | Django 默认规范（`0001_initial.py` / `0002_<slug>.py`） | `apps/campus/migrations/0001_initial.py`、`apps/dictionary/migrations/0002_dictionaryitem_description_and_more.py` |
| 前端目录 | `web/app/src/{router,pages,api,components,composables,stores,utils,directives,config,locales,styles,services,types,plugins}` | — |
| 菜单/权限相关目录 | `src/router/index.ts`、`src/utils/{permissionMenu,role}.ts`、`src/directives/permission.ts`、`src/composables/usePermission.ts`、`src/pages/Layout.vue`、`src/pages/settings/SettingsLayout.vue` | — |
| i18n | `src/locales/`（`zh-CN.ts` + `en-US.ts` + 领域分片 + `index.ts` + `language.ts`）；主菜单仍是中文硬编码 | — |
| 前端构建/lint | `eslint.config.js` / `.stylelintrc.json` / `stylelint-plugin-strict-color.cjs` / `uno.config.ts` / `vite.config.ts` / `vitest.config.ts` / `playwright.config.ts` / `e2e/` | `web/app/` |
| UI 硬约束 | `AGENTS.md` R-101~R-111 / R-201~R-223 / R-209~R-214 + X-01~X-13 禁止清单（含 R-222 用户可见文案 MUST 优先中文） | 根目录 `AGENTS.md` |
| CI 守卫脚本 | `apps/django/scripts_scan_v2_write_guard.py`（未声明权限码的写端点）、`scripts_scan_softdelete.py`（无 deleted_at 模型误过滤）、`scripts_scan_todo.py` | — |
| 后端 URL 注册 | `apps/django/config/urls.py`：声明式 4 段（`_FRONT_ORDERED` / `_EMPTY_PREFIX` / `_NON_EMPTY` 按前缀长度降序 / `_DIRECT_VIEWS`），非空前缀**新增无需关心插入位置**；守卫测试 `apps/core/tests/test_url_resolution.py` | — |
| 响应契约 | 写操作经 `EnvelopeWriteMixin` 包 `{success, data}`；列表 `{success, data:[...], pagination}`；camelCase 自动转换（`CamelCaseJSONRenderer` / `CamelCaseJSONParser`，`config/settings/base.py:375-381`） | — |
| 全局权限默认 | `DEFAULT_PERMISSION_CLASSES = ('apps.core.permissions.IsAuthenticatedDenyByDefault',)` —— **deny-by-default** | `config/settings/base.py:360-362` |
| 中间件 | `RequestIdMiddleware` → `ConditionalCsrfMiddleware`(`/api/` 豁免 CSRF) → `AuthenticationMiddleware` → **`RecruitTypeMiddleware`** → `AuditMiddleware` | `config/settings/base.py:168-186` |

---

## 七、已存在的校招相关能力

### 7.1 `apps/campus/` — 校园大使 / 宣讲会（业务功能）
- 路由：`/api/v1/campus-recruit/`（`apps/campus/urls.py`），资源 `ambassadors`、`sessions`、配置 `ambassadors/config/`、`sessions/config/`
- 模型（`campus/models.py`）：`CampusAmbassador`(:14，字段 school/name/region/status/phone/note/recruit_type)、`CampusSession`(:44，title/school/session_type/start_time/end_time/venue/online_link/capacity/status/note/recruit_type)、`CampusModuleConfig`(:86，key unique + config JSON)
- 视图（`campus/views.py`）：`CampusModelViewSetMixin`(:30) 继承 `ScopeQuerysetMixin`，`permission_classes=[IsAuthenticated]`（**未接 V2 资源码**），`perform_create/update` 注入 `recruit_type` + 审计字段，`perform_destroy` 软删；两个 ViewSet 各带 `restore` action
- 前端：`pages/settings/CampusAmbassador.vue`(454行)、`pages/settings/CampusSession.vue`、`api/campusRecruit.ts`

### 7.2 `apps/campus_control/` — 校招人员比例管控
- 路由：`/api/v1/campus/`（`apps/campus_control/urls.py`），资源 `dimensions`/`indicators`/`rules`/`persons`
- 模型（`campus_control/models.py`，291 行）：`ControlDimension`(:37)、`ControlIndicator`(:53)、`ControlRule`(:73，bu/position/level/dimension/indicator/year/target/strength/annual_target/monthly_targets/rollover_enabled，code 自动 `G%04d`)、**`Person`(:169，校招人员主数据：code/name/bu/school/sex/major/month/status/expected_entry_date/actual_entry_date/position/level/counted/`user_id` FK→User)、`PersonDimensionValue`(:269)
- ⚠️ **`Person` 是校招生人员的既有载体**，且已通过 `user_id`(BigIntegerField，:220) 映射到 `core.User`
- 枚举硬编码在 `apps/campus_control/constants.py`（`DEPTS/LEVELS/MAJORS/POSITIONS/SCHOOLS/SEXES/STATUS/STRENGTH`），**不走数据字典**
- 导入导出：`io_xlsx.py`(302) / `io_indicator.py`(274) / `calc.py`(515) / `signals.py`（Offer 钩子）
- 权限（`campus_control/views.py`）：4 个 ViewSet 均 `EnvelopeWriteMixin + CampusCRUDMixin + ModelViewSet` + **`permission_classes=[V2Permission]`** + `permission_required='recruit:settings:campus-control:list'` + 各自 `permission_required_map`
  `ControlDimensionViewSet`(:145)、`ControlIndicatorViewSet`(:201)、`ControlRuleViewSet`(:307)、`PersonViewSet`(:494)
- 前端：`pages/settings/CampusControl.vue`（1902 行）、`api/campusControl.ts`

### 7.3 `apps/onboarding/` — 待入职
- 路由：`/api/v1/onboardings/`（`apps/onboarding/urls.py`）
- 模型（`onboarding/models.py`）：`Onboarding(FSMModelMixin, FullAuditModel)`(:23)，`offer` OneToOne / `candidate` FK / `position` FK（全 `on_delete=PROTECT`）、start_date/actual_start_date/probation_end_date、todo_list(JSON)、todo_completed(JSON)、`state`(django-fsm FSMField)、regularization_*
- 状态机 7 态（`OnboardingState`:13）：PENDING → PREPARING → COMPLETED → PROBATION → REGULARIZED，支线 DELAYED / RESIGNED_DURING_PROBATION
- 视图（`onboarding/views.py:26`）：`permission_classes=[V2Permission]`、`permission_required='recruit:candidate:onboarding:list'  # 0047 自 recruit:onboarding:list 归位候选人管理「录用信息」页签`、`scope_field='position__department'`、`filterset_fields=['state','candidate','position']`、`@action transition` + `ensure_writable(user,'onboarding',...)`
- 前端：`pages/onboarding/OnboardingList.vue`、`api/onboarding.ts`

### 7.4 ⚠️ 明确的「请勿合并」警告（代码注释原文）
`apps/campus/urls.py:5-9` 与 `apps/campus_control/urls.py:3-7` 均写：
> 本 app（campus）与 campus_control **仅名字相近、职责完全不同，请勿合并**
> - `campus`：校园大使 / 宣讲会 / 校招模块开关（业务功能）
> - `campus_control`：校招**人员比例管控**系统
> 两者是相互独立的两个业务域（`campus_control` 挂 `/api/v1/campus/`，`campus` 挂 `/api/v1/campus-recruit/`）

### 7.5 与「校招生管理助手」重叠面（事实比对）
重叠候选：`campus_control.Person`（校招生人员主数据：bu/school/sex/major/month/status/entry date/position/level）**与**源项目的「校招生花名册」高度同构；`campus_control` 的 `School/Major/Sex` 枚举 **vs** `dictionary` 中的 `EDUCATION`/`POSITION_FAMILY` 及 `library` app（院校库/专业库/公司库）。
**未找到**：导师库、班主任库、轮岗部门、直播间平台 —— ATS 侧**无任何对应模型/表/页面**（`onboarding.todo_list` 是 JSON 清单，不构成导师体系）。

---

## 八、关键约束与坑（迁移时必须遵守）

### A. 数据模型层
1. **主键**：业务模型统一 `UUIDModel`（`apps/common/models.py:65-76`）→ `CharField(max_length=32)` + **nanoid(21)**。**不是 UUID 类型**。`UserRoleV2.user_id` / `ManagementUnitMember.user_id` 是 **BigInteger**（User.id 为 int）。
2. **审计 + 软删**：业务模型统一 `FullAuditModel`（`created_at/updated_at/deleted_at/created_by/updated_by`，`common/models.py:47-64`）。DELETE 一律软删（`perform_destroy → soft_delete()`），并提供 `restore` action。**Department 例外（无 deleted_at，硬删）**。
3. **`User` 表名固定 `auth_user`**，`AUTH_USER_MODEL` **未设置**（`core/models.py:154`）。禁止改名/改主键。
4. **`User.soft_delete()` 同时置 `is_active=False`**（`core/models.py:174-177`）；全库大量 FK 以 `on_delete=PROTECT` 指向 `core.User`，**硬删必 500**。
5. 部门 `code` 自动 `D%06d`、字典类型 `dict_number` 自动 `D{n}`、管控规则 `code` 自动 `G%04d`、人员 `code` 自动 `C%08d` —— 新增编码字段应复用 `save()` 内事务补号范式，不要让调用方传。
6. `ManagementUnitMember` 的 `MEMBER_TYPE` 枚举（`models_permission_v2.py:179-183`）：`DEPT`(Department.id) / `USER`(User.id) / `PERSON`(campus_control.Person.id) —— 已有 `PERSON` 类型但注释写明「本迭代仅存储展示, 执行面生效待补 Person->User 映射」。

### B. recruit_type 硬分区
7. `X-Recruit-Type` 请求头（`core/middleware.py:65-88`）合法值仅 `'social' | 'campus'`，**缺省/非法 → 回落 social + warning**。前端由 `utils/request.ts:39` 读 `useSystemStore().current` 注入。
8. 校招模型**必须**带 `recruit_type` CharField(choices=`RECRUIT_TYPE_CHOICES`, default=`RecruitType.CAMPUS.value`, db_index=True)（范式见 `campus/models.py:30-33, 72-75`）。
9. `ScopeQuerysetMixin.perform_create/perform_update`（`permissions_v2.py:245-259`）**权威覆盖**客户端自填的 `recruit_type`；`_rt_field()` 有 `hasattr` 守卫，模型无该字段则不注入。
10. **超管也不例外**：「含超管, 不受行级 scope 豁免影响」（`middleware.py:69-70`）。
11. 前端当前值在 **localStorage**（`stores/system.ts`，key `recruit-system`），**不是后端配置**；后端不感知「用户选了哪个系统」。

### C. 权限层
12. **deny-by-default**：`DEFAULT_PERMISSION_CLASSES = IsAuthenticatedDenyByDefault`。ViewSet 必须显式声明 `permission_classes`。
13. `V2Permission` 下**写操作必须声明码**，否则拒绝（`permissions_v2.py:113-117, 151-167`），除非设 `V2_STRICT_WRITE_GUARD=False`。有 CI 脚本 `scripts_scan_v2_write_guard.py` 审计。
14. 资源码必须先落 `seed_v2_init.RESOURCES`，否则派生码回退原码 + warning（`_derive` :142-148）。改完资源码要 `invalidate_known_codes()` 清 5 分钟缓存（`permissions_v2.py:56-58`）。
15. **fail-open 是既定哲学**：`/me.permissions` 为空 = 未配置 ≠ 无权限。前端 `canAccess` 与 `filterMenuByPermission` 都据此「不拦」，由后端 403 兜底。新增菜单若忘记在 `MENU_PERMISSION_RULES` 登记路径 → 恒可见。
16. `ENTITY_SCOPE`（`core/entity_scope.py:23-33`）与各 ViewSet 的 `scope_field`/`scope_creator_field` **必须逐一对应**（有 `tests/test_entity_scope.py` 守卫）；新实体需同时登记。
17. `UserRoleV2.role_code` 是**跨系统字符串**（不可建 FK，`RoleV2` 唯一键是复合键单列不唯一），孤儿角色防护靠 `core/signals.py` 的 `purge_role_grants_on_delete` + `serializers.validate_role_code`。
18. `_apply_role_type` 是**覆盖式**（先删后建，`serializers.py:140-149`）—— 用户多角色时走此路径会**丢掉其他角色**；列表接口的 `roleType` 也只取首个（`.first()`）。

### D. 前后端契约
19. **camelCase 自动转换**（`CamelCaseJSONRenderer` / `CamelCaseJSONParser`）—— 后端写 snake_case，前端收 camelCase。但 `parentId` 这类**数字边界**需在 serializer 里显式声明（见 `DepartmentSerializer` 的 `manager_2_id` 注释，`serializers.py:251-253`）。
20. 响应信封：写走 `EnvelopeWriteMixin` → `{success, data}`；但**部分老端点返回裸对象**（`campusRecruit.ts:6-11` 的注释明确列出四种契约并存）。新端点一律走基类。
21. 分页统一 `StandardResultsSetPagination`（PAGE_SIZE=20，`config/settings/base.py:363-364`）。
22. 前端路由删除时**必须留 redirect 深链**（既有范式：`{ path: 'offers', redirect: '/candidates' }` `router/index.ts:86`；`{ path:'metric-library', redirect:'/settings/metrics' }` :147）。
23. Vue Router 4 **不继承父路由 meta** —— 守卫用 `to.matched.some(r => r.meta?.requiresAuth)`（`router/index.ts:262`），不是 `to.meta`。
24. 前端菜单 `key` 必须等于路由 path 且以 `/` 开头，否则点击无反应（`Layout.vue:578`）。
25. 后端加 URL：非空前缀挂 `config/urls.py:54-101` 的 `_NON_EMPTY` 列表即可（按长度降序自动排序），无需关心插入位置；但**空前缀 include 顺序敏感**，须进 `_EMPTY_PREFIX`(:34-47)。

### E. 工程流程
26. pytest 跑 `apps/django` 目录，`DJANGO_SETTINGS_MODULE=config.settings.test`；新增 app 的测试放 `apps/<app>/tests/`（会被 `testpaths=apps` 收集）。
27. ruff 只跑 `F/E9/I` 三条规则（bug-catcher），风格类不入门禁，但 CI 门禁为「只许减少不许新增」。
28. 前端硬约束见 `AGENTS.md`：R-101 完整状态、R-104 四类异步反馈、R-106 可撤销破坏操作（→ 所以才有 `restore` action）、R-107 转义、R-108 长列表虚拟化/分页、R-109 a11y 基线、R-111 完整状态机、R-215 数据列表滚动、R-216~R-221 图标/文案规范、**R-222 用户可见文案 MUST 优先中文**。
29. `scripts_scan_softdelete.py`：对**没有 `deleted_at` 的模型**做 `.filter(deleted_at__isnull=True)` 会被 CI 拦（Department 就是这种模型）。

---

## 九、明确「未找到」清单

| 检索目标 | 结果 |
|---|---|
| 后端菜单表 / Menu 模型 / 菜单 CRUD API | 不存在 |
| `PermissionResource` 上的前端 path 字段 | 不存在（前后端靠前端静态表关联） |
| 用户模型上的「业务身份类型」枚举（如导师/班主任） | 不存在；只有 `user_type`(INTERNAL/EXTERNAL) + `UserRoleV2.role_code` |
| 按 `direct_manager` 筛选用户的接口 / 前端使用 | 不存在（`filterset_fields` 无该字段，前端 0 处引用） |
| `campus` / `campus_control` 的独立 V2 资源码（`:ambassador:` / `:session:`） | 不存在，复用 `recruit:settings:campus-control:*` |
| `TenantConfig` 的读写 API / 业务引用 | 只有模型 + seed 写入，无视图、无业务读取 |
| 前端 `/campus/*` 独立路由组 | 不存在（校招相关全在 `/settings/*`） |
| 导师库 / 班主任库 / 轮岗部门 / 直播间平台 的任何 ATS 侧对应物 | 不存在 |
| `campus_control` 枚举走数据字典 | 未走，`apps/campus_control/constants.py` 硬编码 |
