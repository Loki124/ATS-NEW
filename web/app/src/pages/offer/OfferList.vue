<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">Offer 管理</h1>
      <n-space>
        <n-button :loading="loading" @click="handleRefresh">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
      </n-space>
    </div>

    <!-- 状态统计 -->
    <n-grid x-gap="12" y-gap="12" cols="9" responsive="screen" :item-responsive="true" class="stats-row">
      <n-gi v-for="stat in statusStats" :key="stat.key" :span="1">
        <n-card size="small" :bordered="false" class="stat-card" hoverable>
          <div class="stat-label">{{ stat.label }}</div>
          <div class="stat-value" :style="{ color: stat.color }">{{ stat.count }}</div>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 筛选 + 表格 -->
    <n-card :bordered="false" class="rounded-xl">
      <n-space class="filter-row">
        <n-select
          v-model:value="filterStatus"
          placeholder="Offer 状态"
          style="width: 140px"
          clearable
          :options="statusOptions"
          @update:value="handleFilter"
        />
        <n-button :loading="loading" @click="handleRefresh">查询</n-button>
      </n-space>

      <n-data-table
        :row-props="rowProps"
        :columns="columns"
        :data="dataSource"
        :loading="loading"
        :row-key="(row: Offer) => row.id"
        :pagination="pagination"
        @update:page="(p: number) => { pagination.page = p; loadList() }"
        @update:page-size="(s: number) => { pagination.pageSize = s; pagination.page = 1; loadList() }"
      />
    </n-card>

    <!-- 模板选择 Modal -->
    <n-modal v-model:show="templateModal.show" preset="dialog" title="生成 Offer 模板" style="width: 520px">
      <n-form :model="templateModal.form" label-placement="left" :label-width="80">
        <n-form-item label="选择模板" path="templateKey">
          <n-select
            v-model:value="templateModal.form.templateKey"
            :options="templateOptions"
            placeholder="请选择 Offer 模板"
          />
        </n-form-item>
        <n-form-item label="格式">
          <n-radio-group v-model:value="templateModal.form.format">
            <n-radio value="html">HTML (浏览器打印)</n-radio>
            <n-radio value="pdf" disabled>PDF (Phase 3)</n-radio>
          </n-radio-group>
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="templateModal.show = false">取消</n-button>
          <n-button type="primary" :loading="templateModal.loading" @click="handleGenerateTemplate">生成</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 模板预览 — Fix 3 XSS: 用 sandbox iframe 渲染后端 HTML, 禁用脚本执行 -->
    <n-modal v-model:show="previewModal.show" preset="card" title="Offer 预览" style="width: 800px">
      <iframe
        v-if="previewModal.html"
        :srcdoc="previewModal.html"
        sandbox="allow-same-origin"
        style="width: 100%; min-height: 480px; border: 0; background: var(--glass-bg-card);"
        title="Offer 预览"
      />
      <p v-else style="color: var(--n-400); text-align: center;">(无内容)</p>
    </n-modal>

    <!-- 状态转移 Modal -->
    <n-modal v-model:show="transitionModal.show" preset="dialog" :title="transitionModal.title" style="width: 480px">
      <n-form :model="transitionModal.form" label-placement="left" :label-width="80">
        <n-form-item label="目标状态">
          <n-tag :type="OFFER_STATUS_COLOR[transitionModal.form.to]">
            {{ OFFER_STATUS_LABEL[transitionModal.form.to] }}
          </n-tag>
        </n-form-item>
        <n-form-item v-if="['REJECTED', 'WITHDRAWN', 'EXPIRED'].includes(transitionModal.form.to)" label="原因">
          <n-input v-model:value="transitionModal.form.reason" type="textarea" :rows="3" placeholder="请说明原因" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="transitionModal.show = false">取消</n-button>
          <n-button type="primary" :loading="transitionModal.loading" @click="handleTransitionSubmit">确认</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted, computed } from 'vue'
import { NTag, NSpace, NButton, NIcon, NDropdown, useMessage, useDialog } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import {
  listOffers, transitionOffer, renderOffer,
  OFFER_STATUS_LABEL, OFFER_STATUS_COLOR, OFFER_TEMPLATE_LABEL,
  type Offer,
} from '../../api/offer'

