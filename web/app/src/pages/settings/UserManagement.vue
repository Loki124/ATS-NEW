<template>
  <div class="page-container">
<div class="page-body">
    <div class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-subtitle">管理团队成员账号、角色与所属组织单元</p>
      </div>
      <div class="kpi-row">
        <div class="kpi-card"><span class="kpi-label">用户总数</span><span class="kpi-value">{{ users.length }}</span></div>
        <div class="kpi-card"><span class="kpi-label">角色数</span><span class="kpi-value">{{ roles.length }}</span></div>
      </div>
      <div class="page-header-actions">
        <n-button type="primary" @click="openCreateModal">
          <template #icon><n-icon :component="AddOutline" /></template>
          新建用户
        </n-button>
      </div>
    </div>

    <n-card>
      <n-data-table
        :data="users"
        :columns="columns"
        :row-key="(row: User) => row.id"
        :loading="loading"
        :pagination="{ pageSize: 10, showSizePicker: true, pageSizes: [10, 20, 50] }"
      />
    </n-card>

    <!-- 用户编辑弹窗 -->
    <n-modal
      v-model:show="userModalVisible"
      preset="card"
      :title="editingUser ? '编辑用户' : '新建用户'"
      :style="{ width: '600px' }"
      :mask-closable="false"
    >
      <n-form :model="formState" label-placement="top">
        <n-grid :cols="2" :x-gap="24">
          <n-grid-item>
            <n-form-item label="用户名" required>
              <n-input v-model:value="formState.username" placeholder="请输入用户名" :disabled="!!editingUser" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="真实姓名" required>
              <n-input v-model:value="formState.realName" placeholder="请输入真实姓名" />
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-grid :cols="2" :x-gap="24">
          <n-grid-item>
            <n-form-item label="邮箱">
              <n-input v-model:value="formState.email" placeholder="请输入邮箱" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="手机号">
              <n-input v-model:value="formState.phone" placeholder="请输入手机号" />
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-grid v-if="!editingUser" :cols="2" :x-gap="24">
          <n-grid-item>
            <n-form-item label="密码" required>
              <n-input
                v-model:value="formState.password"
                type="password"
                show-password-on="click"
                placeholder="请输入密码"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="角色类型">
              <n-select
                v-model:value="formState.roleType"
                :options="roleTypeOptions"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-grid :cols="2" :x-gap="24">
          <n-grid-item>
            <n-form-item label="状态">
              <n-select
                v-model:value="formState.status"
                :options="statusOptions"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="权限模式">
              <n-select
                v-model:value="formState.permissionMode"
                :options="permissionModeOptions"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>
      </n-form>

      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button @click="closeUserModal">取消</n-button>
          <n-button type="primary" class="gradient-btn" @click="handleUserSubmit">保存用户</n-button>
        </div>
      </template>
    </n-modal>

    <!-- MOU分配弹窗 -->
    <n-modal
      v-model:show="userMouModalVisible"
      preset="card"
      title="分配MOU"
      :style="{ width: '500px' }"
    >
      <p style="margin-bottom: 16px">请选择该用户所属的MOU（管理单元）：</p>
      <n-data-table
        :data="mous"
        :row-key="(row: Mou) => row.id"
        :pagination="{ pageSize: 10 }"
        :columns="mouColumns"
        :checked-row-keys="userMous"
        @update:checked-row-keys="handleSaveUserMous"
      />
    </n-modal>

    <!-- 角色分配弹窗 -->
    <n-modal
      v-model:show="userRoleModalVisible"
      preset="card"
      title="分配角色"
      :style="{ width: '500px' }"
    >
      <p style="margin-bottom: 16px">请选择该用户的角色：</p>
      <n-data-table
        :data="roles"
        :row-key="(row: Role) => row.id"
        :pagination="{ pageSize: 10 }"
        :columns="roleColumns"
        :checked-row-keys="userRoles"
        @update:checked-row-keys="handleSaveUserRoles"
      />
    </n-modal>
    </div><!-- /.page-body -->
