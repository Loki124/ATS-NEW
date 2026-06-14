/**
 * 自动归档 scheduler - PRD G38 #8
 *
 * 每 10 分钟扫一次所有 enabled rules, 执行:
 *   1. evaluateRule(rule) 评估每条 rule
 *   2. archiveApplications(applicationIds) 把命中 applications 状态改成 ARCHIVED
 *
 * 与 invitation.scheduler / recruitment-auto-advance.scheduler 保持同样
 * 的 start*/stop* 接口 + tasks[] 数组 + try/catch-on-start 风格
 */

import cron from 'node-cron'
import { prisma } from '../app.js'
import { runAutoArchiveCheck } from '../services/auto-archive.service.js'

const tasks = []

/**
 * 启动自动归档 scheduler
 * @param {object} prismaClient Prisma 实例 (保留注入式接口,与 auto-advance 对齐)
 */
export function startAutoArchiveScheduler(prismaClient = prisma) {
  if (!prismaClient) {
    console.warn('[auto-archive-scheduler] no prisma instance provided, scheduler disabled')
    return
  }
  // 每 10 分钟扫一次
  tasks.push(cron.schedule('*/10 * * * *', async () => {
    try {
      const stats = await runAutoArchiveCheck(prismaClient)
      if (stats.archived > 0 || stats.total > 0) {
        console.log(`[auto-archive-scheduler] total=${stats.total} archived=${stats.archived} skipped=${stats.skipped}`)
      }
    } catch (e) {
      console.error('[auto-archive-scheduler] cron failed:', e.message)
    }
  }))
  console.log('[auto-archive-scheduler] started with 1 cron task (every 10 min)')
}

export function stopAutoArchiveScheduler() {
  for (const t of tasks) {
    if (t && typeof t.stop === 'function') t.stop()
  }
  tasks.length = 0
  console.log('[auto-archive-scheduler] stopped')
}
