<template>
  <div class="cc-page">
    <!-- 渐变光斑背景 -->
    <div class="cc-aurora" aria-hidden="true">
      <span class="blob blob-a"></span>
      <span class="blob blob-b"></span>
      <span class="blob blob-c"></span>
    </div>

    <div class="cc-header">
      <div>
        <h1 class="cc-title">校招管控</h1>
        <p class="cc-subtitle">人员比例管控 · 每条规则独立适用范围（全局 / 部门·职务·职级）· 指标库 + 规则增删改</p>
      </div>
    </div>

    <div class="glass-panel">
      <n-tabs v-model:value="activeTab" type="line" class="cc-tabs" @update:value="onTabChange">
        <!-- ===================== 实时看板（含人数规划） ===================== -->
        <n-tab-pane name="ratio" tab="实时看板">
          <n-alert v-if="hasBadSum" type="warning" :show-icon="true" style="margin-bottom: 14px">
            存在目标占比未加和到 100% 的维度（见下方「加和」状态），请前往「规则配置」补全。
          </n-alert>
          <div class="toolbar">
            <n-input-number v-model:value="selectedYear" :min="2020" :max="2100" style="width: 130px" @update:value="loadPlan" />
            <n-select v-model:value="planMonth" :options="monthOptions" style="width: 140px" @update:value="loadPlan" />
            <div class="spacer"></div>
            <n-text depth="3" style="font-size: 12px">看板下方「人数达成」信息随年份 / 月份联动</n-text>
          </div>
          <div class="kpi-row">
            <div class="kpi-card"><span class="kpi-label">计入核算人数</span><span class="kpi-value">{{ ratioData.total }}</span></div>
            <div class="kpi-card"><span class="kpi-label">管控规则数</span><span class="kpi-value">{{ ratioData.rows.length }}</span></div>
            <div class="kpi-card danger"><span class="kpi-label">硬约束超标</span><span class="kpi-value">{{ ratioKpi.hard }}</span></div>
            <div class="kpi-card warn"><span class="kpi-label">软/仅提示超标</span><span class="kpi-value">{{ ratioKpi.soft }}</span></div>
            <div class="kpi-card"><span class="kpi-label">本月总缺口</span><span class="kpi-value">{{ planData.kpi.monthGap }}</span></div>
          </div>
          <div class="table-wrap">
            <n-data-table
              :columns="mergedColumns"
              :data="mergedRows"
              :loading="loading.ratio || loading.plan"
              :row-key="(r: any) => [r.bu, r.position, r.level, r.dimension, r.indicator].join('|')"
              :pagination="false"
              flex-height
            >
              <template #empty><n-empty description="暂无数据" /></template>
            </n-data-table>
          </div>

          <n-alert type="info" :show-icon="true" style="margin-top: 16px; flex-shrink: 0">
            本看板已合并「实时看板」与「人数规划」：上半部分展示各指标的<strong>占比管控</strong>（实际/分母、占比、目标、占比状态），
            下半部分展示<strong>人数达成</strong>（在职、年度目标/缺口、本月目标/实际/缺口）——目标数据（年度 / 12 个月）直接来源于「规则配置」。
          </n-alert>
        </n-tab-pane>

        <!-- ===================== 规则配置 ===================== -->
        <n-tab-pane name="rules" tab="规则配置">
          <div class="toolbar">
            <n-select v-model:value="ruleDimFilter" :options="ruleDimOptions" placeholder="全部维度" clearable style="width: 180px" />
            <div class="spacer"></div>
            <n-button @click="onExportRules">导出规则</n-button>
            <n-button @click="importDrawer.show = true">导入规则</n-button>
            <n-button type="primary" class="gradient-btn" @click="openBatchDrawer()">+ 批量配置规则 + 目标</n-button>
          </div>
          <div class="table-wrap">
            <n-data-table
              :columns="ruleColumns"
              :data="filteredRules"
              :loading="loading.rules"
              :row-key="(r: any) => r.id"
              :pagination="false"
              flex-height
            >
              <template #empty>
                <n-empty description="暂无规则，点击右上角「新增规则」从指标库中选择指标并设定适用范围" />
              </template>
            </n-data-table>
          </div>
        </n-tab-pane>

        <!-- ===================== 指标管理（维度 + 指标库） ===================== -->
        <n-tab-pane name="indicators" tab="指标管理">
          <div class="toolbar">
            <n-select v-model:value="indicatorDimFilter" :options="indicatorDimOptions" placeholder="全部维度" clearable style="width: 180px" />
            <n-button @click="openDimDrawer()">管理维度</n-button>
            <div class="spacer"></div>
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

    <!-- ===================== 规则详情弹窗（新增/编辑，页面居中） ===================== -->
    <n-modal
      v-model:show="ruleDrawer.show"
      preset="card"
      :title="ruleDrawer.editingId ? '编辑规则' : '新增规则'"
      :style="{ width: '620px', maxWidth: '94vw' }"
      :bordered="false"
      :segmented="{ content: true, footer: true }"
      class="rule-modal"
    >
      <n-form label-placement="top">
        <n-form-item label="维度" required>
          <n-select v-model:value="ruleDrawer.dimensionId" :options="dimensionOptions" placeholder="选择维度" @update:value="onRuleDimChange" />
        </n-form-item>
        <n-form-item label="指标（来自指标库）" required>
          <n-select v-model:value="ruleDrawer.indicatorId" :options="ruleIndicatorOptions" placeholder="先选维度，再从指标库选择" />
        </n-form-item>
        <n-divider>适用范围（每个指标独立设定）</n-divider>
        <n-form-item label="适用范围">
          <n-switch v-model:value="ruleDrawer.isGlobal" @update:value="onRuleScopeToggle">
            <template #checked>全局</template>
            <template #unchecked>指定</template>
          </n-switch>
        </n-form-item>
        <n-form-item v-if="!ruleDrawer.isGlobal" label="部门">
          <n-select v-model:value="ruleDrawer.bu" :options="deptOptions" placeholder="部门" />
        </n-form-item>
        <n-form-item v-if="!ruleDrawer.isGlobal" label="职务">
          <n-select v-model:value="ruleDrawer.position" :options="positionOptions" placeholder="职务(不限)" clearable />
        </n-form-item>
        <n-form-item v-if="!ruleDrawer.isGlobal" label="职级">
          <n-select v-model:value="ruleDrawer.level" :options="levelOptions" placeholder="职级(不限)" clearable />
        </n-form-item>
        <n-divider>管控占比（占比上限）</n-divider>
        <n-form-item label="目标占比 %"><n-input-number v-model:value="ruleDrawer.targetPct" :min="0" :max="100" :step="0.5" style="width: 100%" /></n-form-item>
        <n-form-item label="控制强度">
          <n-select v-model:value="ruleDrawer.strength" :options="strengthOptions" />
        </n-form-item>
        <n-divider>管控人数（年度 + 12 月）</n-divider>
        <n-grid :cols="2" :x-gap="12">
          <n-gi><n-form-item label="规划年度"><n-input-number v-model:value="ruleDrawer.year" :min="2020" :max="2100" style="width: 100%" /></n-form-item></n-gi>
          <n-gi><n-form-item label="年度目标人数"><n-input-number v-model:value="ruleDrawer.annualTarget" :min="0" style="width: 100%" /></n-form-item></n-gi>
        </n-grid>
        <n-divider>12 个月目标（单位：人）</n-divider>
        <n-grid :cols="4" :x-gap="8" :y-gap="8">
          <n-gi v-for="(_, i) in 12" :key="i">
            <n-form-item :label="ALL_MONTHS[i]" label-placement="top">
              <n-input-number v-model:value="ruleDrawer.monthly[i]" :min="0" style="width: 100%" />
            </n-form-item>
          </n-gi>
        </n-grid>
      </n-form>
      <template #footer>
        <div class="drawer-footer">
          <n-button @click="ruleDrawer.show = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" :loading="loading.saveRule" @click="saveRule">保存</n-button>
        </div>
      </template>
    </n-modal>

    <!-- ===================== 批量配置规则 + 人数目标弹窗 ===================== -->
    <n-modal
      v-model:show="batchDrawer.show"
      preset="card"
      title="批量配置规则 + 人数目标"
      :style="{ width: '760px', maxWidth: '92vw' }"
      :bordered="false"
      :segmented="{ content: true, footer: true }"
      class="batch-modal"
    >
      <n-form label-placement="top" size="small">
        <n-form-item label="维度" required :show-feedback="false">
          <n-select v-model:value="batchDrawer.dimensionId" :options="dimensionOptions" placeholder="先选维度" @update:value="onBatchDimChange" />
        </n-form-item>
        <n-divider style="margin: 10px 0;">适用范围（每个指标的适用范围独立配置）</n-divider>
        <n-grid :cols="4" :x-gap="12">
          <n-gi>
            <n-form-item label="适用范围" :show-feedback="false">
              <n-switch v-model:value="batchDrawer.isGlobal">
                <template #checked>全局</template>
                <template #unchecked>指定</template>
              </n-switch>
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item v-if="!batchDrawer.isGlobal" label="部门" :show-feedback="false">
              <n-select v-model:value="batchDrawer.bu" :options="deptOptions" placeholder="部门" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item v-if="!batchDrawer.isGlobal" label="职务" :show-feedback="false">
              <n-select v-model:value="batchDrawer.position" :options="positionOptions" placeholder="职务(不限)" clearable />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item v-if="!batchDrawer.isGlobal" label="职级" :show-feedback="false">
              <n-select v-model:value="batchDrawer.level" :options="levelOptions" placeholder="职级(不限)" clearable />
            </n-form-item>
          </n-gi>
        </n-grid>
        <n-divider style="margin: 10px 0;">总人数 → 各指标人数</n-divider>
        <n-grid :cols="2" :x-gap="12">
          <n-gi><n-form-item label="年度" :show-feedback="false"><n-input-number v-model:value="batchDrawer.year" :min="2020" :max="2100" style="width: 100%" /></n-form-item></n-gi>
          <n-gi><n-form-item label="年度总人数（管控人数）" :show-feedback="false"><n-input-number v-model:value="batchDrawer.totalTarget" :min="0" style="width: 100%" /></n-form-item></n-gi>
        </n-grid>
        <n-divider style="margin: 10px 0;">指标与占比（占比之和 = 100%）</n-divider>
        <div v-if="!batchDrawer.dimensionId" style="color: var(--ink-faint); padding: 8px 0; font-size: 13px;">请先选择维度</div>
        <div v-else-if="batchIndicators.length === 0" style="color: var(--ink-faint); padding: 8px 0; font-size: 13px;">该维度下暂无指标，请先到「指标管理」新增</div>
        <div v-else>
          <div v-for="ind in batchIndicators" :key="ind.id" class="batch-row" :class="{ expanded: batchDrawer.indicatorIds.includes(ind.id) }">
            <div class="batch-row-header">
              <n-checkbox :checked="batchDrawer.indicatorIds.includes(ind.id)" @update:checked="(v: boolean) => onBatchIndicatorToggle(ind, v)">
                <span style="font-weight: 500; font-size: 13px;">{{ ind.name }}</span>
              </n-checkbox>
              <span v-if="batchDrawer.indicatorIds.includes(ind.id)" class="batch-row-controls">
                <span class="batch-row-label">占比%</span>
                <n-input-number :value="batchDrawer.rows[ind.id]?.targetPct || 0" :min="0" :max="100" :step="0.5" size="small" style="width: 78px" @update:value="(v: number | null) => setBatchRow(ind.id, 'targetPct', v || 0)" />
                <n-select :value="batchDrawer.rows[ind.id]?.strength || '硬约束'" :options="strengthOptions" size="small" style="width: 90px" @update:value="(v: string) => setBatchRow(ind.id, 'strength', v as Strength)" />
                <span class="batch-row-annual">年度 {{ batchIndicatorAnnual(ind.id) }} 人</span>
              </span>
            </div>
            <div v-if="batchDrawer.indicatorIds.includes(ind.id)" class="batch-monthly-panel">
              <div class="batch-monthly-header">
                <span class="batch-row-label">12 个月度目标（单位：人）</span>
                <n-button text type="primary" size="tiny" @click="redistributeBatchMonthly(ind.id)">均分年度目标</n-button>
              </div>
              <n-grid :cols="6" :x-gap="6" :y-gap="4">
                <n-gi v-for="(_, i) in 12" :key="i">
                  <n-form-item :label="ALL_MONTHS[i]" label-placement="top" :show-feedback="false" :label-style="{ fontSize: '11px', paddingBottom: '2px' }">
                    <n-input-number :value="batchDrawer.rows[ind.id]?.monthly?.[i] || 0" :min="0" size="small" style="width: 100%" @update:value="(v: number | null) => setBatchMonthly(ind.id, i, v)" />
                  </n-form-item>
                </n-gi>
              </n-grid>
              <div class="batch-monthly-sum">
                已分配：{{ (batchDrawer.rows[ind.id]?.monthly || []).reduce((a, b) => a + (b || 0), 0) }} 人
                <n-tag v-if="(batchDrawer.rows[ind.id]?.monthly || []).reduce((a, b) => a + (b || 0), 0) === batchIndicatorAnnual(ind.id)" type="success" size="small" :bordered="false">✓ 等于年度目标</n-tag>
                <n-tag v-else type="warning" size="small" :bordered="false">⚠ 不等于年度目标 {{ batchIndicatorAnnual(ind.id) }} 人</n-tag>
              </div>
            </div>
          </div>
          <div class="batch-sum">
            <span class="batch-row-label">占比之和：</span>
            <n-tag :type="batchSumOk ? 'success' : 'warning'" :bordered="false" size="small">
              {{ batchSumPct.toFixed(1) }}% {{ batchSumOk ? '✓ = 100%' : '⚠ 需 = 100%' }}
            </n-tag>
            <span v-if="!batchSumOk" class="batch-row-label">（差 {{ (100 - batchSumPct).toFixed(1) }}%）</span>
          </div>
        </div>
      </n-form>
      <template #footer>
        <div class="drawer-footer">
          <n-button size="small" @click="batchDrawer.show = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" size="small" :loading="loading.batchConfig" :disabled="!batchSumOk || !batchMonthlyOk || batchDrawer.indicatorIds.length === 0" @click="saveBatchConfig">保存</n-button>
        </div>
      </template>
    </n-modal>

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
import { ref, reactive, computed, h, onMounted } from 'vue'
import {
  NTag, NButton, NSwitch, NCheckbox, NDivider, NSpace,
  NInputNumber, NSelect, NInput, NEmpty, NAlert, NDatePicker,
  useMessage, useDialog, type DataTableColumns,
} from 'naive-ui'
import { extractApiError } from '../../api/dynamic-field'
import {
  listDimensions, createDimension, updateDimension, deleteDimension,
  listIndicators, createIndicator, updateIndicator, deleteIndicator,
  listRules, createRule, updateRule, deleteRule, batchConfigRules,
  getRatio, getPlan, validateDraft,
  listPersons, upsertPerson, deletePerson,
  exportRules, downloadRuleTemplate, importRules, triggerDownload,
  DEPTS, SCHOOLS, MAJORS, SEXES, ALL_MONTHS, STRENGTH, STATUS, POSITIONS, LEVELS,
  type ControlDimension, type ControlIndicator, type ControlRule,
  type Person, type RatioRow, type RatioResult, type PlanRow, type PlanResult,
  type ValidationResult, type Strength, type RuleInput, type BatchConfigPayload,
  type RuleImportResult,
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
  ratio: false, plan: false, rules: false, saveRule: false, batchConfig: false,
  dimensions: false, indicators: false, persons: false, validate: false,
  import: false,
})
const dimensions = ref<ControlDimension[]>([])
const indicators = ref<ControlIndicator[]>([])
const rules = ref<ControlRule[]>([])
const persons = ref<Person[]>([])

