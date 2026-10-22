<template>
  <!--
    动态策略「配置权限与规则」弹窗（全新独立组件）。
    职责单一：编辑某个模块的「写动作集合 actions」与「授权条件组 groups」。
    两级布尔表达式均由用户手填（与角色数据权限弹窗 RuleConfigModal 完全同构）：
      · 组内表达式 group.expr —— 引用本组条件序号 1..N，留空 = 且 (AND)；
      · 组间组合 expr        —— 引用条件组序号 1..N，留空 = 或 (OR)。
    保存前逐组校验表达式语法（validateExpr，与后端 expr_compiler 同口径），
    非法即拦截并提示，绝不放行 —— 否则 enforcement 编译期抛错被吞 →
    Q(pk__in=[]) → 该模块对所有人静默全拒（安全事变了）。
    mode 由父组件计算，本弹窗不负责。
    条件行仅支持关系维度（relationship），不渲染任何属性条件 / 权限模板引用 UI。
  -->
  <n-modal
    :show="show"
    preset="card"
    :title="modalTitle"
    :style="{ width: '860px', maxWidth: '95vw' }"
    :content-style="{ height: 'min(70vh, 720px)', overflowY: 'auto', padding: '16px 20px' }"
    :mask-closable="false"
    :bordered="false"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <!-- ① 受限功能：后端 options.governedResources[moduleKey] 下发的受管控资源 -->
    <section class="section">
      <div class="section-head">
        <h3 class="section-title">{{ t('pages.settings.DynamicStrategy.s25') }}</h3>
        <div class="section-ops">
          <n-button size="tiny" tertiary @click="selectAll">{{ t('pages.settings.DynamicStrategy.s26') }}</n-button>
          <n-button size="tiny" tertiary @click="clearActions">{{ t('pages.settings.DynamicStrategy.s27') }}</n-button>
        </div>
      </div>
      <n-checkbox-group :value="localResourceCodes" @update:value="(v: Array<string | number>) => onResourceCodesChange(v)">
        <div class="action-grid">
          <label v-for="r in governedResources" :key="r.resourceCode" class="action-item">
            <n-checkbox :value="r.resourceCode">{{ r.resourceName }}</n-checkbox>
          </label>
        </div>
      </n-checkbox-group>
      <p v-if="!governedResources.length" class="gov-empty">
        {{ t('pages.settings.DynamicStrategy.s46') }}
      </p>
    </section>

    <!-- ② 授权条件：多条件组列表（仅 relationship）；组内/组间关系由手填表达式决定（留空 = 且/或） -->
    <section class="section">
      <div class="section-head">
        <h3 class="section-title">{{ t('pages.settings.DynamicStrategy.s28') }}</h3>
      </div>

      <div v-if="localGroups.length" class="group-list">
        <template v-for="(g, gi) in localGroups" :key="g.id">
          <div class="group-block">
            <div class="group-head">
              <span class="group-title">
                <n-icon :component="ReorderFourOutline" />
                {{ t('dataperm.modal.groupTitle', { n: gi + 1 }) }}
              </span>
              <div class="group-head-actions">
                <a @click="addCondition(g)">
                  <n-icon :component="AddOutline" /> {{ t('dataperm.modal.addCondition') }}
                </a>
                <a v-if="localGroups.length > 1" class="danger" @click="delGroup(gi)">
                  <n-icon :component="TrashOutline" /> {{ t('dataperm.modal.delGroup') }}
                </a>
              </div>
            </div>

            <!-- 组内条件行：单行铁律（序号 → 维度 → 运算符 → 取值来源 → 业务值 → 删除） -->
            <div
              v-for="(c, ci) in g.conditions"
              :key="c.id"
              class="cond-row"
            >
              <span class="cond-seq">{{ ci + 1 }}</span>
              <n-select
                :value="c.dimension"
                :options="dimensionOptions"
                size="small"
                class="cond-dim"
                @update:value="(v: string) => onDimensionChange(c, v)"
              />
              <n-select
                :value="unifiedOperatorValue(c)"
                :options="unifiedOperatorOptions(c)"
                size="small"
                class="cond-verb"
                @update:value="(v: string) => onUnifiedOperatorChange(c, v)"
              />
              <n-select
                v-if="supportsDynamic(c) && !noValueOperator(c)"
                :value="rangeValue(c)"
                :options="rangeOptions(c)"
                size="small"
                class="cond-src"
                @update:value="(v: string) => onRangeChange(c, v)"
              />
              <n-select
                v-if="isStatic(c) && !noValueOperator(c)"
                :value="validValueIds(c)"
                :options="valueOptions(c)"
                size="small"
                multiple
                filterable
                clearable
                max-tag-count="responsive"
                class="cond-val"
                :placeholder="t('dataperm.modal.valuesPlaceholder')"
                @update:value="(ids: Array<string | number>) => onValuesChange(c, ids)"
              />
              <n-tag
                v-else-if="!noValueOperator(c)"
                size="small"
                :bordered="false"
                class="cond-val-readonly"
              >
                <span class="ellipsis-text">{{ rangeLabel(c) }}</span>
              </n-tag>
              <span class="cond-spacer" />
              <button
                class="cond-del"
                type="button"
                :disabled="g.conditions.length <= 1"
                @click="delCondition(g, ci)"
              >
                <n-icon :component="TrashOutline" />
              </button>
            </div>

            <!-- 组内表达式（用户手填，引用本组条件序号 1..N；留空 = 且 AND）。
                 交互与 RuleConfigModal 逐行同构：label + info 图标 hover 提示
                 + 输入框 + 校验状态图标（ok 绿勾 / bad 红叹，hover 出原因）。 -->
            <div class="group-inner-row">
              <span class="inner-label">
                {{ t('dataperm.modal.expr.intraLabel') }}
                <n-tooltip trigger="hover">
                  <template #trigger>
                    <button
                      type="button"
                      class="hint-btn"
                      :aria-label="t('dataperm.modal.expr.intraPlaceholder')"
                    >
                      <n-icon :component="InformationCircleOutline" />
                    </button>
                  </template>
                  {{ t('dataperm.modal.expr.intraPlaceholder') }}
                </n-tooltip>
              </span>
              <n-input
                v-model:value="g.expr"
                size="small"
                clearable
                placeholder=""
                :class="{ 'input-error': !!intraError(g) }"
              />
              <n-tooltip trigger="hover">
                <template #trigger>
                  <button
                    type="button"
                    class="expr-status"
                    :class="intraError(g) ? 'bad' : 'ok'"
                    :aria-label="intraError(g) ? t('dataperm.modal.expr.invalid', { reason: intraError(g) || '' }) : t('dataperm.modal.expr.valid')"
                  >
                    <n-icon :component="intraError(g) ? AlertCircleOutline : CheckmarkCircleOutline" />
                  </button>
                </template>
                {{ intraError(g) ? t('dataperm.modal.expr.invalid', { reason: intraError(g) || '' }) : t('dataperm.modal.expr.valid') }}
              </n-tooltip>
            </div>
          </div>
        </template>
      </div>

      <!-- 空状态（虚线框） -->
      <div v-else class="empty-state">
        <p class="empty-text">{{ t('dataperm.modal.empty') }}</p>
        <n-button size="small" type="primary" secondary @click="addGroup">
          + {{ t('dataperm.modal.addGroup') }}
        </n-button>
      </div>

      <!-- 添加条件组：文字链 -->
      <a v-if="localGroups.length" class="add-link" @click="addGroup">
        <n-icon :component="AddOutline" /> {{ t('dataperm.modal.addGroup') }}
      </a>

      <!-- 组间组合（引用条件组序号 1..N；留空 = 或 OR）。提示同上：info 图标 + 状态图标。
           自定义组间表达式下，此输入行 + 预览句是真实关系的唯一载体（已移除静态「或 (OR)」分隔符，
           它会把用户配的「且」显示成「或」，属于放大权限的误导）。 -->
      <div v-if="localGroups.length" class="inter-block">
        <div class="group-inner-row">
          <span class="inner-label">
            {{ t('dataperm.modal.expr.interLabel') }}
            <n-tooltip trigger="hover">
              <template #trigger>
                <button
                  type="button"
                  class="hint-btn"
                  :aria-label="t('dataperm.modal.expr.interPlaceholder')"
                >
                  <n-icon :component="InformationCircleOutline" />
                </button>
              </template>
              {{ t('dataperm.modal.expr.interPlaceholder') }}
            </n-tooltip>
          </span>
          <n-input
            v-model:value="localInter"
            size="small"
            clearable
            placeholder=""
            :class="{ 'input-error': !!interError }"
          />
          <n-tooltip trigger="hover">
            <template #trigger>
              <button
                type="button"
                class="expr-status"
                :class="interError ? 'bad' : 'ok'"
                :aria-label="interError ? t('dataperm.modal.expr.invalid', { reason: interError || '' }) : t('dataperm.modal.expr.valid')"
              >
                <n-icon :component="interError ? AlertCircleOutline : CheckmarkCircleOutline" />
              </button>
            </template>
            {{ interError ? t('dataperm.modal.expr.invalid', { reason: interError || '' }) : t('dataperm.modal.expr.valid') }}
          </n-tooltip>
        </div>
      </div>
    </section>

    <!-- ③ 配置预览：实时显示已选功能项数与条件组数 -->
    <section class="section">
      <div class="section-head">
        <h3 class="section-title">{{ t('pages.settings.DynamicStrategy.s33') }}</h3>
      </div>
      <div class="preview-box">
        <span v-if="localResourceCodes.length || localGroups.length" class="preview-text">
          {{ t('pages.settings.DynamicStrategy.s42', { conditions: conditionText, functions: functionsText }) }}
        </span>
        <span v-else class="preview-text">{{ t('pages.settings.DynamicStrategy.s40') }}</span>
      </div>
    </section>

    <template #footer>
      <n-space justify="space-between">
        <n-button @click="clearAll">{{ t('pages.settings.DynamicStrategy.s27') }}</n-button>
        <n-space>
          <n-button @click="emit('update:show', false)">{{ t('pages.settings.DynamicStrategy.s11') }}</n-button>
          <n-button type="primary" @click="apply">{{ t('pages.settings.DynamicStrategy.s37') }}</n-button>
        </n-space>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
