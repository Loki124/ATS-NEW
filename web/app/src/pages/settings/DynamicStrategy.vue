<template>
  <div class="page-container">
    <div class="page-header">
      <div class="ph-left">
        <h1 class="page-title">{{ t('pages.settings.DynamicStrategy.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.DynamicStrategy.s21') }}</p>
      </div>
    </div>

    <div class="page-body">
      <!-- ===== 列表（常驻；新建/编辑统一走弹窗，2026-10-19 兵哥拍板）===== -->
      <div class="glass-panel panel-shell">
        <div class="toolbar">
          <n-input
            v-model:value="searchKeyword"
            :placeholder="t('pages.settings.DynamicStrategy.s22')"
            clearable
            class="ds-search"
            @change="onSearchChange"
            @clear="onSearchChange"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
          <div class="spacer"></div>
          <n-button type="primary" class="gradient-btn" @click="openCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            {{ t('pages.settings.DynamicStrategy.s2') }}
          </n-button>
        </div>

        <div class="table-wrap">
          <n-data-table
            :columns="columns"
            :data="list"
            :loading="loading"
            :row-key="(row: DynamicStrategy) => row.strategyCode"
            :bordered="false"
            :pagination="pagination"
            flex-height
            @update:page="onPageChange"
          >
            <!-- 单一空态（乙系规范：禁止 n-data-table 自带空态 + 自定义 n-empty 并存） -->
            <template #empty>
              <n-empty :description="t('pages.settings.DynamicStrategy.s14')" />
            </template>
          </n-data-table>
        </div>
      </div>
    </div>

    <!-- ===== 策略详情弹窗（新建 / 编辑统一走 modal）===== -->
    <n-modal
      :show="mode === 'edit'"
      preset="card"
      :title="editingCode ? t('pages.settings.DynamicStrategy.s3') : t('pages.settings.DynamicStrategy.s2')"
      :style="{ width: '1080px', maxWidth: '95vw' }"
      :content-style="{ maxHeight: 'min(68vh, 720px)', overflowY: 'auto', padding: '16px 20px' }"
      :mask-closable="false"
      @update:show="(v: boolean) => { if (!v && mode === 'edit') goList() }"
    >
      <div class="ds-form">
        <!-- 名称 + 状态（同行） -->
        <div class="ds-basic-row">
          <n-form-item :label="t('pages.settings.DynamicStrategy.s4')" required class="ds-name-item">
            <n-input
              v-model:value="form.strategy_name"
              :placeholder="t('pages.settings.DynamicStrategy.s4')"
              :disabled="!!editingCode"
            />
          </n-form-item>
          <div class="status-row">
            <n-switch v-model:value="statusSwitch" />
            <span class="status-text" :class="{ off: !statusSwitch }">
              {{ statusSwitch ? t('pages.settings.DynamicStrategy.s17') : t('pages.settings.DynamicStrategy.s18') }}
            </span>
          </div>
        </div>

        <!-- 描述 -->
        <n-form-item :label="t('pages.settings.DynamicStrategy.s6')" class="ds-desc-item">
          <n-input
            v-model:value="form.description"
            type="textarea"
            :rows="2"
            :placeholder="t('pages.settings.DynamicStrategy.s6')"
          />
        </n-form-item>

        <!-- 生效模块 -->
        <section class="ds-section">
          <h2 class="ds-section-title">{{ t('pages.settings.DynamicStrategy.s7') }}</h2>
          <div v-if="!form.governed_functions.length" class="ds-hint">
            {{ t('pages.settings.DynamicStrategy.s41') }}
          </div>
          <n-checkbox-group
            v-else
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

        <!-- 权限与规则配置卡片（每勾选模块一行） -->
        <section class="ds-section">
          <div v-if="!moduleConfigCards.length" class="ds-hint">
            {{ t('pages.settings.DynamicStrategy.s41') }}
          </div>
          <div v-else class="ds-mod-cards">
            <div
              v-for="card in moduleConfigCards"
              :key="card.key"
              class="ds-mod-card"
            >
              <div class="ds-mod-info">
                <span class="ds-mod-name">{{ card.label }}</span>
                <span class="ds-mod-summary" :class="card.summaryClass">{{ card.summary }}</span>
              </div>
              <n-button size="small" secondary type="primary" @click="openModuleConfig(card.key)">
                {{ t('pages.settings.DynamicStrategy.s24') }}
              </n-button>
            </div>
          </div>
        </section>
      </div>
      <template #footer>
        <div class="modal-footer">
          <n-button v-if="editingCode" type="error" quaternary @click="onDeleteCurrent">
            {{ t('pages.settings.DynamicStrategy.s12') }}
          </n-button>
          <div class="spacer"></div>
          <n-button @click="goList">{{ t('pages.settings.DynamicStrategy.s11') }}</n-button>
          <n-button type="primary" :loading="saving" @click="onSave">
            {{ t('pages.settings.DynamicStrategy.s10') }}
          </n-button>
        </div>
      </template>
    </n-modal>

    <!-- 配置权限与规则弹窗（每模块独立；维度/属性字段由 options 按模块下发） -->
    <StrategyModuleConfigModal
      :show="configModalShow"
      :module-key="configModuleKey"
      :module-name="configModuleName"
      :dimensions="configModuleView.dimensions"
      :attribute-fields="configModuleView.attributeFields"
      :governed-resources="configGovernedResources"
      :initial-resource-codes="configInitialResourceCodes"
      :initial-groups="configInitialGroups"
      :initial-expr="configInitialExpr"
      @update:show="(v: boolean) => (configModalShow = v)"
      @apply="onConfigApply"
    />
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { h, ref, reactive, computed, onMounted } from 'vue'
import {
  NButton, NDataTable, NInput, NSwitch, NCheckboxGroup, NCheckbox,
  NTag, NSpace, NForm, NFormItem, NEmpty, NPopconfirm, NIcon, NModal,
  useMessage, useDialog,
  type DataTableColumns,
} from 'naive-ui'
import { SearchOutline, AddOutline } from '@vicons/ionicons5'
import StrategyModuleConfigModal from '@/pages/settings/StrategyModuleConfigModal.vue'
import {
  listStrategies, getStrategyOptions, createStrategy, updateStrategy, deleteStrategy,
  type DynamicStrategy, type StrategyModuleConfig, type StrategyOptions,
  type StrategyModuleOption, type StrategyGovernedResource,
} from '@/api/dynamicStrategy'
import type {
  PermConditionGroup, DimensionMeta, AttributeField,
} from '@/api/data-permission'
import { column, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns'
import { remotePagination } from '@/composables/useTablePagination'

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

/**
 * 策略模块 key → 资源 module（资源码第 2 段）**集合**映射。
 *
 * 用途：`granted_resource_codes` 是**扁平**的全局资源码数组，不带模块归属；
 * 弹窗按模块编辑时，必须知道「哪些旧码属于当前模块」才能做替换式合并
 * （否则 A 模块保存会把 B 模块的码抹掉）。
 * 判定方式：资源码形如 `recruit:{module}:...`，取第 2 段，看是否落在右侧集合内。
 *
 * 🔴 **必须是 1:N**：业务分组口径 ≠ 资源 module 口径。兵哥清单把「安排面试」
 *    （`recruit:interview:schedule`，module=interview）、「推进流程」
 *    （`recruit:application:advance`，module=application）与「放入人才库」
 *    （`recruit:talent_pool:create`，module=talent_pool）都归在**候选人管理**下，
 *    但它们不属于 `candidate` 这个资源 module。若按 1:1 硬配一对，这三条码
 *    既切不进弹窗初始值（开弹窗漏勾），也删不掉旧值（重复堆积）。
 *
 * 🔴 本表是**动态策略专用**的，与角色数据权限的 `DATA_PERM_MODULE_RESOURCE_MODULES`
 *    是两张表 —— 后者被 featureGranted 复用、波及所有角色，不能为弹窗改它。
 *    与后端同名常量 `STRATEGY_MODULE_RESOURCE_MODULES` 互为镜像，
 *    改一侧必须同步另一侧，否则「勾了却判不出归属 → 保存后丢失」。
 */
const STRATEGY_MODULE_RESOURCE_MODULES: Record<string, string[]> = {
  demand: ['demand'],
  process: ['settings'],
  position: ['position'],
  candidate: ['candidate', 'interview', 'application', 'talent_pool'],
  // talent 策略模块当前无受管控资源（talent_pool:create 已并入 candidate）
  talent: [],
}

/** 取资源码的 module 段（第 2 段）；不规范的资源码返回空串 */
function resourceModuleOf(resourceCode: string): string {
  return (resourceCode || '').split(':')[1] ?? ''
}

/**
 * 该资源码是否归属于指定策略模块。
 * 未登记的 module key 兜底为 `[key]`（保持旧行为，不至于把已知码判成无归属）。
 */
function belongsToStrategyModule(resourceCode: string, moduleKey: string): boolean {
  const mods = STRATEGY_MODULE_RESOURCE_MODULES[moduleKey] ?? [moduleKey]
  return mods.includes(resourceModuleOf(resourceCode))
}

// ===== 视图模式 =====
type Mode = 'list' | 'edit'
const mode = ref<Mode>('list')
const editingCode = ref<string | null>(null)
const saving = ref(false)

// ===== 列表（乙系：panel-shell + toolbar + table-wrap + flex-height + remotePagination）=====
const list = ref<DynamicStrategy[]>([])
const loading = ref(false)
const searchKeyword = ref('')
const page = ref(1)
const pageSize = ref(50)
const itemCount = ref(0)

const pagination = remotePagination({
  page,
  itemCount,
  pageSize,
  onPageSizeChange: () => { loadList() },
})

async function loadList() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize.value }
    const kw = searchKeyword.value.trim()
    if (kw) params.search = kw
    const res = await listStrategies(params)
    list.value = res.items
    itemCount.value = res.total
  } catch (e: any) {
    list.value = []
    message.error(e?.response?.data?.message || e?.message || t('pages.settings.DynamicStrategy.s1'))
  } finally {
    loading.value = false
  }
}

