<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">校招管控</h1>
        <p class="page-subtitle">人员比例管控系统 · 实时看板 / 人数规划 / 规则配置 / 录入校验 / 人员数据</p>
      </div>
    </div>

    <n-card :bordered="false" class="content-card">
      <n-tabs v-model:value="activeTab" type="line" @update:value="onTabChange">
        <!-- ===================== 实时看板 ===================== -->
        <n-tab-pane name="ratio" tab="实时看板">
          <div class="kpi-row">
            <div class="kpi-card"><span class="kpi-label">计入核算人数</span><span class="kpi-value">{{ ratioKpi.total }}</span></div>
            <div class="kpi-card"><span class="kpi-label">管控规则数</span><span class="kpi-value">{{ ratioKpi.rules }}</span></div>
            <div class="kpi-card danger"><span class="kpi-label">硬约束超标</span><span class="kpi-value">{{ ratioKpi.hard }}</span></div>
            <div class="kpi-card warn"><span class="kpi-label">软/仅提示超标</span><span class="kpi-value">{{ ratioKpi.soft }}</span></div>
          </div>
          <n-data-table
            :columns="ratioColumns"
            :data="ratioData.rows"
            :loading="loading.ratio"
            :row-key="(r: any) => r.dim + '|' + r.group"
            :pagination="false"
          >
            <template #empty><n-empty description="暂无数据" /></template>
          </n-data-table>
        </n-tab-pane>

        <!-- ===================== 人数规划 ===================== -->
        <n-tab-pane name="plan" tab="人数规划">
          <div class="filter-row">
            <n-select v-model:value="selectedMonth" :options="monthOptions" style="width: 160px" @update:value="loadPlan" />
          </div>
          <div class="kpi-row">
            <div class="kpi-card"><span class="kpi-label">本月总缺口</span><span class="kpi-value">{{ planData.kpi.monthGap }}</span></div>
            <div class="kpi-card"><span class="kpi-label">管控规则数</span><span class="kpi-value">{{ planData.kpi.groupCount }}</span></div>
            <div class="kpi-card danger"><span class="kpi-label">硬约束超标</span><span class="kpi-value">{{ planData.kpi.hardViolationCount }}</span></div>
            <div class="kpi-card warn"><span class="kpi-label">软/仅提示超标</span><span class="kpi-value">{{ planData.kpi.warnCount }}</span></div>
          </div>
          <n-data-table
            :columns="planColumns"
            :data="planData.rows"
            :loading="loading.plan"
            :row-key="(r: any) => r.dim + '|' + r.group"
            :pagination="false"
          >
            <template #empty><n-empty description="暂无数据" /></template>
          </n-data-table>
        </n-tab-pane>

        <!-- ===================== 规则配置 ===================== -->
        <n-tab-pane name="rules" tab="规则配置">
          <div class="toolbar">
            <n-button type="primary" @click="openAddRule">+ 新增规则</n-button>
          </div>
          <n-data-table
            :columns="rulesColumns"
            :data="rules"
            :loading="loading.rules"
            :row-key="(r: any) => r.id"
            :pagination="false"
          >
            <template #empty><n-empty description="暂无规则，点击右上角新增" /></template>
          </n-data-table>
        </n-tab-pane>

        <!-- ===================== 录入校验 ===================== -->
        <n-tab-pane name="validate" tab="录入校验">
          <n-grid :cols="4" :x-gap="16" :y-gap="12" item-responsive responsive="screen">
            <n-gi span="4 m:1"><n-form-item label="人员编码" label-placement="top"><n-input v-model:value="draft.code" placeholder="如 P032" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item label="姓名" label-placement="top"><n-input v-model:value="draft.name" placeholder="如 员工32" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item label="部门" label-placement="top"><n-select v-model:value="draft.bu" :options="deptOptions" /></n-form-item></n-gi>
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
              :row-key="(r: any) => r.dim + '|' + r.group"
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
            <n-button @click="importModal.show = true">批量导入</n-button>
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

    <!-- 规则新增/编辑弹窗 -->
    <n-modal v-model:show="ruleModal.show" :title="ruleModal.editingId ? '编辑规则' : '新增规则'" preset="card" style="width: 560px">
      <n-form label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-gi>
            <n-form-item label="维度">
              <n-select v-model:value="ruleModal.dim" :options="dimOptions" @update:value="onRuleDimChange" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="分组">
              <n-select v-model:value="ruleModal.group" :options="ruleGroupOptions" placeholder="请选择分组" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="目标占比 %">
              <n-input-number v-model:value="ruleModal.targetPct" :min="0" :max="100" :step="0.5" style="width: 100%" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="控制强度">
              <n-select v-model:value="ruleModal.strength" :options="strengthOptions" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="下限 %">
              <n-input-number v-model:value="ruleModal.loPct" :min="0" :max="100" :step="0.5" style="width: 100%" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="上限 %">
              <n-input-number v-model:value="ruleModal.hiPct" :min="0" :max="100" :step="0.5" style="width: 100%" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="整体目标人数">
              <n-input-number v-model:value="ruleModal.whole" :min="0" :step="1" style="width: 100%" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="本月目标人数">
              <n-input-number v-model:value="ruleModal.monthTarget" :min="0" :step="1" style="width: 100%" />
            </n-form-item>
          </n-gi>
        </n-grid>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="ruleModal.show = false">取消</n-button>
          <n-button type="primary" :loading="loading.rules" @click="saveRule">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 人员新增/编辑弹窗 -->
    <n-modal v-model:show="personModal.show" :title="personModal.editingId ? '编辑人员' : '新增人员'" preset="card" style="width: 520px">
      <n-form label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-gi>
            <n-form-item label="人员编码"><n-input v-model:value="personModal.code" placeholder="如 P032" /></n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="姓名"><n-input v-model:value="personModal.name" placeholder="如 员工32" /></n-form-item>
          </n-gi>
          <n-gi><n-form-item label="部门"><n-select v-model:value="personModal.bu" :options="deptOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item label="院校标签"><n-select v-model:value="personModal.school" :options="schoolOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item label="性别"><n-select v-model:value="personModal.sex" :options="sexOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item label="专业标签"><n-select v-model:value="personModal.major" :options="majorOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item label="招聘月份"><n-select v-model:value="personModal.month" :options="monthOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item label="状态"><n-select v-model:value="personModal.status" :options="statusOptions" /></n-form-item></n-gi>
        </n-grid>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="personModal.show = false">取消</n-button>
          <n-button type="primary" :loading="loading.persons" @click="savePerson">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 批量导入弹窗 -->
    <n-modal v-model:show="importModal.show" title="批量导入人员" preset="card" style="width: 640px">
      <n-alert type="info" :show-icon="true" style="margin-bottom: 12px">
        支持粘贴 <b>JSON 数组</b> 或 <b>CSV</b>（首行可为表头）。字段顺序：
        <code>编码,姓名,部门,院校,性别,专业,月份,状态</code>。状态取值：已入职 / 已Offer / 候选池。
      </n-alert>
      <n-input
        v-model:value="importText"
        type="textarea"
        placeholder='例如：
