<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">校招管控</h1>
        <p class="page-subtitle">人员比例管控系统 v2 · 适用范围 / 维度 / 指标 / 规则(100% 加和) / 年度·月度目标 / 看板 / 录入校验 / 人员数据</p>
      </div>
      <n-space v-if="scopeScoped" align="center" style="flex-shrink: 0">
        <span class="scope-label">适用范围</span>
        <n-select
          v-model:value="selectedScopeId"
          :options="scopeOptions"
          style="width: 220px"
          placeholder="请选择方案"
          @update:value="onScopeChange"
        />
      </n-space>
    </div>

    <n-card :bordered="false" class="content-card">
      <n-tabs v-model:value="activeTab" type="line" @update:value="onTabChange">
        <!-- ===================== 实时看板 ===================== -->
        <n-tab-pane name="ratio" tab="实时看板">
          <n-alert v-if="!scopeOk" type="warning" :show-icon="true" style="margin-bottom: 12px">
            该方案存在维度目标占比未加和到 100% 的项，请前往「规则配置」补全。
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
            :row-key="(r: any) => r.dimension + '|' + r.indicator"
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

        <!-- ===================== 目标配置（年度 + 12 月） ===================== -->
        <n-tab-pane name="targets" tab="目标配置">
          <div class="filter-row">
            <n-space>
              <n-input-number v-model:value="targetYear" :min="2020" :max="2100" style="width: 120px" @update:value="loadHeadcounts" />
              <n-button type="primary" @click="openAddHeadcount">+ 新增人数目标</n-button>
            </n-space>
          </div>
          <n-data-table
            :columns="headcountColumns"
            :data="headcounts"
            :loading="loading.headcounts"
            :row-key="(r: any) => r.id"
            :pagination="false"
          >
            <template #empty><n-empty description="暂无目标，点击右上角新增" /></template>
          </n-data-table>
        </n-tab-pane>

        <!-- ===================== 规则配置（100% 加和） ===================== -->
        <n-tab-pane name="rules" tab="规则配置">
          <div class="filter-row">
            <n-space align="center">
              <span class="scope-label">维度</span>
              <n-select v-model:value="ruleDimensionId" :options="dimensionOptions" style="width: 180px" @update:value="loadRuleRows" />
              <n-tag :type="sumPct === 100 ? 'success' : 'error'" :bordered="false" size="large">
                目标占比加和：{{ sumPct.toFixed(1) }}%
              </n-tag>
            </n-space>
          </div>
          <n-data-table
            :columns="ruleEditColumns"
            :data="ruleRows"
            :loading="loading.rules"
            :row-key="(r: any) => r.indicatorId"
            :pagination="false"
          >
            <template #empty><n-empty description="该维度下暂无指标，请先到「维度与指标」配置指标" /></template>
          </n-data-table>
          <n-space justify="end" style="margin-top: 12px">
            <n-button type="primary" :loading="loading.saveRules" :disabled="!ruleRows.length" @click="saveRuleRows">
              保存规则
            </n-button>
          </n-space>
        </n-tab-pane>

        <!-- ===================== 适用范围 ===================== -->
        <n-tab-pane name="scopes" tab="适用范围">
          <div class="toolbar">
            <n-button type="primary" @click="openAddScope">+ 新增方案</n-button>
          </div>
          <n-data-table
            :columns="scopeColumns"
            :data="scopes"
            :loading="loading.scopes"
            :row-key="(r: any) => r.id"
            :pagination="false"
          >
            <template #empty><n-empty description="暂无方案" /></template>
          </n-data-table>
        </n-tab-pane>

        <!-- ===================== 维度与指标 ===================== -->
        <n-tab-pane name="dims" tab="维度与指标">
          <n-grid :cols="2" :x-gap="16" item-responsive responsive="screen">
            <n-gi span="2 m:1">
              <div class="panel-title-row">
                <span class="panel-title">维度</span>
                <n-button size="small" type="primary" @click="openAddDimension">+ 新增维度</n-button>
              </div>
              <n-data-table
                :columns="dimensionColumns"
                :data="dimensions"
                :loading="loading.dimensions"
                :row-key="(r: any) => r.id"
                :pagination="false"
              >
                <template #empty><n-empty description="暂无维度" /></template>
              </n-data-table>
            </n-gi>
            <n-gi span="2 m:1">
              <div class="panel-title-row">
                <span class="panel-title">指标（{{ selectedDimensionName || '请先选择维度' }}）</span>
                <n-button size="small" type="primary" :disabled="!selectedDimensionId" @click="openAddIndicator">+ 新增指标</n-button>
              </div>
              <n-data-table
                :columns="indicatorColumns"
                :data="indicators"
                :loading="loading.indicators"
                :row-key="(r: any) => r.id"
                :pagination="false"
              >
                <template #empty><n-empty description="暂无指标" /></template>
              </n-data-table>
            </n-gi>
          </n-grid>
        </n-tab-pane>

        <!-- ===================== 录入校验 ===================== -->
        <n-tab-pane name="validate" tab="录入校验">
          <n-grid :cols="4" :x-gap="16" :y-gap="12" item-responsive responsive="screen">
            <n-gi span="4 m:1"><n-form-item label="人员编码" label-placement="top"><n-input v-model:value="draft.code" placeholder="如 P032" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item label="姓名" label-placement="top"><n-input v-model:value="draft.name" placeholder="如 员工32" /></n-form-item></n-gi>
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
              :row-key="(r: any) => r.dimension + '|' + r.indicator"
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

    <!-- 规则单条配置弹窗 -->
    <n-modal v-model:show="ruleEditModal.show" :title="`配置指标：${ruleEditModal.indicatorName}`" preset="card" style="width: 460px">
      <n-form label-placement="top">
        <n-form-item label="目标占比 %"><n-input-number v-model:value="ruleEditModal.targetPct" :min="0" :max="100" :step="0.5" style="width: 100%" /></n-form-item>
        <n-grid :cols="2" :x-gap="16">
          <n-gi><n-form-item label="下限 %"><n-input-number v-model:value="ruleEditModal.loPct" :min="0" :max="100" :step="0.5" style="width: 100%" /></n-form-item></n-gi>
          <n-gi><n-form-item label="上限 %"><n-input-number v-model:value="ruleEditModal.hiPct" :min="0" :max="100" :step="0.5" style="width: 100%" /></n-form-item></n-gi>
        </n-grid>
        <n-form-item label="控制强度"><n-select v-model:value="ruleEditModal.strength" :options="strengthOptions" /></n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="ruleEditModal.show = false">取消</n-button>
          <n-button type="primary" @click="applyRuleEdit">确定</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 方案弹窗 -->
    <n-modal v-model:show="scopeModal.show" :title="scopeModal.editingId ? '编辑方案' : '新增方案'" preset="card" style="width: 520px">
      <n-form label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-gi span="2"><n-form-item label="方案名称"><n-input v-model:value="scopeModal.name" placeholder="如 能电BG校招" /></n-form-item></n-gi>
          <n-gi><n-form-item label="BG部门"><n-select v-model:value="scopeModal.bu" :options="deptOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item label="职务（可选）"><n-select v-model:value="scopeModal.position" :options="positionOptions" clearable placeholder="不限" /></n-form-item></n-gi>
          <n-gi><n-form-item label="职级（可选）"><n-select v-model:value="scopeModal.level" :options="levelOptions" clearable placeholder="不限" /></n-form-item></n-gi>
          <n-gi><n-form-item label="启用"><n-switch v-model:value="scopeModal.isActive" /></n-form-item></n-gi>
        </n-grid>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="scopeModal.show = false">取消</n-button>
          <n-button type="primary" :loading="loading.scopes" @click="saveScope">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 维度弹窗 -->
    <n-modal v-model:show="dimensionModal.show" :title="dimensionModal.editingId ? '编辑维度' : '新增维度'" preset="card" style="width: 420px">
      <n-form label-placement="top">
        <n-form-item label="维度名称"><n-select v-model:value="dimensionModal.name" :options="dimOptions" /></n-form-item>
        <n-form-item label="编码（可选）"><n-input v-model:value="dimensionModal.code" placeholder="如 SCHOOL" /></n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="dimensionModal.show = false">取消</n-button>
          <n-button type="primary" :loading="loading.dimensions" @click="saveDimension">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 指标弹窗 -->
    <n-modal v-model:show="indicatorModal.show" :title="indicatorModal.editingId ? '编辑指标' : '新增指标'" preset="card" style="width: 420px">
      <n-form label-placement="top">
        <n-form-item label="所属维度"><n-select v-model:value="indicatorModal.dimensionId" :options="dimensionOptions" :disabled="!!indicatorModal.editingId" /></n-form-item>
        <n-form-item label="指标名称"><n-input v-model:value="indicatorModal.name" placeholder="如 985 / 男 / 工学" /></n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="indicatorModal.show = false">取消</n-button>
          <n-button type="primary" :loading="loading.indicators" @click="saveIndicator">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 人数目标弹窗（年度 + 12 月） -->
    <n-modal v-model:show="headcountModal.show" :title="headcountModal.editingId ? '编辑人数目标' : '新增人数目标'" preset="card" style="width: 680px">
      <n-form label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-gi>
            <n-form-item label="维度">
              <n-select v-model:value="headcountModal.dimensionId" :options="dimensionOptions" :disabled="!!headcountModal.editingId" @update:value="onHeadcountDimChange" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="指标">
              <n-select v-model:value="headcountModal.indicatorId" :options="indicatorOptionsFor(headcountModal.dimensionId)" :disabled="!!headcountModal.editingId" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="所属年度"><n-input-number v-model:value="headcountModal.year" :min="2020" :max="2100" style="width: 100%" /></n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="年度目标人数"><n-input-number v-model:value="headcountModal.annualTarget" :min="0" style="width: 100%" /></n-form-item>
          </n-gi>
        </n-grid>
        <n-divider>12 个月目标（单位：人）</n-divider>
        <n-grid :cols="4" :x-gap="8" :y-gap="8">
          <n-gi v-for="(_, i) in 12" :key="i">
            <n-form-item :label="ALL_MONTHS[i]" label-placement="top">
              <n-input-number v-model:value="headcountModal.monthly[i]" :min="0" style="width: 100%" />
            </n-form-item>
          </n-gi>
        </n-grid>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="headcountModal.show = false">取消</n-button>
          <n-button type="primary" :loading="loading.headcounts" @click="saveHeadcount">保存</n-button>
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
  NTag, NButton, NSpace, NSwitch, NDivider, useMessage, useDialog,
  type DataTableColumns,
} from 'naive-ui'
import { extractApiError } from '../../api/dynamic-field'
import {
  listScopes, createScope, updateScope, deleteScope,
  listDimensions, createDimension, updateDimension, deleteDimension,
  listIndicators, createIndicator, updateIndicator, deleteIndicator,
  listRules, batchSaveRules,
  getRatio, getPlan, validateDraft,
  listHeadcounts, upsertHeadcount, deleteHeadcount,
  listPersons, upsertPerson, deletePerson,
  DEPTS, SCHOOLS, MAJORS, SEXES, ALL_MONTHS, DIMS, STRENGTH, STATUS, POSITIONS, LEVELS,
  type ControlScope, type ControlDimension, type ControlIndicator,
  type ControlHeadcount, type Person, type RatioRow, type RatioResult,
  type PlanRow, type PlanResult, type ValidationResult, type Strength, type RuleDraft,
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
  ratio: false, plan: false, rules: false, saveRules: false,
  scopes: false, dimensions: false, indicators: false,
  headcounts: false, persons: false, validate: false,
})
const scopes = ref<ControlScope[]>([])
const dimensions = ref<ControlDimension[]>([])
const indicators = ref<ControlIndicator[]>([])
const persons = ref<Person[]>([])

