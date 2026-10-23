<template>
  <!-- 月报提交与评分：逆向清单 §4.2 `mymonthly` / `monthlyscore`。
       两个角色视图：提交（学生视角：我的月报列表 + 提交）与 评分（管理视角：待评分月报表 + 评分弹窗）。
       综合得分 = 业务导师总分 × 0.7 + 成长导师总分 × 0.3（逆向清单 A7）。 -->
  <div class="page-container">
    <div class="page-body">
      <n-tabs
        v-model:value="activeTab"
        type="line"
        display-directive="show:lazy"
        class="cmr-tabs"
        @update:value="onTabChange"
      >
        <!-- ① 提交（学生视角） -->
        <n-tab-pane name="submit" tab="月报提交">
          <div class="toolbar">
            <div class="field">
              <span class="field-label">月份</span>
              <n-select
                v-model:value="submitYm"
                :options="ymOptions"
                style="width: 180px"
                @update:value="loadSubmitList"
              />
            </div>
            <div class="spacer"></div>
            <n-button type="primary" @click="openCreate">
              <template #icon><n-icon :component="AddOutline" /></template>
              写月报
            </n-button>
          </div>

          <n-alert v-if="submitError" type="error" :show-icon="true" class="load-error">
            <div class="error-head">
              <span>月报列表没能加载出来，本次查询没有改动任何数据。</span>
              <n-button size="small" tertiary type="error" :loading="submitLoading" @click="loadSubmitList">
                重新加载
              </n-button>
            </div>
            <n-collapse v-if="submitErrorDetail" class="error-collapse">
              <n-collapse-item title="详情" name="detail">
                <div class="error-detail">
                  <code>{{ submitErrorDetail }}</code>
                  <n-button size="tiny" quaternary @click="copyDetail(submitErrorDetail)">复制错误信息</n-button>
                </div>
              </n-collapse-item>
            </n-collapse>
          </n-alert>

          <div v-if="submitLoading && !submitRows.length" class="skeleton-wrap">
            <n-skeleton :repeat="5" animated />
          </div>

          <div v-else class="table-wrap">
            <n-data-table
              :columns="submitColumns"
              :data="submitRows"
              :loading="submitLoading"
              :bordered="false"
              :pagination="pagination"
              :scroll-x="SUBMIT_SCROLL_X"
              :row-key="(row: MonthlyReportRow) => row.id"
              flex-height
            >
              <template #empty>
                <n-empty :description="submitEmptyText" />
              </template>
            </n-data-table>
          </div>
        </n-tab-pane>

        <!-- ② 评分（管理视角） -->
        <n-tab-pane name="score" tab="月报评分">
          <div class="toolbar">
            <div class="field">
              <span class="field-label">月份</span>
              <n-select
                v-model:value="scoreYm"
                :options="ymOptions"
                style="width: 180px"
                @update:value="loadScoreList"
              />
            </div>
            <n-button
              secondary
              type="primary"
              :checked="onlyPending"
              @click="onlyPending = !onlyPending; loadScoreList()"
            >
              只看待评分
            </n-button>
            <div class="spacer"></div>
            <n-button :loading="scoreLoading" @click="loadScoreList">
              <template #icon><n-icon :component="RefreshOutline" /></template>
              刷新待评分
            </n-button>
          </div>

          <n-alert v-if="scoreError" type="error" :show-icon="true" class="load-error">
            <div class="error-head">
              <span>待评分月报没能加载出来，本次查询没有改动任何数据。</span>
              <n-button size="small" tertiary type="error" :loading="scoreLoading" @click="loadScoreList">
                重新加载
              </n-button>
            </div>
            <n-collapse v-if="scoreErrorDetail" class="error-collapse">
              <n-collapse-item title="详情" name="detail">
                <div class="error-detail">
                  <code>{{ scoreErrorDetail }}</code>
                  <n-button size="tiny" quaternary @click="copyDetail(scoreErrorDetail)">复制错误信息</n-button>
                </div>
              </n-collapse-item>
            </n-collapse>
          </n-alert>

          <div v-if="scoreLoading && !scoreRows.length" class="skeleton-wrap">
            <n-skeleton :repeat="5" animated />
          </div>

          <div v-else class="table-wrap">
            <n-data-table
              :columns="scoreColumns"
              :data="scoreRows"
              :loading="scoreLoading"
              :bordered="false"
              :pagination="pagination"
              :scroll-x="SCORE_SCROLL_X"
              :row-key="(row: MonthlyReportRow) => row.id"
              flex-height
            >
              <template #empty>
                <n-empty :description="scoreEmptyText" />
              </template>
            </n-data-table>
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>

    <!-- 写月报弹窗（学生视角） -->
    <n-modal
      v-model:show="createVisible"
      preset="card"
      title="写月报"
      :style="{ width: '680px', maxWidth: '95vw' }"
      :content-style="{ height: 'min(480px, calc(88vh - 180px))', overflowY: 'auto' }"
      :mask-closable="false"
    >
      <n-form :model="createForm" label-placement="top">
        <n-form-item label="月份" required>
          <n-select v-model:value="createForm.ym" :options="ymOptions" placeholder="选择月报月份" />
        </n-form-item>
        <n-form-item label="汇报内容" required>
          <n-input
            v-model:value="createForm.comment"
            type="textarea"
            :rows="6"
            placeholder="写本月做了什么、遇到什么问题、下一步计划"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="saving" @click="createVisible = false">取消</n-button>
          <n-button type="primary" :loading="saving" :disabled="!canCreate" @click="submitCreate">
            保存草稿
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 提交确认（R-106 / R-204：写明后果，不问「是否确认」） -->
    <n-modal
      v-model:show="submitConfirmVisible"
      preset="card"
      title="提交月报"
      :style="{ width: '520px', maxWidth: '95vw' }"
      :content-style="{ height: 'min(320px, calc(88vh - 180px))', overflowY: 'auto' }"
      :mask-closable="false"
    >
      <p class="confirm-text">
        提交后「{{ pendingSubmit?.ym }}」的月报将进入待评分状态，导师评分前不能再改写。需要修改请先撤回草稿。
      </p>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="submitting" @click="submitConfirmVisible = false">继续修改</n-button>
          <n-button type="primary" :loading="submitting" @click="confirmSubmit">上报月报</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 评分弹窗（管理视角） -->
    <n-modal
      v-model:show="scoreVisible"
      preset="card"
      title="月报评分"
      :style="{ width: '820px', maxWidth: '95vw' }"
      :content-style="{ height: 'min(600px, calc(88vh - 180px))', overflowY: 'auto' }"
      :mask-closable="false"
    >
      <n-form :model="scoreForm" label-placement="top">
        <n-form-item label="评分角色" required>
          <n-radio-group v-model:value="scoreForm.role">
            <n-radio-button value="business">业务导师</n-radio-button>
            <n-radio-button value="growth">成长导师</n-radio-button>
          </n-radio-group>
        </n-form-item>

        <n-grid :cols="3" :x-gap="16" responsive="screen" :item-responsive="true">
          <n-grid-item v-for="item in subItems" :key="item.key" span="3 s:1">
            <n-form-item :label="item.label">
              <n-input-number
                v-model:value="scoreForm.sub[item.key]"
                :min="0"
                :max="100"
                :step="1"
                style="width: 100%"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-form-item label="评语">
          <n-input
            v-model:value="scoreForm.comment"
            type="textarea"
            :rows="3"
            placeholder="写给校招生的评语（可留空）"
          />
        </n-form-item>
      </n-form>

      <!-- 实时得分：业务导师分 / 成长导师分 / 综合分（A7） -->
      <div class="score-preview">
        <div class="score-item">
          <span class="score-label">业务导师分</span>
          <span class="score-value">{{ previewBusiness }}</span>
        </div>
        <div class="score-item">
          <span class="score-label">成长导师分</span>
          <span class="score-value">{{ previewGrowth }}</span>
        </div>
        <div class="score-item">
          <span class="score-label">综合分</span>
          <span class="score-value score-final">{{ previewFinal }}</span>
        </div>
        <div class="score-tip">综合分 = 业务导师分 × 0.7 + 成长导师分 × 0.3</div>
      </div>

      <template #footer>
        <n-space justify="end">
          <n-button :disabled="scoring" @click="scoreVisible = false">取消评分</n-button>
          <n-button type="primary" :loading="scoring" @click="submitScore">保存评分</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCollapse,
  NCollapseItem,
  NDataTable,
  NEmpty,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NIcon,
  NInput,
  NInputNumber,
  NModal,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSkeleton,
  NSpace,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
} from 'naive-ui'
import { AddOutline, RefreshOutline } from '@vicons/ionicons5'
import {
  createMonthlyReport,
  listMonthlyReports,
  scoreMonthlyReport,
  submitMonthlyReport,
  REPORT_STATUS_LABEL,
  REPORT_SUB_ITEMS,
  type MonthlyReportRow,
} from '../../api/campusAssessment'
import { extractError } from '../../utils/campus'

