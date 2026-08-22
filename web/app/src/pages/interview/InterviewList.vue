<script setup lang="ts">
import { ref, h, onMounted, computed } from 'vue'
import { NTag, NSpace, NButton, NIcon, NDropdown, useMessage } from 'naive-ui'
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
  for (const it of (dataSource.value ?? [])) {
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
    render: (row: Interview) => h(NTag, { type: FEEDBACK_STATUS_COLOR[row.feedbackStatus], size: 'small' }, { default: () => FEEDBACK_STATUS_LABEL[row.feedbackStatus] || row.feedbackStatus }),
  },
  {
    title: '操作', key: 'actions', width: 140, fixed: 'right' as const,
    render: (row: Interview) => {
      // v2: 主按钮（反馈·通过 / 取消） + 下拉其他
      const items: Array<{ label: string; key: string; danger?: boolean; onClick: () => void }> = []
      let primary: { label: string; type: 'primary' | 'error' | 'default'; onClick: () => void } | null = null
      if (row.feedbackStatus === 'PENDING' && row.interviewStatus !== 'CANCELLED') {
        primary = { label: '反馈·通过', type: 'primary', onClick: () => quickFeedback(row, 'PASS') }
        items.push({ label: '反馈·未通过', key: 'fail', danger: true, onClick: () => quickFeedback(row, 'FAIL') })
      }
      if (row.interviewStatus !== 'CANCELLED' && row.interviewStatus !== 'COMPLETED') {
        if (!primary) primary = { label: '取消', type: 'error', onClick: () => handleCancel(row) }
        else items.push({ label: '取消', key: 'cancel', danger: true, onClick: () => handleCancel(row) })
      }
      if (!primary) return '—'
      return h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'tiny', type: primary.type, onClick: primary.onClick }, { default: () => primary!.label }),
          items.length
            ? h(NDropdown, {
                options: items.map(it => ({
                  label: it.label,
                  key: it.key,
                  ...(it.danger ? { props: { style: 'color: var(--c-error)' } } : {}),
                })),
                trigger: 'click',
                onSelect: (k: string) => items.find(it => it.key === k)?.onClick(),
              }, {
                default: () => h(NButton, { size: 'tiny', quaternary: true }, { default: () => '更多 ⌄' }),
              })
            : null,
        ].filter(Boolean),
      })
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
    dataSource.value = res.data ?? []
    pagination.value.itemCount = res.pagination?.total ?? 0
    pagination.value.pageCount = res.pagination?.totalPages ?? 0
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
        <n-button :loading="loading" @click="loadList">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
      </n-space>
    </div>

    <n-grid x-gap="12" y-gap="12" cols="3" class="stats-row">
      <n-gi>
<n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">待反馈</div>
        <div class="stat-value" style="color: var(--c-warning);">{{ stats.PENDING }}</div>
      </n-card>
</n-gi>
      <n-gi>
<n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">已反馈</div>
        <div class="stat-value" style="color: var(--c-success);">{{ stats.COMPLETED }}</div>
      </n-card>
</n-gi>
      <n-gi>
<n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">总面试数</div>
        <div class="stat-value">{{ dataSource.length }}</div>
      </n-card>
</n-gi>
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
.stat-label { font-size: var(--text-meta); color: var(--ink-faint); }
.stat-value { font-size: 22px; font-weight: 600; margin-top: 4px; }
.filter-row { margin-bottom: 12px; }

/* === v2 响应式补丁 === */
@media (max-width: 1280px) {
  .page-container { padding: var(--space-4); }
  .page-title { font-size: var(--text-h2); }
  :deep(.n-data-table-wrapper) {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
}
@media (max-width: 768px) {
  .page-container { padding: var(--space-3); }
  .page-header { flex-direction: column; align-items: stretch; gap: var(--space-3); }
  .stats-row { grid-template-columns: repeat(2, 1fr) !important; }
}
@media (max-width: 480px) {
  .stats-row { grid-template-columns: 1fr !important; }
}

</style>
