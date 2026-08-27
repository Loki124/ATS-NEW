<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">校招管控</h1>
        <p class="page-subtitle">人员比例管控 · 每条规则独立适用范围（全局 / 部门·职务·职级）· 指标库 + 规则增删改</p>
      </div>
    </div>

    <div class="glass-panel">
      <n-tabs v-model:value="activeTab" type="line" class="cc-tabs" @update:value="onTabChange">
        <!-- ===================== 实时看板（含人数规划） ===================== -->
        <n-tab-pane name="ratio" tab="实时看板">
          <n-alert v-if="hasBadSum" type="warning" :show-icon="true" style="margin-bottom: 14px">
            存在目标占比未加和到 100% 的维度（见下方「加和」状态），请前往「规则配置」补全。
          </n-alert>
          <div class="kpi-row">
            <div class="kpi-card"><span class="kpi-label">计入核算人数</span><span class="kpi-value">{{ ratioData.total }}</span></div>
            <div class="kpi-card"><span class="kpi-label">管控规则数</span><span class="kpi-value">{{ ratioData.rows.length }}</span></div>
            <div class="kpi-card danger"><span class="kpi-label">硬约束超标</span><span class="kpi-value">{{ ratioKpi.hard }}</span></div>
            <div class="kpi-card warn"><span class="kpi-label">软/仅提示超标</span><span class="kpi-value">{{ ratioKpi.soft }}</span></div>
          </div>
          <div class="table-wrap">
            <n-data-table
              :columns="ratioColumns"
              :data="ratioData.rows"
              :loading="loading.ratio"
              :row-key="(r: any) => [r.bu, r.position, r.level, r.dimension, r.indicator].join('|')"
              :pagination="false"
              flex-height
            >
              <template #empty><n-empty description="暂无数据" /></template>
            </n-data-table>
          </div>

          <n-alert type="info" :show-icon="true" style="margin-top: 16px; flex-shrink: 0">
            实时看板按「每条规则独立适用范围」展示各指标的<strong>占比管控</strong>（实际/分母、占比、目标、占比状态）。
            各指标的<strong>年度 / 月度管控人数</strong>在「规则配置」→编辑维度规则集中维护，目标数据直接承载于规则上。
          </n-alert>
        </n-tab-pane>

        <!-- ===================== 规则配置（扁平列表：每条规则一行） ===================== -->
        <n-tab-pane name="rules" tab="规则配置">
          <n-alert
            v-if="mixedScopeGroups.size > 0"
            type="warning"
            :show-icon="true"
            class="scope-mutex-banner"
          >
            检测到 <b>{{ mixedScopeGroups.size }}</b> 个「维度 × 年度」组合同时存在「全局」与「指定范围」规则，会导致人员<b>重复计入</b>。请调整适用范围（编辑规则或删除其一）。
          </n-alert>

          <div class="toolbar">
            <n-button @click="onExportRules">导出规则</n-button>
            <n-button @click="importDrawer.show = true">导入规则</n-button>
            <div class="spacer"></div>
            <n-button type="primary" class="gradient-btn" @click="openRuleDrawer(null)">+ 新增规则</n-button>
          </div>

          <div class="table-wrap">
            <n-data-table
              :columns="ruleColumns"
              :data="rules"
              :loading="loading.rules"
              :row-key="(r: any) => r.id"
              :pagination="false"
              flex-height
              :row-props="ruleRowProps"
            >
              <template #empty>
                <n-empty description="暂无规则，点击右上角「新增规则」" />
              </template>
            </n-data-table>
          </div>

          <RuleConfigDrawer
            v-model:show="ruleDrawer.show"
            :rule="ruleDrawer.rule"
            :mode="ruleDrawer.mode"
            @saved="onRuleSaved"
          />
        </n-tab-pane>

        <!-- ===================== 指标管理（维度 + 指标库） ===================== -->
        <n-tab-pane name="indicators" tab="指标管理">
          <div class="toolbar">
            <n-select v-model:value="indicatorDimFilter" :options="indicatorDimOptions" placeholder="全部维度" clearable style="width: 180px" />
            <n-button @click="openDimDrawer()">管理维度</n-button>
            <div class="spacer"></div>
            <n-dropdown :options="indicatorExportOptions" @select="onExportIndicatorsSelect">
              <n-button>导出指标</n-button>
            </n-dropdown>
            <n-button @click="onDownloadIndicatorTemplate">下载模板</n-button>
            <n-button @click="indicatorImportDrawer.show = true">导入指标</n-button>
            <n-button type="primary" class="gradient-btn" @click="openIndicatorModal()">+ 新增指标</n-button>
          </div>
          <div class="table-wrap">
            <n-data-table
              :columns="indicatorColumns"
              :data="filteredIndicators"
              :loading="loading.indicators"
              :row-key="(r: any) => r.id"
              :pagination="false"
              flex-height
            >
              <template #empty><n-empty description="暂无指标，请先新增维度，再在维度下新增指标" /></template>
            </n-data-table>
          </div>
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
          <div class="toolbar">
            <n-button type="primary" class="gradient-btn" :loading="loading.validate" @click="runValidate">校验判定</n-button>
            <n-button :disabled="!canConfirmEntry" @click="confirmEntry">确认录入为人员</n-button>
          </div>

          <div v-if="validation" class="validate-result">
            <n-tag :type="verdictType(validation.verdict)" size="large" :bordered="false" style="flex-shrink: 0">
              {{ validation.verdict }}
            </n-tag>
            <p v-if="validation.verdict === '❌ 阻断提交'" class="block-hint" style="flex-shrink: 0">
              命中硬约束超标，系统已阻断提交。请调整候选人标签或目标配置后再试。
            </p>
            <div class="table-wrap" style="margin-top: 12px">
              <n-data-table
                :columns="checkColumns"
                :data="validation.checks"
                :row-key="(r: any) => [r.dimension, r.indicator, r.bu, r.position, r.level].join('|')"
                :pagination="false"
                flex-height
              >
                <template #empty><n-empty description="无校验明细" /></template>
              </n-data-table>
            </div>
          </div>
        </n-tab-pane>

        <!-- ===================== 人员数据 ===================== -->
        <n-tab-pane name="persons" tab="人员数据">
          <div class="toolbar">
            <div class="spacer"></div>
            <n-button type="primary" class="gradient-btn" @click="openPersonModal()">+ 新增人员</n-button>
          </div>
          <div class="table-wrap">
            <n-data-table
              :columns="personColumns"
              :data="persons"
              :loading="loading.persons"
              :row-key="(r: any) => r.id"
              :pagination="false"
              flex-height
            >
              <template #empty><n-empty description="暂无人员" /></template>
            </n-data-table>
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>


    <!-- ===================== 导入规则弹窗（页面居中） ===================== -->
    <n-modal
      v-model:show="importDrawer.show"
      preset="card"
      title="导入规则（Excel）"
      :style="{ width: '600px', maxWidth: '94vw' }"
      :bordered="false"
      :segmented="{ content: true, footer: true }"
      class="import-modal"
    >
      <n-space vertical :size="14">
        <n-upload
          accept=".xlsx,.xlsm"
          :max="1"
          :custom-request="handleImportUpload"
          v-model:file-list="importDrawer.fileList"
          @remove="onImportFileRemove"
        >
          <n-button>选择 Excel 文件</n-button>
        </n-upload>
        <n-space align="center" :wrap="false">
          <n-button size="small" quaternary type="primary" @click="onDownloadTemplate">下载模板</n-button>
          <span class="import-hint" style="margin: 0">
            每行一条规则，同一「部门+职务+职级+维度+规划年度」下目标占比之和须 = 100%，且 12 个月目标之和须等于年度目标人数。
          </span>
        </n-space>
        <div v-if="importDrawer.result" class="import-result">
          <n-alert
            v-if="importDrawer.result.success"
            type="success"
            :show-icon="true"
          >
            导入成功：{{ importDrawer.result.data.groups }} 个分组 / {{ importDrawer.result.data.savedRules }} 条规则已写入。
          </n-alert>
          <n-alert v-else type="error" :show-icon="true">
            导入失败（{{ importDrawer.result.data.groups }} 个分组 / 已写入 {{ importDrawer.result.data.savedRules }} 条），请下载错误明细 Excel 修正后重传。
          </n-alert>
          <div v-if="importDrawer.result && importDrawer.result.data.errors.length" class="import-error-actions">
            <n-button v-if="importDrawer.result.data.errorFile" size="small" type="error" @click="downloadImportErrorExcel">下载错误明细（Excel）</n-button>
            <n-button v-else size="small" @click="downloadImportErrorReport">下载错误报告（txt）</n-button>
          </div>
          <ul v-if="importDrawer.result && importDrawer.result.data.errors.length" class="import-errors">
            <li v-for="(e, i) in importDrawer.result.data.errors" :key="i">{{ e }}</li>
          </ul>
        </div>
      </n-space>
      <template #footer>
        <div class="drawer-footer">
          <n-button @click="importDrawer.show = false">关闭</n-button>
        </div>
      </template>
    </n-modal>

    <!-- ===================== 导入指标弹窗（页面居中） ===================== -->
    <n-modal
      v-model:show="indicatorImportDrawer.show"
      preset="card"
      title="导入指标（Excel / CSV）"
      :style="{ width: '600px', maxWidth: '94vw' }"
      :bordered="false"
      :segmented="{ content: true, footer: true }"
      class="import-modal"
    >
      <n-space vertical :size="14">
        <n-radio-group v-model:value="indicatorImportDrawer.mode" name="indicator-import-mode">
          <n-space>
            <n-radio value="skip">跳过已存在</n-radio>
            <n-radio value="update">更新已存在</n-radio>
            <n-radio value="error">遇重复即报错</n-radio>
          </n-space>
        </n-radio-group>
        <n-upload
          accept=".xlsx,.xlsm,.csv"
          :max="1"
          :custom-request="handleIndicatorImportUpload"
          v-model:file-list="indicatorImportDrawer.fileList"
          @remove="onIndicatorImportFileRemove"
        >
          <n-button>选择 Excel / CSV 文件</n-button>
        </n-upload>
        <n-space align="center" :wrap="false">
          <n-button size="small" quaternary type="primary" @click="onDownloadIndicatorTemplate">下载模板</n-button>
          <span class="import-hint" style="margin: 0">
            每行一条指标，列：维度 / 指标名称 / 是否启用（是/否）。指标名称同维度下不可重复。
          </span>
        </n-space>
        <div v-if="indicatorImportDrawer.result" class="import-result">
          <n-alert v-if="indicatorImportDrawer.result.success" type="success" :show-icon="true">
            导入成功：新建 {{ indicatorImportDrawer.result.data.created }} / 更新 {{ indicatorImportDrawer.result.data.updated }} / 跳过 {{ indicatorImportDrawer.result.data.skipped }} 条。
          </n-alert>
          <n-alert v-else type="error" :show-icon="true">
            导入失败（已跳过 {{ indicatorImportDrawer.result.data.skipped }} / 已新建 {{ indicatorImportDrawer.result.data.created }}），请下载错误明细 Excel 修正后重传。
          </n-alert>
          <div v-if="indicatorImportDrawer.result && indicatorImportDrawer.result.data.errors.length" class="import-error-actions">
            <n-button v-if="indicatorImportDrawer.result.data.errorFile" size="small" type="error" @click="downloadIndicatorImportErrorExcel">下载错误明细（Excel）</n-button>
          </div>
          <ul v-if="indicatorImportDrawer.result && indicatorImportDrawer.result.data.errors.length" class="import-errors">
            <li v-for="(e, i) in indicatorImportDrawer.result.data.errors" :key="i">{{ e }}</li>
          </ul>
        </div>
      </n-space>
      <template #footer>
        <div class="drawer-footer">
          <n-button @click="indicatorImportDrawer.show = false">关闭</n-button>
        </div>
      </template>
    </n-modal>

    <!-- ===================== 维度管理弹窗（页面居中） ===================== -->
    <n-modal
      v-model:show="dimDrawer.show"
      preset="card"
      title="维度管理"
      :style="{ width: '560px', maxWidth: '94vw' }"
      :bordered="false"
      :segmented="{ content: true, footer: true }"
      class="dim-modal"
    >
      <n-space vertical :size="12">
        <div class="toolbar" style="margin-bottom: 0">
          <div class="spacer"></div>
          <n-button type="primary" class="gradient-btn" @click="openDimModal()">+ 新增维度</n-button>
        </div>
        <n-data-table
          :columns="dimColumns"
          :data="dimensions"
          :loading="loading.dimensions"
          :row-key="(r: any) => r.id"
          :pagination="false"
          size="small"
        >
          <template #empty><n-empty description="暂无维度" /></template>
        </n-data-table>
      </n-space>
    </n-modal>

    <!-- ===================== 维度表单弹窗 ===================== -->
    <n-modal v-model:show="dimModal.show" :title="dimModal.editingId ? '编辑维度' : '新增维度'" preset="card" style="width: 420px">
      <n-form label-placement="top">
        <n-form-item label="维度名称" required><n-input v-model:value="dimModal.name" placeholder="如 学历 / 院校标签 / 专业标签" /></n-form-item>
        <n-form-item label="编码"><n-input v-model:value="dimModal.code" placeholder="可选，如 education" /></n-form-item>
      </n-form>
      <template #footer>
        <div class="drawer-footer">
          <n-button @click="dimModal.show = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" :loading="loading.dimensions" @click="saveDim">保存</n-button>
        </div>
      </template>
    </n-modal>

    <!-- ===================== 指标表单弹窗 ===================== -->
    <n-modal v-model:show="indicatorModal.show" :title="indicatorModal.editingId ? '编辑指标' : '新增指标'" preset="card" style="width: 420px">
      <n-form label-placement="top">
        <n-form-item label="所属维度" required><n-select v-model:value="indicatorModal.dimensionId" :options="dimensionOptions" :disabled="!!indicatorModal.editingId" /></n-form-item>
        <n-form-item label="指标名称" required><n-input v-model:value="indicatorModal.name" placeholder="如 985 / 男 / 工学" /></n-form-item>
      </n-form>
      <template #footer>
        <div class="drawer-footer">
          <n-button @click="indicatorModal.show = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" :loading="loading.indicators" @click="saveIndicator">保存</n-button>
        </div>
      </template>
    </n-modal>

    <!-- ===================== 人员表单弹窗 ===================== -->
    <n-modal v-model:show="personModal.show" :title="personModal.editingId ? '编辑人员' : '新增人员'" preset="card" style="width: 560px">
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
          <n-gi><n-form-item label="预计入职日期"><n-date-picker v-model:formatted-value="personModal.expectedEntryDate" value-format="yyyy-MM-dd" type="date" clearable style="width:100%" /></n-form-item></n-gi>
          <n-gi><n-form-item label="实际入职日期"><n-date-picker v-model:formatted-value="personModal.actualEntryDate" value-format="yyyy-MM-dd" type="date" clearable style="width:100%" /></n-form-item></n-gi>
          <n-gi><n-form-item label="职务"><n-select v-model:value="personModal.position" :options="positionOptions" clearable placeholder="不限" /></n-form-item></n-gi>
          <n-gi><n-form-item label="职级"><n-select v-model:value="personModal.level" :options="levelOptions" clearable placeholder="不限" /></n-form-item></n-gi>
          <n-gi><n-form-item label="计入核算"><n-switch v-model:value="personModal.counted" /></n-form-item></n-gi>
        </n-grid>
      </n-form>
      <template #footer>
        <div class="drawer-footer">
          <n-button @click="personModal.show = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" :loading="loading.persons" @click="savePerson">保存</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h, onMounted, watch } from 'vue'
