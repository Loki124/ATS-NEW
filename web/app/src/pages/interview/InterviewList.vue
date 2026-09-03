<script setup lang="ts">
import { ref, h, onMounted, computed } from 'vue'
import { NTag, NSpace, NButton, NIcon, NDropdown, useMessage, useDialog } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import {
  listInterviews, cancelInterview,
  INTERVIEW_STATUS_LABEL, FEEDBACK_STATUS_LABEL, FEEDBACK_STATUS_COLOR,
  listEvaluations, createEvaluation,
  EVALUATION_REC_TO_BACKEND, EVALUATION_REC_FROM_BACKEND,
  packEvalScores, stripEvalMeta, unpackEvalMeta,
  type Interview, type InterviewEvaluationApi,
  type EvalFinalResult,
} from '../../api/interview'
import InterviewEvaluationModal, {
  FOUR_DIMS, FIVE_VALUES,
  type Evaluation, type SubmitPayload,
} from './InterviewEvaluationModal.vue'
import { useUserStore } from '../../stores/user'

const message = useMessage()
const userStore = useUserStore()
const loading = ref(false)
const dataSource = ref<Interview[]>([])
const filterFeedback = ref<string | null>(null)
const pagination = ref({ page: 1, pageSize: 20, itemCount: 0, pageCount: 0 })

// 评价弹窗状态
const evalModalShow = ref(false)
const evalMode = ref<'view' | 'edit'>('view')
const currentEval = ref<Evaluation | undefined>(undefined)

const stats = computed(() => {
  const counts = { PENDING: 0, COMPLETED: 0 }
  for (const it of (dataSource.value ?? [])) {
    if (it.feedbackStatus === 'PENDING') counts.PENDING++
    else counts.COMPLETED++
  }
  return counts
})

/** 把后端 5 档字符串反向映射回 3 档（带 fallback 防御） */
function fromBackendRec(v: string | undefined | null): EvalFinalResult {
  const mapped = EVALUATION_REC_FROM_BACKEND[v as string]
  return (mapped ?? 'PENDING') as EvalFinalResult
}

/** 把 InterviewEvaluationApi 转成 modal 期望的 v2 Evaluation 结构
 *  v2 (commit 2fxxxx)：meta 优先读 metaJson 字段（新数据），fallback 到 scores['__meta'] 兼容历史数据 */
function toEvaluation(eva: InterviewEvaluationApi, row: Interview): Evaluation {
  // 1. meta 优先从 metaJson 字段读（新数据），fallback scores['__meta']（v1 历史）
  const meta: any = eva.metaJson ?? unpackEvalMeta(eva.scores as any) ?? {}

  // 2. compliances：从 meta.compliances 还原（缺失字段给空 ComplianceItem）
  const compliances: Record<string, { compliance: 'PASS' | 'PARTIAL' | 'FAIL' | null; reason: string }> = {}
  for (const dim of FOUR_DIMS) {
    const c = meta.compliances?.[dim.key]
    compliances[dim.key] = {
      compliance: c?.compliance ?? null,
      reason: c?.reason ?? '',
    }
  }

  // 3. values：真实五能分数（剥离 __meta key）
  const values = stripEvalMeta(eva.scores as any) ?? {}

  // 4. finalResult：优先 meta.finalResult（提交时冗余存的），否则从 recommendation 兜底
  const finalResult: EvalFinalResult = (meta.finalResult as EvalFinalResult)
    ?? fromBackendRec(eva.recommendation)

  return {
    candidate: {
      name: row.roundName || '—',
      position: row.interviewType || '—',
      level: '—', // Interview model 无 level 字段，留 placeholder（接 candidate detail 后再补）
      interviewDate: row.interviewDate?.slice(0, 10) || '—',
    },
    compliances,
    values,
    suggestedLevel: meta.suggestedLevel || '经理',
    suggestedSalary: meta.suggestedSalary || '',
    finalResult,
    comment: eva.comment || '',
  }
}

