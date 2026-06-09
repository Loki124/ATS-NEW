// G45 - 简历查重 + OCR 解析 路由
import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.middleware.js';
import { findDuplicates } from '../services/resume-duplicate-check.service.js';
import { MockOcrAdapter } from '../services/integration/ocr-adapter.js';

const router = Router();
router.use(authMiddleware);

/**
 * POST /api/duplicate-check/check
 * body: { name, phone, email, threshold? }
 * 主动查重: 用于前端在表单填写完时实时检查
 */
router.post('/check', async (req, res, next) => {
  try {
    const { name, phone, email, threshold } = req.body || {};
    if (!name && !phone && !email) {
      return res.status(400).json({ success: false, message: 'name/phone/email 至少提供一个' });
    }
    const dupes = await findDuplicates({ name, phone, email }, threshold || 0.7);
    res.json({ success: true, data: dupes, hasDuplicate: dupes.length > 0 });
  } catch (err) {
    next(err);
  }
});

/**
 * POST /api/duplicate-check/ocr-parse
 * 简版: 返回 OCR mock 结构化数据
 * 真实场景: 接 multer 文件上传, 调真实 OCR API
 */
router.post('/ocr-parse', async (req, res, next) => {
  try {
    const adapter = new MockOcrAdapter();
    const result = await adapter.parseResume(Buffer.from('mock'));
    res.json({ success: true, data: result });
  } catch (err) {
    next(err);
  }
});

export default router;
