<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">校招管控</h1>
        <p class="page-subtitle">人员比例管控系统 v2.1 · 规则自带适用范围(全局/部门/职务/职级) · 维度 / 指标 / 规则(100% 加和) / 年度·月度目标</p>
      </div>
      <n-space v-if="scopeScoped" align="center" style="flex-shrink: 0">
        <span class="scope-label">适用范围</span>
        <n-switch v-model:value="isGlobal" @update:value="onGlobalChange">
          <template #checked>全局</template>
          <template #unchecked>指定</template>
        </n-switch>
        <template v-if="!isGlobal">
          <n-select v-model:value="scopeBu" :options="deptOptions" placeholder="部门" style="width: 130px" @update:value="onScopeChange" />
          <n-select v-model:value="scopePosition" :options="positionOptions" placeholder="职务(不限)" clearable style="width: 140px" @update:value="onScopeChange" />
          <n-select v-model:value="scopeLevel" :options="levelOptions" placeholder="职级(不限)" clearable style="width: 140px" @update:value="onScopeChange" />
        </template>
      </n-space>
    </div>

    <n-card :bordered="false" class="content-card">
      <n-tabs v-model:value="activeTab" type="line" @update:value="onTabChange">
        <!-- ===================== 实时看板 ===================== -->
        <n-tab-pane name="ratio" tab="实时看板">
          <n-alert v-if="!scopeOk" type="warning" :show-icon="true" style="margin-bottom: 12px">
            当前适用范围存在维度目标占比未加和到 100% 的项，请前往「规则与目标配置」补全。
          </n-alert>
          <div class="kpi-row">
            <div class="kpi-card"><span class="kpi-label">计入核算人数</span><span class="kpi-value">{{ ratioData.total }}</span></div>
            <div class="kpi-card"><span class="kpi-label">管控规则数</span><span class="kpi-value">{{ ratioData.rows.length }}</span></div>
            <div class="kpi-card danger"><span class="kpi-label">硬约束超标</span><span class="kpi-value">{{ ratioKpi.hard }}</span></div>
            <div class="kpi-card warn"><span class="kpi-label">软/仅提示超标</span><span class="kpi-value">{{ ratioKpi.soft }}</span></div>
          </div>
          <n-data-table
            :columns="ratioColumns"
            :data="ratioData.rows"
            :loading="loading.ratio"
            :row-key="(r: any) => r.bu + '|' + r.dimension + '|' + r.indicator"
            :pagination="false"
          >
            <template #empty><n-empty description="暂无数据" /></template>
          </n-data-table>
        </n-tab-pane>

        <!-- ===================== 人数规划（计算看板） ===================== -->
        <n-tab-pane name="plan" tab="人数规划">
          <div class="filter-row">
            <n-space>
              <n-input-number v-model:value="selectedYear" :min="2020" :max="2100" style="width: 120px" @update:value="loadPlan" />
              <n-select v-model:value="planMonth" :options="monthOptions" style="width: 140px" @update:value="loadPlan" />
            </n-space>
          </div>
          <div class="kpi-row">
            <div class="kpi-card"><span class="kpi-label">本月总缺口</span><span class="kpi-value">{{ planData.kpi.monthGap }}</span></div>
            <div class="kpi-card"><span class="kpi-label">管控规则数</span><span class="kpi-value">{{ planData.kpi.ruleCount }}</span></div>
            <div class="kpi-card danger"><span class="kpi-label">硬约束超标</span><span class="kpi-value">{{ planData.kpi.hardViolationCount }}</span></div>
            <div class="kpi-card warn"><span class="kpi-label">软/仅提示超标</span><span class="kpi-value">{{ planData.kpi.warnCount }}</span></div>
          </div>
          <n-data-table
            :columns="planColumns"
            :data="planData.rows"
            :loading="loading.plan"
            :row-key="(r: any) => r.dimension + '|' + r.indicator"
            :pagination="false"
          >
            <template #empty><n-empty description="暂无数据" /></template>
          </n-data-table>
        </n-tab-pane>

        <!-- ===================== 规则与目标配置（适用范围 + 规则 + 目标 三合一） ===================== -->
        <n-tab-pane name="rules" tab="规则与目标配置">
          <div class="filter-row">
            <n-space align="center">
              <n-input-number v-model:value="targetYear" :min="2020" :max="2100" style="width: 120px" @update:value="loadUnified" />
              <n-tag size="small" :bordered="false" type="info">适用范围：{{ scopeLabel }}</n-tag>
            </n-space>
          </div>

          <div class="dim-filter-row">
            <span
              v-for="d in dimFilterOptions"
              :key="d.value"
              class="dim-tag"
              :class="{ active: dimFilter === d.value, ok: d.ok, bad: d.ok === false }"
              @click="dimFilter = d.value"
            >
              {{ d.label }}
              <span class="dim-sum">{{ d.sumText }}</span>
            </span>
          </div>

          <n-data-table
            :columns="unifiedColumns"
            :data="filteredUnifiedRows"
            :loading="loading.unified"
            :row-key="(r: any) => r.indicatorId"
            :pagination="false"
          >
            <template #empty><n-empty description="该维度下暂无指标，请先到「指标管理」配置指标" /></template>
          </n-data-table>

          <n-space justify="end" style="margin-top: 12px">
            <n-button :loading="loading.saveTargets" @click="saveTargets">保存目标</n-button>
            <n-button type="primary" :loading="loading.saveRules" @click="saveRules">批量保存规则</n-button>
          </n-space>
        </n-tab-pane>

        <!-- ===================== 指标管理（维度+指标扁平化） ===================== -->
        <n-tab-pane name="indicators" tab="指标管理">
          <div class="filter-row">
            <n-space>
              <n-select v-model:value="indicatorDimFilter" :options="dimOptions" placeholder="全部维度" style="width: 180px" clearable />
              <n-button type="primary" @click="openAddIndicator">+ 新增指标</n-button>
              <n-button @click="dimDrawerShow = true">管理维度</n-button>
            </n-space>
          </div>
          <n-data-table
            :columns="indicatorColumns"
            :data="filteredIndicators"
            :loading="loading.indicators"
            :row-key="(r: any) => r.id"
            :pagination="false"
          >
            <template #empty><n-empty description="暂无指标" /></template>
          </n-data-table>
        </n-tab-pane>

        <!-- ===================== 录入校验 ===================== -->
        <n-tab-pane name="validate" tab="录入校验">
          <n-grid :cols="4" :x-gap="16" :y-gap="12" item-responsive responsive="screen">
            <n-gi span="4 m:1"><n-form-item label="人员编码" label-placement="top"><n-input v-model:value="draft.code" placeholder="如 P032" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item label="姓名" label-placement="top"><n-input v-model:value="draft.name" placeholder="如 员工32" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item label="部门" label-placement="top"><n-select v-model:value="draft.bu" :options="deptOptions" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item label="职务" label-placement="top"><n-select v-model:value="draft.position" :options="positionOptions" clearable placeholder="不限" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item label="职级" label-placement="top"><n-select v-model:value="draft.level" :options="levelOptions" clearable placeholder="不限" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item label="院校标签" label-placement="top"><n-select v-model:value="draft.school" :options="schoolOptions" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item label="性别" label-placement="top"><n-select v-model:value="draft.sex" :options="sexOptions" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item label="专业标签" label-placement="top"><n-select v-model:value="draft.major" :options="majorOptions" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item label="招聘月份" label-placement="top"><n-select v-model:value="draft.month" :options="monthOptions" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item label="状态" label-placement="top"><n-select v-model:value="draft.status" :options="statusOptions" /></n-form-item></n-gi>
          </n-grid>
          <n-space>
            <n-button type="primary" :loading="loading.validate" @click="runValidate">校验判定</n-button>
            <n-button :disabled="!canConfirmEntry" @click="confirmEntry">确认录入为人员</n-button>
          </n-space>

          <div v-if="validation" class="validate-result">
            <n-tag :type="verdictType(validation.verdict)" size="large" :bordered="false">
              {{ validation.verdict }}
            </n-tag>
            <p v-if="validation.verdict === '❌ 阻断提交'" class="block-hint">
              命中硬约束超标，系统已阻断提交。请调整候选人标签或目标配置后再试。
            </p>
            <n-data-table
              :columns="checkColumns"
              :data="validation.checks"
              :row-key="(r: any) => r.dimension + '|' + r.indicator + '|' + r.bu"
              :pagination="false"
              style="margin-top: 12px"
            >
              <template #empty><n-empty description="无校验明细" /></template>
            </n-data-table>
          </div>
        </n-tab-pane>

        <!-- ===================== 人员数据 ===================== -->
        <n-tab-pane name="persons" tab="人员数据">
          <div class="toolbar">
            <n-button type="primary" @click="openAddPerson">+ 新增人员</n-button>
          </div>
          <n-data-table
            :columns="personColumns"
            :data="persons"
            :loading="loading.persons"
            :row-key="(r: any) => r.id"
            :pagination="false"
          >
            <template #empty><n-empty description="暂无人员" /></template>
          </n-data-table>
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <!-- 维度管理（抽屉） -->
    <n-drawer v-model:show="dimDrawerShow" :width="480" placement="right">
      <n-drawer-content title="维度管理" closable>
        <n-data-table
          :columns="dimDrawerColumns"
          :data="dimensions"
          :loading="loading.dimensions"
          :row-key="(r: any) => r.id"
          :pagination="false"
          size="small"
        >
          <template #empty><n-empty description="暂无维度" /></template>
        </n-data-table>
      </n-drawer-content>
    </n-drawer>

    <!-- 指标表单弹窗 -->
    <n-modal v-model:show="indicatorModal.show" :title="indicatorModal.editingId ? '编辑指标' : '新增指标'" preset="card" style="width: 420px">
      <n-form label-placement="top">
        <n-form-item label="所属维度"><n-select v-model:value="indicatorModal.dimension" :options="dimOptions" :disabled="!!indicatorModal.editingId" /></n-form-item>
        <n-form-item label="指标名称"><n-input v-model:value="indicatorModal.name" placeholder="如 985 / 男 / 工学" /></n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="indicatorModal.show = false">取消</n-button>
          <n-button type="primary" :loading="loading.indicators" @click="saveIndicator">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 12 月度目标弹窗（年度 + 12 月） -->
    <n-modal v-model:show="monthlyModal.show" :title="`${monthlyModal.indicatorName} · ${targetYear} 年度目标`" preset="card" style="width: 680px">
      <n-form label-placement="top">
        <n-form-item label="年度目标人数"><n-input-number v-model:value="monthlyModal.annualTarget" :min="0" style="width: 100%" /></n-form-item>
        <n-divider>12 个月目标（单位：人）</n-divider>
        <n-grid :cols="4" :x-gap="8" :y-gap="8">
          <n-gi v-for="(_, i) in 12" :key="i">
            <n-form-item :label="ALL_MONTHS[i]" label-placement="top">
              <n-input-number v-model:value="monthlyModal.monthly[i]" :min="0" style="width: 100%" />
            </n-form-item>
          </n-gi>
        </n-grid>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="monthlyModal.show = false">取消</n-button>
          <n-button type="primary" @click="applyMonthly">确定</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 人员弹窗 -->
    <n-modal v-model:show="personModal.show" :title="personModal.editingId ? '编辑人员' : '新增人员'" preset="card" style="width: 520px">
      <n-form label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-gi><n-form-item label="人员编码"><n-input v-model:value="personModal.code" placeholder="如 P032" /></n-form-item></n-gi>
          <n-gi><n-form-item label="姓名"><n-input v-model:value="personModal.name" placeholder="如 员工32" /></n-form-item></n-gi>
          <n-gi><n-form-item label="部门"><n-select v-model:value="personModal.bu" :options="deptOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item label="院校标签"><n-select v-model:value="personModal.school" :options="schoolOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item label="性别"><n-select v-model:value="personModal.sex" :options="sexOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item label="专业标签"><n-select v-model:value="personModal.major" :options="majorOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item label="招聘月份"><n-select v-model:value="personModal.month" :options="monthOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item label="状态"><n-select v-model:value="personModal.status" :options="statusOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item label="职务"><n-select v-model:value="personModal.position" :options="positionOptions" clearable placeholder="不限" /></n-form-item></n-gi>
          <n-gi><n-form-item label="职级"><n-select v-model:value="personModal.level" :options="levelOptions" clearable placeholder="不限" /></n-form-item></n-gi>
          <n-gi><n-form-item label="计入核算"><n-switch v-model:value="personModal.counted" /></n-form-item></n-gi>
        </n-grid>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="personModal.show = false">取消</n-button>
          <n-button type="primary" :loading="loading.persons" @click="savePerson">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h, onMounted } from 'vue'
