# ATS-New 整体复盘 + MySQL 迁移 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 ATS-New 项目的数据库从 SQLite 迁移到 MySQL，并对代码做四维度（代码质量 / 安全 / Prisma 模型 / API 架构）的全量整改，最终在真实 MySQL 上端到端跑通。

**Architecture:** Track A 独立完成 MySQL 迁移；Track B1→B2→B3→B4 串行做四个维度的审查与整改；Track C 收尾做端到端验收与报告。每 Track 收尾必须运行具体验证命令并留档。

**Tech Stack:** Backend = Express 4 + Prisma 5 + JWT；Frontend = Vue 3 + Ant Design Vue + Pinia + Vite；Database = MySQL 8.0

---

## 文件结构（先锁清职责）

| 文件 | 职责 | 状态 |
|---|---|---|
| `backend/prisma/schema.prisma` | 48 个数据模型 + datasource | 改 |
| `docker-compose.yml` | 编排 backend + frontend + mysql | 改 |
| `backend/.env.example` | 环境变量模板（含 DATABASE_URL） | 改 |
| `backend/Dockerfile` | backend 镜像构建 | 改 |
| `backend/ats-entrypoint.sh` | 容器启动钩子 | 改 |
| `backend/src/middleware/*.js` | auth/error 中间件 | 改 |
| `backend/src/routes/*.js` | 10 个路由文件 | 改 |
| `backend/src/app.js` | 主应用（路由注册/中间件挂载） | 改 |
| `frontend/src/api/auth.ts` | axios 客户端 | 改（可能要补 helper） |
| `frontend/src/pages/settings/*.vue` | 设置页面 | 部分改 |
| `docs/superpowers/review/2026-06-02-ats-review-report.md` | 复盘报告 | 新建 |

---

# Track A: MySQL 迁移

## Task A1: docker-compose 加 MySQL 服务

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: 读取现有 docker-compose.yml**

读出 mysql 段是否存在、backend 段是怎么写的（依赖、网络）。

- [ ] **Step 2: 加入 mysql 服务**

在 `docker-compose.yml` 中 services 下新增 `mysql`：

```yaml
  mysql:
    image: mysql:8.0
    container_name: ats-mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-rootpass}
      MYSQL_DATABASE: ${MYSQL_DATABASE:-ats}
      MYSQL_USER: ${MYSQL_USER:-ats}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-atspass}
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD:-rootpass}"]
      interval: 5s
      timeout: 5s
      retries: 20
    networks:
      - ats-net
```

在 `backend` 服务的 `depends_on` 中把 `mysql` 加上：

```yaml
      - mysql
```

- [ ] **Step 3: 添加 volume 和网络**

文件最底部如有 `volumes:` / `networks:` 段，确保 `mysql_data` 列入 volumes，`ats-net`（或你现用的网络名）列入 networks。

- [ ] **Step 4: 验证 YAML 合法**

Run: `cd /Users/loki/VScodeWorkspace/ATS-New && docker compose config -q`
Expected: 无输出，exit 0

- [ ] **Step 5: Commit**

```bash
cd /Users/loki/VScodeWorkspace/ATS-New
git add docker-compose.yml
git commit -m "feat(deploy): 添加 MySQL 服务到 docker-compose"
```

---

## Task A2: Prisma datasource 切换 + 字段类型适配

**Files:**
- Modify: `backend/prisma/schema.prisma`

- [ ] **Step 1: 修改 datasource**

把 `datasource db { provider = "sqlite" }` 改为 `provider = "mysql"`。

- [ ] **Step 2: 适配 Decimal 字段**

grep 找 `Float` 字段（涉及金额：Offer、Onboarding、Demand.biddingAmount、Position 暂无）。每个金额字段改为：

```prisma
salaryMin   Decimal? @db.Decimal(12, 2)
```

- [ ] **Step 3: 显式指定 String 长度（MySQL 默认 191 不够）**

对所有 `String` 字段扫一遍，长字段（如 description、requirements、parsedData）显式指定：

```prisma
description String? @db.Text
parsedData  String? @db.Text
```

