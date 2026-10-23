<template>
  <div class="page-container">
    <div class="page-body">
      <n-tabs v-model:value="activeTab" type="line" class="page-tabs" @update:value="onTabChange">
        <n-tab-pane name="revenue" tab="收入统计" />
        <n-tab-pane name="bill" tab="结算账单" />
        <n-tab-pane name="price" tab="定价管理" />
      </n-tabs>

      <!-- ① 收入统计 -->
      <template v-if="activeTab === 'revenue'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">台账</span>
            <n-input
              v-model:value="revenueSearch"
              aria-label="输出部门或月份"
              class="toolbar-search"
              placeholder="搜索输出部门或月份"
              clearable
              @keyup.enter="loadRevenue"
            >
              <template #prefix><n-icon :component="SearchOutline" /></template>
            </n-input>
          </div>
          <div class="filter">
            <span class="filter-label">月份</span>
            <n-select
              v-model:value="revenueYm"
              aria-label="月份"
              class="toolbar-select"
              :options="ymOptions"
              placeholder="全部月份"
              clearable
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="revenueLoading" @click="loadRevenue">查询台账</n-button>
        </div>

        <div class="stat-strip">
          <div class="stat-card">
            <div class="stat-label">台账合计金额</div>
            <div class="stat-value num">{{ revenueTotalAmount }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">台账合计出勤</div>
            <div class="stat-value num">{{ revenueTotalDays }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">覆盖输出部门</div>
            <div class="stat-value num">{{ revenueDeptCount }}</div>
          </div>
        </div>

        <div v-if="revenueError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">收入台账没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，台账数据仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ revenueError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(revenueError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="revenueLoading" @click="loadRevenue">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="revenueLoading && !revenueRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="revenueColumns"
            :data="revenueRows"
            :loading="revenueLoading"
            :bordered="false"
            :scroll-x="REVENUE_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: RevenueRecord) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="revenueEmptyText" size="small">
                <template #extra>
                  <n-button v-if="revenueHasFilter" size="small" @click="clearRevenueFilter">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ② 结算账单 -->
      <template v-if="activeTab === 'bill'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">状态</span>
            <n-select
              v-model:value="billStatus"
              aria-label="账单状态"
              class="toolbar-select"
              :options="billStatusOptions"
              placeholder="全部状态"
              clearable
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="billLoading" @click="loadBills">刷新账单</n-button>
        </div>

        <div v-if="billError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">结算账单没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，账单数据仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ billError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(billError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="billLoading" @click="loadBills">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="billLoading && !billRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="billColumns"
            :data="billRows"
            :loading="billLoading"
            :bordered="false"
            :scroll-x="BILL_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: Bill) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="billEmptyText" size="small">
                <template #extra>
                  <n-button v-if="billStatus" size="small" @click="billStatus = null; loadBills()">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ③ 定价管理 -->
      <template v-if="activeTab === 'price'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">定价方案</span>
            <n-select
              v-model:value="schemeId"
              aria-label="定价方案"
              class="toolbar-select-wide"
              :options="schemeOptions"
              placeholder="请选择定价方案"
              @update:value="loadSchemes"
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="priceLoading" @click="loadSchemes">刷新分档</n-button>
          <n-button type="primary" :disabled="!schemeId" @click="openTierCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增分档
          </n-button>
        </div>

        <div v-if="priceError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">定价分档没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，定价方案仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ priceError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(priceError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="priceLoading" @click="loadSchemes">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="priceLoading && !tierRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="tierColumns"
            :data="tierRows"
            :loading="priceLoading"
            :bordered="false"
            :scroll-x="TIER_SCROLL_X"
            :pagination="false"
            :row-key="(row: TierRow) => row.key"
            flex-height
          >
            <template #empty>
              <n-empty :description="tierEmptyText" size="small">
                <template #extra>
                  <n-button v-if="schemeId" size="small" @click="schemeId = null; loadSchemes()">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- 分档 新增 / 编辑 弹窗 -->
      <n-modal
        v-model:show="tierFormVisible"
        preset="card"
        :title="tierEditing ? '编辑定价分档' : '新增定价分档'"
        :style="{ width: '680px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(480px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="tierForm" label-placement="top">
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="排名区间" required>
                <n-input v-model:value="tierForm.rank" placeholder="如 1-10" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="结算单价" required>
                <n-input-number v-model:value="tierForm.price" :min="0" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="底价">
                <n-input-number v-model:value="tierForm.floor" :min="0" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="交易价允许区间">
                <n-space :wrap="false" :size="8" style="width: 100%">
                  <n-input-number v-model:value="tierForm.min" :min="0" style="flex: 1" />
                  <n-input-number v-model:value="tierForm.max" :min="0" style="flex: 1" />
                </n-space>
              </n-form-item>
            </n-grid-item>
          </n-grid>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="tierFormVisible = false">取消</n-button>
            <n-button type="primary" :loading="tierSaving" :disabled="tierSaving" @click="saveTier">保存分档</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 通用确认框（确认账单等高影响操作） -->
      <n-modal
        v-model:show="confirmVisible"
        preset="card"
        :title="confirmTitle"
        :style="{ width: '560px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(320px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <div class="confirm-body">{{ confirmText }}</div>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="confirmVisible = false">暂不操作</n-button>
            <n-button type="primary" :loading="confirmLoading" :disabled="confirmLoading" @click="confirmSubmit">
              确认账单
            </n-button>
          </div>
        </template>
      </n-modal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NDataTable,
  NEmpty,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NIcon,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NSkeleton,
  NSpace,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
} from 'naive-ui'
import { AddOutline, AlertCircleOutline, CreateOutline, SearchOutline, TrashOutline } from '@vicons/ionicons5'
import {
  listBills,
  listPriceSchemes,
  listRevenueRecords,
  updateBill,
  updatePriceScheme,
  type Bill,
  type PriceScheme,
  type RevenueRecord,
} from '../../api/campusPlacement'
import { extractError } from '../../utils/campus'

const message = useMessage()

type TabKey = 'revenue' | 'bill' | 'price'
const activeTab = ref<TabKey>('revenue')

const BILL_STATUS_OPTIONS = ['待确认', '已确认'].map((v) => ({ label: v, value: v }))
const billStatusOptions = BILL_STATUS_OPTIONS

/* ───────────────────────── 通用工具 ───────────────────────── */

function textCell(text: unknown, width = 140) {
  const s = text == null || text === '' ? '—' : String(text)
  return h('span', { title: s, style: { display: 'inline-block', maxWidth: `${width}px`, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, s)
}

function numCell(value: unknown) {
  return h('span', { style: { fontVariantNumeric: 'tabular-nums' } }, value == null ? '—' : String(value))
}

function money(value: unknown) {
  const n = Number(value)
  if (value == null || Number.isNaN(n)) return '—'
  return h('span', { style: { fontVariantNumeric: 'tabular-nums' } }, n.toLocaleString('zh-CN'))
}

async function copyText(text: string) {
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      message.success('错误信息已复制')
      return
    }
  } catch {
    /* 降级提示 */
  }
  message.warning('复制失败，请手动选中详情内容复制')
}

/* ───────────────────────── ① 收入统计 ───────────────────────── */

const revenueRows = ref<RevenueRecord[]>([])
const revenueLoading = ref(false)
const revenueError = ref('')
const revenueSearch = ref('')
const revenueYm = ref<string | null>(null)

const revenueHasFilter = computed(() => Boolean(revenueSearch.value.trim() || revenueYm.value))
const revenueEmptyText = computed(() => (revenueHasFilter.value ? '没有符合筛选条件的台账' : '暂无数据'))

const ymOptions = computed(() => {
  const set = new Set<string>()
  revenueRows.value.forEach((r) => {
    if (r.ym) set.add(r.ym)
  })
  return [...set].map((v) => ({ label: v, value: v }))
})

const revenueTotalAmount = computed(() =>
  revenueRows.value.reduce((sum, r) => sum + (Number(r.amount) || 0), 0).toLocaleString('zh-CN'),
)
const revenueTotalDays = computed(() =>
  revenueRows.value.reduce((sum, r) => sum + (Number(r.attendDays) || 0), 0),
)
const revenueDeptCount = computed(() => new Set(revenueRows.value.map((r) => r.outputDept || '')).size)

async function loadRevenue() {
  revenueLoading.value = true
  revenueError.value = ''
  try {
    const kw = revenueSearch.value.trim()
    const rows = await listRevenueRecords({ ym: revenueYm.value ?? undefined })
    revenueRows.value = kw
      ? rows.filter((r) => `${r.outputDept}${r.ym}`.includes(kw))
      : rows
  } catch (e: any) {
    revenueError.value = extractError(e)
    revenueRows.value = []
  } finally {
    revenueLoading.value = false
  }
}

function clearRevenueFilter() {
  revenueSearch.value = ''
  revenueYm.value = null
  loadRevenue()
}

const revenueColumns = computed(() => [
  { title: '月份', key: 'ym', width: 110, render: (row: RevenueRecord) => row.ym || '—' },
  { title: '校招生', key: 'personName', width: 120, ellipsis: true, render: (row: RevenueRecord) => textCell(row.personName || row.person, 100) },
  { title: '输出部门', key: 'outputDept', width: 140, ellipsis: true, render: (row: RevenueRecord) => textCell(row.outputDept, 120) },
  { title: '阶段', key: 'stage', width: 110, ellipsis: true, render: (row: RevenueRecord) => textCell(row.stage, 90) },
  { title: '出勤', key: 'attendDays', width: 90, render: (row: RevenueRecord) => numCell(row.attendDays) },
  { title: '计价规则', key: 'rule', width: 140, ellipsis: true, render: (row: RevenueRecord) => textCell(row.rule, 120) },
  { title: '单价', key: 'unitPrice', width: 120, render: (row: RevenueRecord) => money(row.unitPrice) },
  { title: '金额', key: 'amount', width: 130, render: (row: RevenueRecord) => money(row.amount) },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: RevenueRecord) =>
      h(NTag, { type: row.status === '已确认' ? 'success' : 'warning', size: 'small' }, {
        default: () => row.status || '—',
      }),
  },
])

const REVENUE_SCROLL_X = 1160

/* ───────────────────────── ② 结算账单 ───────────────────────── */

const billRows = ref<Bill[]>([])
const billLoading = ref(false)
const billError = ref('')
const billStatus = ref<string | null>(null)

const billEmptyText = computed(() => (billStatus.value ? '没有符合筛选条件的账单' : '暂无数据'))

async function loadBills() {
  billLoading.value = true
  billError.value = ''
  try {
    billRows.value = await listBills({ status: billStatus.value ?? undefined })
  } catch (e: any) {
    billError.value = extractError(e)
    billRows.value = []
  } finally {
    billLoading.value = false
  }
}

const billColumns = computed(() => [
  { title: '账单号', key: 'billNo', width: 180, ellipsis: true, render: (row: Bill) => textCell(row.billNo, 160) },
  { title: '业务部门', key: 'businessDept', width: 150, ellipsis: true, render: (row: Bill) => textCell(row.businessDept, 130) },
  { title: '账期', key: 'period', width: 120, render: (row: Bill) => row.period || '—' },
  { title: '结算人数', key: 'personCount', width: 110, render: (row: Bill) => numCell(row.personCount) },
  { title: '金额', key: 'amount', width: 140, render: (row: Bill) => money(row.amount) },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: Bill) =>
      h(NTag, { type: row.status === '已确认' ? 'success' : 'warning', size: 'small' }, {
        default: () => row.status || '—',
      }),
  },
  {
    title: '确认时间',
    key: 'confirmedAt',
    width: 170,
    render: (row: Bill) => (row.confirmedAt ? h('span', { title: new Date(row.confirmedAt).toLocaleString('zh-CN') }, new Date(row.confirmedAt).toLocaleDateString('zh-CN')) : '—'),
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    fixed: 'right' as const,
    render: (row: Bill) =>
      row.status === '已确认'
        ? h('span', { style: { fontSize: 'var(--text-small)', color: 'var(--ink-faint)' } }, '无需确认')
        : h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => askConfirmBill(row) }, { default: () => '确认账单' }),
  },
])

