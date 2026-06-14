/**
 * GDPR 自动 hard delete scheduler
 *
 * 每天凌晨 3 点跑一次, 删除 soft delete 超过 30 天的记录.
 * 与 invitation/auto-archive 保持同样的 start/stop 接口 + tasks 数组 +
 * try/catch-on-start 风格.
 *
 * 注: 需要绕过 soft-delete 中间件 (它会把 deleteMany 转成 updateMany),
 *     所以此处独立 new 一个 PrismaClient, 与 app.js 的 extended client 隔离.
 */

import cron from 'node-cron'
import { PrismaClient } from '@prisma/client'
import { hardDeleteExpired } from '../services/gdpr.service.js'

const tasks = []
const rawPrisma = new PrismaClient()

export function startGdprScheduler() {
  // 每天凌晨 3 点
  tasks.push(cron.schedule('0 3 * * *', async () => {
    try {
      const result = await hardDeleteExpired(rawPrisma)
      const total = Object.values(result.deleted).reduce((a, b) => a + b, 0)
      console.log(`[gdpr-scheduler] hard-deleted ${total} records past 30d soft-delete`)
    } catch (e) {
      console.error('[gdpr-scheduler] cron failed:', e.message)
    }
  }))
  console.log('[gdpr-scheduler] started (daily 3am)')
}

export function stopGdprScheduler() {
  for (const t of tasks) if (t && typeof t.stop === 'function') t.stop()
  tasks.length = 0
  console.log('[gdpr-scheduler] stopped')
}

export async function shutdownGdprScheduler() {
  stopGdprScheduler()
  try { await rawPrisma.$disconnect() } catch (e) { /* ignore */ }
}