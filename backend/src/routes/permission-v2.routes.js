/**
 * ATS权限管理系统 V2.0 - 增强版路由
 * 支持: MOU管理单元、容器模型、自动化规则、权限审计
 */

import express from 'express';
import { PrismaClient } from '@prisma/client';

const router = express.Router();
const prisma = new PrismaClient();

// ========== MOU管理单元 ==========

// 获取MOU列表
router.get('/mou', async (req, res, next) => {
  try {
    const { type, status } = req.query;
    const where = {};
    if (type) where.type = type;
    if (status) where.status = status;
    
    const mous = await prisma.mou.findMany({
      where,
      include: {
        parent: true,
        _count: { select: { children: true, userMous: true } }
      },
      orderBy: { createdAt: 'desc' }
    });
    
    res.json({ success: true, data: mous });
  } catch (error) {
    next(error);
  }
});

// 创建MOU
router.post('/mou', async (req, res, next) => {
  try {
    const { name, code, type, mouType, description, parentMouId, metadata, scopes } = req.body;

    // 优先使用 mouType（前端字段名），fallback 到 type
    const mouTypeValue = mouType || type;

    // 检查编码唯一性
    const existing = await prisma.mou.findUnique({ where: { code } });
    if (existing) {
      return res.status(400).json({ success: false, message: 'MOU编码已存在' });
    }

    // 计算层级和路径
    let level = 1;
    let path = code;
    if (parentMouId) {
      const parent = await prisma.mou.findUnique({ where: { id: parentMouId } });
      if (parent) {
        level = parent.level + 1;
        path = parent.path + '/' + code;
      }
    }

    const mou = await prisma.mou.create({
      data: {
        name,
        code,
        type: mouTypeValue,
        description,
        parentMouId,
        level,
        path,
        scopes: scopes ? JSON.stringify(scopes) : null,
        metadata: metadata ? JSON.stringify(metadata) : null
      }
    });

    // 返回前把 scopes parse 回对象（前端消费）
    const responseMou = {
      ...mou,
      scopes: mou.scopes ? JSON.parse(mou.scopes) : null
    };

    res.status(201).json({ success: true, data: responseMou });
  } catch (error) {
    next(error);
  }
});

// 更新MOU
router.put('/mou/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { name, description, metadata, scopes, status, startDate, endDate } = req.body;

    const mou = await prisma.mou.update({
      where: { id },
      data: {
        name,
        description,
        metadata: metadata ? JSON.stringify(metadata) : null,
        scopes: scopes !== undefined ? (scopes ? JSON.stringify(scopes) : null) : undefined,
        status,
        startDate: startDate ? new Date(startDate) : null,
        endDate: endDate ? new Date(endDate) : null
      }
    });

    const responseMou = {
      ...mou,
      scopes: mou.scopes ? JSON.parse(mou.scopes) : null
    };

    res.json({ success: true, data: responseMou });
  } catch (error) {
    next(error);
  }
});

// 获取MOU的权限范围（结构化 scopes）
router.get('/mou/:id/scopes', async (req, res, next) => {
  try {
    const { id } = req.params;
    const mou = await prisma.mou.findUnique({ where: { id } });
    if (!mou) {
      return res.status(404).json({ success: false, message: 'MOU不存在' });
    }

    const defaultScopes = { menu: [], function: [], data: { scope: 'ALL' } };
    const scopes = mou.scopes ? JSON.parse(mou.scopes) : defaultScopes;

    res.json({ success: true, data: scopes });
  } catch (error) {
    next(error);
  }
});

// 删除MOU
router.delete('/mou/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    
    // 检查是否有子MOU
    const childCount = await prisma.mou.count({ where: { parentMouId: id } });
    if (childCount > 0) {
      return res.status(400).json({ success: false, message: '请先删除子MOU' });
    }
    
    // 检查是否有用户关联
    const userCount = await prisma.userMou.count({ where: { mouId: id } });
    if (userCount > 0) {
      return res.status(400).json({ success: false, message: '请先移除MOU下的所有用户' });
    }
    
    await prisma.mou.delete({ where: { id } });
    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});

// 添加用户到MOU
router.post('/mou/:mouId/users', async (req, res, next) => {
  try {
    const { mouId } = req.params;
    const { userId, roleInMou, startDate, endDate } = req.body;
    
    const userMou = await prisma.userMou.create({
      data: {
        userId,
        mouId,
        roleInMou,
        startDate: startDate ? new Date(startDate) : null,
        endDate: endDate ? new Date(endDate) : null
      },
      include: { user: true, mou: true }
    });
    
    // 记录审计日志
    await prisma.permissionAuditLog.create({
      data: {
        userId,
        action: 'bind_mou',
        targetType: 'mou',
        targetId: mouId,
        targetName: userMou.mou.name,
        source: 'manual',
        operatorId: req.user?.id,
        operatorName: req.user?.realName
      }
    });
    
    res.status(201).json({ success: true, data: userMou });
  } catch (error) {
    if (error.code === 'P2002') {
      return res.status(400).json({ success: false, message: '用户已在该MOU中' });
    }
    next(error);
  }
});