const selectedYear = ref(2026)
const planMonth = ref('8月')

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

/* ============================ 人数规划 ============================ */
const planData = ref<PlanResult>({
  rows: [],
  kpi: { total: 0, ruleCount: 0, warnCount: 0, hardViolationCount: 0, monthGap: 0 },
  year: 2026,
})

/* ============================ 实时看板 + 人数规划 合并行 ============================ */
// 以实时看板（ratio）为主，左连接人数规划（plan）；plan 缺失的指标，人数达成字段留空。
const mergedRows = computed(() => {
  const planMap = new Map<string, PlanRow>()
  for (const p of planData.value.rows) {
    planMap.set([p.bu, p.position, p.level, p.dimension, p.indicator].join('|'), p)
  }
  const out: any[] = []
  for (const r of ratioData.value.rows) {
    const key = [r.bu, r.position, r.level, r.dimension, r.indicator].join('|')
    const p = planMap.get(key)
    out.push({
      bu: r.bu, position: r.position, level: r.level, dimension: r.dimension, indicator: r.indicator,
      actual: r.actual, denom: r.denom, ratio: r.ratio, target: r.target,
      ratioStatus: r.status, strength: r.strength,
      onjob: p?.onjob ?? null,
      pendingOffer: p?.pendingOffer ?? null,
      pendingEntry: p?.pendingEntry ?? null,
      annualTarget: p?.annualTarget ?? null,
      annualGap: p?.annualGap ?? null,
      monthTarget: p?.monthTarget ?? null,
      monthActual: p?.monthActual ?? null,
      gap: p?.gap ?? null,
      countStatus: p?.status ?? null,
    })
  }
  // 把 plan 中有、ratio 中无的行（占比未算到但有人数目标）也补进来
  const ratioKeys = new Set(out.map((o) => [o.bu, o.position, o.level, o.dimension, o.indicator].join('|')))
  for (const p of planData.value.rows) {
    const key = [p.bu, p.position, p.level, p.dimension, p.indicator].join('|')
    if (ratioKeys.has(key)) continue
    out.push({
      bu: p.bu, position: p.position, level: p.level, dimension: p.dimension, indicator: p.indicator,
      actual: null, denom: null, ratio: null, target: null,
      ratioStatus: null, strength: p.strength ?? null,
      onjob: p.onjob ?? null,
      pendingOffer: p.pendingOffer ?? null,
      pendingEntry: p.pendingEntry ?? null,
      annualTarget: p.annualTarget ?? null,
      annualGap: p.annualGap ?? null,
      monthTarget: p.monthTarget ?? null,
      monthActual: p.monthActual ?? null,
      gap: p.gap ?? null,
      countStatus: p.status ?? null,
    })
  }
  return out
})

