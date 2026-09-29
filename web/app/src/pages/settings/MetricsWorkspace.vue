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
          <div class="ws-hint">
            <span class="ws-hint-dot" />
            {{ t('metrics.definitions.readonlyHint') }}
          </div>
          <n-data-table
            :columns="definitionColumns"
            :data="definitions"
            :loading="loading"
            :bordered="false"
            size="small"
            :row-key="(r: any) => r.id"
          />
        </n-tab-pane>

        <!-- ---------- Tab 2：指标模板（CRUD） ---------- -->
        <n-tab-pane name="template" :tab="t('metrics.tab.template')">
          <div class="ws-tab-bar">
            <n-button type="primary" @click="openTemplateCreate">
              {{ t('metrics.btn.create') }}{{ t('metrics.tab.template') }}
            </n-button>
          </div>
          <n-data-table
            :columns="templateColumns"
            :data="templateList"
            :loading="loading"
            :bordered="false"
            size="small"
            :row-key="(r: any) => r.id"
          />
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
          <div class="detail-cell">
            <div class="cell-label">{{ t('metrics.col.valueMode') }}</div>
            <div class="cell-value">
              <span class="ws-mode-badge" :class="valueModeClass(detailRow)">
                {{ valueModeLabel(detailRow) }}
              </span>
            </div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">{{ t('metrics.col.paramType') }}</div>
            <div class="cell-value">{{ paramTypeLabel(detailRow.paramType) }}</div>
          </div>
          <div class="detail-cell detail-cell-wide">
            <div class="cell-label">{{ t('metrics.col.dataSource') }}</div>
            <div class="cell-value">
              <code class="ws-code">{{ detailRow.dataSource }}</code>
            </div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">{{ t('metrics.col.returnType') }}</div>
            <div class="cell-value">
              {{ returnTypeLabel(detailRow.returnType) }}<template v-if="detailRow.unit">（{{ detailRow.unit }}）</template>
            </div>
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
        </div>
      </template>
    </n-modal>

    <!-- ========== 指标模板新建/编辑弹窗（PRD：参数 / 算子 / 值域） ========== -->
    <n-modal
      v-model:show="showTemplateModal"
      preset="card"
      :title="templateModalTitle"
      style="width: 720px; max-width: 94vw;"
      :mask-closable="false"
    >
      <n-form :model="tplForm" label-placement="top">
        <n-form-item :label="t('metrics.form.name')" required>
          <n-input v-model:value="tplForm.name" :placeholder="t('metrics.form.name')" />
        </n-form-item>

        <n-form-item :label="t('metrics.form.atomicMetric')">
          <n-select
            v-model:value="tplForm.atomicMetric"
            :options="atomicOptions"
            clearable
            :placeholder="t('metrics.form.atomicMetric')"
            @update:value="onTemplateMetricChange"
          />
        </n-form-item>
        <n-form-item :label="t('metrics.form.derivedMetric')">
          <n-select
            v-model:value="tplForm.derivedMetric"
            :options="derivedOptions"
            clearable
            :placeholder="t('metrics.form.derivedMetric')"
            @update:value="onTemplateMetricChange"
          />
        </n-form-item>

        <n-divider title-placement="left">{{ t('metrics.tpl.sectionParam') }}</n-divider>
        <div class="tpl-section">
          <div class="tpl-row">
            <n-form-item :label="t('metrics.tpl.rangeMin')" class="tpl-field">
              <n-input-number v-model:value="tplForm.paramConfig.min" :precision="0" />
            </n-form-item>
            <n-form-item :label="t('metrics.tpl.rangeMax')" class="tpl-field">
              <n-input-number v-model:value="tplForm.paramConfig.max" :precision="0" />
            </n-form-item>
            <n-form-item :label="t('metrics.tpl.step')" class="tpl-field">
              <n-input-number v-model:value="tplForm.paramConfig.step" :min="1" :precision="0" />
            </n-form-item>
          </div>
          <div class="tpl-row">
            <n-form-item :label="t('metrics.tpl.prefix')" class="tpl-field">
              <n-input v-model:value="tplForm.paramConfig.prefix" placeholder="≥" />
            </n-form-item>
            <n-form-item :label="t('metrics.tpl.suffix')" class="tpl-field">
              <n-input v-model:value="tplForm.paramConfig.suffix" :placeholder="t('pages.settings.MetricsWorkspace.s2')" />
            </n-form-item>
            <n-form-item :label="t('metrics.tpl.allOption')" class="tpl-field">
              <n-switch v-model:value="tplForm.paramConfig.allOption" />
            </n-form-item>
          </div>
          <n-form-item v-if="selectedTemplateDataType === 'string'" :label="t('metrics.tpl.paramEnums')">
            <n-dynamic-tags v-model:value="tplForm.paramEnums" />
          </n-form-item>
          <n-form-item :label="t('metrics.tpl.allowNull')">
            <n-switch v-model:value="tplForm.paramAllowNull" />
          </n-form-item>
        </div>

        <n-divider title-placement="left">{{ t('metrics.tpl.sectionOperators') }}</n-divider>
        <n-form-item :label="t('metrics.tpl.enabledOperators')" required>
          <n-select
            v-model:value="tplForm.operators"
            multiple
            :options="operatorCatalog"
            :placeholder="t('metrics.form.operators')"
          />
        </n-form-item>

        <n-divider title-placement="left">{{ t('metrics.tpl.sectionDomain') }}</n-divider>
        <div class="tpl-segments">
          <div v-for="(seg, idx) in tplForm.valueDomain.segments" :key="idx" class="seg-row">
            <n-input-number v-model:value="seg.min" :placeholder="t('metrics.tpl.rangeMin')" class="seg-field" />
            <n-input-number v-model:value="seg.max" :placeholder="t('metrics.tpl.rangeMax')" class="seg-field" />
            <n-input-number v-model:value="seg.step" :min="1" :precision="0" :placeholder="t('metrics.tpl.step')" class="seg-field" />
            <n-input v-model:value="seg.label" :placeholder="t('metrics.tpl.segLabel')" class="seg-field" />
            <n-button size="small" quaternary type="error" @click="removeSegment(idx)">{{ t('metrics.btn.delete') }}</n-button>
          </div>
          <n-button size="small" dashed @click="addSegment">{{ t('metrics.tpl.addSegment') }}</n-button>
        </div>

        <n-form-item :label="t('metrics.form.description')">
          <n-input v-model:value="tplForm.description" type="textarea" :rows="2" />
        </n-form-item>
        <n-form-item :label="t('metrics.form.status')">
          <n-select v-model:value="tplForm.status" :options="statusOptions" />
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
 * MetricsWorkspace —— 指标库。
 *
 * 模块拆分（用户诉求）：
 *   - 指标库（本页）：两个页签
 *       1) 指标定义 —— 只读统一视图（原子 + 派生合并），点击指标名弹出居中详情弹窗。
 *          原子指标与派生指标已整合进「指标定义」，故不再提供独立的新建入口（无停用/启用状态，
 *          展示系统中已注册的全部指标）；取值方式明确为「对象路径 / 参数化 Handler」，
 *          枚举型指标同时展示其出参枚举值。
 *       2) 指标模板 —— 新增/编辑/删除/停用（CRUD），可配置参数范围/步长/显示/算子/值域
 *   - 规则引擎（RuleAuthoring.vue）：承接原「规则配置与执行」「规则管理」两个功能
 */
