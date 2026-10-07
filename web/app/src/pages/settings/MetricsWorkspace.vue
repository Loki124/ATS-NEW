<template>
  <div class="page-container metrics-ws">
    <!-- ========== Header ========== -->
    <div class="page-header">
      <div>
        <h1 class="ws-title">{{ t('metrics.library.title') }}</h1>
        <p class="ws-subtitle">{{ t('metrics.library.subtitle') }}</p>
      </div>
    </div>

    <!-- ========== 顶层 Tab：指标定义 / 指标模板 ========== -->
    <div class="ws-body">
      <n-tabs v-model:value="activeTab" type="line">
        <!-- ---------- Tab 1：指标定义（只读，统一视图） ---------- -->
        <n-tab-pane name="definitions" :tab="t('metrics.tab.definitions')">
          <div class="ws-tab-header">
            <div class="ws-toolbar">
              <n-input
                v-model:value="defKeyword"
                :placeholder="t('metrics.filter.keywordPlaceholder')"
                clearable
                class="ws-search"
              >
                <template #prefix>
                  <n-icon :component="SearchOutline" />
                </template>
              </n-input>
              <n-select
                v-model:value="defKind"
                :placeholder="t('metrics.filter.kind')"
                :options="defKindOptions"
                class="ws-filter"
              />
              <n-select
                v-model:value="defModule"
                :placeholder="t('metrics.filter.sourceModule')"
                :options="defModuleOptions"
                class="ws-filter"
              />
            </div>
          </div>

          <div class="ws-table-wrap">
            <n-spin :show="loading" class="ws-spin">
              <div v-if="loadError" class="ws-empty">
                <n-result status="error" :title="t('metrics.empty.loadErrorTitle')" :description="t('metrics.empty.loadErrorDesc')">
                  <template #footer>
                    <n-button tertiary size="small" @click="load">{{ t('metrics.empty.reload') }}</n-button>
                  </template>
                </n-result>
              </div>
              <div v-else-if="!filteredDefinitions.length" class="ws-empty">
                <n-empty
                  v-if="defEmptyKind === 'first'"
                  :description="t('metrics.empty.definitionsFirst')"
                />
                <template v-else>
                  <n-empty :description="t('metrics.empty.definitionsFiltered')" />
                  <n-button size="small" tertiary class="ws-empty-action" @click="clearDefFilters">
                    {{ t('metrics.empty.clearFilters') }}
                  </n-button>
                </template>
              </div>
              <n-data-table
                v-else
                :columns="defColumns"
                :data="pagedDefinitions"
                :row-props="defRowProps"
              :scroll-x="920"
              :max-height="tableMaxHeight"
              size="small"
              class="ws-table"
              />
            </n-spin>
            <div v-if="filteredDefinitions.length > 0" class="ws-pager">
              <n-pagination
                :page="defPage"
                :page-size="defPageSize"
                :item-count="filteredDefinitions.length"
                :page-sizes="[10, 20, 50, 100]"
                show-size-picker
                show-quick-jumper
                @update:page="(p: number) => (defPage = p)"
                @update:page-size="(s: number) => { defPageSize = s; defPage = 1 }"
              >
                <template #prefix>
                  <span class="ws-pager-count">{{ t('metrics.filter.resultCount', { count: filteredDefinitions.length }) }}</span>
                </template>
              </n-pagination>
            </div>
          </div>
        </n-tab-pane>

        <!-- ---------- Tab 2：指标模板（CRUD） ---------- -->
        <n-tab-pane name="template" :tab="t('metrics.tab.template')">
          <div class="ws-tab-header">
            <div class="ws-tab-bar">
              <div class="ws-toolbar ws-toolbar-grow">
                <n-input
                  v-model:value="tplKeyword"
                  :placeholder="t('metrics.filter.keywordPlaceholder')"
                  clearable
                  class="ws-search"
                >
                  <template #prefix>
                    <n-icon :component="SearchOutline" />
                  </template>
                </n-input>
                <n-select
                  v-model:value="tplStatus"
                  :placeholder="t('metrics.filter.status')"
                :options="tplStatusOptions"
                class="ws-filter"
              />
            </div>
              <div class="ws-io-bar">
                <n-button tertiary size="small" :loading="exporting" @click="onExportTemplates">
                  {{ t('metrics.templateIo.export') }}
                </n-button>
                <n-button tertiary size="small" @click="openImportModal">
                  {{ t('metrics.templateIo.import') }}
                </n-button>
                <n-button type="primary" size="small" @click="openTemplateCreate">
                  {{ t('metrics.btn.create') }}{{ t('metrics.tab.template') }}
                </n-button>
              </div>
            </div>
          </div>

          <div class="ws-table-wrap">
            <n-spin :show="loading" class="ws-spin">
              <div v-if="loadError" class="ws-empty">
                <n-result status="error" :title="t('metrics.empty.loadErrorTitle')" :description="t('metrics.empty.loadErrorDesc')">
                  <template #footer>
                    <n-button tertiary size="small" @click="load">{{ t('metrics.empty.reload') }}</n-button>
                  </template>
                </n-result>
              </div>
              <div v-else-if="!loading && !templateList.length" class="ws-empty">
                <n-empty :description="t('metrics.empty.noTemplates')" />
              </div>
              <div v-else-if="!filteredTemplates.length" class="ws-empty">
                <n-empty :description="t('metrics.empty.templatesFiltered')" />
                <n-button size="small" tertiary class="ws-empty-action" @click="clearTplFilters">
                  {{ t('metrics.empty.clearFilters') }}
                </n-button>
              </div>
              <n-data-table
                v-else
                :columns="tplColumns"
                :data="pagedTemplates"
              :scroll-x="900"
              :max-height="tableMaxHeight"
              size="small"
              class="ws-table"
              />
            </n-spin>
            <div v-if="filteredTemplates.length > 0" class="ws-pager">
              <n-pagination
                :page="tplPage"
                :page-size="tplPageSize"
                :item-count="filteredTemplates.length"
                :page-sizes="[10, 20, 50, 100]"
                show-size-picker
                show-quick-jumper
                @update:page="(p: number) => (tplPage = p)"
                @update:page-size="(s: number) => { tplPageSize = s; tplPage = 1 }"
              >
                <template #prefix>
                  <span class="ws-pager-count">{{ t('metrics.filter.resultCount', { count: filteredTemplates.length }) }}</span>
                </template>
              </n-pagination>
            </div>
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>

    <!-- ========== 指标模板导入弹窗（下载模板 + 选择文件 + 导入 + 异常反馈一体化） ========== -->
    <n-modal
      v-model:show="importModalVisible"
      preset="card"
      :title="t('metrics.templateIo.modalTitle')"
      style="width: 520px; max-width: 92vw;"
      :mask-closable="!importing"
      @after-leave="resetImportModal"
    >
      <div class="im-body">
        <div class="im-row">
          <span class="im-label">{{ t('metrics.templateIo.importMode') }}</span>
          <n-select
            v-model:value="importMode"
            :options="importModeOptions"
            size="small"
            class="im-select"
            :disabled="importing"
          />
        </div>

        <div class="im-row">
          <n-button tertiary size="small" :loading="downloadingTemplate" @click="onDownloadTemplateTemplate">
            {{ t('metrics.templateIo.downloadTemplate') }}
          </n-button>
          <span class="im-hint">{{ t('metrics.templateIo.templateHint') }}</span>
        </div>

        <div class="im-divider" />

        <div class="im-row">
          <n-button size="small" :disabled="importing" @click="onPickFile">
            {{ t('metrics.templateIo.pickFile') }}
          </n-button>
          <span class="im-file" :class="{ 'im-file-empty': !importFile }">
            {{ importFile ? importFile.name : t('metrics.templateIo.noFile') }}
          </span>
        </div>

        <input
          ref="fileInputRef"
          type="file"
          accept=".xlsx,.csv"
          class="ws-hidden-file"
          @change="onFileSelected"
        />

        <div v-if="importSuccessInfo" class="im-feedback">
          <n-alert type="success" :show-icon="true" class="im-alert">
            {{
              t('metrics.templateIo.importSuccess', {
                created: importSuccessInfo.created,
                updated: importSuccessInfo.updated,
                skipped: importSuccessInfo.skipped,
              })
            }}
          </n-alert>
        </div>

        <div v-if="importModalErrors.length" class="im-feedback">
          <n-alert type="error" :show-icon="true" class="im-alert">
            <div class="im-err-title">{{ t('metrics.templateIo.importFailed') }}</div>
            <ul class="im-err-list">
              <li v-for="(msg, idx) in importModalErrors" :key="idx">{{ msg }}</li>
            </ul>
            <n-button
              v-if="importErrorFile"
              size="tiny"
              text
              type="error"
              class="im-dl-btn"
              @click="onDownloadErrorFile"
            >
              {{ t('metrics.templateIo.downloadErrorFile') }}
            </n-button>
          </n-alert>
        </div>
      </div>

      <template #footer>
        <div class="im-footer">
          <n-button size="small" tertiary :disabled="importing" @click="importModalVisible = false">
            {{ t('metrics.btn.cancel') }}
          </n-button>
          <n-button
            type="primary"
            size="small"
            :disabled="!importFile"
            :loading="importing"
            @click="onStartImport"
          >
            {{ t('metrics.templateIo.runImport') }}
          </n-button>
        </div>
      </template>
    </n-modal>

    <!-- ========== 指标定义详情弹窗（居中，只读） ========== -->
    <n-modal
      v-model:show="detailVisible"
      preset="card"
      :title="detailRow ? detailRow.name : ''"
      style="width: 680px; max-width: 92vw;"
      :mask-closable="true"
    >
      <template v-if="detailRow">
        <!-- 顶部 Hero：类型徽标 + 入参/出参 -->
        <div class="dm-hero">
          <span class="dm-eyebrow">{{ t('metrics.tab.definitions') }}</span>
          <div class="dm-hero-row">
            <span class="dm-kind-badge" :class="kindClass(detailRow)">
              <KindIcon :kind="detailRow.kind" :size="18" />
              {{ kindLabel(detailRow) }}
            </span>
            <span class="dm-meta-chip">
              <span class="dm-meta-k">{{ t('metrics.detail.inputLabel') }}</span>
              <span class="dm-meta-v">{{ inputEntityLabel(detailRow) }}</span>
            </span>
            <span class="dm-meta-chip">
              <span class="dm-meta-k">{{ t('metrics.detail.outputLabel') }}</span>
              <span class="dm-meta-v">{{ outputFieldLabel(detailRow) }}</span>
            </span>
          </div>
        </div>

        <!-- 数据源 -->
        <section class="dm-section">
          <div class="dm-section-label">{{ t('metrics.col.dataSource') }}</div>
          <code class="ws-code dm-source">{{ detailRow.dataSource }}</code>
        </section>

        <!-- 支持的算子 -->
        <section class="dm-section">
          <div class="dm-section-label">{{ t('metrics.col.operators') }}</div>
          <div class="ws-ops">
            <span v-for="op in (detailRow.supportedOperators || [])" :key="op" class="ws-op-tag">
              {{ operatorLabel(op) }}
            </span>
            <span v-if="!(detailRow.supportedOperators || []).length" class="ws-muted">-</span>
          </div>
        </section>

        <!-- 枚举取值 -->
        <section v-if="detailRow.isEnum" class="dm-section">
          <div class="dm-section-label">{{ t('metrics.col.enumValues') }}</div>
          <div class="ws-ops">
            <span v-for="ev in enumValuesOf(detailRow)" :key="ev" class="ws-enum-tag">{{ ev }}</span>
            <span v-if="!enumValuesOf(detailRow).length" class="ws-muted">-</span>
          </div>
        </section>

        <!-- 说明 -->
        <section v-if="detailRow.description" class="dm-section">
          <div class="dm-section-label">{{ t('metrics.form.description') }}</div>
          <p class="dm-desc">{{ detailRow.description }}</p>
        </section>

        <!-- 输入参数契约（参数化 Handler；使用本指标必须提供的参数，实际取值在模板层配置） -->
        <section v-if="detailRow?.paramSchema?.length" class="dm-section dm-params">
          <div class="dm-section-label">{{ t('metrics.detail.inputParamsTitle') }}</div>
          <div class="detail-params-readonly">
            <div v-for="p in detailRow.paramSchema" :key="p.key" class="detail-param-row">
              <span class="param-label">{{ p.label }}</span>
              <span class="param-meta">
                {{ paramSchemaTypeLabel(p.type) }}<template v-if="p.required"> · {{ t('metrics.detail.required') }}</template>
              </span>
            </div>
          </div>
          <p class="dm-desc dm-hint">{{ t('metrics.detail.inputParamsHint') }}</p>
        </section>
      </template>
    </n-modal>

    <!-- ========== 指标模板新建/编辑弹窗（PRD：参数 / 算子 / 值域） ========== -->
    <n-modal
      v-model:show="showTemplateModal"
      preset="card"
      :title="templateModalTitle"
      :closable="true"
      style="width: 720px; max-width: 94vw; max-height: 90vh;"
      :mask-closable="false"
    >
      <n-form :model="tplForm" label-placement="top" class="tpl-form">
        <n-form-item :label="t('metrics.form.name')" required>
          <n-input v-model:value="tplForm.name" :placeholder="t('metrics.form.name')" />
        </n-form-item>

        <n-form-item :label="t('metrics.form.metricDefinition')" required>
          <n-select
            v-model:value="tplForm.metricDefinition"
            :options="metricDefinitionOptions"
            clearable
            :placeholder="t('metrics.form.metricDefinition')"
            @update:value="onTemplateMetricChange"
          />
        </n-form-item>

        <div v-if="selectedTemplateDefinition" class="tpl-output-bar">
          <span class="tpl-output-label">{{ t('metrics.tpl.outputParam') }}</span>
          <n-tag size="small" type="info">{{ returnTypeLabel(selectedTemplateDefinition.returnType) }}</n-tag>
          <span v-if="selectedTemplateDefinition.unit" class="tpl-output-unit">{{ selectedTemplateDefinition.unit }}</span>
          <span class="tpl-output-hint">{{ t('metrics.tpl.inheritedHint') }}</span>
        </div>

        <n-form-item v-if="selectedTemplateDefinition" :label="t('metrics.tpl.outputUnit')" class="tpl-unit-field">
          <n-input
            v-model:value="tplForm.unit"
            :placeholder="selectedTemplateDefinition.unit || t('metrics.tpl.outputUnitPlaceholder')"
          />
          <template #help>{{ t('metrics.tpl.outputUnitHint') }}</template>
        </n-form-item>

        <!-- 参数配置：仅参数化 Handler 类型指标展示 -->
        <section v-if="showTemplateParamConfig" class="tpl-section-card">
          <div class="tpl-section-header">
            <span class="tpl-section-number">1</span>
            <span class="tpl-section-title">{{ t('metrics.tpl.paramConfigTitle') }}</span>
            <n-tag
              size="small"
              :type="selectedTemplateDefinition?.paramType === 'continuous' ? 'success' : 'warning'"
            >
              {{ paramTypeLabel(selectedTemplateDefinition?.paramType) }}
            </n-tag>
            <span class="tpl-section-hint">{{ paramConfigHint }}</span>
          </div>
          <div class="tpl-subblock">
            <div class="tpl-subblock-title">{{ t('metrics.tpl.calcParamsTitle') }}</div>
            <p class="tpl-subblock-hint">{{ t('metrics.tpl.calcParamsHint') }}</p>
            <div v-if="selectedTemplateDefinition?.paramSchema?.length" class="tpl-calc-params">
              <div v-for="p in selectedTemplateDefinition.paramSchema" :key="p.key" class="tpl-calc-row">
                <span class="param-label">
                  {{ p.label }}<template v-if="p.required"> *</template>
                </span>
                <n-input-number
                  v-if="p.type === 'number'"
                  v-model:value="tplForm.calcParams[p.key]"
                  :min="p.min ?? 0"
                  class="param-input"
                />
                <n-select
                  v-else-if="p.type === 'select'"
                  v-model:value="tplForm.calcParams[p.key]"
                  :options="(p.options || []).map((o: any) => ({ label: o.label, value: o.value }))"
                  class="param-input"
                />
                <n-switch v-else-if="p.type === 'boolean'" v-model:value="tplForm.calcParams[p.key]" />
                <n-input v-else v-model:value="tplForm.calcParams[p.key]" class="param-input" />
                <span v-if="p.key === 'recent_n'" class="param-hint">{{ t('metrics.detail.recentNHint') }}</span>
              </div>
            </div>
            <div v-else class="tpl-info-text">{{ t('metrics.tpl.handlerNoParamsNeeded') }}</div>
          </div>
          <div class="tpl-section-body">
            <div class="tpl-row">
              <n-form-item :label="t('metrics.tpl.rangeMin')" class="tpl-field">
                <n-input-number v-model:value="tplForm.paramConfig.min" :precision="paramPrecision" />
              </n-form-item>
              <span class="tpl-range-sep">~</span>
              <n-form-item :label="t('metrics.tpl.rangeMax')" class="tpl-field">
                <n-input-number v-model:value="tplForm.paramConfig.max" :precision="paramPrecision" />
              </n-form-item>
              <n-form-item :label="t('metrics.tpl.step')" class="tpl-field">
                <n-input-number v-model:value="tplForm.paramConfig.step" :min="0" :precision="paramPrecision" />
              </n-form-item>
            </div>
            <div class="tpl-row">
              <n-form-item :label="t('metrics.tpl.prefix')" class="tpl-field">
                <n-input v-model:value="tplForm.paramConfig.prefix" />
              </n-form-item>
              <n-form-item :label="t('metrics.tpl.suffix')" class="tpl-field">
                <n-input v-model:value="tplForm.paramConfig.suffix" />
              </n-form-item>
              <n-form-item class="tpl-field tpl-switch-field">
                <template #label>
                  <span>{{ t('metrics.tpl.allOption') }}</span>
                </template>
                <n-switch v-model:value="tplForm.paramConfig.allOption" />
              </n-form-item>
            </div>
            <div v-if="paramPreviewValues.length" class="tpl-preview">
              <span class="tpl-preview-tag">
                [{{ tplForm.paramConfig.allOption ? t('metrics.tpl.unlimited') : t('metrics.tpl.allLabel') }}]
              </span>
              <span>
                · {{ t('metrics.tpl.valuePreview', { count: paramPreviewValues.length }) }}：
                {{ paramPreviewValues.join('，') }}
              </span>
            </div>
          </div>
        </section>
        <div v-else-if="selectedTemplateDefinition && selectedTemplateDefinition.valueMode === 'object_path'" class="tpl-info-text">
          {{ t('metrics.tpl.noParamsNeeded') }}
        </div>
        <div v-else-if="selectedTemplateDefinition" class="tpl-info-text">
          {{ t('metrics.tpl.handlerNoParamsNeeded') }}
        </div>

        <!-- 启用算子 -->
        <section class="tpl-section-card">
          <div class="tpl-section-header">
            <span class="tpl-section-number">2</span>
            <span class="tpl-section-title">{{ t('metrics.tpl.operatorTitle') }}</span>
            <span class="tpl-section-hint">
              {{ t('metrics.tpl.operatorCount', { total: supportedOperatorOptions.length, enabled: tplForm.operators.length }) }}
            </span>
          </div>
          <div class="tpl-section-body">
            <div v-if="supportedOperatorOptions.length" class="tpl-operator-chips">
              <label
                v-for="op in supportedOperatorOptions"
                :key="op.value"
                class="tpl-op-chip"
                :class="{ 'is-checked': tplForm.operators.includes(op.value) }"
              >
                <input
                  type="checkbox"
                  :value="op.value"
                  :checked="tplForm.operators.includes(op.value)"
                  @change="toggleOperator(op.value)"
                />
                <n-icon v-if="tplForm.operators.includes(op.value)" :component="CheckmarkOutline" />
                <span>{{ op.label }}</span>
              </label>
            </div>
            <div v-else class="tpl-info-text">
              {{ t('metrics.tpl.noMetricSelected') }}
            </div>
          </div>
        </section>

        <!-- 值域配置 -->
        <section class="tpl-section-card">
          <div class="tpl-section-header">
            <span class="tpl-section-number">3</span>
            <span class="tpl-section-title">{{ t('metrics.tpl.domainTitle') }}</span>
            <span class="tpl-section-hint">{{ t('metrics.tpl.domainHint') }}</span>
          </div>
          <div class="tpl-section-body">
            <div
              v-for="(seg, idx) in tplForm.valueDomain.segments"
              :key="idx"
              class="tpl-segment-block"
            >
              <div class="tpl-segment-row">
                <span class="tpl-segment-label">{{ t('metrics.tpl.segment', { index: idx + 1 }) }}</span>
                <n-input-number v-model:value="seg.min" class="tpl-seg-field" :precision="paramPrecision" />
                <span class="tpl-range-sep">~</span>
                <n-input-number v-model:value="seg.max" class="tpl-seg-field" :precision="paramPrecision" />
                <span v-if="tplForm.unit || selectedTemplateDefinition?.unit" class="tpl-unit-text">{{ tplForm.unit || selectedTemplateDefinition?.unit }}</span>
                <n-form-item :label="t('metrics.tpl.step')" class="tpl-step-field">
                  <n-input-number v-model:value="seg.step" :min="0" :precision="paramPrecision" />
                </n-form-item>
                <n-button size="small" quaternary type="error" @click="removeSegment(idx)">
                  {{ t('metrics.btn.delete') }}
                </n-button>
              </div>
              <div v-if="segmentPreviewValues(seg).length" class="tpl-preview">
                <span class="tpl-preview-tag">[{{ t('metrics.tpl.segment', { index: idx + 1 }) }}]</span>
                <span>
                  · {{ t('metrics.tpl.valuePreview', { count: segmentPreviewValues(seg).length }) }}：
                  {{ segmentPreviewValues(seg).join('，') }}
                </span>
              </div>
            </div>
            <n-button size="small" dashed @click="addSegment">{{ t('metrics.tpl.addSegment') }}</n-button>
          </div>
        </section>

        <n-form-item :label="t('metrics.form.description')">
          <n-input v-model:value="tplForm.description" type="textarea" :rows="2" />
        </n-form-item>
        <n-form-item :label="t('metrics.form.status')">
          <n-switch
            v-model:value="tplForm.status"
            checked-value="enabled"
            unchecked-value="disabled"
          >
            <template #checked>{{ t('metrics.status.enabled') }}</template>
            <template #unchecked>{{ t('metrics.status.disabled') }}</template>
          </n-switch>
        </n-form-item>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="showTemplateModal = false">{{ t('metrics.btn.cancel') }}</n-button>
          <n-button type="primary" :loading="savingTpl" @click="submitTemplate">{{ t('metrics.btn.save') }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- ========== LIFE-2：指标模板禁用/删除前的受影响规则披露弹窗 ========== -->
    <n-modal
      v-model:show="affectedModalVisible"
      preset="card"
      :title="t('metrics.life2.affectedTitle')"
      :closable="false"
      style="width: 780px; max-width: 94vw; max-height: 88vh;"
      :mask-closable="false"
    >
      <div class="affected-body">
        <n-alert type="warning" :show-icon="true" class="affected-alert">
          <template #default>
            <span class="affected-alert-name">{{ affectedData?.templateName }}</span>
            <span class="affected-alert-count">（{{ affectedData?.total }}）</span>
          </template>
        </n-alert>

        <!-- 进入条件（ORM 路径） -->
        <template v-if="affectedData && affectedData.entryConditions.length">
          <div class="affected-group-title">{{ t('metrics.life2.entryGroup') }}</div>
          <n-table :single-line="false" size="small" class="affected-table">
            <thead>
              <tr>
                <th>{{ t('metrics.life2.colProcess') }}</th>
                <th>{{ t('metrics.life2.colStage') }}</th>
                <th>{{ t('metrics.life2.colRule') }}</th>
                <th>{{ t('metrics.life2.colCondition') }}</th>
                <th>{{ t('metrics.life2.colStatus') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in affectedData.entryConditions" :key="'ec-' + item.itemId">
                <td>{{ item.processName }}</td>
                <td>{{ item.stageName }}</td>
                <td>{{ item.ruleName }}</td>
                <td>{{ formatCondition(item.operator, item.value) }}</td>
                <td>
                  <n-tag size="small" :type="item.ruleStatus === 'ENABLED' ? 'success' : 'default'">
                    {{ item.ruleStatus === 'ENABLED' ? t('metrics.status.enabled') : t('metrics.status.disabled') }}
                  </n-tag>
                </td>
              </tr>
            </tbody>
          </n-table>
        </template>

        <!-- 自动跳过（JSON 路径） -->
        <template v-if="skipRules.length">
          <div class="affected-group-title">{{ t('metrics.life2.skipGroup') }}</div>
          <n-table :single-line="false" size="small" class="affected-table">
            <thead>
              <tr>
                <th>{{ t('metrics.life2.colProcess') }}</th>
                <th>{{ t('metrics.life2.colStage') }}</th>
                <th>{{ t('metrics.life2.colRule') }}</th>
                <th>{{ t('metrics.life2.colCondition') }}</th>
                <th>{{ t('metrics.life2.colStatus') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in skipRules" :key="'sr-' + item.stageRuleId + '-' + item.itemId">
                <td>{{ item.processName }}</td>
                <td>{{ item.stageName }}</td>
                <td>{{ item.ruleName }}</td>
                <td>{{ formatCondition(item.operator, item.value) }}</td>
                <td>
                  <n-tag size="small" :type="item.ruleEnabled ? 'success' : 'default'">
                    {{ item.ruleEnabled ? t('metrics.status.enabled') : t('metrics.status.disabled') }}
                  </n-tag>
                </td>
              </tr>
            </tbody>
          </n-table>
        </template>

        <!-- 自动归档（JSON 路径） -->
        <template v-if="archiveRules.length">
          <div class="affected-group-title">{{ t('metrics.life2.archiveGroup') }}</div>
          <n-table :single-line="false" size="small" class="affected-table">
            <thead>
              <tr>
                <th>{{ t('metrics.life2.colProcess') }}</th>
                <th>{{ t('metrics.life2.colStage') }}</th>
                <th>{{ t('metrics.life2.colRule') }}</th>
                <th>{{ t('metrics.life2.colCondition') }}</th>
                <th>{{ t('metrics.life2.colStatus') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in archiveRules" :key="'ar-' + item.stageRuleId + '-' + item.itemId">
                <td>{{ item.processName }}</td>
                <td>{{ item.stageName }}</td>
                <td>{{ item.ruleName }}</td>
                <td>{{ formatCondition(item.operator, item.value) }}</td>
                <td>
                  <n-tag size="small" :type="item.ruleEnabled ? 'success' : 'default'">
                    {{ item.ruleEnabled ? t('metrics.status.enabled') : t('metrics.status.disabled') }}
                  </n-tag>
                </td>
              </tr>
            </tbody>
          </n-table>
        </template>

        <!-- 指标规则（LIFE-1 R3，JSON 路径：conditions[].templateId） -->
        <template v-if="metricRuleRefs.length">
          <div class="affected-group-title">{{ t('metrics.life2.metricRuleGroup') }}</div>
          <n-table :single-line="false" size="small" class="affected-table">
            <thead>
              <tr>
                <th>{{ t('metrics.life2.colRule') }}</th>
                <th>{{ t('metrics.life2.colScene') }}</th>
                <th>{{ t('metrics.life2.colCondition') }}</th>
                <th>{{ t('metrics.life2.colAction') }}</th>
                <th>{{ t('metrics.life2.colStatus') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in metricRuleRefs" :key="'mr-' + item.ruleId">
                <td>{{ item.ruleName }}</td>
                <td>{{ metricRuleSceneLabel(item.ruleScene) }}</td>
                <td>{{ formatCondition(item.operator, item.value) }}</td>
                <td>{{ metricRuleActionLabel(item.actionType) }}</td>
                <td>
                  <n-tag size="small" :type="item.ruleEnabled ? 'success' : 'default'">
                    {{ item.ruleEnabled ? t('metrics.status.enabled') : t('metrics.status.disabled') }}
                  </n-tag>
                </td>
              </tr>
            </tbody>
          </n-table>
        </template>

        <!-- 处理建议 -->
        <div class="affected-suggest-title">{{ t('metrics.life2.suggestionTitle') }}</div>
        <ul class="affected-suggest-list">
          <li>{{ t('metrics.life2.suggestion1') }}</li>
          <li>{{ t('metrics.life2.suggestion2') }}</li>
          <li>{{ t('metrics.life2.suggestion3') }}</li>
        </ul>
      </div>

      <template #footer>
        <n-space justify="end">
          <n-button :disabled="affectedChecking" @click="onAffectedCancel">
            {{ t('metrics.life2.cancel') }}
          </n-button>
          <n-button
            type="error"
            :loading="affectedChecking"
            @click="onAffectedConfirm"
          >
            {{ affectedAction === 'delete' ? t('metrics.life2.confirmDelete') : t('metrics.life2.confirmDisable') }}
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- ========== LIFE-1：指标模板版本历史抽屉 ========== -->
    <n-drawer
      v-model:show="versionHistoryVisible"
      :width="460"
      placement="right"
      :mask-closable="true"
    >
      <n-drawer-content :title="t('metrics.life1.versionHistory')" closable>
        <div v-if="versionHistoryTarget" class="verh-meta">
          <span class="verh-name">{{ versionHistoryTarget.name }}</span>
          <span class="verh-count">{{ t('metrics.life1.versionCount', { n: versionHistoryTarget.versionCount ?? 0 }) }}</span>
        </div>
        <div v-if="!versionHistoryList.length" class="verh-empty">
          <n-empty :description="t('metrics.life1.noVersions')" />
        </div>
        <div v-else class="verh-list">
          <div v-for="v in versionHistoryList" :key="v.id" class="verh-card">
            <div class="verh-card-head">
              <span class="verh-version">v{{ v.version }}</span>
              <n-tag size="small" :type="verhTagType(v.changeKind)">{{ life1ChangeKindLabel(v.changeKind) }}</n-tag>
            </div>
            <div v-if="v.changeNote" class="verh-note">{{ v.changeNote }}</div>
            <div v-if="v.changedFields && v.changedFields.length" class="verh-changed">
              <div class="verh-sub-label">{{ t('metrics.life1.detailChangedFields') }}</div>
              <n-space :size="6">
                <n-tag v-for="f in v.changedFields" :key="f" size="small" type="warning">{{ snapshotFieldLabel(f) }}</n-tag>
              </n-space>
            </div>
            <div v-else class="verh-changed verh-changed-empty">{{ t('metrics.life1.detailNoChangedFields') }}</div>
            <div class="verh-snap">
              <div class="verh-sub-label">{{ t('metrics.life1.detailSnapshot') }}</div>
              <n-descriptions :column="1" label-placement="left" bordered size="small">
                <n-descriptions-item v-for="row in snapshotRows(v.snapshot)" :key="row.key" :label="row.label">
                  {{ row.text }}
                </n-descriptions-item>
              </n-descriptions>
            </div>
            <div class="verh-foot">
              <span class="verh-time">{{ formatTime(v.createdAt) }}</span>
            </div>
            <div class="verh-actions">
              <!--
                LIFE-1 / 安全闸门：回滚是破坏性操作（会覆盖模板当前配置并 version+1），
                必须先经 n-popconfirm 显式确认，禁止一键直连执行。
              -->
              <n-popconfirm
                :disabled="rollbackLoading"
                @positive-click="confirmRollback(versionHistoryTarget!, v.version)"
              >
                <template #trigger>
                  <n-button
                    size="small"
                    type="primary"
                    secondary
                    :loading="rollbackLoading && rollbackVersionNo === v.version"
                    :disabled="rollbackLoading"
                  >
                    {{ t('metrics.life1.rollback') }}
                  </n-button>
                </template>
                {{ t('metrics.life1.rollbackConfirm', { v: v.version }) }}
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
/**
 * MetricsWorkspace —— 指标管理（原「指标库」）。
 *
 * 模块拆分（用户诉求）：
 *   - 指标管理（本页）：两个页签
 *       1) 指标定义 —— 只读统一视图（原子 + 派生合并），点击卡片弹出居中详情弹窗。
 *          原子指标与派生指标已整合进「指标定义」，故不再提供独立的新建入口（无停用/启用状态，
 *          展示系统中已注册的全部指标）；取值方式明确为「对象路径 / 参数化 Handler」，
 *          枚举型指标同时展示其出参枚举值。
 *       2) 指标模板 —— 新增/编辑/删除/停用（CRUD），可配置参数范围/步长/显示/算子/值域
 *   - 规则引擎（RuleAuthoring.vue）：承接原「规则配置与执行」「规则管理」两个功能
 *
 * 2026-09-30 交互优化：
 *   - 菜单名 / 页面标题统一为「指标管理」
 *   - 数据列表重构为数据卡片（信息层次清晰、视觉一致）
 *   - 新增关键词搜索 + 分类/状态筛选，快速定位目标指标
 *   - 移除冗余只读提示横幅，减少信息干扰
 */
import { computed, h, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  NAlert,
  NButton,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NSwitch,
  NTable,
  NTag,
  useMessage,
  useDialog,
  type DataTableColumns,
} from 'naive-ui'
import { CheckmarkOutline, SearchOutline } from '@vicons/ionicons5'
import KindIcon from '@/components/metrics/KindIcon.vue'
import OperatorBadge from '@/components/metrics/OperatorBadge.vue'
import {
  createMetricTemplate,
  deleteMetricTemplate,
  listAtomicMetrics,
  listDerivedMetrics,
  listMetricDefinitions,
  listMetricTemplates,
  listOperators,
  listCandidateFields,
  updateMetricTemplate,
  exportMetricTemplates,
  downloadTemplateTemplate,
  importMetricTemplates,
  getTemplateAffectedRules,
  listTemplateVersions,
  rollbackTemplateVersion,
  TemplateImportError,
  ACTION_TYPE_OPTIONS,
  type TemplateAffectedRules,
  type TemplateVersion,
  type TemplateImportMode,
  type AtomicMetric,
  type CandidateFieldPath,
  type DerivedMetric,
  type MetricDefinition,
  type MetricTemplate,
  type OptionItem,
} from '@/api/metrics'

const { t } = useI18n()
const message = useMessage()
const dialog = useDialog()

const activeTab = ref<'definitions' | 'template'>('definitions')

// ===== 共享数据 =====
const definitions = ref<MetricDefinition[]>([])
const templateList = ref<MetricTemplate[]>([])
// 指标模板列表客户端分页状态（后端无 keyword/status 过滤，拉全量后前端切片）
const tplPage = ref(1)
const tplPageSize = ref(20)
const atomicList = ref<AtomicMetric[]>([])
const derivedList = ref<DerivedMetric[]>([])
const operatorCatalog = ref<OptionItem[]>([])
const fieldPaths = ref<CandidateFieldPath[]>([])
const loading = ref(false)
const loadError = ref(false)

// ===== LIFE-2：指标模板禁用/删除前的受影响规则披露（事前披露 + 确认闸门） =====
const affectedModalVisible = ref(false)
const affectedData = ref<TemplateAffectedRules | null>(null)
const affectedAction = ref<'disable' | 'delete'>('delete')
const affectedTarget = ref<MetricTemplate | null>(null)
/** 受影响规则查询期间锁定对应行按钮（loading 态） */
const busyRowId = ref<string>('')
/** 确认弹窗「仍要禁用/删除」按钮的 loading 态 */
const affectedChecking = ref(false)

// ===== LIFE-1：指标模板版本历史抽屉 =====
const versionHistoryVisible = ref(false)
const versionHistoryList = ref<TemplateVersion[]>([])
const versionHistoryTarget = ref<MetricTemplate | null>(null)
const rollbackLoading = ref(false)
const rollbackVersionNo = ref<number | null>(null)

// ===== 指标详情弹窗 =====
const detailVisible = ref(false)
const detailRow = ref<MetricDefinition | null>(null)

function openDetail(row: MetricDefinition) {
  detailRow.value = row
  detailVisible.value = true
}

/**
 * 入参 / 出参 合并标签（定义表共用）。
 * 入参改为真实实体标识（候选人 / 需求 / 职位 ID），出参改为数据源末级字段 + 类型，
 * 不再用「离散 / 连续」这种抽象分类。
 */
function inOutLabel(row: MetricDefinition): string {
  return `${inputEntityLabel(row)} / ${outputFieldLabel(row)}`
}

/** 入参实体：从数据源路径前缀推导真实实体，指标如同 API——入参即被查询的实体标识。 */
function inputEntityLabel(row: MetricDefinition): string {
  const ds = (row.dataSource || '') as string
  const prefix = ds.split('.')[0].toLowerCase()
  if (prefix === 'candidate') return t('metrics.detail.inputEntity.candidate')
  if (prefix === 'demand') return t('metrics.detail.inputEntity.demand')
  if (prefix === 'position') return t('metrics.detail.inputEntity.position')
  return t('metrics.detail.inputEntity.global')
}

/** 出参字段：数据源末级字段名 + 出参类型（数值 / 字符串 / 布尔 / 日期）。 */
function outputFieldLabel(row: MetricDefinition): string {
  const ds = (row.dataSource || '') as string
  const field = ds.includes('.') ? ds.slice(ds.lastIndexOf('.') + 1) : ''
  const type = returnTypeLabel(row.returnType)
  return field ? `${field} · ${type}` : type
}
function kindLabel(row: MetricDefinition): string {
  return row.kind === 'derived' ? t('metrics.tab.derived') : t('metrics.tab.atomic')
}
function kindClass(row: MetricDefinition): string {
  return row.kind === 'derived' ? 'is-derived' : 'is-atomic'
}
function enumValuesOf(row: MetricDefinition): string[] {
  return (row.enumValues as string[] | undefined) || []
}

/** 来源模块 key：按实体前缀 / 派生归类，描述指标数据的来源子系统（方案 B）。 */
function sourceModuleKey(row: MetricDefinition): string {
  if (row.kind === 'derived') return 'derived'
  const prefix = (row.dataSource || '').split('.')[0].toLowerCase()
  if (prefix === 'candidate') return 'candidate'
  if (prefix === 'demand') return 'demand'
  if (prefix === 'position') return 'position'
  return 'other'
}
function sourceModuleLabel(row: MetricDefinition): string {
  return t(`metrics.module.${sourceModuleKey(row)}`)
}
function returnTypeLabel(type?: string): string {
  const map: Record<string, string> = {
    number: t('pages.settings.MetricsWorkspace.s7'),
    string: t('pages.settings.MetricsWorkspace.s8'),
    boolean: t('pages.settings.MetricsWorkspace.s9'),
    date: t('pages.settings.MetricsWorkspace.s10'),
  }
  return (type && map[type]) || type || '-'
}
function paramTypeLabel(type?: string): string {
  if (type === 'continuous') return t('metrics.paramType.continuous')
  if (type === 'discrete') return t('metrics.paramType.discrete')
  return '-'
}
/** paramSchema 字段类型 → 中文（定义弹窗只读契约展示用）。 */
function paramSchemaTypeLabel(type?: string): string {
  const map: Record<string, string> = {
    number: t('metrics.detail.paramTypeNumber'),
    select: t('metrics.detail.paramTypeSelect'),
    boolean: t('metrics.detail.paramTypeBoolean'),
    string: t('metrics.detail.paramTypeString'),
  }
  return (type && map[type]) || type || '-'
}
function operatorLabel(value: string) {
  return operatorCatalog.value.find((o) => o.value === value)?.label ?? value
}

// ===== 指标定义：搜索 + 分类筛选 =====
const defKeyword = ref('')
const defKind = ref<'all' | 'atomic' | 'derived'>('all')

const defKindOptions = computed<OptionItem[]>(() => [
  { label: t('metrics.filter.all'), value: 'all' },
  { label: t('metrics.tab.atomic'), value: 'atomic' },
  { label: t('metrics.tab.derived'), value: 'derived' },
])

const defModule = ref<'all' | 'candidate' | 'demand' | 'position' | 'derived' | 'other'>('all')

const defModuleOptions = computed<OptionItem[]>(() => [
  { label: t('metrics.filter.all'), value: 'all' },
  { label: t('metrics.module.candidate'), value: 'candidate' },
  { label: t('metrics.module.demand'), value: 'demand' },
  { label: t('metrics.module.position'), value: 'position' },
  { label: t('metrics.module.derived'), value: 'derived' },
  { label: t('metrics.module.other'), value: 'other' },
])

const filteredDefinitions = computed<MetricDefinition[]>(() => {
  const kw = defKeyword.value.trim().toLowerCase()
  return definitions.value.filter((d) => {
    if (defKind.value !== 'all' && d.kind !== defKind.value) return false
    if (defModule.value !== 'all' && sourceModuleKey(d) !== defModule.value) return false
    if (kw) {
      const hay = [
        d.name,
        d.dataSource,
        returnTypeLabel(d.returnType),
        paramTypeLabel(d.paramType),
        kindLabel(d),
        d.valueMode,
        (d.supportedOperators || []).map((o) => operatorLabel(o)).join(' '),
      ].join(' ').toLowerCase()
      if (!hay.includes(kw)) return false
    }
    return true
  })
})

/** M-3：空态细分——首用 / 搜索无果 / 筛选无果，避免误导 HR 反复调关键词（R-111 强制） */
const defEmptyKind = computed<'first' | 'search' | 'filter'>(() => {
  if (definitions.value.length === 0) return 'first'
  if (defKeyword.value.trim()) return 'search'
  if (defKind.value !== 'all' || defModule.value !== 'all') return 'filter'
  return 'first'
})

function clearDefFilters() {
  defKeyword.value = ''
  defKind.value = 'all'
  defModule.value = 'all'
  defPage.value = 1
}

/** 指标定义列表客户端分页状态 */
const defPage = ref(1)
const defPageSize = ref(20)

/** 对过滤后的指标定义做客户端切片分页 */
const pagedDefinitions = computed<MetricDefinition[]>(() => {
  // M-1 钳制：filtered 列表变短（切 Tab / 关键词 / 分类筛选）后，若仍停在第 N 页，
  // start 会超出列表长度 → 空白表格且无提示。钳到最后一页有效起点。
  const maxStart = Math.max(0, filteredDefinitions.value.length - defPageSize.value)
  const start = Math.min((defPage.value - 1) * defPageSize.value, maxStart)
  return filteredDefinitions.value.slice(start, start + defPageSize.value)
})

/** 搜索关键词 / 分类筛选变化时重置到第 1 页 */
watch([defKeyword, defKind], () => {
  defPage.value = 1
})

// ===== 指标模板：搜索 + 状态筛选 =====
const tplKeyword = ref('')
const tplStatus = ref<'all' | 'enabled' | 'disabled'>('all')

const tplStatusOptions = computed<OptionItem[]>(() => [
  { label: t('metrics.filter.all'), value: 'all' },
  { label: t('metrics.status.enabled'), value: 'enabled' },
  { label: t('metrics.status.disabled'), value: 'disabled' },
])

// ===== 指标模板导入 / 导出 / 下载模板 =====
const importMode = ref<TemplateImportMode>('skip')
const importing = ref(false)
const exporting = ref(false)
const downloadingTemplate = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

/** 导入弹窗：可见性 + 暂存的待导入文件 */
const importModalVisible = ref(false)
const importFile = ref<File | null>(null)
/** 弹窗内反馈区：异常明细 */
const importModalErrors = ref<string[]>([])
/** 弹窗内反馈区：错误报告（base64 xlsx），有值时展示「下载错误报告」按钮 */
const importErrorFile = ref<string | null>(null)
/** 弹窗内反馈区：成功三计数（新建 / 更新 / 跳过） */
const importSuccessInfo = ref<{ created: number; updated: number; skipped: number } | null>(null)

const importModeOptions = computed<OptionItem[]>(() => [
  { label: t('metrics.templateIo.mode.skip'), value: 'skip' },
  { label: t('metrics.templateIo.mode.update'), value: 'update' },
  { label: t('metrics.templateIo.mode.error'), value: 'error' },
])

/** Blob 下载（导出 / 下载模板 / 错误报告通用） */
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/**
 * base64（xlsx）转 Blob 并下载（导入失败错误报告）。
 * 成功返回 true；失败返回 false，由调用方决定呈现方式（此处由导入弹窗反馈区承接）。
 */
function downloadBase64(base64: string, filename: string): boolean {
  try {
    const byteChars = atob(base64)
    const byteNumbers = new Array(byteChars.length)
    for (let i = 0; i < byteChars.length; i++) byteNumbers[i] = byteChars.charCodeAt(i)
    const blob = new Blob([new Uint8Array(byteNumbers)], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    downloadBlob(blob, filename)
    return true
  } catch {
    return false
  }
}

async function onDownloadTemplateTemplate() {
  downloadingTemplate.value = true
  importModalErrors.value = []
  importSuccessInfo.value = null
  try {
    const blob = await downloadTemplateTemplate('xlsx')
    downloadBlob(blob, 'metrics_templates_template.xlsx')
  } catch {
    // 异常反馈收敛到导入弹窗内，不再走全局 toast
    importModalErrors.value = [t('metrics.templateIo.downloadFailed')]
  } finally {
    downloadingTemplate.value = false
  }
}

async function onExportTemplates() {
  exporting.value = true
  try {
    const blob = await exportMetricTemplates('xlsx')
    downloadBlob(blob, 'metrics_templates_export.xlsx')
  } catch {
    message.error(t('metrics.templateIo.importFailed'))
  } finally {
    exporting.value = false
  }
}

/** 打开导入弹窗（先清空上一轮的反馈与暂存文件） */
function openImportModal() {
  resetImportModal()
  importModalVisible.value = true
}

/** 清空弹窗内的暂存文件与反馈区（关闭时 / 再次打开时均会调用，幂等） */
function resetImportModal() {
  importFile.value = null
  importModalErrors.value = []
  importErrorFile.value = null
  importSuccessInfo.value = null
  const input = fileInputRef.value
  if (input) input.value = ''
}

/** 触发弹窗内隐藏的 file input */
function onPickFile() {
  fileInputRef.value?.click()
}

/** 选择文件：仅暂存到 importFile，不自动上传 —— 由用户点「开始导入」执行 */
function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  // 复位，保证同一文件可重复选择触发 change
  input.value = ''
  if (!file) return
  importFile.value = file
  importModalErrors.value = []
  importErrorFile.value = null
  importSuccessInfo.value = null
}

/** 下载导入错误报告（失败信息同样写入弹窗反馈区） */
function onDownloadErrorFile() {
  if (!importErrorFile.value) return
  const ok = downloadBase64(importErrorFile.value, 'metrics_templates_import_errors.xlsx')
  if (!ok) {
    importModalErrors.value = [...importModalErrors.value, t('metrics.templateIo.downloadErrorFileFailed')]
  }
}

/** 执行导入：结果/异常全部呈现在弹窗反馈区，不使用全局 toast */
async function doImport() {
  const file = importFile.value
  if (!file || importing.value) return
  importing.value = true
  importModalErrors.value = []
  importErrorFile.value = null
  importSuccessInfo.value = null
  try {
    const result = await importMetricTemplates(file, importMode.value)
    importSuccessInfo.value = {
      created: result.created,
      updated: result.updated,
      skipped: result.skipped,
    }
    // 导入成功后清空已选文件（含原生 input），使「开始导入」自动置灰，杜绝重复导入
    importFile.value = null
    if (fileInputRef.value) fileInputRef.value.value = ''
    await load()
  } catch (err: any) {
    if (err instanceof TemplateImportError && err.report) {
      const { errors, errorFile } = err.report
      importModalErrors.value =
        errors && errors.length ? errors : [t('metrics.templateIo.importFailed')]
      if (errorFile) importErrorFile.value = errorFile
    } else {
      importModalErrors.value = [t('metrics.templateIo.importFailed')]
    }
  } finally {
    importing.value = false
  }
}

/** M-6：update 模式为覆盖式导入（按名称覆盖已存在模板并递增版本号），须二次确认防止误覆盖 */
function onStartImport() {
  if (importMode.value === 'update' && importFile.value) {
    dialog.warning({
      title: t('metrics.templateIo.updateConfirmTitle'),
      content: t('metrics.templateIo.updateConfirmContent'),
      positiveText: t('metrics.btn.confirm'),
      negativeText: t('metrics.btn.cancel'),
      onPositiveClick: () => {
        void doImport()
      },
    })
    return
  }
  void doImport()
}

const filteredTemplates = computed<MetricTemplate[]>(() => {
  const kw = tplKeyword.value.trim().toLowerCase()
  return templateList.value.filter((tpl) => {
    if (tplStatus.value !== 'all' && tpl.status !== tplStatus.value) return false
    if (kw) {
      const hay = [
        tpl.name,
        tpl.metricName,
        (tpl.operators || []).map((o) => operatorLabel(o)).join(' '),
      ].join(' ').toLowerCase()
      if (!hay.includes(kw)) return false
    }
    return true
  })
})

/** M-3：模板空态清空筛选 action */
function clearTplFilters() {
  tplKeyword.value = ''
  tplStatus.value = 'all'
  tplPage.value = 1
}

/** 对过滤后的结果做客户端切片分页（后端无 keyword/status 过滤，拉全量后前端分页） */
const pagedTemplates = computed<MetricTemplate[]>(() => {
  // M-1 钳制：同 pagedDefinitions，防止列表变短后停在第 N 页显示空白表格。
  const maxStart = Math.max(0, filteredTemplates.value.length - tplPageSize.value)
  const start = Math.min((tplPage.value - 1) * tplPageSize.value, maxStart)
  return filteredTemplates.value.slice(start, start + tplPageSize.value)
})

/** 搜索关键词 / 状态筛选变化时重置到第 1 页 */
watch([tplKeyword, tplStatus], () => {
  tplPage.value = 1
})
watch([defKeyword, defKind, defModule], () => {
  defPage.value = 1
})

// ===== 指标模板列辅助 =====
function templateRange(row: MetricTemplate): string {
  const c = row.paramConfig
  if (!c || (c.min == null && c.max == null && c.step == null)) return '-'
  const parts: string[] = []
  if (c.min != null) parts.push(`min=${c.min}`)
  if (c.max != null) parts.push(`max=${c.max}`)
  if (c.step != null) parts.push(`step=${c.step}`)
  return parts.join(' / ')
}
function templateDomain(row: MetricTemplate): string {
  const segs = row.valueDomain?.segments
  if (!segs || !segs.length) return '-'
  return segs.map((s) => `${s.min}~${s.max}`).join('，')
}

// ===== 指标定义表（n-data-table）列定义 =====
const defColumns = computed<DataTableColumns<MetricDefinition>>(() => [
  {
    title: t('metrics.col.name'),
    key: 'name',
    minWidth: 150,
    render: (row) => h('span', { class: 'ws-cell-name' }, row.name),
  },
  {
    title: t('metrics.col.type'),
    key: 'kind',
    width: 72,
    render: (row) => h(KindIcon, { kind: row.kind, size: 18 }),
  },
  {
    title: t('metrics.col.sourceModule'),
    key: 'sourceModule',
    width: 140,
    render: (row) => h('span', { class: 'ws-module-tag' }, sourceModuleLabel(row)),
  },
  {
    title: t('metrics.col.inOutType'),
    key: 'inOut',
    minWidth: 220,
    render: (row) =>
      h('span', { class: 'ws-inout-cell' }, [
        h('span', { class: 'ws-inout-part' }, inputEntityLabel(row)),
        h('span', { class: 'ws-inout-sep' }, ' / '),
        h('span', { class: 'ws-inout-part' }, outputFieldLabel(row)),
      ]),
  },
  {
    title: t('metrics.col.operatorCount'),
    key: 'operators',
    width: 96,
    render: (row) => h(OperatorBadge, { value: row.supportedOperators, catalog: operatorCatalog.value }),
  },
  {
    title: t('metrics.col.action'),
    key: 'action',
    width: 72,
    render: (row) =>
      h(
        NButton,
        { size: 'small', quaternary: true, onClick: (e: MouseEvent) => { e.stopPropagation(); openDetail(row) } },
        { default: () => t('metrics.btn.view') },
      ),
  },
])

function defRowProps(row: MetricDefinition) {
  return {
    style: 'cursor:pointer',
    onClick: () => openDetail(row),
    onKeydown: (e: KeyboardEvent) => {
      if (e.key === 'Enter') openDetail(row)
    },
  }
}

// ===== 指标模板表（n-data-table，保留 CRUD 操作列）列定义 =====
const tplColumns = computed<DataTableColumns<MetricTemplate>>(() => [
  {
    title: t('metrics.col.name'),
    key: 'name',
    minWidth: 160,
    render: (row) => h('span', { class: 'ws-cell-name' }, row.name),
  },
  {
    title: t('metrics.col.metric'),
    key: 'metric',
    minWidth: 200,
    render: (row) =>
      h('span', { class: 'ws-metric-cell' }, [
        h(KindIcon, { kind: row.metricKind ?? 'atomic', size: 18 }),
        ' ',
        row.metricName ?? '-',
      ]),
  },
  {
    title: t('metrics.tpl.outputType'),
    key: 'dataType',
    width: 150,
    render: (row) =>
      h('span', row.dataType ? `${returnTypeLabel(row.dataType)}${row.unit ? ` (${row.unit})` : ''}` : '-'),
  },
  {
    title: t('metrics.col.operatorCount'),
    key: 'operators',
    width: 110,
    render: (row) => h(OperatorBadge, { value: row.operators, catalog: operatorCatalog.value }),
  },
  {
    title: t('metrics.col.status'),
    key: 'status',
    width: 90,
    render: (row) =>
      h(
        NTag,
        { size: 'small', type: row.status === 'enabled' ? 'success' : 'default' },
        { default: () => (row.status === 'enabled' ? t('metrics.status.enabled') : t('metrics.status.disabled')) },
      ),
  },
  {
    title: t('metrics.life1.versionColumn'),
    key: 'version',
    width: 80,
    // 列头「版本」= 当前版本号（v1/v2/…），与抽屉内的 v{{ v.version }} 保持同一语义；
    // 历史总条数（versionCount）放 title 提示，避免 HR 把「条数」误读成「版本号」。
    render: (row) =>
      h(
        'span',
        { title: t('metrics.life1.versionCount', { n: row.versionCount ?? 0 }) },
        row.version ? `v${row.version}` : '-',
      ),
  },
  {
    title: t('metrics.col.action'),
    key: 'action',
    width: 320,
    render: (row) =>
      h('div', { class: 'ws-row-actions' }, [
        h(NButton, { size: 'small', quaternary: true, onClick: () => openTemplateEdit(row) }, { default: () => t('metrics.btn.edit') }),
        h(
          NButton,
          { size: 'small', quaternary: true, loading: busyRowId.value === row.id, onClick: () => toggleTemplate(row) },
          { default: () => (row.status === 'enabled' ? t('metrics.btn.disable') : t('metrics.btn.enable')) },
        ),
        h(
          NButton,
          { size: 'small', quaternary: true, type: 'error', loading: busyRowId.value === row.id, onClick: () => removeTemplate(row) },
          { default: () => t('metrics.btn.delete') },
        ),
        h(
          NButton,
          { size: 'small', quaternary: true, onClick: () => openVersionHistory(row) },
          { default: () => t('metrics.life1.versionHistory') },
        ),
      ]),
  },
])

// ===== 指标模板新建/编辑 =====
const showTemplateModal = ref(false)
const templateEditId = ref('')
const savingTpl = ref(false)
const emptyTplForm = () => ({
  name: '',
  metricDefinition: null as string | null,
  operators: [] as string[],
  unit: '',
  calcParams: {} as Record<string, any>,
  paramConfig: { min: null, max: null, step: null, prefix: '', suffix: '', allOption: false },
  valueDomain: { segments: [] as any[] },
  paramEnums: [] as string[],
  paramAllowNull: false,
  description: '',
  status: 'enabled',
})
const tplForm = ref<any>(emptyTplForm())

const templateModalTitle = computed(() =>
  templateEditId.value ? t('metrics.dialog.editTemplate') : t('metrics.dialog.createTemplate'),
)

const metricDefinitionOptions = computed<any[]>(() => {
  const atomic = definitions.value.filter((d) => d.kind === 'atomic')
  const derived = definitions.value.filter((d) => d.kind === 'derived')
  const toOption = (d: MetricDefinition) => ({
    label: `${d.name}（${d.dataSource}）`,
    value: `${d.kind}:${d.id}`,
  })
  const groups: any[] = []
  if (atomic.length) {
    groups.push({
      type: 'group',
      label: t('metrics.tab.atomic'),
      key: 'atomic',
      children: atomic.map(toOption),
    })
  }
  if (derived.length) {
    groups.push({
      type: 'group',
      label: t('metrics.tab.derived'),
      key: 'derived',
      children: derived.map(toOption),
    })
  }
  return groups
})

const selectedTemplateDefinition = computed<MetricDefinition | undefined>(() => {
  const key = tplForm.value.metricDefinition
  if (!key) return undefined
  const [kind, id] = String(key).split(':')
  return definitions.value.find((d) => d.kind === kind && d.id === id)
})

const showTemplateParamConfig = computed<boolean>(() => {
  const d = selectedTemplateDefinition.value
  if (!d) return false
  if (d.valueMode !== 'parametric_handler') return false
  // 派生函数注册表声明了参数才展示参数配置
  return d.isParametric !== false
})

const paramPrecision = computed<number>(() => {
  const d = selectedTemplateDefinition.value
  return d?.paramType === 'continuous' ? 2 : 0
})

const paramConfigHint = computed(() => {
  const d = selectedTemplateDefinition.value
  return d?.paramType === 'continuous'
    ? t('metrics.tpl.paramHint')
    : t('metrics.tpl.paramHintDiscrete')
})

function generateValues(min?: number | null, max?: number | null, step?: number | null): number[] {
  if (min == null || max == null || step == null || step <= 0) return []
  const vals: number[] = []
  for (let v = min; v <= max + 1e-9; v += step) {
    vals.push(Number(v.toFixed(6)))
  }
  return vals
}

function formatPreviewValue(n: number): string {
  return Number(n.toFixed(6)).toString()
}

const paramPreviewValues = computed<string[]>(() => {
  const c = tplForm.value.paramConfig
  return generateValues(c.min, c.max, c.step).map(formatPreviewValue)
})

const supportedOperatorOptions = computed<OptionItem[]>(() => {
  const d = selectedTemplateDefinition.value
  if (!d?.supportedOperators?.length) return []
  const allowed = new Set(d.supportedOperators)
  return operatorCatalog.value.filter((o) => allowed.has(o.value))
})

function toggleOperator(value: string) {
  const set = new Set(tplForm.value.operators)
  if (set.has(value)) set.delete(value)
  else set.add(value)
  tplForm.value.operators = Array.from(set)
}

function segmentPreviewValues(seg: any): string[] {
  return generateValues(seg?.min, seg?.max, seg?.step).map(formatPreviewValue)
}

function onTemplateMetricChange() {
  const d = selectedTemplateDefinition.value
  // 切换指标后重置算子为当前指标支持的全部算子（全启）
  if (d?.supportedOperators?.length) {
    tplForm.value.operators = [...d.supportedOperators]
  } else {
    tplForm.value.operators = []
  }
  // 对象路径指标无需参数，切回 handler 时清空旧参数避免误解
  if (!showTemplateParamConfig.value) {
    tplForm.value.paramConfig = { min: null, max: null, step: null, prefix: '', suffix: '', allOption: false }
    tplForm.value.calcParams = {}
  } else if (selectedTemplateDefinition.value?.paramSchema?.length) {
    // 预填 paramSchema default，便于业务人员改
    for (const p of selectedTemplateDefinition.value.paramSchema) {
      if (tplForm.value.calcParams[p.key] === undefined && p.default !== undefined) {
        tplForm.value.calcParams[p.key] = p.default
      }
    }
  }
}

function openTemplateCreate() {
  templateEditId.value = ''
  tplForm.value = emptyTplForm()
  showTemplateModal.value = true
}

function openTemplateEdit(row: MetricTemplate) {
  templateEditId.value = row.id
  const cfg = row.paramConfig || {}
  const domain = row.valueDomain || {}
  const metricKey = row.metricKind && (row.atomicMetric || row.derivedMetric)
    ? `${row.metricKind}:${row.atomicMetric || row.derivedMetric}`
    : null
  tplForm.value = {
    name: row.name,
    metricDefinition: metricKey,
    operators: row.operators || [],
    unit: row.unit || '',
    calcParams: { ...(row.calcParams || {}) },
    paramConfig: {
      min: cfg.min ?? null,
      max: cfg.max ?? null,
      step: cfg.step ?? null,
      prefix: cfg.prefix ?? '',
      suffix: cfg.suffix ?? '',
      allOption: !!cfg.allOption,
    },
    valueDomain: { segments: (domain.segments || []).map((s: any) => ({ ...s })) },
    paramEnums: row.paramEnums || [],
    paramAllowNull: !!row.paramAllowNull,
    description: row.description || '',
    status: row.status || 'enabled',
  }
  showTemplateModal.value = true
}

function addSegment() {
  tplForm.value.valueDomain.segments.push({ min: null, max: null, step: null, label: '' })
}
function removeSegment(idx: number) {
  tplForm.value.valueDomain.segments.splice(idx, 1)
}

async function submitTemplate() {
  if (!tplForm.value.name?.trim()) {
    message.warning(t('metrics.msg.requiredName'))
    return
  }
  if (!tplForm.value.metricDefinition) {
    message.warning(t('metrics.msg.selectOneMetric'))
    return
  }
  const [kind, id] = String(tplForm.value.metricDefinition).split(':')
  if (!kind || !id) {
    message.warning(t('metrics.msg.selectOneMetric'))
    return
  }
  if (!tplForm.value.operators?.length) {
    message.warning(t('metrics.msg.requiredOperators'))
    return
  }
  savingTpl.value = true
  try {
    const payload = {
      name: tplForm.value.name,
      atomicMetric: kind === 'atomic' ? id : null,
      derivedMetric: kind === 'derived' ? id : null,
      operators: tplForm.value.operators,
      unit: tplForm.value.unit,
      calcParams: tplForm.value.calcParams,
      paramConfig: tplForm.value.paramConfig,
      valueDomain: tplForm.value.valueDomain,
      paramEnums: tplForm.value.paramEnums,
      paramAllowNull: tplForm.value.paramAllowNull,
      description: tplForm.value.description,
      status: tplForm.value.status || 'enabled',
    }
    if (templateEditId.value) {
      await updateMetricTemplate(templateEditId.value, payload)
    } else {
      await createMetricTemplate(payload)
    }
    message.success(templateEditId.value ? t('metrics.msg.updated') : t('metrics.msg.created'))
    showTemplateModal.value = false
    templateEditId.value = ''
    await load()
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.saveFailed'))
  } finally {
    savingTpl.value = false
  }
}

async function removeTemplate(row: MetricTemplate) {
  // LIFE-2 事前披露：删除前枚举受影响规则。total>0 弹窗确认；total===0 维持原有直接删除 + Toast 撤销流程。
  busyRowId.value = row.id
  try {
    const impact = await getTemplateAffectedRules(row.id)
    if (impact.total > 0) {
      affectedAction.value = 'delete'
      affectedTarget.value = row
      affectedData.value = impact
      affectedModalVisible.value = true
      return
    }
  } catch {
    // 接口异常不阻断删除（回退为直接执行，避免误伤正常流程）
  } finally {
    busyRowId.value = ''
  }
  await executeDeleteTemplate(row)
}

/** 删除模板 + 成功 Toast（含 8s 撤销 action），保留原 restorePayload 撤销逻辑 */
async function executeDeleteTemplate(row: MetricTemplate) {
  // 中等破坏性操作：直接执行 + Toast 撤销（停留 8s），符合 AGENTS.md R-106
  const restorePayload = {
    name: row.name,
    atomicMetric: row.atomicMetric || null,
    derivedMetric: row.derivedMetric || null,
    operators: row.operators || [],
    paramConfig: row.paramConfig || { min: null, max: null, step: null, prefix: '', suffix: '', allOption: false },
    valueDomain: row.valueDomain || { segments: [] },
    paramEnums: row.paramEnums || [],
    paramAllowNull: !!row.paramAllowNull,
    description: row.description || '',
    status: row.status || 'enabled',
  }
  try {
    await deleteMetricTemplate(row.id)
    await load()
    message.success(t('metrics.life1.deletedWithVersions', { name: row.name, n: row.versionCount ?? 0 }), {
      duration: 8000,
      action: {
        label: t('metrics.btn.undo'),
        onClick: async () => {
          try {
            await createMetricTemplate(restorePayload)
            message.warning(t('metrics.msg.restoredNew'))
            await load()
          } catch (err: any) {
            const detail = err?.response?.data?.error
            message.error(detail ? String(detail) : t('metrics.msg.saveFailed'))
          }
        },
      },
    })
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.deleteFailed'))
  }
}

async function toggleTemplate(row: MetricTemplate) {
  const next = row.status === 'enabled' ? 'disabled' : 'enabled'
  if (next === 'disabled') {
    // LIFE-2 事前披露：仅「禁用」需弹窗；重新启用不弹窗（启用不会破坏引用，EXP-5 会恢复）
    busyRowId.value = row.id
    try {
      const impact = await getTemplateAffectedRules(row.id)
      if (impact.total > 0) {
        affectedAction.value = 'disable'
        affectedTarget.value = row
        affectedData.value = impact
        affectedModalVisible.value = true
        return
      }
    } catch {
      // 接口异常不阻断禁用（回退为直接执行）
    } finally {
      busyRowId.value = ''
    }
    await executeDisableTemplate(row)
  } else {
    // 重新启用：不弹窗，直接执行
    await executeEnableTemplate(row)
  }
}

/** 禁用模板 + 成功 Toast */
async function executeDisableTemplate(row: MetricTemplate) {
  try {
    await updateMetricTemplate(row.id, { status: 'disabled' })
    message.success(t('metrics.msg.disabled'))
    await load()
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.saveFailed'))
  }
}

/** 重新启用模板 + 成功 Toast */
async function executeEnableTemplate(row: MetricTemplate) {
  try {
    await updateMetricTemplate(row.id, { status: 'enabled' })
    message.success(t('metrics.msg.enabled'))
    await load()
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.saveFailed'))
  }
}

// ===== LIFE-2 弹窗交互 =====

/** 跳过 / 归档规则按 ruleType 分组（分别展示） */
const skipRules = computed(() =>
  (affectedData.value?.stageRules ?? []).filter((r) => r.ruleType === 'skip'),
)
const archiveRules = computed(() =>
  (affectedData.value?.stageRules ?? []).filter((r) => r.ruleType === 'archive'),
)

/**
 * LIFE-1 R3：指标规则引用项（后端 conditions[].templateId 路径）。
 * 用 `?? []` 兜底，兼容尚未升级 / 缓存的旧后端响应（该字段缺失时不应让披露弹窗报错）。
 */
const metricRuleRefs = computed(() => affectedData.value?.metricRules ?? [])

/** 指标规则应用场景 → 可读文案（复用 metrics.scene.* 键） */
function metricRuleSceneLabel(scene: string): string {
  return t(`metrics.scene.${scene}` as any)
}

/**
 * 指标规则动作类型 → 可读文案。
 * 复用 ACTION_TYPE_OPTIONS 的 value→labelKey 映射（VETO→metrics.rule.action.veto），
 * 不做字符串插值下标换算，避免大小写拼不上导致 i18n 回退成裸 key；未知值原样返回。
 */
function metricRuleActionLabel(actionType: string): string {
  const hit = ACTION_TYPE_OPTIONS.find((o) => o.value === actionType)
  return hit ? t(hit.labelKey as any) : actionType
}

/** 把运算符 + 值拼成可读文本（如 `EQ: 10`） */
function formatCondition(operator: string, value: any): string {
  if (value === null || value === undefined || value === '') {
    return String(operator)
  }
  const text = typeof value === 'object' ? JSON.stringify(value) : String(value)
  return `${operator}: ${text}`
}

// ===== LIFE-1：版本历史抽屉交互 =====
function life1ChangeKindLabel(kind: string): string {
  const map: Record<string, string> = {
    create: t('metrics.life1.changeKind.create'),
    update: t('metrics.life1.changeKind.update'),
    rollback: t('metrics.life1.changeKind.rollback'),
    import: t('metrics.life1.changeKind.import'),
  }
  return map[kind] ?? kind
}

function verhTagType(kind: string): 'success' | 'info' | 'warning' | 'error' | 'default' {
  if (kind === 'create') return 'success'
  if (kind === 'rollback') return 'warning'
  if (kind === 'import') return 'info'
  return 'default'
}

function formatTime(iso?: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function openVersionHistory(row: MetricTemplate) {
  versionHistoryTarget.value = row
  versionHistoryVisible.value = true
  versionHistoryList.value = []
  try {
    versionHistoryList.value = await listTemplateVersions(row.id)
  } catch {
    message.error(t('metrics.msg.loadFailed'))
  }
}

async function confirmRollback(row: MetricTemplate, versionNo: number) {
  rollbackLoading.value = true
  rollbackVersionNo.value = versionNo
  try {
    await rollbackTemplateVersion(row.id, versionNo)
    message.success(t('metrics.life1.rollbackSuccess', { v: versionNo }))
    await load()
    versionHistoryList.value = await listTemplateVersions(row.id)
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : t('metrics.msg.saveFailed'))
  } finally {
    rollbackLoading.value = false
    rollbackVersionNo.value = null
  }
}

/** 快照字段 → i18n 键 映射（仅展示业务可读字段，跳过内部 FK id） */
const SNAP_FIELD_I18N: Record<string, string> = {
  name: 'metrics.life1.field.name',
  metric_name: 'metrics.life1.field.metric',
  data_type: 'metrics.life1.field.dataType',
  unit: 'metrics.life1.field.unit',
  operators: 'metrics.life1.field.operators',
  param_config: 'metrics.life1.field.paramConfig',
  value_domain: 'metrics.life1.field.valueDomain',
  param_enums: 'metrics.life1.field.paramEnums',
  param_allow_null: 'metrics.life1.field.paramAllowNull',
  status: 'metrics.life1.field.status',
  description: 'metrics.life1.field.description',
}
function snapshotFieldLabel(key: string): string {
  const i18nKey = SNAP_FIELD_I18N[key]
  return i18nKey ? t(i18nKey) : key
}
function fmtParamConfig(c: any): string {
  if (!c || (c.min == null && c.max == null && c.step == null && !c.prefix && !c.suffix && !c.allOption)) return '-'
  const parts: string[] = []
  if (c.min != null) parts.push(`min=${c.min}`)
  if (c.max != null) parts.push(`max=${c.max}`)
  if (c.step != null) parts.push(`step=${c.step}`)
  if (c.prefix) parts.push(`前缀「${c.prefix}」`)
  if (c.suffix) parts.push(`后缀「${c.suffix}」`)
  if (c.allOption) parts.push('含「全部」选项')
  return parts.join(' / ') || '-'
}
function fmtValueDomain(vd: any): string {
  const segs = vd?.segments
  if (!segs || !segs.length) return '-'
  return segs.map((s: any) => `${s.min ?? '*'}~${s.max ?? '*'}`).join('，')
}
function snapshotRows(snap: Record<string, any> | undefined): { key: string; label: string; text: string }[] {
  if (!snap) return []
  const rows: { key: string; label: string; text: string }[] = []
  const push = (k: string, text: string) => {
    const label = snapshotFieldLabel(k)
    rows.push({ key: k, label, text: text === '' || text === null || text === undefined ? '-' : String(text) })
  }
  if ('name' in snap) push('name', snap.name)
  if ('metric_name' in snap) {
    const kind = snap.metric_kind === 'derived' ? t('metrics.life1.field.metricDerived') : t('metrics.life1.field.metricAtomic')
    push('metric_name', `${snap.metric_name ?? '-'}${snap.metric_path ? `（${snap.metric_path}）` : ''} · ${kind}`)
  }
  if ('data_type' in snap) push('data_type', snap.data_type ? `${returnTypeLabel(snap.data_type)}${snap.unit ? ` (${snap.unit})` : ''}` : '-')
  if ('unit' in snap && !('data_type' in snap)) push('unit', snap.unit)
  if ('operators' in snap) push('operators', (snap.operators || []).map((o: string) => operatorLabel(o)).join('、') || '-')
  if ('param_config' in snap) push('param_config', fmtParamConfig(snap.param_config))
  if ('value_domain' in snap) push('value_domain', fmtValueDomain(snap.value_domain))
  if ('param_enums' in snap) push('param_enums', (snap.param_enums || []).join('、') || '-')
  if ('param_allow_null' in snap) push('param_allow_null', snap.param_allow_null ? t('metrics.life1.field.yes') : t('metrics.life1.field.no'))
  if ('status' in snap) push('status', snap.status === 'enabled' ? t('metrics.status.enabled') : t('metrics.status.disabled'))
  if ('description' in snap) push('description', snap.description || '-')
  return rows
}

/** 确认执行（仍要禁用 / 仍要删除） */
async function onAffectedConfirm() {
  const row = affectedTarget.value
  affectedModalVisible.value = false
  affectedTarget.value = null
  affectedData.value = null
  if (!row) return
  affectedChecking.value = true
  try {
    if (affectedAction.value === 'delete') {
      await executeDeleteTemplate(row)
    } else {
      await executeDisableTemplate(row)
    }
  } finally {
    affectedChecking.value = false
  }
}

/** 取消：关闭弹窗，不执行任何操作 */
function onAffectedCancel() {
  affectedModalVisible.value = false
  affectedTarget.value = null
  affectedData.value = null
}

// ===== 主加载 =====
async function load() {
  loading.value = true
  loadError.value = false
  try {
    const [atomic, derived, templates, ops, defs] = await Promise.all([
      listAtomicMetrics(),
      listDerivedMetrics(),
      listMetricTemplates(),
      listOperators(),
      listMetricDefinitions(),
    ])
    atomicList.value = atomic
    derivedList.value = derived
    templateList.value = templates.list
    operatorCatalog.value = ops
    definitions.value = defs
    if (tplPage.value > Math.max(1, Math.ceil(filteredTemplates.value.length / tplPageSize.value))) {
      tplPage.value = 1
    }
    if (defPage.value > Math.max(1, Math.ceil(filteredDefinitions.value.length / defPageSize.value))) {
      defPage.value = 1
    }
    try {
      fieldPaths.value = await listCandidateFields()
    } catch {
      fieldPaths.value = []
    }
  } catch {
    loadError.value = true
    message.error(t('metrics.msg.loadFailed'))
  } finally {
    loading.value = false
  }
}

// ===== 兜底：用 JS 计算表格可用高度，避免 CSS flex 链在各种场景下塌缩导致数据不显示 =====
const tableMaxHeight = ref(480)
function updateTableMaxHeight() {
  const wrap = document.querySelector('.metrics-ws .ws-table-wrap') as HTMLElement | null
  if (wrap) {
    const top = wrap.getBoundingClientRect().top
    tableMaxHeight.value = Math.max(240, window.innerHeight - top - 24)
  } else {
    tableMaxHeight.value = Math.max(240, window.innerHeight - 240)
  }
}

onMounted(() => {
  load()
  updateTableMaxHeight()
  window.addEventListener('resize', updateTableMaxHeight)
})
onUnmounted(() => {
  window.removeEventListener('resize', updateTableMaxHeight)
})
</script>

<style scoped>
.metrics-ws {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.ws-title {
  margin: 0;
  font-size: var(--text-h3, 20px);
  font-weight: 600;
  color: var(--ink);
}
.ws-subtitle {
  margin: 4px 0 0;
  font-size: var(--text-small, 13px);
  color: var(--ink-faint);
}
/* ===== LIFE-2 受影响规则披露弹窗 ===== */
.affected-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.affected-alert-name {
  font-weight: 600;
}
.affected-alert-count {
  opacity: 0.8;
}
.affected-group-title {
  margin-top: 4px;
  font-size: var(--text-small, 13px);
  font-weight: 600;
  color: var(--ink);
}
.affected-table :deep(td),
.affected-table :deep(th) {
  padding: 6px 10px;
  font-size: var(--text-small, 13px);
  vertical-align: middle;
}
.affected-suggest-title {
  margin-top: 4px;
  font-size: var(--text-small, 13px);
  font-weight: 600;
  color: var(--ink);
}
.affected-suggest-list {
  margin: 0;
  padding-left: 18px;
  color: var(--ink-faint);
  font-size: var(--text-small, 13px);
  line-height: 1.7;
}
.ws-body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
/* 让 n-tabs 占满 ws-body，tab pane 成为 flex 列，滚动职责下放到表格区
   铁律：全程用 flex:1;min-height:0，禁止 height:100%（依赖父级确定高度、在 flex 链里会塌缩） */
.metrics-ws {
  gap: 0 !important;
}
.metrics-ws :deep(.n-tabs) {
  display: flex !important;
  flex-direction: column !important;
  flex: 1 1 auto !important;
  min-height: 0 !important;
}
.metrics-ws :deep(.n-tab-pane) {
  display: flex !important;
  flex-direction: column !important;
  flex: 1 1 auto !important;
  min-height: 0 !important;
}
.ws-tab-header {
  flex-shrink: 0;
}
.ws-table-wrap {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
  position: relative;
}
.ws-spin {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  width: 100%;
}
.ws-spin :deep(.n-spin-content) {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
}

/* ===== 工具栏：搜索 + 筛选 + 计数 ===== */
.ws-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}
.ws-toolbar-grow { flex: 1 1 auto; margin-bottom: 0; }
.ws-search { flex: 1 1 260px; max-width: 420px; }
.ws-filter { flex: 0 0 160px; }
.ws-pager-count {
  margin-right: var(--space-2);
  color: var(--ink-faint);
  font-size: var(--fs-12);
  white-space: nowrap;
}
.ws-tab-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}
.ws-io-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.ws-hidden-file { display: none; }

/* ===== 数据表（替代卡片网格） ===== */
.ws-table {
  width: 100%;
}
.ws-cell-name {
  font-weight: 600;
  color: var(--ink);
}
.ws-inout-cell {
  display: inline-flex;
  align-items: baseline;
  gap: 2px;
  flex-wrap: wrap;
}
.ws-inout-part {
  white-space: nowrap;
}
.ws-inout-sep {
  color: var(--ink-faint);
  white-space: nowrap;
}
.ws-module-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: var(--radius-pill);
  background: var(--g1);
  border: 1px solid var(--border-hairline);
  font-size: var(--fs-12);
  color: var(--ink);
  white-space: nowrap;
}
.ws-metric-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.ws-row-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-wrap: nowrap;
}

/* 空态：在表格滚动区内撑满剩余高度 */
.ws-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1 1 auto;
  min-height: 240px;
  padding: var(--space-8) 0;
}

/* ===== 共享视觉元素（详情弹窗与卡片统一） ===== */
.ws-code {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--g1);
  border: 1px solid var(--border-hairline);
  color: var(--ink);
  word-break: break-all;
}
.ws-op-tag {
  font-size: var(--fs-12);
  padding: 1px 8px;
  border-radius: var(--radius-pill);
  background: var(--brand-a12);
  border: 1px solid var(--brand-a22);
  color: var(--brand-text);
  white-space: nowrap;
}
.ws-enum-tag {
  font-size: var(--fs-12);
  padding: 1px 8px;
  border-radius: var(--radius-pill);
  background: var(--c-success-soft);
  border: 1px solid color-mix(in srgb, var(--c-success) 24%, transparent);
  color: var(--c-success-deep);
  white-space: nowrap;
}
.ws-ops { display: flex; flex-wrap: wrap; gap: var(--space-1); }
.ws-muted { color: var(--ink-faint); font-size: var(--text-small, 13px); }

/* 详情弹窗（redesign 2026-10-03）：技术规格书式布局 */
.dm-hero {
  position: relative;
  padding: var(--space-5);
  margin-bottom: var(--space-4);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--brand-a12), transparent 72%);
  border: 1px solid var(--brand-a22);
  overflow: hidden;
  animation: wb-fade-up var(--duration-slow) var(--ease-out) both;
}
.dm-eyebrow {
  display: block;
  font-size: var(--fs-12);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--brand-text);
  font-weight: 600;
  margin-bottom: var(--space-3);
}
.dm-hero-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.dm-kind-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--radius-pill);
  font-size: var(--text-base, 15px);
  font-weight: 600;
  background: var(--surface);
  border: 1px solid var(--border-hairline);
}
.dm-kind-badge.is-atomic { color: var(--brand); border-color: color-mix(in srgb, var(--brand) 30%, transparent); }
.dm-kind-badge.is-derived { color: var(--brand-grad-a); border-color: color-mix(in srgb, var(--brand-grad-a) 30%, transparent); }
.dm-meta-chip {
  display: inline-flex;
  align-items: baseline;
  gap: var(--space-2);
  padding: 6px 14px;
  border-radius: var(--radius-pill);
  background: var(--g1);
  border: 1px solid var(--border-hairline);
}
.dm-meta-k { color: var(--ink-faint); font-size: var(--fs-12); }
.dm-meta-v { color: var(--ink); font-size: var(--text-base, 15px); font-weight: 600; }

