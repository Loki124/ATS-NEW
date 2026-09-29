<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.CampusControl.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.CampusControl.s2') }}</p>
      </div>
    </div>

    <div class="glass-panel">
      <n-tabs v-model:value="activeTab" type="line" class="cc-tabs" @update:value="onTabChange">
        <!-- ===================== 实时看板（含人数规划） ===================== -->
        <n-tab-pane name="ratio" :tab="t('pages.settings.CampusControl.s7')">
          <div class="kpi-row">
            <div class="kpi-card"><span class="kpi-label">{{ t('pages.settings.CampusControl.s3') }}</span><span class="kpi-value">{{ ratioData.total }}</span></div>
            <div class="kpi-card"><span class="kpi-label">{{ t('pages.settings.CampusControl.s4') }}</span><span class="kpi-value">{{ ratioData.rows.length }}</span></div>
            <div class="kpi-card danger"><span class="kpi-label">{{ t('pages.settings.CampusControl.s5') }}</span><span class="kpi-value">{{ ratioKpi.hard }}</span></div>
            <div class="kpi-card warn"><span class="kpi-label">{{ t('pages.settings.CampusControl.s6') }}</span><span class="kpi-value">{{ ratioKpi.soft }}</span></div>
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
              <template #empty><n-empty :description="t('pages.settings.CampusControl.s188')" /></template>
            </n-data-table>
          </div>

          <n-alert type="info" :show-icon="true" style="margin-top: var(--space-4); flex-shrink: 0">
            {{ t('pages.settings.CampusControl.s189') }}<strong>{{ t('pages.settings.CampusControl.s8') }}</strong>{{ t('pages.settings.CampusControl.s190') }}
            {{ t('pages.settings.CampusControl.s9') }}
          </n-alert>
        </n-tab-pane>

        <!-- ===================== 规则配置（扁平列表：每条规则一行） ===================== -->
        <n-tab-pane name="rules" :tab="t('pages.settings.CampusControl.s10')">
          <n-alert
            v-if="mixedScopeGroups.size > 0"
            type="warning"
            :show-icon="true"
            class="scope-mutex-banner"
          >
            {{ t('pages.settings.CampusControl.s191') }}<b>{{ mixedScopeGroups.size }}</b>{{ t('pages.settings.CampusControl.s269') }}<b>{{ t('pages.settings.CampusControl.s11') }}</b>{{ t('pages.settings.CampusControl.s192') }}
          </n-alert>

          <div class="toolbar">
            <n-input
              v-model:value="ruleFilterKeyword"
              :placeholder="t('pages.settings.CampusControl.s12')"
              clearable
              class="rule-filter-search"
            />
            <n-select
              v-model:value="ruleFilterStatus"
              :options="ruleStatusOptions"
              :placeholder="t('pages.settings.CampusControl.s13')"
              class="rule-filter-select"
            />
            <n-select
              v-model:value="ruleFilterDimension"
              :options="dimensionOptions"
              :placeholder="t('pages.settings.CampusControl.s14')"
              clearable
              class="rule-filter-select"
            />
            <n-select
              v-model:value="ruleFilterIndicator"
              :options="ruleIndicatorOptions"
              :placeholder="t('pages.settings.CampusControl.s15')"
              clearable
              filterable
              class="rule-filter-select"
            />
            <n-select
              v-model:value="ruleFilterScope"
              :options="ruleScopeOptions"
              :placeholder="t('pages.settings.CampusControl.s16')"
              clearable
              class="rule-filter-select"
            />
            <div class="spacer"></div>
            <n-button @click="onExportRules">{{ t('pages.settings.CampusControl.s17') }}</n-button>
            <n-button @click="importDrawer.show = true">{{ t('pages.settings.CampusControl.s18') }}</n-button>
            <n-button type="primary" class="gradient-btn" @click="openRuleDrawer(null)">{{ t('pages.settings.CampusControl.s19') }}</n-button>
          </div>

          <div class="table-wrap">
            <n-data-table
              :columns="ruleColumns"
              :data="filteredRules"
              :loading="loading.rules"
              :row-key="(r: any) => r.id"
              :pagination="rulePagination"
              flex-height
              :row-props="ruleRowProps"
            >
              <template #empty>
                <n-empty :description="rules.length === 0 ? t('pages.settings.CampusControl.s193') : t('pages.settings.CampusControl.s194')" />
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
        <n-tab-pane name="indicators" :tab="t('pages.settings.CampusControl.s20')">
          <div class="toolbar">
            <n-select v-model:value="indicatorDimFilter" :options="indicatorDimOptions" :placeholder="t('pages.settings.CampusControl.s21')" clearable style="width: 180px" />
            <n-button @click="openDimDrawer()">{{ t('pages.settings.CampusControl.s22') }}</n-button>
            <div class="spacer"></div>
            <n-dropdown :options="indicatorExportOptions" @select="onExportIndicatorsSelect">
              <n-button>{{ t('pages.settings.CampusControl.s23') }}</n-button>
            </n-dropdown>
            <n-button @click="onDownloadIndicatorTemplate">{{ t('pages.settings.CampusControl.s24') }}</n-button>
            <n-button @click="indicatorImportDrawer.show = true">{{ t('pages.settings.CampusControl.s25') }}</n-button>
            <n-button type="primary" class="gradient-btn" @click="openIndicatorModal()">{{ t('pages.settings.CampusControl.s26') }}</n-button>
          </div>
          <div class="table-wrap">
            <n-data-table
              :columns="indicatorColumns"
              :data="filteredIndicators"
              :loading="loading.indicators"
              :row-key="(r: any) => r.id"
              :pagination="indicatorPagination"
              flex-height
            >
              <template #empty><n-empty :description="t('pages.settings.CampusControl.s195')" /></template>
            </n-data-table>
          </div>
        </n-tab-pane>

        <!-- ===================== 录入校验 ===================== -->
        <n-tab-pane name="validate" :tab="t('pages.settings.CampusControl.s27')">
          <n-grid :cols="4" :x-gap="16" :y-gap="12" item-responsive responsive="screen">
            <n-gi span="4 m:1"><n-form-item :label="t('pages.settings.CampusControl.s28')" label-placement="top"><n-input v-model:value="draft.code" :placeholder="t('pages.settings.CampusControl.s29')" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item :label="t('pages.settings.CampusControl.s30')" label-placement="top"><n-input v-model:value="draft.name" :placeholder="t('pages.settings.CampusControl.s31')" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item :label="t('pages.settings.CampusControl.s32')" label-placement="top"><n-select v-model:value="draft.bu" :options="deptOptions" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item :label="t('pages.settings.CampusControl.s33')" label-placement="top"><n-select v-model:value="draft.position" :options="positionOptions" clearable :placeholder="t('pages.settings.CampusControl.s34')" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item :label="t('pages.settings.CampusControl.s35')" label-placement="top"><n-select v-model:value="draft.level" :options="levelOptions" clearable :placeholder="t('pages.settings.CampusControl.s36')" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item :label="t('pages.settings.CampusControl.s37')" label-placement="top"><n-select v-model:value="draft.school" :options="schoolOptions" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item :label="t('pages.settings.CampusControl.s38')" label-placement="top"><n-select v-model:value="draft.sex" :options="sexOptions" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item :label="t('pages.settings.CampusControl.s39')" label-placement="top"><n-select v-model:value="draft.major" :options="majorOptions" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item :label="t('pages.settings.CampusControl.s40')" label-placement="top"><n-select v-model:value="draft.month" :options="monthOptions" /></n-form-item></n-gi>
            <n-gi span="4 m:1"><n-form-item :label="t('pages.settings.CampusControl.s41')" label-placement="top"><n-select v-model:value="draft.status" :options="statusOptions" /></n-form-item></n-gi>
          </n-grid>
          <div class="toolbar">
            <n-button type="primary" class="gradient-btn" :loading="loading.validate" @click="runValidate">{{ t('pages.settings.CampusControl.s42') }}</n-button>
            <n-button :disabled="!canConfirmEntry" @click="confirmEntry">{{ t('pages.settings.CampusControl.s43') }}</n-button>
          </div>

          <div v-if="validation" class="validate-result">
            <n-tag :type="verdictType(validation)" size="large" :bordered="false" style="flex-shrink: 0">
              <template #icon>
                <n-icon :component="VERDICT_ICON[validation.verdictLevel]" aria-hidden="true" />
              </template>
              {{ VERDICT_LABEL[validation.verdictLevel] }}
            </n-tag>
            <p v-if="validation.verdictLevel === 'block'" class="block-hint" style="flex-shrink: 0">
              {{ t('pages.settings.CampusControl.s44') }}
            </p>
            <div class="table-wrap" style="margin-top: 12px">
              <n-data-table
                :columns="checkColumns"
                :data="validation.checks"
                :row-key="(r: any) => [r.dimension, r.indicator, r.bu, r.position, r.level].join('|')"
                :pagination="false"
                flex-height
              >
                <template #empty><n-empty :description="t('pages.settings.CampusControl.s196')" /></template>
              </n-data-table>
            </div>
          </div>
        </n-tab-pane>

        <!-- ===================== 人员数据 ===================== -->
        <n-tab-pane name="persons" :tab="t('pages.settings.CampusControl.s45')">
          <div class="toolbar toolbar--filters">
            <!-- 搜索框最左：模糊匹配候选人编号/姓名 -->
            <n-input
              v-model:value="personFilterSearch"
              :placeholder="t('pages.settings.CampusControl.s46')"
              clearable
              class="rule-filter-search"
              @keyup.enter="loadPersons()"
            />
            <!-- 状态筛：搜索框右侧第一个（仅 全部/在职/在途Offer/在途待入职） -->
            <n-select
              v-model:value="personFilterStatus"
              :options="personStatusOptions"
              class="rule-filter-select"
            />
            <!-- 8 个精确筛：依次部门/职务/职级/性别/院校/专业/年度/月份 -->
            <n-select
              v-model:value="personFilterBu"
              :options="deptOptions"
              :placeholder="t('pages.settings.CampusControl.s47')"
              clearable
              class="rule-filter-select"
            />
            <n-select
              v-model:value="personFilterPosition"
              :options="positionOptions"
              :placeholder="t('pages.settings.CampusControl.s48')"
              clearable
              class="rule-filter-select"
            />
            <n-select
              v-model:value="personFilterLevel"
              :options="levelOptions"
              :placeholder="t('pages.settings.CampusControl.s49')"
              clearable
              class="rule-filter-select"
            />
            <n-select
              v-model:value="personFilterSex"
              :options="sexOptions"
              :placeholder="t('pages.settings.CampusControl.s50')"
              clearable
              class="rule-filter-select"
            />
            <n-select
              v-model:value="personFilterSchool"
              :options="schoolOptions"
              :placeholder="t('pages.settings.CampusControl.s51')"
              clearable
              class="rule-filter-select"
            />
            <n-select
              v-model:value="personFilterMajor"
              :options="majorOptions"
              :placeholder="t('pages.settings.CampusControl.s52')"
              clearable
              class="rule-filter-select"
            />
            <n-select
              v-model:value="personFilterYear"
              :options="yearOptions"
              :placeholder="t('pages.settings.CampusControl.s53')"
              clearable
              class="rule-filter-select"
            />
            <n-select
              v-model:value="personFilterMonth"
              :options="monthOptions"
              :placeholder="t('pages.settings.CampusControl.s54')"
              clearable
              class="rule-filter-select"
            />
            <div class="spacer"></div>
          </div>
          <div class="table-wrap">
            <n-data-table
              :columns="personColumns"
              :data="persons"
              :loading="loading.persons"
              :row-key="(r: any) => r.id"
              :pagination="personPagination"
              flex-height
            >
              <template #empty><n-empty :description="t('pages.settings.CampusControl.s197')" /></template>
            </n-data-table>
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>


    <!-- ===================== 导入规则弹窗（页面居中） ===================== -->
    <n-modal
      v-model:show="importDrawer.show"
      preset="card"
      :title="t('pages.settings.CampusControl.s55')"
      :style="{ width: '600px', maxWidth: '94vw' }"
      :bordered="false"
      :segmented="{ content: true, footer: true }"
      class="import-modal"
    >
      <n-space vertical :size="14">
        <n-upload
          v-model:file-list="importDrawer.fileList"
          accept=".xlsx,.xlsm"
          :max="1"
          :custom-request="handleImportUpload"
          @remove="onImportFileRemove"
        >
          <n-button>{{ t('pages.settings.CampusControl.s56') }}</n-button>
        </n-upload>
        <n-space align="center" :wrap="false">
          <n-button size="small" quaternary type="primary" @click="onDownloadTemplate">{{ t('pages.settings.CampusControl.s57') }}</n-button>
          <span class="import-hint" style="margin: 0">
            {{ t('pages.settings.CampusControl.s58') }}
          </span>
        </n-space>
        <div v-if="importDrawer.result" class="import-result">
          <n-alert
            v-if="importDrawer.result.success"
            type="success"
            :show-icon="true"
          >
            {{ t('pages.settings.CampusControl.s198', { groups: importDrawer.result.data.groups, rules: importDrawer.result.data.savedRules }) }}
          </n-alert>
          <n-alert v-else type="error" :show-icon="true">
            {{ t('pages.settings.CampusControl.s199', { groups: importDrawer.result.data.groups, rules: importDrawer.result.data.savedRules }) }}
          </n-alert>
          <div v-if="importDrawer.result && importDrawer.result.data.errors.length" class="import-error-actions">
            <n-button v-if="importDrawer.result.data.errorFile" size="small" type="error" @click="downloadImportErrorExcel">{{ t('pages.settings.CampusControl.s59') }}</n-button>
            <n-button v-else size="small" @click="downloadImportErrorReport">{{ t('pages.settings.CampusControl.s60') }}</n-button>
          </div>
          <ul v-if="importDrawer.result && importDrawer.result.data.errors.length" class="import-errors">
            <li v-for="(e, i) in importDrawer.result.data.errors" :key="i">{{ e }}</li>
          </ul>
        </div>
      </n-space>
      <template #footer>
        <div class="drawer-footer">
          <n-button @click="importDrawer.show = false">{{ t('pages.settings.CampusControl.s61') }}</n-button>
        </div>
      </template>
    </n-modal>

    <!-- ===================== 导入指标弹窗（页面居中） ===================== -->
    <n-modal
      v-model:show="indicatorImportDrawer.show"
      preset="card"
      :title="t('pages.settings.CampusControl.s62')"
      :style="{ width: '600px', maxWidth: '94vw' }"
      :bordered="false"
      :segmented="{ content: true, footer: true }"
      class="import-modal"
    >
      <n-space vertical :size="14">
        <n-radio-group v-model:value="indicatorImportDrawer.mode" name="indicator-import-mode">
          <n-space>
            <n-radio value="skip">{{ t('pages.settings.CampusControl.s63') }}</n-radio>
            <n-radio value="update">{{ t('pages.settings.CampusControl.s64') }}</n-radio>
            <n-radio value="error">{{ t('pages.settings.CampusControl.s65') }}</n-radio>
          </n-space>
        </n-radio-group>
        <n-upload
          v-model:file-list="indicatorImportDrawer.fileList"
          accept=".xlsx,.xlsm,.csv"
          :max="1"
          :custom-request="handleIndicatorImportUpload"
          @remove="onIndicatorImportFileRemove"
        >
          <n-button>{{ t('pages.settings.CampusControl.s66') }}</n-button>
        </n-upload>
        <n-space align="center" :wrap="false">
          <n-button size="small" quaternary type="primary" @click="onDownloadIndicatorTemplate">{{ t('pages.settings.CampusControl.s67') }}</n-button>
          <span class="import-hint" style="margin: 0">
            {{ t('pages.settings.CampusControl.s68') }}
          </span>
        </n-space>
        <div v-if="indicatorImportDrawer.result" class="import-result">
          <n-alert v-if="indicatorImportDrawer.result.success" type="success" :show-icon="true">
            {{ t('pages.settings.CampusControl.s200', { created: indicatorImportDrawer.result.data.created, updated: indicatorImportDrawer.result.data.updated, skipped: indicatorImportDrawer.result.data.skipped }) }}
          </n-alert>
          <n-alert v-else type="error" :show-icon="true">
            {{ t('pages.settings.CampusControl.s201', { skipped: indicatorImportDrawer.result.data.skipped, created: indicatorImportDrawer.result.data.created }) }}
          </n-alert>
          <div v-if="indicatorImportDrawer.result && indicatorImportDrawer.result.data.errors.length" class="import-error-actions">
            <n-button v-if="indicatorImportDrawer.result.data.errorFile" size="small" type="error" @click="downloadIndicatorImportErrorExcel">{{ t('pages.settings.CampusControl.s69') }}</n-button>
          </div>
          <ul v-if="indicatorImportDrawer.result && indicatorImportDrawer.result.data.errors.length" class="import-errors">
            <li v-for="(e, i) in indicatorImportDrawer.result.data.errors" :key="i">{{ e }}</li>
          </ul>
        </div>
      </n-space>
      <template #footer>
        <div class="drawer-footer">
          <n-button @click="indicatorImportDrawer.show = false">{{ t('pages.settings.CampusControl.s70') }}</n-button>
        </div>
      </template>
    </n-modal>

    <!-- ===================== 维度管理弹窗（页面居中） ===================== -->
    <n-modal
      v-model:show="dimDrawer.show"
      preset="card"
      :title="t('pages.settings.CampusControl.s71')"
      :style="{ width: '560px', maxWidth: '94vw' }"
      :bordered="false"
      :segmented="{ content: true, footer: true }"
      class="dim-modal"
    >
      <n-space vertical :size="12">
        <div class="toolbar" style="margin-bottom: 0">
          <div class="spacer"></div>
          <n-button type="primary" class="gradient-btn" @click="openDimModal()">{{ t('pages.settings.CampusControl.s72') }}</n-button>
        </div>
        <n-data-table
          :columns="dimColumns"
          :data="dimensions"
          :loading="loading.dimensions"
          :row-key="(r: any) => r.id"
          :pagination="false"
          size="small"
        >
          <template #empty><n-empty :description="t('pages.settings.CampusControl.s202')" /></template>
        </n-data-table>
      </n-space>
    </n-modal>

    <!-- ===================== 维度表单弹窗 ===================== -->
    <n-modal v-model:show="dimModal.show" :title="dimModal.editingId ? t('pages.settings.CampusControl.s203') : t('pages.settings.CampusControl.s204')" preset="card" style="width: 420px; max-width: 90vw">
      <n-form label-placement="top">
        <n-form-item :label="t('pages.settings.CampusControl.s73')" required><n-input v-model:value="dimModal.name" :placeholder="t('pages.settings.CampusControl.s74')" /></n-form-item>
        <n-form-item :label="t('pages.settings.CampusControl.s75')"><n-input v-model:value="dimModal.code" :placeholder="t('pages.settings.CampusControl.s76')" /></n-form-item>
      </n-form>
      <template #footer>
        <div class="drawer-footer">
          <n-button @click="dimModal.show = false">{{ t('pages.settings.CampusControl.s77') }}</n-button>
          <n-button type="primary" class="gradient-btn" :loading="loading.dimensions" @click="saveDim">{{ t('pages.settings.CampusControl.s78') }}</n-button>
        </div>
      </template>
    </n-modal>

    <!-- ===================== 指标表单弹窗 ===================== -->
    <n-modal v-model:show="indicatorModal.show" :title="indicatorModal.editingId ? t('pages.settings.CampusControl.s205') : t('pages.settings.CampusControl.s206')" preset="card" style="width: 420px; max-width: 90vw">
      <n-form label-placement="top">
        <n-form-item :label="t('pages.settings.CampusControl.s79')" required><n-select v-model:value="indicatorModal.dimensionId" :options="dimensionOptions" :disabled="!!indicatorModal.editingId" /></n-form-item>
        <n-form-item :label="t('pages.settings.CampusControl.s80')" required><n-input v-model:value="indicatorModal.name" :placeholder="t('pages.settings.CampusControl.s81')" /></n-form-item>
      </n-form>
      <template #footer>
        <div class="drawer-footer">
          <n-button @click="indicatorModal.show = false">{{ t('pages.settings.CampusControl.s82') }}</n-button>
          <n-button type="primary" class="gradient-btn" :loading="loading.indicators" @click="saveIndicator">{{ t('pages.settings.CampusControl.s83') }}</n-button>
        </div>
      </template>
    </n-modal>

    <!-- ===================== 人员表单弹窗（仅编辑态，列表「+ 新增人员」按钮已按产品决策移除） ===================== -->
    <n-modal v-model:show="personModal.show" :title="t('pages.settings.CampusControl.s84')" preset="card" style="width: 560px; max-width: 90vw">
      <n-form label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-gi><n-form-item :label="t('pages.settings.CampusControl.s85')"><n-input v-model:value="personModal.code" :placeholder="t('pages.settings.CampusControl.s86')" /></n-form-item></n-gi>
          <n-gi><n-form-item :label="t('pages.settings.CampusControl.s87')"><n-input v-model:value="personModal.name" :placeholder="t('pages.settings.CampusControl.s88')" /></n-form-item></n-gi>
          <n-gi><n-form-item :label="t('pages.settings.CampusControl.s89')"><n-select v-model:value="personModal.bu" :options="deptOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item :label="t('pages.settings.CampusControl.s90')"><n-select v-model:value="personModal.school" :options="schoolOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item :label="t('pages.settings.CampusControl.s91')"><n-select v-model:value="personModal.sex" :options="sexOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item :label="t('pages.settings.CampusControl.s92')"><n-select v-model:value="personModal.major" :options="majorOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item :label="t('pages.settings.CampusControl.s93')"><n-select v-model:value="personModal.month" :options="monthOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item :label="t('pages.settings.CampusControl.s94')"><n-select v-model:value="personModal.status" :options="statusOptions" /></n-form-item></n-gi>
          <n-gi><n-form-item :label="t('pages.settings.CampusControl.s95')"><n-date-picker v-model:formatted-value="personModal.expectedEntryDate" value-format="yyyy-MM-dd" type="date" clearable style="width:100%" /></n-form-item></n-gi>
          <n-gi><n-form-item :label="t('pages.settings.CampusControl.s96')"><n-date-picker v-model:formatted-value="personModal.actualEntryDate" value-format="yyyy-MM-dd" type="date" clearable style="width:100%" /></n-form-item></n-gi>
          <n-gi><n-form-item :label="t('pages.settings.CampusControl.s97')"><n-select v-model:value="personModal.position" :options="positionOptions" clearable :placeholder="t('pages.settings.CampusControl.s98')" /></n-form-item></n-gi>
          <n-gi><n-form-item :label="t('pages.settings.CampusControl.s99')"><n-select v-model:value="personModal.level" :options="levelOptions" clearable :placeholder="t('pages.settings.CampusControl.s100')" /></n-form-item></n-gi>
          <n-gi><n-form-item :label="t('pages.settings.CampusControl.s101')"><n-switch v-model:value="personModal.counted" /></n-form-item></n-gi>
        </n-grid>
      </n-form>
      <template #footer>
        <div class="drawer-footer">
          <n-button @click="personModal.show = false">{{ t('pages.settings.CampusControl.s102') }}</n-button>
          <n-button type="primary" class="gradient-btn" :loading="loading.persons" @click="savePerson">{{ t('pages.settings.CampusControl.s103') }}</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, computed, h, onMounted, watch } from 'vue'
