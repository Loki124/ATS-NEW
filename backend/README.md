# ATS Backend - 内推门户 (Referral Portal) Phase 1

## 内推门户模块

### 概述
Phase 1 实现了内推门户的数据模型、核心服务、REST API 和后台调度。**不含任何 UI** - UI 将在 Phase 2+ 实施。

### 入口
- 路由前缀：`/api/referral/*`
- 模块入口：`backend/src/referral/index.js`
- 调度器：`backend/src/referral/scheduler/referral.scheduler.js`

### 数据模型（6 张新表）
- `referral_codes` - 内推码（每个用户一个）
- `referral_expert_configs` - 内推人对接招聘专家配置
- `referral_teams` - 内推团队
- `referral_records` - 内推记录（核心表）
- `referral_rewards` - 内推奖励
- `referral_rules` - 内推规则（成员限制 + 奖励）

### 状态机（XState v5）
- `referralCodeMachine` - 内推码 ACTIVE/INVALID
- `referralRecordMachine` - 记录 NORMAL/PROTECTING/EXPIRED/COMPLETED/INVALID
- `referralRewardMachine` - 奖励 PENDING/TO_CONFIRM/CONFIRMED/REJECTED/ISSUED

### 业务服务
- `code.service.js` - 内推码生成/失效/校验
- `record.service.js` - 推荐创建/状态推进/列表
- `reward.service.js` - 奖励触发/确认/拒绝/发放
- `rule.service.js` + `rule-evaluator.service.js` - 规则 CRUD + 通用条件判定

### REST API（28 端点）
- `GET/POST /api/referral/codes/me|validate|user/:id`
- `GET/POST/PUT/DELETE /api/referral/expert-configs`
- `GET/POST /api/referral/records/me|me/summary|me/:id|/|:id|by-code|urge|recommend-again|invalidate`
- `GET/POST /api/referral/rewards/me|me/summary|/|:id/confirm|:id/reject|:id/issue|trigger`
- `GET/POST/PUT /api/referral/rules/|:id|:id/toggle`

### 后台调度（node-cron 嵌入主进程）
- `0 * * * *` - 保护期过期扫描
- `*/15 * * * *` - 候选人入职 → 奖励触发
- `0 0 * * *` - 内推码失效扫描（事件驱动，此处仅占位）

### 文档
- Spec: `docs/superpowers/specs/2026-06-04-referral-portal-phase1-design.md`
- Plan: `docs/superpowers/plans/2026-06-04-referral-portal-phase1.md`

### 测试
```bash
npm test                # 单元测试
npm run test:coverage   # 覆盖率
```

### 迁移
```bash
npx prisma migrate dev   # 应用迁移
npm run db:seed          # 种子数据
```
