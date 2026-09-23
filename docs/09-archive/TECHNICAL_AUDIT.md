# ATS-NEW 技术维度全面审计报告

> **审计者**：高见远（架构师）
> **审计日期**：2026-08-31
> **审计对象**：`/Users/loki/WorkBuddy/招聘助手/ATS-NEW` @ `04fec99` (main)
> **约束**：纯审计，**未修改任何业务源码**。仅新建 `docs/audit/` 下的报告与只读验证脚本。
> **方法**：运行时内省（`django.urls.get_resolver()`）+ 真跑 `pytest` / `vue-tsc` / `npm run build` / `manage.py migrate` / 真发 HTTP 请求数 SQL，**不采信文档自述**。

**结论标注约定**：
- 【事实】= 有命令输出或 `文件:行号` 硬证据支撑
- 【判断】= 审计者基于事实的评估，可争议
- 【未验证】= 本次未能取得证据，明确存疑

---

## 一、TL;DR

**总体健康度：🟠 中风险（较 2026-08-03 的「🔴 高风险」有实质改善，但出现新的 P0 阻断项）**

1. **上轮 R1–R18 里，10 项真修复、4 项未修、4 项部分修复**（明细见 §9 对照表）。最关键的**假绿重灾区已经真修**：字段级脱敏 `FieldAclService` 从"零业务调用的死代码"变成**真发 HTTP 请求验证返回 `138****1234`**；migration 崩溃修复后后端 **976/977 测试全绿**；依赖锁 37 个 pin **零漂移**。这三项我逐条跑了运行时验证，不是读注释得出的结论。

2. **但出现一个全新的 P0，且性质与上次的"假绿"同源**：`npm run build`（= `vue-tsc && vite build`）在当前 HEAD **直接失败，10 个 TypeScript 错误分布在 7 个文件**。工作区干净（`git status` 仅有未跟踪新文件，无已跟踪文件改动），所以这是**已提交代码的状态** → CI 的 `test-frontend` job 必然红灯。R11 把 CI 门禁从"装饰"收紧成"真门禁"是对的，收紧之后第一个被拦下的就是自己。

3. **第二个新 P0 是 migration 状态漂移**：`apps/core/models.py:246` 的 `Permission` 模型指向 `db_table='permissions'`，但 `apps/core/migrations/0004_v2_apply_schema.py:101` 已把物理表 RENAME 成 `permissions_v1_backup`，而模型**从未从 migration state 中删除**。结果：全新库 `migrate` 后**该表不存在**（实测 108 张表里没有它），而 `makemigrations --check` 却报 "No changes detected"——这类漂移**现有 CI 完全检测不到**。任何触碰 `Permission.objects` 的代码都会 `OperationalError`，`init_demo_data` 命令已因此不可用。

4. **第三个高危项是 WebSocket 越权**（上轮未识别）：`apps/core/consumers.py:30-37` 的 `ApplicationUpdateConsumer` 只校验"已登录"，然后从 URL 取任意 `application_id` 加入对应广播组——**任何登录用户可以订阅任意申请的实时更新流**，是典型水平越权。

5. **好的一面要说清楚**：后端测试 976 通过、N+1 控制良好（候选人列表 15 条 SQL 且不随 `page_size` 增长）、文件上传校验完整（扩展名白名单 + 大小 + 数量 + 前置校验）、生产配置启动期强校验、JWT rotate + blacklist、GDPR 验证码已 hash 化。这些是真实的工程质量，不是文档自述。

6. **根因判断**：上轮报告说"反馈回路断裂"，本轮 CI 已经接上了，但**接上之后立刻暴露出新问题，说明还缺两类门禁**：① `makemigrations --check`（拦 migration 漂移）；② 前端类型检查需要在**提交前**而非 CI 后跑。此外 `apps/*/views.py` 仍在变胖（`campus_control/views.py` 1052 行）、前端 `pages/` 吃掉 88% 代码量，架构收敛未启动。

---

## 二、评分卡

| # | 维度 | 评分 | 核心依据（一句话 + 证据锚点） |
|---|---|---|---|
| 1 | 架构分层与模块边界 | **3/5** | 33 个 app 按业务域切分合理；但 `campus_control/views.py` 1052 行、`application/services/__init__.py` 1084 行，视图层承载业务逻辑；路由注册顺序仍是隐式契约（`config/urls.py:21-31`） |
| 2 | API 设计一致性 | **3/5** | 全局默认 deny-by-default + 统一 camelCase + 统一分页（`base.py:280-320`）；但 469 个去重点中 63 个只挂裸 `IsAuthenticated`、82 个 `AllowAny`，且 441 个未声明限流 |
| 3 | 数据模型 | **2/5** | **扣分项：`permissions` 表漂移（§4.1）**；N+1 实测良好；软删覆盖 48%（47/97）不一致；索引仅 32/97 模型声明 |
| 4 | 认证与权限 | **3/5** | deny-by-default 落地 + 字段脱敏运行时验证通过；**扣分项：WebSocket 无授权（§5.3）**、权限检查零缓存（`permission_check.py:1`）、登出不撤销 access token |
| 5 | 异步与实时 | **3/5** | Celery 重试策略体系完整（`celery_utils.py:131-158`）；**扣分项：WS 越权**、compose 缺 celery-worker/beat |
| 6 | 性能 | **3/5** | 后端 N+1 控制好（候选人列表恒定 15 SQL）；**扣分项：首屏 gzip 976 KB**，其中 vendor 独占 623 KB |
| 7 | 安全 | **3/5** | 上传校验、prod 启动校验、PII 部分加密到位；**扣分项：WS 越权、phone/email 明文、JWT 60 分钟、`admin123` 仍在**（`init_demo_data.py:276`） |
| 8 | 配置与部署 | **2/5** | settings 拆分与 prod 强校验优秀；**扣分项：`npm run build` 失败 → CI 红**（§8.3）、compose 无 celery 服务、V2 权限资源全新库为空需手工 seed |
| 9 | 技术债与坏味道 | **2/5** | 123 处 `except Exception`；god component 不降反增（2289→2490 行）；`.legacy.vue` / `debounce.ts`+`.mjs` 双份 / MOU 挂在 `permissions-v2/` 均未清理 |

**加权总评：约 2.7 / 5**（🟠 中风险。无"跑不起来"级阻断，但有一个 CI 红灯级 P0 和两个安全 P1）

---

## 三、架构分层与模块边界

### 3.1 后端 app 划分

【事实】`apps/django/apps/` 下 **33 个业务 app**；非 migration Python **414 个文件 / 50,145 行**；migration 文件 89 个。

```
analytics  announcement  application  add_candidate  audit  automation
campus_control  candidate  channel  common  core  demand  dictionary
duplicate_check  dynamic_field  entry_condition  external_sync  field_acl
gdpr  integration  interview  invitation  library  mou  notification
onboarding  offer  position  process  referral  resume_flow  rule_engine
scraped_resume  search  talent_pool  time_limit
```

【判断】按业务域切分（招聘流程 / 人才库 / 校招管控 / 背调集成 / 权限 / 数据字典）是**合理的**，领域边界清晰，`common`/`core` 横切职责明确。这在同类 Django 项目中属中上水平。

### 3.2 视图层过胖（业务逻辑泄漏）

【事实】非测试 .py 文件 TOP 5：

| 行数 | 文件 | 性质 |
|---|---|---|
| 1084 | `apps/application/services/__init__.py` | 服务层（**这是对的**） |
| 1052 | `apps/campus_control/views.py` | ⚠️ 视图层 |
| 704 | `apps/integration/services.py` | 服务层 ✅ |
| 682 | `apps/application/views.py` | 视图层 |
| 672 | `apps/candidate/services.py` | 服务层 ✅ |
| 620 | `apps/process/views.py` | 视图层 |

【判断】项目**已经建立了服务层**（`application/services/`、`candidate/services.py`、`integration/services.py`），这是好架构。但 `campus_control`（1052 行）尚未拆分，`application/views.py` 682 行 + `application/services/__init__.py` 1084 行并存说明**迁移正在进行但未完成**。属 P2 技术债，非阻断。

【未验证】跨 app 循环依赖本次**未做系统性检测**（未跑 import-lalider 类工具）。从 `migrate` 与 976 测试全部通过可推断**不存在阻断级循环导入**，但静态层面的环未排除。

### 3.3 前端目录结构

【事实】

| 目录 | 文件数 | 行数 | 占比 |
|---|---|---|---|
| `pages/` | 77 | 31,708 | **88.5%** |
| `api/` | 35 | 4,261 | 11.9% |
| `components/` | 42 | 4,204 | 11.7% |
| `stores/` | 6 | 1,257 | 3.5% |
| `utils/` | 5 | 627 | 1.7% |
| `composables/` | 2 | 93 | 0.3% |

