<template>
  <div class="page-container recruitment-process">
<div class="page-body">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.RecruitmentProcess.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.RecruitmentProcess.s2') }}</p>
      </div>
    </div>

    <div class="toolbar">
      <n-input v-model:value="keyword" :placeholder="t('pages.settings.RecruitmentProcess.s3')" clearable style="width: 220px">
        <template #prefix><n-icon :component="SearchOutline" /></template>
      </n-input>
      <div class="spacer"></div>
      <n-button type="primary" class="gradient-btn" @click="openCreateProcess">
        <template #icon><n-icon :component="AddOutline" /></template>
        {{ t('pages.settings.RecruitmentProcess.s4') }}
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
import { useI18n } from 'vue-i18n'
import { ref, onMounted, h, computed } from 'vue'
import { useMessage, NButton, NTag, NIcon, NDataTable, NPopconfirm, NSpace } from 'naive-ui'
import { AddOutline, SearchOutline } from '@vicons/ionicons5'
import { listProcesses, deleteProcess } from '../../api/recruitment-process'
import api from '../../api/auth'
import ProcessDetailModal from './ProcessDetailModal.vue'
const { t } = useI18n()

const message = useMessage()
const keyword = ref('')
const processes = ref<any[]>([])
const loading = ref(false)
// 2026-09-08: 适用部门列需从结构化 applicable_scope 提取部门 ID 并映射成名称，
// 先拉一次部门选项建 id->name 映射（与 ProcessDetailModal.loadScopeOptions 同源）。
const deptMap = ref<Record<string, string>>({})
async function loadDepartments() {
  try {
    const res = await api.get('/departments/')
    const list = Array.isArray(res) ? res : (res?.data?.data ?? res?.data ?? [])
    const map: Record<string, string> = {}
    for (const d of list) map[String(d.id)] = d.name
    deptMap.value = map
  } catch {
    // 部门解析失败不阻塞列表，列回退显示 ID
  }
}
// 2026-08-29 UX 整改：表头固定 + 行高统一。表格高度 = 视窗高 - 上方累计(标题/工具条/分页)。
// 2026-08-30 UX 二改：56→44 + td 垂直 padding 10→6，压缩行间距（兵哥嫌"行间距太大"）
const TABLE_ROW_HEIGHT = 44
const tableMaxHeight = computed(() => {
  if (typeof window === 'undefined') return 560
  // 预留分页器 64 + page-header 80 + toolbar 56 + page-body gap 32 ≈ 232
  return Math.max(320, window.innerHeight - 232)
})

const columns = computed(() => [
  { title: t('pages.settings.RecruitmentProcess.s5'), key: 'code', width: 100 },
  { title: t('pages.settings.RecruitmentProcess.s6'), key: 'name', width: 200, ellipsis: true, ellipsisProps: { tooltip: true } },
  {
    title: t('pages.settings.RecruitmentProcess.s7'),
    key: 'applicableScope',
    width: 150,
    ellipsis: true,
    ellipsisProps: { tooltip: true },
    render: (r: any) => formatScopeDepts(r.applicableScope),
  },
  {
    title: t('pages.settings.RecruitmentProcess.s8'),
    key: 'stageCount',
    width: 80,
    render: (row: any) => row.stageCount ?? row._count?.links ?? 0,
  },
  {
    title: t('pages.settings.RecruitmentProcess.s9'),
    key: 'status',
    width: 90,
    render: (row: any) => {
      const enabled = row.status === 'ENABLED'
      return h(NTag, { type: enabled ? 'success' : 'default' }, { default: () => enabled ? t('pages.settings.RecruitmentProcess.s10') : t('pages.settings.RecruitmentProcess.s11') })
    },
  },
  { title: t('pages.settings.RecruitmentProcess.s12'), key: 'updatedBy', width: 120, ellipsis: true, ellipsisProps: { tooltip: true }, render: (r: any) => r.updatedBy?.realName || r.updatedBy?.username || '-' },
  { title: t('pages.settings.RecruitmentProcess.s13'), key: 'updatedAt', width: 170, ellipsis: true, ellipsisProps: { tooltip: true }, render: (r: any) => formatDate(r.updatedAt) },
  {
    title: t('pages.settings.RecruitmentProcess.s14'),
    key: 'action',
    width: 160,
    fixed: 'right' as const,
    render: (row: any) => h(NSpace, { size: 'small' }, () => [
      h(NButton, {
        size: 'small',
        type: 'primary',
        text: true,
        onClick: () => openProcessModal(row),
      }, { default: () => t('pages.settings.RecruitmentProcess.s15') }),
      // 2026-09-08: 流程增加删除入口。is_template=True 的流程不可删（属预置模板），
      // 被需求引用的不可删（后端 PermissionDenied 兜底，FE 用 referenceCount 提前禁用）。
      h(NPopconfirm, {
        onPositiveClick: () => handleDelete(row),
        disabled: row.isTemplate || (row.referenceCount ?? 0) > 0,
      }, {
        trigger: () => h(NButton, {
          size: 'small',
          type: 'error',
          text: true,
          disabled: row.isTemplate || (row.referenceCount ?? 0) > 0,
        }, { default: () => t('pages.settings.RecruitmentProcess.s16') }),
        default: () => row.isTemplate
          ? t('pages.settings.RecruitmentProcess.s17')
          : (row.referenceCount ?? 0) > 0
            ? t('pages.settings.RecruitmentProcess.s18', { count: row.referenceCount })
            : t('pages.settings.RecruitmentProcess.s19'),
      }),
    ]),
  },
])

