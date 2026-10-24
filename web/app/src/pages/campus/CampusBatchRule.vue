<template>
  <div class="page-container">
    <div class="page-body">
      <n-tabs v-model:value="activeTab" type="line" class="page-tabs" @update:value="onTabChange">
        <n-tab-pane name="naming" tab="命名规则" />
        <n-tab-pane name="rules" tab="批次定义" />
        <n-tab-pane name="timeline" tab="区间时间轴" />
      </n-tabs>

      <!-- 写入失败三段式（R-203）：① 人话描述发生了什么 ② 你的数据是否安全 ③ 技术详情（折叠 + 一键复制） -->
      <div v-if="writeError" class="error-state" role="alert">
        <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
        <div class="error-state-body">
          <div class="error-state-title">{{ writeError.title }}</div>
          <div class="error-state-desc">{{ writeError.safe }}</div>
          <details class="error-state-detail">
            <summary>查看详情</summary>
            <pre class="error-state-code">{{ writeError.detail }}</pre>
            <n-button size="tiny" quaternary @click="copyText(writeError.detail)">复制错误信息</n-button>
          </details>
        </div>
        <n-button v-if="writeError.retry" size="small" type="primary" ghost @click="runWriteRetry">
          {{ writeError.retryLabel }}
        </n-button>
      </div>

      <!-- ① 命名规则 -->
      <template v-if="activeTab === 'naming'">
        <div class="form-area">
          <div class="form-card">
            <div class="form-card-title">批次命名规则</div>

            <n-form :model="namingForm" label-placement="top">
              <n-form-item
                label="命名模板"
                required
                :validation-status="namingErrors.template ? 'error' : undefined"
                :show-feedback="!!namingErrors.template"
              >
                <n-input
                  v-model:value="namingForm.template"
                  placeholder="如 {YY}{MM}{SEQ}"
                  data-error-field="naming-template"
                />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ namingErrors.template }}
                </template>
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
          <n-button :loading="applying" :disabled="applying" @click="askApplyRules">按规则回写批次</n-button>
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
          <!-- 写入失败三段式（R-203）：弹窗内就地展示，不甩给全局 toast -->
          <div v-if="ruleWriteError" class="error-state" role="alert">
            <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
            <div class="error-state-body">
              <div class="error-state-title">{{ ruleWriteError.title }}</div>
              <div class="error-state-desc">{{ ruleWriteError.safe }}</div>
              <details class="error-state-detail">
                <summary>查看详情</summary>
                <pre class="error-state-code">{{ ruleWriteError.detail }}</pre>
                <n-button size="tiny" quaternary @click="copyText(ruleWriteError.detail)">复制错误信息</n-button>
              </details>
            </div>
            <n-button v-if="ruleWriteError.retry" size="small" type="primary" ghost @click="runRuleRetry">
              {{ ruleWriteError.retryLabel }}
            </n-button>
          </div>
          <n-grid :cols="'1 560:2'" :x-gap="16">
            <n-grid-item>
              <n-form-item
                label="批次号"
                required
                :validation-status="ruleErrors.code ? 'error' : undefined"
                :show-feedback="!!ruleErrors.code"
              >
                <n-input v-model:value="ruleForm.code" placeholder="如 202609" data-error-field="rule-code" />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ ruleErrors.code }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="批次名称"
                required
                :validation-status="ruleErrors.name ? 'error' : undefined"
                :show-feedback="!!ruleErrors.name"
              >
                <n-input v-model:value="ruleForm.name" placeholder="如 2026 年 9 月秋招批次" data-error-field="rule-name" />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ ruleErrors.name }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="区间起始"
                required
                :validation-status="ruleErrors.range ? 'error' : undefined"
                :show-feedback="!!ruleErrors.range"
              >
                <n-date-picker v-model:value="ruleForm.startTs" type="date" style="width: 100%" data-error-field="rule-range" />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ ruleErrors.range }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="区间结束"
                required
                :validation-status="ruleErrors.range ? 'error' : undefined"
                :show-feedback="!!ruleErrors.range"
              >
                <n-date-picker v-model:value="ruleForm.endTs" type="date" style="width: 100%" />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ ruleErrors.range }}
                </template>
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
            <n-button @click="closeRuleForm">取消编辑</n-button>
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
        <div v-if="recalcWriteError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">{{ recalcWriteError.title }}</div>
            <div class="error-state-desc">{{ recalcWriteError.safe }}</div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ recalcWriteError.detail }}</pre>
              <n-button size="tiny" quaternary @click="copyText(recalcWriteError.detail)">复制错误信息</n-button>
            </details>
          </div>
          <n-button v-if="recalcWriteError.retry" size="small" type="primary" ghost @click="runRecalcRetry">
            {{ recalcWriteError.retryLabel }}
          </n-button>
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
import { computed, h, onMounted, reactive, ref, type Ref } from 'vue'
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
import { buildWriteError, extractError } from '../../utils/campus'
import { useFormDraft } from '../../composables/useFormDraft'
import { api } from '../../utils/request'

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

