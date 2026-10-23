<template>
  <div class="page-container">
    <div class="page-body">
      <n-tabs v-model:value="activeTab" type="line" class="page-tabs" @update:value="onTabChange">
        <n-tab-pane name="roster" tab="花名册" />
        <n-tab-pane name="goal" tab="目标" />
        <n-tab-pane name="metric" tab="数据" />
        <n-tab-pane name="assessment" tab="考核" />
      </n-tabs>

      <!-- ① 花名册 -->
      <template v-if="activeTab === 'roster'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">定岗</span>
            <n-input
              v-model:value="rosterSearch"
              aria-label="姓名或定岗部门"
              class="toolbar-search"
              placeholder="搜索姓名或定岗部门"
              clearable
              @keyup.enter="loadRecords"
            >
              <template #prefix><n-icon :component="SearchOutline" /></template>
            </n-input>
          </div>
          <div class="spacer"></div>
          <n-button :loading="recordLoading" @click="loadRecords">查询名单</n-button>
          <n-button type="primary" @click="openRecordCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增定岗
          </n-button>
        </div>

        <div v-if="recordError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">定岗花名册没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，你填的定岗信息仍保留在本页，不会丢失。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ recordError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(recordError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="recordLoading" @click="loadRecords">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="recordLoading && !recordRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="rosterColumns"
            :data="recordRows"
            :loading="recordLoading"
            :bordered="false"
            :scroll-x="ROSTER_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: PlacementRecord) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="rosterEmptyText" size="small">
                <template #extra>
                  <n-button v-if="rosterSearch" size="small" @click="rosterSearch = ''; loadRecords()">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ② 目标 -->
      <template v-if="activeTab === 'goal'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">定岗记录</span>
            <n-select
              v-model:value="goalRecord"
              aria-label="定岗记录"
              class="toolbar-select-wide"
              :options="recordOptions"
              placeholder="全部定岗记录"
              clearable
              @update:value="loadGoals"
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="goalLoading" @click="loadGoals">刷新目标</n-button>
          <n-button type="primary" :disabled="!goalRecord" @click="openGoalCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增目标
          </n-button>
        </div>

        <div v-if="goalError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">定岗目标没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，已维护的目标仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ goalError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(goalError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="goalLoading" @click="loadGoals">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="goalLoading && !goalRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="goalColumns"
            :data="goalRows"
            :loading="goalLoading"
            :bordered="false"
            :scroll-x="GOAL_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: PlacementGoal) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="goalEmptyText" size="small">
                <template #extra>
                  <n-button v-if="goalRecord" size="small" @click="goalRecord = null; loadGoals()">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ③ 数据 -->
      <template v-if="activeTab === 'metric'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">定岗记录</span>
            <n-select
              v-model:value="metricRecord"
              aria-label="定岗记录"
              class="toolbar-select-wide"
              :options="recordOptions"
              placeholder="全部定岗记录"
              clearable
              @update:value="loadMetrics"
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="metricLoading" @click="loadMetrics">刷新数据</n-button>
          <n-button type="primary" :disabled="!metricRecord" @click="openMetricCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增数据
          </n-button>
        </div>

        <div v-if="metricError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">定岗数据没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，已填报的数据仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ metricError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(metricError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="metricLoading" @click="loadMetrics">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="metricLoading && !metricRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="metricColumns"
            :data="metricRows"
            :loading="metricLoading"
            :bordered="false"
            :scroll-x="METRIC_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: PlacementMetric) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="metricEmptyText" size="small">
                <template #extra>
                  <n-button v-if="metricRecord" size="small" @click="metricRecord = null; loadMetrics()">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ④ 考核 -->
      <template v-if="activeTab === 'assessment'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">定岗记录</span>
            <n-select
              v-model:value="assessmentRecord"
              aria-label="定岗记录"
              class="toolbar-select-wide"
              :options="recordOptions"
              placeholder="全部定岗记录"
              clearable
              @update:value="loadAssessments"
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="assessmentLoading" @click="loadAssessments">刷新考核</n-button>
          <n-button type="primary" :disabled="!assessmentRecord" @click="openAssessmentCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增考核
          </n-button>
        </div>

        <div v-if="assessmentError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">定岗考核没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，已录入的考核仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ assessmentError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(assessmentError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="assessmentLoading" @click="loadAssessments">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="assessmentLoading && !assessmentRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="assessmentColumns"
            :data="assessmentRows"
            :loading="assessmentLoading"
            :bordered="false"
            :scroll-x="ASSESSMENT_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: PlacementAssessment) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="assessmentEmptyText" size="small">
                <template #extra>
                  <n-button v-if="assessmentRecord" size="small" @click="assessmentRecord = null; loadAssessments()">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- 定岗记录 新增 / 编辑 弹窗 -->
      <n-modal
        v-model:show="recordFormVisible"
        preset="card"
        :title="recordEditing ? '编辑定岗记录' : '新增定岗记录'"
        :style="{ width: '720px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(560px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="recordForm" label-placement="top">
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="校招生" required>
                <n-select
                  v-model:value="recordForm.person"
                  :options="personOptions"
                  placeholder="搜索并选择校招生"
                  clearable
                  filterable
                  remote
                  :loading="personLoading"
                  :on-search="onPersonSearch"
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="定岗部门" required>
                <n-input v-model:value="recordForm.dept" placeholder="请输入定岗部门" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="岗位名称" required>
                <n-input v-model:value="recordForm.positionName" placeholder="请输入岗位名称" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="定岗日期" required>
                <n-date-picker v-model:value="recordForm.placeDateTs" type="date" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="跟踪年数">
                <n-input-number v-model:value="recordForm.trackYears" :min="0" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="跟踪状态" required>
                <n-select v-model:value="recordForm.status" :options="recordStatusOptions" placeholder="请选择跟踪状态" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="最近绩效">
                <n-input v-model:value="recordForm.latestPerf" placeholder="如 A / 优" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="recordFormVisible = false">取消</n-button>
            <n-button type="primary" :loading="recordSaving" :disabled="recordSaving" @click="saveRecord">保存定岗</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 目标 新增 / 编辑 弹窗 -->
      <n-modal
        v-model:show="goalFormVisible"
        preset="card"
        :title="goalEditing ? '编辑定岗目标' : '新增定岗目标'"
        :style="{ width: '680px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(520px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="goalForm" label-placement="top">
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="目标名称" required>
                <n-input v-model:value="goalForm.name" placeholder="请输入目标名称" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="衡量指标" required>
                <n-input v-model:value="goalForm.metric" placeholder="如 出勤率" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="目标值" required>
                <n-input v-model:value="goalForm.targetValue" placeholder="如 ≥ 95%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="权重（%）" required>
                <n-input-number v-model:value="goalForm.weight" :min="0" :max="100" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="截止日期">
                <n-date-picker v-model:value="goalForm.dueDateTs" type="date" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="目标状态" required>
                <n-select v-model:value="goalForm.status" :options="goalStatusOptions" placeholder="请选择目标状态" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="goalFormVisible = false">取消</n-button>
            <n-button type="primary" :loading="goalSaving" :disabled="goalSaving" @click="saveGoal">保存目标</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 数据 新增 / 编辑 弹窗 -->
      <n-modal
        v-model:show="metricFormVisible"
        preset="card"
        :title="metricEditing ? '编辑定岗数据' : '新增定岗数据'"
        :style="{ width: '680px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(480px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="metricForm" label-placement="top">
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="月份" required>
                <n-input v-model:value="metricForm.ym" placeholder="如 2026-09" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="指标" required>
                <n-input v-model:value="metricForm.metric" placeholder="请输入指标名称" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="完成值" required>
                <n-input v-model:value="metricForm.actualValue" placeholder="如 96%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="备注">
                <n-input v-model:value="metricForm.remark" placeholder="补充说明" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="metricFormVisible = false">取消</n-button>
            <n-button type="primary" :loading="metricSaving" :disabled="metricSaving" @click="saveMetric">保存数据</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 考核 新增 / 编辑 弹窗 -->
      <n-modal
        v-model:show="assessmentFormVisible"
        preset="card"
        :title="assessmentEditing ? '编辑定岗考核' : '新增定岗考核'"
        :style="{ width: '680px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(480px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="assessmentForm" label-placement="top">
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="考核周期" required>
                <n-input v-model:value="assessmentForm.period" placeholder="如 2026 年第三季度" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="考核得分" required>
                <n-input-number v-model:value="assessmentForm.score" :min="0" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="绩效等级" required>
                <n-input v-model:value="assessmentForm.perfLevel" placeholder="如 A / B" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="评定日期" required>
                <n-date-picker v-model:value="assessmentForm.assessedAtTs" type="date" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-form-item label="评语">
            <n-input v-model:value="assessmentForm.comment" type="textarea" placeholder="考核评语" />
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="assessmentFormVisible = false">取消</n-button>
            <n-button type="primary" :loading="assessmentSaving" :disabled="assessmentSaving" @click="saveAssessment">保存考核</n-button>
          </div>
        </template>
      </n-modal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NDataTable,
  NDatePicker,
  NEmpty,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NIcon,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NSkeleton,
  NSpace,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
  useNotification,
} from 'naive-ui'
import { AddOutline, AlertCircleOutline, CreateOutline, SearchOutline, TrashOutline } from '@vicons/ionicons5'
import {
  createPlacementAssessment,
  createPlacementGoal,
  createPlacementMetric,
  createPlacementRecord,
  deletePlacementAssessment,
  deletePlacementGoal,
  deletePlacementMetric,
  deletePlacementRecord,
  listPlacementAssessments,
  listPlacementGoals,
  listPlacementMetrics,
  listPlacementRecords,
  restorePlacementAssessment,
  restorePlacementGoal,
  restorePlacementMetric,
  restorePlacementRecord,
  updatePlacementAssessment,
  updatePlacementGoal,
  updatePlacementMetric,
  updatePlacementRecord,
  type PlacementAssessment,
  type PlacementGoal,
  type PlacementMetric,
  type PlacementRecord,
} from '../../api/campusPlacement'
import { extractError, searchPersons, type SelectOption } from '../../utils/campus'

const message = useMessage()
const notification = useNotification()

type TabKey = 'roster' | 'goal' | 'metric' | 'assessment'
const activeTab = ref<TabKey>('roster')

const RECORD_STATUS_OPTIONS = ['待跟踪', '跟踪中', '已结束'].map((v) => ({ label: v, value: v }))
const recordStatusOptions = RECORD_STATUS_OPTIONS
const GOAL_STATUS_OPTIONS = ['未开始', '进行中', '已完成', '已逾期'].map((v) => ({ label: v, value: v }))
const goalStatusOptions = GOAL_STATUS_OPTIONS

/* ───────────────────────── 通用工具 ───────────────────────── */

function textCell(text: unknown, width = 140) {
  const s = text == null || text === '' ? '—' : String(text)
  return h('span', { title: s, style: { display: 'inline-block', maxWidth: `${width}px`, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, s)
}

function numCell(value: unknown) {
  return h('span', { style: { fontVariantNumeric: 'tabular-nums' } }, value == null ? '—' : String(value))
}

async function copyText(text: string) {
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      message.success('错误信息已复制')
      return
    }
  } catch {
    /* 降级提示 */
  }
  message.warning('复制失败，请手动选中详情内容复制')
}

function toDateStr(ts: number | null) {
  if (!ts) return undefined
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/* ───────────────────────── ① 花名册 ───────────────────────── */

const recordRows = ref<PlacementRecord[]>([])
const recordLoading = ref(false)
const recordError = ref('')
const rosterSearch = ref('')
const goalRows = ref<PlacementGoal[]>([])

const rosterHasFilter = computed(() => Boolean(rosterSearch.value.trim()))
const rosterEmptyText = computed(() => (rosterHasFilter.value ? '没有符合筛选条件的定岗记录' : '暂无数据'))

const recordOptions = computed(() =>
  recordRows.value.map((r) => ({
    label: `${r.personName || '未命名'} · ${r.positionName || ''}`,
    value: String(r.id),
  })),
)

/** 届数：从校招批次推导（如 2026秋招 → 26 届），无批次时显示「—」。 */
function cohortLabel(batch?: string) {
  const m = String(batch || '').match(/(\d{4})/)
  return m ? `${m[1].slice(2)} 届` : '—'
}

async function loadRecords() {
  recordLoading.value = true
  recordError.value = ''
  try {
    const kw = rosterSearch.value.trim()
    const rows = await listPlacementRecords({ search: kw || undefined })
    recordRows.value = kw
      ? rows.filter((r) => `${r.personName}${r.dept}`.includes(kw))
      : rows
  } catch (e: any) {
    recordError.value = extractError(e)
    recordRows.value = []
  } finally {
    recordLoading.value = false
  }
}

/** 每条定岗记录关联的目标数量与首个目标名（目标列）。 */
function goalSummary(recordId: string) {
  const goals = goalRows.value.filter((g) => String(g.record) === String(recordId))
  if (!goals.length) return '—'
  return `${goals.length} 项 · ${goals[0].name}`
}

const rosterColumns = computed(() => [
  { title: '姓名', key: 'personName', width: 120, ellipsis: true, render: (row: PlacementRecord) => textCell(row.personName, 100) },
  { title: '届数', key: 'cohort', width: 90, render: (row: PlacementRecord) => cohortLabel(row.batch) },
  { title: '校招批次', key: 'batch', width: 130, ellipsis: true, render: (row: PlacementRecord) => textCell(row.batch, 110) },
  { title: '定岗部门', key: 'dept', width: 140, ellipsis: true, render: (row: PlacementRecord) => textCell(row.dept, 120) },
  { title: '岗位', key: 'positionName', width: 160, ellipsis: true, render: (row: PlacementRecord) => textCell(row.positionName, 140) },
  { title: '定岗日期', key: 'placeDate', width: 120, render: (row: PlacementRecord) => row.placeDate || '—' },
  { title: '目标', key: 'goals', width: 200, ellipsis: true, render: (row: PlacementRecord) => textCell(goalSummary(row.id), 180) },
  { title: '最近考核', key: 'latestPerf', width: 100, render: (row: PlacementRecord) => row.latestPerf || '—' },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: PlacementRecord) => {
      const map: Record<string, any> = { 待跟踪: 'warning', 跟踪中: 'success', 已结束: 'default' }
      return h(NTag, { type: map[row.status] || 'default', size: 'small' }, { default: () => row.status || '—' })
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 170,
    fixed: 'right' as const,
    render: (row: PlacementRecord) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openRecordEdit(row) }, {
            default: () => '编辑定岗',
            icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeRecord(row) }, {
            default: () => '删除定岗',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          }),
        ],
      }),
  },
])

