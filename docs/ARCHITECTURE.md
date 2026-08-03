# ARCHITECTURE — 系统架构

> **最后更新**: 2026-08-03 — Django 6.0 + DRF 3.15, 28 apps / 60+ 端点 / 9 业务状态机 / 39 pytest + 132 vitest 全过
>
> 旧 Node.js/Express 架构已废弃 (2026-06 切到 Django, 详见 `MIGRATION.md`).

## 总览

```
┌──────────────────┐         ┌──────────────────┐
│  Browser (Vue 3) │ ──────▶ │  Vite Dev Server │
│  :5212           │  /api/* │  + Proxy         │
└──────────────────┘         └────────┬─────────┘
                                      │ proxy_pass → :8000
                                      ▼
                            ┌──────────────────┐
                            │  gunicorn 4w     │
                            │  Django 6.0      │
                            │  + DRF 3.15      │
                            │  :8000           │
                            └────────┬─────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
       ┌─────────────┐       ┌─────────────┐        ┌─────────────┐
       │   MySQL 8   │       │ Redis 7     │        │ Celery      │
       │   :3306     │       │ :6379       │        │ worker+beat │
       │  54+ 表     │       │ cache+broker│        │             │
       └─────────────┘       └─────────────┘        └─────────────┘
```

生产部署: gunicorn 绑 127.0.0.1:8000 → Cloudflare Tunnel → https://ats.lokisong.cloud
(本机 systemd `ats-django.service` + `ats-celery.service` + `ats-celery-beat.service`)

## 模块依赖

### 后端模块树

```
apps/django/
├── config/                        # Django 项目设置
│   ├── settings/
│   │   ├── base.py                # 通用配置 (DRF/JWT/CORS/Celery/Channels)
│   │   ├── dev.py                 # 开发 (SQLite, 关闭 throttle, CORS *)
│   │   ├── prod.py                # 生产 (强校验 SECRET/CORS/DB, Redis 强依赖)
│   │   └── test.py                # 测试 (in-memory SQLite, throttle 关闭, eager Celery)
│   ├── urls.py                    # 根路由 (api_v1 + spa_fallback + admin)
│   ├── asgi.py / wsgi.py
│   └── celery_app.py              # Celery app 实例
│
├── apps/                          # 28 个业务 app
│   ├── core/                      # User/Department/Role + V2 权限 (permission_check/role_v2_query/scope_resolver)
│   ├── field_acl/                 # 字段级 ACL (mask phone/email/salary)
│   ├── audit/                     # 5 路审计 (中间件 + signal + models)
│   ├── notification/              # 22 模板 + 4 渠道
│   ├── integration/               # 企微/短信/RPA adapter (Fernet 加密凭据)
│   ├── gdpr/                      # 数据保留 + 软删除
│   │
│   ├── process/                   # 招聘流程引擎 (RecruitmentProcess/Stage/Link/Rule)
│   ├── entry_condition/           # 阶段进入条件
│   ├── time_limit/                # 阶段限时规则
│   ├── automation/                # 自动化规则
│   │
│   ├── candidate/                 # 候选人 (11 状态机 G44, 字段脱敏 G8, 倒序推荐 G11)
│   ├── add_candidate/             # V2 创建候选人 (Affinda 简历解析)
│   ├── application/               # 应聘记录
│   ├── demand/                    # 需求 (8 状态机 + 4 步审批链)
│   ├── position/                  # 职位 (3 状态机)
│   ├── offer/                     # Offer (9 状态机 + 4 PDF 模板)
│   ├── onboarding/                # 待入职 (8 状态机)
│   ├── invitation/                # 邀约中心 (抢单 + cron 3 次归档)
│   ├── interview/                 # 面试 (5 状态机)
│   ├── referral/                  # 内推 (N+1 检测 + 奖金)
│   │   └── urls_stubs.py          # ⚠️ 20+ stub 端点 (2026-08-03 加 X-Stub header + 日志告警)
│   ├── talent_pool/               # 6 子库人才库
│   ├── channel/                   # 渠道
│   ├── analytics/                 # 数据中心 KPI
│   ├── mou/                       # V2 权限管理 (9 endpoints)
│   ├── library/                   # G41 院校/公司库
│   ├── scraped_resume/            # G30 RPA (mock adapter)
│   ├── external_sync/             # G40 法人公司同步 (stub)
│   ├── duplicate_check/           # G45 简历查重 (stub)
│   └── data/                      # G35 数据中心 (stub, 实际 endpoint 在 analytics/)
│
├── tests/                         # 39 pytest (12 套件, 100% pass)
├── seeds/                         # 7 个 seed JSON (system_stages / system_roles / 4 offer 模板 / demo_user)
├── scripts/                       # init.sh / create_tables_sql.py / verify_audit_fixes.py
├── conftest.py                    # pytest fixtures + V2 schema 兼容 (sqlite 上补 V2 列)
└── pytest.ini                     # DJANGO_SETTINGS_MODULE=config.settings.test
```

