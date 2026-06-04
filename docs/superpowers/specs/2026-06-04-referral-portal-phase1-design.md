# 内推门户 Phase 1 - 数据模型 + 核心服务 设计文档

> 本文档是内推门户 PRD 的 **Phase 1** 实现设计。完整 PRD 范围过大（8-12 周），本文档只覆盖**地基层**：数据模型、状态机、规则引擎、REST API 骨架、后台调度。其他 Phase（员工端 UI、管理端 UI、候选人门户、企微扫码登录、消息通知模板）单独走 spec → plan 流程。

## 1. 目标与范围

### 1.1 业务目标（一句话）
为后续 Phase 提供可依赖的内推核心服务：内推码、推荐记录、保护期状态机、奖励触发、规则引擎。

### 1.2 Phase 1 包含
- ✅ Prisma schema 增 6 张新表 + Resume/Application 字段调整
- ✅ Prisma 迁移脚本（开发 + 生产）
- ✅ XState 状态机：内推记录 5 态、奖励 5 态、内推码 2 态
- ✅ 业务服务层：内推码生成、推荐创建、有效性判定、奖励计算
- ✅ REST API 骨架（不含 UI），覆盖 CRUD + 关键业务动作
- ✅ 后台调度：保护期过期扫描、状态自动转换、奖励触发
- ✅ 规则引擎：配置驱动的成员限制判定
- ✅ 单元测试（状态机、规则、奖励计算）+ 集成测试（API）
- ✅ 种子数据：1 个内推团队、2 条规则、10 个员工内推码

### 1.3 Phase 1 **不**包含（明确边界）
- ❌ 任何 UI / 页面（员工端、管理端、候选人门户）
- ❌ 企微扫码登录（Phase 7，假定用现有 JWT）
- ❌ 二维码/链接分享落地页（Phase 3）
- ❌ 消息通知模板填充（Phase 7，事件钩子留好接口）
- ❌ 收藏/催办/再次推荐 业务动作（Phase 3-4，仅留 service 占位）

### 1.4 关键决策记录
| 决策点 | 选择 | 理由 |
|--------|------|------|
| 状态机实现 | **XState v5** | 状态多、转换多、需可视化与单测保障 |
| 旧字段处理 | **新建独立 ReferralRecord 表，删除 Resume.referralUserId 和 Application.referralUserId** | 旧字段只有 1 个 userId，缺保护期/状态/专家；关联表更可扩展 |
| 奖励触发 | **配置化触发点**（`ReferralRule.triggerStage` = ONBOARDED / PROBATION_PASSED） | PRD 4.2.4.3.4 明确支持"按条件选择" |
| 后台任务 | **node-cron 嵌入主进程** | 单机够用、零额外依赖 |
| 规则引擎 | **JSON conditions 存储 + 通用 evaluator** | MEMBER_RESTRICTION 和 REWARD 复用一张表，灵活支持"任意/全部"逻辑 |
| ID 策略 | **uuid()**（与现有 schema 一致） | 风格统一 |
| 多租户 | **不支持**（单公司） | 现有系统无 tenant 概念，YAGNI |

---

## 2. 数据模型

### 2.1 6 张新表

#### 2.1.1 `referral_codes` 内推码
```prisma
model ReferralCode {
  id            String   @id @default(uuid())
  code          String   @unique @db.VarChar(16)  // 6位 字母大小写+数字
  userId        String   @unique
  status        String   @default("ACTIVE") @db.VarChar(32)  // ACTIVE | INVALID
  invalidReason String?  @db.VarChar(64)  // LEAVER | EXPERT_LEAVER | EXPERT_CHANGED | NO_EXPERT
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt

  user    User              @relation("UserReferralCode", fields: [userId], references: [id], onDelete: Cascade)
  records ReferralRecord[]
  configs ReferralExpertConfig[]

  @@index([status])
  @@map("referral_codes")
}
```

