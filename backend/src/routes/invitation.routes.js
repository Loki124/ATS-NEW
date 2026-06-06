/**
 * 邀约管理路由 - PRD G14 + G15 + G16
 *
 * 资源：
 *   GET    /api/invitations                          列表 (按状态/超时过滤)
 *   GET    /api/invitations/claimable                抢单池 (PENDING_CLAIM)
 *   GET    /api/invitations/:id                      详情
 *   POST   /api/invitations/:id/enter-pool           入抢单池
 *   POST   /api/invitations/:id/claim                抢单
 *   POST   /api/invitations/:id/contact              标记联系候选人
 *   POST   /api/invitations/:id/result               标记结果 (success/fail)
 *   POST   /api/invitations/:id/intervene            干预 (上级接手)
 *   POST   /api/invitations/:id/terminate            终止
 *   POST   /api/invitations/process-expired          手动触发超时处理 (cron 也调)
 */

import { Router } from 'express'
import { prisma } from '../app.js'
import { AppError } from '../middleware/error.middleware.js'
import {
  enterClaimPool,
  claimInvitation,
  markContacted,
  markResult,
  intervene,
  terminate,
  processExpiredInvitations,
} from '../services/invitation.service.js'
import { INVITATION_STATUSES } from '../services/invitation-state-machine.service.js'

const router = Router()

// ====== 列表 ======
router.get('/', async (req, res, next) => {
  try {
    const { status, positionId, ownerId, claimedById, expired, page = 1, pageSize = 20 } = req.query
    const where = {}
    if (status) where.invitationStatus = status
    if (positionId) where.positionId = positionId
    if (ownerId) where.ownerId = ownerId
    if (claimedById) where.claimedById = claimedById
    if (expired === 'true') {
      where.invitationStatus = { in: ['PENDING_CLAIM', 'PENDING_INVITE'] }
      where.timeoutAt = { lt: new Date() }
    }

    const [list, total] = await Promise.all([
      prisma.invitationRecord.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip: (Number(page) - 1) * Number(pageSize),
        take: Number(pageSize),
      }),
      prisma.invitationRecord.count({ where }),
    ])
    res.json({ success: true, data: { list, pagination: { page: Number(page), pageSize: Number(pageSize), total, totalPages: Math.ceil(total / Number(pageSize)) } } })
  } catch (e) { next(e) }
})

// ====== 抢单池 ======
router.get('/claimable', async (req, res, next) => {
  try {
    const list = await prisma.invitationRecord.findMany({
      where: {
        invitationStatus: INVITATION_STATUSES.PENDING_CLAIM,
        timeoutAt: { gt: new Date() },
      },
      orderBy: { timeoutAt: 'asc' }, // 即将超时的在前
    })
    res.json({ success: true, data: list })
  } catch (e) { next(e) }
})

// ====== 详情 ======
router.get('/:id', async (req, res, next) => {
  try {
    const inv = await prisma.invitationRecord.findUnique({ where: { id: req.params.id } })
    if (!inv) return res.status(404).json({ success: false, message: '邀约记录不存在' })
    res.json({ success: true, data: inv })
  } catch (e) { next(e) }
})

// ====== 入抢单池 ======
router.post('/:id/enter-pool', async (req, res, next) => {
  try {
    const inv = await enterClaimPool(req.params.id, { reason: req.body?.reason })
    res.json({ success: true, data: inv })
  } catch (e) { next(e) }
})

// ====== 抢单 ======
router.post('/:id/claim', async (req, res, next) => {
  try {
    const inv = await claimInvitation(req.params.id, req.userId, req.user?.realName || req.user?.username)
    res.json({ success: true, data: inv })
  } catch (e) { next(e) }
})

// ====== 标记联系 ======
router.post('/:id/contact', async (req, res, next) => {
  try {
    const inv = await markContacted(req.params.id, { note: req.body?.note })
    res.json({ success: true, data: inv })
  } catch (e) { next(e) }
})

// ====== 标记结果 ======
router.post('/:id/result', async (req, res, next) => {
  try {
    const { success, reason } = req.body || {}
    if (typeof success !== 'boolean') throw new AppError('success 必填 (true/false)', 400)
    const inv = await markResult(req.params.id, { success, reason })
    res.json({ success: true, data: inv })
  } catch (e) { next(e) }
})

// ====== 干预 ======
router.post('/:id/intervene', async (req, res, next) => {
  try {
    const inv = await intervene(req.params.id, {
      operatorId: req.userId,
      operatorName: req.user?.realName || req.user?.username,
      reason: req.body?.reason,
    })
    res.json({ success: true, data: inv })
  } catch (e) { next(e) }
})

// ====== 终止 ======
router.post('/:id/terminate', async (req, res, next) => {
  try {
    const inv = await terminate(req.params.id, { reason: req.body?.reason, operatorId: req.userId })
    res.json({ success: true, data: inv })
  } catch (e) { next(e) }
})

// ====== 手动触发超时处理 (通常由 cron 调用) ======
router.post('/process-expired', async (req, res, next) => {
  try {
    const stats = await processExpiredInvitations()
    res.json({ success: true, data: stats })
  } catch (e) { next(e) }
})

export default router
