<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NTag, NCard, NSpace, NButton, NIcon, useMessage } from 'naive-ui'
import { PeopleCircleOutline, RefreshOutline, AddOutline } from '@vicons/ionicons5'
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

const message = useMessage()
const loading = ref(false)
const candidateCount = ref(0)

// PRD G32: 6 个子库
const SUB_POOLS = [
  { key: 'PASSIVE', name: '被动库', icon: '📋', description: '暂未投递的潜在候选人', count: 0 },
  { key: 'ACTIVE', name: '主动库', icon: '🚀', description: '主动投递的候选人', count: 0 },
  { key: 'HIRED', name: '已聘库', icon: '✅', description: '已入职候选人储备', count: 0 },
  { key: 'REJECTED', name: '已拒库', icon: '❌', description: '不合适候选人(可重新激活)', count: 0 },
  { key: 'BLACKLIST', name: '黑名单', icon: '🚫', description: '永不联系候选人', count: 0 },
  { key: 'TALENT_POOL', name: '通用库', icon: '📦', description: '其他通用储备', count: 0 },
]

const recentCandidates = ref<any[]>([])

async function loadStats() {
  loading.value = true
  try {
    // 简单实现: 查 candidate 总数 (实际应该按 pool 字段 group)
    const res = await api.get('/api/candidates', { params: { page: 1, pageSize: 1 } })
    candidateCount.value = res.data?.pagination?.total || 0
  } catch (e: any) {
    // 静默
  } finally {
    loading.value = false
  }
}

async function loadRecent() {
  try {
    const res = await api.get('/api/candidates', { params: { page: 1, pageSize: 10 } })
    recentCandidates.value = (res.data?.list || []).slice(0, 10)
  } catch (e) { /* 静默 */ }
}

onMounted(() => {
  loadStats()
  loadRecent()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">人才库</h1>
      <n-space>
        <n-button @click="loadStats" :loading="loading">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
        <n-button type="primary" disabled>
          <template #icon><n-icon :component="AddOutline" /></template>
          添加候选人
        </n-button>
      </n-space>
    </div>

    <n-alert type="info" :show-icon="true" style="margin-bottom: 16px;">
      <strong>PRD G32</strong>: 人才库将拆分为 6 个子库, 暂用候选人总数替代。
      完整 CRUD (跨库转移/标签/搜索) 计划下个迭代实施。
    </n-alert>

    <div class="sub-pool-grid">
      <n-card
        v-for="pool in SUB_POOLS"
        :key="pool.key"
        :bordered="false"
        class="pool-card"
        hoverable
      >
        <div class="pool-header">
          <span class="pool-icon">{{ pool.icon }}</span>
          <span class="pool-name">{{ pool.name }}</span>
        </div>
        <div class="pool-count">{{ pool.count }}</div>
        <div class="pool-desc">{{ pool.description }}</div>
        <n-button size="small" block disabled style="margin-top: 8px;">查看 (Phase 3)</n-button>
      </n-card>
    </div>

    <n-card title="最近活跃候选人" :bordered="false" class="rounded-xl" style="margin-top: 16px;">
      <n-empty v-if="recentCandidates.length === 0" description="暂无候选人" />
      <n-list v-else>
        <n-list-item v-for="c in recentCandidates" :key="c.id">
          <n-thing>
            <template #header>{{ c.name }}</template>
            <template #description>
              {{ c.currentCompany }} · {{ c.currentPosition }}
            </template>
          </n-thing>
        </n-list-item>
      </n-list>
    </n-card>
  </div>
</template>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
.sub-pool-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.pool-card { text-align: center; }
.pool-header { display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 12px; }
.pool-icon { font-size: 32px; }
.pool-name { font-size: 16px; font-weight: 600; }
.pool-count { font-size: 32px; font-weight: 700; color: #1890ff; margin: 12px 0; }
.pool-desc { font-size: 12px; color: #8c8c8c; }
@media (max-width: 768px) {
  .sub-pool-grid { grid-template-columns: 1fr; }
}
</style>
