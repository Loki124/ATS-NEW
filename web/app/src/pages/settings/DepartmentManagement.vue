<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.DepartmentManagement.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.DepartmentManagement.s2') }}</p>
      </div>
      <div class="page-header-actions">
        <n-radio-group v-model:value="statusFilter" size="small">
          <n-radio-button value="ALL">{{ t('pages.settings.DepartmentManagement.s3') }}</n-radio-button>
          <n-radio-button value="ACTIVE">{{ t('pages.settings.DepartmentManagement.s4') }}</n-radio-button>
          <n-radio-button value="INACTIVE">{{ t('pages.settings.DepartmentManagement.s5') }}</n-radio-button>
        </n-radio-group>
        <n-input
          v-model:value="searchKeyword"
          :placeholder="t('pages.settings.DepartmentManagement.s6')"
          style="width: 240px"
          clearable
          @clear="searchKeyword = ''"
        >
          <template #prefix>
            <n-icon :component="SearchOutline" />
          </template>
        </n-input>
        <div class="spacer"></div>
        <n-button ghost @click="loadDepartments">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          {{ t('pages.settings.DepartmentManagement.s7') }}
        </n-button>
        <n-button ghost @click="exportDepartments">
          <template #icon><n-icon :component="DownloadOutline" /></template>
          {{ t('pages.settings.DepartmentManagement.s8') }}
        </n-button>
        <n-button ghost @click="openImportModal">
          <template #icon><n-icon :component="CloudUploadOutline" /></template>
          {{ t('pages.settings.DepartmentManagement.s9') }}
        </n-button>
        <n-button type="primary" class="gradient-btn" @click="openCreateModal">
          <template #icon><n-icon :component="AddOutline" /></template>
          {{ t('pages.settings.DepartmentManagement.s10') }}
        </n-button>
      </div>
    </div>

    <div class="page-body">
      <n-card :bordered="false">
      <n-data-table
        :data="displayData"
        :columns="columns"
        :row-key="(row: Department) => row.id"
        :loading="loading"
        :pagination="pagination"
        :expanded-row-keys="expandedKeys"
        size="medium"
        @update:expanded-row-keys="onExpandedKeysChange"
      />
      </n-card>
    </div>

    <!-- 部门详情 / 编辑 合一弹窗（居中） -->
    <n-modal
      v-model:show="deptModalVisible"
      preset="card"
      :title="modalTitle"
      :style="{ width: '720px' }"
      :mask-closable="false"
      :centered="true"
      :auto-focus="false"
    >
      <!-- 查看态：详情描述 -->
      <n-descriptions
        v-if="deptModalMode === 'view' && viewDept"
        label-placement="left"
        bordered
        :column="1"
        size="medium"
      >
        <n-descriptions-item :label="t('pages.settings.DepartmentManagement.s11')">{{ viewDept.name }}</n-descriptions-item>
        <n-descriptions-item :label="t('pages.settings.DepartmentManagement.s12')">{{ viewDept.code }}</n-descriptions-item>
        <n-descriptions-item :label="t('pages.settings.DepartmentManagement.s13')">
          <span style="font-family: monospace; font-size: 12px; color: #8c8c8c">{{ viewDept.id }}</span>
        </n-descriptions-item>
        <n-descriptions-item :label="t('pages.settings.DepartmentManagement.s14')">
          <span v-if="viewDept.parentId">{{ getParentName(viewDept) }}</span>
          <n-tag v-else type="warning" size="small">{{ t('pages.settings.DepartmentManagement.s15') }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item :label="t('pages.settings.DepartmentManagement.s16')">
          <n-tag type="info" size="small" :bordered="false">{{ t('pages.settings.DepartmentManagement.s79', { n: levelMap[viewDept.id] || 1 }) }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item :label="t('pages.settings.DepartmentManagement.s17')">{{ getUserName(viewDept.managerId) || '—' }}</n-descriptions-item>
        <n-descriptions-item :label="t('pages.settings.DepartmentManagement.s18')">{{ getUserName(viewDept.manager2Id) || '—' }}</n-descriptions-item>
        <n-descriptions-item :label="t('pages.settings.DepartmentManagement.s19')">{{ getUserName(viewDept.hrbpId) || '—' }}</n-descriptions-item>
        <n-descriptions-item :label="t('pages.settings.DepartmentManagement.s20')">{{ getUserName(viewDept.manager3Id) || '—' }}</n-descriptions-item>
        <n-descriptions-item :label="t('pages.settings.DepartmentManagement.s21')">
          <n-tag :type="viewDept.status === 'INACTIVE' ? 'default' : 'success'" size="small">
            {{ viewDept.status === 'INACTIVE' ? t('pages.settings.DepartmentManagement.s45') : t('pages.settings.DepartmentManagement.s44') }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item :label="t('pages.settings.DepartmentManagement.s22')">{{ viewDept.sortOrder ?? '—' }}</n-descriptions-item>
        <n-descriptions-item :label="t('pages.settings.DepartmentManagement.s23')">{{ viewDept.path || '—' }}</n-descriptions-item>
        <n-descriptions-item :label="t('pages.settings.DepartmentManagement.s24')">{{ formatTime(viewDept.createdAt) }}</n-descriptions-item>
        <n-descriptions-item :label="t('pages.settings.DepartmentManagement.s25')">{{ formatTime(viewDept.updatedAt) }}</n-descriptions-item>
      </n-descriptions>

      <!-- 编辑态：可编辑表单 -->
      <n-form v-else :model="formState" label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item :label="t('pages.settings.DepartmentManagement.s26')">
              <n-input
                v-model:value="formState.code"
                :placeholder="t('pages.settings.DepartmentManagement.s27')"
                :disabled="true"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item :label="t('pages.settings.DepartmentManagement.s28')" required>
              <n-input v-model:value="formState.name" :placeholder="t('pages.settings.DepartmentManagement.s29')" />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item :label="t('pages.settings.DepartmentManagement.s30')">
              <n-tree-select
                v-model:value="formState.parentId"
                :options="parentTreeData"
                :placeholder="t('pages.settings.DepartmentManagement.s31')"
                clearable
                default-expand-all
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item :label="t('pages.settings.DepartmentManagement.s32')">
              <n-input-number
                v-model:value="formState.sortOrder"
                :min="0"
                :max="9999"
                style="width: 100%"
                :placeholder="t('pages.settings.DepartmentManagement.s33')"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-divider title-placement="left">{{ t('pages.settings.DepartmentManagement.s34') }}</n-divider>

        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item :label="t('pages.settings.DepartmentManagement.s35')">
              <n-select
                v-model:value="formState.managerId"
                :placeholder="t('pages.settings.DepartmentManagement.s36')"
                clearable
                filterable
                :options="userOptions"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item :label="t('pages.settings.DepartmentManagement.s37')">
              <n-select
                v-model:value="formState.manager2Id"
                :placeholder="t('pages.settings.DepartmentManagement.s38')"
                clearable
                filterable
                :options="userOptions"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item :label="t('pages.settings.DepartmentManagement.s39')">
              <n-select
                v-model:value="formState.hrbpId"
                :placeholder="t('pages.settings.DepartmentManagement.s40')"
                clearable
                filterable
                :options="userOptions"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item :label="t('pages.settings.DepartmentManagement.s41')">
              <n-select
                v-model:value="formState.manager3Id"
                :placeholder="t('pages.settings.DepartmentManagement.s42')"
                clearable
                filterable
                :options="userOptions"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item :label="t('pages.settings.DepartmentManagement.s43')">
              <n-radio-group v-model:value="formState.status">
                <n-radio value="ACTIVE">{{ t('pages.settings.DepartmentManagement.s44') }}</n-radio>
                <n-radio value="INACTIVE">{{ t('pages.settings.DepartmentManagement.s45') }}</n-radio>
              </n-radio-group>
            </n-form-item>
          </n-grid-item>
        </n-grid>
      </n-form>

      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <!-- 查看态：关闭 + 编辑 -->
          <template v-if="deptModalMode === 'view'">
            <n-button text @click="closeDeptModal">{{ t('pages.settings.DepartmentManagement.s46') }}</n-button>
            <n-button type="primary" class="gradient-btn" @click="startEdit(viewDept)">
              <template #icon><n-icon :component="CreateOutline" /></template>
              {{ t('pages.settings.DepartmentManagement.s47') }}
            </n-button>
          </template>
          <!-- 编辑态：取消 + 保存 -->
          <template v-else>
            <n-button text @click="closeDeptModal">{{ t('pages.settings.DepartmentManagement.s48') }}</n-button>
            <n-button type="primary" class="gradient-btn" :loading="submitting" @click="handleDeptSubmit">{{ t('pages.settings.DepartmentManagement.s49') }}</n-button>
          </template>
        </div>
      </template>
    </n-modal>

    <!-- 部门导入弹窗 -->
    <n-modal
      v-model:show="importModalVisible"
      preset="card"
      :title="t('pages.settings.DepartmentManagement.s50')"
      :style="{ width: '720px' }"
      :mask-closable="false"
      :centered="true"
      :auto-focus="false"
    >
      <n-space vertical :size="12">
        <n-alert type="info" :show-icon="true">
          {{ t('pages.settings.DepartmentManagement.s51') }}
        </n-alert>
        <div style="display: flex; align-items: center; gap: 12px;">
          <n-upload
            accept=".csv"
            :default-upload="false"
            :max="1"
            @change="onImportFileChange"
          >
            <n-button ghost>
              <template #icon><n-icon :component="CloudUploadOutline" /></template>
              {{ t('pages.settings.DepartmentManagement.s52') }}
            </n-button>
          </n-upload>
          <n-button text type="primary" @click="downloadTemplate">{{ t('pages.settings.DepartmentManagement.s53') }}</n-button>
          <span v-if="importFile" style="color: var(--ink-soft); font-size: 13px;">{{ t('pages.settings.DepartmentManagement.s80') }}{{ importFile }}</span>
        </div>

        <div v-if="importPreview.length" style="max-height: 320px; overflow-y: auto;">
          <n-data-table
            :data="importPreview"
            :columns="importPreviewColumns"
            :row-key="(r: any) => r._idx"
            :pagination="false"
            size="small"
          />
        </div>
        <n-alert v-if="importWarnings.length" type="warning" :show-icon="true">
          {{ t('pages.settings.DepartmentManagement.s81', { n: importWarnings.length }) }}
        </n-alert>
      </n-space>

      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button text @click="closeImportModal">{{ t('pages.settings.DepartmentManagement.s54') }}</n-button>
          <n-button
            type="primary"
            class="gradient-btn"
            :loading="importing"
            :disabled="!importPreview.length"
            @click="confirmImport"
          >
            {{ t('pages.settings.DepartmentManagement.s82', { n: importPreview.length }) }}
          </n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, onMounted, computed, watch, h } from 'vue';
import {
  AddOutline,
  CreateOutline,
  TrashOutline,
  RefreshOutline,
  PersonOutline,
  SearchOutline,
  DownloadOutline,
  CloudUploadOutline,
} from '@vicons/ionicons5';
import {
  NTag,
  NButton,
  NSpace,
  NIcon,
  NPopconfirm,
  NInput,
  NModal,
  NForm,
  NGrid,
  NGridItem,
  NFormItem,
  NTreeSelect,
  NSelect,
  NInputNumber,
  NRadioGroup,
  NRadio,
  NRadioButton,
  NDivider,
  NCard,
  NDescriptions,
  NDescriptionsItem,
  NUpload,
  NAlert,
  useMessage,
} from 'naive-ui';
import api from '../../api/auth';
import { extractApiError } from '../../api/dynamic-field';
import { localPagination } from '../../composables/useTablePagination';
const { t } = useI18n()

const message = useMessage();

interface Department {
  id: string;
  name: string;
  code: string;
  parentId?: string | null;
  level?: number;
  path?: string;
  managerId?: string | null;
  manager2Id?: string | null;
  manager3Id?: string | null;
  hrbpId?: string | null;
  isActive?: boolean;
  status: string;
  sortOrder?: number;
  createdAt?: string;
  updatedAt?: string;
}

interface User {
  id: string;
  realName: string;
  username: string;
  status: string;
}

// 状态
const departments = ref<Department[]>([]);
const users = ref<User[]>([]);
const loading = ref(false);
const submitting = ref(false);
// 分页：复用统一 localPagination；树形模式下 n-data-table 的 itemCount 仅计顶层节点，
// 故覆盖 prefix 以展示「部门总数」（含所有层级），满足「按部门数量统计」诉求。
const pagination = (() => {
  const base = localPagination();
  return {
    ...base,
    prefix: () => t('pages.settings.DepartmentManagement.s83', { n: departments.value.length }),
  };
})();

// 树形展开状态：首次加载数据后默认展开根组织（集团总部），从而显示所有一级部门；
// 第 2 级及以下仍折叠。后续用户点击节点前的箭头可手动展开/收起子树。
const expandedKeys = ref<string[]>([]);
const onExpandedKeysChange = (keys: string[]) => {
  expandedKeys.value = keys;
};
// 集团总部（根组织，parentId 为空）的 id：用于新增部门默认上级、以及默认展开
const rootDeptId = computed(() => {
  const root = departments.value.find((d) => !d.parentId);
  return root ? root.id : undefined;
});
// 仅首次加载数据后设默认展开根组织（显示一级部门），避免覆盖用户手动操作
let defaultExpandApplied = false;
const applyDefaultExpand = () => {
  if (defaultExpandApplied) return;
  if (rootDeptId.value) {
    expandedKeys.value = [rootDeptId.value];
    defaultExpandApplied = true;
  }
};

// ===== 合一弹窗（查看 / 编辑 两态）=====
const deptModalVisible = ref(false);
const deptModalMode = ref<'view' | 'edit'>('view');
const editingDept = ref<Department | null>(null);
const viewDept = ref<Department | null>(null);

const modalTitle = computed(() => {
  if (deptModalMode.value === 'view') return t('pages.settings.DepartmentManagement.s84');
  return editingDept.value ? t('pages.settings.DepartmentManagement.s85') : t('pages.settings.DepartmentManagement.s86');
});

// 点击部门名称 → 查看态（详情）
const openDetail = (row: Department) => {
  viewDept.value = row;
  editingDept.value = null;
  deptModalMode.value = 'view';
  deptModalVisible.value = true;
};

// 进入编辑态（新建/添加下级 或 从查看态点「编辑」）
const startEdit = (record: Department | null) => {
  editingDept.value = record;
  if (record) {
    Object.assign(formState, {
      code: record.code,
      name: record.name,
      parentId: record.parentId || undefined,
      managerId: record.managerId || undefined,
      manager2Id: record.manager2Id || undefined,
      manager3Id: record.manager3Id || undefined,
      hrbpId: record.hrbpId || undefined,
      sortOrder: record.sortOrder || 0,
      status: record.status,
    });
  } else {
    Object.assign(formState, {
      code: '',
      name: '',
      parentId: rootDeptId.value, // 未选上级时默认挂到集团总部（层级自动为第 1 级）
      managerId: undefined,
      manager2Id: undefined,
      manager3Id: undefined,
      hrbpId: undefined,
      sortOrder: 0,
      status: 'ACTIVE',
    });
  }
  deptModalMode.value = 'edit';
  deptModalVisible.value = true;
};

const closeDeptModal = () => {
  deptModalVisible.value = false;
  editingDept.value = null;
  viewDept.value = null;
  deptModalMode.value = 'view';
};

// 打开新建弹窗
const openCreateModal = () => startEdit(null);

// 打开「添加下级」弹窗：复用新建弹窗并预置上级为该部门
const openCreateChildModal = (parent: Department) => {
  startEdit(null);
  if (parent) formState.parentId = parent.id;
};

// 部门层级：根据 parentId 链计算深度（集团总部等根组织 = 第 0 级，其子为第 1 级，依此类推）
const levelMap = computed<Record<string, number>>(() => {
  const map: Record<string, number> = {};
  const byId = new Map(departments.value.map((d) => [d.id, d]));
  for (const d of departments.value) {
    let level = 0;
    let cur: Department | undefined = d;
    const seen = new Set<string>();
    while (cur?.parentId && !seen.has(cur.id)) {
      seen.add(cur.id);
      const parent = byId.get(cur.parentId);
      if (!parent) break;
      level++;
      cur = parent;
    }
    map[d.id] = level;
  }
  return map;
});
const searchKeyword = ref('');

const formState = reactive({
  code: '',
  name: '',
  parentId: undefined as string | undefined,
  managerId: undefined as string | undefined,
  manager2Id: undefined as string | undefined,
  manager3Id: undefined as string | undefined,
  hrbpId: undefined as string | undefined,
  sortOrder: 0,
  status: 'ACTIVE',
});

// 加载部门列表
const loadDepartments = async () => {
  loading.value = true;
  try {
    const params: Record<string, any> = { page_size: 200 };
    if (statusFilter.value === 'ACTIVE') params.is_active = 'true';
    else if (statusFilter.value === 'INACTIVE') params.is_active = 'false';
    const res = await api.get('/departments/', { params });
    if (res.data?.success) {
      departments.value = res.data.data || [];
      applyDefaultExpand();
    } else {
      message.error(res.data?.message || t('pages.settings.DepartmentManagement.s87'));
    }
  } catch (error) {
    console.error(t('pages.settings.DepartmentManagement.s87'), error);
    message.error(t('pages.settings.DepartmentManagement.s55'));
  } finally {
    loading.value = false;
  }
};

// 加载用户列表（用于下拉选择）
const loadUsers = async () => {
  try {
    const res = await api.get('/users/');
    if (res.data?.success) {
      users.value = (res.data.data || []).filter((u: User) => u.status === 'ACTIVE');
    }
  } catch (error) {
    message.error(extractApiError(error, t('pages.settings.DepartmentManagement.s88')));
  }
};

// 用户下拉项
const userOptions = computed(() =>
  users.value.map(u => ({
    label: t('pages.settings.DepartmentManagement.s114', { realName: u.realName, username: u.username }),
    value: u.id,
  }))
);

// 搜索过滤后的部门
const filteredDepartments = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase();
  if (!keyword) return departments.value;
  return departments.value.filter(
    d => d.name.toLowerCase().includes(keyword) || d.code.toLowerCase().includes(keyword)
  );
});