#### 2.1.2 `referral_expert_configs` 内推人对接配置
```prisma
model ReferralExpertConfig {
  id        String   @id @default(uuid())
  userId    String
  teamId    String
  expertId  String
  isPrimary Boolean  @default(true)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  user   User       @relation("UserExpertConfigs", fields: [userId], references: [id], onDelete: Cascade)
  team   Department @relation("TeamExpertConfigs", fields: [teamId], references: [id], onDelete: Restrict)
  expert User       @relation("ExpertConfigs", fields: [expertId], references: [id], onDelete: Restrict)

  @@unique([userId, teamId, expertId])
  @@index([userId])
  @@index([expertId])
  @@index([teamId])
  @@map("referral_expert_configs")
}
```

#### 2.1.3 `referral_records` 内推记录（核心表）
```prisma
model ReferralRecord {
  id              String   @id @default(uuid())
  referrerId      String                                  // 内推人
  referrerCode    String   @db.VarChar(16)                // 冗余：使用的内推码
  candidateId     String
  resumeId        String?                                 // 内推人代填时为新简历；候选人用码投递时为 null
  positionId      String
  expertId        String                                  // 冗余：方便列表查询
  referralType    String   @db.VarChar(32)                // REFERRER_HELP | CANDIDATE_USED_CODE
  referralStatus  String   @default("NORMAL") @db.VarChar(32)  // NORMAL | PROTECTING | EXPIRED | COMPLETED | INVALID
  protectionEndAt DateTime?
  invalidReason   String?  @db.VarChar(64)                // OVER_3_TIMES | OVER_15_DAYS | NOT_QUALIFIED
  recommendedAt   DateTime @default(now())
  statusChangedAt DateTime @default(now())
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt

  referrer  User        @relation("ReferrerRecords", fields: [referrerId], references: [id], onDelete: Restrict)
  candidate Candidate   @relation("CandidateReferrals", fields: [candidateId], references: [id], onDelete: Cascade)
  resume    Resume?     @relation("ResumeReferrals", fields: [resumeId], references: [id], onDelete: SetNull)
  position  Position    @relation("PositionReferrals", fields: [positionId], references: [id], onDelete: Restrict)
  expert    User        @relation("ExpertRecords", fields: [expertId], references: [id], onDelete: Restrict)
  applicationId String?      @unique                       // 关联到 Application（1:1）
  application   Application? @relation("ApplicationReferrals", fields: [applicationId], references: [id], onDelete: SetNull)
  rewards   ReferralReward[]

  // 同一候选人对同一职位在同一内推人下的去重（PRD：保护期内操作不产生新记录）
  @@unique([candidateId, positionId, referrerId], name: "uniq_candidate_position_referrer")
  @@index([referrerId, referralStatus])
  @@index([expertId, referralStatus])
  @@index([positionId])
  @@index([protectionEndAt])
  @@index([referralStatus, statusChangedAt])
  @@map("referral_records")
}
```

#### 2.1.4 `referral_rewards` 内推奖励
```prisma
model ReferralReward {
  id           String   @id @default(uuid())
  recordId     String
  candidateId  String
  amount       Decimal  @db.Decimal(10, 2)
  reason       String   @db.VarChar(64)              // 触发文案
  triggerStage String   @db.VarChar(32)              // ONBOARDED | PROBATION_PASSED
  status       String   @default("PENDING") @db.VarChar(32)  // PENDING | TO_CONFIRM | CONFIRMED | REJECTED | ISSUED
  ruleId       String?
  triggeredAt  DateTime @default(now())
  confirmedBy  String?
  confirmedAt  DateTime?
  issuedAt     DateTime?
  rejectedAt   DateTime?
  rejectReason String?  @db.VarChar(255)
  createdAt    DateTime @default(now())
  updatedAt    DateTime @updatedAt

  record    ReferralRecord @relation(fields: [recordId], references: [id], onDelete: Cascade)
  candidate Candidate      @relation("CandidateReferralRewards", fields: [candidateId], references: [id], onDelete: Cascade)
  rule      ReferralRule?  @relation(fields: [ruleId], references: [id], onDelete: SetNull)
  confirmer User?          @relation("RewardConfirmer", fields: [confirmedBy], references: [id], onDelete: SetNull)

  @@index([recordId])
  @@index([status])
  @@index([triggeredAt])
  @@index([candidateId])
  @@map("referral_rewards")
}
```