import {
  NTag, NButton, NSwitch, NCheckbox, NDivider, NSpace,
  NInputNumber, NSelect, NInput, NEmpty, NAlert, NDatePicker, NTooltip,
  useMessage, useDialog, type DataTableColumns,
} from 'naive-ui'
import { extractApiError } from '../../api/dynamic-field'
import {
  listDimensions, createDimension, updateDimension, deleteDimension,
  listIndicators, createIndicator, updateIndicator, deleteIndicator,
  listRules, saveDimensionRuleSet,
  getRatio, validateDraft,
  listPersons, upsertPerson, deletePerson,
  exportRules, downloadRuleTemplate, importRules, triggerDownload,
  exportIndicators, downloadIndicatorTemplate, importIndicators,
  DEPTS, SCHOOLS, MAJORS, SEXES, ALL_MONTHS, STRENGTH, STATUS, POSITIONS, LEVELS,
  type ControlDimension, type ControlIndicator, type ControlRule,
  type Person, type RatioRow, type RatioResult,
  type ValidationResult, type Strength, type DimRuleSetItem,
  type RuleImportResult, type IndicatorImportResult,
} from '../../api/campusControl'
import RuleConfigDrawer from '../../components/RuleConfigDrawer.vue'
import { useRuleActions } from '../../composables/useRuleActions'

const message = useMessage()
const dialog = useDialog()

/* ============================ 选项 ============================ */
const opt = (arr: readonly string[]) => arr.map((v) => ({ label: v, value: v }))
const deptOptions = opt(DEPTS)
const schoolOptions = opt(SCHOOLS)
const majorOptions = opt(MAJORS)
const sexOptions = opt(SEXES)
const monthOptions = opt(ALL_MONTHS)
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

const scopeText = (bu: string, position: string, level: string) => {
  if (!bu && !position && !level) return '全局'
  const parts = [bu, position || '职务不限', level || '职级不限']
  return parts.filter(Boolean).join(' · ')
}

/* ============================ 全局状态 ============================ */
const activeTab = ref('ratio')
const loading = reactive({
  ratio: false, plan: false, rules: false, saveDimRuleSet: false,
  dimensions: false, indicators: false, persons: false, validate: false,
  import: false,
})
const dimensions = ref<ControlDimension[]>([])
const indicators = ref<ControlIndicator[]>([])
const rules = ref<ControlRule[]>([])
const persons = ref<Person[]>([])

const dimensionOptions = computed(() => dimensions.value.map((d) => ({ label: d.name, value: d.id })))

/* ============================ 实时看板 ============================ */
const ratioData = ref<RatioResult>({ total: 0, rows: [], sumChecks: [] })
const ratioKpi = computed(() => {
  const rows = ratioData.value.rows
  return {
    hard: rows.filter((r) => r.status !== '正常' && r.strength === '硬约束').length,
    soft: rows.filter((r) => r.status !== '正常' && r.strength !== '硬约束').length,
  }
})
const hasBadSum = computed(() => ratioData.value.sumChecks.some((s) => !s.ok))

/* ============================ 规则配置 ============================ */
const currentMonthIdx = computed(() => new Date().getMonth()) // 0=1月

// 同一 (dimension, year) 下若同时含「全局」与「指定范围」规则集 → 重复计入风险（⚠️ 徽标）。
// 后端已对新写入做互斥拦截，此徽标仅用于提示存量（legacy）混合数据，需用户手动清理。
const mixedScopeGroups = computed<Set<string>>(() => {
  const scopesByGroup = new Map<string, Set<string>>()
  for (const r of rules.value) {
    const gk = [r.dimension, r.year].join('|')
    const sk = (r.bu || r.position || r.level) ? 'specific' : 'global'
    if (!scopesByGroup.has(gk)) scopesByGroup.set(gk, new Set())
    scopesByGroup.get(gk)!.add(sk)
  }
  const mixed = new Set<string>()
  for (const [gk, s] of scopesByGroup) {
    if (s.has('global') && s.has('specific')) mixed.add(gk)
  }
  return mixed
})

/* ============================ 规则配置：维度列表(master) + 维度详情(detail) ============================ */
const MONTH_LABELS = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']

// master/detail 导航状态（detail 改为弹窗，不再整页切换）
const detailDimensionId = ref<string | null>(null)
const dimensionEditModal = ref(false)
const dimEditSaving = ref(false)
const dimEditId = ref<string | null>(null)
const dimEditName = ref('')
const dimEditYear = ref<number>(new Date().getFullYear())
const dimEditAnnual = ref<number>(0)
const detailScopeKey = ref<string>('||')
const detailYear = ref<number>(new Date().getFullYear())

function scopeKeyOf(bu: string, position: string, level: string) {
  return [bu || '', position || '', level || ''].join('|')
}
function keyToScope(key: string) {
  const [bu = '', position = '', level = ''] = key.split('|')
  return { bu, position, level }
}
const detailDimensionName = computed(
  () => dimensions.value.find((d) => d.id === detailDimensionId.value)?.name || '',
)

// master：每维度一行，聚合「指标数 / 规则集数 / 加和状态 / 范围冲突」
const dimensionRuleSummary = computed(() =>
  dimensions.value.map((d) => {
    const dRules = rules.value.filter((r) => r.dimension === d.id)
    const groups = new Map<string, number>()
    const yearsSet = new Set<number>()
    for (const r of dRules) {
      const k = scopeKeyOf(r.bu, r.position, r.level) + '#' + r.year
      groups.set(k, (groups.get(k) || 0) + r.target)
      yearsSet.add(Number(r.year))
    }
    // 「归属年度」：单一年度直接显示；多年份按升序并列（如 "2025 / 2026"），避免隐藏信息。
    const years = Array.from(yearsSet).sort((a, b) => a - b)
    const yearLabels = years.length === 0 ? '—' : years.map(String).join(' / ')
    // 「年度目标(人)」：该维度所有规则的 annualTarget 之和（与详情页「维度年度管控人数」一致口径）。
    const annualTotal = dRules.reduce((s, r) => s + (Number(r.annualTarget) || 0), 0)
    let badSum = false
    for (const s of groups.values()) if (Math.abs(s - 1) >= 0.0005) badSum = true
    const hasMutex = [...mixedScopeGroups.value].some((gk) => gk.startsWith(d.id + '|'))
    const indicatorCount = indicators.value.filter((i) => i.dimension === d.id).length
    return {
      id: d.id,
      name: d.name,
      code: d.code,
      indicatorCount,
      yearLabels,
      annualTotal,
      ruleSetCount: groups.size,
      sumOk: !badSum && dRules.length > 0,
      mutex: hasMutex,
    }
  }),
)