/* ============================ 规则配置 ============================ */
const currentMonthIdx = computed(() => new Date().getMonth()) // 0=1月
const ruleDimFilter = ref<string | null>(null)
const ruleDimOptions = computed(() => [
  { label: '全部维度', value: '' },
  ...dimensions.value.map((d) => ({ label: d.name, value: d.id })),
])
const filteredRules = computed(() => {
  if (!ruleDimFilter.value) return rules.value
  return rules.value.filter((r) => r.dimension === ruleDimFilter.value)
})

// 每条规则所属 (适用范围, 维度) 组的加和
const ruleSumMap = computed(() => {
  const m = new Map<string, number>()
  for (const r of rules.value) {
    const k = [r.bu, r.position, r.level, r.dimension].join('|')
    m.set(k, (m.get(k) || 0) + r.target)
  }
  return m
})

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
async function loadPlan() {
  loading.plan = true
  try { planData.value = await getPlan(selectedYear.value, planMonth.value) }
  catch (e) { message.error(extractApiError(e, '加载规划失败')) }
  finally { loading.plan = false }
}

function onTabChange(name: string) {
  if (name === 'ratio') { loadRatio(); loadPlan() }
  else if (name === 'rules') loadRules()
  else if (name === 'persons') loadPersons()
  else if (name === 'indicators') loadIndicators()
}