（占比按各目录行数/合计 35,823 行粗算，`pages` 含 .vue+script）

【判断】**结构严重失衡**：`pages/` 吃掉 88% 代码，而 `components/` 只有 11.7%。这意味着 UI 复用几乎为零，页面之间靠复制粘贴。TT 的 `composables/` 仅 2 个文件 93 行，说明**组合式函数抽象几乎没被采用**。这是"页面能跑但改不动"的典型形态。

【事实】最大 .vue 文件（god component）：

| 行数 | 文件 | 上轮(2026-08-03) | 变化 |
|---|---|---|---|
| 2490 | `pages/settings/ProcessDetailModal.vue` | 2289 | **+201 ↑** |
| 1709 | `pages/settings/CampusControl.vue` | — | — |
| 1465 | `pages/settings/MouManagement.vue` | 1398 | +67 ↑ |
| 1387 | `pages/settings/ExternalSettings.vue` | — | — |
| 1141 | `pages/candidate/CandidateList.vue` | — | — |
| 1140 | `pages/demand/DemandList.vue` | — | — |
| 1050 | `pages/settings/DataDictionary.vue` | — | — |
| 1019 | `pages/settings/StageRuleConfigModal.vue` | 1014 | +5 ↑ |

【判断】R16 的神组件治理**不仅没做，还在反向增长**。`ProcessDetailModal.vue` 2490 行是维护灾难，且它同时是**本次 10 个 TS 错误里占 3 个的文件**（§8.3）——这不是巧合，是耦合度的直接后果。

---

## 四、数据模型

### 4.1 🔴 P0-1：`permissions` 表不存在 —— migration 状态漂移

**问题**：`apps/core/models.py:246` 的 `Permission` 模型声明 `db_table = 'permissions'`（`:265`），但物理表已被 RENAME 走，而模型从未从 migration state 删除。

**证据链**：

1. 模型仍在注册表中 —— `apps/core/models.py:246` `class Permission(models.Model)`，`apps/core/models.py:265` `db_table = 'permissions'`
2. 0001 建表 —— `apps/core/migrations/0001_initial.py:20` `name='Permission'`，`:32` `'db_table': 'permissions'`
3. 0004 把物理表改名 —— `apps/core/migrations/0004_v2_apply_schema.py:101` `('permissions', 'permissions_v1_backup')`
4. 0004 只从 state 删了另外 3 个 V1 影子模型 —— `0004_v2_apply_schema.py:264,267,270` 三处 `migrations.DeleteModel`（Role / UserRole / RolePermission），**没有 Permission**
5. **实测全新库 migrate 后无此表**：

```
$ DJANGO_SETTINGS_MODULE=config.settings.test DJANGO_DB_NAME=/tmp/aud_test.sqlite3 \
    .venv/bin/python manage.py migrate --run-syncdb
表总数: 108
permissions 存在? False
candidates 存在? True
含 'perm' 的表: ['auth_group_permissions', 'auth_permission',
   'core_user_user_permissions', 'permission_resources',
   'permission_templates', 'permissions_v1_backup',
   'role_permission', 'role_permissions_v1_backup']
```

6. **现有检查手段全部漏报**：

```
$ .venv/bin/python manage.py makemigrations --check --dry-run
No changes detected
```

7. 受影响的业务代码：`apps/core/management/commands/init_demo_data.py:161` `Permission.objects.update_or_create(...)`；`apps/core/views_auth.py:11` `from .models import Permission`（该文件中实际未使用，属**坏模型的死导入**）

**影响**：
- 任何 `Permission.objects.*` 查询 → `OperationalError: no such table: permissions`（本人写的两个审计脚本均在此崩溃，是**实际踩到**而非静态推断）
- `init_demo_data` 初始化命令在全新环境不可用
- Django 测试框架 `setup_databases()` 会在 `serialize_db_to_string()` 阶段遍历全部模型并崩在此表——**这是 `DiscoverRunner` 路径的定时炸弹**（pytest 走的是另一条路径，所以 976 测试没暴露它）
- `makemigrations --check` 报"无变化"，**漂移对人和 CI 都不可见**

**建议（P0）**：三选一，按推荐度排序——
1. **删模型**（推荐）：`Permission` 是 V1 遗留，V2 已用 `PermissionResource` 接管。删除 `apps/core/models.py:246-273` 的类 + 生成删除 migration + 清理 `views_auth.py:11` 与 `init_demo_data.py:76,161` 的引用。
2. 保留模型但加 `managed = False`（模型文件 `:252` 的注释已预告了这个动作，只是没做）。
3. 补一条把 `permissions_v1_backup` 改回 `permissions` 的 migration（**不推荐**，会复活 V1 影子表冲突）。

**配套（P0）**：CI 增加 `manage.py makemigrations --check --dry-run` 门禁 —— 见 §8.2。

### 4.2 N+1 查询

【事实】静态扫描：`get_resolver()` 遍历出 60 个列表类视图（去重后），其中 34 个有 `get_queryset` 或 `select_related`/`prefetch_related` 优化，**11 个既无比优化且模型有外键**（N+1 高风险）：

| FK 数 | 视图 | 路由 |
|---|---|---|
| 8 | `apps.application.views.GrabPoolViewSet` | `api/v1/grab-pool/` |
| 3 | `apps.channel.views.ChannelCostViewSet` | `api/v1/channels/costs/` |
| 2 | `apps.talent_pool.views.TalentPoolTagViewSet` | `api/v1/talent-pool/tags/` |
| 2 | `apps.channel.views.ChannelViewSet` | `api/v1/channels/` |
| 2 | `apps.mou.urls.MouAgreementViewSetWithScopes` | `api/v1/permissions-v2/mou/` |
| 2 | `apps.campus_control.views.ControlDimensionViewSet` | `api/v1/campus/dimensions/` |
| 2 | `apps.campus_control.views.PersonViewSet` | `api/v1/campus/persons/` |
| 1 | `apps.automation.views.AutomationLogViewSet` | `api/v1/automation-rules/logs/` |
| 1 | `apps.mou.views.MouContainerViewSet` | `api/v1/permissions-v2/containers/` |
| 1 | `apps.analytics.views.ExportTaskViewSet` | `api/v1/analytics/exports/` |
| 1 | `apps.analytics.views.ReportSnapshotViewSet` | `api/v1/analytics/` |

【事实】**运行时实测**（真发 HTTP，数 SQL 条数；脚本 `docs/audit/verify_n1_runtime.py`）：

```
端点                                    SQL   重复    耗时ms
/api/v1/candidates/                     15    0    466.3  HTTP 200   ← 首次(含冷启动)
/api/v1/candidates/?page_size=50        15    0      4.7  HTTP 200   ← 同为 15 条！
/api/v1/applications/                    2    0      2.7  HTTP 200
/api/v1/interviews/                      2    0      2.0  HTTP 200
/api/v1/offers/                          2    0      3.4  HTTP 200
/api/v1/campus/dimensions/               2    0      1.4  HTTP 200
```

【判断】**主干列表接口的 N+1 控制得相当好**：`page_size=20` 与 `page_size=50` 都是 15 条 SQL，说明是常数级而非线性级（序列化器做了 `select_related`）。**这是对上轮"N+1 风险"担忧的有力澄清**——不是问题，不用修。

【判断】需要修的是上表 11 个静态高风险点，尤其 `GrabPoolViewSet`（8 个外键全无优化）。优先级 **P2**（这些端点数据量通常小）。

【事实】冒烟过程中另观察到 `UnorderedObjectListWarning`：分页对**无默认排序**的 queryset 工作（如 `Offer`、`AutomationLog`、`TalentPoolTag`、`InterviewEvaluation`、`ApprovalFlow`）。

【判断】分页 + 无 `ordering` = **翻页可能漏行/重行**。属 P2，修法一行（模型 Meta 加 `ordering`）。

### 4.3 软删除覆盖

【事实】97 个受管模型中，47 个（**48%**）有 `deleted_at` 或 `is_deleted`。缺软删的业务模型集中在：

- `core`（10 个）：Department / ManagementUnit / Permission / PermissionResource / PermissionTemplate / RolePermissionV2 / RoleV2 / TenantConfig …
- `integration`（4 个）：**BackgroundCheckOrder / BackgroundCheckOrderEvent** / IntegrationConfig / IntegrationSyncLog
- `mou`（4 个）：MouAgreement / MouContainer / MutualExclusionGroup / AutomationRule
- `gdpr`（1 个）：GDPRRequest
- `resume_flow`（2 个）、`analytics`（2 个）、`library`（2 个）、`process`（2 个）等