// detail：选中维度后，按 (适用范围, 年度) 筛选，展示该维度下所有指标的年度/月度目标
const detailScopeOptions = computed(() => {
  if (!detailDimensionId.value) return []
  const seen = new Set<string>()
  const opts: { label: string; value: string }[] = []
  for (const r of rules.value) {
    if (r.dimension !== detailDimensionId.value) continue
    const k = scopeKeyOf(r.bu, r.position, r.level)
    if (!seen.has(k)) {
      seen.add(k)
      opts.push({ label: scopeText(r.bu, r.position, r.level), value: k })
    }
  }
  return opts
})
const detailYearOptions = computed(() => {
  if (!detailDimensionId.value) return []
  const seen = new Set<number>()
  const opts: { label: string; value: number }[] = []
  for (const r of rules.value) {
    if (r.dimension !== detailDimensionId.value) continue
    if (!seen.has(r.year)) {
      seen.add(r.year)
      opts.push({ label: String(r.year), value: r.year })
    }
  }
  return opts.sort((a, b) => a.value - b.value)
})
const detailMatrix = computed(() => {
  if (!detailDimensionId.value) return []
  const scope = keyToScope(detailScopeKey.value)
  const matched = rules.value.filter(
    (r) =>
      r.dimension === detailDimensionId.value &&
      (r.bu || '') === scope.bu && (r.position || '') === scope.position && (r.level || '') === scope.level &&
      r.year === detailYear.value,
  )
  const byInd = new Map(matched.map((r) => [r.indicator, r]))
  return indicators.value
    .filter((i) => i.dimension === detailDimensionId.value)
    .map((i) => {
      const r = byInd.get(i.id)
      return {
        indicatorId: i.id,
        indicatorName: i.name,
        configured: !!r,
        targetPct: r ? Math.round(r.target * 1000) / 10 : null,
        annualTarget: r ? Math.round(r.annualTarget) : null,
        monthlyTargets: r ? normalizeMonthly(r.monthlyTargets) : Array(12).fill(0),
      }
    })
})
const detailSumOk = computed(() => {
  const s = detailMatrix.value.filter((r) => r.configured).reduce((a, r) => a + (r.targetPct || 0), 0)
  return Math.abs(s - 100) < 0.05
})

function selectDimension(id: string) {
  detailDimensionId.value = id
  const scopes = detailScopeOptions.value
  const years = detailYearOptions.value
  const sk = scopes.length ? scopes[0].value : scopeKeyOf('', '', '')
  const yr = years.length ? years[0].value : new Date().getFullYear()
  detailScopeKey.value = sk
  detailYear.value = yr
  // 直接打开 dimEditor 弹窗的 view 模式（融合旧指标详情弹窗）
  openDetailView(id, sk, yr)
}

/**
 * 从 master 列表打开 dimEditor 弹窗的 view 模式（融合旧 indicatorDetailModal）。
 * - view 模式下 lockContext 解除，主体渲染 detailMatrix；顶部 (scope, year) 切换器即时刷新。
 * - 点底部「编辑」进入 edit 模式（lockContext=true），上下文锁定。
 */
function openDetailView(dimensionId: string, scopeKey: string, year: number) {
  const scope = keyToScope(scopeKey)
  dimEditor.dimensionId = dimensionId
  dimEditor.isGlobal = !(scope.bu || scope.position || scope.level)
  dimEditor.bu = scope.bu
  dimEditor.position = scope.position
  dimEditor.level = scope.level
  dimEditor.year = year
  // view 模式不锁上下文——允许顶部 (scope, year) 切换器即时切换查看
  dimEditor.lockContext = false
  dimEditor.originalScope = { bu: scope.bu, position: scope.position, level: scope.level, year }
  dimEditor.scopeDirty = false
  dimEditor.mode = 'view'
  dimEditor.show = true
  _buildDimRows()
}

// 复用 dimEditor 打开「选中维度 + 选中适用范围 + 选中年度」的规则集（不依赖单条规则推断）
function openDetailEditor() {
  if (!detailDimensionId.value) return
  const scope = keyToScope(detailScopeKey.value)
  dimEditor.dimensionId = detailDimensionId.value
  dimEditor.isGlobal = !(scope.bu || scope.position || scope.level)
  dimEditor.bu = scope.bu
  dimEditor.position = scope.position
  dimEditor.level = scope.level
  dimEditor.year = detailYear.value
  dimEditor.lockContext = true
  dimEditor.originalScope = { bu: scope.bu, position: scope.position, level: scope.level, year: detailYear.value }
  dimEditor.scopeDirty = false
  dimEditor.mode = 'view'
  dimEditor.show = true
  _buildDimRows()
}
// G5 清空入口：打开即把所有指标行标记为「待删」，保存即走后端清空分支
function openDetailClear() {
  openDetailEditor()
  for (const row of dimEditor.rows) row.pendingDelete = true
  dimEditor.mode = 'edit'
}

// 维度层级编辑入口：打开弹窗，预填该维度的「归属年度 + 年度目标」（从 master 聚合行取）
function openDimensionEdit(d: any) {
  dimEditId.value = d.id
  dimEditName.value = d.name
  // 取该维度规则中的主年度（多年份取最大）与主年度对应年度目标之和
  const dRules = rules.value.filter((r) => r.dimension === d.id)
  const years = Array.from(new Set(dRules.map((r) => Number(r.year)))).sort((a, b) => a - b)
  const primaryYear = years.length ? years[years.length - 1] : new Date().getFullYear()
  const annual = dRules
    .filter((r) => Number(r.year) === primaryYear)
    .reduce((s, r) => s + (Number(r.annualTarget) || 0), 0)
  dimEditYear.value = primaryYear
  dimEditAnnual.value = annual
  dimensionEditModal.value = true
}

// 最大余数法：把整数 total 按权重(和≈1)精确分配为若干整数，保证加和严格 == total
function _largestRemainder(total: number, weights: number[]): number[] {
  const n = weights.length
  if (n === 0) return []
  total = Math.max(0, Math.round(total))
  if (total <= 0) return new Array(n).fill(0)
  const wsum = weights.reduce((a, b) => a + b, 0) || 1
  const norm = weights.map((w) => w / wsum)
  const exact = norm.map((w) => total * w)
  const floors = exact.map(Math.floor)
  let remainder = total - floors.reduce((a, b) => a + b, 0)
  const order = exact.map((_, i) => i).sort((a, b) => (exact[b] - floors[b]) - (exact[a] - floors[a]))
  const alloc = floors.slice()
  for (let i = 0; i < remainder; i++) alloc[order[i % n]] += 1
  return alloc
}

// 按比例缩放 12 月数组使其和 == newAnnual（余数用最大余数法分摊）
function _scaleMonthly(oldMonthly: number[], newAnnual: number): number[] {
  const sum = oldMonthly.reduce((a, b) => a + b, 0)
  if (sum <= 0) {
    const base = Math.floor(newAnnual / 12)
    const rem = newAnnual - base * 12
    return Array.from({ length: 12 }, (_, i) => base + (i < rem ? 1 : 0))
  }
  return _largestRemainder(newAnnual, oldMonthly.map((m) => m / sum))
}

// 维度层级保存：把「归属年度 + 年度目标」扇出到该维度下所有适用范围（按各范围当前占比分配），逐 scope 调 set_rules
async function saveDimensionAnnualEdit() {
  if (!dimEditId.value) return
  const dimId = dimEditId.value
  const newYear = dimEditYear.value
  const newAnnual = Math.max(0, Math.round(dimEditAnnual.value || 0))
  const dRules = rules.value.filter((r) => r.dimension === dimId)
  if (dRules.length === 0) {
    message.warning('该维度下暂无规则，无法设置年度目标')
    return
  }
  // 按适用范围分组
  const scopeMap = new Map<string, any[]>()
  for (const r of dRules) {
    const k = scopeKeyOf(r.bu, r.position, r.level)
    if (!scopeMap.has(k)) scopeMap.set(k, [])
    scopeMap.get(k)!.push(r)
  }
  const scopes = [...scopeMap.entries()]
  const n = scopes.length
  const currentTotal = dRules.reduce((s, r) => s + (Number(r.annualTarget) || 0), 0)
  const scopeWeights = scopes.map(([, rs]) => {
    const sa = rs.reduce((s, r) => s + (Number(r.annualTarget) || 0), 0)
    return currentTotal > 0 ? sa / currentTotal : 1 / n
  })
  const scopeAnnuals = _largestRemainder(newAnnual, scopeWeights)
  dimEditSaving.value = true
  try {
    for (let i = 0; i < scopes.length; i++) {
      const [key, rs] = scopes[i]
      const scope = keyToScope(key)
      const scopeNewAnnual = scopeAnnuals[i]
      const curScopeAnnual = rs.reduce((s, r) => s + (Number(r.annualTarget) || 0), 0)
      const indWeights = rs.map((r) => (curScopeAnnual > 0 ? (Number(r.annualTarget) || 0) / curScopeAnnual : 1 / rs.length))
      const indAnnuals = _largestRemainder(scopeNewAnnual, indWeights)
      const items: DimRuleSetItem[] = rs.map((r, j) => ({
        indicator: r.indicator,
        target: r.target,
        strength: r.strength,
        annualTarget: indAnnuals[j],
        monthlyTargets: _scaleMonthly(normalizeMonthly(r.monthlyTargets), indAnnuals[j]),
      }))
      await saveDimensionRuleSet(dimId, {
        bu: scope.bu, position: scope.position, level: scope.level,
        year: newYear, rules: items, totalTarget: scopeNewAnnual,
      })
    }
    message.success('维度年度目标已更新')
    dimensionEditModal.value = false
    await loadRules()
  } catch (e) {
    message.error(extractApiError(e, '保存失败'))
  } finally {
    dimEditSaving.value = false
  }
}

/* ============================ 指标管理 ============================ */
const indicatorDimFilter = ref<string | null>(null)
const indicatorDimOptions = computed(() => [
  { label: '全部维度', value: '' },
  ...dimensions.value.map((d) => ({ label: d.name, value: d.id })),
])
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
async function loadRules() {
  loading.rules = true
  try { rules.value = await listRules() }
  catch (e) { message.error(extractApiError(e, '加载规则失败')) }
  finally { loading.rules = false }
}

/* ============================ 规则配置：扁平列表 ============================ */
const ruleActions = useRuleActions(() => loadRules())

const ruleDrawer = reactive({
  show: false,
  rule: null as ControlRule | null,
  mode: 'view' as 'view' | 'create' | 'edit',
})
function openRuleDrawer(rule: ControlRule | null, mode: 'view' | 'create' | 'edit' = 'view') {
  ruleDrawer.rule = rule
  ruleDrawer.mode = rule ? mode : 'create'
  ruleDrawer.show = true
}
function onRuleSaved() {
  loadRules()
}

const ruleRowProps = (row: any) => ({
  style: 'cursor:pointer',
  onClick: () => openRuleDrawer(row, 'view'),
})

const ruleColumns: DataTableColumns<any> = [
  {
    title: '规则编号', key: 'code', width: 110, fixed: 'left',
    render: (r: any) =>
      h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: (e: MouseEvent) => { e.stopPropagation(); openRuleDrawer(r, 'view') } }, { default: () => r.code || '—' }),
  },
  { title: '维度', key: 'dimensionName', width: 100, render: (r: any) => r.dimensionName || r.dimension },
  { title: '指标', key: 'indicatorName', width: 110, render: (r: any) => r.indicatorName || r.indicator },
  { title: '适用范围', key: 'scope', width: 200, render: (r: any) => scopeText(r.bu, r.position, r.level) },
  { title: '生效年度', key: 'year', width: 90, render: (r: any) => String(r.year) },
  {
    title: '年度目标(人)', key: 'annualTarget', width: 110,
    render: (r: any) => (r.annualTarget ? String(Math.round(r.annualTarget)) : h('span', { class: 'muted' }, '—')),
  },
  {
    title: '控制强度', key: 'strength', width: 120,
    render: (r: any) => (r.strength
      ? h(NTag, { type: strengthType(r.strength), bordered: false, size: 'small' }, { default: () => r.strength })
      : h('span', { class: 'muted' }, '—')),
  },
  {
    title: '启用状态', key: 'isActive', width: 100,
    render: (r: any) => h(NTag, { type: r.isActive ? 'success' : 'default', bordered: false, size: 'small' }, { default: () => (r.isActive ? '启用' : '停用') }),
  },
  {
    title: '操作', key: 'op', width: 210, fixed: 'right',
    render: (r: any) =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'small', tertiary: true, onClick: (e: MouseEvent) => { e.stopPropagation(); ruleActions.copy(r) } }, { default: () => '复制' }),
          h(NButton, { size: 'small', tertiary: true, type: r.isActive ? 'warning' : 'success', onClick: (e: MouseEvent) => { e.stopPropagation(); ruleActions.toggle(r, !r.isActive) } }, { default: () => (r.isActive ? '停用' : '启用') }),
          h(NButton, { size: 'small', tertiary: true, type: 'error', onClick: (e: MouseEvent) => { e.stopPropagation(); ruleActions.remove(r) } }, { default: () => '删除' }),
        ],
      }),
  },
]

