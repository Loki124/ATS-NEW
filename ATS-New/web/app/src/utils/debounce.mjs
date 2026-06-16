/**
 * Debounce 工具 - Plan O Task 6 (运行时版本)
 *
 * 用法:
 *   const onInput = debounce((value) => search(value), 300)
 *   const onSubmit = debounceLeading((value) => submit(value), 300)
 *
 * 类型:
 *   - debounce: 尾部触发 (停止后等待 ms)
 *   - debounceLeading: 头部触发 (首次立即, 后续忽略到 ms 后)
 *   - throttle: 固定频率 (每 ms 最多一次)
 *
 * 注: 这是 debounce.ts 的运行时版本, 去掉类型注解供测试
 */

function debounce(fn, ms) {
  let timer = null
  let lastArgs = null

  const wrapped = function (...args) {
    lastArgs = args
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      timer = null
      if (lastArgs) {
        fn(...lastArgs)
        lastArgs = null
      }
    }, ms)
  }

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
    }
    if (lastArgs) {
      fn(...lastArgs)
      lastArgs = null
    }
  }

  wrapped.pending = () => timer !== null

  return wrapped
}

function debounceLeading(fn, ms) {
  let cooling = false
  let lastArgs = null
  let trailingTimer = null

  const wrapped = function (...args) {
    if (!cooling) {
      cooling = true
      fn(...args)
      trailingTimer = setTimeout(() => {
        cooling = false
        trailingTimer = null
        if (lastArgs) {
          fn(...lastArgs)
          lastArgs = null
        }
      }, ms)
    } else {
      lastArgs = args
    }
  }

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

function throttle(fn, ms) {
  let lastRun = 0
  let timer = null
  let lastArgs = null

  const wrapped = function (...args) {
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
  }

  wrapped.cancel = () => {
    if (timer) clearTimeout(timer)
    timer = null
    lastArgs = null
  }

  wrapped.flush = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    if (lastArgs) {
      fn(...lastArgs)
      lastArgs = null
    }
  }

  wrapped.pending = () => timer !== null

  return wrapped
}

export { debounce, debounceLeading, throttle }
export default debounce