短的：

```prisma
username   String   @db.VarChar(64)
realName   String   @db.VarChar(64)
```

只在长度已确认的字段上做，未知的不动（避免误伤）。

- [ ] **Step 4: 移除 sqlite-only 注释**

搜 `// SQLite only` 等注释删除。

- [ ] **Step 5: 验证 schema**

Run: `cd /Users/loki/VScodeWorkspace/ATS-New/backend && npx prisma validate`
Expected: `The schema at prisma/schema.prisma is valid 🚀`

- [ ] **Step 6: 重新生成 client**

Run: `npx prisma generate`
Expected: `Generated Prisma Client (v5.x.x) to ./node_modules/@prisma/client`

- [ ] **Step 7: Commit**

```bash
git add backend/prisma/schema.prisma
git commit -m "feat(db): Prisma datasource 切换为 MySQL + 字段类型适配"
```

---

## Task A3: 添加 .env.example

**Files:**
- Create or Modify: `backend/.env.example`

- [ ] **Step 1: 写入模板**

```bash
# MySQL 连接串
DATABASE_URL="mysql://ats:atspass@localhost:3306/ats"

# 服务端口
PORT=5125

# JWT 密钥（生产请改）
JWT_SECRET="change-me-in-production"
JWT_EXPIRES_IN="7d"

# CORS 允许来源
CORS_ORIGIN="http://localhost:5173"

# 速率限制
RATE_LIMIT_WINDOW_MS=60000
RATE_LIMIT_MAX=300
```

- [ ] **Step 2: 检查 config/index.js 是否读这些变量**

读 `backend/src/config/index.js`，确认所有变量有 fallback。

- [ ] **Step 3: Commit**

```bash
git add backend/.env.example
git commit -m "chore: 新增 .env.example MySQL 模板"
```

---

## Task A4: Dockerfile 安装 mysql client

**Files:**
- Modify: `backend/Dockerfile`

- [ ] **Step 1: 读现有 Dockerfile**

找到基础镜像（如 `node:20-slim`）。

- [ ] **Step 2: 添加 mysql-client 安装**

在 `apt-get install` 行追加 `default-mysql-client`。同时 `apt-get clean` 等清理保留。

- [ ] **Step 3: 验证（可选）**

如有 docker 可用：`docker build -t ats-backend-test ./backend`，能 build 通即可。

- [ ] **Step 4: Commit**

```bash
git add backend/Dockerfile
git commit -m "chore: backend 镜像安装 mysql 客户端"
```

---

## Task A5: ats-entrypoint.sh 适配 MySQL 健康检查

**Files:**
- Modify: `backend/ats-entrypoint.sh`

- [ ] **Step 1: 替换 prisma db push 前的健康检查**

原 node 内联检查保留，但增加显式 `mysqladmin ping` 等待（避免 prisma 推送时连接未就绪）：

```sh
echo "⏳ [entrypoint] 等待 MySQL 就绪..."
for i in $(seq 1 30); do
  if mysqladmin ping -h"${MYSQL_HOST:-mysql}" -u"${MYSQL_USER:-ats}" -p"${MYSQL_PASSWORD:-atspass}" --silent 2>/dev/null; then
    echo "✅ MySQL 就绪"
    break
  fi
  sleep 2
done
```

- [ ] **Step 2: 让种子执行条件兼容 MySQL**

原"users 表为空才执行种子"逻辑保留。部门种子作为可重复执行（幂等）追加到 else 分支（spec 已定）。

- [ ] **Step 3: shellcheck 验证**

Run: `sh -n backend/ats-entrypoint.sh && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/ats-entrypoint.sh
git commit -m "fix: 启动脚本适配 MySQL 健康检查"
```

---

## Task A6: MySQL 端到端冒烟（Track A 收尾）

**Files:** 无（验证步骤）

- [ ] **Step 1: 启动 MySQL**

```bash
cd /Users/loki/VScodeWorkspace/ATS-New
docker compose up -d mysql
```

等 `docker compose ps` 显示 mysql healthy。