/* ============================ 列定义 ============================ */
// 实时看板（实时看板 + 人数规划 合并）
const mergedColumns: DataTableColumns<any> = [
  { title: '适用范围', key: 'bu', width: 150, fixed: 'left', render: (r) => scopeText(r.bu, r.position, r.level) },
  { title: '维度', key: 'dimension', width: 90, fixed: 'left' },
  { title: '指标', key: 'indicator', width: 80, fixed: 'left' },
  // —— 占比管控（来自实时看板）—— //
  { title: '实际/分母', key: 'actual', width: 100, render: (r) => `${r.actual ?? '-'} / ${r.denom ?? '-'}` },
  { title: '占比', key: 'ratio', width: 76, render: (r) => r.ratio == null ? h(NTag, { type: 'default', bordered: false, size: 'small' }, { default: () => '—' }) : h(NTag, { type: 'default', bordered: false, size: 'small' }, { default: () => pct(r.ratio) }) },
  { title: '目标', key: 'target', width: 68, render: (r) => r.target == null ? '—' : pct(r.target) },
  { title: '占比状态', key: 'ratioStatus', width: 100, render: (r) => h(NTag, { type: ratioStatusType(r.ratioStatus || '正常'), bordered: false, size: 'small' }, { default: () => r.ratioStatus || '—' }) },
  { title: '强度', key: 'strength', width: 88, render: (r) => r.strength ? h(NTag, { type: strengthType(r.strength), bordered: false, size: 'small' }, { default: () => r.strength }) : h('span', { style: 'color:var(--ink-soft)' }, '—') },
  // —— 人数达成（来自人数规划）—— //
  { title: '在职', key: 'onjob', width: 66 },
  { title: '在途 Offer', key: 'pendingOffer', width: 88 },
  { title: '在途待入职', key: 'pendingEntry', width: 90 },
  { title: '年度目标', key: 'annualTarget', width: 86 },
  { title: '年度缺口', key: 'annualGap', width: 86, render: (r) => r.annualTarget == null ? '—' : r.annualGap },
  { title: '本月目标', key: 'monthTarget', width: 86 },
  { title: '本月实际', key: 'monthActual', width: 86 },
  { title: '缺口', key: 'gap', width: 66, render: (r) => r.monthTarget == null ? '—' : r.gap },
  { title: '人数状态', key: 'countStatus', width: 100, render: (r) => r.countStatus ? h(NTag, { type: countStatusType(r.countStatus), bordered: false, size: 'small' }, { default: () => r.countStatus }) : h('span', { style: 'color:var(--ink-soft)' }, '—') },
]

