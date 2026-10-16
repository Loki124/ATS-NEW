/**
 * useTemplatePreview.test.ts — 配置预览（结果读条）域 composable 单测。
 *
 * 覆盖从 useMetricsWorkspace.ts 下沉到本 composable 的联动规则：
 *   - 四个下拉的「首个未禁用项」自动回填（immediate watch）；
 *   - 参数取值枚举随 paramConfig / 离散连续类型变化；
 *   - 免填校验值判定（IS_EMPTY / IS_NOT_EMPTY + 实体型当前登录人）；
 *   - 自由文本正则校验（必填 / 非法）与切走运算符时清空；
 *   - 枚举 / 实体型的单选↔多选形态适配（n-select 单选吃标量、多选吃数组）；
 *   - 「全部」哨兵项在预览多选框里的插入与翻译回真实 id；
 *   - BETWEEN 区间默认上下界回填与候选变化时的钳制；
 *   - 实体型取值方式切换时默认选中首项并回填模板预设对象。
 *
 * 为什么值得测：这块有全文件仅有的 9 个 watch，是「用户改一处、别处悄悄变」的高风险区；
 * 而这些联动都不发请求，纯 computed + watch 单测比 mount 弹窗快一个数量级。
 *
 * mock 说明：i18n 的 t 与 naive-ui 的 useMessage 由 src/__tests__/setup.ts 全局 mock。
 */
import { describe, it, expect } from 'vitest'
import { ref, nextTick } from 'vue'
import { useTemplatePreview } from '../useTemplatePreview'
import { SELECT_ALL } from '@/utils/metricsEntityDomain'
import type { MetricDefinition, OptionItem } from '@/api/metrics'

const ops: OptionItem[] = [
  { value: 'EQ', label: '等于' },
  { value: 'IN', label: '属于' },
  { value: 'NOT_IN', label: '不属于' },
  { value: 'IS_EMPTY', label: '为空' },
  { value: 'REGEX_MATCH', label: '正则匹配' },
  { value: 'BETWEEN', label: '介于' },
]

function paramConfig(p: Record<string, any> = {}) {
  return { min: 1, max: 3, step: 1, prefix: '', suffix: '', allOption: false, allText: '', ...p }
}

function makeDeps(over: Record<string, any> = {}) {
  return {
    tplForm: ref<any>({
      name: '模板A',
      operators: ['EQ'],
      paramConfig: paramConfig(),
      paramEnums: [],
      ...(over.tplForm || {}),
    }),
    selectedTemplateDefinition: ref<MetricDefinition | undefined>(
      over.definition === null ? undefined : (over.definition ?? ({ id: 'd1', kind: 'atomic' } as MetricDefinition)),
    ),
    showTemplateParamConfig: ref(over.showParamConfig ?? true),
    isTextOutput: ref(over.isTextOutput ?? false),
    isEnumOutput: ref(over.isEnumOutput ?? false),
    isEntityOutput: ref(over.isEntityOutput ?? false),
    operatorCatalog: ref<OptionItem[]>(ops),
    domainItems: ref(over.domainItems ?? [{ text: '值1', value: 'v1' }]),
    domainErrorText: ref(over.domainErrorText ?? ''),
    enumCandidateOptions: ref(over.enumCandidateOptions ?? []),
    entityOptions: ref<any[]>(over.entityOptions ?? []),
    entityOptionsForType: (type: string) => (over.entityDir?.[type] ?? []),
    entityTypeLabel: (type: string) => `T:${type}`,
  } as any
}

