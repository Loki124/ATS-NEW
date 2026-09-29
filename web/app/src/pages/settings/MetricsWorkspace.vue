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
        <!-- ---------- Tab 1：指标定义（只读） ---------- -->
        <n-tab-pane name="definitions" :tab="t('metrics.tab.definitions')">
          <div class="ws-tab-bar">
            <n-button type="primary" @click="openCreate('atomic')">
              {{ t('metrics.btn.create') }}{{ t('metrics.tab.atomic') }}
            </n-button>
            <n-button type="primary" @click="openCreate('derived')">
              {{ t('metrics.btn.create') }}{{ t('metrics.tab.derived') }}
            </n-button>
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
            <div class="cell-label">{{ t('metrics.col.name') }}</div>
            <div class="cell-value">{{ detailRow.name }}</div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">{{ t('metrics.col.valueMode') }}</div>
            <div class="cell-value">
              <n-tag size="small" :type="valueModeMeta(detailRow).type">{{ valueModeMeta(detailRow).label }}</n-tag>
            </div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">{{ t('metrics.col.dataSource') }}</div>
            <div class="cell-value"><code class="ws-code">{{ detailRow.dataSource }}</code></div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">{{ t('metrics.col.paramType') }}</div>
            <div class="cell-value">{{ paramTypeLabel(detailRow.paramType) }}</div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">{{ t('metrics.col.returnType') }}</div>
            <div class="cell-value">
              {{ returnTypeLabel(detailRow.returnType) }}<template v-if="detailRow.unit">（{{ detailRow.unit }}）</template>
            </div>
          </div>
          <div class="detail-cell">
            <div class="cell-label">{{ t('metrics.col.status') }}</div>
            <div class="cell-value">
              <n-tag size="small" :type="detailRow.status === 'enabled' ? 'success' : 'default'">
                {{ detailRow.status === 'enabled' ? t('metrics.status.enabled') : t('metrics.status.disabled') }}
              </n-tag>
            </div>
          </div>
          <div v-if="detailRow.isEnum" class="detail-cell detail-cell-wide">
            <div class="cell-label">{{ t('metrics.col.isEnum') }}</div>
            <div class="cell-value">
              <n-tag size="small" type="warning">{{ t('metrics.tag.enum') }}</n-tag>
            </div>
          </div>
          <div class="detail-cell detail-cell-wide">
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
          <div v-if="detailRow.description" class="detail-cell detail-cell-wide">
            <div class="cell-label">{{ t('metrics.form.description') }}</div>
            <div class="cell-value">{{ detailRow.description }}</div>
          </div>
        </div>
      </template>
    </n-modal>

    <!-- ========== 指标新建/编辑弹窗（原子 / 派生，复用既有逻辑） ========== -->
    <n-modal
      v-model:show="showModal"
      preset="card"
      :title="modalTitle"
      style="width: 560px"
      :mask-closable="false"
    >
      <n-form :model="form" label-placement="top">
        <n-form-item :label="t('metrics.form.name')" required>
          <n-input v-model:value="form.name" :placeholder="t('metrics.form.name')" />
        </n-form-item>

        <n-form-item v-if="modalKind === 'atomic'" :label="t('metrics.form.sourcePath')" required>
          <n-select
            v-model:value="form.sourcePath"
            :options="fieldPathOptions"
            filterable
            clearable
            :placeholder="t('metrics.form.sourcePath')"
          />
          <template #feedback>
            <span class="ws-tip">{{ t('metrics.form.sourcePathTip') }}</span>
          </template>
        </n-form-item>

        <template v-if="modalKind === 'derived'">
          <n-form-item :label="t('metrics.form.calcFunc')" required>
            <n-select
              v-model:value="form.calcFunc"
              :options="derivedFuncOptions"
              :placeholder="t('metrics.form.calcFunc')"
              @update:value="onCalcFuncChange"
            />
          </n-form-item>
          <n-form-item :label="t('metrics.form.basePath')" required>
            <n-input v-model:value="form.basePath" placeholder="candidate.workExperience" />
          </n-form-item>
          <n-form-item v-if="selectedFuncHint?.paramSchema?.length" :label="t('metrics.form.params')">
            <div class="ws-params">
              <div v-for="p in selectedFuncHint.paramSchema" :key="p.key" class="ws-param-row">
                <span class="ws-param-label">{{ p.label }}<em v-if="p.required" class="ws-req">*</em></span>
                <n-input-number
                  v-if="p.type === 'number'"
                  v-model:value="form.params[p.key]"
                  :min="0"
                  class="ws-param-control"
                />
                <n-input
                  v-else-if="p.type === 'string'"
                  v-model:value="form.params[p.key]"
                  class="ws-param-control"
                />
                <n-select
                  v-else-if="p.type === 'select'"
                  v-model:value="form.params[p.key]"
                  :options="p.options"
                  class="ws-param-control"
                />
                <n-switch
                  v-else-if="p.type === 'boolean'"
                  v-model:value="form.params[p.key]"
                />
                <n-dynamic-tags
                  v-else-if="p.type === 'tags'"
                  v-model:value="form.params[p.key]"
                />
              </div>
            </div>
          </n-form-item>
          <n-form-item v-else :label="t('metrics.form.params')">
            <span class="ws-tip">{{ t('metrics.form.paramsEmpty') }}</span>
          </n-form-item>
        </template>

        <n-form-item :label="t('metrics.form.dataType')">
          <n-select v-model:value="form.dataType" :options="dataTypeOptions" />
        </n-form-item>
        <n-form-item :label="t('metrics.form.unit')">
          <n-input v-model:value="form.unit" :placeholder="t('pages.settings.MetricsWorkspace.s1')" />
        </n-form-item>
        <n-form-item :label="t('metrics.form.description')">
          <n-input v-model:value="form.description" type="textarea" :rows="2" />
        </n-form-item>
        <n-form-item :label="t('metrics.form.status')">
          <n-select v-model:value="form.status" :options="statusOptions" />
        </n-form-item>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="showModal = false">{{ t('metrics.btn.cancel') }}</n-button>
          <n-button type="primary" :loading="saving" @click="submitMetric">{{ t('metrics.btn.save') }}</n-button>
        </n-space>
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
 * MetricsWorkspace —— 指标库（重构后）。
 *
 * 模块拆分（用户诉求）：
 *   - 指标库（本页）：两个页签
 *       1) 指标定义 —— 只读统一视图（原子 + 派生合并），点击指标名弹出居中详情弹窗
 *       2) 指标模板 —— 新增/编辑/删除/停用（CRUD），可配置参数范围/步长/显示/算子/值域
 *   - 规则引擎（RuleAuthoring.vue）：承接原「规则配置与执行」「规则管理」两个功能
 *
 * 指标定义遵循 PRD：只读、无行级 CRUD（F-1.7）；顶部「新建原子/派生指标」用于注册新定义，
 * 与「定义是字段/注册的产物」语义一致。模板引用原子/派生指标，二者经自动生成信号联动。
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
  createAtomicMetric,
  createDerivedMetric,
  createMetricTemplate,
  deleteMetricTemplate,
  listAtomicMetrics,
  listDerivedFuncs,
  listDerivedMetrics,
  listMetricDefinitions,
  listMetricTemplates,
  listOperators,
  listCandidateFields,
  updateAtomicMetric,
  updateDerivedMetric,
  updateMetricTemplate,
  type AtomicMetric,
  type CandidateFieldPath,
  type DerivedFuncItem,
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
const derivedFuncs = ref<DerivedFuncItem[]>([])
const fieldPaths = ref<CandidateFieldPath[]>([])
const loading = ref(false)

