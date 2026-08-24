<template>
  <div class="page-container recruitment-process">

    <div class="page-body">
    <div class="page-header">
      <div>
        <h1 class="page-title">招聘流程管理</h1>
        <p class="page-subtitle">定义招聘流程及其阶段编排</p>
      </div>
      <n-space>
        <n-input v-model:value="keyword" placeholder="搜索流程名称" clearable style="width: 220px" />
        <n-button type="primary" @click="openCreateProcess">
          <template #icon><n-icon :component="AddOutline" /></template>
          新建流程
        </n-button>
      </n-space>
    </div>

    <div class="kpi-row">
      <div class="kpi-card"><span class="kpi-label">流程总数</span><span class="kpi-value">{{ processes.length }}</span></div>
    </div>

    <n-data-table
      :columns="columns"
      :data="processes"
      :loading="loading"
      :pagination="{ pageSize: 20 }"
      :row-key="(r) => r.id"
    />

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
import { ref, onMounted, h } from 'vue'
import { useMessage, NButton, NTag, NIcon, NDataTable } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { listProcesses } from '../../api/recruitment-process'
import ProcessDetailModal from './ProcessDetailModal.vue'

const message = useMessage()
const keyword = ref('')
const processes = ref<any[]>([])
const loading = ref(false)

const columns = [
  { title: '流程编号', key: 'code', width: 100 },
  { title: '流程名称', key: 'name', width: 200 },
  {
    title: '适用部门',
    key: 'applicableDepartments',
    width: 140,
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
  { title: '最后修改人', key: 'updater', width: 120, render: (r: any) => r.updater?.realName || '-' },
  { title: '最后修改时间', key: 'updatedAt', width: 170, render: (r: any) => formatDate(r.updatedAt) },
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
/* === 2026-08-24 page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
   - 标题区固定（flex-shrink: 0）→ 配置/操作按钮始终可触达
   - 内容区自己滚（flex: 1; min-height: 0; overflow-y: auto）→ 与外层 .settings-scroll 滚职责分离
   - 结构上让 sticky header 天然占据物理空间 → 解决下方内容穿透 header 的视觉 bug === */
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
  padding-top: 8px;
}


/* === 2026-08-24 page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
   - 标题区固定（flex-shrink: 0）→ 配置/操作按钮始终可触达
   - 内容区自己滚（flex: 1; min-height: 0; overflow-y: auto）→ 与外层 .settings-scroll 滚职责分离
   - 结构上让 sticky header 天然占据物理空间 → 解决下方内容穿透 header 的视觉 bug === */
/* === 2026-08-24 page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
   - 标题区固定（flex-shrink: 0）→ 配置/操作按钮始终可触达
   - 内容区自己滚（flex: 1; min-height: 0; overflow-y: auto）→ 与外层 .settings-scroll 滚职责分离
   - 结构上让 sticky header 天然占据物理空间 → 解决下方内容穿透 header 的视觉 bug === */
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
  padding-top: 8px;
}


.recruitment-process {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  min-height: 100%;
}
/* 删除 scoped .page-header margin-bottom 覆盖（规范：复用全局 glass.css 通栏分隔线规则） */
.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.recruitment-process :deep(.n-data-table) {
  flex: 1;
}
.recruitment-process :deep(.n-data-table-wrapper) {
  min-height: 200px;
}
</style>
