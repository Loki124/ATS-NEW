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
  groupFieldsByModule,
  UNGROUPED_MODULE_CODE,
  STANDARD_RESUME_STAGES,
  STANDARD_RESUME_API,
} = await import('../standard-resume')
import type { StandardResumeConfig, ModuleGroup, MergedResumeField } from '../standard-resume'

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

describe('standard-resume config (后端持久化)', () => {
  beforeEach(() => {
    getMock.mockReset()
    putMock.mockReset()
  })

  // ---- 纯函数 ----
  it('hardcoded 必填阶段 = 8 个', () => {
    expect(STANDARD_RESUME_STAGES).toHaveLength(8)
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
    expect(merged.map((m) => m.field.fieldKey)).toEqual(['phone', 'name']) // 按 orderIndex 升序
    expect(merged[0].enabled).toBe(false)
    expect(merged[0].required).toBe(false)
    expect(merged[1].enabled).toBe(true)
    expect(merged[1].required).toBe(true)
  })

  it('mergeFields：配置项覆盖字段默认值', () => {
    const fields = [makeField({ fieldKey: 'name', isVisible: true, isRequired: true })]
    const cfg: StandardResumeConfig = {
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
    const enabled = selectEnabledFields(merged)
    expect(enabled.map((m) => m.field.fieldKey)).toEqual(['a'])
  })

  // ---- groupFieldsByModule 4 种边界（2026-09-20 QA 补充）----
  function makeFieldWithModule(fieldKey: string, moduleCode: string | null, orderIndex: number): MergedResumeField {
    return {
      field: {
        ...makeField({ fieldKey, orderIndex }),
        module: moduleCode
          ? {
              id: moduleCode,
              resource: 'Candidate',
              code: moduleCode,
              name: moduleCode,
              orderIndex: 0,
              isActive: true,
            }
          : null,
      } as FieldDefinition,
      enabled: true,
      required: false,
    }
  }

  it('groupFieldsByModule: moduleOrder 缺省时按字段首现顺序', () => {
    const merged = [
      makeFieldWithModule('a', 'basic', 1),
      makeFieldWithModule('b', 'edu', 2),
      makeFieldWithModule('c', 'basic', 3),
    ]
    const groups = groupFieldsByModule(merged, undefined)
    expect(groups.map((g: ModuleGroup) => g.key)).toEqual(['basic', 'edu'])
    expect(groups[0].fields.map((m) => m.field.fieldKey)).toEqual(['a', 'c'])
    expect(groups[1].fields.map((m) => m.field.fieldKey)).toEqual(['b'])
  })

  it('groupFieldsByModule: moduleOrder 中出现的未声明模块被跳过', () => {
    const merged = [makeFieldWithModule('a', 'basic', 1)]
    const groups = groupFieldsByModule(merged, ['basic', 'nonexistent'])
    expect(groups.map((g) => g.key)).toEqual(['basic'])
  })

  it('groupFieldsByModule: 未声明的 present 模块追加到末尾', () => {
    const merged = [
      makeFieldWithModule('a', 'basic', 1),
      makeFieldWithModule('b', 'edu', 2),
      makeFieldWithModule('c', 'extra', 3),
    ]
    const groups = groupFieldsByModule(merged, ['basic'])
    expect(groups.map((g) => g.key)).toEqual(['basic', 'edu', 'extra'])
  })

  it('groupFieldsByModule: UNGROUPED_MODULE_CODE 永远置末尾', () => {
    const merged = [
      makeFieldWithModule('a', null, 1), // 未分组
      makeFieldWithModule('b', 'basic', 2),
    ]
    const groups = groupFieldsByModule(merged, [UNGROUPED_MODULE_CODE, 'basic'])
    expect(groups.map((g) => g.key)).toEqual(['basic', UNGROUPED_MODULE_CODE])
  })

  // ---- 异步 API ----
  it('fetchConfig 解析 data.data 正常返回', async () => {
    getMock.mockResolvedValue({
      data: {
        data: {
          fields: [{ fieldKey: 'name', enabled: true, required: true }],
          requiredStages: ['screening', 'offer'],
        },
      },
    })
    const c = await fetchConfig()
    expect(getMock).toHaveBeenCalledWith(STANDARD_RESUME_API)
    expect(c.fields).toHaveLength(1)
    expect(c.requiredStages).toEqual(['screening', 'offer'])
  })

  it('fetchConfig 空响应回退默认结构', async () => {
    getMock.mockResolvedValue({ data: {} })
    const c = await fetchConfig()
    expect(c).toEqual(defaultConfig())
  })

  it('fetchConfig 损坏数据回退默认结构（不抛错）', async () => {
    getMock.mockResolvedValue({ data: { data: null } })
    const c = await fetchConfig()
    expect(c).toEqual(defaultConfig())
  })

  it('saveConfig PUT 整份配置并返回落库回显', async () => {
    const cfg: StandardResumeConfig = {
      fields: [{ fieldKey: 'a', enabled: true, required: false }],
      requiredStages: ['screening'],
      moduleOrder: [],
    }
    putMock.mockResolvedValue({ data: { data: cfg } })
    const r = await saveConfig(cfg)
    expect(putMock).toHaveBeenCalledWith(STANDARD_RESUME_API, cfg)
    expect(r).toEqual(cfg)
  })

  it('resetConfig 清空并落库默认配置', async () => {
    putMock.mockResolvedValue({ data: { data: defaultConfig() } })
    const r = await resetConfig()
    expect(putMock).toHaveBeenCalledWith(STANDARD_RESUME_API, defaultConfig())
    expect(r).toEqual(defaultConfig())
  })
})
