/**
 * useTemplatePreview.ts — 模板弹窗「配置预览（结果读条）」域。
 *
 * 从 useMetricsWorkspace.ts 拆出（原 1145–1376 一段）。本域是**纯本地 UI 态**：
 *   - 不发任何接口请求，不碰 tplForm 之外的可写状态；
 *   - 7 个 ref（4 个联动选中项 + 文本 + 区间上下界 + 枚举值数组）
 *     + 9 个 watch 是全文件唯一的响应式密集区。
 *
 * 拆出原因：
 *   1. 该段自成闭环（只读 tplForm 与少量判定 computed），与模板 CRUD / 接口编排无关；
 *   2. 9 个 watch 的时序语义（immediate 回填、切运算符清文本、切回单选保留首值）
 *      集中在一处才好维护，也才有可能补组件级测试。
 *
 * 与主 composable 的耦合通过 `PreviewDeps` 显式声明（只读依赖 + 少量回调），
 * 不用 provide/inject，避免再造一个隐式单例。
 *
 * 行为零变化：所有 watch 的触发时机与赋值顺序与拆分前逐字一致。
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MetricDefinition, OptionItem } from '@/api/metrics'
import * as PV from '@/utils/metricsTemplatePreview'
import * as ED from '@/utils/metricsEntityDomain'
import { firstEnabledValue } from '@/utils/metricsFormat'
import type { DomainItem } from '@/utils/metricsValueDomain'

export interface PreviewOption {
  label: string
  value: string
  disabled?: boolean
}

export interface PreviewDeps {
  /** 模板表单（只读；本域不回写 tplForm 本身）。 */
  tplForm: { value: any }
  /** 已选中的指标定义（只读）。 */
  selectedTemplateDefinition: { value: MetricDefinition | undefined }
  /** 该定义是否为参数化配置型（决定是否出参数下拉）。 */
  showTemplateParamConfig: { value: boolean }
  /** 出参类型判定（决定预览区渲染分支）。 */
  isTextOutput: { value: boolean }
  isEnumOutput: { value: boolean }
  isEntityOutput: { value: boolean }
  /** 运算符目录（用于给运算符加符号前缀与中文名）。 */
  operatorCatalog: { value: OptionItem[] }
  /** 值域候选清单与校验错误（由主 composable 的值域域提供）。 */
  domainItems: { value: DomainItem[] }
  domainErrorText: { value: string }
  /** 枚举型候选清单（枚举型预览的选项源）。 */
  enumCandidateOptions: { value: PreviewOption[] }
  /** 实体值域：当前已配置候选清单。 */
  entityOptions: { value: any[] }
  /** 实体值域：某取值方式下的对象下拉（按类型返回人员/身份/部门）。 */
  entityOptionsForType: (type: string) => PreviewOption[]
  /** 实体取值方式的中文标签。 */
  entityTypeLabel: (type: string) => string
}

