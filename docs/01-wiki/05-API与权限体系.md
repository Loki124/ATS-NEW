# 05 - API 路由与权限体系
> 最后更新：2026-09-07（依据 git 最后提交）

## 1. 顶层路由结构

`apps/django/config/urls.py`：

| 路径 | 指向 | 说明 |
|---|---|---|
| `/{ADMIN_URL_TOKEN}/` | Django admin | token 由 env `ADMIN_URL_TOKEN` 控制（生产必须设随机值） |
| `/api/v1/...` | 业务 API | 见 §2 |
| `/api/schema/` `/api/docs/` `/api/redoc/` | drf-spectacular | OpenAPI schema / Swagger UI / ReDoc |
| `/health/` | `apps.core.urls_health` | 健康检查 → `{"status":"ok"}` |
| `^(?!api/\|health/\|static/\|media/\|__debug__/).*$` | `spa_fallback` | 其余路径回退前端 `index.html`（vue-router history 模式） |

**路由注册顺序陷阱**（`config/urls.py` 内有详细注释）：

1. `search/` 必须在 referral `urls_stubs` **之前**（否则被 stub 抢路由）；
2. `urls_stubs` 与 V2 权限端点必须在 `core.urls` 之前（否则被 `permissions` router 的 `(?P<pk>)` 吃掉）；
3. `grab-pool/` 独立挂顶层（与 `applications/{id}/grab/` 语义区分）。

## 2. API v1 路由总表

| 前缀（`/api/v1/` 下） | app | 主要 ViewSet / View |
|---|---|---|
| `auth/` | core | `LoginView`（username/工号/邮箱/手机号）、refresh、me |
| `search/` | search | 全局统一搜索 APIView |
| `users/` `departments/` `roles/` `permissions/` | core | 用户/组织/角色/权限码管理（V1） |
| `permissions/resources` 等 9 端点 | core | V2 权限：资源、模板、角色、用户角色、管理单元 |
| `stages/` `processes/` `process-stage-links/` `stage-rules/` `expressions/` | process | 阶段/流程/连线/规则/表达式 |
| `recruitment-rules/entry-conditions/` | entry_condition | 进入条件规则 |
| `time-limit-rules/` | time_limit | 阶段限时规则 |
| `automation-rules/` | automation | 自动化规则 |
| `candidates/` | candidate | `CandidateViewSet`（含 `/transition`） |
| `candidates/add-candidate/` | add_candidate | `UploadAndParseView`、`BulkCreateView`、评分 SSE `scoring/stream/`、查重 |
| `applications/` | application | `ApplicationViewSet`（阶段流转、审批、撤回等） |
| `grab-pool/` | application | `GrabPoolViewSet`（抢单池/认领/改派） |
| `demands/` | demand | `DemandViewSet` + `system/config/demand`（`DemandConfigView`） |
| `announcements/` | announcement | 公告 CRUD |
| `positions/` | position | `PositionViewSet` |
| `offers/` | offer | Offer CRUD + PDF |
| `onboardings/` | onboarding | 入职管理 |
| `invitations/` | invitation | 邀约管理 |
| `interviews/` | interview | 面试安排与反馈 |
| `referrals/`（+ `referral/` 别名） | referral | 内推码/记录 |
| `talent-pool/` | talent_pool | 人才库与推荐 |
| `channels/` | channel | 渠道与成本 |
| `permissions-v2/` | mou | MOU 协议 4 ViewSet（历史前缀） |
| `analytics/` | analytics | 报表/快照/导出 |
| `data/` | analytics | `data/kpi`、`data/subscriptions`（`KpiViewSet` / `DataSubscriptionViewSet`） |
| `notifications/` | notification | 通知与已读 |
| `audit-logs/` | audit | 审计查询 |
| `gdpr/` | gdpr | 数据主体请求 |
| `integrations/` | integration | 集成配置 |
| `dictionary-items/` `dictionary-types/` | dictionary | 数据字典 |
| `campus/` | campus_control | 校招管控 |
| `external-sync/` | external_sync | Mock 端点 |
| `dynamic-fields/` | dynamic_field | 动态字段定义 |
| `resumes/approval-flows/` | resume_flow | 履历审批流 |
| `library/` | library | 院校/公司库 |
| `scraped-resumes/` | scraped_resume | RPA 抓取简历 |
| `duplicate-check/` | duplicate_check | 查重算法 |
| `field-acl/` | field_acl | 字段 ACL 配置 |
| `''`（根下 stub） | referral(`urls_stubs`) | 22 个历史 stub（auth/register 501、batch、offer-templates 等） |

