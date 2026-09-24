<template>
  <div class="page-container dynamic-field-settings">
    <div class="page-header">
      <div>
        <h1 class="page-title">
          {{ isEmbedded && props.displayName ? props.displayName + ' · 动态字段' : '动态字段定义' }}
        </h1>
        <p class="page-subtitle">
          {{ isEmbedded
            ? '字段定义 / 分组 / 联动规则（已绑定到当前模块，无需再配置模块）'
            : 'G42 - 元数据驱动的字段配置：字段 / 模块 / 分组 / 联动规则' }}
        </p>
      </div>
      <!-- 顶部操作区：资源切换 + 配置入口（页面无 Tab，配三个按钮触发居中弹窗） -->
      <n-space align="center" :wrap="false">
        <n-space v-if="!isEmbedded" align="center" :wrap="false">
          <span class="res-label">{ t('pages.settings.DynamicFieldManager.s1') }</span>
          <n-select
            v-model:value="currentResource"
            :options="resourceOptions"
            style="width: 160px"
            @update:value="onResourceChange"
          />
        </n-space>
        <n-divider v-if="!isEmbedded" vertical />
        <n-button v-if="!isEmbedded" @click="openModuleCenter">
          <template #icon><n-icon :component="AppsOutline" /></template>模块配置
        </n-button>
        <n-button @click="openGroupCenter">
          <template #icon><n-icon :component="ListOutline" /></template>分组配置
        </n-button>
        <n-button @click="openLinkageCenter">
          <template #icon><n-icon :component="GitNetworkOutline" /></template>联动规则
        </n-button>
      </n-space>
    </div>

    <div class="page-body">
      <!-- 页面无 Tab，「字段定义」全量铺开（分组卡片视图） -->
      <n-space class="filter-row" :wrap="true">
        <n-select v-if="!isEmbedded" v-model:value="filterModule" :options="moduleOptions" style="width: 200px" placeholder="按模块筛选" @update:value="reloadFields" />
        <n-select v-model:value="filterGroup" :options="groupFilterOptions" style="width: 200px" placeholder="按分组筛选" @update:value="reloadFields" />
        <n-button :loading="loading" @click="reloadFields">刷新</n-button>
        <n-button type="primary" @click="openFieldCreate()">
          <template #icon><n-icon :component="AddOutline" /></template>新建字段
        </n-button>
        <n-dropdown :options="exportOptions" @select="onExportSelect">
          <n-button>导出字段</n-button>
        </n-dropdown>
        <n-button @click="importModalVisible = true">导入字段</n-button>
      </n-space>

      <!-- 分组卡片视图：按字段分组(FieldGroup)聚合，每组独立卡片 -->
      <div class="field-groups">
        <div v-for="g in groupedFields" :key="g.key" class="field-group-card">
          <div class="field-group-head">
            <span class="fg-title">{{ g.name }}</span>
            <n-tag :bordered="false" size="small" type="info">全局</n-tag>
            <n-button
              size="small" secondary type="primary"
              @click="openFieldCreate(g.key === 'ungrouped' ? null : g.key)"
            >
              <template #icon><n-icon :component="AddOutline" /></template>添加字段
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
        <n-empty v-if="!groupedFields.length && !loading" description="暂无字段" />
      </div>
    </div>

    <!-- ============ 字段 新建/编辑 Modal ============ -->
      <n-modal
        v-model:show="fieldModalVisible"
        preset="card"
        :title="fieldEditing ? '编辑字段' : '新建字段'"
        style="width: 680px; max-width: 92vw;"
      >
        <n-form :model="fieldForm" label-placement="left" label-width="100px">
          <n-form-item label="字段名称" required>
            <n-input v-model:value="fieldForm.label" placeholder="e.g. 身份证号" />
          </n-form-item>
          <n-form-item label="英文名称">
            <n-input v-model:value="fieldForm.labelEn" placeholder="e.g. id_card_no" />
          </n-form-item>
          <n-form-item label="字段类型" required>
            <n-select v-model:value="fieldForm.fieldType" :options="FIELD_TYPE_OPTIONS" />
          </n-form-item>
          <!-- 2026-09-15 (兵哥) 日期型字段：格式精度单选(年/年月/年月日)，范围类型渲染区间选择器 -->
          <n-form-item v-if="isDateType" label="日期格式">
            <n-space align="center" :size="8">
              <n-radio-group v-model:value="fieldForm.dateFormat">
                <n-radio-button
                  v-for="opt in DATE_FORMAT_OPTIONS"
                  :key="opt.value"
                  :value="opt.value"
                  :label="opt.label"
                />
              </n-radio-group>
              <n-text depth="3">{{ fieldForm.fieldType === 'DATE_RANGE' ? '范围填写时选择起止区间' : '填写时按所选精度选择日期' }}</n-text>
            </n-space>
          </n-form-item>
          <!-- 2026-09-15 行政区划型字段：层级精度 + 国家开关 + 实时级联预览 (数据源: G46 码表库) -->
          <template v-if="isRegionType">
            <n-form-item label="层级">
              <n-radio-group v-model:value="fieldForm.regionLevel">
                <n-space>
                  <n-radio-button v-for="opt in REGION_LEVEL_OPTIONS" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </n-radio-button>
                </n-space>
              </n-radio-group>
            </n-form-item>
            <n-form-item label="启用国家">
              <n-space align="center" :size="8">
                <n-switch v-model:value="fieldForm.withCountry" />
                <n-text depth="3">开启后填写时先选国家，再选行政区划</n-text>
              </n-space>
            </n-form-item>
            <n-form-item label="级联预览">
              <RegionCascader
                :level="fieldForm.regionLevel"
                :with-country="fieldForm.withCountry"
                :value="fieldForm.regionPreviewValue"
                :disabled="true"
                @update:value="(v) => (fieldForm.regionPreviewValue = v)"
              />
              <n-text v-if="!fieldForm.regionPreviewValue" depth="3" class="rc-hint">
                预览为只读示例，候选人填写时实际可选
              </n-text>
            </n-form-item>
          </template>
          <!-- embedded 模式：字段归属当前业务模块，隐藏模块选择，由组件强制绑定默认模块 -->
          <n-form-item v-if="!isEmbedded" label="归属模块">
            <n-select
              v-model:value="fieldForm.moduleId"
              :options="modules.map((m) => ({ label: m.name, value: m.id }))"
              placeholder="选择模块（可选）"
              clearable
              @update:value="onFieldModuleChange"
            />
          </n-form-item>
          <n-form-item label="字段分组">
            <n-select
              v-model:value="fieldForm.groupId"
              :options="fieldGroupOptions"
              placeholder="选择分组（可选）"
              clearable
              :disabled="!fieldForm.moduleId"
            />
          </n-form-item>
          <n-form-item label="占位提示">
            <n-input v-model:value="fieldForm.placeholder" placeholder="placeholder" />
          </n-form-item>
          <n-form-item label="帮助文本">
            <n-input v-model:value="fieldForm.helpText" placeholder="helpText" />
          </n-form-item>
          <!-- 2026-09-24 (兵哥) 限制条件: 按字段类型差异化校验配置
               文本类=最大字数 / 数字类=范围+步长+小数位+单位 / 列表型=可选范围 / 日期型=日期可选范围; 通用=错误提示
               邮箱/电话/URL 等专用格式由字段类型层固有约束, 无配置项 -->
          <template v-if="isLimitTextType">
            <n-form-item label="最大字数">
              <n-input-number
                v-model:value="fieldForm.validation.maxLength"
                :min="1" :precision="0" clearable
                placeholder="不限制" style="width: 200px"
              />
            </n-form-item>
          </template>
          <template v-else-if="isLimitNumberType">
            <n-form-item label="数值约束">
              <n-space align="center" :size="10" wrap>
                <div class="num-field">
                  <span class="num-label">最小值</span>
                  <n-input-number v-model:value="fieldForm.validation.min" placeholder="不限制" style="width: 130px" />
                </div>
                <div class="num-field">
                  <span class="num-label">最大值</span>
                  <n-input-number v-model:value="fieldForm.validation.max" placeholder="不限制" style="width: 130px" />
                </div>
                <div class="num-field">
                  <span class="num-label">步长</span>
                  <n-input-number v-model:value="fieldForm.validation.step" :min="0" placeholder="不限制" style="width: 110px" />
                </div>
                <div class="num-field">
                  <span class="num-label">小数位数</span>
                  <n-input-number v-model:value="fieldForm.validation.decimals" :min="0" :precision="0" clearable placeholder="不限制" style="width: 110px" />
                </div>
                <div class="num-field">
                  <span class="num-label">单位</span>
                  <n-input v-model:value="fieldForm.validation.unit" placeholder="如 人/元/天" style="width: 140px" />
                </div>
              </n-space>
            </n-form-item>
          </template>
          <template v-else-if="isLimitOptionType">
            <n-form-item label="可选范围">
              <n-select
                v-model:value="fieldForm.validation.allowedValues"
                multiple clearable
                :options="allowedValueOptions"
                placeholder="不限制 (默认全部选项可选)"
              />
            </n-form-item>
          </template>
          <template v-else-if="isLimitDateType">
            <n-form-item label="日期可选范围">
              <n-space align="center" :size="10">
                <n-date-picker
                  v-model:value="fieldForm.validation.minDate"
                  type="date"
                  value-format="yyyy-MM-dd"
                  clearable
                  placeholder="起始日期"
                  style="width: 200px"
                />
                <n-text depth="3">至</n-text>
                <n-date-picker
                  v-model:value="fieldForm.validation.maxDate"
                  type="date"
                  value-format="yyyy-MM-dd"
                  clearable
                  placeholder="结束日期"
                  style="width: 200px"
                />
              </n-space>
            </n-form-item>
          </template>
          <n-form-item v-if="hasValidationConfig" label="错误提示">
            <n-input v-model:value="fieldForm.validation.message" placeholder="校验不通过时的提示文案 (留空使用默认文案)" />
          </n-form-item>
          <!-- 确认题专属字段：确认内容 + 确认声明（中英双语） -->
          <template v-if="isConfirmType">
            <n-form-item label="确认内容" required>
              <n-input v-model:value="fieldForm.confirmationContent" type="textarea" placeholder="e.g. 本人承诺所填信息真实有效" />
            </n-form-item>
            <n-form-item label="确认内容(英文)">
              <n-input v-model:value="fieldForm.confirmationContentEn" type="textarea" placeholder="e.g. I certify the information is true" />
            </n-form-item>
            <n-form-item label="确认声明">
              <n-input v-model:value="fieldForm.confirmationDeclaration" type="textarea" placeholder="确认声明文案" />
            </n-form-item>
            <n-form-item label="确认声明(英文)">
              <n-input v-model:value="fieldForm.confirmationDeclarationEn" type="textarea" placeholder="英文确认声明文案" />
            </n-form-item>
          </template>
          <!-- 2026-09-16 (兵哥) 组合字段: 子字段编辑器(可含附件子字段, 页面呈现为组合展示卡) -->
          <template v-if="isCompositeType">
            <n-form-item label="子字段" required>
              <n-space vertical :size="8" style="width: 100%">
                <n-dynamic-input
                  v-model:value="fieldForm.subFields"
                  :on-create="onCreateSubField"
                  item-style="margin-bottom: 8px;"
                >
                  <template #default="{ value }">
                    <div class="sub-field-row">
                      <n-input v-model:value="value.key" placeholder="key(英文, 如 id_front)" style="width: 30%" />
                      <n-input v-model:value="value.label" placeholder="标签(如 身份证正面)" style="width: 28%" />
                      <n-select v-model:value="value.type" :options="SUBFIELD_TYPE_OPTIONS" style="width: 26%" />
                      <n-switch v-model:value="value.required" title="必填" />
                    </div>
                  </template>
                </n-dynamic-input>
                <n-text depth="3" class="sub-field-hint">
                  子字段类型支持 文本/数字/多行/附件/日期/手机号/邮箱；附件子字段在页面应用中呈现为上传控件
                </n-text>
              </n-space>
            </n-form-item>
          </template>
          <n-form-item v-if="fieldNeedsOptions" label="选项来源">
            <n-space vertical :size="8" style="width: 100%">
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
                placeholder="选择字典类型"
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
保存后，选项将从「数据字典 · {{ fieldForm.optionsSource.key }}」动态加载（实时同步字典条目）。
</n-alert>
              <!-- 院校库/专业库/码表库提示 -->
              <n-alert
                v-else-if="sourceHint"
                type="info"
                :show-icon="true"
              >
