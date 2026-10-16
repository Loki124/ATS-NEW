/**
 * metricsTemplateForm.test.ts — 模板表单归一 / 校验 / payload 构造 单测。
 *
 * 覆盖从 useMetricsWorkspace.ts 下沉的业务规则：
 *   - emptyTplForm / normalizeParamConfig / metricSelectionKey：字段归一
 *   - formFromTemplateRow：编辑态按出参类型分流（自由文本 / 枚举 / 实体 / 日期）
 *   - enumCandidateOptions / enumCandidateIssue：枚举候选合并与校验
 *   - templateSubmitIssue：保存前校验的固定短路顺序
 *   - buildTemplateSubmitPayload：API payload 的类型分流
 *   - metricDefinitionGroupOptions / findSelectedDefinition：指标下拉分组与反查
 *
 * 纯函数不接 i18n 的 t，改注入「已解析好的文案函数」；identity mock 让断言只关心选键逻辑。
 */
import { describe, it, expect } from 'vitest'
import {
  emptyTplForm,
  normalizeParamConfig,
  metricSelectionKey,
  formFromTemplateRow,
  enumCandidateOptions,
  enumCandidateIssue,
  templateSubmitIssue,
  buildTemplateSubmitPayload,
  metricDefinitionGroupOptions,
  findSelectedDefinition,
  SET_OPERATORS,
} from '../metricsTemplateForm'
import type { MetricDefinition, MetricTemplate } from '@/api/metrics'

const labels = {
  requiredName: () => 'E_NAME',
  selectOneMetric: () => 'E_METRIC',
  requiredOperators: () => 'E_OPS',
  freetextNoSetOperator: () => 'E_SET_OP',
  enumCandidateRequired: () => 'E_ENUM_REQ',
  enumCandidateEmpty: () => 'E_ENUM_EMPTY',
  enumCandidateDuplicate: () => 'E_ENUM_DUP',
  atomicGroupLabel: () => 'G_ATOMIC',
  derivedGroupLabel: () => 'G_DERIVED',
}
const C = { unit: '段', name: '默认值' } as const

function row(p: Partial<MetricTemplate>): MetricTemplate {
  return { id: 'r1', name: '', ...p } as MetricTemplate
}

describe('emptyTplForm', () => {
  it('返回可用的初始形状', () => {
    const f = emptyTplForm()
    expect(f.name).toBe('')
    expect(f.metricDefinition).toBeNull()
    expect(f.operators).toEqual([])
    expect(f.valueDomain).toEqual({ segments: [] })
    expect(f.paramEnums).toEqual([])
    expect(f.status).toBe('enabled')
  })

  it('paramConfig 七字段齐备且默认 allOption=false', () => {
    expect(emptyTplForm().paramConfig).toEqual({
      min: null, max: null, step: null, prefix: '', suffix: '', allOption: false,
      allText: '全部工作经历',
    })
  })

  it('每次调用返回新对象（不共享引用）', () => {
    const a = emptyTplForm()
    const b = emptyTplForm()
    expect(a).not.toBe(b)
    expect(a.paramConfig).not.toBe(b.paramConfig)
    expect(a.valueDomain).not.toBe(b.valueDomain)
  })
})

describe('normalizeParamConfig', () => {
  it('缺失字段补默认值', () => {
    expect(normalizeParamConfig({})).toEqual({
      min: null, max: null, step: null, prefix: '', suffix: '', allOption: false, allText: '全部工作经历',
    })
  })

  it('0 值不被 nullish 吞掉', () => {
    const r = normalizeParamConfig({ min: 0, max: 0, step: 0 })
    expect(r.min).toBe(0)
    expect(r.max).toBe(0)
    expect(r.step).toBe(0)
  })

  it('allOption 强制转布尔', () => {
    expect(normalizeParamConfig({ allOption: 'yes' }).allOption).toBe(true)
    expect(normalizeParamConfig({ allOption: 0 }).allOption).toBe(false)
  })
})