【判断】**覆盖不完整本身不算 bug**（审计日志、join 表本就不需要软删），问题在于**不一致**：`BackgroundCheckOrder`（背调订单，含敏感个人信息）和 `MouAgreement`（合同）缺软删，而同库其他业务表有——这两类数据恰恰是"删错了要能找回"的。建议 **P2**，优先补 `BackgroundCheckOrder` / `MouAgreement`。

### 4.4 索引与状态机

【事实】97 个受管模型中仅 **32 个**声明了 `Meta.indexes`（33%）；**16 个 `FSMField`**、**51 个 `@transition`**（较上轮的 7/43 有增长，说明流程能力在扩展）。

【判断】索引覆盖偏低，但**未做慢查询实测**，无法判定是否实际构成问题——【未验证】。建议结合 §7 的性能基线一起做。

【事实】`django-fsm` 3.0.1 在 import 时**持续打印弃用告警**（指向 viewflow.fsm）：

```
site-packages/django_fsm/__init__.py:63: UserWarning: The 'django-fsm' package
has been integrated into 'viewflow' as 'viewflow.fsm' starting from version 3.0...
```

每次 `manage.py` / pytest 启动都刷屏。属 P2（噪音），但也是**上游不再维护的信号**，需立项决策（对应上轮待确认问题 7）。

---

## 五、认证与权限

### 5.1 API 权限覆盖面（运行时内省）

【事实】用 `django.urls.get_resolver()` 递归展开全部路由（脚本 `docs/audit/introspect_api.py`，原始明细 `docs/audit/api_endpoints.csv`）：

```
总 URL 模式（不含 admin/static）: 710
DRF 类视图端点: 690
去重（剔除 format-suffix 重复）后: 469  独立 view 类: 136
```

**permission_classes 分布（去重后 469 个）：**

| 数量 | 权限类 | 评估 |
|---|---|---|
| 125 | `V2Permission` | ✅ V2 声明式，主流 |
| **82** | `AllowAny` | ⚠️ 见下 |
| **63** | `IsAuthenticated`（裸） | ⚠️ 绕过 deny-by-default |
| 56 | `ResourceScoped` | ✅ |
| 51 | `HasProcessPermission` | ✅ |
| 24 | `IsHROrAbove` | V1 遗留 |
| 20 | `IsSuperAdmin` | ✅ |
| 12 | `IsAuthenticatedReadOnly` | ✅ |
| 9 | `MOUVIEWSetPermission` | V1 遗留 |
| 4 | `UserViewPermission` | V1 遗留 |
| 3 | `IsAuthenticatedDenyByDefault` | ✅ |

**全局默认**（`config/settings/base.py:286-288`）：
```python
'DEFAULT_PERMISSION_CLASSES': (
    'apps.core.permissions.IsAuthenticatedDenyByDefault',
),
```

【判断】**全局 deny-by-default 是真落地了**（R-T01.2 属实），这是本项目权限设计上最正确的决定。

【判断】但 63 个裸 `IsAuthenticated` 端点**显式覆盖了 deny-by-default**，其中包含了应受控的业务资源。样本（来自内省输出）：

```
api/v1/search/                    apps.search.views.SearchAPIView
api/v1/announcements/^$           apps.announcement.views.AnnouncementViewSet
api/v1/^dictionary-types/$        apps.dictionary.views.DictionaryTypeViewSet
api/v1/^dictionary-items/$        apps.dictionary.views.DictionaryItemViewSet
api/v1/campus/^dimensions/$       apps.campus_control.views.ControlDimensionViewSet
api/v1/campus/^indicators/$       apps.campus_control.views.ControlIndicatorViewSet
```

【判断】这些是"只要登录就能读写"的配置类资源（数据字典、校招管控维度/指标）。**数据字典与校招管控规则属于配置数据，被任意登录用户改写会污染全系统**。建议 **P1**：把这 63 个逐个过一遍，配置类改挂 `ResourceScoped` + `resource_code`。

【事实】82 个 `AllowAny` 中，绝大多数是 DRF router 自动生成的 `APIRootView`（每个 router 一个，列举该 router 下路由名，无业务数据）——**这部分无害**。真正需要关注的 4 个：

```
api/v1/auth/login/    apps.core.views_auth.login_view   perms=AllowAny  throttle=[LoginRateThrottle]
api/v1/auth/refresh/  simplejwt.TokenRefreshView        perms=AllowAny
api/v1/auth/verify/   simplejwt.TokenVerifyView         perms=AllowAny
api/v1/auth/register  urls_stubs.auth_register          perms=AllowAny  throttle=[RegisterRateThrottle]
```

【判断】这 4 个 AllowAny 都是**认证流程本身的端点，合理**。

### 5.2 字段级 ACL（R2）——已真修，运行时验证通过

【事实】1) 接线点：`apps/candidate/serializers.py:26` `CandidateListSerializer(FieldAclSerializerMixin, ...)`、`:65` `CandidateDetailSerializer(...)`、`apps/talent_pool/serializers.py:16` `TalentPoolEntryListSerializer(...)`；mixin 实现在 `apps/field_acl/mixins.py:35`。

【事实】2) **运行时验证**（脚本 `docs/audit/verify_acl_runtime.py`）——构造一个拥有 `recruit:candidate:list/read/view` 资源权限、但**没有任何字段 ACL 规则**的角色用户，真发 HTTP：

```
详情 HTTP 200
   name= 探针甲  phone= 138****1234  email= v***@example.com
列表 HTTP 200
```

手机号 `13800001234` → `138****1234`，邮箱 `victim@example.com` → `v***@example.com`。**脱敏真实生效**。

【事实】3) 无角色用户直接被权限层拦截：`HTTP 403`（deny-by-default 生效，脱敏层无需介入）。

【判断】**R2 从"死代码假绿"变成"真接线 + 真生效 + 有集成测试护航"**，这是本轮审计中质量最高的一项修复。上轮报告"该缓解不存在"的结论已作废。

【事实】4) 残留问题：`apps/field_acl/views.py:77-79` 自述"**也没有在 `FieldAclService.apply_acl` 里埋点记录字段访问**"，即 **PII 字段访问的审计日志未实现**。

【判断】合规视角看，脱敏做了但"谁在什么时候查看了什么敏感字段"没有留痕，PIPL/GDPR 审计要求不完整。**P2**。

### 5.3 🔴 P0-3：WebSocket 水平越权（上轮未识别的新问题）

**问题**：`ApplicationUpdateConsumer` 只做认证（登录），不做授权（是否有权看这个申请）。

**证据** —— `apps/core/consumers.py:28-37`：
```python
class ApplicationUpdateConsumer(AsyncJsonWebsocketConsumer):
    """申请状态更新 - 候选人级"""
    async def connect(self):
        if self.scope['user'].is_anonymous:      # ← 只校验"已登录"
            await self.close()
        else:
            self.application_id = self.scope['url_route']['kwargs']['application_id']  # ← 任意 ID
            self.group_name = f'application_{self.application_id}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()                   # ← 无授权检查即接受
```

路由 —— `apps/core/routing.py:12`：
```python
re_path(r'ws/applications/(?P<application_id>\w+)/$', consumers.ApplicationUpdateConsumer.as_asgi()),
```

**认证侧是正常的** —— `config/asgi.py:18-24` 挂了 `AllowedHostsOriginValidator(JWTAuthMiddleware(URLRouter(...)))`，`apps/core/middleware_ws.py:44-51` 用 `UntypedToken` 校验 JWT 并取 `user`，且**走 `Sec-WebSocket-Protocol` 子协议传 token 避免 token 落 access log**（`:1-20` 设计说明完整）。即：**认证没问题，授权缺失**。

**影响**：任何登录用户（例如权限最低的面试官、甚至内推人）可以 `ws://.../ws/applications/<任意他人申请ID>/` 建立连接，实时接收**任意候选人申请**的状态变更推送（含流程推进、评价、Offer 相关事件，取决于 `push_to_application` 的 payload）。这是**水平越权（IDOR）的实时版**，且因为是推送通道，受害者与审计都难以察觉。

**建议（P1，鉴于需确认 payload 敏感度，先按 P1 处理；若 payload 含 PII 则升 P0）**：
1. 在 `connect()` 内调用与 `ApplicationViewSet` 相同的 V2 权限/数据范围检查（`apps/core/permissions_v2.py` + `scope_resolver.resolve_scope`），无权限则 `await self.close(code=4003)`。
2. 补一个集成测试：用户 A 订阅用户 B 部门下的 application_id，断言连接被拒。
3. 同时排查 `push_to_application` 的 payload 是否含 PII（`apps/core/routing.py:41-53`），必要时先脱敏再广播。