import {
  NTag, NButton, NSpace, NSwitch, NDivider, NDrawer, NDrawerContent,
  NInputNumber, NSelect,
  useMessage, useDialog, type DataTableColumns,
} from 'naive-ui'
import { extractApiError } from '../../api/dynamic-field'
import {
  listDimensions, createDimension, updateDimension, deleteDimension,
  listIndicators, createIndicator, updateIndicator, deleteIndicator,
  listRules, batchSaveRules,
  getRatio, getPlan, validateDraft,
  listHeadcounts, upsertHeadcount, deleteHeadcount,
  listPersons, upsertPerson, deletePerson,
  DEPTS, SCHOOLS, MAJORS, SEXES, ALL_MONTHS, DIMS, STRENGTH, STATUS, POSITIONS, LEVELS,
  type ScopeFilter, type ControlDimension, type ControlIndicator,
  type Person, type RatioRow, type RatioResult, type PlanRow, type PlanResult,
  type ValidationResult, type Strength, type RuleDraft,
} from '../../api/campusControl'

const message = useMessage()
const dialog = useDialog()

/* ============================ 选项 ============================ */
const opt = (arr: readonly string[]) => arr.map((v) => ({ label: v, value: v }))
const deptOptions = opt(DEPTS)
const schoolOptions = opt(SCHOOLS)
const majorOptions = opt(MAJORS)
const sexOptions = opt(SEXES)
const monthOptions = opt(ALL_MONTHS)
const dimOptions = opt(DIMS)
const strengthOptions = opt(STRENGTH)
const statusOptions = opt(STATUS)
const positionOptions = opt(POSITIONS)
const levelOptions = opt(LEVELS)