describe('metricSelectionKey', () => {
  it('原子指标拼 atomic:<id>', () => {
    expect(metricSelectionKey({ metricKind: 'atomic', atomicMetric: 'm1' } as any)).toBe('atomic:m1')
  })

  it('派生指标拼 derived:<id>', () => {
    expect(metricSelectionKey({ metricKind: 'derived', derivedMetric: 'm2' } as any)).toBe('derived:m2')
  })

  it('缺 metricKind 返回 null', () => {
    expect(metricSelectionKey({ atomicMetric: 'm1' } as any)).toBeNull()
  })

  it('缺指标列返回 null', () => {
    expect(metricSelectionKey({ metricKind: 'atomic' } as any)).toBeNull()
  })
})

describe('formFromTemplateRow', () => {
  const flags = {
    isTextOutput: false, isEnumOutput: false, isEntityOutput: false,
    entityKind: '', dateGranularityDefault: '日', isDateOutput: false,
  }

  it('基础字段逐一映射', () => {
    const f = formFromTemplateRow({
      ...flags,
      row: row({ code: 'C1', name: '模板A', unit: '岁', paramUnit: '年', paramAllowNull: true, description: 'd', status: 'disabled' }),
    })
    expect(f.code).toBe('C1')
    expect(f.name).toBe('模板A')
    expect(f.unit).toBe('岁')
    expect(f.paramUnit).toBe('年')
    expect(f.paramAllowNull).toBe(true)
    expect(f.description).toBe('d')
    expect(f.status).toBe('disabled')
  })

  it('calcParams 深拷贝，不与源行共享引用', () => {
    const src = { unit: 'month' }
    const f = formFromTemplateRow({ ...flags, row: row({ calcParams: src }) })
    expect(f.calcParams).toEqual(src)
    expect(f.calcParams).not.toBe(src)
  })

  it('自由文本型：剔除集合运算符且值域清空', () => {
    const f = formFromTemplateRow({
      ...flags, isTextOutput: true,
      row: row({ operators: ['EQ', ...SET_OPERATORS], valueDomain: { segments: [{ min: 1 }] } }),
    })
    expect(f.operators).toEqual(['EQ'])
    expect(f.valueDomain).toEqual({ segments: [] })
  })

  it('枚举型：候选值清空（模板层需重新指定可选范围）', () => {
    const f = formFromTemplateRow({ ...flags, isEnumOutput: true, row: row({ paramEnums: ['A', 'B'] }) })
    expect(f.paramEnums).toEqual([])
  })

  it('实体型：候选值清空且值域 kind 与出参不符时重置', () => {
    const f = formFromTemplateRow({
      ...flags, isEntityOutput: true, entityKind: 'person',
      row: row({ paramEnums: ['A'], valueDomain: { kind: 'department', options: [{ type: 'specified', ids: ['1'] }] } }),
    })
    expect(f.paramEnums).toEqual([])
    expect(f.valueDomain).toEqual({ kind: 'person', options: [] })
  })

  it('实体型：值域 kind 已匹配时保留候选清单', () => {
    const f = formFromTemplateRow({
      ...flags, isEntityOutput: true, entityKind: 'person',
      row: row({ valueDomain: { kind: 'person', options: [{ type: 'specified', ids: ['1'], label: '张三' }] } }),
    })
    expect(f.valueDomain.options).toEqual([{ type: 'specified', ids: ['1'], label: '张三' }])
  })

  it('数值型：候选值同样清空（枚举无意义）', () => {
    const f = formFromTemplateRow({ ...flags, row: row({ paramEnums: ['X'] }) })
    expect(f.paramEnums).toEqual([])
  })

  it('日期型且单位为空时补默认粒度', () => {
    const f = formFromTemplateRow({ ...flags, isDateOutput: true, dateGranularityDefault: '日', row: row({ unit: '' }) })
    expect(f.unit).toBe('日')
  })

  it('日期型且已有单位时保留原值', () => {
    const f = formFromTemplateRow({ ...flags, isDateOutput: true, row: row({ unit: '月' }) })
    expect(f.unit).toBe('月')
  })
})