【未验证】`push_to_application` 的实际调用点与 payload 内容本次未全量追踪，故严重度暂定 P1。

### 5.4 JWT 与登出

【事实】`config/settings/base.py:332-344`：
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=60)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env.int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7)),
    'ROTATE_REFRESH_TOKENS':  True,
    'BLACKLIST_AFTER_ROTATION': True,
    ...
}
```

【事实】登出实现 —— `apps/core/views_auth.py:88-99`：只对 **refresh token** 调 `token.blacklist()`，**access token 没有撤销机制**（JWT 无状态，无服务端记录）。

【判断】**R18-M9（JWT 60 分钟）未修复**。且登出只拉黑 refresh token，意味着：
- 用户点"登出"后，其 access token **在剩余有效期内（最长 60 分钟）依然可用**
- 若 token 泄露，撤销窗口最长 60 分钟

**建议（P2）**：① access token 降到 15 分钟、refresh 1 天（对应上轮 Phase 1-6 的 M9）；② 若要支持即时登出，需引入 access token 黑名单或改短 TTL + 前端主动丢弃。二者择一即可，改 TTL 成本近乎为零。

【事实】`apps/core/views_auth.py:117` 新密码策略 `if len(new_password) < 6`。

【判断】**6 位最小长度过弱**，且未校验复杂度。**P2**。

### 5.5 权限检查零缓存（R12 未修）

【事实】`apps/core/permission_check.py:1` 文件首行注释仍是 `"""V2 权限实时查询. 无 cache, 每个请求重查."""`；`has_perm()` 每次执行 2 条查询（`:22-27` 查 `UserRoleV2`，`:33-36` 查 `RolePermissionV2`）。

【判断】未修。功能上正确（保守兜底 `return False`），但每个受保护端点每次请求 +2 SQL。上轮 R12 已量化"列表页 N 个受保护端点线性放大"。本次实测候选人列表 15 条 SQL 里就有这部分开销。**P2**。

---

## 六、异步与实时

### 6.1 Celery

【事实】10 个 `tasks.py`（notification / time_limit / gdpr / audit / automation / application / invitation / talent_pool / add_candidate / analytics）。

【事实】重试策略**已成体系** —— `apps/common/celery_utils.py:131-158` 提供 `db_retry_task` 装饰器：
```python
max_retries: int = 3,
retry_backoff: int = 60,
retry_backoff_max: int = 600,
...
autoretry_for=DB_RETRY_EXCEPTIONS,
acks_late=True,
```

【事实】实际落地情况：
- ✅ `apps/audit/tasks.py:37-45`：`bind=True, autoretry_for=DB_RETRY_EXCEPTIONS, retry_backoff=300, retry_backoff_max=3600, max_retries=3, acks_late=True`（最完整）
- ✅ `apps/application/tasks.py:27-29,117-119,135-137,148-150,209-211`：均有 `bind=True` + `max_retries`（2~3）+ `default_retry_delay=60`
- ✅ `apps/add_candidate/tasks.py:10,68`：`bind=True, max_retries=3, default_retry_delay=5`（`:68` 还指定了 `queue='scoring'`）
- ⚠️ `apps/analytics/tasks.py:11,106`、`apps/notification/tasks.py:11`、`apps/time_limit/tasks.py`：仅 `@shared_task(name=...)`，**无重试配置**

【判断】重试/acks_late 体系**总体良好**，属中上水平。缺口是 4 个裸 `@shared_task`（analytics 导出、日报快照、通知提醒、时限扫描）——这类**定时/重任务失败后无声消失**的风险最高。**P2**：统一套用 `db_retry_task`。

【未验证】**幂等性**未做系统审计（未逐个检查任务是否有幂等键）。已知 `apps/integration/migrations/0005` 建了 `idx_synclog_cb_idem` 唯一索引（`config, sync_type, external_ref, status`），说明背调同步侧**做了幂等设计**，其余任务【未验证】。

### 6.2 Channels / WebSocket

认证 ✅（见 §5.3）、授权 ❌（见 §5.3）。另有：

【事实】`apps/core/routing.py:26-40` 的 `push_to_user` 返回"成功投递的连接数"，但函数体恒 `return 1`（`group_send` 是异步广播，无法知道连接数）；失败路径 `return 0`。

【判断】返回值语义与实际不符，调用方若据此统计在线数会得到恒为 1 的假数据。**P2**（一行修复或改名）。

### 6.3 Redis 依赖

【事实】`config/settings/prod.py:99-115` 启动期 TCP 探测 Redis，不可达直接 `ImproperlyConfigured`，**明确禁止 LocMemCache 静默 fallback**（注释指出多 gunicorn worker 下 throttle / idempotency / session 全失效）。

【判断】这个设计决策**正确且重要**，是本项目工程成熟度的体现。

---

## 七、性能

### 7.1 后端

【事实】N+1 实测良好，见 §4.2（候选人列表恒定 15 SQL，不随 page_size 增长）。

【事实】权限检查每请求 +2 SQL 且无缓存（§5.5）。

【未验证】**慢查询未做实测**——本次未开 `slow query log`、未做压测（无 locust/k6 基线），`docs/PERFORMANCE.md` 声称的 `AUTO_ADVANCE_P95_TARGET_MS=200` 是否达成**无法判断**。建议立项性能基线（对应上轮 Phase 3-8）。

### 7.2 前端构建产物

【事实】`web/app/dist/` 总体 3.4 MB；**gzip 后 JS+CSS 合计 976 KB**。前 8 大（gzip）：

| gzip | 文件 |
|---|---|
| **358,743 B** | `vendor-naive-ui-*.js` |
| **279,562 B** | `vendor-rich-editor-*.js` |
| 43,287 B | `vendor-vue-*.js` |
| 23,004 B | `vendor-misc-*.js` |
| 17,981 B | `CandidateList-*.js` |
| 17,752 B | `RecruitmentProcess-*.js` |
| 13,351 B | `vendor-icons-*.js` |
| 12,702 B | `app-utils-*.js` |

【判断】**首屏 gzip 976 KB 偏重**，其中两个 vendor 独占 623 KB（64%）。`vendor-rich-editor`（富文本编辑器 273 KB gzip）被拆成独立 chunk 是正确的，但需确认它**只在需要时才加载**（懒加载）而非进首屏——【未验证】（未分析 `index.html` 的 modulepreload 与路由懒加载配置）。

【判断】路由级代码分割**已在做**（`CandidateList`、`RecruitmentProcess`、`CampusControl` 各自成块），这是对的。**P2** 建议：① 确认 rich-editor 懒加载；② Naive UI 改按需引入（若当前是全量 import，350 KB gzip 有大幅压缩空间）。

【未验证】首屏 LCP / FCP 未实测（未跑 Lighthouse）。

### 7.3 大列表虚拟化

【未验证】本次**未检查**前端大列表是否做了虚拟滚动/分页。`CandidateList.vue` 1141 行含 Naive UI `DataTable`；后端有分页（PAGE_SIZE=20），前端若一次性拉取全量则有问题，但**未取得证据**，不做结论。

---

## 八、配置与部署

### 8.1 settings 拆分 —— 优秀

【事实】`config/settings/` 拆 `base / dev / test / prod`，入口 `config/settings/__init__.py:40-63` 白名单 + 未知值**直接抛错**（不再静默回落 dev）。

【事实】`config/settings/prod.py:16-82` 启动期强校验 6 类不安全配置：SECRET_KEY 默认值/长度 <50、DEBUG=True、ALLOWED_HOSTS 含 `*`、`CORS_ALLOW_ALL_ORIGINS`、白名单通配符、SQLite。另有 HSTS / SSL header / secure cookie（`prod.py:85-97`）。

【事实】CI 也验证了这个强校验 —— `.github/workflows/ci.yml:340-353`：
```yaml
DJANGO_SETTINGS_MODULE=config.settings.prod DJANGO_SECRET_KEY=too-short DJANGO_DEBUG=True \
  python manage.py check
