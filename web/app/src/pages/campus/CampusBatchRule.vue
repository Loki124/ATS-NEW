<template>
  <div class="page-container">
    <div class="page-body">
      <n-tabs v-model:value="activeTab" type="line" class="page-tabs" @update:value="onTabChange">
        <n-tab-pane name="naming" tab="命名规则" />
        <n-tab-pane name="rules" tab="批次定义" />
        <n-tab-pane name="timeline" tab="区间时间轴" />
      </n-tabs>

      <!-- ① 命名规则 -->
      <template v-if="activeTab === 'naming'">
        <div class="form-area">
          <div class="form-card">
            <div class="form-card-title">批次命名规则</div>

            <n-form :model="namingForm" label-placement="top">
              <n-form-item label="命名模板" required>
                <n-input v-model:value="namingForm.template" placeholder="如 {YY}{MM}{SEQ}" />
              </n-form-item>
              <div class="var-row">
                <span class="var-hint">点击变量追加到模板：</span>
                <n-button
                  v-for="v in TEMPLATE_VARS"
                  :key="v.token"
                  size="tiny"
                  quaternary
                  type="primary"
                  @click="insertVar(v.token)"
                >
                  {{ v.token }} · {{ v.label }}
                </n-button>
              </div>

              <!-- 响应式列数：窄屏 1 列 / ≥560px 3 列（Naive UI 的断点字符串语法）。
                   固定 3 列在 320px 视口会把「序号位数 / 序号起始值 / 序号循环粒度」
                   挤成 3 条细缝，标签断字、输入框被截断（R-201 / R-103）。 -->
              <n-grid :cols="'1 560:3'" :x-gap="16">
                <n-grid-item>
                  <n-form-item label="序号位数" required>
                    <n-input-number v-model:value="namingForm.seqWidth" :min="1" :max="4" style="width: 100%" />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item>
                  <n-form-item label="序号起始值" required>
                    <n-input-number v-model:value="namingForm.seqStart" :min="1" :max="99" style="width: 100%" />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item>
                  <n-form-item label="序号循环粒度" required>
                    <n-select v-model:value="namingForm.cycle" :options="cycleOptions" placeholder="请选择循环粒度" />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item>
                  <n-form-item label="区间判定依据" required>
                    <n-select v-model:value="namingForm.dateField" :options="dateFieldOptions" placeholder="请选择判定依据" />
                  </n-form-item>
                </n-grid-item>
              </n-grid>
              <!-- 「自动归属」开关独占一行：放在 n-grid 里用 :span="2" 会在窄屏
                   （cols 降为 1）时 span 超出列数 → 控件被挤成一条细缝（R-201 / R-103）。 -->
              <n-form-item label="新增人员时自动按区间归属批次" class="br-switch-row">
                <n-switch v-model:value="namingForm.autoApply">
                  <template #checked>自动归属</template>
                  <template #unchecked>不自动归属</template>
                </n-switch>
              </n-form-item>
            </n-form>

            <div class="preview-box">
              <div class="preview-title">实时预览</div>
              <div v-if="previewLoading" class="preview-tip">正在生成预览…</div>
              <template v-else-if="previewSamples.length">
                <div class="preview-samples">
                  <n-tag v-for="(s, i) in previewSamples" :key="`${s}-${i}`" size="small" type="info">{{ s }}</n-tag>
                </div>
                <div class="preview-meta">
                  未命中区间人数 {{ previewUnmatched }} 人 · 无批次人数 {{ previewNoBatch }} 人
                </div>
              </template>
              <div v-else class="preview-tip">暂无预览样例，请检查模板与区间定义。</div>
            </div>

            <div class="form-actions">
              <n-button :loading="namingLoading" @click="previewNaming">刷新预览</n-button>
              <n-button type="primary" :loading="namingSaving" :disabled="namingSaving" @click="saveNaming">保存规则</n-button>
            </div>
          </div>
        </div>
      </template>

      <!-- ② 批次定义 -->
      <template v-if="activeTab === 'rules'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">批次</span>
            <n-input
              v-model:value="ruleSearch"
              aria-label="批次号或批次名称"
              class="toolbar-search"
              placeholder="搜索批次号或批次名称"
              clearable
              @keyup.enter="loadRules"
            >
              <template #prefix><n-icon :component="SearchOutline" /></template>
            </n-input>
          </div>
          <div class="spacer"></div>
          <n-button :loading="ruleLoading" @click="loadRules">查询批次</n-button>
          <n-button :loading="applying" @click="askApplyRules">按规则回写批次</n-button>
          <n-button @click="askRecalc">重算批次号</n-button>
          <n-button type="primary" @click="openRuleCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增批次
          </n-button>
        </div>

        <div v-if="ruleError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">批次定义没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，你填的批次信息仍保留在本页，不会丢失。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ ruleError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(ruleError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="ruleLoading" @click="loadRules">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="ruleLoading && !ruleRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="ruleColumns"
            :data="ruleRows"
            :loading="ruleLoading"
            :bordered="false"
            :scroll-x="RULE_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: BatchRule) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="ruleEmptyText" size="small">
                <template #extra>
                  <n-button v-if="ruleSearch" size="small" @click="ruleSearch = ''; loadRules()">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ③ 区间时间轴 -->
      <template v-if="activeTab === 'timeline'">
        <div class="toolbar">
          <div class="toolbar-tip">按月份刻度铺开各批次区间，横条重叠即为区间冲突，空白即为区间空隙</div>
          <div class="spacer"></div>
          <n-button :loading="ruleLoading" @click="loadRules">刷新时间轴</n-button>
        </div>

        <div v-if="timelineIssues.length" class="issue-box">
          <n-icon class="issue-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="issue-body">
            <div v-for="(issue, i) in timelineIssues" :key="i" class="issue-line">{{ issue }}</div>
          </div>
        </div>

        <div class="timeline-area">
          <n-skeleton v-if="ruleLoading && !ruleRows.length" :repeat="6" :x-gap="12" />
          <div v-else-if="timelineBars.length" class="timeline-scroll">
            <div class="timeline-inner">
              <div class="timeline-axis">
                <div
                  v-for="t in timelineTicks"
                  :key="t.key"
                  class="timeline-tick"
                  :style="{ left: `${t.leftPct}%` }"
                >
                  {{ t.label }}
                </div>
              </div>
              <div
                v-for="bar in timelineBars"
                :key="bar.id"
                class="timeline-row"
              >
                <div class="timeline-label" :title="bar.name">{{ bar.name }}</div>
                <div class="timeline-track">
                  <div
                    class="timeline-bar"
                    :class="{ 'timeline-bar--off': !bar.enabled }"
                    :style="{ left: `${bar.leftPct}%`, width: `${bar.widthPct}%` }"
                    :title="`${bar.code} ${bar.name}：${bar.startDate} 至 ${bar.endDate}`"
                  >
                    {{ bar.code }}
                  </div>
                </div>
              </div>
            </div>
          </div>
          <n-empty v-else description="暂无数据" size="small" />
        </div>
      </template>

      <!-- 批次规则 新增 / 编辑 弹窗 -->
      <n-modal
        v-model:show="ruleFormVisible"
        preset="card"
        :title="ruleEditing ? '编辑批次规则' : '新增批次规则'"
        :style="{ width: '680px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(460px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="ruleForm" label-placement="top">
          <n-grid :cols="'1 560:2'" :x-gap="16">
            <n-grid-item>
              <n-form-item label="批次号" required>
                <n-input v-model:value="ruleForm.code" placeholder="如 202609" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="批次名称" required>
                <n-input v-model:value="ruleForm.name" placeholder="如 2026 年 9 月秋招批次" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="区间起始" required>
                <n-date-picker v-model:value="ruleForm.startTs" type="date" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="区间结束" required>
                <n-date-picker v-model:value="ruleForm.endTs" type="date" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="排序">
                <n-input-number v-model:value="ruleForm.sort" :min="1" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="启用规则">
                <n-switch v-model:value="ruleForm.enabled">
                  <template #checked>已启用</template>
                  <template #unchecked>已停用</template>
                </n-switch>
              </n-form-item>
            </n-grid-item>
          </n-grid>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="ruleFormVisible = false">取消</n-button>
            <n-button type="primary" :loading="ruleSaving" :disabled="ruleSaving" @click="saveRule">保存批次</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 重算批次号 预览弹窗（两步：高影响操作先预览） -->
      <n-modal
        v-model:show="recalcVisible"
        preset="card"
        title="重算批次号 · 变更预览"
        :style="{ width: '760px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(480px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <div class="recalc-tip">
          以下人员的批次号将发生变化。确认后才会写回数据库，未列出的人员批次号保持不变。
        </div>
        <div v-if="recalcRows.length" class="recalc-list">
          <div v-for="c in recalcRows" :key="c.person" class="recalc-row">
            <span class="recalc-name" :title="c.personName">{{ c.personName || c.person }}</span>
            <span class="recalc-old">{{ c.oldBatch || '（空）' }}</span>
            <n-icon class="recalc-arrow" :component="ArrowForwardOutline" aria-hidden="true" />
            <span class="recalc-new">{{ c.newBatch || '（空）' }}</span>
          </div>
        </div>
        <div v-else class="recalc-empty">按当前命名规则重算后，没有人的批次号需要变化。</div>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="recalcVisible = false">暂不重算</n-button>
            <n-button
              type="primary"
              :loading="recalcApplying"
              :disabled="recalcApplying || !recalcRows.length"
              @click="applyRecalc"
            >
              确认重算
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
  NDatePicker,
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
  NSwitch,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
  useNotification,
} from 'naive-ui'
import { AddOutline, AlertCircleOutline, ArrowForwardOutline, CreateOutline, SearchOutline, TrashOutline } from '@vicons/ionicons5'
import {
  applyBatchRules,
  createBatchRule,
  deleteBatchRule,
  getBatchNaming,
  listBatchRules,
  previewBatchRules,
  recalcBatchRules,
  saveBatchNaming,
  updateBatchRule,
  type BatchNaming,
  type BatchRecalcChange,
  type BatchRule,
} from '../../api/campusBatch'
import { extractError } from '../../utils/campus'