const BILL_SCROLL_X = 1090

/* ── 确认账单（高影响）── */
const confirmVisible = ref(false)
const confirmTitle = ref('')
const confirmText = ref('')
const confirmLoading = ref(false)
const confirmAction = ref<null | (() => Promise<void>)>(null)

function askConfirmBill(row: Bill) {
  confirmTitle.value = '确认结算账单'
  confirmText.value = `确认「${row.billNo}」（${row.businessDept || '业务部门'}，账期 ${row.period || '—'}，金额 ${Number(row.amount || 0).toLocaleString('zh-CN')}）后账单将锁定，不可再修改。确认账单？`
  confirmAction.value = async () => {
    await updateBill(row.id, { status: '已确认' })
    message.success('账单已确认')
    loadBills()
  }
  confirmVisible.value = true
}

async function confirmSubmit() {
  const action = confirmAction.value
  if (!action) return
  confirmLoading.value = true
  try {
    await action()
    confirmVisible.value = false
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    confirmLoading.value = false
  }
}

/* ───────────────────────── ③ 定价管理 ───────────────────────── */

const schemeRows = ref<PriceScheme[]>([])
const priceLoading = ref(false)
const priceError = ref('')
const schemeId = ref<string | null>(null)

const schemeOptions = computed(() =>
  schemeRows.value.map((s) => ({
    label: `${s.name || '未命名方案'}${s.isDefault ? '（默认）' : ''}`,
    value: String(s.id),
  })),
)

