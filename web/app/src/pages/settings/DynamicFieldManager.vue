<template>
  <div class="page-container dynamic-field-settings">
    <div class="page-header">
      <div>
        <h1 class="page-title">
          {{ isEmbedded && props.displayName ? props.displayName + ' · ' + t('pages.settings.DynamicFieldManager.s211') : t('pages.settings.DynamicFieldManager.s212') }}
        </h1>
        <p class="page-subtitle">
          {{ isEmbedded ? t('pages.settings.DynamicFieldManager.s2') : t('pages.settings.DynamicFieldManager.s213') }}
        </p>
      </div>
      <!-- 顶部操作区：资源切换 + 配置入口（页面无 Tab，配三个按钮触发居中弹窗） -->
      <n-space align="center" :wrap="false">
        <n-space v-if="!isEmbedded" align="center" :wrap="false">
          <span class="res-label">{{ t('pages.settings.DynamicFieldManager.s1') }}</span>
          <n-select
            v-model:value="currentResource"
            :options="resourceOptions"
            class="df-input-group-key"
            @update:value="onResourceChange"
          />
        </n-space>
        <n-divider v-if="!isEmbedded" vertical />
        <n-button v-if="!isEmbedded" @click="openModuleCenter">
          <template #icon><n-icon :component="AppsOutline" /></template>{{ t('pages.settings.DynamicFieldManager.s214') }}
        </n-button>
        <n-button @click="openGroupCenter">
          <template #icon><n-icon :component="ListOutline" /></template>{{ t('pages.settings.DynamicFieldManager.s215') }}
        </n-button>
        <n-button @click="openLinkageCenter">
          <template #icon><n-icon :component="GitNetworkOutline" /></template>{{ t('pages.settings.DynamicFieldManager.s216') }}
        </n-button>
      </n-space>
    </div>

    <div class="page-body">
      <!-- 页面无 Tab，「字段定义」全量铺开（分组卡片视图） -->
      <n-space class="filter-row" :wrap="true">
        <n-select v-if="!isEmbedded" v-model:value="filterModule" :options="moduleOptions" class="df-input-select" :placeholder="t('pages.settings.DynamicFieldManager.s3')" @update:value="reloadFields" />
        <n-select v-model:value="filterGroup" :options="groupFilterOptions" class="df-input-select" :placeholder="t('pages.settings.DynamicFieldManager.s4')" @update:value="reloadFields" />
        <n-button :loading="loading" @click="reloadFields">{{ t('pages.settings.DynamicFieldManager.s5') }}</n-button>
        <n-button type="primary" @click="openFieldCreate()">
          <template #icon><n-icon :component="AddOutline" /></template>{{ t('pages.settings.DynamicFieldManager.s217') }}
        </n-button>
        <n-dropdown :options="exportOptions" @select="onExportSelect">
          <n-button>{{ t('pages.settings.DynamicFieldManager.s6') }}</n-button>
        </n-dropdown>
        <n-button @click="importModalVisible = true">{{ t('pages.settings.DynamicFieldManager.s7') }}</n-button>
      </n-space>

      <!-- 分组卡片视图：按字段分组(FieldGroup)聚合，每组独立卡片 -->
      <div class="field-groups">
        <div v-for="g in groupedFields" :key="g.key" class="field-group-card">
          <div class="field-group-head">
            <span class="fg-title">{{ g.name }}</span>
            <n-tag :bordered="false" size="small" type="info">{{ t('pages.settings.DynamicFieldManager.s8') }}</n-tag>
            <n-button
              size="small" secondary type="primary"
              @click="openFieldCreate(g.key === 'ungrouped' ? null : g.key)"
            >
              <template #icon><n-icon :component="AddOutline" /></template>{{ t('pages.settings.DynamicFieldManager.s218') }}
            </n-button>
          </div>
          <n-data-table
            :columns="fieldColumns"
            :data="g.fields"
            :loading="loading"
            :pagination="false"
            :row-key="(row: any) => row.id"
            size="small"
            striped
          />
        </div>
        <n-empty v-if="!groupedFields.length && !loading" :description="t('pages.settings.DynamicFieldManager.s9')" />
      </div>
    </div>

    <!-- ============ 字段 新建/编辑 Modal ============ -->
      <n-modal
        v-model:show="fieldModalVisible"
        preset="card"
        :title="fieldEditing ? t('pages.settings.DynamicFieldManager.s10') : t('pages.settings.DynamicFieldManager.s310')"
        style="width: 680px; max-width: 92vw;"
      >
        <n-form :model="fieldForm" label-placement="left" label-width="100px">
          <n-alert
            v-if="fieldEditing && fieldForm.isSystem"
            :type="fieldForm.isLocked ? 'error' : 'warning'"
            :show-icon="true"
            style="margin-bottom: 16px"
          >
            <template v-if="fieldForm.isLocked">
              {{ t('pages.settings.DynamicFieldManager.s11') }}
            </template>
            <template v-else>
              {{ t('pages.settings.DynamicFieldManager.s12') }}
            </template>
          </n-alert>
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s13')" required>
            <n-input v-model:value="fieldForm.label" :placeholder="t('pages.settings.DynamicFieldManager.s14')" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s15')">
            <n-input v-model:value="fieldForm.labelEn" placeholder="e.g. id_card_no" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s16')" required>
            <!-- 2026-09-24 (兵哥): 分组 options + 虚拟滚动会间歇性错位(只渲分组头/选项不可见), 仅23项禁用虚拟滚动 -->
            <n-select v-model:value="fieldForm.fieldType" :options="FIELD_TYPE_OPTIONS" :virtual-scroll="false" :disabled="!!fieldForm.isLocked" />
          </n-form-item>
          <!-- 2026-09-15 (兵哥) 日期型字段：格式精度单选(年/年月/年月日)，范围类型渲染区间选择器 -->
          <n-form-item v-if="isDateType" :label="t('pages.settings.DynamicFieldManager.s17')">
            <n-space align="center" :size="8">
              <n-radio-group v-model:value="fieldForm.dateFormat">
                <n-radio-button
                  v-for="opt in DATE_FORMAT_OPTIONS"
                  :key="opt.value"
                  :value="opt.value"
                  :label="opt.label"
                />
              </n-radio-group>
              <n-text depth="3">{{ fieldForm.fieldType === 'DATE_RANGE' ? t('pages.settings.DynamicFieldManager.s269') : t('pages.settings.DynamicFieldManager.s270') }}</n-text>
            </n-space>
          </n-form-item>
          <!-- 2026-09-15 行政区划型字段：层级精度 + 国家开关 + 实时级联预览 (数据源: G46 码表库) -->
          <template v-if="isRegionType">
            <n-form-item :label="t('pages.settings.DynamicFieldManager.s18')">
              <n-radio-group v-model:value="fieldForm.regionLevel">
                <n-space>
                  <n-radio-button v-for="opt in REGION_LEVEL_OPTIONS" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </n-radio-button>
                </n-space>
              </n-radio-group>
            </n-form-item>
            <n-form-item :label="t('pages.settings.DynamicFieldManager.s19')">
              <n-space align="center" :size="8">
                <n-switch v-model:value="fieldForm.withCountry" />
                <n-text depth="3">{{ t('pages.settings.DynamicFieldManager.s20') }}</n-text>
              </n-space>
            </n-form-item>
            <n-form-item :label="t('pages.settings.DynamicFieldManager.s21')">
              <RegionCascader
                :level="fieldForm.regionLevel"
                :with-country="fieldForm.withCountry"
                :value="fieldForm.regionPreviewValue"
                :disabled="true"
                @update:value="(v) => (fieldForm.regionPreviewValue = v)"
              />
              <n-text v-if="!fieldForm.regionPreviewValue" depth="3" class="rc-hint">
                {{ t('pages.settings.DynamicFieldManager.s22') }}
              </n-text>
            </n-form-item>
          </template>
          <!-- embedded 模式：字段归属当前业务模块，隐藏模块选择，由组件强制绑定默认模块 -->
          <n-form-item v-if="!isEmbedded" :label="t('pages.settings.DynamicFieldManager.s23')">
            <n-select
              v-model:value="fieldForm.moduleId"
              :options="modules.map((m) => ({ label: m.name, value: m.id }))"
              :placeholder="t('pages.settings.DynamicFieldManager.s24')"
              clearable
              @update:value="onFieldModuleChange"
            />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s25')">
            <n-select
              v-model:value="fieldForm.groupId"
              :options="fieldGroupOptions"
              :placeholder="t('pages.settings.DynamicFieldManager.s26')"
              clearable
              :disabled="!fieldForm.moduleId"
            />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s27')">
            <n-input v-model:value="fieldForm.placeholder" placeholder="placeholder" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s28')">
            <n-input v-model:value="fieldForm.helpText" placeholder="helpText" />
          </n-form-item>
          <!-- 2026-09-24 (兵哥) 限制条件: 按字段类型差异化校验配置
               {{ t('pages.settings.DynamicFieldManager.s29') }}
               邮箱/电话/URL 等专用格式由字段类型层固有约束, 无配置项 -->
          <template v-if="isLimitTextType">
            <n-form-item :label="t('pages.settings.DynamicFieldManager.s30')">
              <n-input-number
                v-model:value="fieldForm.validation.maxLength"
                :min="1" :precision="0" clearable
                :placeholder="t('pages.settings.DynamicFieldManager.s31')" class="df-input-select"
              />
            </n-form-item>
          </template>
          <template v-else-if="isLimitNumberType">
            <n-form-item :label="t('pages.settings.DynamicFieldManager.s32')">
              <n-space align="center" :size="10" wrap>
                <div class="num-field">
                  <span class="num-label">{{ t('pages.settings.DynamicFieldManager.s33') }}</span>
                  <n-input-number v-model:value="fieldForm.validation.min" :placeholder="t('pages.settings.DynamicFieldManager.s34')" class="df-input-min-max" />
                </div>
                <div class="num-field">
                  <span class="num-label">{{ t('pages.settings.DynamicFieldManager.s35') }}</span>
                  <n-input-number v-model:value="fieldForm.validation.max" :placeholder="t('pages.settings.DynamicFieldManager.s36')" class="df-input-min-max" />
                </div>
                <div class="num-field">
                  <span class="num-label">{{ t('pages.settings.DynamicFieldManager.s37') }}</span>
                  <n-input-number v-model:value="fieldForm.validation.step" :min="0" :placeholder="t('pages.settings.DynamicFieldManager.s38')" style="width: 110px" />
                </div>
                <div class="num-field">
                  <span class="num-label">{{ t('pages.settings.DynamicFieldManager.s39') }}</span>
                  <n-input-number v-model:value="fieldForm.validation.decimals" :min="0" :precision="0" clearable :placeholder="t('pages.settings.DynamicFieldManager.s40')" style="width: 110px" />
                </div>
                <div class="num-field">
                  <span class="num-label">{{ t('pages.settings.DynamicFieldManager.s41') }}</span>
                  <n-input v-model:value="fieldForm.validation.unit" :placeholder="t('pages.settings.DynamicFieldManager.s42')" style="width: 140px" />
                </div>
              </n-space>
            </n-form-item>
          </template>
          <template v-else-if="isLimitOptionType">
            <n-form-item :label="t('pages.settings.DynamicFieldManager.s43')">
              <n-select
                v-model:value="fieldForm.validation.allowedValues"
                multiple clearable
                :options="allowedValueOptions"
                :placeholder="t('pages.settings.DynamicFieldManager.s44')"
              />
            </n-form-item>
          </template>
          <template v-else-if="isLimitDateType">
            <n-form-item :label="t('pages.settings.DynamicFieldManager.s45')">
              <n-space vertical :size="8" class="df-width-full">
                <n-space align="center" :size="8" wrap>
                  <n-radio-group :value="minMode" @update:value="(v: any) => setMinMode(v)">
                    <n-radio-button value="absolute">{{ t('pages.settings.DynamicFieldManager.s46') }}</n-radio-button>
                    <n-radio-button value="relative">{{ t('pages.settings.DynamicFieldManager.s47') }}</n-radio-button>
                  </n-radio-group>
                  <n-date-picker
                    v-if="minMode === 'absolute'"
                    v-model:value="fieldForm.validation.minDate"
                    type="date"
                    value-format="yyyy-MM-dd"
                    clearable
                    :placeholder="t('pages.settings.DynamicFieldManager.s48')"
                    style="width: 180px"
                  />
                  <n-input
                    v-else
                    v-model:value="fieldForm.validation.minDate"
                    :placeholder="t('pages.settings.DynamicFieldManager.s49')"
                    class="df-input-min-max"
                    @update:value="() => validateDateExpr('min')"
                  />
                  <n-text depth="3">{{ t('pages.settings.DynamicFieldManager.s50') }}</n-text>
                  <n-radio-group :value="maxMode" @update:value="(v: any) => setMaxMode(v)">
                    <n-radio-button value="absolute">{{ t('pages.settings.DynamicFieldManager.s51') }}</n-radio-button>
                    <n-radio-button value="relative">{{ t('pages.settings.DynamicFieldManager.s52') }}</n-radio-button>
                  </n-radio-group>
                  <n-date-picker
                    v-if="maxMode === 'absolute'"
                    v-model:value="fieldForm.validation.maxDate"
                    type="date"
                    value-format="yyyy-MM-dd"
                    clearable
                    :placeholder="t('pages.settings.DynamicFieldManager.s53')"
                    style="width: 180px"
                  />
                  <n-input
                    v-else
                    v-model:value="fieldForm.validation.maxDate"
                    :placeholder="t('pages.settings.DynamicFieldManager.s54')"
                    class="df-input-min-max"
                    @update:value="() => validateDateExpr('max')"
                  />
                </n-space>
                <n-space vertical :size="2">
                  <n-text v-if="dateExprErrors.min || dateExprErrors.max" type="error" depth="3">
                    {{ dateExprErrors.min || dateExprErrors.max }}
                  </n-text>
                  <n-text v-else depth="3" style="font-size: 12px">
                    {{ t('pages.settings.DynamicFieldManager.s55') }}
                  </n-text>
                </n-space>
              </n-space>
            </n-form-item>
          </template>
          <n-form-item v-if="hasValidationConfig" :label="t('pages.settings.DynamicFieldManager.s56')">
            <n-input v-model:value="fieldForm.validation.message" :placeholder="t('pages.settings.DynamicFieldManager.s57')" />
          </n-form-item>
          <!-- 确认题专属字段：确认内容 + 确认声明（中英双语） -->
          <template v-if="isConfirmType">
            <n-form-item :label="t('pages.settings.DynamicFieldManager.s58')" required>
              <n-input v-model:value="fieldForm.confirmationContent" type="textarea" :placeholder="t('pages.settings.DynamicFieldManager.s59')" />
            </n-form-item>
            <n-form-item :label="t('pages.settings.DynamicFieldManager.s60')">
              <n-input v-model:value="fieldForm.confirmationContentEn" type="textarea" placeholder="e.g. I certify the information is true" />
            </n-form-item>
            <n-form-item :label="t('pages.settings.DynamicFieldManager.s61')">
              <n-input v-model:value="fieldForm.confirmationDeclaration" type="textarea" :placeholder="t('pages.settings.DynamicFieldManager.s62')" />
            </n-form-item>
            <n-form-item :label="t('pages.settings.DynamicFieldManager.s63')">
              <n-input v-model:value="fieldForm.confirmationDeclarationEn" type="textarea" :placeholder="t('pages.settings.DynamicFieldManager.s64')" />
            </n-form-item>
          </template>
          <!-- 2026-09-16 (兵哥) 组合字段: 子字段编辑器(可含附件子字段, 页面呈现为组合展示卡) -->
          <template v-if="isCompositeType">
            <n-form-item :label="t('pages.settings.DynamicFieldManager.s65')" required>
              <n-space vertical :size="8" class="df-width-full">
                <n-dynamic-input
                  v-model:value="fieldForm.subFields"
                  :on-create="onCreateSubField"
                  item-style="margin-bottom: 8px;"
                >
                  <template #default="{ value }">
                    <div class="sub-field-row">
                      <n-input v-model:value="value.key" :placeholder="t('pages.settings.DynamicFieldManager.s66')" style="width: 30%" />
                      <n-input v-model:value="value.label" :placeholder="t('pages.settings.DynamicFieldManager.s67')" style="width: 28%" />
                      <n-select v-model:value="value.type" :options="SUBFIELD_TYPE_OPTIONS" style="width: 26%" />
                      <n-switch v-model:value="value.required" :title="t('pages.settings.DynamicFieldManager.s68')" />
                    </div>
                  </template>
                </n-dynamic-input>
                <n-text depth="3" class="sub-field-hint">
                  {{ t('pages.settings.DynamicFieldManager.s69') }}
                </n-text>
              </n-space>
            </n-form-item>
          </template>
          <n-form-item v-if="fieldNeedsOptions" :label="t('pages.settings.DynamicFieldManager.s70')">
            <n-space vertical :size="8" class="df-width-full">
              <n-select
                :value="sourceValue"
                :options="OPTION_SOURCE_OPTIONS"
                style="width: 280px"
                @update:value="onOptionSourceTypeChange"
              />
              <!-- 仅数据字典需进一步选字典类型（动态从后端拉取），院校库/码表库已拍平为单层选项 -->
              <n-select
                v-if="sourceType === 'dictionary'"
                v-model:value="fieldForm.optionsSource.key"
                :options="sourceKeyOptions"
                :loading="loadingDictTypes"
                :placeholder="t('pages.settings.DynamicFieldManager.s71')"
                filterable
                style="width: 100%"
                @update:value="onSourceKeyChange"
              />
              <!-- 数据字典专属预览（真实渲染由后端解析） -->
              <n-alert
                v-if="sourceType === 'dictionary' && fieldForm.optionsSource.key"
                type="info"
                :show-icon="true"
              >
{{ t('pages.settings.DynamicFieldManager.s288', { key: fieldForm.optionsSource.key }) }}
</n-alert>
              <!-- 院校库/专业库/码表库提示 -->
              <n-alert
                v-else-if="sourceHint"
                type="info"
                :show-icon="true"
              >
{{ t('pages.settings.DynamicFieldManager.s289', { hint: sourceHint }) }}
</n-alert>
            </n-space>
          </n-form-item>
          <n-form-item v-if="fieldNeedsOptions && showManualOptions" :label="t('pages.settings.DynamicFieldManager.s72')">
            <n-dynamic-input
              v-model:value="fieldForm.options"
              :on-create="onCreateOption"
              placeholder="value|label"
            >
              <template #default="{ value }">
                <n-input v-model:value="value.value" placeholder="value" style="width: 40%; margin-right: 8px" />
                <n-input v-model:value="value.label" placeholder="label" style="width: 40%" />
              </template>
            </n-dynamic-input>
          </n-form-item>
          <n-form-item v-if="fieldNeedsOptions && sourceType === 'dictionary'" :label="t('pages.settings.DynamicFieldManager.s73')">
            <n-space>
              <n-tag v-for="o in dictionaryPreviewOptions" :key="o.value" size="small">{{ o.label }}</n-tag>
              <n-text v-if="!dictionaryPreviewOptions.length" depth="3">{{ t('pages.settings.DynamicFieldManager.s74') }}</n-text>
            </n-space>
          </n-form-item>
          <n-form-item v-if="isListType && showManualOptions" :label="t('pages.settings.DynamicFieldManager.s75')" class="list-preview-item">
            <div class="list-preview-wrap">
              <FieldListOptions
                v-model="fieldPreviewValue"
                :options="fieldForm.options"
                :multiple="fieldForm.fieldType === 'LIST_MULTI'"
                :disabled="!fieldForm.options.length"
              />
              <n-text v-if="!fieldForm.options.length" depth="3" class="list-preview-hint">{{ t('pages.settings.DynamicFieldManager.s76') }}</n-text>
            </div>
          </n-form-item>
          <!-- Key 由系统自动生成, 新建时对用户隐藏; 编辑时以只读小字披露, 供开发对接查阅 -->
          <n-form-item v-if="fieldEditing" :label="t('pages.settings.DynamicFieldManager.s77')">
            <n-text depth="3" class="field-key-readonly">
              <code>{{ fieldForm.fieldKey }}</code>
              <span class="field-key-hint">{{ t('pages.settings.DynamicFieldManager.s78') }}</span>
            </n-text>
          </n-form-item>
        </n-form>
        <template #action>
          <n-space justify="end">
            <n-button @click="fieldModalVisible = false">{{ t('pages.settings.DynamicFieldManager.s79') }}</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="saveField">{{ t('pages.settings.DynamicFieldManager.s80') }}</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 字段权限管理 Modal ============ -->
      <n-modal
        v-model:show="permModalVisible"
        preset="card"
        :title="t('pages.settings.DynamicFieldManager.s81')"
        style="width: 520px; max-width: 92vw;"
      >
        <p class="perm-desc">{{ t('pages.settings.DynamicFieldManager.s82') }}</p>
        <n-radio-group v-model:value="permForm.visibilityPermission">
          <n-space vertical :size="12">
            <n-radio
              v-for="opt in VISIBILITY_PERMISSION_OPTIONS"
              :key="opt.value"
              :value="opt.value"
            >
{{ opt.label }}
</n-radio>
          </n-space>
        </n-radio-group>
        <template #action>
          <n-space justify="end">
            <n-button @click="permModalVisible = false">{{ t('pages.settings.DynamicFieldManager.s83') }}</n-button>
            <n-button type="primary" class="gradient-btn" :loading="permSaving" @click="savePermission">{{ t('pages.settings.DynamicFieldManager.s84') }}</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 模块配置 页面居中大弹窗（取代原 Tab） ============ -->
      <n-modal
        v-if="!isEmbedded"
        v-model:show="moduleCenterVisible"
        preset="card"
        :title="t('pages.settings.DynamicFieldManager.s85')"
        :mask-closable="false"
        style="width: 960px; max-width: 96vw;"
        class="df-center-modal"
      >
        <n-space class="filter-row" :wrap="true">
          <n-button :loading="moduleLoading" @click="reloadModules">{{ t('pages.settings.DynamicFieldManager.s86') }}</n-button>
          <n-button type="primary" @click="openModuleCreate">
            <template #icon><n-icon :component="AddOutline" /></template>{{ t('pages.settings.DynamicFieldManager.s219') }}
          </n-button>
        </n-space>
        <n-data-table
          :columns="moduleColumns"
          :data="moduleRows"
          :loading="moduleLoading"
          :pagination="modulePagination"
          :row-key="(row: any) => row.id"
          size="small"
          striped
        />
        <template #action>
          <n-space justify="end">
            <n-button @click="moduleCenterVisible = false">{{ t('pages.settings.DynamicFieldManager.s87') }}</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 模块 Modal（仅 overview 模式使用） ============ -->
      <n-modal
        v-if="!isEmbedded"
        v-model:show="moduleModalVisible"
        preset="card"
        :title="moduleEditing ? t('pages.settings.DynamicFieldManager.s88') : t('pages.settings.DynamicFieldManager.s311')"
        style="width: 560px; max-width: 92vw;"
      >
        <n-form :model="moduleForm" label-placement="left" label-width="100px">
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s89')" required>
            <n-input v-model:value="moduleForm.code" placeholder="e.g. basic" :disabled="!!moduleEditing" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s90')" required>
            <n-input v-model:value="moduleForm.name" :placeholder="t('pages.settings.DynamicFieldManager.s91')" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s92')">
            <n-input v-model:value="moduleForm.description" type="textarea" :placeholder="t('pages.settings.DynamicFieldManager.s93')" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s94')">
            <n-input-number v-model:value="moduleForm.orderIndex" :min="0" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s95')">
            <n-switch v-model:value="moduleForm.isActive" />
          </n-form-item>
        </n-form>
        <template #action>
          <n-space justify="end">
            <n-button @click="moduleModalVisible = false">{{ t('pages.settings.DynamicFieldManager.s96') }}</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="saveModule">{{ t('pages.settings.DynamicFieldManager.s97') }}</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 分组配置 页面居中大弹窗（取代原 Tab） ============ -->
      <n-modal
        v-model:show="groupCenterVisible"
        preset="card"
        :title="t('pages.settings.DynamicFieldManager.s98')"
        :mask-closable="false"
        style="width: 960px; max-width: 96vw;"
        class="df-center-modal"
      >
        <n-space class="filter-row" :wrap="true">
          <n-select v-if="!isEmbedded" v-model:value="groupFilterModule" :options="moduleOptions" class="df-input-select" :placeholder="t('pages.settings.DynamicFieldManager.s99')" @update:value="reloadGroups" />
          <n-button :loading="groupLoading" @click="reloadGroups">{{ t('pages.settings.DynamicFieldManager.s100') }}</n-button>
          <n-button type="primary" @click="openGroupCreate">
            <template #icon><n-icon :component="AddOutline" /></template>{{ t('pages.settings.DynamicFieldManager.s220') }}
          </n-button>
        </n-space>
        <n-data-table
          :columns="groupColumns"
          :data="groupRows"
          :loading="groupLoading"
          :pagination="groupPagination"
          :row-key="(row: any) => row.id"
          size="small"
          striped
        />
        <template #action>
          <n-space justify="end">
            <n-button @click="groupCenterVisible = false">{{ t('pages.settings.DynamicFieldManager.s101') }}</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 分组 Modal ============ -->
      <n-modal
        v-model:show="groupModalVisible"
        preset="card"
        :title="groupEditing ? t('pages.settings.DynamicFieldManager.s102') : t('pages.settings.DynamicFieldManager.s312')"
        style="width: 560px; max-width: 92vw;"
      >
        <n-form :model="groupForm" label-placement="left" label-width="100px">
          <!-- embedded 模式：分组归属当前业务模块，隐藏模块选择，由组件强制绑定默认模块 -->
          <n-form-item v-if="!isEmbedded" :label="t('pages.settings.DynamicFieldManager.s103')" required>
            <n-select
              v-model:value="groupForm.moduleId"
              :options="modules.map((m) => ({ label: m.name, value: m.id }))"
              :placeholder="t('pages.settings.DynamicFieldManager.s104')"
              @update:value="onGroupModuleChange"
            />
          </n-form-item>
          <!-- 2026-09-24 (兵哥): 分组编码由系统自动生成, 新建时不再让用户填写; 编辑仅只读展示 -->
          <n-form-item v-if="groupEditing" :label="t('pages.settings.DynamicFieldManager.s105')">
            <n-input v-model:value="groupForm.code" :placeholder="t('pages.settings.DynamicFieldManager.s106')" disabled />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s107')" required>
            <n-input v-model:value="groupForm.name" :placeholder="t('pages.settings.DynamicFieldManager.s108')" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s109')">
            <n-input-number v-model:value="groupForm.orderIndex" :min="0" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s110')">
            <n-switch v-model:value="groupForm.isActive" />
          </n-form-item>
        </n-form>
        <template #action>
          <n-space justify="end">
            <n-button @click="groupModalVisible = false">{{ t('pages.settings.DynamicFieldManager.s111') }}</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="saveGroup">{{ t('pages.settings.DynamicFieldManager.s112') }}</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 联动规则 页面居中大弹窗（取代原 Tab） ============ -->
      <n-modal
        v-model:show="linkageCenterVisible"
        preset="card"
        :title="t('pages.settings.DynamicFieldManager.s113')"
        :mask-closable="false"
        style="width: 1024px; max-width: 96vw;"
        class="df-center-modal"
      >
        <n-space class="filter-row" :wrap="true">
          <n-select v-if="!isEmbedded" v-model:value="linkageFilterModule" :options="moduleOptions" class="df-input-select" :placeholder="t('pages.settings.DynamicFieldManager.s114')" @update:value="reloadLinkage" />
          <n-button :loading="linkageLoading" @click="reloadLinkage">{{ t('pages.settings.DynamicFieldManager.s115') }}</n-button>
          <n-button type="primary" @click="openLinkageCreate">
            <template #icon><n-icon :component="AddOutline" /></template>{{ t('pages.settings.DynamicFieldManager.s221') }}
          </n-button>
        </n-space>
        <n-data-table
          :columns="linkageColumns"
          :data="linkageRows"
          :loading="linkageLoading"
          :pagination="linkagePagination"
          :row-key="(row: any) => row.id"
          size="small"
          striped
        />
        <template #action>
          <n-space justify="end">
            <n-button @click="linkageCenterVisible = false">{{ t('pages.settings.DynamicFieldManager.s116') }}</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 联动规则 Modal ============ -->
      <n-modal
        v-model:show="linkageModalVisible"
        preset="card"
        :title="linkageEditing ? t('pages.settings.DynamicFieldManager.s117') : t('pages.settings.DynamicFieldManager.s313')"
        style="width: 760px; max-width: 96vw;"
      >
        <n-form :model="linkageForm" label-placement="left" label-width="100px">
          <!-- embedded 模式：规则归属当前业务模块，隐藏模块选择，由组件强制绑定默认模块 -->
          <n-form-item v-if="!isEmbedded" :label="t('pages.settings.DynamicFieldManager.s118')" required>
            <n-select
              v-model:value="linkageForm.moduleId"
              :options="modules.map((m) => ({ label: m.name, value: m.id }))"
              :placeholder="t('pages.settings.DynamicFieldManager.s119')"
              @update:value="onLinkageModuleChange"
            />
          </n-form-item>

          <!-- 条件区域 -->
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s120')" required>
            <n-space vertical class="df-width-full">
              <n-radio-group v-model:value="linkageForm.conditionMode">
                <n-radio value="ALL">{{ t('pages.settings.DynamicFieldManager.s121') }}</n-radio>
                <n-radio value="ANY">{{ t('pages.settings.DynamicFieldManager.s122') }}</n-radio>
              </n-radio-group>
              <div
                v-for="(cond, idx) in linkageForm.conditions"
                :key="cond.__key || idx"
                class="linkage-row"
              >
                <span class="linkage-index">{{ idx + 1 }}</span>
                <n-select
                  v-model:value="cond.fieldKey"
                  :options="linkageFieldOptions"
                  :placeholder="t('pages.settings.DynamicFieldManager.s123')"
                  class="df-input-group-key"
                  clearable
                  @update:value="() => onConditionFieldChange(idx)"
                />
                <n-select
                  v-model:value="cond.op"
                  :options="LINKAGE_OP_OPTIONS"
                  :placeholder="t('pages.settings.DynamicFieldManager.s124')"
                  class="df-input-min-max"
                />
                <n-select
                  v-if="cond.op === 'IN' || cond.op === 'NOT_IN'"
                  v-model:value="cond.value"
                  :options="conditionValueOptions(cond.fieldKey)"
                  :placeholder="t('pages.settings.DynamicFieldManager.s125')"
                  multiple
                  tag
                  filterable
                  style="flex: 1"
                />
                <n-input
                  v-else
                  :value="String(cond.value ?? '')"
                  :placeholder="t('pages.settings.DynamicFieldManager.s126')"
                  style="flex: 1"
                  @update:value="(v: string) => { cond.value = v; }"
                />
                <n-button
                  quaternary
                  type="error"
                  size="small"
                  @click="removeLinkageCondition(idx)"
                >
                  <template #icon><n-icon :component="TrashOutline" /></template>
                </n-button>
              </div>
              <n-button text type="primary" @click="addLinkageCondition">
                <template #icon><n-icon :component="AddOutline" /></template>{{ t('pages.settings.DynamicFieldManager.s222') }}
              </n-button>
            </n-space>
          </n-form-item>

          <!-- 动作区域 -->
          <n-form-item :label="t('pages.settings.DynamicFieldManager.s127')" required>
            <n-space vertical class="df-width-full">
              <div
                v-for="(act, idx) in linkageForm.actions"
                :key="act.__key || idx"
                class="linkage-row"
              >
                <span class="linkage-index">{{ idx + 1 }}</span>
                <n-select
                  v-model:value="act.targetFieldKey"
                  :options="linkageFieldOptions"
                  :placeholder="t('pages.settings.DynamicFieldManager.s128')"
                  class="df-input-group-key"
                  clearable
                />
                <n-select
                  v-model:value="act.actionType"
                  :options="LINKAGE_ACTION_OPTIONS"
                  :placeholder="t('pages.settings.DynamicFieldManager.s129')"
                  class="df-input-min-max"
                />
                <n-select
                  v-if="act.actionType === 'SET_VALUE' || act.actionType === 'CASCADE_OPTIONS'"
                  v-model:value="act.value"
                  :options="actionValueOptions(act.targetFieldKey)"
                  :placeholder="t('pages.settings.DynamicFieldManager.s130')"
                  tag
                  filterable
                  clearable
                  style="flex: 1"
                />
                <n-input
                  v-else-if="act.actionType === 'READONLY'"
                  value="-"
                  disabled
                  style="flex: 1"
                />
                <div v-else style="flex: 1"></div>
                <n-checkbox v-model:checked="act.readOnly">{{ t('pages.settings.DynamicFieldManager.s131') }}</n-checkbox>
                <n-button
                  quaternary
                  type="error"
                  size="small"
                  @click="removeLinkageAction(idx)"
                >
                  <template #icon><n-icon :component="TrashOutline" /></template>
                </n-button>
              </div>
              <n-button text type="primary" @click="addLinkageAction">
                <template #icon><n-icon :component="AddOutline" /></template>{{ t('pages.settings.DynamicFieldManager.s223') }}
              </n-button>
            </n-space>
          </n-form-item>
        </n-form>
        <template #action>
          <n-space justify="end">
            <n-button @click="linkageModalVisible = false">{{ t('pages.settings.DynamicFieldManager.s132') }}</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="saveLinkage">{{ t('pages.settings.DynamicFieldManager.s133') }}</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 导入 Modal ============ -->
      <n-modal
        v-model:show="importModalVisible"
        preset="card"
        :title="t('pages.settings.DynamicFieldManager.s134')"
        style="width: 680px; max-width: 94vw;"
      >
        <n-space vertical :size="12">
          <n-alert type="info" :show-icon="true">
            {{ t('pages.settings.DynamicFieldManager.s135') }}
            <code>field_key,label,field_type,module_code,group_code,is_required,...</code>
            {{ t('pages.settings.DynamicFieldManager.s136') }}
          </n-alert>
          <n-space :wrap="false" :size="12" align="center">
            <n-radio-group v-model:value="importFormat">
              <n-radio value="json">JSON</n-radio>
              <n-radio value="csv">CSV</n-radio>
            </n-radio-group>
            <n-button size="small" secondary @click="downloadTemplateFile">{{ t('pages.settings.DynamicFieldManager.s137') }}</n-button>
            <n-button size="small" secondary @click="fileInput?.click()">{{ t('pages.settings.DynamicFieldManager.s138') }}</n-button>
            <input
              ref="fileInput"
              type="file"
              accept=".json,.csv,application/json,text/csv"
              style="display: none"
              @change="onFilePicked"
            />
            <n-text v-if="selectedFileName" depth="3">{{ t('pages.settings.DynamicFieldManager.s290', { name: selectedFileName }) }}</n-text>
          </n-space>
          <n-input
            v-model:value="importContent"
            type="textarea"
            :placeholder="t('pages.settings.DynamicFieldManager.s139')"
            :autosize="{ minRows: 8, maxRows: 16 }"
          />
          <n-text v-if="importResult" depth="3">{{ t('pages.settings.DynamicFieldManager.s291', { created: importResult.created, updated: importResult.updated, errors: importResult.errors }) }}</n-text>
        </n-space>
        <template #action>
          <n-space justify="end">
            <n-button @click="importModalVisible = false">{{ t('pages.settings.DynamicFieldManager.s140') }}</n-button>
            <n-button type="primary" class="gradient-btn" :loading="importing" @click="runImport">{{ t('pages.settings.DynamicFieldManager.s141') }}</n-button>
          </n-space>
        </template>
      </n-modal>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed, h, onMounted, reactive, watch, withDefaults, defineProps } from 'vue';
