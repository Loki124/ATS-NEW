<template>
  <n-modal
    :show="show"
    preset="card"
    :title="t('dataperm.modal.title', { moduleName })"
    :style="{ width: '760px' }"
    :mask-closable="false"
    :bordered="false"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <!-- 条件组列表（一级白卡） -->
    <div v-if="localGroups.length" class="group-list">
      <div
        v-for="(g, gi) in localGroups"
        :key="g.id"
        class="group-card"
      >
        <div class="group-head">
          <span class="drag-handle">⠿</span>
          <n-tag size="small" :bordered="false" type="primary" class="group-badge">
            {{ t('dataperm.modal.groupTitle', { n: gi + 1 }) }}
          </n-tag>
          <div class="group-head-actions">
            <n-button size="small" tertiary @click="addCondition(g)">
              + {{ t('dataperm.modal.addCondition') }}
            </n-button>
            <n-button
              size="small"
              tertiary
              type="error"
              :disabled="localGroups.length <= 1"
              @click="delGroup(gi)"
            >
              {{ t('dataperm.modal.delGroup') }}
            </n-button>
          </div>
        </div>

        <!-- 组内条件行 -->
        <div
          v-for="(c, ci) in g.conditions"
          :key="c.id"
          class="cond-row"
        >
          <div class="cond-top">
            <span class="cond-idx">{{ ci + 1 }}</span>
            <n-radio-group
              :value="c.kind || 'relationship'"
              size="small"
              @update:value="(k: 'relationship' | 'attribute') => onKindChange(c, k)"
            >
              <n-radio-button value="relationship">{{ t('dataperm.modal.condType.relationship') }}</n-radio-button>
              <n-radio-button value="attribute">{{ t('dataperm.modal.condType.attribute') }}</n-radio-button>
            </n-radio-group>
            <n-button
              size="tiny"
              tertiary
              circle
              class="cond-del"
              :disabled="g.conditions.length <= 1"
              @click="delCondition(g, ci)"
            >
              ×
            </n-button>
          </div>

          <!-- 关系维度（沿用原逻辑：维度 -> 业务值） -->
          <div v-if="!isAttr(c)" class="cond-body rel">
            <n-select
              :value="c.dimension"
              :options="dimensionOptions"
              size="small"
              class="cond-dim"
              @update:value="(v: string) => onDimensionChange(c, v)"
            />
            <n-select
              :value="c.operator"
              :options="operatorOptions"
              size="small"
              class="cond-op"
              @update:value="(v: Operator) => (c.operator = v)"
            />
            <n-select
              :value="validValueIds(c)"
              :options="valueOptions(c)"
              size="small"
              multiple
              filterable
              clearable
              class="cond-val"
              :placeholder="t('dataperm.modal.valuesPlaceholder')"
              @update:value="(ids: Array<string | number>) => onValuesChange(c, ids)"
            />
            <n-tag
              v-for="sv in staleValues(c)"
              :key="sv.id"
              size="small"
              :bordered="false"
              class="stale-tag"
            >
              {{ sv.label }}（{{ t('dataperm.value.stale') }}）
            </n-tag>
          </div>

          <!-- 属性条件（复用指标目录标量字段，右值=字面量；全中文下拉 / 数字步进器，禁手输） -->
          <div v-else class="cond-body attr">
            <n-select
              :value="c.field"
              :options="attrFieldOptions"
              size="small"
              filterable
              clearable
              class="attr-field"
              :placeholder="t('dataperm.modal.fieldPlaceholder')"
              @update:value="(v: string) => onAttrFieldChange(c, v)"
            />
            <n-select
              :value="c.operator"
              :options="attrOperatorOptions(c)"
              size="small"
              class="attr-op"
              :placeholder="t('dataperm.modal.attrOperatorPlaceholder')"
              :disabled="!c.field"
              @update:value="(v: string) => onAttrOperatorChange(c, v)"
            />
            <template v-if="attrValueMode(c) === 'enum-single'">
              <n-select
                :value="attrSingleValueId(c)"
                :options="attrEnumOptions(c)"
                size="small"
                filterable
                class="attr-val"
                :placeholder="t('dataperm.modal.attrValuePlaceholder')"
                @update:value="(id: string | number | boolean) => onAttrEnumSingle(c, id)"
              />
            </template>
            <template v-else-if="attrValueMode(c) === 'enum-multi'">
              <n-select
                multiple
                :value="attrMultiValueIds(c)"
                :options="attrEnumOptions(c)"
                size="small"
                filterable
                class="attr-val"
                :placeholder="t('dataperm.modal.attrValuePlaceholder')"
                @update:value="(ids: Array<string | number | boolean>) => onAttrEnumMulti(c, ids)"
              />
            </template>
            <template v-else-if="attrValueMode(c) === 'num-single'">
              <n-input-number
                :value="(c.value as number | null) ?? null"
                size="small"
                class="attr-val"
                :placeholder="t('dataperm.modal.attrValuePlaceholder')"
                @update:value="(n: number | null) => onAttrNumber(c, n)"
              />
            </template>
            <template v-else-if="attrValueMode(c) === 'num-range'">
              <n-input-number
                :value="c.meta?.min ?? null"
                size="small"
                class="attr-val-sm"
                :placeholder="t('dataperm.modal.rangeMin')"
                @update:value="(n: number | null) => onAttrRangeMin(c, n)"
              />
              <n-input-number
                :value="c.meta?.max ?? null"
                size="small"
                class="attr-val-sm"
                :placeholder="t('dataperm.modal.rangeMax')"
                @update:value="(n: number | null) => onAttrRangeMax(c, n)"
              />
            </template>
            <span v-else class="attr-no-val">{{ t('dataperm.modal.attrOperatorPlaceholder') }}</span>
          </div>
        </div>

        <!-- 组内表达式（用户手填，引用本组条件序号 1..N） -->
        <div class="expr-row">
          <span class="expr-label">{{ t('dataperm.modal.expr.intraLabel') }}</span>
          <n-input
            v-model:value="g.expr"
            size="small"
            clearable
            class="expr-input"
            :status="intraError(g) ? 'error' : undefined"
            :placeholder="t('dataperm.modal.expr.placeholder')"
          />
          <span class="expr-sub">{{ t('dataperm.modal.expr.intraSub', { n: g.conditions.length }) }}</span>
          <span class="expr-check" :class="intraError(g) ? 'bad' : 'ok'">
            {{ intraError(g) ? t('dataperm.modal.expr.invalid', { reason: intraError(g) || '' }) : t('dataperm.modal.expr.valid') }}
          </span>
        </div>
      </div>
    </div>

    <!-- 空状态（虚线框） -->
    <div v-else class="empty-state">
      <p class="empty-text">{{ t('dataperm.modal.empty') }}</p>
      <n-button size="small" type="primary" secondary @click="addGroup">
        + {{ t('dataperm.modal.addGroup') }}
      </n-button>
    </div>

    <!-- 组间组合（强调底色，引用条件组序号 1..N） -->
    <div class="inter-block">
      <div class="expr-row inter">
        <span class="expr-label">{{ t('dataperm.modal.expr.interLabel') }}</span>
        <n-input
          v-model:value="localInter"
          size="small"
          clearable
          class="expr-input inter-input"
          :status="interError ? 'error' : undefined"
          :placeholder="t('dataperm.modal.expr.placeholder')"
        />
        <span class="expr-sub">{{ t('dataperm.modal.expr.interSub', { n: localGroups.length }) }}</span>
        <span class="expr-check" :class="interError ? 'bad' : 'ok'">
          {{ interError ? t('dataperm.modal.expr.invalid', { reason: interError || '' }) : t('dataperm.modal.expr.valid') }}
        </span>
      </div>
      <n-button size="small" type="primary" secondary block class="add-group-btn" @click="addGroup">
        + {{ t('dataperm.modal.addGroup') }}
      </n-button>
    </div>

    <!-- 预览句 -->
    <div class="preview-box">
      <span class="preview-prefix">{{ t('dataperm.preview.prefix') }}</span>
      <span class="preview-text">{{ previewText }}</span>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button @click="clearAll">{{ t('dataperm.modal.clearAll') }}</n-button>
        <n-button @click="emit('update:show', false)">{{ t('dataperm.action.cancel') }}</n-button>
        <n-button type="primary" @click="confirm">{{ t('dataperm.modal.confirm') }}</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
