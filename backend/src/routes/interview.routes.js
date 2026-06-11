/**
 * 面试管理路由 - PRD G3.6
 *
 * 资源：
 *   GET    /api/interviews                 列表（可按 applicationId 过滤）
 *   GET    /api/interviews/:id             详情（含 feedbacks）
 *   POST   /api/interviews                 安排面试
 *   PUT    /api/interviews/:id             修改时间 / 面试官
 *   GET    /api/interviews/history/:cid    G19 - 候选人历史反馈 (供前端预览)
 *   POST   /api/interviews/:id/feedback    提交反馈（关键：触发 stage 状态机刷新 + G19 自动预填）
 *   DELETE /api/interviews/:id             取消面试
 */

import { Router } from 'express'
import { prisma } from '../app.js'
import { AppError } from '../middleware/error.middleware.js'
import { pagination } from '../middleware/pagination.middleware.js'
import { refreshApplicationStageStatus } from '../services/interview-state-machine.service.js'
import { getCandidateHistory } from '../services/interview-history.service.js'

const router = Router()

// ====== 列表 ======
router.get('/', pagination(), async (req, res, next) => {
  try {
    const { applicationId, roundId, feedbackStatus, interviewStatus } = req.query
    const where = {}
    if (applicationId) where.applicationId = applicationId
    if (roundId) where.roundId = roundId
    if (feedbackStatus) where.feedbackStatus = feedbackStatus
    if (interviewStatus) where.interviewStatus = interviewStatus

    const [list, total] = await Promise.all([
      prisma.interview.findMany({
        where,
        include: {
          feedbacks: { select: { id: true, interviewerId: true, result: true, feedbackAt: true } },
          _count: { select: { feedbacks: true } },
        },
        orderBy: { interviewDate: 'desc' },
        skip: req.pagination.skip,
        take: req.pagination.take,
      }),
      prisma.interview.count({ where }),
    ])

    res.json({
      success: true,
      data: { list, pagination: { page: req.pagination.page, pageSize: req.pagination.pageSize, total, totalPages: Math.ceil(total / req.pagination.pageSize) } },
    })
  } catch (e) { next(e) }
})

// ====== 详情 ======
router.get('/:id', async (req, res, next) => {
  try {
    const interview = await prisma.interview.findUnique({
      where: { id: req.params.id },
      include: {
        feedbacks: { orderBy: { feedbackAt: 'asc' } },
        application: { select: { id: true, currentStageId: true, currentStageStatus: true } },
      },
    })
    if (!interview) return res.status(404).json({ success: false, message: '面试不存在' })
    res.json({ success: true, data: interview })
  } catch (e) { next(e) }
})

// ====== 安排面试 ======
router.post('/', async (req, res, next) => {
  try {
    const {
      applicationId, roundId, roundName, interviewType, interviewDate, duration = 60,
      location, meetingLink, interviewerIds, interviewerNames,
    } = req.body || {}

    if (!applicationId) throw new AppError('applicationId 必填', 400)
    if (!interviewType) throw new AppError('interviewType 必填', 400)
    if (!interviewDate) throw new AppError('interviewDate 必填', 400)

    const application = await prisma.application.findUnique({ where: { id: applicationId } })
    if (!application) throw new AppError('申请不存在', 404)

    const interview = await prisma.interview.create({
      data: {
        applicationId,
        roundId,
        roundName,
        interviewType,
        interviewDate: new Date(interviewDate),
        duration,
        location,
        meetingLink,
        interviewerIds: Array.isArray(interviewerIds) ? interviewerIds.join(',') : interviewerIds,
        interviewerNames: Array.isArray(interviewerNames) ? interviewerNames.join(',') : interviewerNames,
        arrangerId: req.userId,
        arrangerName: req.user?.realName || req.user?.username,
        interviewStatus: 'SCHEDULED',
        feedbackStatus: 'PENDING',
      },
    })
    res.status(201).json({ success: true, data: interview })
  } catch (e) { next(e) }
})

