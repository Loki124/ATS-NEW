/**
 * 数据字典 API - Plan L Task 6
 *
 * 提供 GET /api/dictionary?code=interview_round 返回该字典下的所有 items
 * 用于前端 (面试轮次 / 面试形式) 从字典动态拉, 避免硬编码
 *
 * 例:
 *   GET /api/dictionary?code=interview_round
 *   → { success: true, data: { code, name, items: [{ code, name, value, sortOrder }] } }
 *
 *   GET /api/dictionary
 *   → { success: true, data: [{ code, name, itemCount }] } (字典列表)
 */

import { Router } from 'express';
import { prisma } from '../app.js';

const router = Router();

// 列出所有字典 (用于后台管理)
router.get('/', async (req, res, next) => {
  try {
    const dicts = await prisma.dictionary.findMany({
      where: { status: 'ACTIVE' },
      include: { _count: { select: { items: true } } },
      orderBy: { code: 'asc' },
    });
    res.json({
      success: true,
      data: dicts.map((d) => ({
        id: d.id,
        code: d.code,
        name: d.name,
        description: d.description,
        itemCount: d._count.items,
      })),
    });
  } catch (e) { next(e); }
});

// 按 code 取字典 + items
// 注意: Express 不允许同路径不同参数, 所以放 /:code
router.get('/:code', async (req, res, next) => {
  try {
    const dict = await prisma.dictionary.findUnique({
      where: { code: req.params.code },
      include: {
        items: {
          where: { status: 'ACTIVE' },
          orderBy: { sortOrder: 'asc' },
        },
      },
    });
    if (!dict) {
      return res.status(404).json({ success: false, message: '字典不存在' });
    }
    res.json({
      success: true,
      data: {
        id: dict.id,
        code: dict.code,
        name: dict.name,
        description: dict.description,
        items: dict.items.map((it) => ({
          id: it.id,
          code: it.code,
          name: it.name,
          value: it.value,
          sortOrder: it.sortOrder,
          level: it.level,
        })),
      },
    });
  } catch (e) { next(e); }
});

export default router;