/**
 * RuleConfigModal.vue — 规则配置弹窗（设计文档 §2.3 / §三 3.3）。
 *
 * 两类条件共存于同一布尔表达式（AND/OR）：
 *   1. 关系维度（relationship，默认）：维度 -> ORM 字段 -> in/not_in（右值=维度业务值）。
 *   2. 属性条件（attribute，新增）：复用指标目录标量字段，右值=字面量（property filter）。
 *      字段 / 运算符 / 业务值全部来自后端 attributeFields（全中文下拉 / 数字步进器），
 *      自由文本字符串字段不在清单内，杜绝用户手输。
 *
 * 两级布尔表达式均由用户手填（无 且/或 选项按钮）：
 *   - 组内表达式 (group.expr)  引用本组条件序号 1..N
 *   - 组间组合   (interExpr)   引用条件组序号 1..N
 * 实时校验（validateExpr，与后端 expr_compiler 等价）+ 预览句（previewOf）。
 */
import { computed, ref, watch } from 'vue'
import {
  NModal, NButton, NSpace, NSelect, NInput, NTag, NRadioGroup, NRadioButton,
  NInputNumber, useMessage,
} from 'naive-ui'
import {
  newCondition, uid, validateExpr, previewOf,
  ATTR_NOVALUE_OPS, ATTR_LIST_OPS,
  type DimensionMeta, type Operator, type PermCondition, type PermConditionGroup, type AttributeField, type PermValue,
} from '@/composables/useRoleDataPerm'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{
  show: boolean
  moduleName: string
  dimensions: DimensionMeta[]
  attributeFields: AttributeField[]
  groups: PermConditionGroup[]
  interExpr: string
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'update:groups', v: PermConditionGroup[]): void
  (e: 'update:interExpr', v: string): void
}>()