import {
  NTag, NButton, NSwitch, NCheckbox, NDivider, NSpace,
  NInputNumber, NSelect, NInput, NEmpty, NAlert, NDatePicker, NTooltip, NIcon,
  useMessage, useDialog, type DataTableColumns,
} from 'naive-ui'
import { extractApiError } from '../../api/dynamic-field'
import {
  listDimensions, createDimension, updateDimension, deleteDimension,
  listIndicators, createIndicator, updateIndicator, deleteIndicator,
  listRules, saveDimensionRuleSet,
  getRatio, validateDraft,
  listPersons, upsertPerson, deletePerson, restoreDimension, restoreIndicator, restorePerson,
  exportRules, downloadRuleTemplate, importRules, triggerDownload,
  exportIndicators, downloadIndicatorTemplate, importIndicators,
  DEPTS, SCHOOLS, MAJORS, SEXES, ALL_MONTHS, STRENGTH, STATUS, POSITIONS, LEVELS,
  type ControlDimension, type ControlIndicator, type ControlRule,
  type Person, type RatioRow, type RatioResult,
  type ValidationResult, type Strength, type DimRuleSetItem,
  type RuleImportResult, type IndicatorImportResult,
} from '../../api/campusControl'
import { CloseCircleOutline as XCircle, WarningOutline as AlertTriangle, CheckmarkCircleOutline as CheckCircle2 } from '@vicons/ionicons5'
import RuleConfigDrawer from '../../components/RuleConfigDrawer.vue'
import { useRuleActions } from '../../composables/useRuleActions'
import { useUndo } from '../../composables/useUndo'
const { t } = useI18n()