function onPageChange(p: number) {
  page.value = p
  loadList()
}
function onSearchChange() {
  page.value = 1
  loadList()
}

const columns = computed<DataTableColumns<DynamicStrategy>>(() => [
  column({
    title: () => t('pages.settings.DynamicStrategy.s4'),
    key: 'strategyName',
    render: (row: DynamicStrategy) => row.strategyName,
  }, 'short'),
  column({
    title: () => t('pages.settings.DynamicStrategy.s5'),
    key: 'status',
    render: (row: DynamicStrategy) =>
      h(
        NTag,
        { type: row.status === 1 ? 'success' : 'default', size: 'small', bordered: false },
        { default: () => (row.status === 1 ? t('pages.settings.DynamicStrategy.s17') : t('pages.settings.DynamicStrategy.s18')) },
      ),
  }, 'control'),
  column({
    title: () => t('pages.settings.DynamicStrategy.s16'),
    key: 'governedCount',
    render: (row: DynamicStrategy) => `${row.governedFunctions?.length ?? 0}`,
  }, 'numeric'),
  column({
    title: '操作',
    key: 'actions',
    render: (row: DynamicStrategy) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: OP_ACTION_BUTTON_SIZE, quaternary: true, onClick: () => openEdit(row) }, { default: () => t('pages.settings.DynamicStrategy.s3') }),
          h(NPopconfirm, {
            onPositiveClick: () => onDelete(row),
            positiveText: t('pages.settings.DynamicStrategy.s12'),
            negativeText: t('pages.settings.DynamicStrategy.s11'),
          }, {
            default: () => t('pages.settings.DynamicStrategy.s13'),
            trigger: () => h(NButton, { size: OP_ACTION_BUTTON_SIZE, quaternary: true, type: 'error' }, { default: () => t('pages.settings.DynamicStrategy.s12') }),
          }),
        ],
      }),
  }, 'control'),
])