#### 2.1.5 `referral_rules` 内推规则（成员限制 + 奖励 合并）
```prisma
model ReferralRule {
  id            String   @id @default(uuid())
  name          String   @unique @db.VarChar(64)
  ruleType      String   @db.VarChar(32)             // MEMBER_RESTRICTION | REWARD
  positionLevel String?  @db.VarChar(32)             // 仅 REWARD 用
  triggerStage  String?  @db.VarChar(32)             // 仅 REWARD 用：ONBOARDED | PROBATION_PASSED
  conditions    Json                                 // 通用结构：{ logic, conditions: [{key, op, value}] }
  amount        Decimal? @db.Decimal(10, 2)          // 仅 REWARD 用
  status        String   @default("ACTIVE") @db.VarChar(32)
  createdBy     String
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt

  creator User             @relation("RuleCreator", fields: [createdBy], references: [id], onDelete: Restrict)
  rewards ReferralReward[]

  @@index([ruleType, status])
  @@map("referral_rules")
}
```

#### 2.1.6 `referral_teams` 内推团队（关联 Department）
```prisma
model ReferralTeam {
  id          String   @id @default(uuid())
  teamId      String   @unique                       // 对应 Department.id
  description String?  @db.Text
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt

  team Department @relation("DepartmentReferralTeam", fields: [teamId], references: [id], onDelete: Cascade)

  @@map("referral_teams")
}
```

### 2.2 现有表调整

#### `Resume` 表
```diff
 model Resume {
   ...
-  // 暂不调整 Resume 表本身：原 channelSource/channelLink 保留
-  // ReferralRecord.resumeId 仍是外键（如 PRD 4.1.2.4.2 候选人填码时 resumeId 为 null）
+  // 反向关系字段在下方 "Resume 表追加反向关系" 声明
   ...
 }
```

#### `Application` 表
```diff
 model Application {
   ...
-  referralUserId String?
+  // 改用关联 ReferralRecord（由 ReferralRecord.applicationId 反向关联）
+  // referralRecord 关系字段在 ReferralRecord 模型中已定义（applicationId @unique + application @relation）
+  // 不在此处再声明 FK
   ...
 }
```

#### `User` 表追加反向关系
```diff
 model User {
   ...
+  referralCode         ReferralCode?           @relation("UserReferralCode")
+  referralExpertConfigs ReferralExpertConfig[] @relation("UserExpertConfigs")
+  expertConfigs        ReferralExpertConfig[]  @relation("ExpertConfigs")
+  referrerRecords      ReferralRecord[]        @relation("ReferrerRecords")
+  expertRecords        ReferralRecord[]        @relation("ExpertRecords")
+  rewardConfirmations  ReferralReward[]        @relation("RewardConfirmer")
+  createdRules         ReferralRule[]          @relation("RuleCreator")
   ...
 }
```

#### `Department` 表追加反向关系
```diff
 model Department {
   ...
+  expertConfigs     ReferralExpertConfig[] @relation("TeamExpertConfigs")
+  referralTeam      ReferralTeam?          @relation("DepartmentReferralTeam")
   ...
 }
```

#### `Candidate` 表追加反向关系
```diff
 model Candidate {
   ...
+  referralRecords ReferralRecord[] @relation("CandidateReferrals")
+  referralRewards ReferralReward[] @relation("CandidateReferralRewards")
   ...
 }
```

#### `Position` 表追加反向关系
```diff
 model Position {
   ...
+  referralRecords ReferralRecord[] @relation("PositionReferrals")
   ...
 }
```

#### `Resume` 表追加反向关系（仅一处：关联 ReferralRecord）
```diff
 model Resume {
   ...
+  referralRecords ReferralRecord[] @relation("ResumeReferrals")
   ...
 }
```

#### `Application` 表追加反向关系（仅一处：关联 ReferralRecord）
```diff
 model Application {
   ...
+  referralRecord ReferralRecord? @relation("ApplicationReferrals")   // inverse side：ReferralRecord.applicationId 是 owning
   ...
 }
```

