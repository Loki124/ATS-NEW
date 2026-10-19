<template>
  <div class="page-container">
    <div class="page-header">
      <div class="ph-left">
        <h1 class="page-title">{{ mode === 'edit' ? t('pages.settings.DynamicStrategy.s3') : t('pages.settings.DynamicStrategy.s1') }}</h1>
      </div>
      <div class="ph-right">
        <n-button v-if="mode === 'list'" type="primary" @click="openCreate">
          {{ t('pages.settings.DynamicStrategy.s2') }}
        </n-button>
        <template v-else>
          <n-button @click="goList">{{ t('pages.settings.DynamicStrategy.s11') }}</n-button>
          <n-button type="primary" :loading="saving" @click="onSave">{{ t('pages.settings.DynamicStrategy.s10') }}</n-button>
          <n-button v-if="editingCode" type="error" quaternary @click="onDeleteCurrent">
            {{ t('pages.settings.DynamicStrategy.s12') }}
          </n-button>
        </template>
      </div>
    </div>

    <div class="page-body">
      <!-- ===== 列表视图 ===== -->
      <template v-if="mode === 'list'">
        <n-data-table
          :columns="columns"
          :data="list"
          :loading="loading"
          :row-key="(row: DynamicStrategy) => row.strategy_code"
          :bordered="false"
          class="ds-table"
        />
        <n-empty
          v-if="!loading && list.length === 0"
          :description="t('pages.settings.DynamicStrategy.s14')"
          class="ds-empty"
        />
      </template>

      <!-- ===== 详情（新建 / 编辑）视图 ===== -->
      <template v-else>
        <div class="glass-panel ds-form">
          <!-- 基础信息 -->
          <section class="ds-section">
            <h2 class="ds-section-title">{{ t('pages.settings.DynamicStrategy.s4') }}</h2>
            <n-form :model="form" label-placement="top" class="ds-basic">
              <n-form-item :label="t('pages.settings.DynamicStrategy.s4')" required>
                <n-input
                  v-model:value="form.strategy_name"
                  :placeholder="t('pages.settings.DynamicStrategy.s4')"
                  :disabled="!!editingCode"
                />
              </n-form-item>
              <n-form-item :label="t('pages.settings.DynamicStrategy.s5')">
                <div class="status-row">
                  <n-switch v-model:value="statusSwitch" />
                  <span class="status-text" :class="{ off: !statusSwitch }">
                    {{ statusSwitch ? t('pages.settings.DynamicStrategy.s17') : t('pages.settings.DynamicStrategy.s18') }}
                  </span>
                </div>
              </n-form-item>
              <n-form-item :label="t('pages.settings.DynamicStrategy.s6')">
                <n-input
                  v-model:value="form.description"
                  type="textarea"
                  :rows="2"
                  :placeholder="t('pages.settings.DynamicStrategy.s6')"
                />
              </n-form-item>
            </n-form>
          </section>

          <!-- 受策略限制的功能 -->
          <section class="ds-section">
            <h2 class="ds-section-title">{{ t('pages.settings.DynamicStrategy.s7') }}</h2>
            <n-checkbox-group
              :value="form.governed_functions"
              @update:value="(v) => onGovernedChange(v as string[])"
            >
              <n-space :size="[16, 8]">
                <n-checkbox
                  v-for="m in GOVERNED_MODULES"
                  :key="m.value"
                  :value="m.value"
                  class="ds-module-check"
                >
                  {{ m.label }}
                </n-checkbox>
              </n-space>
            </n-checkbox-group>
          </section>

          <!-- 操作权限配置 -->
          <section class="ds-section">
            <h2 class="ds-section-title">{{ t('pages.settings.DynamicStrategy.s8') }}</h2>
            <div v-if="modulePermList.length === 0" class="ds-hint">
              {{ t('pages.settings.DynamicStrategy.s7') }}
            </div>
            <div v-else class="ds-action-cards">
              <ModuleActionCard
                v-for="item in modulePermList"
                :key="item.key"
                :module="item.perm"
                :label="MODULE_LABELS[item.key]"
                :desc="MODULE_DESCS[item.key]"
                :disabled="false"
                :can-config="true"
                :action-registry="options.actions"
                :preset-packages="options.presets"
                @update:write-mode="(wm: WriteMode) => onWriteMode(item.key, wm)"
                @update:write-actions="(acts: string[]) => onWriteActions(item.key, acts)"
              />
            </div>
          </section>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { h, ref, reactive, computed, onMounted } from 'vue'