保存后，{{ sourceHint }}。
</n-alert>
            </n-space>
          </n-form-item>
          <n-form-item v-if="fieldNeedsOptions && showManualOptions" label="选项">
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
          <n-form-item v-if="fieldNeedsOptions && sourceType === 'dictionary'" label="预览">
            <n-space>
              <n-tag v-for="o in dictionaryPreviewOptions" :key="o.value" size="small">{{ o.label }}</n-tag>
              <n-text v-if="!dictionaryPreviewOptions.length" depth="3">请选择字典类型以预览选项</n-text>
            </n-space>
          </n-form-item>
          <n-form-item v-if="isListType && showManualOptions" label="预览" class="list-preview-item">
            <div class="list-preview-wrap">
              <FieldListOptions
                v-model="fieldPreviewValue"
                :options="fieldForm.options"
                :multiple="fieldForm.fieldType === 'LIST_MULTI'"
                :disabled="!fieldForm.options.length"
              />
              <n-text v-if="!fieldForm.options.length" depth="3" class="list-preview-hint">先填写上方选项以预览排列效果</n-text>
            </div>
          </n-form-item>
          <!-- Key 由系统自动生成, 新建时对用户隐藏; 编辑时以只读小字披露, 供开发对接查阅 -->
          <n-form-item v-if="fieldEditing" label="字段 Key">
            <n-text depth="3" class="field-key-readonly">
              <code>{{ fieldForm.fieldKey }}</code>
              <span class="field-key-hint">系统生成，供开发对接使用，不可修改</span>
            </n-text>
          </n-form-item>
        </n-form>
        <template #action>
          <n-space justify="end">
            <n-button @click="fieldModalVisible = false">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="saveField">保存字段</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 字段权限管理 Modal ============ -->
      <n-modal
        v-model:show="permModalVisible"
        preset="card"
        title="字段权限管理"
        style="width: 520px; max-width: 92vw;"
      >
        <p class="perm-desc">仅当满足以下条件时，候选人详情页才完整显示该附件</p>
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
            <n-button @click="permModalVisible = false">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="permSaving" @click="savePermission">确定</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 模块配置 页面居中大弹窗（取代原 Tab） ============ -->
      <n-modal
        v-if="!isEmbedded"
        v-model:show="moduleCenterVisible"
        preset="card"
        title="模块配置"
        :mask-closable="false"
        style="width: 960px; max-width: 96vw;"
        class="df-center-modal"
      >
        <n-space class="filter-row" :wrap="true">
          <n-button :loading="moduleLoading" @click="reloadModules">刷新</n-button>
          <n-button type="primary" @click="openModuleCreate">
            <template #icon><n-icon :component="AddOutline" /></template>新建模块
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
            <n-button @click="moduleCenterVisible = false">关闭</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 模块 Modal（仅 overview 模式使用） ============ -->
      <n-modal
        v-if="!isEmbedded"
        v-model:show="moduleModalVisible"
        preset="card"
        :title="moduleEditing ? '编辑模块' : '新建模块'"
        style="width: 560px; max-width: 92vw;"
      >
        <n-form :model="moduleForm" label-placement="left" label-width="100px">
          <n-form-item label="模块编码" required>
            <n-input v-model:value="moduleForm.code" placeholder="e.g. basic" :disabled="!!moduleEditing" />
          </n-form-item>
          <n-form-item label="模块名称" required>
            <n-input v-model:value="moduleForm.name" placeholder="e.g. 基本信息" />
          </n-form-item>
          <n-form-item label="描述">
            <n-input v-model:value="moduleForm.description" type="textarea" placeholder="模块说明" />
          </n-form-item>
          <n-form-item label="排序">
            <n-input-number v-model:value="moduleForm.orderIndex" :min="0" />
          </n-form-item>
          <n-form-item label="启用">
            <n-switch v-model:value="moduleForm.isActive" />
          </n-form-item>
        </n-form>
        <template #action>
          <n-space justify="end">
            <n-button @click="moduleModalVisible = false">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="saveModule">保存模块</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 分组配置 页面居中大弹窗（取代原 Tab） ============ -->
      <n-modal
        v-model:show="groupCenterVisible"
        preset="card"
        title="分组配置"
        :mask-closable="false"
        style="width: 960px; max-width: 96vw;"
        class="df-center-modal"
      >
        <n-space class="filter-row" :wrap="true">
          <n-select v-if="!isEmbedded" v-model:value="groupFilterModule" :options="moduleOptions" style="width: 200px" placeholder="按模块筛选" @update:value="reloadGroups" />
          <n-button :loading="groupLoading" @click="reloadGroups">刷新</n-button>
          <n-button type="primary" @click="openGroupCreate">
            <template #icon><n-icon :component="AddOutline" /></template>新建分组
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
            <n-button @click="groupCenterVisible = false">关闭</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 分组 Modal ============ -->
      <n-modal
        v-model:show="groupModalVisible"
        preset="card"
        :title="groupEditing ? '编辑分组' : '新建分组'"
        style="width: 560px; max-width: 92vw;"
      >
        <n-form :model="groupForm" label-placement="left" label-width="100px">
          <!-- embedded 模式：分组归属当前业务模块，隐藏模块选择，由组件强制绑定默认模块 -->
          <n-form-item v-if="!isEmbedded" label="归属模块" required>
            <n-select
              v-model:value="groupForm.moduleId"
              :options="modules.map((m) => ({ label: m.name, value: m.id }))"
              placeholder="选择模块"
              @update:value="onGroupModuleChange"
            />
          </n-form-item>
          <!-- 2026-09-24 (兵哥): 分组编码由系统自动生成, 新建时不再让用户填写; 编辑仅只读展示 -->
          <n-form-item v-if="groupEditing" label="分组编码">
            <n-input v-model:value="groupForm.code" placeholder="系统自动生成" disabled />
          </n-form-item>
          <n-form-item label="分组名称" required>
            <n-input v-model:value="groupForm.name" placeholder="e.g. 联系方式" />
          </n-form-item>
          <n-form-item label="排序">
            <n-input-number v-model:value="groupForm.orderIndex" :min="0" />
          </n-form-item>
          <n-form-item label="启用">
            <n-switch v-model:value="groupForm.isActive" />
          </n-form-item>
        </n-form>
        <template #action>
          <n-space justify="end">
            <n-button @click="groupModalVisible = false">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="saveGroup">保存分组</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 联动规则 页面居中大弹窗（取代原 Tab） ============ -->
      <n-modal
        v-model:show="linkageCenterVisible"
        preset="card"
        title="联动规则"
        :mask-closable="false"
        style="width: 1024px; max-width: 96vw;"
        class="df-center-modal"
      >
        <n-space class="filter-row" :wrap="true">
          <n-select v-if="!isEmbedded" v-model:value="linkageFilterModule" :options="moduleOptions" style="width: 200px" placeholder="按模块筛选" @update:value="reloadLinkage" />
          <n-button :loading="linkageLoading" @click="reloadLinkage">刷新</n-button>
          <n-button type="primary" @click="openLinkageCreate">
            <template #icon><n-icon :component="AddOutline" /></template>新建规则
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
            <n-button @click="linkageCenterVisible = false">关闭</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 联动规则 Modal ============ -->
      <n-modal
        v-model:show="linkageModalVisible"
        preset="card"
        :title="linkageEditing ? '编辑规则' : '新建规则'"
        style="width: 760px; max-width: 96vw;"
      >
        <n-form :model="linkageForm" label-placement="left" label-width="100px">
          <!-- embedded 模式：规则归属当前业务模块，隐藏模块选择，由组件强制绑定默认模块 -->
          <n-form-item v-if="!isEmbedded" label="所属模块" required>
            <n-select
              v-model:value="linkageForm.moduleId"
              :options="modules.map((m) => ({ label: m.name, value: m.id }))"
              placeholder="选择模块"
              @update:value="onLinkageModuleChange"
            />
          </n-form-item>

          <!-- 条件区域 -->
          <n-form-item label="条件" required>
            <n-space vertical style="width: 100%">
              <n-radio-group v-model:value="linkageForm.conditionMode">
                <n-radio value="ALL">满足以下所有条件</n-radio>
                <n-radio value="ANY">满足以下任一条件</n-radio>
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
                  placeholder="字段"
                  style="width: 160px"
                  clearable
                  @update:value="() => onConditionFieldChange(idx)"
                />
                <n-select
                  v-model:value="cond.op"
                  :options="LINKAGE_OP_OPTIONS"
                  placeholder="操作符"
                  style="width: 130px"
                />
                <n-select
                  v-if="cond.op === 'IN' || cond.op === 'NOT_IN'"
                  v-model:value="cond.value"
                  :options="conditionValueOptions(cond.fieldKey)"
                  placeholder="选择值(多选)"
                  multiple
                  tag
                  filterable
                  style="flex: 1"
                />
                <n-input
                  v-else
                  :value="String(cond.value ?? '')"
                  placeholder="值"
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
                <template #icon><n-icon :component="AddOutline" /></template>添加条件
              </n-button>
            </n-space>
          </n-form-item>

          <!-- 动作区域 -->
          <n-form-item label="执行动作" required>
            <n-space vertical style="width: 100%">
              <div
                v-for="(act, idx) in linkageForm.actions"
                :key="act.__key || idx"
                class="linkage-row"
              >
                <span class="linkage-index">{{ idx + 1 }}</span>
                <n-select
                  v-model:value="act.targetFieldKey"
                  :options="linkageFieldOptions"
                  placeholder="目标字段"
                  style="width: 160px"
                  clearable
                />
                <n-select
                  v-model:value="act.actionType"
                  :options="LINKAGE_ACTION_OPTIONS"
                  placeholder="动作"
                  style="width: 130px"
                />
                <n-select
                  v-if="act.actionType === 'SET_VALUE' || act.actionType === 'CASCADE_OPTIONS'"
                  v-model:value="act.value"
                  :options="actionValueOptions(act.targetFieldKey)"
                  placeholder="值"
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
                <n-checkbox v-model:checked="act.readOnly">只读</n-checkbox>
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
                <template #icon><n-icon :component="AddOutline" /></template>添加动作
              </n-button>
            </n-space>
          </n-form-item>
        </n-form>
        <template #action>
          <n-space justify="end">
            <n-button @click="linkageModalVisible = false">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="saveLinkage">保存规则</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 导入 Modal ============ -->
      <n-modal
        v-model:show="importModalVisible"
        preset="card"
        title="导入字段"
        style="width: 680px; max-width: 94vw;"
      >
        <n-space vertical :size="12">
          <n-alert type="info" :show-icon="true">
            支持 JSON 数组或 CSV 文本。CSV 需包含表头：
            <code>field_key,label,field_type,module_code,group_code,is_required,...</code>
            可先下载模板对照填写。
          </n-alert>
          <n-space :wrap="false" :size="12" align="center">
            <n-radio-group v-model:value="importFormat">
              <n-radio value="json">JSON</n-radio>
              <n-radio value="csv">CSV</n-radio>
            </n-radio-group>
            <n-button size="small" secondary @click="downloadTemplateFile">下载导入模板</n-button>
            <n-button size="small" secondary @click="fileInput?.click()">选择文件</n-button>
            <input
              ref="fileInput"
              type="file"
              accept=".json,.csv,application/json,text/csv"
              style="display: none"
              @change="onFilePicked"
            />
            <n-text v-if="selectedFileName" depth="3">已选：{{ selectedFileName }}</n-text>
          </n-space>
          <n-input
            v-model:value="importContent"
            type="textarea"
            placeholder="粘贴 JSON 数组或 CSV 文本，或点击「选择文件」从本地读取"
            :autosize="{ minRows: 8, maxRows: 16 }"
          />
          <n-text v-if="importResult" depth="3">导入结果：新增 {{ importResult.created }} · 更新 {{ importResult.updated }} · 失败 {{ importResult.errors }}</n-text>
        </n-space>
        <template #action>
          <n-space justify="end">
            <n-button @click="importModalVisible = false">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="importing" @click="runImport">开始导入</n-button>
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
  NRadioGroup, NRadio, NCheckbox, NAlert, NText, useMessage, useDialog,
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
import { TEXT_MAXLENGTH_TYPES, NUMBER_TYPES, OPTION_TYPES, DATE_TYPES } from '@/utils/fieldValidation';
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
  { label: '候选人', value: 'Candidate' },
  { label: '招聘需求', value: 'Demand' },
  { label: '职位', value: 'Position' },
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
  prefix: (info: { itemCount?: number }) => h('span', `共 ${info.itemCount} 条`),
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
});