.dm-section {
  position: relative;
  padding: var(--space-4);
  padding-left: calc(var(--space-4) + 10px);
  margin-bottom: var(--space-3);
  background: var(--surface);
  border: 1px solid var(--border-hairline);
  border-left: 3px solid var(--brand);
  border-radius: var(--radius-md);
  transition: border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out);
  animation: wb-fade-up var(--duration-slow) var(--ease-out) both;
}
.dm-section:hover {
  border-color: color-mix(in srgb, var(--brand) 30%, transparent);
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
}
.dm-params { border-left-color: var(--c-warning); }
.dm-params:hover { border-color: color-mix(in srgb, var(--c-warning) 45%, transparent); }
.dm-section-label {
  color: var(--ink-faint);
  font-size: var(--fs-12);
  font-weight: 600;
  letter-spacing: 0.02em;
  margin-bottom: var(--space-2);
}
.dm-source {
  display: inline-block;
  max-width: 100%;
  font-size: var(--fs-13, 13px);
}
.dm-desc {
  margin: 0;
  color: var(--ink);
  font-size: var(--text-small, 13px);
  line-height: 1.6;
}

/* 详情弹窗：参数化 Handler 的参数编辑区 */
.detail-params-block { display: flex; flex-direction: column; gap: var(--space-3); }
.detail-params-form { display: flex; flex-direction: column; gap: var(--space-2); }
.detail-param-row { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.param-label { min-width: 96px; color: var(--ink-strong); font-size: var(--fs-13, 13px); font-weight: 500; }
.param-input { width: 220px; max-width: 100%; }
.param-hint { color: var(--ink-faint); font-size: var(--fs-12); line-height: 1.4; }

/* 详情弹窗：只读输入参数契约 */
.detail-params-readonly { display: flex; flex-direction: column; gap: var(--space-2); }
.param-meta { color: var(--ink-soft); font-size: var(--fs-12); }
.dm-hint { color: var(--ink-faint); font-size: var(--fs-12); margin-top: var(--space-2); }

/* 模板弹窗：计算参数子块（实际取值） */
.tpl-subblock { border-top: 1px dashed var(--border-hairline); margin-top: var(--space-3); padding-top: var(--space-3); }
.tpl-subblock-title { font-weight: 600; color: var(--ink-strong); font-size: var(--text-small, 13px); margin-bottom: var(--space-1); }
.tpl-subblock-hint { color: var(--ink-faint); font-size: var(--fs-12); margin: 0 0 var(--space-3); line-height: 1.5; }
.tpl-calc-params { display: flex; flex-direction: column; gap: var(--space-2); }
.tpl-calc-row { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.tpl-unit-field { margin-bottom: var(--space-4); }

/* 模板弹窗分段 */
.tpl-form { padding-right: 2px; }
.tpl-section { width: 100%; }
.tpl-row { display: flex; gap: var(--space-3); flex-wrap: wrap; margin-bottom: var(--space-1); align-items: flex-end; }
.tpl-field { flex: 1 1 0; min-width: 140px; margin-bottom: var(--space-1); }
.tpl-segments { display: flex; flex-direction: column; gap: var(--space-2); }
.seg-row { display: flex; gap: var(--space-2); align-items: center; flex-wrap: wrap; }
.seg-field { flex: 1 1 120px; }

/* 指标模板弹窗新样式 */
.tpl-output-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  margin-bottom: var(--space-4);
  background: var(--c-info-soft);
  border: 1px solid color-mix(in srgb, var(--c-info) 20%, transparent);
  border-radius: var(--radius-md);
  font-size: var(--text-small, 13px);
}
.tpl-output-label { color: var(--ink-soft); font-weight: 500; }
.tpl-output-unit { color: var(--ink); font-weight: 600; }
.tpl-output-hint { margin-left: auto; color: var(--ink-faint); }

.tpl-section-card {
  background: var(--surface);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.tpl-section-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  flex-wrap: wrap;
}
.tpl-section-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--c-warning);
  color: #fff;
  font-size: var(--fs-12);
  font-weight: 700;
}
.tpl-section-title { font-weight: 600; color: var(--ink); }
.tpl-section-hint { margin-left: auto; color: var(--ink-faint); font-size: var(--fs-12); }
.tpl-section-body { display: flex; flex-direction: column; gap: var(--space-2); }
.tpl-range-sep { color: var(--ink-faint); padding-bottom: 8px; }
.tpl-switch-field :deep(.n-form-item-label) { height: auto; }