// 表格展示数据：树形（children 空时置 undefined，避免出现空展开箭头）；
// 搜索时退化为平铺过滤列表，保证命中任意层级部门
const displayData = computed(() => {
  if (searchKeyword.value.trim()) return filteredDepartments.value;
  const buildTree = (parentId: string | null): any[] => {
    const children = departments.value
      .filter((d) => (d.parentId || null) === parentId)
      .sort((a, b) => (a.sortOrder || 0) - (b.sortOrder || 0));
    return children.map((d) => {
      const kids = buildTree(d.id);
      return kids.length ? { ...d, children: kids } : { ...d };
    });
  };
  return buildTree(null);
});

// 启用/停用筛选：ALL=全部 / ACTIVE=启用 / INACTIVE=停用
const statusFilter = ref<'ALL' | 'ACTIVE' | 'INACTIVE'>('ALL');
watch(statusFilter, () => loadDepartments());

// 上级部门树（排除自身及子部门）
const parentTreeData = computed(() => {
  const buildTree = (parentId: string | null): any[] => {
    const children = departments.value
      .filter(d => (d.parentId || null) === parentId)
      .sort((a, b) => (a.sortOrder || 0) - (b.sortOrder || 0));
    return children.map(d => ({
      label: `${d.name} (${d.code})`,
      key: d.id,
      disabled: editingDept.value ? isDescendantOrSelf(d.id, editingDept.value.id) : false,
      children: buildTree(d.id),
    }));
  };
  return [
    {
      label: t('pages.settings.DepartmentManagement.s89'),
      key: '__ROOT__',
      disabled: true,
      children: buildTree(null),
    },
  ];
});

