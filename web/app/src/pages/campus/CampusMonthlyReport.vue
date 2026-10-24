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
                aria-label="月份"
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
                aria-label="月份"
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
      <!-- 草稿恢复提示（R-105）：提供「清空」出口 -->
      <n-alert v-if="createDraftRestored" type="info" :show-icon="true" class="draft-tip">
        <div class="error-head">
          <span>已恢复上次填写的内容</span>
          <n-button size="small" quaternary @click="clearCreateDraft">清空草稿</n-button>
        </div>
      </n-alert>
      <!-- 写入失败三段式（R-203）：人话标题 + 数据是否安全 + 可复制技术详情 -->
      <n-alert v-if="createWriteErr" type="error" :show-icon="true" class="write-error">
        <div class="error-head">
          <span class="error-title">{{ createWriteErr.title }}</span>
        </div>
        <p class="error-safe">{{ createWriteErr.safe }}</p>
        <n-collapse class="error-collapse">
          <n-collapse-item title="详情" name="create-detail">
            <div class="error-detail">
              <code>{{ createWriteErr.detail }}</code>
              <n-button size="tiny" quaternary @click="copyDetail(createWriteErr.detail)">复制错误信息</n-button>
            </div>
          </n-collapse-item>
        </n-collapse>
      </n-alert>
      <n-form :model="createForm" label-placement="top">
        <n-form-item
          label="月份"
          required
          :show-feedback="!!createYmError"
          :validation-status="createYmError ? 'error' : undefined"
        >
          <n-select
            ref="createYmRef"
            v-model:value="createForm.ym"
            :options="ymOptions"
            placeholder="选择月报月份"
          />
          <template #feedback>
            <span v-if="createYmError" class="field-error">
              <n-icon :component="AlertCircleOutline" aria-hidden="true" />{{ createYmError }}
            </span>
          </template>
        </n-form-item>
        <n-form-item
          label="汇报内容"
          required
          :show-feedback="!!createCommentError"
          :validation-status="createCommentError ? 'error' : undefined"
        >
          <n-input
            ref="createCommentRef"
            v-model:value="createForm.comment"
            type="textarea"
            :rows="6"
            placeholder="写本月做了什么、遇到什么问题、下一步计划"
          />
          <template #feedback>
            <span v-if="createCommentError" class="field-error">
              <n-icon :component="AlertCircleOutline" aria-hidden="true" />{{ createCommentError }}
            </span>
          </template>
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="saving" @click="createVisible = false">取消月报</n-button>
          <n-button type="primary" :loading="saving" :disabled="saving" @click="submitCreate">
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
      <!-- 写入失败三段式（R-203） -->
      <n-alert v-if="submitWriteErr" type="error" :show-icon="true" class="write-error">
        <div class="error-head">
          <span class="error-title">{{ submitWriteErr.title }}</span>
        </div>
        <p class="error-safe">{{ submitWriteErr.safe }}</p>
        <n-collapse class="error-collapse">
          <n-collapse-item title="详情" name="submit-detail">
            <div class="error-detail">
              <code>{{ submitWriteErr.detail }}</code>
              <n-button size="tiny" quaternary @click="copyDetail(submitWriteErr.detail)">复制错误信息</n-button>
            </div>
          </n-collapse-item>
        </n-collapse>
      </n-alert>
      <p class="confirm-text">
        提交后「{{ pendingSubmit?.ym }}」的月报将进入待评分状态，导师评分前不能再改写。需要修改请先撤回草稿。
      </p>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="submitting" @click="submitConfirmVisible = false">继续修改</n-button>
          <n-button type="primary" :loading="submitting" :disabled="submitting" @click="confirmSubmit">上报月报</n-button>
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
      <!-- 草稿恢复提示（R-105）：提供「清空」出口 -->
      <n-alert v-if="scoreDraftRestored" type="info" :show-icon="true" class="draft-tip">
        <div class="error-head">
          <span>已恢复上次填写的内容</span>
          <n-button size="small" quaternary @click="clearScoreDraft(scoringRow?.id ?? '')">清空草稿</n-button>
        </div>
      </n-alert>
      <!-- 写入失败三段式（R-203） -->
      <n-alert v-if="scoreWriteErr" type="error" :show-icon="true" class="write-error">
        <div class="error-head">
          <span class="error-title">{{ scoreWriteErr.title }}</span>
        </div>
        <p class="error-safe">{{ scoreWriteErr.safe }}</p>
        <n-collapse class="error-collapse">
          <n-collapse-item title="详情" name="score-detail">
            <div class="error-detail">
              <code>{{ scoreWriteErr.detail }}</code>
              <n-button size="tiny" quaternary @click="copyDetail(scoreWriteErr.detail)">复制错误信息</n-button>
            </div>
          </n-collapse-item>
        </n-collapse>
      </n-alert>
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
          <n-button type="primary" :loading="scoring" :disabled="scoring" @click="submitScore">保存评分</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, watch } from 'vue'
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
import { AddOutline, AlertCircleOutline, RefreshOutline } from '@vicons/ionicons5'
import {
  createMonthlyReport,
  listMonthlyReports,
  scoreMonthlyReport,
  submitMonthlyReport,
  REPORT_STATUS_LABEL,
  REPORT_SUB_ITEMS,
  type MonthlyReportRow,
} from '../../api/campusAssessment'
import { buildWriteError, extractError, type WriteErrorInfo } from '../../utils/campus'
import { useFormDraft } from '../../composables/useFormDraft'

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

