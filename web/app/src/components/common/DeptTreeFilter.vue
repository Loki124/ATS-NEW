<!--
  部门树筛选器（组件库 · 通用组件，2026-10-22 新增）

  以「多选部门树 + 两个策略开关」的形式做部门筛选：
    ① 自动选中全部子部门 —— 勾一个部门即连同其全部下级一起选（筛选语义 = 该部门及其子树）
    ② 展示历史停用部门 —— 把已停用的部门也放进树里（停用部门下仍可能挂着历史数据）

  勾选传播 / 父子联动的规则全部在 `utils/deptTree.ts`（纯函数，可单测），
  组件只负责渲染与交互 —— 勾选规则最容易出「不报错、只是筛不出数据」的错，
  故不放在组件里。

  Props:
    - modelValue:      string[]  已选部门 id（v-model）
    - departments:     部门列表；不传则取 `useDepartmentStore()` 的共享缓存
    - placeholder:     未选时的占位文案（默认「全部部门」）
    - width:           触发器宽度（默认 200px）
    - disabled:        禁用
    - autoSelectChildren: 「自动选中全部子部门」初始值（默认 true）
    - showInactive:      「展示历史停用部门」初始值（默认 false）
    - searchable:      是否显示搜索框（默认 true）
    - panelWidth:      面板宽度（默认 320px）

  Emits:
    - update:modelValue        已选部门 id 列表（变化即回传，由调用方决定何时查询）
    - update:autoSelectChildren
    - update:showInactive
-->
<template>
  <div class="dept-filter" :style="{ width: width }">
    <n-popover
      v-model:show="panelVisible"
      trigger="click"
      placement="bottom-start"
      :width="panelWidth"
      :show-arrow="false"
      raw
    >
      <template #trigger>
        <button
          type="button"
          class="dept-filter__trigger"
          :disabled="disabled"
          :aria-expanded="panelVisible"
          :aria-label="ariaLabel"
        >
          <span class="dept-filter__value" :class="{ 'is-placeholder': !summary }">
            {{ summary || placeholder }}
          </span>
          <n-icon class="dept-filter__arrow" :component="ChevronDownOutline" />
        </button>
      </template>

      <div class="dept-filter__panel">
        <!-- 策略开关 -->
        <div class="dept-filter__options">
          <div class="dept-filter__option">
            <n-switch
              v-model:value="autoSelect"
              size="small"
              aria-label="自动选中全部子部门"
              @update:value="emit('update:autoSelectChildren', $event)"
            />
            <span class="dept-filter__option-text" @click="autoSelect = !autoSelect">
              自动选中全部子部门
            </span>
          </div>
          <div class="dept-filter__option">
            <n-switch
              v-model:value="showInactive"
              size="small"
              aria-label="展示历史停用部门"
              @update:value="emit('update:showInactive', $event)"
            />
            <span class="dept-filter__option-text" @click="showInactive = !showInactive">
              展示历史停用部门
            </span>
          </div>
        </div>

        <!-- 搜索 -->
        <n-input
          v-if="searchable"
          v-model:value="keyword"
          size="small"
          class="dept-filter__search"
          placeholder="搜索部门名称"
          clearable
        />

        <!-- 部门树 -->
        <div class="dept-filter__tree">
          <n-tree
            v-if="treeData.length"
            :data="treeData"
            :filter="filterFn"
            :pattern="keyword"
            :checked-keys="selection.checked"
            :indeterminate-keys="selection.indeterminate"
            :expanded-keys="expandedKeys"
            :node-props="nodeProps"
            checkable
            :cascade="false"
            block-line
            @update:checked-keys="onCheck"
            @update:expanded-keys="expandedKeys = $event as string[]"
          />
          <n-empty v-else description="暂无可筛选的部门" size="small" class="dept-filter__empty" />
        </div>

        <!-- 底部：清空 + 已选计数 -->
        <div class="dept-filter__footer">
          <n-button size="small" quaternary :disabled="!selected.length" @click="clearAll">
            清空
          </n-button>
          <span class="dept-filter__count">已选 {{ selection.checked.length }} 个部门</span>
        </div>
      </div>
    </n-popover>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NEmpty, NIcon, NInput, NPopover, NSwitch, NTree } from 'naive-ui'
import { ChevronDownOutline } from '@vicons/ionicons5'
import { useDepartmentStore } from '../../stores/department'
import {
  buildDeptFilterTree,
  computeDeptSelection,
  deptSelectionSummary,
  toggleDeptNode,
  type DeptLike,
} from '../../utils/deptTree'

