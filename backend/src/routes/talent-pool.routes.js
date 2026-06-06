/**
 * 人才库路由 - PRD G32 (6 子库 MVP)
 *
 * 当前实现: 复用候选人查询 (PRD G32 6 子库完整 CRUD 下个迭代)
 * 路由: GET /api/talent-pool/stats - 6 子库统计
 *       GET /api/talent-pool/candidates - 跨池查询候选人
 */

import { Router } from 'express'
import { prisma } from '../app.js'

const router = Router()

// 6 子库定义 (PRD G32)
const SUB_POOLS = [
  { key: 'PASSIVE', name: '被动库', description: '暂未投递的潜在候选人' },
  { key: 'ACTIVE', name: '主动库', description: '主动投递的候选人' },
  { key: 'HIRED', name: '已聘库', description: '已入职候选人储备' },
  { key: 'REJECTED', name: '已拒库', description: '不合适候选人(可重新激活)' },
  { key: 'BLACKLIST', name: '黑名单', description: '永不联系候选人' },
  { key: 'TALENT_POOL', name: '通用库', description: '其他通用储备' },
]

/**
 * 6 子库统计
 * 注: 当前 schema 没 pool 字段, 全部统计从 candidate.status 推算
 * 完整 G32 实现: 加 pool enum 字段 + 跨库转移 API
 */
router.get('/stats', async (req, res, next) => {
  try {
    const total = await prisma.candidate.count()
    const active = await prisma.candidate.count({ where: { candidateStatus: 'ACTIVE' } })
    const archived = await prisma.candidate.count({ where: { candidateStatus: 'ARCHIVED' } })
    res.json({
      success: true,
      data: {
        pools: SUB_POOLS,
        summary: { total, active, archived, blacklisted: 0 },
        note: '完整 6 子库 CRUD 待 G32 完整实现, 当前从 candidate.status 推算',
      },
    })
  } catch (e) { next(e) }
})

/**
 * 跨池查询候选人
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
 * 根路径 - 返回模块元信息
 */
router.get('/', (req, res) => {
  res.json({
    success: true,
    data: {
      module: 'talent-pool',
      description: '人才库 (PRD G32 6 子库)',
      endpoints: [
        'GET /api/talent-pool/stats - 6 子库统计',
        'GET /api/talent-pool/candidates - 跨池候选人查询',
      ],
      pools: SUB_POOLS,
      status: 'MVP - 6 子库 CRUD 计划下个迭代',
    },
  })
})

export default router