const ROSTER_SCROLL_X = 1310

/* ── 定岗记录 新增 / 编辑 ── */
const recordFormVisible = ref(false)
const recordSaving = ref(false)
const recordEditing = ref<PlacementRecord | null>(null)
const personOptions = ref<SelectOption[]>([])
const personLoading = ref(false)
const recordForm = reactive({
  person: null as string | null,
  dept: '',
  positionName: '',
  placeDateTs: null as number | null,
  trackYears: 1,
  status: '待跟踪',
  latestPerf: '',
})

async function onPersonSearch(kw: string) {
  personLoading.value = true
  try {
    personOptions.value = await searchPersons(kw)
  } catch {
    personOptions.value = []
  } finally {
    personLoading.value = false
  }
}

function openRecordCreate() {
  Object.assign(recordForm, {
    person: null,
    dept: '',
    positionName: '',
    placeDateTs: Date.now(),
    trackYears: 1,
    status: '待跟踪',
    latestPerf: '',
  })
  recordEditing.value = null
  recordFormVisible.value = true
}

function openRecordEdit(row: PlacementRecord) {
  Object.assign(recordForm, {
    person: row.person ? String(row.person) : null,
    dept: row.dept || '',
    positionName: row.positionName || '',
    placeDateTs: row.placeDate ? new Date(row.placeDate).getTime() : null,
    trackYears: row.trackYears ?? 1,
    status: row.status || '待跟踪',
    latestPerf: row.latestPerf || '',
  })
  personOptions.value = row.person ? [{ label: row.personName || String(row.person), value: String(row.person) }] : []
  recordEditing.value = row
  recordFormVisible.value = true
}

