<template>
  <!-- 考勤管理：逆向清单 §4.1 `attendance` 视图（每日打卡排名 / 月度汇总）。
       页面身份由顶部导航「校招生管理 → 考勤管理」承载，与校招生管理其余列表页一致：不重复标题与提示条。 -->
  <div class="page-container">
    <div class="page-body">
      <n-tabs
        v-model:value="activeTab"
        type="line"
        display-directive="show:lazy"
        class="ca-tabs"
        @update:value="onTabChange"
      >
        <!-- ① 每日打卡排名 -->
        <n-tab-pane name="daily" tab="每日打卡排名">
          <div class="toolbar">
            <div class="field">
              <span class="field-label">打卡日期</span>
              <n-date-picker
                v-model:value="dailyDateTs"
                type="date"
                clearable
                aria-label="打卡日期"
                style="width: 200px"
                @update:value="onDailyDateChange"
              />
            </div>
            <div class="spacer"></div>
            <n-button :loading="dailyLoading" @click="loadDaily">
              <template #icon><n-icon :component="RefreshOutline" /></template>
              刷新排名
            </n-button>
            <!-- R-202：本视图唯一实心主操作（导出当前视图数据），其余保持默认态 -->
            <n-button type="primary" @click="exportDaily">
              <template #icon><n-icon :component="DownloadOutline" /></template>
              导出打卡记录
            </n-button>
          </div>

          <!-- 加载失败：错误三段式（人话描述 + 数据是否安全 + 可点击恢复动作），技术码折叠在详情里（R-203） -->
          <n-alert v-if="dailyError" type="error" :show-icon="true" class="load-error">
            <div class="error-head">
              <span>打卡排名没能加载出来，本次查询没有改动任何数据。</span>
              <n-button size="small" tertiary type="error" :loading="dailyLoading" @click="loadDaily">
                重新加载
              </n-button>
            </div>
            <n-collapse v-if="dailyErrorDetail" class="error-collapse">
              <n-collapse-item title="详情" name="detail">
                <div class="error-detail">
                  <code>{{ dailyErrorDetail }}</code>
                  <n-button size="tiny" quaternary @click="copyDetail(dailyErrorDetail)">复制错误信息</n-button>
                </div>
              </n-collapse-item>
            </n-collapse>
          </n-alert>

          <!-- 骨架屏优先于 spinner（R-205 / R-111） -->
          <div v-if="dailyLoading && !dailyRows.length" class="skeleton-wrap">
            <n-skeleton :repeat="6" animated />
          </div>

          <div v-else class="table-wrap">
            <n-data-table
              :columns="dailyColumns"
              :data="dailyRows"
              :loading="dailyLoading"
              :bordered="false"
              :pagination="pagination"
              :scroll-x="DAILY_SCROLL_X"
              :row-key="(row: DailyRankingRow) => row.id || row.personName"
              flex-height
            >
              <template #empty>
                <n-empty :description="dailyEmptyText" />
              </template>
            </n-data-table>
          </div>
        </n-tab-pane>

        <!-- ② 月度汇总 -->
        <n-tab-pane name="monthly" tab="月度汇总">
          <div class="toolbar">
            <div class="field">
              <span class="field-label">统计月份</span>
              <n-select
                v-model:value="monthlyYm"
                :options="ymOptions"
                aria-label="统计月份"
                style="width: 180px"
                @update:value="loadMonthly"
              />
            </div>
            <div class="spacer"></div>
            <n-button :loading="monthlyLoading" @click="loadMonthly">
              <template #icon><n-icon :component="RefreshOutline" /></template>
              刷新汇总
            </n-button>
            <!-- R-202：本视图唯一实心主操作（导出当前视图数据），其余保持默认态 -->
            <n-button type="primary" @click="exportMonthly">
              <template #icon><n-icon :component="DownloadOutline" /></template>
              导出月度汇总
            </n-button>
          </div>

          <n-alert v-if="monthlyError" type="error" :show-icon="true" class="load-error">
            <div class="error-head">
              <span>月度考勤汇总没能加载出来，本次查询没有改动任何数据。</span>
              <n-button size="small" tertiary type="error" :loading="monthlyLoading" @click="loadMonthly">
                重新加载
              </n-button>
            </div>
            <n-collapse v-if="monthlyErrorDetail" class="error-collapse">
              <n-collapse-item title="详情" name="detail">
                <div class="error-detail">
                  <code>{{ monthlyErrorDetail }}</code>
                  <n-button size="tiny" quaternary @click="copyDetail(monthlyErrorDetail)">复制错误信息</n-button>
                </div>
              </n-collapse-item>
            </n-collapse>
          </n-alert>

          <div v-if="monthlyLoading && !monthlyRows.length" class="skeleton-wrap">
            <n-skeleton :repeat="6" animated />
          </div>

          <div v-else class="table-wrap">
            <n-data-table
              :columns="monthlyColumns"
              :data="monthlyRows"
              :loading="monthlyLoading"
              :bordered="false"
              :pagination="pagination"
              :scroll-x="MONTHLY_SCROLL_X"
              :row-key="(row: AttendanceMonthlyRow) => row.id || row.personName"
              flex-height
            >
              <template #empty>
                <n-empty :description="monthlyEmptyText" />
              </template>
            </n-data-table>
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCollapse,
  NCollapseItem,
  NDataTable,
  NDatePicker,
  NEmpty,
  NIcon,
  NSelect,
  NSkeleton,
  NSpace,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
} from 'naive-ui'
import { DownloadOutline, RefreshOutline } from '@vicons/ionicons5'
import {
  fetchDailyRanking,
  listAttendanceMonthly,
  type AttendanceMonthlyRow,
  type DailyRankingRow,
} from '../../api/campusAssessment'
import { extractError } from '../../utils/campus'