/**
 * StrategyModuleConfigModal.vue — 动态策略「配置权限与规则」弹窗。
 *
 * 关系维度条件（relationship）的全部逻辑原样移植自 RuleConfigModal.vue：
 * dimensionOptions / unifiedOperatorValue / unifiedOperatorOptions /
 * supportsDynamic / noValueOperator / isStatic / rangeValue / rangeOptions /
 * rangeLabel / valueOptions / validValueIds / onDimensionChange /
 * onUnifiedOperatorChange / onRangeChange / onValuesChange / addCondition /
 * delCondition / delGroup / addGroup。
 * 不移植任何 isAttr / 属性条件 / 权限模板（templateRef）相关代码。
 *
 * 2026-10-20 表达式能力补齐（兵哥截图反馈「条件之间无法设置且/或」）：
 * 组内（group.expr）/ 组间（localInter）两级表达式输入 + validateExpr 实时校验
 * + previewOf 预览，apply 前与 RuleConfigModal.confirm 同构拦截。
 */
import { computed, ref, watch, onMounted } from 'vue'
import {
  NModal, NButton, NSpace, NSelect, NCheckbox, NCheckboxGroup, NIcon,
  NInput, NTooltip, NTag, useMessage,
} from 'naive-ui'
import {
  AddOutline, TrashOutline, ReorderFourOutline,
  InformationCircleOutline, CheckmarkCircleOutline, AlertCircleOutline,
} from '@vicons/ionicons5'
import {
  uid,
  dynamicSourceOptions,
  resolveValueSource,
  validateExpr,
  previewOf,
  type DimensionMeta, type PermCondition, type PermConditionGroup,
  type AttributeField, type PermValue, type ActionDictItem,
} from '@/composables/useRoleDataPerm'
import type { OperatorOption } from '@/api/data-permission'
import type { StrategyGovernedResource } from '@/api/dynamicStrategy'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
const message = useMessage()