type ReportTab = 'submit' | 'score'

/** 列表分页（R-108：渲染条目 > 200 必须分页；R-215：分页器固定在表格底部，naive 分页器即表格区最后一个子节点）。 */
const pagination = { pageSize: 50, showSizePicker: false }

const message = useMessage()
const activeTab = ref<ReportTab>('submit')

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

/* ────────────────────────── 提交视图 ────────────────────────── */

const submitRows = ref<MonthlyReportRow[]>([])
const submitLoading = ref(false)
const submitError = ref('')
const submitErrorDetail = ref('')
const submitYm = ref('')

const submitEmptyText = computed(() =>
  submitYm.value ? '该月份没有月报记录，换个月份或先写一份月报' : '暂无月报记录',
)

async function loadSubmitList() {
  submitLoading.value = true
  submitError.value = ''
  submitErrorDetail.value = ''
  try {
    submitRows.value = await listMonthlyReports(submitYm.value ? { ym: submitYm.value } : undefined)
  } catch (e: any) {
    submitError.value = extractError(e)
    submitErrorDetail.value = String(e?.message ?? e)
  } finally {
    submitLoading.value = false
  }
}

const submitColumns = [
  { title: '月份', key: 'ym', width: 100 },
  { title: '校招生', key: 'personName', width: 120, ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: any) =>
      h(
        NTag,
        { type: row.status === 'scored' ? 'success' : row.status === 'submitted' ? 'info' : 'warning', size: 'small', bordered: false },
        { default: () => REPORT_STATUS_LABEL[row.status] || row.status || '—' },
      ),
  },
  { title: '提交时间', key: 'submittedAt', width: 160, render: (row: any) => row.submittedAt || '—' },
  { title: '业务导师分', key: 'businessScore', width: 110, render: (row: any) => fmtScore(row.businessScore) },
  { title: '成长导师分', key: 'growthScore', width: 110, render: (row: any) => fmtScore(row.growthScore) },
  { title: '综合分', key: 'finalScore', width: 100, render: (row: any) => fmtScore(row.finalScore) },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    fixed: 'right' as const,
    render: (row: any) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(
            NButton,
            {
              size: 'small',
              quaternary: true,
              type: 'primary',
              disabled: row.status !== 'draft',
              onClick: () => askSubmit(row),
            },
            { default: () => '上报月报' },
          ),
        ],
      }),
  },
]
const SUBMIT_SCROLL_X = 910

