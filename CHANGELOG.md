# CHANGELOG

## 2026-06-08 — P1-D 完成: G31 智能分配 + G32 6 子库完整 CRUD

### G31 待入职智能分配 (PRD G31)
- **position-matcher.service.js** (9 测试) - 候选人↔职位双向推荐
  - 4 维度加权: 学历(0.25) / 经验(0.30) / 职位意向(0.25) / 地点(0.20)
  - `computeMatchScore` / `buildMatchReason` / `rankPositions`
  - `recommendPositionsForCandidate` / `recommendCandidatesForPosition`
- **position-recommendation.routes.js** - 2 个新 API
  - `GET /api/recommendations/positions/for-candidate/:id`
  - `GET /api/recommendations/candidates/for-position/:id`
- **前端 OnboardingList.vue** - 智能分配按钮 + n-drawer 推荐职位列表

### G32 人才库 6 子库完整 CRUD (PRD G32)
- **talent-pool.service.js** (9 测试) - 6 子库枚举 + 跨池移动 (审计)
  - PASSIVE/ACTIVE/HIRED/REJECTED/BLACKLIST/GENERAL
  - `listPoolStats` / `listCandidatesInPool` / `moveCandidateToPool` (写 OperationRecord)
  - 复用 Candidate.archiveToPool + candidateStatus='ARCHIVED'
- **talent-pool.routes.js** - 4 个新 API (types/stats/pool/:code/move)
- **前端 TalentPool.vue** - 6 子库 tab + 跨池移动弹窗 (n-modal)

### 配套
- on boarding.routes.js 列表查询 include application, 列表行带 candidateId/candidateName (供 G31 智能分配按钮)

---

## 2026-06-06 — P0 全部 done：14 个状态机 + 7 完整 UI + 5 路审计修复

### 🏆 P0 14/14 全部完成（PRD Phase 1 + Phase 2 部分）
- **G38** 招聘流程引擎（已之前 done）
- **G1 需求 8 状态机 + G2 审批引擎** + B.1 审计 + B.2 通知 + B.3 配置化 MVP
- **G3.6 面试 5 状态机**
- **G5 职位 3 状态机 + 候选人存在保护**
- **G9 候选人批量操作 API**（4 端点：推荐/归档/分配/导出）
- **G10 + G1.5 候选人阶段进入条件引擎**（复用 recruitment-condition evaluator）
- **G14 邀约抢单 + 8 状态机 + cron 超时处理**（含 G15 + G16）
- **G23 Offer 9 状态机 + G24 4 模板 + PDF 服务端生成**（纯 JS 零依赖）
- **G28 待入职 8 状态机**
- **G36 通知模板系统**（22 个 seed + 4 端点）
- **G1.7 List 页完整化**（5 页面：Demand/Position/Candidate/Offer/Invitation/Interview/Onboarding/Talent）

### 🔒 安全修复
- **#8 async handler** 全部 52 个路由加 `next` 参数（permission-v2/user/department/resume）
- **#9 resume IDOR** 5 端点 operatorId 改 `req.userId` + 审批 expectedApproverId 鉴权
- **PDF 服务端生成** 纯 JS PDF 1.4 实现（10 测试，含 Offer 端到端）
- **JWT/CORS 启动校验** middleware（生产环境不通过即 process.exit(1)）
- **deletedAt Prisma Extension** middleware（7 核心表自动软删除）

### 🛠 5 路审计 + 批量修复（commit `a460729e`）
- C1 修 `/api/processes` 500（stages → links）
- C2 修 4 个 api 文件重复 `/api` 前缀（interview/offer/onboarding/invitation）
- C3 修 ResumeList 4 处路由不匹配（resumes/resume → resume）
- C4 新建 talent-pool.routes.js（G32 MVP）
- C5 `/api/permissions` 加根路由

### 📊 统计
- **14 个新 schema 表**（DemandApprovalStep / DemandStatusHistory / NotificationQueue / NotificationTemplate / DemandApprovalConfig / OfferStatusHistory / PositionStatusHistory / OnboardedAt 字段 / OperationRecord 扩字段）
- **40+ 新端点**
- **204 单元测试** 全过
- **~13,000 行新代码**
- **15 commits**（最后推到 GitHub + Gitee）

---

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