const props = withDefaults(defineProps<{
  show: boolean
  moduleKey: string
  moduleName: string
  /**
   * 后端 options.actions 全部条目。
   * 🔴 2026-10-20 起「受限功能」已改为资源粒度（见 governedResources），
   *    本 prop 仅保留契约兼容，弹窗内不再渲染、不再回写。
   */
  actionOptions?: ActionDictItem[]
  /** 该模块的维度（来自 options.modules[moduleKey].dimensions） */
  dimensions: DimensionMeta[]
  /** 透传但不使用（不渲染任何属性条件 UI） */
  attributeFields: AttributeField[]
  /**
   * 「受限功能」候选资源（后端 options.governedResources[moduleKey]）。
   * 已按 strategy_governed=True + BUTTON + 启用 过滤并分组完毕，前端不再二次过滤。
   */
  governedResources?: StrategyGovernedResource[]
  /** 打开时该模块已选的动作 key（旧契约，仅用于兼容；新链路用 initialResourceCodes） */
  initialActions?: string[]
  /** 打开时该模块已选的资源码（来自 grantedResourceCodes 中归属本模块的部分） */
  initialResourceCodes?: string[]
  /** 打开时该模块已配的条件组 */
  initialGroups: PermConditionGroup[]
  /** 打开时该模块已配的组间组合表达式（scope 模式生效；留空 = 或 OR） */
  initialExpr?: string
}>(), {
  actionOptions: () => [],
  initialActions: () => [],
  initialResourceCodes: () => [],
  initialGroups: () => [],
  attributeFields: () => [],
  governedResources: () => [],
  initialExpr: '',
})

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  /** 受限功能改为资源粒度：勾选结果以资源码集合回传，父组件并入 grantedResourceCodes；
   *  expr 为组间组合表达式（手填，留空 = 或 OR），父组件原样写回 module_config[key].expr */
  (e: 'apply', payload: { resourceCodes: string[]; groups: PermConditionGroup[]; expr: string }): void
}>()

