<template>
  <div class="page-container">
<div class="page-body">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ pageTitle }}</h1>
        <p class="page-subtitle">{{ pageSubtitle }}</p>
      </div>
      <div class="kpi-row">
        <div class="kpi-card"><span class="kpi-label">{{ totalLabel }}</span><span class="kpi-value">{{ filteredUsers.length }}</span></div>
        <div class="kpi-card"><span class="kpi-label">角色数</span><span class="kpi-value">{{ roles.length }}</span></div>
      </div>
      <div class="page-header-actions">
        <n-button type="primary" @click="openCreateModal">
          <template #icon><n-icon :component="AddOutline" /></template>
          新建用户
        </n-button>
      </div>
    </div>

    <n-tabs
      type="line"
      :value="mode"
      class="user-dir-tabs"
      @update:value="onTabChange"
    >
      <n-tab-pane name="internal" tab="内部员工" />
      <n-tab-pane name="external" tab="外部用户" />
      <n-tab-pane name="all" tab="全部用户" />
    </n-tabs>

    <n-card>
      <n-data-table
        :data="filteredUsers"
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
        </n-grid>
      </n-form>

      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button @click="closeUserModal">取消</n-button>
          <n-button type="primary" class="gradient-btn" @click="handleUserSubmit">保存用户</n-button>
        </div>
      </template>
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
import { ref, reactive, onMounted, computed, h } from 'vue';
import { useRoute } from 'vue-router';
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
  NTabs,
  NTabPane,
  useMessage,
} from 'naive-ui';
import { extractApiError } from '../../api/dynamic-field';

const message = useMessage();
const route = useRoute();

// ===== 模式：来自路由 meta.userDirectoryMode（'internal' | 'external' | 'all'）=====
// 2026-09-18：菜单将内部/外部/全部合并为单一「用户管理」入口（指向 users/all），
//   页内用 n-tabs 切换三种视图，故 mode 改为本地 ref，路由仅作初始值。
const routeMode = computed<string>(() => {
  const metaMode = (route.meta as Record<string, unknown>).userDirectoryMode;
  return metaMode === 'internal' || metaMode === 'external' || metaMode === 'all'
    ? (metaMode as string)
    : 'all';
});
const mode = ref<string>(routeMode.value);
// 直接通过路由进入（如深链 /settings/users/internal）时同步本地模式
watch(routeMode, (m) => { mode.value = m; });
// 页签切换（内部/外部/全部）：更新本地模式并重新拉取列表
const onTabChange = (v: string | number) => { mode.value = String(v); };

// 页面标题 / 副标题 / KPI 文案随模式变化（Beisen 风格差异化目录）
const pageTitle = computed(() =>
  mode.value === 'internal' ? '内部员工' : mode.value === 'external' ? '外部用户' : '全部用户'
);
const pageSubtitle = computed(() =>
  mode.value === 'internal'
    ? '管理企业内部员工账号、角色与组织信息'
    : mode.value === 'external'
      ? '管理外部协作用户账号与权限'
      : '管理全部用户账号、角色与状态'
);
const totalLabel = computed(() =>
  mode.value === 'internal' ? '内部员工总数' : mode.value === 'external' ? '外部用户总数' : '用户总数'
);

// 用户状态映射
const STATUS_MAP: Record<string, { type: any; label: string }> = {
  ACTIVE: { type: 'success', label: '正常' },
  INACTIVE: { type: 'default', label: '禁用' },
  LOCKED: { type: 'error', label: '锁定' }
};