// 移除MOU用户
router.delete('/mou/:mouId/users/:userId', async (req, res, next) => {
  try {
    const { mouId, userId } = req.params;
    
    const userMou = await prisma.userMou.findUnique({
      where: { userId_mouId: { userId, mouId } },
      include: { mou: true }
    });
    
    await prisma.userMou.delete({
      where: { userId_mouId: { userId, mouId } }
    });
    
    // 记录审计日志
    await prisma.permissionAuditLog.create({
      data: {
        userId,
        action: 'unbind_mou',
        targetType: 'mou',
        targetId: mouId,
        targetName: userMou?.mou?.name,
        source: 'manual',
        operatorId: req.user?.id,
        operatorName: req.user?.realName
      }
    });
    
    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});

// 获取用户的MOU列表
router.get('/users/:userId/mou', async (req, res, next) => {
  try {
    const { userId } = req.params;
    
    const userMous = await prisma.userMou.findMany({
      where: { userId, status: 'ACTIVE' },
      include: {
        mou: {
          include: { _count: { select: { userMous: true } } }
        }
      }
    });
    
    res.json({ success: true, data: userMous });
  } catch (error) {
    next(error);
  }
});

// ========== 容器模型 ==========

// 获取用户的MOU列表 (兼容前端路径)
router.get('/mou/user-mous/:userId', async (req, res, next) => {
  try {
    const { userId } = req.params;

    const userMous = await prisma.userMou.findMany({
      where: { userId, status: 'ACTIVE' },
      include: {
        mou: {
          include: { _count: { select: { userMous: true } } }
        }
      }
    });

    res.json({ success: true, data: userMous });
  } catch (error) {
    next(error);
  }
});

// 获取容器列表
router.get('/containers', async (req, res, next) => {
  try {
    const { type, status } = req.query;
    const where = {};
    if (type) where.type = type;
    if (status) where.status = status;
    
    const containers = await prisma.permissionContainer.findMany({
      where,
      include: {
        mou: true,
        _count: { select: { userContainers: true, containerResources: true } }
      },
      orderBy: { createdAt: 'desc' }
    });
    
    res.json({ success: true, data: containers });
  } catch (error) {
    next(error);
  }
});

// 创建容器
router.post('/containers', async (req, res, next) => {
  try {
    const { name, code, type, description, mouId, resourceFilter } = req.body;
    
    const existing = await prisma.permissionContainer.findUnique({ where: { code } });
    if (existing) {
      return res.status(400).json({ success: false, message: '容器编码已存在' });
    }
    
    const container = await prisma.permissionContainer.create({
      data: {
        name,
        code,
        type,
        description,
        mouId,
        resourceFilter: resourceFilter ? JSON.stringify(resourceFilter) : null
      },
      include: { mou: true }
    });
    
    res.status(201).json({ success: true, data: container });
  } catch (error) {
    next(error);
  }
});

// 更新容器
router.put('/containers/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { name, description, mouId, resourceFilter, status } = req.body;
    
    const container = await prisma.permissionContainer.update({
      where: { id },
      data: {
        name,
        description,
        mouId,
        resourceFilter: resourceFilter ? JSON.stringify(resourceFilter) : null,
        status
      },
      include: { mou: true }
    });
    
    res.json({ success: true, data: container });
  } catch (error) {
    next(error);
  }
});

// 删除容器
router.delete('/containers/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    
    // 检查是否有用户关联
    const userCount = await prisma.userContainer.count({ where: { containerId: id } });
    if (userCount > 0) {
      return res.status(400).json({ success: false, message: '请先移除容器下的所有用户' });
    }
    
    await prisma.permissionContainer.delete({ where: { id } });
    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});

// 添加用户到容器
router.post('/containers/:containerId/users', async (req, res, next) => {
  try {
    const { containerId } = req.params;
    const { userId, accessLevel, startDate, endDate } = req.body;
    
    const userContainer = await prisma.userContainer.create({
      data: {
        userId,
        containerId,
        accessLevel,
        startDate: startDate ? new Date(startDate) : null,
        endDate: endDate ? new Date(endDate) : null
      },
      include: { container: true }
    });
    
    // 记录审计日志
    await prisma.permissionAuditLog.create({
      data: {
        userId,
        action: 'bind_container',
        targetType: 'container',
        targetId: containerId,
        targetName: userContainer.container.name,
        source: 'manual',
        operatorId: req.user?.id,
        operatorName: req.user?.realName
      }
    });
    
    res.status(201).json({ success: true, data: userContainer });
  } catch (error) {
    if (error.code === 'P2002') {
      return res.status(400).json({ success: false, message: '用户已在该容器中' });
    }
    next(error);
  }
});

