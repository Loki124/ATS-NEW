/**
 * 简历管理路由 - V2.0增强版
 * 双轨锁定人、异步评分、特殊审批流程
 */

import express from 'express';
import { PrismaClient } from '@prisma/client';

const router = express.Router();
const prisma = new PrismaClient();

// ==================== 锁定人相关 ====================

/**
 * 获取简历的当前锁定人信息
 */
router.get('/resume/:resumeId/lock-info', async (req, res, next) => {
  try {
    const { resumeId } = req.params;

    const resume = await prisma.resume.findUnique({
      where: { id: resumeId },
      select: {
        formalLockerId: true,
        tempLockerId: true,
        tempLockerExpireTime: true,
        resumeStatus: true,
        resumeSubStatus: true
      }
    });

    if (!resume) {
      return res.status(404).json({ success: false, message: '简历不存在' });
    }

    // 获取锁定人信息
    let formalLocker = null;
    let tempLocker = null;

    if (resume.formalLockerId) {
      formalLocker = await prisma.user.findUnique({
        where: { id: resume.formalLockerId },
        select: { id: true, realName: true }
      });
    }

    if (resume.tempLockerId && resume.tempLockerExpireTime) {
      const now = new Date();
      if (resume.tempLockerExpireTime > now) {
        tempLocker = await prisma.user.findUnique({
          where: { id: resume.tempLockerId },
          select: { id: true, realName: true }
        });
      }
    }

    res.json({
      success: true,
      data: {
        formalLocker,
        tempLocker,
        tempLockerExpireTime: resume.tempLockerExpireTime,
        resumeStatus: resume.resumeStatus,
        resumeSubStatus: resume.resumeSubStatus
      }
    });
  } catch (error) {
    next(error);
  }
});

/**
 * 校验用户是否为锁定人或有权限操作
 */
router.post('/resume/:resumeId/check-lock-permission', async (req, res, next) => {
  try {
    const { resumeId } = req.params;
    const { userId } = req.body;

    const resume = await prisma.resume.findUnique({
      where: { id: resumeId },
      select: {
        formalLockerId: true,
        tempLockerId: true,
        tempLockerExpireTime: true,
        providerId: true,
        uploaderId: true
      }
    });

    if (!resume) {
      return res.status(404).json({ success: false, message: '简历不存在' });
    }

    // 检查是否为正式锁定人
    if (resume.formalLockerId === userId) {
      return res.json({ success: true, data: { hasPermission: true, lockType: 'FORMAL' } });
    }

    // 检查是否为临时锁定人（且未过期）
    if (resume.tempLockerId === userId && resume.tempLockerExpireTime > new Date()) {
      return res.json({ success: true, data: { hasPermission: true, lockType: 'TEMPORARY', expireTime: resume.tempLockerExpireTime } });
    }

    // 获取锁定人姓名用于提示
    let lockerName = '未知';
    if (resume.formalLockerId) {
      const locker = await prisma.user.findUnique({ where: { id: resume.formalLockerId }, select: { realName: true } });
      lockerName = locker?.realName || lockerName;
    }

    res.json({
      success: true,
      data: {
        hasPermission: false,
        lockType: resume.formalLockerId ? 'FORMAL' : 'NONE',
        lockerName
      }
    });
  } catch (error) {
    next(error);
  }
});

// ==================== 异步评分任务 ====================

/**
 * 创建异步评分任务
 */
