/**
 * 流程-阶段关联路由 (PRD #3.2)
 *
 * 把"全局阶段模板库"中的阶段应用到具体流程中
 *
 * 资源：
 *   GET    /api/recruitment-process-links?processId=...
 *   GET    /api/recruitment-process-links/:id
 *   POST   /api/recruitment-process-links          添加阶段到流程
 *   PUT    /api/recruitment-process-links/:id      更新 link (customName / orderIndex / stageLimit)
 *   PUT    /api/recruitment-process-links/reorder  批量调整顺序
 *   DELETE /api/recruitment-process-links/:id      从流程中移除
 *
 * 业务规则 (#3.2)：
 *   - 同一阶段在每个流程中只能添加一次 (processId, stageId 唯一)
 *   - 阶段顺序可在起止阶段之间自由排列
 *   - 起止阶段不可单独删除
 */

import { Router } from 'express';
import { prisma } from '../app.js';
import { AppError } from '../middleware/error.middleware.js';

const router = Router();

// ====== 列表（按 processId 过滤） ======
router.get('/', async (req, res, next) => {
  try {
    const { processId } = req.query;
    if (!processId) throw new AppError('processId 必填', 400);
    const links = await prisma.processStageLink.findMany({
      where: { processId: String(processId) },
      orderBy: { orderIndex: 'asc' },
      include: {
        stage: true,
        rule: true,
        condition: { include: { items: { orderBy: { orderIndex: 'asc' } } } },
      },
    });
    res.json({ success: true, data: links });
  } catch (e) { next(e); }
});

// ====== 详情 ======
router.get('/:id', async (req, res, next) => {
  try {
    const link = await prisma.processStageLink.findUnique({
      where: { id: req.params.id },
      include: {
        stage: true,
        rule: true,
        condition: { include: { items: true } },
        process: { select: { id: true, name: true, code: true } },
      },
    });
    if (!link) return res.status(404).json({ success: false, message: '关联不存在' });
    res.json({ success: true, data: link });
  } catch (e) { next(e); }
});

// ====== 添加阶段到流程 ======
router.post('/', async (req, res, next) => {
  try {
    const { processId, stageId, orderIndex, customName, stageLimit } = req.body;
    if (!processId || !stageId) throw new AppError('processId / stageId 必填', 400);

    // 校验 - 流程存在
    const process = await prisma.recruitmentProcess.findUnique({ where: { id: processId } });
    if (!process) throw new AppError('流程不存在', 404);

    // 校验 - 阶段存在且启用
    const stage = await prisma.recruitmentStage.findUnique({ where: { id: stageId } });
    if (!stage) throw new AppError('阶段不存在', 404);
    if (stage.status !== 'ACTIVE') throw new AppError('该阶段未启用，无法添加到流程', 400);

    // 校验 - 同一流程内不可重复 (#3.2 业务规则)
    const existing = await prisma.processStageLink.findUnique({
      where: { processId_stageId: { processId, stageId } },
    });
    if (existing) throw new AppError('该阶段已在当前流程中', 400);

    // 计算 orderIndex: 插到结束阶段之前
    let finalOrder = orderIndex;
    if (finalOrder === undefined || finalOrder === null) {
      const endLink = await prisma.processStageLink.findFirst({
        where: { processId, isEnd: true },
        orderBy: { orderIndex: 'desc' },
      });
      finalOrder = endLink ? endLink.orderIndex : 9999;
    }

    const link = await prisma.processStageLink.create({
      data: {
        processId,
        stageId,
        orderIndex: finalOrder,
        customName,
        stageLimit,
      },
      include: { stage: true },
    });
    res.status(201).json({ success: true, data: link });
  } catch (e) { next(e); }
});

// ====== 更新 link ======
router.put('/:id', async (req, res, next) => {
  try {
    const link = await prisma.processStageLink.findUnique({ where: { id: req.params.id } });
    if (!link) throw new AppError('关联不存在', 404);
    if ((link.isStart || link.isEnd) && (req.body.customName !== undefined)) {
      // 起止阶段允许改 customName
    }
    const updated = await prisma.processStageLink.update({
      where: { id: req.params.id },
      data: {
        ...(req.body.customName !== undefined && { customName: req.body.customName }),
        ...(req.body.orderIndex !== undefined && { orderIndex: req.body.orderIndex }),
        ...(req.body.stageLimit !== undefined && { stageLimit: req.body.stageLimit }),
        ...(req.body.status !== undefined && { status: req.body.status }),
      },
    });
    res.json({ success: true, data: updated });
  } catch (e) { next(e); }
});

// ====== 批量调整顺序 ======
router.put('/reorder', async (req, res, next) => {
  try {
    const { processId, orderedLinkIds } = req.body;
    if (!processId || !Array.isArray(orderedLinkIds)) {
      throw new AppError('processId / orderedLinkIds 必填', 400);
    }
    // 起止阶段不参与排序 - 保留在两端
    const updates = orderedLinkIds.map((id, idx) =>
      prisma.processStageLink.update({
        where: { id },
        data: { orderIndex: idx + 1 },
      })
    );
    await prisma.$transaction(updates);
    res.json({ success: true });
  } catch (e) { next(e); }
});

// ====== 从流程中移除 ======
router.delete('/:id', async (req, res, next) => {
  try {
    const link = await prisma.processStageLink.findUnique({ where: { id: req.params.id } });
    if (!link) throw new AppError('关联不存在', 404);
    if (link.isStart || link.isEnd) {
      throw new AppError('起止阶段不可从流程中移除', 400);
    }
    await prisma.processStageLink.delete({ where: { id: req.params.id } });
    res.json({ success: true });
  } catch (e) { next(e); }
});

export default router;
