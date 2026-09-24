<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">{ t('pages.settings.DepartmentManagement.s1') }</h1>
        <p class="page-subtitle">{ t('pages.settings.DepartmentManagement.s2') }</p>
      </div>
      <div class="page-header-actions">
        <n-radio-group v-model:value="statusFilter" size="small">
          <n-radio-button value="ALL">{ t('pages.settings.DepartmentManagement.s3') }</n-radio-button>
          <n-radio-button value="ACTIVE">{ t('pages.settings.DepartmentManagement.s4') }</n-radio-button>
          <n-radio-button value="INACTIVE">{ t('pages.settings.DepartmentManagement.s5') }</n-radio-button>
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
          刷新
        </n-button>
        <n-button ghost @click="exportDepartments">
          <template #icon><n-icon :component="DownloadOutline" /></template>
          导出
        </n-button>
        <n-button ghost @click="openImportModal">
          <template #icon><n-icon :component="CloudUploadOutline" /></template>
          导入
        </n-button>
        <n-button type="primary" class="gradient-btn" @click="openCreateModal">
          <template #icon><n-icon :component="AddOutline" /></template>
          新增部门
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
        <n-descriptions-item label="部门名称">{{ viewDept.name }}</n-descriptions-item>
        <n-descriptions-item label="部门编号">{{ viewDept.code }}</n-descriptions-item>
        <n-descriptions-item label="部门ID">
          <span style="font-family: monospace; font-size: 12px; color: #8c8c8c">{{ viewDept.id }}</span>
        </n-descriptions-item>
        <n-descriptions-item label="上级部门">
          <span v-if="viewDept.parentId">{{ getParentName(viewDept) }}</span>
          <n-tag v-else type="warning" size="small">顶级</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="部门层级">
          <n-tag type="info" size="small" :bordered="false">第 {{ levelMap[viewDept.id] || 1 }} 级</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="部门负责人">{{ getUserName(viewDept.managerId) || '—' }}</n-descriptions-item>
        <n-descriptions-item label="部门负责人 2">{{ getUserName(viewDept.manager2Id) || '—' }}</n-descriptions-item>
        <n-descriptions-item label="部门 HRBP">{{ getUserName(viewDept.hrbpId) || '—' }}</n-descriptions-item>
        <n-descriptions-item label="分管 VP">{{ getUserName(viewDept.manager3Id) || '—' }}</n-descriptions-item>
        <n-descriptions-item label="状态">
          <n-tag :type="viewDept.status === 'INACTIVE' ? 'default' : 'success'" size="small">
            {{ viewDept.status === 'INACTIVE' ? '停用' : '启用' }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="排序值">{{ viewDept.sortOrder ?? '—' }}</n-descriptions-item>
        <n-descriptions-item label="组织路径">{{ viewDept.path || '—' }}</n-descriptions-item>
        <n-descriptions-item label="创建时间">{{ formatTime(viewDept.createdAt) }}</n-descriptions-item>
        <n-descriptions-item label="更新时间">{{ formatTime(viewDept.updatedAt) }}</n-descriptions-item>
      </n-descriptions>

      <!-- 编辑态：可编辑表单 -->
      <n-form v-else :model="formState" label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="部门编号">
              <n-input
                v-model:value="formState.code"
                placeholder="保存后系统自动生成（D + 6 位流水号）"
                :disabled="true"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="部门名称" required>
              <n-input v-model:value="formState.name" placeholder="请输入部门名称" />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="上级部门">
              <n-tree-select
                v-model:value="formState.parentId"
                :options="parentTreeData"
                placeholder="不选则为顶级部门"
                clearable
                default-expand-all
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="排序值">
              <n-input-number
                v-model:value="formState.sortOrder"
                :min="0"
                :max="9999"
                style="width: 100%"
                placeholder="数字越小越靠前"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-divider title-placement="left">人员配置</n-divider>

        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="部门负责人">
              <n-select
                v-model:value="formState.managerId"
                placeholder="请选择部门负责人"
                clearable
                filterable
                :options="userOptions"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="部门负责人 2">
              <n-select
                v-model:value="formState.manager2Id"
                placeholder="请选择部门负责人2"
                clearable
                filterable
                :options="userOptions"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="部门 HRBP">
              <n-select
                v-model:value="formState.hrbpId"
                placeholder="请选择部门HRBP"
                clearable
                filterable
                :options="userOptions"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="分管 VP">
              <n-select
                v-model:value="formState.manager3Id"
                placeholder="请选择分管VP"
                clearable
                filterable
                :options="userOptions"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="状态">
              <n-radio-group v-model:value="formState.status">
                <n-radio value="ACTIVE">启用</n-radio>
                <n-radio value="INACTIVE">停用</n-radio>
              </n-radio-group>
            </n-form-item>
          </n-grid-item>
        </n-grid>
      </n-form>

      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <!-- 查看态：关闭 + 编辑 -->
          <template v-if="deptModalMode === 'view'">
            <n-button text @click="closeDeptModal">关闭</n-button>
            <n-button type="primary" class="gradient-btn" @click="startEdit(viewDept)">
              <template #icon><n-icon :component="CreateOutline" /></template>
              编辑
            </n-button>
          </template>
          <!-- 编辑态：取消 + 保存 -->
          <template v-else>
            <n-button text @click="closeDeptModal">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="submitting" @click="handleDeptSubmit">保存部门</n-button>
          </template>
        </div>
      </template>
    </n-modal>

    <!-- 部门导入弹窗 -->
    <n-modal
      v-model:show="importModalVisible"
      preset="card"
      title="导入部门"
      :style="{ width: '720px' }"
      :mask-closable="false"
      :centered="true"
      :auto-focus="false"
    >
      <n-space vertical :size="12">
        <n-alert type="info" :show-icon="true">
          以「部门编号」为唯一键：编号已存在则更新，不存在则新建。父部门与负责人按编号 / 姓名自动匹配；本页操作不影响现有其他数据。
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
              选择 CSV 文件
            </n-button>
          </n-upload>
          <n-button text type="primary" @click="downloadTemplate">下载模板</n-button>
          <span v-if="importFile" style="color: var(--ink-soft); font-size: 13px;">已选择：{{ importFile }}</span>
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
          {{ importWarnings.length }} 条行存在负责人/上级未匹配（已置空或跳过），详见预览「说明」列。
        </n-alert>
      </n-space>

      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button text @click="closeImportModal">取消</n-button>
          <n-button
            type="primary"
            class="gradient-btn"
            :loading="importing"
            :disabled="!importPreview.length"
            @click="confirmImport"
          >
            确认导入（{{ importPreview.length }} 条）
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
    prefix: () => `共 ${departments.value.length} 条`,
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
  if (deptModalMode.value === 'view') return '部门详情';
  return editingDept.value ? '编辑部门' : '新建部门';
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
      message.error(res.data?.message || '加载部门列表失败');
    }
  } catch (error) {
    console.error('加载部门列表失败', error);
    message.error('网络错误，请检查后端服务');
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
    message.error(extractApiError(error, '加载用户列表失败'));
  }
};