const modalTitle = computed(() => `${t('pages.settings.DynamicStrategy.s24')} · ${props.moduleName}`)

// ===== 内部状态 =====
/**
 * 「受限功能」已选集合 —— 2026-10-20 起由「动作 key」改为「资源码」。
 * 后端 /me 并集按 grantedResourceCodes 真实生效，故勾选即写资源码。
 */
const localResourceCodes = ref<string[]>([])
const localGroups = ref<PermConditionGroup[]>([])
/** 组间组合表达式（引用条件组序号 1..N；留空 = 或 OR）。resetState 时由 initialExpr 回填。 */
const localInter = ref<string>('')

// ===== 受限功能：资源复选格 =====
// 候选由后端按策略模块分组并过滤完毕（strategy_governed=True + BUTTON + 启用），
// 前端不做二次过滤 —— 否则会出现「候选里勾了却在别处被静默丢弃」的漂移。
function onResourceCodesChange(v: Array<string | number>) {
  localResourceCodes.value = v.map(String)
}
function selectAll() {
  localResourceCodes.value = props.governedResources.map((r) => r.resourceCode)
}
function clearActions() {
  localResourceCodes.value = []
}

// ===== 关系维度选项 / 运算符 =====
const dimensionOptions = computed(() =>
  props.dimensions.map((d) => ({ label: d.label, value: d.key })),
)

type UnifiedOperatorOption = OperatorOption & Record<string, unknown>

const UNIFIED_USER_OPERATORS: UnifiedOperatorOption[] = [
  { label: '包含', value: 'in' },
  { label: '不包含', value: 'not_in' },
]
const NOVALUE_OPERATOR_VALUES = new Set(['is_empty', 'is_not_empty'])
const UNIFIED_DEPT_OPERATORS: UnifiedOperatorOption[] = [
  { label: '属于', value: 'in:exact' },
  { label: '不属于', value: 'not_in:exact' },
  { label: '属于（含下级）', value: 'in:in_subtree' },
  { label: '不属于（含下级）', value: 'not_in:in_subtree' },
  { label: '包含', value: 'in:contains' },
  { label: '不包含', value: 'not_in:contains' },
  { label: '包含或属于', value: 'in:overlap' },
  { label: '不包含或属于', value: 'not_in:overlap' },
]

function firstDim(): string {
  return props.dimensions[0]?.key || 'dept'
}
function dimMetaOf(dimension: string) {
  return props.dimensions.find((d) => d.key === dimension)
}
function dimValueType(c: PermCondition): string {
  return dimMetaOf(c.dimension || '')?.valueType || ''
}
function labelOf(dimension: string, id: string | number): string {
  const meta = dimMetaOf(dimension)
  return meta?.options?.find((o) => String(o.id) === String(id))?.label ?? String(id)
}

