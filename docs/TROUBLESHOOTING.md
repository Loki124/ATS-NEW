# TROUBLESHOOTING — 常见问题排查

> 按问题分类，每个问题给"症状 → 原因 → 解法"三段式。

## 一、登录问题

### Q: 登录页点登录后没反应 / 一直转圈

**症状**：点击登录按钮后 loading 状态卡住，console 没报错。

**可能原因 & 解法**：

1. **后端没起来** → 终端跑 `curl http://localhost:5125/api/health` 看返回
2. **Vite proxy 没生效** → 浏览器 DevTools Network 看 `/api/auth/login` 是不是 200
3. **环境变量没加载** → 后端启动日志应该看到 `🚀 ATS招聘管理系统 已启动`，如果看到 `PrismaClientInitializationError` 是 .env 没加载

### Q: 登录后立刻被踢回登录页

**症状**：登录成功但 dashboard 一闪而过，又跳回 `/login`。

**历史 bug**（已修复，2026-06）：
- 前端 axios 拦截器在收到 401 时调用 `/auth/refresh`，但**后端没这个端点**
- 任何 401 → 调 refresh → 404 → 自动 logout + 跳转

**验证修复**：
- `frontend/src/api/auth.ts` 应该有 `handleAuthFailure` 函数
- 不再调 `/auth/refresh`

**如果还出现**：
- 浏览器硬刷新 `Ctrl+Shift+R`
- 清 localStorage：`localStorage.clear()` 然后重登

### Q: 提示"用户名或密码错误"但确认没输错

**检查**：
```bash
# 直接 curl 测试
curl -X POST http://localhost:5125/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

| 返回 | 含义 |
|---|---|
| 200 + token | 凭据对，问题在浏览器（Vite proxy / 缓存） |
| 401 用户名密码错 | 真的密码错，或数据库里没 admin |
| 500 | 后端报错，看后端日志 |

**重置 admin 密码**：
```bash
cd backend
node --env-file=.env -e "
import('@prisma/client').then(async ({ PrismaClient }) => {
  const bcrypt = (await import('bcryptjs')).default;
  const p = new PrismaClient();
  const hash = await bcrypt.hash('admin123', 10);
  await p.user.update({ where: { username: 'admin' }, data: { password: hash } });
  console.log('admin 密码已重置为 admin123');
  await p.\$disconnect();
});
"
```

## 二、数据库连接问题

### Q: `PrismaClientInitializationError: Environment variable not found: DATABASE_URL`

**原因**：`.env` 没创建 或 没被加载。

**解法**：
```bash
cd backend
ls .env   # 确认文件存在
cat .env  # 确认有 DATABASE_URL=mysql://...
# 启动时显式加载：
node --env-file=.env src/app.js
```

### Q: `Error: P1001 Can't reach database server`

**检查 MySQL 状态**：
```bash
lsof -i :3306                 # 看进程在不在
mysql -uroot -p<password> -e "SELECT 1"   # 测试连接
```

如果 MySQL 没起：`brew services start mysql`

### Q: `Access denied for user 'ats'@'localhost'`

**原因**：用了 `.env.example` 里的默认 `atspass` 密码，但 MySQL 9 强密码策略不让用。

**解法**：改用强密码 `AtsPass2024!`（含大小写+数字+特殊字符），重建用户：
```sql
DROP USER 'ats'@'localhost';
DROP USER 'ats'@'127.0.0.1';
CREATE USER 'ats'@'localhost' IDENTIFIED BY 'AtsPass2024!';
CREATE USER 'ats'@'127.0.0.1' IDENTIFIED BY 'AtsPass2024!';
GRANT ALL PRIVILEGES ON ats.* TO 'ats'@'localhost';
GRANT ALL PRIVILEGES ON ats.* TO 'ats'@'127.0.0.1';
FLUSH PRIVILEGES;
```

### Q: `Unknown argument 'status'` 或 `Field does not exist`

**原因**：代码用了 schema 里不存在的字段。

**典型 case**（2026-06 已修）：
```js
// ❌ 错
prisma.onboarding.findMany({ where: { status: 'ONBOARDED' } })
// Onboarding 表只有 onboardingStatus / approvalStatus / syncStatus

// ✅ 对
prisma.onboarding.findMany({ where: { onboardingStatus: 'ONBOARDED' } })
```

