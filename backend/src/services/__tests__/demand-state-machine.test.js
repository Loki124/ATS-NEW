/**
 * 需求状态机纯函数测试
 *
 * 不依赖 prisma,只测状态转换合法性
 */

import { jest } from '@jest/globals'
import {
  DEMAND_STATUSES,
  APPROVAL_STATUSES,
  canTransitionDemand,
  canTransitionApproval,
  canAttachPosition,
  canSubmitForApproval,
} from '../demand-state-machine.service.js'

describe('demand-state-machine: canTransitionDemand', () => {
  it('DRAFT → NOT_STARTED 合法', () => {
    expect(canTransitionDemand('DRAFT', 'NOT_STARTED')).toBe(true)
  })

  it('DRAFT → IN_PROGRESS 非法 (必须先 NOT_STARTED)', () => {
    expect(canTransitionDemand('DRAFT', 'IN_PROGRESS')).toBe(false)
  })

  it('DRAFT → STOPPED 合法 (草稿可终止)', () => {
    expect(canTransitionDemand('DRAFT', 'STOPPED')).toBe(true)
  })

  it('NOT_STARTED → IN_PROGRESS 合法', () => {
    expect(canTransitionDemand('NOT_STARTED', 'IN_PROGRESS')).toBe(true)
  })

  it('NOT_STARTED → EXPIRED 合法 (未开始就超期)', () => {
    expect(canTransitionDemand('NOT_STARTED', 'EXPIRED')).toBe(true)
  })

  it('IN_PROGRESS → COMPLETED 合法', () => {
    expect(canTransitionDemand('IN_PROGRESS', 'COMPLETED')).toBe(true)
  })

  it('IN_PROGRESS → PAUSED 合法', () => {
    expect(canTransitionDemand('IN_PROGRESS', 'PAUSED')).toBe(true)
  })

  it('IN_PROGRESS → STOPPED 合法', () => {
    expect(canTransitionDemand('IN_PROGRESS', 'STOPPED')).toBe(true)
  })

  it('PAUSED → IN_PROGRESS 合法 (恢复)', () => {
    expect(canTransitionDemand('PAUSED', 'IN_PROGRESS')).toBe(true)
  })

  it('PAUSED → STOPPED 合法', () => {
    expect(canTransitionDemand('PAUSED', 'STOPPED')).toBe(true)
  })

  it('COMPLETED → IN_PROGRESS 合法 (恢复为进行中,新增空缺)', () => {
    expect(canTransitionDemand('COMPLETED', 'IN_PROGRESS')).toBe(true)
  })

  it('STOPPED 是终止态,不能转任何状态', () => {
    expect(canTransitionDemand('STOPPED', 'IN_PROGRESS')).toBe(false)
    expect(canTransitionDemand('STOPPED', 'PAUSED')).toBe(false)
    expect(canTransitionDemand('STOPPED', 'DRAFT')).toBe(false)
  })

  it('EXPIRED → IN_PROGRESS 合法 (恢复超期需求)', () => {
    expect(canTransitionDemand('EXPIRED', 'IN_PROGRESS')).toBe(true)
  })

  it('未知源状态 → 返回 false', () => {
    expect(canTransitionDemand('UNKNOWN', 'IN_PROGRESS')).toBe(false)
  })
})

describe('demand-state-machine: canTransitionApproval', () => {
  it('NOT_STARTED → PENDING 合法 (发起审批)', () => {
    expect(canTransitionApproval('NOT_STARTED', 'PENDING')).toBe(true)
  })

  it('PENDING → APPROVED 合法', () => {
    expect(canTransitionApproval('PENDING', 'APPROVED')).toBe(true)
  })

  it('PENDING → REJECTED 合法', () => {
    expect(canTransitionApproval('PENDING', 'REJECTED')).toBe(true)
  })

  it('PENDING → CANCELLED 合法', () => {
    expect(canTransitionApproval('PENDING', 'CANCELLED')).toBe(true)
  })

  it('REJECTED → PENDING 合法 (重发审批)', () => {
    expect(canTransitionApproval('REJECTED', 'PENDING')).toBe(true)
  })

  it('CANCELLED → PENDING 合法 (重发审批)', () => {
    expect(canTransitionApproval('CANCELLED', 'PENDING')).toBe(true)
  })

  it('APPROVED 是终态,不能转任何状态', () => {
    expect(canTransitionApproval('APPROVED', 'PENDING')).toBe(false)
    expect(canTransitionApproval('APPROVED', 'REJECTED')).toBe(false)
  })
})

