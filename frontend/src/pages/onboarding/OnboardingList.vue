<script setup lang="ts">
import { ref, h, onMounted, computed } from 'vue'
import { NTag, NSpace, NButton, NIcon, useMessage } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import {
  listOnboardings, transitionOnboarding,
  ONBOARDING_STATUS_LABEL, ONBOARDING_STATUS_COLOR,
  type Onboarding,
} from '../../api/onboarding'

const message = useMessage()
const loading = ref(false)
const dataSource = ref<Onboarding[]>([])
const filterStatus = ref<string | null>(null)
const pagination = ref({ page: 1, pageSize: 20, itemCount: 0, pageCount: 0 })

const stats = computed(() => {
  const counts: Record<string, number> = {}
  for (const it of dataSource.value) {
    counts[it.onboardingStatus] = (counts[it.onboardingStatus] || 0) + 1
  }
  return counts
})

const columns = computed(() => [
  { title: '岗位', key: 'jobTitle', width: 160, render: (row: Onboarding) => row.jobTitle || '—' },
  { title: '职级', key: 'jobLevel', width: 80, render: (row: Onboarding) => row.jobLevel || '—' },
  { title: '期望入职', key: 'expectedJoinDate', width: 120, render: (row: Onboarding) => row.expectedJoinDate?.slice(0, 10) },
  { title: '实际入职', key: 'onboardedAt', width: 140, render: (row: Onboarding) => row.onboardedAt?.slice(0, 16) || '—' },
  {
    title: '状态', key: 'onboardingStatus', width: 100,
    render: (row: Onboarding) => h(NTag, { type: ONBOARDING_STATUS_COLOR[row.onboardingStatus] as any, size: 'small' }, { default: () => ONBOARDING_STATUS_LABEL[row.onboardingStatus] || row.onboardingStatus }),
  },
  {
    title: '操作', key: 'actions', width: 280, fixed: 'right' as const,
    render: (row: Onboarding) => {
      const buttons: any[] = []
      if (row.onboardingStatus === 'NOT_STARTED') {
        buttons.push(h(NButton, { size: 'tiny', type: 'warning', onClick: () => handleTransition(row, 'PENDING_CONFIRM') }, { default: () => '提醒确认' }))
      }
      if (row.onboardingStatus === 'PENDING_CONFIRM') {
        buttons.push(h(NButton, { size: 'tiny', type: 'success', onClick: () => handleTransition(row, 'CONFIRMED') }, { default: () => '已确认' }))
        buttons.push(h(NButton, { size: 'tiny', type: 'error', onClick: () => handleTransition(row, 'PENDING_REJECT') }, { default: () => '拒入职' }))
      }
      if (row.onboardingStatus === 'CONFIRMED') {
        buttons.push(h(NButton, { size: 'tiny', type: 'primary', onClick: () => handleTransition(row, 'PENDING_ONBOARD') }, { default: () => '到入职日' }))
      }
      if (row.onboardingStatus === 'PENDING_ONBOARD') {
        buttons.push(h(NButton, { size: 'tiny', type: 'primary', onClick: () => handleTransition(row, 'ONBOARDING') }, { default: () => '开始入职' }))
      }
      if (row.onboardingStatus === 'ONBOARDING') {
        buttons.push(h(NButton, { size: 'tiny', type: 'success', onClick: () => handleTransition(row, 'ONBOARDED') }, { default: () => '完成入职' }))
      }
      if (!['ONBOARDED', 'CANCELLED'].includes(row.onboardingStatus)) {
        buttons.push(h(NButton, { size: 'tiny', quaternary: true, onClick: () => handleTransition(row, 'CANCELLED') }, { default: () => '取消' }))
      }
      return buttons.length ? h(NSpace, { size: 4 }, { default: () => buttons }) : '—'
    },
  },
])

async function loadList() {
  loading.value = true
  try {
    const res = await listOnboardings({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      ...(filterStatus.value && { onboardingStatus: filterStatus.value }),
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

async function handleTransition(row: Onboarding, to: string) {
  try {
    await transitionOnboarding(row.id, to)
    message.success('状态已更新')
    loadList()
  } catch (e: any) {
    message.error(`操作失败: ${e.message}`)
  }
}

onMounted(loadList)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">待入职管理</h1>
      <n-space>
        <n-button @click="loadList" :loading="loading">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
      </n-space>
    </div>

    <n-grid x-gap="12" y-gap="12" cols="4" class="stats-row">
      <n-gi v-for="(count, key) in stats" :key="key">
        <n-card size="small" :bordered="false" class="stat-card">
          <div class="stat-label">{{ ONBOARDING_STATUS_LABEL[key] }}</div>
          <div class="stat-value">{{ count }}</div>
        </n-card>
      </n-gi>
    </n-grid>

    <n-card :bordered="false" class="rounded-xl">
      <n-space class="filter-row">
        <n-select
          v-model:value="filterStatus"
          placeholder="入职状态"
          style="width: 140px"
          clearable
          :options="Object.entries(ONBOARDING_STATUS_LABEL).map(([v,l]) => ({value:v,label:l}))"
          @update:value="loadList"
        />
      </n-space>
      <n-data-table
        :columns="columns"
        :data="dataSource"
        :loading="loading"
        :row-key="(row: Onboarding) => row.id"
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