async function loadPersons() {
  loading.persons = true
  try { persons.value = await listPersons() }
  catch (e) { message.error(extractApiError(e, '加载人员失败')) }
  finally { loading.persons = false }
}
async function loadRatio() {
  loading.ratio = true
  try { ratioData.value = await getRatio() }
  catch (e) { message.error(extractApiError(e, '加载看板失败')) }
  finally { loading.ratio = false }
}
function onTabChange(name: string) {
  if (name === 'ratio') { loadRatio() }
  else if (name === 'rules') loadRules()
  else if (name === 'persons') loadPersons()
  else if (name === 'indicators') loadIndicators()
}

/* ============================ 列定义 ============================ */
// 实时看板：占比管控（每条规则独立适用范围）
const ratioColumns: DataTableColumns<any> = [
  { title: '适用范围', key: 'bu', width: 150, fixed: 'left', render: (r) => scopeText(r.bu, r.position, r.level) },
  { title: '维度', key: 'dimension', width: 90, fixed: 'left' },
  { title: '指标', key: 'indicator', width: 80, fixed: 'left' },
  { title: '实际/分母', key: 'actual', width: 100, render: (r) => `${r.actual ?? '-'} / ${r.denom ?? '-'}` },
  { title: '占比', key: 'ratio', width: 76, render: (r) => r.ratio == null ? h(NTag, { type: 'default', bordered: false, size: 'small' }, { default: () => '—' }) : h(NTag, { type: 'default', bordered: false, size: 'small' }, { default: () => pct(r.ratio) }) },
  { title: '目标', key: 'target', width: 68, render: (r) => r.target == null ? '—' : pct(r.target) },
  { title: '占比状态', key: 'status', width: 100, render: (r) => h(NTag, { type: ratioStatusType(r.status || '正常'), bordered: false, size: 'small' }, { default: () => r.status || '—' }) },
  { title: '强度', key: 'strength', width: 88, render: (r) => r.strength ? h(NTag, { type: strengthType(r.strength), bordered: false, size: 'small' }, { default: () => r.strength }) : h('span', { style: 'color:var(--ink-soft)' }, '—') },
]

const dimensionRuleColumns: DataTableColumns<any> = [
  {
    title: '维度名称', key: 'name',
    render: (d: any) => h('div', { style: 'display:flex; align-items:center; gap:8px;' }, [
      h('span', { style: 'font-weight:600;' }, d.name),
      d.code ? h(NTag, { size: 'small', bordered: false, type: 'default' }, { default: () => d.code }) : null,
    ]),
  },
  { title: '归属年度', key: 'yearLabels', width: 110, render: (d: any) => h('span', { class: 'muted' }, d.yearLabels) },
  { title: '年度目标(人)', key: 'annualTotal', width: 130, render: (d: any) => (d.annualTotal > 0 ? h('span', {}, String(d.annualTotal)) : h('span', { class: 'muted' }, '—')) },
  { title: '指标数', key: 'indicatorCount', width: 90, render: (d: any) => h('span', { class: 'muted' }, String(d.indicatorCount)) },
  { title: '规则集(适用范围×年度)', key: 'ruleSetCount', width: 170, render: (d: any) => h('span', { class: 'muted' }, String(d.ruleSetCount)) },
  {
    title: '加和状态', key: 'sumOk', width: 140,
    render: (d: any) => {
      if (d.mutex) return h(NTag, { type: 'error', bordered: false, size: 'small' }, { default: () => '⚠ 范围冲突' })
      if (!d.sumOk) return h(NTag, { type: 'warning', bordered: false, size: 'small' }, { default: () => '⚠ 未达100%' })
      return h(NTag, { type: 'success', bordered: false, size: 'small' }, { default: () => '✓ 100%' })
    },
  },
  {
    title: '操作', key: 'actions', width: 170, fixed: 'right',
    render: (d: any) => h('div', { style: 'display:flex; gap:8px;' }, [
      h(NButton, { size: 'small', type: 'primary', quaternary: true, onClick: () => openDimensionEdit(d) }, { default: () => '编辑维度' }),
      h(NButton, { size: 'small', quaternary: true, onClick: () => selectDimension(d.id) }, { default: () => '查看指标' }),
    ]),
  },
]

const detailMatrixColumns: DataTableColumns<any> = [
  {
    title: '指标', key: 'indicatorName',
    render: (r: any) => h('div', { style: 'display:flex; align-items:center; gap:8px;' }, [
      h('span', {}, r.indicatorName),
      !r.configured ? h(NTag, { size: 'small', type: 'warning', bordered: false }, { default: () => '未配置' }) : null,
    ]),
  },
  {
    title: '目标占比', key: 'targetPct', width: 110,
    render: (r: any) => (r.configured ? h('span', {}, `${r.targetPct}%`) : h('span', { class: 'muted' }, '—')),
  },
  {
    title: '年度目标(人)', key: 'annualTarget', width: 120,
    render: (r: any) => (r.configured ? h('span', {}, String(r.annualTarget)) : h('span', { class: 'muted' }, '—')),
  },
  {
    title: '月度目标(人)', key: 'monthly', width: 210,
    render: (r: any) => (r.configured
      ? h('span', { class: 'muted' }, `${r.monthlyTargets[currentMonthIdx.value]}（${currentMonthIdx.value + 1}月）· 展开看12月`)
      : h('span', { class: 'muted' }, '—')),
  },
]
function renderDetailExpand(row: any) {
  return h('div', { style: 'display:grid; grid-template-columns:repeat(6,1fr); gap:8px; padding:4px 0;' },
    MONTH_LABELS.map((m, i) => h('div', { style: 'display:flex; flex-direction:column; align-items:center; padding:6px; background:rgba(99,102,241,0.06); border-radius:6px;' }, [
      h('span', { style: 'font-size:12px; color:var(--n-text-color-3,#999);' }, m),
      h('span', { style: 'font-weight:600;' }, String(row.monthlyTargets[i] || 0)),
    ])),
  )
}

const indicatorColumns: DataTableColumns<ControlIndicator> = [
  { title: '维度', key: 'dimensionName', width: 160 },
  { title: '指标名称', key: 'name' },
  {
    title: '操作', key: 'actions', width: 120, fixed: 'right',
    render: (r) => h('div', { style: 'display:flex; gap:8px;' }, [
      h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openIndicatorModal(r) }, { default: () => '编辑' }),
      h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeIndicator(r) }, { default: () => '删除' }),
    ]),
  },
]

const dimColumns: DataTableColumns<ControlDimension> = [
  { title: '维度名称', key: 'name' },
  { title: '编码', key: 'code', width: 120, render: (r) => r.code || '—' },
  {
    title: '启用', key: 'isActive', width: 70,
    render: (r) => h(NSwitch, {
      value: r.isActive, size: 'small',
      'onUpdate:value': async (v: boolean) => {
        try { await updateDimension(r.id, { isActive: v }); r.isActive = v; message.success(v ? '已启用' : '已停用') }
        catch (e) { message.error(extractApiError(e, '切换失败')) }
      },
    }),
  },
  {
    title: '操作', key: 'actions', width: 120, fixed: 'right',
    render: (r) => h('div', { style: 'display:flex; gap:8px;' }, [
      h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openDimModal(r) }, { default: () => '编辑' }),
      h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeDim(r) }, { default: () => '删除' }),
    ]),
  },
]

const personColumns: DataTableColumns<Person> = [
  { title: '编码', key: 'code' }, { title: '姓名', key: 'name' }, { title: '部门', key: 'bu' },
  { title: '院校', key: 'school' }, { title: '性别', key: 'sex' }, { title: '专业', key: 'major' },
  { title: '月份', key: 'month' }, { title: '职务', key: 'position', render: (r) => r.position || '—' },
  { title: '职级', key: 'level', render: (r) => r.level || '—' },
  { title: '状态', key: 'status' },
  { title: '计入核算', key: 'counted', render: (r) => h(NTag, { type: r.counted ? 'success' : 'default', bordered: false, size: 'small' }, { default: () => (r.counted ? '是' : '否') }) },
  {
    title: '操作', key: 'actions', width: 120, fixed: 'right',
    render: (r) => h('div', { style: 'display:flex; gap:8px;' }, [
      h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openPersonModal(r) }, { default: () => '编辑' }),
      h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removePerson(r) }, { default: () => '删除' }),
    ]),
  },
]

// v2.6 录入校验只看人数。占比/占比状态/强度三列移除（占比仅用于规则配置时计算实际人数，
// 不参与「是否可以录入」判定；strength 只对占比硬/软约束有意义，人数校验无此概念）。
// 实时看板（ratioColumns）仍使用 strengthType/ratioStatusType/pct，此处不删工具函数。
const checkColumns: DataTableColumns<ValidationResult['checks'][number]> = [
  { title: '适用范围', key: 'bu', width: 180, render: (r) => scopeText(r.bu, r.position, r.level) },
  { title: '维度', key: 'dimension', width: 100 }, { title: '指标', key: 'indicator', width: 100 },
  { title: '本月实际', key: 'monthActual', width: 100 }, { title: '本月目标', key: 'monthTarget', width: 100 },
  { title: '人数状态', key: 'countStatus', width: 110, render: (r) => h(NTag, { type: countStatusType(r.countStatus), bordered: false, size: 'small' }, { default: () => r.countStatus }) },
]

/* ============================ 维度规则集编辑面（占比之和须=100%） ============================ */
interface DimEditorRow {
  indicatorId: string
  indicatorName: string
  targetPct: number | null // null = 未设目标
  strength: Strength
  hasExisting: boolean
  pendingDelete: boolean
  /** 年度管控人数（0 也可编辑）。默认由「维度年度管控人数 × 占比」推导；用户手动改过即脱离联动。 */
  annualTarget: number
  /** 是否被用户手动调整过年度人数。手动调整后，本行的 annualTarget 不再随 top-level totalTarget 自动重算（点行尾「↻ 重算」可解除锁定）。 */
  manuallyEditedAnnual: boolean
  /** 12 个月度管控人数（长度固定 12 的非负整数数组）。 */
  monthlyTargets: number[]
}

