/**
 * ATS招聘管理系统 - 后端主应用
 */

import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { PrismaClient } from '@prisma/client';

// 路由
import authRoutes from './routes/auth.routes.js';
import userRoutes from './routes/user.routes.js';
import departmentRoutes from './routes/department.routes.js';
import demandRoutes from './routes/demand.routes.js';
import positionRoutes from './routes/position.routes.js';
import candidateRoutes from './routes/candidate.routes.js';
import resumeRoutes from './routes/resume.routes.js';
import interviewRoutes from './routes/interview.routes.js';
import offerRoutes from './routes/offer.routes.js';
import onboardingRoutes from './routes/onboarding.routes.js';
import invitationRoutes from './routes/invitation.routes.js';
import dictionaryRoutes from './routes/dictionary.routes.js';
import notificationRoutes from './routes/notification.routes.js';

// 中间件
import { errorHandler } from './middleware/error.middleware.js';
import { authMiddleware } from './middleware/auth.middleware.js';

dotenv.config();

const app = express();
const prisma = new PrismaClient();

// 中间件
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
  credentials: true,
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// 静态文件服务
app.use('/uploads', express.static('uploads'));

// 健康检查
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// 公开路由
app.use('/api/auth', authRoutes);

// 需要认证的路由
app.use('/api/users', authMiddleware, userRoutes);
app.use('/api/departments', authMiddleware, departmentRoutes);
app.use('/api/demands', authMiddleware, demandRoutes);
app.use('/api/positions', authMiddleware, positionRoutes);
app.use('/api/candidates', authMiddleware, candidateRoutes);
app.use('/api/resumes', authMiddleware, resumeRoutes);
app.use('/api/interviews', authMiddleware, interviewRoutes);
app.use('/api/offers', authMiddleware, offerRoutes);
app.use('/api/onboardings', authMiddleware, onboardingRoutes);
app.use('/api/invitations', authMiddleware, invitationRoutes);
app.use('/api/dictionaries', authMiddleware, dictionaryRoutes);
app.use('/api/notifications', authMiddleware, notificationRoutes);

// 错误处理
app.use(errorHandler);

// 404处理
app.use((req, res) => {
  res.status(404).json({ 
    success: false, 
    message: 'API路由不存在' 
  });
});

const PORT = process.env.PORT || 5000;

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
