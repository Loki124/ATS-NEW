<template>
  <div class="page-container recruitment-process">
    <div class="data-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">{{ t('pages.settings.RecruitmentProcess.s1') }}</h1>
          <p class="page-subtitle">{{ t('pages.settings.RecruitmentProcess.s2') }}</p>
        </div>
      </div>

      <div class="glass-panel panel-shell">
        <div class="toolbar">
          <n-input
            v-model:value="keyword"
            class="process-search"
            :placeholder="t('pages.settings.RecruitmentProcess.s3')"
            clearable
          >
            <template #prefix><n-icon :component="SearchOutline" /></template>
          </n-input>
          <div class="spacer"></div>
          <n-button type="primary" class="gradient-btn" @click="openCreateProcess">
            <template #icon><n-icon :component="AddOutline" /></template>
            {{ t('pages.settings.RecruitmentProcess.s4') }}
          </n-button>
        </div>

        <div class="table-wrap table-fade">
          <n-data-table
            :columns="columns"
            :data="processes"
            :loading="loading"
            :pagination="localPagination()"
            :row-key="(r) => r.id"
            flex-height
            :row-height="TABLE_ROW_HEIGHT"
          />
        </div>
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

      <!-- 2026-10-16 方案 A：流程被需求引用时，提供「改绑引用」解钉死入口 -->
      <ProcessRebindModal
        v-model:show="showRebind"
        :process-id="rebindProcessId"
        :process-name="rebindProcessName"
        @rebound="onRebindDone"
      />
    </div><!-- /.data-body -->
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, onMounted, h, computed } from 'vue'
import { useMessage, NButton, NTag, NIcon, NDataTable, NPopconfirm, NSpace } from 'naive-ui'
import { AddOutline, SearchOutline, CreateOutline, TrashOutline, SwapHorizontalOutline } from '@vicons/ionicons5'
import { listProcesses, deleteProcess } from '../../api/recruitment-process'
import api from '../../api/auth'
import ProcessDetailModal from './ProcessDetailModal.vue'
import ProcessRebindModal from './ProcessRebindModal.vue'
import { localPagination } from '@/composables/useTablePagination'
import { column, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns'
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

const columns = computed(() => [
  column({
    title: t('pages.settings.RecruitmentProcess.s5'),
    key: 'code',
    width: 110,
    // 视觉重塑：流程编号渲染为等宽字体品牌浅底 chip（替代裸文本，增强扫读锚点）
    render: (r: any) => h('span', { class: 'code-chip' }, String(r.code ?? '-')),
  }, 'short'),
  column({ title: t('pages.settings.RecruitmentProcess.s6'), key: 'name', width: 200, ellipsis: true }, 'short'),
  column({
    title: t('pages.settings.RecruitmentProcess.s7'),
    key: 'applicableScope',
    width: 150,
    ellipsis: true,
    render: (r: any) => formatScopeDepts(r.applicableScope),
  }, 'short'),
  column({
    title: t('pages.settings.RecruitmentProcess.s8'),
    key: 'stageCount',
    width: 90,
    // 视觉重塑：阶段数渲染为中性玻璃 pill（tabular-nums 对齐）
    render: (row: any) => h('span', { class: 'stage-count' }, String(row.stageCount ?? row._count?.links ?? 0)),
  }, 'numeric'),
  column({
    title: t('pages.settings.RecruitmentProcess.s9'),
    key: 'status',
    width: 90,
    render: (row: any) => {
      const enabled = row.status === 'ENABLED'
      // 视觉重塑：round + 无边框 = 现代胶囊状态签（语义色仍走 Naive success/default，暗色由 tokens 联动）
      return h(NTag, { type: enabled ? 'success' : 'default', round: true, bordered: false, size: 'small' }, { default: () => enabled ? t('pages.settings.RecruitmentProcess.s10') : t('pages.settings.RecruitmentProcess.s11') })
    },
  }, 'short'),
  column({ title: t('pages.settings.RecruitmentProcess.s12'), key: 'updatedBy', width: 120, ellipsis: true, render: (r: any) => r.updatedBy?.realName || r.updatedBy?.username || '-' }, 'short'),
  column({ title: t('pages.settings.RecruitmentProcess.s13'), key: 'updatedAt', width: 170, ellipsis: true, render: (r: any) => formatDate(r.updatedAt) }, 'short'),
  column({
    title: t('pages.settings.RecruitmentProcess.s14'),
    key: 'action',
    width: 160,
    fixed: 'right' as const,
    render: (row: any) => {
      // 2026-10-16 方案 A：被需求引用（referenceCount>0）时，删除是死路（后端 PROTECT 兜死），
      // 与其显示一个永远 disabled 的删除按钮，不如换成「改绑引用」给真正出路（见 ProcessRebindModal）。
      // 改绑成功后引用数归零，该行的操作区会自动切回「编辑 + 删除」。
      const referenced = !row.isTemplate && (row.referenceCount ?? 0) > 0
      const children = [
        h(NButton, {
          size: OP_ACTION_BUTTON_SIZE,
          quaternary: true,
          type: 'primary',
          onClick: () => openProcessModal(row),
        }, { icon: () => h(NIcon, null, { default: () => h(CreateOutline) }), default: () => t('pages.settings.RecruitmentProcess.s15') }),
      ]
      if (referenced) {
        children.push(h(NButton, {
          size: OP_ACTION_BUTTON_SIZE,
          quaternary: true,
          type: 'warning',
          onClick: () => openRebind(row),
        }, { icon: () => h(NIcon, null, { default: () => h(SwapHorizontalOutline) }), default: () => t('pages.settings.RecruitmentProcess.s26') }))
      } else {
        children.push(
          // 2026-09-08: 流程增加删除入口。is_template=True 的流程不可删（属预置模板），
          // 被需求引用的已在上面走「改绑引用」，这里只处理非引用行。
          h(NPopconfirm, {
            onPositiveClick: () => handleDelete(row),
            disabled: row.isTemplate,
          }, {
            trigger: () => h(NButton, {
              size: OP_ACTION_BUTTON_SIZE,
              quaternary: true,
              type: 'error',
              disabled: row.isTemplate,
            }, { icon: () => h(NIcon, null, { default: () => h(TrashOutline) }), default: () => t('pages.settings.RecruitmentProcess.s16') }),
            default: () => row.isTemplate
              ? t('pages.settings.RecruitmentProcess.s17')
              : t('pages.settings.RecruitmentProcess.s19'),
          }),
        )
      }
      return h(NSpace, { size: 8, wrap: false }, () => children)
    },
  }, 'control'),
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

// 2026-10-16 方案 A：流程被需求引用时，提供「改绑引用」入口解钉死（否则后端 PROTECT 永久钉死）。
// 点击「改绑引用」打开 ProcessRebindModal，弹窗内逐条把引用需求改绑到其他流程；
// 改绑成功后本流程 referenceCount 归零，列表重载后该行操作区自动切回「编辑 + 删除」。
const showRebind = ref(false)
const rebindProcessId = ref('')
const rebindProcessName = ref('')
function openRebind(row: any) {
  rebindProcessId.value = row.id
  rebindProcessName.value = row.name
  showRebind.value = true
}
function onRebindDone() {
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
     margin-top:0、padding-top:0，底部走 .data-body 的 gap（全局 .data-body>.page-header{margin-bottom:0} 兜底）。
     scoped 不再写 padding/margin，避免与全局叠加造成跨页顶部留白不一致（2026-09-30）。 */
}
.data-body {
  flex: 1;
  min-height: 0;
  overflow-y: hidden;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/* 玻璃面板内 = 工具条 + table-wrap(flex-height)，与身份管理 RolesTab 同构 */

.recruitment-process {
  /* 2026-08-30 UX 五改：容器外边距交还 SettingsLayout 统一管控（.settings-scroll 20px + 清零规则 !important），
     本处不再设 padding，避免与 .settings-scroll 叠加成 32px（见 SETTINGS_LAYOUT_DIAGNOSIS.md §2） */
}

/* =============================================================
 * 2026-10-02 视觉重塑（兵哥：改善外观简陋 → 现代专业）
 * 原则：全部走 Liquid Glass v2 token（X-05 禁硬编码颜色），
 *       布局结构 / 数据流 / 交互逻辑零改动，仅提升视觉呈现。
 * ============================================================= */

/* —— 工具条：搜索框定宽（替代原 inline style，窄屏 flex-wrap 自然折行）—— */
.process-search {
  width: 240px;
  max-width: 240px;
  flex-shrink: 0;
}

/* —— 表格细节 —— */
/* 2026-08-30 UX 三改：padding 6px 12px 让 row-height=44 真正生效（Naive 未暴露 tdPadding 变量，scoped 兜底） */
.recruitment-process :deep(.n-data-table .n-data-table-tr .n-data-table-td) {
  vertical-align: middle;
  padding: 8px 8px !important;
}
/* 表头：小号灰字 + 字距（ quieter header → 数据更突出，CampusControl 同款层次） */
.recruitment-process :deep(.n-data-table-th) {
  font-size: var(--fs-12);
  letter-spacing: 0.04em;
  color: var(--ink-faint) !important;
}
/* 流程编号：等宽字体品牌浅底 chip —— 扫读锚点，编号可比对 */
.code-chip {
  display: inline-block;
  padding: 1px 8px;
  border-radius: var(--radius-sm);
  background: var(--brand-tint);
  color: var(--brand-text);
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  font-weight: 600;
  letter-spacing: 0.02em;
}
/* 暗色模式：--brand-text 固定指向 --brand-900(深navy)，在深色玻璃上不可读。
   改用亮阶 --brand-200 保证对比度（X-05 仍走 token，不硬编码）。 */
body.dark .code-chip {
  color: var(--brand-200);
}
/* 阶段数：中性玻璃 pill（与 .glass-tag 同源 token） */
.stage-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  padding: 1px 8px;
  border-radius: var(--radius-pill);
  background: var(--overlay-glass-mid);
  border: 1px solid var(--glass-border);
  color: var(--ink-soft);
  font-size: var(--fs-12);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

/* —— 入场动效：表格延迟淡入（prefers-reduced-motion 由
      tokens.css 全局降级规则兜底，无需此处重复）—— */
@keyframes rp-fade-up {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.table-fade {
  animation: rp-fade-up var(--duration-slow) var(--ease-out) 0.18s both;
}
</style>