/* ── 写月报 / 提交月报 ── */

const createVisible = ref(false)
const saving = ref(false)
const createForm = reactive({ ym: '', comment: '' })
const canCreate = computed(() => !!createForm.ym && !!createForm.comment.trim() && !saving.value)

function openCreate() {
  createForm.ym = submitYm.value || ymOptions.value[0]?.value || ''
  createForm.comment = ''
  createVisible.value = true
}

async function submitCreate() {
  if (!canCreate.value) return
  saving.value = true
  try {
    await createMonthlyReport({ ym: createForm.ym, comment: createForm.comment.trim() })
    message.success('月报草稿已保存')
    createVisible.value = false
    await loadSubmitList()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    saving.value = false
  }
}

const submitConfirmVisible = ref(false)
const pendingSubmit = ref<MonthlyReportRow | null>(null)
const submitting = ref(false)

function askSubmit(row: MonthlyReportRow) {
  pendingSubmit.value = row
  submitConfirmVisible.value = true
}

async function confirmSubmit() {
  if (!pendingSubmit.value || submitting.value) return
  submitting.value = true
  try {
    await submitMonthlyReport(pendingSubmit.value.id)
    message.success(`「${pendingSubmit.value.ym}」的月报已提交`)
    submitConfirmVisible.value = false
    await loadSubmitList()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    submitting.value = false
  }
}

