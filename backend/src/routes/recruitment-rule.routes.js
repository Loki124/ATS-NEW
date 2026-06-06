/**
 * 阶段规则 / 进入条件 / 自动归档规则 路由
 * - GET    /api/stage-rules?linkId=...
 * - POST   /api/stage-rules
 * - PUT    /api/stage-rules/:id
 * - DELETE /api/stage-rules/:id
 *
 * - GET    /api/entry-conditions?linkId=...
 * - POST   /api/entry-conditions
 * - PUT    /api/entry-conditions/:id
 * - POST   /api/entry-conditions/:id/items   增/改/删 条件项
 * - DELETE /api/entry-conditions/:id
 *
 * - GET    /api/auto-archive-rules?processId=...
 * - POST   /api/auto-archive-rules
 * - PUT    /api/auto-archive-rules/:id
 * - DELETE /api/auto-archive-rules/:id
 */

import { Router } from 'express';
import { prisma } from '../app.js';
import { AppError } from '../middleware/error.middleware.js';
import { evaluateConditionTree, buildFailedPrompt } from '../services/recruitment-condition.service.js';
import {
  evaluateCandidateForStage,
  evaluateCandidateForStages,
  checkStageTransitionAllowed,
} from '../services/candidate-condition.service.js';

const router = Router();

// ============================================================
// 阶段规则 (#7)
// ============================================================
router.get('/stage-rules', async (req, res, next) => {
  try {
    const { linkId, processId } = req.query;
    const where = {};
    if (linkId) where.linkId = linkId;
    if (processId) where.processId = processId;
    const rules = await prisma.stageRule.findMany({ where });
    res.json({ success: true, data: rules });
  } catch (e) { next(e); }
});

router.post('/stage-rules', async (req, res, next) => {
  try {
    const { linkId, ...data } = req.body;
    if (!linkId) throw new AppError('linkId 必填', 400);
    // 查 stage 拿 processId
    const stage = await prisma.processStageLink.findUnique({ where: { id: linkId } });
    if (!stage) throw new AppError('阶段不存在', 404);
    // upsert
    const rule = await prisma.stageRule.upsert({
      where: { linkId },
      update: { ...data },
      create: { linkId, processId: stage.processId, ...data },
    });
    res.status(201).json({ success: true, data: rule });
  } catch (e) { next(e); }
});

router.put('/stage-rules/:id', async (req, res, next) => {
  try {
    const rule = await prisma.stageRule.update({
      where: { id: req.params.id },
      data: req.body,
    });
    res.json({ success: true, data: rule });
  } catch (e) { next(e); }
});

router.delete('/stage-rules/:id', async (req, res, next) => {
  try {
    await prisma.stageRule.delete({ where: { id: req.params.id } });
    res.json({ success: true });
  } catch (e) { next(e); }
});

// ============================================================
// 进入条件 (#5)
// ============================================================
router.get('/entry-conditions', async (req, res, next) => {
  try {
    const { linkId, processId } = req.query;
    const where = {};
    if (linkId) where.linkId = linkId;
    if (processId) where.processId = processId;
    const conds = await prisma.entryCondition.findMany({
      where,
      include: { items: { orderBy: { orderIndex: 'asc' } } },
    });
    res.json({ success: true, data: conds });
  } catch (e) { next(e); }
});

router.post('/entry-conditions', async (req, res, next) => {
  try {
    const { linkId, matchType = 'ALL', conditionType = 'MIXED', prompt, items = [] } = req.body;
    if (!linkId) throw new AppError('linkId 必填', 400);
    const stage = await prisma.processStageLink.findUnique({ where: { id: linkId } });
    if (!stage) throw new AppError('阶段不存在', 404);

    const cond = await prisma.entryCondition.upsert({
      where: { linkId },
      update: { matchType, conditionType, prompt },
      create: { linkId, processId: stage.processId, matchType, conditionType, prompt },
    });

    // 重建 items
    await prisma.conditionItem.deleteMany({ where: { entryConditionId: cond.id } });
    if (items.length > 0) {
      await prisma.conditionItem.createMany({
        data: items.map((it, idx) => ({
          entryConditionId: cond.id,
          parentId: it.parentId || null,
          relationToParent: it.relationToParent || null,
          field: it.field,
          operator: it.operator,
          value: it.value,
          refStageId: it.refStageId,
          refDictId: it.refDictId,
          orderIndex: idx,
        })),
      });
    }

    const full = await prisma.entryCondition.findUnique({
      where: { id: cond.id },
      include: { items: { orderBy: { orderIndex: 'asc' } } },
    });
    res.status(201).json({ success: true, data: full });
  } catch (e) { next(e); }
});

router.put('/entry-conditions/:id', async (req, res, next) => {
  try {
    const cond = await prisma.entryCondition.update({
      where: { id: req.params.id },
      data: req.body,
    });
    res.json({ success: true, data: cond });
  } catch (e) { next(e); }
});