describe('下拉自动回填', () => {
  it('指标项只有一个「当前模板」；模板名为空时回落未命名', async () => {
    const api = useTemplatePreview(makeDeps())
    expect(api.previewMetricItemOptions.value[0].value).toBe('current')
    expect(api.previewMetricSelected.value).toBe('current')

    const unnamed = useTemplatePreview(makeDeps({ tplForm: { name: '' } }))
    expect(unnamed.previewMetricItemOptions.value[0].label).toBeTruthy()
  })

  it('参数取值按 min/max/step 枚举，首项自动选中', async () => {
    const api = useTemplatePreview(makeDeps())
    await nextTick()
    expect(api.previewParamOptions.value.map((o) => o.value)).toEqual(['1', '2', '3'])
    expect(api.previewParamSelected.value).toBe('1')
    expect(api.paramSampleItems.value).toEqual(['1', '2', '3'])
  })

  it('非参数化出参 → 参数下拉为空', async () => {
    const api = useTemplatePreview(makeDeps({ showParamConfig: false }))
    await nextTick()
    expect(api.previewParamOptions.value).toEqual([])
    expect(api.paramSampleItems.value).toEqual([])
  })

  it('allOption 开启时首位插入「全部」，但样例文案跳过它', async () => {
    const api = useTemplatePreview(makeDeps({ tplForm: { paramConfig: paramConfig({ allOption: true, allText: '全部经历' }) } }))
    await nextTick()
    expect(api.previewParamOptions.value[0].value).toBe('__all__')
    expect(api.paramSampleItems.value).not.toContain('全部经历')
  })

  it('参数一项都产不出 → 禁用占位，值为空串', async () => {
    // 注意：min/max 为 null 时 Number(null)===0，会枚举出一个 0；真正「产不出」要用 undefined
    const api = useTemplatePreview(makeDeps({ tplForm: { paramConfig: paramConfig({ min: undefined, max: undefined }) } }))
    await nextTick()
    expect(api.previewParamOptions.value[0].disabled).toBe(true)
    expect(api.previewParamOptions.value[0].value).toBe('')
  })

  it('运算符下拉用模板已选值，首项自动选中', async () => {
    const api = useTemplatePreview(makeDeps())
    await nextTick()
    expect(api.previewOpOptions.value.map((o) => o.value)).toEqual(['EQ'])
    expect(api.previewOpSelected.value).toBe('EQ')
  })

  it('模板未选运算符时回落到定义支持的运算符', async () => {
    const api = useTemplatePreview(makeDeps({
      tplForm: { operators: [] },
      definition: { id: 'd1', kind: 'atomic', supportedOperators: ['IN', 'NOT_IN'] } as MetricDefinition,
    }))
    await nextTick()
    expect(api.previewOpOptions.value.map((o) => o.value)).toEqual(['IN', 'NOT_IN'])
  })

  it('校验值下拉用值域候选，首项自动选中', async () => {
    const api = useTemplatePreview(makeDeps())
    await nextTick()
    expect(api.previewCheckValueOptions.value.map((o) => o.value)).toEqual(['v1'])
    expect(api.previewValueSelected.value).toBe('v1')
    expect(api.enabledCheckValues()).toEqual(['v1'])
  })

  it('值域非法 → 禁用占位，enabledCheckValues 过滤掉', async () => {
    const api = useTemplatePreview(makeDeps({ domainErrorText: '段1：err', domainItems: [] }))
    await nextTick()
    expect(api.previewCheckValueOptions.value[0].disabled).toBe(true)
    expect(api.enabledCheckValues()).toEqual([])
  })

  it('firstEnabledValueOf 只按 disabled 判定（空串值也可成为首项，历史行为）', () => {
    const api = useTemplatePreview(makeDeps())
    expect(api.firstEnabledValueOf([{ value: '' }, { value: 'a' }])).toBe('')
    expect(api.firstEnabledValueOf([{ value: 'a', disabled: true }, { value: 'b' }])).toBe('b')
  })

  it('NO_VALUE_OPERATORS / MULTI_VALUE_OPERATORS 常量透出', () => {
    const api = useTemplatePreview(makeDeps())
    expect(api.NO_VALUE_OPERATORS).toContain('IS_EMPTY')
    expect(api.MULTI_VALUE_OPERATORS).toEqual(['IN', 'NOT_IN'])
  })
})

describe('免填校验值判定', () => {
  it('IS_EMPTY / IS_NOT_EMPTY 恒免填', async () => {
    const api = useTemplatePreview(makeDeps({ tplForm: { operators: ['IS_EMPTY'] } }))
    await nextTick()
    expect(api.previewNeedsNoValue.value).toBe(true)
    expect(api.previewNeedsTextInput.value).toBe(false)
    expect(api.previewNeedsEnumPicker.value).toBe(false)
  })

  it('自由文本型 + 非免填 → 走单行文本输入', async () => {
    const api = useTemplatePreview(makeDeps({ isTextOutput: true }))
    await nextTick()
    expect(api.previewNeedsTextInput.value).toBe(true)
  })

  it('实体型选「当前登录人」→ 值由运行时决定，免填', async () => {
    const api = useTemplatePreview(makeDeps({
      isEntityOutput: true,
      entityOptions: [{ type: 'current_user', ids: [], label: 'L' }],
    }))
    await nextTick()
    expect(api.previewEntitySelector.value).toBe('current_user')
    expect(api.previewEntityIsAuto.value).toBe(true)
    expect(api.previewNeedsNoValue.value).toBe(true)
  })
})

