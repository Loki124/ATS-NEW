<template>
  <div class="page-container dynamic-field-settings">
    <div class="page-body">
      <div class="page-header">
        <h1 class="page-title">动态字段定义</h1>
        <p class="page-subtitle">G42 - 元数据驱动的字段配置：字段 / 模块 / 分组 / 联动规则</p>
      </div>

      <!-- 共享资源选择 -->
      <n-space class="resource-row" :wrap="true">
        <n-select v-model:value="currentResource" :options="RESOURCE_OPTIONS" style="width: 240px" @update:value="onResourceChange" />
        <n-tag :bordered="false" type="info">当前资源：{{ currentResource }}</n-tag>
      </n-space>

      <n-tabs v-model:value="activeTab" type="line" class="df-tabs">
        <!-- ============ 字段定义 ============ -->
        <n-tab-pane name="fields" tab="字段定义">
          <n-space class="filter-row" :wrap="true">
            <n-select v-model:value="filterModule" :options="moduleOptions" style="width: 200px" placeholder="按模块筛选" @update:value="reloadFields" />
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

          <n-data-table
            :columns="fieldColumns"
            :data="rows"
            :loading="loading"
            :pagination="{ pageSize: 15 }"
            :row-key="(row: any) => row.id"
            size="small"
            striped
          />
        </n-tab-pane>

        <!-- ============ 模块配置 ============ -->
        <n-tab-pane name="modules" tab="模块配置">
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
            :pagination="{ pageSize: 15 }"
            :row-key="(row: any) => row.id"
            size="small"
            striped
          />
        </n-tab-pane>

        <!-- ============ 分组配置 ============ -->
        <n-tab-pane name="groups" tab="分组配置">
          <n-space class="filter-row" :wrap="true">
            <n-select v-model:value="groupFilterModule" :options="moduleOptions" style="width: 200px" placeholder="按模块筛选" @update:value="reloadGroups" />
            <n-button :loading="groupLoading" @click="reloadGroups">刷新</n-button>
            <n-button type="primary" @click="openGroupCreate">
              <template #icon><n-icon :component="AddOutline" /></template>新建分组
            </n-button>
          </n-space>
          <n-data-table
            :columns="groupColumns"
            :data="groupRows"
            :loading="groupLoading"
            :pagination="{ pageSize: 15 }"
            :row-key="(row: any) => row.id"
            size="small"
            striped
          />
        </n-tab-pane>

        <!-- ============ 联动规则 ============ -->
        <n-tab-pane name="linkage" tab="联动规则">
          <n-space class="filter-row" :wrap="true">
            <n-select v-model:value="linkageFilterModule" :options="moduleOptions" style="width: 200px" placeholder="按模块筛选" @update:value="reloadLinkage" />
            <n-button :loading="linkageLoading" @click="reloadLinkage">刷新</n-button>
            <n-button type="primary" @click="openLinkageCreate">
              <template #icon><n-icon :component="AddOutline" /></template>新建规则
            </n-button>
          </n-space>
          <n-data-table
            :columns="linkageColumns"
            :data="linkageRows"
            :loading="linkageLoading"
            :pagination="{ pageSize: 15 }"
            :row-key="(row: any) => row.id"
            size="small"
            striped
          />
        </n-tab-pane>
      </n-tabs>

      <!-- ============ 字段 新建/编辑 Modal ============ -->
      <n-modal
        v-model:show="fieldModalVisible"
        preset="card"
        :title="fieldEditing ? '编辑字段' : '新建字段'"
        style="width: 680px; max-width: 92vw;"
      >
        <n-form :model="fieldForm" label-placement="left" label-width="100px">
          <n-form-item label="字段 Key" required>
            <n-input v-model:value="fieldForm.fieldKey" placeholder="e.g. idCardNo" :disabled="!!fieldEditing" />
          </n-form-item>
          <n-form-item label="字段名称" required>
            <n-input v-model:value="fieldForm.label" placeholder="e.g. 身份证号" />
          </n-form-item>
          <n-form-item label="字段类型" required>
            <n-select v-model:value="fieldForm.fieldType" :options="FIELD_TYPE_OPTIONS" />
          </n-form-item>
          <n-form-item label="归属模块">
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
          <n-form-item label="排序">
            <n-input-number v-model:value="fieldForm.orderIndex" :min="0" />
          </n-form-item>
          <n-form-item label="必填">
            <n-switch v-model:value="fieldForm.isRequired" />
          </n-form-item>
          <n-form-item label="显示">
            <n-switch v-model:value="fieldForm.isVisible" />
          </n-form-item>
          <n-form-item v-if="fieldNeedsOptions" label="选项">
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
        </n-form>
        <template #action>
          <n-space justify="end">
            <n-button @click="fieldModalVisible = false">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="saveField">保存字段</n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- ============ 模块 Modal ============ -->
      <n-modal
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
          <n-form-item label="归属模块" required>
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
          <n-form-item label="规则名称" required>
            <n-input v-model:value="linkageForm.name" placeholder="e.g. 职级层级非管理" />
          </n-form-item>
          <n-form-item label="所属模块" required>
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
        style="width: 640px; max-width: 92vw;"
      >
        <n-space vertical :size="12">
          <n-alert type="info" :show-icon="true">
            支持 JSON 数组或 CSV 文本。CSV 需包含表头：
            <code>field_key,label,field_type,module_code,group_code,is_required,...</code>
          </n-alert>
          <n-form-item label="格式" label-placement="left" :show-feedback="false">
            <n-radio-group v-model:value="importFormat">
              <n-radio value="json">JSON</n-radio>
              <n-radio value="csv">CSV</n-radio>
            </n-radio-group>
          </n-form-item>
          <n-input
            v-model:value="importContent"
            type="textarea"
            placeholder="粘贴 JSON 数组或 CSV 文本"
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h, onMounted, reactive, watch } from 'vue';
import {
  NTag, NButton, NSpace, NSwitch, NInputNumber, NIcon, NSelect, NDataTable,
  NModal, NForm, NFormItem, NInput, NDynamicInput, NTabs, NTabPane, NDropdown,
  NRadioGroup, NRadio, NCheckbox, NAlert, NText, useMessage, useDialog,
} from 'naive-ui';
import { AddOutline, TrashOutline, CreateOutline } from '@vicons/ionicons5';
import {
  listFields, upsertField, deleteField, extractApiError,
  FIELD_TYPE_OPTIONS, FIELD_TYPE_LABEL, RESOURCE_OPTIONS,
  listModules, upsertModule, deleteModule,
  listGroups, upsertGroup, deleteGroup,
  listLinkageRules, upsertLinkageRule, deleteLinkageRule,
  downloadExport, importFields,
  LINKAGE_ACTION_OPTIONS, LINKAGE_OP_OPTIONS, LINKAGE_CONDITION_MODE_OPTIONS,
  type FieldDefinition, type FieldType, type FieldModule, type FieldGroup, type FieldLinkageRule,
  type LinkageCondition, type LinkageAction, type LinkageConditionMode,
  type LinkageConditionOp, type LinkageActionType,
} from '@/api/dynamic-field';

