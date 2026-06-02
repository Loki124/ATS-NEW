/**
 * 后端统一配置文件
 */

import dotenv from 'dotenv';
dotenv.config();

// 应用配置
export const app = {
  name: 'ATS招聘管理系统',
  port: parseInt(process.env.PORT) || 5125,
  env: process.env.NODE_ENV || 'development',
};

// 数据库配置
export const database = {
  url: process.env.DATABASE_URL || 'mysql://ats:atspass@localhost:3306/ats',
};

// MySQL 配置（用于 healthcheck 等）
export const mysql = {
  host: process.env.MYSQL_HOST || 'localhost',
  port: parseInt(process.env.MYSQL_PORT) || 3306,
  user: process.env.MYSQL_USER || 'ats',
  password: process.env.MYSQL_PASSWORD || 'atspass',
  database: process.env.MYSQL_DATABASE || 'ats',
  rootPassword: process.env.MYSQL_ROOT_PASSWORD || 'rootpass',
};

// JWT 配置
export const jwt = {
  secret: process.env.JWT_SECRET || 'ats-secret-key-2024',
  expiresIn: process.env.JWT_EXPIRES_IN || '7d',
};

// CORS 配置
export const cors = {
  origin: process.env.CORS_ORIGIN || 'http://localhost:5212',
  credentials: true,
};

// API 速率限制
export const rateLimit = {
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000,
  max: parseInt(process.env.RATE_LIMIT_MAX) || 1000,
};

// 上传配置
export const upload = {
  maxSize: 10 * 1024 * 1024,
  allowedTypes: ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'],
};

export default { app, database, mysql, jwt, cors, rateLimit, upload };