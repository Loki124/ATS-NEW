<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    :title="t('pages.settings.OrgScopeTreeModal.s6')"
    :style="{ width: '760px' }"
    :mask-closable="false"
  >
    <!-- 标题行：包含停用开关 + 批量包含下级组织 -->
    <div class="os-header-bar">
      <div class="os-header-left">
        <n-switch v-model:value="includeDisabled" size="small" />
        <span class="os-header-label">{ t('pages.settings.OrgScopeTreeModal.s1') }</span>
      </div>
      <div class="os-header-right">
        <n-switch
          :value="batchAllInclude"
          size="small"
          :disabled="!selectedKeys.length"
          @update:value="batchToggle"
        />
        <span class="os-header-label">{ t('pages.settings.OrgScopeTreeModal.s2') }</span>
      </div>
    </div>

    <div class="org-scope-body">
      <!-- 可选组织（窄） -->
      <div class="org-scope-tree glass-card">
        <div class="os-title-bar">
          <span>{ t('pages.settings.OrgScopeTreeModal.s3') }</span>
          <span class="os-count">{{ visibleAvailable.length }}</span>
        </div>
        <n-input
          v-model:value="sourceFilter"
          :placeholder="t('pages.settings.OrgScopeTreeModal.s5')"
          clearable
          size="small"
          class="os-search"
        />
        <div class="panel-content">
          <n-empty
            v-if="!visibleAvailable.length"
            :description="includeDisabled ? '暂无部门' : '无可用部门（停用已隐藏）'"
          />
          <div
            v-for="d in visibleAvailable"
            v-else
            :key="d.id"
            class="os-avail-row"
          >
            <n-checkbox
              :checked="availableChecked.includes(d.id)"
              @update:checked="(v: boolean) => onAvailCheck(d.id, v)"
            />
            <span class="os-avail-name" :title="d.name">{{ d.name }}</span>
            <span v-if="d.status === 'INACTIVE'" class="os-tag-disabled">{ t('pages.settings.OrgScopeTreeModal.s4') }</span>
          </div>
        </div>
      </div>

      <!-- 穿梭按钮 -->
      <div class="os-shuttle">
        <n-button
          size="small"
          type="primary"
          :disabled="!availableChecked.length"
          @click="addToSelected"
        >
          添加 →
        </n-button>
        <n-button
          size="small"
          :disabled="!selectedChecked.length"
          @click="removeFromSelected"
        >
          ← 移除
        </n-button>
      </div>

      <!-- 已选组织（宽） -->
      <div class="org-scope-selected glass-card">
        <div class="os-title-bar">
          <span>已选组织 ({{ selectedKeys.length }})</span>
          <n-button
            v-if="selectedKeys.length"
            text
            type="primary"
            size="tiny"
            @click="clearSelected"
          >
            清空已选
          </n-button>
        </div>
        <div class="panel-content">
          <n-empty v-if="!selectedKeys.length" description="在左侧勾选部门后添加" />
          <template v-else>
            <div v-for="id in selectedKeys" :key="id" class="os-sel-row">
              <n-checkbox
                :checked="selectedChecked.includes(id)"
                @update:checked="(v: boolean) => onSelCheck(id, v)"
              />
              <span class="os-sel-name" :title="deptName(id)">{{ deptName(id) }}</span>
              <span class="os-sel-code" :title="deptCode(id)">{{ deptCode(id) }}</span>
              <n-checkbox
                class="os-sel-include"
                :checked="!!includeMap[id]"
                @update:checked="(v: boolean) => onInclude(id, v)"
              >
                含下级
              </n-checkbox>
              <n-button text size="tiny" type="error" @click="removeOne(id)">×</n-button>
            </div>
          </template>
        </div>
      </div>
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
import { useI18n } from 'vue-i18n'
import { ref, computed, watch } from 'vue'
import { NModal, NButton, NSwitch, NInput, NCheckbox, NEmpty } from 'naive-ui'
import { useDepartmentStore, type Department } from '@/stores/department'
const { t } = useI18n()

export interface OrgScopeNode {
  deptId: string
  includeChildren: boolean
}

const props = defineProps<{
  show: boolean
  value: OrgScopeNode[] | null
}>()
const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'confirm', v: OrgScopeNode[]): void
}>()

const visible = computed({
  get: () => props.show,
  set: (v) => emit('update:show', v),
})

const deptStore = useDepartmentStore()

// 已选部门 id（保序）；includeMap 记录每个已选的「包含下级」
const selectedKeys = ref<string[]>([])
const includeMap = ref<Record<string, boolean>>({})
// 可选/已选列表内的勾选（用于穿梭）
const availableChecked = ref<string[]>([])
const selectedChecked = ref<string[]>([])
// 标题行开关
const includeDisabled = ref(false)
const sourceFilter = ref('')
const loading = ref(false)

