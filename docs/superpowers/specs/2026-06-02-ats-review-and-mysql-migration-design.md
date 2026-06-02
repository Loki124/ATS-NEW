# ATS-New 整体复盘 + MySQL 迁移 设计稿

**日期**: 2026-06-02
**状态**: 已通过段 1-5 评审，等待用户审阅 spec 后进入 writing-plans

## 背景

`ATS-New` 是一套 Express + Prisma + Vue 3 的招聘管理系统。当前规模：

- ~15K LOC
- 48 个 Prisma 模型
- 10 个后端路由文件
- 29 个 Vue 页面
- 数据库当前为 SQLite（`prisma/dev.db`）
- 服务器运维侧已统一为 MySQL

用户需求：

1. 对项目做**整体复盘**，覆盖四个维度：
   - 代码质量与一致性
   - 安全与权限
   - 数据库与 Prisma 模型
   - API 设计与架构
2. **报告 + 全量整改**（不是只读审查）
3. **统一切换到 MySQL**（连接串稍后提供）

## 目标

- 交付一份复盘报告（Markdown，含每条问题的位置、严重度、修复说明）
- MySQL 迁移在用户提供的真实 MySQL 实例上能跑通
- 四个维度的整改后，代码达到可继续迭代的状态
- 所有变更可验证：每个 Track 收尾都有具体的命令 + 输出证据

## 非目标（YAGNI）

- 不引入新的框架 / ORM / 状态管理库
- 不重写架构
- 不做性能压测 / 容量规划
- 不补单元测试覆盖率（除非某 B 维度的整改必然需要）
- 不做 UI 改版

## 方案选择

**方案 A：串行递进（已采纳）**

```
Track A  ━━━━━━━━━━━━━━━━━━━━━━━━━━━ MySQL 迁移（独立，先做）
Track B1 ━━▶ B2 ━━▶ B3 ━━▶ B4 ━━▶ 4 维度串行审查+整改
Track C  ━━━━━━━━━━━━━━━━━━━━━━━━━━━ 端到端验收（连真实 MySQL）
```

理由：B 四个维度高度相关（API 设计影响代码质量、安全漏洞常藏在代码质量里），串行看能看清交叉；本地代码改动居多，并行边际收益不大。

## Track 详细定义

### Track A：MySQL 迁移

**改动文件：**

- `backend/prisma/schema.prisma` — `datasource db.provider` 由 `sqlite` 改为 `mysql`
- `backend/prisma/schema.prisma` — 适配 MySQL 字段类型（`Float → Decimal` 用于金额、`String` 长度限制、必要时 `Json`）
- `backend/.env.example` — 新增 `DATABASE_URL` 模板（`mysql://user:pass@host:3306/dbname`）
- `docker-compose.yml` — 新增 `mysql` 服务（image: mysql:8.0），挂载数据卷
- `backend/Dockerfile` — 安装 `default-mysql-client`（健康检查用）
- `backend/ats-entrypoint.sh` — 健康检查改用 `mysqladmin ping` 而非 node 内联
- `backend/prisma/seed/*.cjs` — 适配 MySQL 兼容语法（如有）

**验证：**

```bash
# 1. 静态校验
npx prisma validate
npx prisma generate

# 2. 推送 schema
npx prisma db push

# 3. 跑种子
node prisma/seed/user.seed.cjs
node prisma/seed/permission.seed.cjs
node prisma/seed/department.seed.cjs

# 4. 烟测
node -e "const {PrismaClient}=require('@prisma/client');const p=new PrismaClient();p.department.findMany({take:3}).then(d=>{console.log(JSON.stringify(d,null,2));return p.\$disconnect()})"
```

### Track B1：代码质量与一致性

**关注点：**

- `.js` 文件中残留的 TS 类型注解（已在 department.routes.js 修过一处，需扫全量）
- 错误处理模式：`try/catch/next(error)` 是否一致
- 命名一致性：路由方法、模型字段
- 前端 API 调用：使用 `frontend/src/api/auth.ts` 的 `api` 实例 vs `fetch` 混用
- 表单/Modal 重复代码
- 注释密度、import 顺序

**验证：**

```bash
# 后端加载
cd backend && node -e "import('./src/app.js').then(()=>console.log('OK')).catch(e=>{console.error(e);process.exit(1)})"

# 前端构建
cd frontend && npx vite build
```

### Track B2：安全与权限

**关注点：**

- `authMiddleware` 是否在所有非公开路由上挂载
- 输入校验：写路由（POST/PUT/DELETE）是否使用 `express-validator` 或至少做字段存在性检查
- 敏感字段：`User.password` 是否在 `select` 中被排除
- JWT 密钥：是否走 env（不能 hardcode）
- CORS 配置：`origin` 是否限定
- 注入风险：是否有任何字符串拼接 SQL（Prisma 本身防注入，但要审计）
- XSS：前端是否对渲染内容做转义（v-html 使用情况）

