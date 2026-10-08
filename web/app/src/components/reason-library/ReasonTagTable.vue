<template>
  <div class="rl-tag-table-wrap">
    <div class="toolbar">
      <n-space :wrap="false" align="center">
        <n-input
          v-model:value="search"
          :placeholder="t('reasonLibrary.tags.search.placeholder')"
          clearable
          style="width: 280px"
        >
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <n-select
          v-model:value="typeFilter"
          :options="typeOptions"
          :placeholder="t('reasonLibrary.tags.filter.allType')"
          style="width: 130px"
          clearable
        />
        <n-select
          v-model:value="statusFilter"
          :options="statusOptions"
          :placeholder="t('reasonLibrary.tags.filter.allStatus')"
          style="width: 130px"
          clearable
        />
      </n-space>
      <n-button type="primary" @click="$emit('create')">
        <template #icon><n-icon :component="AddOutline" /></template>
        {{ t('reasonLibrary.tags.btn.add') }}
      </n-button>
    </div>

    <n-data-table
      :columns="columns"
      :data="filteredRows"
      :loading="loading"
      :row-key="(r: ReasonTag) => r.id"
      :pagination="false"
      :scroll-x="1000"
      size="medium"
      striped
    >
      <template #empty>
        <n-empty :description="t('reasonLibrary.tags.empty')" />
      </template>
    </n-data-table>
  </div>
</template>

<script setup lang="ts">
/**
 * ReasonTagTable (T-16)
 *
 * 纯展示型表格组件 (无业务逻辑):
 * - 6 列: 名称/英文名/提示/类型/状态/操作
 * - 系统标签 (type='system') 的 edit/toggle 按钮 disabled + tooltip
 * - v-model:loading / v-model:search / v-model:tags / v-model:stats
 *
 * 父组件 (tags.vue) 负责 API 调用, 本组件只负责渲染 + 过滤 + 事件 emit。
 */
import { ref, computed, h, watch } from 'vue'
import { NButton, NTag, NSwitch, NTooltip, NSpace, NIcon, NDataTable, NInput, NSelect, NEmpty } from 'naive-ui'
import { SearchOutline, AddOutline, PencilOutline, LockClosedOutline } from '@vicons/ionicons5'
import type { ReasonTag } from '../../types/reason-library'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{
  tags: ReasonTag[]
  loading?: boolean
  isSuperAdmin?: boolean
}>()

const emit = defineEmits<{
  (e: 'edit', tag: ReasonTag): void
  (e: 'toggle', tag: ReasonTag): void
  (e: 'create'): void
}>()

const search = ref('')
const typeFilter = ref<'system' | 'custom' | null>(null)
const statusFilter = ref<'on' | 'off' | null>(null)

const typeOptions = [
  { label: t('reasonLibrary.tags.filter.system'), value: 'system' },
  { label: t('reasonLibrary.tags.filter.custom'), value: 'custom' },
]
const statusOptions = [
  { label: t('reasonLibrary.tags.filter.enabled'), value: 'on' },
  { label: t('reasonLibrary.tags.filter.disabled'), value: 'off' },
]

const filteredRows = computed<ReasonTag[]>(() => {
  const q = search.value.trim().toLowerCase()
  return props.tags.filter((r) => {
    if (q && !r.name.toLowerCase().includes(q) && !(r.enName || '').toLowerCase().includes(q)) return false
    if (typeFilter.value && r.type !== typeFilter.value) return false
    if (statusFilter.value === 'on' && !r.enabled) return false
    if (statusFilter.value === 'off' && r.enabled) return false
    return true
  })
})

const columns = computed(() => [
  { title: t('reasonLibrary.tags.col.name'), key: 'name', width: 180, ellipsis: { tooltip: true } },
  {
    title: t('reasonLibrary.tags.col.enName'),
    key: 'enName',
    width: 160,
    ellipsis: { tooltip: true },
    render: (row: ReasonTag) =>
      row.enName
        ? h('span', { style: 'color: var(--ink-soft);' }, row.enName)
        : h('span', { style: 'color: var(--ink-faint);' }, '—'),
  },
  {
    title: t('reasonLibrary.tags.col.tip'),
    key: 'tip',
    width: 200,
    ellipsis: { tooltip: true },
    render: (row: ReasonTag) =>
      row.tip
        ? h('span', { style: 'color: var(--ink-soft);' }, row.tip)
        : h('span', { style: 'color: var(--ink-faint);' }, '—'),
  },
  {
    title: t('reasonLibrary.tags.col.type'),
    key: 'type',
    width: 100,
    render: (row: ReasonTag) =>
      h(NTag, { size: 'small', type: row.type === 'system' ? 'info' : 'success', bordered: false },
        { default: () => (row.type === 'system' ? t('reasonLibrary.common.system') : t('reasonLibrary.common.custom')) }),
  },
  {
    title: t('reasonLibrary.tags.col.status'),
    key: 'enabled',
    width: 90,
    render: (row: ReasonTag) =>
      h(NSwitch, {
        value: row.enabled,
        size: 'small',
        disabled: row.type === 'system' && !props.isSuperAdmin,
        onUpdateValue: () => emit('toggle', row),
      }),
  },
  {
    title: t('reasonLibrary.tags.col.actions'),
    key: 'actions',
    width: 170,
    fixed: 'right' as const,
    render: (row: ReasonTag) => {
      const isLocked = row.type === 'system' && !props.isSuperAdmin
      const editBtn = h(
        NButton,
        { size: 'small', quaternary: true, disabled: isLocked, onClick: () => emit('edit', row) },
        {
          icon: () => h(NIcon, null, { default: () => h(isLocked ? LockClosedOutline : PencilOutline) }),
          default: () => t('reasonLibrary.common.edit'),
        },
      )
      const wrapped = isLocked
        ? h(NTooltip, null, { trigger: () => editBtn, default: () => t('reasonLibrary.common.systemImmutable') })
        : editBtn
      return h(NSpace, { size: 4 }, () => [wrapped])
    },
  },
])

// 标签变化时清掉过滤器
watch(() => props.tags.length, () => {
  search.value = ''
})
</script>

<style scoped>
.rl-tag-table-wrap { display: flex; flex-direction: column; gap: var(--space-3); }
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}
</style>
