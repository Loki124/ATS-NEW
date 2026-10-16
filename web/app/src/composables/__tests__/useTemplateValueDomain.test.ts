/**
 * useTemplateValueDomain.test.ts — 出参类型判定 + 单位/值域配置 域 composable 单测。
 *
 * 覆盖从 useMetricsWorkspace.ts 下沉到本 composable 的业务判定：
 *   - 五种出参类型互斥判定（日期 / 枚举 / 自由文本 / 实体引用 / 数值）
 *     与「实体引用型不得掉进文本或数值分支」这条硬规则；
 *   - 出参单位候选与当前单位回退（含日期型粒度越界回退默认）；
 *   - setUnit 是否按 UNIT_TO_CALC 回写 calcParams.unit；
 *   - supportedOperators 与运算符目录求交集、空定义返回空；
 *   - 自由文本型禁用集合运算符（IN / NOT_IN）；
 *   - 日期型分段校验委托值域校验并回填错误文案。
 *
 * 为什么值得测：这几个判定决定值域配置区「渲染哪一块表单」，
 * 判错就是用户看到的「人员字段没有值域可配」这类症状；而判定链有 4 层互斥，
 * 纯 computed 单测比 mount 组件更快定位是哪一层判错。
 *
 * 依赖说明：i18n 的 t 与 naive-ui 的 useMessage 由 src/__tests__/setup.ts 全局 mock，
 * 本文件不自己再造 mock。
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { ref, nextTick, isRef } from 'vue'
import { useTemplateValueDomain } from '../useTemplateValueDomain'
import type { MetricDefinition, OptionItem } from '@/api/metrics'
import { SET_OPERATORS } from '@/utils/metricsTemplateForm'

/** 指标定义工厂：默认值取一个「原子 + string 出参」的最小可判形态。 */
function def(p: Partial<MetricDefinition>): MetricDefinition {
  return { id: 'd1', kind: 'atomic', name: '指标', ...p } as MetricDefinition
}
function form(p: Record<string, any> = {}) {
  return ref<any>({ unit: '', paramUnit: '', operators: [], calcParams: {}, valueDomain: { segments: [] }, ...p })
}
const ops: OptionItem[] = [
  { value: 'EQ', label: '等于' },
  { value: 'IN', label: '属于' },
  { value: 'NOT_IN', label: '不属于' },
]

describe('出参类型判定', () => {
  it('returnType=date → isDateOutput，且不是数值型', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ returnType: 'date' })),
      operatorCatalog: ref(ops),
    })
    expect(api.isDateOutput.value).toBe(true)
    expect(api.isNumberOutput.value).toBe(false)
    expect(api.showValueDomain.value).toBe(true)
  })

  it('returnType=string 且 isEnum → 枚举型，不是自由文本', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ returnType: 'string', isEnum: true })),
      operatorCatalog: ref(ops),
    })
    expect(api.isEnumOutput.value).toBe(true)
    expect(api.isTextOutput.value).toBe(false)
  })

  it('returnType=string 非枚举 → 自由文本型，值域区整体隐藏', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ returnType: 'string' })),
      operatorCatalog: ref(ops),
    })
    expect(api.isTextOutput.value).toBe(true)
    expect(api.showValueDomain.value).toBe(false)
  })

  it('🔴 entityKind=person：既不是自由文本也不是数值，否则值域区会被错渲染', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ returnType: 'string', entityKind: 'person' })),
      operatorCatalog: ref(ops),
    })
    expect(api.entityKind.value).toBe('person')
    expect(api.isEntityOutput.value).toBe(true)
    expect(api.isPersonOutput.value).toBe(true)
    expect(api.isDeptOutput.value).toBe(false)
    expect(api.isTextOutput.value).toBe(false)
    expect(api.isNumberOutput.value).toBe(false)
  })

  it('entityKind=department → isDeptOutput，值域区仍可见', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ returnType: 'string', entityKind: 'department' })),
      operatorCatalog: ref(ops),
    })
    expect(api.isDeptOutput.value).toBe(true)
    expect(api.showValueDomain.value).toBe(true)
  })

  it('非法 entityKind 归一为空串（不落进实体分支）', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ returnType: 'string', entityKind: 'robot' as any })),
      operatorCatalog: ref(ops),
    })
    expect(api.entityKind.value).toBe('')
    expect(api.isEntityOutput.value).toBe(false)
  })

  it('其余类型落到数值型', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ returnType: 'number' })),
      operatorCatalog: ref(ops),
    })
    expect(api.isNumberOutput.value).toBe(true)
  })

  it('未选指标 → 全部类型判否且值域区隐藏', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(undefined),
      operatorCatalog: ref(ops),
    })
    expect(api.showValueDomain.value).toBe(false)
    expect(api.isDateOutput.value).toBe(false)
    expect(api.isNumberOutput.value).toBe(true) // 四类全否 → 落入数值分支（历史行为，保持不变）
  })
})

