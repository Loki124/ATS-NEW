# 资源编码规范（permission_resources.resource_code）

> 状态：**现行规范**（2026-10-18 兵哥批准立项）
> 护栏：`apps/core/tests/test_resource_code_convention.py`（新增资源不合规即测试失败）
> 真源：`apps/core/management/commands/seed_v2_init.py` 的 `RESOURCES`

---

## 1. 为什么要定规范（背景事实）

2026-10-18 对全量 285 条资源做审计，实测结果：

| 段数 | 条数 | 形态 | 角色引用 |
|---|---|---|---|
| 3 段 | 65 | `系统:模块:动作` | 63/65 |
| 4 段 | 157 | `系统:模块:页面:动作` | 120/157 |
| 5 段 | 59 | `系统:模块:子模块:菜单\|页面:动作` | 43/59 |
| 6 段 | 4 | `系统:模块:子模块:二层子模块:菜单:动作` | 1/4 |

**段数差异的根因是「模块层级深度不同」，不是随手乱写**：
- 业务域（candidate / offer / mou…）没有子页面层 → 3 段
- settings 域有子页面（account / company / job_level…）→ 5 段
- `settings:permissions:resources` 权限管理下的资源管理页 → 6 段

### 🔴 决策：不拉平段数，改为「按层级定段 + 受控词表 + CI 护栏」

**为什么不统一拉平成同一段数**：
1. 会丢掉层级信息（`settings:company:brand` 与 `settings:company` 的从属关系）；
2. 改动面极大且**失败即静默失权** —— 实测 4 个权限模板的 `permission_codes`
   JSON 字段里存着**全部 285 个码**（`permission_templates` 表实测 distinct = 285），
   任何一处漏改 = 该身份静默丢失对应功能，且不报错。

因此本规范的核心目标是：**约束「新增」而非「重写存量」**。

---

## 2. 编码结构

```
{system_code}:{module}[:{sub_module}...]:{kind}:{action}
                └─ 层级段（1~3 段，按模块实际层级）─┘  └─ 末两段固定 ┘
```

| 位置 | 语义 | 约束 |
|---|---|---|
| 第 1 段 | 系统编码 | 本系统恒为 `recruit`（`PermissionResource.system_code` 默认值） |
| 第 2 段 | 模块 | **必须 == `module` 字段值**（见 §4 规则 R2） |
| 中间段 | 子模块层级 | 0~2 段；层数由模块实际嵌套深度决定 |
| 倒数第 2 段 | **种类** | 受控词表，见 §3 |
| 最后 1 段 | **动作** | 受控词表，见 §3 |

### 2.1 按层级定段（示例）

```
recruit:candidate:menu:view                    4 段  业务域直接功能
recruit:settings:account:menu:view             5 段  settings 一级子页面
recruit:settings:permissions:resources:menu:view  6 段  settings 二级子页面
```

---

## 3. 受控词表

### 3.1 种类段（倒数第 2 段）

| 值 | 含义 | 对应 `resource_type` |
|---|---|---|
| `menu` | 菜单入口 | `MENU` |
| `list` / `create` / `edit` / `delete` / `export` / `view` / `approve` / `assign` / `publish` / `close` / `schedule` / `feedback` / `advance` / `reject` / `start` / `stop` / `approve_l1` / `approve_l2` / `grade:edit` 等 | 功能动作 | `BUTTON` |
| `api` | API 端点（预留，当前 0 条） | `API` |

> 🔴 **规则 R1**：`resource_type == 'MENU'` ⟺ 倒数第 2 段为 `menu`。

### 3.2 动作段（最后 1 段）

实测存量高频动作（新增时优先复用，勿造新词）：

```
list create edit delete export view approve assign
publish close schedule feedback advance reject start stop
```

> 🔴 **规则 R3**：动作段必须落在这个词表内。新增动作需先改本表 + 同步前端按钮，
> 否则「加了动作但前端没有对应按钮」= 永远无法被授权的僵尸资源。

---

## 4. 校验规则（护栏测试逐条执行）

| 编号 | 规则 | 违反后果 |
|---|---|---|
| **R1** | `MENU` 类型 ⟺ 倒数第 2 段 == `menu` | 类型与编码自相矛盾，类型列标签会显示错误 |
| **R2** | 第 2 段 == `module` 字段 | 按模块分组展示时语义错位（实测存量有 3 条违规） |
| **R3** | 最后 1 段 ∈ 动作受控词表 | 造出前端无对应按钮的僵尸资源 |
| **R4** | 段数 ≥ 3，且第 1 段 == `system_code` | 跨系统串码 |
| **R5** | 同前缀下 MENU 至多一条 | 一个页面登记多个菜单入口 |

