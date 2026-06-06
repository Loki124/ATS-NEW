/**
 * 通知服务 - PRD B.2 + G36
 *
 * 模板优先从 DB 读 (NotificationTemplate 表), 兜底用内联 TEMPLATES
 * 占位符: {{name}} (DB 风格) 和 {name} (内联风格) 都支持
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

// 内联模板 (兜底,DB 没找到时用) - PRD G36 MVP 4 模板
const INLINE_TEMPLATES = {
  DEMAND_APPROVAL_PENDING: {
    title: '【审批待办】需求 {{demandName}}',
    content: '{{submitterName}} 提交了需求「{{demandName}}」等待您审批',
    category: 'APPROVAL',
  },
  DEMAND_APPROVAL_APPROVED: {
    title: '【审批通过】需求 {{demandName}}',
    content: '需求「{{demandName}}」已通过全部审批,可开始执行',
    category: 'APPROVAL',
  },
  DEMAND_APPROVAL_REJECTED: {
    title: '【审批拒绝】需求 {{demandName}}',
    content: '需求「{{demandName}}」被拒绝,原因: {{reason}}',
    category: 'APPROVAL',
  },
  DEMAND_APPROVAL_CANCELLED: {
    title: '【审批撤销】需求 {{demandName}}',
    content: '需求「{{demandName}}」的审批已被创建人撤销',
    category: 'APPROVAL',
  },
  DEMAND_APPROVAL_STEP_APPROVED: {
    title: '【审批进展】需求 {{demandName}}',
    content: '需求「{{demandName}}」第 {{stepIndex}} 步({{approverRole}})已通过',
    category: 'APPROVAL',
  },
  INTERVIEW_FEEDBACK_REQUEST: {
    title: '【面试反馈】候选人 {{candidateName}}',
    content: '请提交对候选人「{{candidateName}}」的面试反馈',
    category: 'INTERVIEW',
  },
  OFFER_SENT_TO_CANDIDATE: {
    title: '【Offer】恭喜 {{candidateName}}',
    content: '您的 Offer 已发送,请尽快确认',
    category: 'OFFER',
  },
  OFFER_ACCEPTED: {
    title: '【Offer 已接受】{{candidateName}}',
    content: '候选人 {{candidateName}} 已接受 Offer, 准备入职',
    category: 'OFFER',
  },
  OFFER_REJECTED: {
    title: '【Offer 已拒绝】{{candidateName}}',
    content: '候选人 {{candidateName}} 拒绝了 Offer',
    category: 'OFFER',
  },
  RESUME_RECEIVED: {
    title: '【新简历】{{candidateName}}',
    content: '收到候选人 {{candidateName}} 的简历, 来自 {{source}}',
    category: 'CANDIDATE',
  },
}

/**
 * 渲染模板 - 支持 {{var}} 和 {var} 两种占位符
 */
function renderTemplate(template, context) {
  if (!template) return ''
  let result = template
  for (const [key, value] of Object.entries(context || {})) {
    const v = value ?? ''
    result = result.replace(new RegExp(`\\{\\{\\s*${key}\\s*\\}\\}`, 'g'), v)
    result = result.replace(new RegExp(`\\{\\s*${key}\\s*\\}`, 'g'), v)
  }
  return result
}

/**
 * 加载模板 (DB 优先, 内存兜底)
 */
async function loadTemplate(templateKey) {
  // 1. 尝试 DB
  try {
    const tpl = await prisma.notificationTemplate.findUnique({
      where: { templateKey, isActive: true },
    })
    if (tpl) return { title: tpl.title, content: tpl.content, source: 'db' }
  } catch (e) {
    // DB 不可用时 fallback
  }
  // 2. 内存兜底
  const inline = INLINE_TEMPLATES[templateKey]
  if (inline) return { title: inline.title, content: inline.content, source: 'inline' }
  return null
}

/**
 * 发送通知
 */
export async function sendNotification({
  recipientId,
  templateKey,
  context = {},
  priority = 'NORMAL',
  channel = null, // 覆盖模板的 channel
  tx = null,
}) {
  if (!recipientId) throw new Error('recipientId 必填')
  const tpl = await loadTemplate(templateKey)
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

  console.log(`[notification][${tpl.source}] -> ${recipientId}: ${title}`)

  return queue
}

/**
 * 查询某用户的通知
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

// ====== 模板 CRUD (G36 配套) ======

/**
 * 列出所有模板
 */
export async function listTemplates({ category, channel, isActive, limit = 100 } = {}) {
  return prisma.notificationTemplate.findMany({
    where: { ...(category && { category }), ...(channel && { channel }), ...(isActive !== undefined && { isActive }) },
    orderBy: { category: 'asc', templateKey: 'asc' },
    take: limit,
  })
}

/**
 * 按 key 获取模板
 */
export async function getTemplate(templateKey) {
  return prisma.notificationTemplate.findUnique({ where: { templateKey } })
}

/**
 * 创建/更新模板
 */
export async function upsertTemplate(data) {
  const { templateKey, name, channel = 'SYSTEM', category, title, content, variables, description, isActive = true } = data
  return prisma.notificationTemplate.upsert({
    where: { templateKey },
    create: { templateKey, name, channel, category, title, content, variables, description, isActive },
    update: { name, channel, category, title, content, variables, description, isActive },
  })
}

/**
 * 删除模板 (软删除: 置 isActive=false)
 */
export async function deactivateTemplate(templateKey) {
  return prisma.notificationTemplate.update({
    where: { templateKey },
    data: { isActive: false },
  })
}

export default {
  INLINE_TEMPLATES,
  sendNotification,
  getUserNotifications,
  markAsRead,
  listTemplates,
  getTemplate,
  upsertTemplate,
  deactivateTemplate,
  renderTemplate,
  loadTemplate,
}
