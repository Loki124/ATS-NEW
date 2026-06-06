/**
 * Offer 模板渲染服务 - PRD G24
 *
 * 4 个模板:
 *   GENERAL        - 通用模板 (基础字段)
 *   WITH_COMMISSION - 含提成 (commissionTrial/commissionFormal 字段)
 *   INTERN         - 实习生 (trialMonths 默认 0, 简化版)
 *   MEIZHOU        - 梅州版 (默认 legalCompany + 梅州地址)
 *
 * 渲染方式: 简单 HTML, 前端调用 window.print() 转 PDF
 * 变量: {{name}} 占位, 详见下方变量清单
 *
 * 后续可加 PDF 库 (pdfkit / puppeteer) 走服务端 PDF, 当前 MVP 输出 HTML
 */

import { prisma } from '../app.js'

// ===== 4 个内置模板 =====

const TEMPLATE_GENERAL = `
<div style="font-family: 'Microsoft YaHei', sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; line-height: 1.8;">
  <h1 style="text-align: center; color: #2c3e50;">录用意向书</h1>
  <p style="text-align: center; color: #7f8c8d;">Offer Letter</p>
  <hr/>
  <p>尊敬的 <strong>{{candidateName}}</strong> 先生/女士：</p>
  <p>我们很高兴地通知您，经过公司的严格审核，您已通过 <strong>{{positionTitle}}</strong> ({{jobLevel}}) 的招聘流程。</p>
  <p>现将录用信息通知如下：</p>
  <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa; width: 30%;">入职岗位</td><td style="padding: 8px; border: 1px solid #ddd;">{{positionTitle}} ({{jobLevel}})</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">所属部门</td><td style="padding: 8px; border: 1px solid #ddd;">{{departmentName}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">直接汇报对象</td><td style="padding: 8px; border: 1px solid #ddd;">{{directLeader}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">工作地点</td><td style="padding: 8px; border: 1px solid #ddd;">{{workLocation}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">期望入职日期</td><td style="padding: 8px; border: 1px solid #ddd;">{{expectedJoinDate}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">试用期月薪</td><td style="padding: 8px; border: 1px solid #ddd;">¥ {{baseSalaryTrial}} 元</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">转正月薪</td><td style="padding: 8px; border: 1px solid #ddd;">¥ {{baseSalaryFormal}} 元</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">试用期</td><td style="padding: 8px; border: 1px solid #ddd;">{{trialMonths}} 个月</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">合同类型</td><td style="padding: 8px; border: 1px solid #ddd;">{{contractType}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">法人公司</td><td style="padding: 8px; border: 1px solid #ddd;">{{legalCompany}}</td></tr>
  </table>
  <p>请您在收到本函后 <strong>7 个工作日</strong> 内确认是否接受本 offer，并回复本邮件或联系 HR ({{hrContact}})。</p>
  <p>如有任何疑问，请随时与我们联系。期待您的加入！</p>
  <br/>
  <p style="text-align: right;">{{legalCompany}}<br/>{{issueDate}}</p>
</div>
`

const TEMPLATE_WITH_COMMISSION = `
<div style="font-family: 'Microsoft YaHei', sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; line-height: 1.8;">
  <h1 style="text-align: center; color: #2c3e50;">录用意向书（销售/业务岗）</h1>
  <p style="text-align: center; color: #7f8c8d;">Offer Letter - With Commission</p>
  <hr/>
  <p>尊敬的 <strong>{{candidateName}}</strong>：</p>
  <p>恭喜您通过 <strong>{{positionTitle}}</strong> ({{jobLevel}}) 的招聘。本岗位包含业绩提成，详细如下：</p>
  <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">入职岗位</td><td style="padding: 8px; border: 1px solid #ddd;">{{positionTitle}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">部门</td><td style="padding: 8px; border: 1px solid #ddd;">{{departmentName}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">试用期月薪</td><td style="padding: 8px; border: 1px solid #ddd;">¥ {{baseSalaryTrial}} 元</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">转正月薪</td><td style="padding: 8px; border: 1px solid #ddd;">¥ {{baseSalaryFormal}} 元</td></tr>
    <tr style="background: #fff3cd;"><td style="padding: 8px; border: 1px solid #ddd;">试用期提成</td><td style="padding: 8px; border: 1px solid #ddd;"><strong>¥ {{commissionTrial}} 元/月（按业绩核算）</strong></td></tr>
    <tr style="background: #fff3cd;"><td style="padding: 8px; border: 1px solid #ddd;">转正提成</td><td style="padding: 8px; border: 1px solid #ddd;"><strong>¥ {{commissionFormal}} 元/月（按业绩核算）</strong></td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">提成说明</td><td style="padding: 8px; border: 1px solid #ddd;">具体提成比例与考核详见《销售提成管理办法》</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">期望入职日期</td><td style="padding: 8px; border: 1px solid #ddd;">{{expectedJoinDate}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">工作地点</td><td style="padding: 8px; border: 1px solid #ddd;">{{workLocation}}</td></tr>
  </table>
  <p>请在 7 个工作日内确认。HR 联系人：{{hrContact}}</p>
  <p style="text-align: right;">{{legalCompany}}<br/>{{issueDate}}</p>
</div>
`