export function useTemplatePreview(deps: PreviewDeps) {
  const { t } = useI18n()
  const {
    tplForm,
    selectedTemplateDefinition,
    showTemplateParamConfig,
    isTextOutput,
    isEnumOutput,
    isEntityOutput,
    operatorCatalog,
    domainItems,
    domainErrorText,
    enumCandidateOptions,
    entityOptions,
    entityOptionsForType,
    entityTypeLabel,
  } = deps

  // 纯函数侧不接 i18n 的 t，占位文案在这里集中翻译后以函数形式注入。
  const PV_LABELS: PV.PreviewLabels = {
    allOption: () => t('metrics.tpl.allOption'),
    checkValueDomainInvalid: () => t('metrics.tpl.checkValueDomainInvalid'),
    checkValueNoSegment: () => t('metrics.tpl.checkValueNoSegment'),
  }
  const ED_LABELS: Pick<ED.EntityDomainLabels, 'selectAll' | 'selectAllOff'> = {
    selectAll: () => t('metrics.tpl.selectAll'),
    selectAllOff: () => t('metrics.tpl.selectAllOff'),
  }

  const previewMetricSelected = ref('current')
  const previewParamSelected = ref('')
  const previewOpSelected = ref('')
  const previewValueSelected = ref('')

  function firstEnabledValueOf(opts: any[]): string {
    return PV.firstEnabledPreviewValue(opts)
  }

  const previewMetricItemOptions = computed<any[]>(() => [
    { label: tplForm.value.name || t('metrics.tpl.unnamed'), value: 'current' },
  ])
  watch(previewMetricItemOptions, (opts) => { previewMetricSelected.value = firstEnabledValue(opts) }, { immediate: true })

  const previewParamOptions = computed<any[]>(() =>
    PV.previewParamOptions({
      showParamConfig: showTemplateParamConfig.value,
      paramConfig: tplForm.value.paramConfig,
      isDiscrete: selectedTemplateDefinition.value?.paramType === 'discrete',
      labels: PV_LABELS,
    }),
  )
  watch(previewParamOptions, (opts) => { previewParamSelected.value = firstEnabledValue(opts) }, { immediate: true })

  const paramSampleItems = computed<string[]>(() => PV.paramSampleItems(previewParamOptions.value))

  const previewOpOptions = computed<any[]>(() =>
    PV.previewOpOptions({
      definition: selectedTemplateDefinition.value,
      formOperators: tplForm.value.operators,
      operatorCatalog: operatorCatalog.value,
    }),
  )
  watch(previewOpOptions, (opts) => { previewOpSelected.value = firstEnabledValue(opts) }, { immediate: true })

  const previewCheckValueOptions = computed<any[]>(() =>
    PV.previewCheckValueOptions({
      domainError: domainErrorText.value,
      domainItems: domainItems.value,
      labels: PV_LABELS,
    }),
  )
  watch(previewCheckValueOptions, (opts) => { previewValueSelected.value = firstEnabledValue(opts) }, { immediate: true })

  const NO_VALUE_OPERATORS = PV.NO_VALUE_OPERATORS
  const MULTI_VALUE_OPERATORS = PV.MULTI_VALUE_OPERATORS
  /**
   * 校验值真源（枚举型 / 实体型共用）。统一以数组承载：
   * 单选态只是"取第 0 个"，切到多选不丢已选值，切回单选也不炸。
   */
  const previewEnumValue = ref<string[]>([])
  const previewNeedsNoValue = computed<boolean>(() =>
    // 🔴 实体型选「当前登录人」：值由运行时决定，同样无需填校验值
    PV.previewNeedsNoValue({
      opSelected: previewOpSelected.value,
      isEntityOutput: isEntityOutput.value,
      entityIsAuto: previewEntityIsAuto.value,
    }),
  )
  const previewNeedsTextInput = computed<boolean>(() =>
    PV.previewNeedsTextInput({ isTextOutput: isTextOutput.value, needsNoValue: previewNeedsNoValue.value }),
  )
  const previewNeedsMultiEnum = computed<boolean>(() =>
    PV.previewNeedsMultiEnum({
      isEnumOutput: isEnumOutput.value,
      isEntityOutput: isEntityOutput.value,
      opSelected: previewOpSelected.value,
    }),
  )
  // 🔴 实体引用型预览（2026-10-14 三次修正，兵哥定稿）：
  //   预览行新增「取值方式」下拉（第 4 个框），选中指定人员/指定身份后**联动出对象下拉**；
  //   对象候选 = 值域配置中**该方式配置过的候选值并集**（≤ 值域配置，不超出配置范围）。
  const previewEntitySelector = ref<string>('')
  /** 方式下拉选项 = 模板层配置过的方式（去重），模板没启用的方式不出现 */
  const previewEntitySelectorOptions = computed<{ label: string; value: string }[]>(() =>
    PV.previewEntitySelectorOptions({ entityOptions: entityOptions.value, typeLabel: entityTypeLabel }),
  )
  const previewNeedsEntitySelector = computed<boolean>(() =>
    PV.previewNeedsEntitySelector({
      isEntityOutput: isEntityOutput.value,
      selectorOptions: previewEntitySelectorOptions.value,
    }),
  )
  /** 当前登录人 / 所在部门：无对象下拉 */
  const previewEntityIsAuto = computed<boolean>(
    () => previewEntitySelector.value === 'current_user' || previewEntitySelector.value === 'current_user_dept',
  )
  /**
   * 对象下拉候选 = 值域配置中该方式的候选值并集（同一方式可配多条候选，取 id 并集去重）。
   * label 优先用全量目录反查（防改名后快照过期），查不到兜底用 id 本身。
   */
  const previewEntityObjectOptions = computed<{ label: string; value: string }[]>(() => {
    const dir = new Map(entityOptionsForType(previewEntitySelector.value).map((o) => [o.value, o.label]))
    const out: { label: string; value: string }[] = []
    const seen = new Set<string>()
    for (const o of entityOptions.value) {
      if (o?.type !== previewEntitySelector.value) continue
      for (const id of Array.isArray(o.ids) ? o.ids : []) {
        if (!id || seen.has(id)) continue
        seen.add(id)
        out.push({ label: dir.get(id) || id, value: id })
      }
    }
    return out
  })
  const previewNeedsEntityObject = computed<boolean>(
    () => isEntityOutput.value && previewNeedsEntitySelector.value && !previewEntityIsAuto.value,
  )
  // 方式切换：默认选中列表里第一个；并把模板预设对象回填为默认校验值（兵哥要求 2）
  function applyEntityPreviewPreset() {
    if (!isEntityOutput.value) return
    const opts = previewEntitySelectorOptions.value
    if (!opts.some((o) => o.value === previewEntitySelector.value)) {
      previewEntitySelector.value = opts[0]?.value || ''
    }
    // 模板预设的对象回填为默认校验值（单选态只取第一个，多选态全填）
    const preset = [
      ...new Set(
        entityOptions.value
          .filter((o) => o.type === previewEntitySelector.value)
          .flatMap((o) => (Array.isArray(o.ids) ? o.ids : []))
          .filter(Boolean),
      ),
    ]
    previewEnumValue.value = previewNeedsMultiEnum.value ? preset : preset.slice(0, 1)
  }
  watch([previewEntitySelectorOptions, previewEntitySelector], applyEntityPreviewPreset, { immediate: true })

  // 枚举型与实体型共用候选下拉（实体型仅在需要对象框时走该路径）
  const previewNeedsEnumPicker = computed<boolean>(
    () => (isEnumOutput.value || previewNeedsEntityObject.value) && !previewNeedsNoValue.value,
  )
  /** 预览候选下拉的选项源：实体型用该方式配置过的候选值，枚举型用候选值清单 */
  const previewCandidateOptions = computed<{ label: string; value: string }[]>(() =>
    previewNeedsEntityObject.value ? previewEntityObjectOptions.value : enumCandidateOptions.value,
  )
  /** 多选态（属于集合/不属于集合）时顶部插入「全部」哨兵项 */
  const previewSelectOptions = computed<{ label: string; value: string }[]>(() =>
    previewNeedsMultiEnum.value
      ? ED.withSelectAllOption(previewCandidateOptions.value, previewEnumValue.value, ED_LABELS)
      : previewCandidateOptions.value,
  )
  /** 预览对象框是否处于全选（标签区据此折叠为单个「全部」） */
  const previewIsAllSelected = computed<boolean>(() =>
    ED.isAllSelected(previewCandidateOptions.value, previewEnumValue.value),
  )

  /**
   * 🔴 单选态下 n-select 只吃标量，多选态下只吃数组 —— 类型不对会静默渲染成 placeholder
   * （"预填了值但框里空的"就是这个坑）。用可写 computed 做形态适配，
   * 底层仍以 previewEnumValue 为唯一真源，切换运算符/取值方式不丢值。
   * 多选态还要把「全选」哨兵项翻译成真实 id 列表。
   */
  const previewEnumValueModel = computed<string | string[] | null>({
    get: () => {
      if (!previewNeedsMultiEnum.value) return previewEnumValue.value[0] ?? null
      const base = previewCandidateOptions.value
      return ED.isAllSelected(base, previewEnumValue.value)
        ? [ED.SELECT_ALL, ...previewEnumValue.value]
        : previewEnumValue.value
    },
    set: (v) => {
      const arr = Array.isArray(v) ? v : v === null || v === undefined || v === '' ? [] : [String(v)]
      if (!previewNeedsMultiEnum.value) {
        previewEnumValue.value = arr
        return
      }
      const base = previewCandidateOptions.value
      previewEnumValue.value = ED.applySelectAll(
        arr,
        base,
        ED.isAllSelected(base, previewEnumValue.value),
      )
    },
  })

  const previewTextValue = ref('')
  const previewRegexIssue = computed<string>(() => {
    if (previewOpSelected.value !== 'REGEX_MATCH') return ''
    const raw = previewTextValue.value
    if (!raw || !raw.trim()) return t('metrics.tpl.regexRequired')
    try {
      new RegExp(raw)
      return ''
    } catch {
      return t('metrics.tpl.regexInvalid')
    }
  })
  const previewTextPlaceholder = computed<string>(() =>
    previewOpSelected.value === 'REGEX_MATCH'
      ? t('metrics.tpl.regexPlaceholder')
      : t('metrics.tpl.checkValuePlaceholder'),
  )
  watch(previewOpSelected, (op) => {
    if (op !== 'REGEX_MATCH') previewTextValue.value = ''
  })
  watch(previewNeedsMultiEnum, (multi) => {
    if (multi) return
    // 切回单选：保留已选的第 0 个；一个都没选才退回候选首项
    if (previewEnumValue.value.length) {
      previewEnumValue.value = previewEnumValue.value.slice(0, 1)
      return
    }
    const first = previewCandidateOptions.value[0]?.value
    if (first) previewEnumValue.value = [first]
  })

  const RANGE_OPERATOR = 'BETWEEN'
  const previewNeedsRangeValue = computed<boolean>(() => previewOpSelected.value === RANGE_OPERATOR)
  const previewRangeLower = ref('')
  const previewRangeUpper = ref('')

  function enabledCheckValues(): string[] {
    return previewCheckValueOptions.value.filter((o: any) => !o.disabled).map((o: any) => o.value as string)
  }

  watch(previewNeedsRangeValue, (need) => {
    if (need) {
      const vals = enabledCheckValues()
      if (!previewRangeLower.value) previewRangeLower.value = vals[0] ?? ''
      if (!previewRangeUpper.value) previewRangeUpper.value = vals[vals.length - 1] ?? ''
      if (previewRangeLower.value === previewRangeUpper.value && vals.length > 1) {
        previewRangeUpper.value = vals[vals.length - 1]
      }
    } else if (previewRangeLower.value) {
      previewValueSelected.value = previewRangeLower.value
    }
  })

  watch(previewCheckValueOptions, () => {
    if (!previewNeedsRangeValue.value) return
    const vals = enabledCheckValues()
    if (!vals.includes(previewRangeLower.value)) previewRangeLower.value = vals[0] ?? ''
    if (!vals.includes(previewRangeUpper.value)) previewRangeUpper.value = vals[vals.length - 1] ?? ''
  })

  return {
    previewMetricSelected,
    previewParamSelected,
    previewOpSelected,
    previewValueSelected,
    previewMetricItemOptions,
    previewParamOptions,
    previewOpOptions,
    previewCheckValueOptions,
    paramSampleItems,
    previewEnumValue,
    previewEnumValueModel,
    previewNeedsNoValue,
    previewNeedsTextInput,
    previewNeedsMultiEnum,
    previewNeedsEnumPicker,
    previewNeedsRangeValue,
    previewRangeLower,
    previewRangeUpper,
    previewTextValue,
    previewRegexIssue,
    previewTextPlaceholder,
    previewEntitySelector,
    previewEntitySelectorOptions,
    previewNeedsEntitySelector,
    previewNeedsEntityObject,
    previewEntityIsAuto,
    previewEntityObjectOptions,
    previewCandidateOptions,
    previewSelectOptions,
    previewIsAllSelected,
    firstEnabledValueOf,
    enabledCheckValues,
    NO_VALUE_OPERATORS,
    MULTI_VALUE_OPERATORS,
  }
}