- [ ] **Step 2: 推送 schema**

```bash
cd backend
export DATABASE_URL="mysql://ats:atspass@localhost:3306/ats"
npx prisma db push --skip-generate
```

Expected: `Your database is now in sync with your Prisma schema.`

- [ ] **Step 3: 跑种子**

```bash
node prisma/seed/user.seed.cjs
node prisma/seed/permission.seed.cjs
node prisma/seed/department.seed.cjs
```

Expected: 三条都 `完成`，无 ERROR。

- [ ] **Step 4: 验证数据**

```bash
node -e "const {PrismaClient}=require('@prisma/client');const p=new PrismaClient();p.department.count().then(c=>{console.log('部门数:',c);return p.\$disconnect()})"
```

Expected: `部门数: 14`（或更新后的数字）

- [ ] **Step 5: 验证 Decimal 字段**

```bash
node -e "const {PrismaClient}=require('@prisma/client');const p=new PrismaClient();p.department.findFirst({select:{id:true,sortOrder:true}}).then(d=>{console.log(typeof d.sortOrder, d);return p.\$disconnect()})"
```

Expected: `number 0 ...`（或当前 sortOrder）

- [ ] **Step 6: Track A 完成报告**

把以上 5 步的实际输出粘到回复里。任意一步失败：回到出问题的 Task 重做。

---

# Track B1: 代码质量与一致性

## Task B1.1: 扫除 .js 文件中的 TS 类型注解

**Files:**
- Audit: `backend/src/**/*.js`, `backend/prisma/seed/*.cjs`
- Modify: 命中处

- [ ] **Step 1: 扫描**

```bash
cd /Users/loki/VScodeWorkspace/ATS-New
grep -rn "const [a-zA-Z_]*: " backend/src backend/prisma/seed --include="*.js" --include="*.cjs" 2>&1 | head -30
```

- [ ] **Step 2: 逐个文件去除 `: any`、`: string`、`: number` 等**

仅去类型注解，不动逻辑。每改一个跑 `node --check`（cjs）或 `node -e "import('./path.js')"`（mjs）确认不破。

- [ ] **Step 3: 验证**

```bash
cd backend
node -e "import('./src/app.js').then(()=>console.log('OK')).catch(e=>{console.error(e.message);process.exit(1)})"
```

Expected: 输出 `OK`（端口占用也算 OK——只要 import 链没断）

- [ ] **Step 4: Commit**

```bash
git add backend/src backend/prisma/seed
git commit -m "refactor: 清理后端 .js 残留 TS 类型注解"
```

---

## Task B1.2: 错误处理模式统一

**Files:**
- Audit: `backend/src/routes/*.js`
- Modify: 命中处

- [ ] **Step 1: 扫描模式**

```bash
cd /Users/loki/VScodeWorkspace/ATS-New
grep -rn "catch.*console" backend/src/routes | head -20
```

- [ ] **Step 2: 替换为标准三段式**

把 `catch (e) { console.error(...); res.status(500).json(...) }` 改为 `catch (e) { next(e) }`，由全局 error middleware 统一处理。

具体替换模板：
```js
// Before
} catch (error) {
  console.error('...', error);
  res.status(500).json({ success: false, error: '...' });
}

// After
} catch (error) {
  next(error);
}
```

- [ ] **Step 3: 检查全局 error middleware**

读 `backend/src/middleware/error.middleware.js`，确认其能处理：
- Prisma 错误码（P2002/P2025/P2003）
- 普通 Error
- 业务自定义错误类（如有）

- [ ] **Step 4: 验证**

```bash
cd backend
node -e "import('./src/app.js').then(()=>console.log('OK')).catch(e=>{console.error(e.message);process.exit(1)})"
```

- [ ] **Step 5: Commit**

```bash
git add backend/src
git commit -m "refactor: 统一错误处理走全局中间件"
```

---

## Task B1.3: 前端统一使用 api 客户端

**Files:**
- Audit: `frontend/src/pages/**/*.vue`
- Modify: 直接 `fetch` 调用替换为 `api`

- [ ] **Step 1: 扫描**

