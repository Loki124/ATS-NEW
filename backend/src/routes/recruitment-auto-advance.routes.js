/**
 * 招聘流程自动流转 API - PRD G38 #11
 *
 *   POST /api/recruitment-auto-advance/check
 *     Body: { applicationId: "..." }
 *     Response: { shouldAdvance: bool, reason: string, skipScreen?: bool }
 *
 *   POST /api/recruitment-auto-advance/run
 *     手动触发一次 scheduler 扫描 (admin/HRBP only)
 *     Response: { total, advanced, skipped }
 */

import { Router } from 'express'
import { prisma } from '../app.js'
import { shouldAutoAdvance } from '../services/recruitment-auto-advance.service.js'
import { runAutoAdvanceCheck } from '../scheduler/recruitment-auto-advance.scheduler.js'
import { requireRole } from '../middleware/auth.middleware.js'

const router = Router()

/**
 * 检查单个 application 是否满足自动流转条件
 * (注: authMiddleware 在 app.js 级别统一加, 这里不需要重复)
 */
router.post('/check', async (req, res, next) => {
  try {
    const { applicationId } = req.body
    if (!applicationId) {
      return res.status(400).json({ error: 'applicationId required' })
    }

    const app = await prisma.application.findUnique({
      where: { id: applicationId },
    })
    if (!app) return res.status(404).json({ error: 'application not found' })

    // 解析当前 link (drift fix 2026-06-14: 直接用 application.currentLinkId)
    if (!app.currentLinkId) {
      return res.json({ shouldAdvance: false, reason: 'no current link' })
    }
    const currentLink = await prisma.processStageLink.findUnique({
      where: { id: app.currentLinkId },
      include: { rule: true },
    })
    if (!currentLink) {
      return res.json({ shouldAdvance: false, reason: 'no current link' })
    }

    const result = await shouldAutoAdvance(currentLink, app.candidateId, {
      applicationId: app.id,
    })
    res.json(result)
  } catch (err) {
    next(err)
  }
})

/**
 * 手动触发一次 scheduler 扫描 (admin/HRBP only)
 */
router.post('/run', requireRole('SUPER_ADMIN', 'ADMIN', 'HRBP'), async (req, res, next) => {
  try {
    const stats = await runAutoAdvanceCheck(prisma)
    res.json({ success: true, ...stats })
  } catch (err) {
    next(err)
  }
})

export default router