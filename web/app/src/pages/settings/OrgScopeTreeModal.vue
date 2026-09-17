<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    title="配置组织范围"
    :style="{ width: '720px' }"
    :mask-closable="false"
  >
    <div class="org-scope-body">
      <div class="org-scope-tree">
        <n-tree
          v-if="treeOptions.length"
          :data="treeOptions"
          checkable
          block-line
          :default-expand-all="true"
          :checked-keys="checkedKeys"
          @update:checked-keys="onChecked"
        />
        <n-empty v-else description="暂无部门数据" />
      </div>
      <div class="org-scope-selected">
        <div class="os-title">已选组织 ({{ checkedKeys.length }})</div>
        <n-empty v-if="!checkedKeys.length" description="在左侧勾选部门" />
        <div v-for="id in checkedKeys" :key="id" class="os-row">
          <span class="os-name">{{ deptName(id) }}</span>
          <n-switch :value="includeMap[id]" @update:value="(v: boolean) => onInclude(id, v)">
            <template #checked>含下级</template>
            <template #unchecked>仅本级</template>
          </n-switch>
        </div>
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
import { NTree, NEmpty, NButton, NSwitch, NModal } from 'naive-ui'
import { useDepartmentStore, type Department } from '@/stores/department'

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
const checkedKeys = ref<string[]>([])
const includeMap = ref<Record<string, boolean>>({})

const treeOptions = computed(() => buildTree(deptStore.departments))

function buildTree(list: Department[]): any[] {
  const byId = new Map<string, any>()
  list.forEach((d) => byId.set(String(d.id), { label: d.name, key: String(d.id), children: [] as any[] }))
  const roots: any[] = []
  list.forEach((d) => {
    const node = byId.get(String(d.id))!
    const pid = d.parentId ? String(d.parentId) : null
    if (pid && byId.has(pid)) byId.get(pid)!.children.push(node)
    else roots.push(node)
  })
  return roots
}

function deptName(id: string): string {
  return deptStore.departments.find((d) => String(d.id) === id)?.name || id
}

function onChecked(keys: Array<string | number>) {
  checkedKeys.value = keys.map(String)
}

function onInclude(id: string, v: boolean) {
  includeMap.value = { ...includeMap.value, [id]: v }
}

function onConfirm() {
  const payload: OrgScopeNode[] = checkedKeys.value.map((id) => ({
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
      if (!deptStore.departments.length) {
        try { await deptStore.loadDepartments() } catch { /* 降级 */ }
      }
      const arr = (props.value || []).filter((x) => x && x.deptId)
      checkedKeys.value = arr.map((x) => String(x.deptId))
      const m: Record<string, boolean> = {}
      arr.forEach((x) => { m[String(x.deptId)] = !!x.includeChildren })
      includeMap.value = m
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.org-scope-body { display: flex; gap: var(--space-4); min-height: 320px; }
.org-scope-tree {
  flex: 1; border: 1px solid var(--color-border); border-radius: 8px;
  padding: var(--space-2); overflow: auto; max-height: 360px;
}
.org-scope-selected {
  flex: 1; border: 1px solid var(--color-border); border-radius: 8px;
  padding: var(--space-2); overflow: auto; max-height: 360px;
}
.os-title { font-size: 13px; color: var(--color-text-secondary); margin-bottom: var(--space-2); }
.os-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 0; border-bottom: 1px dashed var(--color-border);
}
.os-name { font-size: 14px; }
</style>
