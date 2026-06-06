/**
 * 待入职状态机测试 - PRD G28
 */

import { jest } from '@jest/globals'
import {
  ONBOARDING_STATUSES,
  canTransitionOnboarding,
  isTerminalOnboarding,
  isInProgress,
  canSyncToPeople,
} from '../onboarding-state-machine.service.js'

describe('onboarding-state-machine: 8 状态', () => {
  it('包含 8 状态', () => {
    expect(Object.keys(ONBOARDING_STATUSES)).toHaveLength(8)
  })
})

describe('onboarding-state-machine: canTransitionOnboarding', () => {
  it('NOT_STARTED → PENDING_CONFIRM 合法', () => {
    expect(canTransitionOnboarding('NOT_STARTED', 'PENDING_CONFIRM')).toBe(true)
  })
  it('PENDING_CONFIRM → CONFIRMED 合法', () => {
    expect(canTransitionOnboarding('PENDING_CONFIRM', 'CONFIRMED')).toBe(true)
  })
  it('CONFIRMED → PENDING_ONBOARD 合法', () => {
    expect(canTransitionOnboarding('CONFIRMED', 'PENDING_ONBOARD')).toBe(true)
  })
  it('PENDING_ONBOARD → ONBOARDING 合法 (到入职日)', () => {
    expect(canTransitionOnboarding('PENDING_ONBOARD', 'ONBOARDING')).toBe(true)
  })
  it('ONBOARDING → ONBOARDED 合法 (完成)', () => {
    expect(canTransitionOnboarding('ONBOARDING', 'ONBOARDED')).toBe(true)
  })
  it('PENDING_CONFIRM → PENDING_REJECT 合法 (拒入职)', () => {
    expect(canTransitionOnboarding('PENDING_CONFIRM', 'PENDING_REJECT')).toBe(true)
  })
  it('PENDING_REJECT → CONFIRMED 合法 (可重确认)', () => {
    expect(canTransitionOnboarding('PENDING_REJECT', 'CONFIRMED')).toBe(true)
  })
  it('ONBOARDED 是终态', () => {
    expect(isTerminalOnboarding('ONBOARDED')).toBe(true)
    expect(canTransitionOnboarding('ONBOARDED', 'CANCELLED')).toBe(false)
  })
  it('CANCELLED 是终态', () => {
    expect(isTerminalOnboarding('CANCELLED')).toBe(true)
  })
  it('NOT_STARTED → ONBOARDED 非法 (不能跳过)', () => {
    expect(canTransitionOnboarding('NOT_STARTED', 'ONBOARDED')).toBe(false)
  })
  it('ONBOARDED → ONBOARDING 非法', () => {
    expect(canTransitionOnboarding('ONBOARDED', 'ONBOARDING')).toBe(false)
  })
  it('任何状态 → CANCELLED 合法 (HR 强制取消)', () => {
    for (const s of Object.values(ONBOARDING_STATUSES)) {
      if (s !== 'ONBOARDED' && s !== 'CANCELLED') {
        expect(canTransitionOnboarding(s, 'CANCELLED')).toBe(true)
      }
    }
  })
})

describe('onboarding-state-machine: isInProgress / canSyncToPeople', () => {
  it('isInProgress 包含 4 个办理中状态', () => {
    expect(isInProgress('PENDING_CONFIRM')).toBe(true)
    expect(isInProgress('CONFIRMED')).toBe(true)
    expect(isInProgress('PENDING_ONBOARD')).toBe(true)
    expect(isInProgress('ONBOARDING')).toBe(true)
  })
  it('isInProgress 终态/初始态都 false', () => {
    expect(isInProgress('NOT_STARTED')).toBe(false)
    expect(isInProgress('ONBOARDED')).toBe(false)
    expect(isInProgress('CANCELLED')).toBe(false)
  })
  it('canSyncToPeople 只 ONBOARDED 可同步摩卡', () => {
    expect(canSyncToPeople('ONBOARDED')).toBe(true)
    expect(canSyncToPeople('ONBOARDING')).toBe(false)
    expect(canSyncToPeople('CONFIRMED')).toBe(false)
  })
})
