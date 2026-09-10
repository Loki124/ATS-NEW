<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">候选人信息表</h1>
        <p class="page-subtitle">
          统一展示候选人全生命周期信息，支持自定义列、搜索筛选与导出。列设置实时保存，刷新后保留。
        </p>
      </div>
      <div class="page-header-actions">
        <n-button tertiary size="small" @click="openColumnSettings">
          <template #icon><n-icon :component="OptionsOutline" /></template>
          列设置
        </n-button>
        <n-button secondary size="small" :loading="exporting" @click="handleExport">
          <template #icon><n-icon :component="DownloadOutline" /></template>
          导出 CSV
        </n-button>
      </div>
    </div>

    <section class="glass-card">
      <div class="cit-toolbar">
        <n-input
          v-model:value="keyword"
          placeholder="搜索姓名 / 手机 / 邮箱 / 公司"
          clearable
          class="cit-search"
          @keyup.enter="onSearch"
          @clear="onSearch"
        />
        <n-select
          v-model:value="stateFilter"
          :options="stateOptions"
          placeholder="全部状态"
          clearable
          class="cit-state"
          @update:value="onSearch"
        />
        <n-button :loading="loading" @click="onSearch">
          <template #icon><n-icon :component="SearchOutline" /></template>
          查询
        </n-button>
        <n-button quaternary @click="resetFilters">
          重置
        </n-button>
      </div>

      <n-spin :show="loading">
        <n-data-table
          remote
          :columns="columns"
          :data="rows"
          :row-key="(row: CandidateRow) => row.id"
          :pagination="pagination"
          :bordered="false"
          @update:page="onPageChange"
          @update:page-size="onPageSizeChange"
        />
        <n-empty v-if="!loading && !rows.length" description="暂无候选人数据" class="cit-empty" />
      </n-spin>
    </section>

    <!-- 列设置弹窗 -->
    <n-modal
      v-model:show="showColumnSettings"
      title="列设置"
      preset="card"
      style="width: 480px"
      :mask-closable="false"
    >
      <p class="cit-modal-desc">勾选显示列，使用上下按钮调整展示顺序，保存后实时生效并落库。</p>
      <div class="cit-col-list">
        <div v-for="(col, idx) in editingColumns" :key="col.key" class="cit-col-row">
          <n-checkbox v-model:checked="col.visible" :label="col.label" class="cit-col-check" />
          <div class="cit-col-order">
            <n-button size="tiny" tertiary :disabled="idx === 0" @click="moveUp(idx)">↑</n-button>
            <n-button size="tiny" tertiary :disabled="idx === editingColumns.length - 1" @click="moveDown(idx)">↓</n-button>
          </div>
        </div>
      </div>
      <template #footer>
        <n-space justify="end">
          <n-button tertiary @click="showColumnSettings = false">取消</n-button>
          <n-button type="primary" :loading="savingColumns" @click="saveColumnSettings">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted, computed } from 'vue'
import {
  NButton,
  NIcon,
  NInput,
  NSelect,
  NDataTable,
  NSpin,
  NEmpty,
  NModal,
  NCheckbox,
  NSpace,
  useMessage,
} from 'naive-ui'
import { RefreshOutline, DownloadOutline, OptionsOutline, SearchOutline } from '@vicons/ionicons5'
import {
  listCandidatesForTable,
  fetchColumnConfig,
  saveColumnConfig,
  resolveVisibleColumns,
  exportTableToCsv,
  DEFAULT_TABLE_COLUMNS,
  type CandidateRow,
  type CandidateTableColumn,
} from '../../api/candidate-info-table'

const message = useMessage()

const rows = ref<CandidateRow[]>([])
const loading = ref(false)
const exporting = ref(false)
const savingColumns = ref(false)
const keyword = ref('')
const stateFilter = ref<string | null>(null)

// 与后端 candidate/views.py:84 get_queryset 的 current_state 枚举严格对齐（原 ACTIVE/ARCHIVED/BLACKLIST/PENDING 非合法值，过滤必返回空）
const stateOptions = [
  { value: 'APPLIED', label: '已投递' },
  { value: 'IN_PROCESS', label: '流程中' },
  { value: 'OFFER_SENT', label: '已发Offer' },
  { value: 'PENDING_ONBOARDING', label: '待入职' },
  { value: 'ONBOARDED', label: '已入职' },
  { value: 'PROCESS_FAILED', label: '本流程未通过' },
  { value: 'WITHDRAWN', label: '候选人主动撤回' },
  { value: 'TALENT_POOL', label: '公共人才库' },
  { value: 'PROCESS_PAUSED', label: '流程暂停' },
]

const pagination = ref({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
})