const fieldNeedsOptions = computed(() => ['SELECT', 'MULTISELECT', 'LIST_SINGLE', 'LIST_MULTI'].includes(fieldForm.fieldType));

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
    return {
      minDate: v.minDate ? String(v.minDate).slice(0, 10) : null,
      maxDate: v.maxDate ? String(v.maxDate).slice(0, 10) : null,
      message: v.message || '',
    };
  }
  return {};
}

// 2026-09-15 选项来源 (兵哥): 下拉/列表型字段除手动维护选项外, 可指定数据源动态解析
// 拍平为单层下拉（兵哥 9-15 反馈: 院校/专业库、码表库不再做二级级联, 直接拆成独立选项）
// 复合 value 形式 type:key, 选择即写入 fieldForm.optionsSource.{type,key}, 后端零改动兼容
const OPTION_SOURCE_OPTIONS = [
  { label: '自定义（手动维护）', value: 'custom' },
  { label: '数据字典', value: 'dictionary' },
  { label: '专业库', value: 'library:major' },
  { label: '院校库', value: 'library:school' },
  { label: '国家/地区', value: 'code_table:country' },
  { label: '民族', value: 'code_table:ethnicity' },
  { label: '语言类型', value: 'code_table:language' },
];
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
  if (sourceType.value === 'library') {
    if (fieldForm.optionsSource?.key === 'school') return '院校库约 2744 所院校，候选人在填写时支持 keyword 服务端搜索';
    if (fieldForm.optionsSource?.key === 'major') return '专业库约 1976 个专业，按名称排序';
    return '请选择子类型';
  }
  if (sourceType.value === 'code_table') {
    if (fieldForm.optionsSource?.key === 'country') return '国家与地区码表，约 250 项';
    if (fieldForm.optionsSource?.key === 'ethnicity') return '中国民族码表（GB/T 3304），58 项';
    if (fieldForm.optionsSource?.key === 'language') return '语言类型码表（ISO 639），约 609 项';
    return '请选择子类型';
  }
  return '';
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
      message.error('加载字典类型失败: ' + extractApiError(e));
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
    message.error('加载字典项失败: ' + extractApiError(e));
  }
}
const fieldGroupOptions = computed(() => {
  const base = fieldForm.moduleId ? groups.value.filter((g) => g.moduleId === fieldForm.moduleId) : groups.value;
  return base.map((g) => ({ label: g.name, value: g.id }));
});