const message = useMessage()
const dialog = useDialog()
// v2: 危险状态二次确认
const DANGER_STATES = ['REJECTED', 'WITHDRAWN', 'EXPIRED']

// v2: 表格行键盘可达 [T8.4]
function rowProps(row: any) {
  return {
    tabindex: 0,
    role: 'button',
    'aria-label': `Offer ${row.candidateName || row.id}`,
  }
}

const loading = ref(false)
const dataSource = ref<Offer[]>([])
const filterStatus = ref<string | null>(null)
const pagination = ref({ page: 1, pageSize: 20, itemCount: 0, pageCount: 0 })

const statusOptions = Object.entries(OFFER_STATUS_LABEL).map(([value, label]) => ({ value, label }))
const templateOptions = Object.entries(OFFER_TEMPLATE_LABEL).map(([value, label]) => ({ value, label }))

const statusStats = computed(() => {
  const counts: Record<string, number> = {}
  for (const it of (dataSource.value ?? [])) {
    counts[it.offerStatus] = (counts[it.offerStatus] || 0) + 1
  }
  return Object.entries(OFFER_STATUS_LABEL).map(([key, label]) => ({
    key, label, count: counts[key] || 0,
    color: statusColor(key),
  }))
})

function statusColor(s: string): string {
  const map: Record<string, string> = {
    DRAFT: 'var(--c-info)', PENDING_APPROVAL: 'var(--c-warning)', APPROVED: 'var(--c-success)',
    SENT: 'var(--brand-grad-a)', ACCEPTED: 'var(--c-success)', REJECTED: 'var(--c-error)', EXPIRED: 'var(--c-warning)',
  }
  return map[s] || 'var(--ink-faint)'
}

const templateModal = ref({
  show: false, loading: false,
  offerId: '',
  form: { templateKey: 'GENERAL', format: 'html' as 'html' | 'pdf' },
})

const previewModal = ref({ show: false, html: '' })
const transitionModal = ref({
  show: false, loading: false, title: '',
  form: { id: '', to: '', reason: '' },
})

