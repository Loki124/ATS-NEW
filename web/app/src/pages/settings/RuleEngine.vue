<template>
  <div class="page-container">
    <!-- ========== Header ========== -->
    <div class="page-header">
      <div>
        <h1 class="page-title">{ t('pages.settings.RuleEngine.s1') }</h1>
        <p class="page-subtitle">
          跨业务规则的统一视图（TCA / BUSINESS_EVENT / CONSTRAINT / SET_PERMISSION）— 仅聚合只读，源数据在各业务模块维护
        </p>
      </div>
    </div>

    <!-- ========== KPI row ========== -->
    <div class="kpi-row">
      <div v-for="kpi in kpiCards" :key="kpi.key" class="glass-card kpi-card">
        <div class="kpi-label">{{ kpi.label }}</div>
        <div class="kpi-value" :style="{ color: kpi.color }">{{ kpi.count }}</div>
        <div class="kpi-foot">{{ kpi.foot }}</div>
      </div>
    </div>

    <!-- ========== Toolbar ========== -->
    <div class="toolbar">
      <n-space align="center" :wrap="false">
        <n-input
          v-model:value="searchText"
          :placeholder="t('pages.settings.RuleEngine.s2')"
          clearable
          style="width: 280px"
          @update:value="onSearchInput"
        >
          <template #prefix>
            <n-icon :component="SearchOutline" />
          </template>
        </n-input>
        <n-select
          v-model:value="categoryFilter"
          :options="categoryOptions"
          placeholder="规则族"
          style="width: 180px"
          @update:value="loadList"
        />
        <n-select
          v-model:value="sourceAppFilter"
          :options="sourceAppOptions"
          placeholder="来源 app"
          style="width: 180px"
          @update:value="loadList"
        />
        <n-select
          v-model:value="enabledFilter"
          :options="enabledOptions"
          placeholder="启用状态"
          style="width: 130px"
          @update:value="loadList"
        />
      </n-space>
      <n-space>
        <n-button @click="loadList">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
      </n-space>
    </div>

    <!-- ========== Table ========== -->
    <div class="table-wrap">
      <n-data-table
        :columns="columns"
        :data="filteredList"
        :loading="loading"
        :row-key="(r: any) => r.id"
        :pagination="pagination"
        :max-height="tableMaxHeight"
        :scroll-x="1380"
        striped
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <template #empty>
          <n-empty description="暂无规则" />
        </template>
      </n-data-table>
    </div>

    <!-- ========== Detail Modal ========== -->
    <n-modal
      v-model:show="detailVisible"
      preset="card"
      :title="`规则详情：${detail?.name || ''}`"
      style="max-width: 880px; max-height: 90vh;"
      :mask-closable="true"
    >
      <template v-if="detail">
        <div class="detail-grid">
          <div class="detail-cell">
            <div class="cell-label">规则族</div>
            <div class="cell-value">
              <n-tag :type="categoryTagType(detail.category)" size="small">
                {{ detail.category }}
              </n-tag>
            </div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">来源 app</div>
            <div class="cell-value">{{ detail.sourceApp }}</div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">legacy 模型</div>
            <div class="cell-value"><code>{{ detail.legacyModel }}</code></div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">legacy_id</div>
            <div class="cell-value"><code class="mono">{{ detail.legacyId }}</code></div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">触发器</div>
            <div class="cell-value"><code>{{ detail.triggerType }}</code></div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">触发时机</div>
            <div class="cell-value">{{ detail.triggerTiming || '—' }}</div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">优先级</div>
            <div class="cell-value">{{ detail.priority }} ({{ detail.priorityRank }})</div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">启用状态</div>
            <div class="cell-value">
              <n-tag :type="detail.enabled ? 'success' : 'default'" size="small">
                {{ detail.enabled ? '已启用' : '已停用' }}
              </n-tag>
            </div>
          </div>
        </div>

        <n-divider />

        <div class="json-section">
          <h4>scope_json</h4>
          <pre class="json-pre">{{ formatJson(detail.scopeJson) }}</pre>
        </div>
        <div class="json-section">
          <h4>config_json</h4>
          <pre class="json-pre">{{ formatJson(detail.configJson) }}</pre>
        </div>
        <div class="json-section">
          <h4>conditions_summary</h4>
          <pre class="json-pre">{{ formatJson(detail.conditionsSummary) }}</pre>
        </div>
        <div class="json-section">
          <h4>actions_summary</h4>
          <pre class="json-pre">{{ formatJson(detail.actionsSummary) }}</pre>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed, h, onMounted } from 'vue'
