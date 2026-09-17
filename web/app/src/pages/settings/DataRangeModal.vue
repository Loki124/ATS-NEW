<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    title="配置数据范围"
    :style="{ width: '760px' }"
    :mask-closable="false"
  >
    <div class="dr-wrap">
      <div class="dr-group-op">
        <span class="dr-label">组间关系</span>
        <n-radio-group :value="model.op" @update:value="setOp">
          <n-radio value="or">满足任一 (OR)</n-radio>
          <n-radio value="and">同时满足 (AND)</n-radio>
        </n-radio-group>
      </div>

      <div v-for="(g, gi) in model.groups" :key="gi" class="dr-group">
        <div class="dr-group-head">
          <span class="dr-group-title">条件组 {{ gi + 1 }}</span>
          <n-radio-group :value="g.op" size="small" @update:value="(v: string) => (g.op = v)">
            <n-radio value="or">组内 OR</n-radio>
            <n-radio value="and">组内 AND</n-radio>
          </n-radio-group>
          <n-button text type="error" size="small" @click="removeGroup(gi)">删除组</n-button>
        </div>

        <div v-for="(c, ci) in g.conditions" :key="ci" class="dr-cond">
          <n-select
            :value="c.dimension"
            :options="dimOptions"
            placeholder="维度"
            style="width: 110px"
            @update:value="(v: string) => onDim(gi, ci, v)"
          />
          <n-select
            v-if="c.dimension === 'dept'"
            :value="c.value"
            :options="deptOptions"
            placeholder="选择部门"
            filterable
            clearable
            style="width: 170px"
            @update:value="(v: string) => (c.value = v)"
          />
          <n-input
            v-else
            v-model:value="c.value"
            placeholder="填写值"
            style="width: 170px"
          />
          <n-select
            :value="c.operator"
            :options="opOptions"
            style="width: 96px"
            @update:value="(v: string) => (c.operator = v)"
          />
          <n-switch
            v-if="c.dimension === 'dept'"
            :value="!!c.includeSub"
            @update:value="(v: boolean) => (c.includeSub = v)"
          >
            <template #checked>含子级</template>
            <template #unchecked>仅本级</template>
          </n-switch>
          <n-button text type="error" size="small" @click="removeCond(gi, ci)">✕</n-button>
        </div>

        <n-button size="small" @click="addCond(gi)">+ 添加条件</n-button>
        <div v-if="g.conditions.length === 0" class="dr-hint">该组暂无条件（将忽略）</div>
      </div>

      <n-button @click="addGroup">+ 添加条件组</n-button>
      <div class="dr-foot-hint">
        当前仅「部门」维度真实生效；职务 / 司龄等维度为占位（no-op，不放开数据，后续版本补齐）。
      </div>
    </div>
    <template #footer>
      <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
        <n-button @click="visible = false">取消</n-button>
        <n-button type="primary" class="gradient-btn" @click="onConfirm">保存</n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { NModal, NButton, NRadio, NRadioGroup, NSelect, NInput, NSwitch } from 'naive-ui'
import { useDepartmentStore, type Department } from '@/stores/department'

interface Cond {
  dimension: string
  field?: string
  operator: string
  value: string
  includeSub?: boolean
}
interface Group {
  op: string
  conditions: Cond[]
}
interface RangeModel {
  op: string
  groups: Group[]
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
const dimOptions = [
  { label: '部门', value: 'dept' },
  { label: '职务', value: 'position' },
  { label: '司龄', value: 'tenure' },
]
const opOptions = [
  { label: '等于', value: 'eq' },
  { label: '不等于', value: 'neq' },
]

const model = ref<RangeModel>({ op: 'or', groups: [] })

function setOp(v: string) { model.value.op = v }
function addGroup() { model.value.groups.push({ op: 'or', conditions: [] }) }
function removeGroup(i: number) { model.value.groups.splice(i, 1) }
function addCond(gi: number) {
  model.value.groups[gi].conditions.push({ dimension: 'dept', operator: 'eq', value: '', includeSub: false })
}
function removeCond(gi: number, ci: number) {
  model.value.groups[gi].conditions.splice(ci, 1)
}
function onDim(gi: number, ci: number, v: string) {
  const c = model.value.groups[gi].conditions[ci]
  c.dimension = v
  c.value = ''
  if (v !== 'dept') delete c.includeSub
}

function onConfirm() {
  const cleaned: RangeModel = {
    op: model.value.op,
    groups: model.value.groups
      .map((g) => ({ op: g.op, conditions: g.conditions.filter((c) => (c.value ?? '') !== '') }))
      .filter((g) => g.conditions.length > 0),
  }
  emit('confirm', cleaned.groups.length ? cleaned : null)
  visible.value = false
}

watch(
  () => props.show,
  async (s) => {
    if (s) {
      if (!deptStore.departments.length) {
        try { await deptStore.loadDepartments() } catch { /* 降级 */ }
      }
      const v = props.value
      if (v && Array.isArray(v.groups) && v.groups.length) {
        model.value = JSON.parse(JSON.stringify(v))
      } else {
        model.value = { op: 'or', groups: [] }
      }
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.dr-wrap { display: flex; flex-direction: column; gap: var(--space-3); }
.dr-group-op { display: flex; align-items: center; gap: var(--space-3); }
.dr-label { font-size: 14px; color: var(--color-text-secondary); }
.dr-group {
  border: 1px solid var(--color-border); border-radius: 8px;
  padding: var(--space-3); display: flex; flex-direction: column; gap: var(--space-2);
}
.dr-group-head { display: flex; align-items: center; gap: var(--space-3); }
.dr-group-title { font-size: 14px; font-weight: 600; }
.dr-cond { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.dr-hint { font-size: 12px; color: var(--color-text-tertiary); }
.dr-foot-hint {
  font-size: 12px; color: var(--color-text-tertiary);
  background: var(--color-bg-subtle); padding: var(--space-2); border-radius: 6px;
}
</style>
