/**
 * Debounce 工具 - Plan O Task 6
 *
 * 用法:
 *   const onInput = debounce((value: string) => search(value), 300)
 *   const onSubmit = debounceLeading((value) => submit(value), 300)
 *
 * 类型:
 *   - debounce: 尾部触发 (停止后等待 ms)
 *   - debounceLeading: 头部触发 (首次立即, 后续忽略到 ms 后)
 *   - throttle: 固定频率 (每 ms 最多一次)
 */

export interface DebouncedFunction<TArgs extends unknown[]> {
  (...args: TArgs): void
  cancel(): void
  flush(): void
  pending(): boolean
}

/**
 * 尾部 debounce: 调用 N 次, 仅在最后一次调用后 ms 触发
 */
export function debounce<TArgs extends unknown[]>(
  fn: (...args: TArgs) => void,
  ms: number,
): DebouncedFunction<TArgs> {
  let timer: ReturnType<typeof setTimeout> | null = null
  let lastArgs: TArgs | null = null

  const wrapped = ((...args: TArgs) => {
    lastArgs = args
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      timer = null
      if (lastArgs) {
        fn(...lastArgs)
        lastArgs = null
      }
    }, ms)
  }) as DebouncedFunction<TArgs>

  wrapped.cancel = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    lastArgs = null
  }

  wrapped.flush = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
      if (lastArgs) {
        fn(...lastArgs)
        lastArgs = null
      }
    }
  }

  wrapped.pending = () => timer !== null

  return wrapped
}

/**
 * 头部 debounce: 首次立即触发, 后续调用在 ms 冷却期内被忽略
 *   适合 "提交按钮" 等场景
 */
export function debounceLeading<TArgs extends unknown[]>(
  fn: (...args: TArgs) => void,
  ms: number,
): DebouncedFunction<TArgs> {
  let cooling = false
  let lastArgs: TArgs | null = null
  let trailingTimer: ReturnType<typeof setTimeout> | null = null

  const wrapped = ((...args: TArgs) => {
    if (!cooling) {
      cooling = true
      fn(...args)
      setTimeout(() => {
        cooling = false
        if (lastArgs && trailingTimer) {
          fn(...lastArgs)
          lastArgs = null
          trailingTimer = null
        }
      }, ms)
    } else {
      lastArgs = args
    }
  }) as DebouncedFunction<TArgs>

  wrapped.cancel = () => {
    cooling = false
    lastArgs = null
    if (trailingTimer) {
      clearTimeout(trailingTimer)
      trailingTimer = null
    }
  }

  wrapped.flush = () => {
    if (lastArgs) {
      fn(...lastArgs)
      lastArgs = null
    }
  }

  wrapped.pending = () => cooling || lastArgs !== null

  return wrapped
}

/**
 * Throttle: 每 ms 最多一次 (固定频率)
 *   适合滚动/resize 等高频事件
 */
export function throttle<TArgs extends unknown[]>(
  fn: (...args: TArgs) => void,
  ms: number,
): DebouncedFunction<TArgs> {
  let lastRun = 0
  let timer: ReturnType<typeof setTimeout> | null = null
  let lastArgs: TArgs | null = null

  const wrapped = ((...args: TArgs) => {
    const now = Date.now()
    const elapsed = now - lastRun
    lastArgs = args
    if (elapsed >= ms) {
      lastRun = now
      fn(...args)
      lastArgs = null
    } else if (!timer) {
      timer = setTimeout(() => {
        lastRun = Date.now()
        timer = null
        if (lastArgs) {
          fn(...lastArgs)
          lastArgs = null
        }
      }, ms - elapsed)
    }
  }) as DebouncedFunction<TArgs>

  wrapped.cancel = () => {
    if (timer) clearTimeout(timer)
    timer = null
    lastArgs = null
  }

  wrapped.flush = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null    }
    if (lastArgs) {
      fn(...lastArgs)
      lastArgs = null
    }
  }

  wrapped.pending = () => timer !== null

  return wrapped
}

export default debounce
