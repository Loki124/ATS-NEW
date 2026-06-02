/**
 * 部门管理路由
 * 支持部门编号/部门ID/部门名称/上级部门/部门负责人/部门HRBP/部门负责人2/分管VP等
 */

import express from 'express';
import { PrismaClient } from '@prisma/client';

const router = express.Router();
const prisma = new PrismaClient();

/**
 * 构建部门路径
 */
const buildDeptPath = (parentPath, code) => {
  return parentPath ? `${parentPath}/${code}` : code;
};

/**
 * 计算部门层级
 */
const computeLevel = (parentPath) => {
  if (!parentPath) return 1;
  return parentPath.split('/').length + 1;
};

// 获取部门列表（平铺）
router.get('/', async (req, res, next) => {
  try {
    const { status, keyword } = req.query;
    const where = {};

    if (status) where.status = status;
    if (keyword) {
      where.OR = [
        { name: { contains: String(keyword) } },
        { code: { contains: String(keyword) } },
      ];
    }

    const departments = await prisma.department.findMany({
      where,
      orderBy: [{ sortOrder: 'asc' }, { code: 'asc' }],
    });

    // 关联用户信息（负责人/HRBP/VP）
    const userIds = new Set();
    departments.forEach(d => {
      if (d.managerId) userIds.add(d.managerId);
      if (d.manager2Id) userIds.add(d.manager2Id);
      if (d.manager3Id) userIds.add(d.manager3Id);
      if (d.hrbpId) userIds.add(d.hrbpId);
    });

    const users = userIds.size
      ? await prisma.user.findMany({
          where: { id: { in: Array.from(userIds) } },
          select: { id: true, realName: true, username: true },
        })
      : [];
    const userMap = new Map(users.map(u => [u.id, u]));

    const data = departments.map(d => ({
      ...d,
      manager: d.managerId ? userMap.get(d.managerId) : null,
      manager2: d.manager2Id ? userMap.get(d.manager2Id) : null,
      manager3: d.manager3Id ? userMap.get(d.manager3Id) : null,
      hrbp: d.hrbpId ? userMap.get(d.hrbpId) : null,
    }));

    res.json({ success: true, data });
  } catch (error) {
    next(error);
  }
});

// 获取部门树形结构
router.get('/tree', async (req, res, next) => {
  try {
    const departments = await prisma.department.findMany({
      where: { status: 'ACTIVE' },
      orderBy: [{ sortOrder: 'asc' }, { code: 'asc' }],
    });

    const userIds = new Set();
    departments.forEach(d => {
      if (d.managerId) userIds.add(d.managerId);
      if (d.manager2Id) userIds.add(d.manager2Id);
      if (d.manager3Id) userIds.add(d.manager3Id);
      if (d.hrbpId) userIds.add(d.hrbpId);
    });

    const users = userIds.size
      ? await prisma.user.findMany({
          where: { id: { in: Array.from(userIds) } },
          select: { id: true, realName: true, username: true },
        })
      : [];
    const userMap = new Map(users.map(u => [u.id, u]));

    const enriched = departments.map(d => ({
      ...d,
      manager: d.managerId ? userMap.get(d.managerId) : null,
      manager2: d.manager2Id ? userMap.get(d.manager2Id) : null,
      manager3: d.manager3Id ? userMap.get(d.manager3Id) : null,
      hrbp: d.hrbpId ? userMap.get(d.hrbpId) : null,
    }));

    const map = new Map();
    const roots = [];
    enriched.forEach(d => { map.set(d.id, { ...d, children: [] }); });
    enriched.forEach(d => {
      const node = map.get(d.id);
      if (d.parentId && map.has(d.parentId)) {
        map.get(d.parentId).children.push(node);
      } else {
        roots.push(node);
      }
    });

    res.json({ success: true, data: roots });
  } catch (error) {
    next(error);
  }
});

// 获取单个部门
router.get('/:id', async (req, res, next) => {
  try {
    const department = await prisma.department.findUnique({
      where: { id: req.params.id },
    });

    if (!department) {
      return res.status(404).json({ success: false, message: '部门不存在' });
    }

    const userIds = [department.managerId, department.manager2Id, department.manager3Id, department.hrbpId].filter(Boolean);
    const users = userIds.length
      ? await prisma.user.findMany({
          where: { id: { in: userIds } },
          select: { id: true, realName: true, username: true },
        })
      : [];

    res.json({
      success: true,
      data: {
        ...department,
        manager: users.find(u => u.id === department.managerId) || null,
        manager2: users.find(u => u.id === department.manager2Id) || null,
        manager3: users.find(u => u.id === department.manager3Id) || null,
        hrbp: users.find(u => u.id === department.hrbpId) || null,
      },
    });
  } catch (error) {
    next(error);
  }
});

