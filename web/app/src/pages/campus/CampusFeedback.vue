<template>
  <!-- 反馈记录：逆向清单 §4.3 `feedback` 视图。
       4 卡统计 + 3 个页签（全部 / 问题·情况记录 / 导师带教反馈）+ 搜索 + 明细弹窗 + 办结。 -->
  <div class="page-container">
    <div class="page-body">
      <!-- 4 卡统计（总数 / 处理中 / 已解决·已闭环 / 含证据记录） -->
      <div class="stat-row">
        <div v-for="card in statCards" :key="card.key" class="stat-card">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value">{{ card.value }}</div>
        </div>
      </div>

      <n-tabs
        v-model:value="activeTab"
        type="line"
        display-directive="show:lazy"
        class="cf-tabs"
        @update:value="onTabChange"
      >
        <n-tab-pane v-for="pane in tabPanes" :key="pane.name" :name="pane.name" :tab="pane.tab">
          <div class="toolbar">
            <div class="field">
              <span class="field-label">关键词</span>
              <n-input
                v-model:value="searchText"
                aria-label="关键词"
                class="toolbar-search"
                placeholder="搜索姓名、描述或类型"
                clearable
                @keyup.enter="loadList"
                @clear="loadList"
              >
                <template #prefix><n-icon :component="SearchOutline" /></template>
              </n-input>
            </div>
            <n-button :loading="loading" @click="loadList">
              <template #icon><n-icon :component="SearchOutline" /></template>
              搜索记录
            </n-button>
            <div class="spacer"></div>
            <n-button type="primary" @click="openCreate">
              <template #icon><n-icon :component="AddOutline" /></template>
              新增记录
            </n-button>
          </div>

          <n-alert v-if="loadError" type="error" :show-icon="true" class="load-error">
            <div class="error-head">
              <span>反馈记录没能加载出来，本次查询没有改动任何数据。</span>
              <n-button size="small" tertiary type="error" :loading="loading" @click="loadList">
                重新加载
              </n-button>
            </div>
            <n-collapse v-if="errorDetail" class="error-collapse">
              <n-collapse-item title="详情" name="detail">
                <div class="error-detail">
                  <code>{{ errorDetail }}</code>
                  <n-button size="tiny" quaternary @click="copyDetail(errorDetail)">复制错误信息</n-button>
                </div>
              </n-collapse-item>
            </n-collapse>
          </n-alert>

          <div v-if="loading && !rows.length" class="skeleton-wrap">
            <n-skeleton :repeat="6" animated />
          </div>

          <div v-else class="table-wrap">
            <n-data-table
              :columns="columns"
              :data="rows"
              :loading="loading"
              :bordered="false"
              :pagination="pagination"
              :scroll-x="TABLE_SCROLL_X"
              :row-key="(row: FeedbackRecordRow) => row.id"
              flex-height
            >
              <template #empty>
                <n-empty :description="emptyText" />
              </template>
            </n-data-table>
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>

    <!-- 新增记录弹窗（R-224 居中弹窗，内容区固定高度，底部按钮在 #footer） -->
    <n-modal
      v-model:show="createVisible"
      preset="card"
      title="新增反馈记录"
      :style="{ width: '720px', maxWidth: '95vw' }"
      :content-style="{ height: 'min(560px, calc(88vh - 180px))', overflowY: 'auto' }"
      :mask-closable="false"
    >
      <!-- 写入失败三段式（R-203）：人话标题 + 数据是否安全 + 折叠技术详情（可一键复制） -->
      <div v-if="writeError" ref="writeErrorRef" class="write-error-wrap">
        <n-alert type="error" :show-icon="true" :title="writeError.title">
          <div class="error-safe">{{ writeError.safe }}</div>
          <details class="error-details">
            <summary>查看详情</summary>
            <pre class="error-code">{{ writeError.detail }}</pre>
            <n-button size="tiny" quaternary @click="copyDetail(writeError.detail)">复制错误信息</n-button>
          </details>
        </n-alert>
      </div>

      <n-form :model="formState" label-placement="top">
        <!-- 未填项提示（R-221 / R-204）：图标 + 文字双通道，提交按钮不再静默置灰 -->
        <div v-if="validateAttempted && missingLabels.length" class="form-hint" role="status">
          <n-icon :component="AlertCircleOutline" aria-hidden="true" />
          <span>还有 {{ missingLabels.length }} 项未填写：{{ missingLabels.join('、') }}</span>
        </div>
        <n-grid :cols="2" :x-gap="16" responsive="screen" :item-responsive="true">
          <n-grid-item span="2 s:1">
            <n-form-item
              label="校招生"
              required
              :validation-status="personError ? 'error' : undefined"
              :show-feedback="!!personError"
            >
              <n-select
                ref="personRef"
                v-model:value="formState.person"
                :options="personOptions"
                placeholder="搜索并选择校招生"
                clearable
                filterable
                remote
                :loading="personSearching"
                :on-search="onPersonSearch"
              />
              <template #feedback>
                <span class="field-error">
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  <span>{{ personError }}</span>
                </span>
              </template>
            </n-form-item>
          </n-grid-item>
          <n-grid-item span="2 s:1">
            <n-form-item
              label="记录日期"
              required
              :validation-status="dateError ? 'error' : undefined"
              :show-feedback="!!dateError"
            >
              <n-date-picker
                v-model:value="formState.dateTs"
                type="date"
                style="width: 100%"
                placeholder="选择记录日期"
              />
              <template #feedback>
                <span class="field-error">
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  <span>{{ dateError }}</span>
                </span>
              </template>
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-grid :cols="2" :x-gap="16" responsive="screen" :item-responsive="true">
          <n-grid-item span="2 s:1">
            <n-form-item
              label="记录分类"
              required
            >
              <n-select
                v-model:value="formState.category"
                :options="categoryOptions"
                placeholder="选择记录分类"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item span="2 s:1">
            <n-form-item
              label="类型"
              required
              :validation-status="typeError ? 'error' : undefined"
              :show-feedback="!!typeError"
            >
              <n-input
                ref="typeRef"
                v-model:value="formState.type"
                placeholder="如 迟到 / 沟通风格 / 适应度"
              />
              <template #feedback>
                <span class="field-error">
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  <span>{{ typeError }}</span>
                </span>
              </template>
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-form-item
          label="描述"
          required
          :validation-status="contentError ? 'error' : undefined"
          :show-feedback="!!contentError"
        >
          <n-input
            ref="contentRef"
            v-model:value="formState.content"
            type="textarea"
            :rows="3"
            placeholder="记录本次反馈的事实与现象"
          />
          <template #feedback>
            <span class="field-error">
              <n-icon :component="AlertCircleOutline" aria-hidden="true" />
              <span>{{ contentError }}</span>
            </span>
          </template>
        </n-form-item>
        <n-form-item label="处理方式">
          <n-input
            v-model:value="formState.handling"
            type="textarea"
            :rows="2"
            placeholder="如 班主任已沟通，安排导师跟进辅导"
          />
        </n-form-item>
        <n-form-item label="证据">
          <n-input
            v-model:value="formState.evidence"
            type="textarea"
            :rows="2"
            placeholder="每行一条证据链接或编号（可留空）"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="saving" @click="createVisible = false">取消新增</n-button>
          <n-button type="primary" :loading="saving" :disabled="saving" @click="submitCreate">
            保存记录
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 记录详情弹窗 -->
    <n-modal
      v-model:show="detailVisible"
      preset="card"
      title="反馈记录详情"
      :style="{ width: '720px', maxWidth: '95vw' }"
      :content-style="{ height: 'min(520px, calc(88vh - 180px))', overflowY: 'auto' }"
      :mask-closable="false"
    >
      <n-descriptions v-if="detailRow" label-placement="left" bordered :column="1" size="small">
        <n-descriptions-item label="日期">{{ detailRow.date || '—' }}</n-descriptions-item>
        <n-descriptions-item label="校招生">{{ detailRow.personName || '—' }}</n-descriptions-item>
        <n-descriptions-item label="记录人">{{ detailRow.reporterName || '—' }}</n-descriptions-item>
        <n-descriptions-item label="记录分类">
          {{ FEEDBACK_CATEGORY_LABEL[detailRow.category] || detailRow.category || '—' }}
        </n-descriptions-item>
        <n-descriptions-item label="类型">{{ detailRow.type || '—' }}</n-descriptions-item>
        <n-descriptions-item label="描述">{{ detailRow.content || '—' }}</n-descriptions-item>
        <n-descriptions-item label="处理方式">{{ detailRow.handling || '—' }}</n-descriptions-item>
        <n-descriptions-item label="状态">{{ detailRow.status || '—' }}</n-descriptions-item>
        <n-descriptions-item label="处理人">{{ detailRow.handlerName || '—' }}</n-descriptions-item>
        <n-descriptions-item label="证据">
          <ul v-if="detailRow.attachments.length" class="evidence-list">
            <li v-for="(item, i) in detailRow.attachments" :key="i" class="evidence-item" :title="item">
              {{ item }}
            </li>
          </ul>
          <span v-else>—</span>
        </n-descriptions-item>
      </n-descriptions>
      <template #footer>
        <n-space justify="end">
          <n-button @click="detailVisible = false">关闭详情</n-button>
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
  NDatePicker,
  NDescriptions,
  NDescriptionsItem,
  NEmpty,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NIcon,
  NInput,
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
import { AddOutline, AlertCircleOutline, SearchOutline } from '@vicons/ionicons5'
import {
  createFeedbackRecord,
  fetchOverviewStats,
  listFeedbackRecords,
  resolveFeedbackRecord,
  FEEDBACK_CATEGORY_LABEL,
  type FeedbackRecordRow,
  type OverviewStats,
} from '../../api/campusAssessment'
import {
  buildWriteError,
  extractError,
  searchPersons,
  type SelectOption,
  type WriteErrorInfo,
} from '../../utils/campus'
import { useFormDraft } from '../../composables/useFormDraft'

