import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import { validateCode, createCodeForUser } from '../services/code.service.js';
import { validateCodeQuery } from '../validators/referral.validator.js';

const router = Router();
const prisma = new PrismaClient();

router.get('/me', async (req, res, next) => {
  try {
    const userId = req.user.id;
    let code = await prisma.referralCode.findUnique({ where: { userId } });
    if (!code) {
      code = await createCodeForUser(prisma, userId);
    }
    res.json({ success: true, data: code });
  } catch (e) { next(e); }
});

router.get('/validate', validateCodeQuery, async (req, res, next) => {
  try {
    const { code } = req.query;
    const r = await validateCode(prisma, code);
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

router.get('/user/:userId', async (req, res, next) => {
  try {
    if (!['SUPER_ADMIN', 'HRBP'].includes(req.user.roleType)) {
      return res.status(403).json({ success: false, message: '权限不足' });
    }
    const code = await prisma.referralCode.findUnique({ where: { userId: req.params.userId } });
    res.json({ success: true, data: code });
  } catch (e) { next(e); }
});

export default router;
