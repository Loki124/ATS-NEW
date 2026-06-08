/**
 * G41 - 院校信息库 路由
 * GET /api/library/schools
 * GET /api/library/schools/provinces
 * GET /api/library/schools/:id
 */

import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import { searchSchools, getSchoolById, listProvinces, filterByLevel } from '../services/school-library.service.js';

const router = Router();
router.use(authMiddleware);

router.get('/schools', async (req, res, next) => {
  try {
    const data = await searchSchools(req.query.keyword, {
      educationLevel: req.query.educationLevel,
      schoolType: req.query.schoolType,
      province: req.query.province,
      city: req.query.city,
      page: parseInt(req.query.page) || 1,
      pageSize: parseInt(req.query.pageSize) || 20,
    });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/schools/provinces', async (req, res, next) => {
  try {
    const data = await listProvinces();
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

router.get('/schools/:id', async (req, res, next) => {
  try {
    const data = await getSchoolById(req.params.id);
    if (!data) return res.status(404).json({ success: false, message: '学校不存在' });
    res.json({ success: true, data });
  } catch (err) { next(err); }
});

export default router;
