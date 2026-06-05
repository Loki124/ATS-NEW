# SETUP — 详细安装步骤

> 5 分钟跑起来。本文假定 macOS + homebrew。其他系统见 [附录](#附录其他系统)。

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
```

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