type FeedbackTab = 'all' | 'issue' | 'mentor'

/** 列表分页（R-108：渲染条目 > 200 必须分页；R-215：分页器固定在表格底部，naive 分页器即表格区最后一个子节点）。 */
const pagination = { pageSize: 50, showSizePicker: false }

const message = useMessage()
const notification = useNotification()

/* ────────────────────────── 统计卡 ────────────────────────── */

const stats = ref<OverviewStats>({
  feedbackTotal: 0,
  feedbackPending: 0,
  feedbackResolved: 0,
  feedbackWithEvidence: 0,
  attendDays: 0,
  lateCount: 0,
  leaveDays: 0,
})
const statCards = computed(() => [
  { key: 'total', label: '反馈总数', value: stats.value.feedbackTotal },
  { key: 'pending', label: '处理中', value: stats.value.feedbackPending },
  { key: 'resolved', label: '已解决·已闭环', value: stats.value.feedbackResolved },
  { key: 'evidence', label: '含证据记录', value: stats.value.feedbackWithEvidence },
])

async function loadStats() {
  try {
    stats.value = await fetchOverviewStats()
  } catch {
    // 统计卡失败不阻断列表：列表自身有独立的失败态与重试入口（R-111）
  }
}

/* ────────────────────────── 列表 ────────────────────────── */

