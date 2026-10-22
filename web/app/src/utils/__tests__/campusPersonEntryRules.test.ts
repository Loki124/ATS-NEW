/**
 * 校招生档案 · 工号 / 入职日期 / 预计入职日期 口径回归测试（2026-10-21 兵哥指令）
 *
 * 锁住前端侧的三条规则（与后端 `apps/campus_control/serializers.py` 的
 * `PersonSerializer.validate` 一一对应）：
 *
 * 1. 工号 = 8 位纯数字；
 * 2. 待入职：有预计入职日期；无工号、无实际入职日期；
 * 3. 在职 / 离职：有工号、有实际入职日期。
 *
 * ⚠️ 本仓的口径**双端各一份**（前端 utils/campus.ts、后端 campus_control/constants.py），
 *    改动任一侧都要同步另一侧，否则会出现「前端能填、后端 400」或反之。
 */
import { describe, it, expect } from 'vitest'
import {
  EMPLOYEE_ID_PATTERN,
  PENDING_STATUSES,
  isPendingStatus,
  validatePersonEntryFields,
} from '../campus'

describe('isPendingStatus', () => {
  it('待入职判定为 true', () => {
    expect(isPendingStatus('待入职')).toBe(true)
    expect(PENDING_STATUSES).toContain('待入职')
  })

  it('在职 / 离职判定为 false', () => {
    expect(isPendingStatus('在职')).toBe(false)
    expect(isPendingStatus('离职')).toBe(false)
  })

  it('旧状态（在途Offer / 在途待入职 / 候选池）已下线，不再是待入职', () => {
    // 2026-10-21 兵哥口径：三态收敛为 在职 / 待入职 / 离职，旧三态合并为「待入职」
    for (const s of ['在途Offer', '在途待入职', '候选池']) {
      expect(isPendingStatus(s)).toBe(false)
      expect(PENDING_STATUSES).not.toContain(s)
    }
  })

  it('空状态按「已入职」处理（不误清字段）', () => {
    expect(isPendingStatus('')).toBe(false)
    expect(isPendingStatus(null)).toBe(false)
    expect(isPendingStatus(undefined)).toBe(false)
  })
})

describe('工号格式', () => {
  it('8 位纯数字通过', () => {
    expect(EMPLOYEE_ID_PATTERN.test('25080001')).toBe(true)
    expect(EMPLOYEE_ID_PATTERN.test('00000000')).toBe(true)
  })

  it('位数不足 / 超位 / 含非数字一律不通过', () => {
    expect(EMPLOYEE_ID_PATTERN.test('2508001')).toBe(false)
    expect(EMPLOYEE_ID_PATTERN.test('250800001')).toBe(false)
    expect(EMPLOYEE_ID_PATTERN.test('CS2026001')).toBe(false)
    expect(EMPLOYEE_ID_PATTERN.test('2508000 ')).toBe(false)
    expect(EMPLOYEE_ID_PATTERN.test('')).toBe(false)
  })
})

describe('validatePersonEntryFields', () => {
  it('待入职：有预计入职日期即通过（工号/入职日期由调用方清空，不报错）', () => {
    expect(
      validatePersonEntryFields({
        status: '待入职',
        employeeId: '25080001',
        actualEntryDate: '2026-08-01',
        expectedEntryDate: '2026-08-15',
      }),
    ).toBeNull()
  })

  it('待入职：缺预计入职日期 → 报错', () => {
    expect(
      validatePersonEntryFields({
        status: '待入职',
        employeeId: '',
        actualEntryDate: '',
        expectedEntryDate: '',
      }),
    ).toBe('待入职人员须填写预计入职日期')
  })

  it('在职 / 离职：缺工号 → 报错', () => {
    for (const status of ['在职', '离职']) {
      expect(
        validatePersonEntryFields({
          status,
          employeeId: '',
          expectedEntryDate: '2026-08-01',
          actualEntryDate: '2026-08-04',
        }),
      ).toBe('在职 / 离职人员须填写工号')
    }
  })

  it('在职 / 离职：工号非 8 位纯数字 → 报错', () => {
    expect(
      validatePersonEntryFields({
        status: '在职',
        employeeId: '2508',
        expectedEntryDate: '2026-08-01',
        actualEntryDate: '2026-08-04',
      }),
    ).toBe('工号须为 8 位纯数字')
    expect(
      validatePersonEntryFields({
        status: '在职',
        employeeId: 'CS2026001',
        expectedEntryDate: '2026-08-01',
        actualEntryDate: '2026-08-04',
      }),
    ).toBe('工号须为 8 位纯数字')
  })

  it('在职 / 离职：缺实际入职日期 → 报错', () => {
    expect(
      validatePersonEntryFields({
        status: '在职',
        employeeId: '25080001',
        expectedEntryDate: '2026-08-01',
        actualEntryDate: '',
      }),
    ).toBe('在职 / 离职人员须填写实际入职日期')
  })

  it('在职 / 离职：三字段齐全 → 通过（预计入职日期可缺，不阻断存量）', () => {
    expect(
      validatePersonEntryFields({
        status: '在职',
        employeeId: '25080001',
        expectedEntryDate: '',
        actualEntryDate: '2026-08-04',
      }),
    ).toBeNull()
  })
})
