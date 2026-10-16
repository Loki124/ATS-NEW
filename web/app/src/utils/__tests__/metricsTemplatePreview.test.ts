/**
 * metricsTemplatePreview.test.ts — 配置预览（结果读条）候选项派生 单测。
 *
 * 覆盖从 useMetricsWorkspace.ts 下沉的判定：
 *   - previewParamOptions：参数枚举、「全部」项、禁用占位
 *   - previewOpOptions：运算符标签带符号、模板已选优先于定义支持
 *   - previewCheckValueOptions：值域非法 / 无分段的禁用占位
 *   - previewNeeds* 系列：免填校验值 / 文本输入 / 多选 / 实体取值方式下拉
 *   - previewEntitySelectorOptions：只出现模板配置过的方式
 */
import { describe, it, expect } from 'vitest'
import {
  previewParamOptions,
  previewOpOptions,
  previewCheckValueOptions,
  paramSampleItems,
  previewNeedsNoValue,
  previewNeedsTextInput,
  previewNeedsMultiEnum,
  previewEntitySelectorOptions,
  previewNeedsEntitySelector,
  firstEnabledPreviewValue,
  NO_VALUE_OPERATORS,
  MULTI_VALUE_OPERATORS,
} from '../metricsTemplatePreview'
import type { MetricDefinition, OptionItem } from '@/api/metrics'

// 纯函数不接 i18n 的 t，改注入「已解析好的文案函数」；identity mock 让断言只关心选键逻辑。
const labels = {
  allOption: () => 'ALL_OPTION',
  checkValueDomainInvalid: () => 'DOMAIN_INVALID',
  checkValueNoSegment: () => 'NO_SEGMENT',
}
const pc = (p: Partial<any> = {}) => ({
  min: 1, max: 3, step: 1, prefix: '', suffix: '', allOption: false, ...p,
})

describe('previewParamOptions', () => {
  it('非参数化出参 → 无选项', () => {
    expect(previewParamOptions({ showParamConfig: false, paramConfig: pc(), isDiscrete: true, labels })).toEqual([])
  })

  it('按 min/max/step 枚举', () => {
    expect(previewParamOptions({ showParamConfig: true, paramConfig: pc(), isDiscrete: true, labels }))
      .toEqual([{ label: '1', value: '1' }, { label: '2', value: '2' }, { label: '3', value: '3' }])
  })

  it('prefix / suffix 拼进 label（suffix 内部空格被 trim 掉）', () => {
    const r = previewParamOptions({
      showParamConfig: true, paramConfig: pc({ min: 1, max: 1, prefix: '≥', suffix: ' 次' }), isDiscrete: true, labels,
    })
    expect(r[0].label).toBe('≥1次')
  })

  it('allOption 开启时首项插入「全部」（固定值 __all__）', () => {
    const r = previewParamOptions({
      showParamConfig: true, paramConfig: pc({ allOption: true, allText: '全部经历' }), isDiscrete: true, labels,
    })
    expect(r[0]).toEqual({ label: '全部经历', value: '__all__' })
  })

  it('allText 为空时回落 i18n 键', () => {
    const r = previewParamOptions({ showParamConfig: true, paramConfig: pc({ allOption: true }), isDiscrete: true, labels })
    expect(r[0].label).toBe('ALL_OPTION')
  })

  it('连续型 step<=0 兜底 0.5', () => {
    const r = previewParamOptions({
      showParamConfig: true, paramConfig: pc({ min: 1, max: 2, step: 0 }), isDiscrete: false, labels,
    })
    expect(r.map((o) => o.value)).toEqual(['1', '1.5', '2'])
  })

  it('min/max 为 null → Number(null)=0 有限，枚举出 0（沿用原实现语义）', () => {
    const r = previewParamOptions({
      showParamConfig: true, paramConfig: pc({ min: null, max: null }), isDiscrete: true, labels,
    })
    expect(r).toEqual([{ label: '0', value: '0' }])
  })

  it('min/max 非有限（undefined → NaN）→ 禁用占位', () => {
    const r = previewParamOptions({
      showParamConfig: true, paramConfig: pc({ min: undefined, max: undefined }), isDiscrete: true, labels,
    })
    expect(r[0].disabled).toBe(true)
    expect(r[0].value).toBe('')
  })

  it('max < min → 禁用占位', () => {
    const r = previewParamOptions({
      showParamConfig: true, paramConfig: pc({ min: 5, max: 1 }), isDiscrete: true, labels,
    })
    expect(r[0].disabled).toBe(true)
  })
})

