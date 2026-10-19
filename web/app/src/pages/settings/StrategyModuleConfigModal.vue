<template>
  <!--
    动态策略「配置权限与规则」弹窗（全新独立组件）。
    职责单一：编辑某个模块的「写动作集合 actions」与「授权条件组 groups」
    （组间组合固定为 OR，无表达式输入框）。mode 由父组件计算，本弹窗不负责。
    条件行仅支持关系维度（relationship），不渲染任何属性条件 / 权限模板引用 UI。
  -->
  <n-modal
    :show="show"
    preset="card"
    :title="modalTitle"
    :style="{ width: '860px', maxWidth: '95vw' }"
    :content-style="{ maxHeight: 'min(70vh, 720px)', overflowY: 'auto', padding: '16px 20px' }"
    :mask-closable="false"
    :bordered="false"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <!-- ① 受限功能：后端 options.actions 中 enabled 且 write/destructive 的项 -->
    <section class="section">
      <div class="section-head">
        <h3 class="section-title">{{ t('pages.settings.DynamicStrategy.s25') }}</h3>
        <div class="section-ops">
          <n-button size="tiny" tertiary @click="selectAll">{{ t('pages.settings.DynamicStrategy.s26') }}</n-button>
          <n-button size="tiny" tertiary @click="clearActions">{{ t('pages.settings.DynamicStrategy.s27') }}</n-button>
        </div>
      </div>
      <n-checkbox-group :value="localActions" @update:value="(v: Array<string | number>) => onActionsChange(v)">
        <div class="action-grid">
          <label v-for="a in filteredActions" :key="a.key" class="action-item">
            <n-checkbox :value="a.key">{{ a.label }}</n-checkbox>
            <n-tag v-if="isDanger(a)" size="tiny" :bordered="false" type="error" class="danger-tag">
              {{ t('dataperm.write.destructive') }}
            </n-tag>
          </label>
        </div>
      </n-checkbox-group>
    </section>

    <!-- ② 授权条件：多条件组列表（仅 relationship），组间用「或 (OR)」分隔 -->
    <section class="section">
      <div class="section-head">
        <h3 class="section-title">{{ t('pages.settings.DynamicStrategy.s28') }}</h3>
      </div>

      <div v-if="localGroups.length" class="group-list">
        <template v-for="(g, gi) in localGroups" :key="g.id">
          <div v-if="gi > 0" class="group-sep">{{ t('pages.settings.DynamicStrategy.s36') }}</div>
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
    </section>

    <!-- ③ 配置预览：实时显示已选功能项数与条件组数 -->
    <section class="section">
      <div class="section-head">
        <h3 class="section-title">{{ t('pages.settings.DynamicStrategy.s33') }}</h3>
      </div>
      <div class="preview-box">
        <span class="preview-text">
          {{ t('pages.settings.DynamicStrategy.s34', { n: localActions.length }) }}
          · {{ t('pages.settings.DynamicStrategy.s35', { m: localGroups.length }) }}
        </span>
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
 */
import { computed, ref, watch, onMounted } from 'vue'
import {
  NModal, NButton, NSpace, NSelect, NCheckbox, NCheckboxGroup, NTag, NIcon,
} from 'naive-ui'
import { AddOutline, TrashOutline, ReorderFourOutline } from '@vicons/ionicons5'
import {
  uid,
  dynamicSourceOptions,
  resolveValueSource,
  type DimensionMeta, type PermCondition, type PermConditionGroup,
  type AttributeField, type PermValue, type ActionDictItem,
} from '@/composables/useRoleDataPerm'
import type { OperatorOption } from '@/api/data-permission'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = withDefaults(defineProps<{
  show: boolean
  moduleKey: string
  moduleName: string
  /** 后端 options.actions 全部条目 */
  actionOptions: ActionDictItem[]
  /** 该模块的维度（来自 options.modules[moduleKey].dimensions） */
  dimensions: DimensionMeta[]
  /** 透传但不使用（不渲染任何属性条件 UI） */
  attributeFields: AttributeField[]
  /** 打开时该模块已选的动作 key */
  initialActions: string[]
  /** 打开时该模块已配的条件组 */
  initialGroups: PermConditionGroup[]
}>(), {
  initialActions: () => [],
  initialGroups: () => [],
  attributeFields: () => [],
})

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'apply', payload: { actions: string[]; groups: PermConditionGroup[] }): void
}>()