// 移除容器用户
router.delete('/containers/:containerId/users/:userId', async (req, res, next) => {
  try {
    const { containerId, userId } = req.params;
    
    const userContainer = await prisma.userContainer.findUnique({
      where: { userId_containerId: { userId, containerId } },
      include: { container: true }
    });
    
    await prisma.userContainer.delete({
      where: { userId_containerId: { userId, containerId } }
    });
    
    // 记录审计日志
    await prisma.permissionAuditLog.create({
      data: {
        userId,
        action: 'unbind_container',
        targetType: 'container',
        targetId: containerId,
        targetName: userContainer?.container?.name,
        source: 'manual',
        operatorId: req.user?.id,
        operatorName: req.user?.realName
      }
    });
    
    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});

// 添加资源到容器
router.post('/containers/:containerId/resources', async (req, res, next) => {
  try {
    const { containerId } = req.params;
    const { resourceType, resourceId } = req.body;
    
    const containerResource = await prisma.containerResource.create({
      data: { containerId, resourceType, resourceId }
    });
    
    res.status(201).json({ success: true, data: containerResource });
  } catch (error) {
    if (error.code === 'P2002') {
      return res.status(400).json({ success: false, message: '资源已在容器中' });
    }
    next(error);
  }
});

// 获取用户的容器列表
router.get('/users/:userId/containers', async (req, res, next) => {
  try {
    const { userId } = req.params;
    
    const userContainers = await prisma.userContainer.findMany({
      where: { userId, status: 'ACTIVE' },
      include: {
        container: {
          include: {
            mou: true,
            _count: { select: { containerResources: true } }
          }
        }
      }
    });
    
    res.json({ success: true, data: userContainers });
  } catch (error) {
    next(error);
  }
});

// ========== 自动化规则 ==========

// 获取自动化规则列表
router.get('/automation-rules', async (req, res, next) => {
  try {
    const { eventType, status } = req.query;
    const where = {};
    if (eventType) where.eventType = eventType;
    if (status) where.status = status;
    
    const rules = await prisma.automationRule.findMany({
      where,
      orderBy: [{ priority: 'desc' }, { createdAt: 'desc' }]
    });
    
    res.json({ success: true, data: rules });
  } catch (error) {
    next(error);
  }
});

// 创建自动化规则
router.post('/automation-rules', async (req, res, next) => {
  try {
    const { name, code, description, eventType, condition, actions, priority } = req.body;
    
    const existing = await prisma.automationRule.findUnique({ where: { code } });
    if (existing) {
      return res.status(400).json({ success: false, message: '规则编码已存在' });
    }
    
    const rule = await prisma.automationRule.create({
      data: {
        name,
        code,
        description,
        eventType,
        condition: condition ? JSON.stringify(condition) : null,
        actions: JSON.stringify(actions)
      }
    });
    
    res.status(201).json({ success: true, data: rule });
  } catch (error) {
    next(error);
  }
});

// 更新自动化规则
router.put('/automation-rules/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { name, description, condition, actions, priority, status } = req.body;
    
    const rule = await prisma.automationRule.update({
      where: { id },
      data: {
        name,
        description,
        condition: condition ? JSON.stringify(condition) : null,
        actions: JSON.stringify(actions),
        priority,
        status
      }
    });
    
    res.json({ success: true, data: rule });
  } catch (error) {
    next(error);
  }
});

// 删除自动化规则
router.delete('/automation-rules/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    await prisma.automationRule.delete({ where: { id } });
    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});

// 执行自动化规则（内部调用）
router.post('/automation-rules/:id/execute', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { userId, context } = req.body;
    
    const rule = await prisma.automationRule.findUnique({ where: { id } });
    if (!rule || rule.status !== 'ACTIVE') {
      return res.status(400).json({ success: false, message: '规则不存在或未启用' });
    }
    
    // 解析条件和动作
    const actions = JSON.parse(rule.actions);
    const condition = rule.condition ? JSON.parse(rule.condition) : null;
    
    // 检查条件
    if (condition && !evaluateCondition(condition, context)) {
      return res.json({ success: true, executed: false, reason: '条件不满足' });
    }
    
    // 执行动作
    const results = [];
    for (const action of actions) {
      const result = await executeAction(action, userId, req.user?.id);
      results.push(result);
    }
    
    // 记录执行日志
    await prisma.automationLog.create({
      data: {
        ruleId: id,
        triggerUserId: userId,
        triggerEvent: rule.eventType,
        executedActions: JSON.stringify(results),
        result: 'success'
      }
    });
    
    res.json({ success: true, executed: true, results });
  } catch (error) {
    next(error);
  }
});

