<template>
  <div class="page-container metric-rules">
    <div class="page-header">
      <div>
        <h1 class="mrs-title">{{ t('metrics.rules.title') }}</h1>
        <p class="mrs-subtitle">{{ t('metrics.rules.subtitle') }}</p>
      </div>
      <n-button type="primary" @click="createRule">
        {{ t('metrics.rule.newRule') }}
      </n-button>
    </div>

    <div class="page-body mrs-body">
      <n-data-table
        :columns="columns"
        :data="rules"
        :loading="loading"
        :bordered="false"
        size="small"
      />
    </div>

    <!-- 执行结果弹窗 -->
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
      <div v-for="step in runResult?.steps || []" :key="step.index" class="mrs-step">
        <n-tag :type="step.pass ? 'success' : 'error'" size="small">
          {{ step.pass ? t('metrics.rule.stepPass') : t('metrics.rule.stepFail') }}
        </n-tag>
        <span class="mrs-step-detail">{{ step.detail || step.error }}</span>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
/**
 * 规则管理 —— 已保存指标的列表、启停、编辑、执行、删除。
 *
 * 与「规则配置与执行」页的分工：
 *   本页 = 管理已持久化规则（CRUD + 启停 + 按规则执行）
 *   配置页 = 编排条件（支持 ?ruleId= 加载已有规则并更新）
 */
import { computed, h, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { NButton, NPopconfirm, NSwitch, useMessage } from 'naive-ui'
import {
  deleteMetricRule,
  listMetricRules,
  runMetricRule,
  toggleMetricRule,
  type ExecuteResult,
  type MetricRule,
} from '@/api/metrics'

const { t } = useI18n()
const router = useRouter()
const message = useMessage()

const rules = ref<MetricRule[]>([])
const loading = ref(false)
const runResult = ref<ExecuteResult | null>(null)
const resultVisible = ref(false)

async function load() {
  loading.value = true
  try {
    rules.value = await listMetricRules()
  } catch (error) {
    message.error(t('metrics.msg.loadFailed'))
  } finally {
    loading.value = false
  }
}

function createRule() {
  router.push('/settings/metric-rule-config')
}

function editRule(row: MetricRule) {
  router.push(`/settings/metric-rule-config?ruleId=${row.id}`)
}

async function onToggle(row: MetricRule, value: boolean) {
  try {
    const res = await toggleMetricRule(row.id)
    row.enabled = res.enabled
  } catch (error) {
    message.error(t('metrics.msg.saveFailed'))
    await load()
  }
}

async function removeRule(row: MetricRule) {
  try {
    await deleteMetricRule(row.id)
    message.success(t('metrics.msg.deleted'))
    await load()
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.deleteFailed'))
  }
}

async function runRule(row: MetricRule) {
  const candidateId = window.prompt(t('metrics.rule.candidateId'))
  if (!candidateId) return
  try {
    runResult.value = await runMetricRule(row.id, candidateId.trim())
    resultVisible.value = true
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.executeFailed'))
  }
}

function sceneLabel(scene: string) {
  return t(`metrics.scene.${scene}` as any)
}

const columns = computed(() => [
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
      h('div', { class: 'mrs-actions' }, [
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

onMounted(load)
</script>

<style scoped>
.metric-rules {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.mrs-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}
.mrs-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}
/* 设置页滚动模型 B */
.mrs-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-top: 8px;
}
.mrs-actions {
  display: flex;
  gap: 2px;
}
.mrs-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-top: 1px solid var(--color-border, #e5e7eb);
  flex-wrap: wrap;
}
.mrs-step-detail {
  font-size: 13px;
}
</style>