// 判断是否某部门的后代（包含自身）
const isDescendantOrSelf = (id: string, ancestorId: string): boolean => {
  if (id === ancestorId) return true;
  let cur = departments.value.find(d => d.id === id);
  while (cur && cur.parentId) {
    if (cur.parentId === ancestorId) return true;
    cur = departments.value.find(d => d.id === cur!.parentId);
  }
  return false;
};

// 从 envelope / DRF 错误结构中提取第一条可读错误信息
const extractErrorMessage = (data: any): string => {
  if (!data) return '';
  if (data.errors && typeof data.errors === 'object') {
    for (const key of Object.keys(data.errors)) {
      const val = data.errors[key];
      if (Array.isArray(val) && val.length) return `${key}: ${val[0]}`;
      if (typeof val === 'string') return `${key}: ${val}`;
    }
  }
  return data.error || data.message || data.detail || '';
};

// 提交表单
const handleDeptSubmit = async () => {
  if (!formState.name) {
    message.error(t('pages.settings.DepartmentManagement.s56'));
    return;
  }
  submitting.value = true;
  try {
    const payload = {
      name: formState.name,
      code: formState.code,
      parentId: formState.parentId || null,
      managerId: formState.managerId || null,
      manager2Id: formState.manager2Id || null,
      manager3Id: formState.manager3Id || null,
      hrbpId: formState.hrbpId || null,
      sortOrder: formState.sortOrder,
      status: formState.status,
    };
    if (editingDept.value) {
      const res = await api.put(`/departments/${editingDept.value.id}/`, payload);
      if (res.status === 200 || res.data?.success === true) {
        message.success(t('pages.settings.DepartmentManagement.s57'));
        closeDeptModal();
        loadDepartments();
      } else {
        message.error(extractErrorMessage(res.data) || t('pages.settings.DepartmentManagement.s90'));
      }
    } else {
      const res = await api.post('/departments/', payload);
      if (res.status === 201 || res.data?.success === true) {
        message.success(t('pages.settings.DepartmentManagement.s58'));
        closeDeptModal();
        loadDepartments();
      } else {
        message.error(extractErrorMessage(res.data) || t('pages.settings.DepartmentManagement.s91'));
      }
    }
  } catch (error: any) {
    message.error(extractErrorMessage(error.response?.data) || t('pages.settings.DepartmentManagement.s92'));
  } finally {
    submitting.value = false;
  }
};