P032,员工32,能电BG,985,男,工学,8月,已入职
P033,员工33,三到BG,211,女,其他,8月,已Offer'
        :autosize="{ minRows: 6, maxRows: 14 }"
      />
      <template #footer>
        <n-space justify="end">
          <n-button @click="importModal.show = false">取消</n-button>
          <n-button type="primary" :loading="loading.import" @click="doImport">开始导入</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h, onMounted, watch } from 'vue'
import {
  NTag,
  NButton,
  NSpace,
  useMessage,
  useDialog,
  type DataTableColumns,
} from 'naive-ui'
import { extractApiError } from '../../api/dynamic-field'
import {
  getRules,
  upsertRule,
  deleteRule,
  getRatio,
  getPlan,
  validateDraft,
  getPersons,
  upsertPerson,
  deletePerson,
  importPersons,
  DEPTS,
  SCHOOLS,
  MAJORS,
  SEXES,
  MONTHS,
  DIMS,
  STRENGTH,
  STATUS,
  GROUP_CHOICES,
  type Rule,
  type RatioRow,
  type PlanRow,
  type Kpi,
  type Person,
  type ValidationResult,
  type Dim,
  type Strength,
} from '../../api/campusControl'

const message = useMessage()
const dialog = useDialog()

/* ============================ 选项 ============================ */
const opt = (arr: readonly string[]) => arr.map((v) => ({ label: v, value: v }))
const deptOptions = opt(DEPTS)
const schoolOptions = opt(SCHOOLS)
const majorOptions = opt(MAJORS)
const sexOptions = opt(SEXES)
const monthOptions = opt(MONTHS)
const dimOptions = opt(DIMS)
const strengthOptions = opt(STRENGTH)
const statusOptions = opt(STATUS)
const groupOptionsFor = (dim: Dim) => (GROUP_CHOICES[dim] ?? []).map((v) => ({ label: v, value: v }))

