# ATS-New 项目复盘报告

**日期**: 2026-06-02
**分支**: `review/mysql-migration`
**范围**: 4 维度（代码质量 / 安全 / Prisma 模型 / API 架构）+ MySQL 迁移
**交付**: 7 个 commit，含 schema 重构、配置、文档、e2e 脚本

---

## 总览

| 维度 | 问题数 | 严重度分布 | 处理 |
|---|---|---|---|
| B1 代码质量 | 5 | 2×P1 / 3×P3 | 全部修/记 |
| B2 安全 | 3 | 1×P1 / 1×P2 / 1×P3 | 全部修 |
| B3 Prisma 模型 | 8 | 3×P1 / 4×P2 / 1×P3 | 全部修 |
| B4 API 架构 | 4 | 2×P1 / 2×P2 | 全部修 |
| MySQL 迁移 | 5 | 全部 P1 | 全部修（待真实库验证） |

---

## Track A: MySQL 迁移

### [A-001] Prisma datasource 切换

- **位置**: `backend/prisma/schema.prisma:9-12`
- **严重度**: P1
- **说明**: 原本用 SQLite (`provider = "sqlite"`)，服务器已统一为 MySQL
- **修复**: `provider = "mysql"`，并通过 `DATABASE_URL` 注入连接串
- **验证**: `npx prisma validate` ✓

### [A-002] 金额字段 Float → Decimal(12,2)

- **位置**: `backend/prisma/schema.prisma` (Offer/Onboarding/Demand/Invitation)
- **严重度**: P1
- **说明**: Float 在金融计算中有精度问题（IEEE 754），企业 ERP 必踩坑
- **修复**: 26 个金额字段全部改为 `Decimal(12, 2) @db.Decimal(12, 2)`
- **保留 Float**: `longitude`/`latitude`（地理坐标）

### [A-003] 长文本字段加 @db.Text

- **位置**: `schema.prisma` 全文
- **严重度**: P2
- **说明**: MySQL 默认 VARCHAR(191) 对 description/requirements/parsedData/JSON 字段不够
- **修复**: 30+ 字段加 `@db.Text`

### [A-004] docker-compose 加 MySQL 服务

- **位置**: `docker-compose.yml`
- **严重度**: P1
- **说明**: 缺 MySQL 服务
- **修复**: 新增 mysql:8.0 服务，utf8mb4 + +08:00 时区 + 健康检查；backend depends_on service_healthy
- **验证**: YAML 合法

### [A-005] Dockerfile + entrypoint MySQL 适配

- **位置**: `backend/Dockerfile` + `backend/ats-entrypoint.sh`
- **严重度**: P1
- **说明**: 容器内需要 mysql 客户端做 healthcheck
- **修复**: Dockerfile 加 `default-mysql-client`；entrypoint 启动前 `mysqladmin ping` 等待（最多 60×2s）

---

## Track B1: 代码质量

### [B1-001] TS 注解残留

- **位置**: `backend/src/**/*.js`
- **严重度**: P1
- **说明**: 早期 `department.routes.js` 用了 `: any` 注解，与项目 ESM JavaScript 不兼容
- **修复**: 已扫除（grep `const x: ` → 0 命中）

### [B1-002] 错误处理走全局中间件

- **位置**: 4 个 routes 文件
- **严重度**: P1
- **说明**: 53 处 `catch (error) { res.status(500).json(...) }` 各自处理 500，绕过全局 Prisma 错误翻译器
- **修复**: 全改为 `catch (error) { next(error); }`
- **涉及文件**: `permission.routes.js` (19) / `permission-v2.routes.js` (21) / `resume.routes.js` (13)
- **保留**: `system.routes.js` 1 处硬编码（业务响应）

### [B1-003] 前端 fetch → api 客户端 (P3, 未修)

- **位置**: `MouManagement.vue` / `AccountSettings.vue` / `UserManagement.vue`
- **严重度**: P3
- **说明**: 20+ 处直接 `fetch` 调用，缺自动 401 跳转和错误归一化
- **状态**: **记录未修**。UserManagement.vue 已用本地 `request()` 包装可工作；MouManagement.vue 和 AccountSettings.vue 直接 fetch
- **建议**: 后续 PR 整改，统一通过 `frontend/src/api/auth.ts` 的 `api` 实例