describe('demand-state-machine: canAttachPosition', () => {
  it('NOT_STARTED 可创建/编辑职位', () => {
    expect(canAttachPosition('NOT_STARTED')).toBe(true)
  })

  it('IN_PROGRESS 可创建/编辑职位', () => {
    expect(canAttachPosition('IN_PROGRESS')).toBe(true)
  })

  it('DRAFT 不能创建职位 (还未提交审批)', () => {
    expect(canAttachPosition('DRAFT')).toBe(false)
  })

  it('STOPPED 不能创建职位', () => {
    expect(canAttachPosition('STOPPED')).toBe(false)
  })

  it('COMPLETED 不能创建职位', () => {
    expect(canAttachPosition('COMPLETED')).toBe(false)
  })

  it('PAUSED 不能创建职位', () => {
    expect(canAttachPosition('PAUSED')).toBe(false)
  })
})

describe('demand-state-machine: canSubmitForApproval', () => {
  it('DRAFT + NOT_STARTED 审批 → ok', () => {
    expect(canSubmitForApproval('NOT_STARTED', 'DRAFT')).toEqual({ ok: true })
  })

  it('DRAFT + REJECTED 审批 → ok (重发)', () => {
    expect(canSubmitForApproval('REJECTED', 'DRAFT')).toEqual({ ok: true })
  })

  it('DRAFT + CANCELLED 审批 → ok (重发)', () => {
    expect(canSubmitForApproval('CANCELLED', 'DRAFT')).toEqual({ ok: true })
  })

  it('PENDING 审批中不能再次发起', () => {
    const r = canSubmitForApproval('PENDING', 'DRAFT')
    expect(r.ok).toBe(false)
    expect(r.reason).toMatch(/PENDING/)
  })

  it('APPROVED 审批后不能再发起', () => {
    const r = canSubmitForApproval('APPROVED', 'DRAFT')
    expect(r.ok).toBe(false)
  })

  it('IN_PROGRESS 状态不能发起审批 (应保持 DRAFT)', () => {
    const r = canSubmitForApproval('NOT_STARTED', 'IN_PROGRESS')
    expect(r.ok).toBe(false)
    expect(r.reason).toMatch(/IN_PROGRESS/)
  })
})

describe('demand-state-machine: 常量导出', () => {
  it('DEMAND_STATUSES 包含 7 个状态', () => {
    expect(Object.keys(DEMAND_STATUSES)).toHaveLength(7)
    expect(DEMAND_STATUSES.DRAFT).toBe('DRAFT')
    expect(DEMAND_STATUSES.NOT_STARTED).toBe('NOT_STARTED')
    expect(DEMAND_STATUSES.IN_PROGRESS).toBe('IN_PROGRESS')
    expect(DEMAND_STATUSES.COMPLETED).toBe('COMPLETED')
    expect(DEMAND_STATUSES.PAUSED).toBe('PAUSED')
    expect(DEMAND_STATUSES.STOPPED).toBe('STOPPED')
    expect(DEMAND_STATUSES.EXPIRED).toBe('EXPIRED')
  })

  it('APPROVAL_STATUSES 包含 5 个状态', () => {
    expect(Object.keys(APPROVAL_STATUSES)).toHaveLength(5)
    expect(APPROVAL_STATUSES.NOT_STARTED).toBe('NOT_STARTED')
    expect(APPROVAL_STATUSES.PENDING).toBe('PENDING')
    expect(APPROVAL_STATUSES.APPROVED).toBe('APPROVED')
    expect(APPROVAL_STATUSES.REJECTED).toBe('REJECTED')
    expect(APPROVAL_STATUSES.CANCELLED).toBe('CANCELLED')
  })
})