/**
 * 草稿自动保存（R-105）：写月报要人工撰写汇报内容，填写时长 > 1 分钟 → 接草稿。
 * 命名空间按「页面-表单」唯一：campus-monthly-report-create。
 */
const createDraft = useFormDraft('campus-monthly-report-create', createForm)

/** 写入失败三段式（R-203）：标题 + 数据是否安全 + 可复制详情。 */
const createWriteErr = ref<WriteErrorInfo | null>(null)
const submitWriteErr = ref<WriteErrorInfo | null>(null)
const scoreWriteErr = ref<WriteErrorInfo | null>(null)

/** 草稿恢复提示（R-105）：naive 的 message 没有 action 槽位，「清空」出口用页内提示承载。 */
const createDraftRestored = ref(false)
const scoreDraftRestored = ref(false)

/** 字段级校验（R-221）：未通过校验的字段就近显示「图标 + 文字」双通道反馈。 */
const createAttempted = ref(false)
const createYmRef = ref<any>(null)
const createCommentRef = ref<any>(null)
const createYmError = computed(() =>
  createAttempted.value && !createForm.ym ? '请选择月报月份' : '',
)
const createCommentError = computed(() =>
  createAttempted.value && !createForm.comment.trim() ? '请填写汇报内容' : '',
)
const canCreate = computed(() => !!createForm.ym && !!createForm.comment.trim() && !saving.value)

/** 聚焦到第一个出错的字段（R-221）。 */
function focusFirstCreateError() {
  const target = createYmError.value ? createYmRef.value : createCommentRef.value
  target?.focus?.()
}

function openCreate() {
  createForm.ym = submitYm.value || ymOptions.value[0]?.value || ''
  createForm.comment = ''
  createAttempted.value = false
  createWriteErr.value = null
  createDraftRestored.value = false
  createVisible.value = true
  // 草稿恢复（R-105）：有未过期草稿才提示，并给「清空」出口
  const before = { ...createForm }
  if (createDraft.probe()) {
    createDraft.restore()
    if (createForm.comment !== before.comment || createForm.ym !== before.ym) {
      createDraftRestored.value = true
      message.info('已恢复上次填写的内容')
    }
  }
}

/** 清空草稿出口（R-105）：丢弃已恢复的内容，草稿不再落盘。 */
function clearCreateDraft() {
  createDraft.clear()
  createDraftRestored.value = false
  createForm.comment = ''
  message.success('已清空草稿')
}

