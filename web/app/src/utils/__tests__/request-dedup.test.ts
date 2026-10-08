/**
 * request-dedup.test.ts - vitest unit tests
 *
 * Plan P Task 2 follow-up: 由 request-dedup.test.mjs 转写而来，
 * 用真实 vitest 的 describe/it/expect 替换原自定义 polyfill，
 * 使其能被 `npm test` (`vitest run`) 的 `src/**\/*.test.ts` glob 收集。
 * 断言与 .mjs 版本保持一致。
 */

import { describe, it, expect } from 'vitest'
import { RequestDedup, createDedupedFetch } from '../request-dedup'

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