const TEMPLATE_INTERN = `
<div style="font-family: 'Microsoft YaHei', sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; line-height: 1.8;">
  <h1 style="text-align: center; color: #2c3e50;">实习生录用通知</h1>
  <p style="text-align: center; color: #7f8c8d;">Internship Offer</p>
  <hr/>
  <p><strong>{{candidateName}}</strong> 同学：</p>
  <p>欢迎您加入 {{legalCompany}}！经面试与考核，您已通过 <strong>{{positionTitle}}</strong> 实习岗位的选拔，详情如下：</p>
  <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">实习岗位</td><td style="padding: 8px; border: 1px solid #ddd;">{{positionTitle}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">部门</td><td style="padding: 8px; border: 1px solid #ddd;">{{departmentName}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">实习津贴</td><td style="padding: 8px; border: 1px solid #ddd;">¥ {{baseSalaryTrial}} 元/月</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">实习周期</td><td style="padding: 8px; border: 1px solid #ddd;">不少于 {{trialMonths}} 个月</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">入职日期</td><td style="padding: 8px; border: 1px solid #ddd;">{{expectedJoinDate}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">工作地点</td><td style="padding: 8px; border: 1px solid #ddd;">{{workLocation}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">导师</td><td style="padding: 8px; border: 1px solid #ddd;">{{directLeader}}</td></tr>
  </table>
  <p><strong>特别说明：</strong></p>
  <ul>
    <li>实习期间表现优秀者，可获得正式 offer 机会</li>
    <li>实习津贴按月发放，实习结束统一出具实习证明</li>
    <li>请按时参加入职培训，详情将由 HR ({{hrContact}}) 另行通知</li>
  </ul>
  <p style="text-align: right;">{{legalCompany}}<br/>{{issueDate}}</p>
</div>
`

const TEMPLATE_MEIZHOU = `
<div style="font-family: 'Microsoft YaHei', sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; line-height: 1.8;">
  <h1 style="text-align: center; color: #c0392b;">录用意向书（梅州分公司）</h1>
  <p style="text-align: center; color: #7f8c8d;">Offer Letter - Meizhou Branch</p>
  <hr/>
  <p>尊敬的 <strong>{{candidateName}}</strong>：</p>
  <p>经 <strong>{{legalCompany}}</strong>（梅州分公司）综合评估，您已通过 <strong>{{positionTitle}}</strong> ({{jobLevel}}) 岗位的招聘流程。</p>
  <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">法人公司</td><td style="padding: 8px; border: 1px solid #ddd;">{{legalCompany}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">工作地点</td><td style="padding: 8px; border: 1px solid #ddd;">广东省梅州市 {{workLocation}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">所属部门</td><td style="padding: 8px; border: 1px solid #ddd;">{{departmentName}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">直接汇报</td><td style="padding: 8px; border: 1px solid #ddd;">{{directLeader}}</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">试用期月薪</td><td style="padding: 8px; border: 1px solid #ddd;">¥ {{baseSalaryTrial}} 元</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">转正月薪</td><td style="padding: 8px; border: 1px solid #ddd;">¥ {{baseSalaryFormal}} 元</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">房补（试用）</td><td style="padding: 8px; border: 1px solid #ddd;">¥ {{housingSubsidyTrial}} 元/月</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">房补（转正）</td><td style="padding: 8px; border: 1px solid #ddd;">¥ {{housingSubsidyFormal}} 元/月</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">出勤奖金</td><td style="padding: 8px; border: 1px solid #ddd;">¥ {{attendanceBonusFormal}} 元/月（转正后）</td></tr>
    <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">期望入职日期</td><td style="padding: 8px; border: 1px solid #ddd;">{{expectedJoinDate}}</td></tr>
  </table>
  <p>请于 7 个工作日内确认。梅州 HR：{{hrContact}}</p>
  <p style="text-align: right;">{{legalCompany}}<br/>梅州分公司<br/>{{issueDate}}</p>
</div>
`

// ===== 模板注册表 =====

