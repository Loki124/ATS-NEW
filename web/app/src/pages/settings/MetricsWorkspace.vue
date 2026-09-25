<template>
  <div class="page-container metrics-ws">
    <!-- ========== Header ========== -->
    <div class="page-header">
      <div>
        <h1 class="ws-title">{{ t('metrics.workspace.title') }}</h1>
        <p class="ws-subtitle">{{ t('metrics.workspace.subtitle') }}</p>
      </div>
    </div>

    <!-- ========== 数据流 ribbon（四个模块如何协同） ========== -->
    <div class="flow-ribbon">
      <div class="flow-head">
        <span class="flow-label">{{ t('metrics.workspace.flowTitle') }}</span>
        <n-tooltip trigger="hover">
          <template #trigger>
            <n-icon class="flow-info" :component="InformationCircleOutline" />
          </template>
          {{ t('metrics.workspace.flowNote') }}
        </n-tooltip>
      </div>
      <div class="flow-chain">
        <div class="flow-node">
          <div class="flow-node-title">{{ t('metrics.workspace.flowDynamic') }}</div>
          <div class="flow-node-sub">DynamicField + 候选人录入值</div>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-node">
          <div class="flow-node-title">{{ t('metrics.workspace.flowMetrics') }}</div>
          <div class="flow-node-sub">原子指标 source_path / 派生指标 base_path</div>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-node">
          <div class="flow-node-title">{{ t('metrics.workspace.flowTemplate') }}</div>
          <div class="flow-node-sub">绑定指标 + 运算符</div>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-node">
          <div class="flow-node-title">{{ t('metrics.workspace.flowRule') }}</div>
          <div class="flow-node-sub">引用模板 + 场景</div>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-node flow-node-exec">
          <div class="flow-node-title">{{ t('metrics.workspace.flowExec') }}</div>
          <div class="flow-node-sub">业务触发点自动执行</div>
        </div>
      </div>
      <p class="flow-legacy">{{ t('metrics.workspace.legendRuleEngine') }}</p>
    </div>

    <!-- ========== 顶层 Tab：指标库 / 规则编排 / 规则管理 ========== -->
    <div class="ws-body">
      <n-tabs v-model:value="activeTab" type="line" animated>
        <!-- ---------- Tab 1：指标库 ---------- -->
        <n-tab-pane name="metrics" :tab="t('metrics.library.title')">
          <div class="ws-tab-bar">
            <n-space>
              <n-button type="primary" @click="openCreate('atomic')">
                {{ t('metrics.btn.create') }}{{ t('metrics.tab.atomic') }}
              </n-button>
              <n-button type="primary" @click="openCreate('derived')">
                {{ t('metrics.btn.create') }}{{ t('metrics.tab.derived') }}
              </n-button>
              <n-button type="primary" @click="openCreate('template')">
                {{ t('metrics.btn.create') }}{{ t('metrics.tab.template') }}
              </n-button>
            </n-space>
          </div>
          <n-tabs v-model:value="innerMetricTab" type="line" animated>
            <n-tab-pane name="atomic" :tab="t('metrics.tab.atomic')">
              <n-data-table
                :columns="atomicColumns"
                :data="atomicList"
                :loading="loading"
                :bordered="false"
                size="small"
              />
            </n-tab-pane>
            <n-tab-pane name="derived" :tab="t('metrics.tab.derived')">
              <n-data-table
                :columns="derivedColumns"
                :data="derivedList"
                :loading="loading"
                :bordered="false"
                size="small"
              />
            </n-tab-pane>
            <n-tab-pane name="template" :tab="t('metrics.tab.template')">
              <n-data-table
                :columns="templateColumns"
                :data="templateList"
                :loading="loading"
                :bordered="false"
                size="small"
              />
            </n-tab-pane>
          </n-tabs>
        </n-tab-pane>

        <!-- ---------- Tab 2：规则编排与执行 ---------- -->
        <n-tab-pane name="author" :tab="t('metrics.rule.title')">
          <div class="ws-author">
            <!-- 规则信息（持久化） -->
            <n-card :title="t('metrics.rule.ruleName')" size="small" class="ws-card">
              <div class="ws-rule-meta">
                <n-input
                  v-model:value="ruleName"
                  :placeholder="t('metrics.rule.ruleName')"
                  class="ws-rule-name"
                />
                <n-select
                  v-model:value="ruleScene"
                  :options="sceneOptions"
                  class="ws-rule-scene"
                />
                <n-button type="primary" :loading="saving" :disabled="!canExecute" @click="saveRule">
                  {{ ruleId ? t('metrics.rule.updateRule') : t('metrics.rule.saveRule') }}
                </n-button>
              </div>
              <div class="ws-rule-action">
                <span class="ws-action-label">{{ t('metrics.rule.actionType') }}</span>
                <n-radio-group v-model:value="actionType" size="small">
                  <n-radio-button
                    v-for="opt in actionTypeOptions"
                    :key="opt.value"
                    :value="opt.value"
                  >{{ t(opt.labelKey) }}</n-radio-button>
                </n-radio-group>
              </div>
            </n-card>

            <!-- 条件编辑区 -->
            <n-card :title="t('metrics.rule.conditionArea')" size="small" class="ws-card">
              <template #header-extra>
                <n-button size="small" @click="addCondition">{{ t('metrics.btn.addCondition') }}</n-button>
              </template>
              <div v-if="!templateList.length" class="ws-empty">
                {{ t('metrics.rule.noTemplateHint') }}
              </div>
              <div v-for="(cond, idx) in conditions" :key="idx" class="ws-cond-row">
                <span class="ws-index">{{ idx + 1 }}</span>
                <n-select
                  v-model:value="cond.templateId"
                  :options="templateOptions"
                  class="ws-template"
                  :placeholder="t('metrics.rule.template')"
                  @update:value="onTemplateChange(cond)"
                />
                <n-select
                  v-model:value="cond.operator"
                  :options="operatorOptionsFor(cond)"
                  class="ws-operator"
                  :placeholder="t('metrics.rule.operator')"
                />
                <n-input
                  v-model:value="cond.value"
                  class="ws-value"
                  :placeholder="t('metrics.rule.value')"
                />
                <span class="ws-unit">{{ unitOf(cond) || '-' }}</span>
                <n-button size="small" quaternary type="error" @click="removeCondition(idx)">
                  {{ t('metrics.btn.delete') }}
                </n-button>
              </div>
              <div class="ws-actions">
                <n-button type="primary" :loading="executing" :disabled="!canExecute" @click="execute">
                  {{ executing ? t('metrics.btn.executing') : t('metrics.btn.execute') }}
                </n-button>
              </div>
            </n-card>

            <!-- 执行结果 -->
            <n-card :title="t('metrics.rule.result')" size="small" class="ws-card">
              <div v-if="!result" class="ws-empty">{{ t('metrics.rule.noResult') }}</div>
              <template v-else>
                <n-alert
                  :type="result.pass ? 'success' : 'error'"
                  :title="result.pass ? t('metrics.rule.pass') : t('metrics.rule.fail')"
                  class="ws-alert"
                >
                  {{ result.summary }}
                </n-alert>
                <div v-for="step in result.steps" :key="step.index" class="ws-step">
                  <n-tag :type="step.pass ? 'success' : 'error'" size="small">
                    {{ step.pass ? t('metrics.rule.stepPass') : t('metrics.rule.stepFail') }}
                  </n-tag>
                  <span class="ws-step-index">{{ t('metrics.rule.step') }} {{ step.index }}</span>
                  <span class="ws-step-detail">{{ step.detail || step.error }}</span>
                </div>
              </template>
            </n-card>

            <!-- 测试数据（可切换为真实候选人快照） -->
            <n-card :title="t('metrics.rule.sampleData')" size="small" class="ws-card">
              <template #header-extra>
                <n-radio-group v-model:value="dataMode" size="small">
                  <n-radio-button value="sample">{{ t('metrics.rule.sample') }}</n-radio-button>
                  <n-radio-button value="real">{{ t('metrics.rule.real') }}</n-radio-button>
                </n-radio-group>
              </template>
              <n-space v-if="dataMode === 'real'" class="ws-snapshot-bar">
                <n-input
                  v-model:value="candidateId"
                  :placeholder="t('metrics.rule.candidateId')"
                  style="width: 240px"
                />
                <n-button size="small" :loading="loadingSnapshot" @click="loadSnapshot">
                  {{ loadingSnapshot ? t('metrics.rule.loading') : t('metrics.rule.loadSnapshot') }}
                </n-button>
              </n-space>
              <pre class="ws-json">{{ JSON.stringify(currentData, null, 2) }}</pre>
            </n-card>
          </div>
        </n-tab-pane>

        <!-- ---------- Tab 3：规则管理 ---------- -->
        <n-tab-pane name="manage" :tab="t('metrics.rules.title')">
          <div class="ws-tab-bar">
            <n-button type="primary" @click="newRule">
              {{ t('metrics.rule.newRule') }}
            </n-button>
          </div>
          <n-data-table
            :columns="ruleColumns"
            :data="rules"
            :loading="loadingRules"
            :bordered="false"
            size="small"
          />
        </n-tab-pane>
      </n-tabs>
    </div>

    <!-- ========== 指标新建弹窗（原子 / 派生 / 模板 共用） ========== -->
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

        <!-- 原子指标：字段路径（下拉选择，避免手填出错） -->
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

        <!-- 派生指标：计算函数 + 数据来源 + 参数 -->
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
          <!-- 类型化参数输入：依据所选函数的 paramSchema 渲染，取代自由 JSON 文本 -->
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

        <!-- 模板：引用指标 + 运算符 -->
        <template v-if="modalKind === 'template'">
          <n-form-item :label="t('metrics.form.atomicMetric')">
            <n-select
              v-model:value="form.atomicMetric"
              :options="atomicOptions"
              clearable
              :placeholder="t('metrics.form.atomicMetric')"
            />
          </n-form-item>
          <n-form-item :label="t('metrics.form.derivedMetric')">
            <n-select
              v-model:value="form.derivedMetric"
              :options="derivedOptions"
              clearable
              :placeholder="t('metrics.form.derivedMetric')"
            />
          </n-form-item>
          <n-form-item :label="t('metrics.form.operators')" required>
            <n-select
              v-model:value="form.operators"
              multiple
              :options="operatorCatalog"
              :placeholder="t('metrics.form.operators')"
            />
          </n-form-item>
        </template>

        <!-- 派生指标：选中函数后展示预期输入与参数提示（函数↔数据来源 的隐式契约） -->
        <n-alert
          v-if="modalKind === 'derived' && selectedFuncHint"
          type="info"
          :title="selectedFuncHint.label"
          class="ws-func-hint"
        >
          <div v-if="selectedFuncHint.description">{{ selectedFuncHint.description }}</div>
          <div v-if="selectedFuncHint.inputKind" class="ws-func-meta">
            {{ t('metrics.form.expectedInput') }}：{{ inputKindLabel(selectedFuncHint.inputKind) }}
          </div>
          <div v-if="selectedFuncHint.outputType" class="ws-func-meta">
            {{ t('metrics.form.outputType') }}：{{ outputTypeLabel(selectedFuncHint.outputType) }}<template v-if="selectedFuncHint.unit">（{{ selectedFuncHint.unit }}）</template>
          </div>
          <div v-if="selectedFuncHint.paramsHint" class="ws-func-params">
            {{ t('metrics.form.paramsTipLabel') }}：{{ selectedFuncHint.paramsHint }}
          </div>
        </n-alert>

        <n-form-item v-if="modalKind !== 'template'" :label="t('metrics.form.dataType')">
          <n-select v-model:value="form.dataType" :options="dataTypeOptions" />
        </n-form-item>
        <n-form-item v-if="modalKind !== 'template'" :label="t('metrics.form.unit')">
          <n-input v-model:value="form.unit" placeholder="岁 / 月 / 元" />
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
          <n-button type="primary" :loading="saving" @click="submit">{{ t('metrics.btn.save') }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- ========== 规则执行结果弹窗（管理页「执行」用） ========== -->
    <n-modal
      v-model:show="resultVisible"
      preset="card"
      :title="t('metrics.rule.result')"
      style="width: 640px"
    >
      <n-alert
        v-if="runResult"
        :type="runResult.pass ? 'success' : 'error'"
        :title="runResult.pass ? t('metrics.rule.pass') : t('metrics.rule.fail')"
      >
        {{ runResult.summary }}
      </n-alert>
      <div v-for="step in runResult?.steps || []" :key="step.index" class="ws-step">
        <n-tag :type="step.pass ? 'success' : 'error'" size="small">
          {{ step.pass ? t('metrics.rule.stepPass') : t('metrics.rule.stepFail') }}
        </n-tag>
        <span class="ws-step-detail">{{ step.detail || step.error }}</span>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
/**
 * MetricsWorkspace —— 指标与规则统一工作区（整合原三页）。
 *
 * 设计目标（用户诉求）：
 *   - 把「指标库 / 规则配置与执行 / 规则管理」三页合并为一个连贯视图，
 *     避免多个页面表达同一业务域造成理解成本。
 *   - 顶部 ribbon 显式表达四个模块的数据流与依赖：
 *       动态字段 → 原子/派生指标 → 指标模板 → 规则 → 执行/筛选
 *   - 「统一规则引擎」(RuleEngine.vue) 是旧版 rule_engine 的聚合只读视图，
 *     与本指标层相互独立，入口仍保留在左侧菜单，ribbon 内已注明。
 *
 * 共享状态：一次 load() 拉取原子/派生/模板/运算符/派生函数/字段路径/规则，
 * 三个 tab 复用同一份数据，规则编辑 ↔ 管理互相跳转，无需离开本页。
 */
import { computed, h, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import {
  NButton,
  NPopconfirm,
  NSwitch,
  NTooltip,
  NIcon,
  NAlert,
  useMessage,
} from 'naive-ui'
import { InformationCircleOutline } from '@vicons/ionicons5'
import {
  createAtomicMetric,
  createDerivedMetric,
  createMetricTemplate,
  createMetricRule,
  deleteAtomicMetric,
  deleteDerivedMetric,
  deleteMetricRule,
  deleteMetricTemplate,
  executeRule,
  getCandidateSnapshot,
  getMetricRule,
  getSampleData,
  listAtomicMetrics,
  listDerivedFuncs,
  listDerivedMetrics,
  listMetricRules,
  listMetricTemplates,
  listOperators,
  listCandidateFields,
  runMetricRule,
  toggleMetricRule,
  updateMetricRule,
  updateAtomicMetric,
  updateDerivedMetric,
  updateMetricTemplate,
  type AtomicMetric,
  type CandidateFieldPath,
  type DerivedMetric,
  type ExecuteResult,
  type MetricRule,
  type MetricRuleScene,
  type MetricTemplate,
  type OptionItem,
  type DerivedFuncItem,
  ACTION_TYPE_OPTIONS,
} from '@/api/metrics'

const { t } = useI18n()
const message = useMessage()
const route = useRoute()

const activeTab = ref<'metrics' | 'author' | 'manage'>('metrics')
const innerMetricTab = ref('atomic')

// ===== 共享数据（一次加载） =====
const atomicList = ref<AtomicMetric[]>([])
const derivedList = ref<DerivedMetric[]>([])
const templateList = ref<MetricTemplate[]>([])
const operatorCatalog = ref<OptionItem[]>([])
const derivedFuncs = ref<DerivedFuncItem[]>([])
const fieldPaths = ref<CandidateFieldPath[]>([])
const rules = ref<MetricRule[]>([])
const loading = ref(false)
const loadingRules = ref(false)

// ===== 指标编辑弹窗（新建 / 编辑 共用） =====
const showModal = ref(false)
const modalKind = ref<'atomic' | 'derived' | 'template'>('atomic')
const editId = ref('') // 空 = 新建；非空 = 编辑（查看与修改同一弹窗）
const saving = ref(false)
const form = ref<any>({})

const statusOptions = computed(() => [
  { label: t('metrics.status.enabled'), value: 'enabled' },
  { label: t('metrics.status.disabled'), value: 'disabled' },
])

// 派生指标：选中计算函数后展示其预期输入与参数提示（明确 函数↔数据来源 的隐式契约）
const selectedFuncHint = computed(() => {
  if (modalKind.value !== 'derived') return null
  return derivedFuncs.value.find((f) => f.name === form.value.calcFunc) || null
})

// input_kind / output_type 枚举 → 中文可读标签（与后端声明的语义对齐）
const INPUT_KIND_LABELS: Record<string, string> = {
  list_periods: '经历/学历对象列表（每段含起止或学历字段）',
  list_edu: '学历对象列表（每段含学历字段）',
  date: '单个日期（如生日）',
}
const OUTPUT_TYPE_LABELS: Record<string, string> = {
  number: '数值', string: '字符串', boolean: '布尔', date: '日期',
}
function inputKindLabel(kind?: string): string {
  return (kind && INPUT_KIND_LABELS[kind]) || kind || ''
}
function outputTypeLabel(type?: string): string {
  return (type && OUTPUT_TYPE_LABELS[type]) || type || ''
}

// 切换计算函数时，按新函数的 paramSchema 重置参数（清除上一个函数的残留参数）
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

const modalTitle = computed(() => {
  const edit = !!editId.value
  if (modalKind.value === 'atomic') return edit ? t('metrics.dialog.editAtomic') : t('metrics.dialog.createAtomic')
  if (modalKind.value === 'derived') return edit ? t('metrics.dialog.editDerived') : t('metrics.dialog.createDerived')
  return edit ? t('metrics.dialog.editTemplate') : t('metrics.dialog.createTemplate')
})

const dataTypeOptions = [
  { label: '数值', value: 'number' },
  { label: '字符串', value: 'string' },
  { label: '布尔', value: 'boolean' },
  { label: '日期', value: 'date' },
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

// 字段路径下拉选项：按来源分组（主表字段 / 动态字段），可搜索，避免手填出错
const fieldPathOptions = computed(() => {
  const toOpts = (src: CandidateFieldPath[]) =>
    src.map((f) => ({ label: `${f.label}（${f.path}）`, value: f.path }))
  const groups = [
    {
      type: 'group' as const,
      label: t('metrics.fieldGroup.model'),
      key: 'model',
      children: toOpts(fieldPaths.value.filter((f) => f.source === 'model')),
    },
    {
      type: 'group' as const,
      label: t('metrics.fieldGroup.dynamic'),
      key: 'dynamic',
      children: toOpts(fieldPaths.value.filter((f) => f.source === 'dynamic')),
    },
  ]
  return groups.filter((g) => g.children.length > 0)
})

// ===== 规则编排与执行 =====
const ruleId = ref('')
const ruleName = ref('')
const ruleScene = ref<MetricRuleScene>('MANUAL')
// T4：动作类型，默认 DEDUCT（优先考虑，安全默认不阻断）
const actionType = ref<'VETO' | 'DEDUCT' | 'BONUS'>('DEDUCT')
const conditions = ref<any[]>([{ templateId: null, operator: null, value: '' }])
const result = ref<ExecuteResult | null>(null)
const executing = ref(false)
const dataMode = ref<'sample' | 'real'>('sample')
const candidateId = ref('')
const realData = ref<Record<string, any>>({})
const sampleData = ref<Record<string, any>>({})
const loadingSnapshot = ref(false)

const currentData = computed(() =>
  dataMode.value === 'real' ? realData.value : sampleData.value,
)

const templateOptions = computed(() =>
  templateList.value.map((tp) => ({
    label: `${tp.name}（${tp.metricName || tp.metricPath || ''}）`,
    value: tp.id,
  })),
)

const sceneOptions = computed(() => [
  { label: t('metrics.scene.TALENT_POOL'), value: 'TALENT_POOL' },
  { label: t('metrics.scene.FILTER'), value: 'FILTER' },
  { label: t('metrics.scene.SCORING'), value: 'SCORING' },
  { label: t('metrics.scene.MANUAL'), value: 'MANUAL' },
])

const actionTypeOptions = ACTION_TYPE_OPTIONS

const canExecute = computed(() => {
  if (!conditions.value.some((c) => c.templateId && c.operator)) return false
  if (dataMode.value === 'real' && !realData.value?.candidate) return false
  return true
})

function operatorOptionsFor(cond: any) {
  const tp = templateList.value.find((x) => x.id === cond.templateId)
  const allowed = tp?.operators || []
  return operatorCatalog.value
    .filter((op) => allowed.includes(op.value))
    .map((op) => ({ label: op.label, value: op.value }))
}

function onTemplateChange(cond: any) {
  const options = operatorOptionsFor(cond)
  if (!options.some((o) => o.value === cond.operator)) {
    cond.operator = options.length ? options[0].value : null
  }
}

function unitOf(cond: any) {
  return templateList.value.find((x) => x.id === cond.templateId)?.unit || ''
}

function addCondition() {
  conditions.value.push({ templateId: null, operator: null, value: '' })
}

function removeCondition(index: number) {
  conditions.value.splice(index, 1)
  if (!conditions.value.length) {
    conditions.value.push({ templateId: null, operator: null, value: '' })
  }
}

async function loadSnapshot() {
  if (!candidateId.value.trim()) {
    message.warning(t('metrics.rule.candidateId'))
    return
  }
  loadingSnapshot.value = true
  try {
    const snap = await getCandidateSnapshot(candidateId.value.trim())
    if (!snap?.candidate) {
      message.warning(t('metrics.rule.dataEmpty'))
      return
    }
    realData.value = snap
    message.success(t('metrics.rule.snapshotOk'))
  } catch {
    message.error(t('metrics.rule.snapshotFail'))
  } finally {
    loadingSnapshot.value = false
  }
}

async function execute() {
  executing.value = true
  result.value = null
  try {
    const payload = {
      conditions: conditions.value
        .filter((c) => c.templateId && c.operator)
        .map((c) => ({ templateId: c.templateId, operator: c.operator, value: c.value })),
      logic: 'AND',
      data: currentData.value,
    }
    result.value = await executeRule(payload as any)
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.executeFailed'))
  } finally {
    executing.value = false
  }
}

// ===== 规则持久化 =====
async function loadRuleIntoAuthor(id: string) {
  try {
    const rule = await getMetricRule(id)
    ruleId.value = rule.id
    ruleName.value = rule.name
    ruleScene.value = rule.scene
    actionType.value = (rule.actionType || 'DEDUCT') as 'VETO' | 'DEDUCT' | 'BONUS'
    conditions.value = (rule.conditions || []).map((c: any) => ({
      templateId: c.templateId,
      operator: c.operator,
      value: c.value ?? '',
    }))
    if (!conditions.value.length) {
      conditions.value = [{ templateId: null, operator: null, value: '' }]
    }
    result.value = null
    activeTab.value = 'author'
  } catch {
    message.error(t('metrics.msg.loadFailed'))
  }
}

async function saveRule() {
  if (!ruleName.value.trim()) {
    message.warning(t('metrics.rule.ruleName'))
    return
  }
  saving.value = true
  try {
    const payload = {
      name: ruleName.value.trim(),
      scene: ruleScene.value,
      actionType: actionType.value,
      logic: 'AND' as const,
      // T5：数值型 value / IN 元素 / BETWEEN 的 min,max 转字符串，避免 JSON number 精度丢失
      conditions: persistConditions(conditions.value),
    }
    if (ruleId.value) {
      await updateMetricRule(ruleId.value, payload)
      message.success(t('metrics.rule.updated'))
    } else {
      const created = await createMetricRule(payload)
      ruleId.value = created.id
      message.success(t('metrics.rule.saved'))
    }
    await loadRules()
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.saveFailed'))
  } finally {
    saving.value = false
  }
}

/** 构造持久化条件：过滤无效项 + 数值转字符串（T5 精度防护）。 */
function persistConditions(list: any[]): any[] {
  return list
    .filter((c) => c.templateId && c.operator)
    .map((c) => {
      const cond: any = {
        templateId: c.templateId,
        operator: c.operator,
        value: c.value,
      }
      if (c.operator === 'IN' || c.operator === 'NOT_IN') {
        if (Array.isArray(c.value)) {
          cond.value = c.value.map((v: any) =>
            typeof v === 'number' ? String(v) : v,
          )
        }
      } else if (typeof c.value === 'number') {
        cond.value = String(c.value)
      }
      if (c.operator === 'BETWEEN' && c.meta) {
        const meta: any = { ...(c.meta || {}) }
        for (const k of ['min', 'max']) {
          if (typeof meta[k] === 'number') meta[k] = String(meta[k])
        }
        cond.meta = meta
      }
      return cond
    })
}

function newRule() {
  ruleId.value = ''
  ruleName.value = ''
  ruleScene.value = 'MANUAL'
  actionType.value = 'DEDUCT'
  conditions.value = [{ templateId: null, operator: null, value: '' }]
  result.value = null
  dataMode.value = 'sample'
  activeTab.value = 'author'
}

// ===== 规则管理 =====
const resultVisible = ref(false)
const runResult = ref<ExecuteResult | null>(null)

async function loadRules() {
  loadingRules.value = true
  try {
    rules.value = await listMetricRules()
  } catch {
    message.error(t('metrics.msg.loadFailed'))
  } finally {
    loadingRules.value = false
  }
}

function editRule(row: MetricRule) {
  loadRuleIntoAuthor(row.id)
}

async function onToggle(row: MetricRule, value: boolean) {
  try {
    const res = await toggleMetricRule(row.id)
    row.enabled = res.enabled
  } catch {
    message.error(t('metrics.msg.saveFailed'))
    await loadRules()
  }
}

async function removeRule(row: MetricRule) {
  try {
    await deleteMetricRule(row.id)
    message.success(t('metrics.msg.deleted'))
    await loadRules()
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.deleteFailed'))
  }
}

async function runRule(row: MetricRule) {
  const cid = window.prompt(t('metrics.rule.candidateId'))
  if (!cid) return
  try {
    runResult.value = await runMetricRule(row.id, cid.trim())
    resultVisible.value = true
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.executeFailed'))
  }
}

function sceneLabel(scene: string) {
  return t(`metrics.scene.${scene}` as any)
}

const ruleColumns = computed(() => [
  { title: t('metrics.col.name'), key: 'name' },
  {
    title: t('metrics.rule.scene'),
    key: 'scene',
    render: (row: MetricRule) => sceneLabel(row.scene),
  },
  { title: t('metrics.col.templateCount'), key: 'conditionCount' },
  {
    title: t('metrics.col.status'),
    key: 'enabled',
    render: (row: MetricRule) =>
      h(NSwitch, {
        value: row.enabled,
        'onUpdate:value': (v: boolean) => onToggle(row, v),
      }),
  },
  {
    title: t('metrics.col.action'),
    key: 'action',
    render: (row: MetricRule) =>
      h('div', { class: 'ws-actions-cell' }, [
        h(
          NButton,
          { size: 'small', quaternary: true, onClick: () => editRule(row) },
          { default: () => t('metrics.rule.edit') },
        ),
        h(
          NButton,
          { size: 'small', quaternary: true, onClick: () => runRule(row) },
          { default: () => t('metrics.rule.run') },
        ),
        h(
          NPopconfirm,
          { onPositiveClick: () => removeRule(row) },
          {
            trigger: () =>
              h(
                NButton,
                { size: 'small', quaternary: true, type: 'error' },
                { default: () => t('metrics.btn.delete') },
              ),
            default: () => t('metrics.msg.confirmDelete', { name: row.name }),
          },
        ),
      ]),
  },
])

// ===== 指标表格列 =====
function deleteButton(row: any, kind: 'atomic' | 'derived' | 'template') {
  return h(
    NPopconfirm,
    {
      onPositiveClick: async () => {
        try {
          if (kind === 'atomic') await deleteAtomicMetric(row.id)
          else if (kind === 'derived') await deleteDerivedMetric(row.id)
          else await deleteMetricTemplate(row.id)
          message.success(t('metrics.msg.deleted'))
          await load()
        } catch (error: any) {
          const detail = error?.response?.data?.error
          message.error(detail ? String(detail) : t('metrics.msg.deleteFailed'))
        }
      },
    },
    {
      trigger: () =>
        h(
          NButton,
          { size: 'small', quaternary: true, type: 'error' },
          { default: () => t('metrics.btn.delete') },
        ),
      default: () => t('metrics.msg.confirmDelete', { name: row.name }),
    },
  )
}

function editButton(row: any, kind: 'atomic' | 'derived' | 'template') {
  return h(
    NButton,
    { size: 'small', quaternary: true, onClick: () => openEdit(kind, row) },
    { default: () => t('metrics.btn.edit') },
  )
}

const atomicColumns = computed(() => [
  { title: t('metrics.col.name'), key: 'name' },
  {
    title: t('metrics.col.sourcePath'),
    key: 'sourcePath',
    render: (row: any) => h('code', { class: 'ws-code' }, { default: () => row.sourcePath }),
  },
  { title: t('metrics.col.dataType'), key: 'dataType' },
  { title: t('metrics.col.unit'), key: 'unit' },
  { title: t('metrics.col.templateCount'), key: 'templateCount' },
  {
    title: t('metrics.col.action'),
    key: 'action',
    render: (row: any) =>
      h('div', { class: 'ws-actions-cell' }, [editButton(row, 'atomic'), deleteButton(row, 'atomic')]),
  },
])

const derivedColumns = computed(() => [
  { title: t('metrics.col.name'), key: 'name' },
  { title: t('metrics.col.calcFunc'), key: 'calcFunc' },
  {
    title: t('metrics.col.basePath'),
    key: 'basePath',
    render: (row: any) => h('code', { class: 'ws-code' }, { default: () => row.basePath }),
  },
  {
    title: t('metrics.col.params'),
    key: 'params',
    render: (row: any) =>
      row.params && Object.keys(row.params).length ? JSON.stringify(row.params) : '-',
  },
  { title: t('metrics.col.unit'), key: 'unit' },
  { title: t('metrics.col.templateCount'), key: 'templateCount' },
  {
    title: t('metrics.col.action'),
    key: 'action',
    render: (row: any) =>
      h('div', { class: 'ws-actions-cell' }, [editButton(row, 'derived'), deleteButton(row, 'derived')]),
  },
])

const templateColumns = computed(() => [
  { title: t('metrics.col.name'), key: 'name' },
  { title: t('metrics.col.metric'), key: 'metricName' },
  {
    title: t('metrics.col.metricPath'),
    key: 'metricPath',
    render: (row: any) => h('code', { class: 'ws-code' }, { default: () => row.metricPath }),
  },
  {
    title: t('metrics.col.operators'),
    key: 'operators',
    render: (row: any) =>
      h(
        'div',
        { class: 'ws-ops' },
        {
          default: () =>
            (row.operators || []).map((op: string) =>
              h('span', { class: 'ws-op-tag' }, { default: () => operatorLabel(op) }),
            ),
        },
      ),
  },
  {
    title: t('metrics.col.action'),
    key: 'action',
    render: (row: any) =>
      h('div', { class: 'ws-actions-cell' }, [editButton(row, 'template'), deleteButton(row, 'template')]),
  },
])

function operatorLabel(value: string) {
  return operatorCatalog.value.find((o) => o.value === value)?.label ?? value
}

// ===== 指标新建 / 编辑（同一弹窗：查看与修改） =====
function openCreate(kind: 'atomic' | 'derived' | 'template') {
  modalKind.value = kind
  editId.value = ''
  form.value = {
    name: '',
    sourcePath: '',
    basePath: '',
    calcFunc: null,
    params: {},
    atomicMetric: null,
    derivedMetric: null,
    operators: [],
    dataType: 'number',
    unit: '',
    description: '',
    status: 'enabled',
  }
  showModal.value = true
}

function openEdit(kind: 'atomic' | 'derived' | 'template', row: any) {
  modalKind.value = kind
  editId.value = row.id
  if (kind === 'atomic') {
    form.value = {
      name: row.name,
      sourcePath: row.sourcePath,
      dataType: row.dataType,
      unit: row.unit || '',
      description: row.description || '',
      status: row.status || 'enabled',
    }
  } else if (kind === 'derived') {
    form.value = {
      name: row.name,
      calcFunc: row.calcFunc,
      basePath: row.basePath,
      params: (row.params && typeof row.params === 'object') ? { ...row.params } : {},
      dataType: row.dataType,
      unit: row.unit || '',
      description: row.description || '',
      status: row.status || 'enabled',
    }
  } else {
    form.value = {
      name: row.name,
      atomicMetric: row.atomicMetric ?? null,
      derivedMetric: row.derivedMetric ?? null,
      operators: row.operators || [],
      description: row.description || '',
      status: row.status || 'enabled',
    }
  }
  showModal.value = true
}

async function submit() {
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
    } else if (modalKind.value === 'derived') {
      if (!form.value.calcFunc) {
        message.warning(t('metrics.msg.requiredFunc'))
        return
      }
      if (!form.value.basePath?.trim()) {
        message.warning(t('metrics.msg.requiredPath'))
        return
      }
      // 由 paramSchema 构建参数对象：仅取 schema 内声明的键，数字类型做强制转换，空值丢弃
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
    } else {
      const hasAtomic = !!form.value.atomicMetric
      const hasDerived = !!form.value.derivedMetric
      if (hasAtomic === hasDerived) {
        message.warning(t('metrics.msg.selectOneMetric'))
        return
      }
      if (!form.value.operators?.length) {
        message.warning(t('metrics.msg.requiredOperators'))
        return
      }
      payload = {
        name: form.value.name,
        atomicMetric: form.value.atomicMetric,
        derivedMetric: form.value.derivedMetric,
        operators: form.value.operators,
        description: form.value.description,
        status: form.value.status || 'enabled',
      }
    }

    if (editId.value) {
      if (modalKind.value === 'atomic') await updateAtomicMetric(editId.value, payload)
      else if (modalKind.value === 'derived') await updateDerivedMetric(editId.value, payload)
      else await updateMetricTemplate(editId.value, payload)
    } else if (modalKind.value === 'atomic') {
      await createAtomicMetric(payload)
    } else if (modalKind.value === 'derived') {
      await createDerivedMetric(payload)
    } else {
      await createMetricTemplate(payload)
    }

    message.success(editId.value ? t('metrics.msg.updated') : t('metrics.msg.created'))
    showModal.value = false
    editId.value = ''
    await load()
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.saveFailed'))
  } finally {
    saving.value = false
  }
}

// ===== 主加载 =====
async function load() {
  loading.value = true
  try {
    const [atomic, derived, templates, ops, funcs] = await Promise.all([
      listAtomicMetrics(),
      listDerivedMetrics(),
      listMetricTemplates(),
      listOperators(),
      listDerivedFuncs(),
    ])
    atomicList.value = atomic
    derivedList.value = derived
    templateList.value = templates
    operatorCatalog.value = ops
    derivedFuncs.value = funcs
    try {
      fieldPaths.value = await listCandidateFields()
    } catch {
      fieldPaths.value = []
    }
    const [sample] = await Promise.all([getSampleData()])
    sampleData.value = sample
    await loadRules()
  } catch {
    message.error(t('metrics.msg.loadFailed'))
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await load()
  // 支持从「规则管理」之外的入口带 ?ruleId= 直达编排页
  const id = (route.query.ruleId as string) || ''
  if (id) {
    await loadRuleIntoAuthor(id)
  }
})
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

/* 数据流 ribbon */
.flow-ribbon {
  flex: 0 0 auto;
  margin-bottom: 12px;
  padding: 12px 14px;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 8px;
  background: var(--color-bg-subtle, #f9fafb);
}
.flow-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.flow-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary, #6b7280);
}
.flow-info {
  cursor: help;
  color: var(--color-text-secondary, #6b7280);
}
.flow-chain {
  display: flex;
  align-items: stretch;
  gap: 6px;
  flex-wrap: wrap;
}
.flow-node {
  flex: 1 1 0;
  min-width: 120px;
  padding: 8px 10px;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 6px;
  background: var(--surface, #fff);
}
.flow-node-exec {
  border-color: var(--brand, #3b6cf6);
  background: var(--brand-soft, #eef3ff);
}
.flow-node-title {
  font-size: 13px;
  font-weight: 600;
}
.flow-node-sub {
  margin-top: 2px;
  font-size: 11px;
  color: var(--color-text-secondary, #6b7280);
}
.flow-arrow {
  align-self: center;
  font-size: 18px;
  color: var(--color-text-secondary, #9ca3af);
}
.flow-legacy {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--color-text-secondary, #6b7280);
}

/* 顶层 body 承担滚动（设置页滚动模型 B） */
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
}

/* 规则编排 */
.ws-author {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ws-card {
  flex: 0 0 auto;
}
.ws-rule-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.ws-rule-name {
  flex: 1 1 240px;
  min-width: 180px;
}
.ws-rule-scene {
  flex: 0 0 160px;
}
.ws-cond-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.ws-index {
  width: 24px;
  text-align: center;
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}
.ws-template {
  flex: 1 1 220px;
  min-width: 180px;
}
.ws-operator {
  flex: 0 0 140px;
}
.ws-value {
  flex: 0 0 140px;
}
.ws-unit {
  flex: 0 0 48px;
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}
.ws-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
.ws-empty {
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
  padding: 8px 0;
}
.ws-alert {
  margin-bottom: 12px;
}
.ws-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-top: 1px solid var(--color-border, #e5e7eb);
  flex-wrap: wrap;
}
.ws-step-index {
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}
.ws-step-detail {
  font-size: 13px;
}
.ws-snapshot-bar {
  margin-bottom: 8px;
}
.ws-json {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  max-height: 240px;
  overflow: auto;
  background: var(--color-bg-subtle, #f9fafb);
  padding: 10px;
  border-radius: 6px;
}

/* 通用原子 */
.ws-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--color-bg-subtle, #f9fafb);
}
.ws-tip {
  font-size: 12px;
  color: var(--color-text-secondary, #6b7280);
}
.ws-ops {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.ws-op-tag {
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--color-bg-subtle, #f9fafb);
  border: 1px solid var(--color-border, #e5e7eb);
}
.ws-actions-cell {
  display: flex;
  gap: 2px;
}
.ws-func-hint {
  margin-bottom: 12px;
}
.ws-func-params {
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-text-secondary, #6b7280);
}
.ws-func-meta {
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-text-secondary, #6b7280);
}
.ws-params {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}
.ws-param-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.ws-param-label {
  flex: 0 0 140px;
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}
.ws-param-control {
  flex: 1 1 auto;
}
.ws-req {
  color: var(--error-color, #d03050);
  font-style: normal;
  margin-left: 2px;
}
</style>
