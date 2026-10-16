/**
 * useTemplateValueDomain.ts — 指标模板「出参类型判定 + 值域配置」域。
 *
 * 从 useMetricsWorkspace.ts 拆出（原 522–687 一段）。本块回答三个问题：
 *   1. 当前选中的指标定义属于哪种出参类型（日期 / 枚举 / 自由文本 / 实体引用 / 数值）；
 *   2. 出参单位有哪些可选项、当前选的是哪个、切换单位要不要回写 calcParams.unit；
 *   3. 值域（segments）怎么枚举候选、怎么校验。
 *
 * 拆出理由：这些派生量是「值域编辑区」的全部输入，体积 166 行但只依赖 3 个外部 ref
 * （tplForm / selectedTemplateDefinition / operatorCatalog）与 useMessage 的 warning，
 * 与加载、提交、版本历史等主流程零耦合。独立成文件后值域规则变更不影响主 composable。
 *
 * 行为零变化：判定顺序（isTextOutput 必须排除实体引用型、isNumberOutput 必须排除实体引用型）
 * 与拆分前逐字一致，注释保留原样以便追溯设计原因。
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import type { MetricDefinition, OptionItem } from '@/api/metrics'
import * as MF from '@/utils/metricsFormat'
import * as TF from '@/utils/metricsTemplateForm'
import * as VD from '@/utils/metricsValueDomain'

export interface TemplateValueDomainDeps {
  /** 模板表单（单位、值域 segments、运算符等全部可编辑字段）。 */
  tplForm: { value: any }
  /** 当前选中的指标定义，决定出参类型与可选单位。 */
  selectedTemplateDefinition: { value: MetricDefinition | undefined }
  /** 运算符目录，用于 supportedOperators 求交集。 */
  operatorCatalog: { value: OptionItem[] }
}