import {
  NButton, NDataTable, NInput, NSwitch, NCheckboxGroup, NCheckbox,
  NTag, NSpace, NForm, NFormItem, NEmpty, useMessage, useDialog,
  type DataTableColumns,
} from 'naive-ui'
import ModuleActionCard from '@/components/role/ModuleActionCard.vue'
import {
  listStrategies, getStrategyOptions, createStrategy, updateStrategy, deleteStrategy,
  type DynamicStrategy, type StrategyModuleConfig, type StrategyOptions,
} from '@/api/dynamicStrategy'
import type { ModulePerm, WriteMode, ActionDictItem, ActionPreset } from '@/api/data-permission'

const { t } = useI18n()
const message = useMessage()
const dialog = useDialog()

// ===== 模块元数据 =====
const GOVERNED_MODULES = [
  { value: 'demand', label: '招聘需求' },
  { value: 'process', label: '招聘流程' },
  { value: 'position', label: '招聘职位' },
  { value: 'candidate', label: '候选人管理' },
  { value: 'talent', label: '人才库' },
]
const MODULE_LABELS: Record<string, string> = {
  demand: '招聘需求',
  process: '招聘流程',
  position: '招聘职位',
  candidate: '候选人管理',
  talent: '人才库',
}
const MODULE_DESCS: Record<string, string> = {
  demand: '控制该策略对「招聘需求」模块可执行的写操作',
  process: '控制该策略对「招聘流程」模块可执行的写操作',
  position: '控制该策略对「招聘职位」模块可执行的写操作',
  candidate: '控制该策略对「候选人管理」模块可执行的写操作',
  talent: '控制该策略对「人才库」模块可执行的写操作',
}

// ===== 视图模式 =====
type Mode = 'list' | 'edit'
const mode = ref<Mode>('list')
const editingCode = ref<string | null>(null)
const saving = ref(false)

// ===== 列表 =====
const list = ref<DynamicStrategy[]>([])
const loading = ref(false)
async function loadList() {
  loading.value = true
  try {
    list.value = await listStrategies()
  } catch (e: any) {
    list.value = []
    message.error(e?.response?.data?.message || e?.message || t('pages.settings.DynamicStrategy.s1'))
  } finally {
    loading.value = false
  }
}

const columns = computed<DataTableColumns<DynamicStrategy>>(() => [
  {
    title: () => t('pages.settings.DynamicStrategy.s4'),
    key: 'strategy_name',
    render: (row: DynamicStrategy) => row.strategy_name,
  },
  {
    title: () => t('pages.settings.DynamicStrategy.s5'),
    key: 'status',
    render: (row: DynamicStrategy) =>
      h(
        NTag,
        { type: row.status === 1 ? 'success' : 'default', size: 'small', bordered: false },
        { default: () => (row.status === 1 ? t('pages.settings.DynamicStrategy.s17') : t('pages.settings.DynamicStrategy.s18')) },
      ),
  },
  {
    title: () => t('pages.settings.DynamicStrategy.s16'),
    key: 'governs',
    render: (row: DynamicStrategy) => `${row.governed_functions?.length ?? 0}`,
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: DynamicStrategy) =>
      h('div', { class: 'row-actions' }, [
        h(NButton, { size: 'small', quaternary: true, onClick: () => openEdit(row) }, { default: () => t('pages.settings.DynamicStrategy.s3') }),
        h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => onDelete(row) }, { default: () => t('pages.settings.DynamicStrategy.s12') }),
      ]),
  },
])

// ===== 表单状态 =====
function defaultModuleConfig(): StrategyModuleConfig {
  return { mode: 'none', expr: '', groups: [], actions: [] }
}