const modalTitle = computed(() => `${t('pages.settings.DynamicStrategy.s24')} · ${props.moduleName}`)

// ===== 内部状态 =====
const localActions = ref<string[]>([])
const localGroups = ref<PermConditionGroup[]>([])

// ===== 受限功能：动作复选格 =====
const filteredActions = computed(() =>
  props.actionOptions.filter(
    (a) => a.enabled && (a.category === 'write' || a.category === 'destructive'),
  ),
)
const isDanger = (a: ActionDictItem): boolean => a.destructive || a.category === 'destructive'

function onActionsChange(v: Array<string | number>) {
  localActions.value = v.map(String)
}
function selectAll() {
  localActions.value = filteredActions.value.map((a) => a.key)
}
function clearActions() {
  localActions.value = []
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
  localActions.value = []
  localGroups.value = []
}

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
  localActions.value = [...(props.initialActions || [])]
  localGroups.value = cloneGroups(props.initialGroups || [])
}

// show 变为 true 时重置内部状态；onMounted 也兜底一次
watch(
  () => props.show,
  (v) => { if (v) resetState() },
  { immediate: true },
)
onMounted(() => { if (props.show) resetState() })

// ===== 确定应用 =====
function apply() {
  emit('apply', {
    actions: [...localActions.value],
    groups: cloneGroups(localGroups.value),
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
  color: var(--ink, #1e293b);
}
.section-ops { display: flex; align-items: center; gap: var(--space-2, 8px); }

/* ===== 受限功能复选格（白卡）===== */
.action-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  padding: var(--space-2, 8px) var(--space-2, 8px) var(--space-2, 8px) var(--space-2, 8px);
  background: var(--surface, #fff);
  border: 1px solid var(--border-hairline, #e2e8f0);
  border-radius: 12px;
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(15, 23, 42, 0.06));
}
.action-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--ink-soft, #64748b);
  cursor: pointer;
  min-width: 0;
}
.danger-tag { font-weight: 600; }

/* ===== 授权条件组列表 ===== */
.group-list { display: flex; flex-direction: column; }
.group-sep {
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-faint, #94a3b8);
  margin: var(--space-3, 12px) 0;
  letter-spacing: 0.04em;
}
.group-block {
  background: var(--surface, #fff);
  border: 1px solid var(--border-hairline, #e2e8f0);
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
  color: var(--ink-soft, #64748b);
}
.group-head-actions { display: flex; align-items: center; gap: var(--space-3, 12px); }
.group-head-actions a {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: var(--ink-faint, #94a3b8);
  text-decoration: none;
  cursor: pointer;
  transition: color var(--dur-fast, 0.15s) var(--ease-out, ease-out);
}
.group-head-actions a:hover { color: var(--brand, #6366f1); }
.group-head-actions a.danger:hover { color: var(--c-error-deep, #b91c1c); }

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
  color: var(--brand, #6366f1);
  font-size: 12px;
  font-weight: 600;
}
.cond-del {
  background: transparent;
  border: none;
  color: var(--ink-faint, #94a3b8);
  cursor: pointer;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-left: 4px;
  padding: 0;
}
.cond-del:hover:not(:disabled) { color: var(--c-error-deep, #b91c1c); }
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

/* 添加条件组文字链 */
.add-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: var(--space-2, 8px);
  color: var(--brand, #6366f1);
  font-size: 12px;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  transition: color var(--dur-fast, 0.15s) var(--ease-out, ease-out);
}
.add-link:hover { color: var(--brand, #6366f1); filter: brightness(0.9); }

.empty-state {
  border: 1px dashed var(--border-hairline, #e2e8f0);
  border-radius: 12px;
  padding: 24px 16px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}
.empty-text { margin: 0; font-size: 13px; color: var(--ink-soft, #64748b); }

/* 配置预览 */
.preview-box {
  padding: 8px;
  background: var(--g1, rgba(148, 163, 184, 0.1));
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
}
.preview-text { color: var(--ink-soft, #64748b); font-weight: 600; }
</style>