// ===== 表单状态（本地 snake_case，buildPayload 时转为 camelCase 出参）=====
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

// ===== 每模块配置卡片（编辑弹窗内：摘要 + 配置权限与规则入口）=====
const moduleConfigCards = computed(() =>
  form.governed_functions.map((key) => {
    const label = MODULE_LABELS[key] || key
    const cfg = form.module_config[key]
    const actionCount = cfg?.actions?.length ?? 0
    const groupCount = cfg?.groups?.length ?? 0
    let summary: string
    let summaryClass = ''
    if (actionCount === 0 && groupCount === 0) {
      summary = t('pages.settings.DynamicStrategy.s40')
      summaryClass = 'is-empty'
    } else {
      const parts: string[] = []
      if (actionCount > 0) parts.push(t('pages.settings.DynamicStrategy.s38', { n: actionCount }))
      if (groupCount > 0) parts.push(t('pages.settings.DynamicStrategy.s39', { m: groupCount }))
      summary = parts.join(' · ')
      summaryClass = 'is-set'
    }
    return { key, label, summary, summaryClass }
  }),
)

function onGovernedChange(vals: string[]) {
  // 保留已配置模块的 module_config，仅同步勾选集合（不自动建默认配置，避免误锁写范围）
  const kept = new Set(vals)
  for (const k of Object.keys(form.module_config)) {
    if (!kept.has(k)) delete form.module_config[k]
  }
  form.governed_functions = vals
}

