<template>
  <div class="page-container metrics-ws">
    <!-- ========== Header ========== -->
    <div class="page-header">
      <div>
        <h1 class="ws-title">{{ t('metrics.library.title') }}</h1>
        <p class="ws-subtitle">{{ t('metrics.library.subtitle') }}</p>
      </div>
    </div>

    <!-- ========== 顶层 Tab：指标定义 / 指标模板 ========== -->
    <div class="ws-body">
      <n-tabs v-model:value="activeTab" type="line" animated>
        <!-- ---------- Tab 1：指标定义（只读，统一视图） ---------- -->
        <n-tab-pane name="definitions" :tab="t('metrics.tab.definitions')">
          <div class="ws-tab-header">
            <div class="ws-toolbar">
              <n-input
                v-model:value="defKeyword"
                :placeholder="t('metrics.filter.keywordPlaceholder')"
                clearable
                class="ws-search"
              >
                <template #prefix>
                  <n-icon :component="SearchOutline" />
                </template>
              </n-input>
              <n-select
                v-model:value="defKind"
                :placeholder="t('metrics.filter.kind')"
                :options="defKindOptions"
                class="ws-filter"
              />
              <span class="ws-result-count">{{ t('metrics.filter.resultCount', { count: filteredDefinitions.length }) }}</span>
            </div>

            <div class="ws-legend">
              <span class="ws-legend-item"><KindIcon kind="atomic" :size="18" /> {{ t('metrics.legend.atomic') }}</span>
              <span class="ws-legend-item"><KindIcon kind="derived" :size="18" /> {{ t('metrics.legend.derived') }}</span>
            </div>
          </div>

          <div class="ws-table-wrap">
            <n-spin :show="loading" class="ws-spin">
              <div v-if="!loading && !filteredDefinitions.length" class="ws-empty">
                <n-empty :description="t('metrics.empty.definitions')" />
              </div>
              <n-data-table
                v-else
                :columns="defColumns"
                :data="filteredDefinitions"
                :row-props="defRowProps"
                :scroll-x="860"
                :flex-height="true"
                size="small"
                class="ws-table"
              />
            </n-spin>
          </div>
        </n-tab-pane>

        <!-- ---------- Tab 2：指标模板（CRUD） ---------- -->
        <n-tab-pane name="template" :tab="t('metrics.tab.template')">
          <div class="ws-tab-header">
            <div class="ws-tab-bar">
              <div class="ws-toolbar ws-toolbar-grow">
                <n-input
                  v-model:value="tplKeyword"
                  :placeholder="t('metrics.filter.keywordPlaceholder')"
                  clearable
                  class="ws-search"
                >
                  <template #prefix>
                    <n-icon :component="SearchOutline" />
                  </template>
                </n-input>
                <n-select
                  v-model:value="tplStatus"
                  :placeholder="t('metrics.filter.status')"
                  :options="tplStatusOptions"
                  class="ws-filter"
                />
                <span class="ws-result-count">{{ t('metrics.filter.resultCount', { count: filteredTemplates.length }) }}</span>
              </div>
              <n-button type="primary" @click="openTemplateCreate">
                {{ t('metrics.btn.create') }}{{ t('metrics.tab.template') }}
              </n-button>
            </div>

            <div class="ws-legend">
              <span class="ws-legend-item"><KindIcon kind="atomic" :size="18" /> {{ t('metrics.legend.atomic') }}</span>
              <span class="ws-legend-item"><KindIcon kind="derived" :size="18" /> {{ t('metrics.legend.derived') }}</span>
            </div>
          </div>

          <div class="ws-table-wrap">
            <n-spin :show="loading" class="ws-spin">
              <div v-if="!loading && !templateList.length" class="ws-empty">
                <n-empty :description="t('metrics.empty.noTemplates')" />
              </div>
              <div v-else-if="!filteredTemplates.length" class="ws-empty">
                <n-empty :description="t('metrics.empty.templates')" />
              </div>
              <n-data-table
                v-else
                :columns="tplColumns"
                :data="filteredTemplates"
                :scroll-x="900"
                :flex-height="true"
                size="small"
                class="ws-table"
              />
            </n-spin>
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>

    <!-- ========== 指标定义详情弹窗（居中，只读） ========== -->
    <n-modal
      v-model:show="detailVisible"
      preset="card"
      :title="detailRow ? detailRow.name : ''"
      style="width: 640px; max-width: 92vw;"
      :mask-closable="true"
    >
      <template v-if="detailRow">
        <div class="detail-grid">
          <div class="detail-cell detail-head-cell">
            <div class="cell-label">{{ t('metrics.col.type') }}</div>
            <div class="cell-value ws-kind-line">
              <KindIcon :kind="detailRow.kind" :size="18" />
              <span :class="['ws-kind-text', kindClass(detailRow)]">{{ kindLabel(detailRow) }}</span>
            </div>
          </div>
          <div class="detail-cell detail-cell-wide">
            <div class="cell-label">{{ t('metrics.col.dataSource') }}</div>
            <div class="cell-value">
              <code class="ws-code">{{ detailRow.dataSource }}</code>
            </div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">{{ t('metrics.col.inOutType') }}</div>
            <div class="cell-value">{{ inOutLabel(detailRow) }}</div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">{{ t('metrics.col.operators') }}</div>
            <div class="cell-value">
              <div class="ws-ops">
                <span v-for="op in (detailRow.supportedOperators || [])" :key="op" class="ws-op-tag">
                  {{ operatorLabel(op) }}
                </span>
                <span v-if="!(detailRow.supportedOperators || []).length" class="ws-muted">-</span>
              </div>
            </div>
          </div>
          <div v-if="detailRow.isEnum" class="detail-cell detail-cell-wide">
            <div class="cell-label">{{ t('metrics.col.enumValues') }}</div>
            <div class="cell-value">
              <div class="ws-ops">
                <span v-for="ev in enumValuesOf(detailRow)" :key="ev" class="ws-enum-tag">{{ ev }}</span>
                <span v-if="!enumValuesOf(detailRow).length" class="ws-muted">-</span>
              </div>
            </div>
          </div>
          <div v-if="detailRow.description" class="detail-cell detail-cell-wide">
            <div class="cell-label">{{ t('metrics.form.description') }}</div>
            <div class="cell-value">{{ detailRow.description }}</div>
          </div>
          <div v-if="hasEditableParams" class="detail-cell detail-cell-wide detail-params-block">
            <div class="cell-label">{{ t('metrics.detail.paramsTitle') }}</div>
            <div class="detail-params-form">
              <div v-for="p in detailRow.paramSchema" :key="p.key" class="detail-param-row">
                <span class="param-label">{{ p.label }}</span>
                <n-input-number
                  v-if="p.type === 'number'"
                  v-model:value="detailParams[p.key]"
                  :min="0"
                  class="param-input"
                />
                <n-select
                  v-else-if="p.type === 'select'"
                  v-model:value="detailParams[p.key]"
                  :options="(p.options || []).map((o: any) => ({ label: o.label, value: o.value }))"
                  class="param-input"
                />
                <n-switch v-else-if="p.type === 'boolean'" v-model:value="detailParams[p.key]" />
                <n-input v-else v-model:value="detailParams[p.key]" class="param-input" />
                <span v-if="p.key === 'recent_n'" class="param-hint">{{ t('metrics.detail.recentNHint') }}</span>
              </div>
            </div>
            <n-button type="primary" size="small" :loading="savingParams" @click="saveDerivedParams">
              {{ t('metrics.detail.saveParams') }}
            </n-button>
          </div>
        </div>
      </template>
    </n-modal>

    <!-- ========== 指标模板新建/编辑弹窗（PRD：参数 / 算子 / 值域） ========== -->
    <n-modal
      v-model:show="showTemplateModal"
      preset="card"
      :title="templateModalTitle"
      :closable="true"
      style="width: 720px; max-width: 94vw; max-height: 90vh;"
      :mask-closable="false"
    >
      <n-form :model="tplForm" label-placement="top" class="tpl-form">
        <n-form-item :label="t('metrics.form.name')" required>
          <n-input v-model:value="tplForm.name" :placeholder="t('metrics.form.name')" />
        </n-form-item>

        <n-form-item :label="t('metrics.form.metricDefinition')" required>
          <n-select
            v-model:value="tplForm.metricDefinition"
            :options="metricDefinitionOptions"
            clearable
            :placeholder="t('metrics.form.metricDefinition')"
            @update:value="onTemplateMetricChange"
          />
        </n-form-item>

        <div v-if="selectedTemplateDefinition" class="tpl-output-bar">
          <span class="tpl-output-label">{{ t('metrics.tpl.outputParam') }}</span>
          <n-tag size="small" type="info">{{ returnTypeLabel(selectedTemplateDefinition.returnType) }}</n-tag>
          <span v-if="selectedTemplateDefinition.unit" class="tpl-output-unit">{{ selectedTemplateDefinition.unit }}</span>
          <span class="tpl-output-hint">{{ t('metrics.tpl.inheritedHint') }}</span>
        </div>

        <!-- 参数配置：仅参数化 Handler 类型指标展示 -->
        <section v-if="showTemplateParamConfig" class="tpl-section-card">
          <div class="tpl-section-header">
            <span class="tpl-section-number">1</span>
            <span class="tpl-section-title">{{ t('metrics.tpl.paramConfigTitle') }}</span>
            <n-tag
              size="small"
              :type="selectedTemplateDefinition?.paramType === 'continuous' ? 'success' : 'warning'"
            >
              {{ paramTypeLabel(selectedTemplateDefinition?.paramType) }}
            </n-tag>
            <span class="tpl-section-hint">{{ paramConfigHint }}</span>
          </div>
          <div class="tpl-section-body">
            <div class="tpl-row">
              <n-form-item :label="t('metrics.tpl.rangeMin')" class="tpl-field">
                <n-input-number v-model:value="tplForm.paramConfig.min" :precision="paramPrecision" />
              </n-form-item>
              <span class="tpl-range-sep">~</span>
              <n-form-item :label="t('metrics.tpl.rangeMax')" class="tpl-field">
                <n-input-number v-model:value="tplForm.paramConfig.max" :precision="paramPrecision" />
              </n-form-item>
              <n-form-item :label="t('metrics.tpl.step')" class="tpl-field">
                <n-input-number v-model:value="tplForm.paramConfig.step" :min="0" :precision="paramPrecision" />
              </n-form-item>
            </div>
            <div class="tpl-row">
              <n-form-item :label="t('metrics.tpl.prefix')" class="tpl-field">
                <n-input v-model:value="tplForm.paramConfig.prefix" />
              </n-form-item>
              <n-form-item :label="t('metrics.tpl.suffix')" class="tpl-field">
                <n-input v-model:value="tplForm.paramConfig.suffix" />
              </n-form-item>
              <n-form-item class="tpl-field tpl-switch-field">
                <template #label>
                  <span>{{ t('metrics.tpl.allOption') }}</span>
                </template>
                <n-switch v-model:value="tplForm.paramConfig.allOption" />
              </n-form-item>
            </div>
            <div v-if="paramPreviewValues.length" class="tpl-preview">
              <span class="tpl-preview-tag">
                [{{ tplForm.paramConfig.allOption ? t('metrics.tpl.unlimited') : t('metrics.tpl.allLabel') }}]
              </span>
              <span>
                · {{ t('metrics.tpl.valuePreview', { count: paramPreviewValues.length }) }}：
                {{ paramPreviewValues.join('，') }}
              </span>
            </div>
          </div>
        </section>
        <div v-else-if="selectedTemplateDefinition && selectedTemplateDefinition.valueMode === 'object_path'" class="tpl-info-text">
          {{ t('metrics.tpl.noParamsNeeded') }}
        </div>
        <div v-else-if="selectedTemplateDefinition" class="tpl-info-text">
          {{ t('metrics.tpl.handlerNoParamsNeeded') }}
        </div>

        <!-- 启用算子 -->
        <section class="tpl-section-card">
          <div class="tpl-section-header">
            <span class="tpl-section-number">2</span>
            <span class="tpl-section-title">{{ t('metrics.tpl.operatorTitle') }}</span>
            <span class="tpl-section-hint">
              {{ t('metrics.tpl.operatorCount', { total: supportedOperatorOptions.length, enabled: tplForm.operators.length }) }}
            </span>
          </div>
          <div class="tpl-section-body">
            <div v-if="supportedOperatorOptions.length" class="tpl-operator-chips">
              <label
                v-for="op in supportedOperatorOptions"
                :key="op.value"
                class="tpl-op-chip"
                :class="{ 'is-checked': tplForm.operators.includes(op.value) }"
              >
                <input
                  type="checkbox"
                  :value="op.value"
                  :checked="tplForm.operators.includes(op.value)"
                  @change="toggleOperator(op.value)"
                />
                <n-icon v-if="tplForm.operators.includes(op.value)" :component="CheckmarkOutline" />
                <span>{{ op.label }}</span>
              </label>
            </div>
            <div v-else class="tpl-info-text">
              {{ t('metrics.tpl.noMetricSelected') }}
            </div>
          </div>
        </section>

        <!-- 值域配置 -->
        <section class="tpl-section-card">
          <div class="tpl-section-header">
            <span class="tpl-section-number">3</span>
            <span class="tpl-section-title">{{ t('metrics.tpl.domainTitle') }}</span>
            <span class="tpl-section-hint">{{ t('metrics.tpl.domainHint') }}</span>
          </div>
          <div class="tpl-section-body">
            <div
              v-for="(seg, idx) in tplForm.valueDomain.segments"
              :key="idx"
              class="tpl-segment-block"
            >
              <div class="tpl-segment-row">
                <span class="tpl-segment-label">{{ t('metrics.tpl.segment', { index: idx + 1 }) }}</span>
                <n-input-number v-model:value="seg.min" class="tpl-seg-field" :precision="paramPrecision" />
                <span class="tpl-range-sep">~</span>
                <n-input-number v-model:value="seg.max" class="tpl-seg-field" :precision="paramPrecision" />
                <span v-if="selectedTemplateDefinition?.unit" class="tpl-unit-text">{{ selectedTemplateDefinition.unit }}</span>
                <n-form-item :label="t('metrics.tpl.step')" class="tpl-step-field">
                  <n-input-number v-model:value="seg.step" :min="0" :precision="paramPrecision" />
                </n-form-item>
                <n-button size="small" quaternary type="error" @click="removeSegment(idx)">
                  {{ t('metrics.btn.delete') }}
                </n-button>
              </div>
              <div v-if="segmentPreviewValues(seg).length" class="tpl-preview">
                <span class="tpl-preview-tag">[{{ t('metrics.tpl.segment', { index: idx + 1 }) }}]</span>
                <span>
                  · {{ t('metrics.tpl.valuePreview', { count: segmentPreviewValues(seg).length }) }}：
                  {{ segmentPreviewValues(seg).join('，') }}
                </span>
              </div>
            </div>
            <n-button size="small" dashed @click="addSegment">{{ t('metrics.tpl.addSegment') }}</n-button>
          </div>
        </section>

        <n-form-item :label="t('metrics.form.description')">
          <n-input v-model:value="tplForm.description" type="textarea" :rows="2" />
        </n-form-item>
        <n-form-item :label="t('metrics.form.status')">
          <n-switch
            v-model:value="tplForm.status"
            checked-value="enabled"
            unchecked-value="disabled"
          >
            <template #checked>{{ t('metrics.status.enabled') }}</template>
            <template #unchecked>{{ t('metrics.status.disabled') }}</template>
          </n-switch>
        </n-form-item>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="showTemplateModal = false">{{ t('metrics.btn.cancel') }}</n-button>
          <n-button type="primary" :loading="savingTpl" @click="submitTemplate">{{ t('metrics.btn.save') }}</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
