/**
 * G41 - 公司信息库 路由
 * GET /api/library/companies
 * GET /api/library/companies/industries
 * GET /api/library/companies/:id
 */

import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import { searchCompanies, getCompanyById, listIndustries, filterByScale } from '../services/company-library.service.js';

const router = Router();
router.use(authMiddleware);

router.get('/companies', async (req, res, next) => {
  try {
    const data = await searchCompanies(req.query.keyword, {
      industry: req.query.industry,
      scale: req.query.scale,
      isBenchmark: req.query.isBenchmark === 'true' ? true : req.query.isBenchmark === 'false' ? false : undefined,
      page: parseInt(req.query.page) || 1,
      pageSize: parseInt(req.query.pageSize) || 20,
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/companies/industries', async (req, res, next) => {
  try {
    const data = await listIndustries();
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/companies/:id', async (req, res, next) => {
  try {
    const data = await getCompanyById(req.params.id);
    if (!data) return res.status(404).json({ success: false, message: '公司不存在' });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

export default router;