const ruleColumns: DataTableColumns<ControlRule> = [
  { title: '维度', key: 'dimensionName', width: 110 },
  { title: '指标', key: 'indicatorName', width: 100 },
  {
    title: '适用范围', key: 'bu', width: 170,
    render: (r) => h(NTag, { type: r.bu || r.position || r.level ? 'info' : 'success', bordered: false, size: 'small' }, { default: () => scopeText(r.bu, r.position, r.level) }),
  },
  { title: '目标占比', key: 'target', width: 90, render: (r) => pct(r.target) },
  { title: '规划年度', key: 'year', width: 80 },
  { title: '年度目标', key: 'annualTarget', width: 80 },
  { title: '本月目标', key: 'monthTarget', width: 80, render: (r: any) => (r.monthlyTargets || [])[currentMonthIdx.value] ?? 0 },
  { title: '强度', key: 'strength', width: 90, render: (r) => h(NTag, { type: strengthType(r.strength), bordered: false, size: 'small' }, { default: () => r.strength }) },
  {
    title: '加和', key: 'sum', width: 90,
    render: (r) => {
      const s = (ruleSumMap.value.get([r.bu, r.position, r.level, r.dimension].join('|')) || 0) * 100
      const ok = Math.abs(s - 100) < 0.05
      return h(NTag, { type: ok ? 'success' : 'warning', bordered: false, size: 'small' }, { default: () => `${s.toFixed(1)}%${ok ? ' ✓' : ' ⚠'}` })
    },
  },
  {
    title: '操作', key: 'actions', width: 120, fixed: 'right',
    render: (r) => h('div', { style: 'display:flex; gap:8px;' }, [
      h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openRuleDrawer(r) }, { default: () => '编辑' }),
      h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeRule(r) }, { default: () => '删除' }),
    ]),
  },
]

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

const checkColumns: DataTableColumns<ValidationResult['checks'][number]> = [
  { title: '适用范围', key: 'bu', width: 150, render: (r) => scopeText(r.bu, r.position, r.level) },
  { title: '维度', key: 'dimension', width: 100 }, { title: '指标', key: 'indicator', width: 90 },
  { title: '强度', key: 'strength', width: 90, render: (r) => h(NTag, { type: strengthType(r.strength), bordered: false, size: 'small' }, { default: () => r.strength }) },
  { title: '占比', key: 'ratio', width: 80, render: (r) => pct(r.ratio) },
  { title: '占比状态', key: 'ratioStatus', width: 100, render: (r) => h(NTag, { type: ratioStatusType(r.ratioStatus), bordered: false, size: 'small' }, { default: () => r.ratioStatus }) },
  { title: '本月实际', key: 'monthActual', width: 90 }, { title: '本月目标', key: 'monthTarget', width: 90 },
  { title: '人数状态', key: 'countStatus', width: 100, render: (r) => h(NTag, { type: countStatusType(r.countStatus), bordered: false, size: 'small' }, { default: () => r.countStatus }) },
]

/* ============================ 规则详情抽屉 ============================ */
const ruleDrawer = reactive({
  show: false,
  editingId: '' as string | null,
  dimensionId: '' as string | null,
  indicatorId: '' as string | null,
  isGlobal: true,
  bu: '', position: '', level: '',
  targetPct: 50, year: 2026, annualTarget: 0, monthly: Array(12).fill(0),
  strength: '硬约束' as Strength,
})

const ruleIndicatorOptions = computed(() => {
  if (!ruleDrawer.dimensionId) return []
  return indicators.value
    .filter((i) => i.dimension === ruleDrawer.dimensionId)
    .map((i) => ({ label: i.name, value: i.id }))
})