async function submitCreate() {
  createAttempted.value = true
  if (createYmError.value || createCommentError.value) {
    focusFirstCreateError()
    return
  }
  if (!canCreate.value) return
  saving.value = true
  createWriteErr.value = null
  try {
    await createMonthlyReport({ ym: createForm.ym, comment: createForm.comment.trim() })
    message.success('月报草稿已保存')
    // R-105：提交成功后立即清除草稿
    createDraft.clear()
    createVisible.value = false
    await loadSubmitList()
  } catch (e: any) {
    // R-203：写入失败三段式（数据仍留在表单里，可直接重试）
    createWriteErr.value = buildWriteError(e, { action: '保存月报草稿' })
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
  submitWriteErr.value = null
  try {
    await submitMonthlyReport(pendingSubmit.value.id)
    message.success(`「${pendingSubmit.value.ym}」的月报已提交`)
    submitConfirmVisible.value = false
    await loadSubmitList()
  } catch (e: any) {
    // R-203：写入失败三段式
    submitWriteErr.value = buildWriteError(e, { action: '上报月报' })
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
      // ⚠️ 「待评分」**不能用 status=submitted 表达**：契约 §2.2 规定「评分落库即置 scored」，
      //    只评了业务导师的月报状态已是 scored，但成长导师仍待评 —— 按 status 过滤会把
      //    这些项从待评分列表里筛掉。后端 `?pending=1` 的口径 = 两个角色都有评分明细才算评完。
      ...(onlyPending.value ? { pending: '1' } : {}),
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

/**
 * 评分草稿仓库（R-105）：key = 月报 id，value = 该月报的评分表单快照。
 * ⚠️ 按月报 id 分桶，避免把 A 月报的分数灌进 B 月报（草稿覆盖真实 row 数据）。
 */
interface ScoreDraftSnapshot {
  role: 'business' | 'growth'
  sub: Record<string, number | null>
  comment: string
}
const scoreDraftStore = reactive<Record<string, ScoreDraftSnapshot>>({})
/** 命名空间按「页面-表单」唯一：campus-monthly-report-score。 */
const scoreDraft = useFormDraft('campus-monthly-report-score', scoreDraftStore as Record<string, unknown>)

/** 表单变化即写入草稿仓库（由 composable 统一 debounce 800ms 落盘）。 */
watch(
  scoreForm,
  () => {
    const id = scoringRow.value?.id
    if (!id) return
    scoreDraftStore[id] = {
      role: scoreForm.role,
      sub: { ...scoreForm.sub },
      comment: scoreForm.comment,
    }
  },
  { deep: true },
)

/** 清掉某份月报的评分草稿（「已恢复」提示里的「清空」出口）。 */
function clearScoreDraft(id: string) {
  delete scoreDraftStore[id]
  scoreDraftRestored.value = false
  scoreForm.comment = ''
  message.success('已清空草稿')
}

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
  scoreWriteErr.value = null
  scoreDraftRestored.value = false
  // 草稿恢复（R-105）：只取回同一份月报的草稿，别的月报的草稿不灌进来
  if (scoreDraft.probe()) {
    scoreDraft.restore()
    const saved = scoreDraftStore[row.id]
    if (saved) {
      scoreForm.role = saved.role
      scoreForm.sub = { ...saved.sub }
      scoreForm.comment = saved.comment
      scoreDraftRestored.value = true
      message.info('已恢复上次填写的内容')
    }
  }
}

async function submitScore() {
  if (!scoringRow.value || scoring.value) return
  scoring.value = true
  scoreWriteErr.value = null
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
    // R-105：提交成功后立即清除草稿
    clearScoreDraft(scoringRow.value.id)
    scoreDraft.clear()
    scoreVisible.value = false
    await loadScoreList()
  } catch (e: any) {
    // R-203：写入失败三段式
    scoreWriteErr.value = buildWriteError(e, { action: '保存月报评分' })
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
.toolbar :deep(.n-base-selection) {
  max-width: 100%;
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
/* 写入失败三段式（R-203）：标题 + 数据安全说明 + 折叠详情 */
.write-error {
  margin-bottom: var(--space-2);
}
/* 草稿恢复提示（R-105）：带「清空」出口 */
.draft-tip {
  margin-bottom: var(--space-2);
}
.error-title {
  font-weight: 600;
}
.error-safe {
  margin: var(--space-1) 0 0;
  font-size: var(--text-small);
  color: var(--ink-soft);
  overflow-wrap: anywhere;
}
/* 字段级校验反馈（R-221）：图标 + 文字双通道，不只靠颜色 */
.field-error {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--c-error-deep);
  font-size: var(--text-small);
  line-height: 1.5;
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