// 获取自动化规则执行日志
router.get('/automation-rules/:id/logs', async (req, res, next) => {
  try {
    const { id } = req.params;
    const logs = await prisma.automationLog.findMany({
      where: { ruleId: id },
      orderBy: { executedAt: 'desc' },
      take: 50
    });
    res.json({ success: true, data: logs });
  } catch (error) {
    next(error);
  }
});

// ========== 互斥角色组 ==========

// 获取互斥角色组列表
router.get('/mutual-exclusion-groups', async (req, res, next) => {
  try {
    const groups = await prisma.mutualExclusionGroup.findMany({
      orderBy: { createdAt: 'desc' }
    });
    res.json({ success: true, data: groups });
  } catch (error) {
    next(error);
  }
});

// 创建互斥角色组
router.post('/mutual-exclusion-groups', async (req, res, next) => {
  try {
    const { name, description, roleIds } = req.body;
    
    const group = await prisma.mutualExclusionGroup.create({
      data: {
        name,
        description,
        roleIds: JSON.stringify(roleIds)
      }
    });
    
    res.status(201).json({ success: true, data: group });
  } catch (error) {
    next(error);
  }
});

// 删除互斥角色组
router.delete('/mutual-exclusion-groups/:id', async (req, res, next) => {
  try {
    await prisma.mutualExclusionGroup.delete({ where: { id: req.params.id } });
    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});

// ========== 权限审计日志 ==========

// 获取权限审计日志
router.get('/audit-logs', async (req, res, next) => {
  try {
    const { userId, action, targetType, startDate, endDate, page = 1, pageSize = 20 } = req.query;
    
    const where = {};
    if (userId) where.userId = userId;
    if (action) where.action = action;
    if (targetType) where.targetType = targetType;
    if (startDate || endDate) {
      where.createdAt = {};
      if (startDate) where.createdAt.gte = new Date(startDate);
      if (endDate) where.createdAt.lte = new Date(endDate);
    }
    
    const [logs, total] = await Promise.all([
      prisma.permissionAuditLog.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip: (page - 1) * pageSize,
        take: parseInt(pageSize)
      }),
      prisma.permissionAuditLog.count({ where })
    ]);
    
    res.json({ success: true, data: logs, total, page: parseInt(page), pageSize: parseInt(pageSize) });
  } catch (error) {
    next(error);
  }
});

// ========== 辅助函数 ==========

// 评估条件
function evaluateCondition(condition, context) {
  if (!condition) return true;
  
  // 简单条件评估，可以扩展为更复杂的表达式
  for (const [key, value] of Object.entries(condition)) {
    if (context[key] !== value) {
      return false;
    }
  }
  return true;
}

// 执行动作
async function executeAction(action, userId, operatorId) {
  try {
    switch (action.type) {
      case 'assign_role':
        await prisma.userRole.upsert({
          where: { userId_roleId: { userId, roleId: action.role_id } },
          create: { userId, roleId: action.role_id, createdBy: operatorId },
          update: { status: 'ACTIVE' }
        });
        // 审计日志
        await prisma.permissionAuditLog.create({
          data: {
            userId,
            action: 'assign_role',
            targetType: 'role',
            targetId: action.role_id,
            source: 'automation',
            operatorId
          }
        });
        return { type: 'assign_role', success: true };
        
      case 'revoke_role':
        await prisma.userRole.updateMany({
          where: { userId, roleId: action.role_id },
          data: { status: 'INACTIVE' }
        });
        await prisma.permissionAuditLog.create({
          data: {
            userId,
            action: 'revoke_role',
            targetType: 'role',
            targetId: action.role_id,
            source: 'automation',
            operatorId
          }
        });
        return { type: 'revoke_role', success: true };
        
      case 'bind_mou':
        await prisma.userMou.upsert({
          where: { userId_mouId: { userId, mouId: action.mou_id } },
          create: { userId, mouId: action.mou_id },
          update: { status: 'ACTIVE' }
        });
        return { type: 'bind_mou', success: true };
        
      case 'bind_container':
        await prisma.userContainer.upsert({
          where: { userId_containerId: { userId, containerId: action.container_id } },
          create: { userId, containerId: action.container_id },
          update: { status: 'ACTIVE' }
        });
        return { type: 'bind_container', success: true };
        
      default:
        return { type: action.type, success: false, message: 'Unknown action type' };
    }
  } catch (error) {
    return { type: action.type, success: false, error: error.message };
  }
}

export default router;
