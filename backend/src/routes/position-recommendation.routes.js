/**
 * position-recommendation.routes.js - PRD G31
 * 双向推荐 API:
 *   GET /api/recommendations/positions/for-candidate/:candidateId
 *   GET /api/recommendations/candidates/for-position/:positionId
 */

import { Router } from 'express'
import { authMiddleware } from '../middleware/auth.middleware.js'
import {
  recommendPositionsForCandidate,
  recommendCandidatesForPosition,
} from '../services/position-matcher.service.js'

const router = Router()
router.use(authMiddleware)

router.get('/positions/for-candidate/:candidateId', async (req, res, next) => {
  try {
    const limit = parseInt(req.query.limit) || 10
    const data = await recommendPositionsForCandidate(req.params.candidateId, { limit })
    res.json({ success: true, data })
  } catch (err) { next(err) }
})

router.get('/candidates/for-position/:positionId', async (req, res, next) => {
  try {
    const limit = parseInt(req.query.limit) || 10
    const data = await recommendCandidatesForPosition(req.params.positionId, { limit })
    res.json({ success: true, data })
  } catch (err) { next(err) }
})

export default router