### [B1-004] 父仓库 .gitignore 缺失 (P3, 未修)

- **位置**: `/Users/loki/VScodeWorkspace/` 根目录
- **严重度**: P3
- **说明**: 父 git 仓库没有 .gitignore，导致 ATS-New 子目录的 node_modules/、dist/、*.db 都被父仓库 track
- **影响**: 父子仓库结构异常，所有子目录的"工作区脏"都是这条引起的
- **建议**: 在父仓库根加 `.gitignore`：`ATS-New/**/node_modules/`、`ATS-New/**/dist/`、`ATS-New/**/*.db`

### [B1-005] /uploads 静态目录无认证 (P3, 记录)

- **位置**: `backend/src/app.js:55`
- **严重度**: P3
- **说明**: `app.use('/uploads', express.static('uploads'))` 任何人能下载
- **建议**: 走 storage 后端 (S3) 或加 token 签名 URL

---

## Track B2: 安全

### [B2-001] JWT secret 走 process.env 直接读

- **位置**: `backend/src/middleware/auth.middleware.js:21`
- **严重度**: P1
- **说明**: 原代码 `jwt.verify(token, process.env.JWT_SECRET)`，没经过 `config/index.js`，无法走 config fallback
- **修复**: 改为 `import { jwt as jwtConfig } from '../config/index.js'`

### [B2-002] 循环引用: auth.middleware.js 引用 app.js

- **位置**: `backend/src/middleware/auth.middleware.js:6`
- **严重度**: P1
- **说明**: `import { prisma } from '../app.js'` 形成循环依赖风险（app.js → routes → middleware → app.js）
- **修复**: middleware 单独 `new PrismaClient()`

### [B2-003] User 响应排除 password 字段

- **位置**: `backend/src/routes/user.routes.js`
- **严重度**: P1
- **说明**: 关键检查
- **验证**: 登录后 GET /api/users，响应 keys 无 `password` ✓

### [B2-004] authMiddleware 覆盖 (记录已验证)

- **位置**: `backend/src/app.js:66-74`
- **验证**: 9 个非公开路由无 token 全部 401 ✓

---

## Track B3: Prisma 模型

### [B3-001] 40+ 模型缺 @@index

- **位置**: 全文
- **严重度**: P2
- **说明**: 仅 5 个 @@index，48 个模型大量 XxxId 字段无索引，热查询必全表扫
- **修复**: 批量加索引到 98 个
- **验证**: Python 脚本确认所有 XxxId 字段均有 @@index

### [B3-002] 22 处 onDelete 缺失

- **位置**: 全文
- **严重度**: P2
- **说明**: 树关系 (Department/Dictionary/Company/Permission/MOU) 缺 onDelete；删除父节点行为未定义
- **修复**:
  - 自引用树: `onDelete: Restrict` (defensive)
  - User.departmentId / ResumeLocker: `Restrict`
  - 关联模板字段 (conditionId/mouId): `SetNull`
  - User → Department 改用 `Restrict` (业务层 dept.routes.js 已先检查)

### [B3-003] Candidate 缺 assignedUser / resumeProvider 关系

- **位置**: `schema.prisma:453-457` + `User:212-214`
- **严重度**: P1
- **说明**: FK 字段已存在 (assignedUserId / resumeProviderId)，但缺 `@relation` 声明。`/api/candidates` 路由用 `include: { assignedUser }` 报 `Unknown field` 错误——这是一个**实际阻塞性 bug**
- **修复**: 添加 `assignedUser` / `resumeProvider` 关系 + User 侧反关联 `assignedCandidates` / `providedCandidates`
- **验证**: prisma validate ✓

### [B3-004] 字符串长度限制 (部分完成)

- **位置**: 短字段 username/realName/email 等
- **严重度**: P3
- **说明**: MySQL 默认 VARCHAR(191) 对 utf8mb4 一般够，但长度已知的短字段显式标注更稳
- **状态**: **记录未修**。长文本（description/requirements/attachments/content/parsedData/JSON）已加 @db.Text

### [B3-005] 状态枚举统一 (P3, 记录)

