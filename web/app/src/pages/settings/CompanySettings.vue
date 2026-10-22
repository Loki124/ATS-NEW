<template>
  <div class="page-container">
    <!-- 遵循「数据列表模板 · 独立设置页列表（乙系）」：page-header 与 page-body 是兄弟节点，
         操作控件一律移入面板内 .toolbar（不在页头堆按钮） -->
    <div class="page-header">
      <h1 class="page-title">{{ t('pages.settings.CompanySettings.s1') }}</h1>
      <p class="page-subtitle">{{ t('pages.settings.CompanySettings.s2') }}</p>
    </div>

    <div class="data-body">
      <div class="glass-panel panel-shell">
        <div class="toolbar">
          <!-- 说明文字属列表语义 → 用全局 .field-hint，禁私建 tip 类名（8px 间距 + 语义色令牌） -->
          <p class="field-hint toolbar-hint">{{ t('pages.settings.CompanySettings.s5') }}</p>
          <div class="spacer"></div>
          <n-button type="primary" class="gradient-btn" :loading="loadingList" @click="loadSyncs">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            {{ t('pages.settings.CompanySettings.s4') }}
          </n-button>
        </div>

        <div class="table-wrap">
          <n-data-table
            :columns="columns"
            :data="syncs"
            :bordered="false"
            :loading="loadingList"
            :row-key="(row: CompanySync) => row.id"
            :pagination="localPagination()"
            flex-height
          >
            <!-- 空态双态：区分「尚未同步过」与「筛选无匹配」 -->
            <template #empty>
              <n-empty
                :description="syncs.length === 0
                  ? t('pages.settings.CompanySettings.s19')
                  : t('pages.settings.CompanySettings.s20')"
              />
            </template>
          </n-data-table>
        </div>
      </div>

      <p class="field-hint sync-note">{{ t('pages.settings.CompanySettings.s6') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { localPagination } from '@/composables/useTablePagination'
import { h, onMounted, ref } from 'vue'
import { NButton, NSpace, NTag, NIcon, NEmpty, useMessage, type DataTableColumns } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { fetchSyncs, retrySync, type CompanySync } from '../../api/external-sync'
import { column, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns'
const { t } = useI18n()

const message = useMessage()
const loadingList = ref(false)
const syncs = ref<CompanySync[]>([])

const columns: DataTableColumns<CompanySync> = [
  column({ title: t('pages.settings.CompanySettings.s7'), key: 'companyId', width: 100 }, 'short'),
  column({
    title: t('pages.settings.CompanySettings.s8'),
    key: 'externalSystem',
    width: 100,
    render: (row) =>
      h(NTag, { type: row.externalSystem === 'MOKA' ? 'info' : 'success', size: 'small' }, { default: () => row.externalSystem }),
  }, 'short'),
  column({ title: t('pages.settings.CompanySettings.s9'), key: 'externalId', width: 140 }, 'short'),
  column({
    title: t('pages.settings.CompanySettings.s10'),
    key: 'syncStatus',
    width: 100,
    render: (row) => {
      const type = row.syncStatus === 'SUCCESS' ? 'success'
        : row.syncStatus === 'FAILED' ? 'error'
        : 'default'
      return h(NTag, { type, size: 'small' }, { default: () => row.syncStatus })
    },
  }, 'short'),
  column({ title: t('pages.settings.CompanySettings.s11'), key: 'lastSyncAt', width: 180 }, 'short'),
  column({ title: t('pages.settings.CompanySettings.s12'), key: 'retryCount', width: 80 }, 'numeric'),
  column({ title: t('pages.settings.CompanySettings.s13'), key: 'lastError', ellipsis: { tooltip: true } }, 'text'),
  column({
    title: t('pages.settings.CompanySettings.s14'),
    key: 'actions',
    width: 120,
    fixed: 'right' as const,
    render: (row) =>
      h(NSpace, { size: 8, wrap: false }, () => [
        h(NButton, {
          size: OP_ACTION_BUTTON_SIZE,
          quaternary: true,
          type: 'primary',
          disabled: row.syncStatus !== 'FAILED',
          onClick: () => handleRetry(row.id),
        }, { icon: () => h(NIcon, null, { default: () => h(RefreshOutline) }), default: () => t('pages.settings.CompanySettings.s16') }),
      ]),
  }, 'control'),
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
/* 全局 glass.css 已提供 .page-container / .page-header / .page-title / .page-subtitle /
   .panel-shell / .toolbar / .table-wrap，本页不再私有重写（SETTINGS_PAGE_STRUCTURE.md §0）。
   仅保留两处页面专属微调：
   1. 工具条内的说明文字：需吃掉 n-form-item 式外边距并顶对齐，不撑高工具条 */
.toolbar-hint {
  margin: 0;
  align-self: center;
}
/* 列表下方的补充说明：与上方面板留 8px（--space-2），由 .page-body 的 gap 统一管控 */
.sync-note {
  margin: 0;
}

/* 2026-10-21 (整改卡 E6 · R-215): 滚动容器由 .page-body 迁到 .data-body ——
   数据列表页用区域滚动：外层不滚（overflow:hidden），真实滚动只在 .table-wrap 内的
   表格体（flex-height），标题/工具条/分页器固定。原依赖 SettingsLayout 对
   .page-body 的 overflow-y:auto 强制滚动，与表格体自滚形成双滚动条。 */
.data-body {
  flex: 1;
  min-height: 0;
  overflow-y: hidden;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
</style>