const columns = computed(() => [
  { title: '轮次', key: 'roundName', width: 100, render: (row: Interview) => row.roundName || '—' },
  { title: '类型', key: 'interviewType', width: 100, render: (row: Interview) => row.interviewType },
  { title: '时间', key: 'interviewDate', width: 160, render: (row: Interview) => row.interviewDate?.slice(0, 16) },
  { title: '时长', key: 'duration', width: 80, render: (row: Interview) => `${row.duration || 60} 分钟` },
  { title: '面试官', key: 'interviewerNames', width: 160, render: (row: Interview) => row.interviewerNames || '—' },
  { title: '地点', key: 'location', width: 140, render: (row: Interview) => row.location || row.meetingLink || '—' },
  {
    title: '状态', key: 'interviewStatus', width: 100,
    render: (row: Interview) => h(NTag, { type: 'info', size: 'small' }, { default: () => INTERVIEW_STATUS_LABEL[row.interviewStatus] || row.interviewStatus }),
  },
  {
    title: '反馈', key: 'feedbackStatus', width: 100,
    render: (row: Interview) => h(NTag, { type: FEEDBACK_STATUS_COLOR[row.feedbackStatus], size: 'small' }, { default: () => FEEDBACK_STATUS_LABEL[row.feedbackStatus] || row.feedbackStatus }),
  },
  {
    title: '操作', key: 'actions', width: 200, fixed: 'right' as const,
    render: (row: Interview) => {
      // v2 (Phase 1 接入): 评价入口替换原 quick 反馈按钮
      // - 已反馈 → "查看评价"（view 态）
      // - 待反馈且未取消 → "填写评价"（edit 态）
      // - 非取消/未完成 → "取消面试"（次级操作）
      const items: Array<{ label: string; key: string; danger?: boolean; onClick: () => void }> = []
      let primary: { label: string; type: 'primary' | 'error' | 'default'; onClick: () => void } | null = null

      if (row.interviewStatus !== 'CANCELLED') {
        if (row.feedbackStatus === 'COMPLETED') {
          primary = { label: '查看评价', type: 'primary', onClick: () => openViewEval(row) }
        } else {
          primary = { label: '填写评价', type: 'primary', onClick: () => openEditEval(row) }
        }
      }
      if (row.interviewStatus !== 'CANCELLED' && row.interviewStatus !== 'COMPLETED') {
        if (!primary) primary = { label: '取消', type: 'error', onClick: () => handleCancel(row) }
        else items.push({ label: '取消面试', key: 'cancel', danger: true, onClick: () => handleCancel(row) })
      }
      if (!primary) return '—'
      return h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'tiny', type: primary.type, onClick: primary.onClick }, { default: () => primary!.label }),
          items.length
            ? h(NDropdown, {
                options: items.map(it => ({
                  label: it.label,
                  key: it.key,
                  ...(it.danger ? { props: { style: 'color: var(--c-error)' } } : {}),
                })),
                trigger: 'click',
                onSelect: (k: string) => items.find(it => it.key === k)?.onClick(),
              }, {
                default: () => h(NButton, { size: 'tiny', quaternary: true }, { default: () => '更多 ⌄' }),
              })
            : null,
        ].filter(Boolean),
      })
    },
  },
])

async function loadList() {
  loading.value = true
  try {
    const res = await listInterviews({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      ...(filterFeedback.value && { feedbackStatus: filterFeedback.value }),
    })
    dataSource.value = res.data ?? []
    pagination.value.itemCount = res.pagination?.total ?? 0
    pagination.value.pageCount = res.pagination?.totalPages ?? 0
  } catch (e: any) {
    message.error(`加载失败: ${e.message}`)
  } finally {
    loading.value = false
  }
}

/** 打开查看评价（取首条 -submitted_at 排序） */
async function openViewEval(row: Interview) {
  try {
    const list = await listEvaluations({ interview: row.id, pageSize: 1 })
    if (!list.length) {
      message.warning('该面试暂无评价记录')
      return
    }
    currentEval.value = toEvaluation(list[0], row)
    evalMode.value = 'view'
    evalModalShow.value = true
  } catch (e: any) {
    message.error(`加载评价失败: ${e.message}`)
  }
}

/** 打开填写评价（edit 态，无预填——前端 demo 用真实提交覆盖） */
function openEditEval(row: Interview) {
  // 不传 evaluation，modal 走内置 DEMO；提交时用真实 interview id 覆盖
  currentEval.value = undefined
  // 但 modal 需要知道当前 interview id —— 用 candidate.interviewer 占位传给 modal 没用
  // 因此这里把当前 interviewId 挂到 row 上，submit 时取
  pendingInterview.value = row
  evalMode.value = 'edit'
  evalModalShow.value = true
}
const pendingInterview = ref<Interview | null>(null)

/** 提交评价 —— 把 modal emit 的 v2 payload 翻译成后端 5 档
 *  v2：finalResult(PASS/FAIL/PENDING) → 后端 RECOMMEND/NOT_RECOMMEND/NEUTRAL
 *      meta(compliances/suggestedLevel/suggestedSalary/finalResult) 塞进 scores['__meta'] */
