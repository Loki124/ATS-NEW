/**
 * Request Dedup - 运行时版本 (无类型)
 *
 * 配套 request-dedup.ts, 供 .mjs 测试用
 */

class RequestDedup {
  constructor(options = {}) {
    this.pending = new Map()
    this.options = {
      methods: options.methods || ['GET'],
      ttlMs: options.ttlMs || 1000,
      keyFn: options.keyFn || this.defaultKeyFn.bind(this),
    }
  }

  defaultKeyFn(url, init) {
    const method = (init?.method || 'GET').toUpperCase()
    return `${method}:${url}`
  }

  async fetch(url, init) {
    const method = (init?.method || 'GET').toUpperCase()
    if (!this.options.methods.includes(method)) {
      return fetch(url, init)
    }
    const key = this.options.keyFn(url, init)
    const existing = this.pending.get(key)
    if (existing) {
      return existing.promise
    }
    const promise = fetch(url, init).finally(() => {
      this.pending.delete(key)
    })
    this.pending.set(key, { promise, createdAt: Date.now() })
    return promise
  }

  wrapAxios(fn, key) {
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

  size() {
    return this.pending.size
  }

  clear() {
    this.pending.clear()
  }
}

let defaultInstance = null

function getDefaultDedup() {
  if (!defaultInstance) {
    defaultInstance = new RequestDedup()
  }
  return defaultInstance
}

function createDedupedFetch(options) {
  return new RequestDedup(options)
}

export { RequestDedup, getDefaultDedup, createDedupedFetch }
export default RequestDedup
