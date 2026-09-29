<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    :title="t('pages.settings.DataRangeModal.s7')"
    :style="{ width: '760px' }"
    :mask-closable="false"
  >
    <div class="dr-wrap">
      <!-- 顶部：数据范围（只读，当前仅管理人员范围） -->
      <n-form-item :label="t('pages.settings.DataRangeModal.s8')" required label-placement="left" class="dr-scope-item">
        <n-select
          :value="'person'"
          :options="[{ label: t('pages.settings.DataRangeModal.s9'), value: 'person' }]"
          disabled
          style="width: 100%"
        />
      </n-form-item>

      <!-- 筛选条件 -->
      <div class="dr-section-head">
        <div class="dr-section-title">
          <span class="dr-section-bar"></span>
          <span>{{ t('pages.settings.DataRangeModal.s1') }}</span>
        </div>
        <div class="dr-section-sub">{{ t('pages.settings.DataRangeModal.s2') }}</div>
      </div>

      <div class="dr-rows">
        <div v-for="(row, i) in rows" :key="i" class="dr-row">
          <span class="dr-row-index">{{ i + 1 }}.</span>
          <n-select
            :value="row.field || 'job_record'"
            :options="sourceOptions"
            :placeholder="t('pages.settings.DataRangeModal.s3')"
            style="width: 120px"
            @update:value="(v: string) => (row.field = v)"
          />
          <n-select
            :value="row.dimension"
            :options="dimOptions"
            :placeholder="t('pages.settings.DataRangeModal.s4')"
            style="width: 130px"
            @update:value="(v: string) => onDim(i, v)"
          />
          <n-select
            :value="row.operator"
            :options="opOptions"
            :placeholder="t('pages.settings.DataRangeModal.s5')"
            style="width: 110px"
            @update:value="(v: string) => (row.operator = v)"
          />
          <template v-if="row.dimension === 'dept'">
            <n-select
              :value="row.value"
              :options="deptOptions"
              :placeholder="t('pages.settings.DataRangeModal.s6')"
              filterable
              clearable
              style="flex: 1; min-width: 160px"
              @update:value="(v: string) => (row.value = v)"
            />
            <n-switch
              :value="!!row.includeSub"
              @update:value="(v: boolean) => (row.includeSub = v)"
            >
              <template #checked>{{ t('pages.settings.DataRangeModal.s10') }}</template>
              <template #unchecked>{{ t('pages.settings.DataRangeModal.s11') }}</template>
            </n-switch>
          </template>
          <n-input
            v-else
            v-model:value="row.value"
            :placeholder="t('pages.settings.DataRangeModal.s12')"
            style="flex: 1; min-width: 160px"
          />
          <n-button text type="error" size="small" @click="removeRow(i)">
            <template #icon><n-icon :component="TrashOutline" /></template>
          </n-button>
        </div>
      </div>

      <n-button text type="primary" class="dr-add" @click="addRow">
        <template #icon><n-icon :component="AddOutline" /></template>
        {{ t('pages.settings.DataRangeModal.s13') }}
      </n-button>

      <!-- 条件表达式 -->
      <n-form-item :label="t('pages.settings.DataRangeModal.s14')" required label-placement="left" class="dr-expr-item">
        <n-input
          :value="exprText"
          :placeholder="t('pages.settings.DataRangeModal.s15')"
          readonly
        />
        <template #feedback>
          {{ t('pages.settings.DataRangeModal.s16') }}
        </template>
      </n-form-item>
    </div>

    <template #footer>
      <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
        <n-button @click="visible = false">{{ t('pages.settings.DataRangeModal.s17') }}</n-button>
        <n-button type="primary" class="gradient-btn" :loading="loading" :disabled="loading" @click="onConfirm">{{ t('pages.settings.DataRangeModal.s18') }}</n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed, watch } from 'vue'
import {
  NModal, NButton, NSelect, NInput, NSwitch, NIcon, NFormItem,
} from 'naive-ui'
import { AddOutline, TrashOutline } from '@vicons/ionicons5'
import { useDepartmentStore, type Department } from '@/stores/department'
const { t } = useI18n()

interface Cond {
  field: string
  dimension: string
  operator: string
  value: string
  includeSub?: boolean
}

const props = defineProps<{ show: boolean; value: any }>()
const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'confirm', v: any): void
}>()

const visible = computed({
  get: () => props.show,
  set: (v) => emit('update:show', v),
})

const deptStore = useDepartmentStore()
const deptOptions = computed(() =>
  deptStore.departments.map((d: Department) => ({ label: d.name, value: String(d.id) })),
)