/**
 * 写入失败的三段式状态（R-203）。
 * ① title 人话描述 ② safe 你的数据是否安全 ③ detail 技术详情（折叠 + 一键复制）。
 */
interface WriteErrorState {
  title: string
  safe: string
  detail: string
  /** 恢复动作（重试 / 撤销…），为空则不渲染恢复按钮 */
  retryLabel?: string
  retry?: () => void | Promise<void>
}

/** 表单级校验错误（R-221）：就近展示在字段旁，图标 + 文字双通道。 */
type FieldErrors = Record<string, string>

/** 聚焦第一个出错的字段（字段上带 data-error-field 标记）。 */
function focusFirstError(field: string) {
  if (typeof document === 'undefined') return
  const el = document.querySelector<HTMLElement>(`[data-error-field="${field}"] input, [data-error-field="${field}"] textarea`)
  el?.focus()
}

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

/* ── 写入失败三段式（R-203）── */

/** 页面级（工具栏写操作 / 读取失败）的写入失败。 */
const writeError = ref<WriteErrorState | null>(null)
/** 批次规则弹窗内的写入失败。 */
const ruleWriteError = ref<WriteErrorState | null>(null)
/** 重算批次号弹窗内的写入失败。 */
const recalcWriteError = ref<WriteErrorState | null>(null)

/** 读取失败的安全提示（数据仍在服务端，不丢）。 */
const READ_SAFE_HINT = '没有连上服务器，页面上的数据仍是上一次加载到的结果，重试一次即可恢复。'

function setWriteError(
  target: Ref<WriteErrorState | null>,
  err: any,
  action: string,
  opts: { retryLabel?: string; retry?: () => void | Promise<void>; safeHint?: string } = {},
) {
  const info = buildWriteError(err, { action, safeHint: opts.safeHint })
  target.value = {
    title: info.title,
    safe: info.safe,
    detail: info.detail,
    retryLabel: opts.retryLabel,
    retry: opts.retry,
  }
}

function runRetry(target: Ref<WriteErrorState | null>) {
  const fn = target.value?.retry
  if (!fn) return
  target.value = null
  void fn()
}

function runWriteRetry() {
  runRetry(writeError)
}
function runRuleRetry() {
  runRetry(ruleWriteError)
}
function runRecalcRetry() {
  runRetry(recalcWriteError)
}

/* ── 草稿（R-105）：命名规则 / 批次规则各自一份草稿 ── */

/**
 * 打开表单时探测草稿：有内容就恢复并给「清空」出口（R-105）。
 * 草稿与服务端数据一致时静默丢弃 —— 没有需要恢复的内容，不打扰用户。
 */
function restoreDraft(
  draft: { probe: () => boolean; restore: () => void; clear: () => void },
  form: Record<string, unknown>,
  label: string,
) {
  if (!draft.probe()) return
  const before = JSON.stringify(form)
  draft.restore()
  if (JSON.stringify(form) === before) {
    draft.clear()
    return
  }
  const n = notification.create({
    title: '已恢复上次填写的内容',
    content: `上次填写但没有提交的${label}已经放回表单，你可以接着改；不需要就点「清空」。`,
    duration: 8000,
    keepAliveOnHover: true,
    action: () =>
      h(
        NButton,
        {
          text: true,
          type: 'primary',
          onClick: () => {
            draft.clear()
            n?.destroy()
          },
        },
        { default: () => '清空' },
      ),
  })
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

/** 字段级校验错误（R-221）：就近展示在「命名模板」旁。 */
const namingErrors = reactive<FieldErrors>({ template: '' })

/** 命名规则草稿（R-105）：单例配置，无编辑态 → 始终启用。 */
const namingDraft = useFormDraft('campus-batch-rule-naming', namingForm as unknown as Record<string, unknown>)

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
    setWriteError(writeError, e, '加载命名规则', { retryLabel: '重新加载', retry: loadNaming, safeHint: READ_SAFE_HINT })
  } finally {
    namingLoading.value = false
  }
  // 服务端数据到位后再探测草稿，避免草稿被服务端数据覆盖
  restoreDraft(namingDraft, namingForm as unknown as Record<string, unknown>, '命名规则')
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
    setWriteError(writeError, e, '生成批次预览', { retryLabel: '重新生成', retry: previewNaming, safeHint: READ_SAFE_HINT })
  } finally {
    previewLoading.value = false
  }
}