describe('previewOpOptions', () => {
  const def = (p: Partial<MetricDefinition> = {}) => ({ id: 'm', kind: 'atomic', ...p }) as MetricDefinition
  const catalog: OptionItem[] = [{ value: 'GTE', label: '大于等于' }]

  it('无选中定义 → 空数组', () => {
    expect(previewOpOptions({ definition: undefined, formOperators: [], operatorCatalog: catalog })).toEqual([])
  })

  it('无选中定义时即使模板已选运算符也返回空（definition 为前置守卫）', () => {
    expect(previewOpOptions({ definition: undefined, formOperators: ['GTE'], operatorCatalog: catalog })).toEqual([])
  })

  it('优先用模板已选运算符', () => {
    const r = previewOpOptions({
      definition: def({ supportedOperators: ['GTE', 'LTE'] }),
      formOperators: ['LTE'], operatorCatalog: [{ value: 'LTE', label: '小于等于' }],
    })
    expect(r.map((o) => o.value)).toEqual(['LTE'])
  })

  it('模板未选时回落定义支持的运算符', () => {
    const r = previewOpOptions({
      definition: def({ supportedOperators: ['GTE'] }), formOperators: [],
      operatorCatalog: [{ value: 'GTE', label: '大于等于' }],
    })
    expect(r).toHaveLength(1)
  })

  it('标签带运算符符号前缀', () => {
    const r = previewOpOptions({
      definition: def({ supportedOperators: ['GTE'] }), formOperators: [],
      operatorCatalog: [{ value: 'GTE', label: '大于等于' }],
    })
    expect(r[0].label).toBe('≥ 大于等于')
  })

  it('目录查不到时以 key 自身作标签（符号查不到则为空串）', () => {
    const r = previewOpOptions({
      definition: def({ supportedOperators: ['ZZZ'] }), formOperators: [], operatorCatalog: [],
    })
    expect(r[0].label).toBe(' ZZZ')
  })
})

describe('previewCheckValueOptions', () => {
  it('值域非法 → 禁用占位', () => {
    const r = previewCheckValueOptions({ domainError: '段1：err', domainItems: [], labels })
    expect(r[0]).toEqual({ label: 'DOMAIN_INVALID', value: '', disabled: true })
  })

  it('无分段 → 禁用占位', () => {
    const r = previewCheckValueOptions({ domainError: '', domainItems: [], labels })
    expect(r[0]).toEqual({ label: 'NO_SEGMENT', value: '', disabled: true })
  })

  it('正常 → 透传值域候选', () => {
    const r = previewCheckValueOptions({ domainError: '', domainItems: [{ text: 'a', value: '1' }], labels })
    expect(r).toEqual([{ label: 'a', value: '1' }])
  })
})

describe('paramSampleItems', () => {
  it('跳过占位项与「全部」项', () => {
    expect(paramSampleItems([
      { label: '全部', value: '__all__' },
      { label: '—', value: '', disabled: true },
      { label: '1', value: '1' },
    ])).toEqual(['1'])
  })
})