import { computed, h, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  NButton,
  NModal,
  NSwitch,
  NTag,
  useMessage,
} from 'naive-ui'
import {
  createMetricTemplate,
  deleteMetricTemplate,
  listAtomicMetrics,
  listDerivedMetrics,
  listMetricDefinitions,
  listMetricTemplates,
  listOperators,
  listCandidateFields,
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

function openDetail(row: MetricDefinition) {
  detailRow.value = row
  detailVisible.value = true
}

function valueModeClass(row: MetricDefinition): string {
  return row.valueMode === 'parametric_handler' ? 'is-parametric' : 'is-object'
}
function valueModeLabel(row: MetricDefinition): string {
  return row.valueMode === 'parametric_handler'
    ? t('metrics.valueMode.parametric')
    : t('metrics.valueMode.objectPath')
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

const definitionColumns = computed(() => [
  {
    title: t('metrics.col.name'),
    key: 'name',
    render: (row: MetricDefinition) =>
      h('span', {
        class: 'ws-def-name-link',
        style: 'cursor:pointer;font-weight:600;color:var(--brand-text);',
        onClick: () => openDetail(row),
      }, { default: () => row.name }),
  },
  {
    title: t('metrics.col.valueMode'),
    key: 'valueMode',
    render: (row: MetricDefinition) =>
      h('span', { class: `ws-mode-badge ${valueModeClass(row)}` }, { default: () => valueModeLabel(row) }),
  },
  {
    title: t('metrics.col.dataSource'),
    key: 'dataSource',
    render: (row: MetricDefinition) => h('code', { class: 'ws-code' }, { default: () => row.dataSource }),
  },
  {
    title: t('metrics.col.paramType'),
    key: 'paramType',
    render: (row: MetricDefinition) => h('span', { class: 'ws-muted' }, { default: () => paramTypeLabel(row.paramType) }),
  },
  {
    title: t('metrics.col.returnType'),
    key: 'returnType',
    render: (row: MetricDefinition) =>
      h('span', { class: 'ws-muted' }, {
        default: () => `${returnTypeLabel(row.returnType)}${row.unit ? '（' + row.unit + '）' : ''}`,
      }),
  },
  {
    title: t('metrics.col.enumValues'),
    key: 'enumValues',
    render: (row: MetricDefinition) => {
      const evs = enumValuesOf(row)
      if (!row.isEnum || !evs.length) return h('span', { class: 'ws-muted' }, { default: () => '-' })
      return h('div', { class: 'ws-ops' }, {
        default: () => evs.map((ev: string) =>
          h('span', { class: 'ws-enum-tag' }, { default: () => ev })),
      })
    },
  },
  {
    title: t('metrics.col.operators'),
    key: 'supportedOperators',
    render: (row: MetricDefinition) =>
      h('div', { class: 'ws-ops' }, {
        default: () =>
          (row.supportedOperators || []).map((op: string) =>
            h('span', { class: 'ws-op-tag' }, { default: () => operatorLabel(op) })),
      }),
  },
])

// ===== 指标模板列 =====
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

const templateColumns = computed(() => [
  { title: t('metrics.col.name'), key: 'name' },
  { title: t('metrics.col.metric'), key: 'metricName' },
  {
    title: t('metrics.tpl.range'),
    key: 'range',
    render: (row: MetricTemplate) => h('span', { class: 'ws-muted' }, { default: () => templateRange(row) }),
  },
  {
    title: t('metrics.col.operators'),
    key: 'operators',
    render: (row: MetricTemplate) =>
      h('div', { class: 'ws-ops' }, {
        default: () => (row.operators || []).map((op: string) =>
          h('span', { class: 'ws-op-tag' }, { default: () => operatorLabel(op) })),
      }),
  },
  {
    title: t('metrics.tpl.domain'),
    key: 'domain',
    render: (row: MetricTemplate) => h('span', { class: 'ws-muted' }, { default: () => templateDomain(row) }),
  },
  {
    title: t('metrics.col.status'),
    key: 'status',
    render: (row: MetricTemplate) =>
      h(NTag, { size: 'small', type: row.status === 'enabled' ? 'success' : 'default' }, {
        default: () => (row.status === 'enabled' ? t('metrics.status.enabled') : t('metrics.status.disabled')),
      }),
  },
  {
    title: t('metrics.col.action'),
    key: 'action',
    render: (row: MetricTemplate) =>
      h('div', { class: 'ws-actions-cell' }, [
        h(NButton, { size: 'small', quaternary: true, onClick: () => openTemplateEdit(row) }, { default: () => t('metrics.btn.edit') }),
        h(NButton, { size: 'small', quaternary: true, onClick: () => toggleTemplate(row) }, { default: () => (row.status === 'enabled' ? t('metrics.btn.disable') : t('metrics.btn.enable')) }),
        h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeTemplate(row) }, { default: () => t('metrics.btn.delete') }),
      ]),
  },
])