const message = useMessage()
const notification = useNotification()

type TabKey = 'naming' | 'rules' | 'timeline'
const activeTab = ref<TabKey>('naming')

/** 模板变量（逆向清单 §4.4 admin：{YYYY}{YY}{MM}{M}{DD}{SEQ}{N}）。 */
const TEMPLATE_VARS = [
  { token: '{YYYY}', label: '四位年份' },
  { token: '{YY}', label: '两位年份' },
  { token: '{MM}', label: '两位月份' },
  { token: '{M}', label: '一位月份' },
  { token: '{DD}', label: '两位日期' },
  { token: '{SEQ}', label: '批次序号' },
  { token: '{N}', label: '第几批' },
]

const cycleOptions = [
  { label: '每月归零', value: 'month' },
  { label: '每年归零', value: 'year' },
  { label: '全局递增', value: 'none' },
]
const dateFieldOptions = [
  { label: '入职日期', value: 'entryDate' },
  { label: '录用日期', value: 'hireDate' },
]

/* ───────────────────────── 通用工具 ───────────────────────── */

function textCell(text: unknown, width = 140) {
  const s = text == null || text === '' ? '—' : String(text)
  return h('span', { title: s, style: { display: 'inline-block', maxWidth: `${width}px`, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, s)
}

function numCell(value: unknown) {
  return h('span', { style: { fontVariantNumeric: 'tabular-nums' } }, value == null ? '—' : String(value))
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

function toDateStr(ts: number | null) {
  if (!ts) return undefined
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function parseDate(v?: string | null) {
  if (!v) return null
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? null : d
}

/* ───────────────────────── ① 命名规则 ───────────────────────── */

const namingForm = reactive({
  template: '{YY}{MM}{SEQ}',
  seqWidth: 2,
  seqStart: 1,
  cycle: 'month' as BatchNaming['cycle'],
  dateField: 'entryDate' as BatchNaming['dateField'],
  autoApply: true,
})

const namingLoading = ref(false)
const namingSaving = ref(false)
const previewLoading = ref(false)
const previewSamples = ref<string[]>([])
const previewUnmatched = ref(0)
const previewNoBatch = ref(0)

function insertVar(token: string) {
  namingForm.template = `${namingForm.template}${token}`
}

async function loadNaming() {
  namingLoading.value = true
  try {
    const data = await getBatchNaming()
    if (data) {
      Object.assign(namingForm, {
        template: data.template ?? namingForm.template,
        seqWidth: data.seqWidth ?? namingForm.seqWidth,
        seqStart: data.seqStart ?? namingForm.seqStart,
        cycle: data.cycle ?? namingForm.cycle,
        dateField: data.dateField ?? namingForm.dateField,
        autoApply: data.autoApply !== false,
      })
    }
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    namingLoading.value = false
  }
  previewNaming()
}

/** 实时预览：把当前表单参数交给后端 preview 端点生成样例与命中统计。 */
async function previewNaming() {
  previewLoading.value = true
  try {
    const res = await previewBatchRules({
      template: namingForm.template,
      seq_width: namingForm.seqWidth,
      seq_start: namingForm.seqStart,
      cycle: namingForm.cycle,
      date_field: namingForm.dateField,
    })
    previewSamples.value = res.samples
    previewUnmatched.value = res.unmatched
    previewNoBatch.value = res.noBatch
  } catch (e: any) {
    previewSamples.value = []
    message.error(extractError(e))
  } finally {
    previewLoading.value = false
  }
}

async function saveNaming() {
  if (!namingForm.template.trim()) {
    message.warning('请填写命名模板')
    return
  }
  namingSaving.value = true
  try {
    await saveBatchNaming({
      template: namingForm.template.trim(),
      seqWidth: namingForm.seqWidth,
      seqStart: namingForm.seqStart,
      cycle: namingForm.cycle,
      dateField: namingForm.dateField,
      autoApply: namingForm.autoApply,
    })
    message.success('命名规则已保存')
    previewNaming()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    namingSaving.value = false
  }
}

/* ───────────────────────── ② 批次定义 ───────────────────────── */

const ruleRows = ref<BatchRule[]>([])
const ruleLoading = ref(false)
const ruleError = ref('')
const ruleSearch = ref('')
/** 每条规则的命中人数（来自 preview 端点的命中统计）。 */
const hitCountMap = ref<Record<string, number>>({})

const ruleHasFilter = computed(() => Boolean(ruleSearch.value.trim()))
const ruleEmptyText = computed(() => (ruleHasFilter.value ? '没有符合筛选条件的批次' : '暂无数据'))

async function loadRules() {
  ruleLoading.value = true
  ruleError.value = ''
  try {
    const kw = ruleSearch.value.trim()
    const rows = await listBatchRules()
    ruleRows.value = kw
      ? rows.filter((r) => `${r.code}${r.name}`.includes(kw))
      : rows
    await refreshHitCounts()
  } catch (e: any) {
    ruleError.value = extractError(e)
    ruleRows.value = []
  } finally {
    ruleLoading.value = false
  }
}

/** 命中人数：preview 端点按规则返回命中统计，这里按批次号对齐。 */
async function refreshHitCounts() {
  try {
    const res = await previewBatchRules({
      template: namingForm.template,
      seq_width: namingForm.seqWidth,
      seq_start: namingForm.seqStart,
      cycle: namingForm.cycle,
      date_field: namingForm.dateField,
    })
    const map: Record<string, number> = {}
    res.ruleHits.forEach((h) => {
      if (h.code) map[h.code] = h.count
    })
    hitCountMap.value = map
  } catch {
    hitCountMap.value = {}
  }
}

const ruleColumns = computed(() => [
  { title: '批次号', key: 'code', width: 140, render: (row: BatchRule) => row.code || '—' },
  { title: '批次名称', key: 'name', width: 220, ellipsis: true, render: (row: BatchRule) => textCell(row.name, 200) },
  { title: '区间起始', key: 'startDate', width: 130, render: (row: BatchRule) => row.startDate || '—' },
  { title: '区间结束', key: 'endDate', width: 130, render: (row: BatchRule) => row.endDate || '—' },
  { title: '命中人数', key: 'hitCount', width: 110, render: (row: BatchRule) => numCell(hitCountMap.value[row.code]) },
  {
    title: '状态',
    key: 'enabled',
    width: 100,
    render: (row: BatchRule) =>
      h(NTag, { type: row.enabled ? 'success' : 'default', size: 'small' }, {
        default: () => (row.enabled ? '已启用' : '已停用'),
      }),
  },
  {
    title: '操作',
    key: 'actions',
    width: 210,
    fixed: 'right' as const,
    render: (row: BatchRule) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openRuleEdit(row) }, {
            default: () => '编辑批次',
            icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => toggleRule(row) }, {
            default: () => (row.enabled ? '停用批次' : '启用批次'),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeRule(row) }, {
            default: () => '删除批次',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          }),
        ],
      }),
  },
])