/** 可选列表 = 未选中的部门，按「包含停用」与搜索词过滤（默认排除停用） */
const visibleAvailable = computed<Department[]>(() => {
  const sel = new Set(selectedKeys.value)
  const kw = sourceFilter.value.trim().toLowerCase()
  return deptStore.departments.filter((d) => {
    if (sel.has(String(d.id))) return false
    if (!includeDisabled.value && d.status === 'INACTIVE') return false
    if (kw && !d.name.toLowerCase().includes(kw)) return false
    return true
  })
})

/** 标题行「批量包含下级」开关的展示态：已选非空且全部为含下级 */
const batchAllInclude = computed(
  () => selectedKeys.value.length > 0 && selectedKeys.value.every((id) => includeMap.value[id]),
)

function deptName(id: string): string {
  return deptStore.departments.find((d) => String(d.id) === id)?.name || id
}
function deptCode(id: string): string {
  return deptStore.departments.find((d) => String(d.id) === id)?.code || id
}

function onAvailCheck(id: string, v: boolean) {
  const s = new Set(availableChecked.value)
  if (v) s.add(id)
  else s.delete(id)
  availableChecked.value = Array.from(s)
}
function onSelCheck(id: string, v: boolean) {
  const s = new Set(selectedChecked.value)
  if (v) s.add(id)
  else s.delete(id)
  selectedChecked.value = Array.from(s)
}
function onInclude(id: string, v: boolean) {
  includeMap.value = { ...includeMap.value, [id]: v }
}

/** 可选 → 已选（穿梭） */
function addToSelected() {
  const next = [...selectedKeys.value]
  const m = { ...includeMap.value }
  availableChecked.value.forEach((id) => {
    if (!next.includes(id)) {
      next.push(id)
      if (!(id in m)) m[id] = false
    }
  })
  selectedKeys.value = next
  includeMap.value = m
  availableChecked.value = []
}
/** 已选 → 可选（穿梭） */
function removeFromSelected() {
  const rm = new Set(selectedChecked.value)
  selectedKeys.value = selectedKeys.value.filter((id) => !rm.has(id))
  const m = { ...includeMap.value }
  rm.forEach((id) => delete m[id])
  includeMap.value = m
  selectedChecked.value = []
}
function removeOne(id: string) {
  selectedKeys.value = selectedKeys.value.filter((x) => x !== id)
  const m = { ...includeMap.value }
  delete m[id]
  includeMap.value = m
  selectedChecked.value = selectedChecked.value.filter((x) => x !== id)
}
function clearSelected() {
  selectedKeys.value = []
  includeMap.value = {}
  selectedChecked.value = []
}
/** 标题行批量：对全部已选统一置位「包含下级」 */
function batchToggle(v: boolean) {
  const m = { ...includeMap.value }
  selectedKeys.value.forEach((id) => {
    m[id] = v
  })
  includeMap.value = m
}

function onConfirm() {
  const payload: OrgScopeNode[] = selectedKeys.value.map((id) => ({
    deptId: id,
    includeChildren: includeMap.value[id] ?? false,
  }))
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
      const arr = (props.value || []).filter((x) => x && x.deptId)
      selectedKeys.value = arr.map((x) => String(x.deptId))
      const m: Record<string, boolean> = {}
      arr.forEach((x) => {
        m[String(x.deptId)] = !!x.includeChildren
      })
      includeMap.value = m
      availableChecked.value = []
      selectedChecked.value = []
      sourceFilter.value = ''
      includeDisabled.value = false
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.org-scope-body {
  display: flex;
  gap: var(--space-3);
  align-items: stretch;
  min-height: 340px;
}
/* 可选（窄） */
.org-scope-tree {
  flex: 0 0 240px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: var(--space-2);
  max-height: 380px;
}
/* 已选（宽） */
.org-scope-selected {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: var(--space-2);
  max-height: 380px;
}
.os-shuttle {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: var(--space-3);
  flex: 0 0 auto;
}
.panel-content {
  flex: 1;
  min-height: 0;
  overflow: auto;
  margin-top: var(--space-2);
}
.os-title-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}
.os-count {
  font-variant-numeric: tabular-nums;
  color: var(--color-text-tertiary);
}
.os-search {
  margin: var(--space-2) 0;
}
.os-avail-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 6px 0;
  font-size: 13px;
  cursor: pointer;
}
.os-avail-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.os-tag-disabled {
  flex: 0 0 auto;
  font-size: 11px;
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
  border-radius: 4px;
  padding: 0 4px;
  line-height: 16px;
}
.os-sel-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 6px 0;
  font-size: 13px;
  border-bottom: 1px dashed var(--color-border);
}
.os-sel-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.os-sel-code {
  flex: 0 0 90px;
  color: var(--color-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.os-sel-include {
  flex: 0 0 auto;
}
.os-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-3);
  flex-wrap: wrap;
}
.os-header-left,
.os-header-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.os-header-label {
  font-size: 13px;
  color: var(--color-text-secondary);
}
</style>