// 用户类型映射（后端 userType: INTERNAL / EXTERNAL）
const USER_TYPE_MAP: Record<string, { type: any; label: string }> = {
  INTERNAL: { type: 'info', label: '内部' },
  EXTERNAL: { type: 'warning', label: '外部' }
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
  employeeId?: string;
  positionTitle?: string;
  userType?: string;
  wechatWorkUserId?: string;
  wechatWorkDeptId?: string;
  wechatWorkName?: string;
  createdAt: string;
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
const roles = ref<Role[]>([]);
const selectedUserId = ref<string>('');
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

// 表单状态
const formState = reactive({
  username: '',
  realName: '',
  email: '',
  phone: '',
  password: '',
  roleType: 'HR',
  status: 'ACTIVE',
});

// 获取token（统一走 useUserStore().accessToken）
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

// 服务端查询参数：internal/external 优先带 ?user_type= 过滤，all 不带
const userTypeParam = computed(() => {
  if (mode.value === 'internal') return '?user_type=INTERNAL';
  if (mode.value === 'external') return '?user_type=EXTERNAL';
  return '';
});

// 加载用户列表（服务端尽量按 user_type 过滤；客户端再兜底一次）
const loadUsers = async () => {
  loading.value = true;
  try {
    const data = await request(`/api/v1/users/${userTypeParam.value}`);
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

// 页签切换（internal/external/all）时重新拉取对应用户列表
watch(mode, () => { loadUsers(); });

// 客户端兜底过滤：保证 internal/external 正确分离（与后端是否就绪无关）
const filteredUsers = computed<User[]>(() => {
  if (mode.value === 'all') return users.value;
  const expected = mode.value === 'internal' ? 'INTERNAL' : 'EXTERNAL';
  // 仅当返回数据确实携带 userType 字段时才做客户端过滤，
  // 否则（后端尚未返回 userType）不做过滤，保证页面可用而不是空白。
  const hasUserType = users.value.some((u) => !!u.userType);
  if (!hasUserType) return users.value;
  return users.value.filter((u) => u.userType === expected);
});

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
    status: 'ACTIVE'
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
    status: 'ACTIVE'
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

// 打开角色分配弹窗
const openRoleModal = async (userId: string) => {
  selectedUserId.value = userId;
  await loadUserRoles(userId);
  userRoleModalVisible.value = true;
};

// ===== 列定义（按模式差异化）=====
const statusColumn = {
  title: '状态',
  key: 'status',
  width: 80,
  render: (row: User) => {
    const item = STATUS_MAP[row.status];
    return h(NTag, { type: item?.type || 'default', size: 'small' }, { default: () => item?.label || row.status });
  }
};

const userTypeColumn = {
  title: '类型',
  key: 'userType',
  width: 80,
  render: (row: User) => {
    const item = USER_TYPE_MAP[row.userType || ''];
    return h(NTag, { type: item?.type || 'default', size: 'small' }, {
      default: () => item?.label || (row.userType || '未知')
    });
  }
};

const wechatColumn = {
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
};

const actionsColumn = {
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
              status: row.status
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
};

// 表格列配置（按模式差异化构建）
const columns = computed(() => {
  const cols: any[] = [];
  if (mode.value === 'internal') {
    // 内部员工：工号 / 姓名 / 职务 / 状态 / 角色 / 操作
    // employeeId / positionTitle 由 UserSerializer 始终返回（空值为 null），属内部员工固有属性，内部模式常显
    cols.push({ title: '工号', key: 'employeeId', width: 120 });
    cols.push({ title: '姓名', key: 'realName', width: 100 });
    cols.push({ title: '职务', key: 'positionTitle', width: 120 });
    cols.push(statusColumn, { title: '角色', key: 'roleType', width: 90 }, actionsColumn);
  } else if (mode.value === 'external') {
    // 外部用户：姓名 / 状态 / 角色 / 类型 / 操作
    cols.push(
      { title: '姓名', key: 'realName', width: 100 },
      statusColumn,
      { title: '角色', key: 'roleType', width: 90 },
      userTypeColumn,
      actionsColumn
    );
  } else {
    // 全部用户：现有列 + 类型列
    cols.push(
      { title: '用户名', key: 'username', width: 120 },
      { title: '姓名', key: 'realName', width: 100 },
      statusColumn,
      { title: '角色类型', key: 'roleType', width: 90 },
      userTypeColumn,
      wechatColumn,
      actionsColumn
    );
  }
  return cols;
});

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
  loadRoles();
});
</script>


<style scoped>

/* === page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
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