async function saveRecord() {
  if (!recordForm.person) {
    message.warning('请选择校招生')
    return
  }
  if (!recordForm.dept.trim()) {
    message.warning('请填写定岗部门')
    return
  }
  if (!recordForm.positionName.trim()) {
    message.warning('请填写岗位名称')
    return
  }
  if (!recordForm.placeDateTs) {
    message.warning('请选择定岗日期')
    return
  }
  recordSaving.value = true
  const payload = {
    person: String(recordForm.person),
    dept: recordForm.dept.trim(),
    positionName: recordForm.positionName.trim(),
    placeDate: toDateStr(recordForm.placeDateTs),
    trackYears: recordForm.trackYears,
    status: recordForm.status,
    latestPerf: recordForm.latestPerf.trim(),
  }
  try {
    if (recordEditing.value) {
      await updatePlacementRecord(recordEditing.value.id, payload)
      message.success('定岗记录已更新')
    } else {
      await createPlacementRecord(payload)
      message.success('定岗记录已创建')
    }
    recordFormVisible.value = false
    loadRecords()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    recordSaving.value = false
  }
}

/** 删除单条定岗记录 = 中等破坏性操作 → 直接执行 + 通知撤销（R-106）。 */
async function removeRecord(row: PlacementRecord) {
  try {
    await deletePlacementRecord(row.id)
    notification.create({
      content: `已删除「${row.personName || '该校招生'}」的定岗记录`,
      duration: 8000,
      keepAliveOnHover: true,
      action: () =>
        h(NButton, {
          text: true,
          type: 'primary',
          onClick: async () => {
            try {
              await restorePlacementRecord(row.id)
              message.success('定岗记录已恢复')
              loadRecords()
            } catch (e: any) {
              message.error(extractError(e))
            }
          },
        }, { default: () => '撤销' }),
    })
    loadRecords()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/* ───────────────────────── ② 目标 ───────────────────────── */

const goalLoading = ref(false)
const goalError = ref('')
const goalRecord = ref<string | null>(null)
const goalHasFilter = computed(() => Boolean(goalRecord.value))
const goalEmptyText = computed(() => (goalRecord.value ? '该定岗记录还没有目标' : '暂无数据'))

async function loadGoals() {
  goalLoading.value = true
  goalError.value = ''
  try {
    goalRows.value = await listPlacementGoals({ record: goalRecord.value ?? undefined })
  } catch (e: any) {
    goalError.value = extractError(e)
    goalRows.value = []
  } finally {
    goalLoading.value = false
  }
}

const goalColumns = computed(() => [
  { title: '目标名称', key: 'name', width: 200, ellipsis: true, render: (row: PlacementGoal) => textCell(row.name, 180) },
  { title: '衡量指标', key: 'metric', width: 140, ellipsis: true, render: (row: PlacementGoal) => textCell(row.metric, 120) },
  { title: '目标值', key: 'targetValue', width: 120, ellipsis: true, render: (row: PlacementGoal) => textCell(row.targetValue, 100) },
  { title: '权重', key: 'weight', width: 90, render: (row: PlacementGoal) => numCell(row.weight == null ? '—' : `${row.weight}%`) },
  { title: '截止日期', key: 'dueDate', width: 120, render: (row: PlacementGoal) => row.dueDate || '—' },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: PlacementGoal) => {
      const map: Record<string, any> = { 未开始: 'default', 进行中: 'warning', 已完成: 'success', 已逾期: 'error' }
      return h(NTag, { type: map[row.status] || 'default', size: 'small' }, { default: () => row.status || '—' })
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 170,
    fixed: 'right' as const,
    render: (row: PlacementGoal) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openGoalEdit(row) }, {
            default: () => '编辑目标',
            icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeGoal(row) }, {
            default: () => '删除目标',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          }),
        ],
      }),
  },
])