import {
  NTag, NButton, NSpace, NSwitch, NInputNumber, NIcon, NSelect, NDataTable,
  NModal, NForm, NFormItem, NInput, NDynamicInput, NTabs, NTabPane, NDropdown,
  NRadioGroup, NRadio, NRadioButton, NCheckbox, NAlert, NText, useMessage, useDialog,
} from 'naive-ui';
import { AddOutline, TrashOutline, CreateOutline, ShieldCheckmarkOutline, BanOutline, PlayOutline, AppsOutline, ListOutline, GitNetworkOutline } from '@vicons/ionicons5';
import FieldListOptions from '@/components/FieldListOptions.vue';
import RegionCascader from '@/components/RegionCascader.vue';
import {
  listFields, upsertField, deleteField, extractApiError,
  FIELD_TYPE_OPTIONS, FIELD_TYPE_LABEL,
  DATE_FORMAT_OPTIONS, isDateFieldType,
  REGION_LEVEL_OPTIONS, isRegionFieldType,
  VISIBILITY_PERMISSION_OPTIONS, VISIBILITY_PERMISSION_LABEL,
  listModules, upsertModule, deleteModule,
  listGroups, upsertGroup, deleteGroup,
  listLinkageRules, upsertLinkageRule, deleteLinkageRule,
  ensureDefaultModule,
  downloadExport, importFields, downloadTemplate,
  LINKAGE_ACTION_OPTIONS, LINKAGE_OP_OPTIONS, LINKAGE_CONDITION_MODE_OPTIONS,
  type FieldDefinition, type FieldType, type FieldModule, type FieldGroup, type FieldLinkageRule,
  type LinkageCondition, type LinkageAction, type LinkageConditionMode,
  type LinkageConditionOp, type LinkageActionType, type VisibilityPermission,
  type DateFormatValue, type RegionLevelValue, type SubField,
  type FieldValidation,
} from '@/api/dynamic-field';
// 2026-09-24 (兵哥) 限制条件: 类型分组与前端校验共用同一真源
import {
  TEXT_MAXLENGTH_TYPES, NUMBER_TYPES, OPTION_TYPES, DATE_TYPES,
  isRelativeDateExpr, isAbsoluteDate,
} from '@/utils/fieldValidation';
import {
  listDictionaryTypes, listDictionaryItems,
  type DictionaryType,
} from '@/api/dictionary';
const { t } = useI18n()