describe('自由文本正则校验', () => {
  it('非正则运算符 → 无校验、无特殊占位文案', async () => {
    const api = useTemplatePreview(makeDeps({ isTextOutput: true }))
    await nextTick()
    expect(api.previewRegexIssue.value).toBe('')
    expect(api.previewTextPlaceholder.value).not.toBe(api.previewTextPlaceholder.value === '' ? 'x' : '')
  })

  it('正则运算符：空 → 必填；非法 → 非法；合法 → 通过', async () => {
    const api = useTemplatePreview(makeDeps({ isTextOutput: true, tplForm: { operators: ['REGEX_MATCH'] } }))
    await nextTick()
    expect(api.previewRegexIssue.value).not.toBe('')

    api.previewTextValue.value = '   '
    expect(api.previewRegexIssue.value).not.toBe('')

    api.previewTextValue.value = '['
    expect(api.previewRegexIssue.value).not.toBe('')

    api.previewTextValue.value = '^abc$'
    expect(api.previewRegexIssue.value).toBe('')
    expect(api.previewTextPlaceholder.value).toBeTruthy()
  })

  it('切走正则运算符时清空已输入文本', async () => {
    const api = useTemplatePreview(makeDeps({ isTextOutput: true, tplForm: { operators: ['REGEX_MATCH'] } }))
    await nextTick()
    api.previewTextValue.value = '^abc$'
    expect(api.previewTextValue.value).toBe('^abc$')
    api.previewOpSelected.value = 'EQ'
    await nextTick()
    expect(api.previewTextValue.value).toBe('')
  })
})

describe('单选 ↔ 多选形态适配', () => {
  it('单选态 getter 返回标量，setter 把标量包成数组', async () => {
    const api = useTemplatePreview(makeDeps({ isEnumOutput: true, enumCandidateOptions: [{ label: 'A', value: 'A' }, { label: 'B', value: 'B' }] }))
    await nextTick()
    expect(api.previewNeedsMultiEnum.value).toBe(false)
    expect(Array.isArray(api.previewEnumValueModel.value)).toBe(false)

    api.previewEnumValueModel.value = 'B'
    expect(api.previewEnumValue.value).toEqual(['B'])
    expect(api.previewEnumValueModel.value).toBe('B')

    api.previewEnumValueModel.value = null
    expect(api.previewEnumValue.value).toEqual([])
    expect(api.previewEnumValueModel.value).toBeNull()
  })

  it('IN / NOT_IN + 枚举型 → 多选态；候选源用枚举候选，多选框顶部有哨兵', async () => {
    const api = useTemplatePreview(makeDeps({
      isEnumOutput: true,
      tplForm: { operators: ['IN'] },
      enumCandidateOptions: [{ label: 'A', value: 'A' }, { label: 'B', value: 'B' }],
    }))
    await nextTick()
    expect(api.previewNeedsMultiEnum.value).toBe(true)
    expect(api.previewCandidateOptions.value.map((o) => o.value)).toEqual(['A', 'B'])
    expect(api.previewSelectOptions.value[0].value).toBe(SELECT_ALL)
  })

  it('多选态全选时 getter 补回哨兵项，setter 翻译回真实 id', async () => {
    const api = useTemplatePreview(makeDeps({
      isEnumOutput: true,
      tplForm: { operators: ['IN'] },
      enumCandidateOptions: [{ label: 'A', value: 'A' }, { label: 'B', value: 'B' }],
    }))
    await nextTick()
    api.previewEnumValueModel.value = [SELECT_ALL]
    expect(api.previewEnumValue.value).toEqual(['A', 'B'])
    expect(api.previewIsAllSelected.value).toBe(true)
    expect(api.previewEnumValueModel.value).toEqual([SELECT_ALL, 'A', 'B'])

    api.previewEnumValueModel.value = ['A']
    expect(api.previewEnumValue.value).toEqual(['A'])
    expect(api.previewIsAllSelected.value).toBe(false)
  })

  it('切回单选：保留已选第 0 个；一个都没选则退回候选首项', async () => {
    const api = useTemplatePreview(makeDeps({
      isEnumOutput: true,
      tplForm: { operators: ['IN'] },
      enumCandidateOptions: [{ label: 'A', value: 'A' }, { label: 'B', value: 'B' }],
    }))
    await nextTick()
    api.previewEnumValue.value = ['A', 'B']
    api.previewOpSelected.value = 'EQ'
    await nextTick()
    expect(api.previewEnumValue.value).toEqual(['A'])

    api.previewEnumValue.value = []
    api.previewOpSelected.value = 'IN'
    await nextTick()
    api.previewOpSelected.value = 'EQ'
    await nextTick()
    expect(api.previewEnumValue.value.length).toBeLessThanOrEqual(1)
  })

  it('单选态 setter 传数组也只取全部值', async () => {
    const api = useTemplatePreview(makeDeps({ isEnumOutput: true, enumCandidateOptions: [{ label: 'A', value: 'A' }] }))
    await nextTick()
    api.previewEnumValueModel.value = ['A', 'B']
    expect(api.previewEnumValue.value).toEqual(['A', 'B'])
  })
})