const message = useMessage()

const localGroups = ref<PermConditionGroup[]>([])
const localInter = ref<string>('')

function cloneGroups(src: PermConditionGroup[]): PermConditionGroup[] {
  return (src || []).map((g) => ({
    id: g.id,
    expr: g.expr,
    conditions: g.conditions.map((c) => ({
      id: c.id,
      kind: c.kind,
      dimension: c.dimension,
      operator: c.operator,
      values: (c.values || []).map((v) => ({ id: v.id, label: v.label, stale: v.stale })),
      field: c.field,
      fieldName: c.fieldName,
      value: c.value,
      meta: c.meta ? { min: c.meta.min ?? null, max: c.meta.max ?? null } : undefined,
    })),
  }))
}

watch(
  () => props.show,
  (v) => {
    if (v) {
      localGroups.value = cloneGroups(props.groups)
      localInter.value = props.interExpr ?? ''
    }
  },
  { immediate: true },
)

// ===== 关系维度选项 =====
const dimensionOptions = computed(() =>
  props.dimensions.map((d) => ({ label: d.label, value: d.key })),
)
const operatorOptions = [
  { label: t('dataperm.operator.in'), value: 'in' as Operator },
  { label: t('dataperm.operator.not_in'), value: 'not_in' as Operator },
]

function firstDim(): string {
  return props.dimensions[0]?.key || 'dept'
}

function dimMetaOf(dimension: string) {
  return props.dimensions.find((d) => d.key === dimension)
}

function valueOptions(c: PermCondition) {
  const meta = dimMetaOf(c.dimension || '')
  return (meta?.options || []).map((o) => ({ label: o.label, value: o.id }))
}

/** 当前维度下仍有效的已选值 id（排除孤儿值，供 n-select 回显）。 */
function validValueIds(c: PermCondition): Array<string | number> {
  const meta = dimMetaOf(c.dimension || '')
  const valid = new Set((meta?.options || []).map((o) => String(o.id)))
  return (c.values || []).filter((v) => valid.has(String(v.id))).map((v) => v.id)
}

/** 孤儿值（维度值已不存在于当前选项）。 */
function staleValues(c: PermCondition) {
  const meta = dimMetaOf(c.dimension || '')
  const valid = new Set((meta?.options || []).map((o) => String(o.id)))
  return (c.values || []).filter((v) => !valid.has(String(v.id)))
}

function labelOf(dimension: string, id: string | number): string {
  const meta = dimMetaOf(dimension)
  return meta?.options?.find((o) => String(o.id) === String(id))?.label ?? String(id)
}

// ===== 属性条件选项 =====
const attrFieldOptions = computed(() =>
  props.attributeFields.map((f) => ({ label: f.name, value: f.sourcePath })),
)

function isAttr(c: PermCondition): boolean {
  return c.kind === 'attribute'
}

function attrFieldOf(c: PermCondition): AttributeField | undefined {
  return props.attributeFields.find((f) => f.sourcePath === c.field)
}

function attrOperatorOptions(c: PermCondition) {
  return (attrFieldOf(c)?.operators || []).map((o) => ({ label: o.label, value: o.value }))
}

function attrEnumOptions(c: PermCondition) {
  return (attrFieldOf(c)?.enumValues || []).map((e) => ({ label: e.label, value: e.id }))
}

