/**
 * 招聘流程管理路由
 */

import express from 'express';
import { prisma } from '../app.js';

const router = express.Router();

// 获取所有招聘流程
router.get('/', async (req, res, next) => {
  try {
    const processes = await prisma.recruitmentProcess.findMany({
      include: {
        stages: {
          orderBy: { sortOrder: 'asc' }
        }
      },
      orderBy: { createdAt: 'desc' }
    });

    res.json({
      success: true,
      data: processes.map(p => ({
        ...p,
        stages: p.stages.length
      }))
    });
  } catch (error) {
    next(error);
  }
});

// 获取单个招聘流程
router.get('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;

    const process = await prisma.recruitmentProcess.findUnique({
      where: { id },
      include: {
        stages: {
          orderBy: { sortOrder: 'asc' }
        }
      }
    });

    if (!process) {
      return res.status(404).json({
        success: false,
        message: '流程不存在'
      });
    }

    res.json({
      success: true,
      data: process
    });
  } catch (error) {
    next(error);
  }
});

// 创建招聘流程
router.post('/', async (req, res, next) => {
  try {
    const { name, code, description, applicableRange, stages } = req.body;

    if (!name || !code) {
      return res.status(400).json({
        success: false,
        message: '流程名称和编码不能为空'
      });
    }

    // 检查编码是否重复
    const existing = await prisma.recruitmentProcess.findUnique({
      where: { code }
    });

    if (existing) {
      return res.status(400).json({
        success: false,
        message: '流程编码已存在'
      });
    }

    const process = await prisma.recruitmentProcess.create({
      data: {
        name,
        code,
        description,
        applicableRange: applicableRange || 'ALL',
        stages: stages ? {
          create: stages.map((s, index) => ({
            name: s.name,
            code: s.code,
            stageType: s.stageType || 'GENERAL',
            sortOrder: s.sortOrder || index + 1,
            isDefault: true,
            status: 'ACTIVE'
          }))
        } : undefined
      },
      include: {
        stages: true
      }
    });

    res.status(201).json({
      success: true,
      message: '流程创建成功',
      data: process
    });
  } catch (error) {
    next(error);
  }
});

// 更新招聘流程
router.put('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { name, description, applicableRange, status } = req.body;

    const process = await prisma.recruitmentProcess.update({
      where: { id },
      data: {
        name,
        description,
        applicableRange,
        status
      },
      include: {
        stages: {
          orderBy: { sortOrder: 'asc' }
        }
      }
    });

    res.json({
      success: true,
      message: '流程更新成功',
      data: process
    });
  } catch (error) {
    if (error.code === 'P2025') {
      return res.status(404).json({
        success: false,
        message: '流程不存在'
      });
    }
    next(error);
  }
});

// 删除招聘流程
router.delete('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;

    // 检查是否有职位使用此流程
    const positionCount = await prisma.position.count({
      where: { processId: id }
    });

    if (positionCount > 0) {
      return res.status(400).json({
        success: false,
        message: '有职位正在使用此流程，无法删除'
      });
    }

    // 删除流程（级联删除阶段）
    await prisma.recruitmentProcess.delete({
      where: { id }
    });

    res.json({
      success: true,
      message: '流程删除成功'
    });
  } catch (error) {
    if (error.code === 'P2025') {
      return res.status(404).json({
        success: false,
        message: '流程不存在'
      });
    }
    next(error);
  }
});

// 添加流程阶段
router.post('/:id/stages', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { name, code, stageType, sortOrder } = req.body;

    if (!name || !code) {
      return res.status(400).json({
        success: false,
        message: '阶段名称和编码不能为空'
      });
    }

    const stage = await prisma.recruitmentStage.create({
      data: {
        processId: id,
        name,
        code,
        stageType: stageType || 'GENERAL',
        sortOrder: sortOrder || 0,
        isDefault: true,
        status: 'ACTIVE'
      }
    });

    res.status(201).json({
      success: true,
      message: '阶段添加成功',
      data: stage
    });
  } catch (error) {
    next(error);
  }
});

// 更新流程阶段
router.put('/:id/stages/:stageId', async (req, res, next) => {
  try {
    const { id, stageId } = req.params;
    const { name, stageType, sortOrder, status } = req.body;

    const stage = await prisma.recruitmentStage.update({
      where: { id: stageId },
      data: { name, stageType, sortOrder, status }
    });

    res.json({
      success: true,
      message: '阶段更新成功',
      data: stage
    });
  } catch (error) {
    next(error);
  }
});

// 删除流程阶段
router.delete('/:id/stages/:stageId', async (req, res, next) => {
  try {
    const { stageId } = req.params;

    await prisma.recruitmentStage.delete({
      where: { id: stageId }
    });

    res.json({
      success: true,
      message: '阶段删除成功'
    });
  } catch (error) {
    next(error);
  }
});

export default router;