const dimEditor = reactive({
  show: false,
  mode: 'view' as 'view' | 'edit',
  // 从已有规则打开时锁定「维度/年度」（规则集身份），适用范围保持可改以支持「重定位」
  lockContext: false,
  dimensionId: '' as string | null,
  isGlobal: true,
  bu: '', position: '', level: '',
  year: 2026,
  /** 编辑态打开时的适用范围快照，作为「重定位」参照；改了适用范围即触发迁移。 */
  originalScope: null as { bu: string; position: string; level: string; year: number } | null,
  /** 编辑态下适用范围是否相对 originalScope 变化（决定是否走重定位路径）。 */
  scopeDirty: false,
  /** 维度级「年度管控人数」。所有未删除指标行的 annualTarget 默认由 该值 × 占比 推导；手调过的行除外。 */
  totalTarget: 0,
  rows: [] as DimEditorRow[],
})

const dimEditorIndicators = computed(() =>
  indicators.value.filter((i) => i.dimension === dimEditor.dimensionId),
)
// 仅统计未标记删除行的占比之和
const dimEditorSumPct = computed(() =>
  dimEditor.rows.reduce((s, r) => s + (r.pendingDelete ? 0 : (r.targetPct || 0)), 0),
)
const dimEditorSumOk = computed(() => dimEditorAllPendingDelete.value || Math.abs(dimEditorSumPct.value - 100) < 0.05)
const dimEditorHasPendingDelete = computed(() => dimEditor.rows.some((r) => r.pendingDelete))
const dimEditorPendingDeleteCount = computed(() => dimEditor.rows.filter((r) => r.pendingDelete).length)
// 仅统计未删除行的年度人数加和（与 totalTarget 比较以判断「人数加和 = 维度年度目标」）。
const dimEditorActiveAnnualSum = computed(() =>
  dimEditor.rows.reduce((s, r) => s + (r.pendingDelete ? 0 : Math.round(r.annualTarget || 0)), 0),
)
// 人数加和 = totalTarget（口径：用户截图需求）。差 0 等同整数加和精确相等；不做四舍五入容差。
const dimEditorTotalOk = computed(() => dimEditorAllPendingDelete.value || dimEditorActiveAnnualSum.value === Math.round(dimEditor.totalTarget || 0))
// G5：所有指标行都标记删除 → 视为「清空该维度规则集」（提交空 rules，走后端清空分支，跳过占比/人数校验）
const dimEditorAllPendingDelete = computed(
  () => dimEditor.rows.length > 0 && dimEditor.rows.every((r) => r.pendingDelete),
)

/** 把任意 monthly 数组规范成长度 12 的非负整数数组（不足补 0、过长截断、非数置 0）。 */
function normalizeMonthly(raw: any): number[] {
  const out = Array(12).fill(0)
  if (Array.isArray(raw)) {
    for (let i = 0; i < 12 && i < raw.length; i++) {
      const v = Number(raw[i])
      out[i] = Number.isFinite(v) && v >= 0 ? Math.round(v) : 0
    }
  }
  return out
}

/**
 * 在 dimEditor.totalTarget 变化时，对「未手动调整且未删除」的行按 targetPct 比例重算 annualTarget。
 * 用最大余数法（largest-remainder / Hamilton）保证加和 = totalTarget 严格相等，
 * 余数部分按比例小数位从大到小分配。
 */
function _redistributeAnnualByPct(total: number) {
  const target = Math.max(0, Math.round(total || 0))
  // 参与分配的行：未删 & 有占比
  const active = dimEditor.rows.filter((r) => !r.pendingDelete && r.targetPct != null)
  const locked = active.filter((r) => r.manuallyEditedAnnual)
  const fluid = active.filter((r) => !r.manuallyEditedAnnual)
  const lockedSum = locked.reduce((s, r) => s + Math.round(r.annualTarget || 0), 0)
  // fluid 行要把总人数里「扣掉已锁」的部分吃满，因此 fluidTotal 的单位值是 fluidTotal/fluidSumPct
  // 而非 totalTarget/100 —— 这就是「60% locked → 40% fluid → 重算 60% → 应得 1039 (== 60%×1731-40%×1731)」
  // 而不是「60%×fluidTotal」= 60%×1039 = 623（v2.7 之前的 bug）。
  const fluidTotal = Math.max(0, target - lockedSum)
  const fluidSumPct = fluid.reduce((s, r) => s + (r.targetPct || 0), 0)
  if (fluidSumPct <= 0) return
  // 各 fluid 行精确分配量：每个 unit% 占比 fluidTotal/fluidSumPct 的「购买力」
  const floats = fluid.map((r) => ({
    row: r,
    exact: ((r.targetPct || 0) / fluidSumPct) * fluidTotal,
    floor: Math.floor(((r.targetPct || 0) / fluidSumPct) * fluidTotal),
    frac: 0,
  }))
  for (const f of floats) f.frac = f.exact - f.floor
  floats.sort((a, b) => b.frac - a.frac)
  const totalFloors = floats.reduce((s, f) => s + f.floor, 0)
  // 用「补足到 fluidTotal」的整差量做最大余数分配（largest-remainder / Hamilton 法），
  // 严格保证 fluidSum = fluidTotal；不再用两段循环（旧实现 second loop 会从 i=0 覆盖 +1）。
  const needAdd = Math.max(0, Math.round(fluidTotal - totalFloors))
  for (let i = 0; i < floats.length; i++) {
    floats[i].row.annualTarget = i < needAdd ? floats[i].floor + 1 : floats[i].floor
  }
}

function _buildDimRows() {
  const bu = dimEditor.isGlobal ? '' : dimEditor.bu
  const position = dimEditor.isGlobal ? '' : dimEditor.position
  const level = dimEditor.isGlobal ? '' : dimEditor.level
  const existing = rules.value.filter(
    (r) =>
      r.dimension === dimEditor.dimensionId &&
      (r.bu || '') === bu && (r.position || '') === position && (r.level || '') === level &&
      r.year === dimEditor.year,
  )
  // 先收集历史 annual；所有行（含新行）首次进入时按业务规则：**历史 annual 是「用户录入的事实」**，标记为手动调整（避免后续 top-total 重分配把它改掉）
  dimEditor.rows = dimEditorIndicators.value.map((ind) => {
    const er = existing.find((r) => r.indicator === ind.id)
    const historical = er ? Math.round(Number(er.annualTarget) || 0) : 0
    return {
      indicatorId: ind.id,
      indicatorName: ind.name,
      targetPct: er ? Math.round(er.target * 1000) / 10 : null,
      strength: er ? (er.strength as Strength) : '硬约束',
      hasExisting: !!er,
      pendingDelete: false,
      annualTarget: historical,
      // 历史 annual 视为「用户录入过」—— 不要被 top-total 自动覆盖
      manuallyEditedAnnual: !!er,
      monthlyTargets: er
        ? normalizeMonthly(er.monthlyTargets)
        : Array(12).fill(0),
    }
  })
  // 维度年度管控人数 = Σ(未删行 annualTarget)，历史有值即按历史求和；无历史置 0 让用户首次输入。
  const existingTotal = existing.reduce((s, r) => s + Math.round(Number(r.annualTarget) || 0), 0)
  dimEditor.totalTarget = existing.length > 0 ? existingTotal : 0
}

/**
 * view 模式下 (适用范围, 年度) 切换 → 同步到 dimEditor 上下文（点底部「编辑」时带入）。
 * 仅在 view 模式触发；edit 模式下 dimEditor 上下文由 lockContext 锁住，不联动。
 */
watch(
  [() => detailScopeKey.value, () => detailYear.value],
  () => {
    if (!dimEditor.show || dimEditor.mode !== 'view') return
    const scope = keyToScope(detailScopeKey.value)
    dimEditor.isGlobal = !(scope.bu || scope.position || scope.level)
    dimEditor.bu = scope.bu
    dimEditor.position = scope.position
    dimEditor.level = scope.level
    dimEditor.year = detailYear.value
    dimEditor.originalScope = { bu: scope.bu, position: scope.position, level: scope.level, year: detailYear.value }
    _buildDimRows()
  },
)

/**
 * 打开维度规则集编辑面。
 * - rule 给定：以该规则的 (适用范围, 维度, 年度) 为上下文，锁定上下文，展示该维度全部指标。
 * - opts.preDelete：打开即进入编辑态并标记某指标「待删」，强制用户重平衡至 100%。
 * 这样点任一指标/删除单条，都进入「维度级」编辑，保证占比之和=100% 的约束。
 */
function openDimensionEditor(rule?: ControlRule, opts?: { preDelete?: string }) {
  if (rule) {
    dimEditor.dimensionId = rule.dimension
    dimEditor.isGlobal = !(rule.bu || rule.position || rule.level)
    dimEditor.bu = rule.bu || ''
    dimEditor.position = rule.position || ''
    dimEditor.level = rule.level || ''
    dimEditor.year = rule.year
    dimEditor.lockContext = true // 维度/年度锁定（身份），适用范围保持可改
    dimEditor.originalScope = { bu: rule.bu || '', position: rule.position || '', level: rule.level || '', year: rule.year }
    dimEditor.scopeDirty = false
  } else {
    dimEditor.dimensionId = null
    dimEditor.isGlobal = true
    dimEditor.bu = ''; dimEditor.position = ''; dimEditor.level = ''
    dimEditor.year = 2026
    dimEditor.lockContext = false
    dimEditor.originalScope = null
    dimEditor.scopeDirty = false
  }
  dimEditor.mode = opts?.preDelete ? 'edit' : 'view'
  dimEditor.show = true
  if (dimEditor.dimensionId) _buildDimRows()
  if (opts?.preDelete) {
    const row = dimEditor.rows.find((r) => r.indicatorId === opts.preDelete)
    if (row) row.pendingDelete = true
  }
}

function onDimEditorDimChange() {
  dimEditor.rows = []
  if (dimEditor.dimensionId) _buildDimRows()
}
/**
 * 上下文切换处理：
 * - 新建态（!lockContext）：适用范围/年度变化 → 重建行，从历史规则派生对应 (适用范围,维度,年度) 的 monthly/annual。
 * - 编辑态（lockContext）：维度/年度已锁定，仅适用范围可改；改适用范围**不重建行**（避免丢失正在编辑的指标/占比/人数），
 *   仅标记 scopeDirty，保存时按「重定位」语义删除原 scope 规则集、在新 scope 重建。
 */
function onDimEditorCtxChange() {
  if (!dimEditor.lockContext) {
    if (dimEditor.dimensionId) _buildDimRows()
    return
  }
  dimEditor.scopeDirty = _isScopeDirty()
}
/** 编辑态下取「当前生效适用范围」（全局时 bu/position/level 归空）。 */
function _currentEffectiveScope() {
  return {
    bu: dimEditor.isGlobal ? '' : dimEditor.bu,
    position: dimEditor.isGlobal ? '' : dimEditor.position,
    level: dimEditor.isGlobal ? '' : dimEditor.level,
    year: dimEditor.year,
  }
}
/** 当前生效适用范围是否与原打开时不同（决定是否触发重定位）。 */
function _isScopeDirty(): boolean {
  const o = dimEditor.originalScope
  if (!o) return false
  const c = _currentEffectiveScope()
  return o.bu !== c.bu || o.position !== c.position || o.level !== c.level || o.year !== c.year
}
/** 适用范围展示文案：全局 →「全局 / YYYY 年」；指定 →「部门 · 职务 · 职级 / YYYY 年」。 */
function formatScopeLabel(s: { bu: string; position: string; level: string; year: number } | null): string {
  if (!s) return '—'
  if (!s.bu && !s.position && !s.level) return `全局 / ${s.year} 年`
  const parts = [s.bu, s.position, s.level].filter(Boolean).join(' · ')
  return `${parts} / ${s.year} 年`
}
/**
 * 当前 (dimension, year) 下，与「当前生效 scope 类型相反」的既有规则集（用于保存前预警）。
 *  - 当前为指定范围 → 取全局规则（bu/position/level 全空）
 *  - 当前为全局 → 取所有指定范围规则
 * 重定位场景下排除 original scope（其规则保存时会被删除，不算冲突）。
 */