// 删除
const handleDelete = async (record: Department) => {
  try {
    const res = await api.delete(`/departments/${record.id}/`);
    if (res.data?.success) {
      message.success(t('pages.settings.DepartmentManagement.s59'));
      loadDepartments();
    } else {
      message.error(res.data?.error || res.data?.message || t('pages.settings.DepartmentManagement.s93'));
    }
  } catch (error: any) {
    message.error(error.response?.data?.error || error.response?.data?.message || t('pages.settings.DepartmentManagement.s93'));
  }
};

const getUserName = (userId?: string | null) => {
  if (!userId) return null;
  const user = users.value.find(u => String(u.id) === String(userId));
  return user ? user.realName || user.username : null;
};

const renderUser = (userId?: string | null) => {
  const name = getUserName(userId);
  if (!name) return h('span', { style: 'color: #bfbfbf' }, '—');
  return h(NTag, { type: 'info', size: 'small' }, {
    default: () => name,
    icon: () => h(NIcon, { component: PersonOutline }),
  });
};

const renderParent = (record: Department) => {
  if (!record.parentId) {
    return h(NTag, { type: 'warning', size: 'small' }, { default: () => t('pages.settings.DepartmentManagement.s15') });
  }
  const parent = departments.value.find(d => d.id === record.parentId);
  if (!parent) return h('span', { style: 'color: #bfbfbf' }, '—');
  return h('span', {}, `${parent.name} (${parent.code})`);
};