/** 分档表的一行（把方案的 tiers 摊平）。 */
interface TierRow {
  key: string
  schemeId: string
  rank: string
  price: number
  floor: number | null
  min: number | null
  max: number | null
}

const tierRows = computed<TierRow[]>(() => {
  const scheme = schemeRows.value.find((s) => String(s.id) === String(schemeId.value))
  if (!scheme) return []
  const tiers = Array.isArray(scheme.tiers) ? scheme.tiers : []
  return tiers.map((t, i) => ({
    key: `${scheme.id}-${i}`,
    schemeId: String(scheme.id),
    rank: t.rank || '',
    price: Number(t.price) || 0,
    floor: t.floor ?? null,
    min: t.min ?? null,
    max: t.max ?? null,
  }))
})

const tierEmptyText = computed(() => (schemeId.value ? '该方案还没有定价分档' : '请先选择定价方案'))

async function loadSchemes() {
  priceLoading.value = true
  priceError.value = ''
  try {
    schemeRows.value = await listPriceSchemes()
    if (schemeId.value && !schemeRows.value.some((s) => String(s.id) === String(schemeId.value))) {
      schemeId.value = null
    }
    if (!schemeId.value) {
      const def = schemeRows.value.find((s) => s.isDefault) || schemeRows.value[0]
      schemeId.value = def ? String(def.id) : null
    }
  } catch (e: any) {
    priceError.value = extractError(e)
    schemeRows.value = []
  } finally {
    priceLoading.value = false
  }
}

