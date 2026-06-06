/**
 * 通知模板 seed - PRD G36
 *
 * 跑法: node prisma/seed.notification-templates.js
 * 已存在 templateKey 的会跳过 (不覆盖,避免误改)
 */

import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

const TEMPLATES = [
  // ===== 需求审批 (5) =====
  { templateKey: 'DEMAND_APPROVAL_PENDING', name: '需求审批待办', channel: 'WECOM', category: 'APPROVAL',
    title: '【审批待办】需求 {{demandName}}',
    content: '{{submitterName}} 提交了需求「{{demandName}}」, 您是 {{approverRole}}, 请尽快审批',
    variables: [
      { name: 'demandName', type: 'string', required: true, description: '需求名称' },
      { name: 'submitterName', type: 'string', required: true, description: '提交人' },
      { name: 'approverRole', type: 'string', required: true, description: '当前审批人角色' },
    ],
  },
  { templateKey: 'DEMAND_APPROVAL_APPROVED', name: '需求审批通过', channel: 'SYSTEM', category: 'APPROVAL',
    title: '【审批通过】需求 {{demandName}}',
    content: '需求「{{demandName}}」已通过全部审批, 可开始执行',
    variables: [{ name: 'demandName', type: 'string', required: true }],
  },
  { templateKey: 'DEMAND_APPROVAL_REJECTED', name: '需求审批拒绝', channel: 'SYSTEM', category: 'APPROVAL',
    title: '【审批拒绝】需求 {{demandName}}',
    content: '需求「{{demandName}}」被拒绝, 原因: {{reason}}',
    variables: [
      { name: 'demandName', type: 'string', required: true },
      { name: 'reason', type: 'string', required: true },
    ],
  },
  { templateKey: 'DEMAND_APPROVAL_CANCELLED', name: '需求审批撤销', channel: 'SYSTEM', category: 'APPROVAL',
    title: '【审批撤销】需求 {{demandName}}',
    content: '需求「{{demandName}}」的审批已被创建人撤销',
    variables: [{ name: 'demandName', type: 'string', required: true }],
  },
  { templateKey: 'DEMAND_APPROVAL_STEP_APPROVED', name: '需求审批进展', channel: 'SYSTEM', category: 'APPROVAL',
    title: '【审批进展】需求 {{demandName}}',
    content: '需求「{{demandName}}」第 {{stepIndex}} 步({{approverRole}})已通过',
    variables: [
      { name: 'demandName', type: 'string', required: true },
      { name: 'stepIndex', type: 'number', required: true },
      { name: 'approverRole', type: 'string', required: true },
    ],
  },

  // ===== 面试 (4) =====
  { templateKey: 'INTERVIEW_FEEDBACK_REQUEST', name: '面试反馈待提交', channel: 'WECOM', category: 'INTERVIEW',
    title: '【面试反馈】候选人 {{candidateName}}',
    content: '请在 {{interviewDate}} 前提交对候选人「{{candidateName}}」的面试反馈',
    variables: [
      { name: 'candidateName', type: 'string', required: true },
      { name: 'interviewDate', type: 'datetime', required: true },
    ],
  },
  { templateKey: 'INTERVIEW_SCHEDULED', name: '面试已安排', channel: 'WECOM', category: 'INTERVIEW',
    title: '【面试安排】{{candidateName}}',
    content: '{{candidateName}} 的 {{interviewType}} 面试已安排在 {{interviewDate}}, 地点: {{location}}',
    variables: [
      { name: 'candidateName', type: 'string', required: true },
      { name: 'interviewType', type: 'string', required: true },
      { name: 'interviewDate', type: 'datetime', required: true },
      { name: 'location', type: 'string', required: false },
    ],
  },
  { templateKey: 'INTERVIEW_PASSED', name: '面试已通过', channel: 'SYSTEM', category: 'INTERVIEW',
    title: '【面试通过】{{candidateName}}',
    content: '候选人 {{candidateName}} 的 {{interviewType}} 已通过, 可进入下一轮',
    variables: [
      { name: 'candidateName', type: 'string', required: true },
      { name: 'interviewType', type: 'string', required: true },
    ],
  },
  { templateKey: 'INTERVIEW_FAILED', name: '面试未通过', channel: 'SYSTEM', category: 'INTERVIEW',
    title: '【面试未通过】{{candidateName}}',
    content: '候选人 {{candidateName}} 的 {{interviewType}} 未通过, 原因: {{reason}}',
    variables: [
      { name: 'candidateName', type: 'string', required: true },
      { name: 'interviewType', type: 'string', required: true },
      { name: 'reason', type: 'string', required: false },
    ],
  },

  // ===== Offer (6) =====
  { templateKey: 'OFFER_SENT_TO_CANDIDATE', name: 'Offer 已发送候选人', channel: 'EMAIL', category: 'OFFER',
    title: '【Offer】恭喜 {{candidateName}}',
    content: '您的 Offer 已发送, 期望入职日期: {{expectedJoinDate}}, 请尽快确认',
    variables: [
      { name: 'candidateName', type: 'string', required: true },
      { name: 'expectedJoinDate', type: 'date', required: true },
    ],
  },
  { templateKey: 'OFFER_ACCEPTED', name: 'Offer 已接受', channel: 'SYSTEM', category: 'OFFER',
    title: '【Offer 已接受】{{candidateName}}',
    content: '候选人 {{candidateName}} 已接受 Offer, 准备入职',
    variables: [{ name: 'candidateName', type: 'string', required: true }],
  },
  { templateKey: 'OFFER_REJECTED', name: 'Offer 已拒绝', channel: 'SYSTEM', category: 'OFFER',
    title: '【Offer 已拒绝】{{candidateName}}',
    content: '候选人 {{candidateName}} 拒绝了 Offer, 原因: {{reason}}',
    variables: [
      { name: 'candidateName', type: 'string', required: true },
      { name: 'reason', type: 'string', required: false },
    ],
  },
  { templateKey: 'OFFER_PENDING_APPROVAL', name: 'Offer 待审批', channel: 'WECOM', category: 'OFFER',
    title: '【Offer 审批】{{candidateName}}',
    content: '{{submitterName}} 提交了 {{candidateName}} 的 Offer, 请审批',
    variables: [
      { name: 'candidateName', type: 'string', required: true },
      { name: 'submitterName', type: 'string', required: true },
    ],
  },
  { templateKey: 'OFFER_APPROVED', name: 'Offer 已审批通过', channel: 'SYSTEM', category: 'OFFER',
    title: '【Offer 审批通过】{{candidateName}}',
    content: '{{candidateName}} 的 Offer 已通过审批, 可发送候选人',
    variables: [{ name: 'candidateName', type: 'string', required: true }],
  },
  { templateKey: 'OFFER_EXPIRED', name: 'Offer 已过期', channel: 'SYSTEM', category: 'OFFER',
    title: '【Offer 过期】{{candidateName}}',
    content: '{{candidateName}} 的 Offer 长期未确认已过期, 可重新编辑发送',
    variables: [{ name: 'candidateName', type: 'string', required: true }],
  },

  // ===== 候选人 (3) =====
  { templateKey: 'RESUME_RECEIVED', name: '新简历到达', channel: 'SYSTEM', category: 'CANDIDATE',
    title: '【新简历】{{candidateName}}',
    content: '收到候选人 {{candidateName}} 的简历, 来自 {{source}}',
    variables: [
      { name: 'candidateName', type: 'string', required: true },
      { name: 'source', type: 'string', required: true },
    ],
  },
  { templateKey: 'CANDIDATE_ARCHIVED', name: '候选人已归档', channel: 'SYSTEM', category: 'CANDIDATE',
    title: '【已归档】{{candidateName}}',
    content: '候选人 {{candidateName}} 已归档, 原因: {{reason}}',
    variables: [
      { name: 'candidateName', type: 'string', required: true },
      { name: 'reason', type: 'string', required: false },
    ],
  },
  { templateKey: 'CANDIDATE_ASSIGNED', name: '候选人已分配', channel: 'WECOM', category: 'CANDIDATE',
    title: '【分配待办】{{candidateName}}',
    content: '{{assignerName}} 将候选人 {{candidateName}} 分配给您, 请尽快跟进',
    variables: [
      { name: 'candidateName', type: 'string', required: true },
      { name: 'assignerName', type: 'string', required: true },
    ],
  },

  // ===== 入职 (2) =====
  { templateKey: 'ONBOARDING_REMINDER', name: '入职提醒', channel: 'WECOM', category: 'ONBOARDING',
    title: '【入职提醒】{{candidateName}}',
    content: '{{candidateName}} 计划 {{joinDate}} 入职, 请准备好工位/账号/合同',
    variables: [
      { name: 'candidateName', type: 'string', required: true },
      { name: 'joinDate', type: 'date', required: true },
    ],
  },
  { templateKey: 'ONBOARDING_OVERDUE', name: '入职逾期', channel: 'SYSTEM', category: 'ONBOARDING',
    title: '【入职逾期】{{candidateName}}',
    content: '{{candidateName}} 计划入职日期已过, 请联系确认',
    variables: [{ name: 'candidateName', type: 'string', required: true }],
  },

  // ===== 需求 (2) =====
  { templateKey: 'DEMAND_EXPIRED', name: '需求已超期', channel: 'SYSTEM', category: 'DEMAND',
    title: '【需求超期】{{demandName}}',
    content: '需求「{{demandName}}」已超过结束日期, 请检查是否需要延期或停招',
    variables: [{ name: 'demandName', type: 'string', required: true }],
  },
  { templateKey: 'DEMAND_COMPLETED', name: '需求已完成', channel: 'SYSTEM', category: 'DEMAND',
    title: '【需求完成】{{demandName}}',
    content: '需求「{{demandName}}」关联职位均已招满, 需求已自动完成',
    variables: [{ name: 'demandName', type: 'string', required: true }],
  },
]

async function main() {
  let created = 0
  let skipped = 0
  for (const tpl of TEMPLATES) {
    const existing = await prisma.notificationTemplate.findUnique({ where: { templateKey: tpl.templateKey } })
    if (existing) {
      skipped++
      continue
    }
    await prisma.notificationTemplate.create({ data: tpl })
    created++
  }
  console.log(`✅ NotificationTemplate seed: created=${created}, skipped=${skipped}, total=${TEMPLATES.length}`)
}

main()
  .catch((e) => { console.error(e); process.exit(1) })
  .finally(() => prisma.$disconnect())
