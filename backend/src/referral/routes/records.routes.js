import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import {
  createReferral,
  listForReferrer,
  listForManagement,
  transitionRecord,
} from '../services/record.service.js';
import { createRecordValidators } from '../validators/referral.validator.js';

const router = Router();
const prisma = new PrismaClient();

router.get('/me', async (req, res, next) => {
  try {
    const { page, pageSize, status, positionId, includeInvalid } = req.query;
    const r = await listForReferrer(prisma, req.user.id, {
      page: Number(page) || 1,
      pageSize: Number(pageSize) || 20,
      status,
      positionId,
      includeInvalid: includeInvalid === 'true',
    });
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

router.get('/me/summary', async (req, res, next) => {
  try {
    const records = await prisma.referralRecord.findMany({
      where: { referrerId: req.user.id, referralStatus: { not: 'INVALID' } },
      include: { rewards: true },
    });
    const summary = {
      recommendValidCount: records.length,
      onboardedCount: 0,
      probationPassedCount: 0,
      rewardToConfirmTotal: 0,
      rewardConfirmedTotal: 0,
      rewardIssuedTotal: 0,
    };
    for (const r of records) {
      for (const reward of r.rewards) {
        if (reward.status === 'TO_CONFIRM') summary.rewardToConfirmTotal += Number(reward.amount);
        if (reward.status === 'CONFIRMED') summary.rewardConfirmedTotal += Number(reward.amount);
        if (reward.status === 'ISSUED') summary.rewardIssuedTotal += Number(reward.amount);
      }
    }
    res.json({ success: true, data: summary });
  } catch (e) { next(e); }
});

router.get('/me/:id', async (req, res, next) => {
  try {
    const r = await prisma.referralRecord.findUnique({
      where: { id: req.params.id },
      include: { candidate: { include: { resumes: true } }, position: true, expert: true, rewards: true },
    });
    if (!r || r.referrerId !== req.user.id) {
      return res.status(404).json({ success: false, message: '记录不存在' });
    }
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

router.post('/', createRecordValidators, async (req, res, next) => {
  try {
    const r = await createReferral(prisma, { referrerId: req.user.id, ...req.body });
    if (!r.created) {
      return res.status(400).json({
        success: false,
        data: r,
        message: r.invalidReason ? `无效内推: ${r.invalidReason}` : '推荐已存在',
      });
    }
    res.status(201).json({ success: true, data: r.record });
  } catch (e) { next(e); }
});

router.post('/by-code', async (req, res, next) => {
  try {
    const { code, candidateId, positionId, resumeId } = req.body;
    const validation = await prisma.referralCode.findUnique({ where: { code } });
    if (!validation) {
      return res.status(400).json({ success: false, message: '内推码无效' });
    }
    const r = await createReferral(prisma, {
      referrerId: validation.userId,
      candidateId, positionId, resumeId,
      referralType: 'CANDIDATE_USED_CODE',
    });
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

router.post('/:id/urge', async (req, res) => {
  res.status(501).json({ success: false, message: '催办功能在 Phase 3 实施' });
});

router.post('/:id/recommend-again', async (req, res) => {
  res.status(501).json({ success: false, message: '再次推荐在 Phase 3 实施' });
});

router.get('/', async (req, res, next) => {
  try {
    if (!['SUPER_ADMIN', 'HRBP'].includes(req.user.roleType)) {
      return res.status(403).json({ success: false, message: '权限不足' });
    }
    const r = await listForManagement(prisma, req.query);
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

router.get('/:id', async (req, res, next) => {
  try {
    const r = await prisma.referralRecord.findUnique({
      where: { id: req.params.id },
      include: { referrer: true, candidate: true, position: true, expert: true, rewards: true },
    });
    if (!r) return res.status(404).json({ success: false, message: '不存在' });
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

router.post('/:id/invalidate', async (req, res, next) => {
  try {
    if (!['SUPER_ADMIN', 'HRBP'].includes(req.user.roleType)) {
      return res.status(403).json({ success: false, message: '权限不足' });
    }
    const { reason } = req.body;
    const r = await transitionRecord(prisma, req.params.id, { type: 'MARK_INVALID', reason });
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

export default router;
