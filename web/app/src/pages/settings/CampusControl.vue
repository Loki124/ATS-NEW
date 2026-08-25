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
            <n-button type="primary" class="gradient-btn" @click="openDimensionEditor()">+ 新增规则</n-button>
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

    <!-- ===================== 维度规则集编辑面（占比之和须=100%） ===================== -->
    <n-modal
      v-model:show="dimEditor.show"
      preset="card"
      title="维度规则集（占比之和须 = 100%）"
      :style="{ width: '820px', maxWidth: '94vw' }"
      :bordered="false"
      :segmented="{ content: true, footer: true }"
      class="dim-ruleset-modal"
    >
      <div class="dim-ctx">
        <div class="form-section">
          <div class="form-section-title">
            <span class="dot" />维度
          </div>
          <n-select
            v-model:value="dimEditor.dimensionId"
            :options="dimensionOptions"
            placeholder="选择维度"
            :disabled="dimEditor.lockContext"
            @update:value="onDimEditorDimChange"
          />
        </div>

        <div class="form-section">
          <div class="form-section-title form-section-title--scope">
            <span class="dot" />适用范围
            <n-switch
              v-model:value="dimEditor.isGlobal"
              size="small"
              class="scope-title-switch"
              @update:value="onDimEditorCtxChange"
            >
              <template #checked>全局</template>
              <template #unchecked>指定</template>
            </n-switch>
          </div>
          <div class="scope-row">
            <template v-if="!dimEditor.isGlobal">
              <div class="scope-field">
                <span class="scope-label">部门</span>
                <n-select v-model:value="dimEditor.bu" :options="deptOptions" placeholder="部门" @update:value="onDimEditorCtxChange" />
              </div>
              <div class="scope-field">
                <span class="scope-label">职务</span>
                <n-select v-model:value="dimEditor.position" :options="positionOptions" placeholder="职务(不限)" clearable @update:value="onDimEditorCtxChange" />
              </div>
              <div class="scope-field">
                <span class="scope-label">职级</span>
                <n-select v-model:value="dimEditor.level" :options="levelOptions" placeholder="职级(不限)" clearable @update:value="onDimEditorCtxChange" />
              </div>
            </template>
            <div class="scope-field">
              <span class="scope-label">年度</span>
              <n-input-number v-model:value="dimEditor.year" :min="2020" :max="2100" :disabled="dimEditor.lockContext" style="width: 110px" @update:value="onDimEditorCtxChange" />
            </div>
            <n-alert v-if="dimEditor.scopeDirty" type="warning" :show-icon="true" class="scope-relocate-hint">
              适用范围已修改，保存时将把该维度规则集从「{{ formatScopeLabel(dimEditor.originalScope) }}」<b>重定位</b>到「{{ formatScopeLabel(_currentEffectiveScope()) }}」，原适用范围下的规则将被删除。
            </n-alert>
          </div>
        </div>

        <div class="form-section" v-if="dimEditor.dimensionId">
          <div class="form-section-title">
            <span class="dot" />维度年度管控人数
            <span class="form-section-hint">（各指标人数加和须 = 此值）</span>
          </div>
          <div class="total-target-row">
            <n-input-number
              :value="dimEditor.totalTarget"
              :min="0" :step="1" size="small" style="width: 180px"
              :disabled="dimEditor.mode === 'view'"
              @update:value="(v: number | null) => setDimEditorTotalTarget(v)"
            />
            <span class="total-target-suffix">人</span>
            <span class="total-target-hint">修改此值将按指标占比自动重算各指标年度（手动调整过的除外）；需保证「人数加和 = 维度年度目标」。</span>
          </div>
          <div class="total-target-summary" v-if="dimEditor.mode === 'edit'">
            <span>当前人数加和：<strong>{{ dimEditorActiveAnnualSum }}</strong> 人</span>
            <span class="total-target-sep">·</span>
            <span>维度目标：<strong>{{ Math.round(dimEditor.totalTarget || 0) }}</strong> 人</span>
            <n-tag v-if="dimEditorTotalOk" type="success" :bordered="false" size="small" round class="total-target-tag">✓ 相等</n-tag>
            <n-tag v-else type="warning" :bordered="false" size="small" round class="total-target-tag">⚠ 差 {{ Math.round(dimEditor.totalTarget || 0) - dimEditorActiveAnnualSum }} 人</n-tag>
          </div>
        </div>
      </div>

      <div v-if="!dimEditor.dimensionId" class="empty-tip">请先选择维度</div>
      <div v-else-if="dimEditor.rows.length === 0" class="empty-tip">该维度下暂无指标，请先到「指标管理」新增</div>
      <div v-else class="dim-rows">
        <div class="dim-row" :class="{ 'row-deleted': row.pendingDelete, 'row-disabled': dimEditor.mode === 'view' }" v-for="row in dimEditor.rows" :key="row.indicatorId">
          <!-- 行 1：指标 + 状态徽标 + 占比% + 控制强度 + 年度（编辑/只读统一） + 删除/恢复 -->
          <div class="dim-row-head">
            <div class="dim-row-id">
              <span class="dim-ind-name">{{ row.indicatorName }}</span>
              <n-tag v-if="row.pendingDelete" type="error" :bordered="false" size="small" round>待删</n-tag>
              <n-tag v-else-if="row.targetPct == null" type="default" :bordered="false" size="small" round>未设目标</n-tag>
              <n-tag v-else type="success" :bordered="false" size="small" round>已设目标</n-tag>
            </div>
            <div class="dim-row-ctrl" v-if="dimEditor.mode === 'edit'">
              <div class="ctrl-group">
                <span class="ctrl-label">占比%</span>
                <n-input-number
                  :value="row.targetPct || 0"
                  :min="0" :max="100" :step="0.5" size="small" style="width: 92px"
                  @update:value="(v: number | null) => setDimRowTarget(row.indicatorId, v)"
                />
              </div>
              <div class="ctrl-group">
                <span class="ctrl-label">强度</span>
                <n-select
                  :value="row.strength" :options="strengthOptions" size="small" style="width: 100px"
                  @update:value="(v: string) => setDimRowStrength(row.indicatorId, v as Strength)"
                />
              </div>
              <div class="ctrl-group ctrl-group--annual">
                <span class="ctrl-label">年度</span>
                <div class="annual-ctrl-row">
                  <n-input-number
                    :value="row.annualTarget"
                    :min="0" size="small" style="width: 96px"
                    @update:value="(v: number | null) => setDimRowAnnual(row.indicatorId, v)"
                  />
                  <span class="annual-unit">人</span>
                  <!-- 手动调整 toggle：auto ↔ manual；auto 时点 = 「·锁定」进入手动，manual 时点 = 「↻ 重算」回到按占比自动值 -->
                  <n-button
                    size="tiny"
                    :type="row.manuallyEditedAnnual ? 'primary' : 'default'"
                    :ghost="!row.manuallyEditedAnnual"
                    class="annual-toggle-btn"
                    :class="{ 'annual-toggle-btn--locked': row.manuallyEditedAnnual }"
                    :title="row.manuallyEditedAnnual ? '点击重算为按占比自动值' : '点击锁定当前值为手动调整（脱离 totalTarget 联动）'"
                    @click="toggleAnnualMode(row.indicatorId)"
                  >
                    {{ row.manuallyEditedAnnual ? '↻ 重算' : '·锁定' }}
                  </n-button>
                </div>
              </div>
              <n-button text :type="row.pendingDelete ? 'primary' : 'error'" size="tiny" @click="toggleDimRowDelete(row.indicatorId)">
                {{ row.pendingDelete ? '恢复' : '删除' }}
              </n-button>
            </div>
            <div class="dim-row-view" v-else>
              <span class="view-pct">{{ row.targetPct == null ? '—' : row.targetPct.toFixed(1) + '%' }}</span>
              <span class="view-strength">{{ row.strength }}</span>
              <span class="view-annual">年度 <strong>{{ Math.round(row.annualTarget || 0) }}</strong> 人</span>
              <n-tag v-if="row.manuallyEditedAnnual" :bordered="false" size="tiny" type="info" round class="view-manual">手动调整</n-tag>
            </div>
          </div>

          <!-- 行 2：12 个月度目标（编辑态展开；删除待删也仍展示，便于用户看清数据避免误删） -->
          <div class="dim-row-monthly" v-if="dimEditor.mode === 'edit'">
            <div class="monthly-head">
              <span class="ctrl-label">12 个月度目标（单位：人）</span>
              <n-button
                size="tiny" ghost type="primary"
                class="monthly-redist-btn"
                title="12 月按「年度 ÷ 12」整除，余数从 1 月开始各 +1"
                @click="redistributeDimMonthly(row.indicatorId)"
              >均分年度目标</n-button>
            </div>
            <div class="monthly-grid">
              <div v-for="(_, i) in 12" :key="i" class="month-cell">
                <span class="month-label">{{ ALL_MONTHS[i] }}</span>
                <n-input-number
                  :value="row.monthlyTargets[i] || 0"
                  :min="0" :show-button="false" size="small"
                  @update:value="(v: number | null) => setDimRowMonthly(row.indicatorId, i, v)"
                />
              </div>
            </div>
            <div class="monthly-foot">
              <span class="allocated">已分配 <strong>{{ dimRowMonthlySum(row) }}</strong> 人</span>
              <n-tag v-if="dimRowMonthlyOk(row)" type="success" :bordered="false" size="small" round>✓ 等于年度目标</n-tag>
              <n-tag v-else type="warning" :bordered="false" size="small" round>⚠ 不等于年度目标 {{ Math.round(row.annualTarget || 0) }} 人</n-tag>
            </div>
          </div>

          <!-- 查看态下也展示月度数据（只读），便于跨维度规则集观察 -->
          <div class="dim-row-monthly dim-row-monthly--readonly" v-else>
            <div class="monthly-head">
              <span class="ctrl-label">12 个月度目标（单位：人）</span>
            </div>
            <div class="monthly-grid">
              <div v-for="(_, i) in 12" :key="i" class="month-cell">
                <span class="month-label">{{ ALL_MONTHS[i] }}</span>
                <span class="month-val">{{ row.monthlyTargets[i] || 0 }}</span>
              </div>
            </div>
            <div class="monthly-foot">
              <span class="allocated">已分配 <strong>{{ dimRowMonthlySum(row) }}</strong> 人</span>
              <n-tag v-if="dimRowMonthlyOk(row)" type="success" :bordered="false" size="small" round>✓ 等于年度目标</n-tag>
              <n-tag v-else type="warning" :bordered="false" size="small" round>⚠ 不等于年度目标 {{ Math.round(row.annualTarget || 0) }} 人</n-tag>
            </div>
          </div>
        </div>

        <div v-if="dimEditor.mode === 'edit'" class="sum-callout" :class="{ ok: dimEditorSumOk && dimEditorTotalOk, warn: !dimEditorSumOk || !dimEditorTotalOk }">
          <div class="sum-left">
            <span class="sum-label">占比之和</span>
            <span class="sum-value">{{ dimEditorSumPct.toFixed(1) }}%</span>
            <span class="sum-sep">·</span>
            <span class="sum-label">人数加和</span>
            <span class="sum-value">{{ dimEditorActiveAnnualSum }} / {{ Math.round(dimEditor.totalTarget || 0) }} 人</span>
          </div>
          <div class="sum-right">
            <n-tag v-if="dimEditorSumOk && dimEditorTotalOk" type="success" :bordered="false" size="small" round>✓ = 100% · 人数对齐</n-tag>
            <template v-else>
              <n-tag v-if="!dimEditorSumOk" type="warning" :bordered="false" size="small" round>⚠ 占比 ≠ 100%</n-tag>
              <n-tag v-if="!dimEditorTotalOk" type="warning" :bordered="false" size="small" round>⚠ 人数加和不齐</n-tag>
            </template>
          </div>
        </div>

        <n-alert v-if="dimEditor.mode === 'edit' && dimEditorHasPendingDelete" type="warning" :show-icon="true" class="dim-del-alert">
          已标记删除 {{ dimEditorPendingDeleteCount }} 个指标，剩余指标占比之和须重平衡至 100% 后方可保存。
        </n-alert>
      </div>

      <template #footer>
        <div class="drawer-footer">
          <n-button @click="closeDimEditor">取消</n-button>
          <template v-if="dimEditor.mode === 'view'">
            <n-button type="primary" class="gradient-btn" @click="enterDimEdit">编辑</n-button>
          </template>
          <template v-else>
            <n-button type="primary" class="gradient-btn" :loading="loading.saveDimRuleSet" :disabled="!dimEditorSumOk || !dimEditorTotalOk" @click="saveDimRuleSet">保存</n-button>
          </template>
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
  listRules, saveDimensionRuleSet,
  getRatio, getPlan, validateDraft,
  listPersons, upsertPerson, deletePerson,
  exportRules, downloadRuleTemplate, importRules, triggerDownload,
  DEPTS, SCHOOLS, MAJORS, SEXES, ALL_MONTHS, STRENGTH, STATUS, POSITIONS, LEVELS,
  type ControlDimension, type ControlIndicator, type ControlRule,
  type Person, type RatioRow, type RatioResult, type PlanRow, type PlanResult,
  type ValidationResult, type Strength, type DimRuleSetItem,
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
  ratio: false, plan: false, rules: false, saveDimRuleSet: false,
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
      h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openDimensionEditor(r) }, { default: () => '编辑' }),
      h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => openDimensionEditor(r, { preDelete: r.indicator }) }, { default: () => '删除' }),
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