/**
 * MetricsWorkspace —— 指标管理（原「指标库」）。
 *
 * 模块拆分（用户诉求）：
 *   - 指标管理（本页）：两个页签
 *       1) 指标定义 —— 只读统一视图（原子 + 派生合并），点击卡片弹出居中详情弹窗。
 *          原子指标与派生指标已整合进「指标定义」，故不再提供独立的新建入口（无停用/启用状态，
 *          展示系统中已注册的全部指标）；取值方式明确为「对象路径 / 参数化 Handler」，
 *          枚举型指标同时展示其出参枚举值。
 *       2) 指标模板 —— 新增/编辑/删除/停用（CRUD），可配置参数范围/步长/显示/算子/值域
 *   - 规则引擎（RuleAuthoring.vue）：承接原「规则配置与执行」「规则管理」两个功能
 *
 * 2026-09-30 交互优化：
 *   - 菜单名 / 页面标题统一为「指标管理」
 *   - 数据列表重构为数据卡片（信息层次清晰、视觉一致）
 *   - 新增关键词搜索 + 分类/状态筛选，快速定位目标指标
 *   - 移除冗余只读提示横幅，减少信息干扰
 */
import { computed, h, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  NButton,
  NDataTable,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NSwitch,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { CheckmarkOutline, SearchOutline } from '@vicons/ionicons5'
import KindIcon from '@/components/metrics/KindIcon.vue'
import OperatorBadge from '@/components/metrics/OperatorBadge.vue'
import {
  createMetricTemplate,
  deleteMetricTemplate,
  listAtomicMetrics,
  listDerivedMetrics,
  listMetricDefinitions,
  listMetricTemplates,
  listOperators,
  listCandidateFields,
  updateDerivedMetric,
  updateMetricTemplate,
  type AtomicMetric,
  type CandidateFieldPath,
  type DerivedMetric,
  type MetricDefinition,
  type MetricTemplate,
  type OptionItem,
} from '@/api/metrics'

const { t } = useI18n()
const message = useMessage()

const activeTab = ref<'definitions' | 'template'>('definitions')

// ===== 共享数据 =====
const definitions = ref<MetricDefinition[]>([])
const templateList = ref<MetricTemplate[]>([])
const atomicList = ref<AtomicMetric[]>([])
const derivedList = ref<DerivedMetric[]>([])
const operatorCatalog = ref<OptionItem[]>([])
const fieldPaths = ref<CandidateFieldPath[]>([])
const loading = ref(false)

// ===== 指标详情弹窗 =====
const detailVisible = ref(false)
const detailRow = ref<MetricDefinition | null>(null)
// 参数化 Handler 指标的可编辑参数副本（来自 detailRow.paramSchema）
const detailParams = ref<Record<string, any>>({})
const savingParams = ref(false)

function openDetail(row: MetricDefinition) {
  detailRow.value = row
  detailParams.value = { ...(row.params || {}) }
  detailVisible.value = true
}

/** 当前指标是否为带参数的「参数化 Handler」，需要渲染参数编辑区。 */
const hasEditableParams = computed<boolean>(() => {
  const d = detailRow.value
  return !!d && d.valueMode === 'parametric_handler' && !!(d.paramSchema && d.paramSchema.length)
})

async function saveDerivedParams() {
  const d = detailRow.value
  if (!d) return
  savingParams.value = true
  try {
    await updateDerivedMetric(d.id, { params: detailParams.value })
    message.success(t('metrics.detail.paramsSaved'))
    if (detailRow.value) detailRow.value.params = { ...detailParams.value }
    await load()
  } catch (error: any) {
    const err = error?.response?.data?.error
    message.error(err ? String(err) : t('metrics.msg.saveFailed'))
  } finally {
    savingParams.value = false
  }
}

/** 入参 / 出参 合并标签（详情弹窗与定义表共用）。无入参时显示「无 / X」。 */
function inOutLabel(row: MetricDefinition): string {
  const param = row.paramType ? paramTypeLabel(row.paramType) : t('metrics.paramType.none')
  return `${param} / ${returnTypeLabel(row.returnType)}`
}
function kindLabel(row: MetricDefinition): string {
  return row.kind === 'derived' ? t('metrics.tab.derived') : t('metrics.tab.atomic')
}
function kindClass(row: MetricDefinition): string {
  return row.kind === 'derived' ? 'is-derived' : 'is-atomic'
}
function enumValuesOf(row: MetricDefinition): string[] {
  return (row.enumValues as string[] | undefined) || []
}
function returnTypeLabel(type?: string): string {
  const map: Record<string, string> = {
    number: t('pages.settings.MetricsWorkspace.s7'),
    string: t('pages.settings.MetricsWorkspace.s8'),
    boolean: t('pages.settings.MetricsWorkspace.s9'),
    date: t('pages.settings.MetricsWorkspace.s10'),
  }
  return (type && map[type]) || type || '-'
}
function paramTypeLabel(type?: string): string {
  if (type === 'continuous') return t('metrics.paramType.continuous')
  if (type === 'discrete') return t('metrics.paramType.discrete')
  return '-'
}
function operatorLabel(value: string) {
  return operatorCatalog.value.find((o) => o.value === value)?.label ?? value
}

// ===== 指标定义：搜索 + 分类筛选 =====
const defKeyword = ref('')
const defKind = ref<'all' | 'atomic' | 'derived'>('all')

const defKindOptions = computed<OptionItem[]>(() => [
  { label: t('metrics.filter.all'), value: 'all' },
  { label: t('metrics.tab.atomic'), value: 'atomic' },
  { label: t('metrics.tab.derived'), value: 'derived' },
])

const filteredDefinitions = computed<MetricDefinition[]>(() => {
  const kw = defKeyword.value.trim().toLowerCase()
  return definitions.value.filter((d) => {
    if (defKind.value !== 'all' && d.kind !== defKind.value) return false
    if (kw) {
      const hay = [
        d.name,
        d.dataSource,
        returnTypeLabel(d.returnType),
        paramTypeLabel(d.paramType),
        kindLabel(d),
        d.valueMode,
        (d.supportedOperators || []).map((o) => operatorLabel(o)).join(' '),
      ].join(' ').toLowerCase()
      if (!hay.includes(kw)) return false
    }
    return true
  })
})

// ===== 指标模板：搜索 + 状态筛选 =====
const tplKeyword = ref('')
const tplStatus = ref<'all' | 'enabled' | 'disabled'>('all')

const tplStatusOptions = computed<OptionItem[]>(() => [
  { label: t('metrics.filter.all'), value: 'all' },
  { label: t('metrics.status.enabled'), value: 'enabled' },
  { label: t('metrics.status.disabled'), value: 'disabled' },
])

const filteredTemplates = computed<MetricTemplate[]>(() => {
  const kw = tplKeyword.value.trim().toLowerCase()
  return templateList.value.filter((tpl) => {
    if (tplStatus.value !== 'all' && tpl.status !== tplStatus.value) return false
    if (kw) {
      const hay = [
        tpl.name,
        tpl.metricName,
        (tpl.operators || []).map((o) => operatorLabel(o)).join(' '),
      ].join(' ').toLowerCase()
      if (!hay.includes(kw)) return false
    }
    return true
  })
})

// ===== 指标模板列辅助 =====
function templateRange(row: MetricTemplate): string {
  const c = row.paramConfig
  if (!c || (c.min == null && c.max == null && c.step == null)) return '-'
  const parts: string[] = []
  if (c.min != null) parts.push(`min=${c.min}`)
  if (c.max != null) parts.push(`max=${c.max}`)
  if (c.step != null) parts.push(`step=${c.step}`)
  return parts.join(' / ')
}
function templateDomain(row: MetricTemplate): string {
  const segs = row.valueDomain?.segments
  if (!segs || !segs.length) return '-'
  return segs.map((s) => `${s.min}~${s.max}`).join('，')
}

// ===== 指标定义表（n-data-table）列定义 =====
const defColumns = computed<DataTableColumns<MetricDefinition>>(() => [
  {
    title: t('metrics.col.name'),
    key: 'name',
    minWidth: 160,
    render: (row) => h('span', { class: 'ws-cell-name' }, row.name),
  },
  {
    title: t('metrics.col.type'),
    key: 'kind',
    width: 96,
    render: (row) => h(KindIcon, { kind: row.kind, size: 18 }),
  },
  {
    title: t('metrics.col.dataSource'),
    key: 'dataSource',
    minWidth: 200,
    render: (row) => h('code', { class: 'ws-code' }, row.dataSource),
  },
  {
    title: t('metrics.col.inOutType'),
    key: 'inOut',
    width: 150,
    render: (row) => h('span', inOutLabel(row)),
  },
  {
    title: t('metrics.col.operatorCount'),
    key: 'operators',
    width: 110,
    render: (row) => h(OperatorBadge, { value: row.supportedOperators, catalog: operatorCatalog.value }),
  },
  {
    title: t('metrics.col.action'),
    key: 'action',
    width: 88,
    render: (row) =>
      h(
        NButton,
        { size: 'small', quaternary: true, onClick: (e: MouseEvent) => { e.stopPropagation(); openDetail(row) } },
        { default: () => t('metrics.btn.view') },
      ),
  },
])

function defRowProps(row: MetricDefinition) {
  return {
    style: 'cursor:pointer',
    onClick: () => openDetail(row),
    onKeydown: (e: KeyboardEvent) => {
      if (e.key === 'Enter') openDetail(row)
    },
  }
}

// ===== 指标模板表（n-data-table，保留 CRUD 操作列）列定义 =====
const tplColumns = computed<DataTableColumns<MetricTemplate>>(() => [
  {
    title: t('metrics.col.name'),
    key: 'name',
    minWidth: 160,
    render: (row) => h('span', { class: 'ws-cell-name' }, row.name),
  },
  {
    title: t('metrics.col.metric'),
    key: 'metric',
    minWidth: 200,
    render: (row) =>
      h('span', { class: 'ws-metric-cell' }, [
        h(KindIcon, { kind: row.metricKind ?? 'atomic', size: 18 }),
        ' ',
        row.metricName ?? '-',
      ]),
  },
  {
    title: t('metrics.tpl.outputType'),
    key: 'dataType',
    width: 150,
    render: (row) =>
      h('span', row.dataType ? `${returnTypeLabel(row.dataType)}${row.unit ? ` (${row.unit})` : ''}` : '-'),
  },
  {
    title: t('metrics.col.operatorCount'),
    key: 'operators',
    width: 110,
    render: (row) => h(OperatorBadge, { value: row.operators, catalog: operatorCatalog.value }),
  },
  {
    title: t('metrics.col.status'),
    key: 'status',
    width: 90,
    render: (row) =>
      h(
        NTag,
        { size: 'small', type: row.status === 'enabled' ? 'success' : 'default' },
        { default: () => (row.status === 'enabled' ? t('metrics.status.enabled') : t('metrics.status.disabled')) },
      ),
  },
  {
    title: t('metrics.col.action'),
    key: 'action',
    width: 210,
    render: (row) =>
      h('div', { class: 'ws-row-actions' }, [
        h(NButton, { size: 'small', quaternary: true, onClick: () => openTemplateEdit(row) }, { default: () => t('metrics.btn.edit') }),
        h(
          NButton,
          { size: 'small', quaternary: true, onClick: () => toggleTemplate(row) },
          { default: () => (row.status === 'enabled' ? t('metrics.btn.disable') : t('metrics.btn.enable')) },
        ),
        h(
          NButton,
          { size: 'small', quaternary: true, type: 'error', onClick: () => removeTemplate(row) },
          { default: () => t('metrics.btn.delete') },
        ),
      ]),
  },
])

// ===== 指标模板新建/编辑 =====
const showTemplateModal = ref(false)
const templateEditId = ref('')
const savingTpl = ref(false)
const emptyTplForm = () => ({
  name: '',
  metricDefinition: null as string | null,
  operators: [] as string[],
  paramConfig: { min: null, max: null, step: null, prefix: '', suffix: '', allOption: false },
  valueDomain: { segments: [] as any[] },
  paramEnums: [] as string[],
  paramAllowNull: false,
  description: '',
  status: 'enabled',
})
const tplForm = ref<any>(emptyTplForm())

const templateModalTitle = computed(() =>
  templateEditId.value ? t('metrics.dialog.editTemplate') : t('metrics.dialog.createTemplate'),
)

const metricDefinitionOptions = computed(() =>
  definitions.value.map((d) => ({
    label: `${d.name}（${d.dataSource}）`,
    value: `${d.kind}:${d.id}`,
  })),
)

const selectedTemplateDefinition = computed<MetricDefinition | undefined>(() => {
  const key = tplForm.value.metricDefinition
  if (!key) return undefined
  const [kind, id] = String(key).split(':')
  return definitions.value.find((d) => d.kind === kind && d.id === id)
})

const showTemplateParamConfig = computed<boolean>(() => {
  const d = selectedTemplateDefinition.value
  if (!d) return false
  if (d.valueMode !== 'parametric_handler') return false
  // 派生函数注册表声明了参数才展示参数配置
  return d.isParametric !== false
})

const paramPrecision = computed<number>(() => {
  const d = selectedTemplateDefinition.value
  return d?.paramType === 'continuous' ? 2 : 0
})

const paramConfigHint = computed(() => {
  const d = selectedTemplateDefinition.value
  return d?.paramType === 'continuous'
    ? t('metrics.tpl.paramHint')
    : t('metrics.tpl.paramHintDiscrete')
})

function generateValues(min?: number | null, max?: number | null, step?: number | null): number[] {
  if (min == null || max == null || step == null || step <= 0) return []
  const vals: number[] = []
  for (let v = min; v <= max + 1e-9; v += step) {
    vals.push(Number(v.toFixed(6)))
  }
  return vals
}

function formatPreviewValue(n: number): string {
  return Number(n.toFixed(6)).toString()
}

const paramPreviewValues = computed<string[]>(() => {
  const c = tplForm.value.paramConfig
  return generateValues(c.min, c.max, c.step).map(formatPreviewValue)
})

const supportedOperatorOptions = computed<OptionItem[]>(() => {
  const d = selectedTemplateDefinition.value
  if (!d?.supportedOperators?.length) return []
  const allowed = new Set(d.supportedOperators)
  return operatorCatalog.value.filter((o) => allowed.has(o.value))
})

function toggleOperator(value: string) {
  const set = new Set(tplForm.value.operators)
  if (set.has(value)) set.delete(value)
  else set.add(value)
  tplForm.value.operators = Array.from(set)
}

function segmentPreviewValues(seg: any): string[] {
  return generateValues(seg?.min, seg?.max, seg?.step).map(formatPreviewValue)
}

function onTemplateMetricChange() {
  const d = selectedTemplateDefinition.value
  // 切换指标后重置算子为当前指标支持的全部算子（全启）
  if (d?.supportedOperators?.length) {
    tplForm.value.operators = [...d.supportedOperators]
  } else {
    tplForm.value.operators = []
  }
  // 对象路径指标无需参数，切回 handler 时清空旧参数避免误解
  if (!showTemplateParamConfig.value) {
    tplForm.value.paramConfig = { min: null, max: null, step: null, prefix: '', suffix: '', allOption: false }
  }
}

function openTemplateCreate() {
  templateEditId.value = ''
  tplForm.value = emptyTplForm()
  showTemplateModal.value = true
}

function openTemplateEdit(row: MetricTemplate) {
  templateEditId.value = row.id
  const cfg = row.paramConfig || {}
  const domain = row.valueDomain || {}
  const metricKey = row.metricKind && (row.atomicMetric || row.derivedMetric)
    ? `${row.metricKind}:${row.atomicMetric || row.derivedMetric}`
    : null
  tplForm.value = {
    name: row.name,
    metricDefinition: metricKey,
    operators: row.operators || [],
    paramConfig: {
      min: cfg.min ?? null,
      max: cfg.max ?? null,
      step: cfg.step ?? null,
      prefix: cfg.prefix ?? '',
      suffix: cfg.suffix ?? '',
      allOption: !!cfg.allOption,
    },
    valueDomain: { segments: (domain.segments || []).map((s: any) => ({ ...s })) },
    paramEnums: row.paramEnums || [],
    paramAllowNull: !!row.paramAllowNull,
    description: row.description || '',
    status: row.status || 'enabled',
  }
  showTemplateModal.value = true
}

function addSegment() {
  tplForm.value.valueDomain.segments.push({ min: null, max: null, step: null, label: '' })
}
function removeSegment(idx: number) {
  tplForm.value.valueDomain.segments.splice(idx, 1)
}

async function submitTemplate() {
  if (!tplForm.value.name?.trim()) {
    message.warning(t('metrics.msg.requiredName'))
    return
  }
  if (!tplForm.value.metricDefinition) {
    message.warning(t('metrics.msg.selectOneMetric'))
    return
  }
  const [kind, id] = String(tplForm.value.metricDefinition).split(':')
  if (!kind || !id) {
    message.warning(t('metrics.msg.selectOneMetric'))
    return
  }
  if (!tplForm.value.operators?.length) {
    message.warning(t('metrics.msg.requiredOperators'))
    return
  }
  savingTpl.value = true
  try {
    const payload = {
      name: tplForm.value.name,
      atomicMetric: kind === 'atomic' ? id : null,
      derivedMetric: kind === 'derived' ? id : null,
      operators: tplForm.value.operators,
      paramConfig: tplForm.value.paramConfig,
      valueDomain: tplForm.value.valueDomain,
      paramEnums: tplForm.value.paramEnums,
      paramAllowNull: tplForm.value.paramAllowNull,
      description: tplForm.value.description,
      status: tplForm.value.status || 'enabled',
    }
    if (templateEditId.value) {
      await updateMetricTemplate(templateEditId.value, payload)
    } else {
      await createMetricTemplate(payload)
    }
    message.success(templateEditId.value ? t('metrics.msg.updated') : t('metrics.msg.created'))
    showTemplateModal.value = false
    templateEditId.value = ''
    await load()
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.saveFailed'))
  } finally {
    savingTpl.value = false
  }
}

async function removeTemplate(row: MetricTemplate) {
  // 中等破坏性操作：直接执行 + Toast 撤销（停留 8s），符合 AGENTS.md R-106
  const restorePayload = {
    name: row.name,
    atomicMetric: row.atomicMetric || null,
    derivedMetric: row.derivedMetric || null,
    operators: row.operators || [],
    paramConfig: row.paramConfig || { min: null, max: null, step: null, prefix: '', suffix: '', allOption: false },
    valueDomain: row.valueDomain || { segments: [] },
    paramEnums: row.paramEnums || [],
    paramAllowNull: !!row.paramAllowNull,
    description: row.description || '',
    status: row.status || 'enabled',
  }
  try {
    await deleteMetricTemplate(row.id)
    await load()
    message.success(t('metrics.msg.deleted'), {
      duration: 8000,
      action: {
        label: t('metrics.btn.undo'),
        onClick: async () => {
          try {
            await createMetricTemplate(restorePayload)
            message.success(t('metrics.msg.restored'))
            await load()
          } catch (err: any) {
            const detail = err?.response?.data?.error
            message.error(detail ? String(detail) : t('metrics.msg.saveFailed'))
          }
        },
      },
    })
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.deleteFailed'))
  }
}

async function toggleTemplate(row: MetricTemplate) {
  try {
    const next = row.status === 'enabled' ? 'disabled' : 'enabled'
    await updateMetricTemplate(row.id, { status: next })
    message.success(next === 'disabled' ? t('metrics.msg.disabled') : t('metrics.msg.enabled'))
    await load()
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.saveFailed'))
  }
}

// ===== 主加载 =====
async function load() {
  loading.value = true
  try {
    const [atomic, derived, templates, ops, defs] = await Promise.all([
      listAtomicMetrics(),
      listDerivedMetrics(),
      listMetricTemplates(),
      listOperators(),
      listMetricDefinitions(),
    ])
    atomicList.value = atomic
    derivedList.value = derived
    templateList.value = templates
    operatorCatalog.value = ops
    definitions.value = defs
    try {
      fieldPaths.value = await listCandidateFields()
    } catch {
      fieldPaths.value = []
    }
  } catch {
    message.error(t('metrics.msg.loadFailed'))
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.metrics-ws {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.ws-title {
  margin: 0;
  font-size: var(--text-h3, 20px);
  font-weight: 600;
  color: var(--ink);
}
.ws-subtitle {
  margin: 4px 0 0;
  font-size: var(--text-small, 13px);
  color: var(--ink-faint);
}
.ws-body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: var(--space-3);
}
/* 让 n-tabs 占满 ws-body，tab pane 成为 flex 列，滚动职责下放到表格区 */
.metrics-ws :deep(.n-tabs) {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
}
.metrics-ws :deep(.n-tabs-pane-wrapper) {
  flex: 1 1 auto;
  min-height: 0;
}
.metrics-ws :deep(.n-tab-pane) {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.ws-tab-header {
  flex-shrink: 0;
}
.ws-table-wrap {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
  position: relative;
}
.ws-spin {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}
.ws-spin :deep(.n-spin-content) {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
}

/* ===== 工具栏：搜索 + 筛选 + 计数 ===== */
.ws-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}
.ws-toolbar-grow { flex: 1 1 auto; margin-bottom: 0; }
.ws-search { flex: 1 1 260px; max-width: 420px; }
.ws-filter { flex: 0 0 160px; }
.ws-result-count {
  margin-left: auto;
  color: var(--ink-faint);
  font-size: var(--fs-12);
  white-space: nowrap;
}
.ws-tab-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}

/* ===== 图例（原子 / 派生 类型说明） ===== */
.ws-legend {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-3);
  flex-wrap: wrap;
}
.ws-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-small, 13px);
  color: var(--ink-soft);
}