// ====== 修改面试 ======
router.put('/:id', async (req, res, next) => {
  try {
    const { id } = req.params
    const updates = req.body || {}
    const data = {}
    if (updates.interviewDate) data.interviewDate = new Date(updates.interviewDate)
    if (updates.duration !== undefined) data.duration = updates.duration
    if (updates.location !== undefined) data.location = updates.location
    if (updates.meetingLink !== undefined) data.meetingLink = updates.meetingLink
    if (updates.interviewerIds !== undefined) {
      data.interviewerIds = Array.isArray(updates.interviewerIds) ? updates.interviewerIds.join(',') : updates.interviewerIds
    }
    if (updates.interviewerNames !== undefined) {
      data.interviewerNames = Array.isArray(updates.interviewerNames) ? updates.interviewerNames.join(',') : updates.interviewerNames
    }
    if (updates.interviewStatus) data.interviewStatus = updates.interviewStatus

    const interview = await prisma.interview.update({ where: { id }, data })
    res.json({ success: true, data: interview })
  } catch (e) {
    if (e.code === 'P2025') return res.status(404).json({ success: false, message: '面试不存在' })
    next(e)
  }
})

// ====== G19: 获取候选人历史面试反馈 (供前端预览) ======
router.get('/history/:candidateId', async (req, res, next) => {
  try {
    const history = await getCandidateHistory(req.params.candidateId)
    res.json({ success: true, data: history })
  } catch (e) { next(e) }
})

// ====== 提交反馈（关键端点 - 触发 G3.6 状态机刷新）======
router.post('/:id/feedback', async (req, res, next) => {
  try {
    const { id } = req.params
    const {
      result, reason, values, comprehensive, recommendation,
      participantFeedback, previousFeedback, viewedPrevious,
    } = req.body || {}

    if (!result) throw new AppError('result 必填 (PASS / FAIL)', 400)
    if (!['PASS', 'FAIL'].includes(result)) throw new AppError('result 必须是 PASS 或 FAIL', 400)

    const interview = await prisma.interview.findUnique({
      where: { id },
      include: { application: { select: { id: true, candidateId: true } } },
    })
    if (!interview) throw new AppError('面试不存在', 404)

    // G19: 自动预填历史反馈 (如果前端没传)
    let prefilled = false
    if (!previousFeedback && interview.application?.candidateId) {
      try {
        const history = await getCandidateHistory(interview.application.candidateId)
        if (history.total > 0) {
          previousFeedback = history.previousFeedback
          prefilled = true
        }
      } catch (e) {
        // 历史聚合失败不影响主流程
        console.warn('[G19] getCandidateHistory 失败:', e.message)
      }
    }

    // upsert 当前用户的 feedback
    const interviewerId = req.userId
    const interviewerName = req.user?.realName || req.user?.username
    const feedback = await prisma.interviewFeedback.upsert({
      where: { interviewId_interviewerId: { interviewId: id, interviewerId } },
      create: {
        interviewId: id,
        interviewerId,
        interviewerName,
        result,
        reason,
        values,
        comprehensive,
        recommendation,
        participantFeedback,
        previousFeedback,
        viewedPrevious: !!viewedPrevious,
        feedbackAt: new Date(),
      },
      update: {
        result,
        reason,
        values,
        comprehensive,
        recommendation,
        participantFeedback,
        previousFeedback,
        viewedPrevious: !!viewedPrevious,
        feedbackAt: new Date(),
      },
    })

    // 更新 interview 的 feedbackStatus 为 COMPLETED
    await prisma.interview.update({
      where: { id },
      data: { feedbackStatus: 'COMPLETED' },
    })

    // 关键：刷新 application.currentStageStatus
    const newStageStatus = await refreshApplicationStageStatus(interview.applicationId)

    res.json({
      success: true,
      data: { feedback, currentStageStatus: newStageStatus, prefilled },
    })
  } catch (e) { next(e) }
})

// ====== 取消面试 ======
router.delete('/:id', async (req, res, next) => {
  try {
    const { id } = req.params
    const { reason, note } = req.body || {}
    const interview = await prisma.interview.update({
      where: { id },
      data: {
        interviewStatus: 'CANCELLED',
        cancelReason: reason,
        cancelNote: note,
      },
    })
    // 取消也触发刷新（可能从 NOT_ARRANGED 退回去）
    await refreshApplicationStageStatus(interview.applicationId)
    res.json({ success: true, data: interview })
  } catch (e) {
    if (e.code === 'P2025') return res.status(404).json({ success: false, message: '面试不存在' })
    next(e)
  }
})

export default router
