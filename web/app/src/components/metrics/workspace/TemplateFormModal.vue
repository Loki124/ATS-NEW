<template>
  <n-modal
    v-model:show="showTemplateModal"
    preset="card"
    :closable="false"
    class="tpl-modal"
    :mask-closable="false"
    :close-on-esc="!savingTpl"
    :style="{ width: 'min(920px, calc(100vw - 48px))', height: 'min(88vh, 860px)' }"
  >
    <template #header>
      <div class="tpl-head">
        <span class="tpl-monogram"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v16a2 2 0 0 0 2 2h16" /><path d="m7 16 4-8 4 4 5-9" /></svg></span>
        <div class="tpl-head-main">
          <div class="tpl-head-title">
            {{ templateModalTitle }}
            <n-tag v-if="templateEditId" size="tiny" type="primary" round>{{ t('metrics.tpl.modeEdit') }}</n-tag>
            <!-- 编号：系统自动生成，只读展示 -->
            <n-tag v-if="tplForm.code" size="tiny" round class="tpl-code-tag">{{ tplForm.code }}</n-tag>
          </div>
        </div>
        <button
          type="button"
          class="tpl-close"
          :title="t('metrics.tpl.close')"
          :aria-label="t('metrics.tpl.close')"
          :disabled="savingTpl"
          @click="showTemplateModal = false"
        >
          <n-icon :component="CloseOutline" :size="18" />
        </button>
      </div>
    </template>

    <n-form :model="tplForm" label-placement="top" class="tpl-form">
      <!-- 01 基础信息 -->
      <section class="tpl-sec">
        <div class="tpl-sec-head"><span class="tpl-sec-title">{{ t('metrics.tpl.baseTitle') }}</span></div>
        <div class="tpl-fields">
          <n-form-item :label="t('metrics.form.name')" required>
            <n-input v-model:value="tplForm.name" :placeholder="t('metrics.form.name')" />
          </n-form-item>
          <n-form-item :label="t('metrics.tpl.templateDesc')">
            <n-input v-model:value="tplForm.description" :placeholder="t('metrics.tpl.templateDesc')" />
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
          <n-form-item :label="t('metrics.form.status')" class="tpl-status">
            <n-switch v-model:value="tplForm.status" checked-value="enabled" unchecked-value="disabled">
              <template #checked>{{ t('metrics.status.enabled') }}</template>
              <template #unchecked>{{ t('metrics.status.disabled') }}</template>
            </n-switch>
          </n-form-item>
        </div>
        <div v-if="selectedTemplateDefinition" class="tpl-inherit">
          <span class="tpl-inherit-k">{{ t('metrics.tpl.outputParam') }}</span>
          <span class="tpl-inherit-v">{{ returnTypeLabel(selectedTemplateDefinition.returnType) }}</span>
          <span class="tpl-inherit-sep">·</span>
          <span class="tpl-inherit-k">{{ t('metrics.tpl.outputUnit') }}</span>
          <template v-if="outputUnitOptions.length > 1">
            <button
              v-for="u in outputUnitOptions"
              :key="u"
              type="button"
              class="tpl-pill"
              :class="{ 'is-on': tplForm.unit === u }"
              @click="setUnit(u)"
            >
              {{ u }}
            </button>
          </template>
          <span v-else class="tpl-inherit-v tpl-inherit-strong">{{ tplForm.unit || outputUnitOptions[0] || t('metrics.tpl.noUnit') }}</span>
          <span class="tpl-inherit-sep">/</span>
          <span class="tpl-inherit-k">{{ t('metrics.tpl.valueModeLabel') }}</span>
          <span class="tpl-inherit-v">{{ valueModeLabel }}</span>
        </div>
      </section>

      <!-- 02 参数配置 -->
      <section v-if="showTemplateParamConfig" class="tpl-sec">
        <div class="tpl-sec-head">
          <span class="tpl-sec-title">{{ t('metrics.tpl.paramConfigTitle') }}</span>
          <n-tag size="tiny" :type="selectedTemplateDefinition?.paramType === 'continuous' ? 'success' : 'warning'" round>{{ paramTypeLabel(selectedTemplateDefinition?.paramType) }}</n-tag>
          <n-tag v-if="currentParamUnit" size="tiny" type="info" round class="tpl-sec-unit">{{ currentParamUnit }}</n-tag>
          <span v-if="paramUnitOptions.length > 1" class="tpl-sec-units">
            <button v-for="u in paramUnitOptions" :key="u" type="button" class="tpl-pill" :class="{ 'is-on': tplForm.paramUnit === u }" @click="setPunit(u)">
              {{ u }}
            </button>
          </span>
        </div>
        <div class="tpl-param-block">
          <div class="tpl-param-grid">
            <div class="tpl-param-field">
              <span class="tpl-param-lbl">{{ t('metrics.tpl.range') }}</span>
              <div class="tpl-param-ctl">
                <n-input-number v-model:value="tplForm.paramConfig.min" :precision="paramConfigPrecision" :show-button="false" class="tpl-range-num" />
                <span class="tpl-range-sep">~</span>
                <n-input-number v-model:value="tplForm.paramConfig.max" :precision="paramConfigPrecision" :show-button="false" class="tpl-range-num" />
              </div>
            </div>
            <div class="tpl-param-field">
              <span class="tpl-param-lbl">{{ t('metrics.tpl.step') }}</span>
              <div class="tpl-param-ctl">
                <n-input-number v-model:value="tplForm.paramConfig.step" :min="0" :precision="paramConfigPrecision" :show-button="false" class="tpl-range-num" />
              </div>
            </div>
            <div class="tpl-param-field">
              <span class="tpl-param-lbl">{{ t('metrics.tpl.display') }}</span>
              <div class="tpl-param-ctl">
                <n-input v-model:value="tplForm.paramConfig.prefix" placeholder="前缀" class="tpl-mini" />
                <span class="tpl-range-static">值</span>
                <n-input v-model:value="tplForm.paramConfig.suffix" placeholder="后缀" class="tpl-mini" />
              </div>
            </div>
            <div class="tpl-param-field tpl-all-field">
              <label class="tpl-param-head">
                <span class="tpl-param-lbl">{{ t('metrics.tpl.allOption') }}</span>
                <n-checkbox v-model:checked="tplForm.paramConfig.allOption" />
              </label>
              <n-input v-model:value="tplForm.paramConfig.allText" :disabled="!tplForm.paramConfig.allOption" placeholder="全部工作经历" class="tpl-alltext" />
            </div>
          </div>
          <div v-if="paramSampleItems.length" class="domain-summary">
            <span class="ds-tag">共 {{ paramSampleItems.length }} 个值</span>
            <span class="ds-vals">{{ paramSampleItems.join(', ') }}</span>
          </div>
        </div>
      </section>

      <!-- 03 启用运算符 -->
      <section class="tpl-sec">
        <div class="tpl-sec-head">
          <span class="tpl-sec-title">{{ t('metrics.tpl.operatorTitle') }}</span>
          <span v-if="supportedOperatorOptions.length" class="tpl-sec-count">{{ tplForm.operators.length }}/{{ supportedOperatorOptions.length }}</span>
        </div>
        <div class="tpl-ops-block">
          <div v-if="supportedOperatorOptions.length" class="tpl-ops">
            <label
              v-for="op in supportedOperatorOptions"
              :key="op.value"
              class="tpl-op"
              :class="{ 'is-on': tplForm.operators.includes(op.value), 'is-disabled': operatorDisabledForFreetext(op.value) }"
              :title="operatorDisabledForFreetext(op.value) ? t('metrics.tpl.freetextNoSetOperatorHint') : undefined"
            >
              <input
                type="checkbox"
                :value="op.value"
                :checked="tplForm.operators.includes(op.value)"
                @change="toggleOperator(op.value)"
              />
              <span v-if="opSymbol(op.value)" class="tpl-op-sym">{{ opSymbol(op.value) }}</span>
              <span class="tpl-op-lbl">{{ op.label }}</span>
            </label>
          </div>
          <div v-else class="tpl-info-text">{{ t('metrics.tpl.noMetricSelected') }}</div>
        </div>
      </section>

      <!-- 04 值域配置（自由文本是无穷域，没有值域可言，整块不渲染） -->
      <section v-if="showValueDomain" class="tpl-sec">
        <div class="tpl-sec-head"><span class="tpl-sec-title">{{ t('metrics.tpl.domainTitle') }}</span></div>
        <div class="tpl-domain-block">
          <!-- 旧版把日期值域按数值 min/max 存过（如 1~3），在新口径下无意义 → 提示重配 -->
          <div v-if="legacyNumericDomainOnDate" class="domain-error">
            <n-icon :component="AlertCircleOutline" :size="14" aria-hidden="true" />
            <span>{{ t('metrics.tpl.legacyNumericDomain') }}</span>
          </div>
          <div class="tpl-segments">
            <!-- 🔴 实体引用型值域（人员 / 部门）：与数值型分段/枚举型候选**同一套语义**——
                 模板层只限定「可选范围」（候选清单），具体选哪个由应用方在使用时决定。
                 旧设计把取值方式做成模板层单选，会导致应用时无法切换 → 已改为候选清单。 -->
            <template v-if="isEntityOutput">
              <div class="tpl-entity-block">
                <label class="tpl-seg-lbl">{{ t('metrics.tpl.entityCandidatesLabel') }}</label>
                <!-- 已配置的候选清单 -->
                <div v-for="(opt, idx) in entityOptions" :key="idx" class="tpl-entity-opt-row">
                  <span class="tpl-seg-tag">{{ t('metrics.tpl.entitySegmentTag', { n: idx + 1 }) }}</span>
                  <span class="tpl-entity-opt-type">{{ entityTypeLabel(opt.type) }}</span>
                  <n-select
                    v-if="entityTypeNeedsPicker(opt.type)"
                    :value="entityRowPickerValue(idx)"
                    multiple
                    filterable
                    clearable
                    :options="entityRowPickerOptions(idx)"
                    :placeholder="t('metrics.tpl.entityPickerPlaceholder')"
                    :loading="entityOptionsLoading"
                    class="tpl-entity-picker"
                    @update:value="(v: string[]) => handleEntityRowPickerUpdate(idx, v)"
                  />
                  <span v-else class="tpl-entity-opt-auto">{{ opt.label }}</span>
                  <n-button size="tiny" quaternary circle type="error" class="tpl-seg-del" :title="t('metrics.btn.delete')" @click="removeEntityOption(idx)">
                    <template #icon><n-icon :component="CloseOutline" /></template>
                  </n-button>
                </div>
                <!-- 新增候选：默认收起（点「+ 添加候选」展开草稿行，确认/取消后收起复位）；
                     取值方式总共只有 3 种、每种只能配一条 → 配齐后入口直接隐藏；
                     先选取值方式，指定类再选具体对象；当前登录人无需选对象 -->
                <n-button
                  v-if="!entityDraftVisible && !entityTypesExhausted"
                  size="small"
                  dashed
                  class="tpl-add-seg"
                  @click="showEntityDraft"
                >
                  <template #icon><n-icon :component="AddOutline" /></template>
                  {{ t('metrics.tpl.entityAddOption') }}
                </n-button>
                <p v-else-if="!entityDraftVisible && entityTypesExhausted" class="tpl-hint">
                  <n-icon :component="InformationCircleOutline" :size="14" aria-hidden="true" />
                  <span>{{ t('metrics.tpl.entityTypesExhausted') }}</span>
                </p>
                <template v-else>
                  <div class="tpl-entity-add-row">
                    <n-select
                      v-model:value="entityDraft.type"
                      :options="entityUnusedSelectorOptions"
                      :placeholder="t('metrics.tpl.entitySelectorPlaceholder')"
                      :disabled="entityOptionsLoading"
                      class="tpl-entity-draft-type"
                    />
                    <n-select
                      v-if="entityTypeNeedsPicker(entityDraft.type)"
                      :value="entityDraftPickerValue"
                      multiple
                      filterable
                      clearable
                      :options="entityDraftPickerOptionsAll"
                      :placeholder="t('metrics.tpl.entityPickerPlaceholder')"
                      :loading="entityOptionsLoading"
                      class="tpl-entity-picker"
                      @update:value="(v: string[]) => handleEntityDraftPickerUpdate(v)"
                    />
                    <span v-else class="tpl-entity-opt-auto">{{ t(entityAutoLabelKey(entityDraft.type)) }}</span>
                    <n-button size="small" quaternary @click="cancelEntityDraft">{{ t('metrics.btn.cancel') }}</n-button>
                    <n-button size="small" type="primary" @click="confirmEntityDraft">{{ t('metrics.btn.confirm') }}</n-button>
                  </div>
                  <p v-if="entityDraftError" class="tpl-field-error">
                    <n-icon :component="AlertCircleOutline" :size="14" aria-hidden="true" />
                    <span>{{ entityDraftError }}</span>
                  </p>
                </template>
                <p v-if="entityDomainIssue" class="tpl-field-error">
                  <n-icon :component="AlertCircleOutline" :size="14" aria-hidden="true" />
                  <span>{{ entityDomainIssue }}</span>
                </p>
                <p v-else class="tpl-hint">{{ t('metrics.tpl.entityHint') }}</p>
                <!-- 候选值汇总（与数值型「共 N 个值」一致） -->
                <div v-if="!entityDomainIssue && domainValueCount" class="domain-summary">
                  <span class="ds-tag">{{ domainSummaryTag }}</span>
                  <span class="ds-vals">{{ domainSummaryText }}</span>
                </div>
              </div>
            </template>
            <!-- 枚举型出参：值域 = 候选值清单。data_type 仍是 string，靠 isEnum 分流。 -->
            <template v-else-if="isEnumOutput">
              <div class="tpl-enum-block">
                <label class="tpl-seg-lbl" for="tpl-enum-candidates">{{ t('metrics.tpl.enumCandidateLabel') }}</label>
                <n-select
                  id="tpl-enum-candidates"
                  v-model:value="tplForm.paramEnums"
                  multiple
                  filterable
                  tag
                  :options="enumCandidateOptions"
                  :placeholder="t('metrics.tpl.enumCandidatePlaceholder')"
                  :status="enumCandidateIssue ? 'error' : undefined"
                  class="tpl-enum-select"
                />
                <p v-if="enumCandidateIssue" class="tpl-field-error">
                  <n-icon :component="AlertCircleOutline" :size="14" aria-hidden="true" />
                  <span>{{ enumCandidateIssue }}</span>
                </p>
                <p v-else class="tpl-hint">{{ t('metrics.tpl.enumCandidateHint') }}</p>
              </div>
            </template>
            <!-- 日期型出参：值域 = 日期区间约束（起止边界 + 步进粒度），不是数值刻度 -->
            <template v-else-if="isDateOutput">
              <div
                v-for="(seg, idx) in tplForm.valueDomain.segments"
                :key="idx"
                class="tpl-seg-card"
                :class="{ 'is-invalid': !!domainSegmentIssues[idx] }"
              >
                <div class="tpl-seg-card-head">
                  <span class="tpl-seg-tag">段{{ idx + 1 }}</span>
                  <span class="tpl-seg-gran">{{ t('metrics.tpl.granularity') }} {{ currentOutputUnit }}</span>
                  <n-button size="tiny" quaternary circle type="error" class="tpl-seg-del" :title="t('metrics.btn.delete')" @click="removeSegment(idx)">
                    <template #icon><n-icon :component="CloseOutline" /></template>
                  </n-button>
                </div>
                <div class="tpl-seg-card-row">
                  <span class="tpl-seg-lbl">{{ t('metrics.tpl.dateFrom') }}</span>
                  <n-select v-model:value="seg.from.type" :options="dateBoundTypeOptions" class="tpl-bound-type" />
                  <n-date-picker
                    v-if="seg.from.type === 'absolute'"
                    v-model:formatted-value="seg.from.date"
                    :type="datePickerType"
                    :value-format="dateValueFormat"
                    class="tpl-bound-date"
                  />
                  <template v-else>
                    <n-input-number v-model:value="seg.from.n" :precision="0" :show-button="false" class="tpl-bound-num" />
                    <n-select v-model:value="seg.from.unit" :options="dateUnitOptions" class="tpl-bound-unit" />
                  </template>
                  <span class="tpl-range-sep">~</span>
                  <span class="tpl-seg-lbl">{{ t('metrics.tpl.dateTo') }}</span>
                  <n-select v-model:value="seg.to.type" :options="dateBoundTypeOptions" class="tpl-bound-type" />
                  <n-date-picker
                    v-if="seg.to.type === 'absolute'"
                    v-model:formatted-value="seg.to.date"
                    :type="datePickerType"
                    :value-format="dateValueFormat"
                    class="tpl-bound-date"
                  />
                  <template v-else>
                    <n-input-number v-model:value="seg.to.n" :precision="0" :show-button="false" class="tpl-bound-num" />
                    <n-select v-model:value="seg.to.unit" :options="dateUnitOptions" class="tpl-bound-unit" />
                  </template>
                </div>
                <div class="tpl-seg-card-row">
                  <span class="tpl-seg-lbl">{{ t('metrics.tpl.step') }}</span>
                  <n-input-number v-model:value="seg.step" :min="1" :precision="0" :show-button="false" class="tpl-seg-num" />
                  <n-select v-model:value="seg.stepUnit" :options="dateUnitOptions" class="tpl-bound-unit" />
                  <span class="tpl-seg-boundtext">{{ dateBoundText(seg.from) }} ~ {{ dateBoundText(seg.to) }}</span>
                </div>
              </div>
            </template>
            <!-- 数值 / 布尔型出参：值域 = 数值分段（min / max / 步长） -->
            <template v-else-if="isNumberOutput">
              <div v-for="(seg, idx) in tplForm.valueDomain.segments" :key="idx" class="tpl-seg-row" :class="{ 'is-invalid': !!domainSegmentIssues[idx] }">
                <span class="tpl-seg-tag">段{{ idx + 1 }}</span>
                <n-input-number v-model:value="seg.min" :precision="0" :show-button="false" class="tpl-seg-num" placeholder="0" />
                <span class="tpl-range-sep">~</span>
                <n-input-number v-model:value="seg.max" :precision="0" :show-button="false" class="tpl-seg-num" placeholder="上限" />
                <span class="tpl-unit-text">{{ tplForm.unit || selectedTemplateDefinition?.unit }}</span>
                <span class="tpl-seg-steplbl">{{ t('metrics.tpl.step') }}</span>
                <n-input-number v-model:value="seg.step" :min="0" :precision="paramPrecision" :show-button="false" class="tpl-seg-num tpl-seg-step" placeholder="1" />
                <n-button size="tiny" quaternary circle type="error" class="tpl-seg-del" :title="t('metrics.btn.delete')" @click="removeSegment(idx)">
                  <template #icon><n-icon :component="CloseOutline" /></template>
                </n-button>
              </div>
            </template>
            <!-- 🔴 实体引用型不使用分段体系：隐藏「添加段」与数值域汇总 -->
            <n-button v-if="!isEnumOutput && !isEntityOutput" size="small" dashed class="tpl-add-seg" @click="addSegment">
              <template #icon><n-icon :component="AddOutline" /></template>
              {{ t('metrics.tpl.addSegment') }}
            </n-button>
            <div v-if="!isEnumOutput && !isEntityOutput && domainErrorText" class="domain-error">
              <n-icon :component="AlertCircleOutline" :size="14" aria-hidden="true" />
              <span>{{ domainErrorText }}</span>
            </div>
            <div v-else-if="!isEnumOutput && !isEntityOutput && domainValueCount" class="domain-summary">
              <span class="ds-tag">{{ domainSummaryTag }}</span>
              <span class="ds-vals">{{ domainSummaryText }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 自由文本出参：无值域配置，改为说明「匹配多个值该用哪个运算符」 -->
      <section v-else-if="isTextOutput" class="tpl-sec tpl-sec-note">
        <div class="tpl-sec-head"><span class="tpl-sec-title">{{ t('metrics.tpl.domainTitle') }}</span></div>
        <div class="tpl-domain-block">
          <p class="tpl-hint tpl-hint-block">
            <n-icon :component="InformationCircleOutline" :size="14" aria-hidden="true" />
            <span>{{ t('metrics.tpl.textNoDomain') }}</span>
          </p>
        </div>
      </section>

      <!-- 配置预览（仪表读数条） -->
      <section class="tpl-readout">
        <div class="tpl-readout-eyebrow">{{ t('metrics.tpl.previewTitle') }} · 规则配置者所见</div>
        <div class="tpl-readout-row" :class="{ 'no-param': !showTemplateParamConfig, 'with-entity': previewNeedsEntitySelector }">
          <n-select v-model:value="previewMetricSelected" :options="previewMetricItemOptions" class="pv-select" />
          <span v-if="showTemplateParamConfig" class="pv-arrow">→</span>
          <n-select v-if="showTemplateParamConfig" v-model:value="previewParamSelected" :options="previewParamOptions" class="pv-select" />
          <span class="pv-arrow">→</span>
          <n-select v-model:value="previewOpSelected" :options="previewOpOptions" class="pv-select" />
          <!-- 🔴 实体引用型：第 4 个下拉 = 取值方式（兵哥定稿）。
               选项来自模板层启用的方式；选「指定人员/指定身份」后联动出对象下拉（候选=全量，
               默认预填模板预设值），选「当前登录人」则不出对象框。 -->
          <template v-if="previewNeedsEntitySelector">
            <span class="pv-arrow">→</span>
            <n-select
              v-model:value="previewEntitySelector"
              :options="previewEntitySelectorOptions"
              :aria-label="t('metrics.tpl.entitySelectorLabel')"
              class="pv-select pv-entity-sel"
            />
          </template>
          <span class="pv-arrow">→</span>
          <!-- 为空 / 不为空 / 当前登录人：语义已自洽，不收校验值 -->
          <span v-if="previewNeedsNoValue" class="pv-novalue">
            {{ previewNeedsEntitySelector && previewEntityIsAuto
              ? entityTypeLabel(previewEntitySelector) : t('metrics.tpl.checkValueNone') }}
          </span>
          <!-- 区间是双值运算符：校验值拆成下限 / 上限两个框 -->
          <span v-else-if="previewNeedsRangeValue" class="pv-range">
            <n-select v-model:value="previewRangeLower" :options="previewCheckValueOptions" :placeholder="t('metrics.tpl.rangeLower')" class="pv-select" />
            <span class="pv-arrow">~</span>
            <n-select v-model:value="previewRangeUpper" :options="previewCheckValueOptions" :placeholder="t('metrics.tpl.rangeUpper')" class="pv-select" />
          </span>
          <!-- 枚举型 / 实体型指定类：对象下拉；属于集合 / 不属于集合时为多选。
               实体型候选 = 值域配置中该方式配置过的候选值并集（≤ 值域配置范围），
               默认预填该方式的第一个候选。 -->
          <n-select
            v-else-if="previewNeedsEnumPicker"
            v-model:value="previewEnumValueModel"
            :multiple="previewNeedsMultiEnum"
            :options="previewSelectOptions"
            :placeholder="t('metrics.tpl.checkValuePlaceholder')"
            :aria-label="t('metrics.tpl.checkValuePlaceholder')"
            class="pv-select"
          />
          <!-- 自由文本型：单行输入（无穷域无法从下拉枚举），正则匹配即时校验表达式合法性 -->
          <span v-else-if="previewNeedsTextInput" class="pv-text">
            <n-input
              v-model:value="previewTextValue"
              :status="previewRegexIssue ? 'error' : undefined"
              :placeholder="previewTextPlaceholder"
              :aria-label="previewTextPlaceholder"
              class="pv-input"
            />
          </span>
          <n-select v-else v-model:value="previewValueSelected" :options="previewCheckValueOptions" :placeholder="t('metrics.tpl.checkValuePlaceholder')" class="pv-select" />
          <span v-if="previewRegexIssue" class="pv-error">
            <n-icon :component="AlertCircleOutline" :size="14" aria-hidden="true" />
            <span>{{ previewRegexIssue }}</span>
          </span>
        </div>
      </section>
    </n-form>

    <template #footer>
      <n-space justify="end" class="tpl-footer">
        <n-button @click="showTemplateModal = false">{{ t('metrics.btn.cancel') }}</n-button>
        <n-button type="primary" :loading="savingTpl" @click="submitTemplate">{{ t('metrics.btn.save') }}</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import { AddOutline, AlertCircleOutline, CloseOutline, InformationCircleOutline } from '@vicons/ionicons5'
import { METRICS_WORKSPACE_KEY } from '@/composables/useMetricsWorkspace'

const ws = inject(METRICS_WORKSPACE_KEY)!
const {
  t,
  showTemplateModal,
  templateModalTitle,
  templateEditId,
  tplForm,
  savingTpl,
  metricDefinitionOptions,
  selectedTemplateDefinition,
  returnTypeLabel,
  outputUnitOptions,
  setUnit,
  valueModeLabel,
  currentParamUnit,
  paramUnitOptions,
  setPunit,
  showTemplateParamConfig,
  paramTypeLabel,
  paramConfigPrecision,
  paramSampleItems,
  supportedOperatorOptions,
  operatorDisabledForFreetext,
  opSymbol,
  toggleOperator,
  showValueDomain,
  legacyNumericDomainOnDate,
  isEnumOutput,
  enumCandidateOptions,
  enumCandidateIssue,
  isDateOutput,
  currentOutputUnit,
  dateBoundTypeOptions,
  datePickerType,
  dateValueFormat,
  dateUnitOptions,
  dateBoundText,
  removeSegment,
  isNumberOutput,
  paramPrecision,
  addSegment,
  domainErrorText,
  domainValueCount,
  domainSummaryTag,
  domainSummaryText,
  domainSegmentIssues,
  isTextOutput,
  // 🔴 实体引用型（人员/部门）值域
  isEntityOutput,
  isDeptOutput,
  entitySelectorOptions,
  entityDomain,
  entityOptions,
  entityTypeNeedsPicker,
  entityOptionsForType,
  entityDraft,
  entityDraftVisible,
  entityDraftError,
  entityAutoLabelKey,
  showEntityDraft,
  cancelEntityDraft,
  confirmEntityDraft,
  entityUnusedSelectorOptions,
  entityTypesExhausted,
  entityDuplicateTypeText,
  entityDraftPickerOptions,
  entityDraftPickerOptionsAll,
  entityDraftPickerValue,
  handleEntityDraftPickerUpdate,
  entityRowPickerOptions,
  entityRowPickerValue,
  handleEntityRowPickerUpdate,
  removeEntityOption,
  updateEntityOptionIds,
  entityTypeLabel,
  entityDomainIssue,
  entityOptionsLoading,
  previewMetricSelected,
  previewMetricItemOptions,
  previewParamSelected,
  previewParamOptions,
  previewOpSelected,
  previewOpOptions,
  previewNeedsNoValue,
  previewCandidateOptions,
  previewEntitySelector,
  previewEntitySelectorOptions,
  previewNeedsEntitySelector,
  previewEntityIsAuto,
  previewNeedsRangeValue,
  previewRangeLower,
  previewCheckValueOptions,
  previewRangeUpper,
  previewNeedsEnumPicker,
  previewSelectOptions,
  previewEnumValueModel,
  previewNeedsMultiEnum,
  previewNeedsTextInput,
  previewTextValue,
  previewRegexIssue,
  previewTextPlaceholder,
  previewValueSelected,
  onTemplateMetricChange,
  submitTemplate,
} = ws
</script>