function valueOptions(c: PermCondition) {
  const meta = dimMetaOf(c.dimension || '')
  return (meta?.options || []).map((o) => ({
    label: o.emptyShell ? `${o.label}（无范围）` : o.label,
    value: o.id,
  }))
}
function validValueIds(c: PermCondition): Array<string | number> {
  const meta = dimMetaOf(c.dimension || '')
  const valid = new Set((meta?.options || []).map((o) => String(o.id)))
  return (c.values || []).filter((v) => valid.has(String(v.id))).map((v) => v.id)
}

function supportsDynamic(c: PermCondition): boolean {
  const meta = dimMetaOf(c.dimension || '')
  return (meta?.contextKeys || []).length > 0
}
function isDynamic(c: PermCondition): boolean {
  return c.valueSource === 'dynamic'
}
function isStatic(c: PermCondition): boolean {
  return !isDynamic(c)
}

function unifiedOperatorOptions(c: PermCondition): UnifiedOperatorOption[] {
  const vt = dimValueType(c)
  if (vt === 'department') return UNIFIED_DEPT_OPERATORS
  const meta = dimMetaOf(c.dimension || '')
  if (meta?.operators?.length) return meta.operators as UnifiedOperatorOption[]
  return UNIFIED_USER_OPERATORS
}

function noValueOperator(c: PermCondition): boolean {
  const v = unifiedOperatorValue(c)
  if (NOVALUE_OPERATOR_VALUES.has(v)) return true
  return unifiedOperatorOptions(c).find((o) => o.value === v)?.noValue ?? false
}

function unifiedOperatorValue(c: PermCondition): string {
  const op = c.operator || 'in'
  const rel = c.relation || 'exact'
  const vt = dimValueType(c)
  if (vt === 'department') {
    return `${op}:${rel}`
  }
  if (unifiedOperatorOptions(c).some((o) => o.value === op)) return op
  if (op === 'eq') return 'in'
  if (op === 'neq') return 'not_in'
  return op === 'not_in' ? 'not_in' : 'in'
}

function onUnifiedOperatorChange(c: PermCondition, v: string) {
  const vt = dimValueType(c)
  if (vt === 'department') {
    const [op, rel] = v.split(':') as [string, PermCondition['relation'] & string]
    c.operator = op
    c.relation = rel
  } else {
    c.operator = v
    c.relation = undefined
  }
  if (noValueOperator(c)) {
    c.values = []
    c.valueSource = 'static'
    c.dynamicKey = undefined
  }
}

// ===== 取值来源（固定 / 动态）=====
function rangeValue(c: PermCondition): string {
  return c.valueSource === 'dynamic' ? (c.dynamicKey || 'static') : 'static'
}
function rangeOptions(c: PermCondition) {
  const meta = dimMetaOf(c.dimension || '')
  return [
    { label: t('dataperm.modal.staticSource'), value: 'static' },
    ...dynamicSourceOptions(meta?.contextKeys),
  ]
}
function rangeLabel(c: PermCondition): string {
  const v = rangeValue(c)
  const opt = rangeOptions(c).find((o) => o.value === v)
  return opt?.label ?? v
}
function onRangeChange(c: PermCondition, v: string) {
  onValueSourceChange(c, v)
}

function onValueSourceChange(c: PermCondition, v: string) {
  const meta = dimMetaOf(c.dimension || '')
  const next = resolveValueSource(v, meta?.valueType)
  const wasDynamic = isDynamic(c)
  c.valueSource = next.valueSource
  c.dynamicKey = next.dynamicKey
  if (!wasDynamic) {
    c.relation = next.relation
  }
  if (!c.operator) {
    c.operator = 'in'
  }
  c.values = []
}

// ===== 维度变更 =====
function onDimensionChange(c: PermCondition, v: string) {
  c.dimension = v
  c.values = []
  if (c.valueSource === 'dynamic') {
    if (!supportsDynamic(c)) {
      c.valueSource = 'static'
      c.dynamicKey = undefined
      c.relation = undefined
    } else {
      const keys = dimMetaOf(v)?.contextKeys || []
      const keep = keys.includes(c.dynamicKey as string) ? (c.dynamicKey as string) : keys[0]
      onValueSourceChange(c, keep || 'static')
    }
  }
}