.tpl-preview {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  background: var(--c-info-soft);
  border-radius: var(--radius-md);
  color: var(--c-info-deep);
  font-size: var(--fs-12);
  line-height: 1.6;
}
.tpl-preview-tag { font-weight: 500; white-space: nowrap; }
.tpl-info-text {
  color: var(--ink-faint);
  font-size: var(--text-small, 13px);
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-4);
  background: var(--g1);
  border-radius: var(--radius-md);
}

.tpl-operator-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.tpl-op-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border-hairline);
  background: var(--surface);
  color: var(--ink-soft);
  font-size: var(--fs-12);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out);
}
.tpl-op-chip:hover { border-color: var(--c-success); }
.tpl-op-chip.is-checked {
  background: var(--c-success-soft);
  border-color: color-mix(in srgb, var(--c-success) 30%, transparent);
  color: var(--c-success-deep);
}
.tpl-op-chip input { position: absolute; opacity: 0; width: 0; height: 0; }

.tpl-segment-block { display: flex; flex-direction: column; gap: var(--space-2); }
.tpl-segment-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.tpl-segment-label { color: var(--ink-faint); font-size: var(--fs-12); min-width: 36px; }
.tpl-seg-field { width: 100px; }
.tpl-unit-text { color: var(--ink-faint); font-size: var(--fs-12); }
.tpl-step-field { width: 120px; margin-bottom: 0; }
.tpl-step-field :deep(.n-form-item-label) { font-size: var(--fs-12); }