const tabPanes: { name: FeedbackTab; tab: string }[] = [
  { name: 'all', tab: '全部' },
  { name: 'issue', tab: '问题·情况记录' },
  { name: 'mentor', tab: '导师带教反馈' },
]
const activeTab = ref<FeedbackTab>('all')
const rows = ref<FeedbackRecordRow[]>([])
const loading = ref(false)
const loadError = ref('')
const errorDetail = ref('')
const searchText = ref('')

/** 当前页签对应的分类过滤值（全部 = 不过滤）。 */
const activeCategory = computed(() => (activeTab.value === 'all' ? '' : activeTab.value))

const emptyText = computed(() =>
  searchText.value.trim() ? '没有匹配「关键词」的反馈记录，换个词再看看' : '暂无反馈记录',
)

async function loadList() {
  loading.value = true
  loadError.value = ''
  errorDetail.value = ''
  try {
    rows.value = await listFeedbackRecords({
      ...(activeCategory.value ? { category: activeCategory.value } : {}),
      ...(searchText.value.trim() ? { kw: searchText.value.trim() } : {}),
    })
  } catch (e: any) {
    loadError.value = extractError(e)
    errorDetail.value = String(e?.message ?? e)
  } finally {
    loading.value = false
  }
}

function onTabChange() {
  loadList()
}