describe('枚举候选', () => {
  it('定义候选与模板候选合并去重，定义值在前', () => {
    const api = useTemplateValueDomain({
      tplForm: form({ paramEnums: ['B', 'A'] }),
      selectedTemplateDefinition: ref(def({ returnType: 'string', isEnum: true, enumValues: ['A', 'C'] })),
      operatorCatalog: ref(ops),
    })
    expect(api.enumCandidateOptions.value.map((o) => o.value)).toEqual(['A', 'C', 'B'])
  })

  it('候选为空 → 报错；非枚举型不校验', () => {
    const api = useTemplateValueDomain({
      tplForm: form({ paramEnums: [] }),
      selectedTemplateDefinition: ref(def({ returnType: 'string', isEnum: true })),
      operatorCatalog: ref(ops),
    })
    expect(api.enumCandidateIssue.value).not.toBe('')

    const nonEnum = useTemplateValueDomain({
      tplForm: form({ paramEnums: [] }),
      selectedTemplateDefinition: ref(def({ returnType: 'number' })),
      operatorCatalog: ref(ops),
    })
    expect(nonEnum.enumCandidateIssue.value).toBe('')
  })

  it('空白项 / 重复项分别命中不同错误', () => {
    const blank = useTemplateValueDomain({
      tplForm: form({ paramEnums: ['A', ' '] }),
      selectedTemplateDefinition: ref(def({ returnType: 'string', isEnum: true })),
      operatorCatalog: ref(ops),
    })
    const dup = useTemplateValueDomain({
      tplForm: form({ paramEnums: ['A', 'A'] }),
      selectedTemplateDefinition: ref(def({ returnType: 'string', isEnum: true })),
      operatorCatalog: ref(ops),
    })
    expect(blank.enumCandidateIssue.value).not.toBe('')
    expect(dup.enumCandidateIssue.value).not.toBe('')
    expect(blank.enumCandidateIssue.value).not.toBe(dup.enumCandidateIssue.value)
  })
})

