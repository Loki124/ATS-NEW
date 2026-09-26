import { describe, it, expect, beforeEach, vi } from 'vitest'

// 固定"本地版本"，避免依赖构建期生成物
vi.mock('@/generated/appVersion', () => ({ APP_VERSION: 'localv1', APP_BUILD_TIME: 't' }))

const LOCAL = 'localv1'
const PROMPTED_KEY = 'ats.promptedAppVersions'
const dialogCalls: any[] = []

/**
 * 用内存版 localStorage 取代 happy-dom 的 localStorage：
 * happy-dom 的 localStorage 在 vitest 跨测试文件时存在状态残留/ clear 不彻底的问题，
 * 会导致本模块的「刷新持久化」用例在隔离跑通过、全量跑偶发失败（时序竞态）。
 * 改为每个用例一块全新内存存储，彻底隔离，行为确定。
 */
const memStore = new Map<string, string>()
const mockLocalStorage = {
  getItem: (k: string) => (memStore.has(k) ? memStore.get(k)! : null),
  setItem: (k: string, v: string) => {
    memStore.set(k, String(v))
  },
  removeItem: (k: string) => {
    memStore.delete(k)
  },
  clear: () => memStore.clear(),
  key: (i: number) => Array.from(memStore.keys())[i] ?? null,
  get length() {
    return memStore.size
  },
}

function stubFetch(version: string | null, opts: { html?: boolean; status?: number } = {}) {
  const { html = false, status = 200 } = opts
  const fn = vi.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    headers: {
      get: (k: string) =>
        k.toLowerCase() === 'content-type' ? (html ? 'text/html' : 'application/json') : null,
    },
    json: async () => ({ version }),
  }))
  ;(globalThis as any).fetch = fn
  return fn
}

async function load() {
  vi.resetModules()
  return await import('@/services/app-version')
}

beforeEach(() => {
  memStore.clear()
  vi.stubGlobal('localStorage', mockLocalStorage)
  dialogCalls.length = 0
  ;(window as any).happyDOM?.setURL?.('http://localhost/settings')
  ;(window as any).$dialog = { info: (o: any) => dialogCalls.push(o) }
  Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true })
})

describe('app-version 升级提示去重', () => {
  it('线上与本地一致 → 不弹', async () => {
    stubFetch(LOCAL)
    const m = await load()
    await m.checkAppVersion()
    expect(dialogCalls).toHaveLength(0)
  })

  it('线上不一致 → 弹一次；重复检测不重复弹（且写入 localStorage 持久化）', async () => {
    stubFetch('remotev2')
    const m = await load()
    await m.checkAppVersion()
    await m.checkAppVersion()
    expect(dialogCalls).toHaveLength(1)
    // 写→读闭环：markPrompted 必须把版本落进 localStorage，下次刷新才不会重弹
    const stored = JSON.parse((globalThis as any).localStorage.getItem(PROMPTED_KEY) || '[]')
    expect(stored).toContain('remotev2')
  })

  it('刷新后仍不重复弹（新模块实例从 localStorage 读出"已提示"集合）', async () => {
    // 模拟"上一次会话已提示过 remotev2"：导入前预置 localStorage
    ;(globalThis as any).localStorage.setItem(PROMPTED_KEY, JSON.stringify(['remotev2']))
    stubFetch('remotev2')
    const m = await load()
    await m.checkAppVersion()
    expect(dialogCalls).toHaveLength(0)
  })

  it('线上版本在多节点间抖动 A/B 不重复弹', async () => {
    stubFetch('verA')
    const m = await load()
    await m.checkAppVersion()
    stubFetch('verB')
    await m.checkAppVersion()
    stubFetch('verA')
    await m.checkAppVersion()
    expect(dialogCalls).toHaveLength(2)
  })

  it('后台标签页不弹且不误标已提示，回到前台后补弹', async () => {
    Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true })
    stubFetch('remotev2')
    const m = await load()
    await m.checkAppVersion()
    expect(dialogCalls).toHaveLength(0)
    // 后台期间未标记，回到前台立即补弹
    Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true })
    await m.checkAppVersion()
    expect(dialogCalls).toHaveLength(1)
  })

  it('登录页不弹', async () => {
    ;(window as any).happyDOM?.setURL?.('http://localhost/login')
    stubFetch('remotev2')
    const m = await load()
    await m.checkAppVersion()
    expect(dialogCalls).toHaveLength(0)
  })

  it('/version.json 回 HTML 时放弃本次检测', async () => {
    stubFetch('remotev2', { html: true })
    const m = await load()
    await m.checkAppVersion()
    expect(dialogCalls).toHaveLength(0)
  })
})