/* ────────────────────────── 办结 ────────────────────────── */

/** 正在办结的行 id（行内按钮 loading，防止重复提交，R-101） */
const resolvingId = ref('')

async function resolveRow(row: FeedbackRecordRow) {
  if (resolvingId.value) return
  resolvingId.value = row.id
  try {
    await resolveFeedbackRecord(row.id)
    message.success(`「${row.personName || '该记录'}」的反馈已办结`)
    await Promise.all([loadList(), loadStats()])
  } catch (e: any) {
    // R-203：行内操作没有独立错误区，用三段式文案兜底（标题 + 数据安全说明）
    const info = buildWriteError(e, { action: '办结反馈记录' })
    message.error(`${info.title}。${info.safe}`)
  } finally {
    resolvingId.value = ''
  }
}

/* ────────────────────────── 详情 / 新增 ────────────────────────── */

const detailVisible = ref(false)
const detailRow = ref<FeedbackRecordRow | null>(null)

function openDetail(row: FeedbackRecordRow) {
  detailRow.value = row
  detailVisible.value = true
}

const createVisible = ref(false)
const saving = ref(false)
const personOptions = ref<SelectOption[]>([])
const personSearching = ref(false)

const emptyForm = () => ({
  person: null as string | null,
  dateTs: Date.now() as number | null,
  category: 'issue' as string,
  type: '',
  content: '',
  handling: '',
  evidence: '',
})
const formState = reactive(emptyForm())

const categoryOptions = Object.entries(FEEDBACK_CATEGORY_LABEL).map(([value, label]) => ({ label, value }))

/* ────────────────────────── 草稿（R-105） ────────────────────────── */

/**
 * 草稿自动保存：命名空间按「页面-表单」唯一。
 * 反馈记录表单共 6 个字段（含 2 段长文本），人工填写超过 1 分钟 → 接草稿。
 * 提交成功后 MUST 立即 draft.clear()。
 *
 * ⚠️ draftEnabled：提交成功后置 false —— 否则「待写入的 800ms 定时器」会在
 *    draft.clear() 之后把刚提交的内容又写回草稿，造成下次打开误报「已恢复」。
 *    下次打开弹窗时重新置 true。
 */
const draftEnabled = ref(true)
const draft = useFormDraft('campus-feedback-create', formState, { enabled: () => draftEnabled.value })

/** 草稿里是否已有有效内容（空草稿不算「填写过」，恢复时不打扰用户）。 */
function hasDraftContent(): boolean {
  return Boolean(formState.person || formState.type.trim() || formState.content.trim())
}

/* ────────────────────────── 字段级校验（R-221） ────────────────────────── */

/** 是否已尝试提交：决定是否显示字段级错误；提交后随输入实时更新。 */
const validateAttempted = ref(false)

/** 缺失必填项的中文字段名（用于「还有 N 项未填写」提示）。 */
const missingLabels = computed(() => {
  const list: string[] = []
  if (!formState.person) list.push('校招生')
  if (!formState.dateTs) list.push('记录日期')
  if (!formState.type.trim()) list.push('类型')
  if (!formState.content.trim()) list.push('描述')
  return list
})

const personError = computed(() => (validateAttempted.value && !formState.person ? '请选择校招生' : ''))
const dateError = computed(() => (validateAttempted.value && !formState.dateTs ? '请选择记录日期' : ''))
const typeError = computed(() => (validateAttempted.value && !formState.type.trim() ? '请填写反馈类型' : ''))
const contentError = computed(() =>
  validateAttempted.value && !formState.content.trim() ? '请填写反馈描述' : '',
)

/** 首个出错字段的聚焦句柄（提交失败时把光标送到第一个出错的控件）。 */
const personRef = ref<any>(null)
const typeRef = ref<any>(null)
const contentRef = ref<any>(null)

function focusFirstInvalid() {
  const candidates = [
    { err: personError.value, el: personRef.value },
    { err: typeError.value, el: typeRef.value },
    { err: contentError.value, el: contentRef.value },
  ]
  const hit = candidates.find((c) => c.err && c.el)
  hit?.el?.focus?.()
}