/* ============================ 工具 ============================ */
const pct = (r: number, d = 1) => `${(r * 100).toFixed(d)}%`
const ratioStatusType = (s: string) => (s === '正常' ? 'success' : s === '高于上限' ? 'error' : 'warning')
const countStatusType = (s: string) => (s === '本月达标' ? 'success' : s === '缺口未达成' ? 'warning' : 'default')
const strengthType = (s: string) => (s === '硬约束' ? 'error' : s === '软约束' ? 'warning' : 'default')
const verdictType = (v: string) => (v.startsWith('❌') ? 'error' : v.startsWith('⚠️') ? 'warning' : 'success')

/* ============================ 全局状态 ============================ */
const activeTab = ref('ratio')
const loading = reactive({
  ratio: false, plan: false, unified: false, saveRules: false, saveTargets: false,
  dimensions: false, indicators: false, persons: false, validate: false,
})
const dimensions = ref<ControlDimension[]>([])
const indicators = ref<ControlIndicator[]>([])
const persons = ref<Person[]>([])

const selectedYear = ref(2026)
const planMonth = ref('8月')
const targetYear = ref(2026)

/* ============================ 适用范围 ============================ */
const isGlobal = ref(true)
const scopeBu = ref('')
const scopePosition = ref('')
const scopeLevel = ref('')
const currentScope = computed<ScopeFilter>(() => ({
  bu: isGlobal.value ? '' : scopeBu.value,
  position: isGlobal.value ? '' : scopePosition.value,
  level: isGlobal.value ? '' : scopeLevel.value,
}))
const scopeLabel = computed(() => {
  if (isGlobal.value) return '全局'
  const parts = [scopeBu.value, scopePosition.value || '职务不限', scopeLevel.value || '职级不限']
  return parts.filter(Boolean).join(' · ')
})
const scopeScoped = computed(() => ['ratio', 'plan', 'rules'].includes(activeTab.value))

