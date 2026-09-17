<template>
  <div class="page-container data-permission">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">字段权限</h1>
          <p class="page-subtitle">
            按角色 / 部门 / 用户维度，配置各业务实体的<strong>字段级</strong>可见性（可读 / 脱敏 / 隐藏）
          </p>
        </div>
        <n-button size="small" :loading="loading" @click="reloadAll">
          <template #icon><n-icon :component="ReloadOutline" /></template>
          刷新
        </n-button>
      </div>

      <!-- 维度切换 -->
      <n-card :bordered="false" class="glass-panel dp-dimension">
        <div class="dp-dimension__row">
          <span class="dp-label">权限维度</span>
          <n-radio-group v-model:value="dimension" type="button" @update:value="onDimensionChange">
            <n-radio-button value="ROLE"><n-icon :component="PeopleOutline" /> 角色</n-radio-button>
            <n-radio-button value="DEPARTMENT"><n-icon :component="BusinessOutline" /> 部门</n-radio-button>
            <n-radio-button value="USER"><n-icon :component="PersonOutline" /> 用户</n-radio-button>
          </n-radio-group>
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-icon class="dp-hint" :component="InformationCircleOutline" />
            </template>
            字段权限控制「每条数据里能看到哪些字段」（可读 / 脱敏 / 隐藏），按所选维度生效。
          </n-tooltip>
        </div>

        <n-divider class="dp-divider" />

        <div class="dp-dimension__row">
          <span class="dp-label">配置对象</span>
          <n-select
            v-if="candidates.length"
            v-model:value="dimensionValue"
            :options="candidates"
            :placeholder="subjectPlaceholder"
            filterable
            clearable
            style="min-width: 280px"
            @update:value="onSubjectChange"
          />
          <n-input
            v-else
            v-model:value="dimensionValue"
            :placeholder="subjectPlaceholder + '（输入编码 / ID）'"
            clearable
            style="min-width: 280px"
            @update:value="onSubjectChange"
          />
          <n-tag v-if="colCount" :bordered="false" type="info">
            当前 {{ colCount }} 条字段权限
          </n-tag>
        </div>
      </n-card>

      <n-empty v-if="!dimensionValue" description="请先选择上方「配置对象」，再设置其字段权限" class="dp-empty" />

      <n-spin v-else :show="loading">
        <!-- 列级字段权限 -->
        <n-card title="列级字段权限" class="glass-panel dp-card">
          <template #header-extra>
            <n-button size="small" :disabled="saving" @click="addColumnDraft">
              <template #icon><n-icon :component="AddOutline" /></template>
              新增字段
            </n-button>
          </template>

          <n-empty v-if="!columnRules.length && !draft" description="暂无字段权限，点击「新增字段」设置字段可见性" />

          <n-data-table
            v-else
            :columns="colColumns"
            :data="columnTableData"
            :pagination="false"
            size="small"
            :bordered="true"
          />
        </n-card>
      </n-spin>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue';
import {
  NButton, NCard, NRadioGroup, NRadioButton, NSelect, NInput,
  NDataTable, NTag, NSpin, NEmpty, NDivider, NTooltip, NIcon, useMessage,
} from 'naive-ui';
import {
  ReloadOutline, InformationCircleOutline, PeopleOutline, BusinessOutline, PersonOutline,
  AddOutline, TrashOutline,
} from '@vicons/ionicons5';

import {
  listRules, createRule, updateRule, deleteRule as apiDeleteRule,
  fetchOptions, listRoles, listDepartments, listUsers,
  type DataPermissionRule, type DimensionType, type ColumnPermission, type OptionItem,
} from '@/api/data-permission';

const message = useMessage();

const dimension = ref<DimensionType>('ROLE');
const dimensionValue = ref<string>('');
const candidates = ref<OptionItem[]>([]);
const options = ref<{
  column_permissions: OptionItem[];
}>({ column_permissions: [] });

const rules = ref<DataPermissionRule[]>([]);
const loading = ref(false);
const saving = ref(false);

// 列级草稿行（新增字段用）
const draft = ref<{ entity: string; field: string; permission: ColumnPermission } | null>(null);

const subjectPlaceholder = computed(() => {
  if (dimension.value === 'ROLE') return '选择角色（如 HRBP / INTERVIEWER）';
  if (dimension.value === 'DEPARTMENT') return '选择部门';
  return '选择用户';
});

const columnPermissionOptions = computed(() => options.value.column_permissions);

const rulesForSubject = computed(() =>
  rules.value.filter(r => r.dimensionType === dimension.value && r.dimensionValue === dimensionValue.value),
);
const columnRules = computed(() => rulesForSubject.value.filter(r => r.level === 'COLUMN'));
const colCount = computed(() => columnRules.value.length);

const PERM_LABEL: Record<ColumnPermission, string> = { READ: '可读', MASK: '脱敏', NONE: '隐藏' };
const PERM_TYPE: Record<ColumnPermission, 'success' | 'warning' | 'error'> = {
  READ: 'success', MASK: 'warning', NONE: 'error',
};

const columnTableData = computed(() => {
  const rows = columnRules.value.map(r => ({ ...r, _editing: false }));
  if (draft.value) {
    rows.push({ id: '__draft__', dimensionType: dimension.value, dimensionValue: dimensionValue.value, level: 'COLUMN',
      entity: draft.value.entity, field: draft.value.field, permission: draft.value.permission,
      priority: 0, status: 1, _editing: true } as any);
  }
  return rows;
});