const selectedScopeId = ref<string>('')
const selectedYear = ref(2026)
const planMonth = ref('8月')

const scopeOptions = computed(() => scopes.value.map((s) => ({ label: s.name, value: s.id })))
const dimensionOptions = computed(() => dimensions.value.map((d) => ({ label: d.name, value: d.id })))
const scopeScoped = computed(() => ['ratio', 'plan', 'targets', 'rules', 'validate'].includes(activeTab.value))
const selectedScope = computed(() => scopes.value.find((s) => s.id === selectedScopeId.value))

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

/* ============================ 目标配置 ============================ */
const targetYear = ref(2026)
const headcounts = ref<ControlHeadcount[]>([])

/* ============================ 规则配置 ============================ */
const ruleDimensionId = ref<string>('')
interface RuleEditRow { indicatorId: string; indicatorName: string; targetPct: number; loPct: number; hiPct: number; strength: Strength }
const ruleRows = ref<RuleEditRow[]>([])
const sumPct = computed(() => ruleRows.value.reduce((s, r) => s + (Number(r.targetPct) || 0), 0))

/* ============================ 加载 ============================ */
async function loadScopes() {
  loading.scopes = true
  try {
    scopes.value = await listScopes()
    if (!selectedScopeId.value && scopes.value.length) {
      selectedScopeId.value = scopes.value[0].id
    }
  } catch (e) {
    message.error(extractApiError(e, '加载方案失败'))
  } finally {
    loading.scopes = false
  }
}
async function loadDimensions() {
  loading.dimensions = true
  try {
    dimensions.value = await listDimensions()
    if (!ruleDimensionId.value && dimensions.value.length) {
      ruleDimensionId.value = dimensions.value[0].id
    }
  } catch (e) {
    message.error(extractApiError(e, '加载维度失败'))
  } finally {
    loading.dimensions = false
  }
}
async function loadIndicators() {
  loading.indicators = true
  try {
    indicators.value = await listIndicators()
  } catch (e) {
    message.error(extractApiError(e, '加载指标失败'))
  } finally {
    loading.indicators = false
  }
}
async function loadPersons() {
  loading.persons = true
  try {
    persons.value = await listPersons()
  } catch (e) {
    message.error(extractApiError(e, '加载人员失败'))
  } finally {
    loading.persons = false
  }
}
async function loadRatio() {
  if (!selectedScopeId.value) return
  loading.ratio = true
  try {
    ratioData.value = await getRatio(selectedScopeId.value)
  } catch (e) {
    message.error(extractApiError(e, '加载看板失败'))
  } finally {
    loading.ratio = false
  }
}
async function loadPlan() {
  if (!selectedScopeId.value) return
  loading.plan = true
  try {
    planData.value = await getPlan(selectedScopeId.value, selectedYear.value, planMonth.value)
  } catch (e) {
    message.error(extractApiError(e, '加载规划失败'))
  } finally {
    loading.plan = false
  }
}
async function loadHeadcounts() {
  if (!selectedScopeId.value) return
  loading.headcounts = true
  try {
    headcounts.value = await listHeadcounts(selectedScopeId.value, targetYear.value)
  } catch (e) {
    message.error(extractApiError(e, '加载目标失败'))
  } finally {
    loading.headcounts = false
  }
}
async function loadRuleRows() {
  if (!selectedScopeId.value || !ruleDimensionId.value) return
  loading.rules = true
  try {
    const rules = await listRules(selectedScopeId.value)
    const dimRules = rules.filter((r) => r.dimension === ruleDimensionId.value)
    const dimIndicators = indicators.value.filter((i) => i.dimension === ruleDimensionId.value)
    const byInd = new Map(dimRules.map((r) => [r.indicator, r]))
    ruleRows.value = dimIndicators.map((ind) => {
      const r = byInd.get(ind.id)
      return {
        indicatorId: ind.id,
        indicatorName: ind.name,
        targetPct: r ? Math.round(r.target * 1000) / 10 : 0,
        loPct: r ? Math.round(r.lo * 1000) / 10 : 0,
        hiPct: r ? Math.round(r.hi * 1000) / 10 : 0,
        strength: (r?.strength ?? '硬约束') as Strength,
      }
    })
  } catch (e) {
    message.error(extractApiError(e, '加载规则失败'))
  } finally {
    loading.rules = false
  }
}

