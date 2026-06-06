/**
 * 职位管理路由
 * 提供扁平职位列表（供下拉框等场景使用）
 */

import express from 'express';
import { prisma } from '../app.js';

const router = express.Router();

// 列出职位（支持按状态、需求、部门过滤）
router.get('/', async (req, res, next) => {
  try {
    const { status = 'ACTIVE', demandId, departmentId, keyword } = req.query;
    const where = {};
    if (status) where.status = status;
    if (demandId) where.demandId = demandId;
    if (departmentId) where.departmentId = departmentId;
    if (keyword) {
      where.OR = [
        { name: { contains: keyword } },
        { code: { contains: keyword } },
      ];
    }
    const positions = await prisma.position.findMany({
      where,
      include: {
        department: { select: { id: true, name: true, code: true } },
        demand: { select: { id: true, name: true, code: true } },
      },
      orderBy: { createdAt: 'desc' },
      take: 200,
    });
    res.json({ success: true, data: positions });
  } catch (e) {
    next(e);
  }
});

// 职位详情
router.get('/:id', async (req, res, next) => {
  try {
    const position = await prisma.position.findUnique({
      where: { id: req.params.id },
      include: {
        department: true,
        demand: true,
      },
    });
    if (!position) return res.status(404).json({ success: false, message: '职位不存在' });
    res.json({ success: true, data: position });
  } catch (e) {
    next(e);
  }
});

// =====================================
// 职位状态机 (PRD G5)
// =====================================

import { canTransitionPosition, closePosition, POSITION_STATUSES } from '../services/position-state-machine.service.js'
import { recordOperation } from '../services/audit-log.service.js'

/**
 * 职位状态转移
 * POST /api/positions/:id/transition
 * body: { to: 'RECRUITING' | 'PAUSED' | 'CLOSED', reason?, forceClose? }
 */
router.post('/:id/transition', async (req, res, next) => {
  try {
    const { to, reason, forceClose = false } = req.body || {}
    if (!to) return res.status(400).json({ success: false, message: 'to 必填' })
    if (!Object.values(POSITION_STATUSES).includes(to)) {
      return res.status(400).json({ success: false, message: `无效目标状态: ${to}` })
    }

    const result = await prisma.$transaction(async (tx) => {
      const position = await tx.position.findUnique({ where: { id: req.params.id } })
      if (!position) throw Object.assign(new Error('职位不存在'), { statusCode: 404 })

      if (!canTransitionPosition(position.positionStatus, to)) {
        throw Object.assign(
          new Error(`状态转移非法: ${position.positionStatus} → ${to}`),
          { statusCode: 400 }
        )
      }

      // 关闭时检查候选人保护
      if (to === POSITION_STATUSES.CLOSED) {
        await closePosition(req.params.id, { forceClose }).catch((e) => {
          throw Object.assign(e, { statusCode: e.statusCode || 400 })
        })
      }

      const updated = await tx.position.update({
        where: { id: req.params.id },
        data: { positionStatus: to },
      })

      await tx.positionStatusHistory.create({
        data: {
          positionId: req.params.id,
          fromStatus: position.positionStatus,
          toStatus: to,
          reason,
          operatorId: req.userId,
        },
      })

      await recordOperation({
        tx,
        entityType: 'position',
        entityId: req.params.id,
        action: 'TRANSITION',
        fromState: position.positionStatus,
        toState: to,
        operatorId: req.userId,
        reason,
        metadata: { forceClose: to === 'CLOSED' ? !!forceClose : undefined },
      })

      return updated
    })

    res.json({ success: true, data: result })
  } catch (e) {
    if (e.statusCode && !e.code?.startsWith('P')) {
      return res.status(e.statusCode).json({ success: false, message: e.message, code: e.code })
    }
    next(e)
  }
})

/**
 * 职位状态历史
 * GET /api/positions/:id/status-history
 */
router.get('/:id/status-history', async (req, res, next) => {
  try {
    const history = await prisma.positionStatusHistory.findMany({
      where: { positionId: req.params.id },
      orderBy: { createdAt: 'desc' },
    })
    res.json({ success: true, data: history })
  } catch (e) { next(e) }
})

export default router;