// 列配置（权威列表：顺序 + 显隐）
const columnConfig = ref<CandidateTableColumn[]>([])
const visibleColumns = computed(() => resolveVisibleColumns(columnConfig.value))

const columns = computed(() =>
  visibleColumns.value.map((col) => {
    if (col.key === 'stateDisplay') {
      return {
        title: col.label,
        key: col.key,
        render: (row: CandidateRow) =>
          h('span', { class: 'cit-state-tag' }, row.stateDisplay || row.currentState || '—'),
      }
    }
    if (col.key === 'createdAt') {
      return {
        title: col.label,
        key: col.key,
        render: (row: CandidateRow) => row.createdAt?.slice(0, 16) || '—',
      }
    }
    if (col.key === 'tags') {
      return {
        title: col.label,
        key: col.key,
        render: (row: CandidateRow) => (row.tags || []).join('、') || '—',
      }
    }
    return {
      title: col.label,
      key: col.key,
      render: (row: CandidateRow) => {
        const v = (row as Record<string, unknown>)[col.key]
        return v == null || v === '' ? '—' : String(v)
      },
    }
  }),
)

async function loadList() {
  loading.value = true
  try {
    const res = await listCandidatesForTable({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      ...(stateFilter.value ? { state: stateFilter.value } : {}),
      ...(keyword.value ? { keyword: keyword.value } : {}),
    })
    rows.value = res.data
    pagination.value.itemCount = res.total
  } catch (e: any) {
    message.error(`加载失败: ${e?.message || e}`)
  } finally {
    loading.value = false
  }
}

function onSearch() {
  pagination.value.page = 1
  loadList()
}
function resetFilters() {
  keyword.value = ''
  stateFilter.value = null
  onSearch()
}
function onPageChange(page: number) {
  pagination.value.page = page
  loadList()
}
function onPageSizeChange(size: number) {
  pagination.value.pageSize = size
  pagination.value.page = 1
  loadList()
}

async function loadColumnConfig() {
  try {
    const cfg = await fetchColumnConfig()
    columnConfig.value = cfg.columns.length ? cfg.columns : clone(DEFAULT_TABLE_COLUMNS)
  } catch {
    columnConfig.value = clone(DEFAULT_TABLE_COLUMNS)
  }
}

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v))
}

// 列设置弹窗
const showColumnSettings = ref(false)
const editingColumns = ref<CandidateTableColumn[]>([])

function openColumnSettings() {
  editingColumns.value = clone(columnConfig.value)
  showColumnSettings.value = true
}
function moveUp(idx: number) {
  if (idx <= 0) return
  const arr = editingColumns.value
  ;[arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]]
  reindex(arr)
}
function moveDown(idx: number) {
  const arr = editingColumns.value
  if (idx >= arr.length - 1) return
  ;[arr[idx + 1], arr[idx]] = [arr[idx], arr[idx + 1]]
  reindex(arr)
}
function reindex(arr: CandidateTableColumn[]) {
  arr.forEach((c, i) => (c.order = i))
}
async function saveColumnSettings() {
  savingColumns.value = true
  try {
    const saved = await saveColumnConfig({ columns: editingColumns.value })
    columnConfig.value = saved.columns.length ? saved.columns : editingColumns.value
    showColumnSettings.value = false
    message.success('列设置已保存')
  } catch (e: any) {
    message.error(`保存失败: ${e?.message || e}`)
  } finally {
    savingColumns.value = false
  }
}

function handleExport() {
  if (!rows.value.length) {
    message.warning('当前无数据可导出')
    return
  }
  exporting.value = true
  try {
    // 导出当前页可见列对应的真实数据（如需全量可改为按筛选条件二次拉取）
    exportTableToCsv(
      rows.value,
      visibleColumns.value.map((c) => ({ key: c.key, label: c.label })),
    )
    message.success('已导出 CSV')
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  await loadColumnConfig()
  await loadList()
})
</script>

<style scoped>
.page-header-actions { display: flex; gap: var(--space-2); }

.cit-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.cit-search { flex: 1 1 240px; max-width: 320px; }
.cit-state { width: 160px; }

.cit-empty { padding: var(--space-12) 0; }

.cit-state-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--space-2);
  border-radius: var(--radius-pill);
  background: var(--c-info-soft);
  color: var(--c-info);
  font-size: var(--text-meta);
}

.cit-modal-desc { margin: 0 0 var(--space-3); font-size: var(--text-meta); color: var(--ink-soft); }
.cit-col-list { display: flex; flex-direction: column; gap: var(--space-2); max-height: 360px; overflow: auto; }
.cit-col-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}
.cit-col-check { flex: 1; }
.cit-col-order { display: flex; gap: 4px; }
</style>