// 创建部门
router.post('/', async (req, res, next) => {
  try {
    const {
      name, code, parentId, managerId, manager2Id, manager3Id, hrbpId,
      sortOrder, status,
    } = req.body;

    if (!name || !code) {
      return res.status(400).json({ success: false, message: '部门名称和部门编号不能为空' });
    }

    // 检查 code 唯一
    const existing = await prisma.department.findUnique({ where: { code } });
    if (existing) {
      return res.status(400).json({ success: false, message: '部门编号已存在' });
    }

    // 计算 path/level
    let parentPath = '';
    let level = 1;
    if (parentId) {
      const parent = await prisma.department.findUnique({ where: { id: parentId } });
      if (!parent) {
        return res.status(400).json({ success: false, message: '上级部门不存在' });
      }
      parentPath = parent.path;
      level = computeLevel(parentPath);
    }

    const department = await prisma.department.create({
      data: {
        name,
        code,
        parentId: parentId || null,
        level,
        path: buildDeptPath(parentPath, code),
        managerId: managerId || null,
        manager2Id: manager2Id || null,
        manager3Id: manager3Id || null,
        hrbpId: hrbpId || null,
        sortOrder: typeof sortOrder === 'number' ? sortOrder : 0,
        status: status || 'ACTIVE',
      },
    });

    res.json({ success: true, data: department });
  } catch (error) {
    if (error.code === 'P2002') {
      return res.status(400).json({ success: false, message: '部门编号已存在' });
    }
    next(error);
  }
});

// 更新部门
router.put('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const {
      name, code, parentId, managerId, manager2Id, manager3Id, hrbpId,
      sortOrder, status,
    } = req.body;

    const current = await prisma.department.findUnique({ where: { id } });
    if (!current) {
      return res.status(404).json({ success: false, message: '部门不存在' });
    }

    // 不能将部门的上级设置为自己或自己的子部门
    if (parentId) {
      if (parentId === id) {
        return res.status(400).json({ success: false, message: '上级部门不能是本部门' });
      }
      const newParent = await prisma.department.findUnique({ where: { id: parentId } });
      if (!newParent) {
        return res.status(400).json({ success: false, message: '上级部门不存在' });
      }
      if (newParent.path.startsWith(current.path + '/')) {
        return res.status(400).json({ success: false, message: '上级部门不能是本部门的子部门' });
      }
    }

    // 检查 code 冲突
    if (code && code !== current.code) {
      const dup = await prisma.department.findUnique({ where: { code } });
      if (dup && dup.id !== id) {
        return res.status(400).json({ success: false, message: '部门编号已存在' });
      }
    }

    // 重新计算 path/level
    let newPath = current.path;
    let newLevel = current.level;
    if (parentId !== undefined && parentId !== current.parentId) {
      let parentPath = '';
      if (parentId) {
        const parent = await prisma.department.findUnique({ where: { id: parentId } });
        parentPath = parent?.path || '';
      }
      const targetCode = code || current.code;
      newPath = buildDeptPath(parentPath, targetCode);
      newLevel = computeLevel(parentPath);
    } else if (code && code !== current.code) {
      // 编号变化但上级未变化，重建 path
      const segments = current.path.split('/');
      segments[segments.length - 1] = code;
      newPath = segments.join('/');
    }

    const updated = await prisma.department.update({
      where: { id },
      data: {
        name: name !== undefined ? name : current.name,
        code: code !== undefined ? code : current.code,
        parentId: parentId !== undefined ? (parentId || null) : current.parentId,
        level: newLevel,
        path: newPath,
        managerId: managerId !== undefined ? (managerId || null) : current.managerId,
        manager2Id: manager2Id !== undefined ? (manager2Id || null) : current.manager2Id,
        manager3Id: manager3Id !== undefined ? (manager3Id || null) : current.manager3Id,
        hrbpId: hrbpId !== undefined ? (hrbpId || null) : current.hrbpId,
        sortOrder: sortOrder !== undefined ? sortOrder : current.sortOrder,
        status: status !== undefined ? status : current.status,
      },
    });

    // 若 path 改变，级联更新子部门 path
    if (newPath !== current.path) {
      const oldPrefix = current.path;
      const newPrefix = newPath;
      const children = await prisma.department.findMany({
        where: { path: { startsWith: oldPrefix + '/' } },
      });
      for (const child of children) {
        const childNewPath = newPrefix + child.path.substring(oldPrefix.length);
        await prisma.department.update({
          where: { id: child.id },
          data: { path: childNewPath, level: childNewPath.split('/').length },
        });
      }
    }

    res.json({ success: true, data: updated });
  } catch (error) {
    if (error.code === 'P2025') {
      return res.status(404).json({ success: false, message: '部门不存在' });
    }
    if (error.code === 'P2002') {
      return res.status(400).json({ success: false, message: '部门编号已存在' });
    }
    next(error);
  }
});

// 删除部门
router.delete('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;

    // 检查是否有子部门
    const childCount = await prisma.department.count({ where: { parentId: id } });
    if (childCount > 0) {
      return res.status(400).json({ success: false, message: '该部门下存在子部门，请先删除子部门' });
    }

    // 检查是否有关联用户
    const userCount = await prisma.user.count({ where: { departmentId: id } });
    if (userCount > 0) {
      return res.status(400).json({ success: false, message: '该部门下存在用户，请先调整用户部门' });
    }

    // 检查是否有关联需求/职位
    const demandCount = await prisma.demand.count({ where: { departmentId: id } });
    if (demandCount > 0) {
      return res.status(400).json({ success: false, message: '该部门下存在招聘需求，请先处理' });
    }
    const positionCount = await prisma.position.count({ where: { departmentId: id } });
    if (positionCount > 0) {
      return res.status(400).json({ success: false, message: '该部门下存在职位，请先处理' });
    }

    await prisma.department.delete({ where: { id } });

    res.json({ success: true, message: '部门删除成功' });
  } catch (error) {
    if (error.code === 'P2025') {
      return res.status(404).json({ success: false, message: '部门不存在' });
    }
    next(error);
  }
});

export default router;
