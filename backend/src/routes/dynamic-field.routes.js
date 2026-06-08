/**
 * G42 - 动态字段定义 路由
 * GET    /api/dynamic-fields/:resource/fields
 * GET    /api/dynamic-fields/:resource/fields/:key
 * POST   /api/dynamic-fields/:resource/fields
 * DELETE /api/dynamic-fields/:resource/fields/:id
 * PUT    /api/dynamic-fields/:resource/fields/reorder
 */

import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import {
  listFieldsForResource, getFieldByKey, getFieldWithOptions,
  upsertField, deleteField, reorderFields, validateFieldValue,
} from '../services/dynamic-field.service.js';

const router = Router();
router.use(authMiddleware);

router.get('/:resource/fields', async (req, res, next) => {
  try {
    const data = await listFieldsForResource(req.params.resource);
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/:resource/fields/:key', async (req, res, next) => {
  try {
    const data = await getFieldByKey(req.params.resource, req.params.key);
    if (!data) return res.status(404).json({ success: false, message: '字段不存在' });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.post('/:resource/fields', async (req, res, next) => {
  try {
    const data = await upsertField({ ...req.body, resource: req.params.resource });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.delete('/:resource/fields/:id', async (req, res, next) => {
  try {
    await deleteField(req.params.id);
    res.json({ success: true });
  } catch (err) { next(err); }
});

router.put('/:resource/fields/reorder', async (req, res, next) => {
  try {
    await reorderFields(req.body.orderedIds || []);
    res.json({ success: true });
  } catch (err) { next(err); }
});

// 工具端点: 校验字段值 (前端录入时实时校验)
router.post('/:resource/fields/:id/validate', async (req, res, next) => {
  try {
    const field = await getFieldWithOptions(req.params.id);
    if (!field) return res.status(404).json({ success: false, message: '字段不存在' });
    const valid = validateFieldValue(field, req.body.value);
    res.json({ success: true, data: { valid } });
  } catch (err) { next(err); }
});

export default router;
