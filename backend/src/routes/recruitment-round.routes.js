/**
 * 面试轮次管理路由 - PRD #6
 * - GET    /api/interview-rounds          列表
 * - GET    /api/interview-rounds/:id      详情
 * - POST   /api/interview-rounds          新增
 * - PUT    /api/interview-rounds/:id      更新
 * - PUT    /api/interview-rounds/:id/status  启用/停用
 * - DELETE /api/interview-rounds/:id      删除（不允许 - 只允许停用 #1883）
 *
 * 业务规则：
 *   - 轮次可停用，不可删除
 *   - 停用校验：若有流程/阶段在用 → 阻断
 *   - "通用评价表"标记
 */

import { Router } from 'express';
import { prisma } from '../app.js';
import { AppError } from '../middleware/error.middleware.js';

const router = Router();

// 列表
router.get('/', async (req, res, next) => {
  try {
    const { status, keyword } = req.query;
    const where = {};
    if (status) where.status = status;
    if (keyword) {
      where.OR = [
        { name: { contains: keyword } },
        { code: { contains: keyword } },
      ];
    }
    const rounds = await prisma.interviewRound.findMany({
      where,
      include: {
        creator: { select: { id: true, realName: true, username: true } },
      },
      orderBy: { code: 'asc' },
    });
    res.json({ success: true, data: rounds });
  } catch (e) { next(e); }
});

router.get('/:id', async (req, res, next) => {
  try {
    const round = await prisma.interviewRound.findUnique({
      where: { id: req.params.id },
      include: { creator: { select: { id: true, realName: true, username: true } } },
    });
    if (!round) return res.status(404).json({ success: false, message: '轮次不存在' });
    res.json({ success: true, data: round });
  } catch (e) { next(e); }
});

router.post('/', async (req, res, next) => {
  try {
    const { name, description, evaluationFormName, isUniversal = false, createdBy } = req.body;
    if (!name) throw new AppError('轮次名称必填', 400);

    // 编号: R + 3 位流水号
    const last = await prisma.interviewRound.findFirst({
      where: { code: { startsWith: 'R' } },
      orderBy: { code: 'desc' },
    });
    const nextNum = last ? parseInt(last.code.slice(1)) + 1 : 1;
    const code = 'R' + String(nextNum).padStart(3, '0');

    const round = await prisma.interviewRound.create({
      data: { code, name, description, evaluationFormName, isUniversal, createdBy },
    });
    res.status(201).json({ success: true, data: round });
  } catch (e) { next(e); }
});

router.put('/:id', async (req, res, next) => {
  try {
    const round = await prisma.interviewRound.update({
      where: { id: req.params.id },
      data: {
        ...(req.body.name !== undefined && { name: req.body.name }),
        ...(req.body.description !== undefined && { description: req.body.description }),
        ...(req.body.evaluationFormName !== undefined && { evaluationFormName: req.body.evaluationFormName }),
        ...(req.body.isUniversal !== undefined && { isUniversal: req.body.isUniversal }),
      },
    });
    res.json({ success: true, data: round });
  } catch (e) { next(e); }
});

// 启用/停用
router.put('/:id/status', async (req, res, next) => {
  try {
    const { status } = req.body;
    if (!['ACTIVE', 'INACTIVE'].includes(status)) {
      throw new AppError('状态值无效', 400);
    }
    // 停用前校验：是否有阶段规则引用 (#1883)
    if (status === 'INACTIVE') {
      const usages = await prisma.stageRule.findMany({
        where: { interviewRoundIds: { not: null } },
        select: { interviewRoundIds: true },
      });
      const isInUse = usages.some((r) => {
        const ids = Array.isArray(r.interviewRoundIds) ? r.interviewRoundIds : [];
        return ids.includes(req.params.id);
      });
      if (isInUse) {
        throw new AppError('当前面试轮次正在被其他功能应用，请先取消应用后再停用', 400);
      }
    }
    const round = await prisma.interviewRound.update({
      where: { id: req.params.id },
      data: { status },
    });
    res.json({ success: true, data: round });
  } catch (e) { next(e); }
});

export default router;