// 详情用：父级名称字符串
const getParentName = (dept: Department): string => {
  if (!dept.parentId) return '';
  const p = departments.value.find(d => d.id === dept.parentId);
  return p ? `${p.name} (${p.code})` : '';
};

const formatTime = (t?: string): string => {
  if (!t) return '—';
  const d = new Date(t);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleString('zh-CN', { hour12: false });
};

// 名称渲染：树模式下 n-data-table 已按层级自动缩进，这里不再手动缩进（避免双缩进）
const renderName = (row: Department) => {
  return h(
    NButton,
    { text: true, type: 'primary', size: 'small', onClick: () => openDetail(row) },
    { default: () => row.name }
  );
};

const columns = computed(() => [
  {
    title: t('pages.settings.DepartmentManagement.s60'),
    key: 'name',
    width: 220,
    render: (row: Department) => renderName(row),
  },
  {
    title: t('pages.settings.DepartmentManagement.s61'),
    key: 'parent',
    width: 180,
    render: (row: Department) => renderParent(row),
  },
  {
    title: t('pages.settings.DepartmentManagement.s62'),
    key: 'level',
    width: 100,
    render: (row: Department) => {
      const lvl = levelMap.value[row.id] ?? 0;
      return h(NTag, { type: 'info', size: 'small', bordered: false }, { default: () => t('pages.settings.DepartmentManagement.s79', { n: lvl }) });
    },
  },
  {
    title: t('pages.settings.DepartmentManagement.s63'),
    key: 'managerId',
    width: 130,
    render: (row: Department) => renderUser(row.managerId),
  },
  {
    title: t('pages.settings.DepartmentManagement.s64'),
    key: 'hrbpId',
    width: 130,
    render: (row: Department) => renderUser(row.hrbpId),
  },
  {
    title: t('pages.settings.DepartmentManagement.s65'),
    key: 'sortOrder',
    width: 90,
    render: (row: Department) => (row.sortOrder != null ? String(row.sortOrder) : h('span', { style: 'color:#bfbfbf' }, '—')),
  },
  {
    title: t('pages.settings.DepartmentManagement.s66'),
    key: 'status',
    width: 90,
    render: (row: Department) => {
      const status = row.status || (row.isActive === false ? 'INACTIVE' : 'ACTIVE');
      const map: Record<string, { type: any; label: string }> = {
        ACTIVE: { type: 'success', label: t('pages.settings.DepartmentManagement.s44') },
        INACTIVE: { type: 'default', label: t('pages.settings.DepartmentManagement.s45') },
      };
      const item = map[status] || { type: 'default', label: status };
      return h(NTag, { type: item.type, size: 'small' }, { default: () => item.label });
    },
  },
  {
    title: t('pages.settings.DepartmentManagement.s67'),
    key: 'actions',
    width: 200,
    fixed: 'right' as const,
    render: (row: Department) =>
      h(NSpace, { size: 'small' }, {
        default: () => [
          h(
            NButton,
            {
              text: true,
              type: 'primary',
              size: 'small',
              onClick: () => openCreateChildModal(row),
            },
            {
              default: () => t('pages.settings.DepartmentManagement.s94'),
              icon: () => h(NIcon, { component: AddOutline }),
            }
          ),
          h(
            NPopconfirm,
            {
              onPositiveClick: () => handleDelete(row),
              positiveText: t('pages.settings.DepartmentManagement.s95'),
              negativeText: t('pages.settings.DepartmentManagement.s48'),
            },
            {
              default: () => t('pages.settings.DepartmentManagement.s96'),
              trigger: () =>
                h(
                  NButton,
                  { text: true, type: 'error', size: 'small' },
                  {
                    default: () => t('pages.settings.DepartmentManagement.s97'),
                    icon: () => h(NIcon, { component: TrashOutline }),
                  }
                ),
            }
          ),
        ],
      }),
  },
]);