const props = withDefaults(defineProps<{
  /** overview: 4 Tab（含模块配置）+ 可切换 resource；embedded: 3 Tab + 锁定 resource + 后端自动建默认模块 */
  mode?: 'overview' | 'embedded';
  /** embedded 模式下锁定的资源（Candidate / Demand / Position） */
  resource?: string;
  /** embedded 模式下的中文展示名（如「招聘需求」「职位」「候选人」） */
  displayName?: string;
}>(), { mode: 'overview', resource: 'Candidate', displayName: '' });
// 2026-09-15 UX 整改：去掉 Tab，「模块配置/分组配置/联动规则」改用顶部按钮触发页面居中弹窗
// 当前模式说明：overview = 4 入口（资源切换 + 3 配置按钮 + 字段定义）；embedded = 3 入口（仅 3 配置按钮 + 字段定义）


const message = useMessage();
const dialog = useDialog();

const isEmbedded = computed(() => props.mode === 'embedded');
const currentResource = ref<string>(props.resource || 'Candidate');
// embedded 模式进入业务模块时，由后端保证存在的唯一默认模块 id（分组/联动规则 FK 归属）
const defaultModuleId = ref<string | null>(null);

const resourceOptions = [
  { label: t('pages.settings.DynamicFieldManager.s142'), value: 'Candidate' },
  { label: t('pages.settings.DynamicFieldManager.s143'), value: 'Demand' },
  { label: t('pages.settings.DynamicFieldManager.s144'), value: 'Position' },
];

