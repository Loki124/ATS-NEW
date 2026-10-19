<template>
  <div class="perm-node" :class="{ 'perm-node--root': depth === 0 }">
    <!-- 分组节点（含子节点）：可折叠 -->
    <template v-if="node.children.length">
      <div class="pn-head" :class="{ 'pn-head--root': depth === 0 }">
        <button
          v-if="depth > 0"
          class="pn-caret"
          :class="{ 'pn-caret--open': expanded }"
          type="button"
          :aria-label="expanded ? '收起' : '展开'"
          @click="toggleExpand"
        >
          ▸
        </button>
        <span class="pn-name" :title="node.label">{{ node.label }}</span>
        <span class="pn-count">{{ totalCodes }}</span>
        <span class="pn-selected">{{ t('pages.settings.permission.RoleEditModal.s38', { n: selectedCount }) }}</span>

        <!-- 模块卡（depth 0）：展开/收起全部 + 全选 -->
        <template v-if="depth === 0">
          <n-button
            v-if="descendantGroups > 0"
            text
            size="tiny"
            class="pn-expand"
            @click="toggleExpandAll(!allExpanded)"
          >
            {{ allExpanded ? t('pages.settings.permission.RoleEditModal.s42') : t('pages.settings.permission.RoleEditModal.s41') }}
          </n-button>
          <n-checkbox
            class="pn-all"
            :checked="allChecked"
            :indeterminate="indeterminate"
            @update:checked="(v: boolean) => toggle(v)"
          >
            {{ t('pages.settings.permission.RoleEditModal.s37') }}
          </n-checkbox>
        </template>
        <!-- 中间分组（depth > 0）：仅全选（折叠头部的全选框在 group 之外，规避 naive 的 NCheckbox 无 value 必丢 checked 的坑） -->
        <n-checkbox
          v-else
          class="pn-all"
          :checked="allChecked"
          :indeterminate="indeterminate"
          @update:checked="(v: boolean) => toggle(v)"
        >
          {{ t('pages.settings.permission.RoleEditModal.s37') }}
        </n-checkbox>
      </div>

      <div v-show="depth === 0 || expanded" class="pn-body" :class="{ 'pn-body--root': depth === 0 }">
        <PermTreeNode
          v-for="child in node.children"
          :key="child.key"
          :node="child"
          :depth="depth + 1"
        />
      </div>
    </template>

    <!-- 叶子节点：单条权限项 -->
    <label v-else class="pn-leaf">
      <n-checkbox
        :checked="checked"
        @update:checked="(v: boolean) => toggleSelf(v)"
      />
      <span class="pn-leaf-name">{{ node.label }}</span>
      <span class="pn-leaf-tag" :class="node.leaf?.isMenu ? 'is-menu' : 'is-btn'">{{ tagText }}</span>
    </label>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, type Ref } from 'vue'
import { NCheckbox, NButton } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import {
  type PermNode,
  collectNodeCodes,
  collectGroupKeys,
  nodeAllChecked,
  nodeIndeterminate,
  nodeSelectedCount,
} from '@/utils/permissionModules'

const { t } = useI18n()

const props = defineProps<{
  node: PermNode
  depth: number
}>()

interface ExpandedApi {
  has: (key: string) => boolean
  toggle: (key: string) => void
  setAll: (keys: string[], on: boolean) => void
}

const selectedCodes = inject<Ref<string[]>>('permSelected')!
const permToggle = inject<(codes: string[], on: boolean) => void>('permToggle')!
const expandedApi = inject<ExpandedApi>('permExpanded')!

const selectedSet = computed(() => new Set(selectedCodes.value))

const totalCodes = computed(() => collectNodeCodes(props.node).length)
const selectedCount = computed(() => nodeSelectedCount(props.node, selectedSet.value))
const allChecked = computed(() => nodeAllChecked(props.node, selectedSet.value))
const indeterminate = computed(() => nodeIndeterminate(props.node, selectedSet.value))