// ===== 指标详情弹窗 =====
const detailVisible = ref(false)
const detailRow = ref<MetricDefinition | null>(null)

function openDetail(row: MetricDefinition) {
  detailRow.value = row
  detailVisible.value = true
}

const RETURN_TYPE_LABELS: Record<string, string> = {
  number: '数值',
  string: '字符串',
  boolean: '布尔',
  date: '日期',
}
function returnTypeLabel(type?: string): string {
  return (type && RETURN_TYPE_LABELS[type]) || type || '-'
}
function paramTypeLabel(type?: string): string {
  if (type === 'continuous') return t('metrics.paramType.continuous')
  if (type === 'discrete') return t('metrics.paramType.discrete')
  return '-'
}
function valueModeMeta(row: MetricDefinition): { label: string; type: 'default' | 'warning' } {
  if (row.valueMode === 'parametric_handler') {
    return { label: t('metrics.valueMode.parametric'), type: 'warning' }
  }
  return { label: t('metrics.valueMode.objectPath'), type: 'default' }
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
        style: 'cursor:pointer;font-weight:500;color:var(--brand);',
        onClick: () => openDetail(row),
      }, { default: () => row.name }),
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
    title: t('metrics.col.operators'),
    key: 'supportedOperators',
    render: (row: MetricDefinition) =>
      h('div', { class: 'ws-ops' }, {
        default: () =>
          (row.supportedOperators || []).map((op: string) =>
            h('span', { class: 'ws-op-tag' }, { default: () => operatorLabel(op) })),
      }),
  },
  {
    title: t('metrics.col.returnType'),
    key: 'returnType',
    render: (row: MetricDefinition) =>
      h('span', { class: 'ws-muted' }, {
        default: () => `${returnTypeLabel(row.returnType)}${row.unit ? '（' + row.unit + '）' : ''}`,
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

// ===== 指标新建/编辑（原子 / 派生） =====
const showModal = ref(false)
const modalKind = ref<'atomic' | 'derived'>('atomic')
const editMetricId = ref('')
const saving = ref(false)
const form = ref<any>({})

const statusOptions = computed(() => [
  { label: t('metrics.status.enabled'), value: 'enabled' },
  { label: t('metrics.status.disabled'), value: 'disabled' },
])

const selectedFuncHint = computed(() => {
  if (modalKind.value !== 'derived') return null
  return derivedFuncs.value.find((f) => f.name === form.value.calcFunc) || null
})

const dataTypeOptions = [
  { label: t('pages.settings.MetricsWorkspace.s3'), value: 'number' },
  { label: t('pages.settings.MetricsWorkspace.s4'), value: 'string' },
  { label: t('pages.settings.MetricsWorkspace.s5'), value: 'boolean' },
  { label: t('pages.settings.MetricsWorkspace.s6'), value: 'date' },
]

const atomicOptions = computed(() =>
  atomicList.value.map((m) => ({ label: `${m.name}（${m.sourcePath}）`, value: m.id })),
)
const derivedOptions = computed(() =>
  derivedList.value.map((m) => ({ label: `${m.name}（${m.calcFunc}）`, value: m.id })),
)
const derivedFuncOptions = computed(() =>
  derivedFuncs.value.map((f) => ({ label: f.label, value: f.name })),
)

const fieldPathOptions = computed(() => {
  const toOpts = (src: CandidateFieldPath[]) =>
    src.map((f) => ({ label: `${f.label}（${f.path}）`, value: f.path }))
  const groups = [
    { type: 'group' as const, label: t('metrics.fieldGroup.model'), key: 'model', children: toOpts(fieldPaths.value.filter((f) => f.source === 'model')) },
    { type: 'group' as const, label: t('metrics.fieldGroup.dynamic'), key: 'dynamic', children: toOpts(fieldPaths.value.filter((f) => f.source === 'dynamic')) },
  ]
  return groups.filter((g) => g.children.length > 0)
})

const modalTitle = computed(() => {
  const edit = !!editMetricId.value
  if (modalKind.value === 'atomic') return edit ? t('metrics.dialog.editAtomic') : t('metrics.dialog.createAtomic')
  return edit ? t('metrics.dialog.editDerived') : t('metrics.dialog.createDerived')
})

function onCalcFuncChange(val: string) {
  form.value.calcFunc = val
  const f = derivedFuncs.value.find((x) => x.name === val)
  const schema = f?.paramSchema || []
  const next: Record<string, any> = {}
  for (const p of schema) {
    if (p.default !== undefined) next[p.key] = p.default
  }
  form.value.params = next
}

function openCreate(kind: 'atomic' | 'derived') {
  modalKind.value = kind
  editMetricId.value = ''
  form.value = {
    name: '',
    sourcePath: '',
    basePath: '',
    calcFunc: null,
    params: {},
    dataType: 'number',
    unit: '',
    description: '',
    status: 'enabled',
  }
  showModal.value = true
}

async function submitMetric() {
  if (!form.value.name?.trim()) {
    message.warning(t('metrics.msg.requiredName'))
    return
  }
  saving.value = true
  try {
    let payload: any
    if (modalKind.value === 'atomic') {
      if (!form.value.sourcePath?.trim()) {
        message.warning(t('metrics.msg.requiredPath'))
        return
      }
      payload = {
        name: form.value.name,
        sourcePath: form.value.sourcePath,
        dataType: form.value.dataType,
        unit: form.value.unit,
        description: form.value.description,
        status: form.value.status || 'enabled',
      }
    } else {
      if (!form.value.calcFunc) {
        message.warning(t('metrics.msg.requiredFunc'))
        return
      }
      if (!form.value.basePath?.trim()) {
        message.warning(t('metrics.msg.requiredPath'))
        return
      }
      const params: Record<string, any> = {}
      const schema = selectedFuncHint.value?.paramSchema || []
      if (form.value.params && typeof form.value.params === 'object') {
        for (const p of schema) {
          const v = form.value.params[p.key]
          if (v === undefined || v === null || v === '') continue
          params[p.key] = p.type === 'number' ? Number(v) : v
        }
      }
      payload = {
        name: form.value.name,
        calcFunc: form.value.calcFunc,
        basePath: form.value.basePath,
        params,
        dataType: form.value.dataType,
        unit: form.value.unit,
        description: form.value.description,
        status: form.value.status || 'enabled',
      }
    }
    if (editMetricId.value) {
      if (modalKind.value === 'atomic') await updateAtomicMetric(editMetricId.value, payload)
      else await updateDerivedMetric(editMetricId.value, payload)
    } else if (modalKind.value === 'atomic') {
      await createAtomicMetric(payload)
    } else {
      await createDerivedMetric(payload)
    }
    message.success(editMetricId.value ? t('metrics.msg.updated') : t('metrics.msg.created'))
    showModal.value = false
    editMetricId.value = ''
    await load()
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.saveFailed'))
  } finally {
    saving.value = false
  }
}

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
    const [atomic, derived, templates, ops, funcs, defs] = await Promise.all([
      listAtomicMetrics(),
      listDerivedMetrics(),
      listMetricTemplates(),
      listOperators(),
      listDerivedFuncs(),
      listMetricDefinitions(),
    ])
    atomicList.value = atomic
    derivedList.value = derived
    templateList.value = templates
    operatorCatalog.value = ops
    derivedFuncs.value = funcs
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
  font-size: 20px;
  font-weight: 600;
}
.ws-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}
.ws-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-top: 4px;
}
.ws-tab-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
  gap: 8px;
}

