import express from 'express';
import { PrismaClient } from '@prisma/client';

const router = express.Router();
const prisma = new PrismaClient();

// 权限验证中间件
const permissionMiddleware = async (req, res, next) => {
  const userId = req.user?.id;
  if (!userId) {
    return res.status(401).json({ error: '未授权访问' });
  }
  
  // 获取用户角色和权限
  const userRoles = await prisma.userRole.findMany({
    where: { userId, status: 'ACTIVE' },
    include: { role: { include: { rolePermissions: { include: { permission: true } } } } }
  });
  
  const permissions = [];
  userRoles.forEach(ur => {
    ur.role.rolePermissions.forEach(rp => {
      if (rp.grantType === 'GRANT') {
        permissions.push(rp.permission);
      }
    });
  });
  
  req.userPermissions = permissions;
  next();
};

// 获取菜单权限树
router.get('/menus', permissionMiddleware, async (req, res) => {
  try {
    const menuPermissions = req.userPermissions.filter(p => p.permissionType === 'MENU' && p.status === 'ACTIVE');
    
    // 构建菜单树
    const buildMenuTree = (permissions, parentId = null) => {
      return permissions
        .filter(p => p.parentId === parentId)
        .map(p => ({
          id: p.id,
          name: p.name,
          code: p.code,
          path: p.resource,
          children: buildMenuTree(permissions, p.id)
        }));
    };
    
    const menuTree = buildMenuTree(menuPermissions);
    res.json({ success: true, data: menuTree });
  } catch (error) {
    next(error);
  }
});

// 获取功能权限列表
router.get('/functions', permissionMiddleware, async (req, res) => {
  try {
    const functionPermissions = req.userPermissions.filter(p => p.permissionType === 'FUNCTION' && p.status === 'ACTIVE');
    res.json({ success: true, data: functionPermissions });
  } catch (error) {
    next(error);
  }
});

// 获取数据权限范围
router.get('/data-scope', permissionMiddleware, async (req, res) => {
  try {
    const userId = req.user.id;
    
    // 获取用户数据权限规则
    const userDataPermissions = await prisma.userDataPermission.findMany({
      where: { userId, status: 'ACTIVE' },
      include: { rule: true }
    });
    
    const dataScopes = userDataPermissions.map(udp => ({
      ruleId: udp.ruleId,
      ruleCode: udp.rule.code,
      scopeType: udp.rule.ruleScope,
      customScope: udp.customScope,
      deptIds: udp.deptIds ? JSON.parse(udp.deptIds) : [],
      userIds: udp.userIds ? JSON.parse(udp.userIds) : []
    }));
    
    res.json({ success: true, data: dataScopes });
  } catch (error) {
    next(error);
  }
});

// ========== 角色管理 ==========

// 获取角色列表
router.get('/roles', async (req, res) => {
  try {
    const roles = await prisma.role.findMany({
      where: { status: 'ACTIVE' },
      orderBy: [{ isBuiltIn: 'desc' }, { sortOrder: 'asc' }]
    });
    res.json({ success: true, data: roles });
  } catch (error) {
    next(error);
  }
});

// 获取角色详情（包含权限）
router.get('/roles/:id', async (req, res) => {
  try {
    const role = await prisma.role.findUnique({
      where: { id: req.params.id },
      include: {
        rolePermissions: { include: { permission: true } }
      }
    });
    if (!role) {
      return res.status(404).json({ error: '角色不存在' });
    }
    res.json({ success: true, data: role });
  } catch (error) {
    next(error);
  }
});

// 创建角色
router.post('/roles', async (req, res) => {
  try {
    const { name, code, description, roleType, sortOrder, permissionIds } = req.body;
    
    // 检查编码是否重复
    const existing = await prisma.role.findUnique({ where: { code } });
    if (existing) {
      return res.status(400).json({ error: '角色编码已存在' });
    }
    
    const role = await prisma.role.create({
      data: {
        name,
        code,
        description,
        roleType: roleType || 'SYSTEM',
        sortOrder: sortOrder || 0,
        isBuiltIn: false
      }
    });
    
    // 关联权限
    if (permissionIds && permissionIds.length > 0) {
      await prisma.rolePermission.createMany({
        data: permissionIds.map(permissionId => ({
          roleId: role.id,
          permissionId,
          grantType: 'GRANT'
        }))
      });
    }
    
    res.json({ success: true, data: role });
  } catch (error) {
    next(error);
  }
});

