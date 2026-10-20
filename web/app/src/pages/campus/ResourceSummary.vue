<template>
  <div class="page-container">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">资源汇总</h1>
          <p class="page-subtitle">按 BU 拆分轮岗资源占用（直播主播 / 客服 / 总数据）</p>
        </div>
      </div>

      <div class="toolbar">
        <div class="spacer"></div>
        <n-button :loading="loading" @click="load">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
      </div>

      <!-- 直播汇总 -->
      <n-card title="直播汇总（主播占用）" class="summary-card" :bordered="false">
        <n-data-table
          :data="liveRows"
          :columns="liveColumns"
          :row-key="(row: LiveRow) => row.buId ?? '—'"
          :loading="loading"
          :bordered="false"
          size="small"
        >
          <template #empty><n-empty description="暂无直播间数据" /></template>
        </n-data-table>
      </n-card>

      <!-- 客服汇总 -->
      <n-card title="客服汇总（客服占用）" class="summary-card" :bordered="false">
        <n-data-table
          :data="serviceRows"
          :columns="serviceColumns"
          :row-key="(row: ServiceRow) => row.buId ?? '—'"
          :loading="loading"
          :bordered="false"
          size="small"
        >
          <template #empty><n-empty description="暂无客服部门数据" /></template>
        </n-data-table>
      </n-card>

      <!-- 总数据 -->
      <n-card title="总数据" class="summary-card" :bordered="false">
        <n-descriptions label-placement="left" bordered size="small">
          <n-descriptions-item label="直播主播总占用">{{ total.liveAnchorTotal }}</n-descriptions-item>
          <n-descriptions-item label="客服总占用">{{ total.serviceTotal }}</n-descriptions-item>
          <n-descriptions-item label="合计占用">{{ total.grandTotal }}</n-descriptions-item>
        </n-descriptions>
        <div class="bu-tags">
          <span class="bu-tags-label">涉及 BU：</span>
          <n-tag
            v-for="b in total.buList"
            :key="b.buId ?? '—'"
            size="small"
            :bordered="true"
            class="bu-tag"
          >
            {{ b.buName || '未分配' }}
          </n-tag>
          <span v-if="total.buList.length === 0" class="bu-tags-empty">—</span>
        </div>
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, h } from 'vue'
import {
  NCard, NDataTable, NEmpty, NButton, NIcon, NTag, NDescriptions, NDescriptionsItem,
} from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { api } from '../../utils/request'

interface LiveRow {
  buId: string | null
  buName: string
  anchorCount: number
  capacity: number
  usedRate: number | null
}

interface ServiceRow {
  buId: string | null
  buName: string
  csCount: number
  capacity: number
  usedRate: number | null
}

interface BuItem {
  buId: string | null
  buName: string
}

interface SummaryTotal {
  liveAnchorTotal: number
  serviceTotal: number
  grandTotal: number
  buList: BuItem[]
}

interface SummaryData {
  live: LiveRow[]
  service: ServiceRow[]
  total: SummaryTotal
}

interface Envelope {
  success: boolean
  data: SummaryData
}

const loading = ref(false)
const liveRows = ref<LiveRow[]>([])
const serviceRows = ref<ServiceRow[]>([])
const total = ref<SummaryTotal>({ liveAnchorTotal: 0, serviceTotal: 0, grandTotal: 0, buList: [] })

const fmtRate = (rate: number | null): string => (rate == null ? '—' : `${(rate * 100).toFixed(1)}%`)

const pct = (row: LiveRow | ServiceRow) => h(NTag, { size: 'small', type: row.usedRate == null ? 'default' : 'info' }, { default: () => fmtRate(row.usedRate) })

const liveColumns = [
  { title: 'BU', key: 'buName', width: 180, render: (row: LiveRow) => row.buName || '未分配' },
  { title: '主播占用', key: 'anchorCount', width: 120 },
  { title: '容量', key: 'capacity', width: 120 },
  { title: '占用率', key: 'usedRate', width: 120, render: (row: LiveRow) => pct(row) },
]

const serviceColumns = [
  { title: 'BU', key: 'buName', width: 180, render: (row: ServiceRow) => row.buName || '未分配' },
  { title: '客服占用', key: 'csCount', width: 120 },
  { title: '容量', key: 'capacity', width: 120 },
  { title: '占用率', key: 'usedRate', width: 120, render: (row: ServiceRow) => pct(row) },
]

async function load() {
  loading.value = true
  try {
    const resp = await api.get<Envelope>('/campus-rotation/resources/bu-summary/')
    const payload = resp.data
    const data: SummaryData = payload?.data ?? { live: [], service: [], total: { liveAnchorTotal: 0, serviceTotal: 0, grandTotal: 0, buList: [] } }
    liveRows.value = data.live ?? []
    serviceRows.value = data.service ?? []
    total.value = data.total ?? { liveAnchorTotal: 0, serviceTotal: 0, grandTotal: 0, buList: [] }
  } catch (e) {
    liveRows.value = []
    serviceRows.value = []
    total.value = { liveAnchorTotal: 0, serviceTotal: 0, grandTotal: 0, buList: [] }
    // 错误由全局拦截器统一 toast，这里静默降级为空态
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.summary-card {
  margin-bottom: 16px;
}
.bu-tags {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.bu-tags-label {
  color: var(--n-text-color-3, #999);
  font-size: 13px;
}
.bu-tag {
  margin-right: 4px;
}
.bu-tags-empty {
  color: var(--n-text-color-3, #999);
}
</style>