const columns = computed(() => [
  { title: '岗位', key: 'jobTitle', width: 160, render: (row: Offer) => row.jobTitle || '—' },
  { title: '职级', key: 'jobLevel', width: 80, render: (row: Offer) => row.jobLevel || '—' },
  {
    title: '状态', key: 'offerStatus', width: 100,
    render: (row: Offer) => h(NTag, { type: OFFER_STATUS_COLOR[row.offerStatus], size: 'small' }, { default: () => OFFER_STATUS_LABEL[row.offerStatus] }),
  },
  { title: '期望入职', key: 'expectedJoinDate', width: 120, render: (row: Offer) => row.expectedJoinDate?.slice(0, 10) },
  { title: '试用期月薪', key: 'baseSalaryTrial', width: 110, render: (row: Offer) => row.baseSalaryTrial ? `¥ ${row.baseSalaryTrial}` : '—' },
  { title: '转正月薪', key: 'baseSalaryFormal', width: 110, render: (row: Offer) => row.baseSalaryFormal ? `¥ ${row.baseSalaryFormal}` : '—' },
  { title: '发送时间', key: 'sentAt', width: 140, render: (row: Offer) => row.sentAt?.slice(0, 16) || '—' },
  {
    title: '操作', key: 'actions', width: 180, fixed: 'right' as const,
    render: (row: Offer) => {
      // v2: 主按钮 + 下拉菜单（drop non-primary actions into dropdown）
      const items: Array<{ label: string; key: string; danger?: boolean; onClick: () => void }> = []
      if (['DRAFT', 'APPROVED', 'PENDING_APPROVAL', 'REJECTED', 'EXPIRED'].includes(row.offerStatus)) {
        items.push({ label: '生成模板', key: 'template', onClick: () => openTemplate(row) })
      }
      if (row.offerStatus === 'DRAFT') {
        items.push({ label: '提交审批', key: 'submit', onClick: () => openTransition(row, 'PENDING_APPROVAL') })
      }
      if (row.offerStatus === 'PENDING_APPROVAL') {
        items.push({ label: '审批通过', key: 'approve', onClick: () => openTransition(row, 'APPROVED') })
        items.push({ label: '撤销', key: 'withdraw1', danger: true, onClick: () => openTransition(row, 'WITHDRAWN') })
      }
      if (row.offerStatus === 'APPROVED') {
        items.push({ label: '发送', key: 'send', onClick: () => openTransition(row, 'SENT') })
        items.push({ label: '撤销', key: 'withdraw2', danger: true, onClick: () => openTransition(row, 'WITHDRAWN') })
      }
      if (row.offerStatus === 'SENT') {
        items.push({ label: '已接受', key: 'accept', onClick: () => openTransition(row, 'ACCEPTED') })
        items.push({ label: '已拒绝', key: 'reject', danger: true, onClick: () => openTransition(row, 'REJECTED') })
        items.push({ label: '过期', key: 'expire', onClick: () => openTransition(row, 'EXPIRED') })
      }
      if (row.offerStatus === 'REJECTED' || row.offerStatus === 'EXPIRED') {
        items.push({ label: '重新编辑', key: 'redraft', onClick: () => openTransition(row, 'DRAFT') })
      }
      if (items.length === 0) return '—'
      const primary = items[0]
      const rest = items.slice(1)
      return h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'tiny', onClick: primary.onClick }, { default: () => primary.label }),
          rest.length
            ? h(NDropdown, {
                options: rest.map(it => ({
                  label: it.label,
                  key: it.key,
                  ...(it.danger ? { props: { style: 'color: var(--c-error)' } } : {}),
                })),
                trigger: 'click',
                onSelect: (k: string) => rest.find(it => it.key === k)?.onClick(),
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
    const res = await listOffers({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      ...(filterStatus.value && { offerStatus: filterStatus.value }),
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

function handleRefresh() {
  pagination.value.page = 1
  loadList()
}

function handleFilter() { handleRefresh() }

function openTemplate(row: Offer) {
  templateModal.value = {
    show: true, loading: false,
    offerId: row.id,
    form: { templateKey: 'GENERAL', format: 'html' },
  }
}

async function handleGenerateTemplate() {
  templateModal.value.loading = true
  try {
    const res = await renderOffer(templateModal.value.offerId, templateModal.value.form.templateKey, 'html')
    previewModal.value.html = res.data.html || res.data.note || '(无内容)'
    templateModal.value.show = false
    previewModal.value.show = true
  } catch (e: any) {
    message.error(`生成失败: ${e.message}`)
  } finally {
    templateModal.value.loading = false
  }
}

function openTransition(row: Offer, to: string) {
  transitionModal.value = {
    show: true, loading: false,
    title: `转移状态 → ${OFFER_STATUS_LABEL[to]}`,
    form: { id: row.id, to, reason: '' },
  }
}

async function handleTransitionSubmit() {
  if (DANGER_STATES.includes(transitionModal.value.form.to) && !transitionModal.value.form.reason.trim()) {
    message.warning('请填写原因')
    return
  }
  // v2: 危险状态弹 dialog 二次确认
  if (DANGER_STATES.includes(transitionModal.value.form.to)) {
    try {
      await dialog.warning({
        title: '确认操作',
        content: `将 Offer 状态变更为「${OFFER_STATUS_LABEL[transitionModal.value.form.to]}」，是否继续？`,
        positiveText: '确认',
        negativeText: '取消',
      })
    } catch { return }
  }
  transitionModal.value.loading = true
  try {
    await transitionOffer(transitionModal.value.form.id, transitionModal.value.form.to, transitionModal.value.form.reason || undefined)
    message.success('状态已更新')
    transitionModal.value.show = false
    loadList()
  } catch (e: any) {
    message.error(`操作失败: ${e.message}`)
  } finally {
    transitionModal.value.loading = false
  }
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.page-container { padding: 24px; animation: wb-fade-up var(--duration-slow) var(--ease-out) both; }
.page-header { margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
.stats-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
/* v2 bugfix P0-B: var(--n-440) → var(--ink-faint) */
.stat-label { font-size: 12px; color: var(--ink-faint); }
.stat-value { font-size: 22px; font-weight: 600; margin-top: 4px; }
.filter-row { margin-bottom: 12px; }

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
