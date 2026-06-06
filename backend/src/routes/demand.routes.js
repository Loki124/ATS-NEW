/**
 * 招聘需求管理路由
 *
 * 状态机相关：
 *   GET  /api/demands/:id/approvals        审批步骤历史
 *   POST /api/demands/:id/submit           发起审批
 *   POST /api/demands/:id/approve         通过当前步骤
 *   POST /api/demands/:id/reject          拒绝 (需 reason)
 *   POST /api/demands/:id/cancel-approval 撤销审批 (仅创建人)
 *   POST /api/demands/:id/transition      状态转移 (target status)
 */

import express from 'express';
import { prisma } from '../app.js';
import { canTransitionDemand, DEMAND_STATUSES } from '../services/demand-state-machine.service.js';
import { submitForApproval, approveDemand, rejectDemand, cancelApproval } from '../services/demand-approval.service.js';

const router = express.Router();

// 获取所有需求
router.get('/', async (req, res, next) => {
  try {
    const { page = 1, pageSize = 10, keyword, status, departmentId } = req.query;

    const where = {};

    if (keyword) {
      where.OR = [
        { name: { contains: keyword } },
        { code: { contains: keyword } }
      ];
    }

    if (status) {
      where.demandStatus = status;
    }

    if (departmentId) {
      where.departmentId = departmentId;
    }

    const [demands, total] = await Promise.all([
      prisma.demand.findMany({
        where,
        include: {
          department: { select: { id: true, name: true, code: true } },
          _count: {
            select: {
              positions: true
            }
          }
        },
        orderBy: { createdAt: 'desc' },
        skip: (Number(page) - 1) * Number(pageSize),
        take: Number(pageSize)
      }),
      prisma.demand.count({ where })
    ]);

    res.json({
      success: true,
      data: {
        list: demands,
        pagination: {
          page: Number(page),
          pageSize: Number(pageSize),
          total,
          totalPages: Math.ceil(total / Number(pageSize))
        }
      }
    });
  } catch (error) {
    next(error);
  }
});

// 获取单个需求详情
router.get('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;

    const demand = await prisma.demand.findUnique({
      where: { id },
      include: {
        department: true,
        positions: {
          where: { status: 'ACTIVE' },
          include: {
            process: true,
            applications: { where: { applicationStatus: 'ACTIVE' } }
          }
        }
      }
    });

    if (!demand) {
      return res.status(404).json({
        success: false,
        message: '需求不存在'
      });
    }

    res.json({
      success: true,
      data: demand
    });
  } catch (error) {
    next(error);
  }
});

// 创建需求
router.post('/', async (req, res, next) => {
  try {
    const {
      name,
      departmentId,
      positionCount,
      demandType,
      positionSeries,
      jobTitle,
      jobLevel,
      startDate,
      endDate,
      salaryMin,
      salaryMax,
      description,
      requirements
    } = req.body;

    // 生成需求编号 (HC + 6位流水号)
    const count = await prisma.demand.count();
    const code = `HC${String(count + 1).padStart(6, '0')}`;

    const demand = await prisma.demand.create({
      data: {
        code,
        name,
        departmentId,
        positionCount: positionCount || 1,
        demandType,
        positionSeries,
        jobTitle,
        jobLevel,
        startDate: startDate ? new Date(startDate) : null,
        endDate: endDate ? new Date(endDate) : null,
        salaryMin,
        salaryMax,
        description,
        requirements,
        demandStatus: 'DRAFT',
        approvalStatus: 'NOT_STARTED',
        creatorId: req.userId
      },
      include: {
        department: true
      }
    });

    res.status(201).json({
      success: true,
      message: '需求创建成功',
      data: demand
    });
  } catch (error) {
    next(error);
  }
});

// 更新需求
router.put('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const updateData = req.body;

    // 删除不可更新的字段
    delete updateData.id;
    delete updateData.code;
    delete updateData.createdAt;
    delete updateData.creatorId;

    // 处理日期字段
    if (updateData.startDate) updateData.startDate = new Date(updateData.startDate);
    if (updateData.endDate) updateData.endDate = new Date(updateData.endDate);

    const demand = await prisma.demand.update({
      where: { id },
      data: updateData,
      include: {
        department: true
      }
    });

    res.json({
      success: true,
      message: '需求更新成功',
      data: demand
    });
  } catch (error) {
    if (error.code === 'P2025') {
      return res.status(404).json({
        success: false,
        message: '需求不存在'
      });
    }
    next(error);
  }
});

// 删除需求
router.delete('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;

    // 检查是否有职位关联
    const positionCount = await prisma.position.count({
      where: { demandId: id }
    });

    if (positionCount > 0) {
      return res.status(400).json({
        success: false,
        message: '该需求下有关联职位，无法删除'
      });
    }

    await prisma.demand.delete({
      where: { id }
    });

    res.json({
      success: true,
      message: '需求删除成功'
    });
  } catch (error) {
    if (error.code === 'P2025') {
      return res.status(404).json({
        success: false,
        message: '需求不存在'
      });
    }
    next(error);
  }
});