**验证：**

```bash
# 无 token 访问
curl -i http://localhost:5125/api/users
# 期望: 401

# 越权访问
TOKEN=$(curl -s -X POST http://localhost:5125/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])")
# 删除一个不存在的资源
curl -i -X DELETE -H "Authorization: Bearer $TOKEN" http://localhost:5125/api/users/00000000-0000-0000-0000-000000000000
# 期望: 404 而非 500
```

### Track B3：Prisma 模型

**关注点：**

- 48 个模型的 FK 是否都有 `@@index`
- `onDelete` 行为一致性：父表删 → 子表如何？
- 字符串字段是否缺长度限制（MySQL 默认 `VARCHAR(191)` 太小）
- 金额字段：`Float` vs `Decimal`（应聘 Offer、Onboarding 等）
- 软删除模式：当前用 `status: ACTIVE/INACTIVE`，但不是所有模型都有一致字段
- `@@unique` 约束是否完整（如 `User.email`、`User.phone` 的可选性）
- 枚举：用 Prisma `enum` 还是 `String`（前者类型安全但迁移麻烦）

**验证：**

```bash
npx prisma validate
npx prisma db push
# 跑完所有种子后查询代表性数据，确认类型正确
```

### Track B4：API 设计与架构

**关注点：**

- 响应包络一致性：`{success, data, error}` vs 其他变体
- HTTP 状态码：4xx vs 5xx 的使用
- 分页：是否有 helper（`page`/`pageSize`/`total`）
- 错误信息：用户可见消息 vs 内部错误
- 路由组织：是否能用 router 子分组（`/api/departments/:id/managers`）
- 中间件：是否复用 `errorHandler`、`authMiddleware`
- 前端 store：是否按域分文件（`user.store.ts` 之外是否还有 `demand.store.ts` 等）

**验证：**

```bash
# 检查 6+ 个端点返回结构一致
for endpoint in /api/users /api/departments /api/processes /api/demands; do
  curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:5125${endpoint}" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'success' in d, f'{sys.argv[1]} 缺 success'; print(f'{sys.argv[1]} ✓')" "${endpoint}"
done
```

### Track C：端到端验收

**5 步烟测脚本（在真实 MySQL 上跑）：**

1. `docker compose up mysql -d` → 等待 healthy
2. 启动 backend → `npx prisma db push` → 跑所有 seed
3. 启动 frontend → `npm run build` 成功
4. curl 流程：登录 → 创部门 → 查部门 → 改部门 → 删部门
5. 故意触发一个错误路径（重复 code、删有子的部门）→ 确认返回结构合理

输出 green/red 报告。

## 数据流 & 顺序依赖

```
A ──▶ B1 ──▶ B2
        └──▶ B3
        └──▶ B4
              │
              ▼
              C
```

- B1 必须在最前：清理 TS 注解让后续审计更清晰
- B2/B3/B4 之间无强依赖，按 B1→B2→B3→B4 顺序是因"安全>模型>API"的"破坏面"递增

## 错误处理策略

| 情况 | 应对 |
|---|---|
| B 维度发现 A 没做对 | 回到 A 修，重跑 A 验证 |
| B 维度发现需要重写某模块 | 停下来报告，列选项，不静默改 |
| MySQL 迁移中遇到 Prisma 不支持的特性 | 改代码而非降级 |
| 改动导致 `vite build` 失败 | 立即停，回滚该子任务 |
| 用户给的 MySQL 串连不上 | 报具体错误（DNS/密码/版本），不瞎猜 |
| 跨 Track 的发现 | 不绕过，回到上游 Track 处理 |

## 测试方法

每个 Track 收尾**必须**跑：

1. **静态**：`npx prisma validate`（涉及 schema 时）
2. **构建**：`npx vite build`（前端改动后）
3. **加载**：`node -e "import('./src/app.js')"` 或 `npm run dev` 起服务
4. **烟测 curl**：登录 + 1 GET + 1 POST + 1 错误路径
5. **报告留档**：把命令 + 实际输出粘到当轮回复

**不通过的 Track 不算完成，不进下一 Track。**

## 报告交付物

`docs/superpowers/review/2026-06-02-ats-review-report.md`，每条问题含：

- **位置**：`file:line`
- **维度**：B1/B2/B3/B4
- **严重度**：P0（阻塞/安全）/P1（必须修）/P2（建议修）/P3（可选）
- **说明**：为什么是问题
- **修复**：具体改动（不只说"应该 X"）

## 自审清单

- [x] 范围聚焦：单次实现计划可消化
- [x] 段间无矛盾
- [x] 无 "TBD"/"TODO" 占位
- [x] 每条需求可观察可验证
- [x] 错误路径明确
- [x] 验收命令具体
