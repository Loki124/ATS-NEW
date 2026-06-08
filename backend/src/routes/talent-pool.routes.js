/**
 * 人才库路由 - PRD G32 (6 子库完整 CRUD)
 *
 * 路由:
 *   GET    /api/talent-pool/types          - 6 子库定义
 *   GET    /api/talent-pool/stats          - 6 子库统计
 *   GET    /api/talent-pool/pool/:poolCode - 子库候选人列表 (分页)
 *   POST   /api/talent-pool/pool/:poolCode/move - 把候选人移入该子库 (写审计)
 *   GET    /api/talent-pool/candidates     - 跨池候选人查询 (兼容旧)
 *   GET    /api/talent-pool/               - 模块元信息
 */

import { Router } from 'express'
import { prisma } from '../app.js'
import {
  TALENT_POOL_TYPES,
  listPoolStats,
  listCandidatesInPool,
  moveCandidateToPool,
} from '../services/talent-pool.service.js'

const router = Router()

/**
 * 6 子库枚举
 */
router.get('/types', (req, res) => {
  res.json({ success: true, data: TALENT_POOL_TYPES })
})

/**
 * 6 子库统计
 */
router.get('/stats', async (req, res, next) => {
  try {
    const stats = await listPoolStats()
    res.json({
      success: true,
      data: {
        pools: Object.values(TALENT_POOL_TYPES),
        stats,
      },
    })
  } catch (e) { next(e) }
})

/**
 * 子库候选人列表 (分页)
 */
router.get('/pool/:poolCode', async (req, res, next) => {
  try {
    const { poolCode } = req.params
    if (!TALENT_POOL_TYPES[poolCode]) {
      return res.status(400).json({ success: false, message: `Unknown pool: ${poolCode}` })
    }
    const page = parseInt(req.query.page) || 1
    const pageSize = parseInt(req.query.pageSize) || 20
    const list = await listCandidatesInPool(poolCode, { page, pageSize })
    res.json({ success: true, data: { list, pagination: { page, pageSize } } })
  } catch (e) { next(e) }
})

/**
 * 把候选人移动到指定子库 (写审计)
 *   POST /api/talent-pool/pool/PASSIVE/move
 *   body: { candidateId, reason }
 */
router.post('/pool/:poolCode/move', async (req, res, next) => {
  try {
    const { poolCode } = req.params
    if (!TALENT_POOL_TYPES[poolCode]) {
      return res.status(400).json({ success: false, message: `Unknown pool: ${poolCode}` })
    }
    const { candidateId, reason } = req.body || {}
    if (!candidateId) {
      return res.status(400).json({ success: false, message: 'candidateId required' })
    }
    const operatorId = req.user?.id || req.user?.userId || 'system'
    const updated = await moveCandidateToPool(candidateId, poolCode, reason || '', operatorId)
    res.json({ success: true, data: updated })
  } catch (e) {
    if (String(e.message).startsWith('Unknown pool')) {
      return res.status(400).json({ success: false, message: e.message })
    }
    next(e)
  }
})

/**
 * 跨池候选人查询 (兼容旧)
 */
router.get('/candidates', async (req, res, next) => {
  try {
    const { page = 1, pageSize = 20, status } = req.query
    const where = {}
    if (status) where.candidateStatus = status

    const [list, total] = await Promise.all([
      prisma.candidate.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip: (Number(page) - 1) * Number(pageSize),
        take: Number(pageSize),
      }),
      prisma.candidate.count({ where }),
    ])

    res.json({
      success: true,
      data: { list, pagination: { page: Number(page), pageSize: Number(pageSize), total } },
    })
  } catch (e) { next(e) }
})

/**
 * 根路径 - 模块元信息
 */
router.get('/', (req, res) => {
  res.json({
    success: true,
    data: {
      module: 'talent-pool',
      description: '人才库 (PRD G32 6 子库完整 CRUD)',
      endpoints: [
        'GET    /api/talent-pool/types',
        'GET    /api/talent-pool/stats',
        'GET    /api/talent-pool/pool/:poolCode',
        'POST   /api/talent-pool/pool/:poolCode/move',
        'GET    /api/talent-pool/candidates',
      ],
      pools: Object.values(TALENT_POOL_TYPES),
    },
  })
})

export default router