const tierColumns = computed(() => [
  { title: '排名区间', key: 'rank', width: 140, render: (row: TierRow) => row.rank || '—' },
  { title: '结算单价', key: 'price', width: 140, render: (row: TierRow) => money(row.price) },
  { title: '底价', key: 'floor', width: 140, render: (row: TierRow) => money(row.floor) },
  {
    title: '交易价允许区间',
    key: 'range',
    width: 200,
    render: (row: TierRow) =>
      row.min == null && row.max == null
        ? '—'
        : h('span', { style: { fontVariantNumeric: 'tabular-nums' } }, `${row.min ?? '不限'} ~ ${row.max ?? '不限'}`),
  },
  {
    title: '操作',
    key: 'actions',
    width: 170,
    fixed: 'right' as const,
    render: (row: TierRow) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openTierEdit(row) }, {
            default: () => '编辑分档',
            icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeTier(row) }, {
            default: () => '删除分档',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          }),
        ],
      }),
  },
])

const TIER_SCROLL_X = 800

const tierFormVisible = ref(false)
const tierSaving = ref(false)
const tierEditing = ref<TierRow | null>(null)
const tierForm = reactive({
  rank: '',
  price: 0,
  floor: 0,
  min: 0,
  max: 0,
})

function openTierCreate() {
  Object.assign(tierForm, { rank: '', price: 0, floor: 0, min: 0, max: 0 })
  tierEditing.value = null
  tierFormVisible.value = true
}