if [ $? -eq 0 ]; then echo "❌ prod settings 接受了不安全配置"; exit 1; fi
```

【判断】**R3 真修，且做到了"配置错误 → 启动失败"而非"启动成功但行为错误"**，这是本项目最扎实的一块。

### 8.2 CI 门禁 —— 已收紧，但缺两类关键检查

【事实】上轮 R11 指出的 4 处装饰性门禁**全部收紧**（`.github/workflows/ci.yml`）：
- `:83` `pytest --tb=short -v --maxfail=10`（全量，不再是 `pytest tests/`）
- `:141` `npm run build`（带 vue-tsc，不再是 `build:nocheck`）
- `:153` `npm run lint:ci`（带 `--max-warnings=0`，不再是 `|| true`）
- `:370` trivy `exit-code: '1'`（不再是 `'0'`）
- `:232-241` e2e 轮询 `/health/` 最多 60s（不再是死等 `sleep 5`）

【判断】**R11 属实修复**。这是本轮最重要的工程改进——反馈回路接上了，且接上后立刻抓出了 §8.3 的构建失败，恰好证明门禁有效。

【事实】**缺失的门禁**：
1. **没有 `makemigrations --check`** —— 正是 §4.1 的 `permissions` 漂移能潜伏至今的直接原因。
2. **没有覆盖率门禁** —— `test-migrations` 只数表数量 `>= 50`（`:321-324`），不校验模型↔表一致性。
3. **QUARANTINE 隔离区**（`:24-33`）deselect 了 9 个用例（`add_candidate` 6 个 + `sync_resources_t29` 3 个），`known-failures` job `continue-on-error: true`（`:90`）。

【判断】隔离区机制本身**是健康的工程实践**（注释明确写"这个清单只允许变短，不允许变长"），比 `|| true` 高明得多。但 9 个存量失败需排期清零。**P2**。

【建议 P1】CI 增加两步（各 1 行）：
```yaml
- run: python manage.py makemigrations --check --dry-run   # 拦 migration 漂移
- run: python manage.py migrate && python -c "from django.db import connection; \
       assert 'permissions' in connection.introspection.table_names()"  # 拦模型↔表不一致
```

### 8.3 🔴 P0-2：`npm run build` 在当前 HEAD 失败

**证据** —— 工作区干净（`git status --short` 只有 18 项，全为**未跟踪**新文件，无任何已跟踪文件被修改），说明以下错误**已在 HEAD `04fec99` 中**：

```
$ cd web/app && npm run build
> vue-tsc && vite build

