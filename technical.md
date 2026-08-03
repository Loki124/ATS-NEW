# ATS招聘管理系统 - 技术说明文档

> **最后更新**: 2026-08-03 — 实际已切到 Django 6.0.6 + DRF 3.15 (旧 Node.js/Express 栈 2026-06 已废弃, 详见 `MIGRATION.md`)
>
> 当前真实状态: 28 apps / 60+ 端点 / 78 张表 / 9 业务状态机 / 39 pytest + 132 vitest 全过
> 真实架构图见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## 1. 技术架构

### 1.1 整体架构 (2026-08-03 当前)
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
       │  78 张表     │       │ cache+broker│        │             │
       └─────────────┘       └─────────────┘        └─────────────┘
```

### 1.2 技术栈 (2026-08-03 当前)

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **前端** | | | |
| 前端框架 | Vue 3 | 3.4+ | Composition API |
| 构建工具 | Vite | 5.x | 快速启动/热更新 |
| UI 框架 | **Naive UI** (2026-06 迁移) | 2.44+ | 企业级组件库 |
| 样式方案 | **UnoCSS** (2026-06 迁移) | 66.7+ | 原子化 CSS |
| 图标库 | **@vicons/ionicons5** | 0.13+ | 统一图标 |
| 状态管理 | Pinia | 2.x | Vue 状态管理 |
| 路由 | Vue Router | 4.x | SPA 路由 + RBAC 守卫 |
| HTTP | Axios | 1.x | API 客户端 (含 JWT 拦截器 + request dedup) |
| 单元测试 | Vitest | 2.x | 132 tests, happy-dom |
| E2E | Playwright | 1.49 | 6 spec / 18 场景 |
| **后端** | | | |
| 后端框架 | **Django** (2026-06 切) | **6.0.6** | 实际版本, 2026-07 解锁主版本锁 |
| API 框架 | **Django REST Framework** | 3.15 | ViewSet + Router + drf-spectacular |
| ORM | **Django ORM** | - | 78 张表, 28 apps |
| 数据库 | **MySQL 8** | 8.x | 生产 (SQLite 3 用于 dev/test) |
| 认证 | **djangorestframework-simplejwt** | 5.3+ | access 60min + refresh 7d, ROTATE |
| 状态机 | **django-fsm** | 2.8.1 | 9 业务状态机 (⚠️ 已废弃, 迁 viewflow.fsm) |
| 异步任务 | **Celery + Redis** | 5.4 + 5.0 | cron / 报表导出 / GDPR 清理 |
| WebSocket | **Channels 4.1** | - | 实时通知 / 协作 |
| 缓存 | **django-redis / LocMem** | 5.0+ | 限流 + 幂等 + session (prod 强 Redis) |
| 监控 | **Sentry + django-prometheus** | 2.3 + 2.3 | 错误追踪 + 性能指标 |
| 字段脱敏 | **FieldAclService** (G8 + G43) | - | phone/email/id_card 自动 mask |
| PDF | **reportlab 4.2** | - | 服务端 PDF (4 个 Offer 模板 + 背调报告) |
| 集成 | **affinda 4.0** | - | 简历解析 (V2 add-candidate) |
| **测试** | | | |
| 后端测试 | pytest + pytest-django | 9.x | 39 tests, 12 套件 |
| 前端测试 | vitest + @vue/test-utils | 2.x | 132 tests |
| E2E | Playwright | 1.49 | 6 spec / 18 场景 |
| Lint | flake8 + ESLint 9 (flat) | - | Python + TypeScript/Vue |
| Type check | mypy + vue-tsc 2.2 | - | Django + Vue |

---

## 2. 项目结构

### 2.1 前端项目结构
```
frontend/
├── public/                  # 静态资源
├── src/
│   ├── api/                # API接口封装
│   │   └── auth.ts         # 认证相关API
│   ├── assets/             # 静态资源
│   ├── components/         # 通用组件
│   ├── config/             # 配置文件
│   │   └── index.ts        # 统一配置
│   ├── pages/              # 页面组件
│   │   ├── Layout.vue      # 主布局
│   │   ├── Login.vue       # 登录页
│   │   ├── Dashboard.vue   # 工作台
│   │   ├── demand/         # 需求管理
│   │   ├── candidate/      # 候选人
│   │   ├── interview/      # 面试管理
│   │   ├── offer/          # Offer管理
│   │   ├── settings/       # 系统设置
│   │   └── ...
│   ├── router/             # 路由配置
│   │   └── index.ts
│   ├── stores/             # 状态管理
│   │   └── user.ts         # 用户状态
│   ├── types/              # TypeScript类型
│   ├── App.vue             # 根组件
│   ├── main.ts             # 入口文件
│   └── index.css           # 全局样式
├── index.html
├── vite.config.ts          # Vite配置
├── tailwind.config.js      # Tailwind配置
├── tsconfig.json           # TypeScript配置
└── package.json
```

### 2.2 后端项目结构
```
backend/
├── prisma/
│   ├── schema.prisma       # 数据模型
│   ├── dev.db              # SQLite数据库
│   └── seed/               # 种子数据
├── src/
│   ├── config/             # 配置文件
│   │   └── index.js        # 后端配置
│   ├── middleware/         # 中间件
│   │   ├── auth.middleware.js
│   │   └── error.middleware.js
│   ├── routes/             # 路由
│   │   ├── auth.routes.js
│   │   ├── user.routes.js
│   │   ├── candidate.routes.js
│   │   ├── demand.routes.js
│   │   ├── process.routes.js
│   │   ├── permission.routes.js
│   │   ├── permission-v2.routes.js
│   │   └── system.routes.js
│   ├── app.js              # 应用入口
│   └── server.js           # 服务器启动
├── uploads/                # 文件上传目录
├── .env                    # 环境变量
├── package.json
└── nodemon.json
```

---

## 3. API接口设计

### 3.1 认证接口
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 用户登录 |
| POST | /api/auth/register | 用户注册 |
| GET | /api/auth/me | 获取当前用户 |

### 3.2 用户管理接口
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/users | 获取用户列表 |
| GET | /api/users/:id | 获取单个用户 |
| POST | /api/users | 创建用户 |
| PUT | /api/users/:id | 更新用户 |
| DELETE | /api/users/:id | 删除用户 |
| GET | /api/users/departments | 获取部门列表 |

### 3.3 招聘需求接口
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/demands | 获取需求列表 |
| GET | /api/demands/:id | 获取需求详情 |
| POST | /api/demands | 创建需求 |
| PUT | /api/demands/:id | 更新需求 |
| DELETE | /api/demands/:id | 删除需求 |

### 3.4 权限管理接口
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/permissions-v2/mou | 获取MOU列表 |
| GET | /api/permissions-v2/containers | 获取容器列表 |
| GET | /api/permissions-v2/mutual-exclusion-groups | 获取互斥组 |

### 3.5 系统配置接口
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/system/config/demand | 获取需求配置 |
| POST | /api/system/config/demand | 保存需求配置 |

---

## 4. 数据模型

### 4.1 核心实体关系
```
User ←→ Department (N:1)
User ←→ Demand (N:1)
Demand ←→ Position (1:N)
Position ←→ Candidate (1:N)
Candidate ←→ Application (1:N)
Candidate ←→ Interview (1:N)
Candidate ←→ Offer (1:1)
Candidate ←→ Onboarding (1:1)
```

### 4.2 主要数据表

#### User（用户表）
- id, username, password, realName, email, phone
- roleType, status, departmentId
- wechatWorkUserId, mochaUserId
- permissionMode, createdAt

#### Department（部门表）
- id, name, code, parentId, level, path
- managerId, status, sortOrder

#### Demand（招聘需求表）
- id, code, title, type, status
- departmentId, managerId, requesterId
- headcount, budget, deadline

#### Position（职位表）
- id, title, code, demandId, status
- departmentId, managerId

#### Candidate（候选人表）
- id, name, phone, email, resumeUrl
- source, status, creatorId

---

## 5. 配置管理

### 5.1 前端配置 (frontend/src/config/index.ts)
```typescript
export const config = {
  frontend: { port: 5212 },
  backend: { port: 5125, url: 'http://localhost:5125' },
  api: { baseUrl: '/api', timeout: 15000 },
}
```

### 5.2 后端配置 (backend/src/config/index.js)
```javascript
export const app = { port: 5125, name: 'ATS招聘管理系统' }
export const jwt = { secret: 'ats-secret-key-2024', expiresIn: '7d' }
export const cors = { origin: 'http://localhost:5212' }
```

### 5.3 环境变量 (backend/.env)
```
PORT=5125
JWT_SECRET=ats-super-secret-key-2024-production
DATABASE_URL=file:./dev.db
CORS_ORIGIN=http://localhost:5212
```

---

## 6. 端口配置

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端开发服务器 | 5212 | Vite Dev Server |
| 后端API服务器 | 5125 | Express Server |
| SQLite数据库 | - | 文件: prisma/dev.db |

### 前后端通讯
- 前端: http://localhost:5212
- 后端: http://localhost:5125
- 前端通过 Vite 代理将 /api 请求转发到后端

---

## 7. 启动命令

### 7.1 开发环境启动
```bash
# 后端启动
cd backend
npm run dev
# 或 node src/app.js