// ===== 配置权限与规则弹窗（每模块独立）=====
const configModalShow = ref(false)
const configModuleKey = ref('')
const configModuleName = computed(() => MODULE_LABELS[configModuleKey.value] || configModuleKey.value)
const configInitialGroups = ref<PermConditionGroup[]>([])
/**
 * 打开弹窗时的组间组合表达式（scope 模式生效；留空 = 或 OR）。
 * 与 configInitialResourceCodes 同 pattern：computed 随 configModuleKey
 * （openModuleConfig 里赋值）联动取数，缺省兜底空串。
 * 🔴 2026-10-20 前这里没有回填链路，弹窗又恒写 expr=''，导致已配置的
 *    组间关系每次保存都被抹回「或」——表达式能力等于不存在。
 */
const configInitialExpr = computed<string>(
  () => form.module_config[configModuleKey.value]?.expr ?? '',
)
const configModuleView = computed(() => moduleView(configModuleKey.value))

/** 当前模块的「受限功能」候选资源（后端按策略模块分组，缺省兜底空数组） */
const configGovernedResources = computed<StrategyGovernedResource[]>(
  () => options.value.governedResources?.[configModuleKey.value] ?? [],
)

/**
 * 打开弹窗时的已选资源码 = granted_resource_codes 中归属当前模块的那部分。
 *
 * ⚠️ 存量策略的 `module_config[key].actions` 是旧契约（动作 key），与资源码不是同一
 *    个值域，**不能**回填到资源复选框里（会出现「勾选项不在候选里」的脏状态）。
 *
 * ⚠️ 必须用集合归属判断而非等值判断：候选人模块下挂着 interview / application 两个
 *    资源 module，按 `=== 'candidate'` 切会把已选的安排面试、推进流程漏掉 → 开弹窗丢勾。
 */
