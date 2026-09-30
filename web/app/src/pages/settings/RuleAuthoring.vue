<template>
  <div class="page-container rule-author">
    <!-- ========== Header ========== -->
    <div class="page-header">
      <div>
        <h1 class="ra-title">{{ t('metrics.ruleEngine.title') }}</h1>
        <p class="ra-subtitle">{{ t('metrics.ruleEngine.subtitle') }}</p>
      </div>
    </div>

    <div class="ra-body">
      <n-tabs v-model:value="activeTab" type="line" animated>
        <!-- ---------- 规则配置与执行 ---------- -->
        <n-tab-pane name="author" :tab="t('metrics.rule.title')">
          <div class="ra-author">
            <n-card :title="t('metrics.rule.ruleName')" size="small" class="ra-card">
              <div class="ra-rule-meta">
                <n-input v-model:value="ruleName" :placeholder="t('metrics.rule.ruleName')" class="ra-rule-name" />
                <n-select v-model:value="ruleScene" :options="sceneOptions" class="ra-rule-scene" />
                <n-button type="primary" :loading="saving" :disabled="!canExecute" @click="saveRule">
                  {{ ruleId ? t('metrics.rule.updateRule') : t('metrics.rule.saveRule') }}
                </n-button>
              </div>
              <div class="ra-rule-action">
                <span class="ra-action-label">{{ t('metrics.rule.actionType') }}</span>
                <n-radio-group v-model:value="actionType" size="small">
                  <n-radio-button v-for="opt in actionTypeOptions" :key="opt.value" :value="opt.value">
                    {{ t(opt.labelKey) }}
                  </n-radio-button>
                </n-radio-group>
              </div>
              <div class="ra-rule-binding">
                <div class="ra-bind-item">
                  <span class="ra-action-label">{{ t('metrics.rule.bindDemand') }}</span>
                  <n-select v-model:value="demandId" :options="demandOptions" clearable :placeholder="t('metrics.rule.bindDemand')" class="ra-bind-select" />
                </div>
                <div class="ra-bind-item">
                  <span class="ra-action-label">{{ t('metrics.rule.bindPosition') }}</span>
                  <n-select v-model:value="positionId" :options="positionOptions" clearable :placeholder="t('metrics.rule.bindPosition')" class="ra-bind-select" />
                </div>
              </div>
            </n-card>

            <n-card :title="t('metrics.rule.conditionArea')" size="small" class="ra-card">
              <template #header-extra>
                <n-button size="small" @click="addCondition">{{ t('metrics.btn.addCondition') }}</n-button>
              </template>
              <div v-if="!templateList.length" class="ra-empty">{{ t('metrics.rule.noTemplateHint') }}</div>
              <div v-for="(cond, idx) in conditions" :key="idx" class="ra-cond-row">
                <span class="ra-index">{{ idx + 1 }}</span>
                <n-select
                  v-model:value="cond.templateId"
                  :options="templateOptions"
                  class="ra-template"
                  :placeholder="t('metrics.rule.template')"
                  @update:value="onTemplateChange(cond)"
                />
                <n-select
                  v-model:value="cond.operator"
                  :options="operatorOptionsFor(cond)"
                  class="ra-operator"
                  :placeholder="t('metrics.rule.operator')"
                />
                <n-input v-model:value="cond.value" class="ra-value" :placeholder="t('metrics.rule.value')" />
                <span class="ra-unit">{{ unitOf(cond) || '-' }}</span>
                <n-button size="small" quaternary type="error" @click="removeCondition(idx)">{{ t('metrics.btn.delete') }}</n-button>
              </div>
              <div class="ra-actions">
                <n-button type="primary" :loading="executing" :disabled="!canExecute" @click="execute">
                  {{ executing ? t('metrics.btn.executing') : t('metrics.btn.execute') }}
                </n-button>
              </div>
            </n-card>

            <n-card :title="t('metrics.rule.result')" size="small" class="ra-card">
              <div v-if="!result" class="ra-empty">{{ t('metrics.rule.noResult') }}</div>
              <template v-else>
                <n-alert :type="result.pass ? 'success' : 'error'" :title="result.pass ? t('metrics.rule.pass') : t('metrics.rule.fail')" class="ra-alert">
                  {{ result.summary }}
                </n-alert>
                <div v-for="step in result.steps" :key="step.index" class="ra-step">
                  <n-tag :type="step.pass ? 'success' : 'error'" size="small">
                    {{ step.pass ? t('metrics.rule.stepPass') : t('metrics.rule.stepFail') }}
                  </n-tag>
                  <span class="ra-step-index">{{ t('metrics.rule.step') }} {{ step.index }}</span>
                  <span class="ra-step-detail">{{ step.detail || step.error }}</span>
                </div>
              </template>
            </n-card>

            <n-card :title="t('metrics.rule.sampleData')" size="small" class="ra-card">
              <template #header-extra>
                <n-radio-group v-model:value="dataMode" size="small">
                  <n-radio-button value="sample">{{ t('metrics.rule.sample') }}</n-radio-button>
                  <n-radio-button value="real">{{ t('metrics.rule.real') }}</n-radio-button>
                </n-radio-group>
              </template>
              <n-space v-if="dataMode === 'real'" class="ra-snapshot-bar">
                <n-input v-model:value="candidateId" :placeholder="t('metrics.rule.candidateId')" style="width: 240px" />
                <n-button size="small" :loading="loadingSnapshot" @click="loadSnapshot">
                  {{ loadingSnapshot ? t('metrics.rule.loading') : t('metrics.rule.loadSnapshot') }}
                </n-button>
              </n-space>
              <pre class="ra-json">{{ JSON.stringify(currentData, null, 2) }}</pre>
            </n-card>
          </div>
        </n-tab-pane>

        <!-- ---------- 规则管理 ---------- -->
        <n-tab-pane name="manage" :tab="t('metrics.rules.title')">
          <div class="ra-tab-bar">
            <n-button type="primary" @click="newRule">{{ t('metrics.rule.newRule') }}</n-button>
          </div>
          <n-data-table
            :columns="ruleColumns"
            :data="rules"
            :loading="loadingRules"
            :bordered="false"
            size="small"
            :row-key="(r: any) => r.id"
          />
        </n-tab-pane>

        <!-- ---------- 规则总览（只读聚合，保留既有统一规则引擎视图） ---------- -->
        <n-tab-pane name="overview" :tab="t('metrics.ruleEngine.overview')">
          <RuleEngine />
        </n-tab-pane>
      </n-tabs>
    </div>

    <n-modal
      v-model:show="resultVisible"
      preset="card"
      :title="t('metrics.rule.result')"
      style="width: 640px"
    >
      <n-alert v-if="runResult" :type="runResult.pass ? 'success' : 'error'" :title="runResult.pass ? t('metrics.rule.pass') : t('metrics.rule.fail')">
        {{ runResult.summary }}
      </n-alert>
      <div v-for="step in runResult?.steps || []" :key="step.index" class="ra-step">
        <n-tag :type="step.pass ? 'success' : 'error'" size="small">
          {{ step.pass ? t('metrics.rule.stepPass') : t('metrics.rule.stepFail') }}
        </n-tag>
        <span class="ra-step-detail">{{ step.detail || step.error }}</span>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