/* ============================ 部门导入 / 导出 ============================ */

// 导出列（与导入模板一致）
const EXPORT_HEADERS = ['部门编号', '部门名称', '上级部门编号', '上级部门名称', '部门负责人', '部门HRBP', '状态', '排序值'];

// CSV 字段转义：含逗号/引号/换行则包裹双引号并转义内部引号
const csvEscape = (v: string | number): string => {
  const s = v == null ? '' : String(v);
  if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
};

// 触发浏览器下载
const triggerDownload = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

// 拉取全量部门（导出/导入解析用，不受状态筛选影响）
const fetchAllDepartments = async (): Promise<Department[]> => {
  try {
    const res = await api.get('/departments/', { params: { page_size: 1000 } });
    if (res.data?.success) return res.data.data || [];
  } catch (e) {
    message.error(extractApiError(e, t('pages.settings.DepartmentManagement.s98')));
  }
  return [];
};

// 拉取全量用户（导入解析负责人/HRBP 用）
const fetchAllUsers = async (): Promise<User[]> => {
  try {
    const res = await api.get('/users/', { params: { page_size: 1000 } });
    if (res.data?.success) return res.data.data || [];
  } catch (e) {
    message.error(extractApiError(e, t('pages.settings.DepartmentManagement.s99')));
  }
  return [];
};

// 导出部门为 CSV（UTF-8 BOM，Excel 友好）
const exportDepartments = async () => {
  const all = await fetchAllDepartments();
  if (!all.length) {
    message.warning(t('pages.settings.DepartmentManagement.s68'));
    return;
  }
  const byId = new Map(all.map(d => [d.id, d]));
  const rows = all.map(d => {
    const parent = d.parentId ? byId.get(d.parentId) : null;
    return [
      d.code,
      d.name,
      parent?.code || '',
      parent?.name || '',
      getUserName(d.managerId) || '',
      getUserName(d.hrbpId) || '',
      d.status === 'INACTIVE' ? t('pages.settings.DepartmentManagement.s45') : t('pages.settings.DepartmentManagement.s44'),
      d.sortOrder ?? '',
    ];
  });
  const lines = [EXPORT_HEADERS.map(csvEscape).join(','), ...rows.map(r => r.map(csvEscape).join(','))];
  const content = '﻿' + lines.join('\r\n');
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
  triggerDownload(blob, `${t('pages.settings.DepartmentManagement.s100')}_${new Date().toISOString().slice(0, 10)}.csv`);
  message.success(t('pages.settings.DepartmentManagement.s102', { n: all.length }));
};

