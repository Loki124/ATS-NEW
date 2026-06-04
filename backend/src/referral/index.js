/**
 * 内推门户模块入口
 * Phase 1: 数据模型 + 核心服务
 *
 * 子路由和调度器将在后续 Task 22-27 中实现并挂载。
 * 参见: docs/superpowers/plans/2026-06-04-referral-portal-phase1.md
 */

import { Router } from 'express';

const router = Router();

// 子路由挂载点（占位 - 将在 Task 22-26 实现）
// router.use('/codes', codesRouter);
// router.use('/expert-configs', expertConfigsRouter);
// router.use('/records', recordsRouter);
// router.use('/rewards', rewardsRouter);
// router.use('/rules', rulesRouter);

// 调度器（占位 - 将在 Task 27 实现）
// export { startReferralScheduler, stopReferralScheduler } from './scheduler/referral.scheduler.js';

export default router;