/** 根据字段数据类型 + 运算符，决定值控件的渲染形态。 */
function attrValueMode(c: PermCondition): 'none' | 'enum-single' | 'enum-multi' | 'num-single' | 'num-range' {
  const f = attrFieldOf(c)
  if (!f || ATTR_NOVALUE_OPS.has(c.operator)) return 'none'
  if (f.dataType === 'number') {
    return c.operator === 'BETWEEN' ? 'num-range' : 'num-single'
  }
  if (f.dataType === 'boolean') return 'enum-single' // 是/否 单选
  // enum
  if (ATTR_LIST_OPS.has(c.operator)) return 'enum-multi'
  return 'enum-single'
}

function attrSingleValueId(c: PermCondition): string | number | boolean | null {
  if (c.value && typeof c.value === 'object') return (c.value as PermValue).id as string | number | boolean
  return null
}

function attrMultiValueIds(c: PermCondition): Array<string | number | boolean> {
  if (Array.isArray(c.value)) {
    return c.value.map((v) => (v && typeof v === 'object' ? (v as PermValue).id : v)) as Array<string | number | boolean>
  }
  return []
}

// ===== 增删改 =====
function addGroup() {
  localGroups.value.push({
    id: uid('g'),
    expr: '1',
    conditions: [newCondition(firstDim())],
  })
}

function addCondition(g: PermConditionGroup) {
  g.conditions.push(newCondition(firstDim()))
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
  localGroups.value = []
}

function onDimensionChange(c: PermCondition, v: string) {
  c.dimension = v
  c.values = [] // 切换维度清空已选值（不同维度值域不可混用）
}

function onValuesChange(c: PermCondition, ids: Array<string | number>) {
  c.values = ids.map((id) => ({ id, label: labelOf(c.dimension || '', id) }))
}

function onKindChange(c: PermCondition, kind: 'relationship' | 'attribute') {
  if (kind === 'attribute') {
    c.kind = 'attribute'
    c.field = ''
    c.fieldName = ''
    c.operator = ''
    c.value = undefined
    c.meta = { min: null, max: null }
    c.values = []
    c.dimension = undefined
  } else {
    c.kind = 'relationship'
    c.dimension = firstDim()
    c.operator = 'in'
    c.values = []
    c.field = ''
    c.fieldName = ''
    c.value = undefined
    c.meta = undefined
  }
}

function onAttrFieldChange(c: PermCondition, sourcePath: string) {
  const meta = props.attributeFields.find((f) => f.sourcePath === sourcePath)
  c.field = sourcePath
  c.fieldName = meta?.name || ''
  c.operator = meta?.operators?.[0]?.value || ''
  c.value = undefined
  c.meta = { min: null, max: null }
}

function onAttrOperatorChange(c: PermCondition, op: string) {
  c.operator = op
  c.value = undefined
  c.meta = { min: null, max: null }
}

function _attrEnumLabel(c: PermCondition, id: string | number | boolean): string {
  return attrEnumOptions(c).find((o) => o.value === id)?.label ?? String(id)
}

function onAttrEnumSingle(c: PermCondition, id: string | number | boolean) {
  c.value = { id, label: _attrEnumLabel(c, id) }
}

function onAttrEnumMulti(c: PermCondition, ids: Array<string | number | boolean>) {
  c.value = ids.map((id) => ({ id, label: _attrEnumLabel(c, id) }))
}

function onAttrNumber(c: PermCondition, n: number | null) {
  c.value = n ?? undefined
}

function onAttrRangeMin(c: PermCondition, n: number | null) {
  c.meta = { min: n ?? null, max: c.meta?.max ?? null }
}

function onAttrRangeMax(c: PermCondition, n: number | null) {
  c.meta = { min: c.meta?.min ?? null, max: n ?? null }
}

// ===== 实时校验 =====
function intraError(g: PermConditionGroup): string | null {
  if (!g.expr || !g.expr.trim()) return null // 留空 = 且(AND)，合法
  return validateExpr(g.expr, g.conditions.length)
}

const interError = computed(() => {
  if (!localInter.value || !localInter.value.trim()) return null // 留空 = 或(OR)，合法
  return validateExpr(localInter.value, localGroups.value.length)
})

/** 单条条件是否合法（关系维度 / 属性条件共用）。 */
function conditionError(c: PermCondition): string | null {
  if (c.kind === 'attribute') {
    if (!c.field) return t('dataperm.error.emptyField')
    if (!c.operator) return t('dataperm.error.emptyOperator')
    if (ATTR_NOVALUE_OPS.has(c.operator)) return null
    if (ATTR_LIST_OPS.has(c.operator)) {
      if (!Array.isArray(c.value) || c.value.length === 0) return t('dataperm.error.emptyValue')
    } else if (c.operator === 'BETWEEN') {
      const mv = c.meta || {}
      if (mv.min == null || mv.max == null || mv.min === '' || mv.max === '') {
        return t('dataperm.error.emptyRange')
      }
    } else if (c.value == null || c.value === '') {
      return t('dataperm.error.emptyValue')
    }
    return null
  }
  if ((c.values || []).length === 0) return t('dataperm.error.emptyValue')
  return null
}

