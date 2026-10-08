import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import axios from 'axios'

// P1-2：request.ts 集中注入 token + X-Recruit-Type，必须随系统切换生效
vi.mock('../../stores/system', () => ({
  useSystemStore: vi.fn(() => ({ current: 'social' })),
}))

// 401 刷新重试依赖用户 store（refreshToken / setAccessToken / logout）
const userStoreMock = {
  accessToken: 'OLD',
  refreshToken: 'REFRESH',
  setAccessToken: vi.fn(),
  logout: vi.fn(),
}
vi.mock('../../stores/user', () => ({
  useUserStore: vi.fn(() => userStoreMock),
}))

import { useSystemStore } from '../../stores/system'
import { api, createApi } from '../request'

function runRequestInterceptor(instance: any, config: any) {
  const handler = instance.interceptors.request.handlers[0].fulfilled
  return handler(config)
}

describe('request.ts 拦截器', () => {
  beforeEach(() => {
    localStorage.clear()
    ;(useSystemStore as any).mockImplementation(() => ({ current: 'social' }))
  })

  it('注入 X-Recruit-Type（取自系统 store）', () => {
    ;(useSystemStore as any).mockImplementation(() => ({ current: 'campus' }))
    const out = runRequestInterceptor(createApi(), { headers: {} })
    expect(out.headers['X-Recruit-Type']).toBe('campus')
  })

  it('默认系统为 social 时注入对应值', () => {
    const out = runRequestInterceptor(createApi(), { headers: {} })
    expect(out.headers['X-Recruit-Type']).toBe('social')
  })

  it('优先用 accessToken 注入 Bearer', () => {
    localStorage.setItem('accessToken', 'abc123')
    const out = runRequestInterceptor(createApi(), { headers: {} })
    expect(out.headers.Authorization).toBe('Bearer abc123')
  })

  it('accessToken 缺失时回退 token', () => {
    localStorage.setItem('token', 'xyz789')
    const out = runRequestInterceptor(createApi(), { headers: {} })
    expect(out.headers.Authorization).toBe('Bearer xyz789')
  })

  it('共享单例 api 默认配置与 baseURL 正确', () => {
    expect(api.defaults.timeout).toBe(15000)
    expect(api.defaults.baseURL).toBe('/api/v1')
  })

  it('工厂支持自定义 timeout', () => {
    const inst = createApi({ timeout: 60000 })
    expect(inst.defaults.timeout).toBe(60000)
  })
})

describe('request.ts 401 刷新重试（修复 PATCH 模板报 401）', () => {
  afterEach(() => {
    ;(axios as any).defaults.adapter = undefined as any
  })

  beforeEach(() => {
    localStorage.clear()
    userStoreMock.accessToken = 'OLD'
    userStoreMock.refreshToken = 'REFRESH'
    userStoreMock.setAccessToken.mockClear()
    userStoreMock.logout.mockClear()
  })

  // 模拟 axios 默认 settle：2xx 解析，非 2xx 抛带 .response 的 AxiosError（触发响应错误拦截器）
  function makeAdapter(handler: (cfg: any, mainCallsRef: { n: number }) => { data: any; status: number }) {
    return vi.fn(async (cfg: any) => {
      const out = handler(cfg, { n: 0 })
      const { data, status } = out
      if (status >= 200 && status < 300) {
        return { data, status, statusText: 'OK', headers: {}, config: cfg }
      }
      const err: any = new Error(`Request failed with status code ${status}`)
      err.config = cfg
      err.response = { data, status, statusText: 'Error', headers: {}, config: cfg }
      err.isAxiosError = true
      throw err
    })
  }

  it('401 时刷新 token 并重试原请求（不再直接抛 401）', async () => {
    const inst = createApi()
    const state = { mainCalls: 0 }
    const handler = (cfg: any) => {
      const url: string = cfg.url || ''
      if (url.includes('/auth/refresh/')) return { data: { data: { access: 'NEW' } }, status: 200 }
      if (url.includes('/metrics/templates/')) {
        state.mainCalls += 1
        if (state.mainCalls === 1) return { data: {}, status: 401 }
        return { data: { ok: true }, status: 200 }
      }
      return { data: {}, status: 200 }
    }
    const adapter = makeAdapter(handler)
    inst.defaults.adapter = adapter as any
    ;(axios as any).defaults.adapter = adapter as any

    const res = await inst.get('/metrics/templates/x/')
    expect(res.data.ok).toBe(true)
    expect(state.mainCalls).toBe(2) // 首次 401 + 刷新后重试 200
    expect(
      adapter.mock.calls.filter((c: any) => (c[0].url || '').includes('/auth/refresh/')).length,
    ).toBe(1)
    expect(userStoreMock.setAccessToken).toHaveBeenCalledWith('NEW')
  })

  it('登录 / 刷新请求本身 401 不重试，直接 reject', async () => {
    const inst = createApi()
    const adapter = makeAdapter(() => ({ data: {}, status: 401 }))
    inst.defaults.adapter = adapter as any
    ;(axios as any).defaults.adapter = adapter as any

    await expect(inst.post('/auth/login/', { username: 'a', password: 'b' })).rejects.toBeTruthy()
    const refreshCalls = adapter.mock.calls.filter((c: any) => (c[0].url || '').includes('/auth/refresh/')).length
    expect(refreshCalls).toBe(0)
  })
})