/**
 * 复制需求 (PRD G3)
 * POST /api/demands/:id/copy
 * body: { name? }  // 复制后名称, 默认 "原名 - 副本"
 * 注: 状态机、审批步骤、状态历史 不复制
 */
router.post('/:id/copy', async (req, res, next) => {
  try {
    const { id } = req.params
    const { name } = req.body || {}
    const source = await prisma.demand.findUnique({ where: { id } })
    if (!source) return res.status(404).json({ success: false, message: '需求不存在' })

    // 重新生成 code
    const count = await prisma.demand.count()
    const code = `HC${String(count + 1).padStart(6, '0')}`

    // 复制字段 (排除 id/code/审批相关/时间戳/状态)
    const excludeFields = ['id', 'code', 'creatorId', 'createdAt', 'updatedAt',
      'demandStatus', 'approvalStatus', 'salaryPlan', 'biddingAmount']
    const data = { code, name: name || `${source.name} - 副本` }
    for (const [k, v] of Object.entries(source)) {
      if (!excludeFields.includes(k) && v !== null && v !== undefined) {
        data[k] = v
      }
    }
    // 重置为初始态
    data.demandStatus = 'DRAFT'
    data.approvalStatus = 'NOT_STARTED'
    data.creatorId = req.userId

    const copy = await prisma.demand.create({ data })
    res.status(201).json({ success: true, message: '需求已复制', data: copy })
  } catch (e) { next(e) }
})

// 获取需求统计
router.get('/:id/stats', async (req, res, next) => {
  try {
    const { id } = req.params;

    const positions = await prisma.position.findMany({
      where: { demandId: id },
      include: {
        applications: { where: { applicationStatus: 'ACTIVE' } }
      }
    });

    const stats = {
      positionCount: positions.length,
      totalCandidates: positions.reduce((sum, p) => sum + p.applications.length, 0),
      hiredCount: positions.reduce((sum, p) => sum + (p.hiredCount || 0), 0),
      onBoardCount: positions.reduce((sum, p) => sum + (p.onBoardCount || 0), 0)
    };

    res.json({
      success: true,
      data: stats
    });
  } catch (error) {
    next(error);
  }
});

export default router;

// =====================================
// 状态机 + 审批 (G1 + G2)
// =====================================

// 发起审批
router.post('/:id/submit', async (req, res, next) => {
  try {
    const { id } = req.params;
    const userId = req.user?.id;
    const demand = await submitForApproval(id, userId);
    res.json({ success: true, data: demand });
  } catch (e) { next(e); }
});

// 审批通过
router.post('/:id/approve', async (req, res, next) => {
  try {
    const { id } = req.params;
    const userId = req.user?.id;
    const { comment } = req.body || {};
    const demand = await approveDemand(id, userId, comment);
    res.json({ success: true, data: demand });
  } catch (e) { next(e); }
});

// 审批拒绝
router.post('/:id/reject', async (req, res, next) => {
  try {
    const { id } = req.params;
    const userId = req.user?.id;
    const { reason } = req.body || {};
    const demand = await rejectDemand(id, userId, reason);
    res.json({ success: true, data: demand });
  } catch (e) { next(e); }
});

// 撤销审批
router.post('/:id/cancel-approval', async (req, res, next) => {
  try {
    const { id } = req.params;
    const userId = req.user?.id;
    const demand = await cancelApproval(id, userId);
    res.json({ success: true, data: demand });
  } catch (e) { next(e); }
});

// 审批步骤历史
router.get('/:id/approvals', async (req, res, next) => {
  try {
    const steps = await prisma.demandApprovalStep.findMany({
      where: { demandId: req.params.id },
      orderBy: { stepIndex: 'asc' },
    });
    res.json({ success: true, data: steps });
  } catch (e) { next(e); }
});

// 状态转移 (需求状态)
router.post('/:id/transition', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { to, reason } = req.body || {};
    const demand = await prisma.demand.findUnique({ where: { id } });
    if (!demand) return res.status(404).json({ success: false, message: '需求不存在' });
    if (!canTransitionDemand(demand.demandStatus, to)) {
      return res.status(400).json({
        success: false,
        message: `状态转移非法: ${demand.demandStatus} → ${to}`,
        from: demand.demandStatus,
        to,
      });
    }
    const updated = await prisma.demand.update({
      where: { id },
      data: { demandStatus: to, ...(reason ? { /* TODO: 记录状态变更原因 */ } : {}) },
      include: { approvalSteps: { orderBy: { stepIndex: 'asc' } } },
    });
    res.json({ success: true, data: updated });
  } catch (e) { next(e); }
});