// ===== 预览 =====
const previewText = computed(() => {
  const groups = localGroups.value.map((g) => ({
    id: g.id,
    expr: g.expr,
    conditions: g.conditions,
  }))
  const m = {
    moduleKey: '', mode: 'scope' as const, expr: localInter.value, groups, featureGranted: true,
  }
  return previewOf(m)
})

// ===== 确认 =====
function confirm() {
  if (localGroups.value.length === 0) {
    emit('update:groups', [])
    emit('update:interExpr', localInter.value)
    emit('update:show', false)
    return
  }
  // ② 每条条件必须校验通过（关系维度 / 属性条件）
  for (let gi = 0; gi < localGroups.value.length; gi++) {
    const g = localGroups.value[gi]
    for (const c of g.conditions) {
      const err = conditionError(c)
      if (err) {
        message.warning(err)
        return
      }
    }
  }
  // ③ 组内 / 组间表达式语法校验
  for (let gi = 0; gi < localGroups.value.length; gi++) {
    const re = intraError(localGroups.value[gi])
    if (re) {
      message.warning(t('dataperm.error.exprIntra', { n: gi + 1, reason: re }))
      return
    }
  }
  if (interError.value) {
    message.warning(t('dataperm.error.exprInter', { reason: interError.value }))
    return
  }
  emit('update:groups', cloneGroups(localGroups.value))
  emit('update:interExpr', localInter.value)
  emit('update:show', false)
}
</script>

<style scoped>
.group-list { display: flex; flex-direction: column; gap: 12px; }

.group-card {
  border: 1px solid var(--border-hairline, #e2e8f0);
  border-radius: 10px;
  padding: 12px;
  background: #fff;
}
.group-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.drag-handle { color: var(--ink-soft, #94a3b8); font-size: 14px; cursor: grab; }
.group-badge { font-weight: 700; }
.group-head-actions { margin-left: auto; display: flex; gap: 6px; }

.cond-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
  margin-bottom: 8px;
  background: var(--g1, #f8fafc);
  border-radius: 8px;
}
.cond-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cond-idx {
  width: 20px; height: 20px;
  flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background: var(--brand, #6366f1);
  color: #fff;
  font-size: 12px; font-weight: 700;
}
.cond-del { flex-shrink: 0; font-size: 16px; line-height: 1; margin-left: auto; }

.cond-body { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cond-dim { width: 110px; flex-shrink: 0; }
.cond-op { width: 90px; flex-shrink: 0; }
.cond-val { flex: 1; min-width: 0; }
.stale-tag { flex-shrink: 0; background: var(--g2, #eef2f7); color: var(--ink-soft, #64748b); }

.attr-field { width: 220px; flex-shrink: 0; }
.attr-op { width: 120px; flex-shrink: 0; }
.attr-val { flex: 1; min-width: 140px; }
.attr-val-sm { width: 110px; flex-shrink: 0; }
.attr-no-val { font-size: 12px; color: var(--ink-soft, #94a3b8); }

.expr-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.expr-label { font-size: 12px; font-weight: 600; color: var(--ink, #1e293b); flex-shrink: 0; }
.expr-input { flex: 1; min-width: 0; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.expr-sub { font-size: 11px; color: var(--ink-soft, #94a3b8); flex-shrink: 0; }
.expr-check { font-size: 12px; font-weight: 600; flex-shrink: 0; white-space: nowrap; }
.expr-check.ok { color: #18a058; }
.expr-check.bad { color: #d03050; }

.inter-block {
  margin-top: 14px;
  padding: 12px;
  border-radius: 10px;
  background: var(--brand-soft, rgba(99, 102, 241, 0.08));
  border: 1px solid var(--brand-tint, rgba(99, 102, 241, 0.2));
}
.expr-row.inter { margin-top: 0; }
.add-group-btn { margin-top: 10px; }

.empty-state {
  border: 1px dashed var(--border-hairline, #cbd5e1);
  border-radius: 10px;
  padding: 28px 16px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
}
.empty-text { margin: 0; font-size: 13px; color: var(--ink-soft, #64748b); }

.preview-box {
  margin-top: 14px;
  padding: 10px 12px;
  background: var(--g1, #f8fafc);
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
}
.preview-prefix { font-weight: 700; color: var(--ink, #1e293b); margin-right: 6px; }
.preview-text { color: var(--ink-soft, #475569); }
</style>
