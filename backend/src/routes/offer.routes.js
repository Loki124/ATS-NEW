/**
 * Offer 状态机管理路由 - PRD G23
 *
 * 资源：
 *   GET    /api/offers/:id                              详情
 *   POST   /api/offers/:id/transition                   状态转移 (核心 G23)
 *   GET    /api/offers/:id/status-history               状态变更历史
 *   GET    /api/offers/:id/background-checks            G26 - 背调列表
 *   POST   /api/offers/:id/background-checks            G26 - 创建背调
 *   PUT    /api/offers/:id/background-checks/:bid/complete  G26 - 完成背调
 *   GET    /api/offers/:id/background-checks/:bid/report    G26 - 下载 PDF 报告
 */

import { Router } from 'express'
import { prisma } from '../app.js'
import { AppError } from '../middleware/error.middleware.js'
import {
  OFFER_STATUSES,
  canTransitionOffer,
  canSendOffer,
  canEditOffer,
} from '../services/offer-state-machine.service.js'
import { recordOperation } from '../services/audit-log.service.js'
import {
  listBackgroundChecks,
  createBackgroundCheck,
  completeBackgroundCheck,
} from '../services/background-check.service.js'
import { renderBackgroundCheckReport } from '../services/pdf-generator.service.js'

const router = Router()

// ====== 列表 ======
router.get('/', async (req, res, next) => {
  try {
    const { offerStatus, demandId, page = 1, pageSize = 20 } = req.query
    const where = {}
    if (offerStatus) where.offerStatus = offerStatus
    if (demandId) where.demandId = demandId

    const [list, total] = await Promise.all([
      prisma.offer.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip: (Number(page) - 1) * Number(pageSize),
        take: Number(pageSize),
      }),
      prisma.offer.count({ where }),
    ])
    res.json({
      success: true,
      data: { list, pagination: { page: Number(page), pageSize: Number(pageSize), total, totalPages: Math.ceil(total / Number(pageSize)) } },
    })
  } catch (e) { next(e) }
})

// ====== 详情 ======
router.get('/:id', async (req, res, next) => {
  try {
    const offer = await prisma.offer.findUnique({
      where: { id: req.params.id },
      include: { statusHistory: { orderBy: { createdAt: 'desc' } } },
    })
    if (!offer) return res.status(404).json({ success: false, message: 'Offer 不存在' })
    res.json({ success: true, data: offer })
  } catch (e) { next(e) }
})

// ====== 状态变更历史 ======
router.get('/:id/status-history', async (req, res, next) => {
  try {
    const history = await prisma.offerStatusHistory.findMany({
      where: { offerId: req.params.id },
      orderBy: { createdAt: 'desc' },
    })
    res.json({ success: true, data: history })
  } catch (e) { next(e) }
})

// ====== 创建 ======
router.post('/', async (req, res, next) => {
  try {
    const { applicationId, demandId, expectedJoinDate, ...rest } = req.body || {}
    if (!applicationId) throw new AppError('applicationId 必填', 400)
    if (!expectedJoinDate) throw new AppError('expectedJoinDate 必填', 400)

    const offer = await prisma.offer.create({
      data: {
        applicationId,
        demandId,
        expectedJoinDate: new Date(expectedJoinDate),
        offerStatus: OFFER_STATUSES.NOT_CREATED,
        ...rest,
      },
    })
    res.status(201).json({ success: true, data: offer })
  } catch (e) { next(e) }
})

// ====== 更新（仅 DRAFT 状态可改） ======
router.put('/:id', async (req, res, next) => {
  try {
    const offer = await prisma.offer.findUnique({ where: { id: req.params.id } })
    if (!offer) throw new AppError('Offer 不存在', 404)
    if (!canEditOffer(offer.offerStatus)) {
      throw new AppError(`当前状态 ${offer.offerStatus} 不可编辑`, 400)
    }

    const allowed = ['expectedJoinDate', 'jobTitle', 'jobLevel', 'baseSalaryTrial', 'baseSalaryFormal',
      'trialMonths', 'contractType', 'contractPeriod', 'legalCompany', 'attachments']
    const data = {}
    for (const k of allowed) {
      if (req.body[k] !== undefined) {
        data[k] = k === 'expectedJoinDate' ? new Date(req.body[k]) : req.body[k]
      }
    }
    const updated = await prisma.offer.update({ where: { id: req.params.id }, data })
    res.json({ success: true, data: updated })
  } catch (e) { next(e) }
})

