/**
 * request-dedup.test.mjs - 可执行 Node 单元测试
 *
 * 用法: node frontend/src/utils/__tests__/request-dedup.test.mjs
 */

import { RequestDedup, createDedupedFetch } from '../request-dedup.mjs'

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

describe('RequestDedup', () => {
  it('创建实例', () => {
    const dedup = new RequestDedup()
    expect(dedup.size()).toBe(0)
  })

  it('wrapAxios 同步请求共享 promise', async () => {
    const dedup = new RequestDedup()
    let callCount = 0
    const fn = () => Promise.resolve().then(() => {
      callCount++
      return { data: 'x' }
    })

    const p1 = dedup.wrapAxios(fn, 'GET:/users')
    const p2 = dedup.wrapAxios(fn, 'GET:/users')
    expect(p1).toBe(p2)
    await p1
    expect(callCount).toBe(1)
  })

  it('请求完成后从 pending 移除', async () => {
    const dedup = new RequestDedup()
    const fn = () => Promise.resolve('ok')
    await dedup.wrapAxios(fn, 'k1')
    expect(dedup.size()).toBe(0)
  })

  it('不同 key 独立去重', async () => {
    const dedup = new RequestDedup()
    const fn1 = () => Promise.resolve(1)
    const fn2 = () => Promise.resolve(2)
    const p1 = dedup.wrapAxios(fn1, 'k1')
    const p2 = dedup.wrapAxios(fn2, 'k2')
    expect(p1 !== p2).toBe(true)
    expect(await p1).toBe(1)
    expect(await p2).toBe(2)
  })

  it('错误也能清理 pending', async () => {
    const dedup = new RequestDedup()
    const fn = () => Promise.reject(new Error('boom'))
    try {
      await dedup.wrapAxios(fn, 'k-err')
    } catch {
      // 预期
    }
    expect(dedup.size()).toBe(0)
  })

  it('clear 清空所有', () => {
    const dedup = new RequestDedup()
    dedup.wrapAxios(() => new Promise(() => {}), 'k1')
    expect(dedup.size()).toBe(1)
    dedup.clear()
    expect(dedup.size()).toBe(0)
  })

  it('createDedupedFetch 返回实例', () => {
    const dedup = createDedupedFetch()
    expect(dedup instanceof RequestDedup).toBe(true)
  })

  it('自定义 keyFn 可定制 key', () => {
    let counter = 0
    const dedup = new RequestDedup({
      keyFn: () => `custom-${++counter}`,
    })
    dedup.wrapAxios(() => Promise.resolve(), 'any')
    dedup.wrapAxios(() => Promise.resolve(), 'any')
    // 两次调用, 实际 key 不同 (因为 counter++)
    expect(dedup.size()).toBe(1) // 第一个已完成
  })
})

console.log(`\n${pass} passed, ${fail} failed`)
if (failures.length > 0) {
  failures.forEach((f) => console.log('  - ' + f))
  process.exit(1)
}