const message = useMessage()
const dialog = useDialog()
const { undoable } = useUndo()

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
const countStatusType = (s: string) => (s === '本月达标' ? 'error' : s === '缺口未达成' ? 'warning' : 'default')
const strengthType = (s: string) => (s === '硬约束' ? 'error' : s === '软约束' ? 'warning' : 'default')
const VERDICT_ICON: Record<string, any> = { block: XCircle, warn: AlertTriangle, pass: CheckCircle2 }
const VERDICT_LABEL: Record<string, string> = { block: t('pages.settings.CampusControl.s207'), warn: t('pages.settings.CampusControl.s208'), pass: t('pages.settings.CampusControl.s209') }
const verdictType = (v: ValidationResult) => (v.verdictLevel === 'block' ? 'error' : v.verdictLevel === 'warn' ? 'warning' : 'success')

const scopeText = (bu: string, position: string, level: string) => {
  if (!bu && !position && !level) return t('pages.settings.CampusControl.s210')
  const parts = [bu, position || t('pages.settings.CampusControl.s211'), level || t('pages.settings.CampusControl.s212')]
  return parts.filter(Boolean).join(' · ')
}

/* ============================ 全局状态 ============================ */
const activeTab = ref('ratio')
const loading = reactive({
  ratio: false, plan: false, rules: false,
  dimensions: false, indicators: false, persons: false, validate: false,
  import: false,
})
const dimensions = ref<ControlDimension[]>([])
const indicators = ref<ControlIndicator[]>([])
const rules = ref<ControlRule[]>([])
const persons = ref<Person[]>([])