const FIELD_TYPE_COLOR: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
  TEXT: 'default', NUMBER: 'info', DATE: 'success', DATE_RANGE: 'success',
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
  { label: '文本', value: 'TEXT' },
  { label: '数字', value: 'NUMBER' },
  { label: '多行文本', value: 'MULTILINE_TEXT' },
  { label: '附件', value: 'ATTACHMENT' },
  { label: '日期', value: 'DATE' },
  { label: '手机号', value: 'PHONE' },
  { label: '邮箱', value: 'EMAIL' },
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
    const gname = row.group?.name || row.groupName || '未分组';
    if (!map.has(gid)) map.set(gid, { key: gid || 'ungrouped', name: gname, fields: [] });
    map.get(gid)!.fields.push(row);
  }
  return Array.from(map.values());
});

const fieldColumns = computed(() => [
  { title: '字段名称', key: 'label', minWidth: 140, render: (row: FieldDefinition) => row.label },
  {
    title: '英文名称', key: 'labelEn', minWidth: 140,
    render: (row: FieldDefinition) => row.labelEn || '-',
  },
  {
    title: '类型', key: 'fieldType', width: 100,
    render: (row: FieldDefinition) => h(NTag, { size: 'small', type: FIELD_TYPE_COLOR[row.fieldType] || 'default' }, () => FIELD_TYPE_LABEL[row.fieldType] || row.fieldType),
  },
  {
    title: '可见权限', key: 'visibilityPermission', width: 130,
    render: (row: FieldDefinition) => {
      const v = row.visibilityPermission || 'ALL_VISIBLE';
      const type = v === 'MANAGER_HIDDEN' ? 'warning' : 'success';
      return h(NTag, { size: 'small', type, bordered: false }, () => VISIBILITY_PERMISSION_LABEL[v]);
    },
  },
  {
    title: '操作', key: 'action', width: 280, fixed: 'right' as const,
    render: (row: FieldDefinition) => {
      const disabled = row.status === 'inactive';
      return h(NSpace, { size: 4, wrap: false }, {
        default: () => [
          h(NButton, { size: 'tiny', quaternary: true, onClick: () => openPermissionModal(row) }, { default: () => '管理权限', icon: () => h(ShieldCheckmarkOutline) }),
          h(NButton, { size: 'tiny', quaternary: true, onClick: () => openFieldEdit(row) }, { default: () => '编辑', icon: () => h(CreateOutline) }),
          h(NButton, {
            size: 'tiny', quaternary: true,
            type: disabled ? 'primary' : 'default',
            onClick: () => toggleFieldStatus(row),
          }, { default: () => (disabled ? '启用' : '停用'), icon: () => disabled ? h(PlayOutline) : h(BanOutline) }),
          h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => confirmDeleteField(row) }, { default: () => '删除', icon: () => h(TrashOutline) }),
        ],
      });
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
    message.error('加载字段失败: ' + extractApiError(e));
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
  });
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
    // 2026-09-16 (兵哥): 组合字段子结构回填
    subFields: row.subFields ? row.subFields.map((s) => ({ ...s })) : [],
    // 2026-09-24 (兵哥): 限制条件回填 (按字段类型差异化, 后端 normalize 兜底)
    validation: { ...(row.validation || {}) },
  });
  fieldModalVisible.value = true;
}

