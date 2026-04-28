/**
 * 认证中间件
 */

import jwt from 'jsonwebtoken';
import { prisma } from '../app.js';

export const authMiddleware = async (req, res, next) => {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({
        success: false,
        message: '未提供认证令牌'
      });
    }

    const token = authHeader.split(' ')[1];
    
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    
    const user = await prisma.user.findUnique({
      where: { id: decoded.userId },
      include: {
        department: true
      }
    });

    if (!user || user.status !== 'ACTIVE') {
      return res.status(401).json({
        success: false,
        message: '用户不存在或已被禁用'
      });
    }

    req.user = user;
    req.userId = user.id;
    
    next();
  } catch (error) {
    if (error.name === 'JsonWebTokenError') {
      return res.status(401).json({
        success: false,
        message: '无效的认证令牌'
      });
    }
    if (error.name === 'TokenExpiredError') {
      return res.status(401).json({
        success: false,
        message: '认证令牌已过期'
      });
    }
    
    return res.status(500).json({
      success: false,
      message: '认证过程出错'
    });
  }
};

/**
 * 角色权限中间件
 */
export const requireRole = (...roles) => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        message: '未登录'
      });
    }

    if (!roles.includes(req.user.roleType)) {
      return res.status(403).json({
        success: false,
        message: '您没有权限执行此操作'
      });
    }

    next();
  };
};

/**
 * 检查虚拟角色权限
 */
export const checkVirtualRole = (roleType) => {
  return async (req, res, next) => {
    const { id } = req.params;
    
    try {
      switch (roleType) {
        case 'DEMAND_MANAGER':
          // 需求负责人
          if (req.user.roleType === 'SUPER_ADMIN' || req.user.roleType === 'ADMIN') {
            return next();
          }
          const demand = await prisma.demand.findUnique({ where: { id } });
          if (demand?.managerId === req.userId) {
            return next();
          }
          break;
          
        case 'POSITION_MANAGER':
          // 职位负责人
          if (req.user.roleType === 'SUPER_ADMIN' || req.user.roleType === 'ADMIN') {
            return next();
          }
          const position = await prisma.position.findUnique({ where: { id } });
          if (position?.managerId === req.userId) {
            return next();
          }
          break;
          
        case 'SUPER_ADMIN':
          if (req.user.roleType !== 'SUPER_ADMIN') {
            return res.status(403).json({
              success: false,
              message: '仅超级管理员可执行此操作'
            });
          }
          break;
      }

      return res.status(403).json({
        success: false,
        message: '您没有权限执行此操作'
      });
    } catch (error) {
      next(error);
    }
  };
};
