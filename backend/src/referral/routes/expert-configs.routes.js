import { Router } from 'express';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

router.get('/me', async (req, res, next) => {
  try {
    const list = await prisma.referralExpertConfig.findMany({
      where: { userId: req.user.id },
      include: { team: true, expert: { select: { id: true, realName: true } } },
    });
    res.json({ success: true, data: list });
  } catch (e) { next(e); }
});

router.post('/', async (req, res, next) => {
  try {
    const { teamId, expertId, isPrimary } = req.body;
    const created = await prisma.referralExpertConfig.create({
      data: { userId: req.user.id, teamId, expertId, isPrimary: isPrimary ?? true },
    });
    res.status(201).json({ success: true, data: created });
  } catch (e) { next(e); }
});

router.put('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const existing = await prisma.referralExpertConfig.findUnique({ where: { id } });
    if (!existing || existing.userId !== req.user.id) {
      return res.status(403).json({ success: false, message: '无权编辑' });
    }
    const updated = await prisma.referralExpertConfig.update({ where: { id }, data: req.body });
    res.json({ success: true, data: updated });
  } catch (e) { next(e); }
});

router.delete('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const existing = await prisma.referralExpertConfig.findUnique({ where: { id } });
    if (!existing || existing.userId !== req.user.id) {
      return res.status(403).json({ success: false, message: '无权删除' });
    }
    await prisma.referralExpertConfig.delete({ where: { id } });
    res.json({ success: true });
  } catch (e) { next(e); }
});

export default router;