// 人员数据：状态筛选（仅 4 项：全部/在职/在途Offer/在途待入职）。
// 「候选池」「占编」已从列表筛选项移除（候选池不占编，默认展示全部人员）。
const personFilterStatus = ref<'all' | '在职' | '在途Offer' | '在途待入职'>('all')
const personStatusOptions = [
  { label: t('pages.settings.CampusControl.s104'), value: 'all' as const },
  { label: t('pages.settings.CampusControl.s105'), value: '在职' as const },
  { label: t('pages.settings.CampusControl.s106'), value: '在途Offer' as const },
  { label: t('pages.settings.CampusControl.s107'), value: '在途待入职' as const },
]

// 人员数据：8 项精确筛 + 1 项模糊搜（候选人编号/姓名 icontains）。
// 年度 = 按 expected_entry_date / actual_entry_date 的年份（后端 OR 逻辑）。
const personFilterBu = ref<string | null>(null)
const personFilterPosition = ref<string | null>(null)
const personFilterLevel = ref<string | null>(null)
const personFilterSex = ref<string | null>(null)
const personFilterSchool = ref<string | null>(null)
const personFilterMajor = ref<string | null>(null)
const personFilterYear = ref<number | null>(null)
const personFilterMonth = ref<string | null>(null)
const personFilterSearch = ref('')

// 年度下拉（默认给一个常识区间；如需精确可改成后端 distinct(year)）
const currentYear = new Date().getFullYear()
const yearOptions = [
  { label: String(currentYear - 2), value: currentYear - 2 },
  { label: String(currentYear - 1), value: currentYear - 1 },
  { label: String(currentYear), value: currentYear },
  { label: String(currentYear + 1), value: currentYear + 1 },
]

/* ============================ 表格分页（列表页） ============================
 * 三个列表页（规则配置/指标管理/人员数据）启用 n-data-table 内置分页：
 *  - 默认 20 条/页，可切换 10/20/50/100
 *  - showQuickJumper 支持输入页码跳页
 *  - prefix 显示「共 N 条」（Naive UI Pagination 的 RenderPrefix 入参为 { itemCount, page, pageSize, pageCount, startIndex, endIndex }，不是 total）
 * 看板/录入校验结果 不分页（语义不同：按维/规则集聚合，单次结果通常 < 50 行）
 */
// T143 修复 n-data-table 内置分页器切换 pageSize 不生效：
// Naive UI 把「含 pageSize 的 reactive pagination」当受控（controlledPageSizeRef = pagination.pageSize），
// 内置分页器的 onUpdate:pageSize 不会回写外部对象，导致 pageSize 永远卡在初始值。
// 修法：移除 reactive 里的 pageSize 让 Naive UI 用内部 uncontrolledPageSizeRef 管理；
//       defaultPageSize 仅作为 uncontrolled 初始值（不受控，可被分页器正常更新）。
const rulePagination = reactive({
  defaultPageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  showQuickJumper: true,
  prefix: ({ itemCount }: { itemCount: number | undefined }) => t('pages.settings.CampusControl.s213', { n: itemCount ?? 0 }),
})
const indicatorPagination = reactive({
  defaultPageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  showQuickJumper: true,
  prefix: ({ itemCount }: { itemCount: number | undefined }) => t('pages.settings.CampusControl.s213', { n: itemCount ?? 0 }),
})
const personPagination = reactive({
  defaultPageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  showQuickJumper: true,
  prefix: ({ itemCount }: { itemCount: number | undefined }) => t('pages.settings.CampusControl.s213', { n: itemCount ?? 0 }),
})

const dimensionOptions = computed(() => dimensions.value.map((d) => ({ label: d.name, value: d.id })))

/* ============================ 规则筛选（左侧工具条） ============================
 * 5 维过滤：关键词（编号/维度/指标/部门）+ 状态 + 维度 + 指标 + 适用范围
 * 适用范围用部门区分（产品设计：职务/职级多留作详情，不下放到筛选）
 */
const ruleFilterKeyword = ref('')
const ruleFilterStatus = ref<'all' | 'active' | 'inactive'>('all')
const ruleFilterDimension = ref<string | null>(null)
const ruleFilterIndicator = ref<string | null>(null)
const ruleFilterScope = ref<string>('') // ''=全部; '<GLOBAL>':全局; 'bu':部门
const ruleStatusOptions = [
  { label: t('pages.settings.CampusControl.s108'), value: 'all' as const },
  { label: t('pages.settings.CampusControl.s109'), value: 'active' as const },
  { label: t('pages.settings.CampusControl.s110'), value: 'inactive' as const },
]
const ruleIndicatorOptions = computed(() =>
  indicators.value
    .filter((i) => !ruleFilterDimension.value || i.dimension === ruleFilterDimension.value)
    .map((i) => ({ label: i.name, value: i.id })),
)
const ruleScopeOptions = computed(() => {
  const buses = Array.from(new Set(rules.value.map((r) => r.bu).filter(Boolean)))
  return [
    { label: t('pages.settings.CampusControl.s111'), value: '' },
    { label: t('pages.settings.CampusControl.s112'), value: '<GLOBAL>' },
    ...buses.map((b) => ({ label: b, value: b })),
  ]
})
const filteredRules = computed(() => {
  const kw = ruleFilterKeyword.value.trim().toLowerCase()
  return rules.value.filter((r) => {
    if (ruleFilterStatus.value === 'active' && !r.isActive) return false
    if (ruleFilterStatus.value === 'inactive' && r.isActive) return false
    if (ruleFilterDimension.value && r.dimension !== ruleFilterDimension.value) return false
    if (ruleFilterIndicator.value && r.indicator !== ruleFilterIndicator.value) return false
    if (ruleFilterScope.value === '<GLOBAL>' && r.bu) return false
    if (ruleFilterScope.value && ruleFilterScope.value !== '<GLOBAL>' && r.bu !== ruleFilterScope.value) return false
    if (kw) {
      const hay = [r.code, r.dimensionName || r.dimension, r.indicatorName || r.indicator, r.bu, r.position, r.level]
        .filter(Boolean).join('|').toLowerCase()
      if (!hay.includes(kw)) return false
    }
    return true
  })
})
// 维度切换时清掉不兼容的指标筛选（避免筛出空集）
watch(ruleFilterDimension, () => {
  if (ruleFilterIndicator.value && !ruleIndicatorOptions.value.some((o) => o.value === ruleFilterIndicator.value)) {
    ruleFilterIndicator.value = null
  }
})

/* ============================ 实时看板 ============================ */
const ratioData = ref<RatioResult>({ total: 0, rows: [] })
const ratioKpi = computed(() => {
  const rows = ratioData.value.rows
  const annualGap = (r: any) => (r.annualTarget || 0) > 0 && (r.annualAchieved || 0) < (r.annualTarget || 0)
  return {
    hard: rows.filter((r) => r.strength === '硬约束' && annualGap(r)).length,
    soft: rows.filter((r) => r.strength !== '硬约束' && annualGap(r)).length,
  }
})

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
const MONTH_LABELS = [t('pages.settings.CampusControl.s214'), t('pages.settings.CampusControl.s215'), t('pages.settings.CampusControl.s216'), t('pages.settings.CampusControl.s217'), t('pages.settings.CampusControl.s218'), t('pages.settings.CampusControl.s219'), t('pages.settings.CampusControl.s220'), t('pages.settings.CampusControl.s221'), t('pages.settings.CampusControl.s222'), t('pages.settings.CampusControl.s223'), t('pages.settings.CampusControl.s224'), t('pages.settings.CampusControl.s225')]

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
        annualTarget: r ? Math.round(r.annualTarget) : null,
        monthlyTargets: r ? normalizeMonthly(r.monthlyTargets) : Array(12).fill(0),
      }
    })
})

