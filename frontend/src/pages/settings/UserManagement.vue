<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">用户管理</h1>
      <div class="page-header-actions">
        <a-button type="primary" @click="openCreateModal">
          <template #icon><PlusOutlined /></template>
          新建用户
        </a-button>
      </div>
    </div>

    <a-card>
      <a-table
        :dataSource="users"
        :columns="columns"
        rowKey="id"
        :loading="loading"
        :pagination="{ pageSize: 10, showSizeChanger: true }"
      />
    </a-card>

    <!-- 用户编辑弹窗 -->
    <a-modal
      :title="editingUser ? '编辑用户' : '新建用户'"
      :open="userModalVisible"
      @cancel="closeUserModal"
      @ok="handleUserSubmit"
      :width="600"
    >
      <a-form :form="form" layout="vertical">
        <a-row :gutter="24">
          <a-col :span="12">
            <a-form-item label="用户名" name="username" :rules="[{ required: true, message: '请输入用户名' }]">
              <a-input v-model:value="formState.username" placeholder="请输入用户名" :disabled="!!editingUser" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="真实姓名" name="realName" :rules="[{ required: true, message: '请输入真实姓名' }]">
              <a-input v-model:value="formState.realName" placeholder="请输入真实姓名" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="24">
          <a-col :span="12">
            <a-form-item label="邮箱" name="email">
              <a-input v-model:value="formState.email" placeholder="请输入邮箱" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="手机号" name="phone">
              <a-input v-model:value="formState.phone" placeholder="请输入手机号" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row v-if="!editingUser" :gutter="24">
          <a-col :span="12">
            <a-form-item label="密码" name="password" :rules="[{ required: true, message: '请输入密码' }]">
              <a-input-password v-model:value="formState.password" placeholder="请输入密码" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="角色类型" name="roleType" initialValue="HR">
              <a-select v-model:value="formState.roleType">
                <a-select-option value="HR">HR</a-select-option>
                <a-select-option value="MANAGER">Manager</a-select-option>
                <a-select-option value="ADMIN">Admin</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="24">
          <a-col :span="12">
            <a-form-item label="状态" name="status">
              <a-select v-model:value="formState.status">
                <a-select-option value="ACTIVE">正常</a-select-option>
                <a-select-option value="INACTIVE">禁用</a-select-option>
                <a-select-option value="LOCKED">锁定</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="权限模式" name="permissionMode">
              <a-select v-model:value="formState.permissionMode">
                <a-select-option value="MOU">MOU管理模式</a-select-option>
                <a-select-option value="CONTAINER">容器管理模式</a-select-option>
                <a-select-option value="MIXED">混合模式</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>

    <!-- MOU分配弹窗 -->
    <a-modal
      title="分配MOU"
      :open="userMouModalVisible"
      @cancel="() => userMouModalVisible = false"
      :footer="null"
      :width="500"
    >
      <p style="margin-bottom: 16px">请选择该用户所属的MOU（管理单元）：</p>
      <a-table
        :dataSource="mous"
        rowKey="id"
        :pagination="{ pageSize: 10 }"
        :columns="mouColumns"
        :rowSelection="{
          type: 'checkbox',
          selectedRowKeys: userMous,
          onChange: (selectedRowKeys: string[]) => handleSaveUserMous(selectedRowKeys)
        }"
      />
    </a-modal>

    <!-- 角色分配弹窗 -->
    <a-modal
      title="分配角色"
      :open="userRoleModalVisible"
      @cancel="() => userRoleModalVisible = false"
      :footer="null"
      :width="500"
    >
      <p style="margin-bottom: 16px">请选择该用户的角色：</p>
      <a-table
        :dataSource="roles"
        rowKey="id"
        :pagination="{ pageSize: 10 }"
        :columns="roleColumns"
        :rowSelection="{
          type: 'checkbox',
          selectedRowKeys: userRoles,
          onChange: (selectedRowKeys: string[]) => handleSaveUserRoles(selectedRowKeys)
        }"
      />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import api from '../../api/auth';
import { ref, reactive, onMounted, computed, h } from 'vue';
import {
  UserOutlined,
  WechatOutlined,
  CoffeeOutlined,
  LockOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  LinkOutlined,
  DisconnectOutlined
} from '@ant-design/icons-vue';
import {
  Table as ATable,
  Tag as ATag,
  Button as AButton,
  Space as ASpace,
  Modal as AModal,
  Form as AForm,
  Input as AInput,
  Select as ASelect,
  Card as ACard,
  Row as ARow,
  Col as ACol,
  Tooltip as ATooltip,
  Popconfirm as APopconfirm,
  message,
  SelectOption as ASelectOption
} from 'ant-design-vue';