/* ===== 数据表（替代卡片网格） ===== */
.ws-table {
  width: 100%;
}
.ws-cell-name {
  font-weight: 600;
  color: var(--ink);
}
.ws-metric-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.ws-row-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-wrap: nowrap;
}

/* 空态：在表格滚动区内撑满剩余高度 */
.ws-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1 1 auto;
  min-height: 240px;
  padding: var(--space-8) 0;
}

/* ===== 共享视觉元素（详情弹窗与卡片统一） ===== */
.ws-code {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--g1);
  border: 1px solid var(--border-hairline);
  color: var(--ink);
  word-break: break-all;
}
.ws-op-tag {
  font-size: var(--fs-12);
  padding: 1px 8px;
  border-radius: var(--radius-pill);
  background: var(--brand-a12);
  border: 1px solid var(--brand-a22);
  color: var(--brand-text);
  white-space: nowrap;
}
.ws-enum-tag {
  font-size: var(--fs-12);
  padding: 1px 8px;
  border-radius: var(--radius-pill);
  background: var(--c-success-soft);
  border: 1px solid color-mix(in srgb, var(--c-success) 24%, transparent);
  color: var(--c-success-deep);
  white-space: nowrap;
}
.ws-kind-line {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.ws-kind-text {
  font-size: var(--text-base, 15px);
  font-weight: 600;
  color: var(--ink);
}
.ws-ops { display: flex; flex-wrap: wrap; gap: var(--space-1); }
.ws-muted { color: var(--ink-faint); font-size: var(--text-small, 13px); }

/* 详情弹窗 */
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
  animation: wb-fade-up var(--duration-slow) var(--ease-out) both;
}
.detail-cell {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  background: var(--g1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}
.detail-cell-wide { grid-column: 1 / -1; }
.cell-label {
  color: var(--ink-faint);
  font-size: var(--fs-12);
  font-weight: 500;
}
.cell-value {
  color: var(--ink);
  font-size: var(--text-small, 13px);
  line-height: 1.5;
}

/* 详情弹窗：参数化 Handler 的参数编辑区 */
.detail-params-block { display: flex; flex-direction: column; gap: var(--space-3); }
.detail-params-form { display: flex; flex-direction: column; gap: var(--space-2); }
.detail-param-row { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.param-label { min-width: 96px; color: var(--ink-strong); font-size: var(--fs-13, 13px); font-weight: 500; }
.param-input { width: 220px; max-width: 100%; }
.param-hint { color: var(--ink-faint); font-size: var(--fs-12); line-height: 1.4; }

/* 模板弹窗分段 */
.tpl-form { padding-right: 2px; }
.tpl-section { width: 100%; }
.tpl-row { display: flex; gap: var(--space-3); flex-wrap: wrap; margin-bottom: var(--space-1); align-items: flex-end; }
.tpl-field { flex: 1 1 0; min-width: 140px; margin-bottom: var(--space-1); }
.tpl-segments { display: flex; flex-direction: column; gap: var(--space-2); }
.seg-row { display: flex; gap: var(--space-2); align-items: center; flex-wrap: wrap; }
.seg-field { flex: 1 1 120px; }

/* 指标模板弹窗新样式 */
.tpl-output-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  margin-bottom: var(--space-4);
  background: var(--c-info-soft);
  border: 1px solid color-mix(in srgb, var(--c-info) 20%, transparent);
  border-radius: var(--radius-md);
  font-size: var(--text-small, 13px);
}
.tpl-output-label { color: var(--ink-soft); font-weight: 500; }
.tpl-output-unit { color: var(--ink); font-weight: 600; }
.tpl-output-hint { margin-left: auto; color: var(--ink-faint); }

.tpl-section-card {
  background: var(--surface);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.tpl-section-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  flex-wrap: wrap;
}
.tpl-section-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--c-warning);
  color: #fff;
  font-size: var(--fs-12);
  font-weight: 700;
}
.tpl-section-title { font-weight: 600; color: var(--ink); }
.tpl-section-hint { margin-left: auto; color: var(--ink-faint); font-size: var(--fs-12); }
.tpl-section-body { display: flex; flex-direction: column; gap: var(--space-2); }
.tpl-range-sep { color: var(--ink-faint); padding-bottom: 8px; }
.tpl-switch-field :deep(.n-form-item-label) { height: auto; }