const GOAL_SCROLL_X = 1010

const goalFormVisible = ref(false)
const goalSaving = ref(false)
const goalEditing = ref<PlacementGoal | null>(null)
const goalForm = reactive({
  name: '',
  metric: '',
  targetValue: '',
  weight: 0,
  dueDateTs: null as number | null,
  status: '未开始',
})

function openGoalCreate() {
  Object.assign(goalForm, { name: '', metric: '', targetValue: '', weight: 0, dueDateTs: null, status: '未开始' })
  goalEditing.value = null
  goalFormVisible.value = true
}

function openGoalEdit(row: PlacementGoal) {
  Object.assign(goalForm, {
    name: row.name || '',
    metric: row.metric || '',
    targetValue: row.targetValue || '',
    weight: row.weight ?? 0,
    dueDateTs: row.dueDate ? new Date(row.dueDate).getTime() : null,
    status: row.status || '未开始',
  })
  goalEditing.value = row
  goalFormVisible.value = true
}

async function saveGoal() {
  if (!goalRecord.value) {
    message.warning('请先选择定岗记录')
    return
  }
  if (!goalForm.name.trim()) {
    message.warning('请填写目标名称')
    return
  }
  if (!goalForm.metric.trim()) {
    message.warning('请填写衡量指标')
    return
  }
  if (!goalForm.targetValue.trim()) {
    message.warning('请填写目标值')
    return
  }
  goalSaving.value = true
  const payload = {
    record: String(goalRecord.value),
    name: goalForm.name.trim(),
    metric: goalForm.metric.trim(),
    targetValue: goalForm.targetValue.trim(),
    weight: goalForm.weight,
    dueDate: toDateStr(goalForm.dueDateTs),
    status: goalForm.status,
  }
  try {
    if (goalEditing.value) {
      await updatePlacementGoal(goalEditing.value.id, payload)
      message.success('定岗目标已更新')
    } else {
      await createPlacementGoal(payload)
      message.success('定岗目标已创建')
    }
    goalFormVisible.value = false
    loadGoals()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    goalSaving.value = false
  }
}