**怎么定位**：
1. 看后端日志完整堆栈，找到 `prisma.xxx.findMany({...})` 的代码位置
2. 去 `prisma/schema.prisma` 确认字段名

## 三、Prisma 相关

### Q: `npx prisma` 报 Prisma 7 语法错（`url no longer supported`）

**原因**：全局有 Prisma 7.8.0 在污染 `npx prisma`，但项目锁的是 5.22.0。

**解法**：用项目本地的：
```bash
cd backend
./node_modules/.bin/prisma migrate dev
# 或
npx -p prisma@5.22.0 prisma migrate dev
```

### Q: `vue-tsc 1.x 报 Search string not found`

**原因**：vue-tsc 1.x 不兼容 Node 24。

**解法**：
```bash
cd frontend
npm i -D vue-tsc@2
# 或跳过类型检查用 vite 直接跑
./node_modules/.bin/vite
```

## 四、前端构建/启动问题

### Q: `Cannot find module 'ant-design-vue'` / `Failed to resolve import "ant-design-vue"`

**解法**：
```bash
cd frontend
npm install ant-design-vue@^4.2.6 @ant-design/icons-vue@^7.0.1
# 清 Vite 缓存
rm -rf node_modules/.vite
./node_modules/.bin/vite
```

### Q: Vite proxy 不生效，CORS 错误

**症状**：浏览器报 `Access to XMLHttpRequest ... has been blocked by CORS policy`。

**解法**：
- 确认请求走 `/api/*` 前缀（不是直连 `http://localhost:5125/api/*`）
- 确认 `vite.config.ts` 的 proxy 配置正确：
  ```ts
  proxy: { [config.api.baseUrl]: { target: config.backend.url, changeOrigin: true } }
  ```
- 改完 vite.config.ts 需要**重启 vite**

### Q: 改完前端代码没生效

**解法**：
1. 软刷新 `F5` 试一下
2. 硬刷新 `Ctrl+Shift+R`
3. 清 Vite 缓存：`rm -rf frontend/node_modules/.vite && npm run dev`

## 五、后端启动问题

### Q: `Error: listen EADDRINUSE :::5125`

**解法**：
```bash
lsof -ti:5125 | xargs kill
# 或
kill $(lsof -ti :5125)
```

### Q: 后端启动后 scheduler 报 `Unknown argument 'status'`

**已修复**（2026-06）：把 `referral.scheduler.js` 的 `where: { status: 'ONBOARDED' }` 改成 `where: { onboardingStatus: 'ONBOARDED' }`。

如果还出现，确认 `backend/src/referral/scheduler/referral.scheduler.js:25` 的代码。

### Q: 报 `prisma.xxx.findUnique` 报 `id: undefined`

**典型场景**（2026-06 已修）：
- `/auth/me` 和 `/change-password` 路由**没挂 authMiddleware**，导致 `req.userId` 是 `undefined`
- 修复：在 `auth.routes.js` 顶部 `import { authMiddleware }`，路由前加 `authMiddleware,`

## 六、Mac M 系列芯片特殊问题

### Q: 启动 Node 进程报 `bad CPU type in executable`

**原因**：某些 npm 包的 prebuilt binary 是 x86_64，M 系列是 arm64。

**解法**：
```bash
# 删除 x86_64 node_modules 重装
rm -rf node_modules
npm install --target_arch=arm64
```

## 七、性能问题

### Q: 后端启动慢（>10s）

**可能原因**：
- Prisma 第一次 query 要 JIT
- 多个 cron 任务启动

**正常范围**：1-3 秒。如果 >10s 看后端日志具体卡在哪。

## 八、如何提交 bug 报告

附上以下信息能极大加速排查：

```bash
# 1. 环境信息
node --version
npm --version
mysql --version
uname -a

# 2. 服务状态
lsof -iTCP:5125 -iTCP:5212 -sTCP:LISTEN

# 3. 后端最近 30 行日志
tail -30 /tmp/backend.log  # 或对应日志文件

# 4. 触发 bug 的 API 调用（带 -v 看完整请求/响应）
curl -v http://localhost:5125/api/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```
