/**
 * ATS招聘管理系统 - 后端主应用
 */

import express from 'express';
import jwt from 'jsonwebtoken';
import { jwt as jwtConfig } from './config/index.js';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { PrismaClient } from '@prisma/client';
import path from 'path';
import { fileURLToPath } from 'url';

// 路由
import authRoutes from './routes/auth.routes.js';
import candidateRoutes from './routes/candidate.routes.js';
import permissionRoutes from './routes/permission.routes.js';
import permissionV2Routes from './routes/permission-v2.routes.js';
import userRoutes from './routes/user.routes.js';
import processRoutes from './routes/process.routes.js';
import demandRoutes from './routes/demand.routes.js';
import systemRoutes from './routes/system.routes.js';
import resumeRoutes from './routes/resume.routes.js';
import departmentRoutes from './routes/department.routes.js';
import positionRoutes from './routes/position.routes.js';
import recruitmentProcessRoutes from './routes/recruitment-process.routes.js';
import recruitmentStageRoutes from './routes/recruitment-stage.routes.js';
import recruitmentProcessStageLinkRoutes from './routes/recruitment-process-stage-link.routes.js';
import recruitmentRuleRoutes from './routes/recruitment-rule.routes.js';
import recruitmentRoundRoutes from './routes/recruitment-round.routes.js';
import interviewRoutes from './routes/interview.routes.js';
import offerRoutes from './routes/offer.routes.js';
import offerTemplateRoutes from './routes/offer-template.routes.js';
import notificationTemplateRoutes from './routes/notification-template.routes.js';
import invitationRoutes from './routes/invitation.routes.js';
import onboardingRoutes from './routes/onboarding.routes.js';
import talentPoolRoutes from './routes/talent-pool.routes.js';
import scoringRuleRoutes from './routes/scoring-rule.routes.js';
import externalSyncRoutes from './routes/external-sync.routes.js';
// G40: 注册 adapter (导入以触发 registerAdapter 副作用)
import './services/integration/mock-moka.adapter.js';
import './services/integration/stub-email.adapter.js';
import referralRoutes from './referral/index.js';
import { startReferralScheduler, stopReferralScheduler } from './referral/index.js';
import { startInvitationScheduler, stopInvitationScheduler } from './scheduler/invitation.scheduler.js';

// 配置
import config from './config/index.js';

// 中间件
import { errorHandler } from './middleware/error.middleware.js';
import { authMiddleware } from './middleware/auth.middleware.js';
import { enforceJwtConfigOrExit } from './middleware/jwt-validation.middleware.js';

const app = express();
const prisma = new PrismaClient();

// 前端 dist 路径（Express 直接服务，免 nginx）
// 优先级：环境变量 > 相对于本文件的 ../../frontend/dist
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_DIST = process.env.FRONTEND_DIST
  || path.resolve(__dirname, '../../frontend/dist');

// 安全中间件
app.use(helmet());

// API 速率限制
const apiLimiter = rateLimit({
  windowMs: config.rateLimit.windowMs,
  max: config.rateLimit.max,
  message: { success: false, message: '请求过于频繁，请稍后再试' },
  standardHeaders: true,
  legacyHeaders: false,
});
app.use('/api', apiLimiter);

// 中间件
app.use(cors({
  origin: config.cors.origin,
  credentials: config.cors.credentials,
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// 静态文件服务（带认证：Bearer header 或 ?token= query）
// 用途：让 <img src="/uploads/.../?token=xxx"> 能工作，
// 同时防止未授权访问
app.use('/uploads', (req, res, next) => {
  // 从 header 或 query 取 token
  const auth = req.headers.authorization;
  let token;
  if (auth && auth.startsWith('Bearer ')) {
    token = auth.split(' ')[1];
  } else if (req.query.token) {
    token = String(req.query.token);
  }

  if (!token) {
    return res.status(401).json({ success: false, message: '需要认证令牌' });
  }

  try {
    jwt.verify(token, jwtConfig.secret);
    next();
  } catch (e) {
    return res.status(401).json({ success: false, message: '无效的认证令牌' });
  }
}, express.static('uploads'));

// 健康检查
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString(), service: 'ATS Backend' });
});

// 公开路由
app.use('/api/auth', authRoutes);