export function useTemplateValueDomain(deps: TemplateValueDomainDeps) {
  const { t } = useI18n()
  const message = useMessage()
  const { tplForm, selectedTemplateDefinition, operatorCatalog } = deps

  // 纯函数侧不接 i18n 的 t，校验/摘要文案在这里集中翻译后以函数形式注入。
  const TF_LABELS: Pick<TF.TemplateFormLabels, 'enumCandidateRequired' | 'enumCandidateEmpty' | 'enumCandidateDuplicate'> = {
    enumCandidateRequired: () => t('metrics.tpl.enumCandidateRequired'),
    enumCandidateEmpty: () => t('metrics.tpl.enumCandidateEmpty'),
    enumCandidateDuplicate: () => t('metrics.tpl.enumCandidateDuplicate'),
  }
  const VD_LABELS: VD.ValueDomainLabels = {
    domainCount: (n) => t('metrics.tpl.domainCount', { n }),
    domainCountTruncated: (total, shown) => t('metrics.tpl.domainCountTruncated', { total, shown }),
    domainStepRequired: () => t('metrics.tpl.domainStepRequired'),
    domainStepPositiveInt: () => t('metrics.tpl.domainStepPositiveInt'),
    domainBoundRequired: () => t('metrics.tpl.domainBoundRequired'),
    domainRelativeRequired: () => t('metrics.tpl.domainRelativeRequired'),
    domainFromBeforeTo: () => t('metrics.tpl.domainFromBeforeTo'),
    domainOverlap: () => t('metrics.tpl.domainOverlap'),
    domainMaxGtMin: () => t('metrics.tpl.domainMaxGtMin'),
    domainStepPositive: () => t('metrics.tpl.domainStepPositive'),
    domainStepInteger: () => t('metrics.tpl.domainStepInteger'),
    domainSegmentOverlap: () => t('metrics.tpl.domainSegmentOverlap'),
  }

  // ===== 日期型出参：单位即「粒度」 =====
  const DATE_GRANULARITIES = MF.DATE_GRANULARITIES
  const DATE_GRANULARITY_DEFAULT = MF.DATE_GRANULARITY_DEFAULT
  const DATE_ENUM_LIMIT = VD.DATE_ENUM_LIMIT
  type GranularityPickerType = 'year' | 'month' | 'date'
  const GRANULARITY_PICKER_TYPE: Record<string, GranularityPickerType> = { 年: 'year', 月: 'month', 日: 'date' }
  const GRANULARITY_VALUE_FORMAT: Record<string, string> = { 年: 'yyyy', 月: 'yyyy-MM', 日: 'yyyy-MM-dd' }

  const isDateOutput = computed<boolean>(() => selectedTemplateDefinition.value?.returnType === 'date')

  // 🔴 实体引用型出参（2026-10-13）：person / department。
  // 后端按 source_path 反查动态字段 field_type 得来（views.py 的 _entity_kinds）。
  // 这类字段虽 returnType==='string'，但对应具体对象 → 走「实体值域」配置，
  // 不能沿用自由文本分支（那边值域整块隐藏，用户报告"人员字段没有值域可配"）。
  const entityKind = computed<'person' | 'department' | ''>(() => {
    const k = (selectedTemplateDefinition.value?.entityKind || '') as 'person' | 'department' | ''
    return k === 'person' || k === 'department' ? k : ''
  })
  const isEntityOutput = computed<boolean>(() => !!entityKind.value)
  const isPersonOutput = computed<boolean>(() => entityKind.value === 'person')
  const isDeptOutput = computed<boolean>(() => entityKind.value === 'department')

  const isEnumOutput = computed<boolean>(
    () => selectedTemplateDefinition.value?.returnType === 'string' && !!selectedTemplateDefinition.value?.isEnum,
  )
  // 实体引用型不是自由文本：isTextOutput 必须排除它，否则值域区被隐藏（本次要修的核心症状）
  const isTextOutput = computed<boolean>(
    () =>
      selectedTemplateDefinition.value?.returnType === 'string' &&
      !selectedTemplateDefinition.value?.isEnum &&
      !entityKind.value,
  )
  // 🔴 必须排除实体引用型：否则人员/部门会掉进数值分支，被渲染成 min/max/步长分段输入框
  const isNumberOutput = computed<boolean>(
    () => !isDateOutput.value && !isEnumOutput.value && !isTextOutput.value && !isEntityOutput.value,
  )
  const showValueDomain = computed<boolean>(() => !!selectedTemplateDefinition.value && !isTextOutput.value)

  const SET_OPERATORS = TF.SET_OPERATORS
  const isFreetextSelected = computed<boolean>(() => isTextOutput.value)
  function operatorDisabledForFreetext(op: string): boolean {
    return isFreetextSelected.value && SET_OPERATORS.includes(op)
  }

  const enumCandidateOptions = computed<{ label: string; value: string }[]>(() =>
    TF.enumCandidateOptions({
      defEnumValues: selectedTemplateDefinition.value?.enumValues || [],
      tplEnumValues: (tplForm.value.paramEnums || []) as string[],
    }),
  )
  const enumCandidateIssue = computed<string>(() =>
    TF.enumCandidateIssue({
      isEnumOutput: isEnumOutput.value,
      tplEnumValues: (tplForm.value.paramEnums || []) as string[],
      labels: TF_LABELS,
    }),
  )

  const outputUnitOptions = computed<string[]>(() => {
    if (isDateOutput.value) return [...DATE_GRANULARITIES]
    const d = selectedTemplateDefinition.value
    const us = d?.units && Array.isArray(d.units) ? d.units.filter(Boolean) : []
    if (us.length) return [...us]
    return d?.unit ? [d.unit] : []
  })
  const currentOutputUnit = computed<string>(() => {
    if (isDateOutput.value) {
      return DATE_GRANULARITIES.includes(tplForm.value.unit) ? tplForm.value.unit : DATE_GRANULARITY_DEFAULT
    }
    return tplForm.value.unit || outputUnitOptions.value[0] || ''
  })

  function emptyDateBound() {
    return { type: 'absolute', date: null as string | null, n: null as number | null, unit: DATE_GRANULARITY_DEFAULT }
  }
  function emptyDateSegment() {
    return { from: emptyDateBound(), to: emptyDateBound(), step: 1, stepUnit: DATE_GRANULARITY_DEFAULT, label: '' }
  }
  const dateBoundTypeOptions = [
    { label: t('metrics.tpl.dateBoundAbsolute'), value: 'absolute' },
    { label: t('metrics.tpl.dateBoundRelative'), value: 'relative' },
  ]
  const dateUnitOptions = DATE_GRANULARITIES.map((u) => ({ label: u, value: u }))
  const datePickerType = computed<GranularityPickerType>(() => GRANULARITY_PICKER_TYPE[currentOutputUnit.value] || 'date')
  const dateValueFormat = computed<string>(() => GRANULARITY_VALUE_FORMAT[currentOutputUnit.value] || 'yyyy-MM-dd')
  const legacyNumericDomainOnDate = computed<boolean>(() => {
    if (!isDateOutput.value) return false
    return (tplForm.value.valueDomain?.segments || []).some(
      (s: any) => s && (s.min !== undefined || s.max !== undefined) && !s.from && !s.to,
    )
  })

  // 显示单位 → 计算参数单位枚举值（仅「月/年」这类需要换算的粒度才写 calcParams.unit）
  const UNIT_TO_CALC = VD.UNIT_TO_CALC

  function setUnit(u: string) {
    tplForm.value.unit = u
    if (isDateOutput.value) return
    if (outputUnitOptions.value.length > 1 && UNIT_TO_CALC[u]) {
      tplForm.value.calcParams.unit = UNIT_TO_CALC[u]
    }
  }
  const valueModeLabel = computed<string>(() => {
    const d = selectedTemplateDefinition.value
    if (!d) return ''
    if (d.valueMode === 'parametric_handler') return `参数化 · ${d.paramType === 'continuous' ? '连续' : '离散'}`
    return '对象路径'
  })

  const paramUnitOptions = computed<string[]>(() => {
    const d = selectedTemplateDefinition.value
    const pus = d?.paramUnits && Array.isArray(d.paramUnits) ? d.paramUnits.filter(Boolean) : []
    return [...pus]
  })
  function setPunit(u: string) {
    tplForm.value.paramUnit = u
  }
  const currentParamUnit = computed<string>(() => {
    const pu = tplForm.value.paramUnit
    if (pu) return pu
    const pus = paramUnitOptions.value
    return pus.length ? pus[0] : ''
  })

  const supportedOperatorOptions = computed<OptionItem[]>(() => {
    const d = selectedTemplateDefinition.value
    if (!d?.supportedOperators?.length) return []
    const allowed = new Set(d.supportedOperators)
    return operatorCatalog.value.filter((o) => allowed.has(o.value))
  })

  function toggleOperator(value: string) {
    if (operatorDisabledForFreetext(value)) {
      message.warning(t('metrics.tpl.freetextNoSetOperator'))
      return
    }
    const set = new Set(tplForm.value.operators)
    if (set.has(value)) set.delete(value)
    else set.add(value)
    tplForm.value.operators = Array.from(set)
  }

  function computeDateDomain(): { items: { text: string; value: string }[]; total: number } {
    return VD.computeDateDomain({
      segments: tplForm.value.valueDomain?.segments || [],
      granularity: currentOutputUnit.value,
    })
  }

  function buildDomainItems(): { text: string; value: string }[] {
    return VD.buildDomainItems({
      segments: tplForm.value.valueDomain?.segments || [],
      unit: tplForm.value.unit || selectedTemplateDefinition.value?.unit || '',
      isDiscrete: selectedTemplateDefinition.value?.paramType === 'discrete',
    })
  }
  //注：domainItems / domainValueCount / domainSummary* 定义在下方实体候选块之后
  //（依赖 entityCandidateOptions，避免 TDZ 与隐式依赖）

  const dateSegmentIssues = computed<(string | null)[]>(() =>
    VD.dateSegmentIssues((tplForm.value.valueDomain?.segments || []) as any[], VD_LABELS),
  )

  return {
    isDateOutput,
    entityKind,
    isEntityOutput,
    isPersonOutput,
    isDeptOutput,
    isEnumOutput,
    isTextOutput,
    isNumberOutput,
    showValueDomain,
    operatorDisabledForFreetext,
    enumCandidateOptions,
    enumCandidateIssue,
    outputUnitOptions,
    currentOutputUnit,
    emptyDateBound,
    emptyDateSegment,
    dateBoundTypeOptions,
    dateUnitOptions,
    datePickerType,
    dateValueFormat,
    legacyNumericDomainOnDate,
    setUnit,
    valueModeLabel,
    paramUnitOptions,
    setPunit,
    currentParamUnit,
    supportedOperatorOptions,
    toggleOperator,
    computeDateDomain,
    buildDomainItems,
    dateSegmentIssues,
  }
}