// 辅助数据
const modules = ref<FieldModule[]>([]);
const groups = ref<FieldGroup[]>([]);

// ============ 字段定义 ============
const rows = ref<FieldDefinition[]>([]);
const loading = ref(false);
const saving = ref(false);
const fieldModalVisible = ref(false);
const fieldEditing = ref<FieldDefinition | null>(null);
const fieldPage = ref(1);
const fieldPageSize = ref(15);
const fieldPagination = computed(() => ({
  page: fieldPage.value,
  pageSize: fieldPageSize.value,
  pageCount: Math.max(1, Math.ceil(rows.value.length / fieldPageSize.value)),
  itemCount: rows.value.length,
  pageSizes: [10, 15, 20, 50],
  showSizePicker: true,
  showQuickJumper: true,
  prefix: (info: { itemCount?: number }) => h('span', t('pages.settings.DynamicFieldManager.s287', { n: info.itemCount ?? 0 })),
  onChange: (p: number) => { fieldPage.value = p; },
  onUpdatePageSize: (s: number) => { fieldPageSize.value = s; fieldPage.value = 1; },
}));
// 列表型字段实时预览的选中值（单选为标量, 多选为数组）；初始为单选用空串, 类型切到 LIST_MULTI 时由 watch 同步为 []
const fieldPreviewValue = ref<string | string[]>('');
const filterModule = ref<string>('');
const filterGroup = ref<string>('');

const fieldForm = reactive<{
  id?: string; fieldKey: string; label: string; labelEn: string; fieldType: FieldType;
  moduleId: string | null; groupId: string | null;
  isRequired: boolean; isVisible: boolean; placeholder: string; helpText: string;
  orderIndex: number; options: { value: string; label: string }[];
  optionsSource: { type: string; key: string };
  confirmationContent: string; confirmationContentEn: string;
  confirmationDeclaration: string; confirmationDeclarationEn: string;
  visibilityPermission: VisibilityPermission;
  withCountry: boolean;
  dateFormat: DateFormatValue;
  regionLevel: RegionLevelValue;
  regionPreviewValue: { country?: {code: string; name: string}; province: {code: string; name: string}; city?: {code: string; name: string}; district?: {code: string; name: string}; } | null;
  subFields: SubField[];
  /** 2026-09-24 (兵哥) 限制条件配置 (按字段类型差异化, 后端 normalize_validation 规范化) */
  validation: FieldValidation;
  /** 2026-09-27 (兵哥): 系统内置字段(种子预置) — 不可删除; 结构性属性后端守卫剥除 */
  isSystem?: boolean;
  /** 系统核心标识字段(编号/名称/状态)完全锁定 — 不可编辑/停用/删除 */
  isLocked?: boolean;
}>({
  fieldKey: '', label: '', labelEn: '', fieldType: 'TEXT',
  moduleId: null, groupId: null,
  isRequired: false, isVisible: true, placeholder: '', helpText: '',
  orderIndex: 0, options: [],
  optionsSource: { type: 'custom', key: '' },
  confirmationContent: '', confirmationContentEn: '',
  confirmationDeclaration: '', confirmationDeclarationEn: '',
  visibilityPermission: 'ALL_VISIBLE',
  withCountry: false,
  dateFormat: 'DAY' as DateFormatValue,
  regionLevel: 'DISTRICT' as RegionLevelValue,
  regionPreviewValue: null,
  subFields: [],
  validation: {},
  isSystem: false,
  isLocked: false,
});

// 系统内置字段的结构性属性(选项/字段类型)由后端守卫剥除, 编辑态不暴露选项编辑器。
const fieldNeedsOptions = computed(() =>
  !fieldForm.isSystem &&
  ['SELECT', 'MULTISELECT', 'LIST_SINGLE', 'LIST_MULTI', 'PERSON', 'DEPARTMENT'].includes(fieldForm.fieldType),
);

// ---------------------------------------------------------------------------
// 2026-09-24 (兵哥) 限制条件配置: 与后端 validators.py 类型分组对齐
//   - 文本类 (TEXT/MULTILINE_TEXT/ADDRESS/ID_CARD/BANK_CARD/URL): 最大字数
//   - 专用格式 (EMAIL/PHONE/URL): 类型层固有格式, 无配置项
//   - 数字类 (NUMBER): 最小值/最大值/步长/小数位数/单位
//   - 选项类 (LIST_SINGLE/LIST_MULTI): 可选范围; 下拉型 SELECT/MULTISELECT 无配置项
//   - 日期类 (DATE/DATE_RANGE): 日期可选范围 (minDate/maxDate)
//   - 其余类型 (RICH_TEXT 等): 无限制条件配置
// ---------------------------------------------------------------------------
const isLimitTextType = computed(() => TEXT_MAXLENGTH_TYPES.includes(fieldForm.fieldType));
const isLimitNumberType = computed(() => NUMBER_TYPES.includes(fieldForm.fieldType));
const isLimitOptionType = computed(() => OPTION_TYPES.includes(fieldForm.fieldType)); // 仅列表型有「可选范围」
const isLimitDateType = computed(() => DATE_TYPES.includes(fieldForm.fieldType)); // 日期型: 可选范围
const hasValidationConfig = computed(() =>
  isLimitTextType.value || isLimitNumberType.value || isLimitOptionType.value || isLimitDateType.value,
);

/** 日期可选范围: 起始/结束边界的模式(绝对日期 / 相对天数) + 相对表达式输入校验错误 */
const minMode = ref<'absolute' | 'relative'>('absolute');
const maxMode = ref<'absolute' | 'relative'>('absolute');
const dateExprErrors = reactive<{ min: string; max: string }>({ min: '', max: '' });

/** 切换边界模式: 切换时清空该边界值, 避免跨模式残留非法字符串 */
function setMinMode(m: 'absolute' | 'relative') {
  minMode.value = m;
  fieldForm.validation.minDate = m === 'relative' ? '' : null;
  dateExprErrors.min = '';
}
function setMaxMode(m: 'absolute' | 'relative') {
  maxMode.value = m;
  fieldForm.validation.maxDate = m === 'relative' ? '' : null;
  dateExprErrors.max = '';
}

/** 校验相对/绝对日期边界输入; 非法即写入红字提示(弹窗内拦截, 不发请求) */
function validateDateExpr(which: 'min' | 'max') {
  const key = which === 'min' ? 'minDate' : 'maxDate';
  const v = (fieldForm.validation as FieldValidation | null)?.[key];
  if (!v || !String(v).trim()) { dateExprErrors[which] = ''; return; }
  const s = String(v).trim();
  if (isRelativeDateExpr(s) || isAbsoluteDate(s)) dateExprErrors[which] = '';
  else dateExprErrors[which] = t('pages.settings.DynamicFieldManager.s273');
}

/** 选项类「可选范围」候选 = 当前手动维护的选项 */
const allowedValueOptions = computed(() =>
  fieldForm.options.map((o) => ({ label: o.label || o.value, value: o.value })),
);

/** 按字段类型组装 validation payload (非受限类型传 {} 清空, 后端 normalize 兜底) */
function buildValidationPayload(): FieldValidation {
  const v = fieldForm.validation || {};
  if (isLimitTextType.value) {
    return { maxLength: v.maxLength ?? null, message: v.message || '' };
  }
  if (isLimitNumberType.value) {
    return {
      min: v.min ?? null, max: v.max ?? null, step: v.step ?? null,
      decimals: v.decimals ?? null,
      // 单位 (unit): 展示用文案, 空则丢弃
      unit: v.unit ? String(v.unit).trim() || null : null,
      message: v.message || '',
    };
  }
  if (isLimitOptionType.value) {
    return {
      allowedValues: v.allowedValues && v.allowedValues.length ? v.allowedValues : null,
      message: v.message || '',
    };
  }
  if (isLimitDateType.value) {
    // 兼容绝对日期(YYYY-MM-DD)与相对表达式(T±N); 非法形态置空(不限制), 不污染存储
    const sanitizeBound = (val: unknown): string | null => {
      const s = typeof val === 'string' ? val.trim() : '';
      return s && (isAbsoluteDate(s) || isRelativeDateExpr(s)) ? s : null;
    };
    return {
      minDate: sanitizeBound(v.minDate),
      maxDate: sanitizeBound(v.maxDate),
      message: v.message || '',
    };
  }
  return {};
}

// 2026-09-15 选项来源 (兵哥): 下拉/列表型字段除手动维护选项外, 可指定数据源动态解析
// 拍平为单层下拉（兵哥 9-15 反馈: 院校/专业库、码表库不再做二级级联, 直接拆成独立选项）
// 复合 value 形式 type:key, 选择即写入 fieldForm.optionsSource.{type,key}, 后端零改动兼容
//
// 2026-09-24 (兵哥): 选项来源按字段类型联动 — 人员/部门类型仅暴露各自的来源集合,
// 避免选到不兼容的数据源 (如给「人员」选「专业库」)。
const OPTION_SOURCE_OPTIONS = computed<{ label: string; value: string }[]>(() => {
  if (fieldForm.fieldType === 'PERSON') {
    return [
      { label: t('pages.settings.DynamicFieldManager.s145'), value: 'custom' },
      { label: t('pages.settings.DynamicFieldManager.s146'), value: 'internal_user' },
      { label: t('pages.settings.DynamicFieldManager.s147'), value: 'external_user' },
    ];
  }
  if (fieldForm.fieldType === 'DEPARTMENT') {
    return [
      { label: t('pages.settings.DynamicFieldManager.s148'), value: 'custom' },
      { label: t('pages.settings.DynamicFieldManager.s149'), value: 'organization' },
    ];
  }
  return [
    { label: t('pages.settings.DynamicFieldManager.s150'), value: 'custom' },
    { label: t('pages.settings.DynamicFieldManager.s151'), value: 'dictionary' },
    { label: t('pages.settings.DynamicFieldManager.s152'), value: 'library:major' },
    { label: t('pages.settings.DynamicFieldManager.s153'), value: 'library:school' },
    { label: t('pages.settings.DynamicFieldManager.s154'), value: 'code_table:country' },
    { label: t('pages.settings.DynamicFieldManager.s155'), value: 'code_table:ethnicity' },
    { label: t('pages.settings.DynamicFieldManager.s156'), value: 'code_table:language' },
  ];
});
// 当前选中的来源类型（兜底 custom）
const sourceType = computed(() => fieldForm.optionsSource?.type || 'custom');
// 下拉当前值（复合 type:key；custom/dictionary 无 key 时退化为纯 type）
const sourceValue = computed(() => {
  const t = fieldForm.optionsSource?.type || 'custom';
  const k = fieldForm.optionsSource?.key || '';
  if (t === 'custom' || t === 'dictionary' || !k) return t;
  return `${t}:${k}`;
});
// 仅自定义来源展示手动选项编辑器（A: 选了数据源则隐藏手动选项）
const showManualOptions = computed(() => sourceType.value === 'custom');
// 当前数据源的子 key 下拉选项：仅数据字典为动态类型列表；院校库/码表库已拍平到主下拉
const sourceKeyOptions = computed(() => {
  if (sourceType.value === 'dictionary') return dictionaryTypeOptions.value;
  return [];
});
// 数据字典类型列表（选「数据字典」时懒加载）
const dictionaryTypes = ref<DictionaryType[]>([]);
const loadingDictTypes = ref(false);
// 当前所选字典类型下的预览选项（仅编辑态预览, 真实渲染仍由后端解析）
const dictionaryPreviewOptions = ref<{ value: string; label: string }[]>([]);
// 字典类型下拉选项：仅展示启用中的字典类型（与后端解析器一致：type 须 is_enabled）
const dictionaryTypeOptions = computed(() =>
  dictionaryTypes.value
    .filter((t) => t.isEnabled)
    .map((t) => ({ label: `${t.name}（${t.code}）`, value: t.code })),
);