function onScopeChange() {
  if (activeTab.value === 'ratio') loadRatio()
  else if (activeTab.value === 'plan') loadPlan()
  else if (activeTab.value === 'targets') loadHeadcounts()
  else if (activeTab.value === 'rules') loadRuleRows()
}
function onTabChange(name: string) {
  if (name === 'ratio') loadRatio()
  else if (name === 'plan') loadPlan()
  else if (name === 'targets') loadHeadcounts()
  else if (name === 'rules') loadRuleRows()
  else if (name === 'persons') loadPersons()
  else if (name === 'scopes') loadScopes()
  else if (name === 'dims') { loadDimensions(); loadIndicators() }
}

/* ============================ 列定义 ============================ */
const ratioColumns: DataTableColumns<RatioRow> = [
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

const headcountColumns: DataTableColumns<ControlHeadcount> = [
  { title: '维度', key: 'dimensionName' },
  { title: '指标', key: 'indicatorName' },
  { title: '年度', key: 'year' },
  { title: '年度目标', key: 'annualTarget' },
  { title: '月度合计', key: 'monthlyTargets', render: (r) => r.monthlyTargets.reduce((a, b) => a + b, 0) },
  {
    title: '操作',
    key: 'actions',
    render: (r) =>
      h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => openEditHeadcount(r) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', type: 'error', quaternary: true, onClick: () => removeHeadcount(r) }, { default: () => '删除' }),
        ],
      }),
  },
]