/* ────────────────────────── 写入失败三段式（R-203） ────────────────────────── */

/** 写入失败的三段式信息（人话标题 / 数据是否安全 / 技术详情）。 */
const writeError = ref<WriteErrorInfo | null>(null)
const writeErrorRef = ref<HTMLElement | null>(null)

/** 失败提示在内容区顶部，滚动到可见位置（内容区固定高度 + 内部滚动）。 */
function scrollWriteErrorIntoView() {
  writeErrorRef.value?.scrollIntoView?.({ block: 'nearest' })
}

function openCreate() {
  validateAttempted.value = false
  writeError.value = null
  draftEnabled.value = true
  // R-105：打开弹窗时探测草稿 → 恢复内容并给出「清空」出口；空草稿直接丢弃。
  if (draft.probe()) {
    draft.restore()
    if (hasDraftContent()) {
      notification.create({
        content: '已恢复上次填写的内容',
        duration: 8000,
        keepAliveOnHover: true,
        action: () =>
          h(
            NButton,
            {
              text: true,
              type: 'primary',
              onClick: () => {
                // R-105：清空出口 = 清草稿 + 清表单，用户可从头重填
                draft.clear()
                Object.assign(formState, emptyForm())
                message.success('已清空草稿，可重新填写')
              },
            },
            { default: () => '清空' },
          ),
      })
    } else {
      draft.clear()
      Object.assign(formState, emptyForm())
    }
  } else {
    Object.assign(formState, emptyForm())
  }
  createVisible.value = true
}

async function onPersonSearch(keyword: string) {
  personSearching.value = true
  try {
    personOptions.value = await searchPersons(keyword)
  } catch {
    personOptions.value = []
  } finally {
    personSearching.value = false
  }
}

function formatDate(ts: number | null): string {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function submitCreate() {
  // R-221：提交前先跑字段级校验，错误就地显示（图标 + 文字），并聚焦第一个出错字段。
  validateAttempted.value = true
  writeError.value = null
  if (missingLabels.value.length) {
    message.warning(`还有 ${missingLabels.value.length} 项未填写，已在对应字段标出`)
    focusFirstInvalid()
    return
  }
  saving.value = true
  try {
    await createFeedbackRecord({
      person: formState.person ?? undefined,
      date: formatDate(formState.dateTs),
      category: formState.category,
      type: formState.type.trim(),
      content: formState.content.trim(),
      handling: formState.handling.trim(),
      attachments: formState.evidence
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean),
    })
    message.success('反馈记录已保存')
    // R-105：提交成功后立即清除草稿（并停掉本次会话的自动保存，避免待写入定时器把已提交内容写回）
    draft.clear()
    draftEnabled.value = false
    validateAttempted.value = false
    createVisible.value = false
    await Promise.all([loadList(), loadStats()])
  } catch (e: any) {
    // R-203：三段式写入失败提示（人话标题 + 数据安全说明 + 折叠技术详情）
    writeError.value = buildWriteError(e, { action: '保存反馈记录' })
    scrollWriteErrorIntoView()
  } finally {
    saving.value = false
  }
}

/* ────────────────────────── 表格列 ────────────────────────── */

function statusType(status: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
  if (status === '已解决' || status === '已闭环') return 'success'
  if (status === '处理中') return 'warning'
  return 'default'
}

