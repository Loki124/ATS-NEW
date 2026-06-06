/**
 * 邀约调度器 - PRD G14 (抢单超时 + 自动归档)
 *
 *  - 每 10 分钟: 处理 PENDING_CLAIM/PENDING_INVITE 超时记录
 *    - 抢单超时: 累计 attempts, 达 3 次 → TERMINATED
 *    - 领取超时: 升级到上级 (G16 escalation)
 *  - 每日 0 点: 通知所有 PENDING_CLAIM 即将超时的 (TODO Phase 3)
 */

import cron from 'node-cron'
import { processExpiredInvitations } from '../services/invitation.service.js'

const tasks = []

export function startInvitationScheduler(prisma) {
  if (!prisma) {
    console.warn('[invitation-scheduler] no prisma instance provided, scheduler disabled')
    return
  }
  // 每 10 分钟扫一次超时
  tasks.push(cron.schedule('*/10 * * * *', async () => {
    try {
      const stats = await processExpiredInvitations()
      if (stats.processed > 0) {
        console.log(`[invitation-scheduler] processed=${stats.processed}, requeued=${stats.requeued}, escalated=${stats.escalated}, terminated=${stats.terminated}`)
      }
    } catch (e) {
      console.error('[invitation-scheduler] processExpired failed:', e.message)
    }
  }))
  console.log('[invitation-scheduler] started with 1 cron task (every 10 min)')
}

export function stopInvitationScheduler() {
  for (const t of tasks) {
    if (t && typeof t.stop === 'function') t.stop()
  }
  tasks.length = 0
  console.log('[invitation-scheduler] stopped')
}