/* 详情弹窗 */
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}
.detail-cell { display: flex; flex-direction: column; gap: 4px; }
.detail-cell-wide { grid-column: 1 / -1; }
.cell-label { color: var(--color-text-secondary, #6b7280); font-size: 12px; }
.cell-value { color: var(--color-text-primary, #111827); font-size: 14px; }
.ws-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--color-bg-subtle, #f9fafb);
}
.ws-ops { display: flex; flex-wrap: wrap; gap: 4px; }
.ws-op-tag {
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--color-bg-subtle, #f9fafb);
  border: 1px solid var(--color-border, #e5e7eb);
}
.ws-muted { color: var(--color-text-tertiary, #9ca3af); font-size: 13px; }
.ws-actions-cell { display: flex; gap: 2px; }

/* 模板弹窗分段 */
.tpl-section { width: 100%; }
.tpl-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 4px; }
.tpl-field { flex: 1 1 0; min-width: 140px; margin-bottom: 4px; }
.tpl-segments { display: flex; flex-direction: column; gap: 8px; }
.seg-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.seg-field { flex: 1 1 120px; }

/* 参数输入行 */
.ws-params { display: flex; flex-direction: column; gap: 10px; width: 100%; }
.ws-param-row { display: flex; align-items: center; gap: 12px; }
.ws-param-label { flex: 0 0 140px; font-size: 13px; color: var(--color-text-secondary, #6b7280); }
.ws-param-control { flex: 1 1 auto; }
.ws-req { color: var(--error-color, #d03050); font-style: normal; margin-left: 2px; }
.ws-tip { font-size: 12px; color: var(--color-text-secondary, #6b7280); }
</style>