const configInitialResourceCodes = computed<string[]>(() => {
  const key = configModuleKey.value
  if (!key) return []
  return form.granted_resource_codes.filter((code) => belongsToStrategyModule(code, key))
})

function openModuleConfig(key: string) {
  configModuleKey.value = key
  const cfg = form.module_config[key] ?? defaultModuleConfig()
  configInitialGroups.value = (cfg.groups || []).map((g) => ({
    ...g,
    conditions: g.conditions.map((c) => ({ ...c })),
  }))
  // configInitialExpr 是 computed（随上面赋的 configModuleKey 联动），无需在此赋值
  configModalShow.value = true
}

function onConfigApply(payload: { resourceCodes: string[]; groups: PermConditionGroup[]; expr: string }) {
  const key = configModuleKey.value
  if (!form.module_config[key]) form.module_config[key] = defaultModuleConfig()

  // ===== 资源码按模块做替换式合并 =====
  // granted_resource_codes 是跨模块的扁平数组，故先剔除「属于当前模块」的旧码，
  // 再并入本次新选 —— 直接整体覆盖会把其它模块勾的码抹掉（多模块策略必踩）。
  //
  // ⚠️ 剔除必须按「是否落在当前模块的资源 module 集合内」判断，不能按单个 module 等值：
  //    candidate 模块同时含 interview / application 两个资源 module，等值剔除会把
  //    「安排面试 / 推进流程」的旧码留在数组里 → 取消勾选删不掉、反复保存重复堆积。
  const mods = STRATEGY_MODULE_RESOURCE_MODULES[key]
  if (mods) {
    const next = payload.resourceCodes.map(String)
    form.granted_resource_codes = [
      ...form.granted_resource_codes.filter((code) => !mods.includes(resourceModuleOf(code))),
      ...next,
    ]
  }

  // groups 仍写 module_config；mode 仍按条件组推导（buildPayload 会把两者都出参）
  form.module_config[key].groups = payload.groups.map((g) => ({ ...g }))
  // mode 由条件组推导：有条件组 → scope（自定义范围）；否则 → all（全部可写）。
  // 严禁 scope 空组：空组在后端编译为 Q(pk__in=[]) 全拒。
  form.module_config[key].mode = payload.groups.length > 0 ? 'scope' : 'all'
  // 组间组合表达式原样回写（弹窗手填，留空 = 或 OR）。
  // 🔴 2026-10-20 前此处恒写 ''（抹数据）：用户配好的「且」关系每次保存都被打回「或」，
  //    既丢配置又是放大权限的静默错误；后端 compile_scope_q 的两级表达式能力被整体旁路。
  form.module_config[key].expr = payload.expr ?? ''
  // 🔴 module_config[key].actions 不再写入：受限功能已改为资源粒度（granted_resource_codes）
  configModalShow.value = false
}

// ===== 选项（动作字典 / 预设包 / 模块×维度×属性字段）=====
const options = ref<StrategyOptions>({ modules: [], actions: [], presets: [] })
async function loadOptions() {
  try {
    options.value = await getStrategyOptions()
  } catch {
    options.value = { modules: [], actions: [], presets: [] }
  }
}