# 前端启动
cd frontend
npm run dev
```

### 7.2 生产构建
```bash
# 前端构建
cd frontend
npm run build

# 后端使用
cd backend
node src/app.js
```

---

## 8. 安全机制

### 8.1 认证机制
- JWT Token 认证
- Token 有效期 7 天
- Token 自动刷新

### 8.2 接口保护
- 认证中间件验证 Token
- 角色权限检查
- SQL 注入防护

### 8.3 安全中间件
- Helmet.js 安全头
- Rate Limit 请求限流
- CORS 跨域控制

---

## 9. 技术亮点

1. **Vue 3 Composition API** - 代码组织更清晰
2. **Pinia 状态管理** - 类型安全的状态管理
3. ~~**Prisma ORM**~~ → **Django ORM** (2026-06 切, 更成熟的内置 ORM, 78 张表)
4. ~~**Ant Design Vue 5**~~ → **Naive UI 2.44** (2026-06 改, ATS 风格更搭, TypeScript 支持更好)
5. **Vite 5 快速构建** - 秒级启动/热更新, manualChunks vendor-naive-ui atomic 避免 TDZ
6. **JWT 认证** - djangorestframework-simplejwt, access 60min + refresh 7d + ROTATE + BLACKLIST

### 2026-06 ~ 2026-08 关键架构变更

| 时间 | 变更 | 影响 |
|---|---|---|
| 2026-06 | Node.js/Express/Prisma → Django 6.0/DRF 3.15 | 全栈重写, 35 → 60+ 端点 |
| 2026-06 | SQLite-only → MySQL 8 (生产) + SQLite (dev/test) | 生产数据库升级 |
| 2026-06 | Ant Design Vue → Naive UI 2.44 | UI 框架替换, 配套 dashboard 重设计 |
| 2026-06 | Tailwind + DaisyUI → UnoCSS | 原子化 CSS |
| 2026-06 | XState v5 → django-fsm | 状态机迁移, 9 个业务状态机 |
| 2026-07 | Django 5.0.6 → 6.0.x | 解锁主版本锁 |
| 2026-07 | node-cron → Celery + Redis | 异步任务平台化, beat scheduler |
| 2026-07 | authMiddleware → djangorestframework-simplejwt | JWT 双 token + blacklist |
| 2026-07 | Admin `/admin/` → `/${ADMIN_URL_TOKEN}/` | 后门 token env 化 (2026-08-03) |
| 2026-08 | CI 切到 pytest + npm | .github/workflows/ci.yml 重写 |
| 2026-08 | stub 路由加 X-Stub header + 告警 | 20+ 兜底端点可视化, 防静默丢数据 |
| 2026-08 | 39/39 pytest + 132/132 vitest 全过 | 修复 10 个长期 fail |

---

*文档版本: V2.0 (2026-08-03 Mavis 现状对齐)*
*创建时间: 2026/05/11*
*技术栈: Django 6.0.6 + DRF 3.15 + MySQL 8 + Redis 7 + Celery 5.4 + Vue 3 + Vite 5 + Naive UI 2.44 + UnoCSS*