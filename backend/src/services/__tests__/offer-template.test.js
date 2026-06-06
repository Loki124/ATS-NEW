/**
 * Offer 模板渲染测试 - PRD G24
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  offer: { findUnique: jest.fn() },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  OFFER_TEMPLATES,
  renderOfferTemplate,
  listOfferTemplates,
  buildOfferContext,
  renderOfferFromRecord,
} = await import('../offer-template.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('offer-template: 4 内置模板', () => {
  it('列表含 4 模板', () => {
    expect(Object.keys(OFFER_TEMPLATES)).toHaveLength(4)
    expect(OFFER_TEMPLATES.GENERAL).toBeDefined()
    expect(OFFER_TEMPLATES.WITH_COMMISSION).toBeDefined()
    expect(OFFER_TEMPLATES.INTERN).toBeDefined()
    expect(OFFER_TEMPLATES.MEIZHOU).toBeDefined()
  })

  it('每个模板都有 variables + html + applicableTypes', () => {
    for (const tpl of Object.values(OFFER_TEMPLATES)) {
      expect(Array.isArray(tpl.variables)).toBe(true)
      expect(tpl.variables.length).toBeGreaterThan(0)
      expect(typeof tpl.html).toBe('string')
      expect(tpl.html.length).toBeGreaterThan(100)
      expect(Array.isArray(tpl.applicableTypes)).toBe(true)
    }
  })

  it('listOfferTemplates 不含 html 字段', () => {
    const list = listOfferTemplates()
    expect(list).toHaveLength(4)
    for (const t of list) {
      expect(t.html).toBeUndefined()
      expect(t.variables).toBeDefined()
    }
  })
})

describe('offer-template: renderOfferTemplate', () => {
  it('渲染 GENERAL 模板, 替换所有变量', () => {
    const ctx = {
      candidateName: '张三',
      positionTitle: '高级工程师',
      jobLevel: 'P6',
      departmentName: '技术部',
      directLeader: '李四',
      workLocation: '深圳',
      expectedJoinDate: '2026-07-01',
      baseSalaryTrial: '20000',
      baseSalaryFormal: '25000',
      trialMonths: '3',
      contractType: '固定期限劳动合同',
      legalCompany: '深圳XX有限公司',
      hrContact: 'HR-王',
      issueDate: '2026-06-06',
    }
    const html = renderOfferTemplate('GENERAL', ctx)
    expect(html).toContain('张三')
    expect(html).toContain('高级工程师')
    expect(html).toContain('P6')
    expect(html).toContain('20000')
    expect(html).toContain('深圳XX有限公司')
    // 占位符应全替换
    expect(html).not.toContain('{{candidateName}}')
    expect(html).not.toContain('{{positionTitle}}')
  })

  it('WITH_COMMISSION 渲染含 commission 字段', () => {
    const html = renderOfferTemplate('WITH_COMMISSION', {
      candidateName: 'X', positionTitle: 'P', jobLevel: 'L', departmentName: 'D',
      baseSalaryTrial: '100', baseSalaryFormal: '200', commissionTrial: '50', commissionFormal: '100',
      expectedJoinDate: '今天', workLocation: 'W', legalCompany: 'LC', hrContact: 'H', issueDate: 'I',
    })
    expect(html).toContain('50')
    expect(html).toContain('100')
  })

  it('INTERN 模板特殊字段 trialMonths', () => {
    const html = renderOfferTemplate('INTERN', {
      candidateName: 'X', positionTitle: 'P', departmentName: 'D', baseSalaryTrial: '3000',
      trialMonths: '6', expectedJoinDate: '今天', workLocation: 'W', directLeader: 'L',
      legalCompany: 'LC', hrContact: 'H', issueDate: 'I',
    })
    expect(html).toContain('实习')
    expect(html).toContain('6 个月')
  })

  it('MEIZHOU 模板含房补 + 出勤奖金', () => {
    const html = renderOfferTemplate('MEIZHOU', {
      candidateName: 'X', positionTitle: 'P', jobLevel: 'L', legalCompany: '梅州XX',
      workLocation: '梅江区', departmentName: 'D', directLeader: 'L',
      baseSalaryTrial: '100', baseSalaryFormal: '200', housingSubsidyTrial: '500',
      housingSubsidyFormal: '1000', attendanceBonusFormal: '300',
      expectedJoinDate: '今天', hrContact: 'H', issueDate: 'I',
    })
    expect(html).toContain('梅州')
    expect(html).toContain('500')
    expect(html).toContain('1000')
  })

  it('未知模板 → 抛错', () => {
    expect(() => renderOfferTemplate('UNKNOWN', {})).toThrow(/未知模板/)
  })

  it('context 缺字段 → 占位符保留 (不替换)', () => {
    const html = renderOfferTemplate('GENERAL', { candidateName: '张三' })
    expect(html).toContain('张三')
    expect(html).toContain('{{positionTitle}}') // 未提供,保留
  })
})

describe('offer-template: buildOfferContext + renderOfferFromRecord', () => {
  const fakeOffer = {
    id: 'off-1',
    expectedJoinDate: new Date('2026-07-01'),
    baseSalaryTrial: { toString: () => '20000' },
    baseSalaryFormal: { toString: () => '25000' },
    trialMonths: 3,
    contractType: '固定期限',
    legalCompany: '深圳XX',
    jobTitle: '高级工程师',
    jobLevel: 'P6',
    directLeader: '李四',
    workLocation: '深圳',
    application: {
      candidate: { name: '张三' },
      position: { name: '工程师', department: { name: '技术部' } },
    },
  }

  it('从 Offer 记录构建 context 并渲染', async () => {
    mockPrisma.offer.findUnique.mockResolvedValue(fakeOffer)
    const html = await renderOfferFromRecord('off-1', 'GENERAL')
    expect(html).toContain('张三')
    expect(html).toContain('高级工程师')
    expect(html).toContain('P6')
    expect(html).toContain('技术部')
    expect(html).toContain('20000')
  })

  it('Offer 不存在 → 抛错', async () => {
    mockPrisma.offer.findUnique.mockResolvedValue(null)
    await expect(renderOfferFromRecord('off-x', 'GENERAL')).rejects.toThrow(/Offer 不存在/)
  })

  it('buildOfferContext 字段映射 (Decimal/Date → string)', async () => {
    mockPrisma.offer.findUnique.mockResolvedValue(fakeOffer)
    const ctx = await buildOfferContext('off-1')
    expect(ctx.candidateName).toBe('张三')
    expect(ctx.baseSalaryTrial).toBe('20000')
    expect(ctx.trialMonths).toBe('3')
    expect(ctx.expectedJoinDate).toMatch(/2026/) // 格式化
  })
})
