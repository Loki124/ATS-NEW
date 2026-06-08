<template>
  <div class="dynamic-field-settings">
    <div class="page-header">
      <h1 class="page-title">动态字段定义</h1>
      <p class="page-subtitle">G42 - 元数据驱动的字段配置, 支持字段类型/选项/排序</p>
    </div>

    <n-card>
      <n-space class="filter-row" :wrap>
        <n-select
          v-model:value="currentResource"
          :options="RESOURCE_OPTIONS"
          style="width: 240px"
          @update:value="reload"
        />
        <n-button @click="reload" :loading="loading">刷新</n-button>
        <n-button type="primary" @click="openCreate">
          <template #icon><n-icon :component="AddOutline" /></template>
          新建字段
        </n-button>
      </n-space>

      <n-data-table
        :columns="columns"
        :data="rows"
        :loading="loading"
        :pagination="{ pageSize: 15 }"
        :row-key="(row: any) => row.id"
        size="small"
        striped
      />
    </n-card>

    <!-- 新建/编辑 Modal -->
    <n-modal
      v-model:show="modalVisible"
      preset="card"
      :title="editing ? '编辑字段' : '新建字段'"
      style="width: 640px; max-width: 92vw;"
    >
      <n-form :model="form" label-placement="left" label-width="100px">
        <n-form-item label="字段 Key" required>
          <n-input v-model:value="form.fieldKey" placeholder="e.g. referrerRelation" :disabled="!!editing" />
        </n-form-item>
        <n-form-item label="显示标签" required>
          <n-input v-model:value="form.label" placeholder="e.g. 推荐人关系" />
        </n-form-item>
        <n-form-item label="字段类型" required>
          <n-select v-model:value="form.fieldType" :options="FIELD_TYPE_OPTIONS" />
        </n-form-item>
        <n-form-item label="分组">
          <n-input v-model:value="form.groupName" placeholder="e.g. 基本信息 / 教育背景" />
        </n-form-item>
        <n-form-item label="占位提示">
          <n-input v-model:value="form.placeholder" placeholder="placeholder" />
        </n-form-item>
        <n-form-item label="帮助文本">
          <n-input v-model:value="form.helpText" placeholder="helpText" />
        </n-form-item>
        <n-form-item label="排序">
          <n-input-number v-model:value="form.orderIndex" :min="0" />
        </n-form-item>
        <n-form-item label="必填">
          <n-switch v-model:value="form.isRequired" />
        </n-form-item>
        <n-form-item label="显示">
          <n-switch v-model:value="form.isVisible" />
        </n-form-item>
        <n-form-item v-if="needsOptions" label="选项">
          <n-dynamic-input
            v-model:value="form.options"
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
          <n-button @click="modalVisible = false">取消</n-button>
          <n-button type="primary" @click="save" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h, onMounted, reactive, watch } from 'vue';
import { NTag, NButton, NSpace, NSwitch, NInputNumber, NIcon, useMessage } from 'naive-ui';
import { AddOutline, TrashOutline, CreateOutline, ConstructOutline } from '@vicons/ionicons5';
import {
  listFields, upsertField, deleteField,
  FIELD_TYPE_OPTIONS, RESOURCE_OPTIONS,
  type FieldDefinition, type FieldType,
} from '@/api/dynamic-field';

const message = useMessage();
const currentResource = ref<string>('Candidate');
const rows = ref<FieldDefinition[]>([]);
const loading = ref(false);
const saving = ref(false);
const modalVisible = ref(false);
const editing = ref<FieldDefinition | null>(null);

const form = reactive<{
  id?: string;
  fieldKey: string;
  label: string;
  fieldType: FieldType;
  isRequired: boolean;
  isVisible: boolean;
  placeholder: string;
  helpText: string;
  defaultValue: string;
  orderIndex: number;
  groupName: string;
  options: { value: string; label: string }[];
}>({
  fieldKey: '',
  label: '',
  fieldType: 'TEXT',
  isRequired: false,
  isVisible: true,
  placeholder: '',
  helpText: '',
  defaultValue: '',
  orderIndex: 0,
  groupName: '',
  options: [],
});

const needsOptions = computed(() => form.fieldType === 'SELECT' || form.fieldType === 'MULTISELECT');