type AttendanceTab = 'daily' | 'monthly'

/** 列表分页（R-108：渲染条目 > 200 必须分页；R-215：分页器固定在表格底部，naive 分页器即表格区最后一个子节点）。 */
const pagination = { pageSize: 50, showSizePicker: false }

const message = useMessage()
const activeTab = ref<AttendanceTab>('daily')

/* ────────────────────────── 每日打卡排名 ────────────────────────── */

const dailyRows = ref<DailyRankingRow[]>([])
const dailyLoading = ref(false)
const dailyError = ref('')
const dailyErrorDetail = ref('')
/** 选中日期（时间戳，null = 不限） */
const dailyDateTs = ref<number | null>(Date.now())
const dailyDate = computed(() => {
  if (!dailyDateTs.value) return ''
  const d = new Date(dailyDateTs.value)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
})

const dailyEmptyText = computed(() =>
  dailyDate.value ? '该日期没有打卡记录，换个日期或清空日期再看看' : '暂无打卡记录',
)

async function loadDaily() {
  dailyLoading.value = true
  dailyError.value = ''
  dailyErrorDetail.value = ''
  try {
    dailyRows.value = await fetchDailyRanking(dailyDate.value ? { date: dailyDate.value } : undefined)
  } catch (e: any) {
    dailyError.value = extractError(e)
    dailyErrorDetail.value = String(e?.message ?? e)
  } finally {
    dailyLoading.value = false
  }
}

function onDailyDateChange() {
  loadDaily()
}

/** 与第 1 名的差距文案：后端给了文案直接用，否则按分钟数折算。 */
function gapText(row: DailyRankingRow): string {
  if (row.gapText) return row.gapText
  if (row.gapToFirst === null || row.gapToFirst === undefined) return '—'
  if (row.rank === 1) return '—'
  return `慢 ${row.gapToFirst} 分钟`
}

