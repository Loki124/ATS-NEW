<template>
  <div class="page-container">
<div class="page-body">
    <div class="page-header">
      <div>
        <h1 class="page-title">部门管理</h1>
        <p class="page-subtitle">维护组织架构与部门职责，作为管控与权限的归属单元</p>
      </div>
      <div class="kpi-row">
        <div class="kpi-card"><span class="kpi-label">部门总数</span><span class="kpi-value">{{ departments.length }}</span></div>
      </div>
      <div class="page-header-actions">
        <n-space>
          <n-input
            v-model:value="searchKeyword"
            placeholder="搜索部门名称/编号"
            style="width: 240px"
            clearable
            @keyup.enter="loadDepartments"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
          <n-button @click="loadDepartments">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            刷新
          </n-button>
          <n-button type="primary" @click="openCreateModal">
            <template #icon><n-icon :component="AddOutline" /></template>
            新建部门
          </n-button>
        </n-space>
      </div>
    </div>

    <n-card>
      <n-data-table
        :data="filteredDepartments"
        :columns="columns"
        :row-key="(row: Department) => row.id"
        :loading="loading"
        :pagination="{ pageSize: 20, showSizePicker: true, pageSizes: [10, 20, 50], prefix: ({ itemCount }: any) => `共 ${itemCount} 条` }"
        size="medium"
      />
    </n-card>

    <!-- 部门编辑弹窗 -->
</div><!-- /.page-body -->
<n-modal
      v-model:show="deptModalVisible"
      preset="card"
      :title="editingDept ? '编辑部门' : '新建部门'"
      :style="{ width: '720px' }"
      :mask-closable="false"
    >
      <n-form :model="formState" label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="部门编号" required>
              <n-input
                v-model:value="formState.code"
                placeholder="请输入部门编号（唯一）"
                :disabled="!!editingDept"
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
                :disabled="!!editingDept && isDescendant(editingDept.id)"
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
          <n-button @click="closeDeptModal">取消</n-button>
          <n-button type="primary" class="gradient-btn" :loading="submitting" @click="handleDeptSubmit">保存部门</n-button>
        </div>
      </template>
    </n-modal>
</div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, h } from 'vue';
import {
  AddOutline,
  CreateOutline,
  TrashOutline,
  RefreshOutline,
  PersonOutline,
  SearchOutline,
} from '@vicons/ionicons5';
import {
  NTag,
  NButton,
  NSpace,
  NTooltip,
  NIcon,
  NPopconfirm,
  useMessage,
} from 'naive-ui';
import api from '../../api/auth';

import { extractApiError } from '../../api/dynamic-field'
const message = useMessage();

interface DeptUserRef {
  id: string;
  realName?: string;
  username?: string;
}

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
  status: string;
  sortOrder?: number;
  createdAt?: string;
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
const deptModalVisible = ref(false);
const editingDept = ref<Department | null>(null);
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
    const res = await api.get('/departments/');
    if (res.data?.success) {
      departments.value = res.data.data || [];
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

const isDescendant = (id: string) => {
  // 当前编辑部门的下属中是否包含 id
  if (!editingDept.value) return false;
  return isDescendantOrSelf(id, editingDept.value.id);
};

// 打开新建弹窗
const openCreateModal = () => {
  editingDept.value = null;
  Object.assign(formState, {
    code: '',
    name: '',
    parentId: undefined,
    managerId: undefined,
    manager2Id: undefined,
    manager3Id: undefined,
    hrbpId: undefined,
    sortOrder: 0,
    status: 'ACTIVE',
  });
  deptModalVisible.value = true;
};

// 打开编辑弹窗
const openEditModal = (record: Department) => {
  editingDept.value = record;
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
  deptModalVisible.value = true;
};

// 关闭弹窗
const closeDeptModal = () => {
  deptModalVisible.value = false;
  editingDept.value = null;
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
  if (!formState.name || !formState.code) {
    message.error('请填写部门名称和部门编号');
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

const columns = computed(() => [
  {
    title: '部门编号',
    key: 'code',
    width: 140,
  },
  {
    title: '部门ID',
    key: 'id',
    width: 220,
    render: (row: Department) =>
      h(NTooltip, null, {
        trigger: () => h('span', { style: 'font-family: monospace; color: #8c8c8c; font-size: 12px' }, row.id.slice(0, 8) + '…'),
        default: () => row.id,
      }),
  },
  {
    title: '部门名称',
    key: 'name',
    width: 180,
  },
  {
    title: '上级部门',
    key: 'parent',
    width: 180,
    render: (row: Department) => renderParent(row),
  },
  {
    title: '部门负责人',
    key: 'managerId',
    width: 130,
    render: (row: Department) => renderUser(row.managerId),
  },
  {
    title: '部门负责人 2',
    key: 'manager2Id',
    width: 130,
    render: (row: Department) => renderUser(row.manager2Id),
  },
  {
    title: '部门 HRBP',
    key: 'hrbpId',
    width: 130,
    render: (row: Department) => renderUser(row.hrbpId),
  },
  {
    title: '分管 VP',
    key: 'manager3Id',
    width: 130,
    render: (row: Department) => renderUser(row.manager3Id),
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row: Department) => {
      const map: Record<string, { type: any; label: string }> = {
        ACTIVE: { type: 'success', label: '启用' },
        INACTIVE: { type: 'default', label: '停用' },
      };
      const item = map[row.status] || { type: 'default', label: row.status };
      return h(NTag, { type: item.type, size: 'small' }, { default: () => item.label });
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 160,
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
              onClick: () => openEditModal(row),
            },
            {
              default: () => '编辑',
              icon: () => h(NIcon, { component: CreateOutline }),
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

onMounted(() => {
  loadDepartments();
  loadUsers();
});
</script>

<style scoped>
/* === 2026-08-24 page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
   - 标题区固定（flex-shrink: 0）→ 配置/操作按钮始终可触达
   - 内容区自己滚（flex: 1; min-height: 0; overflow-y: auto）→ 与外层 .settings-scroll 滚职责分离
   - 结构上让 sticky header 天然占据物理空间 → 解决下方内容穿透 header 的视觉 bug === */
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


/* .page-container 的 padding 由 SettingsLayout 统一注入,本页面不再写 */
/* 删除 scoped .page-header/.page-title 覆盖（规范：复用全局 glass.css） */

.page-header-actions {
  display: flex;
  gap: var(--space-2);
}
</style>