async function removeGoal(row: PlacementGoal) {
  try {
    await deletePlacementGoal(row.id)
    notification.create({
      content: `已删除目标「${row.name}」`,
      duration: 8000,
      keepAliveOnHover: true,
      action: () =>
        h(NButton, {
          text: true,
          type: 'primary',
          onClick: async () => {
            try {
              await restorePlacementGoal(row.id)
              message.success('定岗目标已恢复')
              loadGoals()
            } catch (e: any) {
              message.error(extractError(e))
            }
          },
        }, { default: () => '撤销' }),
    })
    loadGoals()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/* ───────────────────────── ③ 数据 ───────────────────────── */

const metricRows = ref<PlacementMetric[]>([])
const metricLoading = ref(false)
const metricError = ref('')
const metricRecord = ref<string | null>(null)
const metricHasFilter = computed(() => Boolean(metricRecord.value))
const metricEmptyText = computed(() => (metricRecord.value ? '该定岗记录还没有数据' : '暂无数据'))

async function loadMetrics() {
  metricLoading.value = true
  metricError.value = ''
  try {
    metricRows.value = await listPlacementMetrics({ record: metricRecord.value ?? undefined })
  } catch (e: any) {
    metricError.value = extractError(e)
    metricRows.value = []
  } finally {
    metricLoading.value = false
  }
}

const metricColumns = computed(() => [
  { title: '月份', key: 'ym', width: 120, render: (row: PlacementMetric) => row.ym || '—' },
  { title: '指标', key: 'metric', width: 180, ellipsis: true, render: (row: PlacementMetric) => textCell(row.metric, 160) },
  { title: '完成值', key: 'actualValue', width: 140, ellipsis: true, render: (row: PlacementMetric) => textCell(row.actualValue, 120) },
  { title: '备注', key: 'remark', width: 220, ellipsis: true, render: (row: PlacementMetric) => textCell(row.remark, 200) },
  {
    title: '操作',
    key: 'actions',
    width: 170,
    fixed: 'right' as const,
    render: (row: PlacementMetric) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openMetricEdit(row) }, {
            default: () => '编辑数据',
            icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeMetric(row) }, {
            default: () => '删除数据',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          }),
        ],
      }),
  },
])

