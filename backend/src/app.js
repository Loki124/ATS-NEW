/**
 * ATS招聘管理系统 - 后端主应用
 */

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { PrismaClient } from '@prisma/client';

// 路由
import authRoutes from './routes/auth.routes.js';
import candidateRoutes from './routes/candidate.routes.js';
import permissionRoutes from './routes/permission.routes.js';
import permissionV2Routes from './routes/permission-v2.routes.js';
import userRoutes from './routes/user.routes.js';
import processRoutes from './routes/process.routes.js';
import demandRoutes from './routes/demand.routes.js';
import systemRoutes from './routes/system.routes.js';

// 配置
import config from './config/index.js';

// 中间件
import { errorHandler } from './middleware/error.middleware.js';
import { authMiddleware } from './middleware/auth.middleware.js';

const app = express();
const prisma = new PrismaClient();

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

// 静态文件服务
app.use('/uploads', express.static('uploads'));

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

// 错误处理
app.use(errorHandler);

// 404处理
app.use((req, res) => {
  res.status(404).json({
    success: false,
    message: 'API路由不存在'
  });
});

app.listen(config.app.port, () => {
  console.log(`🚀 ${config.app.name} 已启动`);
  console.log(`📡 后端服务: http://localhost:${config.app.port}`);
  console.log(`📚 API文档: http://localhost:${config.app.port}/api/health`);
});

// 优雅关闭
process.on('SIGTERM', async () => {
  console.log('正在关闭服务...');
  await prisma.$disconnect();
  process.exit(0);
});

export { prisma };