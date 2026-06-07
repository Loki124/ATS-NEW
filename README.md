# ATS 招聘管理系统

> 企业级招聘管理系统（Applicant Tracking System），用于管理招聘全流程

## 📋 项目概述

ATS 招聘管理系统是一个功能完善的企业级招聘管理平台，支持候选人管理、招聘流程、简历筛选、面试管理、Offer发放、入职管理等全流程招聘管理能力。

### 最新动态

- 🏆 **P0 全部完成 (2026-06-06)**：14 个 P0 模块 + 5 路审计修复 + B.1/B.2/B.3 配套，详见 [CHANGELOG.md](CHANGELOG.md)
- 🛡 **安全债修复**：52 个 async handler 加 next、5 个 IDOR 漏洞修、CI workflow、Prisma deletedAt middleware、JWT 启动校验
- 📄 **PDF 服务端生成**：纯 JS 零依赖，Offer 4 模板可下载
- 🎨 **UI 迁移完成**（2026-06-05）：Ant Design Vue → Naive UI，UnoCSS 替代 Tailwind
- 🎉 **内推门户（Referral）Phase 1** 上线：内推码、推荐记录、奖励、规则引擎、XState v5 状态机
- 🛠 **2026-06 维护**：修复了若干 auth 中间件漏挂、定时任务字段名错、前端 401 自动登出 bug

## 🎯 核心功能

### P0 优先级（核心模块）✅ 全部完成
- ✅ **G38 招聘流程引擎** - 自定义流程 + 阶段模板 + 阶段规则 + 进入条件 + 自动归档
- ✅ **G1 需求 8 状态机** - DRAFT/NOT_STARTED/IN_PROGRESS/COMPLETED/PAUSED/STOPPED/EXPIRED
- ✅ **G2 审批引擎** - HRBP→MANAGER→MANAGER_SUPER→CHO 多级 + B.3 可配置化
- ✅ **G3.6 面试 5 状态机** - NOT_ARRANGED/PENDING_FEEDBACK/ALL_PASS/PARTIAL_PASS/ALL_FAIL
- ✅ **G5 职位 3 状态机** - RECRUITING/PAUSED/CLOSED + 候选人存在保护
- ✅ **G9 候选人批量操作** - 推荐/归档/分配/导出 4 端点
- ✅ **G10 + G1.5 候选人阶段进入条件引擎** - 复用 recruitment-condition evaluator
- ✅ **G14 邀约抢单 + 8 状态机 + cron** - 48h 倒计时 + 3 次自动归档
- ✅ **G23 Offer 9 状态机** - 完整状态流转
- ✅ **G24 Offer 4 模板 + PDF 服务端生成** - 通用/含提成/实习生/梅州版
- ✅ **G28 待入职 8 状态机** - 完整入职流程
- ✅ **G36 通知模板系统** - 22 个 seed（5 审批 + 4 面试 + 6 Offer + 3 候选 + 2 入职 + 2 需求）
- ✅ **G1.7 List 页完整化** - 5 个核心页面（Invitation/Offer/Interview/Onboarding/Talent + 已存在 3 个）
- ✅ **内推门户** - 内推码、推荐记录、奖励、规则引擎

### P1 优先级（重要模块）
- **邀约中心** - 候选人邀约管理（含抢单模式）
- **面试管理** - 面试安排、反馈评价、日程同步
- **Offer管理** - Offer创建、审批、发送、背调
- **待入职管理** - 入职流程管理、People系统同步

### P2 优先级（辅助模块）
- **系统管理** - 招聘流程配置、评分规则、数据字典
- **数据中心** - 招聘数据报表、BI看板（即将上线）
- **我找的简历** - 简历来源管理

## 🛠 技术栈

### 前端技术栈
- **框架**: Vue 3 + TypeScript + Composition API
- **UI 框架**: Ant Design Vue 4.x
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **HTTP 客户端**: Axios
- **构建工具**: Vite 5

### 后端技术栈
- **运行时**: Node.js 18+（推荐 20 LTS）
- **框架**: Express.js 4
- **数据库**: MySQL 8+（开发/生产统一）
- **ORM**: Prisma 5
- **认证**: JWT (jsonwebtoken)
- **密码**: bcryptjs
- **定时任务**: node-cron
- **状态机**: XState v5
- **测试**: Jest + Supertest

