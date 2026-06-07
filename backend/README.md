# ATS Backend - 招聘管理系统后端

## 概述

ATS 招聘管理系统的后端 API 服务。基于 **Express + Prisma + MySQL 9**，提供完整的状态机驱动的招聘流程 API。

**最后更新**: 2026-06-06（P0 14/14 全部完成）

## 启动

```bash
# 安装依赖
npm install

# 数据库初始化（仅首次）
./node_modules/.bin/prisma db push
node prisma/seed/notification-templates.js  # 22 通知模板 seed

# 启动开发
node --env-file=.env src/app.js
# 或
npm run dev  # nodemon

# 跑测试
NODE_OPTIONS=--experimental-vm-modules ./node_modules/.bin/jest --runInBand
```

后端默认端口：**5125**

## 目录结构

```
src/
├── app.js                       # Express 主入口
├── config/                      # 配置
├── middleware/                  # 鉴权/错误/软删/JWT 校验
├── referral/                    # 内推门户（XState v5 状态机）
│   ├── services/                # 4 个 service + 9 测试
│   ├── routes/                  # 28 端点
│   ├── machines/                # 3 XState 状态机 + 9 测试
│   └── scheduler/               # node-cron 调度（3 任务）
├── routes/                      # 21 个业务路由文件
├── services/                    # 9 个业务 service
│   ├── demand-state-machine.service.js
│   ├── demand-approval.service.js
│   ├── interview-state-machine.service.js
│   ├── position-state-machine.service.js
│   ├── offer-state-machine.service.js
│   ├── invitation-state-machine.service.js
│   ├── onboarding-state-machine.service.js
│   ├── scoring-rule.service.js          # G39
│   ├── audit-log.service.js             # B.1
│   ├── notification.service.js          # B.2 + G36
│   ├── pdf-generator.service.js         # G24 服务端 PDF
│   └── recruitment-condition.service.js # 复用（G10/G38）
├── scheduler/                   # 业务 cron
│   └── invitation.scheduler.js         # G14 超时处理
└── prisma/                      # 种子 + 迁移
```

## API 模块清单（25+ 路由文件 / 60+ 端点）

| 前缀 | 模块 | 端点数 | PRD |
|---|---|---|---|
| `/api/auth` | 认证 | 4 | - |
| `/api/demands` | 需求 + 8 状态机 + 4 审批 | 7 | G1 + G2 + G3 |
| `/api/candidates` | 候选人 + 批量操作 | 12 | G9 + G10 + G11 + G13 |
| `/api/positions` | 职位 + 3 状态机 | 6 | G5 |
| `/api/invitations` | 邀约 + 8 状态机 + 抢单池 | 10 | G14 + G15 + G16 |
| `/api/offers` | Offer + 9 状态机 | 5 | G23 |
| `/api/offer-templates` | Offer 4 模板 + PDF 生成 | 4 | G24 |
| `/api/onboardings` | 待入职 + 8 状态机 | 5 | G28 |
| `/api/notification-templates` | 通知模板 CRUD | 5 | G36 |
| `/api/interviews` | 面试 + 5 状态机聚合 | 6 | G3.6 |
| `/api/recruitment-processes` | 流程 (G38) | 7 | G38 |
| `/api/recruitment-stages` | 全局阶段模板 | 7 | G38 |
| `/api/recruitment-rules` | 阶段规则/进入条件/自动归档 | 14 | G38 |
| `/api/scoring-rules` | 评分规则 | 7 | G39 |
| `/api/talent-pool` | 人才库 6 子库 | 3 | G32 MVP |
| `/api/permissions` | 权限 V1 | 17 | - |
| `/api/permissions-v2` | 权限 V2 (MOU) | 20 | - |
| `/api/users` | 用户 | 8 | - |
| `/api/departments` | 部门 | 6 | - |
| `/api/resumes` | 简历 | 14 | - |
| `/api/referral` | 内推门户 (28 端点) | 28 | Phase 1 |

## 数据模型

**54+ 张表**（详细见 [prisma/schema.prisma](prisma/schema.prisma)），本会话新增 8 张：

- `DemandApprovalStep` - 需求审批步骤
- `DemandStatusHistory` - 需求状态变更历史
- `NotificationQueue` - 通知队列表
- `NotificationTemplate` - 通知模板表
- `DemandApprovalConfig` - 需求审批链配置
- `OfferStatusHistory` - Offer 状态变更历史
- `PositionStatusHistory` - 职位状态变更历史
- `Onboarding.onboardedAt` - 入职完成时间字段

## 安全与中间件

- **authMiddleware** - JWT 验证 + 用户查询
- **permissionMiddleware** - V1 权限检查
- **errorHandler** - Prisma 错误码映射
- **soft-delete.middleware.js** - Prisma Client Extension 自动注入 `deletedAt: null`（7 核心表）
- **jwt-validation.middleware.js** - 启动时校验 JWT 长度 + 占位符检测（生产环境 process.exit(1)）
- **rateLimit** - 300 req/min

## 测试

```bash
# 跑全部（10 个测试套件 / 214 测试）
NODE_OPTIONS=--experimental-vm-modules ./node_modules/.bin/jest --runInBand

# 跑某个
NODE_OPTIONS=--experimental-vm-modules ./node_modules/.bin/jest src/services/__tests__/demand-state-machine.test.js

# 覆盖率
npm run test:coverage
```

## 数据库

```bash
# 应用 schema 变更
./node_modules/.bin/prisma db push

# 打开 Prisma Studio
./node_modules/.bin/prisma studio

# 重置 + 重新 seed
./node_modules/.bin/prisma db push --force-reset
node prisma/seed.notification-templates.js
```

**注意**：当前 MySQL 有 54 张表但只有 1 个 migration 文件（referral）。生产部署需补 baseline migration。

## 后台调度

| Cron 表达式 | 任务 | 文件 |
|---|---|---|
| `0 * * * *` | Referral 保护期过期 | `referral/scheduler/referral.scheduler.js` |
| `*/15 * * * *` | Referral 入职→奖励触发 | 同上 |
| `*/10 * * * *` | 邀约抢单超时处理 | `scheduler/invitation.scheduler.js` |
| `0 0 * * *` | Referral 内推码失效扫描 | `referral/scheduler/referral.scheduler.js` |

## 环境变量（.env）

```bash
DATABASE_URL=mysql://ats:AtsPass2024!@127.0.0.1:3306/ats
JWT_SECRET=<min-32-chars-random-string>
NODE_ENV=development  # production 时会强制 JWT/CORS 校验
CORS_ORIGIN=http://localhost:5212  # 生产必填
PORT=5125
```

## CI

`.github/workflows/ci.yml` 提供 3 个 job：
- test-backend: MySQL 9 service + Jest
- test-frontend: vue-tsc + vite build
- security-scan: Trivy 高危扫描

## 已知遗留

- 5 路审计 leftover：路由 `meta.roles` 粒度、recruitment-auto-advance dead service
- 业务表 `deletedAt` 字段未加（middleware 已就绪）
- PDF 中文字体（当前 Helvetica 显示乱码）
- 5 个 P1 剩余：G8 字段级权限 / G19 复检 / G26 手动背调 / G3 复检
- 外部集成：企微 / 腾讯会议 / 摩卡 People / 背调 / RPA
- e2e 测试（Playwright）
- GDPR 真正合规

详见根目录 [PROJECT_PLAN.md](../PROJECT_PLAN.md) 第 5 阶段和 [CHANGELOG.md](../CHANGELOG.md)。