function selectDimension(id: string) {
  detailDimensionId.value = id
  const scopes = detailScopeOptions.value
  const years = detailYearOptions.value
  const sk = scopes.length ? scopes[0].value : scopeKeyOf('', '', '')
  const yr = years.length ? years[0].value : new Date().getFullYear()
  detailScopeKey.value = sk
  detailYear.value = yr
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

// 维度层级保存：把「归属年度 + 年度目标」扇出到该维度下所有适用范围（按各范围当前占比分配），逐 scope 调 set_rules
async function saveDimensionAnnualEdit() {
  if (!dimEditId.value) return
  const dimId = dimEditId.value
  const newYear = dimEditYear.value
  const newAnnual = Math.max(0, Math.round(dimEditAnnual.value || 0))
  const dRules = rules.value.filter((r) => r.dimension === dimId)
  if (dRules.length === 0) {
    message.warning(t('pages.settings.CampusControl.s113'))
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
    message.success(t('pages.settings.CampusControl.s114'))
    dimensionEditModal.value = false
    await loadRules()
  } catch (e) {
    message.error(extractApiError(e, t('pages.settings.CampusControl.s226')))
  } finally {
    dimEditSaving.value = false
  }
}

/* ============================ 指标管理 ============================ */
const indicatorDimFilter = ref<string | null>(null)
const indicatorDimOptions = computed(() => [
  { label: t('pages.settings.CampusControl.s115'), value: '' },
  ...dimensions.value.map((d) => ({ label: d.name, value: d.id })),
])
const filteredIndicators = computed(() => {
  if (!indicatorDimFilter.value) return indicators.value
  return indicators.value.filter((i) => i.dimension === indicatorDimFilter.value)
})

/* ============================ 加载 ============================
 * silent=true 用于入口批量加载，避免 Promise.all 并行失败时连弹 N 条 toast
 * （单个异常仍由调用方聚合展示一条）。
 */
async function loadDimensions(silent = false) {
  loading.dimensions = true
  try { dimensions.value = await listDimensions() }
  catch (e) { if (!silent) message.error(extractApiError(e, t('pages.settings.CampusControl.s227'))); throw e }
  finally { loading.dimensions = false }
}
async function loadIndicators(silent = false) {
  loading.indicators = true
  try { indicators.value = await listIndicators() }
  catch (e) { if (!silent) message.error(extractApiError(e, t('pages.settings.CampusControl.s228'))); throw e }
  finally { loading.indicators = false }
}
async function loadRules(silent = false) {
  loading.rules = true
  try { rules.value = await listRules() }
  catch (e) { if (!silent) message.error(extractApiError(e, t('pages.settings.CampusControl.s229'))); throw e }
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
    title: t('pages.settings.CampusControl.s116'), key: 'code', width: 110, fixed: 'left',
    render: (r: any) =>
      h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: (e: MouseEvent) => { e.stopPropagation(); openRuleDrawer(r, 'view') } }, { default: () => r.code || '—' }),
  },
  { title: t('pages.settings.CampusControl.s117'), key: 'dimensionName', width: 100, render: (r: any) => r.dimensionName || r.dimension },
  { title: t('pages.settings.CampusControl.s118'), key: 'indicatorName', width: 110, render: (r: any) => r.indicatorName || r.indicator },
  { title: t('pages.settings.CampusControl.s230'), key: 'scope', width: 200, render: (r: any) => scopeText(r.bu, r.position, r.level) },
  { title: t('pages.settings.CampusControl.s119'), key: 'year', width: 90, render: (r: any) => String(r.year) },
  {
    title: t('pages.settings.CampusControl.s120'), key: 'annualTarget', width: 110,
    render: (r: any) => (r.annualTarget ? String(Math.round(r.annualTarget)) : h('span', { class: 'muted' }, '—')),
  },
  {
    title: t('pages.settings.CampusControl.s121'), key: 'strength', width: 120,
    render: (r: any) => (r.strength
      ? h(NTag, { type: strengthType(r.strength), bordered: false, size: 'small' }, { default: () => r.strength })
      : h('span', { class: 'muted' }, '—')),
  },
  {
    title: t('pages.settings.CampusControl.s122'), key: 'rolloverEnabled', width: 110,
    render: (r: any) => h(NTag, {
      type: r.rolloverEnabled ? 'success' : 'default',
      bordered: false,
      size: 'small',
    }, { default: () => (r.rolloverEnabled ? t('pages.settings.CampusControl.s231') : t('pages.settings.CampusControl.s232')) }),
  },
  {
    title: t('pages.settings.CampusControl.s123'), key: 'op', width: 260, fixed: 'right',
    render: (r: any) =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'small', tertiary: true, onClick: (e: MouseEvent) => { e.stopPropagation(); ruleActions.copy(r) } }, { default: () => t('pages.settings.CampusControl.s233') }),
          h(NButton, { size: 'small', tertiary: true, type: 'primary', onClick: (e: MouseEvent) => { e.stopPropagation(); openRuleDrawer(r, 'edit') } }, { default: () => t('pages.settings.CampusControl.s234') }),
          h(NButton, { size: 'small', tertiary: true, type: r.isActive ? 'warning' : 'success', onClick: (e: MouseEvent) => { e.stopPropagation(); ruleActions.toggle(r, !r.isActive) } }, { default: () => (r.isActive ? t('pages.settings.CampusControl.s235') : t('pages.settings.CampusControl.s236')) }),
          h(NButton, { size: 'small', tertiary: true, type: 'error', onClick: (e: MouseEvent) => { e.stopPropagation(); ruleActions.remove(r) } }, { default: () => t('pages.settings.CampusControl.s237') }),
        ],
      }),
  },
]

async function loadRatio(silent = false) {
  loading.ratio = true
  try { ratioData.value = await getRatio() }
  catch (e) { if (!silent) message.error(extractApiError(e, t('pages.settings.CampusControl.s238'))); throw e }
  finally { loading.ratio = false }
}
function onTabChange(name: string) {
  if (name === 'ratio') { loadRatio() }
  else if (name === 'rules') loadRules()
  else if (name === 'persons') loadPersons()
  else if (name === 'indicators') loadIndicators()
}

/* ============================ 列定义 ============================ */
// 实时看板：人数达成管控视角（年度 / 本月 的目标、达成、达成率与在途）
const ratioColumns: DataTableColumns<any> = [
  { title: t('pages.settings.CampusControl.s230'), key: 'bu', width: 150, fixed: 'left', render: (r) => scopeText(r.bu, r.position, r.level) },
  { title: t('pages.settings.CampusControl.s124'), key: 'dimension', width: 90, fixed: 'left' },
  { title: t('pages.settings.CampusControl.s125'), key: 'indicator', width: 80, fixed: 'left' },
  { title: t('pages.settings.CampusControl.s126'), key: 'annualTarget', width: 90, render: (r) => String(r.annualTarget ?? 0) },
  { title: t('pages.settings.CampusControl.s127'), key: 'annualAchieved', width: 90, render: (r) => h(NTag, { type: (r.annualTarget || 0) > 0 && (r.annualAchieved || 0) >= (r.annualTarget || 0) ? 'success' : 'default', bordered: false, size: 'small' }, { default: () => String(r.annualAchieved ?? 0) }) },
  { title: t('pages.settings.CampusControl.s128'), key: 'annualRate', width: 100, render: (r) => r.annualRate == null ? '—' : `${Math.round((r.annualRate as number) * 100)}%` },
  { title: t('pages.settings.CampusControl.s129'), key: 'annualInProgress', width: 90, render: (r) => String(r.annualInProgress ?? 0) },
  { title: t('pages.settings.CampusControl.s130'), key: 'monthTarget', width: 110, render: (r) => String(r.monthTarget ?? 0) },
  // v2.10：新增本月浮动目标列（PR §3.2.2 / 设计文档 §7 T03；rolloverEnabled=False 时恒为 0）
  { title: t('pages.settings.CampusControl.s131'), key: 'monthRollover', width: 110, render: (r) => String(r.monthRollover ?? 0) },
  // v2.10：新增本月可用目标列（= 本月额定 + 本月浮动；达标 success tag）
  {
    title: t('pages.settings.CampusControl.s132'), key: 'monthAvailableTarget', width: 120,
    render: (r) => h(NTag, {
      type: (r.monthAvailableTarget || 0) > 0 && (r.monthAchieved || 0) >= (r.monthAvailableTarget || 0) ? 'success' : 'default',
      bordered: false,
      size: 'small',
    }, { default: () => String(r.monthAvailableTarget ?? 0) }),
  },
  { title: t('pages.settings.CampusControl.s133'), key: 'monthAchieved', width: 90, render: (r) => h(NTag, { type: (r.monthTarget || 0) > 0 && (r.monthAchieved || 0) >= (r.monthTarget || 0) ? 'success' : 'default', bordered: false, size: 'small' }, { default: () => String(r.monthAchieved ?? 0) }) },
  { title: t('pages.settings.CampusControl.s134'), key: 'monthRate', width: 100, render: (r) => r.monthRate == null ? '—' : `${Math.round((r.monthRate as number) * 100)}%` },
  { title: t('pages.settings.CampusControl.s135'), key: 'monthInProgress', width: 90, render: (r) => String(r.monthInProgress ?? 0) },
  { title: t('pages.settings.CampusControl.s136'), key: 'strength', width: 88, render: (r) => r.strength ? h(NTag, { type: strengthType(r.strength), bordered: false, size: 'small' }, { default: () => r.strength }) : h('span', { style: 'color:var(--ink-soft)' }, '—') },
]

