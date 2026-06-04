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
import referralRoutes from './referral/index.js';
import { startReferralScheduler, stopReferralScheduler } from './referral/index.js';

// 配置
import config from './config/index.js';

// 中间件
import { errorHandler } from './middleware/error.middleware.js';
import { authMiddleware } from './middleware/auth.middleware.js';

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
app.use('/api/system', authMiddleware, systemRoutes);
app.use('/api/resumes', authMiddleware, resumeRoutes);
app.use('/api/departments', authMiddleware, departmentRoutes);
app.use('/api/referral', authMiddleware, referralRoutes);

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

// 启动内推后台调度
try {
  startReferralScheduler(prisma);
} catch (e) {
  console.warn('[referral] scheduler start failed:', e.message);
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
  await prisma.$disconnect();
  process.exit(0);
});

export { prisma };