describe('出参单位', () => {
  it('日期型候选固定为年/月/日三种粒度', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ returnType: 'date' })),
      operatorCatalog: ref(ops),
    })
    expect(api.outputUnitOptions.value).toEqual(['年', '月', '日'])
  })

  it('日期型单位越界（表单里存了「小时」）→ 回退默认粒度', () => {
    const api = useTemplateValueDomain({
      tplForm: form({ unit: '小时' }),
      selectedTemplateDefinition: ref(def({ returnType: 'date' })),
      operatorCatalog: ref(ops),
    })
    expect(api.currentOutputUnit.value).toBe('日')
  })

  it('非日期型：units 优先于 unit，都空则无候选', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ units: ['人', '', '次'], unit: '年' })),
      operatorCatalog: ref(ops),
    })
    expect(api.outputUnitOptions.value).toEqual(['人', '次'])

    const onlyUnit = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ unit: '分' })),
      operatorCatalog: ref(ops),
    })
    expect(onlyUnit.outputUnitOptions.value).toEqual(['分'])

    const none = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({})),
      operatorCatalog: ref(ops),
    })
    expect(none.outputUnitOptions.value).toEqual([])
  })

  it('表单单位为空 → 当前单位取候选首项', () => {
    const api = useTemplateValueDomain({
      tplForm: form({ unit: '' }),
      selectedTemplateDefinition: ref(def({ units: ['人', '次'] })),
      operatorCatalog: ref(ops),
    })
    expect(api.currentOutputUnit.value).toBe('人')
  })

  it('🔴 月/年 才回写 calcParams.unit；日期型与单单位不写', () => {
    const multi = form()
    const api = useTemplateValueDomain({
      tplForm: multi,
      selectedTemplateDefinition: ref(def({ units: ['人', '月'] })),
      operatorCatalog: ref(ops),
    })
    api.setUnit('月')
    expect(multi.value.unit).toBe('月')
    expect(multi.value.calcParams.unit).toBe('month')

    const dateForm = form()
    const dateApi = useTemplateValueDomain({
      tplForm: dateForm,
      selectedTemplateDefinition: ref(def({ returnType: 'date' })),
      operatorCatalog: ref(ops),
    })
    dateApi.setUnit('年')
    expect(dateForm.value.unit).toBe('年')
    expect(dateForm.value.calcParams.unit).toBeUndefined()

    const singleForm = form()
    const singleApi = useTemplateValueDomain({
      tplForm: singleForm,
      selectedTemplateDefinition: ref(def({ units: ['月'] })),
      operatorCatalog: ref(ops),
    })
    singleApi.setUnit('月')
    expect(singleForm.value.calcParams.unit).toBeUndefined()
  })
})

describe('参数单位与取值方式', () => {
  it('参数单位候选过滤空值；表单有值时以其为准，否则取首项', () => {
    const api = useTemplateValueDomain({
      tplForm: form({ paramUnit: '' }),
      selectedTemplateDefinition: ref(def({ paramUnits: ['次', '', '人'] })),
      operatorCatalog: ref(ops),
    })
    expect(api.paramUnitOptions.value).toEqual(['次', '人'])
    expect(api.currentParamUnit.value).toBe('次')

    const preset = useTemplateValueDomain({
      tplForm: form({ paramUnit: '人' }),
      selectedTemplateDefinition: ref(def({ paramUnits: ['次', '人'] })),
      operatorCatalog: ref(ops),
    })
    expect(preset.currentParamUnit.value).toBe('人')

    preset.setPunit('次')
    expect(preset.setPunit).toBeTypeOf('function')
  })

  it('setPunit 回写表单字段', () => {
    const f = form({ paramUnit: '次' })
    const api = useTemplateValueDomain({
      tplForm: f,
      selectedTemplateDefinition: ref(def({ paramUnits: ['次', '人'] })),
      operatorCatalog: ref(ops),
    })
    api.setPunit('人')
    expect(f.value.paramUnit).toBe('人')
  })

  it('参数化取值方式 → 文案区分连续/离散；对象路径 → 对象路径；无定义 → 空串', () => {
    const cont = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ valueMode: 'parametric_handler', paramType: 'continuous' })),
      operatorCatalog: ref(ops),
    })
    expect(cont.valueModeLabel.value).toContain('连续')

    const disc = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ valueMode: 'parametric_handler', paramType: 'discrete' })),
      operatorCatalog: ref(ops),
    })
    expect(disc.valueModeLabel.value).toContain('离散')

    const path = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ valueMode: 'object_path' as never })),
      operatorCatalog: ref(ops),
    })
    expect(path.valueModeLabel.value).toBe('对象路径')

    const none = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(undefined),
      operatorCatalog: ref(ops),
    })
    expect(none.valueModeLabel.value).toBe('')
  })
})

