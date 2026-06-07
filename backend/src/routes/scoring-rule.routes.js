/**
 * 评分规则路由 - PRD G39
 *
 * 资源：
 *   GET    /api/scoring-rules                    列表
 *   GET    /api/scoring-rules/:id                详情 (含 conditions + results)
 *   POST   /api/scoring-rules                    创建
 *   PUT    /api/scoring-rules/:id                更新
 *   DELETE /api/scoring-rules/:id                删除
 *   POST   /api/scoring-rules/:id/evaluate       评估候选人 (核心 G39)
 *   POST   /api/scoring-rules/evaluate-batch     批量评估
 */

import { Router } from 'express'
import { prisma } from '../app.js'
import { AppError } from '../middleware/error.middleware.js'
import {
  SCORING_RULE_TYPES,
  SCORING_RULE_TYPE_LABEL,
  evaluateCandidateForRule,
  listScoringRules,
  getScoringRule,
  createScoringRule,
  updateScoringRule,
  deleteScoringRule,
} from '../services/scoring-rule.service.js'

const router = Router()

// ====== 列表 ======
router.get('/', async (req, res, next) => {
  try {
    const { status, page, pageSize } = req.query
    const data = await listScoringRules({ status, page, pageSize })
    res.json({ success: true, data })
  } catch (e) { next(e) }
})

// ====== 详情 ======
router.get('/:id', async (req, res, next) => {
  try {
    const rule = await getScoringRule(req.params.id)
    if (!rule) return res.status(404).json({ success: false, message: '评分规则不存在' })
    res.json({ success: true, data: rule })
  } catch (e) { next(e) }
})

// ====== 创建 ======
router.post('/', async (req, res, next) => {
  try {
    const { name, code, description, ruleType, status, applicableRange } = req.body || {}
    if (!name) throw new AppError('name 必填', 400)
    if (!code) throw new AppError('code 必填', 400)
    if (!Object.values(SCORING_RULE_TYPES).includes(ruleType || '')) {
      throw new AppError(`ruleType 必须是 ${Object.values(SCORING_RULE_TYPES).join('/')}`, 400)
    }
    const existing = await prisma.scoringRule.findUnique({ where: { code } })
    if (existing) throw new AppError('code 已存在', 409)
    const rule = await createScoringRule({
      name, code, description, ruleType, status, applicableRange,
    })
    res.status(201).json({ success: true, data: rule })
  } catch (e) { next(e) }
})

// ====== 更新 ======
router.put('/:id', async (req, res, next) => {
  try {
    const rule = await getScoringRule(req.params.id)
    if (!rule) return res.status(404).json({ success: false, message: '评分规则不存在' })
    const allowed = ['name', 'description', 'ruleType', 'status', 'applicableRange']
    const data = {}
    for (const k of allowed) {
      if (req.body[k] !== undefined) data[k] = req.body[k]
    }
    const updated = await updateScoringRule(req.params.id, data)
    res.json({ success: true, data: updated })
  } catch (e) { next(e) }
})

// ====== 删除 ======
router.delete('/:id', async (req, res, next) => {
  try {
    await deleteScoringRule(req.params.id)
    res.json({ success: true })
  } catch (e) {
    if (e.code === 'P2025') return res.status(404).json({ success: false, message: '评分规则不存在' })
    next(e)
  }
})

// ====== 评估候选人 (核心 G39) ======
router.post('/:id/evaluate', async (req, res, next) => {
  try {
    const context = req.body || {}
    const result = await evaluateCandidateForRule(req.params.id, context)
    res.json({ success: true, data: result })
  } catch (e) { next(e) }
})

// ====== 批量评估 ======
router.post('/evaluate-batch', async (req, res, next) => {
  try {
    const { ruleId, candidates } = req.body || {}
    if (!ruleId) throw new AppError('ruleId 必填', 400)
    if (!Array.isArray(candidates) || candidates.length === 0) {
      throw new AppError('candidates 必填且非空', 400)
    }
    const results = await Promise.all(
      candidates.map(async (c) => ({
        candidateId: c.candidateId || c.id,
        ...(await evaluateCandidateForRule(ruleId, c.context || {})),
      })),
    )
    res.json({ success: true, data: results })
  } catch (e) { next(e) }
})

export default router