// 当前数据源的预览条数提示（library: 2744 + 1976 / code_table: 250+58+609）
const sourceHint = computed(() => {
  if (sourceType.value === 'custom') return '';
  if (sourceType.value === 'internal_user') return t('pages.settings.DynamicFieldManager.s275');
  if (sourceType.value === 'external_user') return t('pages.settings.DynamicFieldManager.s276');
  if (sourceType.value === 'organization') return t('pages.settings.DynamicFieldManager.s277');
  if (sourceType.value === 'library') {
    if (fieldForm.optionsSource?.key === 'school') return t('pages.settings.DynamicFieldManager.s278');
    if (fieldForm.optionsSource?.key === 'major') return t('pages.settings.DynamicFieldManager.s279');
    return t('pages.settings.DynamicFieldManager.s280');
  }
  if (sourceType.value === 'code_table') {
    if (fieldForm.optionsSource?.key === 'country') return t('pages.settings.DynamicFieldManager.s281');
    if (fieldForm.optionsSource?.key === 'ethnicity') return t('pages.settings.DynamicFieldManager.s282');
    if (fieldForm.optionsSource?.key === 'language') return t('pages.settings.DynamicFieldManager.s283');
    return t('pages.settings.DynamicFieldManager.s284');
  }
  return '';
});

// 2026-09-24 (兵哥): 切换字段类型时, 若当前选项来源类型不在新类型的可用集合内, 重置为自定义,
// 避免「人员」字段残留「数据字典 / 专业库」等不兼容来源, 或反之。
watch(() => fieldForm.fieldType, () => {
  const allowed = OPTION_SOURCE_OPTIONS.value.map((o) => o.value.split(':')[0]);
  if (!allowed.includes(fieldForm.optionsSource?.type || 'custom')) {
    fieldForm.optionsSource = { type: 'custom', key: '' };
    dictionaryPreviewOptions.value = [];
    loadingDictTypes.value = false;
  }
});

/** 切换选项来源：val 为复合 value（type 或 type:key）。
 *  custom → 清空 key；dictionary → 懒加载字典类型列表；library:/code_table: 直接拆 type+key 写入。 */
async function onOptionSourceTypeChange(val: string) {
  dictionaryPreviewOptions.value = [];
  if (val === 'custom') {
    fieldForm.optionsSource.type = 'custom';
    fieldForm.optionsSource.key = '';
    return;
  }
  if (val === 'dictionary') {
    fieldForm.optionsSource.type = 'dictionary';
    fieldForm.optionsSource.key = '';
    loadingDictTypes.value = true;
    try {
      dictionaryTypes.value = await listDictionaryTypes({ type: 'all' });
    } catch (e: any) {
      message.error(t('pages.settings.DynamicFieldManager.s244') + extractApiError(e));
    } finally {
      loadingDictTypes.value = false;
    }
    return;
  }
  // 复合 value: type:key（院校库/码表库已拍平, 选中即确定 key）
  const [type, key] = val.split(':');
  fieldForm.optionsSource.type = type;
  fieldForm.optionsSource.key = key;
}

/** 切换子 key（library major/school, code_table country/ethnicity/language, dictionary code）。统一入口 */
function onSourceKeyChange(key: string) {
  fieldForm.optionsSource.key = key;
  dictionaryPreviewOptions.value = [];
  // 字典才需要拉条目预览
  if (sourceType.value === 'dictionary') onDictTypeChange(key);
}

/** 选择具体字典类型后，拉取该字典项作为编辑态预览。 */
async function onDictTypeChange(code: string) {
  fieldForm.optionsSource.key = code;
  dictionaryPreviewOptions.value = [];
  if (!code) return;
  try {
    const items = await listDictionaryItems(code);
    dictionaryPreviewOptions.value = items
      .filter((it) => it.isActive)
      .map((it) => ({ value: it.key, label: it.value }));
  } catch (e: any) {
    message.error(t('pages.settings.DynamicFieldManager.s245') + extractApiError(e));
  }
}
const fieldGroupOptions = computed(() => {
  const base = fieldForm.moduleId ? groups.value.filter((g) => g.moduleId === fieldForm.moduleId) : groups.value;
  return base.map((g) => ({ label: g.name, value: g.id }));
});

const FIELD_TYPE_COLOR: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
  TEXT: 'default', NUMBER: 'info', RANGE_NUMBER: 'info', DATE: 'success', DATE_RANGE: 'success',
  SELECT: 'warning', MULTISELECT: 'warning', BOOLEAN: 'default',
  ATTACHMENT: 'info', ID_CARD: 'error', BANK_CARD: 'error', PHONE: 'error', EMAIL: 'error',
  LIST_SINGLE: 'warning', LIST_MULTI: 'warning', CONFIRM: 'info',
  MULTILINE_TEXT: 'default',
  // 2026-09-15 新增地址: 默认色 (与文本一致)
  ADDRESS: 'default',
  // 行政区划型: success (与日期同色, 表达"地理位置")
  REGION: 'success',
  // 2026-09-16 (兵哥): 组合字段 — 品牌主色, 表达"聚合"
  COMPOSITE: 'warning',
  // 2026-09-24 (兵哥): 富文本 — 默认色 (与文本/地址一致)
  RICH_TEXT: 'default',
};

// 2026-09-16 (兵哥): 组合字段子字段类型选项(与后端 serializers allowed 子集对齐)
const SUBFIELD_TYPE_OPTIONS = [
  { label: t('pages.settings.DynamicFieldManager.s157'), value: 'TEXT' },
  { label: t('pages.settings.DynamicFieldManager.s158'), value: 'NUMBER' },
  { label: t('pages.settings.DynamicFieldManager.s159'), value: 'MULTILINE_TEXT' },
  { label: t('pages.settings.DynamicFieldManager.s160'), value: 'ATTACHMENT' },
  { label: t('pages.settings.DynamicFieldManager.s161'), value: 'DATE' },
  { label: t('pages.settings.DynamicFieldManager.s162'), value: 'PHONE' },
  { label: t('pages.settings.DynamicFieldManager.s163'), value: 'EMAIL' },
];

// 组合字段型: 显示子字段编辑器
const isCompositeType = computed(() => fieldForm.fieldType === 'COMPOSITE');

// n-dynamic-input 新建子字段的默认结构
function onCreateSubField(): SubField {
  return { key: '', label: '', type: 'TEXT', required: false };
}

// 列表型字段预览：切换单选/多选时同步预览值形状
watch(
  () => fieldForm.fieldType,
  (t) => {
    fieldPreviewValue.value = t === 'LIST_MULTI' ? [] : '';
    // 行政区划型切换时重置 region 预览, 避免不同级数的缓存污染
    if (t === 'REGION') {
      fieldForm.regionPreviewValue = null;
    }
  },
);
const isListType = computed(() => fieldForm.fieldType === 'LIST_SINGLE' || fieldForm.fieldType === 'LIST_MULTI');
const isConfirmType = computed(() => fieldForm.fieldType === 'CONFIRM');
// 2026-09-15 (兵哥) 日期型字段(单点/范围): 显示「日期格式」精度单选
const isDateType = computed(() => isDateFieldType(fieldForm.fieldType));
// 2026-09-15 行政区划型: 省/省市/省市区 (层级精度由 region_level 控制)
const isRegionType = computed(() => isRegionFieldType(fieldForm.fieldType));

// 字段按分组(FieldGroup)聚合为卡片；无分组的归到「未分组」
const groupedFields = computed(() => {
  const map = new Map<string, { key: string; name: string; fields: FieldDefinition[] }>();
  for (const row of rows.value) {
    const gid = row.groupId || row.group?.id || '';
    const gname = row.group?.name || row.groupName || t('pages.settings.DynamicFieldManager.s274');
    if (!map.has(gid)) map.set(gid, { key: gid || 'ungrouped', name: gname, fields: [] });
    map.get(gid)!.fields.push(row);
  }
  return Array.from(map.values());
});

const fieldColumns = computed(() => [
  { title: t('pages.settings.DynamicFieldManager.s164'), key: 'label', minWidth: 140, render: (row: FieldDefinition) => row.label },
  {
    title: t('pages.settings.DynamicFieldManager.s165'), key: 'labelEn', minWidth: 140,
    render: (row: FieldDefinition) => row.labelEn || '-',
  },
  {
    title: t('pages.settings.DynamicFieldManager.s166'), key: 'fieldType', width: 100,
    render: (row: FieldDefinition) => h(NTag, { size: 'small', type: FIELD_TYPE_COLOR[row.fieldType] || 'default' }, () => FIELD_TYPE_LABEL[row.fieldType] || row.fieldType),
  },
  {
    title: t('pages.settings.DynamicFieldManager.s167'), key: 'system', width: 120,
    render: (row: FieldDefinition) => {
      if (row.isLocked) return h(NTag, { size: 'small', type: 'error', bordered: false }, () => t('pages.settings.DynamicFieldManager.s224'));
      if (row.isSystem) return h(NTag, { size: 'small', type: 'info', bordered: false }, () => t('pages.settings.DynamicFieldManager.s225'));
      return h(NTag, { size: 'small', type: 'default', bordered: false }, () => t('pages.settings.DynamicFieldManager.s226'));
    },
  },
  {
    title: t('pages.settings.DynamicFieldManager.s168'), key: 'visibilityPermission', width: 130,
    render: (row: FieldDefinition) => {
      const v = row.visibilityPermission || 'ALL_VISIBLE';
      const type = v === 'MANAGER_HIDDEN' ? 'warning' : 'success';
      return h(NTag, { size: 'small', type, bordered: false }, () => VISIBILITY_PERMISSION_LABEL[v]);
    },
  },
  {
    title: t('pages.settings.DynamicFieldManager.s169'), key: 'action', width: 320, fixed: 'right' as const,
    render: (row: FieldDefinition) => {
      const disabled = row.status === 'inactive';
      // 2026-09-27 (兵哥) 修正: 锁定字段(编号/名称/状态)仅「字段类型」与「停用状态」两项不可改,
      // 其余属性(label/英文/提示/必填/可见/选项/分组/排序/可见权限)均可编辑 → 编辑/管理权限启用;
      // 「停用」按钮仍禁用(停用状态锁定); 非锁定系统字段可调整展示属性, 但不可删除(后端 400 拦截)。
      const locked = !!row.isLocked;
      const system = !!row.isSystem;
      const children: any[] = [
        h(NButton, { size: 'tiny', quaternary: true, onClick: () => openPermissionModal(row) }, { default: () => t('pages.settings.DynamicFieldManager.s227'), icon: () => h(ShieldCheckmarkOutline) }),
        h(NButton, { size: 'tiny', quaternary: true, onClick: () => openFieldEdit(row) }, { default: () => t('pages.settings.DynamicFieldManager.s228'), icon: () => h(CreateOutline) }),
        h(NButton, {
          size: 'tiny', quaternary: true,
          type: disabled ? 'primary' : 'default',
          disabled: locked,
          onClick: () => toggleFieldStatus(row),
        }, { default: () => (disabled ? t('pages.settings.DynamicFieldManager.s242') : t('pages.settings.DynamicFieldManager.s243')), icon: () => disabled ? h(PlayOutline) : h(BanOutline) }),
      ];
      if (!system) {
        children.push(
          h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => confirmDeleteField(row) }, { default: () => t('pages.settings.DynamicFieldManager.s229'), icon: () => h(TrashOutline) }),
        );
      }
      return h(NSpace, { size: 4, wrap: false }, { default: () => children });
    },
  },
]);

function onCreateOption() { return { value: '', label: '' }; }

async function reloadFields() {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {};
    if (filterModule.value) params.module_id = filterModule.value;
    if (filterGroup.value) params.group_id = filterGroup.value;
    rows.value = await listFields(currentResource.value, params);
    fieldPage.value = 1;
  } catch (e: any) {
    message.error(t('pages.settings.DynamicFieldManager.s246') + extractApiError(e));
  } finally {
    loading.value = false;
  }
}

/**
 * 自动生成字段 Key（`f_` + 8 位小写字母数字短码）。
 *
 * Key 是程序标识（数据存取列名 / 联动规则引用 / 导入导出匹配主键），
 * 但配置字段的管理员不需要理解它，因此新建时隐藏输入框、由系统生成；
 * 编辑时以只读小字披露，供开发对接查阅。
 */
function generateFieldKey(): string {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let out = '';
  for (let i = 0; i < 8; i += 1) out += chars[Math.floor(Math.random() * chars.length)];
  return `f_${out}`;
}

function resetFieldForm() {
  Object.assign(fieldForm, {
    id: undefined, fieldKey: generateFieldKey(), label: '', labelEn: '', fieldType: 'TEXT',
    moduleId: null, groupId: null,
    isRequired: false, isVisible: true, placeholder: '', helpText: '',
    orderIndex: rows.value.length, options: [],
    optionsSource: { type: 'custom', key: '' },
    confirmationContent: '', confirmationContentEn: '',
    confirmationDeclaration: '', confirmationDeclarationEn: '',
    visibilityPermission: 'ALL_VISIBLE',
    withCountry: false,
    dateFormat: 'DAY' as DateFormatValue,
    regionLevel: 'DISTRICT' as RegionLevelValue,
    regionPreviewValue: null,
    subFields: [],
    validation: {},
    isSystem: false,
    isLocked: false,
  });
  minMode.value = 'absolute';
  maxMode.value = 'absolute';
  dateExprErrors.min = '';
  dateExprErrors.max = '';
}