const dimensionRuleColumns: DataTableColumns<any> = [
  {
    title: t('pages.settings.CampusControl.s137'), key: 'name',
    render: (d: any) => h('div', { style: 'display:flex; align-items:center; gap:8px;' }, [
      h('span', { style: 'font-weight:600;' }, d.name),
      d.code ? h(NTag, { size: 'small', bordered: false, type: 'default' }, { default: () => d.code }) : null,
    ]),
  },
  { title: t('pages.settings.CampusControl.s138'), key: 'yearLabels', width: 110, render: (d: any) => h('span', { class: 'muted' }, d.yearLabels) },
  { title: t('pages.settings.CampusControl.s139'), key: 'annualTotal', width: 130, render: (d: any) => (d.annualTotal > 0 ? h('span', {}, String(d.annualTotal)) : h('span', { class: 'muted' }, '—')) },
  { title: t('pages.settings.CampusControl.s140'), key: 'indicatorCount', width: 90, render: (d: any) => h('span', { class: 'muted' }, String(d.indicatorCount)) },
  { title: t('pages.settings.CampusControl.s141'), key: 'ruleSetCount', width: 170, render: (d: any) => h('span', { class: 'muted' }, String(d.ruleSetCount)) },
  {
    title: t('pages.settings.CampusControl.s142'), key: 'actions', width: 170, fixed: 'right',
    render: (d: any) => h('div', { style: 'display:flex; gap:8px;' }, [
      h(NButton, { size: 'small', quaternary: true, onClick: () => selectDimension(d.id) }, { default: () => t('pages.settings.CampusControl.s239') }),
    ]),
  },
]

const detailMatrixColumns: DataTableColumns<any> = [
  {
    title: t('pages.settings.CampusControl.s143'), key: 'indicatorName',
    render: (r: any) => h('div', { style: 'display:flex; align-items:center; gap:8px;' }, [
      h('span', {}, r.indicatorName),
      !r.configured ? h(NTag, { size: 'small', type: 'warning', bordered: false }, { default: () => t('pages.settings.CampusControl.s240') }) : null,
    ]),
  },
  {
    title: t('pages.settings.CampusControl.s144'), key: 'annualTarget', width: 120,
    render: (r: any) => (r.configured ? h('span', {}, String(r.annualTarget)) : h('span', { class: 'muted' }, '—')),
  },
  {
    title: t('pages.settings.CampusControl.s145'), key: 'monthly', width: 210,
    render: (r: any) => (r.configured
      ? h('span', { class: 'muted' }, t('pages.settings.CampusControl.s241', { n: currentMonthIdx.value + 1 }))
      : h('span', { class: 'muted' }, '—')),
  },
]
function renderDetailExpand(row: any) {
  return h('div', { style: 'display:grid; grid-template-columns:repeat(6,1fr); gap:8px; padding:4px 0;' },
    MONTH_LABELS.map((m, i) => h('div', { style: 'display:flex; flex-direction:column; align-items:center; padding:6px; background:var(--brand-tint); border-radius:6px;' }, [
      h('span', { style: 'font-size:12px; color:var(--n-text-color-3,#999);' }, m),
      h('span', { style: 'font-weight:600;' }, String(row.monthlyTargets[i] || 0)),
    ])),
  )
}

const indicatorColumns: DataTableColumns<ControlIndicator> = [
  { title: t('pages.settings.CampusControl.s146'), key: 'dimensionName', width: 160 },
  { title: t('pages.settings.CampusControl.s147'), key: 'name' },
  {
    title: t('pages.settings.CampusControl.s148'), key: 'actions', width: 120, fixed: 'right',
    render: (r) => h('div', { style: 'display:flex; gap:8px;' }, [
      h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openIndicatorModal(r) }, { default: () => t('pages.settings.CampusControl.s234') }),
      h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeIndicator(r) }, { default: () => t('pages.settings.CampusControl.s237') }),
    ]),
  },
]

const dimColumns: DataTableColumns<ControlDimension> = [
  { title: t('pages.settings.CampusControl.s149'), key: 'name' },
  { title: t('pages.settings.CampusControl.s150'), key: 'code', width: 120, render: (r) => r.code || '—' },
  {
    title: t('pages.settings.CampusControl.s151'), key: 'isActive', width: 70,
    render: (r) => h(NSwitch, {
      value: r.isActive, size: 'small',
      'onUpdate:value': async (v: boolean) => {
        try { await updateDimension(r.id, { isActive: v }); r.isActive = v; message.success(v ? t('pages.settings.CampusControl.s231') : t('pages.settings.CampusControl.s242')) }
        catch (e) { message.error(extractApiError(e, t('pages.settings.CampusControl.s243'))) }
      },
    }),
  },
  {
    title: t('pages.settings.CampusControl.s152'), key: 'actions', width: 120, fixed: 'right',
    render: (r) => h('div', { style: 'display:flex; gap:8px;' }, [
      h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openDimModal(r) }, { default: () => t('pages.settings.CampusControl.s234') }),
      h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeDim(r) }, { default: () => t('pages.settings.CampusControl.s237') }),
    ]),
  },
]

const personColumns: DataTableColumns<Person> = [
  { title: t('pages.settings.CampusControl.s153'), key: 'code' }, { title: t('pages.settings.CampusControl.s154'), key: 'name' }, { title: t('pages.settings.CampusControl.s155'), key: 'bu' },
  { title: t('pages.settings.CampusControl.s156'), key: 'school' }, { title: t('pages.settings.CampusControl.s157'), key: 'sex' }, { title: t('pages.settings.CampusControl.s158'), key: 'major' },
  { title: t('pages.settings.CampusControl.s159'), key: 'month' }, { title: t('pages.settings.CampusControl.s160'), key: 'position', render: (r) => r.position || '—' },
  { title: t('pages.settings.CampusControl.s161'), key: 'level', render: (r) => r.level || '—' },
  { title: t('pages.settings.CampusControl.s162'), key: 'status' },
  { title: t('pages.settings.CampusControl.s163'), key: 'counted', render: (r) => h(NTag, { type: r.counted ? 'success' : 'default', bordered: false, size: 'small' }, { default: () => (r.counted ? t('pages.settings.CampusControl.s267') : t('pages.settings.CampusControl.s268')) }) },
]

