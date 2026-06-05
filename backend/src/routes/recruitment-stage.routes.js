/**
 * 阶段配置路由（全局阶段模板库） - PRD #4
 *
 * 重要：阶段是**全局模板**，不属于任何流程
 * 流程通过 ProcessStageLink 关联到阶段
 *
 * 资源：
 *   GET    /api/recruitment-stages            列表（全局，可按 type/status 过滤）
 *   GET    /api/recruitment-stages/:id        详情
 *   POST   /api/recruitment-stages            新增全局阶段
 *   PUT    /api/recruitment-stages/:id        更新全局阶段
 *   DELETE /api/recruitment-stages/:id        删除全局阶段
 *   POST   /api/recruitment-stages/:id/copy   复制阶段
 *
 * 业务规则 (#4.2)：
 *   - 系统预置阶段 (isSystem=true) 不可停用 / 删除
 *   - 阶段被流程引用时不可停用 / 删除 (需先解除所有 ProcessStageLink)
 *   - 编号: P + 3 位流水号（全局唯一）
 */

import { Router } from 'express';
import { prisma } from '../app.js';
import { AppError } from '../middleware/error.middleware.js';

const router = Router();

// ====== 列表（全局） ======
router.get('/', async (req, res, next) => {
  try {
    const { status, stageType, keyword } = req.query;
    const where = {};
    if (status) where.status = status;
    if (stageType) where.stageType = stageType;
    if (keyword) {
      where.OR = [
        { name: { contains: keyword } },
        { code: { contains: keyword } },
      ];
    }
    // 附带被多少个流程引用
    const stages = await prisma.recruitmentStage.findMany({
      where,
      orderBy: { code: 'asc' },
      include: {
        _count: { select: { links: true } },
      },
    });
    res.json({ success: true, data: stages });
  } catch (e) { next(e); }
});

// ====== 详情 ======
router.get('/:id', async (req, res, next) => {
  try {
    const stage = await prisma.recruitmentStage.findUnique({
      where: { id: req.params.id },
      include: {
        _count: { select: { links: true } },
        links: {
          include: { process: { select: { id: true, name: true, code: true } } },
        },
      },
    });
    if (!stage) return res.status(404).json({ success: false, message: '阶段不存在' });
    res.json({ success: true, data: stage });
  } catch (e) { next(e); }
});

// ====== 新增（全局） ======
router.post('/', async (req, res, next) => {
  try {
    const { name, stageType, features, description, stageLimit } = req.body;
    if (!name || !stageType) throw new AppError('name / stageType 必填', 400);

    // 编号: P + 3 位全局唯一流水号
    const last = await prisma.recruitmentStage.findFirst({
      where: { code: { startsWith: 'P' } },
      orderBy: { code: 'desc' },
    });
    const nextNum = last ? parseInt(last.code.slice(1)) + 1 : 1;
    const code = 'P' + String(nextNum).padStart(3, '0');

    const stage = await prisma.recruitmentStage.create({
      data: {
        code,
        name,
        stageType,
        features: features || [],
        description,
        stageLimit,
        isSystem: false,
      },
    });
    res.status(201).json({ success: true, data: stage });
  } catch (e) { next(e); }
});

// ====== 更新 ======
router.put('/:id', async (req, res, next) => {
  try {
    const stage = await prisma.recruitmentStage.findUnique({ where: { id: req.params.id } });
    if (!stage) throw new AppError('阶段不存在', 404);
    if (stage.isSystem && (req.body.name !== undefined || req.body.stageType !== undefined)) {
      throw new AppError('系统预置阶段不可修改名称/类型', 400);
    }
    const updated = await prisma.recruitmentStage.update({
      where: { id: req.params.id },
      data: {
        ...(req.body.name !== undefined && { name: req.body.name }),
        ...(req.body.stageType !== undefined && { stageType: req.body.stageType }),
        ...(req.body.features !== undefined && { features: req.body.features }),
        ...(req.body.description !== undefined && { description: req.body.description }),
        ...(req.body.stageLimit !== undefined && { stageLimit: req.body.stageLimit }),
        ...(req.body.status !== undefined && { status: req.body.status }),
      },
    });
    res.json({ success: true, data: updated });
  } catch (e) { next(e); }
});

// ====== 删除 ======
router.delete('/:id', async (req, res, next) => {
  try {
    const stage = await prisma.recruitmentStage.findUnique({
      where: { id: req.params.id },
      include: { _count: { select: { links: true } } },
    });
    if (!stage) throw new AppError('阶段不存在', 404);
    if (stage.isSystem) throw new AppError('系统预置阶段不可删除', 400);
    if (stage._count.links > 0) {
      throw new AppError(
        `当前阶段被 ${stage._count.links} 个流程引用，无法删除。请先在流程中移除该阶段。`,
        400
      );
    }
    await prisma.recruitmentStage.delete({ where: { id: req.params.id } });
    res.json({ success: true });
  } catch (e) { next(e); }
});

// ====== 复制 ======
router.post('/:id/copy', async (req, res, next) => {
  try {
    const src = await prisma.recruitmentStage.findUnique({ where: { id: req.params.id } });
    if (!src) throw new AppError('原阶段不存在', 404);

    const last = await prisma.recruitmentStage.findFirst({
      where: { code: { startsWith: 'P' } },
      orderBy: { code: 'desc' },
    });
    const nextNum = last ? parseInt(last.code.slice(1)) + 1 : 1;
    const code = 'P' + String(nextNum).padStart(3, '0');

    const created = await prisma.recruitmentStage.create({
      data: {
        code,
        name: `${src.name} - 副本`,
        stageType: src.stageType,
        features: src.features,
        description: src.description,
        stageLimit: src.stageLimit,
        isSystem: false, // 复制的不是系统预置
      },
    });
    res.status(201).json({ success: true, data: created });
  } catch (e) { next(e); }
});

// ====== 启用/停用 ======
router.put('/:id/status', async (req, res, next) => {
  try {
    const { status } = req.body;
    if (!['ACTIVE', 'INACTIVE'].includes(status)) throw new AppError('状态值无效', 400);

    const stage = await prisma.recruitmentStage.findUnique({
      where: { id: req.params.id },
      include: { _count: { select: { links: true } } },
    });
    if (!stage) throw new AppError('阶段不存在', 404);
    if (stage.isSystem) throw new AppError('系统预置阶段不可停用', 400);
    if (status === 'INACTIVE' && stage._count.links > 0) {
      throw new AppError(`当前阶段被 ${stage._count.links} 个流程引用，无法停用`, 400);
    }
    const updated = await prisma.recruitmentStage.update({
      where: { id: req.params.id },
      data: { status },
    });
    res.json({ success: true, data: updated });
  } catch (e) { next(e); }
});

export default router;
