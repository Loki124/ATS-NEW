<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">部门管理</h1>
      <div class="page-header-actions">
        <a-space>
          <a-input-search
            v-model:value="searchKeyword"
            placeholder="搜索部门名称/编号"
            style="width: 240px"
            @search="loadDepartments"
            allow-clear
          />
          <a-button @click="loadDepartments">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
          <a-button type="primary" @click="openCreateModal">
            <template #icon><PlusOutlined /></template>
            新建部门
          </a-button>
        </a-space>
      </div>
    </div>

    <a-card>
      <a-table
        :dataSource="filteredDepartments"
        :columns="columns"
        rowKey="id"
        :loading="loading"
        :pagination="{ pageSize: 20, showSizeChanger: true, showTotal: (total: number) => `共 ${total} 条` }"
        :expand-row-by-click="false"
        :default-expand-all-rows="false"
        size="middle"
      />
    </a-card>

    <!-- 部门编辑弹窗 -->
    <a-modal
      :title="editingDept ? '编辑部门' : '新建部门'"
      :open="deptModalVisible"
      @cancel="closeDeptModal"
      @ok="handleDeptSubmit"
      :width="720"
      :confirm-loading="submitting"
    >
      <a-form layout="vertical" :model="formState">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="部门编号" required>
              <a-input
                v-model:value="formState.code"
                placeholder="请输入部门编号（唯一）"
                :disabled="!!editingDept"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="部门名称" required>
              <a-input v-model:value="formState.name" placeholder="请输入部门名称" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="上级部门">
              <a-tree-select
                v-model:value="formState.parentId"
                :tree-data="parentTreeData"
                placeholder="不选则为顶级部门"
                allow-clear
                tree-default-expand-all
                :disabled="!!editingDept && isDescendant(editingDept.id)"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="排序值">
              <a-input-number
                v-model:value="formState.sortOrder"
                :min="0"
                :max="9999"
                style="width: 100%"
                placeholder="数字越小越靠前"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider orientation="left" plain>人员配置</a-divider>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="部门负责人">
              <a-select
                v-model:value="formState.managerId"
                placeholder="请选择部门负责人"
                allow-clear
                show-search
                :filter-option="filterUserOption"
                :options="userOptions"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="部门负责人 2">
              <a-select
                v-model:value="formState.manager2Id"
                placeholder="请选择部门负责人2"
                allow-clear
                show-search
                :filter-option="filterUserOption"
                :options="userOptions"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="部门 HRBP">
              <a-select
                v-model:value="formState.hrbpId"
                placeholder="请选择部门HRBP"
                allow-clear
                show-search
                :filter-option="filterUserOption"
                :options="userOptions"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="分管 VP">
              <a-select
                v-model:value="formState.manager3Id"
                placeholder="请选择分管VP"
                allow-clear
                show-search
                :filter-option="filterUserOption"
                :options="userOptions"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="状态">
              <a-radio-group v-model:value="formState.status">
                <a-radio value="ACTIVE">启用</a-radio>
                <a-radio value="INACTIVE">停用</a-radio>
              </a-radio-group>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, h } from 'vue';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  UserOutlined,
} from '@ant-design/icons-vue';
import {
  Tag as ATag,
  Button as AButton,
  Space as ASpace,
  Modal as AModal,
  Input as AInput,
  InputNumber as AInputNumber,
  InputSearch as AInputSearch,
  Select as ASelect,
  Card as ACard,
  Row as ARow,
  Col as ACol,
  Form as AForm,
  FormItem as AFormItem,
  TreeSelect as ATreeSelect,
  Divider as ADivider,
  Radio as ARadio,
  RadioGroup as ARadioGroup,
  Popconfirm as APopconfirm,
  message,
  Tooltip as ATooltip,
} from 'ant-design-vue';
import api from '../../api/auth';

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
  manager?: DeptUserRef | null;
  manager2?: DeptUserRef | null;
  manager3?: DeptUserRef | null;
  hrbp?: DeptUserRef | null;
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
    const res = await api.get('/departments');
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
    const res = await api.get('/users');
    if (res.data?.success) {
      users.value = (res.data.data || []).filter((u: User) => u.status === 'ACTIVE');
    }
  } catch (error) {
    console.error('加载用户列表失败', error);
  }
};

// 用户下拉项
const userOptions = computed(() =>
  users.value.map(u => ({
    label: `${u.realName}（${u.username}）`,
    value: u.id,
  }))
);