### 前端模块树

```
web/app/
├── src/
│   ├── api/                       # 27+ 业务 API 客户端 (axios + JWT 拦截器 + request dedup)
│   ├── stores/                    # Pinia (user/addCandidate/demand/department)
│   ├── router/                    # vue-router 4 + RBAC 守卫 (meta.roles + requiresAuth)
│   ├── components/                # 通用 + dashboard + common + candidate
│   ├── pages/                     # 38+ 路由页面 (Layout/Login/Dashboard/各业务域)
│   ├── styles/                    # tokens.css (OKLCH + 4pt spacing + fade-up stagger)
│   ├── utils/                     # debounce/request-dedup/role 派生
│   └── config/                    # api.baseUrl + backend.url/port 统一配置
├── e2e/                           # Playwright 6 spec
├── vite.config.ts                 # es2022 + manualChunks (vendor-naive-ui atomic)
├── tsconfig.json                  # target: ES2022 + strict
└── eslint.config.js               # ESLint 9 flat
```

## 关键设计决策

### 1. V1/V2 权限双轨 (T30 cutover)

V1 (legacy) 和 V2 (current) **模型并存**, `apps/core/models.py` (V1, managed=False) + `apps/core/models_permission_v2.py` (V2, managed=True)。
V2 切库 `T17 v2_apply_schema` 后 V1 表 drop。当前 fixtures 兼容双 schema (V2 columns 通过 conftest `_ensure_v2_schema_on_sqlite` 补到 sqlite 测试 DB)。

### 2. snake_case ↔ camelCase 自动桥 (DRF + djangorestframework-camel-case)

API 出 Python snake_case → JSON camelCase (FE 直接消费); API 入 FE camelCase → DRF serializer snake_case。
单词字段 (id/username/access/refresh) 不变,字典 key 不变。

### 3. 字段级脱敏 (G8) + 字段级 ACL (G43)

`FieldAclService.apply_acl(entity, data, user)` 在 view 层包装:
- 敏感字段 (phone/email/id_card/salary) 默认 mask (maskPhone/maskEmail/maskIdCard/maskBankCard)
- ACL 规则 (FieldACL 表) 可显式 NONE/MASK/READ,优先级 role-tier 严格
- superuser bypass

### 4. SPA fallback

`config/urls.py` 末尾 re_path 排除 `/api/ /health/ /static/ /__debug__/` 后 fallthrough 到 `web/app/dist/index.html` (whitenoise serve `/static/*`)。深链 `/candidates/123` 走 vue-router。

### 5. admin token env 注入

`/admin/` 改成 `/${ADMIN_URL_TOKEN}/` (默认 `ops-dashboard-7f3b9c2e`, 生产必须设随机串)。spa_fallback 同步。

## 性能优化 (Plan O, 2026-06-11)