const props = withDefaults(
  defineProps<{
    modelValue?: string[]
    departments?: DeptLike[]
    placeholder?: string
    width?: string
    disabled?: boolean
    autoSelectChildren?: boolean
    showInactive?: boolean
    searchable?: boolean
    panelWidth?: number
  }>(),
  {
    modelValue: () => [],
    departments: undefined,
    placeholder: '全部部门',
    width: '200px',
    disabled: false,
    autoSelectChildren: true,
    showInactive: false,
    searchable: true,
    panelWidth: 320,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', val: string[]): void
  (e: 'update:autoSelectChildren', val: boolean): void
  (e: 'update:showInactive', val: boolean): void
}>()

const deptStore = useDepartmentStore()

const panelVisible = ref(false)
const keyword = ref('')
const autoSelect = ref(props.autoSelectChildren)
const showInactive = ref(props.showInactive)
/** 已选部门 id（受控于 modelValue） */
const selected = ref<string[]>([...(props.modelValue ?? [])])

// 外部改 v-model（如清空、外部塞值）→ 同步内部状态
watch(
  () => props.modelValue,
  (v) => {
    const next = (v ?? []).map(String)
    if (next.join('|') !== selected.value.join('|')) selected.value = next
  },
)

const deptList = computed<DeptLike[]>(() =>
  (props.departments ?? deptStore.departments ?? []) as DeptLike[],
)

const tree = computed(() =>
  buildDeptFilterTree(deptList.value, { includeInactive: showInactive.value }),
)

/** n-tree 的 data：停用部门在名称后加「（停用）」标记 */
const treeData = computed(() => {
  const walk = (nodes: any[]): any[] =>
    nodes.map((n) => ({
      ...n,
      label: n.inactive ? `${n.name}（停用）` : n.name,
      children: n.children?.length ? walk(n.children) : undefined,
    }))
  return walk(tree.value.nodes)
})

/** 勾选状态（实心勾 + 半选） */
const selection = computed(() => computeDeptSelection(tree.value, selected.value))

/** 触发器文案：只显示「顶层已选」（选了父部门就不重复列它的孩子） */
const summary = computed(() => deptSelectionSummary(tree.value, selected.value))

const ariaLabel = computed(
  () => `${props.placeholder}（已选 ${selection.value.checked.length} 个部门）`,
)

/** 默认展开前两层（再深就得自己点了） */
const expandedKeys = ref<string[]>([])
const collectDepthKeys = (nodes: any[], depth: number, level = 0): string[] => {
  if (level >= depth) return []
  const out: string[] = []
  for (const n of nodes) {
    out.push(n.key)
    if (n.children?.length) out.push(...collectDepthKeys(n.children, depth, level + 1))
  }
  return out
}
watch(
  tree,
  (t) => {
    expandedKeys.value = collectDepthKeys(t.nodes, 2)
  },
  { immediate: true },
)

/** 搜索：按部门名匹配（不匹配「（停用）」后缀） */
const filterFn = (pattern: string, node: any): boolean => {
  const kw = (pattern || '').trim().toLowerCase()
  if (!kw) return true
  return String(node.name || '').toLowerCase().includes(kw)
}

/** 节点语义：停用部门给出说明，便于读屏与 hover */
const nodeProps = ({ option }: any) => ({
  'aria-label': option.inactive ? `${option.name}（已停用）` : option.name,
  class: option.inactive ? 'dept-filter__node--inactive' : undefined,
})

/**
 * 勾选处理。
 * n-tree 关掉了 cascade（级联由我们自己算），所以它只会把「当前集合 ± 1 个 key」
 * 回传 —— 靠集合差分定位被点的那个 key。
 */
const onCheck = (keys: Array<string | number>) => {
  const nextSet = new Set(keys.map(String))
  const curSet = new Set(selected.value)
  const added = [...nextSet].filter((k) => !curSet.has(k))
  const removed = [...curSet].filter((k) => !nextSet.has(k))
  const key = added[0] ?? removed[0]
  if (!key) return
  const nextSelected = toggleDeptNode(
    tree.value,
    [...curSet],
    key,
    added.length > 0,
    autoSelect.value,
  )
  selected.value = nextSelected
  emit('update:modelValue', nextSelected)
}

const clearAll = () => {
  selected.value = []
  emit('update:modelValue', [])
}
</script>

<style scoped>
/* 触发器：与工具栏里的 n-select 同一档高度（34px / 中档），保持一行排布整齐 */
.dept-filter__trigger {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  height: 34px;
  padding: 0 var(--space-2) 0 var(--space-3);
  font-size: var(--text-body);
  color: var(--ink);
  background: var(--surface);
  border: 1px solid var(--g3);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color 0.15s var(--ease-out);
}
.dept-filter__trigger:hover:not(:disabled) { border-color: var(--brand); }
.dept-filter__trigger:focus-visible {
  outline: 2px solid var(--brand-button);
  outline-offset: 2px;
}
.dept-filter__trigger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.dept-filter__value {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}
.dept-filter__value.is-placeholder { color: var(--ink-faint); }
.dept-filter__arrow { color: var(--g5); flex-shrink: 0; }

.dept-filter__panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--surface-elevated);
  border-radius: var(--radius-md);
  box-shadow: 0 6px 16px -9px rgba(0, 0, 0, 0.12);
}

.dept-filter__options {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-hairline);
}
.dept-filter__option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
/* 开关文字本身也可点（点文字 = 切开关） */
.dept-filter__option-text {
  font-size: var(--text-small);
  color: var(--ink-soft);
  cursor: pointer;
  user-select: none;
}
.dept-filter__option-text:hover { color: var(--brand); }

.dept-filter__search { flex-shrink: 0; }

/* 树区：固定高度 + 内部滚动（面板不随部门数量无限长高） */
.dept-filter__tree {
  height: 260px;
  overflow-y: auto;
  overflow-x: hidden;
}
.dept-filter__empty { padding: var(--space-4) 0; }

.dept-filter__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--border-hairline);
}
.dept-filter__count {
  font-size: var(--text-meta);
  color: var(--ink-faint);
  font-variant-numeric: tabular-nums;
}
</style>