// 权限管理模式映射
const PERMISSION_MODE_MAP: Record<string, { color: string; label: string }> = {
  MOU: { color: 'blue', label: 'MOU管理模式' },
  CONTAINER: { color: 'green', label: '容器管理模式' },
  MIXED: { color: 'purple', label: '混合模式' }
};

// 用户状态映射
const STATUS_MAP: Record<string, { color: string; label: string }> = {
  ACTIVE: { color: 'success', label: '正常' },
  INACTIVE: { color: 'default', label: '禁用' },
  LOCKED: { color: 'error', label: '锁定' }
};

interface User {
  id: string;
  username: string;
  realName: string;
  email?: string;
  phone?: string;
  status: string;
  roleType: string;
  departmentId?: string;
  wechatWorkUserId?: string;
  wechatWorkDeptId?: string;
  wechatWorkName?: string;
  mochaUserId?: string;
  mochaDeptId?: string;
  mochaName?: string;
  permissionMode: string;
  createdAt: string;
}

interface Mou {
  id: string;
  name: string;
  code: string;
  type: string;
  description?: string;
}

interface Role {
  id: string;
  name: string;
  code: string;
  roleType?: string;
}

// 状态
const users = ref<User[]>([]);
const loading = ref(false);
const userModalVisible = ref(false);
const editingUser = ref<User | null>(null);
const mous = ref<Mou[]>([]);
const mouModalVisible = ref(false);
const roles = ref<Role[]>([]);
const userMouModalVisible = ref(false);
const selectedUserId = ref<string>('');
const userMous = ref<string[]>([]);
const userRoleModalVisible = ref(false);
const userRoles = ref<string[]>([]);

// 表单状态
const formState = reactive({
  username: '',
  realName: '',
  email: '',
  phone: '',
  password: '',
  roleType: 'HR',
  status: 'ACTIVE',
  permissionMode: 'MOU'
});

// 获取token
const getToken = () => localStorage.getItem('token');

// API请求封装
const request = async (url: string, options: RequestInit = {}) => {
  const token = getToken();
  if (!token) {
    message.error('请先登录');
    return null;
  }
  const response = await fetch(url, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers
    }
  });
  return response.json();
};

// 加载用户列表
const loadUsers = async () => {
  loading.value = true;
  try {
    const data = await request('/api/users');
    if (data?.success) {
      users.value = data.data;
    } else {
      message.error(data?.message || '加载用户列表失败');
    }
  } catch (error) {
    console.error('加载用户列表失败', error);
    message.error('网络错误，请检查后端服务');
  } finally {
    loading.value = false;
  }
};

// 加载MOU列表
const loadMous = async () => {
  try {
    const data = await request('/api/permissions-v2/mou');
    if (data?.success) {
      mous.value = data.data;
    }
  } catch (error) {
    console.error('加载MOU列表失败', error);
  }
};

// 加载角色列表
const loadRoles = async () => {
  try {
    const data = await request('/api/permissions/roles');
    if (data?.success) {
      roles.value = data.data;
    }
  } catch (error) {
    console.error('加载角色列表失败', error);
  }
};

// 加载用户MOU关联
const loadUserMous = async (userId: string) => {
  try {
    const data = await request(`/api/permissions-v2/mou/user-mous/${userId}`);
    if (data?.success) {
      userMous.value = data.data.map((um: any) => um.mouId);
    }
  } catch (error) {
    console.error('加载用户MOU失败', error);
  }
};

// 加载用户角色
const loadUserRoles = async (userId: string) => {
  try {
    const data = await request(`/api/permissions/users/${userId}/roles`);
    if (data?.success) {
      userRoles.value = data.data.map((ur: any) => ur.roleId);
    }
  } catch (error) {
    console.error('加载用户角色失败', error);
  }
};

// 打开新建用户弹窗
const openCreateModal = () => {
  editingUser.value = null;
  Object.assign(formState, {
    username: '',
    realName: '',
    email: '',
    phone: '',
    password: '',
    roleType: 'HR',
    status: 'ACTIVE',
    permissionMode: 'MOU'
  });
  userModalVisible.value = true;
};

// 关闭用户弹窗
const closeUserModal = () => {
  userModalVisible.value = false;
  editingUser.value = null;
  Object.assign(formState, {
    username: '',
    realName: '',
    email: '',
    phone: '',
    password: '',
    roleType: 'HR',
    status: 'ACTIVE',
    permissionMode: 'MOU'
  });
};

// 创建用户
const handleCreateUser = async () => {
  try {
    const data = await request('/api/users', {
      method: 'POST',
      body: JSON.stringify(formState)
    });
    if (data?.success) {
      message.success('用户创建成功');
      closeUserModal();
      loadUsers();
    } else {
      message.error(data?.error || '创建失败');
    }
  } catch (error) {
    message.error('创建失败');
  }
};