/* ============================ 工具 ============================ */
const pct = (r: number, d = 1) => `${(r * 100).toFixed(d)}%`
const ratioStatusType = (s: string) => (s === '正常' ? 'success' : s === '高于上限' ? 'error' : 'warning')
const countStatusType = (s: string) => (s === '本月达标' ? 'success' : s === '缺口未达成' ? 'warning' : 'default')
const strengthType = (s: string) => (s === '硬约束' ? 'error' : s === '软约束' ? 'warning' : 'default')
const verdictType = (v: string) => (v.startsWith('❌') ? 'error' : v.startsWith('⚠️') ? 'warning' : 'success')

/* ============================ 状态 ============================ */
const activeTab = ref('ratio')
const loading = reactive({ ratio: false, plan: false, rules: false, persons: false, validate: false, import: false })

const ratioData = ref<{ total: number; rows: RatioRow[] }>({ total: 0, rows: [] })
const planData = ref<{ rows: PlanRow[]; kpi: Kpi }>({
  rows: [],
  kpi: { total: 0, groupCount: 0, warnCount: 0, hardViolationCount: 0, monthGap: 0 },
})
const rules = ref<Rule[]>([])
const persons = ref<Person[]>([])
const selectedMonth = ref('8月')

const ratioKpi = computed(() => {
  const rows = ratioData.value.rows
  return {
    total: ratioData.value.total,
    rules: rows.length,
    hard: rows.filter((r) => r.status !== '正常' && r.strength === '硬约束').length,
    soft: rows.filter((r) => r.status !== '正常' && r.strength !== '硬约束').length,
  }
})

/* ============================ 加载 ============================ */
async function loadRules() {
  loading.rules = true
  try {
    rules.value = await getRules()
  } catch (e) {
    message.error(extractApiError(e, '加载规则失败'))
  } finally {
    loading.rules = false
  }
}
async function loadRatio() {
  loading.ratio = true
  try {
    ratioData.value = await getRatio()
  } catch (e) {
    message.error(extractApiError(e, '加载看板失败'))
  } finally {
    loading.ratio = false
  }
}
async function loadPlan() {
  loading.plan = true
  try {
    planData.value = await getPlan(selectedMonth.value)
  } catch (e) {
    message.error(extractApiError(e, '加载规划失败'))
  } finally {
    loading.plan = false
  }
}
async function loadPersons() {
  loading.persons = true
  try {
    persons.value = await getPersons()
  } catch (e) {
    message.error(extractApiError(e, '加载人员失败'))
  } finally {
    loading.persons = false
  }
}

function onTabChange(name: string) {
  if (name === 'ratio') loadRatio()
  else if (name === 'plan') loadPlan()
  else if (name === 'persons') loadPersons()
}

