<template>
  <div class="page-container data-permission">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">数据权限管理</h1>
          <p class="page-subtitle">
            按角色 / 部门 / 用户维度，统一配置数据的<strong>行级</strong>与<strong>列级</strong>访问范围（RBAC 数据权限）
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
            行级控制「能看到哪些数据行」，列级控制「每条数据里能看到哪些字段」。两者都按所选维度生效。
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
          <n-tag v-if="rowCount + colCount" :bordered="false" type="info">
            当前 {{ rowCount }} 条行级 · {{ colCount }} 条列级
          </n-tag>
        </div>
      </n-card>

      <n-empty v-if="!dimensionValue" description="请先选择上方「配置对象」，再设置其数据权限" class="dp-empty" />

      <n-spin v-else :show="loading">
        <!-- 行级访问控制 -->
        <n-card title="行级访问控制" class="glass-panel dp-card">
          <template #header-extra>
            <n-tag v-if="rowRule" :type="rowRule.status ? 'success' : 'default'" :bordered="false">
              {{ rowRule.status ? '已启用' : '已停用' }}
            </n-tag>
          </template>

          <div class="dp-form">
            <div class="dp-form__item">
              <span class="dp-form__label">数据可见范围</span>
              <n-select
                v-model:value="rowForm.scopeType"
                :options="rowScopeOptions"
                placeholder="选择行级范围"
                style="min-width: 240px"
              />
            </div>

            <div v-if="rowForm.scopeType === 'CUSTOM'" class="dp-form__item dp-form__item--full">
              <span class="dp-form__label">自定义范围 (JSON)</span>
              <n-input
                v-model:value="customPayloadText"
                type="textarea"
                :rows="2"
                placeholder='{"department_ids":["d1","d2"]} 或 {"management_unit_ids":[1,2]}'
              />
            </div>

            <div class="dp-form__item dp-form__item--full dp-form__actions">
              <n-button
                type="primary"
                :loading="saving"
                :disabled="!rowForm.scopeType"
                @click="saveRowRule"
              >
                <template #icon><n-icon :component="SaveOutline" /></template>
                {{ rowRule ? '保存修改' : '新增行级规则' }}
              </n-button>
              <n-button v-if="rowRule" tertiary type="error" :disabled="saving" @click="deleteRule(rowRule.id)">
                删除该规则
              </n-button>
            </div>
          </div>

          <n-alert v-if="!rowRule" type="warning" :show-icon="false" class="dp-tip">
            尚未配置行级规则：保存后将按所选范围限制该对象可见的数据行；未配置时沿用系统默认数据范围。
          </n-alert>
        </n-card>

        <!-- 列级字段权限 -->
        <n-card title="列级字段权限" class="glass-panel dp-card">
          <template #header-extra>
            <n-button size="small" :disabled="saving" @click="addColumnDraft">
              <template #icon><n-icon :component="AddOutline" /></template>
              新增字段
            </n-button>
          </template>

          <n-empty v-if="!columnRules.length && !draft" description="暂无列级规则，点击「新增字段」设置字段可见性" />

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
  NButton, NCard, NRadioGroup, NRadioButton, NSelect, NInput, NInputGroup,
  NDataTable, NTag, NSpin, NEmpty, NDivider, NTooltip, NIcon, NAlert, useMessage,
} from 'naive-ui';
import {
  ReloadOutline, InformationCircleOutline, PeopleOutline, BusinessOutline, PersonOutline,
  AddOutline, TrashOutline, SaveOutline,
} from '@vicons/ionicons5';

import {
  listRules, createRule, updateRule, deleteRule as apiDeleteRule,
  fetchOptions, listRoles, listDepartments, listUsers,
  type DataPermissionRule, type DimensionType, type RowScopeType, type ColumnPermission, type OptionItem,
} from '@/api/data-permission';

const message = useMessage();

const dimension = ref<DimensionType>('ROLE');
const dimensionValue = ref<string>('');
const candidates = ref<OptionItem[]>([]);
const options = ref<{
  row_scopes: OptionItem[];
  column_permissions: OptionItem[];
}>({ row_scopes: [], column_permissions: [] });

const rules = ref<DataPermissionRule[]>([]);
const loading = ref(false);
const saving = ref(false);

const rowForm = ref<{ scopeType?: RowScopeType | null }>({ scopeType: null });
const customPayloadText = ref('');

// 列级草稿行（新增字段用）
const draft = ref<{ entity: string; field: string; permission: ColumnPermission } | null>(null);