const columns = [
  { title: '日期', key: 'date', width: 110 },
  { title: '校招生', key: 'personName', width: 110, ellipsis: { tooltip: true } },
  { title: '记录人', key: 'reporterName', width: 110, ellipsis: { tooltip: true } },
  {
    title: '类型',
    key: 'type',
    width: 130,
    ellipsis: { tooltip: true },
    render: (row: any) => row.type || '—',
  },
  {
    title: '描述',
    key: 'content',
    width: 240,
    ellipsis: { tooltip: true },
    render: (row: any) => row.content || '—',
  },
  {
    title: '处理方式',
    key: 'handling',
    width: 200,
    ellipsis: { tooltip: true },
    render: (row: any) => row.handling || '—',
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: any) =>
      h(NTag, { type: statusType(row.status), size: 'small', bordered: false }, { default: () => row.status || '—' }),
  },
  {
    title: '证据',
    key: 'attachments',
    width: 110,
    render: (row: any) => {
      const list: string[] = Array.isArray(row.attachments) ? row.attachments : []
      if (!list.length) return '—'
      return h(
        'span',
        { title: list.join('\n') },
        list.length > 1 ? `${list[0]} 等 ${list.length} 条` : list[0],
      )
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    fixed: 'right' as const,
    render: (row: any) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(
            NButton,
            { size: 'small', quaternary: true, type: 'primary', onClick: () => openDetail(row) },
            { default: () => '查看详情' },
          ),
          h(
            NButton,
            {
              size: 'small',
              quaternary: true,
              type: 'warning',
              disabled: row.status !== '处理中' || resolvingId.value === row.id,
              loading: resolvingId.value === row.id,
              onClick: () => resolveRow(row),
            },
            { default: () => '办结记录' },
          ),
        ],
      }),
  },
]
const TABLE_SCROLL_X = 1260

/* ────────────────────────── 通用 ────────────────────────── */

async function copyDetail(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    message.success('已复制错误信息')
  } catch {
    message.warning('浏览器不允许复制，请手动选中详情文本')
  }
}

onMounted(() => {
  loadList()
  loadStats()
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
/* 4 卡统计（自适应栅格，流式列）
   ⚠️ minmax(min(--col-min, 100%), 1fr)：--col-min=280px 在 320px 视口下比内容区还宽，
      会把卡片撑出容器被 overflow:hidden 裁掉 → 用仓库既有写法（见 PersonProfileModal）收敛。 */
.stat-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(var(--col-min), 100%), 1fr));
  gap: var(--space-2);
  flex-shrink: 0;
}
.stat-card {
  background: var(--surface);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
}
.stat-label {
  font-size: var(--text-small);
  color: var(--ink-soft);
  line-height: 1.5;
}
.stat-value {
  font-size: var(--text-h2);
  font-weight: 600;
  line-height: 1.3;
  font-variant-numeric: tabular-nums;
}
.cf-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.cf-tabs :deep(.n-tabs-pane-wrapper) {
  flex: 1;
  min-height: 0;
}
.cf-tabs :deep(.n-tab-pane) {
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
  /* R-103：窄屏换行，避免固定宽控件被 .page-body 的 overflow:hidden 裁切 */
  flex-wrap: wrap;
  padding-bottom: var(--space-2);
}
/* 固定宽控件窄屏收敛到容器宽度（320px 视口不产生横向溢出） */
.toolbar-search {
  width: 260px;
  max-width: 100%;
  min-width: 0;
  flex: 0 1 auto;
}
.field {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  /* R-103：允许整组在窄屏收缩到行宽以内（否则 260px 输入框会被 overflow:hidden 裁掉尾巴） */
  min-width: 0;
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
/* 写入失败三段式（R-203）：标题 + 数据安全说明 + 折叠技术详情 */
.write-error-wrap {
  margin-bottom: var(--space-3);
}
.error-safe {
  font-size: var(--text-small);
  color: var(--ink-soft);
  overflow-wrap: anywhere;
}
.error-details {
  margin-top: var(--space-2);
  font-size: var(--text-meta);
  color: var(--ink-soft);
}
.error-code {
  margin: var(--space-1) 0;
  padding: var(--space-2);
  background: var(--surface);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  white-space: pre-wrap;
  word-break: break-all;
}
/* 字段级错误：图标 + 文字双通道（R-221），不靠颜色单独表达 */
.field-error {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-small);
  color: var(--c-error-deep);
}
.form-hint {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-bottom: var(--space-3);
  font-size: var(--text-small);
  color: var(--c-error-deep);
  overflow-wrap: anywhere;
}
.evidence-list {
  margin: 0;
  padding-left: var(--space-4);
}
.evidence-item {
  overflow-wrap: anywhere;
}
/* 动态数字防抖动（作用于 naive 自身 DOM，不涉及 h() 渲染节点） */
.table-wrap :deep(.n-data-table-td) {
  font-variant-numeric: tabular-nums;
}
</style>
