import { describe, it, expect, beforeEach, vi } from 'vitest'

// --- 异步 API mock：拦截 axios.create 返回的实例，避免真实请求 ---
const getMock = vi.fn()
const postMock = vi.fn()
const putMock = vi.fn()
const deleteMock = vi.fn()
vi.mock('axios', () => {
  const instance = {
    get: (...args: any[]) => getMock(...args),
    post: (...args: any[]) => postMock(...args),
    put: (...args: any[]) => putMock(...args),
    delete: (...args: any[]) => deleteMock(...args),
    interceptors: { request: { use: () => {} } },
  }
  return { default: { create: () => instance }, create: () => instance }
})
vi.mock('../../config', () => ({ default: { api: { baseUrl: '/api/v1' } } }))

const {
  listRegistrationForms,
  createRegistrationForm,
  updateRegistrationForm,
  deleteRegistrationForm,
} = await import('../application-form')

function makeForm(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    name: '猎头更新简历登记表',
    formType: 'registration',
    departments: ['dept_1'],
    mode: 'default',
    fields: [],
    orderIndex: 0,
    isActive: true,
    ...overrides,
  }
}

describe('application-form 多表单 CRUD', () => {
  beforeEach(() => {
    getMock.mockReset()
    postMock.mockReset()
    putMock.mockReset()
    deleteMock.mockReset()
  })

  it('listRegistrationForms 解析 data.data 数组', async () => {
    const forms = [makeForm()]
    getMock.mockResolvedValue({ data: { success: true, data: forms } })
    const r = await listRegistrationForms()
    expect(getMock).toHaveBeenCalledWith('/standard-resume/application-form/')
    expect(r).toHaveLength(1)
    expect(r[0].name).toBe('猎头更新简历登记表')
  })

  it('createRegistrationForm POST 并返回完整对象', async () => {
    const payload: Parameters<typeof createRegistrationForm>[0] = {
      name: '新表单',
      formType: 'registration',
      departments: [],
      mode: 'default',
      fields: [],
      isActive: true,
    }
    const created = { id: 2, ...payload, orderIndex: 0 }
    postMock.mockResolvedValue({ data: { success: true, data: created } })
    const r = await createRegistrationForm(payload)
    expect(postMock).toHaveBeenCalledWith('/standard-resume/application-form/', payload)
    expect(r.id).toBe(2)
  })

  it('updateRegistrationForm PUT /:id/ 并返回更新后对象', async () => {
    const payload = { name: '改名后的表单' }
    const updated = makeForm({ id: 3, name: '改名后的表单' })
    putMock.mockResolvedValue({ data: { success: true, data: updated } })
    const r = await updateRegistrationForm(3, payload)
    expect(putMock).toHaveBeenCalledWith('/standard-resume/application-form/3/', payload)
    expect(r.name).toBe('改名后的表单')
  })

  it('deleteRegistrationForm DELETE /:id/', async () => {
    deleteMock.mockResolvedValue({ data: { success: true } })
    await deleteRegistrationForm(4)
    expect(deleteMock).toHaveBeenCalledWith('/standard-resume/application-form/4/')
  })
})
