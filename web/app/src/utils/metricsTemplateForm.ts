/**
 * metricsTemplateForm.ts — 指标模板表单的字段归一、枚举候选校验、保存前校验与 payload 构造纯逻辑。
 *
 * 从 composables/useMetricsWorkspace.ts 抽出的部分：
 *   - emptyTplForm：新建表单的初始形状
 *   - openTemplateEdit 的行 → 表单映射（含 paramConfig / valueDomain 归一）
 *   - enumCandidateOptions / enumCandidateIssue：枚举型候选清单与校验
 *   - buildTemplateSubmitPayload：保存前的字段级校验 + API payload 构造
 *
 * 约定（重构铁律）：
 *   - 全部为纯函数；**不接受 i18n 的 t**：需要文案的规则一律由调用方把
 *     「已解析好的文案函数」注入（labels），单测传 identity mock 即可，无需真实字典与接口。
 *   - 校验「返回首个错误文案 / 空串表示通过」而非直接弹窗，弹窗由调用方做，
 *     这样每条规则都能被独立单测。
 *   - 行为与拆分前逐字一致，重构不改判定规则与文案键。
 */
import type { MetricDefinition, MetricTemplate } from '@/api/metrics'
import { normalizeValueDomain } from './metricsEntityDomain'

/** 保存前校验与分组下拉用到的文案函数集合（由 composable 用 `MF.xxx(t, x)` 薄包装注入）。 */
export interface TemplateFormLabels {
  requiredName: () => string
  selectOneMetric: () => string
  requiredOperators: () => string
  freetextNoSetOperator: () => string
  enumCandidateRequired: () => string
  enumCandidateEmpty: () => string
  enumCandidateDuplicate: () => string
  atomicGroupLabel: () => string
  derivedGroupLabel: () => string
}

/** 自由文本型出参不支持的集合运算符（IN / NOT_IN 对纯文本无意义）。 */
export const SET_OPERATORS = ['IN', 'NOT_IN']

export const ALL_OPTION_LABEL_FALLBACK = '全部工作经历'

export interface ParamConfig {
  min: number | null
  max: number | null
  step: number | null
  prefix: string
  suffix: string
  allOption: boolean
  allText: string
}

export interface TplForm {
  code: string
  name: string
  metricDefinition: string | null
  operators: string[]
  unit: string
  paramUnit: string
  calcParams: Record<string, any>
  paramConfig: ParamConfig
  valueDomain: any
  paramEnums: string[]
  paramAllowNull: boolean
  description: string
  status: string
  [k: string]: any
}

/** 新建模板的表单初始值。 */
export function emptyTplForm(): TplForm {
  return {
    code: '',
    name: '',
    metricDefinition: null,
    operators: [],
    unit: '',
    paramUnit: '',
    calcParams: {},
    paramConfig: {
      min: null,
      max: null,
      step: null,
      prefix: '',
      suffix: '',
      allOption: false,
      allText: ALL_OPTION_LABEL_FALLBACK,
    },
    valueDomain: { segments: [] },
    paramEnums: [],
    paramAllowNull: false,
    description: '',
    status: 'enabled',
  }
}

/** paramConfig 从接口行归一到表单形状（缺失字段补默认值，避免 undefined 进 UI）。 */
export function normalizeParamConfig(cfg: any): ParamConfig {
  return {
    min: cfg.min ?? null,
    max: cfg.max ?? null,
    step: cfg.step ?? null,
    prefix: cfg.prefix ?? '',
    suffix: cfg.suffix ?? '',
    allOption: !!cfg.allOption,
    allText: cfg.allText ?? ALL_OPTION_LABEL_FALLBACK,
  }
}

/** metricKind + atomic/derived 两列 → 表单里 `${kind}:${id}` 的选择键。 */
export function metricSelectionKey(row: Pick<MetricTemplate, 'metricKind' | 'atomicMetric' | 'derivedMetric'>): string | null {
  const m = row.atomicMetric || row.derivedMetric
  return row.metricKind && m ? `${row.metricKind}:${m}` : null
}