describe('previewNeedsNoValue', () => {
  it('IS_EMPTY / IS_NOT_EMPTY 恒免填', () => {
    for (const op of NO_VALUE_OPERATORS) {
      expect(previewNeedsNoValue({ opSelected: op, isEntityOutput: false, entityIsAuto: false })).toBe(true)
    }
  })

  it('实体型且取值为运行时决定 → 免填', () => {
    expect(previewNeedsNoValue({ opSelected: 'EQ', isEntityOutput: true, entityIsAuto: true })).toBe(true)
  })

  it('实体型但指定对象 → 需填', () => {
    expect(previewNeedsNoValue({ opSelected: 'EQ', isEntityOutput: true, entityIsAuto: false })).toBe(false)
  })

  it('非免填运算符且非实体 → 需填', () => {
    expect(previewNeedsNoValue({ opSelected: 'EQ', isEntityOutput: false, entityIsAuto: false })).toBe(false)
  })
})

describe('previewNeedsTextInput', () => {
  it('自由文本型且未免填 → 需要输入框', () => {
    expect(previewNeedsTextInput({ isTextOutput: true, needsNoValue: false })).toBe(true)
  })

  it('自由文本型但免填 → 不需要输入框', () => {
    expect(previewNeedsTextInput({ isTextOutput: true, needsNoValue: true })).toBe(false)
  })

  it('非自由文本型 → 不需要输入框', () => {
    expect(previewNeedsTextInput({ isTextOutput: false, needsNoValue: false })).toBe(false)
  })
})

describe('previewNeedsMultiEnum', () => {
  it('枚举型 + IN → 多选', () => {
    expect(previewNeedsMultiEnum({ isEnumOutput: true, isEntityOutput: false, opSelected: 'IN' })).toBe(true)
  })

  it('实体型 + NOT_IN → 多选', () => {
    expect(previewNeedsMultiEnum({ isEnumOutput: false, isEntityOutput: true, opSelected: 'NOT_IN' })).toBe(true)
  })

  it('枚举型 + 非集合运算符 → 单选', () => {
    expect(previewNeedsMultiEnum({ isEnumOutput: true, isEntityOutput: false, opSelected: 'EQ' })).toBe(false)
  })

  it('数值型 + IN → 单选（只对枚举/实体生效）', () => {
    expect(previewNeedsMultiEnum({ isEnumOutput: false, isEntityOutput: false, opSelected: 'IN' })).toBe(false)
  })
})

describe('previewEntitySelectorOptions', () => {
  const label = (x: string) => `L:${x}`

  it('只出现模板配置过的方式（去重保序）', () => {
    expect(previewEntitySelectorOptions({
      entityOptions: [{ type: 'specified' }, { type: 'current_user' }, { type: 'specified' }], typeLabel: label,
    })).toEqual([{ label: 'L:specified', value: 'specified' }, { label: 'L:current_user', value: 'current_user' }])
  })

  it('无候选 → 空数组', () => {
    expect(previewEntitySelectorOptions({ entityOptions: [], typeLabel: label })).toEqual([])
  })

  it('type 缺失的脏候选被忽略', () => {
    expect(previewEntitySelectorOptions({ entityOptions: [{} as any], typeLabel: label })).toEqual([])
  })
})

describe('previewNeedsEntitySelector', () => {
  it('实体型且有配置过的方式 → 显示', () => {
    expect(previewNeedsEntitySelector({ isEntityOutput: true, selectorOptions: [{ label: 'a', value: 'a' }] })).toBe(true)
  })

  it('实体型但无配置方式 → 隐藏', () => {
    expect(previewNeedsEntitySelector({ isEntityOutput: true, selectorOptions: [] })).toBe(false)
  })

  it('非实体型 → 隐藏', () => {
    expect(previewNeedsEntitySelector({ isEntityOutput: false, selectorOptions: [{ label: 'a', value: 'a' }] })).toBe(false)
  })
})

describe('firstEnabledPreviewValue', () => {
  it('取首个未禁用项（value 为空的未禁用项也算命中）', () => {
    expect(firstEnabledPreviewValue([{ value: '' }, { value: 'B' }])).toBe('')
  })

  it('跳过禁用项取下一个', () => {
    expect(firstEnabledPreviewValue([{ value: 'A', disabled: true }, { value: 'B' }])).toBe('B')
  })

  it('空数组 → 空串', () => {
    expect(firstEnabledPreviewValue([])).toBe('')
  })
})
