import { beforeEach, describe, expect, it, vi } from 'vitest'

// P1-2：request.ts 集中注入 token + X-Recruit-Type，必须随系统切换生效
vi.mock('../../stores/system', () => ({
  useSystemStore: vi.fn(() => ({ current: 'social' })),
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
