/**
 * GDPR API - Plan K #7
 *
 *  POST /api/gdpr/anonymize  { userId } → 软删除 + PII 替换
 *  GET  /api/gdpr/export?userId=... → 导出该用户所有数据为 JSON
 *  POST /api/gdpr/hard-delete-now  (admin) → 立即跑一次 hard delete
 *
 * 注: hard-delete 必须绕过 soft-delete 中间件, 故此处用独立的 rawPrisma 实例.
 *     anonymize / export 使用 app.js 的 extended client (与其它 service 一致).
 */

import { Router } from 'express'
import { PrismaClient } from '@prisma/client'
import { authMiddleware, requireRole } from '../middleware/auth.middleware.js'
import { anonymizeUser, exportUserData, hardDeleteExpired } from '../services/gdpr.service.js'

const router = Router()
const rawPrisma = new PrismaClient()

router.post('/anonymize', authMiddleware, async (req, res, next) => {
  try {
    const { userId } = req.body
    if (!userId) return res.status(400).json({ error: 'userId required' })

    // 只能自己 anonymize 自己, 或 SUPER_ADMIN
    if (req.user.id !== userId && req.user.roleType !== 'SUPER_ADMIN') {
      return res.status(403).json({ error: 'can only anonymize self' })
    }

    const result = await anonymizeUser(userId)
    res.json({ success: true, ...result })
  } catch (err) {
    next(err)
  }
})

router.get('/export', authMiddleware, async (req, res, next) => {
  try {
    const { userId } = req.query
    if (!userId) return res.status(400).json({ error: 'userId required' })

    // 只能导出自己, 或 SUPER_ADMIN
    if (req.user.id !== userId && req.user.roleType !== 'SUPER_ADMIN') {
      return res.status(403).json({ error: 'can only export self' })
    }

    const data = await exportUserData(String(userId))
    if (data.error) return res.status(404).json(data)

    res.setHeader('Content-Type', 'application/json; charset=utf-8')
    res.setHeader('Content-Disposition', `attachment; filename="gdpr-export-${userId}.json"`)
    res.json(data)
  } catch (err) {
    next(err)
  }
})

router.post('/hard-delete-now', authMiddleware, requireRole('SUPER_ADMIN'), async (req, res, next) => {
  try {
    const result = await hardDeleteExpired(rawPrisma)
    res.json({ success: true, ...result })
  } catch (err) {
    next(err)
  }
})

export default router