// 过滤用户选项
const filterUserOption = (input: string, option: any) => {
  const text = String(option.label || '').toLowerCase();
  return text.includes(input.toLowerCase());
};

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
      title: `${d.name} (${d.code})`,
      value: d.id,
      key: d.id,
      disabled: editingDept.value ? isDescendantOrSelf(d.id, editingDept.value.id) : false,
      children: buildTree(d.id),
    }));
  };
  return [
    {
      title: '顶级部门',
      value: '__ROOT__',
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
      const res = await api.put(`/departments/${editingDept.value.id}`, payload);
      if (res.data?.success) {
        message.success('部门更新成功');
        closeDeptModal();
        loadDepartments();
      } else {
        message.error(res.data?.error || res.data?.message || '更新失败');
      }
    } else {
      const res = await api.post('/departments', payload);
      if (res.data?.success) {
        message.success('部门创建成功');
        closeDeptModal();
        loadDepartments();
      } else {
        message.error(res.data?.error || res.data?.message || '创建失败');
      }
    }
  } catch (error: any) {
    message.error(error.response?.data?.error || error.response?.data?.message || '操作失败');
  } finally {
    submitting.value = false;
  }
};

// 删除
const handleDelete = async (record: Department) => {
  try {
    const res = await api.delete(`/departments/${record.id}`);
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

const renderUser = (user?: DeptUserRef | null) => {
  if (!user) return h('span', { style: 'color: #bfbfbf' }, '—');
  return h(ATag, { color: 'blue' }, () => [h(UserOutlined), ' ', user.realName || user.username]);
};

const renderParent = (record: Department) => {
  if (!record.parentId) {
    return h(ATag, { color: 'purple' }, () => '顶级');
  }
  const parent = departments.value.find(d => d.id === record.parentId);
  if (!parent) return h('span', { style: 'color: #bfbfbf' }, '—');
  return h('span', {}, `${parent.name} (${parent.code})`);
};

const columns = computed(() => [
  {
    title: '部门编号',
    dataIndex: 'code',
    key: 'code',
    width: 140,
  },
  {
    title: '部门ID',
    dataIndex: 'id',
    key: 'id',
    width: 220,
    customRender: ({ text }: { text: string }) =>
      h(ATooltip, { title: text }, () =>
        h('span', { style: 'font-family: monospace; color: #8c8c8c; font-size: 12px' }, text.slice(0, 8) + '…')
      ),
  },
  {
    title: '部门名称',
    dataIndex: 'name',
    key: 'name',
    width: 180,
  },
  {
    title: '上级部门',
    key: 'parent',
    width: 180,
    customRender: ({ record }: { record: Department }) => renderParent(record),
  },
  {
    title: '部门负责人',
    key: 'manager',
    width: 130,
    customRender: ({ record }: { record: Department }) => renderUser(record.manager),
  },
  {
    title: '部门负责人 2',
    key: 'manager2',
    width: 130,
    customRender: ({ record }: { record: Department }) => renderUser(record.manager2),
  },
  {
    title: '部门 HRBP',
    key: 'hrbp',
    width: 130,
    customRender: ({ record }: { record: Department }) => renderUser(record.hrbp),
  },
  {
    title: '分管 VP',
    key: 'manager3',
    width: 130,
    customRender: ({ record }: { record: Department }) => renderUser(record.manager3),
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    width: 90,
    customRender: ({ text }: { text: string }) => {
      const map: Record<string, { color: string; label: string }> = {
        ACTIVE: { color: 'success', label: '启用' },
        INACTIVE: { color: 'default', label: '停用' },
      };
      const item = map[text] || { color: 'default', label: text };
      return h(ATag, { color: item.color }, () => item.label);
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    fixed: 'right' as const,
    customRender: ({ record }: { record: Department }) =>
      h(ASpace, { size: 'small' }, () => [
        h(
          AButton,
          {
            type: 'link',
            size: 'small',
            onClick: () => openEditModal(record),
          },
          () => [h(EditOutlined), ' 编辑']
        ),
        h(
          APopconfirm,
          {
            title: '确认删除此部门？',
            okText: '确认',
            cancelText: '取消',
            onConfirm: () => handleDelete(record),
          },
          () =>
            h(
              AButton,
              { type: 'link', size: 'small', danger: true },
              () => [h(DeleteOutlined), ' 删除']
            )
        ),
      ]),
  },
]);

onMounted(() => {
  loadDepartments();
  loadUsers();
});
</script>

<style scoped>
.page-container {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.page-header-actions {
  display: flex;
  gap: 8px;
}
</style>
