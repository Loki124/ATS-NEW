/**
 * 通知服务 - PRD B.2 (占位)
 *
 * 暂不接企微/邮件/IM(Phase 3)
 * 当前: 写入 NotificationQueue 表 + 控制台日志,后续可由 cron 拉表发送
 *
 * 用法:
 *   await sendNotification({
 *     recipientId: 'user-xxx',
 *     templateKey: 'DEMAND_APPROVAL_PENDING',
 *     context: { demandId, demandName, approverRole, submitterName }
 *   })
 */

import { prisma } from '../app.js'

// 模板定义 (内联,Phase 3 可抽 NotificationTemplate 表)
const TEMPLATES = {
  DEMAND_APPROVAL_PENDING: {
    title: '【审批待办】需求 {demandName}',
    content: '{submitterName} 提交了需求「{demandName}」等待您审批',
  },
  DEMAND_APPROVAL_APPROVED: {
    title: '【审批通过】需求 {demandName}',
    content: '需求「{demandName}」已通过全部审批,可开始执行',
  },
  DEMAND_APPROVAL_REJECTED: {
    title: '【审批拒绝】需求 {demandName}',
    content: '需求「{demandName}」被拒绝,原因: {reason}',
  },
  DEMAND_APPROVAL_CANCELLED: {
    title: '【审批撤销】需求 {demandName}',
    content: '需求「{demandName}」的审批已被创建人撤销',
  },
  DEMAND_APPROVAL_STEP_APPROVED: {
    title: '【审批进展】需求 {demandName}',
    content: '需求「{demandName}」第 {stepIndex} 步({approverRole})已通过,共 {totalSteps} 步',
  },
  INTERVIEW_FEEDBACK_REQUEST: {
    title: '【面试反馈】候选人 {candidateName}',
    content: '请在 {interviewDate} 前提交对候选人「{candidateName}」的面试反馈',
  },
}

/**
 * 渲染模板（简单变量替换）
 */
function renderTemplate(template, context) {
  let result = template
  for (const [key, value] of Object.entries(context || {})) {
    result = result.replace(new RegExp(`\\{${key}\\}`, 'g'), value ?? '')
  }
  return result
}

/**
 * 发送通知
 *  - 写入 NotificationQueue 表(cron 后续拉表实际发送)
 *  - 控制台日志(开发/调试可见)
 */
export async function sendNotification({
  recipientId,
  templateKey,
  context = {},
  priority = 'NORMAL', // LOW / NORMAL / HIGH
  tx = null,
}) {
  if (!recipientId) throw new Error('recipientId 必填')
  const tpl = TEMPLATES[templateKey]
  if (!tpl) {
    console.warn(`[notification] 未知模板: ${templateKey}`)
    return null
  }
  const title = renderTemplate(tpl.title, context)
  const content = renderTemplate(tpl.content, context)

  const client = tx || prisma
  const queue = await client.notificationQueue.create({
    data: {
      recipientId,
      templateKey,
      title,
      content,
      context: JSON.stringify(context),
      priority,
      status: 'PENDING',
    },
  })

  // 开发期日志(生产可由 cron 拉表后实际发)
  console.log(`[notification] -> ${recipientId}: ${title}`)

  return queue
}

/**
 * 查询某用户的待发/已发通知
 */
export async function getUserNotifications(userId, { status = null, limit = 20, offset = 0 } = {}) {
  return prisma.notificationQueue.findMany({
    where: { recipientId: userId, ...(status ? { status } : {}) },
    orderBy: { createdAt: 'desc' },
    take: limit,
    skip: offset,
  })
}

/**
 * 标记已读
 */
export async function markAsRead(notificationId) {
  return prisma.notificationQueue.update({
    where: { id: notificationId },
    data: { status: 'READ', readAt: new Date() },
  })
}

export default {
  TEMPLATES,
  sendNotification,
  getUserNotifications,
  markAsRead,
}