- 后端: gzip + ETag 30s + 304 协商, 列表分页 middleware (max 100), N+1 detector, Offer 列表 include (3 表 1 query)
- 前端: Dashboard 7 子组件 defineAsyncComponent, 路由级 code splitting (webpackChunkName), vite manualChunks (vendor-naive-ui atomic 避免 TDZ), debounce 300ms, request dedup, rollup-plugin-visualizer analyze
- 度量: /dashboard 首屏 JS 365KB gzip, /api/offers 38KB gzip (-60%)

## 已知问题 (2026-08-03)

- **stub 路由**: 20+ endpoint 返 fake UUID + PENDING, 已在 `urls_stubs.py` 加 `X-Stub: true` header + WARNING log + `_log_stub_hit` 监控埋点,生产应监控 `apps.stub` logger
- **django-fsm 2.8.1**: 已废弃, 迁 viewflow.fsm (P2 升级窗口)
- **P2 集成**: 企微/腾讯会议/摩卡/背调/RPA/IM 需企业 API 授权

    └── __tests__/                  # Jest 单元测试
```

### 前端模块树

```
src/
├── main.ts                         # Vue 应用入口（注册 Ant Design Vue、Pinia、Router）
├── App.vue
├── config/
│   └── index.ts                    # 端口、API baseUrl 等常量
│
├── api/
│   └── auth.ts                     # axios 实例 + 请求/响应拦截器
│
├── stores/                         # Pinia
│   ├── user.ts                     # 当前登录用户 + token
│   ├── department.ts
│   └── demand.ts
│
├── router/
│   └── index.ts                    # 路由表 + beforeEach 守卫
│
└── pages/
    ├── Login.vue                   # 登录页
    ├── Layout.vue                  # 主布局（侧边栏 + 头部 + 内容区）
    ├── Dashboard.vue
    ├── demand/                     # 需求管理
    ├── position/                   # 职位管理
    ├── candidate/                  # 候选人
    ├── interview/                  # 面试
    ├── offer/                      # Offer
    ├── onboarding/                 # 入职
    ├── talent/                     # 人才库
    ├── resume/                     # 简历
    ├── invitation/                 # 邀约
    ├── screening/                  # 简历筛选
    ├── notification/               # 通知
    └── settings/                   # 系统设置（含 Placeholder.vue）