const sourceOptions = [
  { label: t('pages.settings.DataRangeModal.s19'), value: 'job_record' },
  { label: t('pages.settings.DataRangeModal.s20'), value: 'contract' },
  { label: t('pages.settings.DataRangeModal.s21'), value: 'employee' },
]
const dimOptions = [
  { label: t('pages.settings.DataRangeModal.s22'), value: 'dept' },
  { label: t('pages.settings.DataRangeModal.s23'), value: 'work_place' },
  { label: t('pages.settings.DataRangeModal.s24'), value: 'job_level' },
  { label: t('pages.settings.DataRangeModal.s25'), value: 'person_type' },
  { label: t('pages.settings.DataRangeModal.s26'), value: 'employment_type' },
  { label: t('pages.settings.DataRangeModal.s27'), value: 'job_grade' },
  { label: t('pages.settings.DataRangeModal.s28'), value: 'employment_relation' },
  { label: t('pages.settings.DataRangeModal.s29'), value: 'position_sequence' },
]
const opOptions = [
  { label: t('pages.settings.DataRangeModal.s30'), value: 'eq' },
  { label: t('pages.settings.DataRangeModal.s31'), value: 'neq' },
]

const op = ref('or')
const rows = ref<Cond[]>([])
const loading = ref(false)

const exprText = computed(() => {
  if (rows.value.length === 0) return ''
  if (rows.value.length === 1) return '1'
  const nums = rows.value.map((_, i) => String(i + 1))
  return nums.join(` ${op.value} `)
})

function addRow() {
  rows.value.push({
    field: 'job_record',
    dimension: 'dept',
    operator: 'eq',
    value: '',
    includeSub: false,
  })
}
function removeRow(i: number) { rows.value.splice(i, 1) }
function onDim(i: number, v: string) {
  const row = rows.value[i]
  row.dimension = v
  row.value = ''
  if (v === 'dept') row.includeSub = false
  else delete row.includeSub
}

function onConfirm() {
  const cleaned = rows.value.filter((r) => (r.value ?? '') !== '')
  const payload = cleaned.length
    ? {
        op: op.value,
        groups: cleaned.map((r) => ({
          op: 'or',
          conditions: [{ ...r }],
        })),
      }
    : null
  emit('confirm', payload)
  visible.value = false
}

watch(
  () => props.show,
  async (s) => {
    if (s) {
      loading.value = true
      try {
        if (!deptStore.departments.length) {
          await deptStore.loadDepartments()
        }
      } catch {
        /* 降级 */
      } finally {
        loading.value = false
      }
      const v = props.value
      op.value = v?.op || 'or'
      if (v && Array.isArray(v.groups) && v.groups.length) {
        // 将 group-based 结构展平为行列表（每行 = 一个条件）
        const flat: Cond[] = []
        v.groups.forEach((g: any) => {
          ;(g?.conditions || []).forEach((c: any) => {
            flat.push({
              field: c?.field || 'job_record',
              dimension: c?.dimension || 'dept',
              operator: c?.operator || 'eq',
              value: c?.value ?? '',
              includeSub: c?.includeSub ?? false,
            })
          })
        })
        rows.value = flat
      } else {
        rows.value = []
      }
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.dr-wrap { display: flex; flex-direction: column; gap: var(--space-3); }
.dr-scope-item { margin-bottom: 0; }
.dr-scope-item :deep(.n-form-item-label) { font-weight: 500; }

.dr-section-head { display: flex; flex-direction: column; gap: 4px; }
.dr-section-title {
  display: flex; align-items: center; gap: var(--space-2);
  font-size: 14px; font-weight: 600; color: var(--color-text-primary);
}
.dr-section-bar {
  width: 4px; height: 14px; border-radius: 2px;
  background: var(--color-primary);
}
.dr-section-sub {
  font-size: 12px; color: var(--color-text-tertiary);
  padding-left: calc(4px + var(--space-2));
}

.dr-rows { display: flex; flex-direction: column; gap: var(--space-2); }
.dr-row {
  display: flex; align-items: center; gap: var(--space-2);
  flex-wrap: wrap;
}
.dr-row-index {
  width: 20px; text-align: right;
  font-size: 14px; color: var(--color-text-secondary);
}

.dr-add { justify-content: flex-start; width: fit-content; }

.dr-expr-item { margin-bottom: 0; }
.dr-expr-item :deep(.n-form-item-feedback) { color: var(--color-text-tertiary); }
</style>