router.post('/resume/:resumeId/scoring-tasks', async (req, res, next) => {
  try {
    const { resumeId } = req.params;
    const { positionId } = req.body;

    // 创建评分任务
    const task = await prisma.asyncScoringTask.create({
      data: {
        resumeId,
        positionId,
        status: 'PENDING'
      }
    });

    // 更新简历子状态
    await prisma.resume.update({
      where: { id: resumeId },
      data: { resumeSubStatus: 'SCORING' }
    });

    // TODO: 实际场景中，这里应该将任务加入异步队列进行处理
    // 此处模拟异步处理，设置延迟后更新结果
    setTimeout(async () => {
      try {
        // 模拟评分结果（实际应调用AI评分服务）
        const mockScore = Math.floor(Math.random() * 40) + 60; // 60-100分
        const passed = mockScore >= 70;

        await prisma.asyncScoringTask.update({
          where: { id: task.id },
          data: {
            status: 'COMPLETED',
            matchScore: mockScore,
            matchDetails: JSON.stringify({ score: mockScore, passed }),
            completedAt: new Date()
          }
        });

        // 更新简历状态
        await prisma.resume.update({
          where: { id: resumeId },
          data: {
            resumeSubStatus: null,
            matchScore: mockScore
          }
        });
      } catch (e) {
        console.error('评分任务处理失败', e);
      }
    }, 3000);

    res.status(201).json({ success: true, data: task });
  } catch (error) {
    next(error);
  }
});

/**
 * 获取评分任务状态
 */
router.get('/scoring-tasks/:taskId', async (req, res, next) => {
  try {
    const { taskId } = req.params;

    const task = await prisma.asyncScoringTask.findUnique({
      where: { id: taskId }
    });

    res.json({ success: true, data: task });
  } catch (error) {
    next(error);
  }
});

// ==================== 特殊审批流程 ====================

/**
 * 创建特殊审批流程
 */
router.post('/resume/:resumeId/approval-flow', async (req, res, next) => {
  try {
    const { resumeId } = req.params;
    const { positionId, approvers } = req.body;

    // 更新简历子状态
    await prisma.resume.update({
      where: { id: resumeId },
      data: { resumeSubStatus: 'APPROVAL' }
    });

    const flow = await prisma.specialApprovalFlow.create({
      data: {
        resumeId,
        positionId,
        flowType: 'SPECIAL_RESUME',
        status: 'PENDING',
        nodes: JSON.stringify(approvers || []),
        currentNodeId: approvers?.[0]?.nodeId || null
      }
    });

    res.status(201).json({ success: true, data: flow });
  } catch (error) {
    next(error);
  }
});

/**
 * 获取特殊审批流程状态
 */
router.get('/resume/:resumeId/approval-flow', async (req, res, next) => {
  try {
    const { resumeId } = req.params;

    const flow = await prisma.specialApprovalFlow.findFirst({
      where: { resumeId },
      orderBy: { createdAt: 'desc' }
    });

    res.json({ success: true, data: flow });
  } catch (error) {
    next(error);
  }
});

/**
 * 获取所有特殊审批流程列表
 */
router.get('/approval-flows', async (req, res, next) => {
  try {
    const { status } = req.query;
    const where = {};
    if (status) where.status = status;

    const flows = await prisma.specialApprovalFlow.findMany({
      where,
      include: {
        resume: {
          include: { candidate: true }
        }
      },
      orderBy: { createdAt: 'desc' }
    });

    res.json({ success: true, data: flows });
  } catch (error) {
    next(error);
  }
});

/**
 * 审批操作（通过/驳回）
 */
