<template>
  <div class="rl-rule-table-wrap">
    <div class="toolbar">
      <n-space :wrap="false" align="center">
        <n-input
          v-model:value="search"
          :placeholder="t('reasonLibrary.rules.search.placeholder')"
          clearable
          style="width: 260px"
        >
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <n-select
          v-model:value="statusFilter"
          :options="statusOptions"
          :placeholder="t('reasonLibrary.rules.filter.allStatus')"
          style="width: 130px"
          clearable
        />
      </n-space>
      <n-button type="primary" @click="$emit('create')">
        <template #icon><n-icon :component="AddOutline" /></template>
        {{ t('reasonLibrary.rules.btn.create') }}
      </n-button>
    </div>

    <n-data-table
      :columns="columns"
      :data="filteredRows"
      :loading="loading"
      :row-key="(r: SceneRuleListItem) => r.id"
      :pagination="false"
      :scroll-x="1000"
      size="medium"
      striped
    >
      <template #empty>
        <n-empty :description="t('reasonLibrary.rules.empty')" />
      </template>
    </n-data-table>
  </div>
</template>

<script setup lang="ts">
/**
 * ReasonRuleTable (T-17)
 * - 5 列: 规则名 / 应用场景 / 原因数量 / 规则状态 / 操作
 * - 系统预置 badge + 应用场景 tag 展示
 * - 操作: 编辑 (打开 wizard) + 启停 (按 E-03 条件)
 */
import { ref, computed, h } from 'vue'
import { NButton, NTag, NSwitch, NSpace, NIcon, NDataTable, NInput, NSelect, NEmpty, NTooltip } from 'naive-ui'
import { SearchOutline, AddOutline, SettingsOutline, LockClosedOutline } from '@vicons/ionicons5'
import type { SceneRuleListItem } from '../../types/reason-library'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{
  rules: SceneRuleListItem[]
  loading?: boolean
  isSuperAdmin?: boolean
}>()

const emit = defineEmits<{
  (e: 'edit', rule: SceneRuleListItem): void
  (e: 'toggle', rule: SceneRuleListItem): void
  (e: 'remove', rule: SceneRuleListItem): void
  (e: 'create'): void
}>()

const search = ref('')
const statusFilter = ref<'on' | 'off' | null>(null)

const statusOptions = [
  { label: t('reasonLibrary.rules.filter.enabled'), value: 'on' },
  { label: t('reasonLibrary.rules.filter.disabled'), value: 'off' },
]

const filteredRows = computed<SceneRuleListItem[]>(() => {
  const q = search.value.trim().toLowerCase()
  return props.rules.filter((r) => {
    if (q && !r.name.toLowerCase().includes(q)) return false
    if (statusFilter.value === 'on' && !r.enabled) return false
    if (statusFilter.value === 'off' && r.enabled) return false
    return true
  })
})

const columns = computed(() => [
  {
    title: t('reasonLibrary.rules.col.name'),
    key: 'name',
    width: 240,
    ellipsis: { tooltip: true },
    render: (row: SceneRuleListItem) =>
      h('div', { class: 'rl-name-cell' }, [
        h('span', { class: 'rl-name-text' }, row.name),
        row.isPresetDefault
          ? h(NTag, { size: 'tiny', type: 'primary', bordered: false, style: 'margin-left: 8px;' },
              { default: () => t('reasonLibrary.rules.col.presetDefaultBadge') })
          : (row.isSystem
            ? h(NTag, { size: 'tiny', type: 'warning', bordered: false, style: 'margin-left: 8px;' },
                { default: () => t('reasonLibrary.rules.col.systemBadge') })
            : null),
      ]),
  },
  {
    title: t('reasonLibrary.rules.col.scenes'),
    key: 'scenes',
    width: 240,
    render: (row: SceneRuleListItem) => {
      if (row.isPresetDefault) {
        return h(NTag, { size: 'small', type: 'primary', bordered: false, class: 'rl-scene-tag' },
          { default: () => t('reasonLibrary.rules.col.presetDefaultScope') })
      }
      if (!row.scenes?.length) {
        return h('span', { class: 'rl-empty' }, t('reasonLibrary.rules.col.emptyScenes'))
      }
      return h(NSpace, { size: 4 }, () =>
        row.scenes.map((s) =>
          h(NTag, { size: 'small', type: 'info', bordered: false, class: 'rl-scene-tag' },
            { default: () => s }),
        ),
      )
    },
  },
  {
    title: t('reasonLibrary.rules.col.tagCount'),
    key: 'tagCount',
    width: 100,
    align: 'center' as const,
    render: (row: SceneRuleListItem) =>
      h('span', { class: 'rl-count' }, [
        String(row.tagCount),
        h('span', { class: 'rl-unit' }, ' 条'),
      ]),
  },
  {
    title: t('reasonLibrary.rules.col.status'),
    key: 'enabled',
    width: 100,
    render: (row: SceneRuleListItem) => {
      const sceneLocked = row.sceneCount > 0
      const systemLocked = row.isSystem && !props.isSuperAdmin
      const tip = sceneLocked
        ? t('reasonLibrary.rules.toggle.sceneLocked')
        : systemLocked
          ? t('reasonLibrary.rules.toggle.systemImmutable')
          : ''
      const sw = h(NSwitch, {
        value: row.enabled,
        size: 'small',
        disabled: sceneLocked || systemLocked,
        onUpdateValue: () => emit('toggle', row),
      })
      return tip ? h(NTooltip, null, { trigger: () => sw, default: () => tip }) : sw
    },
  },
  {
    title: t('reasonLibrary.rules.col.actions'),
    key: 'actions',
    width: 220,
    fixed: 'right' as const,
    render: (row: SceneRuleListItem) => {
      const editBtn = h(
        NButton,
        { size: 'small', quaternary: true, onClick: () => emit('edit', row) },
        {
          icon: () => h(NIcon, null, { default: () => h(row.isSystem ? LockClosedOutline : SettingsOutline) }),
          default: () => t('reasonLibrary.rules.edit'),
        },
      )
      const delBtn = h(
        NButton,
        { size: 'small', quaternary: true, type: 'error', disabled: row.isSystem && !props.isSuperAdmin, onClick: () => emit('remove', row) },
        { default: () => t('reasonLibrary.common.delete') },
      )
      return h(NSpace, { size: 4 }, () => [editBtn, delBtn])
    },
  },
])
</script>

<style scoped>
.rl-rule-table-wrap { display: flex; flex-direction: column; gap: var(--space-3); }
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}
.rl-name-cell { display: flex; align-items: center; min-width: 0; }
.rl-name-text {
  font-weight: 500; color: var(--ink);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px;
}
.rl-empty { color: var(--ink-faint); font-size: var(--fs-12); }
.rl-scene-tag { font-size: var(--fs-11); }
.rl-count { color: var(--brand); font-weight: 600; }
.rl-unit { color: var(--ink-soft); font-size: var(--fs-12); font-weight: 400; margin-left: 2px; }
</style>