> 注：早期版本曾支持 SQLite 作为开发数据库，现已统一为 MySQL。Prisma schema 声明 `provider = "mysql"`，迁移文件全部使用 MySQL 语法。

## 📁 项目结构

```
ATS-New/
├── frontend/                      # 前端项目
│   ├── src/
│   │   ├── api/                  # API 接口封装
│   │   │   └── auth.ts           # 认证 + axios 拦截器
│   │   ├── pages/                # 页面组件
│   │   │   ├── demand/           # 需求管理
│   │   │   ├── position/         # 职位管理
│   │   │   ├── candidate/        # 候选人管理
│   │   │   ├── interview/        # 面试管理
│   │   │   ├── offer/            # Offer 管理
│   │   │   ├── onboarding/       # 入职管理
│   │   │   ├── talent/           # 人才库
│   │   │   ├── resume/           # 简历管理
│   │   │   ├── invitation/       # 邀约中心
│   │   │   ├── screening/        # 简历筛选
│   │   │   ├── notification/     # 消息通知
│   │   │   └── settings/         # 系统设置
│   │   ├── stores/               # Pinia 状态管理
│   │   │   └── user.ts
│   │   ├── router/               # Vue Router
│   │   └── config/               # 前后端配置常量
│   └── package.json
│
├── backend/                       # 后端项目
│   ├── src/
│   │   ├── app.js                # Express 主入口（中间件、路由挂载）
│   │   ├── config/               # 统一配置
│   │   ├── middleware/           # 错误处理、auth 拦截
│   │   ├── routes/               # 业务路由
│   │   └── referral/             # 内推模块
│   │       ├── machines/         # XState v5 状态机
│   │       ├── services/         # 业务服务
│   │       ├── routes/           # REST 路由
│   │       ├── scheduler/        # cron 任务
│   │       └── validators/       # 参数校验
│   ├── prisma/
│   │   ├── schema.prisma         # 54 个数据模型
│   │   ├── migrations/           # 迁移历史（注意：仅含 referral phase1，主体表用 db push 推）
│   │   └── seed/                 # 基础数据 seed
│   └── package.json
│
├── docs/                         # 项目文档
│   ├── superpowers/              # Claude Code skills（已装到 ~/.claude/skills/）
│   ├── SETUP.md                  # 详细安装步骤
│   ├── ARCHITECTURE.md           # 架构说明
│   └── TROUBLESHOOTING.md        # 常见问题排查
│
├── CHANGELOG.md                  # 变更日志
├── PROJECT_PLAN.md               # 项目实施计划
└── README.md
```

## 🚀 快速开始

> 详细步骤见 [docs/SETUP.md](docs/SETUP.md)。最小可用版本：

```bash
# 1. 启动 MySQL（homebrew）
brew services start mysql

# 2. 建库建用户
mysql -uroot -p<password> <<SQL
CREATE DATABASE ats CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ats'@'127.0.0.1' IDENTIFIED BY 'AtsPass2024!';
GRANT ALL PRIVILEGES ON ats.* TO 'ats'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

# 3. 后端
cd backend
cp .env.example .env   # 按需修改密码
npm install
./node_modules/.bin/prisma generate
./node_modules/.bin/prisma db push
npm run db:seed
node --env-file=.env src/app.js

# 4. 前端（另开终端）
cd frontend
npm install
./node_modules/.bin/vite
```

### 默认账号

```
用户名: admin
密码:   admin123
```

### 访问入口

| 服务 | 地址 |
|---|---|
| 前端 | http://localhost:5212 |
| 后端 | http://localhost:5125 |
| API 健康检查 | http://localhost:5125/api/health |

## 📊 数据库模型概览

54 个数据模型，按模块分组：

