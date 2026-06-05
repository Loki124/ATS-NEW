/**
 * 招聘流程管理路由 - PRD G38 (P0)
 * 资源：
 *   GET    /api/recruitment-processes        列表（含阶段数/状态/最后修改）
 *   GET    /api/recruitment-processes/:id    详情（含完整 stages/rules/conditions）
 *   POST   /api/recruitment-processes        创建（含默认起止阶段）
 *   PUT    /api/recruitment-processes/:id    更新（含适用范围/校验开关等）
 *   DELETE /api/recruitment-processes/:id    删除（需无候选人关联）
 *   POST   /api/recruitment-processes/:id/copy  复制流程
 *   PUT    /api/recruitment-processes/:id/status  启用/停用
 */

import { Router } from 'express';
import { prisma } from '../app.js';
import { AppError } from '../middleware/error.middleware.js';

const router = Router();

// ====== 列表 ======
router.get('/', async (req, res, next) => {
  try {
    const { status, keyword } = req.query;
    const where = {};
    if (status) where.status = status;
    if (keyword) where.name = { contains: keyword };

    const processes = await prisma.recruitmentProcess.findMany({
      where,
      include: {
        _count: { select: { links: true, stageRules: true, autoRules: true } },
        updater: { select: { id: true, realName: true, username: true } },
      },
      orderBy: { updatedAt: 'desc' },
    });
    res.json({ success: true, data: processes });
  } catch (e) { next(e); }
});

// ====== 详情 ======
router.get('/:id', async (req, res, next) => {
  try {
    const p = await prisma.recruitmentProcess.findUnique({
      where: { id: req.params.id },
      include: {
        links: {
          orderBy: { orderIndex: 'asc' },
          include: {
            stage: true,
            rule: true,
            condition: { include: { items: { orderBy: { orderIndex: 'asc' } } } },
          },
        },
        autoRules: { orderBy: { ruleType: 'asc' } },
        creator: { select: { id: true, realName: true, username: true } },
        updater: { select: { id: true, realName: true, username: true } },
      },
    });
    if (!p) return res.status(404).json({ success: false, message: '流程不存在' });
    res.json({ success: true, data: p });
  } catch (e) { next(e); }
});

// ====== 创建（自动添加起止两阶段 link） ======
router.post('/', async (req, res, next) => {
  try {
    const { name, description, applicableDepartments, applicablePositionLevels,
            applicableUserIds, applicableJobs, applicableMode = 'ALL',
            validateResumeScore = true, failPrompt, createdBy } = req.body;
    if (!name) throw new AppError('流程名称必填', 400);

    // 编号: F + 3 位流水号
    const last = await prisma.recruitmentProcess.findFirst({
      where: { code: { startsWith: 'F' } },
      orderBy: { code: 'desc' },
    });
    const nextNum = last ? parseInt(last.code.slice(1)) + 1 : 1;
    const code = 'F' + String(nextNum).padStart(3, '0');

    // 找到（或创建）系统预置的 2 个全局阶段模板 - 起止
    const sysStages = await ensureSystemStages(prisma);

    const created = await prisma.recruitmentProcess.create({
      data: {
        code,
        name,
        description,
        applicableDepartments,
        applicablePositionLevels,
        applicableUserIds,
        applicableJobs,
        applicableMode,
        validateResumeScore,
        failPrompt,
        createdBy,
        // 创建时自动 link 起止两个系统预置阶段
        links: {
          create: [
            {
              stageId: sysStages.start.id,
              orderIndex: 0,
              isStart: true,
            },
            {
              stageId: sysStages.end.id,
              orderIndex: 9999,
              isEnd: true,
            },
          ],
        },
      },
      include: { links: { include: { stage: true } } },
    });
    res.status(201).json({ success: true, data: created });
  } catch (e) { next(e); }
});

/**
 * 确保系统预置的 2 个全局阶段模板存在
 * - P001 初评 (FILTER)
 * - P002 正式录用 (ONBOARDING)
 * 不存在则创建，存在则返回
 */
async function ensureSystemStages(prisma) {
  const startCode = 'P001';
  const endCode = 'P002';
  let start = await prisma.recruitmentStage.findUnique({ where: { code: startCode } });
  if (!start) {
    start = await prisma.recruitmentStage.create({
      data: {
        code: startCode,
        name: '初评',
        stageType: 'FILTER',
        features: ['INVITE_FILTER', 'INVITE_UPDATE_INFO', 'TRANSFER_STAGE', 'ARCHIVE'],
        isSystem: true,
        description: '系统预置起始阶段 - 候选人初次评估',
      },
    });
  }
  let end = await prisma.recruitmentStage.findUnique({ where: { code: endCode } });
  if (!end) {
    end = await prisma.recruitmentStage.create({
      data: {
        code: endCode,
        name: '正式录用',
        stageType: 'ONBOARDING',
        features: ['START_ONBOARDING', 'TRANSFER_STAGE', 'ARCHIVE'],
        isSystem: true,
        description: '系统预置结束阶段 - 候选人正式入职',
      },
    });
  }
  return { start, end };
}