import {
  NIcon, NTag, NSpace, NInput, NSelect, NButton, NDataTable, NEmpty, NModal, NDivider,
  useDialog,
} from 'naive-ui'
import type { DataTableColumns, PaginationProps } from 'naive-ui'
import {
  SearchOutline, RefreshOutline, EyeOutline,
} from '@vicons/ionicons5'
import { listRules, type UnifiedRule, type RuleCategory } from '../../api/rule-engine'
import { extractApiError } from '../../api/dynamic-field'
const { t } = useI18n()

const dialog = useDialog()

const loading = ref(false)
const list = ref<UnifiedRule[]>([])
const searchText = ref('')
const categoryFilter = ref<string>('')
const sourceAppFilter = ref<string>('')
const enabledFilter = ref<string>('')

const detailVisible = ref(false)
const detail = ref<UnifiedRule | null>(null)

const pagination = ref<PaginationProps>({
  page: 1,
  pageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (p: number) => { pagination.value.page = p },
  onUpdatePageSize: (s: number) => { pagination.value.pageSize = s; pagination.value.page = 1 },
})

// KPI cards (聚合自全量列表,不受分页影响)
const kpiCards = computed(() => {
  const all = list.value
  const total = all.length
  const enabled = all.filter(r => r.enabled).length
  const byCat = (cat: string) => all.filter(r => r.category === cat).length
  return [
    { key: 'total', label: '总规则数', count: total, foot: `${enabled} 已启用`, color: 'var(--ink)' },
    { key: 'tca', label: 'TCA', count: byCat('TCA'), foot: '时间驱动', color: 'var(--brand)' },
    { key: 'be', label: 'BUSINESS_EVENT', count: byCat('BUSINESS_EVENT'), foot: '业务事件', color: 'var(--success)' },
    { key: 'constraint', label: 'CONSTRAINT', count: byCat('CONSTRAINT'), foot: '硬/软约束', color: 'var(--warning)' },
  ]
})

const categoryOptions = [
  { label: '全部规则族', value: '' },
  { label: 'TCA (时间驱动)', value: 'TCA' },
  { label: 'BUSINESS_EVENT (业务事件)', value: 'BUSINESS_EVENT' },
  { label: 'CONSTRAINT (约束)', value: 'CONSTRAINT' },
  { label: 'SET_PERMISSION (设置权限)', value: 'SET_PERMISSION' },
]

const sourceAppOptions = [
  { label: '全部来源', value: '' },
  { label: 'automation', value: 'automation' },
  { label: 'time_limit', value: 'time_limit' },
  { label: 'entry_condition', value: 'entry_condition' },
  { label: 'mou', value: 'mou' },
  { label: 'campus_control', value: 'campus_control' },
]

const enabledOptions = [
  { label: '全部状态', value: '' },
  { label: '已启用', value: 'true' },
  { label: '已停用', value: 'false' },
]

function categoryTagType(cat: string): 'default' | 'success' | 'info' | 'warning' | 'error' {
  switch (cat) {
    case 'TCA': return 'info'
    case 'BUSINESS_EVENT': return 'success'
    case 'CONSTRAINT': return 'warning'
    case 'SET_PERMISSION': return 'default'
    default: return 'default'
  }
}

function formatJson(v: any): string {
  if (v == null) return '—'
  try {
    return JSON.stringify(v, null, 2)
  } catch {
    return String(v)
  }
}

// 表格列
const columns = computed<DataTableColumns<UnifiedRule>>(() => [
  {
    title: '规则名称',
    key: 'name',
    minWidth: 200,
    ellipsis: { tooltip: true },
    render: (row) => h('span', { class: 'rule-name' }, row.name || '—'),
  },
  {
    title: '规则族',
    key: 'category',
    width: 170,
    render: (row) => h(NTag, { type: categoryTagType(row.category), size: 'small', round: true }, () => row.category),
  },
  {
    title: '来源 app',
    key: 'sourceApp',
    width: 130,
    render: (row) => h('code', { class: 'mono' }, row.sourceApp),
  },
  {
    title: '触发器',
    key: 'triggerType',
    width: 170,
    ellipsis: { tooltip: true },
    render: (row) => h('code', { class: 'mono' }, row.triggerType),
  },
  {
    title: '优先级',
    key: 'priority',
    width: 80,
    render: (row) => row.priority || '—',
  },
  {
    title: '状态',
    key: 'enabled',
    width: 90,
    render: (row) => h(NTag, { type: row.enabled ? 'success' : 'default', size: 'small' }, () => row.enabled ? '启用' : '停用'),
  },
  {
    title: '条件',
    key: 'conditions',
    width: 90,
    align: 'center',
    render: (row) => {
      const cs = row.conditionsSummary
      const n = Array.isArray(cs) ? cs.length : (cs ? 1 : 0)
      return h('span', { class: 'count-badge' }, String(n))
    },
  },
  {
    title: '动作',
    key: 'actions',
    width: 90,
    align: 'center',
    render: (row) => {
      const as = row.actionsSummary
      const n = Array.isArray(as) ? as.length : (as ? 1 : 0)
      return h('span', { class: 'count-badge' }, String(n))
    },
  },
  {
    title: '操作',
    key: 'actions_op',
    width: 90,
    fixed: 'right',
    render: (row) => h(NButton, {
      size: 'small',
      quaternary: true,
      onClick: () => openDetail(row),
    }, { default: () => '详情', icon: () => h(NIcon, null, { default: () => h(EyeOutline) }) }),
  },
])