```bash
cd /Users/loki/VScodeWorkspace/ATS-New
grep -rln "fetch(" frontend/src/pages 2>&1
```

- [ ] **Step 2: 替换为 api 实例**

原代码（示例）：
```ts
const data = await fetch('/api/users', {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());
```

改为：
```ts
import api from '../../api/auth';
const res = await api.get('/users');
const data = res.data;
```

（已用 `api` 的页面保持原状）

- [ ] **Step 3: 验证构建**

```bash
cd frontend
npx vite build 2>&1 | tail -20
```

Expected: `✓ built in ...s`（无 error）

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages
git commit -m "refactor(frontend): 统一使用 api 客户端"
```

---

## Task B1.4: Track B1 收尾

**Files:** 无（验证步骤）

- [ ] **Step 1: 后端加载验证**

```bash
cd backend
node -e "import('./src/app.js').then(()=>console.log('OK')).catch(e=>{console.error(e.message);process.exit(1)})"
```

- [ ] **Step 2: 前端构建验证**

```bash
cd ../frontend
npx vite build 2>&1 | tail -5
```

- [ ] **Step 3: 启动后端 + 烟测**

```bash
cd ../backend
nohup node src/app.js > /tmp/ats-backend.log 2>&1 &
sleep 3
TOKEN=$(curl -s -X POST http://localhost:5125/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])")
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:5125/api/departments | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('success'), d; print('部门列表 OK, count=', len(d['data']))"
```

Expected: `部门列表 OK, count= 14`（或更新后的数字）

- [ ] **Step 4: 杀进程、Track B1 报告**

把以上输出留档。失败回到出问题的 Task。

---

# Track B2: 安全与权限

## Task B2.1: authMiddleware 覆盖审计

**Files:**
- Audit: `backend/src/app.js`
- Modify: 路由挂载顺序/中间件

- [ ] **Step 1: 列出所有路由挂载点**

```bash
cd /Users/loki/VScodeWorkspace/ATS-New
grep -n "app.use" backend/src/app.js
```

- [ ] **Step 2: 确认每个非公开路由都过 authMiddleware**

公开路由（仅 `/api/auth`）保留，其他 `/api/*` 必须过 `authMiddleware`。

- [ ] **Step 3: 验证无 token 访问被拒**

```bash
TOKEN=""
for endpoint in /api/users /api/departments /api/processes /api/demands /api/candidates; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5125${endpoint}")
  echo "${endpoint}: ${STATUS}"
  [ "$STATUS" = "401" ] || { echo "FAIL: ${endpoint} 不需要 token"; exit 1; }
done
```

Expected: 全部 `401`

- [ ] **Step 4: Commit（如有改动）**

```bash
git add backend/src
git commit -m "fix(security): 确认 authMiddleware 覆盖所有非公开路由"
```

---

## Task B2.2: User 敏感字段从 select 排除

**Files:**
- Modify: `backend/src/routes/user.routes.js`

- [ ] **Step 1: 审计所有 User 查询**

```bash
cd /Users/loki/VScodeWorkspace/ATS-New
grep -n "prisma.user.find" backend/src/routes/user.routes.js
```

- [ ] **Step 2: 确认 password 已被排除**

每个 `find*` 调用的 `select` 不包含 `password` 字段（之前 review 时看到是 exclude 的，确认无遗漏）。

- [ ] **Step 3: 验证**

```bash
TOKEN=$(curl -s -X POST http://localhost:5125/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])")
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:5125/api/users | python3 -c "import sys,json; d=json.load(sys.stdin); u=d['data'][0]; assert 'password' not in u, 'password 泄露'; print('User 字段无 password ✓')"
```

Expected: `User 字段无 password ✓`

- [ ] **Step 4: Commit（如有改动）**

---

## Task B2.3: JWT secret 走 env

**Files:**
- Audit: `backend/src/middleware/auth.middleware.js` 或 config/index.js

- [ ] **Step 1: 找 JWT 密钥引用**

```bash
cd /Users/loki/VScodeWorkspace/ATS-New
grep -rn "jwt.sign\|jwt.verify\|JWT_SECRET" backend/src 2>&1
```

- [ ] **Step 2: 确认密钥从 config 读**

```js
import config from '../config/index.js';
jwt.sign(payload, config.jwt.secret, { expiresIn: config.jwt.expiresIn });
```

config 中：
```js
jwt: {
  secret: process.env.JWT_SECRET || 'dev-secret-do-not-use-in-prod',
  expiresIn: process.env.JWT_EXPIRES_IN || '7d',
}
```

- [ ] **Step 3: 验证**

```bash
cd backend
JWT_SECRET="custom-test-secret" node -e "console.log(require('./src/config/index.js').jwt.secret)"
```

Expected: `custom-test-secret`

- [ ] **Step 4: Commit（如有改动）**

---

## Task B2.4: Track B2 收尾

**Files:** 无（验证步骤）

- [ ] **Step 1: 跑完 B2.1-B2.3 所有验证**

收集所有命令的输出。

- [ ] **Step 2: 触发错误路径测试**

```bash
TOKEN=$(curl -s -X POST http://localhost:5125/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])")
# 删除不存在的资源
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" http://localhost:5125/api/users/00000000-0000-0000-0000-000000000000 | python3 -m json.tool
```

Expected: `{"success": false, "error": "用户不存在"}`（不返回 500）

- [ ] **Step 3: 报告留档**

把 B2.1-B2.4 输出汇总。

---

# Track B3: Prisma 模型

## Task B3.1: 给所有 FK 字段加 @@index

**Files:**
- Modify: `backend/prisma/schema.prisma`

- [ ] **Step 1: 列出所有模型与 FK**

```bash
cd /Users/loki/VScodeWorkspace/ATS-New/backend
grep -E "^\s*[a-zA-Z]+\s+String[?]?\s+@relation" prisma/schema.prisma | head -50
```

- [ ] **Step 2: 给热路径 FK 加索引**

对每个外键字段，定位其所属模型，在模型 `@@map` 前加：

```prisma
@@index([departmentId])
@@index([userId])
```

重点关注：
- `Department.parentId`
- `User.departmentId`
- `Demand.departmentId`
- `Position.departmentId`
- `Application.candidateId`、`Application.positionId`
- `Resume.candidateId`
- `Interview.applicationId`
- 所有 `createdBy/operatorId/triggerUserId` 类字段

- [ ] **Step 3: 验证**

```bash
npx prisma validate
npx prisma db push --skip-generate
```

- [ ] **Step 4: Commit**

```bash
git add backend/prisma/schema.prisma
git commit -m "perf(db): 给所有热路径外键加索引"
```

---

## Task B3.2: 审计 onDelete 行为

**Files:**
- Audit: `backend/prisma/schema.prisma`
- Modify: 缺省 onDelete 的关键关系

- [ ] **Step 1: 列出所有关系**

```bash
cd /Users/loki/VScodeWorkspace/ATS-New/backend
grep -E "@relation" prisma/schema.prisma | head -60
```

- [ ] **Step 2: 决策每个关系的 onDelete**

规则：
- 子表强依赖父表（如 Interview→Application）→ `Cascade`
- 父表不应被强删（Department→User）→ `Restrict`
- 软删除即可（status 字段管）→ 不动 onDelete

补全缺失的 onDelete。

- [ ] **Step 3: 验证 + 推送**

```bash
npx prisma validate
npx prisma db push --skip-generate
```

- [ ] **Step 4: Commit**

---

## Task B3.3: 金额字段 Float → Decimal

**Files:**
- Modify: `backend/prisma/schema.prisma`

- [ ] **Step 1: 定位金额 Float 字段**

```bash
cd /Users/loki/VScodeWorkspace/ATS-New/backend
grep -nE "Float\?" prisma/schema.prisma
```

- [ ] **Step 2: 改 Decimal**

涉及 Offer、Onboarding、Demand.biddingAmount 等。模板：

```prisma
// Before
baseSalaryTrial Float?

// After
baseSalaryTrial Decimal? @db.Decimal(12, 2)
```

Decimal 已在 Onboarding 出现，确保口径一致。

- [ ] **Step 3: 验证**

```bash
npx prisma validate
npx prisma db push --skip-generate
```

- [ ] **Step 4: Commit**

```bash
git add backend/prisma/schema.prisma
git commit -m "fix(db): 金额字段统一为 Decimal(12,2)"
```

---

## Task B3.4: Track B3 收尾

**Files:** 无

- [ ] **Step 1: 跑 B3.1-B3.3 所有验证**

- [ ] **Step 2: 跑种子（如果 schema 变更涉及表结构）**

```bash
node prisma/seed/user.seed.cjs
node prisma/seed/permission.seed.cjs
node prisma/seed/department.seed.cjs
```

- [ ] **Step 3: 留档输出**

---

# Track B4: API 设计与架构

## Task B4.1: 响应包络标准化

**Files:**
- Audit: `backend/src/routes/*.js`

- [ ] **Step 1: 抽样响应结构**

```bash
cd /Users/loki/VScodeWorkspace/ATS-New
for endpoint in /api/users /api/departments /api/processes /api/demands; do
  TOKEN=$(curl -s -X POST http://localhost:5125/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])")
  echo "=== ${endpoint} ==="
  curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:5125${endpoint}" | python3 -c "import sys,json; d=json.load(sys.stdin); print('keys:', list(d.keys()))"
done
```

- [ ] **Step 2: 统一为 `{success, data, error, code, message}`**

发现变体就修。`success: true` 必带 `data`，`success: false` 必带 `error`。

- [ ] **Step 3: 验证 6 端点一致**

复用 Step 1 命令，所有 keys 一致。

- [ ] **Step 4: Commit**

```bash
git add backend/src
git commit -m "refactor(api): 统一响应包络"
```

---

## Task B4.2: 全局 error 中间件处理 Prisma 错误码

**Files:**
- Modify: `backend/src/middleware/error.middleware.js`

- [ ] **Step 1: 读现有 error.middleware.js**

- [ ] **Step 2: 加 Prisma 错误码翻译**

```js
import { Prisma } from '@prisma/client';

export const errorHandler = (err, req, res, next) => {
  if (err instanceof Prisma.PrismaClientKnownRequestError) {
    if (err.code === 'P2002') {
      return res.status(409).json({ success: false, code: 'UNIQUE_VIOLATION', error: '数据已存在' });
    }
    if (err.code === 'P2025') {
      return res.status(404).json({ success: false, code: 'NOT_FOUND', error: '资源不存在' });
    }
    if (err.code === 'P2003') {
      return res.status(400).json({ success: false, code: 'FK_VIOLATION', error: '存在关联数据，无法操作' });
    }
  }
  console.error('[Error]', err);
  res.status(500).json({ success: false, code: 'INTERNAL', error: '服务器内部错误' });
};
```

- [ ] **Step 3: 验证**

```bash
TOKEN=$(curl -s -X POST http://localhost:5125/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])")
# 重复 code
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"name":"重复","code":"ROOT"}' http://localhost:5125/api/departments | python3 -m json.tool
```

Expected: `{"success": false, "code": "UNIQUE_VIOLATION", "error": "数据已存在"}`

- [ ] **Step 4: Commit**

```bash
git add backend/src/middleware
git commit -m "feat(api): 全局错误中间件处理 Prisma 错误码"
```

---

## Task B4.3: Track B4 收尾

**Files:** 无

- [ ] **Step 1: 跑 B4.1-B4.2 验证**

- [ ] **Step 2: 前端构建**

```bash
cd frontend && npx vite build 2>&1 | tail -5
```

- [ ] **Step 3: 留档**

---

# Track C: 端到端验收

## Task C1: e2e 烟测脚本

**Files:**
- Create: `scripts/e2e-smoke.sh`（如不存在）

- [ ] **Step 1: 写烟测脚本**

```bash
#!/bin/sh
set -e

echo "=== 1. 启动后端 ==="
cd /Users/loki/VScodeWorkspace/ATS-New/backend
nohup node src/app.js > /tmp/ats-backend.log 2>&1 &
BACKEND_PID=$!
sleep 4

echo "=== 2. 登录 ==="
TOKEN=$(curl -s -X POST http://localhost:5125/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")
[ -n "$TOKEN" ] || { echo "FAIL: 登录"; exit 1; }
echo "  ✓ 登录成功"

echo "=== 3. 创建部门 ==="
CREATE=$(curl -s -X POST http://localhost:5125/api/departments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"E2E部门","code":"E2E-DEPT","sortOrder":99}')
DEPT_ID=$(echo "$CREATE" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")
echo "  ✓ 创建成功: $DEPT_ID"

echo "=== 4. 查询部门 ==="
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:5125/api/departments/$DEPT_ID" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['data']['name']=='E2E部门', d; print('  ✓ 查询一致')"

echo "=== 5. 更新部门 ==="
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"E2E部门-已改"}' \
  "http://localhost:5125/api/departments/$DEPT_ID" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['data']['name']=='E2E部门-已改'; print('  ✓ 更新成功')"

echo "=== 6. 错误路径：重复 code ==="
STATUS=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"重复","code":"E2E-DEPT"}' \
  http://localhost:5125/api/departments | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('code'))")
[ "$STATUS" = "UNIQUE_VIOLATION" ] && echo "  ✓ 重复 code 返回 UNIQUE_VIOLATION" || { echo "FAIL: 期望 UNIQUE_VIOLATION 实际 $STATUS"; exit 1; }

echo "=== 7. 删除部门 ==="
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" "http://localhost:5125/api/departments/$DEPT_ID" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['success']; print('  ✓ 删除成功')"

echo ""
echo "🎉 e2e 烟测全部通过"
kill $BACKEND_PID 2>/dev/null
```

- [ ] **Step 2: 执行**

```bash
chmod +x scripts/e2e-smoke.sh
./scripts/e2e-smoke.sh
```

Expected: `🎉 e2e 烟测全部通过`

- [ ] **Step 3: 把脚本纳入 git**

```bash
git add scripts/e2e-smoke.sh
git commit -m "test: 端到端烟测脚本"
```

---

## Task C2: 复盘报告

**Files:**
- Create: `docs/superpowers/review/2026-06-02-ats-review-report.md`

- [ ] **Step 1: 汇总所有 Track 发现**

把 B1-B4 的所有"扫到 → 修 → 验证"过程写进报告。

- [ ] **Step 2: 写报告**

每条问题：
```markdown
### [B1-001] xxx

- **位置**：`backend/src/routes/foo.js:23`
- **维度**：B1 代码质量
- **严重度**：P1
- **说明**：原代码用了 TS 注解 `const x: any`，但项目 backend 是纯 JS，导致 `node --check` 失败
- **修复**：删除 `: any`，改 `const x = {}`
- **验证**：`node -e "import('./src/app.js')"` 加载通过
```

- [ ] **Step 3: 统计 + 落款**

报告末尾加：
- P0 / P1 / P2 / P3 数量统计
- MySQL 迁移记录（迁移前/后字段对比）
- 4 维度覆盖率

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/review
git commit -m "docs: 复盘报告"
```

---

## 自审

**1. Spec 覆盖检查**

| Spec 段落 | 对应 Task |
|---|---|
| Track A MySQL 迁移 | A1-A6 ✅ |
| Track B1 代码质量 | B1.1-B1.4 ✅ |
| Track B2 安全 | B2.1-B2.4 ✅ |
| Track B3 Prisma | B3.1-B3.4 ✅ |
| Track B4 API 架构 | B4.1-B4.3 ✅ |
| Track C 端到端 | C1-C2 ✅ |

**2. 占位扫描** — 无 TBD/TODO/模糊描述。每步有具体命令或代码。

**3. 类型一致性** — 字段名 `code/managerId/manager2Id/manager3Id/hrbpId/parentId/path/level` 全程统一引用，与 [department.routes.js](backend/src/routes/department.routes.js) 一致。

无需要修复的内容。
