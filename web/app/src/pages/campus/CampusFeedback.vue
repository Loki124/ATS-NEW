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
                placeholder="搜索姓名、描述或类型"
                clearable
                style="width: 260px"
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
      <n-form :model="formState" label-placement="top">
        <n-grid :cols="2" :x-gap="16" responsive="screen" :item-responsive="true">
          <n-grid-item span="2 s:1">
            <n-form-item label="校招生" required>
              <n-select
                v-model:value="formState.person"
                :options="personOptions"
                placeholder="搜索并选择校招生"
                clearable
                filterable
                remote
                :loading="personSearching"
                :on-search="onPersonSearch"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item span="2 s:1">
            <n-form-item label="记录日期" required>
              <n-date-picker
                v-model:value="formState.dateTs"
                type="date"
                style="width: 100%"
                placeholder="选择记录日期"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-grid :cols="2" :x-gap="16" responsive="screen" :item-responsive="true">
          <n-grid-item span="2 s:1">
            <n-form-item label="记录分类" required>
              <n-select
                v-model:value="formState.category"
                :options="categoryOptions"
                placeholder="选择记录分类"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item span="2 s:1">
            <n-form-item label="类型" required>
              <n-input v-model:value="formState.type" placeholder="如 迟到 / 沟通风格 / 适应度" />
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-form-item label="描述" required>
          <n-input
            v-model:value="formState.content"
            type="textarea"
            :rows="3"
            placeholder="记录本次反馈的事实与现象"
          />
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
          <n-button :disabled="saving" @click="createVisible = false">取消</n-button>
          <n-button type="primary" :loading="saving" :disabled="!canSubmit" @click="submitCreate">
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
} from 'naive-ui'
import { AddOutline, SearchOutline } from '@vicons/ionicons5'
import {
  createFeedbackRecord,
  fetchOverviewStats,
  listFeedbackRecords,
  resolveFeedbackRecord,
  FEEDBACK_CATEGORY_LABEL,
  type FeedbackRecordRow,
  type OverviewStats,
} from '../../api/campusAssessment'
import { extractError, searchPersons, type SelectOption } from '../../utils/campus'

type FeedbackTab = 'all' | 'issue' | 'mentor'

/** 列表分页（R-108：渲染条目 > 200 必须分页；R-215：分页器固定在表格底部，naive 分页器即表格区最后一个子节点）。 */
const pagination = { pageSize: 50, showSizePicker: false }

const message = useMessage()

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
    message.error(extractError(e))
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

/** 必填项齐备才允许提交（表单按钮禁用态，R-101）。 */
const canSubmit = computed(
  () =>
    !!formState.person &&
    !!formState.dateTs &&
    !!formState.type.trim() &&
    !!formState.content.trim() &&
    !saving.value,
)

function openCreate() {
  Object.assign(formState, emptyForm())
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
  if (!canSubmit.value) return
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
    createVisible.value = false
    await Promise.all([loadList(), loadStats()])
  } catch (e: any) {
    message.error(extractError(e))
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
              disabled: row.status !== '处理中',
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
/* 4 卡统计（自适应栅格，流式列） */
.stat-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(var(--col-min), 1fr));
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