// ===== 指标模板新建/编辑 =====
const showTemplateModal = ref(false)
const templateEditId = ref('')
const savingTpl = ref(false)
const emptyTplForm = () => ({
  name: '',
  atomicMetric: null,
  derivedMetric: null,
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

const statusOptions = computed(() => [
  { label: t('metrics.status.enabled'), value: 'enabled' },
  { label: t('metrics.status.disabled'), value: 'disabled' },
])

const atomicOptions = computed(() =>
  atomicList.value.map((m) => ({ label: `${m.name}（${m.sourcePath}）`, value: m.id })),
)
const derivedOptions = computed(() =>
  derivedList.value.map((m) => ({ label: `${m.name}（${m.calcFunc}）`, value: m.id })),
)

const selectedTemplateDataType = computed<string>(() => {
  const am = tplForm.value.atomicMetric
  const dm = tplForm.value.derivedMetric
  if (am) return atomicList.value.find((x) => x.id === am)?.dataType || ''
  if (dm) return derivedList.value.find((x) => x.id === dm)?.dataType || ''
  return ''
})

function onTemplateMetricChange() {
  // 切换引用指标时不清空已选算子，仅保证数据类型联动（枚举字段展示枚举值输入）
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
  tplForm.value = {
    name: row.name,
    atomicMetric: row.atomicMetric ?? null,
    derivedMetric: row.derivedMetric ?? null,
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
  const hasAtomic = !!tplForm.value.atomicMetric
  const hasDerived = !!tplForm.value.derivedMetric
  if (hasAtomic === hasDerived) {
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
      atomicMetric: tplForm.value.atomicMetric,
      derivedMetric: tplForm.value.derivedMetric,
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
  try {
    await deleteMetricTemplate(row.id)
    message.success(t('metrics.msg.deleted'))
    await load()
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
  overflow-y: auto;
  padding-top: var(--space-3);
}
.ws-tab-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--space-3);
  gap: var(--space-2);
}

/* 只读提示 */
.ws-hint {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-small, 13px);
  color: var(--ink-soft);
  background: var(--brand-a12);
  border: 1px solid var(--brand-a22);
  border-radius: var(--radius-md);
}
.ws-hint-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brand-600);
  flex: 0 0 auto;
}

