/**
 * 权限验证中间件
 * 支持菜单权限、功能权限、数据权限的验证
 */

import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

// 获取用户权限
export const getUserPermissions = async (userId) => {
  const userRoles = await prisma.userRole.findMany({
    where: { 
      userId, 
      status: 'ACTIVE',
      OR: [
        { startDate: null },
        { startDate: { lte: new Date() } }
      ],
      AND: [
        {
          OR: [
            { endDate: null },
            { endDate: { gte: new Date() } }
          ]
        }
      ]
    },
    include: { 
      role: { 
        include: { 
          rolePermissions: { 
            include: { permission: true } 
          } 
        } 
      } 
    }
  });
  
  const permissions = [];
  const denyPermissions = [];
  
  userRoles.forEach(ur => {
    ur.role.rolePermissions.forEach(rp => {
      if (rp.grantType === 'GRANT') {
        // 检查是否已有拒绝权限
        const hasDeny = denyPermissions.some(dp => dp.code === rp.permission.code);
        if (!hasDeny) {
          permissions.push(rp.permission);
        }
      } else if (rp.grantType === 'DENY') {
        denyPermissions.push(rp.permission);
      }
    });
  });
  
  return permissions;
};

// 获取用户数据权限范围
export const getUserDataScopes = async (userId) => {
  const userDataPermissions = await prisma.userDataPermission.findMany({
    where: { 
      userId, 
      status: 'ACTIVE',
      OR: [
        { startDate: null },
        { startDate: { lte: new Date() } }
      ],
      AND: [
        {
          OR: [
            { endDate: null },
            { endDate: { gte: new Date() } }
          ]
        }
      ]
    },
    include: { rule: true }
  });
  
  return userDataPermissions.map(udp => ({
    ruleId: udp.ruleId,
    ruleCode: udp.rule.code,
    permissionType: udp.rule.permissionType,
    scopeType: udp.rule.ruleScope,
    customScope: udp.customScope,
    deptIds: udp.deptIds ? JSON.parse(udp.deptIds) : [],
    userIds: udp.userIds ? JSON.parse(udp.userIds) : []
  }));
};

// 菜单权限验证中间件
export const menuPermission = (requiredMenus) => {
  return async (req, res, next) => {
    try {
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: '未授权访问', code: 'UNAUTHORIZED' });
      }
      
      // 管理员拥有所有权限
      if (req.user.roleType === 'SUPER_ADMIN') {
        return next();
      }
      
      const permissions = await getUserPermissions(userId);
      const menuPermissions = permissions.filter(p => p.permissionType === 'MENU');
      
      // 检查是否有必需的菜单权限
      const hasPermission = requiredMenus.every(menu => 
        menuPermissions.some(p => 
          p.resource === menu || 
          p.code === menu ||
          (p.path && menu.startsWith(p.path))
        )
      );
      
      if (!hasPermission) {
        return res.status(403).json({ 
          error: '您没有访问该页面的权限', 
          code: 'MENU_FORBIDDEN' 
        });
      }
      
      // 将权限信息附加到请求对象
      req.userPermissions = permissions;
      req.menuPermissions = menuPermissions;
      
      next();
    } catch (error) {
      console.error('Menu permission check error:', error);
      res.status(500).json({ error: '权限验证失败', code: 'PERMISSION_CHECK_FAILED' });
    }
  };
};

// 功能权限验证中间件
export const functionPermission = (requiredFunctions) => {
  return async (req, res, next) => {
    try {
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: '未授权访问', code: 'UNAUTHORIZED' });
      }
      
      // 管理员拥有所有权限
      if (req.user.roleType === 'SUPER_ADMIN') {
        return next();
      }
      
      // 从请求对象获取已加载的权限或重新获取
      let permissions = req.userPermissions;
      if (!permissions) {
        permissions = await getUserPermissions(userId);
      }
      
      const functionPermissions = permissions.filter(p => p.permissionType === 'FUNCTION');
      
      // 检查是否有必需的功能权限
      const hasPermission = requiredFunctions.every(func => 
        functionPermissions.some(p => 
          p.code === func || 
          p.resource === func ||
          p.action === func ||
          p.action === '*'
        )
      );
      
      if (!hasPermission) {
        return res.status(403).json({ 
          error: '您没有执行该操作的权限', 
          code: 'FUNCTION_FORBIDDEN' 
        });
      }
      
      next();
    } catch (error) {
      console.error('Function permission check error:', error);
      res.status(500).json({ error: '权限验证失败', code: 'PERMISSION_CHECK_FAILED' });
    }
  };
};