## 3. 认证体系（JWT 双 token）

`djangorestframework-simplejwt==5.5.1`：

| 项 | 值 |
|---|---|
| access token | 15 分钟（env `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`，#19 已缩短） |
| refresh token | 7 天（env `JWT_REFRESH_TOKEN_LIFETIME_DAYS`） |
| 轮换 | ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION |
| 登录方式 | username / 工号 / 邮箱 / 手机号（`LoginView`） |
| 401 处理 | 前端 axios 拦截器自动 refresh + 重放原请求（见 06-前端架构） |

WebSocket 握手同样走 `JWTAuthMiddleware`（`config/asgi.py`）。

自助注册 `POST /api/v1/auth/register/` 返回 501（企业内 ATS 不开放，账号由 admin 创建）。

## 4. 权限体系（V1 + V2 双轨）

### 4.1 V2 功能权限

```
请求 → V2Permission（DRF permission）
     → core.permission_check.has_perm(user, resource_code)
        ├─ 超管 → True（bypass）
        ├─ UserRoleV2 查用户角色
        ├─ RolePermissionV2 查角色是否授权该 resource_code
        └─ V2 schema 缺失 → 保守返回 False（deny by default）
```

- 资源码集中在 `permission_resources` 表，管理端点 `/api/v1/permissions/resources/` 维护。
- 角色可由模板（`permission_templates`）批量初始化。

### 4.2 V2 数据范围（scope）

`core/scope_resolver.py` `resolve_scope()` 四层堆栈（高优先覆盖低优先）：

| 层 | 来源 | 说明 |
|---|---|---|
| L1 | 用户级 `user_roles.management_unit_ids`（JSON） | 用户显式指定的管理单元 |
| L2 | 角色级 `roles.default_data_scope_type` | 角色默认范围（ALL/DEPT/UNIT/SELF） |
| L3 | 租户 `tenant_configs` 全局配置 | 全局默认 |
| L4 | 兜底 | SELF（最小权限） |

`ScopeQuerysetMixin`（`core/permissions_v2.py`）将解析结果应用到 queryset：按 `department_ids` / `management_unit_ids` 过滤——这是 **IDOR 防护** 的核心（R8 修复 DEPT scope 折空问题）。

### 4.3 字段级 ACL

`apps/field_acl/services.py` `FieldAclService`：按角色对响应字段做隐藏/脱敏（R2 接入）。ViewSet 通过 `field_acl/mixins.py` 混入。

### 4.4 V1 备份

旧 `roles/user_roles/permissions/role_permissions` 4 表被 RENAME 为 `*_v1_backup` 保留，作为救援回滚路径。

## 5. 节流（Rate Limit）

`config/settings/base.py` DRF 配置：

| 档 | 速率 |
|---|---|
| 匿名 | 60/min |
| 登录用户 | 1000/min |
| login 端点 | 5/min（防爆破） |

后端另有 `django-ratelimit==4.1.0`（env `RATELIMIT_ENABLE` 控制，Redis 存储）。

## 6. 实时通道

| 通道 | 端点 | 消费者 | 用途 |
|---|---|---|---|
| WebSocket | `ws/notifications/` | `NotificationConsumer` | 按用户推送站内通知 |
| WebSocket | `ws/applications/{id}/` | `ApplicationUpdateConsumer` | 申请状态变更协作 |
| SSE | `GET /api/v1/candidates/add-candidate/scoring/stream/` | — | 简历评分进度流 |

服务层推送工具：`apps/core/routing.py` 的 `push_to_user()` / `push_to_application()`。

## 7. 响应约定

- **camelCase 适配**：`djangorestframework-camel-case` 自动转换——前端发 camelCase，后端收 snake_case，响应反向。
- **分页**：`StandardResultsSetPagination`（page/page_size，前端 `src/config` 单一真源对齐）。
- **异常**：`apps/common/exceptions.py` `custom_exception_handler` 统一错误结构。
- **审计**：写操作自动经 `AuditMiddleware` 落 `audit_logs`（带 request_id）。
