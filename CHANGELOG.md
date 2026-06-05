# CHANGELOG

## 2026-06-05 — UI 框架大迁移：Ant Design Vue + Tailwind → Naive UI + UnoCSS

### 🔄 框架替换
- **前端 UI 库**：`ant-design-vue@4.2.6` → `naive-ui@2.44.1`
- **图标库**：`@ant-design/icons-vue@7.0.1` → `@vicons/ionicons5@0.13.0`
- **CSS 方案**：`tailwindcss@3.4` + `daisyui` → `unocss@66.7` + `@unocss/reset`
- 删除：`tailwind.config.js`、`postcss.config.js`

### 📁 新增配置
- `frontend/uno.config.ts` — UnoCSS 配置（含品牌色、字体、shortcuts）
- `frontend/src/main.ts` — 改用 `virtual:uno.css` + `@unocss/reset/tailwind.css`
- `frontend/src/App.vue` — 包 `<n-config-provider>` 等 4 个 provider（message/dialog/notification/loading-bar）
- `MIGRATION.md` — 完整 ant→naive 组件 + 图标 + API 映射文档

### 🔧 迁移范围
**全部 29 个 .vue 文件迁移**（用 3 个并行 agent + 我亲自处理最大 2 个）：
- 4 个核心文件（Layout / Login / Dashboard / ReferralCenter）— 我做
- 7 个小文件（OfferList / Notification / Screening / Onboarding / Invitation / Interview / Placeholder）— Agent 1
- 7 个中文件（Settings / ProcessManagement / SpecialApproval / AccountSettings / PositionList / ResumeList / AddCandidateModal）— Agent 2
- 5 个大文件（DepartmentManagement / DemandConfig / UserManagement / DemandList / MouManagement）— Agent 3
- 2 个超大文件（CandidateList 24KB / CandidateDetail 40KB）— 我做
- 6 个空数据 placeholder（DataDictionary / StageConfig / PermissionManagement / CompanySettings / ScoringRules / TalentPool）— 改用 n-empty

### ⚠️ 关键 API 差异
- `<a-table>` → `<n-data-table>` + `render(row)` 函数替代 `customRender`
- `<a-modal :visible>` → `<n-modal :show>`
- `<a-tabs :items>` → `<n-tabs :options>` 数组
- `<a-row/a-col>` → `<n-grid>/<n-grid-item>`
- `<a-tag :color>` → `<n-tag :type>`（预设值：default/primary/info/success/warning/error）
- `message.success()` → `useMessage()` 包裹
- `import { UserOutlined }` → `import { PersonOutline }` from `@vicons/ionicons5`

### 🧹 清理
- 删除孤儿 `PermissionManagement.css`（不再被任何文件 import）
- 删除 `frontend/api/auth.ts` 残留的 `import('ant-design-vue')` 动态 import

### ✅ 验证
- 0 残留 `ant-design-vue` 引用
- 0 残留 `<a-*>` 组件
- 0 残留 `@tailwind` / `@apply`
- 32 个文件用 naive-ui 组件
- 前端首页 HTTP 200，main.ts/App.vue/Layout.vue/Login.vue/ReferralCenter.vue 全部能编译
- E2E：登录 + 内推码查询均通过

---

## 2026-06-04 — 维护与 bug 修复

### 🐛 修复
- **AUTH BUG: `/auth/me` 和 `/change-password` 漏挂 auth 中间件**
  - 文件：`backend/src/routes/auth.routes.js`
  - 症状：`/auth/me` 返回 `id: undefined` Prisma 错误
  - 修复：加 `import { authMiddleware }`，路由前挂 `authMiddleware,`

- **AUTH BUG: 前端拦截器调不存在的 `/auth/refresh`**
  - 文件：`frontend/src/api/auth.ts`
  - 症状：任何 401 → 调 refresh → 404 → 自动登出 + 跳登录页
  - 修复：移除 refresh 逻辑，401 直接 logout + 跳登录；同时排除 login 自身的 401（让 Login.vue 自己处理）

- **SCHEDULER BUG: `Onboarding.status` 字段不存在**
  - 文件：`backend/src/referral/scheduler/referral.scheduler.js:25`
  - 症状：cron 每 15 分钟报 `Unknown argument 'status'`
  - 修复：改用 `onboardingStatus`

- **ROUTER BUG: `/report` 路由在菜单里但没注册**
  - 文件：`frontend/src/router/index.ts`
  - 修复：加占位路由 → `Placeholder.vue`（显示"即将上线"）

- **ROUTER BUG: 重复的 `name: 'ProcessManagement'`**
  - 文件：`frontend/src/router/index.ts`
  - 修复：第二个改名 `ProcessManagementConfig`

### 🧹 清理
- 删除未使用的 `getCurrentUser`（`frontend/src/api/auth.ts`）
- 删除历史残留的 `prisma/dev.db`（SQLite 文件，与 MySQL schema 冲突）
- 删除 `prisma/seed/` 之外残留的旧 seed 文件

### 📝 文档
- 重写 `README.md`：反映 MySQL 真实环境、添加变更摘要、链接到新文档
- 新增 `docs/SETUP.md`：5 分钟安装步骤 + 故障排查附录
- 新增 `docs/ARCHITECTURE.md`：模块依赖、数据流、关键决策
- 新增 `docs/TROUBLESHOOTING.md`：登录/数据库/Prisma/前端 4 大类问题
- 新增本 CHANGELOG

### 🏗 基础设施
- 创建 `ats` 数据库 + `ats@127.0.0.1` 用户
- 创建 `backend/.env`（含 MySQL 连接、JWT、端口、CORS）
- 推送 Prisma schema（54 张表）
- 灌入 4 个 seed：user / department / permission / referral

### ✅ 验证
- 后端 7 个登录场景全过（正常登录/错密码/空请求/proxy/无 token/无效 token 等）
- `/auth/me` 修复后返回完整用户对象
- 端到端：浏览器 `http://localhost:5212` → 登录 → dashboard

### ➕ 新增
- **内推门户前端**（Phase 1 MVP）
  - `frontend/src/api/referral.ts` - 6 个端点的 API 客户端 + TypeScript 类型定义
  - `frontend/src/pages/referral/ReferralCenter.vue` - 5 个 Tab：我的码 / 战绩 / 记录 / 奖励 / 规则
  - 路由 `/referral` + Layout 菜单"内推中心"（`ShareAltOutlined` 图标）
  - 包含：复制内推码、生成分享链接、战绩统计卡片、分页表格、规则卡片展示
  - 懒加载：切 tab 才请求对应接口，避免初始加载过重
  - 菜单路径：侧边栏 → "内推中心"（在 Offer管理 和 数据中心 之间）

---

## 2026-05（节选）

- 内推门户 Phase 1 上线（5 路由 + 3 cron + 3 XState 状态机 + 3 核心服务 + 规则引擎）
- 详见 [git log](https://github.com/.../commits/main) 590a8e71..960018b6