### 2.3 字段约束关键说明
- `ReferralRecord.@@unique([candidateId, positionId, referrerId])` - PRD 第 4.1.2.4.2 "同一候选人的同一内推行为计为一条"
- `ReferralCode.code @db.VarChar(16)` - 6位字符 + 预留扩展
- `ReferralRecord.protectionEndAt` - 保护期截止时间，用于 cron 扫描
- 冗余字段 `referrerCode`、`expertId` - 避免列表查询多 join

---

## 3. 状态机（XState v5）

### 3.1 内推记录状态机 `referralRecordMachine`

```
                      ┌──────────────┐
                      │   NORMAL     │  (有效内推，候选人简历审核中)
                      └──────┬───────┘
                             │ 简历进入流程（HRBP筛选/用人经理筛选/...）
                             ▼
                ┌────────────────────────┐
       ┌───────►│      PROTECTING        │  (有效内推，简历不在流程中但还在保护期)
       │        └─┬──────────────────┬───┘
       │          │                  │ 入职归档
       │   简历回退│                  ▼
       │   流程    │         ┌──────────────┐
       │          │         │  COMPLETED   │  (达成所有奖励要求)
       │          │         └──────────────┘
       │          │ 保护期过期 & 未在流程
       │          ▼
       │   ┌──────────────┐
       │   │   EXPIRED    │  (保护期结束)
       │   └──────────────┘
       │
       └──── (任何状态) ─── 判定为无效 ──►  ┌──────────────┐
                                           │   INVALID    │  (无效内推，走普通流程)
                                           └──────────────┘
```

**事件**：
- `STAGE_CHANGED` { from, to } - 候选人流程阶段变化
- `PROTECTION_EXPIRED` - 保护期到期（cron 触发）
- `CANDIDATE_ONBOARDED` - 候选人入职归档
- `REWARD_COMPLETED` - 所有奖励已发放
- `MARK_INVALID` { reason } - 标为无效
- `CANDIDATE_LEFT` - 候选人离职（已入职后）

**guards**：
- `isProtectionActive` - `protectionEndAt > now()`
- `isInProcess` - 当前 stage 在 HRBP筛选/用人经理筛选/.../待入职列表中
- `allRewardsIssued` - 所有关联奖励 status = ISSUED

**actions**：
- 更新 `referralStatus`、`statusChangedAt`
- 必要时更新 `protectionEndAt`

**实现位置**：`backend/src/referral/machines/referralRecord.machine.js`

### 3.2 奖励状态机 `referralRewardMachine`

```
PENDING ──trigger──► TO_CONFIRM ──hrbp confirm──► CONFIRMED ──issue──► ISSUED
                          │
                          └──hrbp reject──► REJECTED
```

**事件**：
- `TRIGGER` - 规则触发（cron 监听到候选人 ONBOARDED / PROBATION_PASSED）
- `CONFIRM` - HRBP 确认
- `REJECT` { reason } - HRBP 拒绝
- `ISSUE` - 财务发放

### 3.3 内推码状态机 `referralCodeMachine`

```
ACTIVE ──invalidate──► INVALID
INVALID ──reactivate──► ACTIVE
```

**事件**：
- `INVALIDATE` { reason: LEAVER | EXPERT_LEAVER | EXPERT_CHANGED | NO_EXPERT }
- `REACTIVATE`

---

## 4. 业务服务层

### 4.1 模块结构
```
backend/src/referral/
├── machines/
│   ├── referralRecord.machine.js     # XState 机器定义
│   ├── referralReward.machine.js
│   └── referralCode.machine.js
├── services/
│   ├── code.service.js               # 内推码生成/失效
│   ├── record.service.js             # 推荐创建/查询/状态推进
│   ├── reward.service.js             # 奖励触发/状态推进
│   ├── rule-evaluator.service.js     # 规则条件判定
│   └── referral.service.js           # 业务编排 facade
├── routes/
│   ├── codes.routes.js               # /api/referral/codes
│   ├── records.routes.js             # /api/referral/records
│   ├── rewards.routes.js             # /api/referral/rewards
│   ├── rules.routes.js               # /api/referral/rules
│   └── expert-configs.routes.js      # /api/referral/expert-configs
├── scheduler/
│   └── referral.scheduler.js         # node-cron 任务
├── events/
│   └── referral.events.js            # 事件钩子（Phase 7 接入企微）
├── validators/
│   └── referral.validator.js         # express-validator 规则
└── index.js                          # 模块入口（导出 mountRoutes）
```