describe('enumCandidateOptions', () => {
  it('合并定义值与模板值，定义值在前', () => {
    expect(enumCandidateOptions({ defEnumValues: ['A'], tplEnumValues: ['B'] })).toEqual([
      { label: 'A', value: 'A' }, { label: 'B', value: 'B' },
    ])
  })

  it('按首次出现去重', () => {
    expect(enumCandidateOptions({ defEnumValues: ['A', 'B'], tplEnumValues: ['A', 'C'] })).toHaveLength(3)
  })

  it('剔除空串与纯空白项', () => {
    expect(enumCandidateOptions({ defEnumValues: ['A', '', '  '], tplEnumValues: [] })).toHaveLength(1)
  })

  it('两侧均为 undefined/空 → 返回空数组', () => {
    expect(enumCandidateOptions({ defEnumValues: undefined, tplEnumValues: [] })).toEqual([])
  })
})

describe('enumCandidateIssue', () => {
  it('非枚举型不校验', () => {
    expect(enumCandidateIssue({ isEnumOutput: false, tplEnumValues: [], labels })).toBe('')
  })

  it('枚举型缺候选 → 必填文案', () => {
    expect(enumCandidateIssue({ isEnumOutput: true, tplEnumValues: [], labels })).toBe('E_ENUM_REQ')
  })

  it('存在空白候选 → 空白项文案', () => {
    expect(enumCandidateIssue({ isEnumOutput: true, tplEnumValues: ['A', ' '], labels })).toBe('E_ENUM_EMPTY')
  })

  it('存在重复候选 → 重复项文案', () => {
    expect(enumCandidateIssue({ isEnumOutput: true, tplEnumValues: ['A', 'A'], labels })).toBe('E_ENUM_DUP')
  })

  it('合法候选返回空串', () => {
    expect(enumCandidateIssue({ isEnumOutput: true, tplEnumValues: ['A', 'B'], labels })).toBe('')
  })
})

describe('templateSubmitIssue', () => {
  const ok = { enumIssue: '', entityIssue: '', domainError: '' }
  const good = { ...emptyTplForm(), name: 'n', metricDefinition: 'atomic:m1', operators: ['EQ'] }

  it('全部合法 → 空串', () => {
    expect(templateSubmitIssue({ form: good, isTextOutput: false, ...ok, labels })).toBe('')
  })

  it('名称为空（纯空白也算）→ 名称必填', () => {
    expect(templateSubmitIssue({ form: { ...good, name: '   ' }, isTextOutput: false, ...ok, labels }))
      .toBe('E_NAME')
  })

  it('未选指标 → 选指标文案', () => {
    expect(templateSubmitIssue({ form: { ...good, metricDefinition: null }, isTextOutput: false, ...ok, labels }))
      .toBe('E_METRIC')
  })

  it('指标键缺 id 部分 → 选指标文案', () => {
    expect(templateSubmitIssue({ form: { ...good, metricDefinition: 'atomic:' }, isTextOutput: false, ...ok, labels }))
      .toBe('E_METRIC')
  })

  it('运算符为空 → 运算符必填', () => {
    expect(templateSubmitIssue({ form: { ...good, operators: [] }, isTextOutput: false, ...ok, labels }))
      .toBe('E_OPS')
  })

  it('自由文本型含集合运算符 → 拒绝', () => {
    expect(templateSubmitIssue({ form: { ...good, operators: ['IN'] }, isTextOutput: true, ...ok, labels }))
      .toBe('E_SET_OP')
  })

  it('校验顺序：名称优先于运算符', () => {
    expect(templateSubmitIssue({ form: { ...good, name: '', operators: [] }, isTextOutput: false, ...ok, labels }))
      .toBe('E_NAME')
  })

  it('校验顺序：运算符优先于枚举候选', () => {
    const r = templateSubmitIssue({
      form: { ...good, operators: [] }, isTextOutput: false,
      enumIssue: 'E_ENUM_REQ', entityIssue: '', domainError: '', labels: labels,
    })
    expect(r).toBe('E_OPS')
  })

  it('校验顺序：枚举候选优先于实体候选', () => {
    expect(templateSubmitIssue({
      form: good, isTextOutput: false,
      enumIssue: 'E', entityIssue: 'N', domainError: 'D', labels: labels,
    })).toBe('E')
  })

  it('校验顺序：实体候选优先于值域', () => {
    expect(templateSubmitIssue({
      form: good, isTextOutput: false, enumIssue: '', entityIssue: 'N', domainError: 'D', labels: labels,
    })).toBe('N')
  })

  it('仅值域有错时透传值域文案', () => {
    expect(templateSubmitIssue({ form: good, isTextOutput: false, enumIssue: '', entityIssue: '', domainError: 'D', labels }))
      .toBe('D')
  })
})