src/components/dashboard/index.ts(21,39): error TS2307: Cannot find module './EmptyState.vue'
src/pages/Login.vue(237,9): error TS2353: 'containerStyle' does not exist in type 'MessageOptions'
src/pages/settings/ProcessDetailModal.vue(294,66): error TS2339: Property 'autoSkipNPlusTwo' does not exist
src/pages/settings/ProcessDetailModal.vue(299,55): error TS2339: Property 'autoSkipNPlusTwo' does not exist
src/pages/settings/ProcessDetailModal.vue(580,42): error TS2339: Property 'autoSkipNPlusTwo' does not exist
src/pages/settings/RecruitmentProcess.vue(31,8): error TS2559: ...ExtractThemeOverrides<Theme<"DataTable"...
src/pages/settings/RecruitmentRound.vue(31,8):   error TS2559: （同上）
src/pages/settings/RecruitmentStage.vue(36,8):   error TS2559: （同上）
src/pages/settings/SettingsLayout.vue(185,30): error TS2322: '(Key | undefined)[]' not assignable
src/pages/settings/SettingsLayout.vue(187,58): error TS2345: （同上）
```

**统计：10 个 TS 错误，分布在 7 个文件**（`ProcessDetailModal.vue` 独占 3 个）。

**影响**：
- CI `test-frontend` job **必然红灯**（`:141` 跑的正是 `npm run build`）
- `e2e` job `needs: [test-backend, test-frontend]`（`:183`），前端红了 e2e 也不会执行
- **R10 声称"已把 3 个类型错误修掉"不成立**：错误数从 3 涨到 10

**错误性质分析【判断】**：
| 错误 | 性质 | 修法成本 |
|---|---|---|
| `Cannot find module './EmptyState.vue'` | **文件缺失**（死引用） | 极低：补文件或删引用 |
| `autoSkipNPlusTwo` 不属于该类型（×3） | 类型定义与实现**不同步** | 低：补字段声明或改实现 |
| `DataTable` theme override 类型不匹配（×3） | Naive UI 主题覆写**键名写错**（`tdPaddingMedium`/`thPaddingMedium` 不在 `DataTable` 主题里） | 低：删掉或改正确键名 |
| `SettingsLayout.vue` `Key \| undefined`（×2） | 空值处理缺失 | 低：加过滤 |

【判断】**10 个错误全是"低垂果实"，合计约半天工作量**。但也说明一件事：`pages/` 里 88% 的代码没有类型守护的缓冲区，改动极易产生类型漂移。

**建议（P0）**：立即修复这 10 个错误让 CI 转绿。同时（P1）加 pre-commit 钩子跑 `vue-tsc`，把类型检查左移到提交前——否则这个红灯会反复出现。

### 8.4 Docker 编排

【事实】`ops/docker-compose.yml`（141 行）R4 修复到位：
- ✅ `redis:7-alpine` 服务已补（`:55-81`），带 healthcheck、AOF、`maxmemory 512mb`
- ✅ env 名对齐：`DJANGO_SECRET_KEY`、`CORS_ALLOWED_ORIGINS`（`:92,105`），且全部 `${VAR:?错误提示}` 强制校验
- ✅ 端口统一 8000（`:87`），nginx 反代到 `backend:8000`
- ✅ 缺变量**直接拒绝启动**（无 `${VAR:-weak-default}`）
- ✅ `Dockerfile:11-23` 用 `ARG PYTHON_VERSION` 绑定基础镜像与 COPY 路径（R9 修复）

【事实】**残留缺口**：compose 中**没有 `celery-worker` / `celery-beat` 服务**。20+ 个 Celery 任务与定时（含 3AM 清理）在容器路径下**无人执行**。`Dockerfile:89-90` 注释说"celery-worker / celery-beat 服务会覆盖为 celery 命令"，但 compose 里根本没有这两个服务。

【判断】**P1**。容器部署路径下异步能力完全缺失（公告推送、时限扫描、背调同步、日报快照全不跑）。而生产实际走的是 systemd `ats-django.service` + `scripts/webhook-deploy.sh`（daphne），所以**当前生产可能不受影响**——但 compose 是文档承诺的部署路径，要么补服务，要么在文档里明确"compose 仅用于本地联调"。

【事实】`Dockerfile:11` `ARG PYTHON_VERSION=3.12`，而开发 venv 是 **Python 3.14.6**、CI 是 **3.14**（`ci.yml:59`）。

【判断】**三套 Python 版本**（容器 3.12 / 本地 venv 3.14.6 / CI 3.14）。容器与本地大版本不同，是典型的"本地能跑、容器炸"温床。**P1**：统一到 3.14。

### 8.5 部署引导缺口

【事实】全新库 migrate 后 `PermissionResource` 表**为空**：
```
资源码总数: 0
```
资源码需通过 API action `apps/core/views_permission_v2.py:127 sync_resources` 或 `seed_v2_init` 命令灌入；而 **RUNBOOK.md 中未出现 `seed_v2_init` / `sync_resources` 字样**（grep 无命中）。

【判断】**P1 部署风险**：全新环境部署后，因为 V2 deny-by-default + 资源表为空，**所有业务接口对所有人返回 403**，而 RUNBOOK 没有这一步。运维会卡在一个错误提示不明确的状态。

【建议】RUNBOOK 增加"初始化权限资源"步骤，并把 `seed_v2_init` 纳入部署脚本或 `post_migrate` 信号。

### 8.6 环境 / 密钥管理

【事实】`config/settings/base.py:58` `SECRET_KEY = env('DJANGO_SECRET_KEY', default='insecure-dev-key-change-me')` —— 保留弱默认值，但 `prod.py:27` 会拦截（长度 <50 或命中默认值黑名单即崩）。

【判断】✅ 可接受（dev 便利 + prod 强制）。

【事实】`.gitignore` 已覆盖 `.env` / `*.pem` / `*.key` / `secrets/`。`apps/django/.env` 存在（860 B），`config/settings/base.py` 用 `django-environ` 读取。

【未验证】未扫描 git 历史中是否曾提交过密钥（需 `gitleaks` / `trufflehog`）。**建议补充扫描**。

---

## 九、安全

### 9.1 已落地的安全能力（正面清单）

| 能力 | 证据 | 状态 |
|---|---|---|
| 全局 deny-by-default 权限 | `base.py:286-288` | ✅ |
| 字段级 PII 脱敏 | `mixins.py:35` + 运行时验证见 §5.2 | ✅ |
| 登录限流 5/min | `views_auth.py:17-19` + `base.py:317` | ✅ |
| 注册限流 3/h、改密限流 5/min | `views_auth.py:22-30` | ✅ |
| JWT rotate + blacklist | `base.py:339-340` | ✅ |
| WS token 不落 URL（子协议传输） | `middleware_ws.py:1-20` | ✅ |
| 文件上传：扩展名白名单 + 10MB + 数量 + **前置全量校验** | `add_candidate/views.py:66-77` | ✅ |
| CORS 禁止全放开 + 通配符拦截 | `prod.py:54-65` | ✅ |
| HSTS / nosniff / X-Frame DENY / secure cookie | `prod.py:85-97` | ✅ |
| Sentry `send_default_pii=False` | `prod.py:131` | ✅ |
| GDPR 验证码 hash + 15min 过期 + 5 次锁定 | `gdpr/models.py:80-88` | ✅ |
| HMAC-SHA256 双向签名（背调集成） | `apps/integration/services.py`（704 行） | 【未验证】仅确认文件规模，签名逻辑未逐行审计 |

【判断】这份清单说明**安全不是没做，而是做了七八成**。缺的是最后一公里（见下）。

### 9.2 未闭合的安全项

| 项 | 证据 | 级别 |
|---|---|---|
| WebSocket 水平越权 | `consumers.py:30-37` | **P1**（见 §5.3） |
| `phone` / `email` 明文入库 | `candidate/models.py:32` 自述"phone/email 仍存明文" | P1（PII 合规） |
| JWT access token 60 分钟 + 登出不撤销 | `base.py:334`、`views_auth.py:88-99` | P2 |
| `admin123` 弱口令仍在 demo 数据 | `init_demo_data.py:276`、`:48` 且会打印到 stdout | P2 |
| `except Exception` 123 处（非测试） | 全仓统计 | P2（异常吞没→静默降级） |
| PII 字段访问无审计留痕 | `field_acl/views.py:77-79` 自述 | P2 |
| 新密码最小 6 位无复杂度 | `views_auth.py:117` | P2 |
| SQL 注入 / XSS | 未发现裸 SQL 拼接；Vue 默认转义 | 【未验证】未做专项扫描 |

【事实】**路径穿越（R18-M3）实际已被缓解，但属偶然防御** —— `apps/analytics/tasks.py:56` 用 `task.entity` 拼文件名：
```python
filename = f'{task.entity}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.{task.format.lower()}'
```
- `format` 受 `choices` 约束（XLSX/CSV/PDF，`models.py:61`）—— 安全
- `entity` 是自由 `CharField(max_length=64)`（`models.py:57`），序列化器无校验（`analytics/serializers.py:64`）
- **但** `tasks.py:28-38` 的 if/elif 只放行 `candidates`/`applications`/`demands`，其余 `raise ValueError(f'未知 entity: ...')` —— 到达 `:56` 时 entity 必为三个字面量之一

【判断】**当前不可利用**。但安全性依赖于另一段"碰巧存在"的校验分支，属于**脆弱防御**：谁给 entity 加一个合法值（比如带斜杠的实体名）就会立刻引入穿越。**P2**：在序列化器层给 `entity` 加 `ChoiceField` 或正则校验，把校验前移。

### 9.3 日志脱敏

【事实】存在**两套重复的脱敏实现**：
- `apps/common/masking.py`：`mask_phone`(`:21`)、`mask_phone_tail`(`:31`)、`mask_email`(`:45`)、`mask_id_card`(`:58`)、`mask_amount`(`:68`)、`mask_generic`(`:75`)
- `apps/common/utils.py`：`mask_sensitive`(`:18`)、`mask_phone`(`:28`)、`mask_email`(`:35`)、`mask_id_card`(`:47`)

`FieldAclService._MASKERS`（`services.py:155-167`）走的是 `masking.py`。

【判断】**双份实现是坏味道**，`utils.py` 那份是否还有调用方【未验证】。若无人调用应删除；若有人调用应统一。**P2**。

【事实】`apps/common/masking.py:4` 的注释仍写着 `apps/field_acl/services.py:FieldAclService._mask_value (有实现, 但零业务调用)` —— **该描述已过时**（§5.2 已证明有 3 处业务调用）。

【判断】这是**文档腐烂的活样本**：代码修好了，注释没跟着改，下一个人读到会做出错误判断（比如"既然没人用，那就删掉吧"）。**P2**，建议在 CI 增加注释-代码一致性抽查或周期性清理。

---

## 十、技术债与坏味道

### 10.1 量化

| 指标 | 实测值 | 说明 |
|---|---|---|
| `except Exception`（非测试） | **123** 处 | R13 未修。0 处裸 `except:`、0 处静默 `pass`，比上轮的"103 处 + 12 处静默 pass"在**静默**这项上有改善 |
| `TODO` / `FIXME` / `HACK` / `XXX`（后端） | **7** 处（`time_limit/tasks.py`、`demand/views.py`、`demand/models.py`、`application/services/__init__.py`、`application/tasks.py` 等） | 极少，✅ |
| `TODO`/`FIXME`（前端 `src/`） | **4** 处（`utils/role.ts`、`api/dict.ts`、`AnnouncementSettings.vue`） | 极少，✅ |
| 后端非 migration Python | 414 文件 / **50,145 行** | |
| Migration 文件 | 89 个 | |
| 前端 `src/` .vue+.ts | 167 文件 / **35,823 行** | |

### 10.2 死代码 / 重复代码

【事实】
- `web/app/src/pages/candidate/AddCandidateModal.legacy.vue` —— **仍存在**（上轮已点名）
- `web/app/src/pages/settings/Placeholder.vue` —— 仍存在
- `web/app/src/utils/debounce.ts` 与 `web/app/src/utils/debounce.mjs` —— **双份实现仍在**
- `web/app/src/utils/__tests__/debounce.test.ts` 与 `debounce.test.mjs` —— 双份测试
- `apps/core/views_auth.py:11` `from .models import Permission` —— **导入了一个表不存在的模型，且文件内未使用**
- `apps/core/permissions.py` V1 权限类仍在被 24+9+4=37 个端点使用（`IsHROrAbove` / `MOUVIEWSetPermission` / `UserViewPermission`）

【判断】R16 死代码清理**未执行**。前 4 项清理成本约 1 小时，建议顺手做掉（P2）。最后一项（V1/V2 权限双轨）是上轮 Phase 3-1 的 8 天工作量，需单独立项。

### 10.3 命名/语义错配（R17 未修）

【事实】`config/urls.py:97`：
```python
path('permissions-v2/', include('apps.mou.urls')),
```
MOU（谅解备忘录/合同）业务挂在 `/api/v1/permissions-v2/` 下。实体是 `MouAgreementViewSetWithScopes`、`MouContainerViewSet`、`AutomationRule`。

【判断】**未修**。新人按 URL 找 MOU 代码会找不到，按权限模块找又会看到合同代码。**P2**（纯改名 + 前端同步，约半天）。

【事实】`ScopedQuerysetMixin`（V1，`core/permissions.py`）与 `ScopeQuerysetMixin`（V2，`core/permissions_v2.py`）**一字之差并存**。

### 10.4 路由注册顺序隐式契约（R14 未修）

【事实】`config/urls.py:21-38` 三段注释都在解释"必须挂在 core.urls 之前，否则被 router 抢"：
```python
# 全局统一搜索 (Plan P): 必须排在 urls_stubs 的 search stub 之前以优先命中
path('search/', include('apps.search.urls')),
# 把 urls_stubs 挂到 core.urls 之前, 避免 core/permissions router 抢
path('', include('apps.referral.urls_stubs')),
# V2 权限系统 9 endpoints 必须在 core.urls 之前注册 —
#   core.urls 的 router.register(r'permissions', ...) 抢 '^permissions/<pk>/$'
path('', include('apps.core.urls_permission_v2')),
```

【判断】**未修**。任何人重排 `urlpatterns` 都会**静默改变 API 语义**（比如 `/permissions/resources/` 被当成 `pk=resources` 吃掉落 404），且**没有路由快照测试保护**。这是本项目最脆弱的隐式契约。**P1**：加路由快照测试（断言 URL→view 映射），成本 1 天。

### 10.5 工作区卫生

【事实】`web/app/` 下堆积 **15 个 `dist_old_*` 目录**、`dist-qa-verify` / `dist-verify` / `dist.bak281`、**40+ 个 `vite.config.ts.timestamp-*.mjs`**、`vitest.config.ts.timestamp-*.mjs`；`node_modules` 447 MB。

【事实】但 `.gitignore` **已覆盖** `dist*/`、`*.timestamp-*.mjs`、`qa-*.mjs`、`test-*.mjs`；`git ls-files web/app | grep -cE "dist_old|timestamp-|dist-verify|dist\.bak"` = **0**。唯一被跟踪的杂物是 `web/app/t2-screenshot.mjs`（不匹配 `qa-*`/`test-*` 规则）。

【判断】**这不是仓库污染，是本地工作区污染**——不影响 clone 体积与他人环境，**危害有限**。修正我上一条直觉判断：此项评级 **P3（可忽略）**，顺手清理即可。但 `t2-screenshot.mjs` 应删或加进 .gitignore。

---

## 十一、优先级修复清单

### P0（立即，合计约 1.5 人天）

| # | 项 | 动作 | 证据 | 工作量 |
|---|---|---|---|---|
| **P0-1** | 修 `permissions` 表漂移 | 删 `apps/core/models.py:246-273` 的 `Permission` 模型 + 生成删除 migration + 清理 `views_auth.py:11`、`init_demo_data.py:76,161` 引用 | §4.1 | 0.5 天 |
| **P0-2** | 让 `npm run build` 转绿 | 修 10 个 TS 错误（`EmptyState.vue` 缺失 ×1、`autoSkipNPlusTwo` ×3、DataTable 主题键名 ×3、`Key\|undefined` ×2） | §8.3 | 0.5 天 |
| **P0-3** | CI 加 migration 一致性门禁 | `makemigrations --check --dry-run` + 关键表存在性断言 | §8.2 | 0.1 天 |
| **P0-4** | WebSocket 授权补齐 | `consumers.py:30-37` 接入 V2 权限 + 数据范围校验 + 集成测试 | §5.3 | 0.5 天 |

> P0-4 若确认 `push_to_application` payload 含 PII，则升为最高优先级并同步做广播脱敏。

### P1（2 周内，合计约 3.5 人天）

| # | 项 | 动作 | 证据 |
|---|---|---|---|
| P1-1 | 统一 Python 版本到 3.14 | `Dockerfile:11` `ARG PYTHON_VERSION=3.12` → 3.14 | §8.4 |
| P1-2 | compose 补 celery-worker / celery-beat | 新增两个服务（覆盖 Dockerfile CMD） | §8.4 |
| P1-3 | RUNBOOK 补"初始化权限资源"步骤 | 纳入 `seed_v2_init` 或 `sync_resources` | §8.5 |
| P1-4 | 路由快照测试 | 锁定 URL→view 映射，消除顺序隐式契约 | §10.4 |
| P1-5 | 63 个裸 `IsAuthenticated` 端点过审 | 配置类资源改挂 `ResourceScoped` + resource_code | §5.1 |
| P1-6 | phone / email 加密方案决策 | 当前明文（`candidate/models.py:32`）；AES-SIV deterministic 可保留查重能力 | §9.2 |
| P1-7 | 前端类型检查左移 | pre-commit 跑 `vue-tsc`，防止 §8.3 复发 | §8.3 |

### P2（1 个季度内）

| # | 项 | 证据 |
|---|---|---|
| P2-1 | 11 个 N+1 高风险视图补 `select_related`/`prefetch_related`（优先 `GrabPoolViewSet` 8 FK） | §4.2 |
| P2-2 | 无排序 queryset 补 `ordering`（Offer / AutomationLog / TalentPoolTag / InterviewEvaluation / ApprovalFlow） | §4.2 |
| P2-3 | 权限检查加 per-request memo + Redis 缓存（TTL 60s，角色变更主动失效） | §5.5 |
| P2-4 | JWT access 15min / refresh 1d；评估即时登出方案 | §5.4 |
| P2-5 | 4 个裸 `@shared_task` 套用 `db_retry_task` | §6.1 |
| P2-6 | 123 处 `except Exception` 分类治理（可恢复→`logger.warning`，未知→`logger.exception`+Sentry） | §10.1 |
| P2-7 | 软删补齐 `BackgroundCheckOrder` / `MouAgreement` | §4.3 |
| P2-8 | 死代码清理：`.legacy.vue` / `Placeholder.vue` / `debounce.mjs` 双份 / `views_auth.py:11` 死导入 | §10.2 |
| P2-9 | MOU 从 `/permissions-v2/` 迁到 `/mou/` | §10.3 |
| P2-10 | PII 字段访问审计留痕 | §5.2 |
| P2-11 | 前端 bundle 优化：确认 rich-editor 懒加载 + Naive UI 按需引入 | §7.2 |
| P2-12 | 前端结构治理：`pages/` 88% 代码下沉到 `components/` / `composables/`；`ProcessDetailModal.vue`(2490) 拆分 | §3.3 |
| P2-13 | analytics `entity` 校验前移到序列化器 | §9.2 |
| P2-14 | 统一脱敏实现（`masking.py` vs `utils.py`）+ 修 `masking.py:4` 过时注释 | §9.3 |
| P2-15 | 性能基线：慢查询日志 + 压测，验证 P95 < 200ms | §7.1 |
| P2-16 | `init_demo_data.py:276` 去掉 `admin123`，改为生成随机密码 | §9.2 |
| P2-17 | 新密码最小长度 6 → 10 并加复杂度 | §5.4 |
| P2-18 | CI QUARANTINE 9 个存量失败清零 | §8.2 |
| P2-19 | git 历史密钥扫描（gitleaks） | §8.6 |

---

## 十二、附：R1–R18 复核对照表

> 基准：`docs/ARCHITECTURE_REVIEW_2026-08-03.md` §7 风险清单（第 383-407 行）
> 复核方式：运行时内省 / 真跑命令 / 读代码。**"真修"必须有运行时或命令输出证据，仅读注释不算。**

| ID | 风险 | 上轮判定 | **本轮复核** | 判定依据（硬证据） |
|---|---|---|---|---|
| **R1** | migration 图加载即崩 | 🔴 P0 | ✅ **真修** | `apps/candidate/migrations/0004...py:27` 已补 `from django.db import migrations`；`manage.py migrate --plan` 成功；全新库 `migrate` 建出 108 张表；`makemigrations --check` → `No changes detected`；后端 976 测试全绿 |
| **R2** | 字段级脱敏未接线（死代码） | 🔴 P0 安全 | ✅ **真修** | `candidate/serializers.py:26,65` + `talent_pool/serializers.py:16` 接 `FieldAclSerializerMixin`；**运行时 HTTP 验证**：`phone=138****1234`、`email=v***@example.com`；无角色用户 403 |
| **R3** | settings 默认回落 dev | 🔴 P0 | ✅ **真修** | `config/settings/__init__.py:40-63` 白名单 + 未知值抛 `ImproperlyConfigured`；`wsgi.py:9`/`asgi.py:9`/`Dockerfile:22` 默认 prod；`prod.py:16-82` 六类启动期强校验；CI `ci.yml:340-353` 反向验证 |
| **R4** | docker-compose 无法启动 | 🔴 P0 | ✅ **基本真修**（有残留） | redis 服务已补（`docker-compose.yml:55-81`）；env 名对齐 `DJANGO_SECRET_KEY`/`CORS_ALLOWED_ORIGINS`（`:92,105`）；端口 5125→8000；**残留：无 celery-worker / celery-beat 服务** |
| **R5** | 37 个 stub 端点假成功 | 🔴 高 | ✅ **真修** | `urls_stubs.py:147-158` register → `_not_implemented()` 返 501 + `RegisterRateThrottle`；`/api/v1/auth/change-password/` 运行时解析到**真实实现** `views_auth.py:109`；无角色用户 403 |
| **R6** | `/login` 别名无限流 | 🔴 高 | ✅ **真修** | `urls_stubs.py:181-183` `@throttle_classes([LoginRateThrottle])`；运行时 `resolve('/api/v1/login/')` → `throttle=[LoginRateThrottle]`，与 `/auth/login/` 共用 `login` scope |
| **R7** | 68% 后端测试从未进 CI | 🟠 中高 | ✅ **真修** | `pytest.ini:14` `testpaths = tests apps`；**977 collected，976 passed / 1 skipped，33.81s** |
| **R8** | DEPT 数据范围逻辑坏 | 🟠 中高 | ✅ **真修** | `scope_resolver.py:65-70` DEPT 分支返回 `{'department_ids': own}`，不再丢弃 `_dept_ids`；注释 `:25-35` 记录了原 bug 与修复理由 |
| **R9** | 依赖锁与实装漂移 | 🟠 中 | ✅ **真修**（小残留） | requirements.txt **37 个 pin，与 `pip freeze` 逐条比对零漂移**（django-fsm 3.0.1 / celery 5.6.3 / redis 8.0.1 / pytest 9.1.1 / reportlab 5.0.0 …全中）；**残留：`django-cryptography==1.1` 仍为幽灵依赖** |
| **R10** | `npm run build` 必失败 + nocheck | 🟠 中 | ❌ **未修，且恶化** | `npm run build` 在干净 HEAD 上失败：**10 个 TS 错误 / 7 个文件**（上轮为 3 个）。错误清单见 §8.3 |
| **R11** | CI 三道质量门全无效 | 🟠 中 | ✅ **真修** | `ci.yml:83` 全量 pytest、`:141` `npm run build`（带 vue-tsc）、`:153` `lint:ci --max-warnings=0`、`:370` trivy `exit-code:'1'`、`:232-241` e2e 轮询探活。**无 `\|\| true`** |
| **R12** | 权限检查零缓存 | 🟠 中 | ❌ **未修** | `apps/core/permission_check.py:1` 首行注释仍为"无 cache, 每个请求重查"；`has_perm()` 每请求 2 条 SQL |
| **R13** | 103 处 `except Exception` / 12 处静默 pass | 🟠 中 | ⚠️ **部分** | 数量 103 → **123**（非测试）；但**裸 `except:` 0 处、静默 `except: pass` 0 处**（上轮 12 处静默 pass 已消除）。量未减、危害降低 |
| **R14** | 路由注册顺序隐式契约 | 🟠 中 | ❌ **未修** | `config/urls.py:21-38` 三段"必须挂在 core.urls 之前"注释原样保留；无路由快照测试 |
| **R15** | PII 未加密 + `__str__` 泄露 | 🟡 中低 | ⚠️ **部分** | ✅ `id_card_no` 已改 `EncryptedCharField`（migration 0003/0004 + `models.py:29`）；✅ `__str__` 已脱敏（`models.py:131-135`）；❌ **phone/email 仍明文**（`models.py:32` 自述"phone/email 仍存明文"） |
| **R16** | god component + 死代码 | 🟡 中低 | ❌ **未修，反向恶化** | `ProcessDetailModal.vue` 2289 → **2490 行（+201）**；`MouManagement.vue` 1398 → 1465；`AddCandidateModal.legacy.vue` 仍在；`debounce.ts` + `debounce.mjs` 双份仍在 |
| **R17** | 命名/语义错配 | 🟡 中低 | ❌ **未修** | `config/urls.py:97` MOU 仍挂 `/api/v1/permissions-v2/`；V1 `ScopedQuerysetMixin` 与 V2 `ScopeQuerysetMixin` 并存 |
| **R18** | 未修的审计遗留（S2/M3/M4/M9…） | 🟡 低 | ⚠️ **部分（2 修 2 未修）** | ✅ **S2** GDPR 验证码已 hash 化 + 15min 过期 + 5 次锁定（`gdpr/models.py:80-88`）；✅ **M3** 路径穿越被 `tasks.py:28-38` entity 白名单意外缓解（但校验未前移，脆弱）；✅ **M7** `__str__` 脱敏；❌ **M4** `admin123` 仍在（`init_demo_data.py:276`）；❌ **M9** JWT access 60min 未改（`base.py:334`） |

**复核统计：真修 10 项 / 部分修复 4 项 / 未修 4 项**

- 真修：R1 R2 R3 R4 R5 R6 R7 R8 R9 R11
- 部分：R13 R15 R18（另 R4 有小残留）
- 未修：R10 R12 R14 R16 R17

**本轮新发现的、上轮未识别的问题：**
1. 🔴 `permissions` 表不存在（migration 状态漂移，且现有检查全部漏报）—— §4.1
2. 🔴 `npm run build` 10 个 TS 错误（R10 实际恶化）—— §8.3
3. 🔴 WebSocket 水平越权 —— §5.3
4. 🟠 CI 缺 `makemigrations --check` 门禁 —— §8.2
5. 🟠 V2 权限资源全新库为空 + RUNBOOK 无此步骤 —— §8.5
6. 🟠 compose 缺 celery-worker/beat；容器 Python 3.12 vs 本地 3.14 —— §8.4
7. 🟡 登出不撤销 access token（与 JWT 60min 叠加）—— §5.4
8. 🟡 脱敏实现双份 + 过时注释 —— §9.3

---

## 十三、审计脚本与原始数据

| 文件 | 用途 | 运行方式 |
|---|---|---|
| `docs/audit/introspect_api.py` | 遍历 `get_resolver()` 导出全部端点的 permission/throttle/pagination/filter 配置 | `cd apps/django && .venv/bin/python ../../docs/audit/introspect_api.py` |
| `docs/audit/api_endpoints.csv` | 上者输出：710 条路由 × 10 个字段的原始明细 | — |
| `docs/audit/verify_acl_runtime.py` | 真发 HTTP 验证字段脱敏是否生效（R2） | 同上 |
| `docs/audit/verify_n1_runtime.py` | 真发 HTTP 数 SQL 条数验证 N+1 | 同上 |

> 三个脚本均为**只读**，不写入项目数据库（使用临时 sqlite），不修改任何业务代码。

**核心可复现命令**：
```bash
cd apps/django
# 后端全量测试
.venv/bin/python -m pytest -q                       # → 976 passed, 1 skipped
# migration 一致性
.venv/bin/python manage.py makemigrations --check --dry-run   # → No changes detected
# 全新库建表（暴露 permissions 漂移）
DJANGO_SETTINGS_MODULE=config.settings.test DJANGO_DB_NAME=/tmp/t.sqlite3 \
  .venv/bin/python manage.py migrate --run-syncdb