### 4.2 关键 service 接口

#### `code.service.js`
```javascript
// 生成 6 位 字母大小写+数字 内推码（去重）
async generateCode(): Promise<string>
// 为新员工创建内推码
async createCodeForUser(userId): Promise<ReferralCode>
// 失效处理
async invalidateCode(codeId, reason: 'LEAVER'|'EXPERT_LEAVER'|'EXPERT_CHANGED'|'NO_EXPERT'): Promise<void>
// 校验有效性（候选人填码时）
async validateCode(code: string): Promise<{ valid: boolean, reason?: string, code?: ReferralCode }>
// 失效时刷新：扫描所有用户的内推码，状态变化时同步
async refreshCodesForEvent(event: { type: 'USER_LEAVER'|'EXPERT_CHANGED'|'EXPERT_LEAVER', userId? }): Promise<void>
```

#### `record.service.js`
```javascript
// 创建推荐记录（含有效性判定 + 去重）
async createReferral({ referrerId, candidateId, positionId, expertId?, resumeId?, referralType }): Promise<{ record, created, invalidReason? }>
// 推进状态（XState 事件）
async transitionRecord(recordId, event): Promise<ReferralRecord>
// 候选人阶段变化时批量更新
async handleCandidateStageChange(candidateId, fromStage, toStage): Promise<void>
// 查询我的内推列表
async listForReferrer(referrerId, { status?, positionId?, page, pageSize }): Promise<{ list, total }>
// 查询内推管理列表（HR/HRBP/招聘专家）
async listForManagement({ role, userId, filters }): Promise<{ list, total }>
```

#### `reward.service.js`
```javascript
// 触发奖励（候选人在 triggerStage 时调用）
async triggerRewardsForCandidate(candidateId, stage): Promise<ReferralReward[]>
// HRBP 确认/拒绝
async confirmReward(rewardId, hrbpId): Promise<ReferralReward>
async rejectReward(rewardId, hrbpId, reason): Promise<ReferralReward>
// 标记已发放
async markIssued(rewardId): Promise<ReferralReward>
// 查询我的奖励
async listRewardsForReferrer(referrerId, filters): Promise<{ list, total, summary }>
```

#### `rule-evaluator.service.js`
```javascript
// 通用条件判定：{ logic: 'ANY'|'ALL', conditions: [{key, op, value}] }
// 支持 key: 'isManager' | 'positionSeries' | 'demandStakeholder' | 'internalPosition'
// 支持 op: 'EQ' | 'IN' | 'NOT_IN' | 'CONTAINS' | 'NOT_CONTAINS' | 'GT' | 'LT'
async evaluate(rule: ReferralRule, context: object): Promise<boolean>
// 查询当前生效的成员限制规则
async getActiveMemberRestrictions(): Promise<ReferralRule[]>
// 查询当前生效的某岗位层级奖励规则
async getActiveRewardRule(positionLevel, stage): Promise<ReferralRule | null>
```

### 4.3 业务编排 `referral.service.js`
```javascript
// 候选人填写内推码投递时的总入口
async handleCandidateSubmission({ code, candidateId, positionId, resumeId }): Promise<{ accepted: boolean, record?: ReferralRecord, message: string }>
```

---

## 5. REST API 设计

### 5.1 通用规范
- 路径前缀：`/api/referral/*`
- 认证：所有路由 `authMiddleware`（Phase 1 用现有 JWT，Phase 7 替换为企微扫码）
- 响应包络：与现有代码一致 `{ success: boolean, data?, message? }`
- 错误处理：走全局 `errorHandler` 中间件
- 权限：基于 `req.user.roleType` 和 `req.user.id` 校验