/* ============================ 实时看板 ============================ */
const ratioData = ref<RatioResult>({ total: 0, rows: [], sumChecks: [] })
const ratioKpi = computed(() => {
  const rows = ratioData.value.rows
  return {
    hard: rows.filter((r) => r.status !== '正常' && r.strength === '硬约束').length,
    soft: rows.filter((r) => r.status !== '正常' && r.strength !== '硬约束').length,
  }
})
const scopeOk = computed(() => ratioData.value.sumChecks.every((s) => s.ok))

/* ============================ 人数规划 ============================ */
const planData = ref<PlanResult>({
  rows: [],
  kpi: { total: 0, ruleCount: 0, warnCount: 0, hardViolationCount: 0, monthGap: 0 },
  year: 2026,
})

/* ============================ 统一规则与目标配置 ============================ */
interface UnifiedRow {
  indicatorId: string
  dimensionId: string
  dimensionName: string
  indicatorName: string
  targetPct: number
  loPct: number
  hiPct: number
  strength: Strength
  headcountId: string | null
  annualTarget: number
  monthlyTargets: number[]
}
const unifiedRows = ref<UnifiedRow[]>([])
const dimFilter = ref<string>('all')

const dimFilterOptions = computed(() => {
  const all: { value: string; label: string; ok?: boolean; sumText: string }[] = [
    { value: 'all', label: '全部', sumText: `${unifiedRows.value.length} 项` },
  ]
  for (const d of dimensions.value) {
    const rows = unifiedRows.value.filter((r) => r.dimensionId === d.id)
    const sum = rows.reduce((s, r) => s + (Number(r.targetPct) || 0), 0)
    const ok = Math.abs(sum - 100) < 0.05
    all.push({ value: d.id, label: d.name, ok, sumText: `${sum.toFixed(1)}%` })
  }
  return all
})

const filteredUnifiedRows = computed(() => {
  if (dimFilter.value === 'all') return unifiedRows.value
  return unifiedRows.value.filter((r) => r.dimensionId === dimFilter.value)
})

/* ============================ 指标管理 ============================ */
const indicatorDimFilter = ref<string | null>(null)
const filteredIndicators = computed(() => {
  if (!indicatorDimFilter.value) return indicators.value
  return indicators.value.filter((i) => i.dimension === indicatorDimFilter.value)
})