/* ────────────────────────── 评分视图 ────────────────────────── */

const scoreRows = ref<MonthlyReportRow[]>([])
const scoreLoading = ref(false)
const scoreError = ref('')
const scoreErrorDetail = ref('')
const scoreYm = ref('')
const onlyPending = ref(true)

const scoreEmptyText = computed(() =>
  scoreYm.value ? '该月份没有待评分月报，换个月份再看看' : '暂无待评分月报',
)

async function loadScoreList() {
  scoreLoading.value = true
  scoreError.value = ''
  scoreErrorDetail.value = ''
  try {
    scoreRows.value = await listMonthlyReports({
      ...(scoreYm.value ? { ym: scoreYm.value } : {}),
      ...(onlyPending.value ? { status: 'submitted' } : {}),
    })
  } catch (e: any) {
    scoreError.value = extractError(e)
    scoreErrorDetail.value = String(e?.message ?? e)
  } finally {
    scoreLoading.value = false
  }
}

const scoreColumns = [
  { title: '月份', key: 'ym', width: 100 },
  { title: '校招生', key: 'personName', width: 120, ellipsis: { tooltip: true } },
  { title: '班级', key: 'classRoomName', width: 140, ellipsis: { tooltip: true } },
  { title: '提交时间', key: 'submittedAt', width: 160, render: (row: any) => row.submittedAt || '—' },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: any) =>
      h(
        NTag,
        { type: row.status === 'scored' ? 'success' : 'info', size: 'small', bordered: false },
        { default: () => REPORT_STATUS_LABEL[row.status] || row.status || '—' },
      ),
  },
  { title: '业务导师分', key: 'businessScore', width: 110, render: (row: any) => fmtScore(row.businessScore) },
  { title: '成长导师分', key: 'growthScore', width: 110, render: (row: any) => fmtScore(row.growthScore) },
  { title: '综合分', key: 'finalScore', width: 100, render: (row: any) => fmtScore(row.finalScore) },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    fixed: 'right' as const,
    render: (row: any) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(
            NButton,
            { size: 'small', quaternary: true, type: 'primary', onClick: () => openScore(row) },
            { default: () => '月报评分' },
          ),
        ],
      }),
  },
]
const SCORE_SCROLL_X = 1040

/* ── 评分弹窗 ── */

const scoreVisible = ref(false)
const scoring = ref(false)
const scoringRow = ref<MonthlyReportRow | null>(null)
const subItems = REPORT_SUB_ITEMS

const emptySub = (): Record<string, number | null> => ({
  case: null,
  insight: null,
  problem: null,
  clarity: null,
  executable: null,
})
const scoreForm = reactive<{ role: 'business' | 'growth'; sub: Record<string, number | null>; comment: string }>({
  role: 'business',
  sub: emptySub(),
  comment: '',
})