const RULE_SCROLL_X = 1040

const ruleFormVisible = ref(false)
const ruleSaving = ref(false)
const ruleEditing = ref<BatchRule | null>(null)
const ruleForm = reactive({
  code: '',
  name: '',
  startTs: null as number | null,
  endTs: null as number | null,
  sort: 1,
  enabled: true,
})

function openRuleCreate() {
  Object.assign(ruleForm, { code: '', name: '', startTs: Date.now(), endTs: Date.now(), sort: 1, enabled: true })
  ruleEditing.value = null
  ruleFormVisible.value = true
}

function openRuleEdit(row: BatchRule) {
  Object.assign(ruleForm, {
    code: row.code || '',
    name: row.name || '',
    startTs: row.startDate ? new Date(row.startDate).getTime() : null,
    endTs: row.endDate ? new Date(row.endDate).getTime() : null,
    sort: row.sort ?? 1,
    enabled: row.enabled !== false,
  })
  ruleEditing.value = row
  ruleFormVisible.value = true
}

async function saveRule() {
  if (!ruleForm.code.trim()) {
    message.warning('请填写批次号')
    return
  }
  if (!ruleForm.name.trim()) {
    message.warning('请填写批次名称')
    return
  }
  if (!ruleForm.startTs || !ruleForm.endTs) {
    message.warning('请选择区间起止日期')
    return
  }
  ruleSaving.value = true
  const payload = {
    code: ruleForm.code.trim(),
    name: ruleForm.name.trim(),
    startDate: toDateStr(ruleForm.startTs),
    endDate: toDateStr(ruleForm.endTs),
    sort: ruleForm.sort,
    enabled: ruleForm.enabled,
  }
  try {
    if (ruleEditing.value) {
      await updateBatchRule(ruleEditing.value.id, payload)
      message.success('批次规则已更新')
    } else {
      await createBatchRule(payload)
      message.success('批次规则已创建')
    }
    ruleFormVisible.value = false
    loadRules()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    ruleSaving.value = false
  }
}

