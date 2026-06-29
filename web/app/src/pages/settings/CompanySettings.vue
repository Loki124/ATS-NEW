<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">公司设置</h1>
    </div>

    <n-card title="法人公司 - 外部同步 (G40)">
      <n-space vertical>
        <n-space>
          <n-button
            type="primary"
            :loading="loadingList"
            @click="loadSyncs"
          >
            刷新同步状态
          </n-button>
          <n-text depth="3">
            法人公司可同步到 摩卡 People / 邮箱 (企业 API 待授权, 当前为 Mock)
          </n-text>
        </n-space>

        <n-data-table
          :columns="columns"
          :data="syncs"
          :bordered="false"
          size="small"
          :pagination="{ pageSize: 20 }"
        />

        <n-divider />

        <n-text depth="3" style="font-size: 12px">
          真实同步按钮需要在公司列表中触发 (管理公司 CRUD API 待开发, 占位中)
        </n-text>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { NButton, NSpace, NTag, useMessage, type DataTableColumns } from 'naive-ui'
import { fetchSyncs, retrySync, type CompanySync } from '../../api/external-sync'

const message = useMessage()
const loadingList = ref(false)
const syncs = ref<CompanySync[]>([])

const columns: DataTableColumns<CompanySync> = [
  { title: '公司ID', key: 'companyId', width: 100 },
  {
    title: '外部系统',
    key: 'externalSystem',
    width: 100,
    render: (row) =>
      h(NTag, { type: row.externalSystem === 'MOKA' ? 'info' : 'success', size: 'small' }, { default: () => row.externalSystem }),
  },
  { title: '外部ID', key: 'externalId', width: 140 },
  {
    title: '状态',
    key: 'syncStatus',
    width: 100,
    render: (row) => {
      const type = row.syncStatus === 'SUCCESS' ? 'success'
        : row.syncStatus === 'FAILED' ? 'error'
        : 'default'
      return h(NTag, { type, size: 'small' }, { default: () => row.syncStatus })
    },
  },
  { title: '上次同步', key: 'lastSyncAt', width: 180 },
  { title: '重试次数', key: 'retryCount', width: 80 },
  { title: '错误', key: 'lastError', ellipsis: { tooltip: true } },
  {
    title: '操作',
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
        { default: () => '重试' }
      ),
  },
]

async function loadSyncs() {
  loadingList.value = true
  try {
    syncs.value = await fetchSyncs()
  } catch (e: any) {
    message.error('加载同步状态失败: ' + (e?.message || e))
  } finally {
    loadingList.value = false
  }
}

async function handleRetry(syncId: string) {
  try {
    await retrySync(syncId)
    message.success('重试已触发')
    await loadSyncs()
  } catch (e: any) {
    message.error('重试失败: ' + (e?.message || e))
  }
}

onMounted(() => {
  loadSyncs()
})
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