/* ============================ 列定义 ============================ */
const ratioColumns: DataTableColumns<RatioRow> = [
  { title: '维度', key: 'dim' },
  { title: '分组', key: 'group' },
  { title: '实际/分母', key: 'actual', render: (r) => `${r.actual} / ${r.denom}` },
  { title: '占比', key: 'ratio', render: (r) => h(NTag, { type: 'default', bordered: false }, { default: () => pct(r.ratio) }) },
  { title: '目标', key: 'target', render: (r) => pct(r.target) },
  { title: '下限', key: 'lo', render: (r) => pct(r.lo) },
  { title: '上限', key: 'hi', render: (r) => pct(r.hi) },
  { title: '状态', key: 'status', render: (r) => h(NTag, { type: ratioStatusType(r.status), bordered: false }, { default: () => r.status }) },
  { title: '控制强度', key: 'strength', render: (r) => h(NTag, { type: strengthType(r.strength), bordered: false }, { default: () => r.strength }) },
]

const planColumns: DataTableColumns<PlanRow> = [
  { title: '维度', key: 'dim' },
  { title: '分组', key: 'group' },
  { title: '强度', key: 'strength', render: (r) => h(NTag, { type: strengthType(r.strength), bordered: false }, { default: () => r.strength }) },
  { title: '在职', key: 'onjob' },
  { title: '整体目标', key: 'whole' },
  { title: '整体缺口', key: 'wholeGap' },
  { title: '本月目标', key: 'monthTarget' },
  { title: '本月实际', key: 'monthActual' },
  { title: '缺口', key: 'gap' },
  { title: '状态', key: 'status', render: (r) => h(NTag, { type: countStatusType(r.status), bordered: false }, { default: () => r.status }) },
]

