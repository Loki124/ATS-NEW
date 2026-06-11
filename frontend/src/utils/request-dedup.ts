/**
 * Request Dedup - Plan O Task 7
 *
 * 同 URL + method 的请求在 pending 期间共享同一个 Promise
 *   - 避免 React/Vue 组件重复挂载时发多次相同请求
 *   - 提高首屏并发性能
 *
 * 用法:
 *   const dedupedFetch = createDedupedFetch()
 *   dedupedFetch('/api/users?page=1')   // 第一次, 真正发请求
 *   dedupedFetch('/api/users?page=1')   // 第二次, 共享 pending Promise
 *   // ...
 *   dedupedFetch('/api/users?page=1')   // 请求完成后, 新建一个
 */

export interface DedupedFetchOptions {
  /**
   * 哪些 method 去重 (默认 ['GET'])
   *  POST/PUT/DELETE 副作用请求不去重
   */
  methods?: string[]

  /**
   * 多久后清理已完成的请求 (默认 1000ms)
   *   - 太短: 高频去重场景会失效
   *   - 太长: 内存累积
   */
  ttlMs?: number

  /**
   * 自定义 key 生成函数 (默认 URL + method)
   */
  keyFn?: (url: string, init?: RequestInit) => string
}

interface PendingEntry {
  promise: Promise<any>
  createdAt: number
}

export class RequestDedup {
  private pending = new Map<string, PendingEntry>()
  private options: Required<DedupedFetchOptions>

  constructor(options: DedupedFetchOptions = {}) {
    this.options = {
      methods: options.methods || ['GET'],
      ttlMs: options.ttlMs || 1000,
      keyFn: options.keyFn || this.defaultKeyFn,
    }
  }

  defaultKeyFn(url: string, init?: RequestInit): string {
    const method = (init?.method || 'GET').toUpperCase()
    return `${method}:${url}`
  }

  /**
   * 去重 fetch
   */
  async fetch(url: string, init?: RequestInit): Promise<Response> {
    const method = (init?.method || 'GET').toUpperCase()

    // 非去重 method: 直接发请求
    if (!this.options.methods.includes(method)) {
      return fetch(url, init)
    }

    const key = this.options.keyFn(url, init)

    // 命中 pending: 共享 Promise
    const existing = this.pending.get(key)
    if (existing) {
      return existing.promise
    }

    // 新建请求
    const promise = fetch(url, init).finally(() => {
      // 完成后从 pending 移除, 防止内存累积
      this.pending.delete(key)
    })

    this.pending.set(key, { promise, createdAt: Date.now() })
    return promise
  }

  /**
   * 包装 axios 调用
   *   - 用法: dedup.wrapAxios(() => api.get('/users'))
   */
  wrapAxios<T>(fn: () => Promise<T>, key: string): Promise<T> {
    const existing = this.pending.get(key)
    if (existing) {
      return existing.promise
    }
    const promise = fn().finally(() => {
      this.pending.delete(key)
    })
    this.pending.set(key, { promise, createdAt: Date.now() })
    return promise
  }

  /**
   * 获取当前 pending 请求数 (用于调试)
   */
  size(): number {
    return this.pending.size
  }

  /**
   * 清空所有 pending (慎用)
   */
  clear(): void {
    this.pending.clear()
  }
}

let defaultInstance: RequestDedup | null = null

export function getDefaultDedup(): RequestDedup {
  if (!defaultInstance) {
    defaultInstance = new RequestDedup()
  }
  return defaultInstance
}

export function createDedupedFetch(options?: DedupedFetchOptions): RequestDedup {
  return new RequestDedup(options)
}

export default RequestDedup