// 下载导入模板（仅表头）
const downloadTemplate = () => {
  const content = '﻿' + EXPORT_HEADERS.map(csvEscape).join(',');
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
  triggerDownload(blob, t('pages.settings.DepartmentManagement.s101') + '.csv');
};

// 简易 CSV 解析（支持引号包裹、字段内逗号/换行）
const parseCsv = (text: string): string[][] => {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += c;
    } else {
      if (c === '"') inQuotes = true;
      else if (c === ',') { row.push(field); field = ''; }
      else if (c === '\r') { /* ignore */ }
      else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
      else field += c;
    }
  }
  if (field.length > 0 || row.length > 0) { row.push(field); rows.push(row); }
  return rows.filter(r => r.some(c => c.trim() !== ''));
};

// 导入弹窗状态
const importModalVisible = ref(false);
const importFile = ref('');
const importing = ref(false);
const importPreview = ref<any[]>([]);
const importWarnings = ref<string[]>([]);

interface ImportRow {
  _idx: number;
  code: string;
  name: string;
  parentCode: string;
  manager: string;
  hrbp: string;
  status: string;
  sortOrder: string;
  action: string; // 新建 / 更新
  note: string;
}

const importPreviewColumns = [
  { title: t('pages.settings.DepartmentManagement.s69'), key: 'code', width: 110 },
  { title: t('pages.settings.DepartmentManagement.s70'), key: 'name', width: 140 },
  { title: t('pages.settings.DepartmentManagement.s71'), key: 'parentCode', width: 110 },
  { title: t('pages.settings.DepartmentManagement.s72'), key: 'status', width: 80 },
  { title: t('pages.settings.DepartmentManagement.s73'), key: 'action', width: 80,
    render: (r: any) => h(NTag, { type: r.action === '更新' ? 'warning' : 'success', size: 'small', bordered: false }, { default: () => r.action }) },
  { title: t('pages.settings.DepartmentManagement.s74'), key: 'note', minWidth: 160,
    render: (r: any) => r.note ? h('span', { style: 'color: var(--ink-soft); font-size: 12px' }, r.note) : h('span', { style: 'color:#bfbfbf' }, '—') },
];

const openImportModal = async () => {
  importFile.value = '';
  importPreview.value = [];
  importWarnings.value = [];
  importModalVisible.value = true;
};

const closeImportModal = () => {
  importModalVisible.value = false;
  importFile.value = '';
  importPreview.value = [];
  importWarnings.value = [];
};

// 选择 CSV → 解析为预览（仅本地，未写库）
const onImportFileChange = async ({ file }: any) => {
  const raw = file?.file as File | undefined;
  if (!raw) return;
  importFile.value = raw.name;
  importPreview.value = [];
  importWarnings.value = [];
  try {
    const text = await raw.text();
    const parsed = parseCsv(text);
    if (parsed.length < 2) {
      message.warning(t('pages.settings.DepartmentManagement.s75'));
      return;
    }
    const header = parsed[0].map(h => h.trim());
    const colOf = (...keys: string[]) => {
      for (const k of keys) {
        const idx = header.findIndex(x => x.includes(k));
        if (idx >= 0) return idx;
      }
      return -1;
    };
    const iCode = colOf('部门编号', '编号');
    const iName = colOf('部门名称', '名称');
    const iParent = colOf('上级部门编号', '上级编号');
    const iManager = colOf('部门负责人');
    const iHrbp = colOf('部门HRBP', 'HRBP');
    const iStatus = colOf('状态');
    const iSort = colOf('排序值', '排序');
    if (iCode < 0 || iName < 0) {
      message.error(t('pages.settings.DepartmentManagement.s76'));
      return;
    }
    const all = await fetchAllDepartments();
    const allUsers = await fetchAllUsers();
    const codeToId = new Map(all.map(d => [d.code, d.id]));
    const userByKey = new Map<string, string>();
    allUsers.forEach(u => { userByKey.set(u.username, u.id); userByKey.set(u.realName, u.id); });
    const warnings: string[] = [];
    const preview: ImportRow[] = [];
    parsed.slice(1).forEach((cells, i) => {
      const code = (cells[iCode] || '').trim();
      const name = (cells[iName] || '').trim();
      if (!name) return; // 跳过无名称行
      const parentCode = iParent >= 0 ? (cells[iParent] || '').trim() : '';
      const manager = iManager >= 0 ? (cells[iManager] || '').trim() : '';
      const hrbp = iHrbp >= 0 ? (cells[iHrbp] || '').trim() : '';
      const statusRaw = iStatus >= 0 ? (cells[iStatus] || '').trim() : t('pages.settings.DepartmentManagement.s44');
      const sortRaw = iSort >= 0 ? (cells[iSort] || '').trim() : '';
      let note = '';
      if (parentCode && !codeToId.has(parentCode) && !all.find(d => d.code === parentCode)) {
        note += t('pages.settings.DepartmentManagement.s104');
      }
      if (manager && !userByKey.has(manager)) note += t('pages.settings.DepartmentManagement.s105');
      if (hrbp && !userByKey.has(hrbp)) note += t('pages.settings.DepartmentManagement.s106');
      if (note) warnings.push(t('pages.settings.DepartmentManagement.s107', { n: i + 2, note }));
      const action = code && codeToId.has(code) ? t('pages.settings.DepartmentManagement.s111') : t('pages.settings.DepartmentManagement.s112');
      preview.push({ _idx: i, code, name, parentCode, manager, hrbp, status: statusRaw, sortOrder: sortRaw, action, note: note ? note.slice(0, -1) : '' });
    });
    importPreview.value = preview;
    importWarnings.value = warnings;
    if (!preview.length) message.warning(t('pages.settings.DepartmentManagement.s77'));
    else message.success(t('pages.settings.DepartmentManagement.s103', { n: preview.length }));
  } catch (e) {
    message.error(t('pages.settings.DepartmentManagement.s78'));
  }
};