// 用户下拉项
const userOptions = computed(() =>
  users.value.map(u => ({
    label: `${u.realName}（${u.username}）`,
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
      label: '顶级部门',
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
    message.error('请填写部门名称');
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
        message.success('部门更新成功');
        closeDeptModal();
        loadDepartments();
      } else {
        message.error(extractErrorMessage(res.data) || '更新失败');
      }
    } else {
      const res = await api.post('/departments/', payload);
      if (res.status === 201 || res.data?.success === true) {
        message.success('部门创建成功');
        closeDeptModal();
        loadDepartments();
      } else {
        message.error(extractErrorMessage(res.data) || '创建失败');
      }
    }
  } catch (error: any) {
    message.error(extractErrorMessage(error.response?.data) || '操作失败');
  } finally {
    submitting.value = false;
  }
};

// 删除
const handleDelete = async (record: Department) => {
  try {
    const res = await api.delete(`/departments/${record.id}/`);
    if (res.data?.success) {
      message.success('部门删除成功');
      loadDepartments();
    } else {
      message.error(res.data?.error || res.data?.message || '删除失败');
    }
  } catch (error: any) {
    message.error(error.response?.data?.error || error.response?.data?.message || '删除失败');
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
    return h(NTag, { type: 'warning', size: 'small' }, { default: () => '顶级' });
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
    title: '部门名称',
    key: 'name',
    width: 220,
    render: (row: Department) => renderName(row),
  },
  {
    title: '上级部门',
    key: 'parent',
    width: 180,
    render: (row: Department) => renderParent(row),
  },
  {
    title: '部门层级',
    key: 'level',
    width: 100,
    render: (row: Department) => {
      const lvl = levelMap.value[row.id] ?? 0;
      return h(NTag, { type: 'info', size: 'small', bordered: false }, { default: () => `第 ${lvl} 级` });
    },
  },
  {
    title: '部门负责人',
    key: 'managerId',
    width: 130,
    render: (row: Department) => renderUser(row.managerId),
  },
  {
    title: '部门 HRBP',
    key: 'hrbpId',
    width: 130,
    render: (row: Department) => renderUser(row.hrbpId),
  },
  {
    title: '排序值',
    key: 'sortOrder',
    width: 90,
    render: (row: Department) => (row.sortOrder != null ? String(row.sortOrder) : h('span', { style: 'color:#bfbfbf' }, '—')),
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row: Department) => {
      const status = row.status || (row.isActive === false ? 'INACTIVE' : 'ACTIVE');
      const map: Record<string, { type: any; label: string }> = {
        ACTIVE: { type: 'success', label: '启用' },
        INACTIVE: { type: 'default', label: '停用' },
      };
      const item = map[status] || { type: 'default', label: status };
      return h(NTag, { type: item.type, size: 'small' }, { default: () => item.label });
    },
  },
  {
    title: '操作',
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
              default: () => '添加下级',
              icon: () => h(NIcon, { component: AddOutline }),
            }
          ),
          h(
            NPopconfirm,
            {
              onPositiveClick: () => handleDelete(row),
              positiveText: '确认',
              negativeText: '取消',
            },
            {
              default: () => '确认删除此部门？',
              trigger: () =>
                h(
                  NButton,
                  { text: true, type: 'error', size: 'small' },
                  {
                    default: () => '删除',
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
    message.error(extractApiError(e, '获取部门数据失败'));
  }
  return [];
};

// 拉取全量用户（导入解析负责人/HRBP 用）
const fetchAllUsers = async (): Promise<User[]> => {
  try {
    const res = await api.get('/users/', { params: { page_size: 1000 } });
    if (res.data?.success) return res.data.data || [];
  } catch (e) {
    message.error(extractApiError(e, '获取用户数据失败'));
  }
  return [];
};

// 导出部门为 CSV（UTF-8 BOM，Excel 友好）
const exportDepartments = async () => {
  const all = await fetchAllDepartments();
  if (!all.length) {
    message.warning('暂无可导出的部门数据');
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
      d.status === 'INACTIVE' ? '停用' : '启用',
      d.sortOrder ?? '',
    ];
  });
  const lines = [EXPORT_HEADERS.map(csvEscape).join(','), ...rows.map(r => r.map(csvEscape).join(','))];
  const content = '﻿' + lines.join('\r\n');
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
  triggerDownload(blob, `部门数据_${new Date().toISOString().slice(0, 10)}.csv`);
  message.success(`已导出 ${all.length} 个部门`);
};