/* ============================ 加载 ============================ */
async function loadDimensions() {
  loading.dimensions = true
  try { dimensions.value = await listDimensions() }
  catch (e) { message.error(extractApiError(e, '加载维度失败')) }
  finally { loading.dimensions = false }
}
async function loadIndicators() {
  loading.indicators = true
  try { indicators.value = await listIndicators() }
  catch (e) { message.error(extractApiError(e, '加载指标失败')) }
  finally { loading.indicators = false }
}
async function loadPersons() {
  loading.persons = true
  try { persons.value = await listPersons() }
  catch (e) { message.error(extractApiError(e, '加载人员失败')) }
  finally { loading.persons = false }
}
async function loadRatio() {
  loading.ratio = true
  try { ratioData.value = await getRatio(currentScope.value) }
  catch (e) { message.error(extractApiError(e, '加载看板失败')) }
  finally { loading.ratio = false }
}
async function loadPlan() {
  loading.plan = true
  try { planData.value = await getPlan(currentScope.value, selectedYear.value, planMonth.value) }
  catch (e) { message.error(extractApiError(e, '加载规划失败')) }
  finally { loading.plan = false }
}
async function loadUnified() {
  loading.unified = true
  try {
    const [rules, headcounts] = await Promise.all([
      listRules(currentScope.value),
      listHeadcounts(currentScope.value, targetYear.value),
    ])
    const ruleByInd = new Map(rules.map((r) => [r.indicator, r]))
    const hcByInd = new Map(headcounts.map((h) => [h.indicator, h]))
    unifiedRows.value = indicators.value.map((ind) => {
      const r = ruleByInd.get(ind.id)
      const h = hcByInd.get(ind.id)
      return {
        indicatorId: ind.id,
        dimensionId: ind.dimension,
        dimensionName: ind.dimensionName,
        indicatorName: ind.name,
        targetPct: r ? Math.round(r.target * 1000) / 10 : 0,
        loPct: r ? Math.round(r.lo * 1000) / 10 : 0,
        hiPct: r ? Math.round(r.hi * 1000) / 10 : 0,
        strength: (r?.strength ?? '硬约束') as Strength,
        headcountId: h?.id ?? null,
        annualTarget: h?.annualTarget ?? 0,
        monthlyTargets: h ? [...h.monthlyTargets] : Array(12).fill(0),
      }
    })
  } catch (e) { message.error(extractApiError(e, '加载配置失败')) }
  finally { loading.unified = false }
}

function onGlobalChange(v: boolean) {
  if (!v && !scopeBu.value) scopeBu.value = DEPTS[0]
  onScopeChange()
}
function onScopeChange() {
  if (activeTab.value === 'ratio') loadRatio()
  else if (activeTab.value === 'plan') loadPlan()
  else if (activeTab.value === 'rules') loadUnified()
}
function onTabChange(name: string) {
  if (name === 'ratio') loadRatio()
  else if (name === 'plan') loadPlan()
  else if (name === 'rules') loadUnified()
  else if (name === 'persons') loadPersons()
  else if (name === 'indicators') loadIndicators()
}

/* ============================ 列定义 ============================ */
const ratioColumns: DataTableColumns<RatioRow> = [
  { title: '适用范围', key: 'bu', render: (r) => r.bu || '全局' },
  { title: '维度', key: 'dimension' },
  { title: '指标', key: 'indicator' },
  { title: '实际/分母', key: 'actual', render: (r) => `${r.actual} / ${r.denom}` },
  { title: '占比', key: 'ratio', render: (r) => h(NTag, { type: 'default', bordered: false }, { default: () => pct(r.ratio) }) },
  { title: '目标', key: 'target', render: (r) => pct(r.target) },
  { title: '下限', key: 'lo', render: (r) => pct(r.lo) },
  { title: '上限', key: 'hi', render: (r) => pct(r.hi) },
  { title: '状态', key: 'status', render: (r) => h(NTag, { type: ratioStatusType(r.status), bordered: false }, { default: () => r.status }) },
  { title: '控制强度', key: 'strength', render: (r) => h(NTag, { type: strengthType(r.strength), bordered: false }, { default: () => r.strength }) },
]

const planColumns: DataTableColumns<PlanRow> = [
  { title: '适用范围', key: 'bu', render: (r) => r.bu || '全局' },
  { title: '维度', key: 'dimension' },
  { title: '指标', key: 'indicator' },
  { title: '强度', key: 'strength', render: (r) => h(NTag, { type: strengthType(r.strength), bordered: false }, { default: () => r.strength }) },
  { title: '在职', key: 'onjob' },
  { title: '年度目标', key: 'annualTarget' },
  { title: '年度缺口', key: 'annualGap' },
  { title: '本月目标', key: 'monthTarget' },
  { title: '本月实际', key: 'monthActual' },
  { title: '缺口', key: 'gap' },
  { title: '状态', key: 'status', render: (r) => h(NTag, { type: countStatusType(r.status), bordered: false }, { default: () => r.status }) },
]

const renderPctInput = (key: 'targetPct' | 'loPct' | 'hiPct') => (row: UnifiedRow) =>
  h(NInputNumber, {
    value: row[key], min: 0, max: 100, step: 0.5, size: 'small', style: 'width: 88px', showButton: false,
    'onUpdate:value': (v: number | null) => { if (v != null) row[key] = v },
  })