const rulesColumns: DataTableColumns<Rule> = [
  { title: '维度', key: 'dim' },
  { title: '分组', key: 'group' },
  { title: '目标占比', key: 'target', render: (r) => pct(r.target) },
  { title: '下限', key: 'lo', render: (r) => pct(r.lo) },
  { title: '上限', key: 'hi', render: (r) => pct(r.hi) },
  { title: '强度', key: 'strength', render: (r) => h(NTag, { type: strengthType(r.strength), bordered: false }, { default: () => r.strength }) },
  { title: '整体目标', key: 'whole' },
  { title: '本月目标', key: 'monthTarget' },
  {
    title: '操作',
    key: 'actions',
    render: (r) =>
      h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => openEditRule(r) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', type: 'error', quaternary: true, onClick: () => removeRule(r) }, { default: () => '删除' }),
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
  { title: '维度', key: 'dim' },
  { title: '分组', key: 'group' },
  { title: '强度', key: 'strength', render: (r) => h(NTag, { type: strengthType(r.strength), bordered: false }, { default: () => r.strength }) },
  { title: '占比', key: 'ratio', render: (r) => pct(r.ratio) },
  { title: '占比状态', key: 'ratioStatus', render: (r) => h(NTag, { type: ratioStatusType(r.ratioStatus), bordered: false }, { default: () => r.ratioStatus }) },
  { title: '本月实际', key: 'monthActual' },
  { title: '本月目标', key: 'monthTarget' },
  { title: '人数状态', key: 'countStatus', render: (r) => h(NTag, { type: countStatusType(r.countStatus), bordered: false }, { default: () => r.countStatus }) },
]

/* ============================ 规则弹窗 ============================ */
const ruleModal = reactive({
  show: false,
  editingId: '' as string | null,
  dim: '院校标签' as Dim,
  group: '',
  targetPct: 34,
  loPct: 32,
  hiPct: 36,
  strength: '硬约束' as Strength,
  whole: 0,
  monthTarget: 0,
})
const ruleGroupOptions = computed(() => groupOptionsFor(ruleModal.dim))

function onRuleDimChange() {
  ruleModal.group = ''
}
function openAddRule() {
  ruleModal.editingId = null
  ruleModal.dim = '院校标签'
  ruleModal.group = ''
  ruleModal.targetPct = 34
  ruleModal.loPct = 32
  ruleModal.hiPct = 36
  ruleModal.strength = '硬约束'
  ruleModal.whole = 0
  ruleModal.monthTarget = 0
  ruleModal.show = true
}
function openEditRule(row: Rule) {
  ruleModal.editingId = row.id
  ruleModal.dim = row.dim
  ruleModal.group = row.group
  ruleModal.targetPct = Math.round(row.target * 1000) / 10
  ruleModal.loPct = Math.round(row.lo * 1000) / 10
  ruleModal.hiPct = Math.round(row.hi * 1000) / 10
  ruleModal.strength = row.strength
  ruleModal.whole = row.whole
  ruleModal.monthTarget = row.monthTarget
  ruleModal.show = true
}
async function saveRule() {
  if (!ruleModal.group) {
    message.warning('请选择分组')
    return
  }
  if (!(ruleModal.loPct <= ruleModal.targetPct && ruleModal.targetPct <= ruleModal.hiPct)) {
    message.warning('需满足 下限% ≤ 目标% ≤ 上限%')
    return
  }
  try {
    await upsertRule({
      id: ruleModal.editingId ?? undefined,
      dim: ruleModal.dim,
      group: ruleModal.group,
      target: ruleModal.targetPct / 100,
      lo: ruleModal.loPct / 100,
      hi: ruleModal.hiPct / 100,
      strength: ruleModal.strength,
      whole: ruleModal.whole,
      monthTarget: ruleModal.monthTarget,
    })
    message.success('保存成功')
    ruleModal.show = false
    await Promise.all([loadRules(), loadRatio(), loadPlan()])
  } catch (e) {
    message.error(extractApiError(e, '保存失败'))
  }
}
function removeRule(row: Rule) {
  dialog.warning({
    title: '删除规则',
    content: `确认删除「${row.dim} - ${row.group}」？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteRule(row.id)
        message.success('删除成功')
        await Promise.all([loadRules(), loadRatio(), loadPlan()])
      } catch (e) {
        message.error(extractApiError(e, '删除失败'))
      }
    },
  })
}

/* ============================ 录入校验 ============================ */
const draft = reactive({
  code: '',
  name: '',
  bu: '能电BG',
  school: '985',
  sex: '男',
  major: '工学',
  month: '8月',
  status: '已入职',
})
const validation = ref<ValidationResult | null>(null)

async function runValidate() {
  validation.value = null
  loading.validate = true
  try {
    validation.value = await validateDraft({
      bu: draft.bu,
      school: draft.school,
      sex: draft.sex,
      major: draft.major,
      month: draft.month,
    })
  } catch (e) {
    message.error(extractApiError(e, '校验失败'))
  } finally {
    loading.validate = false
  }
}
const canConfirmEntry = computed(
  () => !!draft.code.trim() && !!draft.name.trim() && validation.value != null && validation.value.verdict !== '❌ 阻断提交',
)
async function confirmEntry() {
  if (!draft.code.trim() || !draft.name.trim()) {
    message.warning('请先填写人员编码与姓名')
    return
  }
  try {
    await upsertPerson({
      code: draft.code.trim(),
      name: draft.name.trim(),
      bu: draft.bu,
      school: draft.school,
      sex: draft.sex,
      major: draft.major,
      month: draft.month,
      status: draft.status,
      counted: true,
    })
    message.success('已录入人员')
    validation.value = null
    await Promise.all([loadPersons(), loadRatio(), loadPlan()])
  } catch (e) {
    message.error(extractApiError(e, '录入失败'))
  }
}

/* ============================ 人员弹窗 ============================ */
const personModal = reactive({
  show: false,
  editingId: '' as string | null,
  code: '',
  name: '',
  bu: '能电BG',
  school: '985',
  sex: '男',
  major: '工学',
  month: '8月',
  status: '已入职',
})
function openAddPerson() {
  personModal.editingId = null
  personModal.code = ''
  personModal.name = ''
  personModal.bu = '能电BG'
  personModal.school = '985'
  personModal.sex = '男'
  personModal.major = '工学'
  personModal.month = '8月'
  personModal.status = '已入职'
  personModal.show = true
}
function openEditPerson(row: Person) {
  personModal.editingId = row.id
  personModal.code = row.code
  personModal.name = row.name
  personModal.bu = row.bu
  personModal.school = row.school
  personModal.sex = row.sex
  personModal.major = row.major
  personModal.month = row.month
  personModal.status = row.status
  personModal.show = true
}
async function savePerson() {
  if (!personModal.code.trim() || !personModal.name.trim()) {
    message.warning('请填写编码与姓名')
    return
  }
  try {
    await upsertPerson({
      id: personModal.editingId ?? undefined,
      code: personModal.code.trim(),
      name: personModal.name.trim(),
      bu: personModal.bu,
      school: personModal.school,
      sex: personModal.sex,
      major: personModal.major,
      month: personModal.month,
      status: personModal.status,
      counted: true,
    })
    message.success('保存成功')
    personModal.show = false
    await loadPersons()
  } catch (e) {
    message.error(extractApiError(e, '保存失败'))
  }
}
function removePerson(row: Person) {
  dialog.warning({
    title: '删除人员',
    content: `确认删除「${row.name}（${row.code}）」？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deletePerson(row.id)
        message.success('删除成功')
        await loadPersons()
      } catch (e) {
        message.error(extractApiError(e, '删除失败'))
      }
    },
  })
}

