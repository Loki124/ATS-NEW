# Todo #1: recruitment-auto-advance 接入 — 设计

> **Date**: 2026-06-14
> **Type**: Feature completion (G38 #8 关键路径)
> **Effort**: 1-2d

---

## 0. 背景

`backend/src/services/recruitment-auto-advance.service.js` 已有 ~80% 实现,但 **3 个关键缺口**:

1. **`checkDoubleASkip` 是 stub**:返回 `pass: false, reason: '需要等 ApplicationStageRecord 表建好'`
2. **`ApplicationStageRecord` 表不在 schema** — service 注释里反复提到
3. **service 是 dead code**:无任何 caller,无 cron scheduler
4. **没有自动流转 cron** — Plan K 的"每 5 分钟扫描"承诺没落地

PRD G38 #11 双 A / N+2 免筛选的核心价值未交付。

## 1. 目标

- 候选人阶段流转记录可追踪(`ApplicationStageRecord` 表 + schema + migration)
- `checkDoubleASkip` 真实实现(同部门 2 评估人意见一致 → 自动标记)
- 自动流转 cron 每 5 分钟扫一次,按 `StageRule.autoAdvanceType` 推进
- 手动阶段转移也走同一个 service(避免双路径)
- 100% jest 覆盖(状态机 + cron)

## 2. 范围

### 包含
- ✅ 新表 `ApplicationStageRecord` (Prisma schema + migration)
- ✅ `recruitment-auto-advance.service.js` 完整实现:
  - `checkN2Skip` 已存在,小修(用真实 ApplicationStageRecord 校验)
  - `checkDoubleASkip` 重写真实实现
  - `shouldAutoAdvance` 已存在,小修(读真实记录)
- ✅ 新 cron `recruitment-auto-advance.scheduler.js` (每 5 分钟)
- ✅ `app.js` 启动时 wire scheduler
- ✅ 新 API 端点 `POST /api/recruitment/auto-advance/check` (手动触发)
- ✅ 单测 + 集成测

### 不包含
- ❌ UI 改动(留到下个 plan)
- ❌ Webhook / 通知(用现有的 NotificationTemplate)
- ❌ 候选人阶段历史 UI

## 3. 数据模型

### `application_stage_records` 表

```prisma
model ApplicationStageRecord {
  id              String   @id @default(uuid())

  // 关联
  applicationId  String
  candidateId     String
  processId       String
  linkId          String   // process_stage_links.id
  stageId         String   // recruitment_stages.id

  // 流转数据
  fromStatus      String?  // 进入时的阶段状态 (初评进入 / 用人经理筛 进入)
  toStatus        String   // 流转结果 (PASS / FAIL / TIMEOUT / AUTO_ADVANCE / MANUAL)
  decision        String?  // ALL_PASS / PARTIAL_PASS / ALL_FAIL / N+2_SKIP / DOUBLE_A_SKIP

  // 时间
  enteredAt       DateTime?  // 进入这个 link 的时间
  exitedAt        DateTime @default(now())

  // 谁决定
  decidedBy       String?  // userId (handler) 或 'SYSTEM'
  decisionReason  String?  // 决策原因 / 备注

  // 元数据
  autoAdvanced    Boolean  @default(false)  // 是否自动流转
  createdAt       DateTime @default(now())

  application Application @relation(fields: [applicationId], references: [id], onDelete: Cascade)
  link        ProcessStageLink @relation(fields: [linkId], references: [id], onDelete: Cascade)
  stage       RecruitmentStage @relation(fields: [stageId], references: [id], onDelete: Cascade)
  decider     User? @relation("StageRecordDecider", fields: [decidedBy], references: [id], onDelete: SetNull)

  @@index([applicationId, exitedAt])
  @@index([linkId, exitedAt])
  @@index([candidateId, exitedAt])
  @@index([toStatus])
  @@map("application_stage_records")
}
```

(9 个核心字段 + 4 索引,catch 95% 业务查询)

### 关联改动
- `Application` model 加 `stageRecords ApplicationStageRecord[]`
- `ProcessStageLink` model 加 `stageRecords ApplicationStageRecord[]`
- `RecruitmentStage` model 加 `stageRecords ApplicationStageRecord[]`
- `User` model 加 `decidedStageRecords ApplicationStageRecord[] @relation("StageRecordDecider")`

## 4. Service 实现

### `checkDoubleASkip` 真实实现

```js
export async function checkDoubleASkip(candidateId) {
  // 1. 找候选人最近一次用人经理评估阶段记录
  const recentRecord = await prisma.applicationStageRecord.findFirst({
    where: {
      candidateId,
      stage: { stageType: 'EVALUATE' },  // 评估型
    },
    orderBy: { exitedAt: 'desc' },
    include: { stage: true, decider: { include: { department: true } } },
  });

  if (!recentRecord) {
    return { pass: false, decision: null, reason: '无最近评估记录' };
  }

  // 2. 查该阶段的所有评估人
  const evaluators = await prisma.applicationStageRecord.findMany({
    where: {
      applicationId: recentRecord.applicationId,
      linkId: recentRecord.linkId,
      toStatus: { in: ['PASS', 'FAIL', 'ALL_PASS', 'ALL_FAIL'] },
      decidedBy: { not: null },
    },
    include: { decider: { include: { department: true } } },
  });

  // 3. 必须正好 2 人
  if (evaluators.length !== 2) {
    return { pass: false, decision: null, reason: `评估人 ${evaluators.length} 人(需 2 人)` };
  }

  // 4. 同部门 + 是部门负责人
  const [e1, e2] = evaluators;
  if (e1.decider?.departmentId !== e2.decider?.departmentId) {
    return { pass: false, decision: null, reason: '非同一部门' };
  }
  const deptName = e1.decider?.department?.name;
  if (DOUBLE_A_EXCLUDED_DEPARTMENTS.includes(deptName)) {
    return { pass: false, decision: null, reason: `${deptName} 不在双 A 开放名单` };
  }

  // 5. 评估结果一致
  const allPass = evaluators.every(e => e.toStatus === 'PASS' || e.toStatus === 'ALL_PASS');
  const allFail = evaluators.every(e => e.toStatus === 'FAIL' || e.toStatus === 'ALL_FAIL');
  if (!allPass && !allFail) {
    return { pass: false, decision: null, reason: '评估结果不一致' };
  }

  return {
    pass: true,
    decision: allPass ? 'PASS' : 'FAIL',
    reason: `${deptName} 双A 意见一致 (${allPass ? '通过' : '不通过'})`,
  };
}
```

### `checkN2Skip` 微调(用真实记录)

原版基于 `candidate.recommenderName` 简化判断。改进:查候选人最新 Application 是否被标记为 N+2 推荐(新增 `Application.isN2Recommended` 字段,或复用 recommenderId 非空)。

为最小化 scope,**保持现有 `recommenderName` 判定**(已可用),但增加注释说明可在未来升级到 `Application.isN2Recommended`。

### `shouldAutoAdvance` 微调

读 `ApplicationStageRecord` 校验时间(`enteredAt` + `autoAdvanceDays`),cron 才能决定 DELAYED 流转时机。

## 5. Cron Scheduler

`backend/src/scheduler/recruitment-auto-advance.scheduler.js`:

```js
import cron from 'node-cron'
import { prisma } from '../app.js'
import { shouldAutoAdvance } from '../services/recruitment-auto-advance.service.js'

export function startAutoAdvanceScheduler() {
  // 每 5 分钟扫一次
  cron.schedule('*/5 * * * *', async () => {
    try {
      await runAutoAdvanceCheck()
    } catch (e) {
      console.error('[auto-advance] cron failed:', e)
    }
  })
}

async function runAutoAdvanceCheck() {
  // 1. 找所有 active application + 他们的当前 link
  const applications = await prisma.application.findMany({
    where: { status: 'ACTIVE' },
    include: {
      currentLink: { include: { rule: true, stage: true } },
    },
    take: 200,  // 每次批 200,防 OOM
  })

  let advanced = 0
  for (const app of applications) {
    if (!app.currentLink?.rule) continue

    const record = {
      shouldAdvance: false,
      reason: '',
    }

    // 检查 entry condition
    const stageRecord = await prisma.applicationStageRecord.findFirst({
      where: { applicationId: app.id, linkId: app.currentLinkId, exitedAt: null },
    })

    if (rule.autoAdvanceType === 'IGNORE_NEXT') {
      record.shouldAdvance = true
      record.reason = 'IGNORE_NEXT'
    } else if (rule.autoAdvanceType === 'MEET_NEXT' || rule.autoAdvanceType === 'MEET_NEXT_OR_N2') {
      // 调 shouldAutoAdvance
      const result = await shouldAutoAdvance(app.currentLink, app.candidateId, {
        applicationId: app.id,
        currentStageRecord: stageRecord,
      })
      record.shouldAdvance = result.shouldAdvance
      record.reason = result.reason
    } else if (rule.autoAdvanceType === 'N1_ALL_PASS') {
      // N+1 全部通过判定
      const n1Records = await prisma.applicationStageRecord.findMany({
        where: { applicationId: app.id, stageId: { in: [...] } },
      })
      const allPass = n1Records.length > 0 && n1Records.every(r => r.toStatus === 'ALL_PASS' || r.toStatus === 'PASS')
      record.shouldAdvance = allPass
      record.reason = allPass ? 'N+1 全部通过' : 'N+1 未全部通过'
    }

    if (record.shouldAdvance) {
      // 写 record + 推进到下一阶段
      await prisma.applicationStageRecord.create({
        data: {
          applicationId: app.id,
          candidateId: app.candidateId,
          processId: app.processId,
          linkId: app.currentLink.id,
          stageId: app.currentLink.stageId,
          fromStatus: stageRecord?.toStatus,
          toStatus: 'AUTO_ADVANCE',
          decision: record.reason,
          autoAdvanced: true,
          decidedBy: null,  // 系统决策
          decisionReason: record.reason,
        },
      })
      // 推进 application.currentLinkId 到下一 link
      const nextLink = await findNextLink(app.currentLink)
      if (nextLink) {
        await prisma.application.update({
          where: { id: app.id },
          data: { currentLinkId: nextLink.id },
        })
        advanced++
      }
    }
  }
  console.log(`[auto-advance] cron: ${advanced}/${applications.length} advanced`)
}
```

`app.js` 启动时:
```js
import { startAutoAdvanceScheduler } from './scheduler/recruitment-auto-advance.scheduler.js'
startAutoAdvanceScheduler()
```

## 6. API 端点

`POST /api/recruitment/auto-advance/check`:

```js
// Body: { applicationId: "..." }
// Response: { shouldAdvance: bool, reason: string, skipScreen?: bool }
router.post('/check', authMiddleware, async (req, res) => {
  const { applicationId } = req.body
  const app = await prisma.application.findUnique({ where: { id: applicationId }, include: { currentLink: { include: { rule: true } } } })
  if (!app) return res.status(404).json({ error: 'application not found' })
  const result = await shouldAutoAdvance(app.currentLink, app.candidateId, { applicationId: app.id })
  res.json(result)
})
```

## 7. 测试

### 单元 (jest)
- `recruitment-auto-advance.service.js`:
  - `checkN2Skip`: N+2 / non-N+2 / 不存在候选 (3)
  - `checkDoubleASkip`: 2 evaluators same dept all pass / all fail / different dept / 1 evaluator / 0 evaluators (5)
  - `shouldAutoAdvance`: 各 autoAdvanceType × IMMEDIATE/DELAYED (8)
- `recruitment-auto-advance.scheduler.js`:
  - cron tick: IGNORE_NEXT 推进 / MEET_NEXT 推进 / N+2 / 边界 (4)

### 集成 (vitest e2e, 可选)
- Plan P 已有 4 spec,本次不新增(避免 scope 蔓延)

## 8. 风险 + 缓解

| 风险 | 缓解 |
|---|---|
| 新表 `ApplicationStageRecord` 大数据量 | 加 4 索引,数据 append-only,可定期归档 |
| Cron 5min 频次可能在生产卡 | 批 200 限速,日志显示 advanced/total |
| 双 A 部门排除名单是占位 | seed 阶段用真实部门 ID 填充 |
| Application 是否有 `currentLinkId` 字段? | 调研阶段确认(预期有,Plan L 应已加) |

## 9. 验收 (5 AC)

- AC-1: `ApplicationStageRecord` 表存在,4 索引就位
- AC-2: `prisma migrate status` 0 pending
- AC-3: `checkDoubleASkip` 5 个 test case 全过
- AC-4: `checkN2Skip` + `shouldAutoAdvance` 全 11 个 test case 过
- AC-5: cron 5min 启动,跑 1 次人工触发(通过 `POST /api/recruitment/auto-advance/check`),advanced 计数正确

---

*Spec 创建: 2026-06-14*
*基于: backend/src/services/recruitment-auto-advance.service.js 现状 + PRD G38 #11*
*预计: 1 commit, 1-2d 工作量*
