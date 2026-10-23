<template>
  <div class="page-container">
    <div class="page-body">
      <n-tabs v-model:value="activeTab" type="line" class="page-tabs" @update:value="onTabChange">
        <n-tab-pane name="list" tab="考试管理" />
        <n-tab-pane name="rank" tab="成绩排名" />
      </n-tabs>

      <!-- ① 考试管理 -->
      <template v-if="activeTab === 'list'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">考试</span>
            <n-input
              v-model:value="examSearch"
              aria-label="考试名称"
              class="toolbar-search"
              placeholder="搜索考试名称"
              clearable
              @keyup.enter="loadExams"
            >
              <template #prefix><n-icon :component="SearchOutline" /></template>
            </n-input>
          </div>
          <div class="filter">
            <span class="filter-label">形式</span>
            <n-select
              v-model:value="examFormFilter"
              aria-label="考试形式"
              class="toolbar-select"
              :options="examFormOptions"
              placeholder="全部形式"
              clearable
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="examLoading" @click="loadExams">查询考试</n-button>
          <n-button type="primary" @click="openExamCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增考试
          </n-button>
        </div>

        <div v-if="examError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">考试列表没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，你填的考试信息仍保留在本页，不会丢失。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ examError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(examError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="examLoading" @click="loadExams">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="examLoading && !examRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="examColumns"
            :data="examRows"
            :loading="examLoading"
            :bordered="false"
            :scroll-x="EXAM_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: Exam) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="examEmptyText" size="small">
                <template #extra>
                  <n-button v-if="examHasFilter" size="small" @click="clearExamFilter">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ② 成绩排名 -->
      <template v-if="activeTab === 'rank'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">考试</span>
            <n-select
              v-model:value="rankExamId"
              aria-label="考试"
              class="toolbar-select-wide"
              :options="examOptions"
              placeholder="请选择考试"
              clearable
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="rankLoading" :disabled="!rankExamId" @click="loadRanking">刷新排名</n-button>
          <n-button type="primary" :disabled="!rankExamId" @click="openScoreCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            录入成绩
          </n-button>
        </div>

        <div v-if="rankError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">成绩排名没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，已录入的成绩仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ rankError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(rankError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="rankLoading" @click="loadRanking">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="rankLoading && !rankRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="rankColumns"
            :data="rankRows"
            :loading="rankLoading"
            :bordered="false"
            :scroll-x="RANK_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: ExamRankingRow) => row.person || String(row.rank)"
            flex-height
          >
            <template #empty>
              <n-empty :description="rankEmptyText" size="small">
                <template #extra>
                  <n-button v-if="rankExamId" size="small" @click="rankExamId = null">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- 考试 新增 / 编辑 弹窗 -->
      <n-modal
        v-model:show="examFormVisible"
        preset="card"
        :title="examEditing ? '编辑考试' : '新增考试'"
        :style="{ width: '720px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(560px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="examForm" label-placement="top">
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="考试名称" required>
                <n-input v-model:value="examForm.name" placeholder="请输入考试名称" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="考试日期" required>
                <n-date-picker v-model:value="examForm.dateTs" type="date" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="考试形式" required>
                <n-select v-model:value="examForm.form" :options="examFormOptions" placeholder="请选择考试形式" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="关联课程">
                <n-select v-model:value="examForm.course" :options="courseOptions" placeholder="不关联课程" clearable />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="满分" required>
                <n-input-number v-model:value="examForm.fullScore" :min="1" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="及格分" required>
                <n-input-number v-model:value="examForm.passScore" :min="0" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="启用考试">
                <n-switch v-model:value="examForm.enabled">
                  <template #checked>已启用</template>
                  <template #unchecked>已停用</template>
                </n-switch>
              </n-form-item>
            </n-grid-item>
          </n-grid>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="examFormVisible = false">取消</n-button>
            <n-button type="primary" :loading="examSaving" :disabled="examSaving" @click="saveExam">保存考试</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 成绩录入 弹窗 -->
      <n-modal
        v-model:show="scoreFormVisible"
        preset="card"
        title="录入成绩"
        :style="{ width: '620px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(460px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="scoreForm" label-placement="top">
          <n-form-item label="考试" required>
            <n-select v-model:value="scoreForm.exam" :options="examOptions" placeholder="请选择考试" />
          </n-form-item>
          <n-form-item label="校招生" required>
            <n-select
              v-model:value="scoreForm.person"
              :options="personOptions"
              placeholder="搜索并选择校招生"
              clearable
              filterable
              remote
              :loading="personLoading"
              :on-search="onPersonSearch"
            />
          </n-form-item>
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="得分" required>
                <n-input-number v-model:value="scoreForm.score" :min="0" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="及格分">
                <n-input :value="scorePassScore" readonly placeholder="选择考试后自动带出" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-form-item label="备注">
            <n-input v-model:value="scoreForm.remark" type="textarea" placeholder="如 补考 / 缺考说明" />
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="scoreFormVisible = false">取消</n-button>
            <n-button type="primary" :loading="scoreSaving" :disabled="scoreSaving" @click="saveScore">保存成绩</n-button>
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
  NSwitch,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
  useNotification,
} from 'naive-ui'
import { AddOutline, AlertCircleOutline, BarChartOutline, CreateOutline, SearchOutline, TrashOutline } from '@vicons/ionicons5'
import {
  createExam,
  createExamScore,
  deleteExam,
  getExamRanking,
  listCourses,
  listExams,
  restoreExam,
  updateExam,
  type Course,
  type Exam,
  type ExamRankingRow,
} from '../../api/campusLearning'
import { extractError, searchPersons, type SelectOption } from '../../utils/campus'

const message = useMessage()
const notification = useNotification()

type TabKey = 'list' | 'rank'
const activeTab = ref<TabKey>('list')

const EXAM_FORM_VALUES = ['线上', '线下']
const examFormOptions = EXAM_FORM_VALUES.map((v) => ({ label: v, value: v }))

/* ───────────────────────── 通用工具 ───────────────────────── */

/**
 * 得分条：用**内联样式**渲染。
 * ⚠️ h() 造出的 VNode 不带 data-v-*，scoped 规则不命中（AGENTS.md R-225）。
 */
function scoreBar(percent: number, color: string) {
  const p = Math.max(0, Math.min(100, Number(percent) || 0))
  return h('div', {
    style: {
      width: '100%',
      height: 'var(--fs-10)',
      background: 'var(--g1)',
      borderRadius: 'var(--radius-pill)',
      overflow: 'hidden',
    },
  }, [h('div', { style: { width: `${p}%`, height: '100%', background: color } })])
}

function textCell(text: unknown, width = 140) {
  const s = text == null || text === '' ? '—' : String(text)
  return h('span', { title: s, style: { display: 'inline-block', maxWidth: `${width}px`, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, s)
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

/* ───────────────────────── ① 考试管理 ───────────────────────── */

const examRows = ref<Exam[]>([])
const examLoading = ref(false)
const examError = ref('')
const examSearch = ref('')
const examFormFilter = ref<string | null>(null)
const courseRows = ref<Course[]>([])

const examHasFilter = computed(() => Boolean(examSearch.value.trim() || examFormFilter.value))
const examEmptyText = computed(() => (examHasFilter.value ? '没有符合筛选条件的考试' : '暂无数据'))

const examOptions = computed(() =>
  examRows.value.map((e) => ({ label: e.name || `考试 ${e.id}`, value: String(e.id) })),
)
const courseOptions = computed(() =>
  courseRows.value.map((c) => ({ label: c.name || c.code || String(c.id), value: String(c.id) })),
)

async function loadExams() {
  examLoading.value = true
  examError.value = ''
  try {
    const kw = examSearch.value.trim()
    const rows = await listExams({ search: kw || undefined })
    examRows.value = kw
      ? rows.filter((r) => String(r.name || '').includes(kw))
      : examFormFilter.value
        ? rows.filter((r) => r.form === examFormFilter.value)
        : rows
  } catch (e: any) {
    examError.value = extractError(e)
    examRows.value = []
  } finally {
    examLoading.value = false
  }
}

function clearExamFilter() {
  examSearch.value = ''
  examFormFilter.value = null
  loadExams()
}

const examColumns = computed(() => [
  { title: '考试', key: 'name', width: 200, ellipsis: true, render: (row: Exam) => textCell(row.name, 180) },
  { title: '日期', key: 'date', width: 120, render: (row: Exam) => row.date || '—' },
  { title: '形式', key: 'form', width: 90, render: (row: Exam) => row.form || '—' },
  { title: '满分', key: 'fullScore', width: 90, render: (row: Exam) => h('span', { style: { fontVariantNumeric: 'tabular-nums' } }, String(row.fullScore ?? '—')) },
  { title: '及格分', key: 'passScore', width: 90, render: (row: Exam) => h('span', { style: { fontVariantNumeric: 'tabular-nums' } }, String(row.passScore ?? '—')) },
  { title: '关联课程', key: 'courseName', width: 160, ellipsis: true, render: (row: Exam) => textCell(row.courseName, 140) },
  {
    title: '状态',
    key: 'enabled',
    width: 90,
    render: (row: Exam) =>
      h(NTag, { type: row.enabled ? 'success' : 'default', size: 'small' }, {
        default: () => (row.enabled ? '已启用' : '已停用'),
      }),
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    fixed: 'right' as const,
    render: (row: Exam) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => showRanking(row) }, {
            default: () => '查看排名',
            icon: () => h(NIcon, null, { default: () => h(BarChartOutline) }),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openExamEdit(row) }, {
            default: () => '编辑考试',
            icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeExam(row) }, {
            default: () => '删除考试',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          }),
        ],
      }),
  },
])

