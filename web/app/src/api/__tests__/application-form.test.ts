import { describe, it, expect, beforeEach, vi } from 'vitest'
import type { FieldDefinition, FieldType, FieldOption } from '../dynamic-field'

// --- 异步 API mock：拦截 axios.create 返回的实例，避免真实请求 ---
const getMock = vi.fn()
const putMock = vi.fn()
vi.mock('axios', () => {
  const instance = {
    get: (...args: any[]) => getMock(...args),
    put: (...args: any[]) => putMock(...args),
    interceptors: { request: { use: () => {} } },
  }
  return { default: { create: () => instance }, create: () => instance }
})
vi.mock('../../config', () => ({ default: { api: { baseUrl: '/api/v1' } } }))

const {
  defaultConfig,
  fetchConfig,
  saveConfig,
  resetConfig,
  mergeFields,
  selectEnabledFields,
  APPLICATION_FORM_API,
} = await import('../application-form')
import type { ApplicationFormConfig } from '../application-form'

function makeField(opts: {
  fieldKey: string
  label?: string
  fieldType?: FieldType
  isRequired?: boolean
  isVisible?: boolean
  orderIndex?: number
  groupName?: string | null
  options?: FieldOption[]
}): FieldDefinition {
  return {
    id: opts.fieldKey,
    resource: 'Candidate',
    fieldKey: opts.fieldKey,
    label: opts.label ?? opts.fieldKey,
    fieldType: opts.fieldType ?? 'TEXT',
    isRequired: opts.isRequired ?? false,
    isVisible: opts.isVisible ?? true,
    orderIndex: opts.orderIndex ?? 0,
    groupName: opts.groupName ?? null,
    options: opts.options,
  } as FieldDefinition
}

describe('application-form config (后端持久化)', () => {
  beforeEach(() => {
    getMock.mockReset()
    putMock.mockReset()
  })

  it('defaultConfig 返回空结构', () => {
    const c = defaultConfig()
    expect(c.fields).toEqual([])
    expect(c.requiredStages).toEqual([])
  })

  it('mergeFields：缺失配置项时回退到字段默认值', () => {
    const fields = [
      makeField({ fieldKey: 'name', isVisible: true, isRequired: true, orderIndex: 2 }),
      makeField({ fieldKey: 'phone', isVisible: false, isRequired: false, orderIndex: 1 }),
    ]
    const merged = mergeFields(fields, defaultConfig())
    expect(merged.map((m) => m.field.fieldKey)).toEqual(['phone', 'name'])
    expect(merged[0].enabled).toBe(false)
    expect(merged[0].required).toBe(false)
    expect(merged[1].enabled).toBe(true)
    expect(merged[1].required).toBe(true)
  })

  it('mergeFields：配置项覆盖字段默认值', () => {
    const fields = [makeField({ fieldKey: 'name', isVisible: true, isRequired: true })]
    const cfg: ApplicationFormConfig = {
      fields: [{ fieldKey: 'name', enabled: false, required: false }],
      requiredStages: [],
    }
    const merged = mergeFields(fields, cfg)
    expect(merged[0].enabled).toBe(false)
    expect(merged[0].required).toBe(false)
  })

  it('selectEnabledFields：仅返回 enabled', () => {
    const fields = [makeField({ fieldKey: 'a' }), makeField({ fieldKey: 'b', isVisible: false })]
    const merged = mergeFields(fields, defaultConfig())
    expect(selectEnabledFields(merged).map((m) => m.field.fieldKey)).toEqual(['a'])
  })

  it('fetchConfig 解析 data.data', async () => {
    getMock.mockResolvedValue({
      data: { data: { fields: [{ fieldKey: 'name', enabled: true, required: true }], requiredStages: [] } },
    })
    const c = await fetchConfig()
    expect(getMock).toHaveBeenCalledWith(APPLICATION_FORM_API)
    expect(c.fields).toHaveLength(1)
  })

  it('fetchConfig 空响应回退默认结构', async () => {
    getMock.mockResolvedValue({ data: {} })
    const c = await fetchConfig()
    expect(c).toEqual(defaultConfig())
  })

  it('saveConfig PUT 整份配置', async () => {
    const cfg: ApplicationFormConfig = {
      fields: [{ fieldKey: 'a', enabled: true, required: false }],
      requiredStages: [],
    }
    putMock.mockResolvedValue({ data: { data: cfg } })
    const r = await saveConfig(cfg)
    expect(putMock).toHaveBeenCalledWith(APPLICATION_FORM_API, cfg)
    expect(r).toEqual(cfg)
  })

  it('resetConfig 清空并落库默认', async () => {
    putMock.mockResolvedValue({ data: { data: defaultConfig() } })
    const r = await resetConfig()
    expect(putMock).toHaveBeenCalledWith(APPLICATION_FORM_API, defaultConfig())
    expect(r).toEqual(defaultConfig())
  })
})