function _oppositeScopeRules(): ControlRule[] {
  const dim = dimEditor.dimensionId
  const year = dimEditor.year
  if (!dim) return []
  const c = _currentEffectiveScope()
  const curIsGlobal = !c.bu && !c.position && !c.level
  const o = dimEditor.originalScope
  return rules.value.filter((r) => {
    if (r.dimension !== dim || r.year !== year) return false
    const rIsGlobal = !r.bu && !r.position && !r.level
    if (rIsGlobal !== curIsGlobal) {
      if (o && o.bu === r.bu && o.position === r.position && o.level === r.level && o.year === r.year) return false
      return true
    }
    return false
  })
}

function enterDimEdit() { dimEditor.mode = 'edit' }
function closeDimEditor() {
  dimEditor.show = false
  dimEditor.mode = 'view'
}
function setDimRowTarget(id: string, v: number | null) {
  const r = dimEditor.rows.find((x) => x.indicatorId === id)
  if (r) {
    r.targetPct = v == null ? null : v
    // 不联动改 annual：让占比 / 年度各自独立，方便用户「指标下的年度支持单独调整」
  }
}
function setDimRowStrength(id: string, v: string) {
  const r = dimEditor.rows.find((x) => x.indicatorId === id)
  if (r) r.strength = v as Strength
}
function setDimRowAnnual(id: string, v: number | null) {
  const r = dimEditor.rows.find((x) => x.indicatorId === id)
  if (!r) return
  r.annualTarget = v == null ? 0 : Math.max(0, Math.round(v))
  r.manuallyEditedAnnual = true // 标记脱离联动，下次 totalTarget 变化不再重算该行
}
/**
 * 用户在顶部改了「维度年度管控人数」→ 对「未手动调整 / 未删除」的行按 targetPct 比例重算（最大余数法），
 * 已手动调整的行保留原值。最后用「fluid 重算后」的 Σ 同步 totalTarget，确保总数与分项之和自洽。
 */
function setDimEditorTotalTarget(v: number | null) {
  const target = v == null ? 0 : Math.max(0, Math.round(v))
  dimEditor.totalTarget = target
  _redistributeAnnualByPct(target)
}
/** 行内 toggle：auto ↔ manual。auto 时点 = "锁定到手动"（脱离 totalTarget 联动），manual 时点 = "↻ 重算"（回到按总人数×占比 推算）。 */
function toggleAnnualMode(id: string) {
  const r = dimEditor.rows.find((x) => x.indicatorId === id)
  if (!r) return
  if (r.manuallyEditedAnnual) {
    r.manuallyEditedAnnual = false
    _redistributeAnnualByPct(dimEditor.totalTarget)
  } else {
    // 锁定当前值（即便它跟"理论自动值"一致，也明确标手动，避免 top-total 改动时被覆盖）
    r.manuallyEditedAnnual = true
  }
}
function setDimRowMonthly(id: string, idx: number, v: number | null) {
  const r = dimEditor.rows.find((x) => x.indicatorId === id)
  if (!r) return
  const arr = [...r.monthlyTargets]
  arr[idx] = v == null ? 0 : Math.max(0, Math.round(v))
  r.monthlyTargets = arr
}
/** 把月度按「年度/12」整除，余数从 1 月开始各 +1。 */
function redistributeDimMonthly(id: string) {
  const r = dimEditor.rows.find((x) => x.indicatorId === id)
  if (!r) return
  const annual = Math.max(0, Math.round(r.annualTarget || 0))
  const base = Math.floor(annual / 12)
  const rem = annual - base * 12
  r.monthlyTargets = Array.from({ length: 12 }, (_, i) => base + (i < rem ? 1 : 0))
}
function toggleDimRowDelete(id: string) {
  const r = dimEditor.rows.find((x) => x.indicatorId === id)
  if (r) {
    r.pendingDelete = !r.pendingDelete
    // 删除/恢复态变化不重算总数 —— 用户在顶部 totalTarget 里看到的是「当前未删行」的真实加和，
    // 由 dimEditorActiveAnnualSum 提供；如果想保持 Σ = totalTarget 校验，需要在切回未删后补上重算。
    // 这里不自动重算：让用户主动调整比静默改写好理解。
  }
}

/** 单行 monthly 加和（按当前数据实时派生）。 */
function dimRowMonthlySum(r: DimEditorRow) {
  return r.monthlyTargets.reduce((a, b) => a + (b || 0), 0)
}
/** 单行 monthly 是否等于年度目标。 */
function dimRowMonthlyOk(r: DimEditorRow) {
  return dimRowMonthlySum(r) === Math.round(r.annualTarget || 0)
}

async function saveDimRuleSet() {
  if (!dimEditor.dimensionId) { message.warning('请选择维度'); return }
  // G5：全部指标标记删除 → 清空该维度规则集（跳过占比/人数校验，二次确认后提交空 rules）
  if (dimEditorAllPendingDelete.value) {
    const relocate = !!dimEditor.lockContext && !!dimEditor.scopeDirty
    const doClear = async () => {
      loading.saveDimRuleSet = true
      try {
        const res = await saveDimensionRuleSet(dimEditor.dimensionId!, {
          bu: dimEditor.isGlobal ? '' : dimEditor.bu,
          position: dimEditor.isGlobal ? '' : dimEditor.position,
          level: dimEditor.isGlobal ? '' : dimEditor.level,
          year: dimEditor.year,
          totalTarget: 0,
          rules: [],
          ...(relocate && dimEditor.originalScope ? { original: dimEditor.originalScope } : {}),
        })
        message.success(`已清空维度规则集（${res.data.saved} 条）`)
        dimEditor.show = false
        dimEditor.mode = 'view'
        await Promise.all([loadRules(), loadRatio()])
      } catch (e) {
        message.error(extractApiError(e, '清空失败'))
      } finally {
        loading.saveDimRuleSet = false
      }
    }
    const c = _currentEffectiveScope()
    const curIsGlobal = !c.bu && !c.position && !c.level
    const opposite = _oppositeScopeRules()
    // 清空全局但存在其他指定范围 → 后端会拦截，提前告知
    if (curIsGlobal && opposite.length > 0) {
      dialog.error({
        title: '无法清空为全局规则',
        content: '该维度年度下已存在指定范围规则集，清空全局会同时清除这些指定范围，操作被拦截。请先删除指定范围规则，或改用指定范围清空。',
        positiveText: '我知道了',
      })
      return
    }
    if (relocate) {
      const clearGlobalNote =
        !curIsGlobal && opposite.length > 0
          ? '\n注意：清空指定范围会同时清除该维度年度下的全局规则。'
          : ''
      dialog.warning({
        title: '清空并迁移适用范围',
        content: `将清空该维度规则集，并从「${formatScopeLabel(dimEditor.originalScope)}」迁移到「${formatScopeLabel(_currentEffectiveScope())}」。\n原「${formatScopeLabel(dimEditor.originalScope)}」下的规则将被删除。${clearGlobalNote}`,
        positiveText: '清空',
        negativeText: '取消',
        onPositiveClick: doClear,
      })
      return
    }
    // 非重定位的普通清空：若会触发跨 scope 清理（指定范围→清全局），显式确认
    if (!curIsGlobal && opposite.length > 0) {
      dialog.warning({
        title: '跨适用范围清空确认',
        content: '清空指定范围将同时清除该维度年度下的全局规则，是否继续？',
        positiveText: '继续清空',
        negativeText: '取消',
        onPositiveClick: doClear,
      })
      return
    }
    dialog.warning({
      title: '清空该维度规则集',
      content: '所有指标都已标记删除，保存将清空该维度下当前适用范围的全部规则，是否继续？',
      positiveText: '清空',
      negativeText: '取消',
      onPositiveClick: doClear,
    })
    return
  }
  const validRows = dimEditor.rows.filter((r) => !r.pendingDelete && r.targetPct != null)
  if (validRows.length === 0) { message.warning('请至少保留一个指标并设置占比'); return }
  if (!dimEditorSumOk.value) { message.warning(`占比之和须 = 100%，当前 ${dimEditorSumPct.value.toFixed(1)}%`); return }
  // 人数加和 = 维度年度总人数（用户口径）
  if (!dimEditorTotalOk.value) {
    message.warning(
      `各指标年度人数加和（${dimEditorActiveAnnualSum.value}）须等于「维度年度管控人数」（${Math.round(dimEditor.totalTarget || 0)}），请调整各指标年度或顶部总人数后重试`,
    )
    return
  }
  // 月度校验：单行 12 月加和 = 该行年度人数
  const badMonths = validRows.filter((r) => !dimRowMonthlyOk(r))
  if (badMonths.length) {
    message.warning(`指标「${badMonths.map((r) => r.indicatorName).join('、')}」的 12 月之和 ≠ 年度人数`)
    return
  }
  const rulesPayload: DimRuleSetItem[] = validRows.map((r) => ({
    indicator: r.indicatorId,
    target: (r.targetPct || 0) / 100,
    strength: r.strength,
    // 年度/月度都已规范化；显式传给后端，覆盖"从旧规则继承"路径
    annualTarget: Math.round(r.annualTarget || 0),
    monthlyTargets: r.monthlyTargets.slice(),
  }))
  // 编辑态且适用范围已改 → 走「重定位」：删除原 scope 规则集 + 在新 scope 重建。需二次确认。
  const relocate = !!dimEditor.lockContext && !!dimEditor.scopeDirty
  const doSave = async () => {
    loading.saveDimRuleSet = true
    try {
      const res = await saveDimensionRuleSet(dimEditor.dimensionId!, {
        bu: dimEditor.isGlobal ? '' : dimEditor.bu,
        position: dimEditor.isGlobal ? '' : dimEditor.position,
        level: dimEditor.isGlobal ? '' : dimEditor.level,
        year: dimEditor.year,
        totalTarget: dimEditorActiveAnnualSum.value,
        rules: rulesPayload,
        ...(relocate && dimEditor.originalScope ? { original: dimEditor.originalScope } : {}),
      })
      message.success(`已保存维度规则集（${res.data.saved} 条）`)
      dimEditor.show = false
      dimEditor.mode = 'view'
      await Promise.all([loadRules(), loadRatio()])
    } catch (e) {
      message.error(extractApiError(e, '保存失败'))
    } finally {
      loading.saveDimRuleSet = false
    }
  }
  const c = _currentEffectiveScope()
  const curIsGlobal = !c.bu && !c.position && !c.level
  const opposite = _oppositeScopeRules()
  // 保存全局但存在其他指定范围 → 后端会拦截，这里提前告知，避免误以为能保存
  if (curIsGlobal && opposite.length > 0) {
    dialog.error({
      title: '无法保存为全局规则',
      content: '该维度年度下已存在指定范围规则集，保存全局会清空这些指定范围，操作被拦截。请先删除指定范围规则，或改用指定范围保存。',
      positiveText: '我知道了',
    })
    return
  }
  if (relocate) {
    const clearGlobalNote =
      !curIsGlobal && opposite.length > 0
        ? '\n注意：保存指定范围会同时清除该维度年度下的全局规则。'
        : ''
    dialog.warning({
      title: '重定位适用范围',
      content: `将把该维度规则集从「${formatScopeLabel(dimEditor.originalScope)}」迁移到「${formatScopeLabel(_currentEffectiveScope())}」。\n原「${formatScopeLabel(dimEditor.originalScope)}」下的规则将被删除。${clearGlobalNote}`,
      positiveText: '迁移',
      negativeText: '取消',
      onPositiveClick: doSave,
    })
    return
  }
  // 非重定位的普通保存：若会触发跨 scope 清理（指定范围→清全局），显式确认
  if (!curIsGlobal && opposite.length > 0) {
    dialog.warning({
      title: '跨适用范围保存确认',
      content: '保存指定范围将同时清除该维度年度下的全局规则，是否继续？',
      positiveText: '继续保存',
      negativeText: '取消',
      onPositiveClick: doSave,
    })
    return
  }
  await doSave()
}