// v2.6 录入校验只看人数。占比/占比状态/强度三列移除（占比仅用于规则配置时计算实际人数，
// 不参与「是否可以录入」判定；strength 只对占比硬/软约束有意义，人数校验无此概念）。
// 实时看板（ratioColumns）仍使用 strengthType/ratioStatusType/pct，此处不删工具函数。
const checkColumns: DataTableColumns<ValidationResult['checks'][number]> = [
  { title: t('pages.settings.CampusControl.s230'), key: 'bu', width: 180, render: (r) => scopeText(r.bu, r.position, r.level) },
  { title: t('pages.settings.CampusControl.s164'), key: 'dimension', width: 100 }, { title: t('pages.settings.CampusControl.s165'), key: 'indicator', width: 100 },
  { title: t('pages.settings.CampusControl.s166'), key: 'monthActual', width: 100 }, { title: t('pages.settings.CampusControl.s167'), key: 'monthTarget', width: 100 },
  { title: t('pages.settings.CampusControl.s168'), key: 'countStatus', width: 110, render: (r) => h(NTag, { type: countStatusType(r.countStatus), bordered: false, size: 'small' }, { default: () => r.countStatus }) },
]

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
    message.success(t('pages.settings.CampusControl.s244', { format }))
  } catch (e) {
    message.error(extractApiError(e, t('pages.settings.CampusControl.s245')))
  }
}
async function onDownloadIndicatorTemplate() {
  // 导入弹窗内与工具栏的「下载模板」共用；默认 xlsx
  try {
    await downloadIndicatorTemplate('xlsx')
    message.success(t('pages.settings.CampusControl.s169'))
  } catch (e) {
    message.error(extractApiError(e, t('pages.settings.CampusControl.s246')))
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
        message.success(t('pages.settings.CampusControl.s247', { created: res.data.created, updated: res.data.updated, skipped: res.data.skipped }))
        loadIndicators()
        onFinish()
      } else {
        message.error(t('pages.settings.CampusControl.s248', { n: res.data.errors.length }))
        onError()
      }
    })
    .catch((e) => {
      const errRes = e?.response?.data
      if (errRes?.data?.errors) {
        indicatorImportDrawer.result = errRes
      } else {
        message.error(extractApiError(e, t('pages.settings.CampusControl.s249')))
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
    message.error(t('pages.settings.CampusControl.s170'))
  }
}
function onIndicatorImportFileRemove() {
  indicatorImportDrawer.fileList = []
  indicatorImportDrawer.result = null
}

async function onExportRules() {
  try {
    await exportRules()
    message.success(t('pages.settings.CampusControl.s171'))
  } catch (e) {
    message.error(extractApiError(e, t('pages.settings.CampusControl.s245')))
  }
}
async function onDownloadTemplate() {
  try {
    await downloadRuleTemplate()
    message.success(t('pages.settings.CampusControl.s172'))
  } catch (e) {
    message.error(extractApiError(e, t('pages.settings.CampusControl.s246')))
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
        message.success(t('pages.settings.CampusControl.s250', { groups: res.data.groups, rules: res.data.savedRules }))
        loadRules()
        loadRatio()
        onFinish()
      } else {
        message.error(t('pages.settings.CampusControl.s248', { n: res.data.errors.length }))
        onError()
      }
    })
    .catch((e) => {
      const errRes = e?.response?.data
      if (errRes?.data?.errors) {
        importDrawer.result = errRes
      } else {
        message.error(extractApiError(e, t('pages.settings.CampusControl.s249')))
      }
      onError()
    })
    .finally(() => { loading.import = false })
}
function downloadImportErrorReport() {
  const errors = importDrawer.result?.data?.errors || []
  if (!errors.length) return
  const text = [t('pages.settings.CampusControl.s251'), '====================', ...errors].join('\n')
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
    message.error(t('pages.settings.CampusControl.s173'))
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
  if (!dimModal.name.trim()) { message.warning(t('pages.settings.CampusControl.s174')); return }
  try {
    if (dimModal.editingId) await updateDimension(dimModal.editingId, { name: dimModal.name.trim(), code: dimModal.code.trim() })
    else await createDimension({ name: dimModal.name.trim(), code: dimModal.code.trim() })
    message.success(t('pages.settings.CampusControl.s175'))
    dimModal.show = false
    await loadDimensions()
  } catch (e) { message.error(extractApiError(e, t('pages.settings.CampusControl.s226'))) }
}
function removeDim(d: ControlDimension) {
  deleteDimension(d.id)
    .then(async () => {
      message.success(t('pages.settings.CampusControl.s176'))
      await Promise.all([loadDimensions(), loadIndicators()])
      undoable(t('pages.settings.CampusControl.s252', { name: d.name }), async () => {
        await restoreDimension(d.id)
        message.success(t('pages.settings.CampusControl.s177'))
        await Promise.all([loadDimensions(), loadIndicators()])
      })
    })
    .catch((e: any) => message.error(extractApiError(e, t('pages.settings.CampusControl.s253'))))
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
  if (!indicatorModal.dimensionId || !indicatorModal.name.trim()) { message.warning(t('pages.settings.CampusControl.s178')); return }
  try {
    if (indicatorModal.editingId) await updateIndicator(indicatorModal.editingId, { name: indicatorModal.name.trim() })
    else await createIndicator({ dimension: indicatorModal.dimensionId, name: indicatorModal.name.trim() })
    message.success(t('pages.settings.CampusControl.s179'))
    indicatorModal.show = false
    await loadIndicators()
  } catch (e) { message.error(extractApiError(e, t('pages.settings.CampusControl.s226'))) }
}
function removeIndicator(ind: ControlIndicator) {
  deleteIndicator(ind.id)
    .then(async () => {
      message.success(t('pages.settings.CampusControl.s180'))
      await loadIndicators()
      undoable(t('pages.settings.CampusControl.s254', { name: ind.name }), async () => {
        await restoreIndicator(ind.id)
        message.success(t('pages.settings.CampusControl.s181'))
        await loadIndicators()
      })
    })
    .catch((e: any) => message.error(extractApiError(e, t('pages.settings.CampusControl.s253'))))
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
  } catch (e) { message.error(extractApiError(e, t('pages.settings.CampusControl.s255'))) }
  finally { loading.validate = false }
}
const canConfirmEntry = computed(
  () => !!draft.code.trim() && !!draft.name.trim() && validation.value != null && validation.value.verdictLevel !== 'block',
)
async function confirmEntry() {
  if (!draft.code.trim() || !draft.name.trim()) { message.warning(t('pages.settings.CampusControl.s182')); return }
  try {
    await upsertPerson({
      code: draft.code.trim(), name: draft.name.trim(), bu: draft.bu,
      school: draft.school, sex: draft.sex, major: draft.major, month: draft.month, status: draft.status, counted: true,
      position: draft.position, level: draft.level,
    })
    message.success(t('pages.settings.CampusControl.s183'))
    validation.value = null
    await Promise.all([loadPersons(), loadRatio()])
  } catch (e) { message.error(extractApiError(e, t('pages.settings.CampusControl.s256'))) }
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
  if (!personModal.code.trim() || !personModal.name.trim()) { message.warning(t('pages.settings.CampusControl.s184')); return }
  try {
    await upsertPerson({
      id: personModal.editingId ?? undefined,
      code: personModal.code.trim(), name: personModal.name.trim(), bu: personModal.bu,
      school: personModal.school, sex: personModal.sex, major: personModal.major, month: personModal.month, status: personModal.status,
      expectedEntryDate: personModal.expectedEntryDate,
      actualEntryDate: personModal.actualEntryDate,
      position: personModal.position, level: personModal.level, counted: personModal.counted,
    })
    message.success(t('pages.settings.CampusControl.s185'))
    personModal.show = false
    await loadPersons()
  } catch (e) { message.error(extractApiError(e, t('pages.settings.CampusControl.s226'))) }
}
function removePerson(p: Person) {
  deletePerson(p.id)
    .then(async () => {
      message.success(t('pages.settings.CampusControl.s186'))
      await loadPersons()
      undoable(t('pages.settings.CampusControl.s257', { name: p.name, code: p.code }), async () => {
        await restorePerson(p.id)
        message.success(t('pages.settings.CampusControl.s187'))
        await loadPersons()
      })
    })
    .catch((e: any) => message.error(extractApiError(e, t('pages.settings.CampusControl.s253'))))
}

async function loadPersons(silent = false) {
  loading.persons = true
  try {
    const params: {
      staffed?: boolean; status?: string
      bu?: string; position?: string; level?: string
      school?: string; sex?: string; major?: string
      month?: string; year?: number; search?: string
    } = {}
    if (personFilterStatus.value !== 'all') params.status = personFilterStatus.value
    if (personFilterBu.value) params.bu = personFilterBu.value
    if (personFilterPosition.value) params.position = personFilterPosition.value
    if (personFilterLevel.value) params.level = personFilterLevel.value
    if (personFilterSchool.value) params.school = personFilterSchool.value
    if (personFilterSex.value) params.sex = personFilterSex.value
    if (personFilterMajor.value) params.major = personFilterMajor.value
    if (personFilterMonth.value) params.month = personFilterMonth.value
    if (personFilterYear.value) params.year = personFilterYear.value
    if (personFilterSearch.value.trim()) params.search = personFilterSearch.value.trim()
    persons.value = await listPersons(params)
  }
  catch (e) { if (!silent) message.error(extractApiError(e, t('pages.settings.CampusControl.s258'))); throw e }
  finally { loading.persons = false }
}
// 任一筛选变化即时重载（分页计数由后端按过滤结果返回，保持准确）
watch(personFilterStatus, () => loadPersons())
watch([personFilterBu, personFilterPosition, personFilterLevel, personFilterSchool,
       personFilterSex, personFilterMajor, personFilterYear, personFilterMonth,
       personFilterSearch], () => loadPersons())