const message = useMessage();
const dialog = useDialog();

const currentResource = ref<string>('Candidate');
const activeTab = ref<string>('fields');

// 辅助数据
const modules = ref<FieldModule[]>([]);
const groups = ref<FieldGroup[]>([]);

// ============ 字段定义 ============
const rows = ref<FieldDefinition[]>([]);
const loading = ref(false);
const saving = ref(false);
const fieldModalVisible = ref(false);
const fieldEditing = ref<FieldDefinition | null>(null);
const filterModule = ref<string>('');
const filterGroup = ref<string>('');

const fieldForm = reactive<{
  id?: string; fieldKey: string; label: string; fieldType: FieldType;
  moduleId: string | null; groupId: string | null;
  isRequired: boolean; isVisible: boolean; placeholder: string; helpText: string;
  orderIndex: number; options: { value: string; label: string }[];
}>({
  fieldKey: '', label: '', fieldType: 'TEXT',
  moduleId: null, groupId: null,
  isRequired: false, isVisible: true, placeholder: '', helpText: '',
  orderIndex: 0, options: [],
});

const fieldNeedsOptions = computed(() => fieldForm.fieldType === 'SELECT' || fieldForm.fieldType === 'MULTISELECT');
const fieldGroupOptions = computed(() => {
  const base = fieldForm.moduleId ? groups.value.filter((g) => g.moduleId === fieldForm.moduleId) : groups.value;
  return base.map((g) => ({ label: g.name, value: g.id }));
});