### 5.2 端点列表

#### 5.2.1 内推码 `/api/referral/codes`
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/me` | 登录 | 获取我的内推码 + 状态 |
| GET | `/validate?code=XXXXXX` | 公开（候选人门户用） | 校验码有效性 |
| GET | `/user/:userId` | 超管/HRBP | 查询某员工的内推码 |

#### 5.2.2 对接配置 `/api/referral/expert-configs`
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/me` | 登录 | 我的对接配置列表 |
| POST | `/` | 登录 | 新增对接（PRD 4.1.2.4.1 双向联动） |
| PUT | `/:id` | 登录（仅自己） | 编辑 |
| DELETE | `/:id` | 登录（仅自己） | 删除 |

#### 5.2.3 内推记录 `/api/referral/records`
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/me` | 登录 | 我的内推（4.1.2.4.2） |
| GET | `/me/summary` | 登录 | 顶部统计：推荐有效/入职/转正/待确认奖励/已确认/已发放 |
| GET | `/me/:id` | 登录（仅自己） | 记录详情 + 候选人原始简历 |
| GET | `/` | 超管/HRBP/招聘专家 | 管理列表（4.1.4.4.1） |
| GET | `/:id` | 超管/HRBP/招聘专家 | 管理详情 |
| POST | `/` | 登录 | 创建推荐（内推人代填） |
| POST | `/by-code` | 公开 | 候选人填码投递（创建 ReferralRecord） |
| POST | `/:id/invalidate` | 超管/HRBP | 标为无效 |

> 业务动作（催办/再次推荐/邀请推荐）**接口留 placeholder**，返回 `501 Not Implemented`，等 Phase 3-4 实施。

#### 5.2.4 奖励 `/api/referral/rewards`
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/me` | 登录 | 我的奖励列表 |
| GET | `/me/summary` | 登录 | 奖励金额统计 |
| GET | `/` | 超管/HRBP | 管理列表 |
| POST | `/:id/confirm` | 超管/HRBP | HRBP 确认 |
| POST | `/:id/reject` | 超管/HRBP | HRBP 拒绝（带 reason） |
| POST | `/:id/issue` | 超管/HRBP | 标记已发放 |
| POST | `/trigger` | 超管 | 手动触发（测试/补发） |

#### 5.2.5 规则 `/api/referral/rules`
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/` | 超管 | 列表（type/status 筛选） |
| GET | `/:id` | 超管 | 详情 |
| POST | `/` | 超管 | 新增（同时校验 conditions JSON 合法性） |
| PUT | `/:id` | 超管 | 编辑（仅 ACTIVE 状态可改 conditions） |
| POST | `/:id/toggle` | 超管 | 启/停 |

### 5.3 路由挂载
在 `backend/src/app.js` 中追加：
```javascript
import referralRoutes from './referral/index.js';
app.use('/api/referral', authMiddleware, referralRoutes);
```

---

## 6. 后台调度（node-cron）

### 6.1 任务列表

| Cron 表达式 | 任务 | 说明 |
|-------------|------|------|
| `0 * * * *` | 保护期扫描 | 找出 `protectionEndAt <= now AND referralStatus IN ('NORMAL','PROTECTING')` 的记录，推进状态 |
| `*/15 * * * *` | 奖励触发 | 找出 stage=ONBOARDED 或 PROBATION_PASSED 但无对应奖励的 candidate，触发 |
| `0 0 * * *` | 内推码失效扫描 | 扫描员工离职/专家变更，调用 `refreshCodesForEvent` |
| `0 2 * * *` | 重复内推记录检测 | 同候选人-职位-内推人重复时合并（防御性，理论上 unique 约束已防） |

### 6.2 实现细节
- 文件：`backend/src/referral/scheduler/referral.scheduler.js`
- 在 `app.js` 启动时调用 `startReferralScheduler()`
- 优雅关闭：`process.on('SIGTERM', stopReferralScheduler)`
- 任务执行日志：标准 `console.log('[referral-scheduler] task=... duration=...')`
- 失败重试：单任务 try/catch 隔离，单个失败不影响其他任务

---

## 7. 规则引擎

### 7.1 规则数据结构
```typescript
type RuleCondition = {
  key: 'isManager' | 'positionSeries' | 'demandStakeholder' | 'internalPosition'
       | 'referralCount' | 'referralIntervalDays' | 'positionLevel';
  op: 'EQ' | 'IN' | 'NOT_IN' | 'CONTAINS' | 'NOT_CONTAINS' | 'GT' | 'LT' | 'GTE' | 'LTE';
  value: string | number | string[] | number[];
};

