<template>
  <div class="page-container recruitment-process">
<div class="page-body">
    <div class="page-header">
      <div>
        <h1 class="page-title">招聘流程管理</h1>
        <p class="page-subtitle">定义招聘流程及其阶段编排</p>
      </div>
    </div>

    <div class="toolbar">
      <n-input v-model:value="keyword" placeholder="搜索流程名称" clearable style="width: 220px">
        <template #prefix><n-icon :component="SearchOutline" /></template>
      </n-input>
      <div class="spacer"></div>
      <n-button type="primary" class="gradient-btn" @click="openCreateProcess">
        <template #icon><n-icon :component="AddOutline" /></template>
        新建流程
      </n-button>
    </div>

    <div class="table-wrap">
    <n-data-table
      :columns="columns"
      :data="processes"
      :loading="loading"
      :pagination="{ pageSize: 20 }"
      :row-key="(r) => r.id"
      :max-height="tableMaxHeight"
      :row-height="TABLE_ROW_HEIGHT"
    />
    </div>

    <!-- 流程详情 modal (view + edit 双模态, 统一入口) -->
    <ProcessDetailModal
      v-model:show="showDetail"
      :process-id="detailProcessId"
      :default-mode="detailDefaultMode"
      :editable="true"
      @saved="onProcessSaved"
      @copied="onProcessCopied"
    />
    </div><!-- /.page-body -->
</div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, computed } from 'vue'
import { useMessage, NButton, NTag, NIcon, NDataTable } from 'naive-ui'
import { AddOutline, SearchOutline } from '@vicons/ionicons5'
import { listProcesses } from '../../api/recruitment-process'
import ProcessDetailModal from './ProcessDetailModal.vue'

const message = useMessage()
const keyword = ref('')
const processes = ref<any[]>([])
const loading = ref(false)
// 2026-08-29 UX 整改：表头固定 + 行高统一。表格高度 = 视窗高 - 上方累计(标题/工具条/分页)。
const TABLE_ROW_HEIGHT = 56
const tableMaxHeight = computed(() => {
  if (typeof window === 'undefined') return 560
  // 预留分页器 64 + page-header 80 + toolbar 56 + page-body gap 32 ≈ 232
  return Math.max(320, window.innerHeight - 232)
})

const columns = [
  { title: '流程编号', key: 'code', width: 100 },
  { title: '流程名称', key: 'name', width: 200, ellipsis: true, ellipsisProps: { tooltip: true } },
  {
    title: '适用部门',
    key: 'applicableDepartments',
    width: 140,
    ellipsis: true,
    ellipsisProps: { tooltip: true },
    render: (r: any) => formatDepts(r.applicableDepartments),
  },
  {
    title: '阶段数',
    key: 'stageCount',
    width: 80,
    render: (row: any) => row.stageCount ?? row._count?.links ?? 0,
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row: any) => h(NTag, { type: row.status === 'ACTIVE' ? 'success' : 'default' }, { default: () => row.status === 'ACTIVE' ? '启用' : '停用' }),
  },
  { title: '最后修改人', key: 'updater', width: 120, ellipsis: true, ellipsisProps: { tooltip: true }, render: (r: any) => r.updater?.realName || '-' },
  { title: '最后修改时间', key: 'updatedAt', width: 170, ellipsis: true, ellipsisProps: { tooltip: true }, render: (r: any) => formatDate(r.updatedAt) },
  {
    title: '操作',
    key: 'action',
    width: 100,
    fixed: 'right' as const,
    render: (row: any) => h(NButton, {
      size: 'small',
      type: 'primary',
      text: true,
      onClick: () => openProcessModal(row),
    }, { default: () => '编辑' }),
  },
]

function formatDate(s: string) {
  return s ? new Date(s).toLocaleString('zh-CN', { hour12: false }) : '-'
}

/** 适用部门字段 (JSON 数组) */
function formatDepts(d: any): string {
  if (!d) return '全部'
  if (Array.isArray(d)) {
    if (d.length === 0) return '全部'
    if (d.length <= 2) return d.join(', ')
    return `${d.slice(0, 2).join(', ')} +${d.length - 2}`
  }
  return '全部'
}

async function loadList() {
  loading.value = true
  try {
    processes.value = await listProcesses({ keyword: keyword.value || undefined })
  } catch (e: any) {
    message.error(e?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

// === 流程详情 modal (统一入口) ===
const showDetail = ref(false)
const detailProcessId = ref('')
const detailDefaultMode = ref<'view' | 'edit'>('edit')

function openProcessModal(row: any) {
  detailProcessId.value = row.id
  detailDefaultMode.value = 'edit'
  showDetail.value = true
}

function openCreateProcess() {
  detailProcessId.value = ''
  detailDefaultMode.value = 'edit'
  showDetail.value = true
}

function onProcessSaved() {
  loadList()
}

// 详情 modal 中的 "复制此流程" 按钮 -> modal 已自动关 + 已 toast, list 重新拉即可
function onProcessCopied(_newProcessId: string) {
  loadList()
}

onMounted(() => loadList())
</script>

<style scoped>
/* 模型 B：固定标题 + 内部滚动三件套（与 AccountSettings/DemandConfig 同款） */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-header {
  flex-shrink: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.recruitment-process {
  padding: 20px 24px;
}

/* 2026-08-29 UX 整改：行高统一 + 标签列中线对齐；X-05 严禁硬编码颜色 */
.recruitment-process :deep(.n-data-table .n-data-table-tr .n-data-table-td) {
  vertical-align: middle;
}
</style>
