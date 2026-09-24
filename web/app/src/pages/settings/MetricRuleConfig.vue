<template>
  <div class="page-container metric-rule">
    <div class="page-header">
      <div>
        <h1 class="mr-title">{{ t('metrics.rule.title') }}</h1>
        <p class="mr-subtitle">{{ t('metrics.rule.subtitle') }}</p>
      </div>
    </div>

    <div class="page-body mr-body">
      <!-- 条件编辑区 -->
      <n-card :title="t('metrics.rule.conditionArea')" size="small" class="mr-card">
        <template #header-extra>
          <n-button size="small" @click="addCondition">{{ t('metrics.btn.addCondition') }}</n-button>
        </template>

        <div v-if="!templateList.length" class="mr-empty">
          {{ t('metrics.rule.noTemplateHint') }}
        </div>

        <div v-for="(cond, idx) in conditions" :key="idx" class="mr-cond-row">
          <span class="mr-index">{{ idx + 1 }}</span>
          <n-select
            v-model:value="cond.templateId"
            :options="templateOptions"
            class="mr-template"
            :placeholder="t('metrics.rule.template')"
            @update:value="onTemplateChange(cond)"
          />
          <n-select
            v-model:value="cond.operator"
            :options="operatorOptionsFor(cond)"
            class="mr-operator"
            :placeholder="t('metrics.rule.operator')"
          />
          <n-input
            v-model:value="cond.value"
            class="mr-value"
            :placeholder="t('metrics.rule.value')"
          />
          <span class="mr-unit">{{ unitOf(cond) || '-' }}</span>
          <n-button size="small" quaternary type="error" @click="removeCondition(idx)">
            {{ t('metrics.btn.delete') }}
          </n-button>
        </div>

        <div class="mr-actions">
          <n-button
            type="primary"
            :loading="executing"
            :disabled="!canExecute"
            @click="execute"
          >
            {{ executing ? t('metrics.btn.executing') : t('metrics.btn.execute') }}
          </n-button>
        </div>
      </n-card>

      <!-- 执行结果 -->
      <n-card :title="t('metrics.rule.result')" size="small" class="mr-card">
        <div v-if="!result" class="mr-empty">{{ t('metrics.rule.noResult') }}</div>
        <template v-else>
          <n-alert :type="result.pass ? 'success' : 'error'" :title="result.pass ? t('metrics.rule.pass') : t('metrics.rule.fail')" class="mr-alert">
            {{ result.summary }}
          </n-alert>
          <div v-for="step in result.steps" :key="step.index" class="mr-step">
            <n-tag :type="step.pass ? 'success' : 'error'" size="small">
              {{ step.pass ? t('metrics.rule.stepPass') : t('metrics.rule.stepFail') }}
            </n-tag>
            <span class="mr-step-index">{{ t('metrics.rule.step') }} {{ step.index }}</span>
            <span class="mr-step-detail">{{ step.detail || step.error }}</span>
          </div>
        </template>
      </n-card>

      <!-- 测试数据 -->
      <n-card :title="t('metrics.rule.sampleData')" size="small" class="mr-card">
        <pre class="mr-json">{{ JSON.stringify(sampleData, null, 2) }}</pre>
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 规则配置与执行 —— 运营选择指标模板 + 运算符 + 值，即时执行并看到分步结果。
 *
 * 与 PRD 原方案的差异：
 *  1. 不落库：直接调 /metrics/rules/execute/，避免每次执行都产生一条垃圾规则记录
 *  2. 运算符来自模板 operators 子集（切换模板时自动重置非法运算符，PRD F-07）
 *  3. 取值支持派生指标，故「最大空窗期 ≤ 6 个月」这类计算型规则同样零代码可配
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import {
  executeRule,
  getSampleData,
  listMetricTemplates,
  listOperators,
  type ExecuteResult,
  type MetricTemplate,
} from '@/api/metrics'

const { t } = useI18n()
const message = useMessage()

const templateList = ref<MetricTemplate[]>([])
const operatorCatalog = ref<{ label: string; value: string }[]>([])
const sampleData = ref<Record<string, any>>({})
const conditions = ref<any[]>([{ templateId: null, operator: null, value: '' }])
const result = ref<ExecuteResult | null>(null)
const executing = ref(false)

const templateOptions = computed(() =>
  templateList.value.map((tp) => ({
    label: `${tp.name}（${tp.metricName || tp.metricPath || ''}）`,
    value: tp.id,
  })),
)

const canExecute = computed(() =>
  conditions.value.some((c) => c.templateId && c.operator),
)

function operatorOptionsFor(cond: any) {
  const tp = templateList.value.find((x) => x.id === cond.templateId)
  const allowed = tp?.operators || []
  return operatorCatalog.value
    .filter((op) => allowed.includes(op.value))
    .map((op) => ({ label: op.label, value: op.value }))
}

function onTemplateChange(cond: any) {
  // 切换模板：若当前运算符不在新模板的运算符集合中，自动重置为第一个（PRD F-07）
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

async function execute() {
  executing.value = true
  result.value = null
  try {
    const payload = {
      conditions: conditions.value
        .filter((c) => c.templateId && c.operator)
        .map((c) => ({ templateId: c.templateId, operator: c.operator, value: c.value })),
      logic: 'AND',
      data: sampleData.value,
    }
    result.value = await executeRule(payload as any)
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.executeFailed'))
  } finally {
    executing.value = false
  }
}

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
  } catch (error) {
    message.error(t('metrics.msg.loadFailed'))
  }
}

onMounted(load)
</script>

<style scoped>
.metric-rule {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.mr-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}
.mr-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}
/* 设置页滚动模型 B：page-body 承担滚动 */
.mr-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.mr-card {
  flex: 0 0 auto;
}
.mr-cond-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.mr-index {
  width: 24px;
  text-align: center;
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}
.mr-template {
  flex: 1 1 220px;
  min-width: 180px;
}
.mr-operator {
  flex: 0 0 140px;
}
.mr-value {
  flex: 0 0 140px;
}
.mr-unit {
  flex: 0 0 48px;
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}
.mr-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
.mr-empty {
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
  padding: 8px 0;
}
.mr-alert {
  margin-bottom: 12px;
}
.mr-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-top: 1px solid var(--color-border, #e5e7eb);
  flex-wrap: wrap;
}
.mr-step-index {
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}
.mr-step-detail {
  font-size: 13px;
}
.mr-json {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  max-height: 240px;
  overflow: auto;
  background: var(--color-bg-subtle, #f9fafb);
  padding: 10px;
  border-radius: 6px;
}
</style>