function onFieldModuleChange() { fieldForm.groupId = null; }

async function saveField() {
  if (!fieldForm.label.trim()) { message.error('请填写字段名称'); return; }
  // 2026-09-15 选项来源校验: 选了非 custom 但子 key 空 → 拦截
  if (fieldNeedsOptions.value && sourceType.value !== 'custom' && !fieldForm.optionsSource?.key) {
    message.error('选项来源选择了「' + OPTION_SOURCE_OPTIONS.find((o) => o.value === sourceType.value)?.label + '」，请继续选择子类型');
    return;
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
    message.success('保存成功');
    await reloadFields();
  } catch (e: any) {
    message.error('保存失败: ' + extractApiError(e));
  } finally {
    saving.value = false;
  }
}

function confirmDeleteField(row: FieldDefinition) {
  dialog.warning({
    title: '删除字段',
    content: `确认删除字段「${row.label}」?`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteField(currentResource.value, row.id);
        message.success('删除成功');
        await reloadFields();
      } catch (e: any) { message.error('删除失败: ' + extractApiError(e)); }
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
    message.success('已更新可见权限');
    permModalVisible.value = false;
  } catch (e: any) {
    message.error('更新可见权限失败: ' + extractApiError(e));
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
    message.success(next === 'inactive' ? '已停用该字段' : '已启用该字段');
  } catch (e: any) {
    message.error('操作失败: ' + extractApiError(e));
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
  prefix: (info: { itemCount?: number }) => h('span', `共 ${info.itemCount} 条`),
  onChange: (p: number) => { modulePage.value = p; },
  onUpdatePageSize: (s: number) => { modulePageSize.value = s; modulePage.value = 1; },
}));
const moduleForm = reactive<{
  id?: string; code: string; name: string; description: string; orderIndex: number; isActive: boolean;
}>({ code: '', name: '', description: '', orderIndex: 0, isActive: true });

