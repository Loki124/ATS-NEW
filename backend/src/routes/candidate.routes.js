/**
 * 候选人路由
 */

import express from 'express';
import { prisma } from '../app.js';
import { checkVirtualRole } from '../middleware/auth.middleware.js';

const router = express.Router();

/**
 * 获取候选人列表
 */
router.get('/', async (req, res, next) => {
  try {
    const {
      page = 1,
      pageSize = 20,
      keyword,
      status,
      archiveType,
      gender,
      highestEducation,
      channelSource,
      departmentId,
      positionId,
      startDate,
      endDate
    } = req.query;

    const where = {};
    
    // 关键词搜索
    if (keyword) {
      where.OR = [
        { name: { contains: keyword, mode: 'insensitive' } },
        { phone: { contains: keyword, mode: 'insensitive' } },
        { email: { contains: keyword, mode: 'insensitive' } }
      ];
    }
    
    // 状态筛选
    if (status) {
      where.candidateStatus = status;
    }
    
    // 归档类型
    if (archiveType) {
      where.archiveType = archiveType;
    }
    
    // 性别
    if (gender) {
      where.gender = gender;
    }
    
    // 最高学历
    if (highestEducation) {
      where.highestEducation = highestEducation;
    }
    
    // 渠道来源
    if (channelSource) {
      where.channelSource = channelSource;
    }

    // 数据权限过滤
    const user = req.user;
    if (user.roleType !== 'SUPER_ADMIN' && user.roleType !== 'ADMIN') {
      // 非管理员只能看到自己负责的候选人
      where.assignedUserId = user.id;
    }

    const [candidates, total] = await Promise.all([
      prisma.candidate.findMany({
        where,
        include: {
          assignedUser: {
            select: { id: true, realName: true }
          },
          resumes: {
            take: 1,
            orderBy: { createdAt: 'desc' }
          },
          applications: {
            where: { applicationStatus: 'ACTIVE' },
            include: {
              position: {
                select: { id: true, name: true, code: true }
              },
              currentStage: true
            }
          }
        },
        orderBy: { createdAt: 'desc' },
        skip: (Number(page) - 1) * Number(pageSize),
        take: Number(pageSize)
      }),
      prisma.candidate.count({ where })
    ]);

    res.json({
      success: true,
      data: {
        list: candidates,
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

/**
 * 获取候选人详情
 */
router.get('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;

    const candidate = await prisma.candidate.findUnique({
      where: { id },
      include: {
        assignedUser: {
          select: { id: true, realName: true }
        },
        resumes: true,
        applications: {
          include: {
            position: {
              select: { 
                id: true, 
                name: true, 
                code: true,
                department: true,
                manager: { select: { id: true, realName: true } }
              }
            },
            stageRecords: {
              orderBy: { enterTime: 'desc' }
            },
            interviews: {
              include: {
                feedbacks: true
              }
            },
            offer: true,
            onboarding: true
          }
        },
        remarks: {
          include: {
            user: { select: { id: true, realName: true } }
          },
          orderBy: { createdAt: 'desc' }
        }
      }
    });

    if (!candidate) {
      return res.status(404).json({
        success: false,
        message: '候选人不存在'
      });
    }

    res.json({
      success: true,
      data: candidate
    });
  } catch (error) {
    next(error);
  }
});

/**
 * 创建候选人
 */
router.post('/', async (req, res, next) => {
  try {
    const {
      name,
      gender,
      birthday,
      phone,
      email,
      householdLocation,
      originLocation,
      maritalStatus,
      highestEducation,
      firstEducation,
      workExperience,
      channelSource,
      channelLink,
      recommenderId,
      recommenderName
    } = req.body;

    // 生成候选人编号
    const count = await prisma.candidate.count();
    const code = `C${String(count + 1).padStart(8, '0')}`;

    const candidate = await prisma.candidate.create({
      data: {
        code,
        name,
        gender,
        birthday: birthday ? new Date(birthday) : null,
        phone,
        email,
        householdLocation,
        originLocation,
        maritalStatus,
        highestEducation,
        firstEducation,
        workExperience: workExperience ? JSON.parse(JSON.stringify(workExperience)) : null,
        channelSource,
        channelLink,
        recommenderId,
        recommenderName,
        // 设置分配人和简历提供人
        assignedUserId: req.userId
      },
      include: {
        assignedUser: { select: { id: true, realName: true } }
      }
    });

    // 候选人已创建，分配人已设置
    res.status(201).json({
      success: true,
      message: '候选人创建成功',
      data: candidate
    });
  } catch (error) {
    next(error);
  }
});

/**
 * 更新候选人
 */
router.put('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const updateData = req.body;

    // 删除不可更新的字段
    delete updateData.id;
    delete updateData.code;
    delete updateData.createdAt;

    // 处理日期字段
    if (updateData.birthday) {
      updateData.birthday = new Date(updateData.birthday);
    }

    const candidate = await prisma.candidate.update({
      where: { id },
      data: updateData
    });

    res.json({
      success: true,
      message: '候选人更新成功',
      data: candidate
    });
  } catch (error) {
    next(error);
  }
});

/**
 * 归档候选人
 */
router.post('/:id/archive', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { archiveType, archiveReason } = req.body;

    if (!archiveType || !archiveReason) {
      return res.status(400).json({
        success: false,
        message: '归档类型和归档原因不能为空'
      });
    }

    // 更新候选人状态
    const candidate = await prisma.candidate.update({
      where: { id },
      data: {
        candidateStatus: 'ARCHIVED',
        archiveType,
        archiveReason,
        archiveToPool: archiveType
      }
    });

    // 同时归档所有活跃的应聘记录
    await prisma.application.updateMany({
      where: {
        candidateId: id,
        applicationStatus: 'ACTIVE'
      },
      data: {
        applicationStatus: 'ARCHIVED',
        archivedAt: new Date()
      }
    });

    res.json({
      success: true,
      message: '候选人已归档',
      data: candidate
    });
  } catch (error) {
    next(error);
  }
});