const ruleEditColumns: DataTableColumns<RuleEditRow> = [
  { title: '指标', key: 'indicatorName' },
  { title: '目标占比 %', key: 'targetPct', render: (r) => h('span', {}, `${r.targetPct}%`) },
  { title: '下限 %', key: 'loPct', render: (r) => h('span', {}, `${r.loPct}%`) },
  { title: '上限 %', key: 'hiPct', render: (r) => h('span', {}, `${r.hiPct}%`) },
  { title: '强度', key: 'strength', render: (r) => h(NTag, { type: strengthType(r.strength), bordered: false }, { default: () => r.strength }) },
  {
    title: '操作',
    key: 'actions',
    render: (r) => h(NButton, { size: 'small', onClick: () => openEditRuleRow(r) }, { default: () => '配置' }),
  },
]

const scopeColumns: DataTableColumns<ControlScope> = [
  { title: '方案名称', key: 'name' },
  { title: 'BG部门', key: 'bu' },
  { title: '职务', key: 'position', render: (r) => r.position || '不限' },
  { title: '职级', key: 'level', render: (r) => r.level || '不限' },
  { title: '启用', key: 'isActive', render: (r) => h(NTag, { type: r.isActive ? 'success' : 'default', bordered: false }, { default: () => (r.isActive ? '启用' : '停用') }) },
  {
    title: '操作',
    key: 'actions',
    render: (r) =>
      h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => openEditScope(r) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', type: 'error', quaternary: true, onClick: () => removeScope(r) }, { default: () => '删除' }),
        ],
      }),
  },
]

