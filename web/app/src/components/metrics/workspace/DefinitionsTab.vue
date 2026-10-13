<template>
  <div>
    <div class="ws-tab-header">
      <div class="ws-toolbar">
        <n-input
          v-model:value="defKeyword"
          :placeholder="t('metrics.filter.keywordPlaceholder')"
          clearable
          class="ws-search"
        >
          <template #prefix>
            <n-icon :component="SearchOutline" />
          </template>
        </n-input>
        <n-select
          v-model:value="defKind"
          :placeholder="t('metrics.filter.kind')"
          :options="defKindOptions"
          class="ws-filter"
        />
        <n-select
          v-model:value="defModule"
          :placeholder="t('metrics.filter.sourceModule')"
          :options="defModuleOptions"
          class="ws-filter"
        />
      </div>
    </div>

    <div class="ws-table-wrap">
      <n-spin :show="loading" class="ws-spin">
        <div v-if="loadError" class="ws-empty">
          <n-result status="error" :title="t('metrics.empty.loadErrorTitle')" :description="t('metrics.empty.loadErrorDesc')">
            <template #footer>
              <n-button tertiary size="small" @click="load">{{ t('metrics.empty.reload') }}</n-button>
            </template>
          </n-result>
        </div>
        <div v-else-if="!filteredDefinitions.length" class="ws-empty">
          <n-empty
            v-if="defEmptyKind === 'first'"
            :description="t('metrics.empty.definitionsFirst')"
          />
          <template v-else>
            <n-empty :description="t('metrics.empty.definitionsFiltered')" />
            <n-button size="small" tertiary class="ws-empty-action" @click="clearDefFilters">
              {{ t('metrics.empty.clearFilters') }}
            </n-button>
          </template>
        </div>
        <n-data-table
          v-else
          :columns="defColumns"
          :data="pagedDefinitions"
          :row-props="defRowProps"
          :scroll-x="920"
          :max-height="tableMaxHeight"
          size="small"
          class="ws-table"
        />
      </n-spin>
      <div v-if="filteredDefinitions.length > 0" class="ws-pager">
        <n-pagination
          :page="defPage"
          :page-size="defPageSize"
          :item-count="filteredDefinitions.length"
          :page-sizes="[10, 20, 50, 100]"
          show-size-picker
          show-quick-jumper
          @update:page="(p: number) => (defPage = p)"
          @update:page-size="(s: number) => { defPageSize = s; defPage = 1 }"
        >
          <template #prefix>
            <span class="ws-pager-count">{{ t('metrics.filter.resultCount', { count: filteredDefinitions.length }) }}</span>
          </template>
        </n-pagination>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import { SearchOutline } from '@vicons/ionicons5'
import { METRICS_WORKSPACE_KEY } from '@/composables/useMetricsWorkspace'

const ws = inject(METRICS_WORKSPACE_KEY)!
const {
  t,
  defKeyword,
  defKind,
  defKindOptions,
  defModule,
  defModuleOptions,
  loading,
  loadError,
  load,
  clearDefFilters,
  defEmptyKind,
  filteredDefinitions,
  pagedDefinitions,
  defColumns,
  defRowProps,
  tableMaxHeight,
  defPage,
  defPageSize,
} = ws
</script>