onMounted(async () => {
  // 入口批量加载：silent 抑制各调用内部 toast，由下方 allSettled 聚合成单条
  const results = await Promise.allSettled([
    loadDimensions(true),
    loadIndicators(true),
    loadPersons(true),
    loadRatio(true),
    loadRules(true),
  ])
  const failures = results
    .map((r, i) => ({ r, label: [t('pages.settings.CampusControl.s259'), t('pages.settings.CampusControl.s260'), t('pages.settings.CampusControl.s261'), t('pages.settings.CampusControl.s262'), t('pages.settings.CampusControl.s263')][i] }))
    .filter((x) => x.r.status === 'rejected')
  if (failures.length === 1) {
    message.error(t('pages.settings.CampusControl.s264', { label: failures[0].label, msg: (failures[0].r as PromiseRejectedResult).reason?.response?.data?.message || (failures[0].r as PromiseRejectedResult).reason?.message || t('pages.settings.CampusControl.s265') }))
  } else if (failures.length > 1) {
    message.error(t('pages.settings.CampusControl.s266', { n: failures.length, labels: failures.map((x) => x.label).join('、') }))
  }
})
</script>

<style scoped>
/* 仅保留「布局链」相关规则，视觉（玻璃/极光/标题渐变/KPI/表格/弹窗）统一复用全局 glass.css
   —— 单一设计系统，校招管控不再持有私有视觉定义。 */

/* 「全局 + 指定范围」混合规则集 → 重复计入风险徽标 */
.scope-mutex-badge {
  cursor: help;
  font-size: var(--fs-14);
  line-height: 1;
  user-select: none;
}
.scope-mutex-banner {
  margin-bottom: var(--space-3);
}

/* 规则配置工具条：搜索稍宽 + 4 个筛选下拉等宽，避免 1440px 视口被挤换行 */
.rule-filter-search {
  width: 200px;
  flex-shrink: 0;
}
.rule-filter-select {
  width: 130px;
  flex-shrink: 0;
}

/* 人员数据工具条：搜索框 + 状态筛 + 8 筛 单行排列（搜索框最左、状态筛紧随其后、spacer 推到最右）。
   窄视口下 flex-wrap 兜底自动换行，避免横向溢出（AGENTS.md R-103 320px 无横向溢出）。 */
.toolbar--filters {
  flex-wrap: wrap;
  row-gap: var(--space-2);
  align-items: center;
}
.toolbar--filters .rule-filter-select {
  width: 116px;
}
.toolbar--filters .rule-filter-search {
  width: 282px;
  flex-shrink: 0;
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
  padding: var(--space-3) 14px 14px;
  margin-bottom: var(--space-3);
  transition: border-color 0.2s ease;
}
.form-section:last-child { margin-bottom: 0; }
.form-section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-13);
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
  font-size: var(--fs-12);
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
  gap: var(--space-1);
  min-width: 0;
  flex: 1 1 140px;
}
.scope-label {
  font-size: var(--fs-12);
  color: var(--ink-soft);
  line-height: 1;
}

/* 12 个月网格（批量=6 列，规则=4 列） */
.monthly-block-label {
  font-size: var(--fs-12);
  color: var(--ink-soft);
  margin: var(--space-3) 0 6px;
}
.monthly-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 6px 6px;
}
.monthly-grid--rule {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-2);
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
  gap: var(--space-2);
  margin-top: var(--space-2);
  font-size: var(--fs-12);
  color: var(--ink);
}
.allocated strong { font-weight: 700; }

/* 占比之和 callout */
.sum-callout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-3);
  padding: 10px 14px;
  border-radius: var(--radius-md);
  transition: background 0.2s ease, border-color 0.2s ease;
}
.sum-callout.ok {
  background: var(--c-success-soft);
  border: 1px solid var(--c-success-soft);
}
.sum-callout.warn {
  background: var(--c-warning-soft);
  border: 1px solid var(--c-warning-soft);
}
.sum-left {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}
.sum-label {
  font-size: var(--fs-12);
  color: var(--ink-soft);
}
.sum-value {
  font-size: var(--fs-18);
  font-weight: 700;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.sum-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.sum-diff {
  font-size: var(--fs-12);
  color: var(--ink-soft);
  font-variant-numeric: tabular-nums;
}

.empty-tip {
  color: var(--ink-faint);
  padding: var(--space-3) var(--space-1);
  font-size: var(--fs-13);
  text-align: center;
}

/* form-row-2 间距微调 */
.form-row-2 { margin-bottom: var(--space-1); }

/* ===================== 维度规则集编辑面 ===================== */

/* 适用范围 form-section 标题行右移 switch */
.form-section-title--scope {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.form-section-title--scope .dot { flex-shrink: 0; }
.scope-title-switch { margin-left: auto; }
/* 编辑态改了适用范围 → 重定位提示横幅 */
.scope-relocate-hint {
  margin-top: var(--space-2);
  font-size: var(--fs-12);
  line-height: 1.5;
}
.scope-relocate-hint :deep(.n-alert__content) { font-size: var(--fs-12); }

/* 维度层级编辑弹窗 */
.dim-edit-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: var(--space-1) 0;
}
.dim-edit-form .scope-field {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.dim-edit-form .scope-label {
  width: 92px;
  font-size: var(--fs-13);
  color: var(--ink);
  flex-shrink: 0;
}

/* 维度年度管控人数 section */
.total-target-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.total-target-suffix { font-size: var(--fs-13); color: var(--ink); }
.total-target-hint { font-size: var(--fs-12); color: var(--ink-faint); }
.total-target-summary {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
  font-size: var(--fs-12);
  color: var(--ink-soft);
  font-variant-numeric: tabular-nums;
}
.total-target-summary strong { color: var(--ink); font-weight: 700; }
.total-target-sep { color: var(--ink-faint); }
.total-target-tag { margin-left: auto; }

/* 行内控件：统一上下结构（label 上、控件下），与「占比%」「强度」一致 */


/* ===================== 弹窗级微调 ===================== */
.rule-modal :deep(.n-card__content),
.dim-ruleset-modal :deep(.n-card__content) {
  padding: var(--space-4) 20px 14px !important;
}
.rule-modal :deep(.n-card__footer),
.dim-ruleset-modal :deep(.n-card__footer) {
  padding: 10px 20px 14px !important;
}
.rule-modal :deep(.n-card-header__main),
.dim-ruleset-modal :deep(.n-card-header__main) {
  font-size: var(--fs-16);
  font-weight: 600;
}
.rule-modal :deep(.n-form-item),
.dim-ruleset-modal :deep(.n-form-item) {
  margin-bottom: 10px;
}
.rule-modal :deep(.n-form-item-label),
.dim-ruleset-modal :deep(.n-form-item-label) {
  font-size: var(--fs-12);
  padding-bottom: var(--space-1) !important;
}
.rule-modal :deep(.n-input-number--small) {
  --n-height: 28px !important;
}
.rule-modal :deep(.n-select--small) {
  --n-height: 28px !important;
}

.import-hint {
  margin: var(--space-3) 0 0;
  font-size: var(--text-small);
  color: var(--ink-soft);
  line-height: 1.6;
}
.import-result { margin-top: var(--space-4); }
.import-error-actions {
  margin: var(--space-2) 0;
  display: flex;
  justify-content: flex-end;
}
.import-errors {
  margin: var(--space-2) 0 0;
  padding-left: 18px;
  max-height: 240px;
  overflow: auto;
}
.import-errors li {
  font-size: var(--fs-12);
  color: var(--c-error);
  margin-bottom: var(--space-1);
}

/* 弹窗居中 + 内部滚动 + 去边框由全局 .n-modal .n-card（glass.css 阶段 F）统一处理，
   本页仅保留 .batch-modal 的密集表单紧凑间距微调。 */
</style>