function openFieldCreate(groupId?: string | null) {
  fieldEditing.value = null;
  resetFieldForm();
  // embedded 模式：字段归属默认模块
  if (isEmbedded.value) fieldForm.moduleId = defaultModuleId.value;
  // 从分组卡片「添加字段」进入时，预填该分组
  if (groupId) fieldForm.groupId = groupId;
  fieldModalVisible.value = true;
}

function openFieldEdit(row: FieldDefinition) {
  fieldEditing.value = row;
  Object.assign(fieldForm, {
    id: row.id, fieldKey: row.fieldKey, label: row.label, labelEn: row.labelEn || '', fieldType: row.fieldType,
    moduleId: isEmbedded.value ? (defaultModuleId.value || row.moduleId || null) : (row.moduleId || null),
    groupId: row.groupId || null,
    isRequired: row.isRequired, isVisible: row.isVisible,
    placeholder: row.placeholder || '', helpText: row.helpText || '',
    orderIndex: row.orderIndex,
    // 非自定义来源: 后端 to_representation 已把 options 解析成数据源全量, 编辑态不回填手动编辑器
    optionsSource: row.optionsSource || { type: 'custom', key: '' },
    options: (row.optionsSource && row.optionsSource.type && row.optionsSource.type !== 'custom')
      ? []
      : (row.options || []).map((o) => ({ value: o.value, label: o.label })),
    confirmationContent: row.confirmationContent || '',
    confirmationContentEn: row.confirmationContentEn || '',
    confirmationDeclaration: row.confirmationDeclaration || '',
    confirmationDeclarationEn: row.confirmationDeclarationEn || '',
    visibilityPermission: row.visibilityPermission || 'ALL_VISIBLE',
    withCountry: !!row.withCountry,
    dateFormat: (row.dateFormat as DateFormatValue) || 'DAY',
    regionLevel: (row.regionLevel as RegionLevelValue) || 'DISTRICT',
    regionPreviewValue: null,
    isSystem: !!row.isSystem,
    isLocked: !!row.isLocked,
    // 2026-09-16 (兵哥): 组合字段子结构回填
    subFields: row.subFields ? row.subFields.map((s) => ({ ...s })) : [],
    // 2026-09-24 (兵哥): 限制条件回填 (按字段类型差异化, 后端 normalize 兜底)
    validation: { ...(row.validation || {}) },
  });
  // 2026-09-28 (寇豆码): 日期可选范围 — 按既有 minDate/maxDate 形态推导边界模式(绝对/相对)
  const v0 = (row.validation || {}) as FieldValidation;
  minMode.value = isRelativeDateExpr(v0.minDate) ? 'relative' : 'absolute';
  maxMode.value = isRelativeDateExpr(v0.maxDate) ? 'relative' : 'absolute';
  dateExprErrors.min = '';
  dateExprErrors.max = '';
  fieldModalVisible.value = true;
}

function onFieldModuleChange() { fieldForm.groupId = null; }

async function saveField() {
  if (!fieldForm.label.trim()) { message.error(t('pages.settings.DynamicFieldManager.s170')); return; }
  // 2026-09-15 选项来源校验: 选了非 custom 但子 key 空 → 拦截
  // 2026-09-15 选项来源校验: 仅「数据字典」需要继续选择子类型(key);
  // 内部用户/外部用户/组织管理/专业库/院校库/码表库 选中即确定来源, 无需子 key。
  if (fieldNeedsOptions.value && sourceType.value !== 'custom' && sourceType.value === 'dictionary' && !fieldForm.optionsSource?.key) {
    message.error(t('pages.settings.DynamicFieldManager.s247') + OPTION_SOURCE_OPTIONS.value.find((o) => o.value === sourceType.value)?.label  + t('pages.settings.DynamicFieldManager.s266'));
    return;
  }
  // 2026-09-28 (寇豆码): 日期可选范围 — 保存前再校验相对/绝对表达式, 非法输入在弹窗内拦截、不发请求
  if (isLimitDateType.value) {
    validateDateExpr('min');
    validateDateExpr('max');
    if (dateExprErrors.min || dateExprErrors.max) {
      message.error(t('pages.settings.DynamicFieldManager.s171'));
      return;
    }
  }
  saving.value = true;
  try {
    const payload: any = {
      // Key 由系统自动生成; 此处兜底防御 (极端情况下 fieldForm 被外部置空)
      fieldKey: fieldForm.fieldKey || generateFieldKey(),
      label: fieldForm.label, labelEn: fieldForm.labelEn, fieldType: fieldForm.fieldType,
      isRequired: fieldForm.isRequired, isVisible: fieldForm.isVisible,
      placeholder: fieldForm.placeholder, helpText: fieldForm.helpText,
      orderIndex: fieldForm.orderIndex,
      moduleId: fieldForm.moduleId || null, groupId: fieldForm.groupId || null,
      // 2026-09-14 确认题 + 英文字段名 + 可见权限
      confirmationContent: fieldForm.confirmationContent,
      confirmationContentEn: fieldForm.confirmationContentEn,
      confirmationDeclaration: fieldForm.confirmationDeclaration,
      confirmationDeclarationEn: fieldForm.confirmationDeclarationEn,
      visibilityPermission: fieldForm.visibilityPermission,
      // 2026-09-15 行政区划型字段开关 (默认 false; 非 REGION 类型上传无副作用)
      withCountry: !!fieldForm.withCountry,
      // 2026-09-15 日期格式精度 (默认 DAY; 非日期型字段上传无副作用)
      dateFormat: fieldForm.dateFormat || 'DAY',
      // 2026-09-15 行政区划层级精度 (默认 DISTRICT; 非 REGION 类型上传无副作用)
      regionLevel: fieldForm.regionLevel || 'DISTRICT',
      // 2026-09-16 (兵哥): 组合字段子结构; 非 COMPOSITE 类型上传空数组无副作用
      subFields: fieldForm.fieldType === 'COMPOSITE' ? (fieldForm.subFields || []) : [],
      // 2026-09-24 (兵哥): 限制条件 (按类型组装; 非受限类型 {} 清空)
      validation: buildValidationPayload(),
      id: fieldEditing.value?.id,
    };
    // 2026-09-15 选项来源: 选项型字段若指定了数据源, 清空手动 options, 由后端按 options_source 解析
    payload.optionsSource = fieldForm.optionsSource || { type: 'custom', key: '' };
    if (!fieldNeedsOptions.value) {
      payload.options = [];
    } else if (fieldForm.optionsSource && fieldForm.optionsSource.type && fieldForm.optionsSource.type !== 'custom') {
      payload.options = [];
    } else {
      payload.options = fieldForm.options;
    }
    await upsertField(currentResource.value, payload);
    fieldModalVisible.value = false;
    message.success(t('pages.settings.DynamicFieldManager.s172'));
    await reloadFields();
  } catch (e: any) {
    message.error(t('pages.settings.DynamicFieldManager.s248') + extractApiError(e));
  } finally {
    saving.value = false;
  }
}

function confirmDeleteField(row: FieldDefinition) {
  dialog.warning({
    title: t('pages.settings.DynamicFieldManager.s173'),
    content: t('pages.settings.DynamicFieldManager.s292', { label: row.label }),
    positiveText: t('pages.settings.DynamicFieldManager.s293'),
    negativeText: t('pages.settings.DynamicFieldManager.s294'),
    onPositiveClick: async () => {
      try {
        await deleteField(currentResource.value, row.id);
        message.success(t('pages.settings.DynamicFieldManager.s174'));
        await reloadFields();
      } catch (e: any) { message.error(t('pages.settings.DynamicFieldManager.s249') + extractApiError(e)); }
    },
  });
}

// ============ 字段权限管理弹窗 ============
const permModalVisible = ref(false);
const permSaving = ref(false);
const permTarget = ref<FieldDefinition | null>(null);
const permForm = reactive<{ visibilityPermission: VisibilityPermission }>({ visibilityPermission: 'ALL_VISIBLE' });

function openPermissionModal(row: FieldDefinition) {
  permTarget.value = row;
  permForm.visibilityPermission = row.visibilityPermission || 'ALL_VISIBLE';
  permModalVisible.value = true;
}

async function savePermission() {
  if (!permTarget.value) return;
  permSaving.value = true;
  try {
    const updated = await upsertField(currentResource.value, {
      id: permTarget.value.id,
      visibilityPermission: permForm.visibilityPermission,
    });
    const idx = rows.value.findIndex((r) => r.id === updated.id);
    if (idx >= 0) rows.value[idx] = updated;
    message.success(t('pages.settings.DynamicFieldManager.s175'));
    permModalVisible.value = false;
  } catch (e: any) {
    message.error(t('pages.settings.DynamicFieldManager.s250') + extractApiError(e));
  } finally {
    permSaving.value = false;
  }
}

// 停用 / 启用（可逆操作，直接执行 + 乐观更新，无需二次确认）
async function toggleFieldStatus(row: FieldDefinition) {
  const next = row.status === 'inactive' ? 'active' : 'inactive';
  try {
    const updated = await upsertField(currentResource.value, { id: row.id, status: next });
    const idx = rows.value.findIndex((r) => r.id === updated.id);
    if (idx >= 0) rows.value[idx] = updated;
    message.success(next === 'inactive' ? t('pages.settings.DynamicFieldManager.s267') : t('pages.settings.DynamicFieldManager.s268'));
  } catch (e: any) {
    message.error(t('pages.settings.DynamicFieldManager.s251') + extractApiError(e));
  }
}

// ============ 模块配置（仅 overview 模式使用） ============
const moduleRows = ref<FieldModule[]>([]);
const moduleLoading = ref(false);
const moduleModalVisible = ref(false);
const moduleCenterVisible = ref(false);
const moduleEditing = ref<FieldModule | null>(null);
const modulePage = ref(1);
const modulePageSize = ref(15);
const modulePagination = computed(() => ({
  page: modulePage.value,
  pageSize: modulePageSize.value,
  pageCount: Math.max(1, Math.ceil(moduleRows.value.length / modulePageSize.value)),
  itemCount: moduleRows.value.length,
  pageSizes: [10, 15, 20, 50],
  showSizePicker: true,
  showQuickJumper: true,
  prefix: (info: { itemCount?: number }) => h('span', t('pages.settings.DynamicFieldManager.s287', { n: info.itemCount ?? 0 })),
  onChange: (p: number) => { modulePage.value = p; },
  onUpdatePageSize: (s: number) => { modulePageSize.value = s; modulePage.value = 1; },
}));
const moduleForm = reactive<{
  id?: string; code: string; name: string; description: string; orderIndex: number; isActive: boolean;
}>({ code: '', name: '', description: '', orderIndex: 0, isActive: true });

const moduleColumns = computed(() => [
  { title: t('pages.settings.DynamicFieldManager.s176'), key: 'orderIndex', width: 70, render: (row: FieldModule) => row.orderIndex },
  { title: t('pages.settings.DynamicFieldManager.s177'), key: 'code', width: 140, render: (row: FieldModule) => row.code },
  { title: t('pages.settings.DynamicFieldManager.s178'), key: 'name', width: 180, render: (row: FieldModule) => row.name },
  { title: t('pages.settings.DynamicFieldManager.s179'), key: 'description', width: 240, render: (row: FieldModule) => row.description || '-' },
  {
    title: t('pages.settings.DynamicFieldManager.s180'), key: 'isActive', width: 90,
    render: (row: FieldModule) => row.isActive ? h(NTag, { type: 'success', size: 'small' }, () => t('pages.settings.DynamicFieldManager.s230')) : h(NTag, { size: 'small' }, () => t('pages.settings.DynamicFieldManager.s231')),
  },
  {
    title: t('pages.settings.DynamicFieldManager.s181'), key: 'action', width: 160, fixed: 'right' as const,
    render: (row: FieldModule) =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'tiny', quaternary: true, onClick: () => openModuleEdit(row) }, { default: () => t('pages.settings.DynamicFieldManager.s232'), icon: () => h(CreateOutline) }),
          h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => confirmDeleteModule(row) }, { default: () => t('pages.settings.DynamicFieldManager.s233'), icon: () => h(TrashOutline) }),
        ],
      }),
  },
]);

async function reloadModules() {
  moduleLoading.value = true;
  try { moduleRows.value = await listModules(currentResource.value); modulePage.value = 1; }
  catch (e: any) { message.error(t('pages.settings.DynamicFieldManager.s252') + extractApiError(e)); }
  finally { moduleLoading.value = false; }
}

/** 2026-09-15 UX：顶部「模块配置」按钮 → 打开页面居中弹窗 */
async function openModuleCenter() {
  await reloadModules();
  moduleCenterVisible.value = true;
}