const METRIC_SCROLL_X = 830

const metricFormVisible = ref(false)
const metricSaving = ref(false)
const metricEditing = ref<PlacementMetric | null>(null)
const metricForm = reactive({ ym: '', metric: '', actualValue: '', remark: '' })

function openMetricCreate() {
  Object.assign(metricForm, { ym: '', metric: '', actualValue: '', remark: '' })
  metricEditing.value = null
  metricFormVisible.value = true
}

function openMetricEdit(row: PlacementMetric) {
  Object.assign(metricForm, {
    ym: row.ym || '',
    metric: row.metric || '',
    actualValue: row.actualValue || '',
    remark: row.remark || '',
  })
  metricEditing.value = row
  metricFormVisible.value = true
}

async function saveMetric() {
  if (!metricRecord.value) {
    message.warning('请先选择定岗记录')
    return
  }
  if (!metricForm.ym.trim()) {
    message.warning('请填写月份')
    return
  }
  if (!metricForm.metric.trim()) {
    message.warning('请填写指标')
    return
  }
  if (!metricForm.actualValue.trim()) {
    message.warning('请填写完成值')
    return
  }
  metricSaving.value = true
  const payload = {
    record: String(metricRecord.value),
    ym: metricForm.ym.trim(),
    metric: metricForm.metric.trim(),
    actualValue: metricForm.actualValue.trim(),
    remark: metricForm.remark.trim(),
  }
  try {
    if (metricEditing.value) {
      await updatePlacementMetric(metricEditing.value.id, payload)
      message.success('定岗数据已更新')
    } else {
      await createPlacementMetric(payload)
      message.success('定岗数据已创建')
    }
    metricFormVisible.value = false
    loadMetrics()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    metricSaving.value = false
  }
}

