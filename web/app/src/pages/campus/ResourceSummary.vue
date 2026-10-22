<template>
  <!-- 轮岗资源 · BU 汇总面板：作为 RotationResource 的「BU汇总」页签内容渲染。
       页面标题与提示条由宿主页承载（校招生管理各列表页统一去标题），本面板只保留刷新与三块汇总。 -->
  <div class="campus-panel">
    <div class="campus-panel-body">
      <div class="toolbar">
        <div class="spacer"></div>
        <CampusMockBar :is-mock="isMock" @change="load" />
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

      <!-- 其他类型汇总（2026-10-22 兵哥指令：新增「其他」资源类型，不能从汇总里消失） -->
      <n-card title="其他类型汇总（其他占用）" class="summary-card" :bordered="false">
        <n-data-table
          :data="otherRows"
          :columns="otherColumns"
          :row-key="(row: OtherRow) => row.buId ?? '—'"
          :loading="loading"
          :bordered="false"
          size="small"
        >
          <template #empty><n-empty description="暂无其他类型资源" /></template>
        </n-data-table>
      </n-card>

      <!-- 总数据 -->
      <n-card title="总数据" class="summary-card" :bordered="false">
        <n-descriptions label-placement="left" bordered size="small">
          <n-descriptions-item label="直播主播总占用">{{ total.liveAnchorTotal }}</n-descriptions-item>
          <n-descriptions-item label="客服总占用">{{ total.serviceTotal }}</n-descriptions-item>
          <n-descriptions-item label="其他类型总占用">{{ total.otherTotal }}</n-descriptions-item>
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
import { onMounted, ref, computed, h } from 'vue'
import {
  NCard, NDataTable, NEmpty, NButton, NIcon, NTag, NDescriptions, NDescriptionsItem,
} from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { api } from '../../utils/request'
import CampusMockBar from '../../components/campus/CampusMockBar.vue'
import { useCampusMock } from '../../composables/useCampusMock'
import {
  MOCK_RESOURCES,
  buildMockBuSummary,
  resolveDeptRefs,
} from '../../mocks/campus'

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

interface OtherRow {
  buId: string | null
  buName: string
  otherCount: number
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
  otherTotal: number
  grandTotal: number
  buList: BuItem[]
}

interface SummaryData {
  live: LiveRow[]
  service: ServiceRow[]
  other: OtherRow[]
  total: SummaryTotal
}

interface Envelope {
  success: boolean
  data: SummaryData
}

const loading = ref(false)
const liveRows = ref<LiveRow[]>([])
const serviceRows = ref<ServiceRow[]>([])
const otherRows = ref<OtherRow[]>([])
const total = ref<SummaryTotal>({
  liveAnchorTotal: 0, serviceTotal: 0, otherTotal: 0, grandTotal: 0, buList: [],
})

// 示例数据（真实为空时兜底；汇总数字由示例轮岗资源聚合，与「轮岗资源」页签自洽）
const { pickBy, isMock, isMockOnly } = useCampusMock()
const EMPTY_SUMMARY: SummaryData = {
  live: [],
  service: [],
  other: [],
  total: { liveAnchorTotal: 0, serviceTotal: 0, otherTotal: 0, grandTotal: 0, buList: [] },
}
const mockSummary = computed(() =>
  buildMockBuSummary(resolveDeptRefs(MOCK_RESOURCES, [])) as SummaryData,
)

/** 把一份汇总数据写进各段展示区。 */
function applySummary(data: SummaryData) {
  liveRows.value = data.live ?? []
  serviceRows.value = data.service ?? []
  otherRows.value = data.other ?? []
  total.value = data.total ?? {
    liveAnchorTotal: 0, serviceTotal: 0, otherTotal: 0, grandTotal: 0, buList: [],
  }
}

const fmtRate = (rate: number | null): string => (rate == null ? '—' : `${(rate * 100).toFixed(1)}%`)

const pct = (row: LiveRow | ServiceRow | OtherRow) => h(NTag, { size: 'small', type: row.usedRate == null ? 'default' : 'info' }, { default: () => fmtRate(row.usedRate) })

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

const otherColumns = [
  { title: 'BU', key: 'buName', width: 180, render: (row: OtherRow) => row.buName || '未分配' },
  { title: '其他占用', key: 'otherCount', width: 120 },
  { title: '容量', key: 'capacity', width: 120 },
  { title: '占用率', key: 'usedRate', width: 120, render: (row: OtherRow) => pct(row) },
]

async function load() {
  loading.value = true
  try {
    // 强制示例数据模式：跳过接口，用示例直播间/客服部门聚合出 BU 汇总
    if (isMockOnly.value) {
      applySummary(mockSummary.value)
      return
    }
    const resp = await api.get<Envelope>('/campus-rotation/resources/bu-summary/')
    const payload = resp.data
    const data: SummaryData = payload?.data ?? {
      live: [], service: [], other: [],
      total: { liveAnchorTotal: 0, serviceTotal: 0, otherTotal: 0, grandTotal: 0, buList: [] },
    }
    const real: SummaryData = {
      live: data.live ?? [],
      service: data.service ?? [],
      other: data.other ?? [],
      total: data.total ?? {
        liveAnchorTotal: 0, serviceTotal: 0, otherTotal: 0, grandTotal: 0, buList: [],
      },
    }
    // 真实优先：真实汇总为空时用示例数据兜底（数字与示例行自洽）
    const hasReal =
      (real.live?.length || 0) + (real.service?.length || 0) + (real.other?.length || 0) > 0 ||
      (real.total?.grandTotal || 0) > 0
    applySummary(pickBy(hasReal, real, mockSummary.value))
  } catch (e) {
    applySummary(pickBy(false, EMPTY_SUMMARY, mockSummary.value))
    // 错误由全局拦截器统一 toast，这里静默降级为空态
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.campus-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.campus-panel-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.summary-card {
  flex-shrink: 0;
}
.bu-tags {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.bu-tags-label {
  color: var(--ink-faint);
  font-size: 13px;
}
.bu-tag {
  margin-right: 4px;
}
.bu-tags-empty {
  color: var(--ink-faint);
}
</style>