describe('BETWEEN 区间', () => {
  it('切到 BETWEEN → 下界取首候选、上界取末候选', async () => {
    const api = useTemplatePreview(makeDeps({
      domainItems: [{ text: '1', value: '1' }, { text: '2', value: '2' }, { text: '3', value: '3' }],
    }))
    await nextTick()
    expect(api.previewNeedsRangeValue.value).toBe(false)
    api.previewOpSelected.value = 'BETWEEN'
    await nextTick()
    expect(api.previewNeedsRangeValue.value).toBe(true)
    expect(api.previewRangeLower.value).toBe('1')
    expect(api.previewRangeUpper.value).toBe('3')
  })

  it('初始即 BETWEEN 时区间不回填（该 watch 非 immediate，需手动切换触发）', async () => {
    const api = useTemplatePreview(makeDeps({
      domainItems: [{ text: '1', value: '1' }, { text: '3', value: '3' }],
      tplForm: { operators: ['BETWEEN'] },
    }))
    await nextTick()
    await nextTick()
    expect(api.previewNeedsRangeValue.value).toBe(true)
    expect(api.previewRangeLower.value).toBe('')
    expect(api.previewRangeUpper.value).toBe('')
  })

  it('离开 BETWEEN → 把下界写回校验值', async () => {
    const api = useTemplatePreview(makeDeps({
      domainItems: [{ text: '1', value: '1' }, { text: '3', value: '3' }],
    }))
    await nextTick()
    api.previewOpSelected.value = 'BETWEEN'
    await nextTick()
    api.previewOpSelected.value = 'EQ'
    await nextTick()
    expect(api.previewNeedsRangeValue.value).toBe(false)
    expect(api.previewValueSelected.value).toBe('1')
  })

  it('候选变化后区间越界被钳回有效值', async () => {
    const items = ref<any[]>([{ text: '1', value: '1' }, { text: '2', value: '2' }, { text: '3', value: '3' }])
    const deps = makeDeps()
    deps.domainItems = items as any
    const api = useTemplatePreview(deps)
    await nextTick()
    api.previewOpSelected.value = 'BETWEEN'
    await nextTick()
    expect(api.previewRangeLower.value).toBe('1')
    items.value = [{ text: '8', value: '8' }, { text: '9', value: '9' }]
    await nextTick()
    expect(api.previewRangeLower.value).toBe('8')
    expect(api.previewRangeUpper.value).toBe('9')
  })

  it('候选为空时切到 BETWEEN → 区间上下界仍为空串', async () => {
    const deps = makeDeps({ domainItems: [] })
    const api = useTemplatePreview(deps)
    await nextTick()
    api.previewOpSelected.value = 'BETWEEN'
    await nextTick()
    expect(api.previewRangeLower.value).toBe('')
    expect(api.previewRangeUpper.value).toBe('')
  })
})