async function handleEvalSubmit(payload: SubmitPayload) {
  if (!pendingInterview.value) {
    message.error('未选中面试，无法提交')
    return
  }
  if (!userStore.user?.id) {
    message.error('当前用户未登录，无法提交评价')
    return
  }
  // 1. scores 纯净：只放五能真实分数，meta 走 metaJson 独立字段（v2 commit 2fxxxx）
  const scores = { ...payload.values }
  // 2. overallScore 取五能均分（兼容后端 model 的 overall_score 字段）
  const scoreArr = Object.values(payload.values).filter(v => v > 0)
  const overallScore = scoreArr.length
    ? Math.round((scoreArr.reduce((a, b) => a + b, 0) / scoreArr.length) * 10) / 10
    : 0
  try {
    await createEvaluation({
      interview: pendingInterview.value.id,
      interviewer: String(userStore.user.id),
      scores,
      overallScore,
      recommendation: EVALUATION_REC_TO_BACKEND[payload.finalResult] ?? 'NEUTRAL',
      comment: payload.comment,
      metaJson: {
        compliances: payload.compliances,
        suggestedLevel: payload.suggestedLevel,
        suggestedSalary: payload.suggestedSalary,
        finalResult: payload.finalResult,
      },
    })
    message.success('评价已提交')
    evalModalShow.value = false
    pendingInterview.value = null
    loadList()
  } catch (e: any) {
    message.error(`提交失败: ${e.response?.data?.message || e.message}`)
  }
}

async function handleCancel(row: Interview) {
  // v2: 取消面试弹 dialog 二次确认
  try {
    const dialog = useDialog()
    await dialog.warning({
      title: '确认取消',
      content: `确认取消「${row.roundName || '面试'}」？取消后候选人将收到通知。`,
      positiveText: '确认取消',
      negativeText: '返回',
    })
  } catch { return }
  try {
    await cancelInterview(row.id, 'HR 取消面试')
    message.success('已取消面试')
    loadList()
  } catch (e: any) {
    message.error(`取消失败: ${e.message}`)
  }
}

onMounted(loadList)

// v2: 表格行键盘可达 [T8.4]
function rowProps(row: any) {
  return {
    tabindex: 0,
    role: 'button',
    'aria-label': `面试 ${row.roundName || row.id}`,
  }
}
</script>

<template>
  <!-- 面试评价弹窗（v2 Phase 1 接入） -->
  <InterviewEvaluationModal
    v-model:show="evalModalShow"
    :mode="evalMode"
    :evaluation="currentEval"
    @submit="handleEvalSubmit"
  />

  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">面试管理</h1>
      <n-space>
        <n-button :loading="loading" @click="loadList">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
      </n-space>
    </div>

    <n-grid x-gap="12" y-gap="12" cols="3" class="stats-row">
      <n-gi>
<n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">待反馈</div>
        <div class="stat-value" style="color: var(--c-warning);">{{ stats.PENDING }}</div>
      </n-card>
</n-gi>
      <n-gi>
<n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">已反馈</div>
        <div class="stat-value" style="color: var(--c-success);">{{ stats.COMPLETED }}</div>
      </n-card>
</n-gi>
      <n-gi>
<n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">总面试数</div>
        <div class="stat-value">{{ dataSource.length }}</div>
      </n-card>
</n-gi>
    </n-grid>

    <n-card :bordered="false" class="rounded-xl">
      <n-space class="filter-row">
        <n-select
          v-model:value="filterFeedback"
          placeholder="反馈状态"
          style="width: 140px"
          clearable
          :options="[{value:'PENDING',label:'待反馈'},{value:'COMPLETED',label:'已反馈'}]"
          @update:value="loadList"
        />
      </n-space>
      <n-data-table
        :columns="columns"
        :row-props="rowProps"
        :data="dataSource"
        :loading="loading"
        :row-key="(row: Interview) => row.id"
        :pagination="pagination"
        @update:page="(p: number) => { pagination.page = p; loadList() }"
      />
    </n-card>
  </div>
</template>

<style scoped>
.page-container { padding: var(--space-6); animation: wb-fade-up var(--duration-slow) var(--ease-out) both; }
.page-header { margin-bottom: var(--space-4); display: flex; align-items: center; justify-content: space-between; }
.page-title { font-size: var(--fs-24); font-weight: 600; margin: 0; }
.stats-row { margin-bottom: var(--space-4); }
.stat-card { text-align: center; }
.stat-label { font-size: var(--text-meta); color: var(--ink-faint); }
.stat-value { font-size: 22px; font-weight: 600; margin-top: var(--space-1); }
.filter-row { margin-bottom: var(--space-3); }

/* === v2 响应式补丁 === */
@media (max-width: 1280px) {
  .page-container { padding: var(--space-4); }
  .page-title { font-size: var(--text-h2); }
  :deep(.n-data-table-wrapper) {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
}
@media (max-width: 768px) {
  .page-container { padding: var(--space-3); }
  .page-header { flex-direction: column; align-items: stretch; gap: var(--space-3); }
  .stats-row { grid-template-columns: repeat(2, 1fr) !important; } /* v2.9: 保留 !important（覆盖 Naive n-grid 内联 grid-template-columns，移除则移动端不退化为 2 列） */
}
@media (max-width: 480px) {
  .stats-row { grid-template-columns: 1fr !important; } /* v2.9: 保留 !important（覆盖 Naive n-grid 内联 grid-template-columns，移除则移动端不退化为 1 列） */
}

</style>