function openRuleDrawer(rule?: ControlRule) {
  ruleDrawer.editingId = rule?.id ?? null
  ruleDrawer.dimensionId = rule?.dimension ?? null
  ruleDrawer.indicatorId = rule?.indicator ?? null
  ruleDrawer.isGlobal = !(rule?.bu || rule?.position || rule?.level)
  ruleDrawer.bu = rule?.bu ?? ''
  ruleDrawer.position = rule?.position ?? ''
  ruleDrawer.level = rule?.level ?? ''
  ruleDrawer.targetPct = rule ? Math.round(rule.target * 1000) / 10 : 50
  ruleDrawer.year = rule?.year ?? 2026
  ruleDrawer.annualTarget = rule ? Number(rule.annualTarget) || 0 : 0
  ruleDrawer.monthly = rule
    ? Array.from({ length: 12 }, (_, i) => Number(rule.monthlyTargets?.[i]) || 0)
    : Array(12).fill(0)
  ruleDrawer.strength = rule?.strength ?? '硬约束'
  ruleDrawer.show = true
}

function onRuleDimChange() {
  ruleDrawer.indicatorId = null
}
function onRuleScopeToggle(v: boolean) {
  if (!v && !ruleDrawer.bu) ruleDrawer.bu = DEPTS[0]
}

async function saveRule() {
  if (!ruleDrawer.dimensionId) { message.warning('请选择维度'); return }
  if (!ruleDrawer.indicatorId) { message.warning('请从指标库中选择指标'); return }
  const payload: RuleInput = {
    bu: ruleDrawer.isGlobal ? '' : ruleDrawer.bu,
    position: ruleDrawer.isGlobal ? '' : ruleDrawer.position,
    level: ruleDrawer.isGlobal ? '' : ruleDrawer.level,
    dimension: ruleDrawer.dimensionId,
    indicator: ruleDrawer.indicatorId,
    year: ruleDrawer.year,
    target: ruleDrawer.targetPct / 100,
    strength: ruleDrawer.strength,
    annualTarget: Math.round(ruleDrawer.annualTarget) || 0,
    monthlyTargets: ruleDrawer.monthly.map((v) => Math.round(v) || 0),
  }
  loading.saveRule = true
  try {
    if (ruleDrawer.editingId) await updateRule(ruleDrawer.editingId, payload)
    else await createRule(payload)
    message.success('保存成功')
    ruleDrawer.show = false
    await Promise.all([loadRules(), loadRatio(), loadPlan()])
  } catch (e) { message.error(extractApiError(e, '保存失败')) }
  finally { loading.saveRule = false }
}

function removeRule(r: ControlRule) {
  dialog.warning({
    title: '删除规则', content: `确认删除「${r.dimensionName} · ${r.indicatorName}（${scopeText(r.bu, r.position, r.level)}）」？`, positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try { await deleteRule(r.id); message.success('删除成功'); await Promise.all([loadRules(), loadRatio(), loadPlan()]) }
      catch (e) { message.error(extractApiError(e, '删除失败')) }
    },
  })
}

/* ============================ 规则导入 / 导出 ============================ */
const importDrawer = reactive({
  show: false,
  fileList: [] as any[],
  result: null as RuleImportResult | null,
})

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
        loadPlan()
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

/* ============================ 批量配置规则 + 人数目标 ============================ */
interface BatchRow {
  targetPct: number
  strength: Strength
  monthly: number[] // 12 个月度目标
}
const batchDrawer = reactive({
  show: false,
  dimensionId: '' as string | null,
  indicatorIds: [] as string[],
  isGlobal: true,
  bu: '', position: '', level: '',
  year: 2026,
  totalTarget: 0,
  rows: {} as Record<string, BatchRow>,
})

const batchIndicators = computed(() => {
  if (!batchDrawer.dimensionId) return []
  return indicators.value.filter((i) => i.dimension === batchDrawer.dimensionId)
})

const batchSumPct = computed(() => {
  let s = 0
  for (const id of batchDrawer.indicatorIds) {
    const r = batchDrawer.rows[id]
    if (r) s += r.targetPct || 0
  }
  return s
})
const batchSumOk = computed(() => Math.abs(batchSumPct.value - 100) < 0.05)
const batchMonthlyOk = computed(() => {
  for (const id of batchDrawer.indicatorIds) {
    const r = batchDrawer.rows[id]
    if (!r) return false
    const annual = batchIndicatorAnnual(id)
    const sum = (r.monthly || []).reduce((a, b) => a + (b || 0), 0)
    if (sum !== annual) return false
  }
  return true
})

function openBatchDrawer() {
  batchDrawer.dimensionId = null
  batchDrawer.indicatorIds = []
  batchDrawer.isGlobal = true
  batchDrawer.bu = ''; batchDrawer.position = ''; batchDrawer.level = ''
  batchDrawer.year = 2026
  batchDrawer.totalTarget = 0
  batchDrawer.rows = {}
  batchDrawer.show = true
}

function onBatchDimChange() {
  batchDrawer.indicatorIds = []
  batchDrawer.rows = {}
}

function distributeMonthly(annual: number): number[] {
  const base = Math.floor(annual / 12)
  const rem = annual - base * 12
  return Array.from({ length: 12 }, (_, i) => base + (i < rem ? 1 : 0))
}

function onBatchIndicatorToggle(ind: ControlIndicator, checked: boolean) {
  if (checked) {
    batchDrawer.indicatorIds = [...batchDrawer.indicatorIds, ind.id]
    // 首个勾选时均分剩余比例（提示用户）
    const curCount = batchDrawer.indicatorIds.length
    const equal = curCount > 0 ? Math.round((100 / curCount) * 10) / 10 : 0
    const annual = Math.round((batchDrawer.totalTarget || 0) * (equal / 100))
    batchDrawer.rows = { ...batchDrawer.rows, [ind.id]: { targetPct: equal, strength: '硬约束', monthly: distributeMonthly(annual) } }
  } else {
    batchDrawer.indicatorIds = batchDrawer.indicatorIds.filter((id) => id !== ind.id)
    const nr: Record<string, BatchRow> = {}
    for (const id of batchDrawer.indicatorIds) nr[id] = batchDrawer.rows[id]
    batchDrawer.rows = nr
  }
}