type Rule = {
  logic: 'ANY' | 'ALL';  // 任意条件满足 / 全部条件满足
  conditions: RuleCondition[];
};
```

### 7.2 判定示例
**MEMBER_RESTRICTION**（是否经营者）：
```json
{
  "logic": "ANY",
  "conditions": [
    { "key": "isManager", "op": "EQ", "value": "YES" }
  ]
}
```

**REWARD**（按岗位层级 + 阶段）：
```json
{
  "logic": "ALL",
  "conditions": [
    { "key": "positionLevel", "op": "EQ", "value": "P5" },
    { "key": "referralCount", "op": "GTE", "value": 1 }
  ],
  "amount": 3000.00,
  "triggerStage": "ONBOARDED"
}
```

### 7.3 Context 输入
```typescript
type EvalContext = {
  user: User;                              // 内推人
  position: Position;                      // 推荐职位
  candidate: Candidate;                    // 候选人
  referralHistory: ReferralRecord[];       // 内推人历史推荐（含本次）
  daysSinceLastReferral?: number;          // 距上次推荐天数
};
```

### 7.4 操作符实现要点
- `IN` / `NOT_IN`: 数组包含/不包含
- `CONTAINS` / `NOT_CONTAINS`: 字符串包含（positionSeries 用）
- `GT` / `LT` / `GTE` / `LTE`: 数值比较
- 不识别的 key/op 抛 `RuleEvaluationError`（防配置错误）

---

## 8. 迁移与种子

### 8.1 迁移步骤
1. `npx prisma migrate dev --name add_referral_phase1` 生成迁移
2. 手动追加到迁移 SQL 中：
   - `ALTER TABLE resumes DROP COLUMN referral_user_id;` （如存在）
   - `ALTER TABLE applications DROP COLUMN referral_user_id;` （如存在）
   - 注：如生产已有数据，先写 backfill 脚本（从 `referral_user_id` 关联出 `referralRecordId`）

### 8.2 种子数据
`prisma/seed.referral.js` 包含：
- 1 个 ReferralTeam（关联"技术中心"部门）
- 2 条 ReferralRule：1 条 MEMBER_RESTRICTION（是否经营者=否），1 条 REWARD（P5 入职 3000 元）
- 10 个员工 ReferralCode（随机 6 位）
- 5 条 ReferralRecord（覆盖 NORMAL/PROTECTING/EXPIRED/INVALID/COMPLETED 各一）
- 2 条 ReferralReward（1 PENDING + 1 ISSUED）

### 8.3 数据回填（生产环境）
如生产已有数据：
```sql
-- 1. 创建 ReferralCode（每个有 referral_user_id 的 user）
INSERT INTO referral_codes (id, code, user_id, status, created_at, updated_at)
SELECT UUID(), SUBSTRING(MD5(RAND()), 1, 6), referral_user_id, 'ACTIVE', NOW(), NOW()
FROM (SELECT DISTINCT referral_user_id FROM resumes WHERE referral_user_id IS NOT NULL) t;

-- 2. 创建 ReferralRecord
INSERT INTO referral_records (id, referrer_id, referrer_code, candidate_id, resume_id, position_id, expert_id, referral_type, referral_status, created_at, updated_at)
SELECT UUID(), r.referral_user_id, rc.code, r.candidate_id, r.id, r.position_id,
       (SELECT id FROM users WHERE department_id = r.position_id LIMIT 1), -- 占位：实际由 service 设置
       'REFERRER_HELP', 'NORMAL', r.created_at, r.updated_at