function onValuesChange(c: PermCondition, ids: Array<string | number>) {
  c.values = ids.map((id) => ({ id, label: labelOf(c.dimension || '', id) }))
}

// ===== 增删改（仅 relationship）=====
/** 该维度首运算符（与 unifiedOperatorOptions 顺序一致）。 */
function firstOperatorOf(dimensionKey?: string): string {
  const meta = dimMetaOf(dimensionKey || '')
  if (meta?.valueType === 'department') return UNIFIED_DEPT_OPERATORS[0].value
  if (meta?.operators?.length) return meta.operators![0].value
  return UNIFIED_USER_OPERATORS[0].value
}

function createCondition(): PermCondition {
  const dim = props.dimensions[0]?.key || 'dept'
  return {
    id: uid('c'),
    kind: 'relationship',
    dimension: dim,
    operator: firstOperatorOf(dim),
    values: [],
    valueSource: 'static',
  }
}

function addGroup() {
  localGroups.value.push({
    id: uid('g'),
    expr: '',
    conditions: [createCondition()],
  })
}
function addCondition(g: PermConditionGroup) {
  g.conditions.push(createCondition())
}
function delCondition(g: PermConditionGroup, idx: number) {
  if (g.conditions.length <= 1) return
  g.conditions.splice(idx, 1)
}
function delGroup(gi: number) {
  if (localGroups.value.length <= 1) return
  localGroups.value.splice(gi, 1)
}
function clearAll() {
  localResourceCodes.value = []
  localGroups.value = []
}

// ===== 表达式实时校验（validateExpr 与后端 expr_compiler 同口径）=====
/** 组内表达式错误原因；留空 = 且 (AND)，合法（与 RuleConfigModal.intraError 逐字同构）。 */
function intraError(g: PermConditionGroup): string | null {
  if (!g.expr || !g.expr.trim()) return null
  return validateExpr(g.expr, g.conditions.length)
}

/** 组间组合错误原因；留空 = 或 (OR)，合法（与 RuleConfigModal.interError 逐字同构）。 */
const interError = computed<string | null>(() => {
  if (!localInter.value || !localInter.value.trim()) return null
  return validateExpr(localInter.value, localGroups.value.length)
})

// ===== 深拷贝并补全 id（往返编辑不损坏存量条件）=====
function cloneGroups(src: PermConditionGroup[]): PermConditionGroup[] {
  return (src || []).map((g) => ({
    id: g.id || uid('g'),
    expr: g.expr || '',
    conditions: (g.conditions || []).map((c) => ({
      id: c.id || uid('c'),
      kind: c.kind || 'relationship',
      dimension: c.dimension,
      operator: c.operator,
      values: (c.values || []).map((v) => ({ id: v.id, label: v.label, stale: v.stale })),
      valueSource: c.valueSource,
      dynamicKey: c.dynamicKey,
      relation: c.relation,
      // 透传属性条件存量字段，避免往返编辑静默损坏（本弹窗只读这些内容）
      field: c.field,
      fieldName: c.fieldName,
      value: c.value,
      meta: c.meta ? { min: c.meta.min ?? null, max: c.meta.max ?? null } : undefined,
    })),
  }))
}

function resetState() {
  /**
   * 已选资源码以 props.initialResourceCodes 为准（父组件按模块从 grantedResourceCodes 切出）。
   * ⚠️ 候选之外（后端已取消受管控 / 已停用）的存量码不在 governedResources 里，
   *    但 Naive 的 n-checkbox-group 只回传「当前可见勾选项」，
   *    若此处过滤掉会导致用户一打开弹窗就静默丢码 —— 故原样保留，交由后端忽略。
   */
  localResourceCodes.value = [...(props.initialResourceCodes || [])]
  localGroups.value = cloneGroups(props.initialGroups || [])
  // 组间组合表达式回填（父组件 configInitialExpr computed 供数；缺省空串 = 或 OR）
  localInter.value = props.initialExpr ?? ''
}

// show 变为 true 时重置内部状态；onMounted 也兜底一次
watch(
  () => props.show,
  (v) => { if (v) resetState() },
  { immediate: true },
)
onMounted(() => { if (props.show) resetState() })