const form = reactive({
  strategy_code: '',
  strategy_name: '',
  status: 1 as number,
  description: '',
  governed_functions: [] as string[],
  granted_resource_codes: [] as string[],
  module_config: {} as Record<string, StrategyModuleConfig>,
})

const statusSwitch = computed({
  get: () => form.status === 1,
  set: (v: boolean) => { form.status = v ? 1 : 0 },
})

// ModuleActionCard 需要稳定的 ModulePerm 引用（避免每次渲染新建对象触发卡内折叠重置）
const modulePerms = reactive<Record<string, ModulePerm>>({})
function clearModulePerms() {
  Object.keys(modulePerms).forEach((k) => { delete modulePerms[k] })
}
function ensureModulePerm(key: string) {
  if (modulePerms[key]) return
  const cfg = form.module_config[key] ?? defaultModuleConfig()
  modulePerms[key] = {
    moduleKey: key,
    mode: 'all',
    expr: '',
    groups: [],
    featureGranted: true,
    write: { mode: cfg.mode, expr: cfg.expr, groups: cfg.groups, actions: cfg.actions },
  }
}
const modulePermList = computed(() =>
  form.governed_functions
    .filter((k) => modulePerms[k])
    .map((k) => ({ key: k, perm: modulePerms[k] })),
)

function onGovernedChange(vals: string[]) {
  form.governed_functions = vals
  for (const k of vals) {
    if (!modulePerms[k]) {
      const cfg = form.module_config[k] ?? defaultModuleConfig()
      modulePerms[k] = {
        moduleKey: k,
        mode: 'all',
        expr: '',
        groups: [],
        featureGranted: true,
        write: { mode: cfg.mode, expr: cfg.expr, groups: cfg.groups, actions: cfg.actions },
      }
    }
  }
}

function onWriteMode(key: string, modeVal: WriteMode) {
  ensureModulePerm(key)
  modulePerms[key].write!.mode = modeVal
  if (!form.module_config[key]) form.module_config[key] = defaultModuleConfig()
  form.module_config[key].mode = modeVal
}
function onWriteActions(key: string, actions: string[]) {
  ensureModulePerm(key)
  modulePerms[key].write!.actions = [...actions]
  if (!form.module_config[key]) form.module_config[key] = defaultModuleConfig()
  form.module_config[key].actions = [...actions]
}

// ===== 选项（动作字典 / 预设包）=====
const options = ref<StrategyOptions>({ modules: [], actions: [] as ActionDictItem[], presets: [] as ActionPreset[] })
async function loadOptions() {
  try {
    options.value = await getStrategyOptions()
  } catch {
    options.value = { modules: [], actions: [], presets: [] }
  }
}

// ===== 进入新建 / 编辑 =====
async function openCreate() {
  editingCode.value = null
  form.strategy_code = ''
  form.strategy_name = ''
  form.status = 1
  form.description = ''
  form.governed_functions = []
  form.granted_resource_codes = []
  form.module_config = {}
  clearModulePerms()
  mode.value = 'edit'
  await loadOptions()
}

async function openEdit(row: DynamicStrategy) {
  editingCode.value = row.strategy_code
  form.strategy_code = row.strategy_code
  form.strategy_name = row.strategy_name
  form.status = row.status
  form.description = row.description ?? ''
  form.governed_functions = [...(row.governed_functions || [])]
  form.granted_resource_codes = [...(row.granted_resource_codes || [])]
  form.module_config = {}
  for (const k of form.governed_functions) {
    const cfg = row.module_config?.[k]
    form.module_config[k] = cfg
      ? { mode: cfg.mode, expr: cfg.expr, groups: cfg.groups ? cfg.groups.map((g) => ({ ...g })) : [], actions: [...cfg.actions] }
      : defaultModuleConfig()
  }
  clearModulePerms()
  // 为预勾选的受限制模块预建稳定的 ModulePerm 引用（checkbox 初始值不会触发 onGovernedChange）
  for (const k of form.governed_functions) {
    const cfg = form.module_config[k] ?? defaultModuleConfig()
    modulePerms[k] = {
      moduleKey: k,
      mode: 'all',
      expr: '',
      groups: [],
      featureGranted: true,
      write: { mode: cfg.mode, expr: cfg.expr, groups: cfg.groups, actions: cfg.actions },
    }
  }
  mode.value = 'edit'
  await loadOptions()
}

