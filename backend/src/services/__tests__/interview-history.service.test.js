/**
 * G19 - 面试历史评价自动预填 - 服务测试
 *
 * 覆盖:
 *  - aggregateHistory 聚合统计
 *  - buildPreviousFeedbackString 中文模板
 *  - shouldAutoPrefill 决策
 *  - getCandidateHistory 拉取 + 标准化 + 排序
 */

import { jest } from '@jest/globals'

const mockPrisma = {
  interviewFeedback: { findMany: jest.fn() },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  getCandidateHistory,
  aggregateHistory,
  buildPreviousFeedbackString,
  shouldAutoPrefill,
} = await import('../interview-history.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('interview-history: aggregateHistory', () => {
  it('聚合 3 个反馈, 统计 pass/fail', () => {
    const feedbacks = [
      { result: 'PASS', reason: '技术扎实' },
      { result: 'PASS', reason: '沟通好' },
      { result: 'FAIL', reason: '深度不够' },
    ]
    const summary = aggregateHistory(feedbacks)
    expect(summary.passCount).toBe(2)
    expect(summary.failCount).toBe(1)
    expect(summary.total).toBe(3)
  })

  it('空数组 → 全 0', () => {
    const s = aggregateHistory([])
    expect(s).toEqual({ passCount: 0, failCount: 0, total: 0 })
  })

  it('null/undefined 输入 → 全 0', () => {
    expect(aggregateHistory(null)).toEqual({ passCount: 0, failCount: 0, total: 0 })
    expect(aggregateHistory(undefined)).toEqual({ passCount: 0, failCount: 0, total: 0 })
  })
})

describe('interview-history: buildPreviousFeedbackString', () => {
  it('中文模板包含 roundName/PASS/原因', () => {
    const str = buildPreviousFeedbackString({
      passCount: 2, failCount: 1, total: 3,
      feedbacks: [
        { roundName: 'HR初筛', interviewerName: 'Alice', result: 'PASS', reason: '沟通好' },
        { roundName: '技术一面', interviewerName: 'Bob',   result: 'PASS', reason: '基础扎实' },
        { roundName: '技术二面', interviewerName: 'Carol', result: 'FAIL', reason: '深度不够' },
      ]
    })
    expect(str).toContain('HR初筛')
    expect(str).toContain('PASS')
    expect(str).toContain('深度不够')
  })

  it('total=0 → 返回空字符串', () => {
    expect(buildPreviousFeedbackString({ passCount: 0, failCount: 0, total: 0, feedbacks: [] })).toBe('')
  })
})

describe('interview-history: shouldAutoPrefill', () => {
  it('候选人有 ≥1 历史 → true', () => {
    expect(shouldAutoPrefill({ total: 1 })).toBe(true)
  })

  it('无历史 → false', () => {
    expect(shouldAutoPrefill({ total: 0 })).toBe(false)
  })
})

describe('interview-history: getCandidateHistory', () => {
  it('返回结构化历史', async () => {
    mockPrisma.interviewFeedback.findMany.mockResolvedValueOnce([
      { id: 'f1', result: 'PASS', reason: '好', roundName: '一面', interviewerName: 'A', feedbackAt: new Date() }
    ])
    const h = await getCandidateHistory('c1')
    expect(h.total).toBe(1)
    expect(h.feedbacks).toHaveLength(1)
  })

  it('SQL 包含 candidateId 过滤', async () => {
    mockPrisma.interviewFeedback.findMany.mockResolvedValueOnce([])
    await getCandidateHistory('c-123')
    const call = mockPrisma.interviewFeedback.findMany.mock.calls[0][0]
    expect(JSON.stringify(call.where)).toContain('c-123')
  })

  it('历史聚合按时间倒序', async () => {
    mockPrisma.interviewFeedback.findMany.mockResolvedValueOnce([
      { id: '1', result: 'PASS', feedbackAt: new Date('2025-01-01'), roundName: 'A', interviewerName: 'X' },
      { id: '2', result: 'FAIL', feedbackAt: new Date('2025-03-01'), roundName: 'B', interviewerName: 'Y' },
    ])
    const h = await getCandidateHistory('c1')
    expect(h.feedbacks[0].id).toBe('2')
  })
})
