<template>
  <div class="page-container metric-library">
    <div class="page-header">
      <div>
        <h1 class="ml-title">{{ t('metrics.library.title') }}</h1>
        <p class="ml-subtitle">{{ t('metrics.library.subtitle') }}</p>
      </div>
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

    <div class="page-body ml-body">
      <n-tabs v-model:value="activeTab" type="line" animated>
        <!-- 原子指标 -->
        <n-tab-pane name="atomic" :tab="t('metrics.tab.atomic')">
          <n-data-table
            :columns="atomicColumns"
            :data="atomicList"
            :loading="loading"
            :bordered="false"
            size="small"
          />
        </n-tab-pane>

        <!-- 派生指标 -->
        <n-tab-pane name="derived" :tab="t('metrics.tab.derived')">
          <n-data-table
            :columns="derivedColumns"
            :data="derivedList"
            :loading="loading"
            :bordered="false"
            size="small"
          />
        </n-tab-pane>

        <!-- 指标模板 -->
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
    </div>

    <!-- 新建弹窗 -->
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

        <!-- 原子指标：字段路径 -->
        <n-form-item v-if="modalKind === 'atomic'" :label="t('metrics.form.sourcePath')" required>
          <n-input v-model:value="form.sourcePath" placeholder="candidate.age" />
          <template #feedback>
            <span class="ml-tip">{{ t('metrics.form.sourcePathTip') }}</span>
          </template>
        </n-form-item>

        <!-- 派生指标：计算函数 + 数据来源 + 参数 -->
        <template v-if="modalKind === 'derived'">
          <n-form-item :label="t('metrics.form.calcFunc')" required>
            <n-select
              v-model:value="form.calcFunc"
              :options="derivedFuncOptions"
              :placeholder="t('metrics.form.calcFunc')"
            />
          </n-form-item>
          <n-form-item :label="t('metrics.form.basePath')" required>
            <n-input v-model:value="form.basePath" placeholder="candidate.workExperience" />
          </n-form-item>
          <n-form-item :label="t('metrics.form.params')">
            <n-input v-model:value="form.paramsText" :placeholder="t('metrics.form.paramsTip')" />
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
              :options="operatorOptions"
              :placeholder="t('metrics.form.operators')"
            />
          </n-form-item>
        </template>

        <n-form-item :label="t('metrics.form.dataType')">
          <n-select v-model:value="form.dataType" :options="dataTypeOptions" />
        </n-form-item>
        <n-form-item :label="t('metrics.form.unit')">
          <n-input v-model:value="form.unit" placeholder="岁 / 月 / 元" />
        </n-form-item>
        <n-form-item :label="t('metrics.form.description')">
          <n-input v-model:value="form.description" type="textarea" :rows="2" />
        </n-form-item>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="showModal = false">{{ t('metrics.btn.cancel') }}</n-button>
          <n-button type="primary" :loading="saving" @click="submit">
            {{ t('metrics.btn.save') }}
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
/**
 * 指标库 —— 原子指标 / 派生指标 / 指标模板 三合一管理页。
 *
 * 派生指标是本页与 PRD 原方案的关键差异：它让「最大空窗期」「近 N 年跳槽段数」
 * 这类计算型规则也能由运营零代码配置，而不必新增开发。
 */