const subjectPlaceholder = computed(() => {
  if (dimension.value === 'ROLE') return '选择角色（如 HRBP / INTERVIEWER）';
  if (dimension.value === 'DEPARTMENT') return '选择部门';
  return '选择用户';
});

const rowScopeOptions = computed(() => options.value.row_scopes);
const columnPermissionOptions = computed(() => options.value.column_permissions);

const rulesForSubject = computed(() =>
  rules.value.filter(r => r.dimensionType === dimension.value && r.dimensionValue === dimensionValue.value),
);
const rowRule = computed(() => rulesForSubject.value.find(r => r.level === 'ROW') || null);
const columnRules = computed(() => rulesForSubject.value.filter(r => r.level === 'COLUMN'));
const rowCount = computed(() => (rowRule.value ? 1 : 0));
const colCount = computed(() => columnRules.value.length);

const PERM_LABEL: Record<ColumnPermission, string> = { READ: '可读', MASK: '脱敏', NONE: '隐藏' };
const PERM_TYPE: Record<ColumnPermission, 'success' | 'warning' | 'error'> = {
  READ: 'success', MASK: 'warning', NONE: 'error',
};
const SCOPE_LABEL: Record<string, string> = {
  ALL: '全部数据', DEPT: '仅本部门', DEPT_AND_SUB: '本部门及下属', SELF: '仅自己创建', CUSTOM: '自定义范围',
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
    options.value = {
      row_scopes: opts.row_scopes,
      column_permissions: opts.column_permissions,
    };
    syncRowForm();
  } catch (err: any) {
    message.error(`加载失败：${err?.message || err}`);
  } finally {
    loading.value = false;
  }
}

function syncRowForm() {
  if (rowRule.value) {
    rowForm.value.scopeType = rowRule.value.scopeType ?? null;
    customPayloadText.value = rowRule.value.scopePayload ? JSON.stringify(rowRule.value.scopePayload) : '';
  } else {
    rowForm.value.scopeType = null;
    customPayloadText.value = '';
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
  syncRowForm();
}

async function saveRowRule() {
  if (!dimensionValue.value) { message.warning('请先选择配置对象'); return; }
  if (!rowForm.value.scopeType) { message.warning('请选择数据可见范围'); return; }
  saving.value = true;
  try {
    const payload: any = {
      dimension_type: dimension.value,
      dimension_value: dimensionValue.value,
      level: 'ROW',
      scope_type: rowForm.value.scopeType,
      priority: 10,
      status: 1,
    };
    if (rowForm.value.scopeType === 'CUSTOM') {
      try {
        payload.scope_payload = customPayloadText.value.trim() ? JSON.parse(customPayloadText.value) : null;
      } catch {
        message.error('自定义范围不是合法 JSON');
        saving.value = false;
        return;
      }
    } else {
      payload.scope_payload = null;
    }
    if (rowRule.value) await updateRule(rowRule.value.id, payload);
    else await createRule(payload);
    await loadRules();
    syncRowForm();
    message.success(rowRule.value ? '行级规则已更新' : '行级规则已创建');
  } catch (err: any) {
    message.error(`保存失败：${err?.message || err}`);
  } finally {
    saving.value = false;
  }
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
    message.success('列级字段已添加');
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
    syncRowForm();
    message.success('已删除');
  } catch (err: any) {
    message.error(`删除失败：${err?.message || err}`);
  } finally {
    saving.value = false;
  }
}

// 行级删除走 popconfirm
function deleteRule(id: string) {
  // NPopconfirm 包裹在外面模板里调用
  apiDeleteRule(id).then(async () => {
    await loadRules();
    syncRowForm();
    message.success('已删除');
  }).catch((err: any) => message.error(`删除失败：${err?.message || err}`));
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
.dp-tip { margin-top: var(--space-3); }

.dp-form { display: flex; flex-wrap: wrap; gap: var(--space-4); align-items: flex-end; }
.dp-form__item { display: flex; flex-direction: column; gap: 6px; }
.dp-form__item--full { flex: 1 1 100%; }
.dp-form__label { font-size: var(--fs-13); color: var(--ink-soft); font-weight: 500; }
.dp-form__actions { flex-direction: row; align-items: center; gap: var(--space-3); }

/* 维度 radio 图标与文字间距 */
.dp-dimension :deep(.n-radio-button__label) { display: inline-flex; align-items: center; gap: 6px; }
</style>
