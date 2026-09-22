<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    title="配置人员范围"
    :style="{ width: '760px' }"
    :mask-closable="false"
  >
    <div class="dr-wrap">
      <!-- 顶部：数据范围（只读，当前仅管理人员范围） -->
      <n-form-item label="数据范围" required label-placement="left" class="dr-scope-item">
        <n-select
          :value="'person'"
          :options="[{ label: '管理人员范围', value: 'person' }]"
          disabled
          style="width: 100%"
        />
      </n-form-item>

      <!-- 筛选条件 -->
      <div class="dr-section-head">
        <div class="dr-section-title">
          <span class="dr-section-bar"></span>
          <span>筛选条件设置</span>
        </div>
        <div class="dr-section-sub">筛选条件设置完成后，将根据条件筛选数据范围</div>
      </div>

      <div class="dr-rows">
        <div v-for="(row, i) in rows" :key="i" class="dr-row">
          <span class="dr-row-index">{{ i + 1 }}.</span>
          <n-select
            :value="row.field || 'job_record'"
            :options="sourceOptions"
            placeholder="来源"
            style="width: 120px"
            @update:value="(v: string) => (row.field = v)"
          />
          <n-select
            :value="row.dimension"
            :options="dimOptions"
            placeholder="维度"
            style="width: 130px"
            @update:value="(v: string) => onDim(i, v)"
          />
          <n-select
            :value="row.operator"
            :options="opOptions"
            placeholder="运算符"
            style="width: 110px"
            @update:value="(v: string) => (row.operator = v)"
          />
          <template v-if="row.dimension === 'dept'">
            <n-select
              :value="row.value"
              :options="deptOptions"
              placeholder="选择部门"
              filterable
              clearable
              style="flex: 1; min-width: 160px"
              @update:value="(v: string) => (row.value = v)"
            />
            <n-switch
              :value="!!row.includeSub"
              @update:value="(v: boolean) => (row.includeSub = v)"
            >
              <template #checked>含下级</template>
              <template #unchecked>仅本级</template>
            </n-switch>
          </template>
          <n-input
            v-else
            v-model:value="row.value"
            placeholder="填写值"
            style="flex: 1; min-width: 160px"
          />
          <n-button text type="error" size="small" @click="removeRow(i)">
            <template #icon><n-icon :component="TrashOutline" /></template>
          </n-button>
        </div>
      </div>

      <n-button text type="primary" class="dr-add" @click="addRow">
        <template #icon><n-icon :component="AddOutline" /></template>
        新增
      </n-button>

      <!-- 条件表达式 -->
      <n-form-item label="条件表达式" required label-placement="left" class="dr-expr-item">
        <n-input
          :value="exprText"
          placeholder="如：1 or 2"
          readonly
        />
        <template #feedback>
          当前仅「部门」维度真实生效；其它维度为占位（no-op，不放开数据，后续版本补齐）。
        </template>
      </n-form-item>
    </div>

    <template #footer>
      <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
        <n-button @click="visible = false">取消</n-button>
        <n-button type="primary" class="gradient-btn" :loading="loading" :disabled="loading" @click="onConfirm">保存</n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  NModal, NButton, NSelect, NInput, NSwitch, NIcon, NFormItem,
} from 'naive-ui'
import { AddOutline, TrashOutline } from '@vicons/ionicons5'
import { useDepartmentStore, type Department } from '@/stores/department'

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
  { label: '任职记录', value: 'job_record' },
  { label: '合同协议', value: 'contract' },
  { label: '员工信息', value: 'employee' },
]
const dimOptions = [
  { label: '部门', value: 'dept' },
  { label: '工作地点', value: 'work_place' },
  { label: '职级', value: 'job_level' },
  { label: '人员类别', value: 'person_type' },
  { label: '用工形式', value: 'employment_type' },
  { label: '职等', value: 'job_grade' },
  { label: '雇佣关系', value: 'employment_relation' },
  { label: '职务序列', value: 'position_sequence' },
]
const opOptions = [
  { label: '等于', value: 'eq' },
  { label: '不等于', value: 'neq' },
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
