/**
 * 候选人路由
 */

import express from 'express';
import { prisma } from '../app.js';
import { checkVirtualRole } from '../middleware/auth.middleware.js';
import { fieldAcl } from '../middleware/field-acl.middleware.js';

const router = express.Router();

/**
 * 获取候选人列表
 */
router.get('/', fieldAcl('Candidate'), async (req, res, next) => {
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
router.get('/:id', fieldAcl('Candidate'), async (req, res, next) => {
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

// =====================================
// 批量操作 (PRD G9)
// =====================================

/**
 * 批量推荐候选人到职位
 * POST /api/candidates/batch/recommend
 * body: { candidateIds: string[], positionId: string, comment?: string }
 */
router.post('/batch/recommend', async (req, res, next) => {
  try {
    const { candidateIds, positionId, comment } = req.body || {}
    if (!Array.isArray(candidateIds) || candidateIds.length === 0) {
      return res.status(400).json({ success: false, message: 'candidateIds 必填且非空' })
    }
    if (!positionId) {
      return res.status(400).json({ success: false, message: 'positionId 必填' })
    }

    const position = await prisma.position.findUnique({ where: { id: positionId } })
    if (!position) return res.status(404).json({ success: false, message: '职位不存在' })

    // 事务: 批量创建 Application
    const applications = await prisma.$transaction(
      candidateIds.map((cid) =>
        prisma.application.create({
          data: {
            code: `APP-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            candidateId: cid,
            positionId,
            processId: position.processId || position.processIdDefault,
            processName: position.processName || '',
            applicationStatus: 'ACTIVE',
            source: 'BATCH_RECOMMEND',
          },
        })
      )
    )

    res.json({
      success: true,
      message: `已推荐 ${applications.length} 个候选人`,
      data: { count: applications.length, applications },
    })
  } catch (e) { next(e) }
})

/**
 * 批量归档候选人
 * POST /api/candidates/batch/archive
 * body: { candidateIds: string[], reason?: string, archiveToPool?: boolean }
 */
router.post('/batch/archive', async (req, res, next) => {
  try {
    const { candidateIds, reason, archiveToPool = true } = req.body || {}
    if (!Array.isArray(candidateIds) || candidateIds.length === 0) {
      return res.status(400).json({ success: false, message: 'candidateIds 必填且非空' })
    }

    const result = await prisma.candidate.updateMany({
      where: { id: { in: candidateIds } },
      data: { status: 'ARCHIVED', archiveReason: reason, archivedAt: new Date() },
    })

    res.json({
      success: true,
      message: `已归档 ${result.count} 个候选人`,
      data: { count: result.count, archiveToPool },
    })
  } catch (e) { next(e) }
})

/**
 * 批量分配招聘人
 * POST /api/candidates/batch/assign
 * body: { candidateIds: string[], recruiterId: string }
 */
router.post('/batch/assign', async (req, res, next) => {
  try {
    const { candidateIds, recruiterId } = req.body || {}
    if (!Array.isArray(candidateIds) || candidateIds.length === 0) {
      return res.status(400).json({ success: false, message: 'candidateIds 必填且非空' })
    }
    if (!recruiterId) {
      return res.status(400).json({ success: false, message: 'recruiterId 必填' })
    }

    const result = await prisma.candidate.updateMany({
      where: { id: { in: candidateIds } },
      data: { ownerId: recruiterId, ownerName: req.user?.realName || req.user?.username },
    })

    res.json({
      success: true,
      message: `已分配 ${result.count} 个候选人`,
      data: { count: result.count, recruiterId },
    })
  } catch (e) { next(e) }
})

/**
 * 批量导出候选人 CSV
 * POST /api/candidates/batch/export
 * body: { candidateIds: string[] } 或 { filter: { ... } }
 * 返回 text/csv
 */
router.post('/batch/export', async (req, res, next) => {
  try {
    const { candidateIds, filter = {} } = req.body || {}
    const where = candidateIds && candidateIds.length > 0
      ? { id: { in: candidateIds } }
      : filter

    const candidates = await prisma.candidate.findMany({
      where,
      select: {
        id: true, name: true, phone: true, email: true, gender: true, age: true,
        highestEducation: true, currentCompany: true, currentPosition: true,
        status: true, source: true, createdAt: true,
      },
      orderBy: { createdAt: 'desc' },
    })

    // 生成 CSV
    const headers = ['ID', '姓名', '电话', '邮箱', '性别', '年龄', '学历', '当前公司', '当前职位', '状态', '来源', '创建时间']
    const rows = candidates.map((c) => [
      c.id, c.name, c.phone, c.email, c.gender, c.age, c.highestEducation,
      c.currentCompany, c.currentPosition, c.status, c.source,
      c.createdAt ? new Date(c.createdAt).toISOString() : '',
    ])
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${(cell ?? '').toString().replace(/"/g, '""')}"`).join(','))
      .join('\n')

    res.setHeader('Content-Type', 'text/csv; charset=utf-8')
    res.setHeader('Content-Disposition', `attachment; filename=candidates-${Date.now()}.csv`)
    res.send('﻿' + csv) // BOM 让 Excel 识别 UTF-8
  } catch (e) { next(e) }
})

/**
 * 批量筛选候选人 (PRD G13)
 * POST /api/candidates/batch/screen
 * body: { candidateIds: string[], result: 'PASS' | 'FAIL', comment?: string, positionId?: string }
 * 批量创建筛选记录 + 更新 application 状态
 */
router.post('/batch/screen', async (req, res, next) => {
  try {
    const { candidateIds, result, comment, positionId } = req.body || {}
    if (!Array.isArray(candidateIds) || candidateIds.length === 0) {
      return res.status(400).json({ success: false, message: 'candidateIds 必填且非空' })
    }
    if (!['PASS', 'FAIL'].includes(result)) {
      return res.status(400).json({ success: false, message: 'result 必须是 PASS 或 FAIL' })
    }

    // 批量更新 application 状态 (筛选结论)
    const updateResult = await prisma.application.updateMany({
      where: { candidateId: { in: candidateIds } },
      data: { currentStageStatus: result },
    })

    // 记录操作审计
    const records = await Promise.all(
      candidateIds.map((cid) =>
        prisma.operationRecord.create({
          data: {
            userId: req.userId,
            userName: req.user?.realName || req.user?.username,
            operationType: 'BATCH_SCREEN',
            targetType: 'candidate',
            targetId: cid,
            detail: `批量筛选: ${result} - ${comment || ''}`,
            afterValue: result,
            metadata: { positionId, batchSize: candidateIds.length },
          },
        })
      )
    )

    res.json({
      success: true,
      message: `已批量筛选 ${updateResult.count} 条记录`,
      data: { affected: updateResult.count, auditCount: records.length },
    })
  } catch (e) { next(e) }
})

/**
 * 倒序推荐候选人 (PRD G11)
 * 已在其他职位到联合面试 → 免筛选免邀约
 * POST /api/candidates/recommend-reverse
 * body: { positionId, candidateIds?: string[] }
 * 找出曾在其他 position 经历过当前 position 阶段的候选人, 标记免筛选
 */
router.post('/recommend-reverse', async (req, res, next) => {
  try {
    const { positionId, candidateIds } = req.body || {}
    if (!positionId) return res.status(400).json({ success: false, message: 'positionId 必填' })

    // 找出当前 position 的 processId
    const position = await prisma.position.findUnique({
      where: { id: positionId },
      select: { processId: true, name: true },
    })
    if (!position) return res.status(404).json({ success: false, message: '职位不存在' })

    // 找出所有 candidates 中, 曾在同 process 任何阶段 ALL_PASS 的 (联合面试通过)
    const passedApplications = await prisma.application.findMany({
      where: {
        ...(candidateIds ? { candidateId: { in: candidateIds } } : {}),
        processId: position.processId,
        currentStageStatus: { in: ['ALL_PASS', 'PARTIAL_PASS'] },
      },
      include: {
        candidate: { select: { id: true, name: true } },
        position: { select: { id: true, name: true } },
      },
      orderBy: { updatedAt: 'desc' },
    })

    // 去重 (同一候选人在多个 position 通过, 只取最近)
    const seen = new Set()
    const result = []
    for (const app of passedApplications) {
      if (seen.has(app.candidateId)) continue
      seen.add(app.candidateId)
      result.push({
        candidateId: app.candidateId,
        candidateName: app.candidate.name,
        fromPositionId: app.positionId,
        fromPositionName: app.position.name,
        passedAt: app.updatedAt,
        canSkipFilter: true,
        canSkipInvite: true, // PRD G11 含义
      })
    }

    res.json({
      success: true,
      data: {
        positionId,
        total: result.length,
        candidates: result,
        note: candidateIds
          ? '已限定候选范围, 仅显示该范围中已通过其他职位的'
          : '全量倒序推荐',
      },
    })
  } catch (e) { next(e) }
})

export default router;