const colColumns = computed(() => [
  {
    title: '实体', key: 'entity', width: 150,
    render: (row: any) => row._editing
      ? h(NInput, { value: draft.value?.entity, 'onUpdate:value': (v: string) => (draft.value!.entity = v), placeholder: '如 candidate / offer', size: 'small' })
      : h('span', row.entity || '-'),
  },
  {
    title: '字段', key: 'field', width: 160,
    render: (row: any) => row._editing
      ? h(NInput, { value: draft.value?.field, 'onUpdate:value': (v: string) => (draft.value!.field = v), placeholder: '如 phone / salary', size: 'small' })
      : h('span', row.field || '-'),
  },
  {
    title: '权限', key: 'permission', width: 140,
    render: (row: any) => {
      if (row._editing) {
        return h(NSelect, {
          value: draft.value?.permission,
          options: columnPermissionOptions.value,
          'onUpdate:value': (v: ColumnPermission) => (draft.value!.permission = v),
          size: 'small',
        });
      }
      const p = row.permission as ColumnPermission;
      return h(NTag, { type: PERM_TYPE[p] || 'default', size: 'small', bordered: false }, () => PERM_LABEL[p] || p);
    },
  },
  {
    title: '状态', key: 'status', width: 90,
    render: (row: any) => row._editing
      ? h('span', '-')
      : h(NTag, { type: row.status ? 'success' : 'default', size: 'small', bordered: false }, () => (row.status ? '启用' : '停用')),
  },
  {
    title: '操作', key: 'actions', width: 160,
    render: (row: any) => {
      if (row._editing) {
        return h('div', { style: 'display:flex;gap:8px' }, [
          h(NButton, { size: 'small', type: 'primary', loading: saving.value, onClick: () => saveDraftColumn() }, () => '保存'),
          h(NButton, { size: 'small', tertiary: true, onClick: () => (draft.value = null) }, () => '取消'),
        ]);
      }
      return h('div', { style: 'display:flex;gap:8px' }, [
        h(NButton, { size: 'small', tertiary: true, onClick: () => toggleStatus(row) }, () => (row.status ? '停用' : '启用')),
        h(NPopconfirm as any, { onPositiveClick: () => removeRule(row.id) },
          { trigger: () => h(NButton, { size: 'small', tertiary: true, type: 'error' }, () => h(NIcon, { component: TrashOutline })) }),
      ]);
    },
  },
]);

async function loadCandidates() {
  candidates.value = [];
  try {
    if (dimension.value === 'ROLE') candidates.value = await listRoles();
    else if (dimension.value === 'DEPARTMENT') candidates.value = await listDepartments();
    else candidates.value = await listUsers();
  } catch {
    candidates.value = [];
  }
}

async function loadRules() {
  rules.value = await listRules();
}

async function reloadAll() {
  loading.value = true;
  try {
    const [opts] = await Promise.all([fetchOptions(), loadCandidates(), loadRules()]);
    options.value = { column_permissions: opts.column_permissions };
  } catch (err: any) {
    message.error(`加载失败：${err?.message || err}`);
  } finally {
    loading.value = false;
  }
}

function onDimensionChange() {
  dimensionValue.value = '';
  draft.value = null;
  loadCandidates();
  loadRules();
}

function onSubjectChange() {
  draft.value = null;
}

function addColumnDraft() {
  if (!dimensionValue.value) { message.warning('请先选择配置对象'); return; }
  draft.value = { entity: '', field: '', permission: 'MASK' };
}

async function saveDraftColumn() {
  if (!draft.value?.entity || !draft.value?.field) {
    message.warning('请填写实体与字段'); return;
  }
  saving.value = true;
  try {
    await createRule({
      dimension_type: dimension.value,
      dimension_value: dimensionValue.value,
      level: 'COLUMN',
      entity: draft.value.entity,
      field: draft.value.field,
      permission: draft.value.permission,
      priority: 10,
      status: 1,
    });
    draft.value = null;
    await loadRules();
    message.success('字段权限已添加');
  } catch (err: any) {
    message.error(`保存失败：${err?.message || err}`);
  } finally {
    saving.value = false;
  }
}

async function toggleStatus(row: DataPermissionRule) {
  saving.value = true;
  try {
    await updateRule(row.id, { status: row.status ? 0 : 1 });
    await loadRules();
    message.success(row.status ? '已停用' : '已启用');
  } catch (err: any) {
    message.error(`操作失败：${err?.message || err}`);
  } finally {
    saving.value = false;
  }
}

async function removeRule(id: string) {
  saving.value = true;
  try {
    await apiDeleteRule(id);
    await loadRules();
    message.success('已删除');
  } catch (err: any) {
    message.error(`删除失败：${err?.message || err}`);
  } finally {
    saving.value = false;
  }
}

onMounted(reloadAll);
</script>

<style scoped>
.page-container { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.page-header { flex-shrink: 0; display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-3); }
.page-body {
  flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden;
  display: flex; flex-direction: column; gap: var(--space-4);
}
.data-permission { width: 100%; }

.dp-dimension__row { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.dp-label { font-size: var(--fs-13); color: var(--ink-soft); font-weight: 500; min-width: 64px; }
.dp-hint { color: var(--ink-faint); cursor: help; font-size: var(--fs-16); }
.dp-divider { margin: var(--space-3) 0; }

.dp-card { margin-bottom: 0; }
.dp-empty { margin-top: 48px; }

/* 维度 radio 图标与文字间距 */
.dp-dimension :deep(.n-radio-button__label) { display: inline-flex; align-items: center; gap: 6px; }
</style>