const EXAM_SCROLL_X = 1040

/* ── 考试 新增 / 编辑 ── */
const examFormVisible = ref(false)
const examSaving = ref(false)
const examEditing = ref<Exam | null>(null)
const examForm = reactive({
  name: '',
  dateTs: null as number | null,
  form: '线上',
  fullScore: 100,
  passScore: 60,
  course: null as string | null,
  enabled: true,
})

function toDateStr(ts: number | null) {
  if (!ts) return undefined
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function openExamCreate() {
  Object.assign(examForm, {
    name: '',
    dateTs: Date.now(),
    form: '线上',
    fullScore: 100,
    passScore: 60,
    course: null,
    enabled: true,
  })
  examEditing.value = null
  examFormVisible.value = true
}

function openExamEdit(row: Exam) {
  Object.assign(examForm, {
    name: row.name || '',
    dateTs: row.date ? new Date(row.date).getTime() : null,
    form: row.form || '线上',
    fullScore: row.fullScore ?? 100,
    passScore: row.passScore ?? 60,
    course: row.course ? String(row.course) : null,
    enabled: row.enabled !== false,
  })
  examEditing.value = row
  examFormVisible.value = true
}

async function saveExam() {
  if (!examForm.name.trim()) {
    message.warning('请填写考试名称')
    return
  }
  if (!examForm.dateTs) {
    message.warning('请选择考试日期')
    return
  }
  examSaving.value = true
  const payload = {
    name: examForm.name.trim(),
    date: toDateStr(examForm.dateTs),
    form: examForm.form,
    fullScore: examForm.fullScore,
    passScore: examForm.passScore,
    course: examForm.course,
    enabled: examForm.enabled,
  }
  try {
    if (examEditing.value) {
      await updateExam(examEditing.value.id, payload)
      message.success('考试已更新')
    } else {
      await createExam(payload)
      message.success('考试已创建')
    }
    examFormVisible.value = false
    loadExams()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    examSaving.value = false
  }
}

/** 删除单条考试 = 中等破坏性操作 → 直接执行 + 通知撤销（R-106）。 */
async function removeExam(row: Exam) {
  try {
    await deleteExam(row.id)
    notification.create({
      content: `已删除「${row.name}」`,
      duration: 8000,
      keepAliveOnHover: true,
      action: () =>
        h(NButton, {
          text: true,
          type: 'primary',
          onClick: async () => {
            try {
              await restoreExam(row.id)
              message.success('考试已恢复')
              loadExams()
            } catch (e: any) {
              message.error(extractError(e))
            }
          },
        }, { default: () => '撤销' }),
    })
    loadExams()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/* ───────────────────────── ② 成绩排名 ───────────────────────── */

const rankRows = ref<ExamRankingRow[]>([])
const rankLoading = ref(false)
const rankError = ref('')
const rankExamId = ref<string | null>(null)

const rankEmptyText = computed(() =>
  rankExamId.value ? '该考试还没有成绩记录' : '请先选择一场考试查看排名',
)

async function loadRanking() {
  if (!rankExamId.value) {
    rankRows.value = []
    return
  }
  rankLoading.value = true
  rankError.value = ''
  try {
    rankRows.value = await getExamRanking(rankExamId.value)
  } catch (e: any) {
    rankError.value = extractError(e)
    rankRows.value = []
  } finally {
    rankLoading.value = false
  }
}

function showRanking(row: Exam) {
  rankExamId.value = String(row.id)
  activeTab.value = 'rank'
  loadRanking()
}

const rankColumns = computed(() => [
  { title: '排名', key: 'rank', width: 80, render: (row: ExamRankingRow) => row.rank },
  { title: '校招生', key: 'personName', width: 140, ellipsis: true, render: (row: ExamRankingRow) => textCell(row.personName, 120) },
  { title: '班级', key: 'className', width: 150, ellipsis: true, render: (row: ExamRankingRow) => textCell(row.className, 130) },
  { title: '得分', key: 'score', width: 100, render: (row: ExamRankingRow) => h('span', { style: { fontVariantNumeric: 'tabular-nums' } }, String(row.score ?? '—')) },
  {
    title: '结果',
    key: 'passed',
    width: 110,
    render: (row: ExamRankingRow) =>
      h(NTag, { type: row.passed ? 'success' : 'error', size: 'small' }, {
        default: () => (row.passed ? '通过' : '未通过'),
      }),
  },
  { title: '得分条', key: 'percent', width: 200, render: (row: ExamRankingRow) => scoreBar(row.percent, row.passed ? 'var(--c-success)' : 'var(--c-error)') },
])

const RANK_SCROLL_X = 780

/* ── 成绩录入 ── */
const scoreFormVisible = ref(false)
const scoreSaving = ref(false)
const personOptions = ref<SelectOption[]>([])
const personLoading = ref(false)
const scoreForm = reactive({
  exam: null as string | null,
  person: null as string | null,
  score: 0,
  remark: '',
})

const scorePassScore = computed(() => {
  const exam = examRows.value.find((e) => String(e.id) === String(scoreForm.exam))
  return exam ? String(exam.passScore ?? '') : ''
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

function openScoreCreate() {
  Object.assign(scoreForm, { exam: rankExamId.value, person: null, score: 0, remark: '' })
  scoreFormVisible.value = true
}

async function saveScore() {
  if (!scoreForm.exam) {
    message.warning('请选择考试')
    return
  }
  if (!scoreForm.person) {
    message.warning('请选择校招生')
    return
  }
  scoreSaving.value = true
  try {
    await createExamScore({
      exam: String(scoreForm.exam),
      person: String(scoreForm.person),
      score: scoreForm.score,
      remark: scoreForm.remark.trim(),
    })
    message.success('成绩已保存')
    scoreFormVisible.value = false
    if (rankExamId.value) loadRanking()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    scoreSaving.value = false
  }
}

/* ───────────────────────── 生命周期 ───────────────────────── */

function onTabChange(tab: TabKey) {
  if (tab === 'rank') {
    if (!examRows.value.length) loadExams()
    if (rankExamId.value) loadRanking()
  } else {
    loadExams()
  }
}

onMounted(async () => {
  await loadExams()
  try {
    courseRows.value = await listCourses()
  } catch {
    courseRows.value = []
  }
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
.toolbar-select {
  width: 150px;
}
.toolbar-select-wide {
  width: 280px;
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