/* ============================ 规则导入 / 导出 ============================ */
const importDrawer = reactive({
  show: false,
  fileList: [] as any[],
  result: null as RuleImportResult | null,
})

/* ============================ 指标导入 / 导出 ============================ */
const indicatorExportOptions = [
  { label: 'Excel (.xlsx)', key: 'xlsx' },
  { label: 'CSV (.csv)', key: 'csv' },
]
const indicatorImportDrawer = reactive({
  show: false,
  mode: 'skip' as 'skip' | 'update' | 'error',
  fileList: [] as any[],
  result: null as IndicatorImportResult | null,
})

function onExportIndicatorsSelect(key: 'xlsx' | 'csv') {
  onExportIndicators(key)
}
async function onExportIndicators(format: 'xlsx' | 'csv' = 'xlsx') {
  try {
    await exportIndicators(format)
    message.success(`已导出指标（${format}）`)
  } catch (e) {
    message.error(extractApiError(e, '导出失败'))
  }
}
async function onDownloadIndicatorTemplate() {
  // 导入弹窗内与工具栏的「下载模板」共用；默认 xlsx
  try {
    await downloadIndicatorTemplate('xlsx')
    message.success('已下载指标导入模板')
  } catch (e) {
    message.error(extractApiError(e, '下载模板失败'))
  }
}
function handleIndicatorImportUpload({ file, onFinish, onError }: any) {
  indicatorImportDrawer.result = null
  const raw = file.file as File
  if (!raw) { onError(); return }
  loading.import = true
  importIndicators(raw, indicatorImportDrawer.mode)
    .then((res) => {
      indicatorImportDrawer.result = res
      if (res.success) {
        message.success(`导入成功：新建 ${res.data.created} / 更新 ${res.data.updated} / 跳过 ${res.data.skipped}`)
        loadIndicators()
        onFinish()
      } else {
        message.error(`导入失败：${res.data.errors.length} 处错误`)
        onError()
      }
    })
    .catch((e) => {
      const errRes = e?.response?.data
      if (errRes?.data?.errors) {
        indicatorImportDrawer.result = errRes
      } else {
        message.error(extractApiError(e, '导入失败'))
      }
      onError()
    })
    .finally(() => { loading.import = false })
}
function downloadIndicatorImportErrorExcel() {
  const b64 = indicatorImportDrawer.result?.data?.errorFile
  if (!b64) return
  try {
    const bin = atob(b64)
    const bytes = new Uint8Array(bin.length)
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
    const blob = new Blob([bytes], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    triggerDownload(blob, `campus_indicators_import_errors_${Date.now()}.xlsx`)
  } catch (e) {
    message.error('错误明细 Excel 解析失败')
  }
}
function onIndicatorImportFileRemove() {
  indicatorImportDrawer.fileList = []
  indicatorImportDrawer.result = null
}

async function onExportRules() {
  try {
    await exportRules()
    message.success('已导出规则 Excel')
  } catch (e) {
    message.error(extractApiError(e, '导出失败'))
  }
}
async function onDownloadTemplate() {
  try {
    await downloadRuleTemplate()
    message.success('已下载导入模板')
  } catch (e) {
    message.error(extractApiError(e, '下载模板失败'))
  }
}

function handleImportUpload({ file, onFinish, onError }: any) {
  importDrawer.result = null
  const raw = file.file as File
  if (!raw) { onError(); return }
  loading.import = true
  importRules(raw)
    .then((res) => {
      importDrawer.result = res
      if (res.success) {
        message.success(`导入成功：${res.data.groups} 组 / ${res.data.savedRules} 条规则`)
        loadRules()
        loadRatio()
        onFinish()
      } else {
        message.error(`导入失败：${res.data.errors.length} 处错误`)
        onError()
      }
    })
    .catch((e) => {
      const errRes = e?.response?.data
      if (errRes?.data?.errors) {
        importDrawer.result = errRes
      } else {
        message.error(extractApiError(e, '导入失败'))
      }
      onError()
    })
    .finally(() => { loading.import = false })
}
function downloadImportErrorReport() {
  const errors = importDrawer.result?.data?.errors || []
  if (!errors.length) return
  const text = ['规则导入失败原因明细', '====================', ...errors].join('\n')
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  triggerDownload(blob, `campus_rules_import_errors_${Date.now()}.txt`)
}
function downloadImportErrorExcel() {
  const b64 = importDrawer.result?.data?.errorFile
  if (!b64) return
  try {
    const bin = atob(b64)
    const bytes = new Uint8Array(bin.length)
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
    const blob = new Blob([bytes], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    triggerDownload(blob, `campus_rules_import_errors_${Date.now()}.xlsx`)
  } catch (e) {
    message.error('错误明细 Excel 解析失败，请改用 txt 报告')
  }
}
function onImportFileRemove() {
  importDrawer.fileList = []
  importDrawer.result = null
}

/* ============================ 维度管理 ============================ */
const dimDrawer = reactive({ show: false })
function openDimDrawer() { dimDrawer.show = true }

const dimModal = reactive({ show: false, editingId: '' as string | null, name: '', code: '' })
function openDimModal(d?: ControlDimension) {
  dimModal.editingId = d?.id ?? null
  dimModal.name = d?.name ?? ''
  dimModal.code = d?.code ?? ''
  dimModal.show = true
}
async function saveDim() {
  if (!dimModal.name.trim()) { message.warning('请填写维度名称'); return }
  try {
    if (dimModal.editingId) await updateDimension(dimModal.editingId, { name: dimModal.name.trim(), code: dimModal.code.trim() })
    else await createDimension({ name: dimModal.name.trim(), code: dimModal.code.trim() })
    message.success('保存成功')
    dimModal.show = false
    await loadDimensions()
  } catch (e) { message.error(extractApiError(e, '保存失败')) }
}
function removeDim(d: ControlDimension) {
  dialog.warning({
    title: '删除维度', content: `确认删除维度「${d.name}」？该维度下的指标将一并删除。`, positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try { await deleteDimension(d.id); message.success('删除成功'); await Promise.all([loadDimensions(), loadIndicators()]) }
      catch (e) { message.error(extractApiError(e, '删除失败')) }
    },
  })
}

/* ============================ 指标 CRUD ============================ */
const indicatorModal = reactive({ show: false, editingId: '' as string | null, dimensionId: '' as string | null, name: '' })
function openIndicatorModal(ind?: ControlIndicator) {
  indicatorModal.editingId = ind?.id ?? null
  indicatorModal.dimensionId = ind?.dimension ?? indicatorDimFilter.value ?? null
  indicatorModal.name = ind?.name ?? ''
  indicatorModal.show = true
}
async function saveIndicator() {
  if (!indicatorModal.dimensionId || !indicatorModal.name.trim()) { message.warning('请选择维度并填写指标名称'); return }
  try {
    if (indicatorModal.editingId) await updateIndicator(indicatorModal.editingId, { name: indicatorModal.name.trim() })
    else await createIndicator({ dimension: indicatorModal.dimensionId, name: indicatorModal.name.trim() })
    message.success('保存成功')
    indicatorModal.show = false
    await loadIndicators()
  } catch (e) { message.error(extractApiError(e, '保存失败')) }
}
function removeIndicator(ind: ControlIndicator) {
  dialog.warning({
    title: '删除指标', content: `确认删除指标「${ind.name}」？`, positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try { await deleteIndicator(ind.id); message.success('删除成功'); await loadIndicators() }
      catch (e) { message.error(extractApiError(e, '删除失败')) }
    },
  })
}

/* ============================ 录入校验 ============================ */
const draft = reactive({
  code: '', name: '', bu: '能电BG', position: '', level: '',
  school: '985', sex: '男', major: '工学', month: '8月', status: '在职',
})
const validation = ref<ValidationResult | null>(null)
const validateYear = ref(new Date().getFullYear())
async function runValidate() {
  validation.value = null
  loading.validate = true
  try {
    validation.value = await validateDraft(validateYear.value, {
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
    await Promise.all([loadPersons(), loadRatio()])
  } catch (e) { message.error(extractApiError(e, '录入失败')) }
}

/* ============================ 人员 CRUD ============================ */
const personModal = reactive({
  show: false, editingId: '' as string | null,
  code: '', name: '', bu: '能电BG', school: '985', sex: '男', major: '工学', month: '8月', status: '在职',
  expectedEntryDate: null as string | null,
  actualEntryDate: null as string | null,
  position: '', level: '', counted: true,
})
function openPersonModal(p?: Person) {
  personModal.editingId = p?.id ?? null
  personModal.code = p?.code ?? ''; personModal.name = p?.name ?? ''
  personModal.bu = p?.bu ?? '能电BG'; personModal.school = p?.school ?? '985'
  personModal.sex = p?.sex ?? '男'; personModal.major = p?.major ?? '工学'; personModal.month = p?.month ?? '8月'
  personModal.status = p?.status ?? '在职'
  personModal.expectedEntryDate = p?.expectedEntryDate ?? null
  personModal.actualEntryDate = p?.actualEntryDate ?? null
  personModal.position = p?.position ?? ''
  personModal.level = p?.level ?? ''; personModal.counted = p?.counted ?? true
  personModal.show = true
}
async function savePerson() {
  if (!personModal.code.trim() || !personModal.name.trim()) { message.warning('请填写编码与姓名'); return }
  try {
    await upsertPerson({
      id: personModal.editingId ?? undefined,
      code: personModal.code.trim(), name: personModal.name.trim(), bu: personModal.bu,
      school: personModal.school, sex: personModal.sex, major: personModal.major, month: personModal.month, status: personModal.status,
      expectedEntryDate: personModal.expectedEntryDate,
      actualEntryDate: personModal.actualEntryDate,
      position: personModal.position, level: personModal.level, counted: personModal.counted,
    })
    message.success('保存成功')
    personModal.show = false
    await loadPersons()
  } catch (e) { message.error(extractApiError(e, '保存失败')) }
}
function removePerson(p: Person) {
  dialog.warning({
    title: '删除人员', content: `确认删除「${p.name}（${p.code}）」？`, positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try { await deletePerson(p.id); message.success('删除成功'); await loadPersons() }
      catch (e) { message.error(extractApiError(e, '删除失败')) }
    },
  })
}

onMounted(async () => {
  await Promise.all([loadDimensions(), loadIndicators(), loadPersons()])
  await Promise.all([loadRatio(), loadRules()])
})
</script>

<style scoped>
/* 仅保留「布局链」相关规则，视觉（玻璃/极光/标题渐变/KPI/表格/弹窗）统一复用全局 glass.css
   —— 单一设计系统，校招管控不再持有私有视觉定义。 */

/* 「全局 + 指定范围」混合规则集 → 重复计入风险徽标 */
.scope-mutex-badge {
  cursor: help;
  font-size: 14px;
  line-height: 1;
  user-select: none;
}
.scope-mutex-banner {
  margin-bottom: 12px;
}

/* 极光由 SettingsLayout 外壳统一注入（.settings-aurora），本页不再自绘 */

/* 多 tab 看板需要整页纵向撑满：页面根作为 flex 列，.glass-panel 才能 flex:1 填满剩余高度 */
.page-container {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  /* 不强制 height:100%，避免 settings-scroll 不可滚动时内容被截断；
     玻璃面板在可用空间内撑满，内容超过时内部滚动链生效 */
}

/* .glass-panel 已是全局玻璃工具类；此处补充「作为页面内容根时撑满高度」的布局行为 */
.glass-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding: var(--space-4);
}
.cc-tabs {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
.cc-tabs :deep(.n-tabs-nav) { background: transparent; }
.cc-tabs :deep(.n-tabs-pane-wrapper) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.cc-tabs :deep(.n-tab-pane) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
/* 表格滚动由全局 .table-wrap（glass.css 阶段 F）统一处理，本页不再持有重复定义 */
.validate-result {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  margin-top: var(--space-4);
}

.block-hint { color: var(--c-error); font-size: var(--text-small); margin: var(--space-2) 0 0; }

.drawer-footer { display: flex; justify-content: flex-end; gap: var(--space-3); }

/* ===================== 统一分区卡片（规则详情 / 批量配置 共享） ===================== */
.form-section {
  position: relative;
  background: var(--glass-bg-input);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  padding: 12px 14px 14px;
  margin-bottom: 12px;
  transition: border-color 0.2s ease;
}
.form-section:last-child { margin-bottom: 0; }
.form-section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  margin: 2px 0 10px;
  letter-spacing: 0.2px;
}
.form-section-title .dot {
  width: 3px;
  height: 12px;
  background: var(--brand);
  border-radius: 2px;
  flex-shrink: 0;
}
.form-section-hint {
  font-size: 12px;
  font-weight: 400;
  color: var(--ink-faint);
  margin-left: 2px;
}

