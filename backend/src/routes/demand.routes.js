/**
 * 招聘需求管理路由
 */

import express from 'express';
import { prisma } from '../app.js';

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

// 提交需求审批
router.post('/:id/submit', async (req, res, next) => {
  try {
    const { id } = req.params;

    const demand = await prisma.demand.update({
      where: { id },
      data: {
        demandStatus: 'IN_PROGRESS',
        approvalStatus: 'PENDING'
      }
    });

    res.json({
      success: true,
      message: '需求已提交审批',
      data: demand
    });
  } catch (error) {
    next(error);
  }
});

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