// 更新用户
const handleUpdateUser = async () => {
  try {
    const data = await request(`/api/users/${editingUser.value?.id}`, {
      method: 'PUT',
      body: JSON.stringify(formState)
    });
    if (data?.success) {
      message.success('用户更新成功');
      closeUserModal();
      loadUsers();
    } else {
      message.error(data?.error || '更新失败');
    }
  } catch (error) {
    message.error('更新失败');
  }
};

// 提交用户表单
const handleUserSubmit = () => {
  if (editingUser.value) {
    handleUpdateUser();
  } else {
    handleCreateUser();
  }
};

// 删除用户
const handleDeleteUser = async (userId: string) => {
  try {
    const data = await request(`/api/users/${userId}`, {
      method: 'DELETE'
    });
    if (data?.success) {
      message.success('用户删除成功');
      loadUsers();
    } else {
      message.error(data?.error || '删除失败');
    }
  } catch (error) {
    message.error('删除失败');
  }
};

// 保存用户MOU关联
const handleSaveUserMous = async (mouIds: string[]) => {
  try {
    const data = await request(`/api/permissions-v2/mou/user-mous/${selectedUserId.value}`, {
      method: 'POST',
      body: JSON.stringify({ mouIds })
    });
    if (data?.success) {
      message.success('MOU分配成功');
      userMouModalVisible.value = false;
    } else {
      message.error(data?.error || '分配失败');
    }
  } catch (error) {
    message.error('分配失败');
  }
};

// 保存用户角色
const handleSaveUserRoles = async (roleIds: string[]) => {
  try {
    const data = await request(`/api/permissions/users/${selectedUserId.value}/roles`, {
      method: 'POST',
      body: JSON.stringify({ roleIds })
    });
    if (data?.success) {
      message.success('角色分配成功');
      userRoleModalVisible.value = false;
    } else {
      message.error(data?.error || '分配失败');
    }
  } catch (error) {
    message.error('分配失败');
  }
};

// 绑定企微
const handleBindWechatWork = async (userId: string, wechatWorkUserId: string) => {
  try {
    const data = await request(`/api/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify({ wechatWorkUserId })
    });
    if (data?.success) {
      message.success('企微绑定成功');
      loadUsers();
    } else {
      message.error(data?.error || '绑定失败');
    }
  } catch (error) {
    message.error('绑定失败');
  }
};

// 解绑企微
const handleUnbindWechatWork = async (userId: string) => {
  try {
    const data = await request(`/api/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify({ wechatWorkUserId: null })
    });
    if (data?.success) {
      message.success('企微解绑成功');
      loadUsers();
    } else {
      message.error(data?.error || '解绑失败');
    }
  } catch (error) {
    message.error('解绑失败');
  }
};

// 绑定摩卡
const handleBindMocha = async (userId: string, mochaUserId: string) => {
  try {
    const data = await request(`/api/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify({ mochaUserId })
    });
    if (data?.success) {
      message.success('摩卡绑定成功');
      loadUsers();
    } else {
      message.error(data?.error || '绑定失败');
    }
  } catch (error) {
    message.error('绑定失败');
  }
};

// 解绑摩卡
const handleUnbindMocha = async (userId: string) => {
  try {
    const data = await request(`/api/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify({ mochaUserId: null })
    });
    if (data?.success) {
      message.success('摩卡解绑成功');
      loadUsers();
    } else {
      message.error(data?.error || '解绑失败');
    }
  } catch (error) {
    message.error('解绑失败');
  }
};

// 打开MOU分配弹窗
const openMouModal = async (userId: string) => {
  selectedUserId.value = userId;
  await loadUserMous(userId);
  userMouModalVisible.value = true;
};

// 打开角色分配弹窗
const openRoleModal = async (userId: string) => {
  selectedUserId.value = userId;
  await loadUserRoles(userId);
  userRoleModalVisible.value = true;
};

