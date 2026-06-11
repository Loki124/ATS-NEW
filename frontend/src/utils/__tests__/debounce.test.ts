/**
 * debounce.test.ts - 自包含测试
 *
 * 用法: npx tsx frontend/src/utils/__tests__/debounce.test.ts
 * 或: node --import tsx frontend/src/utils/__tests__/debounce.test.ts
 *
 * 简化的 test runner: 不依赖 vitest/jest
 *   - describe(name, fn) -> 嵌套
 *   - it(name, fn) -> 测试用例
 *   - expect(actual).toBe(expected) 等
 */

import { debounce, debounceLeading, throttle } from '../debounce'

// 极简 test runner
let pass = 0
let fail = 0
const failures: string[] = []

function describe(_name: string, fn: () => void) { fn() }

async function it(name: string, fn: () => void | Promise<void>) {
  try {
    await fn()
    pass++
    console.log(`  PASS  ${name}`)
  } catch (e: any) {
    fail++
    failures.push(`${name}: ${e?.message || e}`)
    console.log(`  FAIL  ${name}: ${e?.message || e}`)
  }
}

const expect = (actual: any) => ({
  toBe(expected: any) {
    if (actual !== expected) throw new Error(`expected ${expected}, got ${actual}`)
  },
  toEqual(expected: any) {
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {
      throw new Error(`expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`)
    }
  },
  toBeTruthy() {
    if (!actual) throw new Error(`expected truthy, got ${actual}`)
  },
  toBeFalsy() {
    if (actual) throw new Error(`expected falsy, got ${actual}`)
  },
  toBeGreaterThan(n: number) {
    if (!(actual > n)) throw new Error(`expected > ${n}, got ${actual}`)
  },
  toHaveBeenCalledTimes(n: number) {
    if (actual.calls !== n) throw new Error(`expected ${n} calls, got ${actual.calls}`)
  },
})

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

console.log('debounce tests')

describe('debounce (trailing)', () => {
  it('300ms 内连续调用, 仅最后一次触发', async () => {
    const calls: number[] = []
    const fn = debounce((v: number) => calls.push(v), 50)
    fn(1); fn(2); fn(3)
    await sleep(100)
    expect(calls).toEqual([3])
  })

  it('调用后立即 cancel, 不触发', async () => {
    const calls: number[] = []
    const fn = debounce((v: number) => calls.push(v), 50)
    fn(1)
    fn.cancel()
    await sleep(100)
    expect(calls).toEqual([])
  })

  it('flush 立即触发待执行调用', () => {
    const calls: number[] = []
    const fn = debounce((v: number) => calls.push(v), 50)
    fn(1); fn(2)
    fn.flush()
    expect(calls).toEqual([2])
  })

  it('pending() 返回 true 当有定时器', () => {
    const fn = debounce(() => {}, 1000)
    expect(fn.pending()).toBeFalsy()
    fn()
    expect(fn.pending()).toBeTruthy()
    fn.cancel()
  })
})

describe('debounceLeading', () => {
  it('首次立即触发, 后续被压制', async () => {
    const calls: number[] = []
    const fn = debounceLeading((v: number) => calls.push(v), 50)
    fn(1); fn(2); fn(3)
    await sleep(20)
    expect(calls).toEqual([1])
  })

  it('冷却期结束后再次触发', async () => {
    const calls: number[] = []
    const fn = debounceLeading((v: number) => calls.push(v), 30)
    fn(1)
    await sleep(50)
    fn(2)
    expect(calls).toEqual([1, 2])
  })
})

describe('throttle', () => {
  it('高频调用限制为 1/ms 频率', async () => {
    const calls: number[] = []
    const fn = throttle((v: number) => calls.push(v), 30)
    fn(1); fn(2); fn(3)
    await sleep(10)
    expect(calls).toEqual([1]) // 第一次立即触发
    await sleep(50)
    expect(calls.length).toBeGreaterThan(1) // 后续触发
  })
})

console.log(`\n${pass} passed, ${fail} failed`)
if (failures.length > 0) {
  failures.forEach((f) => console.log('  - ' + f))
  process.exit(1)
}