function toggle(on: boolean): void {
  permToggle(collectNodeCodes(props.node), on)
}

// ===== 折叠 =====
const expanded = computed(() => expandedApi.has(props.node.key))
function toggleExpand(): void {
  expandedApi.toggle(props.node.key)
}
const descendantGroups = computed(() => collectGroupKeys(props.node, false).length)
const allExpanded = computed(() =>
  descendantGroups.value > 0 && collectGroupKeys(props.node, false).every((k) => expandedApi.has(k)),
)
function toggleExpandAll(on: boolean): void {
  expandedApi.setAll(collectGroupKeys(props.node, false), on)
}

// ===== 叶子 =====
const checked = computed(() =>
  props.node.leaf ? selectedSet.value.has(props.node.leaf.resourceCode) : false,
)
function toggleSelf(on: boolean): void {
  if (props.node.leaf) permToggle([props.node.leaf.resourceCode], on)
}

// 动作码 → 中文小标签（高频动作映射，未命中的回退原始码段，忠实于编码结构）
const ACTION_LABELS: Record<string, string> = {
  view: '查看',
  list: '列表',
  create: '新增',
  edit: '编辑',
  delete: '删除',
  export: '导出',
  approve: '审批',
  reject: '驳回',
  confirm: '确认',
  assign: '指派',
  evaluate: '评估',
  advance: '推进',
  schedule: '排期',
  feedback: '反馈',
  publish: '发布',
  close: '关闭',
  rotate: '轮岗',
}
const tagText = computed(() => {
  if (!props.node.leaf) return ''
  if (props.node.leaf.isMenu) return '菜单'
  return ACTION_LABELS[props.node.leaf.action] ?? props.node.leaf.action
})
</script>

<style scoped>
/* 模块卡（depth 0）：沿用原 .perm-group 的「面 + 线」双通道边界表达 */
.perm-node--root {
  background: var(--g1);
  border: 1px solid var(--g4);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4) var(--space-4);
  margin-bottom: var(--space-3);
  transition: border-color var(--dur-fast) var(--ease-out);
}
.perm-node--root:hover {
  border-color: var(--g5);
}
.pn-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}
.pn-head--root {
  margin-bottom: 8px;
}
.pn-caret {
  flex: 0 0 auto;
  width: 18px;
  height: 18px;
  border: none;
  background: transparent;
  color: var(--ink-faint);
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
  padding: 0;
  transition: transform var(--dur-fast) var(--ease-out);
}
.pn-caret--open {
  transform: rotate(90deg);
}
.pn-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  overflow-wrap: anywhere;
}
.pn-count {
  font-size: 12px;
  color: var(--ink-faint);
  font-variant-numeric: tabular-nums;
}
.pn-selected {
  font-size: 12px;
  color: var(--c-info-deep);
  font-variant-numeric: tabular-nums;
}
.pn-all {
  margin-left: auto;
}
.pn-expand {
  margin-left: auto;
  font-size: 12px;
}
.pn-expand + .pn-all {
  margin-left: var(--space-4);
}
.pn-body {
  padding-left: calc(var(--space-4) + 14px);
}
.pn-body--root {
  padding-left: 0;
}
/* 叶子：单条权限项 */
.pn-leaf {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 5px 0;
  cursor: pointer;
  min-width: 0;
}
.pn-leaf-name {
  font-size: 13px;
  color: var(--ink);
  overflow-wrap: anywhere;
}
.pn-leaf-tag {
  flex: 0 0 auto;
  font-size: 11px;
  line-height: 18px;
  padding: 0 6px;
  border-radius: 4px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.pn-leaf-tag.is-menu {
  color: var(--c-info-deep);
  background: color-mix(in srgb, var(--c-info-deep) 12%, transparent);
}
.pn-leaf-tag.is-btn {
  color: var(--ink-faint);
  background: var(--g3);
}
</style>
