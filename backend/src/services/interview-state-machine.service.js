/**
 * 面试状态机 - PRD G3.6
 *
 * 阶段状态枚举（PRD #5.2 面试型阶段）：
 *   NOT_ARRANGED   - 未安排：当前阶段无任何面试
 *   PENDING_FEEDBACK - 待反馈：有面试已过时间但未全部提交反馈
 *   ALL_PASS       - 全部通过：全部反馈已提交且全部 PASS
 *   PARTIAL_PASS   - 部分通过：全部反馈已提交，至少一个 PASS
 *   ALL_FAIL       - 全部不通过：全部反馈已提交但都 FAIL
 *
 * 进入下一阶段的条件：ALL_PASS 或 PARTIAL_PASS
 *
 * 数据来源：
 *   - Interview.feedbackStatus (PENDING/COMPLETED)
 *   - InterviewFeedback.result (PASS/FAIL)
 *
 * 触发动机：面试反馈提交 (POST /api/interviews/:id/feedback) 后调用
 *           refreshApplicationStageStatus(applicationId) 重新计算并写回
 */

import { prisma } from '../app.js'

export const INTERVIEW_STAGE_STATUS = {
  NOT_ARRANGED: 'NOT_ARRANGED',
  PENDING_FEEDBACK: 'PENDING_FEEDBACK',
  ALL_PASS: 'ALL_PASS',
  PARTIAL_PASS: 'PARTIAL_PASS',
  ALL_FAIL: 'ALL_FAIL',
}

// 状态机转换图
const INTERVIEW_TRANSITIONS = {
  NOT_ARRANGED: ['PENDING_FEEDBACK', 'ALL_PASS', 'PARTIAL_PASS', 'ALL_FAIL'],
  PENDING_FEEDBACK: ['ALL_PASS', 'PARTIAL_PASS', 'ALL_FAIL'],
  ALL_PASS: ['PENDING_FEEDBACK'], // 重新安排面试可回退
  PARTIAL_PASS: ['PENDING_FEEDBACK'],
  ALL_FAIL: ['PENDING_FEEDBACK'],
}

export function canTransitionInterview(from, to) {
  return (INTERVIEW_TRANSITIONS[from] || []).includes(to)
}

/**
 * 计算候选人面试阶段的聚合状态
 * @param {string} applicationId
 * @returns {Promise<string>} 聚合状态
 */
export async function computeInterviewStageStatus(applicationId) {
  const application = await prisma.application.findUnique({
    where: { id: applicationId },
    include: {
      interviews: {
        select: {
          id: true,
          feedbackStatus: true,
          interviewDate: true,
          feedbacks: { select: { result: true } },
        },
      },
    },
  })
  if (!application) return INTERVIEW_STAGE_STATUS.NOT_ARRANGED

  const interviews = application.interviews || []

  // 无任何面试 → 未安排
  if (interviews.length === 0) {
    return INTERVIEW_STAGE_STATUS.NOT_ARRANGED
  }

  const now = new Date()
  const finished = interviews.filter((i) => i.interviewDate < now)
  const completed = interviews.filter((i) => i.feedbackStatus === 'COMPLETED')

  // 有面试但都没到时间 → NOT_ARRANGED
  if (finished.length === 0) {
    return INTERVIEW_STAGE_STATUS.NOT_ARRANGED
  }

  // 有面试已过时间但未全部反馈 → PENDING_FEEDBACK
  if (completed.length < finished.length) {
    return INTERVIEW_STAGE_STATUS.PENDING_FEEDBACK
  }

  // 全部已反馈 → 计算通过/不通过
  // 收集所有 PASS 反馈数 (一个面试可能有多个面试官各提交一份)
  let passCount = 0
  let totalFeedbackCount = 0
  for (const interview of completed) {
    for (const fb of interview.feedbacks || []) {
      totalFeedbackCount++
      if (fb.result === 'PASS') passCount++
    }
  }
  if (totalFeedbackCount === 0) return INTERVIEW_STAGE_STATUS.PENDING_FEEDBACK
  if (passCount === totalFeedbackCount) return INTERVIEW_STAGE_STATUS.ALL_PASS
  if (passCount === 0) return INTERVIEW_STAGE_STATUS.ALL_FAIL
  return INTERVIEW_STAGE_STATUS.PARTIAL_PASS
}

/**
 * 重新计算并更新 application.currentStageStatus
 * 当有面试反馈变化时调用
 */
export async function refreshApplicationStageStatus(applicationId) {
  const newStatus = await computeInterviewStageStatus(applicationId)
  await prisma.application.update({
    where: { id: applicationId },
    data: { currentStageStatus: newStatus },
  })
  return newStatus
}

/**
 * 检查是否可以进入下一阶段
 * 全部通过 OR 部分通过
 */
export function canAdvanceToNext(stageStatus) {
  return stageStatus === INTERVIEW_STAGE_STATUS.ALL_PASS ||
         stageStatus === INTERVIEW_STAGE_STATUS.PARTIAL_PASS
}

export default {
  INTERVIEW_STAGE_STATUS,
  canTransitionInterview,
  computeInterviewStageStatus,
  refreshApplicationStageStatus,
  canAdvanceToNext,
}
