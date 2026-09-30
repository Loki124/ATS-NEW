<template>
  <div class="page-container">
<div class="page-body">
    <div class="page-header">
      <h1 class="page-title">{{ t('pages.settings.CompanySettings.s1') }}</h1>
      <p class="page-subtitle">{{ t('pages.settings.CompanySettings.s2') }}</p>
    </div>

    <n-card :title="t('pages.settings.CompanySettings.s3')">
      <n-space vertical>
        <n-space>
          <n-button
            type="primary"
            :loading="loadingList"
            @click="loadSyncs"
          >
            {{ t('pages.settings.CompanySettings.s4') }}
          </n-button>
          <n-text depth="3">
            {{ t('pages.settings.CompanySettings.s5') }}
          </n-text>
        </n-space>

        <n-data-table
          :columns="columns"
          :data="syncs"
          :bordered="false"
          size="small"
          :pagination="localPagination()"
        />

        <n-divider />

        <n-text depth="3" style="font-size: 12px">
          {{ t('pages.settings.CompanySettings.s6') }}
        </n-text>
      </n-space>
    </n-card>
    </div><!-- /.page-body -->
</div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { localPagination } from '@/composables/useTablePagination'
import { h, onMounted, ref } from 'vue'
import { NButton, NSpace, NTag, useMessage, type DataTableColumns } from 'naive-ui'
import { fetchSyncs, retrySync, type CompanySync } from '../../api/external-sync'
const { t } = useI18n()

const message = useMessage()
const loadingList = ref(false)
const syncs = ref<CompanySync[]>([])

const columns: DataTableColumns<CompanySync> = [
  { title: t('pages.settings.CompanySettings.s7'), key: 'companyId', width: 100 },
  {
    title: t('pages.settings.CompanySettings.s8'),
    key: 'externalSystem',
    width: 100,
    render: (row) =>
      h(NTag, { type: row.externalSystem === 'MOKA' ? 'info' : 'success', size: 'small' }, { default: () => row.externalSystem }),
  },
  { title: t('pages.settings.CompanySettings.s9'), key: 'externalId', width: 140 },
  {
    title: t('pages.settings.CompanySettings.s10'),
    key: 'syncStatus',
    width: 100,
    render: (row) => {
      const type = row.syncStatus === 'SUCCESS' ? 'success'
        : row.syncStatus === 'FAILED' ? 'error'
        : 'default'
      return h(NTag, { type, size: 'small' }, { default: () => row.syncStatus })
    },
  },
  { title: t('pages.settings.CompanySettings.s11'), key: 'lastSyncAt', width: 180 },
  { title: t('pages.settings.CompanySettings.s12'), key: 'retryCount', width: 80 },
  { title: t('pages.settings.CompanySettings.s13'), key: 'lastError', ellipsis: { tooltip: true } },
  {
    title: t('pages.settings.CompanySettings.s14'),
    key: 'actions',
    width: 120,
    render: (row) =>
      h(
        NButton,
        {
          size: 'small',
          disabled: row.syncStatus !== 'FAILED',
          onClick: () => handleRetry(row.id),
        },
        { default: () => t('pages.settings.CompanySettings.s16') }
      ),
  },
]

async function loadSyncs() {
  loadingList.value = true
  try {
    syncs.value = await fetchSyncs()
  } catch (e: any) {
    message.error(t('pages.settings.CompanySettings.s17') + (e?.message || e))
  } finally {
    loadingList.value = false
  }
}

async function handleRetry(syncId: string) {
  try {
    await retrySync(syncId)
    message.success(t('pages.settings.CompanySettings.s15'))
    await loadSyncs()
  } catch (e: any) {
    message.error(t('pages.settings.CompanySettings.s18') + (e?.message || e))
  }
}

onMounted(() => {
  loadSyncs()
})
</script>

<style scoped>
/* === 2026-08-24 page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
   - 标题区固定（flex-shrink: 0）→ 配置/操作按钮始终可触达
   - 内容区自己滚（flex: 1; min-height: 0; overflow-y: auto）→ 与外层 .settings-scroll 滚职责分离
   - 结构上让 sticky header 天然占据物理空间 → 解决下方内容穿透 header 的视觉 bug === */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-header {
  flex-shrink: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}


/* 删除 scoped .page-header/.page-title 覆盖（规范：复用全局 glass.css） */
</style>
