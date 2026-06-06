/**
 * Offer 状态机测试 - PRD G23
 */

import { jest } from '@jest/globals'
import {
  OFFER_STATUSES,
  canTransitionOffer,
  isTerminalOffer,
  canSendOffer,
  canEditOffer,
  canSubmitOfferForApproval,
} from '../offer-state-machine.service.js'

describe('offer-state-machine: 9 状态', () => {
  it('包含全部 9 个状态', () => {
    expect(Object.keys(OFFER_STATUSES)).toHaveLength(9)
    expect(OFFER_STATUSES.NOT_CREATED).toBe('NOT_CREATED')
    expect(OFFER_STATUSES.DRAFT).toBe('DRAFT')
    expect(OFFER_STATUSES.PENDING_APPROVAL).toBe('PENDING_APPROVAL')
    expect(OFFER_STATUSES.APPROVED).toBe('APPROVED')
    expect(OFFER_STATUSES.SENT).toBe('SENT')
    expect(OFFER_STATUSES.ACCEPTED).toBe('ACCEPTED')
    expect(OFFER_STATUSES.REJECTED).toBe('REJECTED')
    expect(OFFER_STATUSES.WITHDRAWN).toBe('WITHDRAWN')
    expect(OFFER_STATUSES.EXPIRED).toBe('EXPIRED')
  })
})

describe('offer-state-machine: canTransitionOffer', () => {
  it('NOT_CREATED → DRAFT 合法', () => {
    expect(canTransitionOffer('NOT_CREATED', 'DRAFT')).toBe(true)
  })
  it('DRAFT → PENDING_APPROVAL 合法', () => {
    expect(canTransitionOffer('DRAFT', 'PENDING_APPROVAL')).toBe(true)
  })
  it('PENDING_APPROVAL → APPROVED 合法', () => {
    expect(canTransitionOffer('PENDING_APPROVAL', 'APPROVED')).toBe(true)
  })
  it('PENDING_APPROVAL → WITHDRAWN 合法 (撤销)', () => {
    expect(canTransitionOffer('PENDING_APPROVAL', 'WITHDRAWN')).toBe(true)
  })
  it('APPROVED → SENT 合法', () => {
    expect(canTransitionOffer('APPROVED', 'SENT')).toBe(true)
  })
  it('SENT → ACCEPTED 合法', () => {
    expect(canTransitionOffer('SENT', 'ACCEPTED')).toBe(true)
  })
  it('SENT → REJECTED 合法', () => {
    expect(canTransitionOffer('SENT', 'REJECTED')).toBe(true)
  })
  it('SENT → EXPIRED 合法', () => {
    expect(canTransitionOffer('SENT', 'EXPIRED')).toBe(true)
  })
  it('REJECTED → DRAFT 合法 (重新编辑)', () => {
    expect(canTransitionOffer('REJECTED', 'DRAFT')).toBe(true)
  })
  it('EXPIRED → DRAFT 合法 (重新发送)', () => {
    expect(canTransitionOffer('EXPIRED', 'DRAFT')).toBe(true)
  })
  it('DRAFT → SENT 非法 (必须先 PENDING_APPROVAL)', () => {
    expect(canTransitionOffer('DRAFT', 'SENT')).toBe(false)
  })
  it('NOT_CREATED → SENT 非法 (必须 DRAFT → 审批 → 发送)', () => {
    expect(canTransitionOffer('NOT_CREATED', 'SENT')).toBe(false)
  })
  it('APPROVED → DRAFT 非法', () => {
    expect(canTransitionOffer('APPROVED', 'DRAFT')).toBe(false)
  })
  it('WITHDRAWN 是终态,不能转任何状态', () => {
    expect(canTransitionOffer('WITHDRAWN', 'DRAFT')).toBe(false)
    expect(canTransitionOffer('WITHDRAWN', 'SENT')).toBe(false)
  })
  it('ACCEPTED 不在本机,不能转任何状态', () => {
    expect(canTransitionOffer('ACCEPTED', 'DRAFT')).toBe(false)
  })
  it('未知状态 → false', () => {
    expect(canTransitionOffer('UNKNOWN', 'DRAFT')).toBe(false)
  })
})

describe('offer-state-machine: isTerminalOffer', () => {
  it('WITHDRAWN 是终态', () => {
    expect(isTerminalOffer('WITHDRAWN')).toBe(true)
  })
  it('ACCEPTED 是终态 (转 G28)', () => {
    expect(isTerminalOffer('ACCEPTED')).toBe(true)
  })
  it('DRAFT 不是终态', () => {
    expect(isTerminalOffer('DRAFT')).toBe(false)
  })
  it('SENT 不是终态', () => {
    expect(isTerminalOffer('SENT')).toBe(false)
  })
})

describe('offer-state-machine: canSendOffer', () => {
  it('APPROVED 状态可发送', () => {
    expect(canSendOffer('APPROVED')).toBe(true)
  })
  it('DRAFT 状态不可发送', () => {
    expect(canSendOffer('DRAFT')).toBe(false)
  })
  it('PENDING_APPROVAL 不可发送', () => {
    expect(canSendOffer('PENDING_APPROVAL')).toBe(false)
  })
  it('SENT 不可再次发送', () => {
    expect(canSendOffer('SENT')).toBe(false)
  })
})

describe('offer-state-machine: canEditOffer', () => {
  it('NOT_CREATED / DRAFT / REJECTED / EXPIRED 可编辑', () => {
    expect(canEditOffer('NOT_CREATED')).toBe(true)
    expect(canEditOffer('DRAFT')).toBe(true)
    expect(canEditOffer('REJECTED')).toBe(true)
    expect(canEditOffer('EXPIRED')).toBe(true)
  })
  it('PENDING_APPROVAL / APPROVED / SENT / ACCEPTED / WITHDRAWN 不可编辑', () => {
    expect(canEditOffer('PENDING_APPROVAL')).toBe(false)
    expect(canEditOffer('APPROVED')).toBe(false)
    expect(canEditOffer('SENT')).toBe(false)
    expect(canEditOffer('ACCEPTED')).toBe(false)
    expect(canEditOffer('WITHDRAWN')).toBe(false)
  })
})

describe('offer-state-machine: canSubmitOfferForApproval', () => {
  it('DRAFT 可提交审批', () => {
    expect(canSubmitOfferForApproval('DRAFT')).toBe(true)
  })
  it('REJECTED 可重新提交审批', () => {
    expect(canSubmitOfferForApproval('REJECTED')).toBe(true)
  })
  it('PENDING_APPROVAL 不可再次提交', () => {
    expect(canSubmitOfferForApproval('PENDING_APPROVAL')).toBe(false)
  })
  it('APPROVED 不可再提交', () => {
    expect(canSubmitOfferForApproval('APPROVED')).toBe(false)
  })
})