router.post('/approval-flows/:flowId/approve', async (req, res, next) => {
  try {
    const { flowId } = req.params;
    const { action, comment } = req.body; // action: APPROVED, REJECTED
    const approverId = req.userId; // IDOR fix: 服务端取, 不从 body 信任

    const flow = await prisma.specialApprovalFlow.findUnique({
      where: { id: flowId }
    });

    if (!flow) {
      return res.status(404).json({ success: false, message: '审批流程不存在' });
    }

    if (flow.status !== 'PENDING') {
      return res.status(400).json({ success: false, message: '审批流程已结束' });
    }

    const nodes = JSON.parse(flow.nodes || '[]');
    const currentNode = nodes.find(n => n.nodeId === flow.currentNodeId);

    // 鉴权: 当前节点必须指定 approverId,且必须匹配当前用户
    if (currentNode?.expectedApproverId && currentNode.expectedApproverId !== approverId) {
      return res.status(403).json({ success: false, message: '您不是当前步骤的审批人' });
    }

    // 更新当前节点审批信息
    if (currentNode) {
      currentNode.status = action;
      currentNode.comment = comment;
      currentNode.approverId = approverId;
      currentNode.decidedAt = new Date().toISOString();
    }

    // 更新流程状态
    let newStatus = flow.status;
    let newCurrentNodeId = flow.currentNodeId;
    let nextNode = null;

    if (action === 'APPROVED') {
      const currentIndex = nodes.findIndex(n => n.nodeId === flow.currentNodeId);
      if (currentIndex < nodes.length - 1) {
        // 还有下一节点
        nextNode = nodes[currentIndex + 1];
        newCurrentNodeId = nextNode.nodeId;
      } else {
        // 审批通过
        newStatus = 'APPROVED';
      }
    } else if (action === 'REJECTED') {
      newStatus = 'REJECTED';
    }

    await prisma.specialApprovalFlow.update({
      where: { id: flowId },
      data: {
        status: newStatus,
        currentNodeId: newCurrentNodeId,
        nodes: JSON.stringify(nodes),
        result: action === 'APPROVED' ? '通过' : '驳回',
        resultComment: comment,
        decidedAt: newStatus !== 'PENDING' ? new Date() : null
      }
    });

    // 如果审批完成，更新简历状态并打标签
    if (newStatus === 'APPROVED') {
      await prisma.resume.update({
        where: { id: flow.resumeId },
        data: {
          resumeStatus: 'ASSIGNED',
          resumeSubStatus: null
        }
      });

      // 添加特殊标签
      await prisma.specialResumeTag.create({
        data: {
          resumeId: flow.resumeId,
          positionId: flow.positionId,
          approvalId: flowId
        }
      });
    } else if (newStatus === 'REJECTED') {
      // 驳回，回归待分配
      await prisma.resume.update({
        where: { id: flow.resumeId },
        data: {
          resumeSubStatus: null
        }
      });
    }

    res.json({
      success: true,
      data: {
        status: newStatus,
        nextNode: nextNode || null
      }
    });
  } catch (error) {
    next(error);
  }
});

// ==================== 简历流转日志 ====================

/**
 * 记录简历流转日志
 */
async function addResumeFlowLog(resumeId, candidateId, action, operatorId, operatorName, fromStatus, toStatus, positionId, positionName, detail) {
  await prisma.resumeFlowLog.create({
    data: {
      resumeId,
      candidateId,
      action,
      operatorId,
      operatorName,
      fromStatus,
      toStatus,
      positionId,
      positionName,
      detail: detail ? JSON.stringify(detail) : null
    }
  });
}

/**
 * 获取简历流转日志
 */
router.get('/resume/:resumeId/flow-logs', async (req, res, next) => {
  try {
    const { resumeId } = req.params;

    const logs = await prisma.resumeFlowLog.findMany({
      where: { resumeId },
      orderBy: { createdAt: 'desc' }
    });

    res.json({ success: true, data: logs });
  } catch (error) {
    next(error);
  }
});

// ==================== 简历分配（核心操作） ====================

/**
 * 分配简历到职位
 */