async function removeMetric(row: PlacementMetric) {
  try {
    await deletePlacementMetric(row.id)
    notification.create({
      content: `已删除「${row.ym}」的数据`,
      duration: 8000,
      keepAliveOnHover: true,
      action: () =>
        h(NButton, {
          text: true,
          type: 'primary',
          onClick: async () => {
            try {
              await restorePlacementMetric(row.id)
              message.success('定岗数据已恢复')
              loadMetrics()
            } catch (e: any) {
              message.error(extractError(e))
            }
          },
        }, { default: () => '撤销' }),
    })
    loadMetrics()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/* ───────────────────────── ④ 考核 ───────────────────────── */

const assessmentRows = ref<PlacementAssessment[]>([])
const assessmentLoading = ref(false)
const assessmentError = ref('')
const assessmentRecord = ref<string | null>(null)
const assessmentHasFilter = computed(() => Boolean(assessmentRecord.value))
const assessmentEmptyText = computed(() => (assessmentRecord.value ? '该定岗记录还没有考核' : '暂无数据'))

async function loadAssessments() {
  assessmentLoading.value = true
  assessmentError.value = ''
  try {
    assessmentRows.value = await listPlacementAssessments({ record: assessmentRecord.value ?? undefined })
  } catch (e: any) {
    assessmentError.value = extractError(e)
    assessmentRows.value = []
  } finally {
    assessmentLoading.value = false
  }
}

const assessmentColumns = computed(() => [
  { title: '考核周期', key: 'period', width: 180, ellipsis: true, render: (row: PlacementAssessment) => textCell(row.period, 160) },
  { title: '得分', key: 'score', width: 100, render: (row: PlacementAssessment) => numCell(row.score) },
  { title: '绩效等级', key: 'perfLevel', width: 110, render: (row: PlacementAssessment) => row.perfLevel || '—' },
  { title: '评定日期', key: 'assessedAt', width: 120, render: (row: PlacementAssessment) => row.assessedAt || '—' },
  { title: '评语', key: 'comment', width: 240, ellipsis: true, render: (row: PlacementAssessment) => textCell(row.comment, 220) },
  {
    title: '操作',
    key: 'actions',
    width: 170,
    fixed: 'right' as const,
    render: (row: PlacementAssessment) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openAssessmentEdit(row) }, {
            default: () => '编辑考核',
            icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeAssessment(row) }, {
            default: () => '删除考核',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          }),
        ],
      }),
  },
])

const ASSESSMENT_SCROLL_X = 920

const assessmentFormVisible = ref(false)
const assessmentSaving = ref(false)
const assessmentEditing = ref<PlacementAssessment | null>(null)
const assessmentForm = reactive({
  period: '',
  score: 0,
  perfLevel: '',
  assessedAtTs: null as number | null,
  comment: '',
})