router.delete('/entry-conditions/:id', async (req, res, next) => {
  try {
    const id = req.params.id;
    await prisma.conditionItem.deleteMany({ where: { entryConditionId: id } });
    await prisma.entryCondition.delete({ where: { id } });
    res.json({ success: true });
  } catch (e) { next(e); }
});

// 评估接口 (候选人转移阶段前调用)
router.post('/entry-conditions/:id/evaluate', async (req, res, next) => {
  try {
    const cond = await prisma.entryCondition.findUnique({
      where: { id: req.params.id },
      include: { items: { orderBy: { orderIndex: 'asc' } } },
    });
    if (!cond) return res.status(404).json({ success: false, message: '条件不存在' });

    // req.body 是候选人 + 前序阶段状态
    const context = req.body || {};
    const result = evaluateConditionTree(cond.items, cond.matchType, context);
    res.json({
      success: true,
      data: {
        passed: result.passed,
        failedItems: result.failedItems,
        prompt: result.passed ? null : buildFailedPrompt(cond.items, result.failedItems, context, cond.prompt),
      },
    });
  } catch (e) { next(e) }
});

// ============================================================
// 候选人进入条件 (PRD G10 + G1.5) - 候选人上下文的快捷入口
// ============================================================

/**
 * 评估候选人是否满足某条 EntryCondition
 * POST /api/recruitment-rules/candidates/:candidateId/evaluate
 * body: { entryConditionId, applicationId? }
 */
router.post('/candidates/:candidateId/evaluate', async (req, res, next) => {
  try {
    const { entryConditionId, applicationId } = req.body || {}
    if (!entryConditionId) return res.status(400).json({ success: false, message: 'entryConditionId 必填' })
    const result = await evaluateCandidateForStage(req.params.candidateId, entryConditionId, applicationId)
    res.json({ success: true, data: result })
  } catch (e) { next(e) }
})

/**
 * 批量评估候选人对多条 EntryCondition
 * POST /api/recruitment-rules/candidates/:candidateId/evaluate-batch
 * body: { entryConditionIds: string[], applicationId? }
 */
router.post('/candidates/:candidateId/evaluate-batch', async (req, res, next) => {
  try {
    const { entryConditionIds, applicationId } = req.body || {}
    if (!Array.isArray(entryConditionIds) || entryConditionIds.length === 0) {
      return res.status(400).json({ success: false, message: 'entryConditionIds 必填且非空' })
    }
    const results = await evaluateCandidateForStages(req.params.candidateId, entryConditionIds, applicationId)
    res.json({ success: true, data: results })
  } catch (e) { next(e) }
})

/**
 * 应用阶段转移前校验 (核心 G10 端点)
 * POST /api/recruitment-rules/applications/:applicationId/check-stage-transition
 * body: { entryConditionId? }   // 可选, 不传则用 application 的 link 上的条件
 */
router.post('/applications/:applicationId/check-stage-transition', async (req, res, next) => {
  try {
    const { entryConditionId } = req.body || {}
    const result = await checkStageTransitionAllowed(req.params.applicationId, entryConditionId)
    res.json({ success: true, data: result })
  } catch (e) { next(e) }
})

// ============================================================
// 自动归档规则 (#8)
// ============================================================
router.get('/auto-archive-rules', async (req, res, next) => {
  try {
    const { processId } = req.query;
    const where = {};
    if (processId) where.processId = processId;
    const rules = await prisma.autoArchiveRule.findMany({
      where,
      orderBy: { ruleType: 'asc' },
    });
    res.json({ success: true, data: rules });
  } catch (e) { next(e); }
});

router.post('/auto-archive-rules', async (req, res, next) => {
  try {
    const { processId, ruleType, enabled = true, config = {} } = req.body;
    if (!processId || !ruleType) throw new AppError('processId / ruleType 必填', 400);
    const validTypes = ['INVITE_FAIL', 'OFFER_FAIL', 'EVAL_FAIL', 'TIMEOUT_UNASSIGNED'];
    if (!validTypes.includes(ruleType)) throw new AppError(`ruleType 必须是 ${validTypes.join('|')}`, 400);

    const rule = await prisma.autoArchiveRule.upsert({
      where: { processId_ruleType: { processId, ruleType } },
      update: { enabled, config },
      create: { processId, ruleType, enabled, config },
    });
    res.status(201).json({ success: true, data: rule });
  } catch (e) { next(e); }
});

router.put('/auto-archive-rules/:id', async (req, res, next) => {
  try {
    const rule = await prisma.autoArchiveRule.update({
      where: { id: req.params.id },
      data: req.body,
    });
    res.json({ success: true, data: rule });
  } catch (e) { next(e); }
});

router.delete('/auto-archive-rules/:id', async (req, res, next) => {
  try {
    await prisma.autoArchiveRule.delete({ where: { id: req.params.id } });
    res.json({ success: true });
  } catch (e) { next(e); }
});

export default router;
