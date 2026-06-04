/**
 * 内推门户模块入口
 * Phase 1: 数据模型 + 核心服务
 */

import { Router } from 'express';
import codesRouter from './routes/codes.routes.js';
import expertConfigsRouter from './routes/expert-configs.routes.js';
import recordsRouter from './routes/records.routes.js';
import rewardsRouter from './routes/rewards.routes.js';
import rulesRouter from './routes/rules.routes.js';
import { startReferralScheduler, stopReferralScheduler } from './scheduler/referral.scheduler.js';

const router = Router();

router.use('/codes', codesRouter);
router.use('/expert-configs', expertConfigsRouter);
router.use('/records', recordsRouter);
router.use('/rewards', rewardsRouter);
router.use('/rules', rulesRouter);

export { startReferralScheduler, stopReferralScheduler };
export default router;
