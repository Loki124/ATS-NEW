import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import {
  listRewardsForReferrer,
  getRewardSummary,
  confirmReward,
  rejectReward,
  markIssued,
  triggerRewardsForCandidate,
} from '../services/reward.service.js';

const router = Router();
const prisma = new PrismaClient();

router.get('/me', async (req, res, next) => {
  try {
    const r = await listRewardsForReferrer(prisma, req.user.id, req.query);
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

router.get('/me/summary', async (req, res, next) => {
  try {
    const s = await getRewardSummary(prisma, req.user.id);
    res.json({ success: true, data: s });
  } catch (e) { next(e); }
});

router.get('/', async (req, res, next) => {
  try {
    if (!['SUPER_ADMIN', 'HRBP'].includes(req.user.roleType)) {
      return res.status(403).json({ success: false, message: '权限不足' });
    }
    const { page = 1, pageSize = 20, status } = req.query;
    const where = status ? { status } : {};
    const [list, total] = await Promise.all([
      prisma.referralReward.findMany({
        where,
        include: { candidate: true, record: { include: { position: true, referrer: true } } },
        orderBy: { triggeredAt: 'desc' },
        skip: (Number(page) - 1) * Number(pageSize),
        take: Number(pageSize),
      }),
      prisma.referralReward.count({ where }),
    ]);
    res.json({ success: true, data: { list, total, page: Number(page), pageSize: Number(pageSize) } });
  } catch (e) { next(e); }
});

router.post('/:id/confirm', async (req, res, next) => {
  try {
    if (!['SUPER_ADMIN', 'HRBP'].includes(req.user.roleType)) {
      return res.status(403).json({ success: false, message: '权限不足' });
    }
    const r = await confirmReward(prisma, req.params.id, req.user.id);
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

router.post('/:id/reject', async (req, res, next) => {
  try {
    if (!['SUPER_ADMIN', 'HRBP'].includes(req.user.roleType)) {
      return res.status(403).json({ success: false, message: '权限不足' });
    }
    const r = await rejectReward(prisma, req.params.id, req.user.id, req.body.reason);
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

router.post('/:id/issue', async (req, res, next) => {
  try {
    if (!['SUPER_ADMIN', 'HRBP'].includes(req.user.roleType)) {
      return res.status(403).json({ success: false, message: '权限不足' });
    }
    const r = await markIssued(prisma, req.params.id);
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

router.post('/trigger', async (req, res, next) => {
  try {
    if (req.user.roleType !== 'SUPER_ADMIN') {
      return res.status(403).json({ success: false, message: '权限不足' });
    }
    const { candidateId, stage } = req.body;
    const r = await triggerRewardsForCandidate(prisma, candidateId, stage);
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

export default router;