/**
 * 编辑态的行 → 表单映射（含值域按出参类型的分流收尾）。
 *
 * 分流规则（载入即分流，避免「实体值域里的 segments」残留干扰既有分支）：
 *   - 自由文本型：剔除集合运算符，值域清空为 segments；
 *   - 枚举型：候选值清空（由用户在模板层重新指定可选范围）；
 *   - 实体引用型：候选值清空，值域 kind 与当前出参不符时重置为该 kind；
 *   - 其余：候选值清空。
 */
export function formFromTemplateRow(params: {
  row: MetricTemplate
  isTextOutput: boolean
  isEnumOutput: boolean
  isEntityOutput: boolean
  entityKind: string
  dateGranularityDefault: string
  isDateOutput: boolean
}): TplForm {
  const { row, isTextOutput, isEnumOutput, isEntityOutput, entityKind, dateGranularityDefault, isDateOutput } =
    params
  const form: TplForm = {
    code: row.code || '',
    name: row.name,
    metricDefinition: metricSelectionKey(row),
    operators: row.operators || [],
    unit: row.unit || '',
    paramUnit: row.paramUnit || '',
    calcParams: { ...(row.calcParams || {}) },
    paramConfig: normalizeParamConfig(row.paramConfig || {}),
    valueDomain: normalizeValueDomain(row.valueDomain || {}),
    paramEnums: row.paramEnums || [],
    paramAllowNull: !!row.paramAllowNull,
    description: row.description || '',
    status: row.status || 'enabled',
  }
  if (isTextOutput) {
    form.operators = form.operators.filter((op: string) => !SET_OPERATORS.includes(op))
    form.valueDomain = { segments: [] }
  } else if (isEnumOutput) {
    form.paramEnums = []
  } else if (isEntityOutput) {
    form.paramEnums = []
    if (form.valueDomain.kind !== entityKind) {
      form.valueDomain = { kind: entityKind, options: [] }
    }
  } else {
    form.paramEnums = []
  }
  if (isDateOutput && !form.unit) {
    form.unit = dateGranularityDefault
  }
  return form
}

/**
 * 枚举型候选清单：定义自带值与模板层候选合并，按首次出现去重、剔除空串。
 * 定义值在前，保证既有配置项排在前面。
 */
export function enumCandidateOptions(params: {
  defEnumValues: string[] | undefined
  tplEnumValues: string[]
}): { label: string; value: string }[] {
  const { defEnumValues, tplEnumValues } = params
  const seen = new Set<string>()
  const out: { label: string; value: string }[] = []
  for (const v of [...(defEnumValues || []), ...(tplEnumValues || [])]) {
    const s = String(v ?? '').trim()
    if (!s || seen.has(s)) continue
    seen.add(s)
    out.push({ label: s, value: s })
  }
  return out
}

/**
 * 枚举型候选校验：至少一条 → 无空白项 → 无重复项。
 * 非枚举型（isEnumOutput=false）不校验，返回空串。
 */
export function enumCandidateIssue(params: {
  isEnumOutput: boolean
  tplEnumValues: string[]
  labels: Pick<TemplateFormLabels, 'enumCandidateRequired' | 'enumCandidateEmpty' | 'enumCandidateDuplicate'>
}): string {
  const { isEnumOutput, tplEnumValues, labels } = params
  if (!isEnumOutput) return ''
  const vals = tplEnumValues || []
  if (!vals.length) return labels.enumCandidateRequired()
  if (vals.some((v) => !String(v ?? '').trim())) return labels.enumCandidateEmpty()
  if (new Set(vals.map((v) => String(v).trim())).size !== vals.length) {
    return labels.enumCandidateDuplicate()
  }
  return ''
}

/**
 * 保存前的字段级校验，按 submitTemplate 中的固定顺序短路：
 *   名称必填 → 必选且合法选中一个指标 → 运算符非空 →
 *   自由文本型不得含集合运算符 → 枚举候选校验 → 实体候选校验 → 值域分段校验。
 *
 * 返回 '' 表示全部通过；否则返回首个错误文案（调用方原样弹 warning）。
 * 枚举 / 实体 / 值域三项的文案由调用方算好传入，避免此处反向依赖其它模块。
 */