function setBatchRow(id: string, key: keyof BatchRow, val: any) {
  batchDrawer.rows = { ...batchDrawer.rows, [id]: { ...batchDrawer.rows[id], [key]: val } }
}
function setBatchMonthly(id: string, idx: number, val: number | null) {
  const monthly = [...(batchDrawer.rows[id]?.monthly || Array(12).fill(0))]
  monthly[idx] = Math.max(0, Math.round(val || 0))
  setBatchRow(id, 'monthly', monthly)
}
function redistributeBatchMonthly(id: string) {
  const r = batchDrawer.rows[id]
  if (!r) return
  setBatchRow(id, 'monthly', distributeMonthly(batchIndicatorAnnual(id)))
}

function batchIndicatorAnnual(indId: string) {
  const r = batchDrawer.rows[indId]
  if (!r) return 0
  return Math.round(batchDrawer.totalTarget * (r.targetPct / 100))
}

async function saveBatchConfig() {
  if (!batchDrawer.dimensionId) { message.warning('请选择维度'); return }
  if (batchDrawer.indicatorIds.length === 0) { message.warning('请至少勾选一个指标'); return }
  if (!batchSumOk.value) {
    message.warning(`占比之和须=100%，当前 ${batchSumPct.value.toFixed(1)}%`); return
  }
  if (!batchMonthlyOk.value) {
    message.warning('存在指标的 12 个月度目标之和不等于年度目标，请检查或点击「均分年度目标」'); return
  }

  const payload: BatchConfigPayload = {
    bu: batchDrawer.isGlobal ? '' : batchDrawer.bu,
    position: batchDrawer.isGlobal ? '' : batchDrawer.position,
    level: batchDrawer.isGlobal ? '' : batchDrawer.level,
    dimension: batchDrawer.dimensionId,
    year: batchDrawer.year,
    totalTarget: batchDrawer.totalTarget,
    rules: batchDrawer.indicatorIds.map((id) => {
      const r = batchDrawer.rows[id]
      return {
        indicator: id,
        target: r.targetPct / 100,
        strength: r.strength,
        monthlyTargets: (r.monthly || []).map((v) => Math.round(v) || 0),
      }
    }),
  }
  loading.batchConfig = true
  try {
    const res = await batchConfigRules(payload)
    message.success(`已保存 ${res.data.saved} 条规则 + ${res.data.saved} 项目标（总人数 ${res.data.totalTarget}）`)
    batchDrawer.show = false
    await Promise.all([loadRules(), loadRatio(), loadPlan()])
  } catch (e) {
    message.error(extractApiError(e, '保存失败'))
  } finally {
    loading.batchConfig = false
  }
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
  await Promise.all([loadRatio(), loadPlan(), loadRules()])
})
</script>

<style scoped>
.cc-page {
  position: relative;
  min-height: 100%;
  height: 100%;
  border-radius: 16px;
  overflow: hidden;
  padding: 16px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}
.cc-aurora { position: absolute; inset: 0; pointer-events: none; }
.blob { position: absolute; border-radius: 50%; filter: blur(60px); opacity: 0.55; }
.blob-a { width: 520px; height: 520px; top: -220px; left: -140px; background: radial-gradient(circle, rgba(99,102,241,0.28), transparent 65%); }
.blob-b { width: 460px; height: 460px; top: -80px; right: -160px; background: radial-gradient(circle, rgba(236,72,153,0.18), transparent 65%); }
.blob-c { width: 420px; height: 420px; bottom: -180px; left: 40%; background: radial-gradient(circle, rgba(34,197,94,0.14), transparent 65%); }

.cc-header { position: relative; z-index: 1; margin-bottom: 16px; padding-top: 0; padding-bottom: 0; flex-shrink: 0; }
.cc-title {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--brand) 0%, var(--brand-grad-a) 55%, var(--brand-grad-b) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.cc-subtitle { margin: 6px 0 0; color: var(--ink-soft); font-size: var(--text-small); }

.glass-panel {
  position: relative;
  z-index: 1;
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--glass-blur-card));
  -webkit-backdrop-filter: blur(var(--glass-blur-card));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: var(--space-4) var(--space-4);
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
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
.table-wrap {
  flex: 1;
  min-height: 180px;
  overflow: hidden;
  position: relative;
  display: flex;
  flex-direction: column;
}
.table-wrap :deep(.n-data-table) {
  flex: 1;
  min-height: 0;
  /* ★ 与外层 glass-panel 圆角一致，避免表格直角与面板圆角重叠 */
  border-radius: var(--radius-md);
  overflow: hidden;
}
/* 表格内部层级圆角统一：
   - wrapper/header/body 分别负责上/下半圆角
   - table 根背景透明，避免 light 模式下白色直角底露出
   - th 首尾单元格顶角分别圆角，避免 thead 背景直角顶穿 */