const FIELD_TYPE_COLOR: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
  TEXT: 'default', NUMBER: 'info', DATE: 'success',
  SELECT: 'warning', MULTISELECT: 'warning', BOOLEAN: 'default',
  ATTACHMENT: 'info', ID_CARD: 'error', BANK_CARD: 'error', PHONE: 'error', EMAIL: 'error',
};

const fieldColumns = computed(() => [
  { title: '顺序', key: 'orderIndex', width: 70, render: (row: FieldDefinition) => row.orderIndex },
  { title: '字段名称', key: 'label', width: 160, render: (row: FieldDefinition) => row.label },
  { title: 'Key', key: 'fieldKey', width: 160, render: (row: FieldDefinition) => row.fieldKey },
  {
    title: '类型', key: 'fieldType', width: 100,
    render: (row: FieldDefinition) => h(NTag, { size: 'small', type: FIELD_TYPE_COLOR[row.fieldType] || 'default' }, () => FIELD_TYPE_LABEL[row.fieldType] || row.fieldType),
  },
  { title: '模块', key: 'module', width: 110, render: (row: FieldDefinition) => row.module?.name || '-' },
  { title: '分组', key: 'group', width: 110, render: (row: FieldDefinition) => row.group?.name || row.groupName || '-' },
  {
    title: '必填', key: 'isRequired', width: 70,
    render: (row: FieldDefinition) => row.isRequired ? h(NTag, { type: 'error', size: 'small' }, () => '是') : '-',
  },
  {
    title: '选项数', key: 'optionCount', width: 80,
    render: (row: FieldDefinition) => (row.options?.length ?? 0) || '-',
  },
  {
    title: '操作', key: 'action', width: 160, fixed: 'right' as const,
    render: (row: FieldDefinition) =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'tiny', quaternary: true, onClick: () => openFieldEdit(row) }, { default: () => '编辑', icon: () => h(CreateOutline) }),
          h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => confirmDeleteField(row) }, { default: () => '删除', icon: () => h(TrashOutline) }),
        ],
      }),
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
  } catch (e: any) {
    message.error('加载字段失败: ' + extractApiError(e));
  } finally {
    loading.value = false;
  }
}

function resetFieldForm() {
  Object.assign(fieldForm, {
    id: undefined, fieldKey: '', label: '', fieldType: 'TEXT',
    moduleId: null, groupId: null,
    isRequired: false, isVisible: true, placeholder: '', helpText: '',
    orderIndex: rows.value.length, options: [],
  });
}

function openFieldCreate() { fieldEditing.value = null; resetFieldForm(); fieldModalVisible.value = true; }

function openFieldEdit(row: FieldDefinition) {
  fieldEditing.value = row;
  Object.assign(fieldForm, {
    id: row.id, fieldKey: row.fieldKey, label: row.label, fieldType: row.fieldType,
    moduleId: row.moduleId || null, groupId: row.groupId || null,
    isRequired: row.isRequired, isVisible: row.isVisible,
    placeholder: row.placeholder || '', helpText: row.helpText || '',
    orderIndex: row.orderIndex,
    options: (row.options || []).map((o) => ({ value: o.value, label: o.label })),
  });
  fieldModalVisible.value = true;
}