FROM resumes r JOIN referral_codes rc ON rc.user_id = r.referral_user_id
WHERE r.referral_user_id IS NOT NULL;

-- 3. 删除旧字段
ALTER TABLE resumes DROP COLUMN referral_user_id;
ALTER TABLE applications DROP COLUMN referral_user_id;
```

---

## 9. 测试策略

### 9.1 单元测试（jest）
- `machines/referralRecord.machine.test.js` - 状态机所有合法/非法转换
- `machines/referralReward.machine.test.js` - 奖励状态机
- `services/rule-evaluator.test.js` - 每种 op、每种 logic 组合
- `services/code.service.test.js` - 内推码生成唯一性、6位字符
- `services/reward.service.test.js` - 触发、确认、拒绝、发放

### 9.2 集成测试（jest + supertest）
- `routes/codes.test.js` - GET /me, GET /validate
- `routes/records.test.js` - POST /, POST /by-code, 重复创建返回 existing
- `routes/rewards.test.js` - 触发 → 确认 → 发放 全链路
- `routes/rules.test.js` - CRUD + 启停

### 9.3 测试覆盖目标
- 业务 service 覆盖率 ≥ 80%
- 状态机覆盖所有 transition 路径（含非法转换抛错）
- API 集成测试：每个端点至少 1 正例 + 1 反例

---

## 10. 边界与开放问题

### 10.1 边界确认
- Phase 1 不实现 UI 页面，所有 API 通过 Postman/curl 验证
- Phase 1 不接入企微通知，但 service 中保留 `emitEvent()` 调用
- Phase 1 不实现收藏/催办/再次推荐/邀请推荐 业务动作的 service 方法（占位 TODO）

### 10.2 开放问题（需用户确认）
1. **Q**: 内推码生成失败的兜底（6 位字符空间 62^6 ≈ 568 亿，但极端碰撞）？
   **建议**: 10 次重试，仍冲突则降级为 cuid 后缀

2. **Q**: 候选人阶段变化的钩子从哪里注入？
   **建议**: 监听 Application.currentStageName 变化，PR 间由候选人/简历服务调用 record.service.handleCandidateStageChange

3. **Q**: "保护期内的转推"具体行为？
   **建议**: 保护期内同候选人转推其他职位，**新** ReferralRecord（不同 positionId），原记录 status 不变；新记录走"保护期内转推"逻辑标记 referralType=REFERRER_HELP

4. **Q**: 奖励触发后候选人离职如何处理？
   **建议**: 走 `CandidateLeft` 事件 → 候选中奖励 REJECTED，已发放的不追回

---

## 11. 关键文件清单

### 新增
- `backend/prisma/schema.prisma` - 追加 6 个 model + 调整 3 个
- `backend/prisma/seed.referral.js` - 种子数据
- `backend/src/referral/machines/*.js` - 3 个 XState 机器
- `backend/src/referral/services/*.js` - 5 个 service
- `backend/src/referral/routes/*.js` - 5 个路由
- `backend/src/referral/scheduler/referral.scheduler.js`
- `backend/src/referral/events/referral.events.js`
- `backend/src/referral/validators/referral.validator.js`
- `backend/src/referral/index.js`
- `backend/src/referral/__tests__/*.test.js` - 测试
- `backend/package.json` - 加依赖 `xstate@^5`, `node-cron@^3`, `nanoid@^5`（生成内推码）

### 修改
- `backend/src/app.js` - 挂载 `/api/referral`
- `backend/prisma/schema.prisma` - User/Department/Resume/Application 增反向关系

---

## 12. 实施检查清单（用于 plan 阶段展开）

- [ ] Prisma schema 编写 + 迁移
- [ ] 种子脚本
- [ ] XState 机器 + 单元测试
- [ ] rule-evaluator + 单元测试
- [ ] code.service + 单元测试
- [ ] record.service + 单元测试
- [ ] reward.service + 单元测试
- [ ] referral.service 编排
- [ ] 5 个 routes + 集成测试
- [ ] scheduler 实现
- [ ] events 钩子实现
- [ ] app.js 挂载
- [ ] README 更新 + API 文档