function buildPayload(): Partial<DynamicStrategy> {
  const module_config: Record<string, StrategyModuleConfig> = {}
  for (const k of form.governed_functions) {
    module_config[k] = form.module_config[k] ?? defaultModuleConfig()
  }
  return {
    strategy_code: form.strategy_code,
    strategy_name: form.strategy_name,
    status: form.status,
    description: form.description,
    governed_functions: [...form.governed_functions],
    granted_resource_codes: [...form.granted_resource_codes],
    module_config,
  }
}

// ===== 保存 =====
async function onSave() {
  if (!form.strategy_name.trim()) {
    message.warning(`${t('pages.settings.DynamicStrategy.s4')}不能为空`)
    return
  }
  saving.value = true
  try {
    if (editingCode.value) {
      await updateStrategy(editingCode.value, buildPayload())
      message.success(t('pages.settings.DynamicStrategy.s20'))
    } else {
      const payload = buildPayload()
      if (!payload.strategy_code) payload.strategy_code = `STRAT_${Date.now()}`
      await createStrategy(payload)
      message.success(t('pages.settings.DynamicStrategy.s19'))
    }
    mode.value = 'list'
    editingCode.value = null
    clearModulePerms()
    await loadList()
  } catch (e: any) {
    message.error(e?.response?.data?.message || e?.message || t('pages.settings.DynamicStrategy.s10'))
  } finally {
    saving.value = false
  }
}

function goList() {
  mode.value = 'list'
  editingCode.value = null
  clearModulePerms()
  loadList()
}

// ===== 删除 =====
function onDelete(row: DynamicStrategy) {
  dialog.warning({
    title: t('pages.settings.DynamicStrategy.s12'),
    content: t('pages.settings.DynamicStrategy.s13'),
    positiveText: t('pages.settings.DynamicStrategy.s12'),
    negativeText: t('pages.settings.DynamicStrategy.s11'),
    onPositiveClick: async () => {
      try {
        await deleteStrategy(row.strategy_code)
        message.success('删除成功')
        await loadList()
      } catch (e: any) {
        message.error(e?.response?.data?.message || e?.message || t('pages.settings.DynamicStrategy.s12'))
      }
    },
  })
}

function onDeleteCurrent() {
  if (!editingCode.value) return
  const code = editingCode.value
  dialog.warning({
    title: t('pages.settings.DynamicStrategy.s12'),
    content: t('pages.settings.DynamicStrategy.s13'),
    positiveText: t('pages.settings.DynamicStrategy.s12'),
    negativeText: t('pages.settings.DynamicStrategy.s11'),
    onPositiveClick: async () => {
      try {
        await deleteStrategy(code)
        message.success('删除成功')
        mode.value = 'list'
        editingCode.value = null
        clearModulePerms()
        await loadList()
      } catch (e: any) {
        message.error(e?.response?.data?.message || e?.message || t('pages.settings.DynamicStrategy.s12'))
      }
    },
  })
}

onMounted(loadList)
</script>

<style scoped>
/* 页面布局三件套（与 PermissionManagement 同款）：页头固定 + 内容区自滚 */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}
.page-title {
  margin: 0;
  font-size: var(--fs-18, 18px);
  font-weight: 600;
  color: var(--ink);
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.ph-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.ds-table { background: transparent; }
.ds-empty { padding: 48px 0; }

/* 表单面板 */
.ds-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding: var(--space-5);
}
.ds-section { display: flex; flex-direction: column; gap: var(--space-2); }
.ds-section-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}
.ds-basic {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3) var(--space-4);
}
.ds-basic :deep(.n-form-item) { margin-bottom: 0; }
.status-row { display: flex; align-items: center; gap: var(--space-2); }
.status-text { font-size: 13px; color: var(--c-success-deep); }
.status-text.off { color: var(--ink-faint); }

.ds-module-check { font-size: 14px; }

.ds-hint {
  font-size: 13px;
  color: var(--ink-faint);
  padding: var(--space-2) 0;
}
.ds-action-cards {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
</style>