**护栏只校验「新增」，不对存量报警** —— 存量违规项以「已知债务」清单形式单独维护
（见 §6），避免存量拖垮 CI。

---

## 5. 新增资源的标准流程

```bash
# 1. 在 seed_v2_init.py 的 RESOURCES 里追加元组（该命令幂等，update_or_create）
#    ('recruit:{module}:{kind}:{action}', '中文名', 'TYPE', 'module')

# 2. 跑护栏测试
cd apps/django && .venv/bin/python -m pytest apps/core/tests/test_resource_code_convention.py -q

# 3. 落库
.venv/bin/python manage.py migrate          # 无迁移时跳过
.venv/bin/python manage.py seed_v2_init

# 4. 同步权限模板（🔴 高危：模板 JSON 存的是资源码字面量，漏同步 = 静默失权）
#    见 §7
```

---

## 6. 🟢 存量债务清零记录（2026-10-18）

> 本节原是「已知存量债务（护栏放行白名单）」。兵哥明确要求「项目初期不要把债务留到未来」，
> 故 2026-10-18 一次性清零，并把各项从「放行」升级为「护栏永久拦截」（见 §4 规则 R7
> 及 `test_resource_code_convention.py`）。下方只做历史留痕，**不再存在任何放行权**。

| 原债务项 | 条数 | 处置（迁移 / 状态） | 现状 |
|---|---|---|---|
| `module` 与第 2 段不一致 | 3 | `core.0027_fix_module_field` 迁移修正 | ✅ 清零 |
| 连字符段值（`company-brand` / `field-acl` 等 29 个段，98 条码）与下划线族并存 | ~98 | `core.0028_unify_resource_code_segments` 段级改名 + 护栏 R7 锁死 | ✅ 清零 |
| 2 组资源名重复（「编辑角色」「删除角色」各 2 条） | 4 | 经查证：`recruit:role:{create,edit,delete}` 是**后端在役鉴权真源**，不得停用；`recruit:settings:permissions:{create,edit,delete,export}` 是 2026-09-18「角色管理→身份管理」更名遗留的**零消费僵尸码**，`core.0029` 已停用（保留 `settings:permissions:menu:view`，前端菜单守卫在用） | ✅ 清零 |
| 10 条 DB 孤儿资源（`data-permission:*` / `user-management:*`，功能已下线但库里残留） | 10 | `core.0029` 停用（`status=0`，不物理删除以保留历史授权可追溯） | ✅ 清零 |
| 动作段用 `_l1` / `_l2` 后缀（`approve_l1/approve_l2`） | 2 | 已随 Offer 两级审批下线停用（0026 之前处置） | ✅ 清零 |

**段数差异不再视为债务**：3/4/5/6 段并存是模块层级深度不同的自然结果（业务域无子页面=3 段，
settings 子页面=5 段，权限下资源管理页=6 段），符合本规范 §2「按层级定段」，**不是缺陷**。
R1~R6 对全部 285 条资源恒成立，无需任何白名单。

### 6.1 改名同步清单（P0：漏一处即静默失权）

`core.0028` 改名必须同步三处存储，已在同一事务内完成：

| 存储点 | 表 / 字段 | 同步方式 |
|---|---|---|
| 资源定义本体 | `permission_resources.resource_code` | 逐条 `update`（unique 约束，批量 UPDATE 会撞 1062） |
| 真实授权 | `role_permission.resource_code` | 逐条 `update`；冲突合并去重，不撞 `uk_role_resource` |
| 模板 JSON | `permission_templates.permission_codes` | 逐条解析 JSON 数组改写 |

离线（非库）同步点：前端 `web/app/src/utils/permissionMenu.ts`（57 条菜单映射）、
各后端 `views.py` 的 `permission_required` / `has_perm` 声明（27 个文件 339 处），
已由脚本按映射表全量改写并验证零残留。

---

## 7. 🔴 模板 JSON 同步（P0 风险点）

`PermissionTemplate.permission_codes` 是 **JSON 数组字段，存资源码字面量**，
Django 的外键级联/迁移**完全不覆盖**它。

**实测**：`SELECT DISTINCT` 全部模板的 `permission_codes` → **285 个码，覆盖全部资源**。

因此任何资源码变更都必须同步：
```sql
UPDATE permission_templates SET permission_codes = ... WHERE permission_codes LIKE '%旧码%';
```
遗漏后果：该身份**静默丢失**对应功能权限 —— 用户看不到按钮、无报错、测试也测不出。

**护栏**：`test_resource_code_convention.py::test_template_codes_all_exist_in_resources`
锁住「模板里的每个码都必须能在资源表中找到」，防止资源被删/改名后模板留下悬空码。