function openAssessmentCreate() {
  Object.assign(assessmentForm, { period: '', score: 0, perfLevel: '', assessedAtTs: Date.now(), comment: '' })
  assessmentEditing.value = null
  assessmentFormVisible.value = true
}

function openAssessmentEdit(row: PlacementAssessment) {
  Object.assign(assessmentForm, {
    period: row.period || '',
    score: row.score ?? 0,
    perfLevel: row.perfLevel || '',
    assessedAtTs: row.assessedAt ? new Date(row.assessedAt).getTime() : null,
    comment: row.comment || '',
  })
  assessmentEditing.value = null
  assessmentEditing.value = row
  assessmentFormVisible.value = true
}

async function saveAssessment() {
  if (!assessmentRecord.value) {
    message.warning('请先选择定岗记录')
    return
  }
  if (!assessmentForm.period.trim()) {
    message.warning('请填写考核周期')
    return
  }
  if (!assessmentForm.perfLevel.trim()) {
    message.warning('请填写绩效等级')
    return
  }
  if (!assessmentForm.assessedAtTs) {
    message.warning('请选择评定日期')
    return
  }
  assessmentSaving.value = true
  const payload = {
    record: String(assessmentRecord.value),
    period: assessmentForm.period.trim(),
    score: assessmentForm.score,
    perfLevel: assessmentForm.perfLevel.trim(),
    assessedAt: toDateStr(assessmentForm.assessedAtTs),
    comment: assessmentForm.comment.trim(),
  }
  try {
    if (assessmentEditing.value) {
      await updatePlacementAssessment(assessmentEditing.value.id, payload)
      message.success('定岗考核已更新')
    } else {
      await createPlacementAssessment(payload)
      message.success('定岗考核已创建')
    }
    assessmentFormVisible.value = false
    loadAssessments()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    assessmentSaving.value = false
  }
}

async function removeAssessment(row: PlacementAssessment) {
  try {
    await deletePlacementAssessment(row.id)
    notification.create({
      content: `已删除「${row.period}」的考核`,
      duration: 8000,
      keepAliveOnHover: true,
      action: () =>
        h(NButton, {
          text: true,
          type: 'primary',
          onClick: async () => {
            try {
              await restorePlacementAssessment(row.id)
              message.success('定岗考核已恢复')
              loadAssessments()
            } catch (e: any) {
              message.error(extractError(e))
            }
          },
        }, { default: () => '撤销' }),
    })
    loadAssessments()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/* ───────────────────────── 生命周期 ───────────────────────── */

function onTabChange(tab: TabKey) {
  if (tab === 'roster') {
    loadRecords()
  } else if (tab === 'goal') {
    loadGoals()
  } else if (tab === 'metric') {
    loadMetrics()
  } else {
    loadAssessments()
  }
}

onMounted(async () => {
  await loadRecords()
  await loadGoals()
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
.page-tabs {
  flex-shrink: 0;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  flex-wrap: wrap;
}
.toolbar-search {
  width: 240px;
}
.toolbar-select-wide {
  width: 260px;
}
.spacer {
  flex: 1;
}
.table-wrap {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
.filter {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.filter-label {
  font-size: var(--text-small);
  color: var(--ink-soft);
  white-space: nowrap;
}

.error-state {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--c-error);
  border-radius: var(--radius-md);
  background: var(--c-error-soft);
  flex-shrink: 0;
}
.error-state-icon {
  color: var(--c-error-deep);
  font-size: var(--text-h4);
  flex-shrink: 0;
}
.error-state-body {
  flex: 1;
  min-width: 0;
}
.error-state-title {
  font-size: var(--text-body);
  font-weight: 600;
  color: var(--c-error-deep);
}
.error-state-desc {
  font-size: var(--text-small);
  color: var(--ink-soft);
  margin-top: var(--space-1);
}
.error-state-detail {
  margin-top: var(--space-2);
  font-size: var(--text-meta);
  color: var(--ink-soft);
}
.error-state-code {
  margin: var(--space-1) 0;
  padding: var(--space-2);
  background: var(--surface);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