// ===== 配置预览：当满足 {条件内容} 时，可操作 {功能清单} 功能 =====
/**
 * 条件内容预览：改用 previewOf（与后端 expr_compiler 同口径的两级布尔表达式渲染）。
 * 组内 / 组间关系按用户手填表达式**真实**呈现（留空分别回落 且/或），
 * 不再像旧实现那样把 join 写死 —— 写死会把用户配的「且」显示成「或」，
 * 属于放大权限的误导。预览为空（无条件组）时回落「全部数据」。
 */
const conditionText = computed(() =>
  previewOf({
    moduleKey: '',
    mode: 'scope' as const,
    expr: localInter.value,
    groups: localGroups.value,
    featureGranted: true,
  }) || t('pages.settings.DynamicStrategy.s43'),
)

/** 功能清单：已勾选资源的名称，顿号连接 */
const functionsText = computed(() => {
  if (!localResourceCodes.value.length) return t('pages.settings.DynamicStrategy.s44')
  const selected = new Set(localResourceCodes.value)
  const labels = props.governedResources.filter((r) => selected.has(r.resourceCode)).map((r) => r.resourceName)
  return labels.join('、') || t('pages.settings.DynamicStrategy.s44')
})

// ===== 确定应用 =====
function apply() {
  // 无任何条件组：与 RuleConfigModal.confirm 同构的早退（mode 将由父组件推导为 all，
  // 表达式不参与编译，故不做表达式校验）。
  if (localGroups.value.length === 0) {
    emit('apply', {
      resourceCodes: [...localResourceCodes.value],
      groups: [],
      expr: localInter.value,
    })
    emit('update:show', false)
    return
  }
  // ① 组内表达式逐组校验（任一失败 → warning 拦截，**不发 apply**）
  for (let gi = 0; gi < localGroups.value.length; gi++) {
    const reason = intraError(localGroups.value[gi])
    if (reason) {
      message.warning(t('dataperm.error.exprIntra', { n: gi + 1, reason }))
      return
    }
  }
  // ② 组间组合表达式校验
  if (interError.value) {
    message.warning(t('dataperm.error.exprInter', { reason: interError.value }))
    return
  }
  emit('apply', {
    resourceCodes: [...localResourceCodes.value],
    groups: cloneGroups(localGroups.value),
    expr: localInter.value,
  })
  emit('update:show', false)
}
</script>

<style scoped>
/* 视觉重量对齐 RuleConfigModal / ModuleActionCard：白卡 + 1px hairline + 圆角 12px */
.section { margin-bottom: var(--space-4, 16px); }
.section:last-child { margin-bottom: 0; }
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2, 8px);
}
.section-title {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
}
.section-ops { display: flex; align-items: center; gap: var(--space-2, 8px); }

/* ===== 受限功能复选格（白卡）===== */
.action-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  padding: var(--space-2, 8px) var(--space-2, 8px) var(--space-2, 8px) var(--space-2, 8px);
  background: var(--surface, #fff);
  border: 1px solid var(--border-hairline);
  border-radius: 12px;
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(15, 23, 42, 0.06));
}
.action-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--ink-soft);
  cursor: pointer;
  min-width: 0;
}
/* 该策略模块下无受管控资源时的说明：提示去「资源管理」页勾选，而不是留一片空白 */
.gov-empty {
  margin: var(--space-2, 8px) 0 0;
  font-size: 12px;
  color: var(--ink-faint);
}

/* ===== 授权条件组列表 ===== */
.group-list { display: flex; flex-direction: column; }
.group-block {
  background: var(--surface, #fff);
  border: 1px solid var(--border-hairline);
  border-radius: 12px;
  padding: var(--space-2, 8px) var(--space-2, 8px) 4px;
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(15, 23, 42, 0.06));
}
.group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.group-title {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-soft);
}
.group-head-actions { display: flex; align-items: center; gap: var(--space-3, 12px); }
.group-head-actions a {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: var(--ink-faint);
  text-decoration: none;
  cursor: pointer;
  transition: color var(--dur-fast, 0.15s) var(--ease-out, ease-out);
}
.group-head-actions a:hover { color: var(--brand); }
.group-head-actions a.danger:hover { color: var(--c-error-deep); }

/* 条件行：单行铁律（序号 → 维度 → 运算符 → 取值来源 → 业务值 → 删除）。
   flex-wrap:nowrap + 全链路 min-width:0：超宽截断而非换行。 */
