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
          <span class="res-label">资源</span>
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
        <n-button type="primary" @click="openFieldCreate">
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
          <!-- 2026-09-15 行政区划型字段：国家开关 + 实时级联预览 (数据源: G46 码表库) -->
          <template v-if="isRegionType">
            <n-form-item label="启用国家">
              <n-space align="center" :size="8">
                <n-switch v-model:value="fieldForm.withCountry" />
                <n-text depth="3">开启后填写时先选国家，再选行政区划</n-text>
              </n-space>
            </n-form-item>
            <n-form-item label="级联预览">
              <RegionCascader
                :field-type="(fieldForm.fieldType as any)"
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
              <n-input v-model:value="fieldForm.confirmationDeclarationEn" type="textarea" placeholder="Declaration text (EN)" />
            </n-form-item>
          </template>
          <n-form-item label="显示">
            <n-switch v-model:value="fieldForm.isVisible" />
          </n-form-item>
          <n-form-item v-if="fieldNeedsOptions" label="选项来源">
            <n-space vertical :size="8" style="width: 100%">
              <n-select
                :value="sourceType"
                :options="OPTION_SOURCE_OPTIONS"
                style="width: 280px"
                @update:value="onOptionSourceTypeChange"
              />
              <n-select
                v-if="sourceType === 'dictionary'"
                v-model:value="fieldForm.optionsSource.key"
                :options="dictionaryTypeOptions"
                :loading="loadingDictTypes"
                placeholder="选择字典类型"
                filterable
                style="width: 100%"
                @update:value="onDictTypeChange"
              />
              <n-alert
                v-if="sourceType === 'library'"
                type="info"
                :show-icon="true"
              >保存后，选项将从「专业库 · 专业名称」动态加载（实时同步专业库数据）。</n-alert>
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
            >{{ opt.label }}</n-radio>
          </n-space>
        </n-radio-group>
        <template #action>
          <n-space justify="end">
            <n-button @click="permModalVisible = false">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="permSaving" @click="savePermission">确定</n-button>
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
          <n-form-item label="分组编码" required>
            <n-input v-model:value="groupForm.code" placeholder="e.g. contact" :disabled="!!groupEditing" />
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
} from '@/api/dynamic-field';
import {
  listDictionaryTypes, listDictionaryItems,
  type DictionaryType,
} from '@/api/dictionary';

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
  prefix: (info: { itemCount: number }) => h('span', `共 ${info.itemCount} 条`),
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
  regionPreviewValue: { country?: {code: string; name: string}; province: {code: string; name: string}; city?: {code: string; name: string}; district?: {code: string; name: string}; } | null;
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
  regionPreviewValue: null,
});

const fieldNeedsOptions = computed(() => ['SELECT', 'MULTISELECT', 'LIST_SINGLE', 'LIST_MULTI'].includes(fieldForm.fieldType));

// 2026-09-15 选项来源 (兵哥): 下拉/列表型字段除手动维护选项外, 可指定数据源动态解析
const OPTION_SOURCE_OPTIONS = [
  { label: '自定义（手动维护）', value: 'custom' },
  { label: '数据字典', value: 'dictionary' },
  { label: '专业库', value: 'library' },
];
// 当前选中的来源类型（兜底 custom）
const sourceType = computed(() => fieldForm.optionsSource?.type || 'custom');
// 仅自定义来源展示手动选项编辑器（A: 选了数据源则隐藏手动选项）
const showManualOptions = computed(() => sourceType.value === 'custom');
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

/** 切换选项来源类型：dictionary 时懒加载字典类型列表；library 时锁定 key=major；custom 时清空 key。 */
async function onOptionSourceTypeChange(type: string) {
  fieldForm.optionsSource.type = type;
  fieldForm.optionsSource.key = '';
  dictionaryPreviewOptions.value = [];
  if (type === 'dictionary') {
    loadingDictTypes.value = true;
    try {
      dictionaryTypes.value = await listDictionaryTypes({ type: 'all' });
    } catch (e: any) {
      message.error('加载字典类型失败: ' + extractApiError(e));
    } finally {
      loadingDictTypes.value = false;
    }
  } else if (type === 'library') {
    // 首个落地的专业库数据源为「专业名称」（library_major）
    fieldForm.optionsSource.key = 'major';
  }
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
  TEXT: 'default', NUMBER: 'info', DATE: 'success',
  SELECT: 'warning', MULTISELECT: 'warning', BOOLEAN: 'default',
  ATTACHMENT: 'info', ID_CARD: 'error', BANK_CARD: 'error', PHONE: 'error', EMAIL: 'error',
  LIST_SINGLE: 'warning', LIST_MULTI: 'warning', CONFIRM: 'info',
  MULTILINE_TEXT: 'default',
  // 2026-09-15 新增地址: 默认色 (与文本一致)
  ADDRESS: 'default',
  // 行政区划级联型: success (与日期同色, 表达"地理位置")
  REGION_PROVINCE: 'success',
  REGION_PROVINCE_CITY: 'success',
  REGION_PROVINCE_CITY_DISTRICT: 'success',
};

