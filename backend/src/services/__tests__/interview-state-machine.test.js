/**
 * 面试状态机测试
 *
 * 纯函数 (canTransitionInterview, canAdvanceToNext) + service (computeInterviewStageStatus)
 */

import { jest } from '@jest/globals'

// Mock prisma 在 service import 之前
const mockPrisma = {
  application: {
    findUnique: jest.fn(),
    update: jest.fn(),
  },
}
jest.unstable_mockModule('../../app.js', () => ({ prisma: mockPrisma }))

const {
  INTERVIEW_STAGE_STATUS,
  canTransitionInterview,
  canAdvanceToNext,
  computeInterviewStageStatus,
  refreshApplicationStageStatus,
} = await import('../interview-state-machine.service.js')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('interview-state-machine: canTransitionInterview', () => {
  it('NOT_ARRANGED → PENDING_FEEDBACK 合法', () => {
    expect(canTransitionInterview('NOT_ARRANGED', 'PENDING_FEEDBACK')).toBe(true)
  })
  it('PENDING_FEEDBACK → ALL_PASS 合法', () => {
    expect(canTransitionInterview('PENDING_FEEDBACK', 'ALL_PASS')).toBe(true)
  })
  it('PENDING_FEEDBACK → PARTIAL_PASS 合法', () => {
    expect(canTransitionInterview('PENDING_FEEDBACK', 'PARTIAL_PASS')).toBe(true)
  })
  it('PENDING_FEEDBACK → ALL_FAIL 合法', () => {
    expect(canTransitionInterview('PENDING_FEEDBACK', 'ALL_FAIL')).toBe(true)
  })
  it('ALL_PASS → PENDING_FEEDBACK 合法 (重新安排)', () => {
    expect(canTransitionInterview('ALL_PASS', 'PENDING_FEEDBACK')).toBe(true)
  })
  it('未知状态 → false', () => {
    expect(canTransitionInterview('UNKNOWN', 'ALL_PASS')).toBe(false)
  })
})

describe('interview-state-machine: canAdvanceToNext', () => {
  it('ALL_PASS 可进下一阶段', () => {
    expect(canAdvanceToNext(INTERVIEW_STAGE_STATUS.ALL_PASS)).toBe(true)
  })
  it('PARTIAL_PASS 可进下一阶段', () => {
    expect(canAdvanceToNext(INTERVIEW_STAGE_STATUS.PARTIAL_PASS)).toBe(true)
  })
  it('ALL_FAIL 不可进下一阶段', () => {
    expect(canAdvanceToNext(INTERVIEW_STAGE_STATUS.ALL_FAIL)).toBe(false)
  })
  it('PENDING_FEEDBACK 不可进下一阶段', () => {
    expect(canAdvanceToNext(INTERVIEW_STAGE_STATUS.PENDING_FEEDBACK)).toBe(false)
  })
  it('NOT_ARRANGED 不可进下一阶段', () => {
    expect(canAdvanceToNext(INTERVIEW_STAGE_STATUS.NOT_ARRANGED)).toBe(false)
  })
})

describe('interview-state-machine: computeInterviewStageStatus', () => {
  const now = new Date()
  const past = new Date(now.getTime() - 86400000) // 昨天
  const future = new Date(now.getTime() + 86400000) // 明天

  it('application 不存在 → NOT_ARRANGED', async () => {
    mockPrisma.application.findUnique.mockResolvedValue(null)
    expect(await computeInterviewStageStatus('app-1')).toBe('NOT_ARRANGED')
  })

  it('无任何面试 → NOT_ARRANGED', async () => {
    mockPrisma.application.findUnique.mockResolvedValue({
      id: 'app-1',
      interviews: [],
    })
    expect(await computeInterviewStageStatus('app-1')).toBe('NOT_ARRANGED')
  })

  it('有面试但都未到时间 → NOT_ARRANGED', async () => {
    mockPrisma.application.findUnique.mockResolvedValue({
      id: 'app-1',
      interviews: [
        { id: 'i1', interviewDate: future, feedbackStatus: 'PENDING', feedbacks: [] },
      ],
    })
    expect(await computeInterviewStageStatus('app-1')).toBe('NOT_ARRANGED')
  })

  it('有面试已过时间但未全部反馈 → PENDING_FEEDBACK', async () => {
    mockPrisma.application.findUnique.mockResolvedValue({
      id: 'app-1',
      interviews: [
        { id: 'i1', interviewDate: past, feedbackStatus: 'PENDING', feedbacks: [] },
        { id: 'i2', interviewDate: past, feedbackStatus: 'COMPLETED', feedbacks: [{ result: 'PASS' }] },
      ],
    })
    expect(await computeInterviewStageStatus('app-1')).toBe('PENDING_FEEDBACK')
  })

  it('全部反馈且全部 PASS → ALL_PASS', async () => {
    mockPrisma.application.findUnique.mockResolvedValue({
      id: 'app-1',
      interviews: [
        { id: 'i1', interviewDate: past, feedbackStatus: 'COMPLETED', feedbacks: [{ result: 'PASS' }] },
        { id: 'i2', interviewDate: past, feedbackStatus: 'COMPLETED', feedbacks: [{ result: 'PASS' }] },
      ],
    })
    expect(await computeInterviewStageStatus('app-1')).toBe('ALL_PASS')
  })

  it('全部反馈且全部 FAIL → ALL_FAIL', async () => {
    mockPrisma.application.findUnique.mockResolvedValue({
      id: 'app-1',
      interviews: [
        { id: 'i1', interviewDate: past, feedbackStatus: 'COMPLETED', feedbacks: [{ result: 'FAIL' }] },
      ],
    })
    expect(await computeInterviewStageStatus('app-1')).toBe('ALL_FAIL')
  })

  it('全部反馈但有 PASS 有 FAIL → PARTIAL_PASS', async () => {
    mockPrisma.application.findUnique.mockResolvedValue({
      id: 'app-1',
      interviews: [
        { id: 'i1', interviewDate: past, feedbackStatus: 'COMPLETED', feedbacks: [{ result: 'PASS' }, { result: 'FAIL' }] },
      ],
    })
    expect(await computeInterviewStageStatus('app-1')).toBe('PARTIAL_PASS')
  })

  it('多面试官的混合结果 → 按 PASS 比例计算', async () => {
    mockPrisma.application.findUnique.mockResolvedValue({
      id: 'app-1',
      interviews: [
        {
          id: 'i1', interviewDate: past, feedbackStatus: 'COMPLETED',
          feedbacks: [{ result: 'PASS' }, { result: 'FAIL' }, { result: 'PASS' }],
        },
      ],
    })
    expect(await computeInterviewStageStatus('app-1')).toBe('PARTIAL_PASS')
  })
})

describe('interview-state-machine: refreshApplicationStageStatus', () => {
  it('重新计算并写回 application', async () => {
    mockPrisma.application.findUnique.mockResolvedValue({
      id: 'app-1',
      interviews: [],
    })
    mockPrisma.application.update.mockResolvedValue({ id: 'app-1', currentStageStatus: 'NOT_ARRANGED' })
    const result = await refreshApplicationStageStatus('app-1')
    expect(result).toBe('NOT_ARRANGED')
    expect(mockPrisma.application.update).toHaveBeenCalledWith({
      where: { id: 'app-1' },
      data: { currentStageStatus: 'NOT_ARRANGED' },
    })
  })
})