function openModuleCreate() {
  moduleEditing.value = null;
  Object.assign(moduleForm, { id: undefined, code: '', name: '', description: '', orderIndex: moduleRows.value.length, isActive: true });
  moduleModalVisible.value = true;
}
function openModuleEdit(row: FieldModule) {
  moduleEditing.value = row;
  Object.assign(moduleForm, { id: row.id, code: row.code, name: row.name, description: row.description || '', orderIndex: row.orderIndex, isActive: row.isActive });
  moduleModalVisible.value = true;
}
async function saveModule() {
  if (!moduleForm.code || !moduleForm.name) { message.error(t('pages.settings.DynamicFieldManager.s182')); return; }
  saving.value = true;
  try {
    const payload: any = { code: moduleForm.code, name: moduleForm.name, description: moduleForm.description, orderIndex: moduleForm.orderIndex, isActive: moduleForm.isActive, id: moduleEditing.value?.id };
    await upsertModule(currentResource.value, payload);
    moduleModalVisible.value = false;
    message.success(t('pages.settings.DynamicFieldManager.s183'));
    await reloadModules(); await loadAux();
  } catch (e: any) { message.error(t('pages.settings.DynamicFieldManager.s253') + extractApiError(e)); }
  finally { saving.value = false; }
}
function confirmDeleteModule(row: FieldModule) {
  dialog.warning({
    title: t('pages.settings.DynamicFieldManager.s184'), content: t('pages.settings.DynamicFieldManager.s314', { name: row.name }),
    positiveText: t('pages.settings.DynamicFieldManager.s295'), negativeText: t('pages.settings.DynamicFieldManager.s296'),
    onPositiveClick: async () => {
      try { await deleteModule(currentResource.value, row.id); message.success(t('pages.settings.DynamicFieldManager.s185')); await reloadModules(); await loadAux(); }
      catch (e: any) { message.error(t('pages.settings.DynamicFieldManager.s254') + extractApiError(e)); }
    },
  });
}

// ============ 分组配置 ============
const groupRows = ref<FieldGroup[]>([]);
const groupLoading = ref(false);
const groupModalVisible = ref(false);
const groupCenterVisible = ref(false);
const groupEditing = ref<FieldGroup | null>(null);
const groupPage = ref(1);
const groupPageSize = ref(15);
const groupPagination = computed(() => ({
  page: groupPage.value,
  pageSize: groupPageSize.value,
  pageCount: Math.max(1, Math.ceil(groupRows.value.length / groupPageSize.value)),
  itemCount: groupRows.value.length,
  pageSizes: [10, 15, 20, 50],
  showSizePicker: true,
  showQuickJumper: true,
  prefix: (info: { itemCount?: number }) => h('span', t('pages.settings.DynamicFieldManager.s287', { n: info.itemCount ?? 0 })),
  onChange: (p: number) => { groupPage.value = p; },
  onUpdatePageSize: (s: number) => { groupPageSize.value = s; groupPage.value = 1; },
}));
const groupFilterModule = ref<string>('');
const groupForm = reactive<{
  id?: string; moduleId: string | null; code: string; name: string; orderIndex: number; isActive: boolean;
}>({ moduleId: null, code: '', name: '', orderIndex: 0, isActive: true });

const groupFilterOptions = computed(() => {
  const base = groupFilterModule.value ? groups.value.filter((g) => g.moduleId === groupFilterModule.value) : groups.value;
  return base.map((g) => ({ label: `${g.module?.name || ''} / ${g.name}`, value: g.id }));
});

const groupColumns = computed(() => [
  { title: t('pages.settings.DynamicFieldManager.s186'), key: 'orderIndex', width: 70, render: (row: FieldGroup) => row.orderIndex },
  { title: t('pages.settings.DynamicFieldManager.s187'), key: 'module', width: 140, render: (row: FieldGroup) => row.module?.name || '-' },
  { title: t('pages.settings.DynamicFieldManager.s188'), key: 'code', width: 140, render: (row: FieldGroup) => row.code },
  { title: t('pages.settings.DynamicFieldManager.s189'), key: 'name', width: 180, render: (row: FieldGroup) => row.name },
  {
    title: t('pages.settings.DynamicFieldManager.s190'), key: 'isActive', width: 90,
    render: (row: FieldGroup) => row.isActive ? h(NTag, { type: 'success', size: 'small' }, () => t('pages.settings.DynamicFieldManager.s234')) : h(NTag, { size: 'small' }, () => t('pages.settings.DynamicFieldManager.s235')),
  },
  {
    title: t('pages.settings.DynamicFieldManager.s191'), key: 'action', width: 160, fixed: 'right' as const,
    render: (row: FieldGroup) =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'tiny', quaternary: true, onClick: () => openGroupEdit(row) }, { default: () => t('pages.settings.DynamicFieldManager.s236'), icon: () => h(CreateOutline) }),
          h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => confirmDeleteGroup(row) }, { default: () => t('pages.settings.DynamicFieldManager.s237'), icon: () => h(TrashOutline) }),
        ],
      }),
  },
]);

async function reloadGroups() {
  groupLoading.value = true;
  try {
    // embedded 模式：按默认模块过滤；overview 模式：按筛选模块过滤
    const mid = isEmbedded.value ? (defaultModuleId.value || undefined) : (groupFilterModule.value || undefined);
    groupRows.value = await listGroups(currentResource.value, mid);
    groupPage.value = 1;
  }
  catch (e: any) { message.error(t('pages.settings.DynamicFieldManager.s255') + extractApiError(e)); }
  finally { groupLoading.value = false; }
}
/** 2026-09-15 UX：顶部「分组配置」按钮 → 打开页面居中弹窗 */
async function openGroupCenter() {
  await reloadGroups();
  groupCenterVisible.value = true;
}
function openGroupCreate() {
  groupEditing.value = null;
  Object.assign(groupForm, {
    id: undefined,
    moduleId: isEmbedded.value ? defaultModuleId.value : (groupFilterModule.value || null),
    code: '', name: '', orderIndex: groupRows.value.length, isActive: true,
  });
  groupModalVisible.value = true;
}
function openGroupEdit(row: FieldGroup) {
  groupEditing.value = row;
  Object.assign(groupForm, {
    id: row.id,
    moduleId: isEmbedded.value ? (defaultModuleId.value || row.moduleId) : row.moduleId,
    code: row.code, name: row.name, orderIndex: row.orderIndex, isActive: row.isActive,
  });
  groupModalVisible.value = true;
}
function onGroupModuleChange() { /* 仅用于后续扩展 */ }
async function saveGroup() {
  // 2026-09-24 (兵哥): 分组编码由系统自动生成, 前端不再校验/填写 code; 编辑时原样回传保持不变
  if (!groupForm.moduleId || !groupForm.name) { message.error(t('pages.settings.DynamicFieldManager.s192')); return; }
  saving.value = true;
  try {
    const payload: any = { moduleId: groupForm.moduleId, name: groupForm.name, orderIndex: groupForm.orderIndex, isActive: groupForm.isActive, id: groupEditing.value?.id };
    if (groupEditing.value) payload.code = groupForm.code;
    await upsertGroup(currentResource.value, payload);
    groupModalVisible.value = false;
    message.success(t('pages.settings.DynamicFieldManager.s193'));
    await reloadGroups(); await loadAux();
  } catch (e: any) { message.error(t('pages.settings.DynamicFieldManager.s256') + extractApiError(e)); }
  finally { saving.value = false; }
}
function confirmDeleteGroup(row: FieldGroup) {
  dialog.warning({
    title: t('pages.settings.DynamicFieldManager.s194'), content: t('pages.settings.DynamicFieldManager.s315', { name: row.name }),
    positiveText: t('pages.settings.DynamicFieldManager.s297'), negativeText: t('pages.settings.DynamicFieldManager.s298'),
    onPositiveClick: async () => {
      try { await deleteGroup(currentResource.value, row.id); message.success(t('pages.settings.DynamicFieldManager.s195')); await reloadGroups(); await loadAux(); }
      catch (e: any) { message.error(t('pages.settings.DynamicFieldManager.s257') + extractApiError(e)); }
    },
  });
}

// ============ 联动规则 ============
const linkageRows = ref<FieldLinkageRule[]>([]);
const linkageLoading = ref(false);
const linkageModalVisible = ref(false);
const linkageCenterVisible = ref(false);
const linkageEditing = ref<FieldLinkageRule | null>(null);
const linkagePage = ref(1);
const linkagePageSize = ref(15);
const linkagePagination = computed(() => ({
  page: linkagePage.value,
  pageSize: linkagePageSize.value,
  pageCount: Math.max(1, Math.ceil(linkageRows.value.length / linkagePageSize.value)),
  itemCount: linkageRows.value.length,
  pageSizes: [10, 15, 20, 50],
  showSizePicker: true,
  showQuickJumper: true,
  prefix: (info: { itemCount?: number }) => h('span', t('pages.settings.DynamicFieldManager.s287', { n: info.itemCount ?? 0 })),
  onChange: (p: number) => { linkagePage.value = p; },
  onUpdatePageSize: (s: number) => { linkagePageSize.value = s; linkagePage.value = 1; },
}));
const linkageFilterModule = ref<string>('');
const linkageFields = ref<FieldDefinition[]>([]);
const linkageForm = reactive<{
  id?: string;
  moduleId: string | null;
  name: string;
  conditionMode: LinkageConditionMode;
  conditions: (LinkageCondition & { __key?: string })[];
  actions: (LinkageAction & { __key?: string })[];
}>({
  moduleId: null, name: '', conditionMode: 'ALL', conditions: [], actions: [],
});

const linkageFieldOptions = computed(() => linkageFields.value.map((f) => ({ label: `${f.label} (${f.fieldKey})`, value: f.fieldKey })));

function linkageFieldLabel(fieldKey: string) {
  const f = linkageFields.value.find((it) => it.fieldKey === fieldKey);
  return f ? f.label : fieldKey;
}

function linkageConditionSummary(row: FieldLinkageRule): string {
  const modeLabel = row.conditionMode === 'ANY' ? t('pages.settings.DynamicFieldManager.s271') : t('pages.settings.DynamicFieldManager.s272');
  const conds = (row.conditions || []).map((c) => {
    const op = LINKAGE_OP_OPTIONS.find((o) => o.value === c.op)?.label || c.op;
    const val = Array.isArray(c.value) ? c.value.join('、') : String(c.value ?? '');
    return t('pages.settings.DynamicFieldManager.s304', { field: linkageFieldLabel(c.fieldKey), op, val });
  }).join(t('pages.settings.DynamicFieldManager.s305')) || t('pages.settings.DynamicFieldManager.s306');
  const acts = (row.actions || []).map((a) => {
    const act = LINKAGE_ACTION_OPTIONS.find((o) => o.value === a.actionType)?.label || a.actionType;
    const suffix = a.readOnly ? t('pages.settings.DynamicFieldManager.s307') : '';
    const val = a.value ? ` ${a.value}` : '';
    return t('pages.settings.DynamicFieldManager.s308', { field: linkageFieldLabel(a.targetFieldKey), act, val, suffix });
  }).join('，');
  return t('pages.settings.DynamicFieldManager.s309', { modeLabel, conds, acts });
}

const linkageColumns = computed(() => [
  { title: t('pages.settings.DynamicFieldManager.s196'), key: 'name', width: 160, render: (row: FieldLinkageRule) => row.name || '-' },
  { title: t('pages.settings.DynamicFieldManager.s197'), key: 'summary', render: (row: FieldLinkageRule) => linkageConditionSummary(row) },
  {
    title: t('pages.settings.DynamicFieldManager.s198'), key: 'isActive', width: 90,
    render: (row: FieldLinkageRule) => row.isActive ? h(NTag, { type: 'success', size: 'small' }, () => t('pages.settings.DynamicFieldManager.s238')) : h(NTag, { size: 'small' }, () => t('pages.settings.DynamicFieldManager.s239')),
  },
  {
    title: t('pages.settings.DynamicFieldManager.s199'), key: 'action', width: 160, fixed: 'right' as const,
    render: (row: FieldLinkageRule) =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'tiny', quaternary: true, onClick: () => openLinkageEdit(row) }, { default: () => t('pages.settings.DynamicFieldManager.s240'), icon: () => h(CreateOutline) }),
          h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => confirmDeleteLinkage(row) }, { default: () => t('pages.settings.DynamicFieldManager.s241'), icon: () => h(TrashOutline) }),
        ],
      }),
  },
]);

function conditionValueOptions(fieldKey: string) {
  const f = linkageFields.value.find((it) => it.fieldKey === fieldKey);
  return (f?.options || []).map((o) => ({ label: o.label, value: o.value }));
}

function actionValueOptions(fieldKey: string) {
  const f = linkageFields.value.find((it) => it.fieldKey === fieldKey);
  return (f?.options || []).map((o) => ({ label: o.label, value: o.value }));
}

function newCondition(): LinkageCondition & { __key?: string } {
  return { fieldKey: '', op: 'IN', value: [], __key: Math.random().toString(36).slice(2) };
}

function newAction(): LinkageAction & { __key?: string } {
  return { targetFieldKey: '', actionType: 'SET_VALUE', value: '', readOnly: false, __key: Math.random().toString(36).slice(2) };
}

