<template>
  <div class="condition-picker">
    <n-select
      class="cp-field"
      size="small"
      :value="item.condition_type"
      :options="sourceOptions"
      :placeholder="t('pages.settings.stage-rule.components.ConditionPicker.s1')"
      @update:value="onSource"
    />
    <n-select
      class="cp-field"
      size="small"
      :value="item.field"
      :options="fieldOptions"
      :placeholder="t('pages.settings.stage-rule.components.ConditionPicker.s2')"
      @update:value="onField"
    />
    <n-select
      class="cp-field cp-op"
      size="small"
      :value="item.operator"
      :options="operatorOptions"
      :placeholder="t('pages.settings.stage-rule.components.ConditionPicker.s3')"
      @update:value="onOperator"
    />
    <div class="cp-value">
      <!-- 空值运算符：无值 -->
      <span v-if="isNoValueOp" class="cp-value__na">—</span>
      <!-- 枚举 / 布尔字段：下拉（IN / NOT_IN 多选，其余单选），选项由后端指标枚举 / 布尔定义驱动 -->
      <n-select
        v-else-if="hasOptions"
        :multiple="isMulti"
        size="small"
        filterable
        :value="isMulti ? arrayValue : (item.value ?? null)"
        :options="valueOptions"
        :placeholder="t('pages.settings.stage-rule.components.ConditionPicker.s4')"
        @update:value="onMultiValue"
      />
      <!-- 数值（由后端 value_type=number 决定，不再硬编码字段名） -->
      <n-input-number
        v-else-if="isNumeric"
        size="small"
        :value="numberValue"
        :placeholder="t('pages.settings.stage-rule.components.ConditionPicker.s5')"
        @update:value="onNumberValue"
      />
      <!-- 文本 -->
      <n-input
        v-else
        size="small"
        :value="textValue"
        :placeholder="t('pages.settings.stage-rule.components.ConditionPicker.s6')"
        @update:value="onTextValue"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { computed, reactive, watch } from 'vue'
import { NSelect, NInput, NInputNumber } from 'naive-ui'
import type { ConditionItem, FieldCatalog, OperatorKey, SourceKey } from '../types'
const { t } = useI18n()

const props = defineProps<{
  modelValue: ConditionItem
  catalog: FieldCatalog | null
}>()

const emit = defineEmits<{ (e: 'update:modelValue', v: ConditionItem): void }>()

const item = reactive<ConditionItem>({ ...props.modelValue })

watch(
  () => props.modelValue,
  (v) => {
    Object.assign(item, v)
  },
  { deep: true },
)

function sync() {
  emit('update:modelValue', { ...item })
}

const sourceOptions = computed(() =>
  (props.catalog?.sources || []).map((s) => ({ label: s.label, value: s.source })),
)
const sourceDef = computed(() => (props.catalog?.sources || []).find((s) => s.source === item.condition_type))
const fieldOptions = computed(() => (sourceDef.value?.fields || []).map((f) => ({ label: f.label, value: f.field })))
const fieldDef = computed(() => sourceDef.value?.fields.find((f) => f.field === item.field))
const operatorOptions = computed(() =>
  (fieldDef.value?.operators || []).map((op) => ({ label: props.catalog?.operators?.[op] || op, value: op })),
)

const isNoValueOp = computed(() => item.operator === 'IS_EMPTY' || item.operator === 'IS_NOT_EMPTY')
const isMulti = computed(
  () => item.operator === 'IN' || item.operator === 'NOT_IN' || !!fieldDef.value?.is_array,
)
// 数值判定改为数据驱动：读后端按指标 data_type 推导的 value_type，不再硬编码字段名
const isNumeric = computed(() => fieldDef.value?.valueType === 'number')
// 枚举 / 布尔字段：后端返回 options 时渲染下拉
const hasOptions = computed(() => (fieldDef.value?.options?.length || 0) > 0)
const valueOptions = computed(() => fieldDef.value?.options || [])

const arrayValue = computed<string[]>(() => (Array.isArray(item.value) ? item.value : []))
const numberValue = computed<number | null>(() => (typeof item.value === 'number' ? item.value : null))
const textValue = computed<string>(() => (item.value == null ? '' : String(item.value)))

function onSource(v: SourceKey) {
  item.condition_type = v
  const first = sourceDef.value?.fields?.[0]
  item.field = first?.field || ''
  item.operator = (first?.operators?.[0] as OperatorKey) || 'EQ'
  item.value = null
  item.stage_name = null
  item.stage_statuses = []
  sync()
}
function onField(v: string) {
  item.field = v
  item.operator = (fieldDef.value?.operators?.[0] as OperatorKey) || 'EQ'
  item.value = null
  item.stage_name = null
  item.stage_statuses = []
  sync()
}
function onOperator(v: OperatorKey) {
  item.operator = v
  if (isNoValueOp.value) item.value = null
  else if (isMulti.value && !Array.isArray(item.value)) item.value = []
  else if (item.value == null) item.value = isNumeric.value ? null : ''
  sync()
}
function onMultiValue(v: string[]) {
  if (item.field === 'stage_statuses') item.stage_statuses = v
  else item.value = v
  sync()
}
function onNumberValue(v: number | null) {
  item.value = v
  sync()
}
function onTextValue(v: string) {
  if (item.field === 'stage_name') item.stage_name = v
  else item.value = v
  sync()
}
</script>

<style scoped>
.condition-picker {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  flex-wrap: wrap;
}
.cp-field {
  width: 130px;
  flex-shrink: 0;
}
.cp-op {
  width: 96px;
}
.cp-value {
  flex: 1;
  min-width: 140px;
  display: flex;
  align-items: center;
}
.cp-value__na {
  color: var(--ink-faint);
  font-size: var(--fs-12);
}
@media (max-width: 767px) {
  .cp-field {
    width: 100%;
  }
}
</style>
