/**
 * ATS招聘管理系统 - 后端主应用
 */

import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { PrismaClient } from '@prisma/client';

// 路由 - 只导入存在的路由
import authRoutes from './routes/auth.routes.js';
import candidateRoutes from './routes/candidate.routes.js';
import permissionRoutes from './routes/permission.routes.js';
import permissionV2Routes from './routes/permission-v2.routes.js';
import userRoutes from './routes/user.routes.js';

// 中间件
import { errorHandler } from './middleware/error.middleware.js';
import { authMiddleware } from './middleware/auth.middleware.js';

dotenv.config();

const app = express();
const prisma = new PrismaClient();

// 安全中间件
app.use(helmet());

// API 速率限制
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 分钟
  max: 1000, // 限制每个 IP 15分钟内最多 1000 次请求
  message: { success: false, message: '请求过于频繁，请稍后再试' },
  standardHeaders: true,
  legacyHeaders: false,
});
app.use('/api', apiLimiter);

// 中间件
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:5212',
  credentials: true,
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

// 错误处理
app.use(errorHandler);

// 404处理
app.use((req, res) => {
  res.status(404).json({ 
    success: false, 
    message: 'API路由不存在' 
  });
});

const PORT = process.env.PORT || 3002;

app.listen(PORT, () => {
  console.log(`🚀 ATS后端服务已启动: http://localhost:${PORT}`);
  console.log(`📚 API文档: http://localhost:${PORT}/api/health`);
});

// 优雅关闭
process.on('SIGTERM', async () => {
  console.log('正在关闭服务...');
  await prisma.$disconnect();
  process.exit(0);
});

export { prisma };