// 解析负责人/HRBP 姓名→用户ID；状态文本→枚举
const resolveUser = (key: string, userByKey: Map<string, string>): string | null => {
  if (!key) return null;
  return userByKey.get(key) || null;
};
const resolveStatus = (raw: string): string => {
  if (['停用', 'INACTIVE', '0', 'false'].includes(raw)) return 'INACTIVE';
  return 'ACTIVE';
};

// 确认导入：按部门编号 upsert（多趟处理保证父级先于子级创建）
const confirmImport = async () => {
  if (!importPreview.value.length) return;
  importing.value = true;
  try {
    const all = await fetchAllDepartments();
    const allUsers = await fetchAllUsers();
    const codeToId = new Map(all.map(d => [d.code, d.id]));
    const userByKey = new Map<string, string>();
    allUsers.forEach(u => { userByKey.set(u.username, u.id); userByKey.set(u.realName, u.id); });

    let created = 0;
    let updated = 0;
    const errors: string[] = [];
    const rows = importPreview.value.map(r => ({ ...r }));

    // 最多遍历 rows.length 趟，每趟尝试未完成的行；父级创建后其编号可被子级解析
    let progress = true;
    let guard = rows.length + 1;
    while (progress && guard-- > 0) {
      progress = false;
      for (const r of rows) {
        if (r._done) continue;
        let parentId: string | null = null;
        if (r.parentCode) {
          if (codeToId.has(r.parentCode)) parentId = codeToId.get(r.parentCode)!;
          else { continue; } // 父级尚未就绪，本趟跳过，留待后续趟
        }
        const managerId = resolveUser(r.manager, userByKey);
        const hrbpId = resolveUser(r.hrbp, userByKey);
        const status = resolveStatus(r.status);
        const sortOrder = parseInt(r.sortOrder, 10);
        const payload: any = {
          name: r.name,
          parentId,
          managerId,
          manager2Id: null,
          manager3Id: null,
          hrbpId,
          sortOrder: isNaN(sortOrder) ? 0 : sortOrder,
          status,
        };
        try {
          if (r.code && codeToId.has(r.code)) {
            const id = codeToId.get(r.code)!;
            const res = await api.put(`/departments/${id}/`, payload);
            if (res.status === 200 || res.data?.success) { updated++; r._done = true; progress = true; }
            else { errors.push(`${r.name}: ${t('pages.settings.DepartmentManagement.s90')}`); r._done = true; }
          } else {
            const res = await api.post('/departments/', payload);
            if (res.status === 201 || res.data?.success) {
              created++;
              const newId = res.data?.data?.id || res.data?.id;
              if (r.code && newId) codeToId.set(r.code, newId);
              r._done = true; progress = true;
            } else { errors.push(`${r.name}: ${t('pages.settings.DepartmentManagement.s91')}`); r._done = true; }
          }
        } catch (e: any) {
          errors.push(`${r.name}: ${extractErrorMessage(e?.response?.data) || t('pages.settings.DepartmentManagement.s108')}`);
          r._done = true;
        }
      }
    }

    if (errors.length) {
      message.error(t('pages.settings.DepartmentManagement.s109', { created, updated, errors: errors.length }));
    } else {
      message.success(t('pages.settings.DepartmentManagement.s110', { created, updated }));
    }
    closeImportModal();
    loadDepartments();
  } catch (e) {
    message.error(extractApiError(e, t('pages.settings.DepartmentManagement.s113')));
  } finally {
    importing.value = false;
  }
};

onMounted(() => {
  loadDepartments();
  loadUsers();
});
</script>

<style scoped>
/* === 2026-08-24 page-header + page-body 三件套 === */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
/* .page-header 的 flex-shrink:0 与 .spacer 的 flex:1 已由 glass.css 全局 .page-header / .toolbar .spacer 提供，此处不再私有重写（SETTINGS_PAGE_STRUCTURE.md §0） */
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.page-header-actions {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}
</style>