// ====== 更新 ======
router.put('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const updates = req.body;
    const updated = await prisma.recruitmentProcess.update({
      where: { id },
      data: {
        ...(updates.name !== undefined && { name: updates.name }),
        ...(updates.description !== undefined && { description: updates.description }),
        ...(updates.applicableDepartments !== undefined && { applicableDepartments: updates.applicableDepartments }),
        ...(updates.applicablePositionLevels !== undefined && { applicablePositionLevels: updates.applicablePositionLevels }),
        ...(updates.applicableUserIds !== undefined && { applicableUserIds: updates.applicableUserIds }),
        ...(updates.applicableJobs !== undefined && { applicableJobs: updates.applicableJobs }),
        ...(updates.applicableMode !== undefined && { applicableMode: updates.applicableMode }),
        ...(updates.validateResumeScore !== undefined && { validateResumeScore: updates.validateResumeScore }),
        ...(updates.failPrompt !== undefined && { failPrompt: updates.failPrompt }),
        updatedBy: req.user?.id,
      },
    });
    res.json({ success: true, data: updated });
  } catch (e) { next(e); }
});

// ====== 删除 ======
router.delete('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    // 检查是否有职位引用了此流程
    const usage = await prisma.position.count({ where: { processId: id } });
    if (usage > 0) {
      throw new AppError(`当前流程被 ${usage} 个职位引用，无法删除`, 400);
    }
    await prisma.recruitmentProcess.delete({ where: { id } });
    res.json({ success: true });
  } catch (e) { next(e); }
});

// ====== 复制 ======
router.post('/:id/copy', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { newName, createdBy } = req.body;
    const src = await prisma.recruitmentProcess.findUnique({
      where: { id },
      include: { links: true },
    });
    if (!src) throw new AppError('原流程不存在', 404);

    // 新编号
    const last = await prisma.recruitmentProcess.findFirst({
      where: { code: { startsWith: 'F' } },
      orderBy: { code: 'desc' },
    });
    const nextNum = last ? parseInt(last.code.slice(1)) + 1 : 1;
    const newCode = 'F' + String(nextNum).padStart(3, '0');

    // 确保系统阶段存在
    const sysStages = await ensureSystemStages(prisma);

    // 复制 link - 引用相同的 stage，不复制 stageRule/condition
    const created = await prisma.recruitmentProcess.create({
      data: {
        code: newCode,
        name: newName || `${src.name} - 副本`,
        description: src.description,
        applicableDepartments: src.applicableDepartments,
        applicablePositionLevels: src.applicablePositionLevels,
        applicableUserIds: src.applicableUserIds,
        applicableJobs: src.applicableJobs,
        applicableMode: src.applicableMode,
        validateResumeScore: src.validateResumeScore,
        failPrompt: src.failPrompt,
        createdBy,
        // 先建不带 link 的 process
      },
    });

    // 然后建 links - 优先用原 src.links；如 src 没有 link（理论上必有起止），用系统起止
    if (src.links && src.links.length > 0) {
      await prisma.processStageLink.createMany({
        data: src.links.map((l) => ({
          processId: created.id,
          stageId: l.stageId,
          orderIndex: l.orderIndex,
          customName: l.customName,
          stageLimit: l.stageLimit,
          isStart: l.isStart,
          isEnd: l.isEnd,
        })),
      });
    } else {
      await prisma.processStageLink.createMany({
        data: [
          { processId: created.id, stageId: sysStages.start.id, orderIndex: 0, isStart: true },
          { processId: created.id, stageId: sysStages.end.id, orderIndex: 9999, isEnd: true },
        ],
      });
    }

    const full = await prisma.recruitmentProcess.findUnique({
      where: { id: created.id },
      include: { links: { include: { stage: true } } },
    });
    res.status(201).json({ success: true, data: full });
  } catch (e) { next(e); }
});

// ====== 启用/停用 ======
router.put('/:id/status', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { status } = req.body;
    if (!['ACTIVE', 'INACTIVE'].includes(status)) {
      throw new AppError('状态值无效', 400);
    }
    // 启用前检查 - 流程内 link 数量限制（至少需要起止 2 个 link）
    if (status === 'ACTIVE') {
      const linkCount = await prisma.processStageLink.count({ where: { processId: id } });
      if (linkCount < 2) {
        throw new AppError('至少需要 2 个阶段链接（起止）', 400);
      }
    }
    const updated = await prisma.recruitmentProcess.update({
      where: { id },
      data: { status, updatedBy: req.user?.id },
    });
    res.json({ success: true, data: updated });
  } catch (e) { next(e); }
});

export default router;