// 下载导入模板（仅表头）
const downloadTemplate = () => {
  const content = '﻿' + EXPORT_HEADERS.map(csvEscape).join(',');
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
  triggerDownload(blob, '部门导入模板.csv');
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
  { title: '部门编号', key: 'code', width: 110 },
  { title: '部门名称', key: 'name', width: 140 },
  { title: '上级部门编号', key: 'parentCode', width: 110 },
  { title: '状态', key: 'status', width: 80 },
  { title: '操作', key: 'action', width: 80,
    render: (r: any) => h(NTag, { type: r.action === '更新' ? 'warning' : 'success', size: 'small', bordered: false }, { default: () => r.action }) },
  { title: '说明', key: 'note', minWidth: 160,
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
      message.warning('文件无有效数据行');
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
      message.error('模板缺少「部门编号 / 部门名称」列');
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
      const statusRaw = iStatus >= 0 ? (cells[iStatus] || '').trim() : '启用';
      const sortRaw = iSort >= 0 ? (cells[iSort] || '').trim() : '';
      let note = '';
      if (parentCode && !codeToId.has(parentCode) && !all.find(d => d.code === parentCode)) {
        note += '上级编号未匹配(将置顶级);';
      }
      if (manager && !userByKey.has(manager)) note += '负责人未匹配(留空);';
      if (hrbp && !userByKey.has(hrbp)) note += 'HRBP未匹配(留空);';
      if (note) warnings.push(`第 ${i + 2} 行：${note}`);
      const action = code && codeToId.has(code) ? '更新' : '新建';
      preview.push({ _idx: i, code, name, parentCode, manager, hrbp, status: statusRaw, sortOrder: sortRaw, action, note: note ? note.slice(0, -1) : '' });
    });
    importPreview.value = preview;
    importWarnings.value = warnings;
    if (!preview.length) message.warning('未解析到有效部门行');
    else message.success(`已解析 ${preview.length} 条，可确认导入`);
  } catch (e) {
    message.error('CSV 解析失败，请检查文件格式');
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
            else { errors.push(`${r.name}: 更新失败`); r._done = true; }
          } else {
            const res = await api.post('/departments/', payload);
            if (res.status === 201 || res.data?.success) {
              created++;
              const newId = res.data?.data?.id || res.data?.id;
              if (r.code && newId) codeToId.set(r.code, newId);
              r._done = true; progress = true;
            } else { errors.push(`${r.name}: 创建失败`); r._done = true; }
          }
        } catch (e: any) {
          errors.push(`${r.name}: ${extractErrorMessage(e?.response?.data) || '请求异常'}`);
          r._done = true;
        }
      }
    }

    if (errors.length) {
      message.error(`导入完成：新建 ${created} / 更新 ${updated}，${errors.length} 条失败`);
    } else {
      message.success(`导入成功：新建 ${created} / 更新 ${updated}`);
    }
    closeImportModal();
    loadDepartments();
  } catch (e) {
    message.error(extractApiError(e, '导入失败'));
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
.page-header {
  flex-shrink: 0;
}
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
.spacer {
  flex: 1;
}

</style>