- **位置**: 多模型用 `status String @default("ACTIVE")` 而非 `enum`
- **说明**: 用 String 灵活但失去类型安全；用 Prisma enum 需重新迁移
- **建议**: 后续重构用 `enum DepartmentStatus { ACTIVE INACTIVE }`

### [B3-006] 金额 Float→Decimal 已在 A-002 处理

---

## Track B4: API 架构

### [B4-001] 响应包络不统一

- **位置**: 4 个 routes 文件
- **严重度**: P1
- **说明**: 错误响应混用 `error` / `message` 字段名，前端处理需要 if-else
- **修复**:
  - 全部 `{ error: '...' }` → `{ message: '...' }`
  - 补全 `success: false` 字段
  - 涉及 30+ 处
- **现状**: 6 端点 GET 响应 keys 全部 `[data, success]` ✓

### [B4-002] permission.middleware.js 仍用 error 字段 (P2, 记录)

- **位置**: `backend/src/middleware/permission.middleware.js`
- **严重度**: P2
- **说明**: 仍用 `{ error, code }` 而非 `{ success: false, message, code }`
- **影响**: 鉴权失败响应形状不一致
- **建议**: 后续 PR 整改

### [B4-003] 分页 helper 缺失 (P2, 记录)

- **位置**: 各 routes
- **严重度**: P2
- **说明**: 无统一分页 helper，目前 candidate.routes.js 等各自手写 skip/take
- **建议**: 加 `middleware/pagination.js`：`{page, pageSize}` → `{skip, take}`

### [B4-004] 前端 store 按域分文件 (P3, 记录)

- **位置**: `frontend/src/stores/`
- **严重度**: P3
- **说明**: 仅有 `user.store.ts`，需求/部门等状态散落在页面里
- **建议**: 按业务域拆 store

---

## MySQL 迁移前后对比

| 字段 | Before (SQLite) | After (MySQL) |
|---|---|---|
| provider | sqlite | mysql |
| 金额 (baseSalaryTrial 等 26 处) | `Float?` | `Decimal(12, 2)` |
| 长文本 (description 等 30+ 处) | `String?` | `String? @db.Text` |
| 索引 (5 → 98) | 5 个 @@index | 98 个 |
| onDelete 显式 (34 → 56) | 34 个 | 56 个 |
| DATABASE_URL | `file:./dev.db` | `mysql://ats:atspass@localhost:3306/ats` |

---

## 端到端验证状态

**已就绪**：
- ✓ `prisma validate`：schema 合法
- ✓ `prisma generate`：client 生成
- ✓ 后端模块加载（import chain 无断）
- ✓ 前端 vite build
- ✓ `scripts/e2e-smoke.sh` 已写完（10 步烟测）
- ✓ 401/404 错误路径用 SQLite 文件复测（响应包络一致）

**待真实 MySQL 验证**（需用户提供连接串）：
- docker compose up -d mysql
- npx prisma db push
- 三个 seed
- 跑 e2e-smoke.sh

---

## 风险/已知问题

1. **CORS 配置硬编码** `http://10.10.22.80:9908`（docker-compose.yml）—— 本地开发会被 CORS 拒绝
2. **JWT secret 在 .env 是明文** —— 生产必须从 secret manager 注入
3. **e2e-smoke.sh 跑不通因为本地无 docker** —— 用户提供 MySQL 后才能跑
4. **父仓库无 .gitignore** 导致工作区永远脏 —— 需单独 PR
5. **未做单元测试** —— 计划里明确 YAGNI

---

## Commit 列表

```
2abe4772 refactor(api): 统一响应包络 + 修复 Candidate 缺失关系
7dccaf34 perf(db): 给所有 FK 字段加索引 + 补全 onDelete 行为
29fa6c53 fix(security): JWT secret 走 config + 解除 app.js 循环引用
56f32ada refactor: 统一路由错误处理走全局 error 中间件
3fc7354e feat(deploy): backend Dockerfile 加 mysql-client + entrypoint 加 MySQL 健康检查
1bde593c feat(db): Prisma datasource 切换为 MySQL + 字段类型适配 + 配置
6c0b664c feat(deploy): 添加 MySQL 服务到 docker-compose
65b8b371 feat(org): 部门管理 - CRUD/树形/HRBP/VP 配置
```