/** 当前弹窗所评角色的 5 子项之和。 */
const currentSubTotal = computed(() =>
  subItems.reduce((sum, it) => sum + Number(scoreForm.sub[it.key] ?? 0), 0),
)
/** 业务导师分：正在评业务角色时用当前输入，否则用月报上的既有分。 */
const previewBusiness = computed(() =>
  scoreForm.role === 'business' ? currentSubTotal.value : Number(scoringRow.value?.businessScore ?? 0),
)
/** 成长导师分。 */
const previewGrowth = computed(() =>
  scoreForm.role === 'growth' ? currentSubTotal.value : Number(scoringRow.value?.growthScore ?? 0),
)
/** 综合分 = 业务 × 0.7 + 成长 × 0.3（逆向清单 A7，保留 1 位）。 */
const previewFinal = computed(
  () => Math.round((previewBusiness.value * 0.7 + previewGrowth.value * 0.3) * 10) / 10,
)

function openScore(row: MonthlyReportRow) {
  scoringRow.value = row
  scoreForm.role = 'business'
  scoreForm.sub = emptySub()
  scoreForm.comment = ''
  scoreVisible.value = true
}

async function submitScore() {
  if (!scoringRow.value || scoring.value) return
  scoring.value = true
  try {
    await scoreMonthlyReport(scoringRow.value.id, {
      role: scoreForm.role,
      case: Number(scoreForm.sub.case ?? 0),
      insight: Number(scoreForm.sub.insight ?? 0),
      problem: Number(scoreForm.sub.problem ?? 0),
      clarity: Number(scoreForm.sub.clarity ?? 0),
      executable: Number(scoreForm.sub.executable ?? 0),
      comment: scoreForm.comment.trim(),
    })
    message.success('月报评分已保存')
    scoreVisible.value = false
    await loadScoreList()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    scoring.value = false
  }
}

/* ────────────────────────── 通用 ────────────────────────── */

/** 分数展示：0 分与「未评分」区分（后端 0 与 null 不同义）。 */
function fmtScore(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  return String(v)
}

function onTabChange(tab: ReportTab) {
  if (tab === 'score' && !scoreRows.value.length) loadScoreList()
}

async function copyDetail(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    message.success('已复制错误信息')
  } catch {
    message.warning('浏览器不允许复制，请手动选中详情文本')
  }
}

onMounted(() => {
  submitYm.value = ymOptions.value[0]?.value ?? ''
  scoreYm.value = submitYm.value
  loadSubmitList()
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
.cmr-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.cmr-tabs :deep(.n-tabs-pane-wrapper) {
  flex: 1;
  min-height: 0;
}
.cmr-tabs :deep(.n-tab-pane) {
  box-sizing: border-box;
  height: 100%;
  padding: var(--space-2) 0 0 0;
  display: flex;
  flex-direction: column;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  padding-bottom: var(--space-2);
}
.field {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
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
.confirm-text {
  margin: 0;
  font-size: var(--text-body);
  line-height: 1.6;
  color: var(--ink);
  overflow-wrap: anywhere;
}
/* 实时得分面板 */
.score-preview {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  flex-wrap: wrap;
  margin-top: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--surface);
}
.score-item {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}
.score-label {
  font-size: var(--text-small);
  color: var(--ink-soft);
}
.score-value {
  font-size: var(--text-h3);
  font-weight: 600;
  line-height: 1.3;
  font-variant-numeric: tabular-nums;
}
.score-final {
  color: var(--brand-fg);
}
.score-tip {
  font-size: var(--text-meta);
  color: var(--ink-faint);
  margin-left: auto;
}
/* 动态数字防抖动（作用于 naive 自身 DOM，不涉及 h() 渲染节点） */
.table-wrap :deep(.n-data-table-td) {
  font-variant-numeric: tabular-nums;
}
</style>