.tpl-preview {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  background: var(--c-info-soft);
  border-radius: var(--radius-md);
  color: var(--c-info-deep);
  font-size: var(--fs-12);
  line-height: 1.6;
}
.tpl-preview-tag { font-weight: 500; white-space: nowrap; }
.tpl-info-text {
  color: var(--ink-faint);
  font-size: var(--text-small, 13px);
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-4);
  background: var(--g1);
  border-radius: var(--radius-md);
}

.tpl-operator-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.tpl-op-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border-hairline);
  background: var(--surface);
  color: var(--ink-soft);
  font-size: var(--fs-12);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out);
}
.tpl-op-chip:hover { border-color: var(--c-success); }
.tpl-op-chip.is-checked {
  background: var(--c-success-soft);
  border-color: color-mix(in srgb, var(--c-success) 30%, transparent);
  color: var(--c-success-deep);
}
.tpl-op-chip input { position: absolute; opacity: 0; width: 0; height: 0; }

.tpl-segment-block { display: flex; flex-direction: column; gap: var(--space-2); }
.tpl-segment-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.tpl-segment-label { color: var(--ink-faint); font-size: var(--fs-12); min-width: 36px; }
.tpl-seg-field { width: 100px; }
.tpl-unit-text { color: var(--ink-faint); font-size: var(--fs-12); }
.tpl-step-field { width: 120px; margin-bottom: 0; }
.tpl-step-field :deep(.n-form-item-label) { font-size: var(--fs-12); }

@media (max-width: 768px) {
  .detail-grid { grid-template-columns: 1fr; }
  .tpl-section-hint { margin-left: 0; width: 100%; }
  .tpl-output-hint { margin-left: 0; width: 100%; }
}
</style>
