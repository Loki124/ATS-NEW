/**
 * debounce.test.mjs - 可执行的 Node 单元测试
 *
 * 用法: node frontend/src/utils/__tests__/debounce.test.mjs
 *
 * Plan O: 5+ 测试覆盖 debounce / debounceLeading / throttle
 */

import { debounce, debounceLeading, throttle } from '../debounce.mjs'

let pass = 0
let fail = 0
const failures = []

function describe(name, fn) {
  console.log(`\n${name}`)
  fn()
}

async function it(name, fn) {
  try {
    await fn()
    pass++
    console.log(`  PASS  ${name}`)
  } catch (e) {
    fail++
    const msg = e?.message || String(e)
    failures.push(`${name}: ${msg}`)
    console.log(`  FAIL  ${name}: ${msg}`)
  }
}

const expect = (actual) => ({
  toBe(expected) {
    if (actual !== expected) throw new Error(`expected ${expected}, got ${actual}`)
  },
  toEqual(expected) {
    const a = JSON.stringify(actual)
    const b = JSON.stringify(expected)
    if (a !== b) throw new Error(`expected ${b}, got ${a}`)
  },
  toBeTruthy() {
    if (!actual) throw new Error(`expected truthy, got ${actual}`)
  },
  toBeFalsy() {
    if (actual) throw new Error(`expected falsy, got ${actual}`)
  },
  toBeGreaterThan(n) {
    if (!(actual > n)) throw new Error(`expected > ${n}, got ${actual}`)
  },
})

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

describe('debounce (trailing)', () => {
  it('连续调用, 仅最后一次触发', async () => {
    const calls = []
    const fn = debounce((v) => calls.push(v), 30)
    fn(1); fn(2); fn(3)
    await sleep(80)
    expect(calls).toEqual([3])
  })

  it('cancel 取消待执行调用', async () => {
    const calls = []
    const fn = debounce((v) => calls.push(v), 30)
    fn(1)
    fn.cancel()
    await sleep(80)
    expect(calls).toEqual([])
  })

  it('flush 立即执行待执行调用', () => {
    const calls = []
    const fn = debounce((v) => calls.push(v), 30)
    fn(1); fn(2)
    fn.flush()
    expect(calls).toEqual([2])
  })

  it('pending() 反映定时器状态', () => {
    const fn = debounce(() => {}, 1000)
    expect(fn.pending()).toBe(false)
    fn()
    expect(fn.pending()).toBe(true)
    fn.cancel()
    expect(fn.pending()).toBe(false)
  })

  it('多次 delay 后仍正常触发', async () => {
    const calls = []
    const fn = debounce((v) => calls.push(v), 20)
    fn(1)
    await sleep(40)
    fn(2)
    await sleep(40)
    expect(calls).toEqual([1, 2])
  })
})

describe('debounceLeading', () => {
  it('首次立即触发, 后续被压制', async () => {
    const calls = []
    const fn = debounceLeading((v) => calls.push(v), 30)
    fn(1); fn(2); fn(3)
    await sleep(20)
    expect(calls).toEqual([1])
  })

  it('冷却期结束后再次触发', async () => {
    const calls = []
    const fn = debounceLeading((v) => calls.push(v), 30)
    fn(1)
    await sleep(50)
    fn(2)
    expect(calls).toEqual([1, 2])
  })
})

describe('throttle', () => {
  it('高频调用限制为 1/ms 频率', async () => {
    const calls = []
    const fn = throttle((v) => calls.push(v), 30)
    fn(1); fn(2); fn(3); fn(4)
    await sleep(10)
    expect(calls).toEqual([1])
    await sleep(60)
    expect(calls.length).toBeGreaterThan(1)
  })
})

console.log(`\n${pass} passed, ${fail} failed`)
if (failures.length > 0) {
  failures.forEach((f) => console.log('  - ' + f))
  process.exit(1)
}