/**
 * RuleAuthoring —— 规则引擎模块（重构后承接原「规则配置与执行」「规则管理」）。
 *
 * 原先这两个功能寄生在「指标与规则」统一工作区（MetricsWorkspace）内，
 * 现按用户诉求拆分到独立的「规则引擎」模块：
 *   - 规则配置与执行：可视化编排条件 + 即时执行（不落库 / 落库）
 *   - 规则管理：已保存规则的启用停用 / 编辑 / 删除
 *   - 规则总览：复用既有统一规则引擎只读聚合视图（RuleEngine.vue），能力不丢
 */
import { computed, h, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import {
  NButton,
  NPopconfirm,
  NSwitch,
  NTag,
  useMessage,
} from 'naive-ui'
import {
  createMetricRule,
  deleteMetricRule,
  executeRule,
  getCandidateSnapshot,
  getMetricRule,
  getSampleData,
  listMetricRules,
  listMetricTemplates,
  listOperators,
  runMetricRule,
  toggleMetricRule,
  updateMetricRule,
  type ExecuteResult,
  type MetricRule,
  type MetricRuleScene,
  type MetricTemplate,
  type OptionItem,
  ACTION_TYPE_OPTIONS,
} from '@/api/metrics'
import { listDemands, listPositions, type Option } from '@/api/position'
import RuleEngine from './RuleEngine.vue'

const { t } = useI18n()
const message = useMessage()
const route = useRoute()

const activeTab = ref<'author' | 'manage' | 'overview'>('author')

// ===== 规则编排与执行 =====
const ruleId = ref('')
const ruleName = ref('')
const ruleScene = ref<MetricRuleScene>('MANUAL')
const actionType = ref<'VETO' | 'DEDUCT' | 'BONUS'>('DEDUCT')
const conditions = ref<any[]>([{ templateId: null, operator: null, value: '' }])
const result = ref<ExecuteResult | null>(null)
const executing = ref(false)
const saving = ref(false)
const dataMode = ref<'sample' | 'real'>('sample')
const candidateId = ref('')
const realData = ref<Record<string, any>>({})
const sampleData = ref<Record<string, any>>({})
const loadingSnapshot = ref(false)

// ===== 关联需求 / 职位：规则可绑定到具体业务对象，求值时注入 demand.* / position.* 指标路径 =====
const demandId = ref('')
const positionId = ref('')
const demandOptions = ref<Option[]>([])
const positionOptions = ref<Option[]>([])

const templateList = ref<MetricTemplate[]>([])
const operatorCatalog = ref<OptionItem[]>([])
const rules = ref<MetricRule[]>([])
const loadingRules = ref(false)

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

const currentData = computed(() => (dataMode.value === 'real' ? realData.value : sampleData.value))

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
  if (!conditions.value.length) conditions.value.push({ templateId: null, operator: null, value: '' })
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
    if (!conditions.value.length) conditions.value = [{ templateId: null, operator: null, value: '' }]
    demandId.value = rule.demandId || ''
    positionId.value = rule.positionId || ''
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
      conditions: persistConditions(conditions.value),
      demandId: demandId.value || null,
      positionId: positionId.value || null,
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

function persistConditions(list: any[]): any[] {
  return list
    .filter((c) => c.templateId && c.operator)
    .map((c) => {
      const cond: any = { templateId: c.templateId, operator: c.operator, value: c.value }
      if (c.operator === 'IN' || c.operator === 'NOT_IN') {
        if (Array.isArray(c.value)) cond.value = c.value.map((v: any) => (typeof v === 'number' ? String(v) : v))
      } else if (typeof c.value === 'number') {
        cond.value = String(c.value)
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
  demandId.value = ''
  positionId.value = ''
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
      h('div', { class: 'ra-actions-cell' }, [
        h(NButton, { size: 'small', quaternary: true, onClick: () => editRule(row) }, { default: () => t('metrics.rule.edit') }),
        h(NButton, { size: 'small', quaternary: true, onClick: () => runRule(row) }, { default: () => t('metrics.rule.run') }),
        h(
          NPopconfirm,
          { onPositiveClick: () => removeRule(row) },
          {
            trigger: () =>
              h(NButton, { size: 'small', quaternary: true, type: 'error' }, { default: () => t('metrics.btn.delete') }),
            default: () => t('metrics.msg.confirmDelete', { name: row.name }),
          },
        ),
      ]),
  },
])

async function load() {
  try {
    const [templates, ops, sample] = await Promise.all([
      listMetricTemplates(),
      listOperators(),
      getSampleData(),
    ])
    templateList.value = templates
    operatorCatalog.value = ops
    sampleData.value = sample
    await loadRules()
    // 关联需求 / 职位下拉（加载失败不阻塞规则主流程）
    try {
      const [demands, positions] = await Promise.all([listDemands(), listPositions()])
      demandOptions.value = demands
      positionOptions.value = positions.map((p) => ({ label: p.title || p.code, value: p.id }))
    } catch {
      /* demand/position 列表拉取失败不影响规则编辑 */
    }
  } catch {
    message.error(t('metrics.msg.loadFailed'))
  }
}

onMounted(async () => {
  await load()
  const id = (route.query.ruleId as string) || ''
  if (id) await loadRuleIntoAuthor(id)
})
</script>

<style scoped>
.rule-author { display: flex; flex-direction: column; height: 100%; }
.ra-title { margin: 0; font-size: 20px; font-weight: 600; }
.ra-subtitle { margin: 4px 0 0; font-size: 13px; color: var(--color-text-secondary, #6b7280); }
.ra-body { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding-top: 4px; }
.ra-tab-bar { display: flex; justify-content: flex-end; margin-bottom: 10px; }
.ra-author { display: flex; flex-direction: column; gap: 12px; }
.ra-card { flex: 0 0 auto; }
.ra-rule-meta { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.ra-rule-name { flex: 1 1 240px; min-width: 180px; }
.ra-rule-scene { flex: 0 0 160px; }
.ra-rule-binding { display: flex; gap: 16px; align-items: flex-end; flex-wrap: wrap; margin-top: 12px; }
.ra-bind-item { display: flex; flex-direction: column; gap: 4px; flex: 1 1 240px; min-width: 200px; }
.ra-bind-select { width: 100%; }
.ra-cond-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.ra-index { width: 24px; text-align: center; font-size: 13px; color: var(--color-text-secondary, #6b7280); }
.ra-template { flex: 1 1 220px; min-width: 180px; }
.ra-operator { flex: 0 0 140px; }
.ra-value { flex: 0 0 140px; }
.ra-unit { flex: 0 0 48px; font-size: 13px; color: var(--color-text-secondary, #6b7280); }
.ra-actions { margin-top: 12px; display: flex; justify-content: flex-end; }
.ra-empty { font-size: 13px; color: var(--color-text-secondary, #6b7280); padding: 8px 0; }
.ra-alert { margin-bottom: 12px; }
.ra-step { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-top: 1px solid var(--color-border, #e5e7eb); flex-wrap: wrap; }
.ra-step-index { font-size: 13px; color: var(--color-text-secondary, #6b7280); }
.ra-step-detail { font-size: 13px; }
.ra-snapshot-bar { margin-bottom: 8px; }
.ra-json { margin: 0; font-size: 12px; line-height: 1.5; max-height: 240px; overflow: auto; background: var(--color-bg-subtle, #f9fafb); padding: 10px; border-radius: 6px; }
.ra-actions-cell { display: flex; gap: 2px; }
</style>