const dailyColumns = [
  { title: '排名', key: 'rank', width: 72, render: (row: any) => String(row.rank || '—') },
  { title: '校招生', key: 'personName', width: 120, ellipsis: { tooltip: true } },
  { title: '班级', key: 'classRoomName', width: 140, ellipsis: { tooltip: true } },
  { title: '打卡时间', key: 'punchTime', width: 120, render: (row: any) => row.punchTime || '—' },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: any) => {
      const map: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
        正常: 'success',
        迟到: 'warning',
        请假: 'info',
        缺勤: 'error',
        加班: 'default',
      }
      return h(NTag, { type: map[row.status] ?? 'default', size: 'small', bordered: false }, { default: () => row.status || '—' })
    },
  },
  { title: '与第1名差距', key: 'gap', width: 130, render: (row: any) => gapText(row) },
]
const DAILY_SCROLL_X = 682

/* ────────────────────────── 月度汇总 ────────────────────────── */

const monthlyRows = ref<AttendanceMonthlyRow[]>([])
const monthlyLoading = ref(false)
const monthlyError = ref('')
const monthlyErrorDetail = ref('')
/** 选中月份（yyyy-mm） */
const monthlyYm = ref<string>('')

/** 最近 12 个月的下拉选项。 */
const ymOptions = computed(() => {
  const out: { label: string; value: string }[] = []
  const now = new Date()
  for (let i = 0; i < 12; i += 1) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const ym = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    out.push({ label: ym, value: ym })
  }
  return out
})

const monthlyEmptyText = computed(() =>
  monthlyYm.value ? '该月份没有考勤汇总，换个月份再看看' : '暂无考勤汇总',
)

async function loadMonthly() {
  monthlyLoading.value = true
  monthlyError.value = ''
  monthlyErrorDetail.value = ''
  try {
    monthlyRows.value = await listAttendanceMonthly(monthlyYm.value ? { ym: monthlyYm.value } : undefined)
  } catch (e: any) {
    monthlyError.value = extractError(e)
    monthlyErrorDetail.value = String(e?.message ?? e)
  } finally {
    monthlyLoading.value = false
  }
}

const monthlyColumns = [
  { title: '校招生', key: 'personName', width: 120, ellipsis: { tooltip: true } },
  { title: '班级', key: 'classRoomName', width: 140, ellipsis: { tooltip: true } },
  { title: '轮岗部门', key: 'dept', width: 160, ellipsis: { tooltip: true } },
  { title: '出勤(天)', key: 'attendDays', width: 100, render: (row: any) => String(row.attendDays ?? 0) },
  { title: '迟到(次)', key: 'lateCount', width: 100, render: (row: any) => String(row.lateCount ?? 0) },
  { title: '请假(天)', key: 'leaveDays', width: 100, render: (row: any) => String(row.leaveDays ?? 0) },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: any) =>
      h(NTag, { type: row.status === '异常' ? 'warning' : 'success', size: 'small', bordered: false }, { default: () => row.status || '—' }),
  },
]
const MONTHLY_SCROLL_X = 820

/* ────────────────────────── 页签与通用 ────────────────────────── */

function onTabChange(tab: AttendanceTab) {
  if (tab === 'monthly' && !monthlyRows.value.length) loadMonthly()
}

/* ────────────────────────── 导出（R-202 唯一实心主操作） ────────────────────────── */

/**
 * CSV 单元格转义：双引号包裹 + 公式注入防护（= + - @ 开头加单引号）。
 * 导出的是后端返回的原始文本，不能原样写进 CSV。
 */
function csvCell(value: unknown): string {
  const raw = String(value ?? '')
  const guarded = /^[=+\-@]/.test(raw) ? `'${raw}` : raw
  return `"${guarded.replace(/"/g, '""')}"`
}

/** 触发浏览器下载（happy-dom / 老浏览器无 createObjectURL 时降级为提示）。 */
function downloadCsv(csv: string, filename: string): boolean {
  if (typeof URL.createObjectURL !== 'function') {
    message.warning('当前浏览器不支持文件导出，请手动复制表格内容')
    return false
  }
  try {
    // BOM：让 Excel 正确识别 UTF-8 中文
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
    return true
  } catch {
    message.warning('导出没有成功，请手动复制表格内容')
    return false
  }
}