import { computed, h, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { NButton, NPopconfirm, useMessage } from 'naive-ui'
import {
  createAtomicMetric,
  createDerivedMetric,
  createMetricTemplate,
  deleteAtomicMetric,
  deleteDerivedMetric,
  deleteMetricTemplate,
  listAtomicMetrics,
  listDerivedFuncs,
  listDerivedMetrics,
  listMetricTemplates,
  listOperators,
  type AtomicMetric,
  type DerivedMetric,
  type MetricTemplate,
} from '@/api/metrics'

const { t } = useI18n()
const message = useMessage()

const activeTab = ref('atomic')
const loading = ref(false)
const saving = ref(false)

const atomicList = ref<AtomicMetric[]>([])
const derivedList = ref<DerivedMetric[]>([])
const templateList = ref<MetricTemplate[]>([])
const operatorOptions = ref<{ label: string; value: string }[]>([])
const derivedFuncs = ref<{ name: string; label: string }[]>([])

const showModal = ref(false)
const modalKind = ref<'atomic' | 'derived' | 'template'>('atomic')
const form = ref<any>({})

const modalTitle = computed(() => {
  if (modalKind.value === 'atomic') return t('metrics.dialog.createAtomic')
  if (modalKind.value === 'derived') return t('metrics.dialog.createDerived')
  return t('metrics.dialog.createTemplate')
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
    operatorOptions.value = ops
    derivedFuncs.value = funcs
  } catch (error) {
    message.error(t('metrics.msg.loadFailed'))
  } finally {
    loading.value = false
  }
}

function openCreate(kind: 'atomic' | 'derived' | 'template') {
  modalKind.value = kind
  form.value = {
    name: '',
    sourcePath: '',
    basePath: '',
    calcFunc: null,
    paramsText: '',
    atomicMetric: null,
    derivedMetric: null,
    operators: [],
    dataType: kind === 'template' ? 'number' : 'number',
    unit: '',
    description: '',
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
    if (modalKind.value === 'atomic') {
      if (!form.value.sourcePath?.trim()) {
        message.warning(t('metrics.msg.requiredPath'))
        return
      }
      await createAtomicMetric({
        name: form.value.name,
        sourcePath: form.value.sourcePath,
        dataType: form.value.dataType,
        unit: form.value.unit,
        description: form.value.description,
      })
    } else if (modalKind.value === 'derived') {
      if (!form.value.calcFunc) {
        message.warning(t('metrics.msg.requiredFunc'))
        return
      }
      if (!form.value.basePath?.trim()) {
        message.warning(t('metrics.msg.requiredPath'))
        return
      }
      let params: Record<string, any> = {}
      if (form.value.paramsText?.trim()) {
        try {
          params = JSON.parse(form.value.paramsText)
          if (typeof params !== 'object' || Array.isArray(params) || params === null) {
            message.warning(t('metrics.msg.badParams'))
            return
          }
        } catch {
          message.warning(t('metrics.msg.badParams'))
          return
        }
      }
      await createDerivedMetric({
        name: form.value.name,
        calcFunc: form.value.calcFunc,
        basePath: form.value.basePath,
        params,
        dataType: form.value.dataType,
        unit: form.value.unit,
        description: form.value.description,
      })
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
      await createMetricTemplate({
        name: form.value.name,
        atomicMetric: form.value.atomicMetric,
        derivedMetric: form.value.derivedMetric,
        operators: form.value.operators,
        description: form.value.description,
      })
    }
    message.success(t('metrics.msg.created'))
    showModal.value = false
    await load()
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.saveFailed'))
  } finally {
    saving.value = false
  }
}

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

const atomicColumns = computed(() => [
  { title: t('metrics.col.name'), key: 'name' },
  {
    title: t('metrics.col.sourcePath'),
    key: 'sourcePath',
    render: (row: any) => h('code', { class: 'ml-code' }, { default: () => row.sourcePath }),
  },
  { title: t('metrics.col.dataType'), key: 'dataType' },
  { title: t('metrics.col.unit'), key: 'unit' },
  { title: t('metrics.col.templateCount'), key: 'templateCount' },
  {
    title: t('metrics.col.action'),
    key: 'action',
    render: (row: any) => deleteButton(row, 'atomic'),
  },
])

const derivedColumns = computed(() => [
  { title: t('metrics.col.name'), key: 'name' },
  { title: t('metrics.col.calcFunc'), key: 'calcFunc' },
  {
    title: t('metrics.col.basePath'),
    key: 'basePath',
    render: (row: any) => h('code', { class: 'ml-code' }, { default: () => row.basePath }),
  },
  {
    title: t('metrics.col.params'),
    key: 'params',
    render: (row: any) => (row.params && Object.keys(row.params).length ? JSON.stringify(row.params) : '-'),
  },
  { title: t('metrics.col.unit'), key: 'unit' },
  { title: t('metrics.col.templateCount'), key: 'templateCount' },
  {
    title: t('metrics.col.action'),
    key: 'action',
    render: (row: any) => deleteButton(row, 'derived'),
  },
])

const templateColumns = computed(() => [
  { title: t('metrics.col.name'), key: 'name' },
  { title: t('metrics.col.metric'), key: 'metricName' },
  {
    title: t('metrics.col.metricPath'),
    key: 'metricPath',
    render: (row: any) => h('code', { class: 'ml-code' }, { default: () => row.metricPath }),
  },
  {
    title: t('metrics.col.operators'),
    key: 'operators',
    render: (row: any) =>
      h(
        'div',
        { class: 'ml-ops' },
        {
          default: () =>
            (row.operators || []).map((op: string) =>
              h('span', { class: 'ml-op-tag' }, { default: () => operatorLabel(op) }),
            ),
        },
      ),
  },
  {
    title: t('metrics.col.action'),
    key: 'action',
    render: (row: any) => deleteButton(row, 'template'),
  },
])

function operatorLabel(value: string) {
  return operatorOptions.value.find((o) => o.value === value)?.label ?? value
}

onMounted(load)
</script>

<style scoped>
.metric-library {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.ml-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}
.ml-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}
/* 设置页滚动模型 B：page-body 承担滚动，避免整页冻结 */
.ml-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-top: 8px;
}
.ml-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--color-bg-subtle, #f9fafb);
}
.ml-tip {
  font-size: 12px;
  color: var(--color-text-secondary, #6b7280);
}
.ml-ops {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.ml-op-tag {
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--color-bg-subtle, #f9fafb);
  border: 1px solid var(--color-border, #e5e7eb);
}
</style>