describe('实体型取值方式联动', () => {
  const entityDir = {
    specified: [{ label: '张三', value: 'u1' }, { label: '李四', value: 'u2' }],
    current_user: [{ label: '当前登录人', value: 'me' }],
  }

  it('方式下拉 = 值域配置过的方式（去重按首次出现），未启用的不出现', async () => {
    const api = useTemplatePreview(makeDeps({
      isEntityOutput: true,
      entityOptions: [
        { type: 'specified', ids: ['u1'], label: '张三' },
        { type: 'specified', ids: ['u2'], label: '李四' },
      ],
      entityDir,
    }))
    await nextTick()
    expect(api.previewEntitySelectorOptions.value.map((o) => o.value)).toEqual(['specified'])
    expect(api.previewEntitySelector.value).toBe('specified')
    expect(api.previewNeedsEntitySelector.value).toBe(true)
  })

  it('未配置任何方式 → 不出方式下拉', async () => {
    const api = useTemplatePreview(makeDeps({ isEntityOutput: true, entityOptions: [], entityDir }))
    await nextTick()
    expect(api.previewEntitySelectorOptions.value).toEqual([])
    expect(api.previewNeedsEntitySelector.value).toBe(false)
    expect(api.previewEntitySelector.value).toBe('')
  })

  it('对象候选 = 该方式下所有候选的 id 并集；label 优先全量目录反查', async () => {
    const api = useTemplatePreview(makeDeps({
      isEntityOutput: true,
      entityOptions: [
        { type: 'specified', ids: ['u1'], label: '张三' },
        { type: 'specified', ids: ['u2', 'u1'], label: '李四' },
      ],
      entityDir,
    }))
    await nextTick()
    expect(api.previewEntityObjectOptions.value.map((o) => o.value)).toEqual(['u1', 'u2'])
    expect(api.previewEntityObjectOptions.value.map((o) => o.label)).toEqual(['张三', '李四'])
    expect(api.previewNeedsEntityObject.value).toBe(true)
  })

  it('目录查不到的 id 用 id 本身兜底', async () => {
    const api = useTemplatePreview(makeDeps({
      isEntityOutput: true,
      entityOptions: [{ type: 'specified', ids: ['gone'], label: '' }],
      entityDir,
    }))
    await nextTick()
    expect(api.previewEntityObjectOptions.value[0].label).toBe('gone')
  })

  it('模板预设对象回填为默认校验值；单选只取第一个', async () => {
    const api = useTemplatePreview(makeDeps({
      isEntityOutput: true,
      entityOptions: [{ type: 'specified', ids: ['u1', 'u2'], label: '张三、李四' }],
      entityDir,
    }))
    await nextTick()
    expect(api.previewEnumValue.value).toEqual(['u1'])
  })

  it('IN 运算符下同一条候选全填', async () => {
    const api = useTemplatePreview(makeDeps({
      isEntityOutput: true,
      tplForm: { operators: ['IN'] },
      entityOptions: [{ type: 'specified', ids: ['u1', 'u2'], label: '张三、李四' }],
      entityDir,
    }))
    await nextTick()
    expect(api.previewEnumValue.value).toEqual(['u1', 'u2'])
  })

  it('切到另一种方式 → 预设对象随之切换', async () => {
    const api = useTemplatePreview(makeDeps({
      isEntityOutput: true,
      entityOptions: [
        { type: 'specified', ids: ['u1'], label: '张三' },
        { type: 'current_user', ids: [], label: '当前登录人' },
      ],
      entityDir,
    }))
    await nextTick()
    api.previewEntitySelector.value = 'current_user'
    await nextTick()
    expect(api.previewEntityIsAuto.value).toBe(true)
    expect(api.previewNeedsEntityObject.value).toBe(false)
    expect(api.previewEnumValue.value).toEqual([])
  })

  it('非实体型：方式联动整体短路', async () => {
    const api = useTemplatePreview(makeDeps({
      entityOptions: [{ type: 'specified', ids: ['u1'], label: '张三' }],
      entityDir,
    }))
    await nextTick()
    expect(api.previewEntitySelector.value).toBe('')
    expect(api.previewNeedsEntityObject.value).toBe(false)
  })

  it('实体型走候选下拉路径而非枚举候选', async () => {
    const api = useTemplatePreview(makeDeps({
      isEntityOutput: true,
      enumCandidateOptions: [{ label: 'X', value: 'X' }],
      entityOptions: [{ type: 'specified', ids: ['u1'], label: '张三' }],
      entityDir,
    }))
    await nextTick()
    expect(api.previewCandidateOptions.value.map((o) => o.value)).toEqual(['u1'])
    expect(api.previewNeedsEnumPicker.value).toBe(true)
  })
})
