import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import { listRules, getMatrix, upsertRule, deleteRule, queryAudit } from '../services/field-acl.service.js';

const router = Router();
router.use(authMiddleware);

// 规则列表
router.get('/rules', async (req, res, next) => {
  try {
    const data = await listRules({ resource: req.query.resource, roleCode: req.query.roleCode });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

// 矩阵 (供 UI 渲染)
router.get('/matrix', async (req, res, next) => {
  try {
    const data = await getMatrix();
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

// upsert 规则
router.post('/rules', async (req, res, next) => {
  try {
    const data = await upsertRule(req.body);
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.put('/rules/:id', async (req, res, next) => {
  try {
    const data = await upsertRule({ ...req.body, roleId: req.params.id });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.delete('/rules/:id', async (req, res, next) => {
  try {
    await deleteRule(req.params.id);
    res.json({ success: true });
  } catch (err) { next(err); }
});

// 审计查询
router.get('/audit', async (req, res, next) => {
  try {
    const data = await queryAudit({
      userId: req.query.userId,
      resource: req.query.resource,
      field: req.query.field,
      limit: parseInt(req.query.limit) || 50,
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

export default router;
