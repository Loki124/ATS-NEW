/**
 * debounce.test.ts - vitest unit tests
 *
 * Plan P Task 2 follow-up: converted from the Plan O custom-polyfill
 * runner to real vitest imports, so it works with the new
 * `npm test` (`vitest run`) setup and the `src/**\/*.ts` glob.
 *
 * Covers: debounce (trailing) / debounceLeading / throttle
 *         + cancel() / flush() / pending() methods
 */

import { describe, it, expect, vi } from 'vitest'
import { debounce, debounceLeading, throttle } from '../debounce'

describe('debounce (trailing)', () => {
  it('triggers only after ms of silence', () => {
    vi.useFakeTimers()
    const fn = vi.fn()
    const d = debounce(fn, 100)
    d('a')
    d('b')
    d('c')
    expect(fn).not.toHaveBeenCalled()
    vi.advanceTimersByTime(100)
    expect(fn).toHaveBeenCalledTimes(1)
    expect(fn).toHaveBeenCalledWith('c')
    vi.useRealTimers()
  })

  it('cancel() aborts pending call', () => {
    vi.useFakeTimers()
    const fn = vi.fn()
    const d = debounce(fn, 100)
    d('a')
    d.cancel()
    vi.advanceTimersByTime(200)
    expect(fn).not.toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('flush() triggers pending call immediately', () => {
    vi.useFakeTimers()
    const fn = vi.fn()
    const d = debounce(fn, 100)
    d('a')
    d('b')
    d.flush()
    expect(fn).toHaveBeenCalledTimes(1)
    expect(fn).toHaveBeenCalledWith('b')
    vi.useRealTimers()
  })

  it('pending() returns true while a call is scheduled', () => {
    vi.useFakeTimers()
    const fn = vi.fn()
    const d = debounce(fn, 100)
    expect(d.pending()).toBe(false)
    d('a')
    expect(d.pending()).toBe(true)
    vi.advanceTimersByTime(100)
    expect(d.pending()).toBe(false)
    vi.useRealTimers()
  })
})

describe('debounceLeading', () => {
  it('fires on first call, trailing-fires last args after window', () => {
    vi.useFakeTimers()
    const fn = vi.fn()
    const d = debounceLeading(fn, 100)
    d('a') // fires immediately
    expect(fn).toHaveBeenCalledWith('a')
    d('b') // queued as lastArgs (within window)
    d('c') // queued as lastArgs (within window)
    expect(fn).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(100)
    // trailing fires with last queued args 'c'
    expect(fn).toHaveBeenCalledTimes(2)
    expect(fn).toHaveBeenLastCalledWith('c')
    d('d') // new window, fires immediately
    expect(fn).toHaveBeenCalledTimes(3)
    expect(fn).toHaveBeenLastCalledWith('d')
    vi.useRealTimers()
  })
})

describe('throttle', () => {
  it('fires at most once per ms', () => {
    vi.useFakeTimers()
    const fn = vi.fn()
    const t = throttle(fn, 100)
    t('a')
    vi.advanceTimersByTime(50)
    t('b') // throttled, queued
    expect(fn).toHaveBeenCalledTimes(1)
    expect(fn).toHaveBeenCalledWith('a')
    vi.advanceTimersByTime(50)
    expect(fn).toHaveBeenCalledTimes(2)
    expect(fn).toHaveBeenLastCalledWith('b')
    vi.useRealTimers()
  })
})