router.post('/resume/:resumeId/assign', async (req, res, next) => {
  try {
    const { resumeId } = req.params;
    const { positionId, skipScoring } = req.body;
    const operatorId = req.userId; // IDOR fix

    const resume = await prisma.resume.findUnique({
      where: { id: resumeId },
      include: { candidate: true }
    });

    if (!resume) {
      return res.status(404).json({ success: false, message: '简历不存在' });
    }

    // 检查锁定权限
    const now = new Date();
    const isFormalLocker = resume.formalLockerId === operatorId;
    const isTempLocker = resume.tempLockerId === operatorId && resume.tempLockerExpireTime > now;

    if (!isFormalLocker && !isTempLocker) {
      return res.status(403).json({
        success: false,
        message: '您不是该简历的当前锁定人，无法执行此操作'
      });
    }

    // 检查简历状态
    if (resume.resumeStatus === 'ASSIGNED') {
      return res.status(400).json({ success: false, message: '简历已分配' });
    }

    if (resume.resumeStatus === 'DELETED') {
      return res.status(400).json({ success: false, message: '简历已删除' });
    }

    const position = await prisma.position.findUnique({
      where: { id: positionId },
      include: { department: true }
    });

    if (!position) {
      return res.status(404).json({ success: false, message: '职位不存在' });
    }

    // 检查是否需要异步评分
    if (!skipScoring && resume.resumeSubStatus !== 'SCORING') {
      // 触发异步评分
      const scoringTask = await prisma.asyncScoringTask.create({
        data: {
          resumeId,
          positionId,
          status: 'PENDING'
        }
      });

      await prisma.resume.update({
        where: { id: resumeId },
        data: { resumeSubStatus: 'SCORING' }
      });

      // 记录日志
      await addResumeFlowLog(
        resumeId,
        resume.candidateId,
        'SCORE',
        operatorId,
        null,
        resume.resumeStatus,
        null,
        positionId,
        position.name,
        { taskId: scoringTask.id, action: '异步评分启动' }
      );

      return res.json({
        success: true,
        data: {
          needScoring: true,
          taskId: scoringTask.id,
          message: '简历正在异步评分中，预计3分钟内完成'
        }
      });
    }

    // 更新简历状态
    const previousStatus = resume.resumeStatus;
    await prisma.resume.update({
      where: { id: resumeId },
      data: {
        resumeStatus: 'ASSIGNED',
        resumeSubStatus: null,
        positionId,
        formalLockerId: operatorId // 分配人成为正式锁定人
      }
    });

    // 记录锁定历史
    await prisma.resumeLockRecord.create({
      data: {
        resumeId,
        lockerId: operatorId,
        lockType: 'FORMAL',
        source: 'ASSIGN',
        isActive: true
      }
    });

    // 记录日志
    await addResumeFlowLog(
      resumeId,
      resume.candidateId,
      'ASSIGN',
      operatorId,
      null,
      previousStatus,
      'ASSIGNED',
      positionId,
      position.name,
      { assignerId: operatorId }
    );

    res.json({
      success: true,
      data: {
        resumeStatus: 'ASSIGNED',
        positionId
      }
    });
  } catch (error) {
    next(error);
  }
});

// ==================== 简历归档与激活 ====================

/**
 * 归档简历到人才库
 */