.venv/bin/python -c "import sqlite3;print('permissions' in [r[0] for r in sqlite3.connect('/tmp/t.sqlite3').execute(\"select name from sqlite_master where type='table'\")])"   # → False
# 依赖漂移
.venv/bin/python -m pip freeze > /tmp/freeze.txt   # 与 requirements.txt 逐条比对
# 前端类型检查
cd web/app && npx vue-tsc --noEmit                 # → 10 error
```

---

## 十四、结论

**项目状态：从"跑不起来"进化到"跑得起来、测得过、但有一处关键红灯和若干系统性隐患"。**

上轮那份报告的核心指控——"假绿"——本轮复核下来**大部分已被真修**。特别是三个最严重的：migration 崩溃（5 秒的 import 缺失）修了、字段脱敏死代码接上线了（我用真实 HTTP 请求看到 `138****1234`）、依赖漂移从 15+ 项降到 0。这些都是能验证的硬事实，不是文档自述。测试从 60 ERROR 变成 976 通过，CI 从"三个装饰门"变成真门禁。

**但"假绿"的模式没有根治，只是换了位置。** 上轮是"测试通过但功能没接"（脱敏有单测无调用）；这轮是"CI 收紧了但主干就是红的"（`npm run build` 10 个错误躺在 HEAD 上）。共同点是：**反馈信号产生了，但没人接收**。R11 接好了回路，R10 却没能跟上——这不是能力问题，是**修复工作的覆盖不完整**：Phase 0/1 做完了一批，R10/R12/R14/R16/R17 这一批（Phase 1-5、Phase 3-5 的收尾）没排上。

**给决策者的建议排序**：

1. **先花 1.5 人天做掉 4 个 P0**。成本极低、收益确定：CI 转绿、migration 漂移被拦住、WebSocket 越权堵上。这四件事不做，后面投的任何功能都是在红灯上叠代码。

2. **不要再开新的功能模块，直到 `pages/` 的结构失衡被处理**。`pages/` 占 88% 代码、`ProcessDetailModal.vue` 2490 行且贡献了本次 3/10 的类型错误——这是"每加一个功能就多一分改不动"的负向复利。这不是审美问题，是交付速度问题。

3. **PII 合规需要一个明确决策**。phone/email 明文存储 + 字段访问无审计留痕，如果系统已在处理真实候选人数据，这是需要法务/DPO 评估的事项（上轮待确认问题 6 未答复）。技术上有成熟方案（AES-SIV deterministic encryption 保留查重能力），缺的是决策和排期。

4. **补两类门禁再谈长期质量**：`makemigrations --check`（已在 P0-3）和 pre-commit `vue-tsc`（P1-7）。在这个项目里，"能被自动检测到的错误"基本都被修了，"检测不到的"就一直躺着——`permissions` 漂移是最新的例子。

**最后一句提醒**：本轮我验证的每一条"真修"都有命令输出或 `文件:行号` 支撑。但仍有 6 处明确标注【未验证】（跨 app 循环依赖、任务幂等性、SQL 注入/XSS 专项、慢查询实测、首屏 LCP、rich-editor 是否懒加载）。**这些不要当成"没问题"，它们只是"本次没查"**。

---

**报告结束**
IS_PASS: YES