// 列表型字段预览：切换单选/多选时同步预览值形状
watch(
  () => fieldForm.fieldType,
  (t) => {
    fieldPreviewValue.value = t === 'LIST_MULTI' ? [] : '';
    // 行政区划级联型切换时重置 region 预览, 避免不同级数的缓存污染
    if (t === 'REGION_PROVINCE' || t === 'REGION_PROVINCE_CITY' || t === 'REGION_PROVINCE_CITY_DISTRICT') {
      fieldForm.regionPreviewValue = null;
    } else {
      fieldForm.regionPreviewValue = null;
    }
  },
);
const isListType = computed(() => fieldForm.fieldType === 'LIST_SINGLE' || fieldForm.fieldType === 'LIST_MULTI');
const isConfirmType = computed(() => fieldForm.fieldType === 'CONFIRM');
// 2026-09-15 行政区划级联型: 省/省市/省市区
const isRegionType = computed(
  () => fieldForm.fieldType === 'REGION_PROVINCE'
    || fieldForm.fieldType === 'REGION_PROVINCE_CITY'
    || fieldForm.fieldType === 'REGION_PROVINCE_CITY_DISTRICT',
);

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
    regionPreviewValue: null,
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
    regionPreviewValue: null,
  });
  fieldModalVisible.value = true;
}

function onFieldModuleChange() { fieldForm.groupId = null; }

async function saveField() {
  if (!fieldForm.label.trim()) { message.error('请填写字段名称'); return; }
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
      // 2026-09-15 行政区划型字段开关 (默认 false; 非 REGION_* 类型上传无副作用)
      withCountry: !!fieldForm.withCountry,
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
  prefix: (info: { itemCount: number }) => h('span', `共 ${info.itemCount} 条`),
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
  moduleModalVisible.value = true;
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
  prefix: (info: { itemCount: number }) => h('span', `共 ${info.itemCount} 条`),
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
  if (!groupForm.moduleId || !groupForm.code || !groupForm.name) { message.error('模块、编码和名称必填'); return; }
  saving.value = true;
  try {
    const payload: any = { moduleId: groupForm.moduleId, code: groupForm.code, name: groupForm.name, orderIndex: groupForm.orderIndex, isActive: groupForm.isActive, id: groupEditing.value?.id };
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
  prefix: (info: { itemCount: number }) => h('span', `共 ${info.itemCount} 条`),
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
.res-label { color: var(--color-text-secondary); font-size: 14px; }
/* 页面级不滚动: 标题/Tabs/筛选固定, 仅数据表格区域内部滚动 (n-data-table flex-height) */
.page-body {
  flex: 1; min-height: 0;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.filter-row { flex-shrink: 0; margin-bottom: var(--space-3); }
.dynamic-field-settings { display: flex; flex-direction: column; gap: var(--space-3); }
.df-tabs {
  flex: 1; min-height: 0;
  display: flex; flex-direction: column;
}
.df-tabs :deep(.n-tabs-nav) { flex-shrink: 0; }
.df-tabs :deep(.n-tabs-content) { flex: 1; min-height: 0; }
.df-tabs :deep(.n-tab-pane) {
  height: 100%;
  display: flex; flex-direction: column;
}
.df-tabs :deep(.n-tab-pane > .n-data-table) {
  flex: 1; min-height: 0;
}
.field-key-readonly {
  display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap;
  font-size: var(--text-xs, 12px);
}
.field-key-readonly code {
  padding: 2px 6px; border-radius: 4px;
  background: var(--color-bg-subtle); color: var(--color-text-secondary);
  font-variant-numeric: tabular-nums;
}
.field-key-hint { color: var(--color-text-tertiary); }
.linkage-row {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) 0; border-bottom: 1px dashed var(--color-border);
}
.linkage-row:last-child { border-bottom: none; }
.linkage-index {
  width: 18px; height: 18px; border-radius: 50%;
  background: var(--color-bg-subtle); color: var(--color-text-secondary);
  font-size: 12px; display: flex; align-items: center; justify-content: center;
}
/* 字段定义：分组卡片视图 */
.field-groups {
  display: flex; flex-direction: column; gap: var(--space-5);
  overflow-y: auto; padding-right: var(--space-2); min-height: 0;
}
.field-group-card {
  border: 1px solid var(--color-border); border-radius: var(--radius-md);
  padding: var(--space-5); background: var(--color-bg);
}
.field-group-head {
  display: flex; align-items: center; gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.fg-title { font-weight: 600; font-size: var(--text-base); }
.fg-spacer { flex: 1; }
/* 字段权限管理弹窗 */
.perm-desc { color: var(--color-text-secondary); margin-bottom: var(--space-3); line-height: 1.5; }
.perm-radio { padding: var(--space-1) 0; }
</style>
