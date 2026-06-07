<script setup lang="ts">
/**
 * 阶段配置 - StageConfig
 * G38 系统管理 - 全局阶段模板 (与流程解耦的 stage 库)
 *
 * 后端: /api/recruitment-stages
 */
import { ref, h, onMounted, computed } from 'vue'
import { NTag, NSpace, NButton, NIcon, useMessage, NDataTable, NCard, NInput } from 'naive-ui'
import { GitNetworkOutline, AddOutline, RefreshOutline, CopyOutline } from '@vicons/ionicons5'
import api from '../../api/auth'

const message = useMessage()
const loading = ref(false)
const stages = ref<any[]>([])
const filter = ref('')

const columns = computed(() => [
  { title: '编码', key: 'code', width: 100 },
  { title: '阶段名', key: 'name', width: 160 },
  {
    title: '类型', key: 'stageType', width: 120,
    render: (row: any) => {
      const colors: any = { FILTER: 'warning', INTERVIEW: 'primary', OFFER: 'success', ONBOARDING: 'info', GENERAL: 'default' }
      return h(NTag, { type: colors[row.stageType] || 'default', size: 'small' }, { default: () => row.stageType || 'GENERAL' })
    },
  },
  { title: '功能', key: 'features', ellipsis: { tooltip: true }, render: (row: any) => (row.features || []).join(', ') || '—' },
  {
    title: '系统预置', key: 'isSystem', width: 100,
    render: (row: any) => row.isSystem ? h(NTag, { type: 'warning', size: 'small' }, { default: () => '是' }) : '—',
  },
  {
    title: '状态', key: 'status', width: 100,
    render: (row: any) => h(NTag, { type: row.status === 'ACTIVE' ? 'success' : 'default', size: 'small' }, { default: () => row.status || 'ACTIVE' }),
  },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '操作', key: 'actions', width: 160, fixed: 'right' as const,
    render: (row: any) => h(NSpace, { size: 4 }, {
      default: () => [
        h(NButton, { size: 'tiny', quaternary: true, onClick: () => handleCopy(row) }, {
          default: () => '复制',
        }),
        !row.isSystem && h(NButton, { size: 'tiny', type: 'error', quaternary: true, onClick: () => handleDelete(row) }, {
          default: () => '删除',
        }),
      ].filter(Boolean),
    }),
  },
])

async function loadStages() {
  loading.value = true
  try {
    const { data } = await api.get('/recruitment-stages')
    if (data.success) stages.value = data.data
  } catch (e: any) {
    message.error(`加载阶段失败: ${e.message}`)
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  message.info('阶段创建：完整 CRUD界面在下个迭代实现')
}

function handleCopy(row: any) {
  try {
    api.post(`/recruitment-stages/${row.id}/copy`)
    message.success('已复制')
    loadStages()
  } catch (e: any) {
    message.error(`复制失败: ${e.message}`)
  }
}

function handleDelete(row: any) {
  message.warning(`阶段「${row.name}」删除需在下个迭代确认 (含关联检查)`)
}

const filteredStages = computed(() => {
  if (!filter.value) return stages.value
  return stages.value.filter((s) => s.name?.includes(filter.value) || s.code?.includes(filter.value))
})

const stats = computed(() => ({
  total: stages.value.length,
  system: stages.value.filter((s) => s.isSystem).length,
  active: stages.value.filter((s) => s.status === 'ACTIVE').length,
}))

onMounted(loadStages)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">阶段配置</h1>
      <n-space>
        <n-button @click="loadStages" :loading="loading">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
        <n-button type="primary" @click="handleAdd">
          <template #icon><n-icon :component="AddOutline" /></template>
          新建阶段
        </n-button>
      </n-space>
    </div>

    <n-grid x-gap="12" y-gap="12" cols="3" responsive="screen" :item-responsive="true" class="stats-row">
      <n-gi><n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">总阶段数</div>
        <div class="stat-value">{{ stats.total }}</div>
      </n-card></n-gi>
      <n-gi><n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">系统预置</div>
        <div class="stat-value" style="color: #fa8c16;">{{ stats.system }}</div>
      </n-card></n-gi>
      <n-gi><n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">启用中</div>
        <div class="stat-value" style="color: #52c41a;">{{ stats.active }}</div>
      </n-card></n-gi>
    </n-grid>

    <n-card :bordered="false" class="rounded-xl">
      <n-space class="filter-row">
        <n-input
          v-model:value="filter"
          placeholder="搜索阶段名或编码"
          style="width: 240px"
          clearable
        >
          <template #prefix><n-icon :component="GitNetworkOutline" /></template>
        </n-input>
        <n-button @click="loadStages">查询</n-button>
      </n-space>

      <n-data-table
        :columns="columns"
        :data="filteredStages"
        :loading="loading"
        :row-key="(row: any) => row.id"
        :pagination="{ pageSize: 20 }"
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