function addLinkageCondition() { linkageForm.conditions.push(newCondition()); }
function removeLinkageCondition(idx: number) { linkageForm.conditions.splice(idx, 1); }
function addLinkageAction() { linkageForm.actions.push(newAction()); }
function removeLinkageAction(idx: number) { linkageForm.actions.splice(idx, 1); }

function onConditionFieldChange(idx: number) {
  const cond = linkageForm.conditions[idx];
  if (!cond) return;
  cond.value = cond.op === 'IN' || cond.op === 'NOT_IN' ? [] : '';
}

async function reloadLinkage() {
  linkageLoading.value = true;
  try {
    // embedded 模式：按默认模块过滤；overview 模式：按筛选模块过滤
    const mid = isEmbedded.value ? (defaultModuleId.value || undefined) : (linkageFilterModule.value || undefined);
    linkageRows.value = await listLinkageRules(currentResource.value, mid);
    linkagePage.value = 1;
  }
  catch (e: any) { message.error(t('pages.settings.DynamicFieldManager.s258') + extractApiError(e)); }
  finally { linkageLoading.value = false; }
}
/** 2026-09-15 UX：顶部「联动规则」按钮 → 打开页面居中弹窗 */
async function openLinkageCenter() {
  await reloadLinkage();
  linkageCenterVisible.value = true;
}

async function loadLinkageFields(moduleId: string) {
  if (!moduleId) { linkageFields.value = []; return; }
  try { linkageFields.value = await listFields(currentResource.value, { module_id: moduleId }); }
  catch { linkageFields.value = []; }
}

function openLinkageCreate() {
  linkageEditing.value = null;
  Object.assign(linkageForm, {
    id: undefined,
    moduleId: isEmbedded.value ? defaultModuleId.value : (linkageFilterModule.value || null),
    name: '',
    conditionMode: 'ALL', conditions: [newCondition()], actions: [newAction()],
  });
  linkageModalVisible.value = true;
  if (linkageForm.moduleId) loadLinkageFields(linkageForm.moduleId);
}
function openLinkageEdit(row: FieldLinkageRule) {
  linkageEditing.value = row;
  Object.assign(linkageForm, {
    id: row.id,
    moduleId: isEmbedded.value ? (defaultModuleId.value || row.moduleId) : row.moduleId,
    name: row.name,
    conditionMode: row.conditionMode || 'ALL',
    conditions: (row.conditions || []).map((c) => ({ ...c, __key: Math.random().toString(36).slice(2) })),
    actions: (row.actions || []).map((a) => ({ ...a, __key: Math.random().toString(36).slice(2) })),
  });
  linkageModalVisible.value = true;
  loadLinkageFields(row.moduleId);
}
function onLinkageModuleChange() { loadLinkageFields(linkageForm.moduleId || ''); }

async function saveLinkage() {
  if (!linkageForm.moduleId) { message.error(t('pages.settings.DynamicFieldManager.s200')); return; }
  if (!linkageForm.name.trim()) { message.error(t('pages.settings.DynamicFieldManager.s201')); return; }
  if (!linkageForm.conditions.length || linkageForm.conditions.some((c) => !c.fieldKey)) {
    message.error(t('pages.settings.DynamicFieldManager.s202')); return;
  }
  if (!linkageForm.actions.length || linkageForm.actions.some((a) => !a.targetFieldKey)) {
    message.error(t('pages.settings.DynamicFieldManager.s203')); return;
  }
  saving.value = true;
  try {
    const payload: any = {
      moduleId: linkageForm.moduleId,
      name: linkageForm.name.trim(),
      conditionMode: linkageForm.conditionMode,
      conditions: linkageForm.conditions.map(({ __key, ...c }) => c),
      actions: linkageForm.actions.map(({ __key, ...a }) => a),
      id: linkageEditing.value?.id,
    };
    await upsertLinkageRule(currentResource.value, payload);
    linkageModalVisible.value = false;
    message.success(t('pages.settings.DynamicFieldManager.s204'));
    await reloadLinkage();
  } catch (e: any) { message.error(t('pages.settings.DynamicFieldManager.s259') + extractApiError(e)); }
  finally { saving.value = false; }
}
function confirmDeleteLinkage(row: FieldLinkageRule) {
  dialog.warning({
    title: t('pages.settings.DynamicFieldManager.s205'), content: t('pages.settings.DynamicFieldManager.s316', { name: row.name || t('pages.settings.DynamicFieldManager.s317') }),
    positiveText: t('pages.settings.DynamicFieldManager.s299'), negativeText: t('pages.settings.DynamicFieldManager.s300'),
    onPositiveClick: async () => {
      try { await deleteLinkageRule(currentResource.value, row.id); message.success(t('pages.settings.DynamicFieldManager.s206')); await reloadLinkage(); }
      catch (e: any) { message.error(t('pages.settings.DynamicFieldManager.s260') + extractApiError(e)); }
    },
  });
}

// ============ 导出 / 导入 ============
const exportOptions = [
  { label: t('pages.settings.DynamicFieldManager.s285'), key: 'json' },
  { label: t('pages.settings.DynamicFieldManager.s286'), key: 'csv' },
];
function onExportSelect(key: string) {
  downloadExport(currentResource.value, key as 'json' | 'csv', filterModule.value || undefined, filterGroup.value || undefined)
    .then(() => message.success(t('pages.settings.DynamicFieldManager.s207')))
    .catch((e: any) => message.error(t('pages.settings.DynamicFieldManager.s261') + extractApiError(e)));
}

const importModalVisible = ref(false);
const importFormat = ref<'json' | 'csv'>('json');
const importContent = ref('');
const importing = ref(false);
const importResult = ref<{ success: boolean; created: number; updated: number; errors: number } | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const selectedFileName = ref('');

async function downloadTemplateFile() {
  try {
    await downloadTemplate(currentResource.value, importFormat.value);
    message.success(t('pages.settings.DynamicFieldManager.s208'));
  } catch (e: any) {
    message.error(t('pages.settings.DynamicFieldManager.s262') + extractApiError(e));
  }
}

async function onFilePicked(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  // 按扩展名自动识别格式
  const ext = file.name.toLowerCase().split('.').pop();
  if (ext === 'csv') importFormat.value = 'csv';
  else if (ext === 'json') importFormat.value = 'json';
  try {
    importContent.value = await file.text();
    selectedFileName.value = file.name;
    message.success(t('pages.settings.DynamicFieldManager.s301', { name: file.name, len: importContent.value.length }));
  } catch (err: any) {
    message.error(t('pages.settings.DynamicFieldManager.s263') + (err?.message || err));
  } finally {
    input.value = ''; // 允许重复选择同一文件
  }
}

async function runImport() {
  if (!importContent.value.trim()) { message.error(t('pages.settings.DynamicFieldManager.s209')); return; }
  importing.value = true;
  importResult.value = null;
  try {
    const res = await importFields(currentResource.value, importFormat.value, importContent.value);
    importResult.value = res;
    if (res.errors > 0) message.warning(t('pages.settings.DynamicFieldManager.s302', { created: res.created, updated: res.updated, errors: res.errors }));
    else message.success(t('pages.settings.DynamicFieldManager.s303', { created: res.created, updated: res.updated }));
    await reloadFields(); await loadAux();
  } catch (e: any) { message.error(t('pages.settings.DynamicFieldManager.s264') + extractApiError(e)); }
  finally { importing.value = false; }
}

// ============ 辅助加载 ============
const moduleOptions = computed(() => [
  { label: t('pages.settings.DynamicFieldManager.s210'), value: '' },
  ...modules.value.map((m) => ({ label: m.name, value: m.id })),
]);

/** embedded 模式：进入业务模块时确保默认模块存在（后端自动创建），作为分组/联动的 FK 归属 */
async function ensureDefault() {
  if (!isEmbedded.value) return;
  try {
    const m = await ensureDefaultModule(currentResource.value, props.displayName || currentResource.value);
    defaultModuleId.value = m.id;
  } catch (e: any) {
    message.error(t('pages.settings.DynamicFieldManager.s265') + extractApiError(e));
  }
}

async function loadAux() {
  try {
    modules.value = await listModules(currentResource.value);
    groups.value = await listGroups(currentResource.value);
  } catch { /* 辅助数据加载失败不阻塞主表 */ }
}

/** overview 模式切换资源时全量刷新 */
async function onResourceChange() {
  defaultModuleId.value = null;
  filterModule.value = '';
  groupFilterModule.value = '';
  linkageFilterModule.value = '';
  await loadAux();
  await reloadFields();
  await reloadModules();
  await reloadGroups();
  await reloadLinkage();
}

onMounted(async () => {
  if (isEmbedded.value) await ensureDefault();
  await loadAux();
  await reloadFields();
  if (!isEmbedded.value) await reloadModules();
  await reloadGroups();
  await reloadLinkage();
});
</script>

<style scoped>
.page-container {
  display: flex; flex-direction: column; height: 100%; min-height: 0; padding: 0;
}
.page-header { flex-shrink: 0; display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-4); }
.res-label { color: var(--ink-soft); font-size: var(--fs-14); }
/* 页面级不滚动: 标题/筛选固定, 仅分组卡片区内部滚动 */
.page-body {
  flex: 1; min-height: 0;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.filter-row { flex-shrink: 0; margin-bottom: var(--space-3); }
.dynamic-field-settings { display: flex; flex-direction: column; gap: var(--space-3); }
.field-key-readonly {
  display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap;
  font-size: var(--text-meta);
}
.field-key-readonly code {
  padding: 2px 6px; border-radius: 4px;
  background: var(--g1); color: var(--ink-soft);
  font-variant-numeric: tabular-nums;
}
.field-key-hint { color: var(--ink-faint); }
/* 数字类「数值约束」单行整合: 每项含小标签 + 控件 */
.num-field { display: flex; flex-direction: column; gap: 4px; }
.num-label { font-size: var(--fs-12, 12px); color: var(--ink-soft); }
.linkage-row {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) 0; border-bottom: 1px dashed var(--border-hairline);
}
.linkage-row:last-child { border-bottom: none; }
.linkage-index {
  width: 18px; height: 18px; border-radius: 50%;
  background: var(--g1); color: var(--ink-soft);
  font-size: var(--fs-12); display: flex; align-items: center; justify-content: center;
}
/* 字段定义：分组卡片视图
 * 卡片内嵌 n-data-table（自带 td padding），卡片自身不再加 padding，避免双层留白；
 * 模块之间的区分靠「卡片边框 + 背景 + 阴影 + 头部底色带」，不靠额外留白。 */
.field-groups {
  flex: 1 1 auto; min-height: 0;          /* 撑满 page-body 剩余高度并在此滚动（移除 Tabs 后必须补回） */
  display: flex; flex-direction: column; gap: var(--space-4);
  overflow-y: auto;
  scrollbar-width: none;                  /* Firefox：隐藏滚动条轨道，避免右侧固定占位 */
}
.field-groups::-webkit-scrollbar { width: 0; background: transparent; }
.field-group-card {
  flex-shrink: 0;                         /* 关键：禁止 flex 收缩。默认 shrink:1 会把卡片压扁，配合 overflow:hidden 直接裁掉表格 → 只剩头部堆叠（模块“糊在一起”的成因之一） */
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--glass-bg-card);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}
.field-group-head {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--g1);                  /* 头部底色带：分组标题与表格内容一眼可分 */
  border-bottom: 1px solid var(--border-hairline);
}
.fg-title { font-weight: 600; font-size: var(--fs-16); }
.fg-spacer { flex: 1; }
/* 字段权限管理弹窗 */
.perm-desc { color: var(--ink-soft); margin-bottom: var(--space-3); line-height: 1.5; }
.perm-radio { padding: var(--space-1) 0; }
/* 分组卡片 / 居中弹窗内 n-data-table td 左右内边距（Naive 默认 12px 过窄，内容视觉贴边） */
.field-group-card :deep(.n-data-table-td),
.field-group-card :deep(.n-data-table-th),
.df-center-modal :deep(.n-data-table-td),
.df-center-modal :deep(.n-data-table-th) {
  padding-left: var(--space-4);
  padding-right: var(--space-4);
}
/* 居中弹窗 body 加足内部呼吸空间，避免表格贴弹窗内壁 */
.df-center-modal :deep(.n-card__content) { padding: var(--space-5) var(--space-6) 0; }
/* 2026-09-16 (兵哥): 组合字段子字段编辑器行 — 横向排布 key/label/type/必填 */
.sub-field-row {
  display: flex; align-items: center; gap: var(--space-2); width: 100%;
}
.sub-field-hint { margin-top: 4px; line-height: 1.4; }
/* 字段宽度与微调（替代散落的 width:NNNpx / flex:1 行内样式） */
.df-input-min-max   { width: 130px; }
.df-input-group-key { width: 160px; }
.df-input-select    { width: 200px; }
.df-flex-grow       { flex: 1; }
.df-width-full      { width: 100%; }
</style>
