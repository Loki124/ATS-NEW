/**
 * metricsTemplatePreview.ts — 模板弹窗「配置预览（结果读条）」的候选项派生纯逻辑。
 *
 * 从 composables/useMetricsWorkspace.ts 抽出的部分（原 1317–1553 一段，
 * 含全文件仅有的 9 个 watch 的数据来源）：
 *   - previewParamOptions：参数取值枚举（含「全部工作经历」开关项与「请先配置参数」占位）
 *   - previewOpOptions：运算符选项（标签带符号前缀）
 *   - previewCheckValueOptions：校验值选项（值域非法 / 无分段时给出禁用占位）
 *   - previewNeeds* 判定：是否免填校验值 / 是否文本输入 / 是否多选枚举 / 是否实体取值方式
 *
 * 约定（重构铁律）：
 *   - 全部为纯函数；**不接受 i18n 的 t**：占位项文案由调用方注入已解析好的文案函数，
 *     单测传 identity mock 即可，无需真实字典与接口。
 *   - 行为与拆分前逐字一致，重构不改判定规则与文案键。
 */
import type { MetricDefinition, OptionItem } from '@/api/metrics'
import { fmtNum, firstEnabledValue, opSymbol } from './metricsFormat'
import type { DomainItem } from './metricsValueDomain'

/** 预览候选项里禁用占位所需的文案函数（由 composable 用 `t('...')` 的薄包装注入）。 */
export interface PreviewLabels {
  /** 「全部」项缺省文案（paramConfig.allText 为空时兜底）。 */
  allOption: () => string
  checkValueDomainInvalid: () => string
  checkValueNoSegment: () => string
}

/** 免填校验值的运算符：IS_EMPTY / IS_NOT_EMPTY */
export const NO_VALUE_OPERATORS = ['IS_EMPTY', 'IS_NOT_EMPTY']
/** 多选校验值的运算符：IN / NOT_IN */
export const MULTI_VALUE_OPERATORS = ['IN', 'NOT_IN']

export interface PreviewOption {
  label: string
  value: string
  disabled?: boolean
}

/** 从选项列表取首个未禁用项的值（各 preview 下拉的默认值来源）。 */
export function firstEnabledPreviewValue(opts: Array<{ value: unknown; disabled?: boolean }>): string {
  return firstEnabledValue(opts)
}

/**
 * 参数取值枚举。
 *   - 非参数化出参 → 无可选项；
 *   - allOption 开启时在首位插入「全部工作经历」项（value 固定 `__all__`）；
 *   - 按 min/max/step 累积枚举，step 非正时按参数类型兜底（离散 1 / 连续 0.5）；
 *   - 一项都产不出时给出禁用的「请先配置参数」占位，避免下拉空不可操作。
 */
export function previewParamOptions(params: {
  showParamConfig: boolean
  paramConfig: {
    min: number | null
    max: number | null
    step: number | null
    prefix: string
    suffix: string
    allOption: boolean
    allText?: string
  }
  isDiscrete: boolean
  labels: Pick<PreviewLabels, 'allOption'>
}): PreviewOption[] {
  const { showParamConfig, paramConfig: c, isDiscrete, labels } = params
  if (!showParamConfig) return []
  const opts: PreviewOption[] = []
  if (c.allOption) opts.push({ label: c.allText || labels.allOption(), value: '__all__' })
  const mn = Number(c.min)
  const mx = Number(c.max)
  let st = Number(c.step)
  if (!st || st <= 0) st = isDiscrete ? 1 : 0.5
  if (Number.isFinite(mn) && Number.isFinite(mx) && st > 0) {
    for (let v = mn; v <= mx + 1e-9; v += st) {
      const vv = fmtNum(v)
      opts.push({ label: `${c.prefix || ''}${vv}${(c.suffix || '').trim()}`, value: vv })
    }
  }
  if (!opts.length) opts.push({ label: '— 请先配置参数 —', value: '', disabled: true })
  return opts
}