const moduleColumns = computed(() => [
  { title: '顺序', key: 'orderIndex', width: 70, render: (row: FieldModule) => row.orderIndex },
  { title: '编码', key: 'code', width: 140, render: (row: FieldModule) => row.code },
  { title: '名称', key: 'name', width: 180, render: (row: FieldModule) => row.name },
  { title: '描述', key: 'description', width: 240, render: (row: FieldModule) => row.description || '-' },
  {
    title: '状态', key: 'isActive', width: 90,
    render: (row: FieldModule) => row.isActive ? h(NTag, { type: 'success', size: 'small' }, () => '启用') : h(NTag, { size: 'small' }, () => '停用'),
  },
  {
    title: '操作', key: 'action', width: 160, fixed: 'right' as const,
    render: (row: FieldModule) =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'tiny', quaternary: true, onClick: () => openModuleEdit(row) }, { default: () => '编辑', icon: () => h(CreateOutline) }),
          h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => confirmDeleteModule(row) }, { default: () => '删除', icon: () => h(TrashOutline) }),
        ],
      }),
  },
]);

async function reloadModules() {
  moduleLoading.value = true;
  try { moduleRows.value = await listModules(currentResource.value); modulePage.value = 1; }
  catch (e: any) { message.error('加载模块失败: ' + extractApiError(e)); }
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
  if (!moduleForm.code || !moduleForm.name) { message.error('编码和名称必填'); return; }
  saving.value = true;
  try {
    const payload: any = { code: moduleForm.code, name: moduleForm.name, description: moduleForm.description, orderIndex: moduleForm.orderIndex, isActive: moduleForm.isActive, id: moduleEditing.value?.id };
    await upsertModule(currentResource.value, payload);
    moduleModalVisible.value = false;
    message.success('保存成功');
    await reloadModules(); await loadAux();
  } catch (e: any) { message.error('保存失败: ' + extractApiError(e)); }
  finally { saving.value = false; }
}
function confirmDeleteModule(row: FieldModule) {
  dialog.warning({
    title: '删除模块', content: `确认删除模块「${row.name}」? 其下分组将一并删除。`,
    positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try { await deleteModule(currentResource.value, row.id); message.success('删除成功'); await reloadModules(); await loadAux(); }
      catch (e: any) { message.error('删除失败: ' + extractApiError(e)); }
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
  prefix: (info: { itemCount?: number }) => h('span', `共 ${info.itemCount} 条`),
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
  { title: '顺序', key: 'orderIndex', width: 70, render: (row: FieldGroup) => row.orderIndex },
  { title: '模块', key: 'module', width: 140, render: (row: FieldGroup) => row.module?.name || '-' },
  { title: '编码', key: 'code', width: 140, render: (row: FieldGroup) => row.code },
  { title: '名称', key: 'name', width: 180, render: (row: FieldGroup) => row.name },
  {
    title: '状态', key: 'isActive', width: 90,
    render: (row: FieldGroup) => row.isActive ? h(NTag, { type: 'success', size: 'small' }, () => '启用') : h(NTag, { size: 'small' }, () => '停用'),
  },
  {
    title: '操作', key: 'action', width: 160, fixed: 'right' as const,
    render: (row: FieldGroup) =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'tiny', quaternary: true, onClick: () => openGroupEdit(row) }, { default: () => '编辑', icon: () => h(CreateOutline) }),
          h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => confirmDeleteGroup(row) }, { default: () => '删除', icon: () => h(TrashOutline) }),
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
  catch (e: any) { message.error('加载分组失败: ' + extractApiError(e)); }
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
  if (!groupForm.moduleId || !groupForm.name) { message.error('模块和名称必填'); return; }
  saving.value = true;
  try {
    const payload: any = { moduleId: groupForm.moduleId, name: groupForm.name, orderIndex: groupForm.orderIndex, isActive: groupForm.isActive, id: groupEditing.value?.id };
    if (groupEditing.value) payload.code = groupForm.code;
    await upsertGroup(currentResource.value, payload);
    groupModalVisible.value = false;
    message.success('保存成功');
    await reloadGroups(); await loadAux();
  } catch (e: any) { message.error('保存失败: ' + extractApiError(e)); }
  finally { saving.value = false; }
}
function confirmDeleteGroup(row: FieldGroup) {
  dialog.warning({
    title: '删除分组', content: `确认删除分组「${row.name}」?`,
    positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try { await deleteGroup(currentResource.value, row.id); message.success('删除成功'); await reloadGroups(); await loadAux(); }
      catch (e: any) { message.error('删除失败: ' + extractApiError(e)); }
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
  prefix: (info: { itemCount?: number }) => h('span', `共 ${info.itemCount} 条`),
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
  const modeLabel = row.conditionMode === 'ANY' ? '满足以下任一条件时' : '满足以下所有条件时';
  const conds = (row.conditions || []).map((c) => {
    const op = LINKAGE_OP_OPTIONS.find((o) => o.value === c.op)?.label || c.op;
    const val = Array.isArray(c.value) ? c.value.join('、') : String(c.value ?? '');
    return `当 ${linkageFieldLabel(c.fieldKey)} ${op} ${val}`;
  }).join('，且 ') || '无条件';
  const acts = (row.actions || []).map((a) => {
    const act = LINKAGE_ACTION_OPTIONS.find((o) => o.value === a.actionType)?.label || a.actionType;
    const suffix = a.readOnly ? '(只读)' : '';
    const val = a.value ? ` ${a.value}` : '';
    return `${linkageFieldLabel(a.targetFieldKey)} ${act}${val}${suffix}`;
  }).join('，');
  return `${modeLabel}：${conds}，则 ${acts}`;
}

const linkageColumns = computed(() => [
  { title: '规则名称', key: 'name', width: 160, render: (row: FieldLinkageRule) => row.name || '-' },
  { title: '条件和执行动作', key: 'summary', render: (row: FieldLinkageRule) => linkageConditionSummary(row) },
  {
    title: '状态', key: 'isActive', width: 90,
    render: (row: FieldLinkageRule) => row.isActive ? h(NTag, { type: 'success', size: 'small' }, () => '启用') : h(NTag, { size: 'small' }, () => '停用'),
  },
  {
    title: '操作', key: 'action', width: 160, fixed: 'right' as const,
    render: (row: FieldLinkageRule) =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'tiny', quaternary: true, onClick: () => openLinkageEdit(row) }, { default: () => '编辑', icon: () => h(CreateOutline) }),
          h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => confirmDeleteLinkage(row) }, { default: () => '删除', icon: () => h(TrashOutline) }),
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
  catch (e: any) { message.error('加载规则失败: ' + extractApiError(e)); }
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
  if (!linkageForm.moduleId) { message.error('请选择所属模块'); return; }
  if (!linkageForm.name.trim()) { message.error('规则名称必填'); return; }
  if (!linkageForm.conditions.length || linkageForm.conditions.some((c) => !c.fieldKey)) {
    message.error('请填写完整的条件'); return;
  }
  if (!linkageForm.actions.length || linkageForm.actions.some((a) => !a.targetFieldKey)) {
    message.error('请填写完整的执行动作'); return;
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
    message.success('保存成功');
    await reloadLinkage();
  } catch (e: any) { message.error('保存失败: ' + extractApiError(e)); }
  finally { saving.value = false; }
}
function confirmDeleteLinkage(row: FieldLinkageRule) {
  dialog.warning({
    title: '删除规则', content: `确认删除规则「${row.name || '未命名'}」?`,
    positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try { await deleteLinkageRule(currentResource.value, row.id); message.success('删除成功'); await reloadLinkage(); }
      catch (e: any) { message.error('删除失败: ' + extractApiError(e)); }
    },
  });
}

