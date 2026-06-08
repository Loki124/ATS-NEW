<script setup lang="ts">
/**
 * 简历筛选 - ScreeningList
 * PRD G13 批量筛选 + G9 批量操作
 *
 * 后端: /api/candidates (G9 批量) + /api/candidates/batch/screen (G13 筛选)
 */
import { ref, h, onMounted, computed } from 'vue'
import { NTag, NSpace, NButton, NIcon, useMessage, NDataTable, NCard, NSelect, useDialog } from 'naive-ui'
import { RefreshOutline, CheckmarkDoneOutline, DownloadOutline } from '@vicons/ionicons5'
import { listCandidates, batchScreen, batchExport, type Candidate } from '../../api/candidate'

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const candidates = ref<Candidate[]>([])
const selectedIds = ref<string[]>([])
const filterStatus = ref<string | null>(null)
const pagination = ref({ page: 1, pageSize: 20, itemCount: 0 })

const STATUS_LABEL: Record<string, string> = {
  ACTIVE: '活跃', ARCHIVED: '已归档', BLACKLIST: '黑名单', PENDING: '待审',
}
const STATUS_COLOR: Record<string, string> = {
  ACTIVE: 'success', ARCHIVED: 'default', BLACKLIST: 'error', PENDING: 'warning',
}
const statusOptions = [
  { value: 'ACTIVE', label: '活跃' },
  { value: 'ARCHIVED', label: '已归档' },
  { value: 'BLACKLIST', label: '黑名单' },
  { value: 'PENDING', label: '待审' },
]

const columns = computed<any[]>(() => [
  { type: 'selection', width: 50 },
  { title: '姓名', key: 'name', width: 100, render: (row: Candidate) => row.name || '—' },
  { title: '性别', key: 'gender', width: 60, render: (row: Candidate) => row.gender || '—' },
  { title: '年龄', key: 'age', width: 60, render: (row: Candidate) => row.age || '—' },
  { title: '学历', key: 'highestEducation', width: 100, render: (row: Candidate) => row.highestEducation || '—' },
  { title: '当前公司', key: 'currentCompany', width: 160, render: (row: Candidate) => row.currentCompany || '—' },
  { title: '当前职位', key: 'currentPosition', width: 140, render: (row: Candidate) => row.currentPosition || '—' },
  { title: '来源', key: 'source', width: 100, render: (row: Candidate) => row.source || '—' },
  {
    title: '状态', key: 'candidateStatus', width: 100,
    render: (row: Candidate) => h(NTag, { type: STATUS_COLOR[row.candidateStatus || 'ACTIVE'] as any, size: 'small' }, { default: () => STATUS_LABEL[row.candidateStatus || 'ACTIVE'] || row.candidateStatus }),
  },
  { title: '创建时间', key: 'createdAt', width: 160, render: (row: Candidate) => row.createdAt?.slice(0, 16) || '—' },
])

async function loadList() {
  loading.value = true
  try {
    const res = await listCandidates({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      ...(filterStatus.value && { candidateStatus: filterStatus.value }),
    })
    candidates.value = res.data.list
    pagination.value.itemCount = res.data.pagination.total
  } catch (e: any) {
    message.error(`加载失败: ${e.message}`)
  } finally {
    loading.value = false
  }
}

function handleBatchScreen(result: 'PASS' | 'FAIL') {
  if (selectedIds.value.length === 0) {
    message.warning('请先选择候选人')
    return
  }
  dialog.warning({
    title: `批量筛选 - ${result === 'PASS' ? '通过' : '未通过'}`,
    content: `确定将 ${selectedIds.value.length} 个候选人标记为「${result === 'PASS' ? '通过' : '未通过'}」?`,
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const res = await batchScreen({
          candidateIds: selectedIds.value,
          result,
          comment: `批量筛选 - ${result === 'PASS' ? '通过' : '未通过'}`,
        })
        message.success(`已筛选 ${res.data.affected} 条`)
        selectedIds.value = []
        loadList()
      } catch (e: any) {
        message.error(`筛选失败: ${e.message}`)
      }
    },
  })
}

async function handleExport() {
  try {
    const res = await batchExport({})
    // 触发 CSV 下载
    const blob = new Blob([res as any], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `candidates-${Date.now()}.csv`
    a.click()
    URL.revokeObjectURL(url)
    message.success('已导出')
  } catch (e: any) {
    message.error(`导出失败: ${e.message}`)
  }
}

const stats = computed(() => ({
  total: pagination.value.itemCount,
  active: candidates.value.filter((c) => c.candidateStatus === 'ACTIVE').length,
  selected: selectedIds.value.length,
}))

onMounted(loadList)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">简历筛选</h1>
      <n-space>
        <n-button @click="loadList" :loading="loading">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
        <n-button type="success" :disabled="selectedIds.length === 0" @click="handleBatchScreen('PASS')">
          <template #icon><n-icon :component="CheckmarkDoneOutline" /></template>
          批量通过 ({{ selectedIds.length }})
        </n-button>
        <n-button type="error" :disabled="selectedIds.length === 0" @click="handleBatchScreen('FAIL')">
          批量未通过
        </n-button>
        <n-button @click="handleExport">
          <template #icon><n-icon :component="DownloadOutline" /></template>
          导出 CSV
        </n-button>
      </n-space>
    </div>

    <n-grid x-gap="12" y-gap="12" cols="3" class="stats-row">
      <n-gi><n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">总候选人数</div>
        <div class="stat-value">{{ stats.total }}</div>
      </n-card></n-gi>
      <n-gi><n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">活跃</div>
        <div class="stat-value" style="color: #52c41a;">{{ stats.active }}</div>
      </n-card></n-gi>
      <n-gi><n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">已选择</div>
        <div class="stat-value" style="color: #fa8c16;">{{ stats.selected }}</div>
      </n-card></n-gi>
    </n-grid>

    <n-card :bordered="false" class="rounded-xl">
      <n-space class="filter-row">
        <n-select
          v-model:value="filterStatus"
          placeholder="候选人状态"
          style="width: 160px"
          clearable
          :options="statusOptions"
          @update:value="loadList"
        />
        <n-button @click="loadList">查询</n-button>
      </n-space>

      <n-data-table
        :columns="columns"
        :data="candidates"
        :loading="loading"
        :row-key="(row: Candidate) => row.id"
        :pagination="pagination"
        v-model:checked-row-keys="selectedIds"
        @update:page="(p: number) => { pagination.page = p; loadList() }"
      />
    </n-card>
  </div>
</template>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
.stats-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-label { font-size: 12px; color: #8c8c8c; }
.stat-value { font-size: 22px; font-weight: 600; margin-top: 4px; }
.filter-row { margin-bottom: 12px; }
</style>
