<script setup lang="ts">
import { ref, h, onMounted, computed } from 'vue'
import { NTag, NSpace, NButton, NIcon, useMessage } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import {
  listInterviews, submitFeedback, cancelInterview,
  INTERVIEW_STATUS_LABEL, FEEDBACK_STATUS_LABEL, FEEDBACK_STATUS_COLOR,
  type Interview,
} from '../../api/interview'

const message = useMessage()
const loading = ref(false)
const dataSource = ref<Interview[]>([])
const filterFeedback = ref<string | null>(null)
const pagination = ref({ page: 1, pageSize: 20, itemCount: 0, pageCount: 0 })

const stats = computed(() => {
  const counts = { PENDING: 0, COMPLETED: 0 }
  for (const it of dataSource.value) {
    if (it.feedbackStatus === 'PENDING') counts.PENDING++
    else counts.COMPLETED++
  }
  return counts
})

const columns = computed(() => [
  { title: '轮次', key: 'roundName', width: 100, render: (row: Interview) => row.roundName || '—' },
  { title: '类型', key: 'interviewType', width: 100, render: (row: Interview) => row.interviewType },
  { title: '时间', key: 'interviewDate', width: 160, render: (row: Interview) => row.interviewDate?.slice(0, 16) },
  { title: '时长', key: 'duration', width: 80, render: (row: Interview) => `${row.duration || 60} 分钟` },
  { title: '面试官', key: 'interviewerNames', width: 160, render: (row: Interview) => row.interviewerNames || '—' },
  { title: '地点', key: 'location', width: 140, render: (row: Interview) => row.location || row.meetingLink || '—' },
  {
    title: '状态', key: 'interviewStatus', width: 100,
    render: (row: Interview) => h(NTag, { type: 'info', size: 'small' }, { default: () => INTERVIEW_STATUS_LABEL[row.interviewStatus] || row.interviewStatus }),
  },
  {
    title: '反馈', key: 'feedbackStatus', width: 100,
    render: (row: Interview) => h(NTag, { type: FEEDBACK_STATUS_COLOR[row.feedbackStatus] as any, size: 'small' }, { default: () => FEEDBACK_STATUS_LABEL[row.feedbackStatus] || row.feedbackStatus }),
  },
  {
    title: '操作', key: 'actions', width: 200, fixed: 'right' as const,
    render: (row: Interview) => {
      const buttons: any[] = []
      if (row.feedbackStatus === 'PENDING' && row.interviewStatus !== 'CANCELLED') {
        buttons.push(h(NButton, { size: 'tiny', type: 'primary', onClick: () => quickFeedback(row, 'PASS') }, { default: () => '反馈·通过' }))
        buttons.push(h(NButton, { size: 'tiny', type: 'error', onClick: () => quickFeedback(row, 'FAIL') }, { default: () => '反馈·未通过' }))
      }
      if (row.interviewStatus !== 'CANCELLED' && row.interviewStatus !== 'COMPLETED') {
        buttons.push(h(NButton, { size: 'tiny', quaternary: true, onClick: () => handleCancel(row) }, { default: () => '取消' }))
      }
      return buttons.length ? h(NSpace, { size: 4 }, { default: () => buttons }) : '—'
    },
  },
])

async function loadList() {
  loading.value = true
  try {
    const res = await listInterviews({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      ...(filterFeedback.value && { feedbackStatus: filterFeedback.value }),
    })
    dataSource.value = res.data.list
    pagination.value.itemCount = res.data.pagination.total
    pagination.value.pageCount = res.data.pagination.totalPages
  } catch (e: any) {
    message.error(`加载失败: ${e.message}`)
  } finally {
    loading.value = false
  }
}

async function quickFeedback(row: Interview, result: 'PASS' | 'FAIL') {
  try {
    await submitFeedback(row.id, { result, reason: result === 'PASS' ? '面试通过' : '面试未通过' })
    message.success(`已记录反馈: ${result}`)
    loadList()
  } catch (e: any) {
    message.error(`反馈失败: ${e.message}`)
  }
}

async function handleCancel(row: Interview) {
  try {
    await cancelInterview(row.id, 'HR 取消面试')
    message.success('已取消面试')
    loadList()
  } catch (e: any) {
    message.error(`取消失败: ${e.message}`)
  }
}

onMounted(loadList)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">面试管理</h1>
      <n-space>
        <n-button @click="loadList" :loading="loading">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
      </n-space>
    </div>

    <n-grid x-gap="12" y-gap="12" cols="3" class="stats-row">
      <n-gi><n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">待反馈</div>
        <div class="stat-value" style="color: #fa8c16;">{{ stats.PENDING }}</div>
      </n-card></n-gi>
      <n-gi><n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">已反馈</div>
        <div class="stat-value" style="color: #52c41a;">{{ stats.COMPLETED }}</div>
      </n-card></n-gi>
      <n-gi><n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">总面试数</div>
        <div class="stat-value">{{ dataSource.length }}</div>
      </n-card></n-gi>
    </n-grid>

    <n-card :bordered="false" class="rounded-xl">
      <n-space class="filter-row">
        <n-select
          v-model:value="filterFeedback"
          placeholder="反馈状态"
          style="width: 140px"
          clearable
          :options="[{value:'PENDING',label:'待反馈'},{value:'COMPLETED',label:'已反馈'}]"
          @update:value="loadList"
        />
      </n-space>
      <n-data-table
        :columns="columns"
        :data="dataSource"
        :loading="loading"
        :row-key="(row: Interview) => row.id"
        :pagination="pagination"
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