// ===== 模块视图（维度/属性字段由 options 按模块下发）=====
function moduleView(key: string): { label: string; dimensions: DimensionMeta[]; attributeFields: AttributeField[] } {
  const opt: StrategyModuleOption | undefined = options.value.modules.find((o) => (o.moduleKey ?? o.key) === key)
  const meta = MODULE_LABELS[key] || key
  return {
    label: opt?.label || meta,
    dimensions: opt?.dimensions || [],
    attributeFields: opt?.attributeFields || [],
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
  mode.value = 'edit'
  await loadOptions()
}

async function openEdit(row: DynamicStrategy) {
  editingCode.value = row.strategyCode
  form.strategy_code = row.strategyCode
  form.strategy_name = row.strategyName
  form.status = row.status
  form.description = row.description ?? ''
  form.governed_functions = [...(row.governedFunctions || [])]
  form.granted_resource_codes = [...(row.grantedResourceCodes || [])]
  form.module_config = {}
  for (const k of form.governed_functions) {
    const cfg = row.moduleConfig?.[k]
    form.module_config[k] = cfg
      ? { mode: cfg.mode, expr: cfg.expr, groups: cfg.groups ? cfg.groups.map((g) => ({ ...g })) : [], actions: [...cfg.actions] }
      : defaultModuleConfig()
  }
  mode.value = 'edit'
  await loadOptions()
}

function buildPayload(): Record<string, unknown> {
  const moduleConfig: Record<string, StrategyModuleConfig> = {}
  for (const k of form.governed_functions) {
    moduleConfig[k] = form.module_config[k] ?? defaultModuleConfig()
  }
  return {
    strategyCode: form.strategy_code,
    strategyName: form.strategy_name,
    status: form.status,
    description: form.description,
    governedFunctions: [...form.governed_functions],
    grantedResourceCodes: [...form.granted_resource_codes],
    moduleConfig,
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
      if (!payload.strategyCode) payload.strategyCode = `STRAT_${Date.now()}`
      await createStrategy(payload)
      message.success(t('pages.settings.DynamicStrategy.s19'))
    }
    mode.value = 'list'
    editingCode.value = null
    page.value = 1
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
  loadList()
}

// ===== 删除 =====
// 列表行删除：NPopconfirm 已是唯一确认层，此处直接执行删除（不再二次 dialog）。
async function onDelete(row: DynamicStrategy) {
  try {
    await deleteStrategy(row.strategyCode)
    message.success(t('pages.settings.DynamicStrategy.s23'))
    await loadList()
  } catch (e: any) {
    message.error(e?.response?.data?.message || e?.message || t('pages.settings.DynamicStrategy.s12'))
  }
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
        message.success(t('pages.settings.DynamicStrategy.s23'))
        mode.value = 'list'
        editingCode.value = null
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
/* 页面布局三件套（与 DepartmentManagement 同款）：页头固定 + 内容区自滚 */
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
.page-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--ink-faint);
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/* 列表：乙系 panel-shell + toolbar + table-wrap（结构同 DepartmentManagement） */
.glass-panel.panel-shell {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.table-wrap {
  flex: 1;
  min-height: 0;
}
.ds-search { width: 240px; }

/* 表单面板（置于详情弹窗内；弹窗 content-style 已提供内边距） */
.ds-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.modal-footer {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.modal-footer .spacer { flex: 1; }
.ds-section { display: flex; flex-direction: column; gap: var(--space-2); }
.ds-section-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}
.ds-basic-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: flex-end;
  gap: var(--space-4);
}
.ds-name-item { margin-bottom: 0; }
.ds-desc-item { margin-bottom: 0; }
.status-row { display: flex; align-items: center; gap: var(--space-2); padding-bottom: 6px; }
.status-text { font-size: 13px; color: var(--c-success-deep); }
.status-text.off { color: var(--ink-faint); }

.ds-module-check { font-size: 14px; }

.ds-hint {
  font-size: 13px;
  color: var(--ink-faint);
  padding: var(--space-2) 0;
}

/* 权限与规则配置卡片 */
.ds-mod-cards {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.ds-mod-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  background: var(--surface);
  border: 1px solid var(--border-hairline, #e2e8f0);
  border-radius: 12px;
  padding: 12px 16px;
}
.ds-mod-info { display: flex; align-items: center; gap: var(--space-3); min-width: 0; }
.ds-mod-name { font-size: 15px; font-weight: 600; color: var(--ink); }
.ds-mod-summary { font-size: 13px; color: var(--ink-faint); }
.ds-mod-summary.is-set { color: var(--ink-soft); }
.ds-mod-summary.is-empty { color: var(--ink-faint); }
</style>
