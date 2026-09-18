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
          :render-label="renderTreeLabel"
          @update:checked-keys="onChecked"
        />
        <n-empty v-else description="暂无部门数据" />
      </div>
      <div class="org-scope-selected">
        <div class="os-title-bar">
          <span>已选组织 ({{ checkedKeys.length }})</span>
          <n-button
            v-if="checkedKeys.length"
            text
            type="primary"
            size="tiny"
            @click="clearSelected"
          >
            清空已选
          </n-button>
        </div>
        <n-empty v-if="!checkedKeys.length" description="在左侧勾选部门" />
        <template v-else>
          <div class="os-table-header">
            <span>组织编码</span>
            <span>组织名称</span>
            <span>上级组织</span>
            <span>包含下级组织</span>
          </div>
          <div class="os-table-body">
            <div v-for="id in checkedKeys" :key="id" class="os-table-row">
              <span :title="deptCode(id)">{{ deptCode(id) }}</span>
              <span :title="deptName(id)">{{ deptName(id) }}</span>
              <span :title="parentName(id)">{{ parentName(id) }}</span>
              <span>
                <n-checkbox
                  :checked="includeMap[id]"
                  @update:checked="(v: boolean) => onInclude(id, v)"
                />
              </span>
            </div>
          </div>
        </template>
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
import { ref, computed, watch, h } from 'vue'
import { NTree, NEmpty, NButton, NModal, NCheckbox } from 'naive-ui'
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

function deptCode(id: string): string {
  return deptStore.departments.find((d) => String(d.id) === id)?.code || id
}

function parentName(id: string): string {
  const dept = deptStore.departments.find((d) => String(d.id) === id)
  if (!dept?.parentId) return '-'
  return deptStore.departments.find((d) => String(d.id) === String(dept.parentId))?.name || dept.parentId
}

function selectSiblings(key: string) {
  const target = deptStore.departments.find((d) => String(d.id) === key)
  if (!target) return
  const pid = target.parentId || null
  const siblingIds = deptStore.departments
    .filter((d) => (d.parentId || null) === pid)
    .map((d) => String(d.id))
  const set = new Set(checkedKeys.value)
  siblingIds.forEach((id) => set.add(id))
  checkedKeys.value = Array.from(set)
  const map = { ...includeMap.value }
  siblingIds.forEach((id) => {
    if (!(id in map)) map[id] = false
  })
  includeMap.value = map
}

function clearSelected() {
  checkedKeys.value = []
  includeMap.value = {}
}

function renderTreeLabel(info: { option: any }) {
  const key = String(info.option.key)
  return h(
    'span',
    { class: 'tree-label-row' },
    {
      default: () => [
        info.option.label as string,
        h(
          NButton,
          {
            text: true,
            type: 'primary',
            size: 'tiny',
            class: 'select-sibling-btn',
            onClick: (e: MouseEvent) => {
              e.stopPropagation()
              selectSiblings(key)
            },
          },
          { default: () => '选中同级' }
        ),
      ],
    }
  )
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
.os-title-bar {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 13px; color: var(--color-text-secondary); margin-bottom: var(--space-2);
}
.os-table-header,
.os-table-row {
  display: grid;
  grid-template-columns: 72px 1fr 72px 90px;
  gap: var(--space-2);
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
}
.os-table-header {
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
  font-weight: 500;
}
.os-table-row {
  border-bottom: 1px dashed var(--color-border);
}
.os-table-row > span,
.os-table-header > span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tree-label-row {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}
.select-sibling-btn {
  opacity: 0;
  padding: 0 4px;
  height: 18px;
  font-size: 12px;
  transition: opacity 0.2s;
}
:deep(.n-tree-node:hover) .select-sibling-btn {
  opacity: 1;
}
</style>