| 模块 | 关键模型 |
|---|---|
| 认证与用户 | User, Department, Permission, MouPermission |
| 招聘需求 | Demand, DemandApproval |
| 职位 | Position, PositionCategory |
| 候选人 | Candidate, Resume, Application |
| 流程 | Process, ProcessStage, Screening |
| 面试 | Interview, InterviewFeedback |
| Offer | Offer, OfferApproval |
| 入职 | Onboarding, OnboardingApproval |
| 邀约 | Invitation, InvitationRecord |
| 通知 | Notification |
| **内推（Referral）** | ReferralCode, ReferralRecord, ReferralTeam, ReferralReward, ReferralRule, ExpertConfig |
| 字典 | Dictionary, ScoringRule |

完整 schema 见 [backend/prisma/schema.prisma](backend/prisma/schema.prisma)。

## 🔐 角色权限

8 个角色，按权限级别从高到低：

| 角色 | 说明 | 级别 |
|---|---|---|
| SUPER_ADMIN | 超级管理员 | 8 |
| ADMIN | 系统管理员 | 7 |
| HRBP | HR 业务伙伴 | 6 |
| HR | 招聘专员 | 5 |
| MANAGER | 用人经理 | 4 |
| INTERVIEWER | 面试官 | 3 |
| CANDIDATE | 候选人 | 2 |
| RECEPTION | 前台/门卫 | 1 |

权限矩阵（功能权限 + 数据权限）由 `permission.seed.cjs` 灌入，存储在 Permission / MouPermission 表。

## 📝 API 接口

所有业务接口都在 `/api` 前缀下，**全部需要 Bearer token**（`authMiddleware` 挂在 `app.use` 级别）。

### 认证接口（无需 token）

| Method | Path | 说明 |
|---|---|---|
| POST | `/api/auth/login` | 用户登录（用户名+密码） |
| POST | `/api/auth/register` | 用户注册（需超管权限） |
| POST | `/api/auth/change-password` | 修改密码（需登录） |
| GET | `/api/auth/me` | 获取当前登录用户（需登录） |
| GET | `/api/health` | 健康检查 |

### 业务接口

| 路径 | 模块 |
|---|---|
| `/api/users` | 用户管理 |
| `/api/departments` | 部门管理 |
| `/api/demands` | 招聘需求 |
| `/api/candidates` | 候选人管理 |
| `/api/resumes` | 简历管理 |
| `/api/interviews` | 面试管理 |
| `/api/offers` | Offer 管理 |
| `/api/onboardings` | 入职管理 |
| `/api/invitations` | 邀约中心 |
| `/api/notifications` | 消息通知 |
| `/api/permissions` | 权限管理（V1） |
| `/api/permissions-v2` | 权限管理（V2 / MOU） |
| `/api/referral/*` | 内推门户（详见下文） |

## 🎁 内推门户（Referral）使用指南

### 用户视角

打开 **内推中心**（侧边栏 → 内推中心），5 个 Tab：

| Tab | 内容 | 操作 |
|---|---|---|
| **我的内推码** | 你的专属 8 位内推码（自动生成，可复制码或分享链接） | 复制码 / 复制链接 / 失效可联系管理员 |
| **我的战绩** | 6 张统计卡：有效推荐 / 已入职 / 过试用期 / 待确认奖励 / 已确认 / 已发放 | 只读 |
| **推荐记录** | 候选人 + 职位 + 状态 + 推荐时间 | 只读 |
| **我的奖励** | 候选人 + 金额 + 状态 + 时间 | 只读（管理员可确认/拒绝/发放） |
| **内推规则** | 当前生效的奖励规则 + 限制规则 | 只读（管理员 CRUD 在 `/api/referral/rules`） |

**人工新增推荐**：页面右上角"**新增推荐**"按钮 → 选需求 → 选职位 → 填候选人姓名/手机号/邮箱 → 提交。后端会自动：1) 创建 `Candidate`；2) 创建 `ReferralRecord`（`referralType=REFERRER_HELP`）；3) 走规则校验（成员限制）。

**奖励生命周期**：`TO_CONFIRM`（HRBP 确认）→ `CONFIRMED`（HRBP 发放）→ `ISSUED`，或被 `REJECTED` 拒绝。

### 架构