function formatDate(s: string) {
  return s ? new Date(s).toLocaleString('zh-CN', { hour12: false }) : '-'
}

/** 适用部门字段 (JSON 数组) */
function formatDepts(d: any): string {
  if (!d) return t('pages.settings.RecruitmentProcess.s20')
  if (Array.isArray(d)) {
    if (d.length === 0) return t('pages.settings.RecruitmentProcess.s20')
    if (d.length <= 2) return d.join(', ')
    return `${d.slice(0, 2).join(', ')} +${d.length - 2}`
  }
  return t('pages.settings.RecruitmentProcess.s20')
}

/** 从结构化 applicable_scope 提取部门条件，映射成名称；无部门条件 = 全部。
 *  兼容新格式 scope.indicators 与旧格式 scope.items（与 ProcessDetailModal.findIndicator 一致）。 */
function formatScopeDepts(scope: any): string {
  if (!scope) return t('pages.settings.RecruitmentProcess.s20')
  const list = scope.indicators || scope.items
  if (!Array.isArray(list)) return t('pages.settings.RecruitmentProcess.s20')
  const deptIds = list
    .filter((it: any) => it && it.key === 'department' && it.mode === 'include' && Array.isArray(it.values))
    .flatMap((it: any) => it.values)
  if (deptIds.length === 0) return t('pages.settings.RecruitmentProcess.s20')
  const names = deptIds.map((id: any) => deptMap.value[String(id)] || String(id))
  if (names.length <= 2) return names.join('、')
  return `${names.slice(0, 2).join('、')} ${t('pages.settings.RecruitmentProcess.s22', { count: names.length })}`
}

async function loadList() {
  loading.value = true
  try {
    processes.value = await listProcesses({ keyword: keyword.value || undefined })
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('pages.settings.RecruitmentProcess.s23'))
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

// 2026-09-08: 删除流程。后端 perform_destroy 走 is_process_referenced 校验 + soft_delete。
// 422（被引用）/ 4xx 的错误信息直接 toast 给用户。
async function handleDelete(row: any) {
  if (row.isTemplate) {
    message.warning(t('pages.settings.RecruitmentProcess.s17'))
    return
  }
  if ((row.referenceCount ?? 0) > 0) {
    message.warning(t('pages.settings.RecruitmentProcess.s18', { count: row.referenceCount }))
    return
  }
  try {
    await deleteProcess(row.id)
    message.success(t('pages.settings.RecruitmentProcess.s24', { name: row.name }))
    loadList()
  } catch (e: any) {
    const errBody = e?.response?.data
    message.error(errBody?.message || errBody?.detail || t('pages.settings.RecruitmentProcess.s25'))
  }
}

onMounted(async () => { await loadDepartments(); loadList() })
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
  /* 顶部/底部间距由全局 .settings-scroll .page-header（glass.css）统一提供：
     margin-top:0、padding-top:0，底部走 .page-body 的 gap（全局 .page-body>.page-header{margin-bottom:0} 兜底）。
     scoped 不再写 padding/margin，避免与全局叠加造成跨页顶部留白不一致（2026-09-30）。 */
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  /* 2026-08-30 UX 四改：gap 16px→12px，缓解 11 层嵌套 + 多 padding 叠加的视觉膨胀 */
  gap: var(--space-3);
}

.recruitment-process {
  /* 2026-08-30 UX 五改：容器外边距交还 SettingsLayout 统一管控（.settings-scroll 20px + 清零规则 !important），
     本处不再设 padding，避免与 .settings-scroll 叠加成 32px（见 SETTINGS_LAYOUT_DIAGNOSIS.md §2） */
}

/* 2026-08-29 UX 整改：行高统一 + 标签列中线对齐；X-05 严禁硬编码颜色 */
/* 2026-08-30 UX 三改：补 padding:6px 12px !important 把行内垂直空白从 Naive 默认 ~10px 收到 6px，让 row-height=44 真正生效。
   Naive UI 当前版本 themeOverrides 类型不含 tdPaddingMedium/thPaddingMedium（cssr vars 存在但未暴露给类型），
   全靠此 scoped CSS 兜底。 */
.recruitment-process :deep(.n-data-table .n-data-table-tr .n-data-table-td) {
  vertical-align: middle;
  padding: 6px 12px !important;
}
</style>