// v2.6 录入校验只看人数。占比/占比状态/强度三列移除（占比仅用于规则配置时计算实际人数，
// 不参与「是否可以录入」判定；strength 只对占比硬/软约束有意义，人数校验无此概念）。
// 实时看板（mergedColumns）仍使用 strengthType/ratioStatusType/pct，此处不删工具函数。
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
const dimEditorSumOk = computed(() => Math.abs(dimEditorSumPct.value - 100) < 0.05)
const dimEditorHasPendingDelete = computed(() => dimEditor.rows.some((r) => r.pendingDelete))
const dimEditorPendingDeleteCount = computed(() => dimEditor.rows.filter((r) => r.pendingDelete).length)
// 仅统计未删除行的年度人数加和（与 totalTarget 比较以判断「人数加和 = 维度年度目标」）。
const dimEditorActiveAnnualSum = computed(() =>
  dimEditor.rows.reduce((s, r) => s + (r.pendingDelete ? 0 : Math.round(r.annualTarget || 0)), 0),
)
// 人数加和 = totalTarget（口径：用户截图需求）。差 0 等同整数加和精确相等；不做四舍五入容差。
const dimEditorTotalOk = computed(() => dimEditorActiveAnnualSum.value === Math.round(dimEditor.totalTarget || 0))

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
        rules: rulesPayload,
        ...(relocate && dimEditor.originalScope ? { original: dimEditor.originalScope } : {}),
      })
      message.success(`已保存维度规则集（${res.data.saved} 条）`)
      dimEditor.show = false
      dimEditor.mode = 'view'
      await Promise.all([loadRules(), loadRatio(), loadPlan()])
    } catch (e) {
      message.error(extractApiError(e, '保存失败'))
    } finally {
      loading.saveDimRuleSet = false
    }
  }
  if (relocate) {
    dialog.warning({
      title: '重定位适用范围',
      content: `将把该维度规则集从「${formatScopeLabel(dimEditor.originalScope)}」迁移到「${formatScopeLabel(_currentEffectiveScope())}」。\n原「${formatScopeLabel(dimEditor.originalScope)}」下的规则将被删除，是否继续？`,
      positiveText: '迁移',
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
/* 仅保留「布局链」相关规则，视觉（玻璃/极光/标题渐变/KPI/表格/弹窗）统一复用全局 glass.css
   —— 单一设计系统，校招管控不再持有私有视觉定义。 */

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