const FIELD_TYPE_LABEL: Record<FieldType, string> = {
  TEXT: '文本', NUMBER: '数字', DATE: '日期',
  SELECT: '单选', MULTISELECT: '多选', BOOLEAN: '布尔',
};
const FIELD_TYPE_COLOR: Record<FieldType, 'default' | 'info' | 'success' | 'warning'> = {
  TEXT: 'default', NUMBER: 'info', DATE: 'success',
  SELECT: 'warning', MULTISELECT: 'warning', BOOLEAN: 'default',
};

const columns = computed(() => [
  { title: '顺序', key: 'orderIndex', width: 70 },
  { title: 'Key', key: 'fieldKey', width: 160 },
  { title: '标签', key: 'label', width: 140 },
  {
    title: '类型',
    key: 'fieldType',
    width: 90,
    render: (row: FieldDefinition) => h(NTag, { size: 'small', type: FIELD_TYPE_COLOR[row.fieldType] }, () => FIELD_TYPE_LABEL[row.fieldType]),
  },
  { title: '分组', key: 'groupName', width: 110, render: (row: FieldDefinition) => row.groupName || '-' },
  {
    title: '必填',
    key: 'isRequired',
    width: 70,
    render: (row: FieldDefinition) => row.isRequired ? h(NTag, { type: 'error', size: 'small' }, () => '是') : '-',
  },
  {
    title: '选项数',
    key: 'optionCount',
    width: 80,
    render: (row: FieldDefinition) => (row.options?.length ?? 0) || '-',
  },
  {
    title: '操作',
    key: 'action',
    width: 160,
    fixed: 'right' as const,
    render: (row: FieldDefinition) =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'tiny', quaternary: true, onClick: () => openEdit(row) }, { default: () => '编辑', icon: () => h(CreateOutline) }),
          h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => confirmDelete(row) }, { default: () => '删除', icon: () => h(TrashOutline) }),
        ],
      }),
  },
]);

function onCreateOption() {
  return { value: '', label: '' };
}

async function reload() {
  loading.value = true;
  try {
    rows.value = await listFields(currentResource.value);
  } catch (e: any) {
    message.error('加载字段失败: ' + (e?.response?.data?.message || e.message));
  } finally {
    loading.value = false;
  }
}

function resetForm() {
  Object.assign(form, {
    id: undefined,
    fieldKey: '',
    label: '',
    fieldType: 'TEXT',
    isRequired: false,
    isVisible: true,
    placeholder: '',
    helpText: '',
    defaultValue: '',
    orderIndex: rows.value.length,
    groupName: '',
    options: [],
  });
}

function openCreate() {
  editing.value = null;
  resetForm();
  modalVisible.value = true;
}

function openEdit(row: FieldDefinition) {
  editing.value = row;
  Object.assign(form, {
    id: row.id,
    fieldKey: row.fieldKey,
    label: row.label,
    fieldType: row.fieldType,
    isRequired: row.isRequired,
    isVisible: row.isVisible,
    placeholder: row.placeholder || '',
    helpText: row.helpText || '',
    defaultValue: row.defaultValue || '',
    orderIndex: row.orderIndex,
    groupName: row.groupName || '',
    options: (row.options || []).map((o) => ({ value: o.value, label: o.label })),
  });
  modalVisible.value = true;
}

async function save() {
  if (!form.fieldKey || !form.label) {
    message.error('Key 和标签必填');
    return;
  }
  saving.value = true;
  try {
    const payload: any = { ...form };
    if (!needsOptions.value) delete payload.options;
    await upsertField(currentResource.value, payload);
    modalVisible.value = false;
    message.success('保存成功');
    await reload();
  } catch (e: any) {
    message.error('保存失败: ' + (e?.response?.data?.message || e.message));
  } finally {
    saving.value = false;
  }
}

async function confirmDelete(row: FieldDefinition) {
  if (!confirm(`确认删除字段 "${row.label}" 吗?`)) return;
  try {
    await deleteField(currentResource.value, row.id);
    message.success('删除成功');
    await reload();
  } catch (e: any) {
    message.error('删除失败: ' + (e?.response?.data?.message || e.message));
  }
}

watch(needsOptions, (v) => {
  if (!v) form.options = [];
});

onMounted(() => { reload(); });
</script>

<style scoped>
.dynamic-field-settings { display: flex; flex-direction: column; gap: 12px; height: 100%; }
.page-header { padding: 0 0 4px 0; }
.page-title { font-size: 22px; font-weight: 600; margin: 0; }
.page-subtitle { color: #888; margin: 4px 0 0 0; font-size: 13px; }
.filter-row { margin-bottom: 12px; }
</style>