function openTierEdit(row: TierRow) {
  Object.assign(tierForm, {
    rank: row.rank,
    price: row.price,
    floor: row.floor ?? 0,
    min: row.min ?? 0,
    max: row.max ?? 0,
  })
  tierEditing.value = row
  tierFormVisible.value = true
}

async function saveTier() {
  const scheme = schemeRows.value.find((s) => String(s.id) === String(schemeId.value))
  if (!scheme) {
    message.warning('请先选择定价方案')
    return
  }
  if (!tierForm.rank.trim()) {
    message.warning('请填写排名区间')
    return
  }
  tierSaving.value = true
  const tiers = (Array.isArray(scheme.tiers) ? scheme.tiers.slice() : []).map((t) => ({
    rank: t.rank,
    price: Number(t.price) || 0,
    floor: t.floor ?? null,
    min: t.min ?? null,
    max: t.max ?? null,
  }))
  const next = {
    rank: tierForm.rank.trim(),
    price: Number(tierForm.price) || 0,
    floor: tierForm.floor ?? null,
    min: tierForm.min ?? null,
    max: tierForm.max ?? null,
  }
  const idx = tierEditing.value
    ? tiers.findIndex((t, i) => `${scheme.id}-${i}` === tierEditing.value!.key)
    : -1
  if (idx >= 0) tiers[idx] = next
  else tiers.push(next)
  try {
    await updatePriceScheme(String(scheme.id), { tiers })
    message.success('定价分档已保存')
    tierFormVisible.value = false
    loadSchemes()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    tierSaving.value = false
  }
}

/** 删除分档 = 中等破坏性操作 → 直接执行 + 通知撤销（R-106）。 */
async function removeTier(row: TierRow) {
  const scheme = schemeRows.value.find((s) => String(s.id) === String(schemeId.value))
  if (!scheme) return
  const tiers = (Array.isArray(scheme.tiers) ? scheme.tiers : []).filter(
    (t, i) => `${scheme.id}-${i}` !== row.key,
  )
  try {
    await updatePriceScheme(String(scheme.id), { tiers })
    message.success('定价分档已删除')
    loadSchemes()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/* ───────────────────────── 生命周期 ───────────────────────── */

function onTabChange(tab: TabKey) {
  if (tab === 'revenue') loadRevenue()
  else if (tab === 'bill') loadBills()
  else loadSchemes()
}

onMounted(() => {
  loadRevenue()
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
.page-tabs {
  flex-shrink: 0;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  flex-wrap: wrap;
}
.toolbar-search {
  width: 240px;
}
.toolbar-select {
  width: 150px;
}
.toolbar-select-wide {
  width: 280px;
}
.spacer {
  flex: 1;
}
.stat-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(var(--col-min), 1fr));
  gap: var(--space-2);
  flex-shrink: 0;
}
.stat-card {
  padding: var(--space-3);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--surface);
}
.stat-label {
  font-size: var(--text-small);
  color: var(--ink-faint);
}
.stat-value {
  margin-top: var(--space-1);
  font-size: var(--text-h3);
  font-weight: 600;
  color: var(--ink);
}
.stat-value.num {
  font-variant-numeric: tabular-nums;
}
.table-wrap {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
.confirm-body {
  font-size: var(--text-body);
  color: var(--ink-soft);
  line-height: 1.6;
  overflow-wrap: anywhere;
}
.filter {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.filter-label {
  font-size: var(--text-small);
  color: var(--ink-soft);
  white-space: nowrap;
}

.error-state {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--c-error);
  border-radius: var(--radius-md);
  background: var(--c-error-soft);
  flex-shrink: 0;
}
.error-state-icon {
  color: var(--c-error-deep);
  font-size: var(--text-h4);
  flex-shrink: 0;
}
.error-state-body {
  flex: 1;
  min-width: 0;
}
.error-state-title {
  font-size: var(--text-body);
  font-weight: 600;
  color: var(--c-error-deep);
}
.error-state-desc {
  font-size: var(--text-small);
  color: var(--ink-soft);
  margin-top: var(--space-1);
}
.error-state-detail {
  margin-top: var(--space-2);
  font-size: var(--text-meta);
  color: var(--ink-soft);
}
.error-state-code {
  margin: var(--space-1) 0;
  padding: var(--space-2);
  background: var(--surface);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
