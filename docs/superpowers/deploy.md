# 部署指南

> **当前数据库已切换到 `ats_pro`**（2026-06-02 更新）
> 历史曾用 `ats_new`，已弃用。

## 服务器信息

| 项 | 值 |
|---|---|
| MySQL 地址 | `10.10.22.80:3306` |
| MySQL 版本 | 8.4.9 |
| 数据库 | `ats_pro` |
| 用户 | `ATS_pro`（**真实凭据在服务器本地 .env，不入 git**） |
| 字符集 | utf8mb4 |
| ATS 入口 | nginx 9908 → backend 5125 |

## 本地 .env 模板（生产环境）

```bash
# Database - 真凭据放服务器 .env，本文件仅占位
DATABASE_URL="mysql://ATS_pro:REAL_PASSWORD@10.10.22.80:3306/ats_pro"

# JWT
JWT_SECRET="生产环境必须改"
JWT_EXPIRES_IN="7d"

# Server
PORT=5125
NODE_ENV=production

# CORS
CORS_ORIGIN="http://10.10.22.80:9908"

# MySQL connection (for entrypoint healthcheck)
MYSQL_HOST=10.10.22.80
MYSQL_USER=ATS_pro
MYSQL_PASSWORD="REAL_PASSWORD"
MYSQL_DATABASE=ats_pro

# Rate Limit
RATE_LIMIT_WINDOW_MS=60000
RATE_LIMIT_MAX=300
```

⚠️ **生产部署时**：
- `JWT_SECRET` 改为长随机串
- `MYSQL_*` 凭据改用 secret manager 注入环境变量，不要写进 .env 文件本身
- `CORS_ORIGIN` 设为实际前端域名

## 部署步骤（docker-compose）

### 方式 A：本地起 MySQL 容器（开发/演示）

```bash
cd /path/to/ATS-New
docker compose up -d --build
# backend 启动时会自动：
# 1. 等待 mysql 容器 healthy
# 2. 跑 prisma db push
# 3. 首次启动跑 3 个 seed
# 4. 启动 node 应用
```

### 方式 B：用外部 MySQL（本服务器场景）

```bash
# 1. 把 .env 改成服务器 MySQL 连接（见上）
cd backend
DATABASE_URL="mysql://ATS_new:rFrjmxtfFCb575cB@10.10.22.80:3306/ats_new" \
  npx prisma db push --skip-generate --accept-data-loss

# 2. 跑种子（首次部署）
DATABASE_URL="..." node prisma/seed/user.seed.cjs
DATABASE_URL="..." node prisma/seed/permission.seed.cjs
DATABASE_URL="..." node prisma/seed/department.seed.cjs

# 3. 启动 backend
node src/app.js
# 或后台：nohup node src/app.js > /var/log/ats-backend.log 2>&1 &

# 4. 部署前端 dist 到 nginx
cd ../frontend
npm run build
# 同步 dist/ 到 nginx html 目录
```

## 端到端验证

```bash
cd /path/to/ATS-New
bash scripts/e2e-smoke.sh
```

预期：10 步全过，最后输出 `🎉 端到端烟测全部通过`

## 关键变更（从这次合并起）

| 旧 | 新 |
|---|---|
| SQLite (file:./dev.db) | MySQL (10.10.22.80:3306) |
| 金额 Float | Decimal(12, 2) |
| 5 个索引 | 98 个索引 |
| 错误响应混用 error/message | 统一 `{success: false, message: ...}` |
| 53 处 res.status(500) | 全部 next(error) → 全局中间件 |
| Candidate 关系缺失 | 已补 |
| 无 MySQL 服务 | docker-compose 加 mysql:8.0 + 等待脚本 |

## 已知遗留

- 前端 20+ 处直接 fetch 调用（待 P3 整改）
- 父仓库 .gitignore 缺失（待 P3 整改）
- `/uploads` 静态目录无认证（待 P3 整改）
- 短字符串字段未显式 @db.VarChar（待 P3 整改）
- status 字段未改 Prisma enum（待 P3 整改）
- 前端 store 未按域拆分（待 P3 整改）

## 回滚

```bash
cd /Users/loki/VScodeWorkspace
git checkout main~1  # 回滚到合并前
# 或
git revert 7f47c17f  # 反向提交
```