/** 导出每日打卡排名（当前视图数据）。 */
function exportDaily() {
  if (!dailyRows.value.length) {
    message.warning('当前没有可导出的打卡记录')
    return
  }
  const header = ['排名', '校招生', '班级', '打卡时间', '状态', '与第1名差距']
  const body = dailyRows.value.map((row) => [
    row.rank,
    row.personName,
    row.classRoomName,
    row.punchTime,
    row.status,
    gapText(row),
  ])
  const csv = [header, ...body].map((line) => line.map(csvCell).join(',')).join('\r\n')
  if (downloadCsv(csv, `打卡排名-${dailyDate.value || '全部日期'}.csv`)) {
    message.success(`已导出 ${dailyRows.value.length} 条打卡记录`)
  }
}

/** 导出月度考勤汇总（当前视图数据）。 */
function exportMonthly() {
  if (!monthlyRows.value.length) {
    message.warning('当前没有可导出的月度汇总')
    return
  }
  const header = ['校招生', '班级', '轮岗部门', '出勤(天)', '迟到(次)', '请假(天)', '状态']
  const body = monthlyRows.value.map((row) => [
    row.personName,
    row.classRoomName,
    row.dept,
    row.attendDays,
    row.lateCount,
    row.leaveDays,
    row.status,
  ])
  const csv = [header, ...body].map((line) => line.map(csvCell).join(',')).join('\r\n')
  if (downloadCsv(csv, `月度考勤汇总-${monthlyYm.value || '全部月份'}.csv`)) {
    message.success(`已导出 ${monthlyRows.value.length} 条月度汇总`)
  }
}

/** 复制技术错误信息（折叠在「详情」里，R-203）。 */
async function copyDetail(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    message.success('已复制错误信息')
  } catch {
    message.warning('浏览器不允许复制，请手动选中详情文本')
  }
}

onMounted(() => {
  monthlyYm.value = ymOptions.value[0]?.value ?? ''
  loadDaily()
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
/* 页签栏固定在上方，内容区占满剩余高度并各自内部滚动（R-215 区域滚动） */
.ca-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.ca-tabs :deep(.n-tabs-pane-wrapper) {
  flex: 1;
  min-height: 0;
}
.ca-tabs :deep(.n-tab-pane) {
  box-sizing: border-box;
  height: 100%;
  padding: var(--space-2) 0 0 0;
  display: flex;
  flex-direction: column;
}
/* 工具栏固定，不随表格滚动；窄屏换行，避免固定宽控件被 overflow:hidden 裁切（R-103） */
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  padding-bottom: var(--space-2);
  flex-wrap: wrap;
}
.field {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  min-width: 0;
  max-width: 100%;
}
/* 固定 px 宽的控件在窄屏下不得超过容器宽度（R-103） */
.toolbar :deep(.n-base-selection),
.toolbar :deep(.n-date-picker) {
  max-width: 100%;
}
/* 输入框必须有可见标签（R-218） */
.field-label {
  font-size: var(--text-small);
  color: var(--ink-soft);
  white-space: nowrap;
}
.spacer {
  flex: 1;
}
.skeleton-wrap {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: var(--space-4);
  background: var(--surface);
  border-radius: var(--radius-md);
}
.load-error {
  flex-shrink: 0;
  margin-bottom: var(--space-2);
}
.error-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.error-collapse {
  margin-top: var(--space-2);
}
.error-detail {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  font-size: var(--text-small);
  color: var(--ink-soft);
  overflow-wrap: anywhere;
}
/* 动态数字防抖动：表格数值列统一等宽数字（作用于 naive 自身 DOM，不涉及 h() 渲染节点） */
.table-wrap :deep(.n-data-table-td) {
  font-variant-numeric: tabular-nums;
}
</style>