async function saveNaming() {
  // 就近校验（R-221）：错误落在「命名模板」字段旁，并聚焦该字段
  namingErrors.template = namingForm.template.trim() ? '' : '请填写命名模板'
  if (namingErrors.template) {
    focusFirstError('naming-template')
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
    // 提交成功后立即清除草稿（R-105）
    namingDraft.clear()
    previewNaming()
  } catch (e: any) {
    setWriteError(writeError, e, '保存命名规则', { retryLabel: '重试保存', retry: saveNaming })
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

/** 字段级校验错误（R-221）：就近展示在对应字段旁。 */
const ruleErrors = reactive<FieldErrors>({ code: '', name: '', range: '' })

/** 批次规则草稿（R-105）：编辑态不启用，避免草稿覆盖真实行数据。 */
const ruleDraft = useFormDraft('campus-batch-rule-form', ruleForm as unknown as Record<string, unknown>, {
  enabled: () => !ruleEditing.value,
})

function openRuleCreate() {
  Object.assign(ruleForm, { code: '', name: '', startTs: Date.now(), endTs: Date.now(), sort: 1, enabled: true })
  Object.assign(ruleErrors, { code: '', name: '', range: '' })
  ruleEditing.value = null
  ruleWriteError.value = null
  ruleFormVisible.value = true
  restoreDraft(ruleDraft, ruleForm as unknown as Record<string, unknown>, '批次规则')
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
  Object.assign(ruleErrors, { code: '', name: '', range: '' })
  ruleEditing.value = row
  ruleWriteError.value = null
  ruleFormVisible.value = true
}

/** 关闭弹窗：清掉校验与写入失败状态，下次打开是干净的。 */
function closeRuleForm() {
  ruleFormVisible.value = false
  Object.assign(ruleErrors, { code: '', name: '', range: '' })
  ruleWriteError.value = null
}

async function saveRule() {
  // 就近校验（R-221）：逐字段置错误态 + 聚焦第一个出错字段
  ruleErrors.code = ruleForm.code.trim() ? '' : '请填写批次号'
  ruleErrors.name = ruleForm.name.trim() ? '' : '请填写批次名称'
  ruleErrors.range = ruleForm.startTs && ruleForm.endTs ? '' : '请选择区间起止日期'
  const firstError = ruleErrors.code ? 'rule-code' : ruleErrors.name ? 'rule-name' : ruleErrors.range ? 'rule-range' : ''
  if (firstError) {
    focusFirstError(firstError)
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
    // 提交成功后立即清除草稿（R-105）
    ruleDraft.clear()
    loadRules()
  } catch (e: any) {
    setWriteError(ruleWriteError, e, ruleEditing.value ? '保存批次规则' : '创建批次规则', {
      retryLabel: '重试保存',
      retry: saveRule,
    })
  } finally {
    ruleSaving.value = false
  }
}

/** 启停批次规则（可逆：直接执行 + 结果提示，R-106）。 */
async function toggleRule(row: BatchRule) {
  try {
    await updateBatchRule(row.id, { enabled: !row.enabled })
    message.success(row.enabled ? '批次已停用' : '批次已启用')
    loadRules()
  } catch (e: any) {
    setWriteError(writeError, e, row.enabled ? '停用批次' : '启用批次', {
      retryLabel: '重试停用',
      retry: () => toggleRule(row),
    })
  }
}

/** 撤销删除：把被删掉的批次规则重新建回来。 */
async function rebuildRule(row: BatchRule) {
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
    setWriteError(writeError, e, '重建批次', { retryLabel: '重试重建', retry: () => rebuildRule(row) })
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
            await rebuildRule(row)
          },
        }, { default: () => '撤销' }),
    })
    loadRules()
  } catch (e: any) {
    setWriteError(writeError, e, '删除批次', { retryLabel: '重试删除', retry: () => removeRule(row) })
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

/* ── 按规则回写人员批次（中等影响：直接执行 + Toast 撤销，R-106）── */
const applying = ref(false)

/** 回写接口返回的受影响人员（用于撤销回滚）。 */
interface AppliedPerson {
  person_id?: string | number
  code?: string
  name?: string
  batch?: string
}

/**
 * 撤销回写：把本次被补上批次号的人员批次清回空值。
 * ⚠️ 后端没有专门的「撤销回写」端点，这里按人员逐个 PATCH 批次字段。
 */
async function rollbackApplied(details: AppliedPerson[]) {
  if (!details.length) {
    message.warning('这次没有可撤销的批次回写')
    return
  }
  let failed = 0
  for (const p of details) {
    if (p.person_id == null) {
      failed += 1
      continue
    }
    try {
      await api.patch(`/campus/persons/${p.person_id}/`, { batch: '' })
    } catch {
      failed += 1
    }
  }
  if (failed) {
    setWriteError(writeError, { response: { status: 500, data: { detail: `${failed} 人的批次未能清空` } } }, '撤销批次回写', {
      retryLabel: '重试撤销',
      retry: () => rollbackApplied(details),
    })
  } else {
    message.success(`已撤销 ${details.length} 人的批次回写`)
  }
  loadRules()
}

async function askApplyRules() {
  applying.value = true
  try {
    const res = await applyBatchRules()
    // ⚠️ 后端回写条数字段是 filled；前端归一化层只透出了 raw，这里按后端口径取值。
    const filled = Number(res.raw?.filled ?? res.updated ?? 0)
    const details: AppliedPerson[] = Array.isArray(res.raw?.details) ? res.raw.details : []
    notification.create({
      content: `已按规则回写 ${filled} 人的批次（只补空值，不覆盖人工填过的批次）`,
      duration: 8000,
      keepAliveOnHover: true,
      action: () =>
        h(NButton, {
          text: true,
          type: 'primary',
          onClick: async () => {
            await rollbackApplied(details)
          },
        }, { default: () => '撤销' }),
    })
    loadRules()
  } catch (e: any) {
    setWriteError(writeError, e, '按规则回写批次', { retryLabel: '重试回写', retry: askApplyRules })
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
    recalcWriteError.value = null
    recalcVisible.value = true
  } catch (e: any) {
    setWriteError(writeError, e, '生成重算预览', { retryLabel: '重试预览', retry: askRecalc, safeHint: READ_SAFE_HINT })
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
    setWriteError(recalcWriteError, e, '重算批次号', { retryLabel: '重试重算', retry: applyRecalc })
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
  /* 标签列宽度只在这里定义一次：刻度轴与每一行共用同一套栅格（不再靠 margin 偏移对齐） */
  --timeline-label-width: 160px;
  display: grid;
  grid-template-columns: var(--timeline-label-width) minmax(0, 1fr);
  column-gap: var(--space-2);
}
.timeline-axis {
  /* 刻度轴落在「轨道列」，与下方区间条左边缘严格对齐 */
  grid-column: 2;
  position: relative;
  height: var(--space-6);
  border-bottom: 1px solid var(--border-hairline);
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
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: var(--timeline-label-width) minmax(0, 1fr);
  column-gap: var(--space-2);
  align-items: center;
  min-height: var(--space-8);
  border-bottom: 1px solid var(--border-hairline);
}
.timeline-label {
  min-width: 0;
  padding-right: var(--space-2);
  font-size: var(--text-small);
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.timeline-track {
  position: relative;
  height: var(--space-6);
}
.timeline-bar {
  position: absolute;
  top: var(--space-1);
  height: var(--space-4);
  padding: 0 var(--space-1);
  border-radius: var(--radius-sm);
  /* R-109 对比度：--c-info(#3B82F6) 作实底 + 白字只有 3.68:1（不达 AA 4.5:1）；
     文字色必须走 --c-*-deep 阶 —— --c-info-deep(#1E40AF) + --on-c-info-deep(白) = 8.72:1。 */
  background: var(--c-info-deep);
  color: var(--on-c-info-deep);
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