/**
 * 恢复候选人（从人才库重新分配）
 */
router.post('/:id/restore', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { positionId } = req.body;

    if (!positionId) {
      return res.status(400).json({
        success: false,
        message: '请选择要分配的职位'
      });
    }

    // 获取职位信息
    const position = await prisma.position.findUnique({
      where: { id: positionId },
      include: {
        process: {
          include: {
            stages: {
              orderBy: { sortOrder: 'asc' }
            }
          }
        }
      }
    });

    if (!position) {
      return res.status(404).json({
        success: false,
        message: '职位不存在'
      });
    }

    if (position.positionStatus !== 'RECRUITING') {
      return res.status(400).json({
        success: false,
        message: '该职位已停止招聘'
      });
    }

    // 获取候选人
    const candidate = await prisma.candidate.findUnique({
      where: { id }
    });

    if (!candidate) {
      return res.status(404).json({
        success: false,
        message: '候选人不存在'
      });
    }

    // 创建新的应聘记录
    const firstStage = position.process.stages[0];
    const applicationCount = await prisma.application.count();
    const applicationCode = `A${String(applicationCount + 1).padStart(8, '0')}`;

    const application = await prisma.application.create({
      data: {
        code: applicationCode,
        candidateId: id,
        positionId,
        processId: position.processId,
        processName: position.process.name,
        currentStageId: firstStage?.id,
        currentStageName: firstStage?.name,
        applicationStatus: 'ACTIVE'
      }
    });

    // 更新候选人状态
    await prisma.candidate.update({
      where: { id },
      data: {
        candidateStatus: 'ACTIVE',
        archiveType: null,
        archiveReason: null,
        archiveToPool: null
      }
    });

    // 创建阶段记录
    if (firstStage) {
      await prisma.applicationStageRecord.create({
        data: {
          applicationId: application.id,
          stageId: firstStage.id,
          stageName: firstStage.name,
          stageType: firstStage.stageType,
          stageStatus: 'IN_PROGRESS'
        }
      });
    }

    res.json({
      success: true,
      message: '候选人已恢复并分配职位',
      data: {
        candidate,
        application
      }
    });
  } catch (error) {
    next(error);
  }
});

/**
 * 添加候选人备注
 */
router.post('/:id/remarks', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { content, mentionedUsers } = req.body;

    if (!content) {
      return res.status(400).json({
        success: false,
        message: '备注内容不能为空'
      });
    }

    const remark = await prisma.candidateRemark.create({
      data: {
        candidateId: id,
        userId: req.userId,
        userName: req.user.realName,
        content
      }
    });

    res.status(201).json({
      success: true,
      message: '备注添加成功',
      data: remark
    });
  } catch (error) {
    next(error);
  }
});

/**
 * 删除候选人（仅超管）
 */
router.delete('/:id', async (req, res, next) => {
  try {
    if (req.user.roleType !== 'SUPER_ADMIN') {
      return res.status(403).json({
        success: false,
        message: '仅超级管理员可删除候选人'
      });
    }

    const { id } = req.params;

    await prisma.candidate.delete({
      where: { id }
    });

    res.json({
      success: true,
      message: '候选人已删除'
    });
  } catch (error) {
    next(error);
  }
});

export default router;
