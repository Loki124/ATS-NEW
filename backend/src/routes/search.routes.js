/**
 * 全局搜索路由 - Plan T1
 *
 * GET /api/search?q=...&types=candidate,demand&limit=5
 *
 * 权限: 任意登录用户
 * 字段脱敏: 当前通过 field-masking.service 在 service 层 select 控制返回字段
 *          (避免泄漏 phone/email/salary 等敏感信息到搜索结果)
 *          计划中提到的 dataPermissionMiddleware (G8) 当前未在 middleware/ 目录
 *          下实现,本路由先只挂 authMiddleware。
 */

import { Router } from 'express';
import { search, DEFAULT_LIMIT } from '../services/search.service.js';

const router = Router();

router.get('/', async (req, res, next) => {
  try {
    const q = (req.query.q || '').trim();

    if (!q) {
      return res.status(400).json({ error: 'q is required' });
    }
    if (q.length > 64) {
      return res.status(400).json({ error: 'q too long (max 64 chars)' });
    }

    const types = req.query.types
      ? String(req.query.types).split(',').map((t) => t.trim()).filter(Boolean)
      : undefined;

    const limit = req.query.limit ? parseInt(req.query.limit, 10) : DEFAULT_LIMIT;

    const result = await search({ q, types, limit });
    res.json(result);
  } catch (err) {
    next(err);
  }
});

export default router;
