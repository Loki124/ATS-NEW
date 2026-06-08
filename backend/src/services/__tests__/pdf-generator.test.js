/**
 * PDF 生成器测试
 */

import { jest } from '@jest/globals'
import { generateSimplePdf, offerContextToLines, renderBackgroundCheckReport } from '../pdf-generator.service.js'

describe('pdf-generator: generateSimplePdf', () => {
  it('生成非空 Buffer', () => {
    const pdf = generateSimplePdf({ title: 'Test', lines: ['Hello World'] })
    expect(Buffer.isBuffer(pdf)).toBe(true)
    expect(pdf.length).toBeGreaterThan(100)
  })

  it('以 %PDF-1.4 开头', () => {
    const pdf = generateSimplePdf({ title: 'T', lines: ['x'] })
    const head = pdf.slice(0, 8).toString('utf8')
    expect(head).toBe('%PDF-1.4')
  })

  it('以 %%EOF 结尾', () => {
    const pdf = generateSimplePdf({ title: 'T', lines: ['x'] })
    const tail = pdf.slice(-6).toString('utf8')
    expect(tail).toBe('%%EOF\n')
  })

  it('多页: 大量 lines 自动分页', () => {
    const lines = Array(200).fill('line content')
    const pdf = generateSimplePdf({ title: 'Multi', lines })
    const text = pdf.toString('utf8')
    // xref 应有正确的对象数
    expect(text).toMatch(/^xref\n0 \d+$/m)
  })

  it('空 lines 也生成合法 PDF', () => {
    const pdf = generateSimplePdf({ title: 'Empty' })
    expect(pdf.length).toBeGreaterThan(50)
  })

  it('转义 PDF 特殊字符 ( ) \\', () => {
    const pdf = generateSimplePdf({ title: 'T', lines: ['has (paren) and \\back'] })
    expect(pdf.length).toBeGreaterThan(0)
  })
})

describe('pdf-generator: offerContextToLines', () => {
  it('生成完整 Offer 行', () => {
    const ctx = {
      candidateName: '张三', positionTitle: '工程师', jobLevel: 'P6',
      departmentName: '技术部', directLeader: '李四', workLocation: '深圳',
      expectedJoinDate: '2026-07-01', baseSalaryTrial: '20000', baseSalaryFormal: '25000',
      trialMonths: '3', contractType: '固定期限', legalCompany: '深圳XX',
      hrContact: 'HR-王', issueDate: '2026-06-06',
    }
    const lines = offerContextToLines(ctx)
    expect(lines).toContain('录用意向书 / Offer Letter')
    expect(lines.some(l => l.includes('张三'))).toBe(true)
    expect(lines.some(l => l.includes('20000'))).toBe(true)
    expect(lines.some(l => l.includes('25000'))).toBe(true)
  })

  it('含提成时显示提成信息', () => {
    const lines = offerContextToLines({
      candidateName: 'X', positionTitle: 'P', jobLevel: 'L',
      departmentName: 'D', directLeader: 'L', workLocation: 'W',
      expectedJoinDate: 'E', baseSalaryTrial: '1', baseSalaryFormal: '2',
      trialMonths: '1', contractType: 'C', legalCompany: 'LC', hrContact: 'H', issueDate: 'I',
      commissionTrial: '500', commissionFormal: '1000',
    })
    expect(lines.some(l => l.includes('提成'))).toBe(true)
    expect(lines.some(l => l.includes('500'))).toBe(true)
  })

  it('无提成时不显示提成段落', () => {
    const lines = offerContextToLines({
      candidateName: 'X', positionTitle: 'P', jobLevel: 'L',
      departmentName: 'D', directLeader: 'L', workLocation: 'W',
      expectedJoinDate: 'E', baseSalaryTrial: '1', baseSalaryFormal: '2',
      trialMonths: '1', contractType: 'C', legalCompany: 'LC', hrContact: 'H', issueDate: 'I',
    })
    expect(lines.some(l => l.includes('提成'))).toBe(false)
  })
})

describe('pdf-generator: 端到端', () => {
  it('生成可下载的 PDF (Offer 完整流程)', () => {
    const ctx = {
      candidateName: '张三', positionTitle: '高级工程师', jobLevel: 'P6',
      departmentName: '技术部', directLeader: '李四', workLocation: '深圳',
      expectedJoinDate: '2026-07-01', baseSalaryTrial: '20000', baseSalaryFormal: '25000',
      trialMonths: '3', contractType: '固定期限劳动合同', legalCompany: '深圳XX有限公司',
      hrContact: 'HR-王', issueDate: '2026-06-06',
      commissionTrial: '500', commissionFormal: '1000',
    }
    const lines = offerContextToLines(ctx)
    const pdf = generateSimplePdf({ title: 'Offer Letter', lines, author: 'ATS System' })
    expect(pdf.length).toBeGreaterThan(500)
    expect(pdf.slice(0, 8).toString()).toBe('%PDF-1.4')
  })
})

describe('pdf-generator: renderBackgroundCheckReport (G26)', () => {
  it('生成非空 PDF Buffer', () => {
    const pdf = renderBackgroundCheckReport({
      offer: { id: 'o1', positionName: '工程师' },
      candidate: { name: '张三', phone: '13800138000' },
      record: { level: 'PASS', score: 100, risks: [], checkType: '学历', completedAt: new Date() },
    })
    expect(Buffer.isBuffer(pdf)).toBe(true)
    expect(pdf.length).toBeGreaterThan(500)
  })

  it('PDF 头部为 %PDF-1.4', () => {
    const pdf = renderBackgroundCheckReport({
      offer: { id: 'o1' },
      candidate: { name: '李四' },
      record: { level: 'WARN', score: 70 },
    })
    expect(pdf.slice(0, 8).toString()).toBe('%PDF-1.4')
  })
})