const dimensionColumns: DataTableColumns<ControlDimension> = [
  { title: '维度', key: 'name' },
  { title: '编码', key: 'code', render: (r) => r.code || '—' },
  {
    title: '操作',
    key: 'actions',
    render: (r) =>
      h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => selectDimension(r) }, { default: () => '查看指标' }),
          h(NButton, { size: 'small', type: 'error', quaternary: true, onClick: () => removeDimension(r) }, { default: () => '删除' }),
        ],
      }),
  },
]

const indicatorColumns: DataTableColumns<ControlIndicator> = [
  { title: '指标', key: 'name' },
  {
    title: '操作',
    key: 'actions',
    render: (r) =>
      h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => openEditIndicator(r) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', type: 'error', quaternary: true, onClick: () => removeIndicator(r) }, { default: () => '删除' }),
        ],
      }),
  },
]

const personColumns: DataTableColumns<Person> = [
  { title: '编码', key: 'code' },
  { title: '姓名', key: 'name' },
  { title: '部门', key: 'bu' },
  { title: '院校', key: 'school' },
  { title: '性别', key: 'sex' },
  { title: '专业', key: 'major' },
  { title: '月份', key: 'month' },
  { title: '职务', key: 'position', render: (r) => r.position || '—' },
  { title: '职级', key: 'level', render: (r) => r.level || '—' },
  { title: '状态', key: 'status' },
  { title: '计入核算', key: 'counted', render: (r) => h(NTag, { type: r.counted ? 'success' : 'default', bordered: false }, { default: () => (r.counted ? '是' : '否') }) },
  {
    title: '操作',
    key: 'actions',
    render: (r) =>
      h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => openEditPerson(r) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', type: 'error', quaternary: true, onClick: () => removePerson(r) }, { default: () => '删除' }),
        ],
      }),
  },
]

