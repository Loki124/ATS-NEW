/**
 * 职位管理路由
 * 提供扁平职位列表（供下拉框等场景使用）
 */

import express from 'express';
import { prisma } from '../app.js';

const router = express.Router();

// 列出职位（支持按状态、需求、部门过滤）
router.get('/', async (req, res, next) => {
  try {
    const { status = 'ACTIVE', demandId, departmentId, keyword } = req.query;
    const where = {};
    if (status) where.status = status;
    if (demandId) where.demandId = demandId;
    if (departmentId) where.departmentId = departmentId;
    if (keyword) {
      where.OR = [
        { name: { contains: keyword } },
        { code: { contains: keyword } },
      ];
    }
    const positions = await prisma.position.findMany({
      where,
      include: {
        department: { select: { id: true, name: true, code: true } },
        demand: { select: { id: true, name: true, code: true } },
      },
      orderBy: { createdAt: 'desc' },
      take: 200,
    });
    res.json({ success: true, data: positions });
  } catch (e) {
    next(e);
  }
});

// 职位详情
router.get('/:id', async (req, res, next) => {
  try {
    const position = await prisma.position.findUnique({
      where: { id: req.params.id },
      include: {
        department: true,
        demand: true,
      },
    });
    if (!position) return res.status(404).json({ success: false, message: '职位不存在' });
    res.json({ success: true, data: position });
  } catch (e) {
    next(e);
  }
});

export default router;