describe('运算符', () => {
  it('定义支持的运算符与目录求交集，目录外的丢弃', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ supportedOperators: ['EQ', 'NOT_EXIST'] })),
      operatorCatalog: ref(ops),
    })
    expect(api.supportedOperatorOptions.value.map((o) => o.value)).toEqual(['EQ'])
  })

  it('定义未声明 supportedOperators → 空数组', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({})),
      operatorCatalog: ref(ops),
    })
    expect(api.supportedOperatorOptions.value).toEqual([])
  })

  it('自由文本型禁用集合运算符，其余类型不禁用', () => {
    const text = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ returnType: 'string' })),
      operatorCatalog: ref(ops),
    })
    for (const op of SET_OPERATORS) expect(text.operatorDisabledForFreetext(op)).toBe(true)
    expect(text.operatorDisabledForFreetext('EQ')).toBe(false)

    const num = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ returnType: 'number' })),
      operatorCatalog: ref(ops),
    })
    expect(num.operatorDisabledForFreetext('IN')).toBe(false)
  })

  it('🔴 自由文本型点任何集合运算符都不改表单；普通运算符正常增删', async () => {
    const f = form({ operators: ['EQ'] })
    const api = useTemplateValueDomain({
      tplForm: f,
      selectedTemplateDefinition: ref(def({ returnType: 'string' })),
      operatorCatalog: ref(ops),
    })
    // 自由文本型下 IN / NOT_IN 都被禁用，重复点击也不会写进表单
    api.toggleOperator('IN')
    expect(f.value.operators).toEqual(['EQ'])
    api.toggleOperator('NOT_IN')
    expect(f.value.operators).toEqual(['EQ'])

    // 非集合运算符正常增删
    api.toggleOperator('LTE')
    expect(f.value.operators).toEqual(['EQ', 'LTE'])
    api.toggleOperator('EQ')
    expect(f.value.operators).toEqual(['LTE'])
    await nextTick()
  })

  it('非自由文本型点集合运算符直接生效', () => {
    const f = form({ operators: [] })
    const api = useTemplateValueDomain({
      tplForm: f,
      selectedTemplateDefinition: ref(def({ returnType: 'number' })),
      operatorCatalog: ref(ops),
    })
    api.toggleOperator('IN')
    expect(f.value.operators).toEqual(['IN'])
  })
})