// 数据权限验证中间件
export const dataPermission = (resourceType) => {
  return async (req, res, next) => {
    try {
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: '未授权访问', code: 'UNAUTHORIZED' });
      }
      
      // 管理员拥有所有数据权限
      if (req.user.roleType === 'SUPER_ADMIN') {
        req.dataPermissionScope = 'ALL';
        return next();
      }
      
      // 获取数据权限范围
      const dataScopes = await getUserDataScopes(userId);
      const relevantScopes = dataScopes.filter(s => s.permissionType === resourceType);
      
      if (relevantScopes.length === 0) {
        // 如果没有配置数据权限，检查用户角色权限
        const permissions = await getUserPermissions(userId);
        const dataPerms = permissions.filter(p => p.permissionType === 'DATA');
        const hasDataPerm = dataPerms.some(p => p.dataScope === 'ALL');
        
        if (hasDataPerm) {
          req.dataPermissionScope = 'ALL';
        } else {
          // 默认只能访问本人数据
          req.dataPermissionScope = 'PERSONAL';
          req.dataPermissionFilter = { createdBy: userId };
        }
      } else {
        // 合并数据权限范围
        const scopes = relevantScopes.map(s => s.scopeType);
        if (scopes.includes('ALL')) {
          req.dataPermissionScope = 'ALL';
        } else if (scopes.includes('DEPT_AND_CHILD')) {
          req.dataPermissionScope = 'DEPT_AND_CHILD';
          // 需要获取用户部门及下级部门
          const user = await prisma.user.findUnique({
            where: { id: userId },
            include: { department: true }
          });
          req.dataPermissionFilter = { 
            departmentId: { in: await getChildDeptIds(user?.departmentId) }
          };
        } else if (scopes.includes('DEPT')) {
          req.dataPermissionScope = 'DEPT';
          const user = await prisma.user.findUnique({
            where: { id: userId },
            include: { department: true }
          });
          req.dataPermissionFilter = { departmentId: user?.departmentId };
        } else {
          req.dataPermissionScope = 'PERSONAL';
          req.dataPermissionFilter = { createdBy: userId };
        }
        
        // 处理自定义数据范围
        const customScopes = relevantScopes.filter(s => s.scopeType === 'CUSTOM');
        if (customScopes.length > 0) {
          req.customDataPermissions = customScopes;
        }
      }
      
      next();
    } catch (error) {
      console.error('Data permission check error:', error);
      res.status(500).json({ error: '权限验证失败', code: 'PERMISSION_CHECK_FAILED' });
    }
  };
};

// 获取子部门ID列表
const getChildDeptIds = async (parentDeptId) => {
  if (!parentDeptId) return [];
  
  const allDepts = await prisma.department.findMany({
    where: { status: 'ACTIVE' }
  });
  
  const childIds = [parentDeptId];
  const findChildren = (parentId) => {
    allDepts.forEach(dept => {
      if (dept.parentId === parentId && !childIds.includes(dept.id)) {
        childIds.push(dept.id);
        findChildren(dept.id);
      }
    });
  };
  
  findChildren(parentDeptId);
  return childIds;
};

// 组合权限验证中间件
export const requirePermission = (options = {}) => {
  const { menus = [], functions = [], dataType = null } = options;
  
  return async (req, res, next) => {
    try {
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: '未授权访问', code: 'UNAUTHORIZED' });
      }
      
      // 管理员拥有所有权限
      if (req.user.roleType === 'SUPER_ADMIN') {
        return next();
      }
      
      let permissions = req.userPermissions;
      if (!permissions) {
        permissions = await getUserPermissions(userId);
      }
      
      // 验证菜单权限
      if (menus.length > 0) {
        const menuPermissions = permissions.filter(p => p.permissionType === 'MENU');
        const hasMenuPermission = menus.every(menu => 
          menuPermissions.some(p => 
            p.resource === menu || 
            p.code === menu ||
            (p.path && menu.startsWith(p.path))
          )
        );
        
        if (!hasMenuPermission) {
          return res.status(403).json({ 
            error: '您没有访问该页面的权限', 
            code: 'MENU_FORBIDDEN' 
          });
        }
      }
      
      // 验证功能权限
      if (functions.length > 0) {
        const functionPermissions = permissions.filter(p => p.permissionType === 'FUNCTION');
        const hasFunctionPermission = functions.every(func => 
          functionPermissions.some(p => 
            p.code === func || 
            p.resource === func ||
            p.action === func ||
            p.action === '*'
          )
        );
        
        if (!hasFunctionPermission) {
          return res.status(403).json({ 
            error: '您没有执行该操作的权限', 
            code: 'FUNCTION_FORBIDDEN' 
          });
        }
      }
      
      // 验证数据权限
      if (dataType) {
        const dataScopes = await getUserDataScopes(userId);
        const relevantScopes = dataScopes.filter(s => s.permissionType === dataType);
        
        if (relevantScopes.length === 0) {
          const dataPerms = permissions.filter(p => p.permissionType === 'DATA');
          const hasDataPerm = dataPerms.some(p => p.dataScope === 'ALL');
          
          if (!hasDataPerm) {
            req.dataPermissionScope = 'PERSONAL';
            req.dataPermissionFilter = { createdBy: userId };
          } else {
            req.dataPermissionScope = 'ALL';
          }
        } else {
          const scopes = relevantScopes.map(s => s.scopeType);
          if (scopes.includes('ALL')) {
            req.dataPermissionScope = 'ALL';
          } else if (scopes.includes('DEPT_AND_CHILD')) {
            req.dataPermissionScope = 'DEPT_AND_CHILD';
            const user = await prisma.user.findUnique({
              where: { id: userId },
              include: { department: true }
            });
            req.dataPermissionFilter = { 
              departmentId: { in: await getChildDeptIds(user?.departmentId) }
            };
          } else if (scopes.includes('DEPT')) {
            req.dataPermissionScope = 'DEPT';
            const user = await prisma.user.findUnique({
              where: { id: userId },
              include: { department: true }
            });
            req.dataPermissionFilter = { departmentId: user?.departmentId };
          } else {
            req.dataPermissionScope = 'PERSONAL';
            req.dataPermissionFilter = { createdBy: userId };
          }
        }
      }
      
      req.userPermissions = permissions;
      next();
    } catch (error) {
      console.error('Permission check error:', error);
      res.status(500).json({ error: '权限验证失败', code: 'PERMISSION_CHECK_FAILED' });
    }
  };
};

// 检查特定权限
export const checkPermission = async (userId, permissionCode, permissionType = null) => {
  const permissions = await getUserPermissions(userId);
  
  return permissions.some(p => {
    if (permissionType && p.permissionType !== permissionType) return false;
    return p.code === permissionCode || p.resource === permissionCode || p.action === permissionCode;
  });
};

export default {
  getUserPermissions,
  getUserDataScopes,
  menuPermission,
  functionPermission,
  dataPermission,
  requirePermission,
  checkPermission
};