const checkColumns: DataTableColumns<ValidationResult['checks'][number]> = [
  { title: '维度', key: 'dimension' },
  { title: '指标', key: 'indicator' },
  { title: '强度', key: 'strength', render: (r) => h(NTag, { type: strengthType(r.strength), bordered: false }, { default: () => r.strength }) },
  { title: '占比', key: 'ratio', render: (r) => pct(r.ratio) },
  { title: '占比状态', key: 'ratioStatus', render: (r) => h(NTag, { type: ratioStatusType(r.ratioStatus), bordered: false }, { default: () => r.ratioStatus }) },
  { title: '本月实际', key: 'monthActual' },
  { title: '本月目标', key: 'monthTarget' },
  { title: '人数状态', key: 'countStatus', render: (r) => h(NTag, { type: countStatusType(r.countStatus), bordered: false }, { default: () => r.countStatus }) },
]

/* ============================ 方案 CRUD ============================ */
const scopeModal = reactive({
  show: false, editingId: '' as string | null,
  name: '', bu: '能电BG', position: '', level: '', isActive: true,
})
function openAddScope() {
  scopeModal.editingId = null; scopeModal.name = ''; scopeModal.bu = '能电BG'
  scopeModal.position = ''; scopeModal.level = ''; scopeModal.isActive = true; scopeModal.show = true
}
function openEditScope(r: ControlScope) {
  scopeModal.editingId = r.id; scopeModal.name = r.name; scopeModal.bu = r.bu
  scopeModal.position = r.position; scopeModal.level = r.level; scopeModal.isActive = r.isActive; scopeModal.show = true
}
async function saveScope() {
  if (!scopeModal.name.trim()) { message.warning('请填写方案名称'); return }
  try {
    const payload = {
      name: scopeModal.name.trim(), bu: scopeModal.bu,
      position: scopeModal.position, level: scopeModal.level, isActive: scopeModal.isActive,
    }
    if (scopeModal.editingId) await updateScope(scopeModal.editingId, payload)
    else await createScope(payload)
    message.success('保存成功')
    scopeModal.show = false
    await loadScopes()
  } catch (e) { message.error(extractApiError(e, '保存失败')) }
}
function removeScope(r: ControlScope) {
  dialog.warning({
    title: '删除方案', content: `确认删除「${r.name}」？其下规则/目标将一并删除。`, positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteScope(r.id)
        message.success('删除成功')
        if (selectedScopeId.value === r.id) selectedScopeId.value = ''
        await loadScopes()
      } catch (e) { message.error(extractApiError(e, '删除失败')) }
    },
  })
}

