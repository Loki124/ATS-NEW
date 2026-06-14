/**
 * 招聘流程自动流转 scheduler - PRD G38 #11
 *
 * 每 5 分钟扫描一次:
 *   1. 找所有 ACTIVE 状态的 applications (批 200 防 OOM)
 *   2. 解析每个 application 的当前 link
 *      - 优先: application.currentLinkId (Plan L 承诺, 但当前 schema 缺失 - 报告为 drift)
 *      - 兜底: application_stage_records.findFirst({ applicationId, exitedAt: null })
 *   3. 按 StageRule.autoAdvanceType 推进候选人
 *   4. 推进成功 → 写一条 ApplicationStageRecord (toStatus=AUTO_ADVANCE, autoAdvanced=true)
 *   5. 推进 application.currentLinkId 到下一 link (若字段存在)
 */

import cron from 'node-cron'
import { prisma } from '../app.js'
import { shouldAutoAdvance } from '../services/recruitment-auto-advance.service.js'

const tasks = []

/**
 * 启动自动流转 scheduler
 * @param {object} prismaClient Prisma 实例 (保留注入式接口,与 invitation.scheduler 对齐)
 */
export function startAutoAdvanceScheduler(prismaClient = prisma) {
  if (!prismaClient) {
    console.warn('[auto-advance-scheduler] no prisma instance provided, scheduler disabled')
    return
  }
  // 每 5 分钟扫一次
  tasks.push(cron.schedule('*/5 * * * *', async () => {
    try {
      const stats = await runAutoAdvanceCheck(prismaClient)
      if (stats.advanced > 0 || stats.total > 0) {
        console.log(`[auto-advance-scheduler] advanced=${stats.advanced}/${stats.total}`)
      }
    } catch (e) {
      console.error('[auto-advance-scheduler] cron failed:', e.message)
    }
  }))
  console.log('[auto-advance-scheduler] started with 1 cron task (every 5 min)')
}

export function stopAutoAdvanceScheduler() {
  for (const t of tasks) {
    if (t && typeof t.stop === 'function') t.stop()
  }
  tasks.length = 0
  console.log('[auto-advance-scheduler] stopped')
}

/**
 * 执行一次自动流转扫描 (供 scheduler 和手动触发共用)
 * @param {object} prismaClient
 * @returns {Promise<{total: number, advanced: number, skipped: number}>}
 */
export async function runAutoAdvanceCheck(prismaClient = prisma) {
  // 1. 找所有 active applications (批 200 防 OOM)
  const applications = await prismaClient.application.findMany({
    where: { status: 'ACTIVE' },
    take: 200,
  })

  let advanced = 0
  let skipped = 0

  for (const app of applications) {
    try {
      // 2. 解析当前 link
      // 优先: app.currentLinkId (Plan L 应已加, 当前 schema 缺失 → 报告 drift)
      // 兜底: application_stage_records 最近一条未退出的记录
      let currentLink = null
      let currentLinkId = null

      if (app.currentLinkId) {
        currentLinkId = app.currentLinkId
        currentLink = await prismaClient.processStageLink.findUnique({
          where: { id: currentLinkId },
          include: { rule: true, stage: true },
        })
      } else {
        // Drift 模式: 从 application_stage_records 推断当前 link
        const activeRecord = await prismaClient.applicationStageRecord.findFirst({
          where: { applicationId: app.id, exitedAt: null },
          orderBy: { createdAt: 'desc' },
        })
        if (activeRecord) {
          currentLinkId = activeRecord.linkId
          currentLink = await prismaClient.processStageLink.findUnique({
            where: { id: currentLinkId },
            include: { rule: true, stage: true },
          })
        }
      }

      if (!currentLink || !currentLink.rule) {
        skipped++
        continue
      }
      const rule = currentLink.rule

      let shouldAdvance = false
      let reason = ''

      if (rule.autoAdvanceType === 'IGNORE_NEXT') {
        shouldAdvance = true
        reason = 'IGNORE_NEXT'
      } else if (rule.autoAdvanceType === 'MEET_NEXT' || rule.autoAdvanceType === 'MEET_NEXT_OR_N2') {
        const result = await shouldAutoAdvance(currentLink, app.candidateId, {
          applicationId: app.id,
        })
        shouldAdvance = result.shouldAdvance
        reason = result.reason
      } else if (rule.autoAdvanceType === 'N1_ALL_PASS') {
        // N+1 全部通过: 查 N+1 阶段的流转记录
        const n1Records = await prismaClient.applicationStageRecord.findMany({
          where: {
            applicationId: app.id,
            linkId: { not: currentLinkId },
          },
          orderBy: { exitedAt: 'desc' },
          take: 10,
        })
        const allPass = n1Records.length > 0 && n1Records.every(
          (r) => r.toStatus === 'ALL_PASS' || r.toStatus === 'PASS',
        )
        shouldAdvance = allPass
        reason = allPass ? 'N+1 全部通过' : 'N+1 未全部通过'
      }

      if (shouldAdvance) {
        // 写 record
        await prismaClient.applicationStageRecord.create({
          data: {
            applicationId: app.id,
            candidateId: app.candidateId,
            processId: app.processId,
            linkId: currentLink.id,
            stageId: currentLink.stageId,
            toStatus: 'AUTO_ADVANCE',
            decision: reason,
            autoAdvanced: true,
            decisionReason: reason,
          },
        })

        // 推进到下一 link
        const nextLink = await prismaClient.processStageLink.findFirst({
          where: {
            processId: app.processId,
            orderIndex: { gt: currentLink.orderIndex },
            isEnd: false,
          },
          orderBy: { orderIndex: 'asc' },
        })
        if (nextLink) {
          // 仅当 currentLinkId 字段存在时更新 (drift 模式跳过 - 由未来阶段补字段)
          if (app.currentLinkId !== undefined) {
            await prismaClient.application.update({
              where: { id: app.id },
              data: { currentLinkId: nextLink.id },
            })
          }
          advanced++
        } else {
          skipped++
        }
      } else {
        skipped++
      }
    } catch (err) {
      console.error(`[auto-advance-scheduler] app ${app.id} failed:`, err.message)
      skipped++
    }
  }

  return { total: applications.length, advanced, skipped }
}