```

## 数据流示例：用户登录

```
1. 用户在 Login.vue 输入 admin / admin123
2. Login.vue 调用 login() from api/auth.ts
3. axios POST /api/auth/login
4. Vite 拦截 /api/*，proxy_pass → http://localhost:5125/api/auth/login
5. Express 路由 /api/auth/login (无需 authMiddleware)
6. auth.routes.js:
   - prisma.user.findUnique({ username: 'admin' })
   - bcrypt.compare('admin123', user.password)
   - prisma.user.update({ lastLoginAt: now() })
   - jwt.sign({ userId, role }, JWT_SECRET, { expiresIn: '7d' })
7. 返回 { success: true, data: { token, user } }
8. 前端：
   - localStorage.setItem('token', token)
   - userStore.setUser({ ...user })    # 写入 Pinia
   - router.push('/dashboard')
9. router.beforeEach 检查 localStorage.token 存在 → 放行
10. Dashboard 渲染（无 API 调用）
```

## 数据流示例：受保护资源

```
1. 浏览器调 GET /api/users
2. Vite proxy → 后端
3. Express 路由 /api/users
4. app.js 级别挂的 authMiddleware 先执行：
   - 解析 Authorization: Bearer <token>
   - jwt.verify(token, JWT_SECRET) → { userId, role }
   - prisma.user.findUnique({ id: userId })
   - 检查 user.status === 'ACTIVE'
   - 注入 req.user / req.userId
5. userRoutes 控制器执行（req.userId 可用）
6. 返回数据
7. axios 响应拦截器：成功透传；4xx/5xx 触发 catch
   - 401 → handleAuthFailure() → 清 token + 跳 /login（详见 auth.ts）
```

## 关键技术决策

### 0. 为什么 2026-06 把 XState v5 状态机替换为 Prisma 字段 + 纯函数转换图？

- **决策**：6 个新状态机（需求/职位/邀约/Offer/待入职/面试）放弃 XState v5，改用 Prisma 字段 + `xxx-state-machine.service.js` 纯函数 + Transition 图
- **优点**：
  - 数据库是真实状态源（XState 是内存状态，DB 同步是隐患）
  - 测试更简单（纯函数 + mock prisma，无需启动 XState actor）
  - 减少依赖
  - 与 Prisma migration 同步
- **代价**：
  - 失去 XState 的可视化状态机
  - 复杂守卫逻辑需在 service 内手写
- **保留**：Referral 仍用 XState v5（已上线，3 个 machines + 9 测试），因为其状态转换复杂

### 1. 为什么所有路由用 `app.use('/api/*', authMiddleware, *Router)` 而不是每个路由单独挂？

### 2. 为什么 auth.ts 拦截器不再做 token 刷新？

之前的设计：401 → 调 `/auth/refresh` → 拿新 token → 重试。
**问题**：后端没实现 `/auth/refresh`，导致 401 自动跳登录页（幽灵 bug）。
**当前方案**：401 → 直接登出 + 跳登录。简单可靠。
**未来**：如果要做 token 刷新，必须先实现后端 `/auth/refresh` 端点 + refresh token 机制。

### 3. 为什么用 `node --env-file=.env` 而不是 dotenv 包？

- Node 20.6+ 内建支持 `--env-file`，零依赖
- 不需要 `require('dotenv').config()` 污染每个入口文件
- 对 Prisma CLI 也生效（之前 Prisma 找不到 DATABASE_URL 是因为 `dotenv` 加载顺序问题）

### 4. 为什么用 XState 状态机管内推流程？

- 内推码、推荐记录、奖励 3 个实体各自有复杂状态流转
- 状态机让"哪些事件触发什么转移"集中可视化、可测试
- 替代散落的 if/else，状态合法性由机器保证

### 5. 为什么 prisma db push 而不是 migrate？

历史原因：`prisma/migrations/` 只有 referral phase1 的 migration，主体 48 张表的 base migration 缺失。
**短期**：用 `db push` 推全部 schema（快、适合开发期）。
**长期**：补全 base migration，或从现在起 `prisma migrate dev --name xxx` 累积。

## 数据模型关系（核心）

```
User ─┬─ Department (N:1)
      ├─ Position (1:N, as manager)
      ├─ Candidate (1:N, as creator)
      └─ ReferralCode (1:1)

Candidate ─┬─ Resume (1:N)
           ├─ Application (1:N) ─┬─ Interview (1:N)
           │                      ├─ Offer (1:1)
           │                      └─ Onboarding (1:1)
           └─ ReferralRecord (1:N) ── ReferralReward (1:1)

ReferralCode ──── ReferralRecord (1:N) ──── ReferralReward (1:1)
                                        └─ ExpertConfig (N:N, via User)

ReferralRule (1:N) ──── RewardStrategy (1:1)
```

## 部署架构（生产）

```
┌──────────────┐
│ Cloudflare   │ HTTPS 终止
│ Tunnel       │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ nginx        │ 静态文件 + 反代 /api 到 backend
│              │ 80/443
└──────┬───────┘
       │
       ├─▶ /            → frontend/dist (静态)
       └─▶ /api/*       → backend:5125

backend (node) + MySQL (docker-compose)
```

生产部署配置见 `docker-compose.yml` + `backend/Dockerfile` + `frontend/Dockerfile`。

## 安全模型

| 层 | 措施 |
|---|---|
| 网络 | HTTPS (Cloudflare Tunnel) + CORS 白名单 |
| 应用 | helmet()、express-rate-limit、JWT 鉴权 |
| 数据 | Prisma 预编译 SQL 防 SQL 注入、bcrypt 加盐密码 |
| 操作 | 角色权限矩阵（Permission / MouPermission 表） |
| 审计 | 关键操作日志（待补全） |