/* LIFE-1 版本历史抽屉 */
.verh-meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.verh-name { font-weight: 600; color: var(--ink); }
.verh-count { color: var(--ink-faint); font-size: var(--fs-12); white-space: nowrap; }
.verh-empty { padding: var(--space-8) 0; display: flex; justify-content: center; }
.verh-list { display: flex; flex-direction: column; gap: var(--space-3); }
.verh-card {
  padding: var(--space-3) var(--space-4);
  background: var(--surface);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}
.verh-card-head { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.verh-version { font-weight: 600; color: var(--ink); }
.verh-note { color: var(--ink-soft); font-size: var(--fs-12); line-height: 1.5; margin-bottom: var(--space-2); }
.verh-foot { margin-bottom: var(--space-2); }
.verh-time { color: var(--ink-faint); font-size: var(--fs-12); }
.verh-actions { display: flex; justify-content: flex-end; }
.verh-sub-label {
  color: var(--ink-faint);
  font-size: var(--fs-12);
  font-weight: 600;
  letter-spacing: 0.02em;
  margin-bottom: var(--space-2);
}
.verh-changed { margin-bottom: var(--space-3); }
.verh-changed-empty { color: var(--ink-faint); font-size: var(--fs-12); }
.verh-snap { margin-bottom: var(--space-3); }

/* 指标模板列表 / 指标定义列表分页控件 */
.ws-pager {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  padding: var(--space-3) 0 0;
}

/* ===== 导入弹窗（下载模板 + 选择文件 + 导入 + 异常反馈一体化） ===== */
.im-body { display: flex; flex-direction: column; gap: var(--space-3); }
.im-row { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.im-label { color: var(--ink-soft); font-size: var(--fs-13); flex-shrink: 0; }
.im-select { flex: 1 1 200px; max-width: 260px; }
.im-hint { color: var(--ink-faint); font-size: var(--fs-12); line-height: 1.5; flex: 1 1 auto; }
.im-divider { height: 1px; background: var(--border-hairline); }
.im-file {
  color: var(--ink);
  font-size: var(--fs-13);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 320px;
}
.im-file-empty { color: var(--ink-faint); }
.im-feedback { margin-top: var(--space-1); }
.im-alert :deep(.n-alert-body) { align-items: flex-start; }
.im-err-title { font-size: var(--fs-13); color: var(--ink-strong); }
.im-err-list {
  margin: var(--space-1) 0 0;
  padding-left: var(--space-4);
  color: var(--ink-soft);
  font-size: var(--fs-12);
  line-height: 1.6;
}
.im-dl-btn { margin-top: var(--space-2); }
.im-footer { display: flex; justify-content: flex-end; gap: var(--space-2); }

@media (max-width: 768px) {
  .tpl-section-hint { margin-left: 0; width: 100%; }
  .tpl-output-hint { margin-left: 0; width: 100%; }
}
</style>