// ====== 状态转移（核心 G23 端点） ======
router.post('/:id/transition', async (req, res, next) => {
  try {
    const { to, reason } = req.body || {}
    if (!to) throw new AppError('to 必填', 400)
    if (!Object.values(OFFER_STATUSES).includes(to)) {
      throw new AppError(`无效目标状态: ${to}`, 400)
    }

    const result = await prisma.$transaction(async (tx) => {
      const offer = await tx.offer.findUnique({ where: { id: req.params.id } })
      if (!offer) throw new AppError('Offer 不存在', 404)

      if (!canTransitionOffer(offer.offerStatus, to)) {
        throw new AppError(`状态转移非法: ${offer.offerStatus} → ${to}`, 400)
      }

      // 特殊校验: SENT 状态必须先有 senderId/sentAt
      if (to === OFFER_STATUSES.SENT) {
        if (!canSendOffer(offer.offerStatus)) {
          throw new AppError(`当前状态 ${offer.offerStatus} 不可发送 (需先 APPROVED)`, 400)
        }
      }

      const updated = await tx.offer.update({
        where: { id: offer.id },
        data: {
          offerStatus: to,
          ...(to === OFFER_STATUSES.SENT ? { sentAt: new Date(), senderId: req.userId } : {}),
        },
      })

      // 状态历史
      await tx.offerStatusHistory.create({
        data: {
          offerId: offer.id,
          fromStatus: offer.offerStatus,
          toStatus: to,
          reason,
          operatorId: req.userId,
        },
      })

      // 通用审计日志
      await recordOperation({
        tx,
        entityType: 'offer',
        entityId: offer.id,
        action: 'TRANSITION',
        fromState: offer.offerStatus,
        toState: to,
        operatorId: req.userId,
        reason,
      })

      return updated
    })

    res.json({ success: true, data: result })
  } catch (e) { next(e) }
})

// ========================================================
// G26 - Offer 手动背调 4 等级 + PDF 报告
// ========================================================

// 列表
router.get('/:id/background-checks', async (req, res, next) => {
  try {
    const data = await listBackgroundChecks(req.params.id)
    res.json({ success: true, data })
  } catch (e) { next(e) }
})

// 创建
router.post('/:id/background-checks', async (req, res, next) => {
  try {
    const data = await createBackgroundCheck({
      offerId: req.params.id,
      checkType: req.body.checkType,
      supplier: req.body.supplier,
      note: req.body.note,
    })
    res.json({ success: true, data })
  } catch (e) { next(e) }
})

// 完成 (写等级)
router.put('/:id/background-checks/:bid/complete', async (req, res, next) => {
  try {
    const data = await completeBackgroundCheck(req.params.bid, req.body)
    res.json({ success: true, data })
  } catch (e) { next(e) }
})

// 下载报告 PDF
router.get('/:id/background-checks/:bid/report', async (req, res, next) => {
  try {
    const record = await prisma.backgroundCheckRecord.findUnique({
      where: { id: req.params.bid },
    })
    if (!record) throw new AppError('背调记录不存在', 404)
    if (!record.level) throw new AppError('背调未完成, 暂不能生成报告', 400)
    const offer = await prisma.offer.findUnique({
      where: { id: req.params.id },
      include: { application: { include: { candidate: true } } },
    })
    if (!offer) throw new AppError('Offer 不存在', 404)
    const pdf = await renderBackgroundCheckReport({
      offer,
      candidate: offer.application?.candidate,
      record,
    })
    res.setHeader('Content-Type', 'application/pdf')
    res.setHeader('Content-Disposition', `attachment; filename="bg-check-${req.params.bid}.pdf"`)
    res.send(pdf)
  } catch (e) { next(e) }
})

export default router