/** 启停批次规则（中等影响：直接执行 + 结果提示）。 */
async function toggleRule(row: BatchRule) {
  try {
    await updateBatchRule(row.id, { enabled: !row.enabled })
    message.success(row.enabled ? '批次已停用' : '批次已启用')
    loadRules()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/** 删除批次规则 = 中等破坏性操作 → 直接执行 + 通知撤销（R-106）。 */
async function removeRule(row: BatchRule) {
  try {
    await deleteBatchRule(row.id)
    notification.create({
      content: `已删除批次「${row.code}」`,
      duration: 8000,
      keepAliveOnHover: true,
      action: () =>
        h(NButton, {
          text: true,
          type: 'primary',
          onClick: async () => {
            try {
              await createBatchRule({
                code: row.code,
                name: row.name,
                startDate: row.startDate,
                endDate: row.endDate,
                sort: row.sort,
                enabled: row.enabled,
              })
              message.success('批次已重建')
              loadRules()
            } catch (e: any) {
              message.error(extractError(e))
            }
          },
        }, { default: () => '撤销' }),
    })
    loadRules()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/* ───────────────────────── ③ 区间时间轴 ───────────────────────── */

interface TimelineBar {
  id: string
  code: string
  name: string
  startDate: string
  endDate: string
  enabled: boolean
  leftPct: number
  widthPct: number
}

interface TimelineTick {
  key: string
  label: string
  leftPct: number
}

/** 时间轴的月份刻度与横条（按月份等分，暴露区间覆盖与空隙）。 */
const timelineBars = computed<TimelineBar[]>(() => {
  const rules = ruleRows.value
    .filter((r) => r.startDate && r.endDate)
    .map((r) => ({ rule: r, start: parseDate(r.startDate), end: parseDate(r.endDate) }))
    .filter((x) => x.start && x.end) as { rule: BatchRule; start: Date; end: Date }[]
  if (!rules.length) return []

  let minMonth = Number.MAX_SAFE_INTEGER
  let maxMonth = -Number.MAX_SAFE_INTEGER
  rules.forEach(({ start, end }) => {
    const s = start.getFullYear() * 12 + start.getMonth()
    const e = end.getFullYear() * 12 + end.getMonth()
    if (s < minMonth) minMonth = s
    if (e > maxMonth) maxMonth = e
  })
  const total = maxMonth - minMonth + 1
  if (total <= 0) return []

  return rules
    .map(({ rule, start, end }) => {
      const s = start.getFullYear() * 12 + start.getMonth() - minMonth
      const e = end.getFullYear() * 12 + end.getMonth() - minMonth
      const leftPct = Math.max(0, Math.min(100, (s / total) * 100))
      const rightPct = Math.max(0, Math.min(100, ((e + 1) / total) * 100))
      return {
        id: rule.id,
        code: rule.code,
        name: rule.name,
        startDate: rule.startDate,
        endDate: rule.endDate,
        enabled: rule.enabled !== false,
        leftPct,
        widthPct: Math.max(2, rightPct - leftPct),
      }
    })
    .sort((a, b) => a.leftPct - b.leftPct)
})

const timelineTicks = computed<TimelineTick[]>(() => {
  const bars = timelineBars.value
  if (!bars.length) return []
  const start = bars[0]
  const end = bars[bars.length - 1]
  const s = parseDate(start.startDate)
  const e = parseDate(end.endDate)
  if (!s || !e) return []
  const total = (e.getFullYear() * 12 + e.getMonth()) - (s.getFullYear() * 12 + s.getMonth()) + 1
  const ticks: TimelineTick[] = []
  for (let i = 0; i < total; i += 1) {
    const d = new Date(s.getFullYear(), s.getMonth() + i, 1)
    ticks.push({
      key: `${d.getFullYear()}-${d.getMonth()}`,
      label: `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}`,
      leftPct: (i / total) * 100,
    })
  }
  return ticks
})

/** 区间覆盖与空隙检测（按起始日排序后两两比较）。 */
const timelineIssues = computed<string[]>(() => {
  const bars = timelineBars.value.filter((b) => b.enabled)
  const issues: string[] = []
  for (let i = 0; i < bars.length - 1; i += 1) {
    const cur = bars[i]
    const next = bars[i + 1]
    const curEnd = parseDate(cur.endDate)
    const nextStart = parseDate(next.startDate)
    if (!curEnd || !nextStart) continue
    if (nextStart.getTime() <= curEnd.getTime()) {
      issues.push(`区间重叠：「${cur.name}」与「${next.name}」的日期区间有交叉，同一人员可能被命中两次。`)
    } else {
      const gapDays = Math.round((nextStart.getTime() - curEnd.getTime()) / 86400000)
      if (gapDays > 1) {
        issues.push(`区间空隙：「${cur.name}」到「${next.name}」之间有 ${gapDays - 1} 天不在任何区间内。`)
      }
    }
  }
  return issues
})

/* ── 按规则回写人员批次（只补空值，不覆盖人工填过 → 中等影响，直接执行 + 结果提示）── */
const applying = ref(false)

async function askApplyRules() {
  applying.value = true
  try {
    const res = await applyBatchRules()
    message.success(`已按规则回写 ${res.updated} 人的批次（只补空值，不覆盖人工填过的批次）`)
    loadRules()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    applying.value = false
  }
}

/* ── 重算批次号（两步：先预览，确认后才落库）── */
const recalcVisible = ref(false)
const recalcApplying = ref(false)
const recalcRows = ref<BatchRecalcChange[]>([])

async function askRecalc() {
  try {
    const res = await recalcBatchRules()
    recalcRows.value = res.changes
    recalcVisible.value = true
  } catch (e: any) {
    message.error(extractError(e))
  }
}

async function applyRecalc() {
  recalcApplying.value = true
  try {
    await recalcBatchRules({ apply: true })
    message.success(`已重算 ${recalcRows.value.length} 人的批次号`)
    recalcVisible.value = false
    loadRules()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    recalcApplying.value = false
  }
}

/* ───────────────────────── 生命周期 ───────────────────────── */

function onTabChange(tab: TabKey) {
  if (tab === 'naming') {
    loadNaming()
  } else {
    loadRules()
  }
}

onMounted(async () => {
  await loadNaming()
  await loadRules()
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
.toolbar-tip {
  font-size: var(--text-small);
  color: var(--ink-faint);
}
.spacer {
  flex: 1;
}
/* 「自动归属」开关独占一行：与上方 n-grid 拉开一点间距（窄屏不与栅格挤在一起） */
.br-switch-row {
  margin-top: var(--space-2);
}
.form-area {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.form-card {
  padding: var(--space-4);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--surface);
}
.form-card-title {
  font-size: var(--text-h3);
  font-weight: 600;
  color: var(--ink);
  margin-bottom: var(--space-4);
}
.var-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-bottom: var(--space-4);
}
.var-hint {
  font-size: var(--text-small);
  color: var(--ink-faint);
}
.preview-box {
  padding: var(--space-3);
  border: 1px dashed var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--g1);
  margin-top: var(--space-2);
}
.preview-title {
  font-size: var(--text-body);
  font-weight: 600;
  color: var(--ink);
  margin-bottom: var(--space-2);
}
.preview-samples {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.preview-meta {
  margin-top: var(--space-2);
  font-size: var(--text-small);
  color: var(--ink-soft);
}
.preview-tip {
  font-size: var(--text-small);
  color: var(--ink-faint);
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-4);
}
.table-wrap {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.timeline-area {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.timeline-scroll {
  flex: 1;
  min-height: 0;
  overflow-x: auto;
  overflow-y: auto;
}
.timeline-inner {
  position: relative;
  min-width: 720px;
  padding: var(--space-2) var(--space-4);
}
.timeline-axis {
  position: relative;
  height: var(--space-6);
  border-bottom: 1px solid var(--border-hairline);
  margin-left: 160px;
}
.timeline-tick {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  font-size: var(--fs-12);
  color: var(--ink-faint);
  white-space: nowrap;
}
.timeline-row {
  display: flex;
  align-items: center;
  min-height: var(--space-8);
  border-bottom: 1px solid var(--border-hairline);
}
.timeline-label {
  width: 160px;
  flex-shrink: 0;
  padding-right: var(--space-2);
  font-size: var(--text-small);
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.timeline-track {
  position: relative;
  flex: 1;
  height: var(--space-6);
}
.timeline-bar {
  position: absolute;
  top: var(--space-1);
  height: var(--space-4);
  padding: 0 var(--space-1);
  border-radius: var(--radius-sm);
  background: var(--c-info);
  color: var(--surface);
  font-size: var(--fs-12);
  line-height: var(--space-4);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.timeline-bar--off {
  background: var(--g5);
}
.issue-box {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--c-warning);
  border-radius: var(--radius-md);
  background: var(--c-warning-soft);
  flex-shrink: 0;
}
.issue-icon {
  color: var(--c-warning-deep);
  font-size: var(--text-h4);
  flex-shrink: 0;
}
.issue-body {
  flex: 1;
  min-width: 0;
}
.issue-line {
  font-size: var(--text-small);
  color: var(--ink-soft);
  overflow-wrap: anywhere;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
.recalc-tip {
  font-size: var(--text-small);
  color: var(--ink-soft);
  margin-bottom: var(--space-3);
  overflow-wrap: anywhere;
}
.recalc-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.recalc-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-small);
}
.recalc-name {
  width: 140px;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ink);
}
.recalc-old {
  font-variant-numeric: tabular-nums;
  color: var(--ink-faint);
}
.recalc-arrow {
  color: var(--ink-faint);
  flex-shrink: 0;
}
.recalc-new {
  font-variant-numeric: tabular-nums;
  color: var(--c-success-deep);
  font-weight: 600;
}
.recalc-empty {
  font-size: var(--text-small);
  color: var(--ink-faint);
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