describe('日期型值域派生', () => {
  it('空日期边界 / 分段的初始形状', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ returnType: 'date' })),
      operatorCatalog: ref(ops),
    })
    expect(api.emptyDateBound()).toEqual({ type: 'absolute', date: null, n: null, unit: '日' })
    const seg = api.emptyDateSegment()
    expect(seg.step).toBe(1)
    expect(seg.stepUnit).toBe('日')
    expect(seg.from).toEqual(api.emptyDateBound())
  })

  it('粒度 → 控件类型与日期格式（年/月/日，未知粒度回退 date + yyyy-MM-dd）', () => {
    const f = form({ unit: '年' })
    const api = useTemplateValueDomain({
      tplForm: f,
      selectedTemplateDefinition: ref(def({ returnType: 'date' })),
      operatorCatalog: ref(ops),
    })
    expect(api.datePickerType.value).toBe('year')
    expect(api.dateValueFormat.value).toBe('yyyy')

    f.value.unit = '月'
    expect(api.datePickerType.value).toBe('month')
    expect(api.dateValueFormat.value).toBe('yyyy-MM')

    f.value.unit = '日'
    expect(api.datePickerType.value).toBe('date')
    expect(api.dateValueFormat.value).toBe('yyyy-MM-dd')
  })

  it('边界类型候选只有绝对/相对两项', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ returnType: 'date' })),
      operatorCatalog: ref(ops),
    })
    expect(api.dateBoundTypeOptions.map((o) => o.value)).toEqual(['absolute', 'relative'])
    expect(api.dateUnitOptions.map((o) => o.value)).toEqual(['年', '月', '日'])
  })

  it('legacyNumericDomainOnDate：仅日期型且存在「只有 min/max 没有 from/to」的段时为真', () => {
    const api = useTemplateValueDomain({
      tplForm: form({ valueDomain: { segments: [{ min: 1, max: 5, step: 1 }] } }),
      selectedTemplateDefinition: ref(def({ returnType: 'date' })),
      operatorCatalog: ref(ops),
    })
    expect(api.legacyNumericDomainOnDate.value).toBe(true)

    const num = useTemplateValueDomain({
      tplForm: form({ valueDomain: { segments: [{ min: 1, max: 5, step: 1 }] } }),
      selectedTemplateDefinition: ref(def({ returnType: 'number' })),
      operatorCatalog: ref(ops),
    })
    expect(num.legacyNumericDomainOnDate.value).toBe(false)
  })

  it('computeDateDomain / buildDomainItems 按类型分流，dateSegmentIssues 委托校验', () => {
    const dateF = form({
      unit: '日',
      valueDomain: { segments: [{ from: { type: 'absolute', date: '2024-01-01', n: null, unit: '日' }, to: { type: 'absolute', date: '2024-01-03', n: null, unit: '日' }, step: 1 }] },
    })
    const dateApi = useTemplateValueDomain({
      tplForm: dateF,
      selectedTemplateDefinition: ref(def({ returnType: 'date' })),
      operatorCatalog: ref(ops),
    })
    const r = dateApi.computeDateDomain()
    expect(r.total).toBe(3)
    expect(r.items[0].text).toBe('2024-01-01')
    expect(dateApi.dateSegmentIssues.value).toEqual([null])

    const numF = form({ valueDomain: { segments: [{ min: 1, max: 3, step: 1 }] } })
    const numApi = useTemplateValueDomain({
      tplForm: numF,
      selectedTemplateDefinition: ref(def({ units: ['人'] })),
      operatorCatalog: ref(ops),
    })
    expect(numApi.buildDomainItems().map((i) => i.value)).toEqual(['1', '2', '3'])
  })

  it('step 缺失的日期段 → 校验不通过并给出可读文案', () => {
    const api = useTemplateValueDomain({
      tplForm: form({ unit: '日', valueDomain: { segments: [{ from: null, to: null, step: null }] } }),
      selectedTemplateDefinition: ref(def({ returnType: 'date' })),
      operatorCatalog: ref(ops),
    })
    expect(api.dateSegmentIssues.value[0]).toBeTruthy()
  })
})

describe('契约', () => {
  it('返回的都是 ref / 函数，供主 composable 二次透出', () => {
    const api = useTemplateValueDomain({
      tplForm: form(),
      selectedTemplateDefinition: ref(def({ returnType: 'date' })),
      operatorCatalog: ref(ops),
    })
    expect(isRef(api.isDateOutput)).toBe(true)
    expect(isRef(api.entityKind)).toBe(true)
    expect(api.setUnit).toBeTypeOf('function')
    expect(api.toggleOperator).toBeTypeOf('function')
    expect(api.computeDateDomain).toBeTypeOf('function')
    expect(api.buildDomainItems).toBeTypeOf('function')
    expect(api.emptyDateSegment).toBeTypeOf('function')
  })

  it('同一实例重复读取得到同一响应式对象（不新建状态）', () => {
    const f = form()
    const api = useTemplateValueDomain({
      tplForm: f,
      selectedTemplateDefinition: ref(def({ returnType: 'date' })),
      operatorCatalog: ref(ops),
    })
    const before = api.currentOutputUnit.value
    f.value.unit = '年'
    expect(api.currentOutputUnit.value).not.toBe(before)
    expect(api.currentOutputUnit.value).toBe('年')
  })
})
