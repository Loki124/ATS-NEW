/**
 * 用户管理路由
 */

import express from 'express';
import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

const router = express.Router();
const prisma = new PrismaClient();

// 获取所有部门
router.get('/departments', async (req, res, next) => {
  try {
    const departments = await prisma.department.findMany({
      where: { status: 'ACTIVE' },
      orderBy: { sortOrder: 'asc' }
    });

    res.json({ success: true, data: departments });
  } catch (error) {
    next(error);
  }
});

// 获取所有用户
router.get('/', async (req, res, next) => {
  try {
    const users = await prisma.user.findMany({
      select: {
        id: true,
        username: true,
        realName: true,
        email: true,
        phone: true,
        status: true,
        roleType: true,
        departmentId: true,
        wechatWorkUserId: true,
        wechatWorkDeptId: true,
        wechatWorkName: true,
        mochaUserId: true,
        mochaDeptId: true,
        mochaName: true,
        permissionMode: true,
        createdAt: true,
      },
      orderBy: { createdAt: 'desc' }
    });
    
    res.json({ success: true, data: users });
  } catch (error) {
    next(error);
  }
});

// 获取单个用户
router.get('/:id', async (req, res, next) => {
  try {
    const user = await prisma.user.findUnique({
      where: { id: req.params.id },
      select: {
        id: true,
        username: true,
        realName: true,
        email: true,
        phone: true,
        status: true,
        roleType: true,
        departmentId: true,
        wechatWorkUserId: true,
        wechatWorkDeptId: true,
        wechatWorkName: true,
        mochaUserId: true,
        mochaDeptId: true,
        mochaName: true,
        permissionMode: true,
        createdAt: true,
      }
    });
    
    if (!user) {
      return res.status(404).json({ success: false, message: '用户不存在' });
    }
    
    res.json({ success: true, data: user });
  } catch (error) {
    next(error);
  }
});

// 创建用户
router.post('/', async (req, res, next) => {
  try {
    const { username, password, realName, email, phone, roleType, status, permissionMode, wechatWorkUserId, wechatWorkDeptId, wechatWorkName, mochaUserId, mochaDeptId, mochaName } = req.body;
    
    // 检查用户名是否已存在
    const existingUser = await prisma.user.findUnique({
      where: { username }
    });
    
    if (existingUser) {
      return res.status(400).json({ success: false, message: '用户名已存在' });
    }
    
    // 密码加密
    const hashedPassword = await bcrypt.hash(password || '123456', 10);
    
    const user = await prisma.user.create({
      data: {
        username,
        password: hashedPassword,
        realName,
        email,
        phone,
        roleType: roleType || 'HR',
        status: status || 'ACTIVE',
        permissionMode: permissionMode || 'MOU',
        wechatWorkUserId,
        wechatWorkDeptId,
        wechatWorkName,
        mochaUserId,
        mochaDeptId,
        mochaName,
      },
      select: {
        id: true,
        username: true,
        realName: true,
        email: true,
        phone: true,
        status: true,
        roleType: true,
        permissionMode: true,
        createdAt: true,
      }
    });
    
    res.json({ success: true, data: user });
  } catch (error) {
    next(error);
  }
});

// 更新用户
router.put('/:id', async (req, res, next) => {
  try {
    const { realName, email, phone, roleType, status, permissionMode, wechatWorkUserId, wechatWorkDeptId, wechatWorkName, mochaUserId, mochaDeptId, mochaName, password } = req.body;
    
    const updateData = {
      realName,
      email,
      phone,
      roleType,
      status,
      permissionMode,
      wechatWorkUserId,
      wechatWorkDeptId,
      wechatWorkName,
      mochaUserId,
      mochaDeptId,
      mochaName,
    };
    
    // 如果提供了新密码
    if (password) {
      updateData.password = await bcrypt.hash(password, 10);
    }
    
    // 过滤掉 undefined 值
    Object.keys(updateData).forEach(key => {
      if (updateData[key] === undefined) {
        delete updateData[key];
      }
    });
    
    const user = await prisma.user.update({
      where: { id: req.params.id },
      data: updateData,
      select: {
        id: true,
        username: true,
        realName: true,
        email: true,
        phone: true,
        status: true,
        roleType: true,
        permissionMode: true,
        wechatWorkUserId: true,
        wechatWorkDeptId: true,
        wechatWorkName: true,
        mochaUserId: true,
        mochaDeptId: true,
        mochaName: true,
        createdAt: true,
      }
    });
    
    res.json({ success: true, data: user });
  } catch (error) {
    if (error.code === 'P2025') {
      return res.status(404).json({ success: false, message: '用户不存在' });
    }
    next(error);
  }
});

// 删除用户
router.delete('/:id', async (req, res, next) => {
  try {
    await prisma.user.delete({
      where: { id: req.params.id }
    });

    res.json({ success: true, message: '用户删除成功' });
  } catch (error) {
    if (error.code === 'P2025') {
      return res.status(404).json({ success: false, message: '用户不存在' });
    }
    next(error);
  }
});

export default router;
