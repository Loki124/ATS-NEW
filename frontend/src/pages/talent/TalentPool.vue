<script setup lang="ts">
/**
 * TalentPool.vue - PRD G32
 * 6 子库 (PASSIVE/ACTIVE/HIRED/REJECTED/BLACKLIST/GENERAL) + 跨池移动
 */
import { ref, h, onMounted, computed } from 'vue'
import {
  NTag, NCard, NSpace, NButton, NIcon, NTabs, NTabPane,
  NDataTable, NEmpty, NSelect, NModal, useMessage,
} from 'naive-ui'
import { RefreshOutline, AddOutline, ArrowForwardOutline } from '@vicons/ionicons5'
import axios from 'axios'
import config from '../../config'

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

interface PoolDef {
  code: string
  label: string
  description: string
}

const message = useMessage()
const loading = ref(false)
const poolDefs = ref<Record<string, PoolDef>>({})
const poolStats = ref<Record<string, number>>({})
const activePool = ref<string>('PASSIVE')

// 候选人列表 (按 activePool 切换加载)
const candidates = ref<any[]>([])
const listLoading = ref(false)

// 跨池移动弹窗
const moveModal = ref(false)
const moveTargetPool = ref<string | null>(null)
const moveReason = ref<string>('')
const moveCandidate = ref<any | null>(null)

const allPools = computed(() => Object.values(poolDefs.value))

const columns = computed(() => [
  { title: '姓名', key: 'name', width: 100 },
  { title: '电话', key: 'phone', width: 140, render: (row: any) => row.phone || '—' },
  { title: '学历', key: 'highestEducation', width: 90, render: (row: any) => row.highestEducation || '—' },
  { title: '经验', key: 'workExperience', width: 90, render: (row: any) => row.workExperience || '—' },
  {
    title: '归档原因', key: 'archiveReason', width: 160,
    render: (row: any) => row.archiveReason || '—',
  },
  {
    title: '归档时间', key: 'updatedAt', width: 160,
    render: (row: any) => row.updatedAt ? row.updatedAt.slice(0, 16) : '—',
  },
  {
    title: '操作', key: 'actions', width: 120, fixed: 'right' as const,
    render: (row: any) => h(NButton, {
      size: 'tiny', type: 'primary', onClick: () => openMoveModal(row),
    }, {
      default: () => '移动',
      icon: () => h(NIcon, null, { default: () => h(ArrowForwardOutline) }),
    }),
  },
])

const movePoolOptions = computed(() =>
  allPools.value
    .filter(p => p.code !== activePool.value)
    .map(p => ({ label: p.label, value: p.code }))
)

async function loadPoolTypes() {
  const res = await api.get('/api/talent-pool/types')
  poolDefs.value = res.data?.data || {}
  if (!activePool.value && Object.keys(poolDefs.value).length) {
    activePool.value = Object.keys(poolDefs.value)[0]
  }
}

async function loadPoolStats() {
  loading.value = true
  try {
    const res = await api.get('/api/talent-pool/stats')
    poolStats.value = res.data?.data?.stats || {}
  } catch (e: any) {
    message.error(`加载子库统计失败: ${e.message}`)
  } finally {
    loading.value = false
  }
}

async function loadCandidates() {
  if (!activePool.value) return
  listLoading.value = true
  try {
    const res = await api.get(`/api/talent-pool/pool/${activePool.value}`, {
      params: { page: 1, pageSize: 50 },
    })
    candidates.value = res.data?.data?.list || []
  } catch (e: any) {
    message.error(`加载 ${activePool.value} 失败: ${e.message}`)
    candidates.value = []
  } finally {
    listLoading.value = false
  }
}

function openMoveModal(row: any) {
  moveCandidate.value = row
  moveTargetPool.value = null
  moveReason.value = ''
  moveModal.value = true
}

async function confirmMove() {
  if (!moveCandidate.value || !moveTargetPool.value) {
    message.warning('请选择目标子库')
    return
  }
  try {
    await api.post(`/api/talent-pool/pool/${moveTargetPool.value}/move`, {
      candidateId: moveCandidate.value.id,
      reason: moveReason.value,
    })
    message.success(`已移动到 ${poolDefs.value[moveTargetPool.value]?.label || moveTargetPool.value}`)
    moveModal.value = false
    loadPoolStats()
    loadCandidates()
  } catch (e: any) {
    message.error(`移动失败: ${e.response?.data?.message || e.message}`)
  }
}

onMounted(async () => {
  await loadPoolTypes()
  await loadPoolStats()
  await loadCandidates()
})

// 切换 tab 时刷新列表
function onTabChange(key: string) {
  activePool.value = key
  loadCandidates()
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">人才库 - 6 子库</h1>
      <n-space>
        <n-button @click="loadPoolStats" :loading="loading">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
        <n-button type="primary" disabled>
          <template #icon><n-icon :component="AddOutline" /></template>
          添加候选人
        </n-button>
      </n-space>
    </div>

    <n-tabs
      type="line"
      :value="activePool"
      @update:value="onTabChange"
      animated
    >
      <n-tab-pane
        v-for="pool in allPools"
        :key="pool.code"
        :name="pool.code"
        :tab="`${pool.label} (${poolStats[pool.code] || 0})`"
      >
        <n-card :bordered="false" class="rounded-xl">
          <n-empty v-if="candidates.length === 0 && !listLoading" description="该子库暂无候选人" />
          <n-data-table
            v-else
            :columns="columns"
            :data="candidates"
            :loading="listLoading"
            :row-key="(row: any) => row.id"
            :pagination="{ pageSize: 20 }"
          />
        </n-card>
      </n-tab-pane>
    </n-tabs>

    <!-- 跨池移动弹窗 -->
    <n-modal
      v-model:show="moveModal"
      preset="dialog"
      title="移动到其他子库"
      positive-text="确认移动"
      negative-text="取消"
      :positive-button-props="{ type: 'primary' }"
      @positive-click="confirmMove"
    >
      <n-space vertical>
        <div>候选人: <strong>{{ moveCandidate?.name || '—' }}</strong></div>
        <n-select
          v-model:value="moveTargetPool"
          :options="movePoolOptions"
          placeholder="选择目标子库"
        />
        <n-input
          v-model:value="moveReason"
          type="textarea"
          placeholder="移动原因 (审计用)"
          :autosize="{ minRows: 2, maxRows: 4 }"
        />
      </n-space>
    </n-modal>
  </div>
</template>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