/* ===== 共享视觉元素（列表与详情统一） ===== */
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
.ws-mode-badge {
  display: inline-flex;
  align-items: center;
  font-size: var(--fs-12);
  font-weight: 500;
  padding: 2px 10px;
  border-radius: var(--radius-pill);
  border: 1px solid transparent;
}
.ws-mode-badge.is-object {
  background: var(--c-info-soft);
  border-color: color-mix(in srgb, var(--c-info) 24%, transparent);
  color: var(--c-info-deep);
}
.ws-mode-badge.is-parametric {
  background: var(--c-warning-soft);
  border-color: color-mix(in srgb, var(--c-warning) 26%, transparent);
  color: var(--c-warning-deep);
}
.ws-ops { display: flex; flex-wrap: wrap; gap: var(--space-1); }
.ws-muted { color: var(--ink-faint); font-size: var(--text-small, 13px); }
.ws-actions-cell { display: flex; gap: 2px; }
.ws-def-name-link:hover { text-decoration: underline; }

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

/* 模板弹窗分段 */
.tpl-section { width: 100%; }
.tpl-row { display: flex; gap: var(--space-3); flex-wrap: wrap; margin-bottom: var(--space-1); }
.tpl-field { flex: 1 1 0; min-width: 140px; margin-bottom: var(--space-1); }
.tpl-segments { display: flex; flex-direction: column; gap: var(--space-2); }
.seg-row { display: flex; gap: var(--space-2); align-items: center; flex-wrap: wrap; }
.seg-field { flex: 1 1 120px; }

@media (max-width: 768px) {
  .detail-grid { grid-template-columns: 1fr; }
}
</style>
