/**
 * G35 - 数据中心路由 (KPI + 通用导出 + 订阅 CRUD)
 * 5 端点: GET /kpi, GET /export/:resource, POST /subscriptions, GET /subscriptions, DELETE /subscriptions/:id
 */
import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import { exportResource } from '../services/data-export.service.js';
import { getDashboardKpi } from '../services/data-dashboard.service.js';
import { prisma } from '../app.js';

const router = Router();
router.use(authMiddleware);

router.get('/kpi', async (req, res, next) => {
  try {
    const data = await getDashboardKpi();
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/export/:resource', async (req, res, next) => {
  try {
    const format = req.query.format || 'csv';
    const fields = req.query.fields ? req.query.fields.split(',') : undefined;
    const data = await exportResource(req.params.resource, format, fields);
    const filename = `${req.params.resource}-${Date.now()}.${format}`;
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.setHeader('Content-Type', format === 'csv' ? 'text/csv; charset=utf-8' : 'application/json');
    res.send(data);
  } catch (err) { next(err); }
});

router.post('/subscriptions', async (req, res, next) => {
  try {
    const data = await prisma.dataSubscription.create({
      data: { ...req.body, userId: req.user.id, userName: req.user.name || req.user.username },
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/subscriptions', async (req, res, next) => {
  try {
    const data = await prisma.dataSubscription.findMany({
      where: { userId: req.user.id, isActive: true },
      orderBy: { createdAt: 'desc' },
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.delete('/subscriptions/:id', async (req, res, next) => {
  try {
    await prisma.dataSubscription.update({ where: { id: req.params.id }, data: { isActive: false } });
    res.json({ success: true });
  } catch (err) { next(err); }
});

export default router;