// ============ 导出 / 导入 ============
const exportOptions = [
  { label: '导出 JSON', key: 'json' },
  { label: '导出 CSV', key: 'csv' },
];
function onExportSelect(key: string) {
  downloadExport(currentResource.value, key as 'json' | 'csv', filterModule.value || undefined, filterGroup.value || undefined)
    .then(() => message.success('导出已开始'))
    .catch((e: any) => message.error('导出失败: ' + extractApiError(e)));
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
    message.success('模板已开始下载');
  } catch (e: any) {
    message.error('模板下载失败: ' + extractApiError(e));
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
    message.success(`已读取文件：${file.name}（${importContent.value.length} 字符）`);
  } catch (err: any) {
    message.error('文件读取失败: ' + (err?.message || err));
  } finally {
    input.value = ''; // 允许重复选择同一文件
  }
}

async function runImport() {
  if (!importContent.value.trim()) { message.error('请粘贴导入内容或选择文件'); return; }
  importing.value = true;
  importResult.value = null;
  try {
    const res = await importFields(currentResource.value, importFormat.value, importContent.value);
    importResult.value = res;
    if (res.errors > 0) message.warning(`导入完成：新增 ${res.created}，更新 ${res.updated}，失败 ${res.errors}`);
    else message.success(`导入完成：新增 ${res.created}，更新 ${res.updated}`);
    await reloadFields(); await loadAux();
  } catch (e: any) { message.error('导入失败: ' + extractApiError(e)); }
  finally { importing.value = false; }
}

// ============ 辅助加载 ============
const moduleOptions = computed(() => [
  { label: '全部', value: '' },
  ...modules.value.map((m) => ({ label: m.name, value: m.id })),
]);

/** embedded 模式：进入业务模块时确保默认模块存在（后端自动创建），作为分组/联动的 FK 归属 */
async function ensureDefault() {
  if (!isEmbedded.value) return;
  try {
    const m = await ensureDefaultModule(currentResource.value, props.displayName || currentResource.value);
    defaultModuleId.value = m.id;
  } catch (e: any) {
    message.error('初始化默认模块失败: ' + extractApiError(e));
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
</style>