/* ============================ 维度 CRUD ============================ */
const dimensionModal = reactive({ show: false, editingId: '' as string | null, name: '院校标签' as string, code: '' })
function openAddDimension() { dimensionModal.editingId = null; dimensionModal.name = '院校标签'; dimensionModal.code = ''; dimensionModal.show = true }
function openEditDimension(r: ControlDimension) { dimensionModal.editingId = r.id; dimensionModal.name = r.name; dimensionModal.code = r.code; dimensionModal.show = true }
async function saveDimension() {
  if (!dimensionModal.name) { message.warning('请选择维度'); return }
  try {
    const payload = { name: dimensionModal.name as any, code: dimensionModal.code, isActive: true }
    if (dimensionModal.editingId) await updateDimension(dimensionModal.editingId, payload)
    else await createDimension(payload)
    message.success('保存成功')
    dimensionModal.show = false
    await loadDimensions()
  } catch (e) { message.error(extractApiError(e, '保存失败')) }
}
function removeDimension(r: ControlDimension) {
  dialog.warning({
    title: '删除维度', content: `确认删除维度「${r.name}」？其下指标将被级联删除。`, positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try { await deleteDimension(r.id); message.success('删除成功'); await loadDimensions(); await loadIndicators() }
      catch (e) { message.error(extractApiError(e, '删除失败')) }
    },
  })
}