</div>
</template>
<script setup lang="ts">
import api from '../../api/auth';
import { ref, reactive, onMounted, computed, h } from 'vue';
import { useUserStore } from '../../stores/user';
import {
  LockClosedOutline,
  AddOutline,
  CreateOutline,
  TrashOutline,
  LinkOutline,
  CloseOutline,
  ChatbubblesOutline,
} from '@vicons/ionicons5';
import {
  NTag,
  NButton,
  NSpace,
  NTooltip,
  NPopconfirm,
  NIcon,
  useMessage,
} from 'naive-ui';
import { extractApiError } from '../../api/dynamic-field';

const message = useMessage();

// 权限管理模式映射
const PERMISSION_MODE_MAP: Record<string, { type: any; label: string }> = {
  MOU: { type: 'info', label: 'MOU管理模式' },
  CONTAINER: { type: 'success', label: '容器管理模式' },
  MIXED: { type: 'warning', label: '混合模式' }
};

// 用户状态映射
const STATUS_MAP: Record<string, { type: any; label: string }> = {
  ACTIVE: { type: 'success', label: '正常' },
  INACTIVE: { type: 'default', label: '禁用' },
  LOCKED: { type: 'error', label: '锁定' }
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

// 下拉选项
const roleTypeOptions = [
  { label: 'HR', value: 'HR' },
  { label: 'Manager', value: 'MANAGER' },
  { label: 'Admin', value: 'ADMIN' },
];

const statusOptions = [
  { label: '正常', value: 'ACTIVE' },
  { label: '禁用', value: 'INACTIVE' },
  { label: '锁定', value: 'LOCKED' },
];

const permissionModeOptions = [
  { label: 'MOU管理模式', value: 'MOU' },
  { label: '容器管理模式', value: 'CONTAINER' },
  { label: '混合模式', value: 'MIXED' },
];

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
//   Fix 8 之前 token 存在 localStorage.getItem('token'), 现在统一到 useUserStore().accessToken,
//   老的 'token' key 已被清掉. 此处返回 store 里的 accessToken, 与项目其它处一致.
const getToken = () => useUserStore().accessToken;

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
    const data = await request('/api/v1/users/');
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
    const data = await request('/api/v1/permissions/mous/');
    if (data?.success) {
      mous.value = data.data;
    }
  } catch (error) {
    message.error(extractApiError(error, '加载MOU列表失败'));
  }
};

// 加载角色列表
const loadRoles = async () => {
  try {
    const data = await request('/api/v1/permissions/roles/');
    if (data?.success) {
      roles.value = data.data;
    }
  } catch (error) {
    message.error(extractApiError(error, '加载角色列表失败'));
  }
};

// 加载用户MOU关联
const loadUserMous = async (userId: string) => {
  try {
    const data = await request(`/api/v1/permissions/user-mous/${userId}/`);
    if (data?.success) {
      userMous.value = data.data.map((um: any) => um.mouId);
    }
  } catch (error) {
    message.error(extractApiError(error, '加载用户MOU失败'));
  }
};