.table-wrap :deep(.n-data-table-wrapper) { border-radius: var(--radius-md); overflow: hidden; }
.table-wrap :deep(.n-data-table-base-table-header) { border-radius: var(--radius-md) var(--radius-md) 0 0 !important; overflow: hidden; }
.table-wrap :deep(.n-data-table-base-table-body) { border-radius: 0 0 var(--radius-md) var(--radius-md); overflow: hidden; }
.table-wrap :deep(.n-data-table-table) { background: transparent !important; border-radius: 0; }
.table-wrap :deep(.n-data-table-thead) { border-radius: var(--radius-md) var(--radius-md) 0 0; overflow: hidden; }
.table-wrap :deep(.n-data-table-th:first-child) { border-top-left-radius: var(--radius-md); }
.table-wrap :deep(.n-data-table-th:last-child) { border-top-right-radius: var(--radius-md); }
.validate-result {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  margin-top: var(--space-4);
}

.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.spacer { flex: 1; }

.gradient-btn {
  background: linear-gradient(135deg, var(--brand), var(--brand-grad-a));
  border: none;
  box-shadow: 0 4px 14px var(--glow-brand);
  transition: all var(--duration-base) var(--ease-out);
}
.gradient-btn:hover { box-shadow: 0 6px 20px var(--glow-brand); transform: translateY(-1px); }

.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-3); margin-bottom: var(--space-4); }
.kpi-card {
  position: relative;
  z-index: 1;
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--glass-blur-card));
  -webkit-backdrop-filter: blur(var(--glass-blur-card));
  /* 去掉边框与投影，让 KPI 卡片完全融入玻璃面板，消除边界感 */
  border: none;
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  box-shadow: none;
  transition: all var(--duration-base) var(--ease-out);
}
.kpi-card:hover {
  /* 无投影：仅通过背景微亮 + 轻微上移提供反馈，保持无边际感 */
  background: var(--brand-a12);
  transform: translateY(-2px);
}
.kpi-card.danger:hover { background: rgba(239, 68, 68, .12); }
.kpi-card.warn:hover { background: rgba(245, 158, 11, .12); }
.kpi-label { font-size: var(--text-meta); color: var(--ink-soft); }
.kpi-value { font-size: 26px; font-weight: 700; color: var(--ink); }
.kpi-card.danger .kpi-value { color: var(--c-error); }
.kpi-card.warn .kpi-value { color: var(--c-warning); }

.block-hint { color: var(--c-error); font-size: var(--text-small); margin: var(--space-2) 0 0; }

.drawer-footer { display: flex; justify-content: flex-end; gap: var(--space-3); }

.batch-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3) 0;
  border-bottom: 1px dashed var(--border-hairline);
}
.batch-row-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
}
.batch-row-controls { flex: 1; display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.batch-row-label { color: var(--ink-soft); font-size: var(--text-meta); }
.batch-row-annual {
  margin-left: auto;
  color: var(--brand);
  font-size: var(--text-meta);
  font-weight: 600;
  min-width: 88px;
  text-align: right;
}
.batch-monthly-panel {
  width: 100%;
  padding: var(--space-3) var(--space-3) var(--space-2);
  background: var(--glass-bg-input);
  border-radius: var(--radius-sm);
  border: 1px solid var(--brand-a12);
}
.batch-monthly-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.batch-monthly-sum {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--ink);
}
.batch-sum {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 0 0;
  margin-top: 10px;
  border-top: 1px solid var(--border-hairline);
}

/* 批量配置弹窗：居中 + 紧凑 */
.batch-modal :deep(.n-card__content) {
  padding: 16px 20px 12px !important;
}
.batch-modal :deep(.n-card__footer) {
  padding: 10px 20px 14px !important;
}
.batch-modal :deep(.n-card-header__main) {
  font-size: 16px;
  font-weight: 600;
}
.batch-modal :deep(.n-form-item) {
  margin-bottom: 8px;
}
.batch-modal :deep(.n-form-item-label) {
  font-size: 12px;
  padding-bottom: 4px !important;
}
.batch-modal :deep(.n-divider__title) {
  font-size: 12px;
  color: var(--ink-soft);
}
.batch-modal :deep(.n-checkbox__label) {
  font-size: 13px;
}
.batch-modal .batch-row {
  padding: 8px 0;
  gap: 8px;
}
.batch-modal .batch-monthly-panel {
  padding: 8px 10px;
}
.batch-modal .batch-monthly-header {
  margin-bottom: 6px;
}
.batch-modal .batch-monthly-sum {
  margin-top: 6px;
}
.batch-modal :deep(.n-input-number--small) {
  --n-height: 28px !important;
}
.batch-modal :deep(.n-select--small) {
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

/* 校招管控：弹窗统一页面居中 + 高度自适应屏幕（超出 90vh 内部滚动） */
.import-modal :deep(.n-card),
.dim-modal :deep(.n-card),
.rule-modal :deep(.n-card) {
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}
.import-modal :deep(.n-card__content),
.dim-modal :deep(.n-card__content),
.rule-modal :deep(.n-card__content) {
  overflow-y: auto;
  max-height: calc(90vh - 110px);
}
.import-modal :deep(.n-card-header__main),
.dim-modal :deep(.n-card-header__main),
.rule-modal :deep(.n-card-header__main) {
  font-size: 16px;
  font-weight: 600;
}
.import-modal .import-hint {
  font-size: var(--text-small);
  color: var(--ink-soft);
  line-height: 1.6;
}
</style>