export function templateSubmitIssue(params: {
  form: TplForm
  isTextOutput: boolean
  enumIssue: string
  entityIssue: string
  domainError: string
  labels: Pick<TemplateFormLabels, 'requiredName' | 'selectOneMetric' | 'requiredOperators' | 'freetextNoSetOperator'>
}): string {
  const { form, isTextOutput, enumIssue, entityIssue, domainError, labels } = params
  if (!form.name?.trim()) return labels.requiredName()
  if (!form.metricDefinition) return labels.selectOneMetric()
  const [kind, id] = String(form.metricDefinition).split(':')
  if (!kind || !id) return labels.selectOneMetric()
  if (!form.operators?.length) return labels.requiredOperators()
  if (isTextOutput && form.operators.some((op: string) => SET_OPERATORS.includes(op))) {
    return labels.freetextNoSetOperator()
  }
  if (enumIssue) return enumIssue
  if (entityIssue) return entityIssue
  if (domainError) return domainError
  return ''
}

/**
 * 构造 createMetricTemplate / updateMetricTemplate 的 payload。
 * 与分段校验一致：自由文本 / 枚举型出参的值域一律落空 segments；
 * 枚举型的 paramEnums 才落库（其余类型候选无意义），运算符在自由文本型下剔除集合运算符。
 */
export function buildTemplateSubmitPayload(params: {
  form: TplForm
  isTextOutput: boolean
  isEnumOutput: boolean
  valueDomain: any
}): Record<string, any> {
  const { form, isTextOutput, isEnumOutput, valueDomain } = params
  const [kind, id] = String(form.metricDefinition || '').split(':')
  return {
    name: form.name,
    atomicMetric: kind === 'atomic' ? id : null,
    derivedMetric: kind === 'derived' ? id : null,
    operators: isTextOutput
      ? form.operators.filter((op: string) => !SET_OPERATORS.includes(op))
      : form.operators,
    unit: form.unit,
    paramUnit: form.paramUnit,
    calcParams: form.calcParams,
    paramConfig: form.paramConfig,
    valueDomain: isEnumOutput || isTextOutput ? { segments: [] } : valueDomain,
    paramEnums: isEnumOutput ? form.paramEnums : [],
    paramAllowNull: form.paramAllowNull,
    description: form.description,
    status: form.status || 'enabled',
  }
}

/** 指标定义 → 模板表单的分组下拉项（原子 / 派生两组，空组不出现）。 */
export function metricDefinitionGroupOptions(params: {
  definitions: MetricDefinition[]
  labels: Pick<TemplateFormLabels, 'atomicGroupLabel' | 'derivedGroupLabel'>
}): { type: string; label: string; key: string; children: { label: string; value: string }[] }[] {
  const { definitions, labels } = params
  const atomic = definitions.filter((d) => d.kind === 'atomic')
  const derived = definitions.filter((d) => d.kind === 'derived')
  const toOption = (d: MetricDefinition) => ({
    label: `${d.name}（${d.dataSource}）`,
    value: `${d.kind}:${d.id}`,
  })
  const groups: { type: string; label: string; key: string; children: { label: string; value: string }[] }[] = []
  if (atomic.length) {
    groups.push({
      type: 'group',
      label: labels.atomicGroupLabel(),
      key: 'atomic',
      children: atomic.map(toOption),
    })
  }
  if (derived.length) {
    groups.push({
      type: 'group',
      label: labels.derivedGroupLabel(),
      key: 'derived',
      children: derived.map(toOption),
    })
  }
  return groups
}

/** 「已选指标定义」反查：表单里的 `${kind}:${id}` → 定义行。 */
export function findSelectedDefinition(
  definitions: MetricDefinition[],
  key: string | null | undefined,
): MetricDefinition | undefined {
  if (!key) return undefined
  const [kind, id] = String(key).split(':')
  return definitions.find((d) => d.kind === kind && d.id === id)
}