/** 运算符选项：优先用模板已选运算符，为空时回落到定义支持的运算符；标签带符号前缀。 */
export function previewOpOptions(params: {
  definition: MetricDefinition | undefined
  formOperators: string[]
  operatorCatalog: OptionItem[]
}): PreviewOption[] {
  const { definition, formOperators, operatorCatalog } = params
  if (!definition) return []
  const keys = (formOperators.length ? formOperators : definition.supportedOperators || []) as string[]
  return keys.map((k) => {
    const o = operatorCatalog.find((x) => x.value === k) || { value: k, label: k }
    return { label: `${opSymbol(k)} ${o.label}`, value: k }
  })
}

/**
 * 校验值选项。
 *   - 值域分段非法 → 禁用占位「值域配置有误」，不让用户基于错数据选值；
 *   - 值域无分段 → 禁用占位「未配置分段」；
 *   - 正常 → 直接用值域候选。
 */
export function previewCheckValueOptions(params: {
  domainError: string
  domainItems: DomainItem[]
  labels: Pick<PreviewLabels, 'checkValueDomainInvalid' | 'checkValueNoSegment'>
}): PreviewOption[] {
  const { domainError, domainItems, labels } = params
  if (domainError) return [{ label: labels.checkValueDomainInvalid(), value: '', disabled: true }]
  if (!domainItems.length) return [{ label: labels.checkValueNoSegment(), value: '', disabled: true }]
  return domainItems.map((i) => ({ label: i.text, value: i.value }))
}

/** 参数样例文本：只展示真实枚举出的参数值（跳过占位项与「全部」项）。 */
export function paramSampleItems(paramOptions: PreviewOption[]): string[] {
  return paramOptions
    .filter((o) => !o.disabled && o.value !== '__all__')
    .map((o) => o.label as string)
}

/**
 * 是否免填校验值：IS_EMPTY / IS_NOT_EMPTY 恒免填；
 * 实体型且选了「当前登录人 / 当前登录人部门」时值由运行时决定，同样免填。
 */
export function previewNeedsNoValue(params: {
  opSelected: string
  isEntityOutput: boolean
  entityIsAuto: boolean
}): boolean {
  const { opSelected, isEntityOutput, entityIsAuto } = params
  return (
    NO_VALUE_OPERATORS.includes(opSelected) || (isEntityOutput && entityIsAuto)
  )
}

/** 是否需要单行文本输入：仅自由文本型出参且未免填校验值时。 */
export function previewNeedsTextInput(params: {
  isTextOutput: boolean
  needsNoValue: boolean
}): boolean {
  const { isTextOutput, needsNoValue } = params
  return isTextOutput && !needsNoValue
}

/** 是否需要多选：枚举型 / 实体型出参且运算符为 IN / NOT_IN。 */
export function previewNeedsMultiEnum(params: {
  isEnumOutput: boolean
  isEntityOutput: boolean
  opSelected: string
}): boolean {
  const { isEnumOutput, isEntityOutput, opSelected } = params
  return (isEnumOutput || isEntityOutput) && MULTI_VALUE_OPERATORS.includes(opSelected)
}

/**
 * 「取值方式」下拉选项 = 模板值域里配置过的方式（去重、按首次出现顺序）。
 * 模板没启用过的方式不出现在预览里 —— 预览不可超出模板限定的可选范围。
 */
export function previewEntitySelectorOptions(params: {
  entityOptions: { type?: string }[]
  typeLabel: (type: string) => string
}): PreviewOption[] {
  const { entityOptions, typeLabel } = params
  const types: string[] = []
  for (const o of entityOptions) {
    if (o?.type && !types.includes(o.type)) types.push(o.type)
  }
  return types.map((tp) => ({ label: typeLabel(tp), value: tp }))
}

/** 是否展示「取值方式」下拉：实体型出参且值域里至少配置过一种方式。 */
export function previewNeedsEntitySelector(params: {
  isEntityOutput: boolean
  selectorOptions: PreviewOption[]
}): boolean {
  const { isEntityOutput, selectorOptions } = params
  return isEntityOutput && selectorOptions.length > 0
}
