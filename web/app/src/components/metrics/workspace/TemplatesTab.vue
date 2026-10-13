<template>
  <div>
    <div class="ws-tab-header">
      <div class="ws-tab-bar">
        <div class="ws-toolbar ws-toolbar-grow">
          <n-input
            v-model:value="tplKeyword"
            :placeholder="t('metrics.filter.keywordPlaceholder')"
            clearable
            class="ws-search"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
          <n-select
            v-model:value="tplStatus"
            :placeholder="t('metrics.filter.status')"
            :options="tplStatusOptions"
            class="ws-filter"
          />
        </div>
        <div class="ws-io-bar">
          <n-button tertiary size="small" :loading="exporting" @click="onExportTemplates">
            {{ t('metrics.templateIo.export') }}
          </n-button>
          <n-button tertiary size="small" @click="openImportModal">
            {{ t('metrics.templateIo.import') }}
          </n-button>
          <n-button type="primary" size="small" @click="openTemplateCreate">
            {{ t('metrics.btn.create') }}{{ t('metrics.tab.template') }}
          </n-button>
        </div>
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
        <div v-else-if="!loading && !templateList.length" class="ws-empty">
          <n-empty :description="t('metrics.empty.noTemplates')" />
        </div>
        <div v-else-if="!filteredTemplates.length" class="ws-empty">
          <n-empty :description="t('metrics.empty.templatesFiltered')" />
          <n-button size="small" tertiary class="ws-empty-action" @click="clearTplFilters">
            {{ t('metrics.empty.clearFilters') }}
          </n-button>
        </div>
        <n-data-table
          v-else
          :columns="tplColumns"
          :data="pagedTemplates"
          :row-props="tplRowProps"
          :scroll-x="900"
          :max-height="tableMaxHeight"
          size="small"
          class="ws-table"
        />
      </n-spin>
      <div v-if="filteredTemplates.length > 0" class="ws-pager">
        <n-pagination
          :page="tplPage"
          :page-size="tplPageSize"
          :item-count="filteredTemplates.length"
          :page-sizes="[10, 20, 50, 100]"
          show-size-picker
          show-quick-jumper
          @update:page="(p: number) => (tplPage = p)"
          @update:page-size="(s: number) => { tplPageSize = s; tplPage = 1 }"
        >
          <template #prefix>
            <span class="ws-pager-count">{{ t('metrics.filter.resultCount', { count: filteredTemplates.length }) }}</span>
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
  tplKeyword,
  tplStatus,
  tplStatusOptions,
  exporting,
  onExportTemplates,
  openImportModal,
  openTemplateCreate,
  loading,
  loadError,
  load,
  clearTplFilters,
  templateList,
  filteredTemplates,
  pagedTemplates,
  tplColumns,
  tplRowProps,
  tableMaxHeight,
  tplPage,
  tplPageSize,
} = ws
</script>