// 更新角色
router.put('/roles/:id', async (req, res) => {
  try {
    const { name, description, sortOrder, permissionIds } = req.body;
    const roleId = req.params.id;
    
    const role = await prisma.role.findUnique({ where: { id: roleId } });
    if (!role) {
      return res.status(404).json({ error: '角色不存在' });
    }
    
    if (role.isBuiltIn) {
      return res.status(400).json({ error: '内置角色不可修改' });
    }
    
    const updated = await prisma.role.update({
      where: { id: roleId },
      data: { name, description, sortOrder }
    });
    
    // 更新权限关联
    if (permissionIds !== undefined) {
      // 删除旧权限
      await prisma.rolePermission.deleteMany({ where: { roleId } });
      
      // 添加新权限
      if (permissionIds.length > 0) {
        await prisma.rolePermission.createMany({
          data: permissionIds.map(permissionId => ({
            roleId,
            permissionId,
            grantType: 'GRANT'
          }))
        });
      }
    }
    
    res.json({ success: true, data: updated });
  } catch (error) {
    next(error);
  }
});

// 删除角色
router.delete('/roles/:id', async (req, res) => {
  try {
    const role = await prisma.role.findUnique({ where: { id: req.params.id } });
    if (!role) {
      return res.status(404).json({ error: '角色不存在' });
    }
    
    if (role.isBuiltIn) {
      return res.status(400).json({ error: '内置角色不可删除' });
    }
    
    // 检查是否有用户使用此角色
    const userCount = await prisma.userRole.count({ where: { roleId: req.params.id } });
    if (userCount > 0) {
      return res.status(400).json({ error: '该角色已被用户使用，无法删除' });
    }
    
    await prisma.rolePermission.deleteMany({ where: { roleId: req.params.id } });
    await prisma.role.delete({ where: { id: req.params.id } });
    
    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});

// ========== 权限管理 ==========

// 获取权限树（所有权限）
router.get('/permissions', async (req, res) => {
  try {
    const permissions = await prisma.permission.findMany({
      where: { status: 'ACTIVE' },
      orderBy: [{ permissionType: 'asc' }, { sortOrder: 'asc' }]
    });
    
    // 构建权限树
    const buildTree = (perms, parentId = null) => {
      return perms
        .filter(p => p.parentId === parentId)
        .map(p => ({
          ...p,
          children: buildTree(perms, p.id)
        }));
    };
    
    const tree = buildTree(permissions);
    res.json({ success: true, data: tree });
  } catch (error) {
    next(error);
  }
});

// 获取权限列表（扁平结构）
router.get('/permissions/list', async (req, res) => {
  try {
    const { type } = req.query;
    const where = { status: 'ACTIVE' };
    if (type) {
      where.permissionType = type;
    }
    
    const permissions = await prisma.permission.findMany({
      where,
      orderBy: [{ permissionType: 'asc' }, { sortOrder: 'asc' }]
    });
    
    res.json({ success: true, data: permissions });
  } catch (error) {
    next(error);
  }
});

// 创建权限
router.post('/permissions', async (req, res) => {
  try {
    const { name, code, permissionType, resource, action, dataScope, parentId, description, sortOrder } = req.body;
    
    // 检查编码是否重复
    const existing = await prisma.permission.findUnique({ where: { code } });
    if (existing) {
      return res.status(400).json({ error: '权限编码已存在' });
    }
    
    // 计算级别和路径
    let level = 1;
    let path = code;
    if (parentId) {
      const parent = await prisma.permission.findUnique({ where: { id: parentId } });
      if (parent) {
        level = parent.level + 1;
        path = parent.path + '/' + code;
      }
    }
    
    const permission = await prisma.permission.create({
      data: {
        name,
        code,
        permissionType,
        resource,
        action,
        dataScope,
        parentId,
        level,
        path,
        description,
        sortOrder: sortOrder || 0
      }
    });
    
    res.json({ success: true, data: permission });
  } catch (error) {
    next(error);
  }
});

// 更新权限
router.put('/permissions/:id', async (req, res) => {
  try {
    const { name, description, sortOrder, status } = req.body;
    
    const permission = await prisma.permission.update({
      where: { id: req.params.id },
      data: { name, description, sortOrder, status }
    });
    
    res.json({ success: true, data: permission });
  } catch (error) {
    next(error);
  }
});

// 删除权限
router.delete('/permissions/:id', async (req, res) => {
  try {
    // 检查是否有子权限
    const childCount = await prisma.permission.count({ where: { parentId: req.params.id } });
    if (childCount > 0) {
      return res.status(400).json({ error: '请先删除子权限' });
    }
    
    // 删除角色权限关联
    await prisma.rolePermission.deleteMany({ where: { permissionId: req.params.id } });
    
    await prisma.permission.delete({ where: { id: req.params.id } });
    
    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});

// ========== 用户角色管理 ==========

// 获取用户角色
router.get('/users/:userId/roles', async (req, res) => {
  try {
    const userRoles = await prisma.userRole.findMany({
      where: { userId: req.params.userId, status: 'ACTIVE' },
      include: { role: true }
    });
    res.json({ success: true, data: userRoles });
  } catch (error) {
    next(error);
  }
});

// 分配用户角色
router.post('/users/:userId/roles', async (req, res) => {
  try {
    const { roleIds, scope } = req.body;
    const userId = req.params.userId;
    
    // 先删除现有角色
    await prisma.userRole.deleteMany({ where: { userId } });
    
    // 添加新角色
    if (roleIds && roleIds.length > 0) {
      await prisma.userRole.createMany({
        data: roleIds.map(roleId => ({
          userId,
          roleId,
          scope,
          createdBy: req.user?.id
        }))
      });
    }
    
    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});

// ========== 数据权限规则 ==========

// 获取数据权限规则列表
router.get('/data-rules', async (req, res) => {
  try {
    const rules = await prisma.dataPermissionRule.findMany({
      where: { status: 'ACTIVE' },
      orderBy: { priority: 'asc' }
    });
    res.json({ success: true, data: rules });
  } catch (error) {
    next(error);
  }
});

// 创建数据权限规则
router.post('/data-rules', async (req, res) => {
  try {
    const { name, code, description, permissionType, ruleScope, ruleExpression, roleIds, priority } = req.body;
    
    const rule = await prisma.dataPermissionRule.create({
      data: {
        name,
        code,
        description,
        permissionType,
        ruleScope,
        ruleExpression,
        roleIds: roleIds ? JSON.stringify(roleIds) : null,
        priority: priority || 0
      }
    });
    
    res.json({ success: true, data: rule });
  } catch (error) {
    next(error);
  }
});

// ========== 权限检查 ==========

// 检查用户是否有特定权限
router.post('/check', permissionMiddleware, async (req, res) => {
  try {
    const { resource, action, permissionType } = req.body;
    
    const hasPermission = req.userPermissions.some(p => {
      if (permissionType && p.permissionType !== permissionType) return false;
      if (resource && p.resource !== resource) return false;
      if (action && p.action !== action && p.action !== '*') return false;
      return true;
    });
    
    res.json({ success: true, hasPermission });
  } catch (error) {
    next(error);
  }
});

// 获取用户完整权限信息
router.get('/user-info', permissionMiddleware, async (req, res) => {
  try {
    const userId = req.user.id;
    
    // 获取用户信息
    const user = await prisma.user.findUnique({
      where: { id: userId },
      include: {
        userRoles: { include: { role: true } },
        userDataPermissions: { include: { rule: true } }
      }
    });
    
    // 获取用户菜单权限
    const menuPermissions = req.userPermissions
      .filter(p => p.permissionType === 'MENU')
      .map(p => ({ id: p.id, name: p.name, code: p.code, path: p.resource }));
    
    // 获取用户功能权限
    const functionPermissions = req.userPermissions
      .filter(p => p.permissionType === 'FUNCTION')
      .map(p => ({ id: p.id, name: p.name, code: p.code, action: p.action }));
    
    // 获取数据权限范围
    const dataScopes = user.userDataPermissions.map(udp => ({
      type: udp.rule.permissionType,
      scope: udp.rule.ruleScope,
      customScope: udp.customScope,
      deptIds: udp.deptIds ? JSON.parse(udp.deptIds) : [],
      userIds: udp.userIds ? JSON.parse(udp.userIds) : []
    }));
    
    res.json({
      success: true,
      data: {
        user: {
          id: user.id,
          username: user.username,
          realName: user.realName,
          roleType: user.roleType,
          departmentId: user.departmentId
        },
        roles: user.userRoles.map(ur => ur.role),
        menus: menuPermissions,
        functions: functionPermissions,
        dataScopes
      }
    });
  } catch (error) {
    next(error);
  }
});

export default router;