/* 适用范围：flex 行；开关 + 字段并排 */
.scope-row {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  flex-wrap: wrap;
}
.scope-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1 1 140px;
}
.scope-label {
  font-size: 12px;
  color: var(--ink-soft);
  line-height: 1;
}

/* 12 个月网格（批量=6 列，规则=4 列） */
.monthly-block-label {
  font-size: 12px;
  color: var(--ink-soft);
  margin: 12px 0 6px;
}
.monthly-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 6px 6px;
}
.monthly-grid--rule {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.month-cell {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 2px;
  min-width: 0;
}
.month-label {
  font-size: 11px;
  color: var(--ink-soft);
  line-height: 1.2;
  text-align: center;
}
.month-cell .n-input-number { width: 100%; }

.monthly-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.monthly-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--ink);
}
.allocated strong { font-weight: 700; }

/* 占比之和 callout */
.sum-callout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  transition: background 0.2s ease, border-color 0.2s ease;
}
.sum-callout.ok {
  background: rgba(82, 196, 26, 0.08);
  border: 1px solid rgba(82, 196, 26, 0.25);
}
.sum-callout.warn {
  background: rgba(250, 140, 22, 0.08);
  border: 1px solid rgba(250, 140, 22, 0.25);
}
.sum-left {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.sum-label {
  font-size: 12px;
  color: var(--ink-soft);
}
.sum-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.sum-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sum-diff {
  font-size: 12px;
  color: var(--ink-soft);
  font-variant-numeric: tabular-nums;
}

.empty-tip {
  color: var(--ink-faint);
  padding: 12px 4px;
  font-size: 13px;
  text-align: center;
}

/* form-row-2 间距微调 */
.form-row-2 { margin-bottom: 4px; }

/* ===================== 维度规则集编辑面 ===================== */
.dim-ctx { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
.dim-ctx .form-section { margin-bottom: 10px; }
.dim-ctx .form-section:last-child { margin-bottom: 0; }
.dim-rows { display: flex; flex-direction: column; gap: 10px; }
.dim-summary {
  display: flex; align-items: baseline; gap: 12px;
  padding: 8px 12px;
  border: 1px dashed var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--glass-bg-card);
  font-size: 13px; color: var(--ink-soft);
}
.dim-summary .sum-label { color: var(--ink-faint); }
.dim-summary .sum-value { font-size: 18px; font-weight: 700; color: var(--ink); font-variant-numeric: tabular-nums; }
.dim-summary .sum-hint { font-size: 12px; color: var(--ink-faint); }

/* 适用范围 form-section 标题行右移 switch */
.form-section-title--scope {
  display: flex;
  align-items: center;
  gap: 8px;
}
.form-section-title--scope .dot { flex-shrink: 0; }
.scope-title-switch { margin-left: auto; }
/* 编辑态改了适用范围 → 重定位提示横幅 */
.scope-relocate-hint {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.5;
}
.scope-relocate-hint :deep(.n-alert__content) { font-size: 12px; }

/* 维度层级编辑弹窗 */
.dim-edit-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 4px 0;
}
.dim-edit-form .scope-field {
  display: flex;
  align-items: center;
  gap: 12px;
}
.dim-edit-form .scope-label {
  width: 92px;
  font-size: 13px;
  color: var(--ink);
  flex-shrink: 0;
}

/* 维度年度管控人数 section */
.total-target-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.total-target-suffix { font-size: 13px; color: var(--ink); }
.total-target-hint { font-size: 12px; color: var(--ink-faint); }
.total-target-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--ink-soft);
  font-variant-numeric: tabular-nums;
}
.total-target-summary strong { color: var(--ink); font-weight: 700; }
.total-target-sep { color: var(--ink-faint); }
.total-target-tag { margin-left: auto; }

/* 行内控件：统一上下结构（label 上、控件下），与「占比%」「强度」一致 */
.ctrl-group {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}
.ctrl-group--annual {
  /* 继承 .ctrl-group 的 column 布局：标签在上，输入框+单位+toggle 在下 */
  /* 与「占比%」「强度」保持一致的上下结构 */
}
.annual-ctrl-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.annual-unit {
  font-size: 12px;
  color: var(--ink-soft);
  padding-right: 2px;
}
.annual-toggle-btn {
  font-size: 12px !important;
  padding: 0 12px !important;
  height: 28px !important;
  border-radius: var(--radius-sm, 6px) !important;
  white-space: nowrap !important;
  min-width: 78px !important;
  flex-shrink: 0 !important;
}
/* Locked 态（auto 模式，可锁定）：ghost 风格，仅边框 + brand 文字 */
.annual-toggle-btn:not(.annual-toggle-btn--locked) {
  background: transparent !important;
  border: 1px solid var(--border-hairline) !important;
  color: var(--ink-soft) !important;
}
.annual-toggle-btn:not(.annual-toggle-btn--locked):hover {
  border-color: var(--brand) !important;
  color: var(--brand) !important;
  background: color-mix(in srgb, var(--brand) 8%, transparent) !important;
}
/* Locked 态（manual 模式，可解锁）：实心 brand 紫 + 白字，让"已被手动调整"在视觉上突出 */
.annual-toggle-btn--locked {
  border: 1px solid var(--brand) !important;
}
.annual-toggle-btn--locked:hover {
  filter: brightness(1.05);
}
/* 「均分年度目标」按钮（monthly 区） */
.monthly-redist-btn {
  font-size: 12px !important;
  padding: 0 10px !important;
  height: 26px !important;
  border-radius: var(--radius-sm, 6px) !important;
}
.view-manual { margin-left: 4px; }

/* 占比/人数 加和 callout 双指标 */
.sum-callout .sum-sep {
  margin: 0 6px;
  color: var(--ink-faint);
}
.dim-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--glass-bg-card);
  transition: opacity 0.15s ease, border-color 0.15s ease;
}
.dim-row.row-deleted { opacity: 0.62; border-style: dashed; border-color: var(--c-error); }
.dim-row.row-disabled { background: transparent; }
.dim-row-head { display: flex; align-items: center; gap: 10px; width: 100%; flex-wrap: wrap; }
.dim-row-id { display: flex; align-items: center; gap: 8px; flex: 1 1 auto; min-width: 160px; }
.dim-ind-name { font-weight: 600; color: var(--ink); min-width: 88px; }
.dim-row-ctrl { display: flex; align-items: center; gap: 10px; margin-left: auto; flex-wrap: wrap; }
.dim-row-view { display: flex; align-items: center; gap: 10px; margin-left: auto; color: var(--ink-soft); font-size: 13px; font-variant-numeric: tabular-nums; }
.dim-row-view .view-annual strong { font-weight: 700; color: var(--ink); }
.pct-suffix { font-size: 12px; color: var(--ink-soft); }
.dim-del-alert { margin-top: 12px; }
.dim-row-monthly {
  display: flex; flex-direction: column; gap: 6px;
  padding: 10px 12px;
  border: 1px dashed var(--border-hairline);
  border-radius: var(--radius-md);
  background: rgba(99, 102, 241, 0.03);
}
.dim-row-monthly--readonly {
  background: transparent;
  opacity: 0.85;
}
.dim-row-monthly .monthly-head,
.dim-row-monthly .monthly-foot { display: flex; align-items: center; gap: 12px; font-size: 12px; }
.dim-row-monthly .monthly-head { color: var(--ink-soft); justify-content: space-between; }
.dim-row-monthly .monthly-foot .allocated { color: var(--ink-soft); font-variant-numeric: tabular-nums; }
.month-val {
  display: inline-block; min-height: 28px; padding: 0 8px;
  line-height: 28px; font-variant-numeric: tabular-nums; font-size: 13px;
  background: var(--ink-faint); color: var(--ink); border-radius: 6px;
}

/* ===================== 弹窗级微调 ===================== */
.rule-modal :deep(.n-card__content),
.dim-ruleset-modal :deep(.n-card__content) {
  padding: 16px 20px 14px !important;
}
.rule-modal :deep(.n-card__footer),
.dim-ruleset-modal :deep(.n-card__footer) {
  padding: 10px 20px 14px !important;
}
.rule-modal :deep(.n-card-header__main),
.dim-ruleset-modal :deep(.n-card-header__main) {
  font-size: 16px;
  font-weight: 600;
}
.rule-modal :deep(.n-form-item),
.dim-ruleset-modal :deep(.n-form-item) {
  margin-bottom: 10px;
}
.rule-modal :deep(.n-form-item-label),
.dim-ruleset-modal :deep(.n-form-item-label) {
  font-size: 12px;
  padding-bottom: 4px !important;
}
.rule-modal :deep(.n-input-number--small) {
  --n-height: 28px !important;
}
.rule-modal :deep(.n-select--small) {
  --n-height: 28px !important;
}

.import-hint {
  margin: 12px 0 0;
  font-size: var(--text-small);
  color: var(--ink-soft);
  line-height: 1.6;
}
.import-result { margin-top: 16px; }
.import-error-actions {
  margin: 8px 0;
  display: flex;
  justify-content: flex-end;
}
.import-errors {
  margin: 8px 0 0;
  padding-left: 18px;
  max-height: 240px;
  overflow: auto;
}
.import-errors li {
  font-size: 12px;
  color: var(--c-error);
  margin-bottom: 4px;
}

/* 弹窗居中 + 内部滚动 + 去边框由全局 .n-modal .n-card（glass.css 阶段 F）统一处理，
   本页仅保留 .batch-modal 的密集表单紧凑间距微调。 */
</style>