/* ============================ 批量导入 ============================ */
const importModal = reactive({ show: false })
const importText = ref('')

function parseImport(text: string): Partial<Person>[] {
  const trimmed = text.trim()
  if (!trimmed) return []
  // 1) 尝试 JSON 数组
  try {
    const arr = JSON.parse(trimmed)
    if (Array.isArray(arr)) return arr as Partial<Person>[]
  } catch {
    /* 非 JSON，按 CSV 解析 */
  }
  // 2) CSV：按行；首行若含表头则跳过
  const cols = ['code', 'name', 'bu', 'school', 'sex', 'major', 'month', 'status']
  const lines = trimmed.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
  let start = 0
  if (lines[0] && /编码|code/i.test(lines[0])) start = 1
  return lines.slice(start).map((line) => {
    const parts = line.split(/[,，\t]/).map((p) => p.trim())
    const o: Record<string, string> = { counted: 'true' }
    cols.forEach((c, i) => (o[c] = parts[i] ?? ''))
    return o as Partial<Person>
  })
}
async function doImport() {
  const rows = parseImport(importText.value)
  if (!rows.length) {
    message.warning('没有可导入的数据')
    return
  }
  loading.import = true
  try {
    const res = await importPersons(rows)
    message.success(
      `成功导入 ${res.createdCount} 条` + (res.errors.length ? `，${res.errors.length} 条失败` : ''),
    )
    if (res.errors.length) console.warn('[校招管控] 导入部分失败：', res.errors)
    importModal.show = false
    importText.value = ''
    await loadPersons()
  } catch (e) {
    message.error(extractApiError(e, '导入失败'))
  } finally {
    loading.import = false
  }
}

onMounted(() => {
  loadRules()
  loadRatio()
  loadPlan()
  loadPersons()
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
  flex-shrink: 0;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}
.page-subtitle {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}
.content-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.content-card :deep(.n-card__content) {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  flex-shrink: 0;
}
.filter-row {
  margin-bottom: 12px;
  flex-shrink: 0;
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
  flex-shrink: 0;
}
.kpi-card {
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.kpi-card.danger {
  background: #fef2f2;
  border-color: #fecaca;
}
.kpi-card.warn {
  background: #fffbeb;
  border-color: #fde68a;
}
.kpi-label {
  font-size: 12px;
  color: #6b7280;
}
.kpi-value {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
}
.kpi-card.danger .kpi-value {
  color: #dc2626;
}
.kpi-card.warn .kpi-value {
  color: #d97706;
}
.validate-result {
  margin-top: 16px;
}
.block-hint {
  color: #dc2626;
  font-size: 13px;
  margin: 8px 0 0;
}
</style>