// 表格 max-height 适配
const tableMaxHeight = computed(() => {
  if (typeof window === 'undefined') return 600
  // header 56 + page-header ~80 + kpi-row ~120 + toolbar ~64 + padding 32 + buffer
  return Math.max(320, window.innerHeight - 360)
})

// 客户端过滤（搜索 + 筛选），分页在 n-data-table 内置处理
const filteredList = computed(() => {
  const kw = searchText.value.trim().toLowerCase()
  return list.value.filter(r => {
    if (kw && !(r.name?.toLowerCase().includes(kw) || r.legacyId?.toLowerCase().includes(kw))) return false
    if (categoryFilter.value && r.category !== categoryFilter.value) return false
    if (sourceAppFilter.value && r.sourceApp !== sourceAppFilter.value) return false
    if (enabledFilter.value !== '') {
      const want = enabledFilter.value === 'true'
      if (Boolean(r.enabled) !== want) return false
    }
    return true
  })
})

let searchTimer: number | null = null
function onSearchInput() {
  if (searchTimer) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    pagination.value.page = 1
  }, 300)
}

function onPageChange(p: number) { pagination.value.page = p }
function onPageSizeChange(s: number) {
  pagination.value.pageSize = s
  pagination.value.page = 1
}

async function loadList() {
  loading.value = true
  try {
    // 一次拉全量（受 StandardResultsSetPagination 分页上限保护）；
    // 数据量预期在几十 ~ 几百条，全量加载即可
    const res = await listRules({ page: 1, pageSize: 500 })
    list.value = res?.data || []
    pagination.value.page = 1
  } catch (e: any) {
    const msg = extractApiError(e) || '规则列表拉取失败'
    dialog.error({ title: '加载失败', content: msg, positiveText: '关闭' })
  } finally {
    loading.value = false
  }
}

function openDetail(row: UnifiedRule) {
  detail.value = row
  detailVisible.value = true
}

onMounted(loadList)
</script>

<style scoped>
/* 继承 settings 子页 .page-container / .page-header / .toolbar / .table-wrap / .kpi-row (docs/ui/SETTINGS_PAGE_STRUCTURE.md §2) */
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: var(--space-4); }
.page-title { margin: 0 0 4px 0; font-size: var(--fs-20); font-weight: 600; color: var(--ink); }
.page-subtitle { margin: 0; color: var(--ink-soft); font-size: var(--fs-13); }

.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-3); margin-bottom: var(--space-4); }
.kpi-card { padding: var(--space-3) var(--space-4); }
.kpi-label { color: var(--ink-soft); font-size: var(--fs-12); margin-bottom: 4px; }
.kpi-value { font-size: var(--fs-24); font-weight: 700; line-height: 1.2; font-variant-numeric: tabular-nums; }
.kpi-foot { color: var(--ink-faint); font-size: var(--fs-11); margin-top: 4px; }

.toolbar {
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;
  gap: var(--space-3); margin-bottom: var(--space-3);
}
.table-wrap { /* settings 子页已有 .table-wrap 全局,内容承载 n-data-table */ }

.rule-name { font-weight: 500; color: var(--ink); }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: var(--fs-12); }
.count-badge {
  display: inline-block; min-width: 24px; padding: 0 8px; line-height: 18px;
  background: var(--brand-tint); color: var(--brand);
  border-radius: 10px; font-size: var(--fs-12); font-weight: 600;
  text-align: center;
}

/* detail modal */
.detail-grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-3);
}
.detail-cell { display: flex; flex-direction: column; gap: 4px; }
.cell-label { color: var(--ink-soft); font-size: var(--fs-12); }
.cell-value { color: var(--ink); font-size: var(--fs-14); }
.json-section { margin-top: var(--space-3); }
.json-section h4 { margin: 0 0 6px 0; color: var(--ink-soft); font-size: var(--fs-13); font-weight: 500; }
.json-pre {
  margin: 0; padding: var(--space-3);
  background: var(--n-code-color, var(--glass-bg-elevated));
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: var(--fs-12);
  color: var(--ink);
  max-height: 240px; overflow: auto;
  white-space: pre-wrap; word-break: break-all;
}

@media (max-width: 900px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .detail-grid { grid-template-columns: 1fr; }
}
</style>