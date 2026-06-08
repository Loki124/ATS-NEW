// G40 - 外部同步 API
// 资源:
//   POST /api/external-sync/sync/:companyId/:system  手动触发同步
//   GET  /api/external-sync/syncs                    查询同步状态
//   POST /api/external-sync/syncs/:id/retry          重试失败

import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import {
  syncCompany,
  listSyncs,
  retryFailed,
} from '../services/external-sync.service.js';

const router = Router();
router.use(authMiddleware);

router.post('/sync/:companyId/:system', async (req, res, next) => {
  try {
    const data = await syncCompany(
      req.params.companyId,
      req.params.system,
      req.user.id
    );
    res.json({ success: true, data });
  } catch (err) {
    next(err);
  }
});

router.get('/syncs', async (req, res, next) => {
  try {
    const data = await listSyncs({
      system: req.query.system,
      status: req.query.status,
    });
    res.json({ success: true, data });
  } catch (err) {
    next(err);
  }
});

router.post('/syncs/:id/retry', async (req, res, next) => {
  try {
    const data = await retryFailed(req.params.id, req.user.id);
    res.json({ success: true, data });
  } catch (err) {
    next(err);
  }
});

export default router;
