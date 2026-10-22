/**
 * 校招生管理 · 示例数据开关回归测试（2026-10-21）
 *
 * 锁住「真实优先、示例兜底」的核心约定：
 * - auto：真实有数据 → 真实；真实为空 → 示例（并标记 isMock）；
 * - on：强制示例；off：强制真实，**任何情况下都不兜底**；
 * - 模式跨页共享（模块级单例），并持久化到 localStorage；
 * - localStorage 不可用时（测试环境 happy-dom 未实现 Storage 方法）不抛错。
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useCampusMock } from '../useCampusMock'

/**
 * 本仓测试环境的 globalThis.localStorage 是个**没有 Storage 方法**的普通对象
 * （happy-dom 未实现），直接调用 getItem/setItem/clear 会抛 TypeError。
 * 这里装一个完整桩，既能验证持久化，也能验证「存储不可用时静默降级」。
 */
const store: Record<string, string> = {}
const storageStub = {
  getItem: (k: string) => (k in store ? store[k] : null),
  setItem: (k: string, v: string) => {
    store[k] = String(v)
  },
  removeItem: (k: string) => {
    delete store[k]
  },
  clear: () => {
    for (const k of Object.keys(store)) delete store[k]
  },
  key: (i: number) => Object.keys(store)[i] ?? null,
  get length() {
    return Object.keys(store).length
  },
}
;(globalThis as any).localStorage = storageStub

const REAL = [{ id: 'r1' }]
const MOCK = [{ id: 'MOCK_1' }]

describe('useCampusMock.pick', () => {
  beforeEach(() => {
    storageStub.clear()
    useCampusMock().setMode('auto')
  })
  afterEach(() => {
    storageStub.clear()
    useCampusMock().setMode('auto')
  })

  it('auto：真实数据非空 → 用真实数据，且不标记为示例', () => {
    const { pick, isMock } = useCampusMock()
    expect(pick(REAL, MOCK)).toBe(REAL)
    expect(isMock.value).toBe(false)
  })

  it('auto：真实数据为空 → 用示例数据兜底，并标记为示例', () => {
    const { pick, isMock } = useCampusMock()
    expect(pick([], MOCK)).toBe(MOCK)
    expect(isMock.value).toBe(true)
  })

  it('on：强制用示例数据（即使真实数据有内容）', () => {
    const { pick, isMock, isMockOnly } = useCampusMock()
    useCampusMock().setMode('on')
    expect(pick(REAL, MOCK)).toBe(MOCK)
    expect(isMock.value).toBe(true)
    expect(isMockOnly.value).toBe(true)
  })

  it('off：强制用真实数据，即使真实数据为空也不兜底', () => {
    const { pick, isMock, isMockOnly } = useCampusMock()
    useCampusMock().setMode('off')
    expect(pick([], MOCK)).toEqual([])
    expect(isMock.value).toBe(false)
    expect(isMockOnly.value).toBe(false)
  })

  it('模式持久化到 localStorage（跨页共享）', () => {
    useCampusMock().setMode('on')
    expect(storageStub.getItem('campus-mock-mode')).toBe('on')
  })

  it('模式是跨实例共享的（一个页面切换，其他页面同步）', () => {
    const a = useCampusMock()
    const b = useCampusMock()
    a.setMode('on')
    expect(b.mode.value).toBe('on')
  })

  it('localStorage 不可用时不抛错（存储失败静默降级）', () => {
    const original = (globalThis as any).localStorage
    ;(globalThis as any).localStorage = {}
    try {
      expect(() => useCampusMock().setMode('on')).not.toThrow()
    } finally {
      ;(globalThis as any).localStorage = original
    }
  })
})

describe('useCampusMock.pickBy（聚合类接口）', () => {
  beforeEach(() => {
    storageStub.clear()
    useCampusMock().setMode('auto')
  })

  it('由调用方判定「有无真实数据」：无 → 示例，有 → 真实', () => {
    const { pickBy, isMock } = useCampusMock()
    const real = { grandTotal: 0 }
    const mock = { grandTotal: 42 }
    expect(pickBy(false, real, mock)).toBe(mock)
    expect(isMock.value).toBe(true)
    expect(pickBy(true, real, mock)).toBe(real)
    expect(isMock.value).toBe(false)
  })

  it('on/off 模式优先于「有无真实数据」判定', () => {
    const { pickBy, isMock } = useCampusMock()
    const real = { grandTotal: 1 }
    const mock = { grandTotal: 42 }
    useCampusMock().setMode('on')
    expect(pickBy(true, real, mock)).toBe(mock)
    expect(isMock.value).toBe(true)
    useCampusMock().setMode('off')
    expect(pickBy(false, real, mock)).toBe(real)
    expect(isMock.value).toBe(false)
  })
})