function onFieldModuleChange() { fieldForm.groupId = null; }

async function saveField() {
  if (!fieldForm.fieldKey || !fieldForm.label) { message.error('Key 和字段名称必填'); return; }
  saving.value = true;
  try {
    const payload: any = {
      fieldKey: fieldForm.fieldKey, label: fieldForm.label, fieldType: fieldForm.fieldType,
      isRequired: fieldForm.isRequired, isVisible: fieldForm.isVisible,
      placeholder: fieldForm.placeholder, helpText: fieldForm.helpText,
      orderIndex: fieldForm.orderIndex,
      moduleId: fieldForm.moduleId || null, groupId: fieldForm.groupId || null,
      id: fieldEditing.value?.id,
    };
    if (!fieldNeedsOptions.value) payload.options = [];
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

// ============ 模块配置 ============
const moduleRows = ref<FieldModule[]>([]);
const moduleLoading = ref(false);
const moduleModalVisible = ref(false);
const moduleEditing = ref<FieldModule | null>(null);
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
  try { moduleRows.value = await listModules(currentResource.value); }
  catch (e: any) { message.error('加载模块失败: ' + extractApiError(e)); }
  finally { moduleLoading.value = false; }
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
  try { groupRows.value = await listGroups(currentResource.value, groupFilterModule.value || undefined); }
  catch (e: any) { message.error('加载分组失败: ' + extractApiError(e)); }
  finally { groupLoading.value = false; }
}
function openGroupCreate() {
  groupEditing.value = null;
  Object.assign(groupForm, { id: undefined, moduleId: groupFilterModule.value || null, code: '', name: '', orderIndex: groupRows.value.length, isActive: true });
  groupModalVisible.value = true;
}
function openGroupEdit(row: FieldGroup) {
  groupEditing.value = row;
  Object.assign(groupForm, { id: row.id, moduleId: row.moduleId, code: row.code, name: row.name, orderIndex: row.orderIndex, isActive: row.isActive });
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
  try { linkageRows.value = await listLinkageRules(currentResource.value, linkageFilterModule.value || undefined); }
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
    id: undefined, moduleId: linkageFilterModule.value || null, name: '',
    conditionMode: 'ALL', conditions: [newCondition()], actions: [newAction()],
  });
  linkageModalVisible.value = true;
  if (linkageForm.moduleId) loadLinkageFields(linkageForm.moduleId);
}
function openLinkageEdit(row: FieldLinkageRule) {
  linkageEditing.value = row;
  Object.assign(linkageForm, {
    id: row.id, moduleId: row.moduleId, name: row.name,
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

async function runImport() {
  if (!importContent.value.trim()) { message.error('请粘贴导入内容'); return; }
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

async function loadAux() {
  try {
    modules.value = await listModules(currentResource.value);
    groups.value = await listGroups(currentResource.value);
  } catch { /* 辅助数据加载失败不阻塞主表 */ }
}

function onResourceChange() {
  filterModule.value = ''; filterGroup.value = '';
  groupFilterModule.value = ''; linkageFilterModule.value = '';
  loadAux(); reloadFields(); reloadModules(); reloadGroups(); reloadLinkage();
}

onMounted(() => { loadAux(); reloadFields(); reloadModules(); reloadGroups(); reloadLinkage(); });
</script>

<style scoped>
.page-container {
  display: flex; flex-direction: column; height: 100%; min-height: 0; padding: 0;
}
.page-header { flex-shrink: 0; }
.page-body {
  flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden;
  display: flex; flex-direction: column; gap: var(--space-4);
}
.resource-row { margin-bottom: var(--space-2); }
.filter-row { margin-bottom: var(--space-3); }
.dynamic-field-settings { display: flex; flex-direction: column; gap: var(--space-3); }
.df-tabs { margin-top: var(--space-2); }
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
</style>