// 需要认证的路由
app.use('/api/candidates', authMiddleware, candidateRoutes);
app.use('/api/permissions', authMiddleware, permissionRoutes);
app.use('/api/permissions-v2', authMiddleware, permissionV2Routes);
app.use('/api/users', authMiddleware, userRoutes);
app.use('/api/processes', authMiddleware, processRoutes);
app.use('/api/demands', authMiddleware, demandRoutes);
app.use('/api/positions', authMiddleware, positionRoutes);
app.use('/api/system', authMiddleware, systemRoutes);
app.use('/api/resumes', authMiddleware, resumeRoutes);
app.use('/api/departments', authMiddleware, departmentRoutes);
app.use('/api/referral', authMiddleware, referralRoutes);

// ====== 招聘流程管理 (PRD G38) ======
app.use('/api/recruitment-processes', authMiddleware, recruitmentProcessRoutes);
app.use('/api/recruitment-stages', authMiddleware, recruitmentStageRoutes);
app.use('/api/recruitment-process-stage-links', authMiddleware, recruitmentProcessStageLinkRoutes);
app.use('/api/recruitment-rounds', authMiddleware, recruitmentRoundRoutes);
app.use('/api/recruitment-rules', authMiddleware, recruitmentRuleRoutes);

// ====== 面试管理 (PRD G3.6) ======
app.use('/api/interviews', authMiddleware, interviewRoutes);

// ====== Offer 状态机 (PRD G23) ======
app.use('/api/offers', authMiddleware, offerRoutes);
app.use('/api/offer-templates', authMiddleware, offerTemplateRoutes);

// ====== 通知模板管理 (PRD G36) ======
app.use('/api/notification-templates', authMiddleware, notificationTemplateRoutes);

// ====== 邀约管理 (PRD G14 + G15 + G16) ======
app.use('/api/invitations', authMiddleware, invitationRoutes);

// ====== 待入职管理 (PRD G28) ======
app.use('/api/onboardings', authMiddleware, onboardingRoutes);

// ====== 人才库 (PRD G32 MVP) ======
app.use('/api/talent-pool', authMiddleware, talentPoolRoutes);

// ====== 评分规则 (PRD G39) ======
app.use('/api/scoring-rules', authMiddleware, scoringRuleRoutes);

// ====== G40 法人公司同步 ======
app.use('/api/external-sync', authMiddleware, externalSyncRoutes);

// 静态前端 + SPA fallback（让 Express 直接服务前端，免 nginx）
// 1) 真实静态资源（dist/assets/*）
app.use(express.static(FRONTEND_DIST));
// 2) SPA fallback：所有非 /api、非 /uploads 的 GET 都返回 index.html
//    找不到 index.html 时落回 404
app.get(/^\/(?!api|uploads).*/, (req, res, next) => {
  res.sendFile(path.join(FRONTEND_DIST, 'index.html'), (err) => {
    if (err) next();
  });
});

// 错误处理
app.use(errorHandler);

// 404处理
app.use((req, res) => {
  res.status(404).json({
    success: false,
    message: 'API路由不存在'
  });
});

// JWT/CORS 配置校验 (报告 #11 安全债)
enforceJwtConfigOrExit();

// 启动内推后台调度
try {
  startReferralScheduler(prisma);
} catch (e) {
  console.warn('[referral] scheduler start failed:', e.message);
}

// 启动邀约超时调度
try {
  startInvitationScheduler(prisma);
} catch (e) {
  console.warn('[invitation] scheduler start failed:', e.message);
}

app.listen(config.app.port, () => {
  console.log(`🚀 ${config.app.name} 已启动`);
  console.log(`📡 后端服务: http://localhost:${config.app.port}`);
  console.log(`📚 API文档: http://localhost:${config.app.port}/api/health`);
});

// 优雅关闭
process.on('SIGTERM', async () => {
  console.log('正在关闭服务...');
  try {
    stopReferralScheduler();
  } catch (e) {
    console.warn('[referral] scheduler stop failed:', e.message);
  }
  try {
    stopInvitationScheduler();
  } catch (e) {
    console.warn('[invitation] scheduler stop failed:', e.message);
  }
  await prisma.$disconnect();
  process.exit(0);
});

export { prisma };
export default app;