# SETUP — 详细安装步骤

> 5 分钟跑起来。本文假定 macOS + homebrew。其他系统见 [附录](#附录其他系统)。
>
> **最后更新**: 2026-06-06 — 新增"快速启动"段（5 步）和 22 通知模板 seed

## 🚀 快速启动（5 步）

```bash
# 1. 启动 MySQL 9（homebrew）
brew services start mysql
mysql -u root -p'35010800' -e "CREATE DATABASE IF NOT EXISTS ats;"

# 2. 后端
cd backend
npm install
./node_modules/.bin/prisma db push                            # 推 schema 到 DB
node prisma/seed.notification-templates.js                   # 22 通知模板 seed
node --env-file=.env src/app.js                              # 启动 (端口 5125)

# 3. 前端（另一个 terminal）
cd frontend
npm install
npm run dev                                                  # 启动 vite (端口 5212)

# 4. 浏览器打开
open http://localhost:5212/

# 5. 登录
# 用户名: admin
# 密码:   admin123
```

如果一切顺利，应该看到：登录页 → 输入 admin/admin123 → 进入 Dashboard 看到 8 个业务菜单。

## ✅ 启动验证

```bash
# 后端健康
curl http://localhost:5125/api/health
# {"status":"ok","timestamp":"...","service":"ATS Backend"}

# 前端代理是否工作（前端 5212 → 后端 5125）
curl http://localhost:5212/api/health
# 应该返回同样的 JSON

# 跑测试
cd backend
NODE_OPTIONS=--experimental-vm-modules ./node_modules/.bin/jest --runInBand
# 期望: 13 passed, 13 total / Tests: 214 passed
```

---

## 📦 服务器部署（生产环境）

部署到新服务器时，数据库结构 + 种子数据 **必须** 用下面这套**固定流程**，避免 schema/seed 不一致。

### 部署脚本（推荐）

```bash
# 一键部署（含备份、迁移、种子、验证）
cd backend
bash scripts/deploy.sh

# 跳过备份（开发环境）
bash scripts/deploy.sh --skip-backup

# 跳过 seed（生产已有数据）
bash scripts/deploy.sh --skip-seed

# 不询问直接执行
bash scripts/deploy.sh --force

# 出问题回滚到最后备份
bash scripts/deploy.sh --rollback
```

### 流程（5 步）

1. **备份**：mysqldump 当前 DB → `backups/ats_backup_<时间戳>.sql`（保留最近 10 份）
2. **环境验证**：检查 `node_modules`、`prisma generate`
3. **迁移**：`prisma migrate deploy`（应用所有未执行的 migrations，幂等）
4. **种子**：按顺序跑 `user → department → permission → recruitment-process → notification-templates → referral`（自动检测存在的脚本）
5. **验证**：表数量 ≥ 50、关键表存在、关键数据行数

### 为什么不用 `prisma db push`？

| | `prisma db push` | `prisma migrate deploy` |
|---|---|---|
| 用途 | **开发**（快速同步 schema）| **生产**（可控 migration）|
| 记录 | ❌ 不留历史 | ✅ 每次都有 migration 文件 |
| 回滚 | ❌ 难 | ✅ `migrate resolve --rolled-back` |
| 团队 | ❌ 容易冲突 | ✅ 文件 review 友好 |
| 部署 | ❌ 风险高 | ✅ 标准 Prisma 部署流程 |

**生产环境永远用 `migrate deploy`**。

### 现有 migrations

```
prisma/migrations/
├── 20260604062449_add_referral_phase1/    # Referral 模块
└── 20260607000000_baseline_54_tables/    # 54 张表 baseline
```

### 添加新 migration（开发流程）

```bash
# 1. 改 schema.prisma
vim prisma/schema.prisma

# 2. 生成 migration 文件（dev 自动 + 文件名）
./node_modules/.bin/prisma migrate dev --name add_xxx_feature

# 3. 提交到 git
git add prisma/migrations/

# 4. 部署到生产（CI 跑 test-migrations job 验证）
# 部署脚本 deploy.sh 自动应用新 migration
```

### CI 自动验证（test-migrations job）

`.github/workflows/ci.yml` 加了 `test-migrations` job：
- 启动干净的 MySQL
- 跑 `prisma migrate deploy`
- 验证表数量 ≥ 50
- 再跑一次（验证幂等性）
- ✅ 失败则 PR 不能合并

### 备份位置与回滚

- **备份目录**：`backend/backups/ats_backup_*.sql`（默认保留最近 10 份，可通过 `KEEP_BACKUPS` 环境变量调整）
- **回滚**：`bash scripts/deploy.sh --rollback`（恢复到最新一份备份）
- **生产回滚**建议流程：
  1. 停服 → `pm2 stop ats-backend`
  2. 回滚 → `bash scripts/deploy.sh --rollback`
  3. 启服 → `pm2 start ats-backend`

### 完整部署示例

```bash
# 1. SSH 到服务器
ssh user@ats-prod
cd /opt/ats/backend

# 2. 拉新代码
git pull origin main

# 3. 部署（自动备份 → 迁移 → 种子 → 验证）
bash scripts/deploy.sh

# 4. 重启服务
pm2 restart ats-backend
# 或
pkill -f "node.*src/app.js" && nohup node --env-file=.env src/app.js > /tmp/ats-backend.log 2>&1 &

# 5. 验证
curl http://localhost:5125/api/health
# 期望: {"status":"ok",...}
```

### 紧急情况

- **migration 失败**：`deploy.sh` 失败不会启动服务，需手动 `bash scripts/deploy.sh --rollback` 恢复
- **种子失败**：部分种子失败不会阻塞服务（用户数据可在管理后台补）
- **表数量不对**：`< 50` 表说明 migration 没应用完，检查 `prisma migrate status`
- **完整重置**（危险！清空所有数据）：`npm run db:reset`（会跑 prisma migrate reset --force + 全部 seed）



## 0. 前置依赖

| 工具 | 版本要求 | 检查命令 |
|---|---|---|
| Node.js | >= 18（推荐 20 LTS） | `node --version` |
| npm | >= 9 | `npm --version` |
| MySQL | >= 8.0 | `mysql --version` |
| homebrew | 最新 | `brew --version`（仅 macOS） |

## 1. 启动 MySQL

### macOS (homebrew)

```bash
brew install mysql
brew services start mysql
# 验证
mysql -uroot -p<你安装时设的密码> -e "SELECT VERSION();"
```

### 如果忘记 root 密码

```bash
# 停服务
brew services stop mysql

# 用 skip-grant-tables 启动（会绕过密码校验）
mysqld_safe --skip-grant-tables --skip-networking &

# 重置密码
mysql -uroot
> FLUSH PRIVILEGES;
> ALTER USER 'root'@'localhost' IDENTIFIED BY '<新密码>';
> \q

# 重启服务
brew services restart mysql
```

## 2. 建库建用户

```sql
CREATE DATABASE IF NOT EXISTS ats CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'ats'@'127.0.0.1' IDENTIFIED BY 'AtsPass2024!';
CREATE USER IF NOT EXISTS 'ats'@'localhost' IDENTIFIED BY 'AtsPass2024!';
GRANT ALL PRIVILEGES ON ats.* TO 'ats'@'127.0.0.1';
GRANT ALL PRIVILEGES ON ats.* TO 'ats'@'localhost';
FLUSH PRIVILEGES;
```

> ⚠️ MySQL 9 默认密码策略要求大小写+数字+特殊字符，所以这里用强密码 `AtsPass2024!`。改弱密码会被 `ERROR 1819` 拦。

## 3. 后端启动

```bash
cd backend

# 3.1 装依赖
npm install

# 3.2 复制环境变量模板
cp .env.example .env

# 3.3 按需修改 .env（数据库密码、JWT_SECRET 等）
# 默认配置:
#   DATABASE_URL=mysql://ats:AtsPass2024!@127.0.0.1:3306/ats
#   PORT=5125
#   JWT_SECRET=change-me-in-production   ← 生产前必须改

# 3.4 生成 Prisma client
./node_modules/.bin/prisma generate

# 3.5 推送 schema 到数据库（54 张表）
./node_modules/.bin/prisma db push

# 3.6 灌种子数据（4 个 seed：用户/部门/权限/内推）
npm run db:seed
# 或拆开跑：
#   node prisma/seed/user.seed.cjs
#   node prisma/seed/department.seed.cjs
#   node prisma/seed/permission.seed.cjs
#   node prisma/seed.referral.js

# 3.7 启动（必须显式加载 .env）
node --env-file=.env src/app.js
# 开发模式带热重载：
node --env-file=.env ./node_modules/.bin/nodemon src/app.js
```

启动成功标志：

```
[referral-scheduler] started with 3 cron tasks
🚀 ATS招聘管理系统 已启动
📡 后端服务: http://localhost:5125
📚 API文档: http://localhost:5125/api/health
```

## 4. 前端启动

```bash
cd frontend

# 4.1 装依赖
npm install

# 4.2 直接启动
./node_modules/.bin/vite
# 第一次启动如果 ant-design-vue 报错，详见 TROUBLESHOOTING.md

# 等价：npm run dev
```

启动成功标志：

```
VITE v5.4.21 ready in 209 ms
➜ Local: http://localhost:5212/
```

## 5. 验证

打开浏览器：

- 访问 http://localhost:5212
- 登录页输入：`admin` / `admin123`
- 看到 Dashboard 即表示成功

## 6. 端口冲突

| 服务 | 默认端口 | 修改方式 |
|---|---|---|
| 后端 | 5125 | 改 `backend/.env` 的 `PORT` |
| 前端 | 5212 | 改 `frontend/src/config/index.ts` 的 `frontend.port` |
| MySQL | 3306 | 改 `my.cnf` 或 homebrew 配置 |

如果改了后端端口，前端要同步改 `frontend/src/config/index.ts` 的 `backend.url`。

## 7. 常用 npm 脚本

### 后端

```bash
npm run dev                # nodemon 热重载
npm start                  # 生产启动
npm test                   # 跑 jest 测试
npm run db:seed            # 一键灌全部 seed
npm run db:generate        # 重新生成 prisma client
```

### 前端

```bash
npm run dev                # vite dev server
npm run build              # 生产构建（含 vue-tsc 类型检查）
npm run preview            # 预览生产构建
npm run lint               # ESLint
npm run e2e                # Playwright e2e (需先 npm run e2e:install)
npm run e2e:ui             # Playwright 调试 UI
```

## 8. 跑 e2e 测试 (Playwright, 2026-06-08 新增)

```bash
cd frontend
npm install                           # 装 @playwright/test
npx playwright install --with-deps chromium  # 一次性下载浏览器 (~80MB)
npm run e2e                           # 跑全部 e2e (6 spec: login / settings-layout / candidate-list / demand-flow / offer-flow / settings-menu)
npm run e2e:ui                        # 调试模式 (可视化 UI)
```

**前置条件**: 后端需先跑 (`cd backend && node --env-file=.env src/app.js &`)

**CI 自动跑**: `.github/workflows/ci.yml` 的 `e2e` job 依赖 `test-backend` + `test-frontend` 通过后自动跑。

## 9. 类型检查 (vue-tsc 2.x, 2026-06-08 升级)

```bash
cd frontend
npx vue-tsc --noEmit
```

**升级背景**: 旧 vue-tsc 1.8.0 + Node 24 抛 `Search string not found: "supportedTSExtensions"`, 已升到 2.2.12 修复。
当前 `tsconfig.json` 设 `"ignoreDeprecations": "5.0"` (适配 TS 5.3), 并关 `noUnusedLocals/noUnusedParameters` (旧 .vue 大量未用变量)。

**已知遗留**: 6 个旧 .vue 文件 (InvitationCenter/BackgroundCheckPanel/AddReferralModal/ReferralCenter/ProcessStageEditor 等) 有真实类型错, 暂用 `as any` 宽松策略, 后续可逐个修。

## 附录：其他系统

### Linux (Ubuntu)

```bash
sudo apt update
sudo apt install mysql-server nodejs npm
sudo systemctl start mysql
# 建库建用户同上
```

### Windows

不推荐——MySQL + Node.js 在 Windows 上坑比较多。建议用 WSL2 跑 Ubuntu。

### Docker

参考 `docker-compose.yml`：

```bash
docker-compose up -d
```

会自动启动 MySQL + 后端 + nginx + 前端。

## 附录：常见安装错误

| 错误 | 原因 | 解法 |
|---|---|---|
| `Prisma schema validation - P1012` 找不到 DATABASE_URL | 没创建 .env 或没显式加载 | `node --env-file=.env ...` |
| `npx prisma` 报 Prisma 7 语法错 | 用错了全局 npx | 改用 `./node_modules/.bin/prisma` |
| `Cannot find module ant-design-vue` | 第一次 install 没装上 | `cd frontend && npm install ant-design-vue@^4.2.6` |
| `MySQL ERROR 1819 password policy` | 弱密码被拦 | 改用强密码（含大小写+数字+特殊字符） |
| `Error: listen EADDRINUSE :::5125` | 端口被占 | `lsof -ti:5125 \| xargs kill` |
| `vue-tsc 报错 "Search string not found"` | vue-tsc 1.x 不兼容 Node 24 | `npm i -D vue-tsc@2` 或跳过类型检查用 vite 启动 |

更多排查见 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)。
