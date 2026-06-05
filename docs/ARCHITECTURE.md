# ARCHITECTURE — 系统架构

## 总览

```
┌──────────────────┐         ┌──────────────────┐
│  Browser (Vue 3) │ ──────▶ │  Vite Dev Server │
│  5212            │  /api/* │  + Proxy         │
└──────────────────┘         └────────┬─────────┘
                                      │ proxy_pass
                                      ▼
                            ┌──────────────────┐
                            │  Express Backend │
                            │  5125            │
                            │  + Prisma ORM    │
                            └────────┬─────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │   MySQL 8/9     │
                            │   3306           │
                            └──────────────────┘
```

## 模块依赖

### 后端模块树

```
src/
├── app.js                          # Express 主入口
│   ├── helmet()                    # 安全头
│   ├── cors()                      # 跨域
│   ├── express.json()              # JSON 解析
│   ├── rateLimit()                 # /api 速率限制（300/分钟）
│   ├── /api/auth → authRoutes      # 公开
│   ├── /api/*    → authMiddleware → *Routes  # 受保护
│   └── static(FRONTEND_DIST)       # 生产模式直出前端
│
├── config/
│   └── index.js                    # 统一读 .env，提供 app/database/jwt/cors
│
├── middleware/
│   ├── auth.middleware.js          # JWT 校验 + 注入 req.user / req.userId
│   └── error.middleware.js         # 全局错误处理
│
├── routes/
│   ├── auth.routes.js              # /auth/login, /auth/me, /auth/register, /auth/change-password
│   ├── user.routes.js              # /users CRUD
│   ├── department.routes.js        # /departments + 部门树
│   ├── candidate.routes.js         # /candidates（含 archive/restore）
│   ├── demand.routes.js            # /demands
│   ├── resume.routes.js            # /resumes
│   ├── process.routes.js           # /processes
│   ├── system.routes.js            # /system
│   └── permission-v2.routes.js     # /permissions-v2 (MOU)
│
└── referral/                       # 内推门户（独立模块）
    ├── index.js                    # 挂载 5 个子路由 + 启动 scheduler
    ├── machines/                   # XState v5 状态机
    │   ├── code.machine.js
    │   ├── record.machine.js
    │   └── reward.machine.js
    ├── services/                   # 业务逻辑
    │   ├── code.service.js
    │   ├── record.service.js
    │   ├── reward.service.js
    │   └── rule-evaluator.js
    ├── routes/                     # 5 个 REST 路由
    │   ├── codes.routes.js         # /codes/me, /codes/validate
    │   ├── records.routes.js       # /records (含 /me/summary)
    │   ├── rewards.routes.js
    │   ├── rules.routes.js
    │   └── expert-configs.routes.js
    ├── scheduler/                  # cron 任务
    │   └── referral.scheduler.js   # 3 个定时任务
    ├── events/
    ├── validators/
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

### 1. 为什么所有路由用 `app.use('/api/*', authMiddleware, *Router)` 而不是每个路由单独挂？

- **优点**：DRY，新增路由自动受保护，不会漏挂
- **代价**：每个请求都跑 authMiddleware（一次 DB 查询 + bcrypt 验证可以省掉，因为 JWT 已经验证了签名）
- **未来优化**：可以在 JWT payload 里塞 user 信息，省一次 DB 查询

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