describe('buildTemplateSubmitPayload', () => {
  const form = { ...emptyTplForm(), name: 'n', metricDefinition: 'atomic:m1', operators: ['EQ'], description: 'd' }

  it('原子指标写入 atomicMetric，derivedMetric 为 null', () => {
    const p = buildTemplateSubmitPayload({ form, isTextOutput: false, isEnumOutput: false, valueDomain: {} })
    expect(p.atomicMetric).toBe('m1')
    expect(p.derivedMetric).toBeNull()
  })

  it('派生指标写入 derivedMetric，atomicMetric 为 null', () => {
    const p = buildTemplateSubmitPayload({
      form: { ...form, metricDefinition: 'derived:m2' }, isTextOutput: false, isEnumOutput: false, valueDomain: {},
    })
    expect(p.derivedMetric).toBe('m2')
    expect(p.atomicMetric).toBeNull()
  })

  it('数值型：值域原样落库', () => {
    const vd = { segments: [{ min: 1, max: 3, step: 1 }] }
    expect(buildTemplateSubmitPayload({ form, isTextOutput: false, isEnumOutput: false, valueDomain: vd }).valueDomain)
      .toBe(vd)
  })

  it('枚举型：值域强制清空，候选值才落库', () => {
    const p = buildTemplateSubmitPayload({
      form: { ...form, paramEnums: ['A'] }, isTextOutput: false, isEnumOutput: true, valueDomain: {},
    })
    expect(p.valueDomain).toEqual({ segments: [] })
    expect(p.paramEnums).toEqual(['A'])
  })

  it('自由文本型：值域清空且候选值不落库', () => {
    const p = buildTemplateSubmitPayload({
      form: { ...form, paramEnums: ['A'], operators: ['EQ', 'IN'] }, isTextOutput: true, isEnumOutput: false, valueDomain: {},
    })
    expect(p.valueDomain).toEqual({ segments: [] })
    expect(p.paramEnums).toEqual([])
    expect(p.operators).toEqual(['EQ'])
  })

  it('status 为空时兜底 enabled', () => {
    expect(buildTemplateSubmitPayload({ form: { ...form, status: '' }, isTextOutput: false, isEnumOutput: false, valueDomain: {} }).status)
      .toBe('enabled')
  })
})

describe('metricDefinitionGroupOptions', () => {
  const defs = [
    { id: 'a', kind: 'atomic', name: '甲', dataSource: 'candidate.x' },
    { id: 'b', kind: 'derived', name: '乙', dataSource: 'candidate.y' },
  ] as unknown as MetricDefinition[]

  it('按原子/派生分组，标签含数据来源', () => {
    const g = metricDefinitionGroupOptions({ definitions: defs, labels })
    expect(g).toHaveLength(2)
    expect(g[0].children[0].label).toBe('甲（candidate.x）')
    expect(g[0].children[0].value).toBe('atomic:a')
  })

  it('空组不出现', () => {
    const g = metricDefinitionGroupOptions({ definitions: [defs[0]] as any, labels })
    expect(g).toHaveLength(1)
    expect(g[0].key).toBe('atomic')
  })

  it('无定义返回空数组', () => {
    expect(metricDefinitionGroupOptions({ definitions: [], labels })).toEqual([])
  })
})

describe('findSelectedDefinition', () => {
  const defs = [
    { id: 'a', kind: 'atomic', name: '甲' },
    { id: 'a', kind: 'derived', name: '乙' },
  ] as unknown as MetricDefinition[]

  it('按 kind:id 精确反查', () => {
    expect(findSelectedDefinition(defs, 'derived:a')!.name).toBe('乙')
  })

  it('key 为空返回 undefined', () => {
    expect(findSelectedDefinition(defs, null)).toBeUndefined()
  })

  it('key 不存在返回 undefined', () => {
    expect(findSelectedDefinition(defs, 'atomic:zzz')).toBeUndefined()
  })
})