export const OFFER_TEMPLATES = {
  GENERAL: {
    key: 'GENERAL',
    name: '通用模板',
    description: '标准 Offer 模板, 覆盖基础字段 (岗位/薪资/试用期/合同)',
    applicableTypes: ['FULL_TIME', 'PART_TIME', 'CONTRACTOR'],
    variables: ['candidateName', 'positionTitle', 'jobLevel', 'departmentName', 'directLeader',
      'workLocation', 'expectedJoinDate', 'baseSalaryTrial', 'baseSalaryFormal',
      'trialMonths', 'contractType', 'legalCompany', 'hrContact', 'issueDate'],
    html: TEMPLATE_GENERAL,
  },
  WITH_COMMISSION: {
    key: 'WITH_COMMISSION',
    name: '含提成模板',
    description: '销售/业务岗, 额外展示试用期/转正提成',
    applicableTypes: ['SALES', 'BUSINESS'],
    variables: ['candidateName', 'positionTitle', 'jobLevel', 'departmentName',
      'baseSalaryTrial', 'baseSalaryFormal', 'commissionTrial', 'commissionFormal',
      'expectedJoinDate', 'workLocation', 'legalCompany', 'hrContact', 'issueDate'],
    html: TEMPLATE_WITH_COMMISSION,
  },
  INTERN: {
    key: 'INTERN',
    name: '实习生模板',
    description: '实习岗, 简化版, 加实习说明',
    applicableTypes: ['INTERN'],
    variables: ['candidateName', 'positionTitle', 'departmentName', 'baseSalaryTrial',
      'trialMonths', 'expectedJoinDate', 'workLocation', 'directLeader',
      'legalCompany', 'hrContact', 'issueDate'],
    html: TEMPLATE_INTERN,
  },
  MEIZHOU: {
    key: 'MEIZHOU',
    name: '梅州版',
    description: '梅州分公司专属, 加房补+出勤奖金',
    applicableTypes: ['FULL_TIME'],
    variables: ['candidateName', 'positionTitle', 'jobLevel', 'legalCompany', 'workLocation',
      'departmentName', 'directLeader', 'baseSalaryTrial', 'baseSalaryFormal',
      'housingSubsidyTrial', 'housingSubsidyFormal', 'attendanceBonusFormal',
      'expectedJoinDate', 'hrContact', 'issueDate'],
    html: TEMPLATE_MEIZHOU,
  },
}

/**
 * 渲染模板 (HTML)
 * @param {string} templateKey - GENERAL / WITH_COMMISSION / INTERN / MEIZHOU
 * @param {object} context - 变量值
 */
export function renderOfferTemplate(templateKey, context = {}) {
  const tpl = OFFER_TEMPLATES[templateKey]
  if (!tpl) throw new Error(`未知模板: ${templateKey}`)
  let html = tpl.html
  for (const [key, value] of Object.entries(context)) {
    const v = value ?? ''
    html = html.replace(new RegExp(`\\{\\{\\s*${key}\\s*\\}\\}`, 'g'), v)
  }
  return html
}

/**
 * 列出所有模板
 */
export function listOfferTemplates() {
  return Object.values(OFFER_TEMPLATES).map(({ html, ...meta }) => meta)
}

/**
 * 从 Offer 记录构建 context
 * 自动从关联表 (Application → Position → Department) 取字段
 */
export async function buildOfferContext(offerId) {
  const offer = await prisma.offer.findUnique({
    where: { id: offerId },
    include: {
      application: {
        include: {
          candidate: { select: { name: true } },
          position: {
            include: { department: { select: { name: true } } },
          },
        },
      },
    },
  })
  if (!offer) throw new Error(`Offer 不存在: ${offerId}`)

  return {
    candidateName: offer.application?.candidate?.name || '',
    positionTitle: offer.jobTitle || offer.application?.position?.name || '',
    jobLevel: offer.jobLevel || '',
    departmentName: offer.application?.position?.department?.name || '',
    directLeader: offer.directLeader || '',
    workLocation: offer.workLocation || offer.reportLocation || '',
    expectedJoinDate: offer.expectedJoinDate
      ? new Date(offer.expectedJoinDate).toLocaleDateString('zh-CN')
      : '',
    baseSalaryTrial: offer.baseSalaryTrial?.toString() || '0',
    baseSalaryFormal: offer.baseSalaryFormal?.toString() || '0',
    commissionTrial: offer.commissionTrial?.toString() || '0',
    commissionFormal: offer.commissionFormal?.toString() || '0',
    housingSubsidyTrial: offer.housingSubsidyTrial?.toString() || '0',
    housingSubsidyFormal: offer.housingSubsidyFormal?.toString() || '0',
    attendanceBonusFormal: offer.attendanceBonusFormal?.toString() || '0',
    trialMonths: offer.trialMonths?.toString() || '3',
    contractType: offer.contractType || '固定期限劳动合同',
    legalCompany: offer.legalCompany || '',
    hrContact: 'HR Department',
    issueDate: new Date().toLocaleDateString('zh-CN'),
  }
}

/**
 * 渲染并返回 Offer 的 HTML
 * @param {string} offerId
 * @param {string} templateKey
 */
export async function renderOfferFromRecord(offerId, templateKey) {
  const context = await buildOfferContext(offerId)
  return renderOfferTemplate(templateKey, context)
}

export default {
  OFFER_TEMPLATES,
  renderOfferTemplate,
  listOfferTemplates,
  buildOfferContext,
  renderOfferFromRecord,
}