.cond-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
  padding: 4px 0;
  min-width: 0;
}
.cond-spacer { flex: 1; min-width: 0; }
.cond-seq {
  width: 22px; height: 22px;
  flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background: color-mix(in oklch, var(--brand, #6366f1) 12%, transparent);
  color: var(--brand);
  font-size: 12px;
  font-weight: 600;
}
.cond-del {
  background: transparent;
  border: none;
  color: var(--ink-faint);
  cursor: pointer;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-left: 4px;
  padding: 0;
}
.cond-del:hover:not(:disabled) { color: var(--c-error-deep); }
.cond-del:disabled { opacity: 0.4; cursor: not-allowed; }

/* 单行空间预算（弹窗 860px，组内可用 ≈ 770px）。
   维度 flex3(190/230) + 运算符 160 + 来源 128 + 业务值 flex2(150) + 删除 24 + 间隙。 */
.cond-dim { flex: 3 1 190px; min-width: 180px; max-width: 230px; }
.cond-verb { flex: 0 1 auto; width: 160px; min-width: 92px; }
.cond-src { flex: 0 1 auto; width: 128px; min-width: 92px; }
.cond-val { flex: 2 1 150px; min-width: 110px; }
.cond-val-readonly { flex: 2 1 auto; min-width: 0; max-width: 100%; }
.cond-val-readonly :deep(.n-tag__content) {
  min-width: 0;
  overflow: hidden;
}
.ellipsis-text {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}

/* ===== 组内表达式 / 组间组合：label + input + 状态图标的一行式
   （移植自 RuleConfigModal，保持本文件 var(--x, fallback) 既有风格）===== */
.group-inner-row {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  margin-top: 8px;
}
.inner-label {
  font-size: var(--fs-12, 12px);
  color: var(--ink-soft);
  white-space: nowrap;
  min-width: 72px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
}
.group-inner-row :deep(.n-input) { flex: 1; min-width: 0; }

/* 提示图标按钮：button 保键盘可达 + aria-label 供读屏，hover/focus 出 n-tooltip。
   cursor: help 明示「这是说明、不是动作」。 */
.hint-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  margin-left: 2px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--ink-faint);
  cursor: help;
  padding: 0;
  font-size: 13px;
  flex-shrink: 0;
  transition: color 0.15s ease, background 0.15s ease;
}
.hint-btn:hover,
.hint-btn:focus-visible {
  color: var(--brand);
  background: var(--g1);
  outline: none;
}
.hint-btn:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 1px;
}

/* 表达式校验状态图标（ok 绿勾 / bad 红叹，hover 出原因） */
.expr-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: 0;
  background: transparent;
  cursor: help;
  padding: 0;
  font-size: 15px;
  flex-shrink: 0;
  border-radius: 50%;
}
.expr-status.ok { color: var(--c-success-deep); }
.expr-status.bad { color: var(--c-error-deep); }
.expr-status:hover { background: var(--g1); }
.expr-status:focus-visible { outline: 2px solid var(--brand); outline-offset: 1px; }

/* 输入错误态：error 边框 + 浅红底 */
.input-error :deep(.n-input__input-el) {
  border-color: var(--c-error-deep) !important;
  background: var(--c-error-soft);
}

/* 组间组合：极浅底，标示它是「组合方式」而非条件本身 */
.inter-block {
  margin-top: var(--space-3, 12px);
  padding: 8px 10px;
  border-radius: 12px;
  background: var(--g1);
  border: 1px solid var(--border-hairline);
}

/* 添加条件组文字链 */
.add-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: var(--space-2, 8px);
  color: var(--brand);
  font-size: 12px;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  transition: color var(--dur-fast, 0.15s) var(--ease-out, ease-out);
}
.add-link:hover { color: var(--brand); filter: brightness(0.9); }

.empty-state {
  border: 1px dashed var(--border-hairline);
  border-radius: 12px;
  padding: 24px 16px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}
.empty-text { margin: 0; font-size: 13px; color: var(--ink-soft); }

/* 配置预览 */
.preview-box {
  padding: 8px;
  background: var(--g1);
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
}
.preview-text { color: var(--ink-soft); font-weight: 600; }
</style>