```
backend/src/referral/
├── index.js                          // 路由聚合 + 启停 scheduler
├── machines/                         // XState v5 状态机
│   ├── referralCode.machine.js       // 内推码状态：ACTIVE / INVALID
│   ├── referralRecord.machine.js     // 推荐记录：NORMAL→PROTECTING→HIRED / REJECTED / EXPIRED
│   └── referralReward.machine.js     // 奖励状态：PENDING→TO_CONFIRM→CONFIRMED→ISSUED / REJECTED
├── services/
│   ├── code.service.js               // 码生成（nanoid 6 位）+ CRUD
│   ├── record.service.js             // 创建/推进/去重
│   ├── rule.service.js               // 规则 CRUD
│   ├── rule-evaluator.service.js     // 条件求值（ALL/ANY 逻辑）
│   └── reward.service.js             // 奖励触发/确认/发放/拒绝
├── routes/                           // 5 个 Express 路由（29 个端点）
├── validators/referral.validator.js  // express-validator
├── scheduler/referral.scheduler.js   // 3 个 cron：保护期失效 / 奖励触发 / 过期清理
└── __tests__/                        // 9 个 Jest 测试
```

### 关键 API（`/api/referral/*`）

| Group | Endpoints | 用途 |
|---|---|---|
| **codes** | `GET /codes/me`, `GET /codes/validate?code=X`, `GET /codes/user/:userId` | 内推码 |
| **records** | `GET /records/me`, `GET /records/me/summary`, `GET /records/me/:id`, `POST /records`, `POST /records/by-code`, `POST /records/:id/urge`, `POST /records/:id/recommend-again`, `GET /records`, `GET /records/:id`, `POST /records/:id/invalidate` | 推荐记录 |
| **rewards** | `GET /rewards/me`, `GET /rewards/me/summary`, `GET /rewards`, `POST /rewards/:id/confirm`, `POST /rewards/:id/reject`, `POST /rewards/:id/issue`, `POST /rewards/trigger` | 奖励 |
| **rules** | `GET /rules`, `GET /rules/:id`, `POST /rules`, `PUT /rules/:id`, `POST /rules/:id/toggle`（**仅管理员**） | 规则管理 |
| **expert-configs** | `GET /expert-configs/me`, `POST /expert-configs`, `PUT /expert-configs/:id`, `DELETE /expert-configs/:id` | 招聘专家配置 |

### 规则配置示例

```js
// 规则 conditions 字段（JSON）
{
  "logic": "ALL",  // AND
  "conditions": [
    { "key": "positionLevel", "op": "EQ", "value": "P5" },
    { "key": "referralCount", "op": "GTE", "value": 1 }
  ]
}
// 支持 op: EQ / NEQ / GT / GTE / LT / LTE / IN / CONTAINS
// logic: ALL（全部满足） / ANY（任一满足）
```

### Seed 数据

```bash
node --env-file=.env prisma/seed.referral.js
```

会创建：1 个团队 + 2 条规则（`P5 入职奖励 ¥3000` / `经营者不可内推`）+ 10 个内推码 + 3 个候选人 + 3 条记录 + 1 条待确认奖励。

> ⚠️ 依赖基础 user / department / position seed 已跑过。**至少 1 个 ACTIVE 职位**，否则记录 seed 跳过。

## 🔌 第三方集成

- **企微审批流** - Offer 审批、入职审批
- **三方背调系统** - 背调下单及结果回传
- **视频会议** - 腾讯会议（面试视频链接）

## 📅 招聘流程

```
简历上传 → 简历解析 → 职位匹配 → 进入招聘流程
    ↓
初评筛选 → HRBP筛选 → 用人经理筛选 → 用人经理上级筛选
    ↓
邀约 → 联合面试 → 综合面试
    ↓
Offer沟通 → 背调 → 待入职 → 入职
```

## 📚 配套文档

- [docs/SETUP.md](docs/SETUP.md) - 详细安装步骤（含 Windows / Linux / Docker）
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - 系统架构、模块依赖、数据流
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - 常见问题排查（登录失败、数据库连接、CORS 等）
- [CHANGELOG.md](CHANGELOG.md) - 版本变更日志
- [PROJECT_PLAN.md](PROJECT_PLAN.md) - 实施计划

## 📄 许可证

本项目仅供内部使用。
