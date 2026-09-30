import { describe, it, expect, beforeEach, vi } from 'vitest'

// --- 异步 API mock：拦截 axios.create 返回的实例，避免真实请求 ---
const getMock = vi.fn()
const putMock = vi.fn()
vi.mock('axios', () => {
  const instance = {
    get: (...args: any[]) => getMock(...args),
    put: (...args: any[]) => putMock(...args),
    // request.ts 的 createApi() 同时注册 request/response 两个拦截器（P1-2 收敛后）
    interceptors: { request: { use: () => {} }, response: { use: () => {} } },
  }
  return { default: { create: () => instance }, create: () => instance }
})
vi.mock('../../config', () => ({ default: { api: { baseUrl: '/api/v1' } } }))

const { getResumeFields, putResumeFields } = await import('../candidate-resume-fields')

describe('candidate-resume-fields API', () => {
  beforeEach(() => {
    getMock.mockReset()
    putMock.mockReset()
  })

  it('getResumeFields: 调用正确端点并返回 data.data 映射', async () => {
    getMock.mockResolvedValue({ data: { success: true, data: { School: '清华大学', Major: '计算机' } } })
    const r = await getResumeFields('c1')
    expect(getMock).toHaveBeenCalledWith('/candidates/c1/resume-fields/')
    expect(r).toEqual({ School: '清华大学', Major: '计算机' })
  })

  it('getResumeFields: 容错 - 缺失 data 时返回空对象', async () => {
    getMock.mockResolvedValue({ data: {} })
    expect(await getResumeFields('c1')).toEqual({})
  })

  it('putResumeFields: 发送 { values } 负载并返回保存结果', async () => {
    putMock.mockResolvedValue({ data: { success: true, data: { Major: 'CS' } } })
    const r = await putResumeFields('c1', { Major: 'CS', School: '清华' })
    expect(putMock).toHaveBeenCalledWith('/candidates/c1/resume-fields/', {
      values: { Major: 'CS', School: '清华' },
    })
    expect(r).toEqual({ Major: 'CS' })
  })

  it('putResumeFields: 容错 - 缺失 data 时返回空对象', async () => {
    putMock.mockResolvedValue({ data: {} })
    expect(await putResumeFields('c1', { A: 1 })).toEqual({})
  })
})
