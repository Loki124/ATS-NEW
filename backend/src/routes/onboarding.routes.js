/**
 * 待入职管理路由 - PRD G28
 *
 * 资源：
 *   GET    /api/onboardings                  列表
 *   GET    /api/onboardings/:id              详情
 *   POST   /api/onboardings                  创建 (通常从 Offer 流转)
 *   POST   /api/onboardings/:id/transition   状态转移 (核心 G28)
 *   GET    /api/onboardings/:id/status-history 状态历史
 */

import { Router } from 'express'
import { prisma } from '../app.js'
import { AppError } from '../middleware/error.middleware.js'
import {
  ONBOARDING_STATUSES,
  canTransitionOnboarding,
} from '../services/onboarding-state-machine.service.js'
import { recordOperation, recordDemandStatusChange } from '../services/audit-log.service.js'

const router = Router()

// ====== 列表 ======
router.get('/', async (req, res, next) => {
  try {
    const { onboardingStatus, demandId, page = 1, pageSize = 20 } = req.query
    const where = {}
    if (onboardingStatus) where.onboardingStatus = onboardingStatus
    if (demandId) where.demandId = demandId

    const [list, total] = await Promise.all([
      prisma.onboarding.findMany({
        where,
        orderBy: { expectedJoinDate: 'asc' },
        skip: (Number(page) - 1) * Number(pageSize),
        take: Number(pageSize),
      }),
      prisma.onboarding.count({ where }),
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
    const ob = await prisma.onboarding.findUnique({ where: { id: req.params.id } })
    if (!ob) return res.status(404).json({ success: false, message: '入职记录不存在' })
    res.json({ success: true, data: ob })
  } catch (e) { next(e) }
})

// ====== 创建 ======
router.post('/', async (req, res, next) => {
  try {
    const { applicationId, expectedJoinDate, ...rest } = req.body || {}
    if (!applicationId) throw new AppError('applicationId 必填', 400)
    if (!expectedJoinDate) throw new AppError('expectedJoinDate 必填', 400)

    const ob = await prisma.onboarding.create({
      data: {
        applicationId,
        expectedJoinDate: new Date(expectedJoinDate),
        onboardingStatus: ONBOARDING_STATUSES.NOT_STARTED,
        ...rest,
      },
    })
    res.status(201).json({ success: true, data: ob })
  } catch (e) { next(e) }
})

// ====== 状态转移 ======
router.post('/:id/transition', async (req, res, next) => {
  try {
    const { to, reason } = req.body || {}
    if (!to) throw new AppError('to 必填', 400)
    if (!Object.values(ONBOARDING_STATUSES).includes(to)) {
      throw new AppError(`无效目标状态: ${to}`, 400)
    }

    const result = await prisma.$transaction(async (tx) => {
      const ob = await tx.onboarding.findUnique({ where: { id: req.params.id } })
      if (!ob) throw new AppError('入职记录不存在', 404)

      if (!canTransitionOnboarding(ob.onboardingStatus, to)) {
        throw new AppError(`状态转移非法: ${ob.onboardingStatus} → ${to}`, 400)
      }

      const data = { onboardingStatus: to }
      // 入职完成时记录入职时间
      if (to === ONBOARDING_STATUSES.ONBOARDED) {
        data.onboardedAt = new Date()
      }
      // 取消时记录原因
      if (to === ONBOARDING_STATUSES.CANCELLED) {
        data.cancelReason = reason || ''
        data.cancelNote = reason
      }

      const updated = await tx.onboarding.update({ where: { id: req.params.id }, data })

      // 通用审计
      await recordOperation({
        tx,
        entityType: 'onboarding',
        entityId: req.params.id,
        action: 'TRANSITION',
        fromState: ob.onboardingStatus,
        toState: to,
        operatorId: req.userId,
        reason,
      })

      return updated
    })

    res.json({ success: true, data: result })
  } catch (e) { next(e) }
})

export default router