router.post('/resume/:resumeId/archive', async (req, res, next) => {
  try {
    const { resumeId } = req.params;
    const { archiveType, archiveToPool } = req.body;
    const operatorId = req.userId; // IDOR fix

    const resume = await prisma.resume.findUnique({
      where: { id: resumeId }
    });

    if (!resume) {
      return res.status(404).json({ success: false, message: '简历不存在' });
    }

    // 更新状态
    await prisma.resume.update({
      where: { id: resumeId },
      data: {
        resumeStatus: 'ARCHIVED',
        archiveType,
        archiveToPool
      }
    });

    // 记录日志
    await addResumeFlowLog(
      resumeId,
      resume.candidateId,
      'ARCHIVE',
      operatorId,
      null,
      resume.resumeStatus,
      'ARCHIVED',
      null,
      null,
      { archiveType, archiveToPool }
    );

    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});

/**
 * 从人才库激活简历
 */
router.post('/resume/:resumeId/activate', async (req, res, next) => {
  try {
    const { resumeId } = req.params;
    const operatorId = req.userId; // IDOR fix

    const resume = await prisma.resume.findUnique({
      where: { id: resumeId }
    });

    if (!resume) {
      return res.status(404).json({ success: false, message: '简历不存在' });
    }

    const now = new Date();
    const hoursLater = new Date(now.getTime() + 72 * 60 * 60 * 1000);

    // 确定锁定人
    let formalLockerId = null;
    let tempLockerId = null;
    let tempLockerExpireTime = null;

    // 规则：激活人≠提供人时，激活人获得临时锁定
    if (resume.providerId && resume.providerId !== operatorId) {
      tempLockerId = operatorId;
      tempLockerExpireTime = hoursLater;
    } else {
      formalLockerId = operatorId;
    }

    // 更新简历状态
    await prisma.resume.update({
      where: { id: resumeId },
      data: {
        resumeStatus: 'PENDING_ASSIGN',
        resumeSubStatus: null,
        formalLockerId,
        tempLockerId,
        tempLockerExpireTime,
        archiveType: null,
        archiveToPool: null
      }
    });

    // 记录锁定历史
    await prisma.resumeLockRecord.create({
      data: {
        resumeId,
        lockerId: formalLockerId || tempLockerId,
        lockType: formalLockerId ? 'FORMAL' : 'TEMPORARY',
        expireTime: tempLockerExpireTime,
        source: 'ACTIVATE',
        isActive: true
      }
    });

    // 记录日志
    await addResumeFlowLog(
      resumeId,
      resume.candidateId,
      'ACTIVATE',
      operatorId,
      null,
      'ARCHIVED',
      'PENDING_ASSIGN',
      null,
      null,
      { activatedBy: operatorId }
    );

    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});

// ==================== 简历合并 ====================

/**
 * 合并重复简历
 */
router.post('/resume-merge', async (req, res, next) => {
  try {
    const { mainResumeId, mergedResumeId, mergeType, reason } = req.body;
    const operatorId = req.userId; // IDOR fix

    const mainResume = await prisma.resume.findUnique({ where: { id: mainResumeId } });
    const mergedResume = await prisma.resume.findUnique({ where: { id: mergedResumeId } });

    if (!mainResume || !mergedResume) {
      return res.status(404).json({ success: false, message: '简历不存在' });
    }

    // 创建合并记录
    await prisma.resumeMergeRecord.create({
      data: {
        mainResumeId,
        mergedResumeId,
        mergeType: mergeType || 'MANUAL',
        operatorId,
        mergeReason: reason
      }
    });

    // 更新被合并简历状态
    await prisma.resume.update({
      where: { id: mergedResumeId },
      data: {
        resumeStatus: 'DELETED',
        duplicateOfId: mainResumeId
      }
    });

    // 记录日志
    await addResumeFlowLog(
      mergedResumeId,
      mergedResume.candidateId,
      'MERGE',
      operatorId,
      null,
      mergedResume.resumeStatus,
      'DELETED',
      null,
      null,
      { mergedTo: mainResumeId, reason }
    );

    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});

// ==================== 简历列表（按状态筛选） ====================

/**
 * 获取简历列表（支持状态筛选）
 * GET /api/resumes?status=PENDING_ASSIGN&subStatus=SCORING
 */
router.get('/', async (req, res, next) => {
  try {
    const { status, subStatus, page = 1, pageSize = 20 } = req.query;

    const where = {};
    if (status) where.resumeStatus = status;
    if (subStatus) where.resumeSubStatus = subStatus;

    const [resumes, total] = await Promise.all([
      prisma.resume.findMany({
        where,
        include: {
          candidate: true,
          lockRecords: {
            where: { isActive: true },
            include: { locker: { select: { id: true, realName: true } } }
          }
        },
        skip: (Number(page) - 1) * Number(pageSize),
        take: Number(pageSize),
        orderBy: { createdAt: 'desc' }
      }),
      prisma.resume.count({ where })
    ]);

    res.json({
      success: true,
      data: {
        list: resumes,
        total,
        page: Number(page),
        pageSize: Number(pageSize)
      }
    });
  } catch (error) {
    next(error);
  }
});

export default router;