// 加载用户角色
const loadUserRoles = async (userId: string) => {
  try {
    const data = await request(`/api/v1/permissions/users/${userId}/roles/`);
    if (data?.success) {
      userRoles.value = data.data.map((ur: any) => ur.roleId);
    }
  } catch (error) {
    message.error(extractApiError(error, '加载用户角色失败'));
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
    const data = await request('/api/v1/auth/users', {
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
    const data = await request(`/api/v1/users/${editingUser.value?.id}/`, {
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
    const data = await request(`/api/v1/users/${userId}/`, {
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
    const data = await request(`/api/v1/permissions/user-mous/${selectedUserId.value}/`, {
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
    const data = await request(`/api/v1/permissions/users/${selectedUserId.value}/roles/`, {
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
    const data = await request(`/api/v1/users/${userId}/`, {
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
    const data = await request(`/api/v1/users/${userId}/`, {
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
  { title: '用户名', key: 'username', width: 120 },
  { title: '姓名', key: 'realName', width: 100 },
  {
    title: '状态',
    key: 'status',
    width: 80,
    render: (row: User) => {
      const item = STATUS_MAP[row.status];
      return h(NTag, { type: item?.type || 'default', size: 'small' }, { default: () => item?.label || row.status });
    }
  },
  { title: '角色类型', key: 'roleType', width: 80 },
  {
    title: '权限模式',
    key: 'permissionMode',
    width: 120,
    render: (row: User) => {
      const item = PERMISSION_MODE_MAP[row.permissionMode];
      return h(NTag, { type: item?.type || 'default', size: 'small' }, { default: () => item?.label || row.permissionMode });
    }
  },
  {
    title: '企微绑定',
    key: 'wechatWork',
    width: 150,
    render: (row: User) => {
      if (row.wechatWorkUserId) {
        return h(NSpace, { size: 'small' }, {
          default: () => [
            h(NTooltip, null, {
              trigger: () => h(NTag, { type: 'success', size: 'small' }, {
                default: () => row.wechatWorkName || row.wechatWorkUserId!.slice(0, 8),
                icon: () => h(NIcon, { component: ChatbubblesOutline }),
              }),
              default: () => `ID: ${row.wechatWorkUserId}`,
            }),
            h(NButton, {
              text: true,
              size: 'small',
              onClick: () => handleUnbindWechatWork(row.id),
            }, { default: () => h(NIcon, { component: CloseOutline }) }),
          ],
        });
      }
      return h(NButton, {
        text: true,
        type: 'primary',
        size: 'small',
        onClick: () => {
          const input = prompt('请输入企微用户ID:');
          if (input) handleBindWechatWork(row.id, input);
        }
      }, {
        default: () => '绑定',
        icon: () => h(NIcon, { component: LinkOutline }),
      });
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render: (row: User) => {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, {
            text: true,
            type: 'primary',
            size: 'small',
            onClick: () => openMouModal(row.id)
          }, {
            default: () => 'MOU',
            icon: () => h(NIcon, { component: LockClosedOutline }),
          }),
          h(NButton, {
            text: true,
            type: 'primary',
            size: 'small',
            onClick: () => openRoleModal(row.id)
          }, {
            default: () => '角色',
            icon: () => h(NIcon, { component: LockClosedOutline }),
          }),
          h(NButton, {
            text: true,
            type: 'primary',
            size: 'small',
            onClick: () => {
              editingUser.value = row;
              Object.assign(formState, {
                username: row.username,
                realName: row.realName,
                email: row.email || '',
                phone: row.phone || '',
                password: '',
                roleType: row.roleType,
                status: row.status,
                permissionMode: row.permissionMode
              });
              userModalVisible.value = true;
            }
          }, { default: () => h(NIcon, { component: CreateOutline }) }),
          h(NPopconfirm, {
            onPositiveClick: () => handleDeleteUser(row.id),
            positiveText: '确认',
            negativeText: '取消',
          }, {
            default: () => '确认删除此用户？',
            trigger: () => h(NButton, {
              text: true,
              type: 'error',
              size: 'small',
            }, { default: () => h(NIcon, { component: TrashOutline }) }),
          }),
        ],
      });
    }
  }
]);

// MOU表格列
const mouColumns = [
  { type: 'selection' as const },
  { title: 'MOU名称', key: 'name' },
  { title: '编码', key: 'code' },
  {
    title: '类型',
    key: 'type',
    render: (row: Mou) => {
      const typeMap: Record<string, string> = {
        DEPT: '部门', PROJECT: '项目', TEAM: '团队', VIRTUAL: '虚拟'
      };
      return h(NTag, { size: 'small' }, { default: () => typeMap[row.type] || row.type });
    }
  }
];

// 角色表格列
const roleColumns = [
  { type: 'selection' as const },
  { title: '角色名称', key: 'name' },
  { title: '编码', key: 'code' },
  {
    title: '类型',
    key: 'roleType',
    render: (row: Role) => {
      return h(NTag, { type: row.roleType === 'SYSTEM' ? 'info' : 'success', size: 'small' }, {
        default: () => row.roleType === 'SYSTEM' ? '系统' : '业务'
      });
    }
  }
];

// 生命周期
onMounted(() => {
  loadUsers();
  loadMous();
  loadRoles();
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

</style>