const unifiedColumns: DataTableColumns<UnifiedRow> = [
  { title: '维度', key: 'dimensionName', width: 100 },
  { title: '指标', key: 'indicatorName', width: 100 },
  { title: '目标占比 %', key: 'targetPct', width: 110, render: renderPctInput('targetPct') },
  { title: '下限 %', key: 'loPct', width: 100, render: renderPctInput('loPct') },
  { title: '上限 %', key: 'hiPct', width: 100, render: renderPctInput('hiPct') },
  {
    title: '强度', key: 'strength', width: 110,
    render: (row) => h(NSelect, {
      value: row.strength, size: 'small', options: strengthOptions, style: 'width: 110px',
      'onUpdate:value': (v: string) => { row.strength = v as Strength },
    }),
  },
  {
    title: '年度目标', key: 'annualTarget', width: 130,
    render: (row) => h(NInputNumber, {
      value: row.annualTarget, min: 0, size: 'small', style: 'width: 120px', showButton: false,
      'onUpdate:value': (v: number | null) => { if (v != null) row.annualTarget = v },
    }),
  },
  { title: '月度合计', key: 'monthlySum', width: 90, render: (row) => row.monthlyTargets.reduce((a, b) => a + b, 0) },
  { title: '操作', key: 'actions', width: 120, fixed: 'right', render: (row) => h(NButton, { size: 'small', onClick: () => openMonthlyModal(row) }, { default: () => '编辑月度' }) },
]

const indicatorColumns: DataTableColumns<ControlIndicator> = [
  { title: '维度', key: 'dimensionName' },
  { title: '指标', key: 'name' },
  {
    title: '操作', key: 'actions',
    render: (r) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', onClick: () => openEditIndicator(r) }, { default: () => '编辑' }),
        h(NButton, { size: 'small', type: 'error', quaternary: true, onClick: () => removeIndicator(r) }, { default: () => '删除' }),
      ],
    }),
  },
]

const personColumns: DataTableColumns<Person> = [
  { title: '编码', key: 'code' }, { title: '姓名', key: 'name' }, { title: '部门', key: 'bu' },
  { title: '院校', key: 'school' }, { title: '性别', key: 'sex' }, { title: '专业', key: 'major' },
  { title: '月份', key: 'month' }, { title: '职务', key: 'position', render: (r) => r.position || '—' },
  { title: '职级', key: 'level', render: (r) => r.level || '—' },
  { title: '状态', key: 'status' },
  { title: '计入核算', key: 'counted', render: (r) => h(NTag, { type: r.counted ? 'success' : 'default', bordered: false }, { default: () => (r.counted ? '是' : '否') }) },
  {
    title: '操作', key: 'actions',
    render: (r) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', onClick: () => openEditPerson(r) }, { default: () => '编辑' }),
        h(NButton, { size: 'small', type: 'error', quaternary: true, onClick: () => removePerson(r) }, { default: () => '删除' }),
      ],
    }),
  },
]

const checkColumns: DataTableColumns<ValidationResult['checks'][number]> = [
  { title: '适用范围', key: 'bu', render: (r) => r.bu || '全局' },
  { title: '维度', key: 'dimension' }, { title: '指标', key: 'indicator' },
  { title: '强度', key: 'strength', render: (r) => h(NTag, { type: strengthType(r.strength), bordered: false }, { default: () => r.strength }) },
  { title: '占比', key: 'ratio', render: (r) => pct(r.ratio) },
  { title: '占比状态', key: 'ratioStatus', render: (r) => h(NTag, { type: ratioStatusType(r.ratioStatus), bordered: false }, { default: () => r.ratioStatus }) },
  { title: '本月实际', key: 'monthActual' }, { title: '本月目标', key: 'monthTarget' },
  { title: '人数状态', key: 'countStatus', render: (r) => h(NTag, { type: countStatusType(r.countStatus), bordered: false }, { default: () => r.countStatus }) },
]

/* ============================ 维度管理 ============================ */
const dimDrawerShow = ref(false)
const dimDrawerColumns: DataTableColumns<ControlDimension> = [
  { title: '维度', key: 'name' },
  { title: '编码', key: 'code', render: (r) => r.code || '—' },
  {
    title: '启用', key: 'isActive',
    render: (r) => h(NSwitch, {
      value: r.isActive,
      onUpdateValue: async (v: boolean) => {
        try { await updateDimension(r.id, { isActive: v }); r.isActive = v; message.success(v ? '已启用' : '已停用') }
        catch (e) { message.error(extractApiError(e, '切换失败')) }
      },
    }),
  },
]