/* ============================ 指标 CRUD ============================ */
const selectedDimensionId = ref<string>('')
const selectedDimensionName = computed(() => dimensions.value.find((d) => d.id === selectedDimensionId.value)?.name ?? '')
const indicatorOptionsFor = (dimId: string) => indicators.value.filter((i) => i.dimension === dimId).map((i) => ({ label: i.name, value: i.id }))
function selectDimension(r: ControlDimension) {
  selectedDimensionId.value = r.id
  loadIndicators()
}
const indicatorModal = reactive({ show: false, editingId: '' as string | null, dimensionId: '', name: '' })
function openAddIndicator() {
  indicatorModal.editingId = null; indicatorModal.dimensionId = selectedDimensionId.value; indicatorModal.name = ''; indicatorModal.show = true
}
function openEditIndicator(r: ControlIndicator) {
  indicatorModal.editingId = r.id; indicatorModal.dimensionId = r.dimension; indicatorModal.name = r.name; indicatorModal.show = true
}
async function saveIndicator() {
  if (!indicatorModal.dimensionId || !indicatorModal.name.trim()) { message.warning('请选择维度并填写指标名称'); return }
  try {
    if (indicatorModal.editingId) await updateIndicator(indicatorModal.editingId, { name: indicatorModal.name.trim() })
    else await createIndicator({ dimension: indicatorModal.dimensionId, name: indicatorModal.name.trim() })
    message.success('保存成功')
    indicatorModal.show = false
    await loadIndicators()
    if (activeTab.value === 'rules') await loadRuleRows()
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

/* ============================ 规则配置（100% 批量保存） ============================ */
const ruleEditModal = reactive({ show: false, indicatorId: '', indicatorName: '', targetPct: 0, loPct: 0, hiPct: 0, strength: '硬约束' as Strength })
function openEditRuleRow(r: RuleEditRow) {
  ruleEditModal.indicatorId = r.indicatorId; ruleEditModal.indicatorName = r.indicatorName
  ruleEditModal.targetPct = r.targetPct; ruleEditModal.loPct = r.loPct; ruleEditModal.hiPct = r.hiPct; ruleEditModal.strength = r.strength
  ruleEditModal.show = true
}
function applyRuleEdit() {
  const row = ruleRows.value.find((r) => r.indicatorId === ruleEditModal.indicatorId)
  if (row) {
    row.targetPct = ruleEditModal.targetPct; row.loPct = ruleEditModal.loPct; row.hiPct = ruleEditModal.hiPct; row.strength = ruleEditModal.strength
  }
  ruleEditModal.show = false
}
async function saveRuleRows() {
  if (!selectedScopeId.value || !ruleDimensionId.value) return
  for (const r of ruleRows.value) {
    if (!(r.loPct <= r.targetPct && r.targetPct <= r.hiPct)) {
      message.warning(`指标「${r.indicatorName}」需满足 下限% ≤ 目标% ≤ 上限%`)
      return
    }
  }
  loading.saveRules = true
  try {
    const rules: RuleDraft[] = ruleRows.value.map((r) => ({
      indicator: r.indicatorId,
      target: r.targetPct / 100,
      lo: r.loPct / 100,
      hi: r.hiPct / 100,
      strength: r.strength,
    }))
    await batchSaveRules(selectedScopeId.value, ruleDimensionId.value, rules)
    message.success('保存成功，目标占比加和 = 100%')
    await Promise.all([loadRuleRows(), loadRatio(), loadPlan()])
  } catch (e) {
    message.error(extractApiError(e, '保存失败'))
  } finally {
    loading.saveRules = false
  }
}

/* ============================ 目标配置 ============================ */
const headcountModal = reactive({
  show: false, editingId: '' as string | null,
  dimensionId: '', indicatorId: '', year: 2026, annualTarget: 0, monthly: Array(12).fill(0),
})
function onHeadcountDimChange() { headcountModal.indicatorId = '' }
function openAddHeadcount() {
  headcountModal.editingId = null; headcountModal.dimensionId = ruleDimensionId.value || dimensions.value[0]?.id || ''
  headcountModal.indicatorId = ''; headcountModal.year = targetYear.value; headcountModal.annualTarget = 0
  headcountModal.monthly = Array(12).fill(0); headcountModal.show = true
}
function openEditHeadcount(r: ControlHeadcount) {
  headcountModal.editingId = r.id; headcountModal.dimensionId = dimensions.value.find((d) => d.name === r.dimensionName)?.id ?? ''
  headcountModal.indicatorId = r.indicator; headcountModal.year = r.year; headcountModal.annualTarget = r.annualTarget
  headcountModal.monthly = [...r.monthlyTargets]; headcountModal.show = true
}
async function saveHeadcount() {
  if (!headcountModal.indicatorId) { message.warning('请选择指标'); return }
  try {
    await upsertHeadcount({
      id: headcountModal.editingId ?? undefined,
      scope: selectedScopeId.value,
      indicator: headcountModal.indicatorId,
      year: headcountModal.year,
      annualTarget: headcountModal.annualTarget,
      monthlyTargets: headcountModal.monthly,
    })
    message.success('保存成功')
    headcountModal.show = false
    await loadHeadcounts()
  } catch (e) { message.error(extractApiError(e, '保存失败')) }
}
function removeHeadcount(r: ControlHeadcount) {
  dialog.warning({
    title: '删除目标', content: `确认删除「${r.indicatorName}」的 ${r.year} 年度目标？`, positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try { await deleteHeadcount(r.id); message.success('删除成功'); await loadHeadcounts() }
      catch (e) { message.error(extractApiError(e, '删除失败')) }
    },
  })
}

/* ============================ 录入校验 ============================ */
const draft = reactive({
  code: '', name: '', bu: '能电BG', school: '985', sex: '男', major: '工学', month: '8月', status: '已入职',
})
const validation = ref<ValidationResult | null>(null)
async function runValidate() {
  validation.value = null
  loading.validate = true
  try {
    validation.value = await validateDraft(selectedScopeId.value, selectedYear.value, {
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
      code: draft.code.trim(), name: draft.name.trim(), bu: selectedScope.value?.bu ?? draft.bu,
      school: draft.school, sex: draft.sex, major: draft.major, month: draft.month, status: draft.status, counted: true,
      position: selectedScope.value?.position ?? '', level: selectedScope.value?.level ?? '',
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
  await Promise.all([loadScopes(), loadDimensions(), loadIndicators(), loadPersons()])
  if (selectedScopeId.value) await Promise.all([loadRatio(), loadPlan(), loadHeadcounts(), loadRuleRows()])
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  min-height: 0;
}
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-shrink: 0;
}
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
.panel-title-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.panel-title { font-weight: 600; font-size: 14px; }
</style>
