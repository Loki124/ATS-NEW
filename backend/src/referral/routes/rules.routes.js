import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import { createRule, updateRule, toggleRule, listRules } from '../services/rule.service.js';
import { createRuleValidators } from '../validators/referral.validator.js';

const router = Router();
const prisma = new PrismaClient();

const requireAdmin = (req, res, next) => {
  if (req.user.roleType !== 'SUPER_ADMIN') {
    return res.status(403).json({ success: false, message: '仅超管可操作' });
  }
  next();
};

router.get('/', requireAdmin, async (req, res, next) => {
  try {
    const list = await listRules(prisma, req.query);
    res.json({ success: true, data: list });
  } catch (e) { next(e); }
});

router.get('/:id', requireAdmin, async (req, res, next) => {
  try {
    const r = await prisma.referralRule.findUnique({ where: { id: req.params.id } });
    if (!r) return res.status(404).json({ success: false, message: '不存在' });
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

router.post('/', requireAdmin, createRuleValidators, async (req, res, next) => {
  try {
    const r = await createRule(prisma, { ...req.body, createdBy: req.user.id });
    res.status(201).json({ success: true, data: r });
  } catch (e) { next(e); }
});

router.put('/:id', requireAdmin, async (req, res, next) => {
  try {
    const r = await updateRule(prisma, req.params.id, req.body);
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

router.post('/:id/toggle', requireAdmin, async (req, res, next) => {
  try {
    const r = await toggleRule(prisma, req.params.id);
    res.json({ success: true, data: r });
  } catch (e) { next(e); }
});

export default router;