/* ============================ 指标 CRUD ============================ */
const indicatorModal = reactive({ show: false, editingId: '' as string | null, dimension: '院校标签' as string, name: '' })
function openAddIndicator() {
  indicatorModal.editingId = null
  indicatorModal.dimension = indicatorDimFilter.value || '院校标签'
  indicatorModal.name = ''
  indicatorModal.show = true
}
function openEditIndicator(r: ControlIndicator) {
  indicatorModal.editingId = r.id; indicatorModal.dimension = r.dimension; indicatorModal.name = r.name; indicatorModal.show = true
}
async function saveIndicator() {
  if (!indicatorModal.dimension || !indicatorModal.name.trim()) { message.warning('请选择维度并填写指标名称'); return }
  try {
    if (indicatorModal.editingId) await updateIndicator(indicatorModal.editingId, { name: indicatorModal.name.trim() })
    else await createIndicator({ dimension: indicatorModal.dimension, name: indicatorModal.name.trim() })
    message.success('保存成功')
    indicatorModal.show = false
    await loadIndicators()
    if (activeTab.value === 'rules') await loadUnified()
  } catch (e) { message.error(extractApiError(e, '保存失败')) }
}
function removeIndicator(r: ControlIndicator) {
  dialog.warning({
    title: '删除指标', content: `确认删除指标「${r.name}」？`, positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try { await deleteIndicator(r.id); message.success('删除成功'); await loadIndicators() }
      catch (e) { message.error(extractApiError(e, '删除失败')) }
    },
  })
}

/* ============================ 统一表 — 规则批量保存 ============================ */
async function saveRules() {
  const grouped = new Map<string, UnifiedRow[]>()
  for (const r of filteredUnifiedRows.value) {
    if (!grouped.has(r.dimensionId)) grouped.set(r.dimensionId, [])
    grouped.get(r.dimensionId)!.push(r)
  }
  for (const [, rows] of grouped) {
    for (const r of rows) {
      if (!(r.loPct <= r.targetPct && r.targetPct <= r.hiPct)) {
        message.warning(`指标「${r.indicatorName}」需满足 下限% ≤ 目标% ≤ 上限%`); return
      }
    }
  }
  loading.saveRules = true
  try {
    let okCount = 0
    for (const [dimensionId, rows] of grouped) {
      const rules: RuleDraft[] = rows.map((r) => ({
        indicator: r.indicatorId, target: r.targetPct / 100, lo: r.loPct / 100, hi: r.hiPct / 100, strength: r.strength,
      }))
      await batchSaveRules(currentScope.value, dimensionId, rules)
      okCount++
    }
    message.success(`已保存 ${okCount} 个维度的规则（每维度加和 = 100%）`)
    await Promise.all([loadUnified(), loadRatio(), loadPlan()])
  } catch (e) { message.error(extractApiError(e, '保存失败')) }
  finally { loading.saveRules = false }
}

/* ============================ 统一表 — 目标保存 ============================ */
async function saveTargets() {
  loading.saveTargets = true
  try {
    let ok = 0
    for (const r of filteredUnifiedRows.value) {
      await upsertHeadcount({
        id: r.headcountId ?? undefined,
        bu: currentScope.value.bu, position: currentScope.value.position, level: currentScope.value.level,
        indicator: r.indicatorId, year: targetYear.value, annualTarget: r.annualTarget, monthlyTargets: r.monthlyTargets,
      })
      ok++
    }
    message.success(`已保存 ${ok} 项目标`)
    await Promise.all([loadUnified(), loadPlan()])
  } catch (e) { message.error(extractApiError(e, '保存失败')) }
  finally { loading.saveTargets = false }
}

/* ============================ 12 月度目标弹窗 ============================ */
const monthlyModal = reactive({
  show: false, indicatorId: '', indicatorName: '', annualTarget: 0, monthly: Array(12).fill(0),
})
function openMonthlyModal(row: UnifiedRow) {
  monthlyModal.indicatorId = row.indicatorId
  monthlyModal.indicatorName = row.indicatorName
  monthlyModal.annualTarget = row.annualTarget
  monthlyModal.monthly = [...row.monthlyTargets]
  monthlyModal.show = true
}
function applyMonthly() {
  const row = unifiedRows.value.find((r) => r.indicatorId === monthlyModal.indicatorId)
  if (row) { row.annualTarget = monthlyModal.annualTarget; row.monthlyTargets = [...monthlyModal.monthly] }
  monthlyModal.show = false
}

/* ============================ 录入校验 ============================ */
const draft = reactive({
  code: '', name: '', bu: '能电BG', position: '', level: '',
  school: '985', sex: '男', major: '工学', month: '8月', status: '已入职',
})
const validation = ref<ValidationResult | null>(null)
async function runValidate() {
  validation.value = null
  loading.validate = true
  try {
    validation.value = await validateDraft(selectedYear.value, {
      bu: draft.bu, position: draft.position, level: draft.level,
      school: draft.school, sex: draft.sex, major: draft.major, month: draft.month,
    })
  } catch (e) { message.error(extractApiError(e, '校验失败')) }
  finally { loading.validate = false }
}
const canConfirmEntry = computed(
  () => !!draft.code.trim() && !!draft.name.trim() && validation.value != null && validation.value.verdict !== '❌ 阻断提交',
)
async function confirmEntry() {
  if (!draft.code.trim() || !draft.name.trim()) { message.warning('请先填写人员编码与姓名'); return }
  try {
    await upsertPerson({
      code: draft.code.trim(), name: draft.name.trim(), bu: draft.bu,
      school: draft.school, sex: draft.sex, major: draft.major, month: draft.month, status: draft.status, counted: true,
      position: draft.position, level: draft.level,
    })
    message.success('已录入人员')
    validation.value = null
    await Promise.all([loadPersons(), loadRatio(), loadPlan()])
  } catch (e) { message.error(extractApiError(e, '录入失败')) }
}