// 表格列配置
const columns = computed(() => [
  { title: '用户名', dataIndex: 'username', key: 'username', width: 120 },
  { title: '姓名', dataIndex: 'realName', key: 'realName', width: 100 },
  { 
    title: '状态', 
    dataIndex: 'status', 
    key: 'status',
    width: 80,
    customRender: ({ text }: { text: string }) => {
      return h(ATag, { color: STATUS_MAP[text]?.color }, () => STATUS_MAP[text]?.label || text);
    }
  },
  { title: '角色类型', dataIndex: 'roleType', key: 'roleType', width: 80 },
  { 
    title: '权限模式', 
    dataIndex: 'permissionMode', 
    key: 'permissionMode',
    width: 120,
    customRender: ({ text }: { text: string }) => {
      return h(ATag, { color: PERMISSION_MODE_MAP[text]?.color }, () => PERMISSION_MODE_MAP[text]?.label || text);
    }
  },
  { 
    title: '企微绑定', 
    key: 'wechatWork',
    width: 150,
    customRender: ({ record }: { record: User }) => {
      return h(ASpace, { size: 'small' }, () => {
        if (record.wechatWorkUserId) {
          return [
            h(ATooltip, { title: `ID: ${record.wechatWorkUserId}` }, () =>
              h(ATag, { color: 'green' }, () => [
                h(WechatOutlined),
                ' ',
                record.wechatWorkName || record.wechatWorkUserId.slice(0, 8)
              ])
            ),
            h(AButton, {
              type: 'text',
              size: 'small',
              onClick: () => handleUnbindWechatWork(record.id)
            }, () => h(DisconnectOutlined))
          ];
        } else {
          return h(AButton, {
            type: 'link',
            size: 'small',
            onClick: () => {
              const input = prompt('请输入企微用户ID:');
              if (input) handleBindWechatWork(record.id, input);
            }
          }, () => [
            h(LinkOutlined),
            ' 绑定'
          ]);
        }
      });
    }
  },
  { 
    title: '摩卡绑定', 
    key: 'mocha',
    width: 150,
    customRender: ({ record }: { record: User }) => {
      return h(ASpace, { size: 'small' }, () => {
        if (record.mochaUserId) {
          return [
            h(ATooltip, { title: `ID: ${record.mochaUserId}` }, () =>
              h(ATag, { color: 'blue' }, () => [
                h(CoffeeOutlined),
                ' ',
                record.mochaName || record.mochaUserId.slice(0, 8)
              ])
            ),
            h(AButton, {
              type: 'text',
              size: 'small',
              onClick: () => handleUnbindMocha(record.id)
            }, () => h(DisconnectOutlined))
          ];
        } else {
          return h(AButton, {
            type: 'link',
            size: 'small',
            onClick: () => {
              const input = prompt('请输入摩卡用户ID:');
              if (input) handleBindMocha(record.id, input);
            }
          }, () => [
            h(LinkOutlined),
            ' 绑定'
          ]);
        }
      });
    }
  },
  { 
    title: '操作', 
    key: 'actions',
    width: 200,
    customRender: ({ record }: { record: User }) => {
      return h(ASpace, { size: 'small' }, () => [
        h(AButton, {
          type: 'link',
          size: 'small',
          onClick: () => openMouModal(record.id)
        }, () => [h(LockOutlined), ' MOU']),
        h(AButton, {
          type: 'link',
          size: 'small',
          onClick: () => openRoleModal(record.id)
        }, () => [h(LockOutlined), ' 角色']),
        h(AButton, {
          type: 'link',
          size: 'small',
          onClick: () => {
            editingUser.value = record;
            Object.assign(formState, {
              username: record.username,
              realName: record.realName,
              email: record.email || '',
              phone: record.phone || '',
              password: '',
              roleType: record.roleType,
              status: record.status,
              permissionMode: record.permissionMode
            });
            userModalVisible.value = true;
          }
        }, () => h(EditOutlined)),
        h(APopconfirm, {
          title: '确认删除此用户？',
          okText: '确认',
          cancelText: '取消',
          onConfirm: () => handleDeleteUser(record.id)
        }, () => h(AButton, {
          type: 'link',
          size: 'small',
          danger: true
        }, () => h(DeleteOutlined)))
      ]);
    }
  }
]);

// MOU表格列
const mouColumns = [
  { title: 'MOU名称', dataIndex: 'name', key: 'name' },
  { title: '编码', dataIndex: 'code', key: 'code' },
  { 
    title: '类型', 
    dataIndex: 'type', 
    key: 'type',
    customRender: ({ text }: { text: string }) => {
      const typeMap: Record<string, string> = {
        DEPT: '部门', PROJECT: '项目', TEAM: '团队', VIRTUAL: '虚拟'
      };
      return h(ATag, {}, () => typeMap[text] || text);
    }
  }
];

// 角色表格列
const roleColumns = [
  { title: '角色名称', dataIndex: 'name', key: 'name' },
  { title: '编码', dataIndex: 'code', key: 'code' },
  { 
    title: '类型', 
    dataIndex: 'roleType', 
    key: 'roleType',
    customRender: ({ text }: { text: string }) => {
      return h(ATag, { color: text === 'SYSTEM' ? 'blue' : 'green' }, () =>
        text === 'SYSTEM' ? '系统' : '业务'
      );
    }
  }
];

// 生命周期
onMounted(() => {
  loadUsers();
  loadMous();
  loadRoles();
});

// Form实例 (用于兼容 ant-design-vue 表单验证)
const form = {
  validateFields: async () => {
    return true;
  }
};
</script>