/* ============================ 人员 CRUD ============================ */
const personModal = reactive({
  show: false, editingId: '' as string | null,
  code: '', name: '', bu: '能电BG', school: '985', sex: '男', major: '工学', month: '8月', status: '已入职',
  position: '', level: '', counted: true,
})
function openAddPerson() {
  personModal.editingId = null; personModal.code = ''; personModal.name = ''; personModal.bu = '能电BG'
  personModal.school = '985'; personModal.sex = '男'; personModal.major = '工学'; personModal.month = '8月'
  personModal.status = '已入职'; personModal.position = ''; personModal.level = ''; personModal.counted = true
  personModal.show = true
}
function openEditPerson(r: Person) {
  personModal.editingId = r.id; personModal.code = r.code; personModal.name = r.name; personModal.bu = r.bu
  personModal.school = r.school; personModal.sex = r.sex; personModal.major = r.major; personModal.month = r.month
  personModal.status = r.status; personModal.position = r.position; personModal.level = r.level; personModal.counted = r.counted
  personModal.show = true
}
async function savePerson() {
  if (!personModal.code.trim() || !personModal.name.trim()) { message.warning('请填写编码与姓名'); return }
  try {
    await upsertPerson({
      id: personModal.editingId ?? undefined,
      code: personModal.code.trim(), name: personModal.name.trim(), bu: personModal.bu,
      school: personModal.school, sex: personModal.sex, major: personModal.major, month: personModal.month, status: personModal.status,
      position: personModal.position, level: personModal.level, counted: personModal.counted,
    })
    message.success('保存成功')
    personModal.show = false
    await loadPersons()
  } catch (e) { message.error(extractApiError(e, '保存失败')) }
}
function removePerson(r: Person) {
  dialog.warning({
    title: '删除人员', content: `确认删除「${r.name}（${r.code}）」？`, positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try { await deletePerson(r.id); message.success('删除成功'); await loadPersons() }
      catch (e) { message.error(extractApiError(e, '删除失败')) }
    },
  })
}

onMounted(async () => {
  await Promise.all([loadDimensions(), loadIndicators(), loadPersons()])
  await Promise.all([loadRatio(), loadPlan(), loadUnified()])
})
</script>

<style scoped>
.page-container { display: flex; flex-direction: column; gap: 12px; height: 100%; min-height: 0; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-shrink: 0; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
.page-subtitle { margin: 4px 0 0; color: #6b7280; font-size: 13px; }
.scope-label { color: #6b7280; font-size: 13px; white-space: nowrap; }
.content-card { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.content-card :deep(.n-card__content) { display: flex; flex-direction: column; min-height: 0; }
.toolbar { display: flex; gap: 12px; margin-bottom: 12px; flex-shrink: 0; }
.filter-row { margin-bottom: 12px; flex-shrink: 0; }
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; flex-shrink: 0; }
.kpi-card { background: #f8fafc; border: 1px solid #eef2f7; border-radius: 8px; padding: 14px 16px; display: flex; flex-direction: column; gap: 6px; }
.kpi-card.danger { background: #fef2f2; border-color: #fecaca; }
.kpi-card.warn { background: #fffbeb; border-color: #fde68a; }
.kpi-label { font-size: 12px; color: #6b7280; }
.kpi-value { font-size: 24px; font-weight: 700; color: #111827; }
.kpi-card.danger .kpi-value { color: #dc2626; }
.kpi-card.warn .kpi-value { color: #d97706; }
.validate-result { margin-top: 16px; }
.block-hint { color: #dc2626; font-size: 13px; margin: 8px 0 0; }

.dim-filter-row { display: flex; gap: 8px; margin-bottom: 12px; flex-shrink: 0; flex-wrap: wrap; }
.dim-tag {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px; border-radius: 16px; border: 1px solid #d1d5db;
  background: #fff; cursor: pointer; font-size: 13px; user-select: none;
  transition: all 0.15s;
}
.dim-tag:hover { border-color: #93c5fd; }
.dim-tag.active { background: #eff6ff; border-color: #2563eb; color: #1d4ed8; font-weight: 600; }
.dim-tag.ok .dim-sum { color: #059669; }
.dim-tag.bad .dim-sum { color: #dc2626; font-weight: 600; }
.dim-sum { font-size: 12px; color: #6b7280; font-weight: 400; }
</style>
