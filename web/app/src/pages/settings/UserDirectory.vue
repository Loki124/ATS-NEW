<template>
  <div class="page-container">
<div class="page-body">
    <div class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-subtitle">管理全部用户账号、角色与状态（内部员工 / 外部用户以「用户类型」区分）</p>
      </div>
    </div>

    <!-- 搜索 + 筛选行：对齐校招管控规则配置工具条（搜索框 + 筛选项 + spacer 推右按钮） -->
    <div class="toolbar">
      <n-input
        v-model:value="searchText"
        placeholder="搜索用户名 / 姓名"
        clearable
        class="rule-filter-search"
        @keyup.enter="() => {}"
      >
        <template #prefix><n-icon :component="SearchOutline" /></template>
      </n-input>
      <n-select
        v-model:value="filterUserType"
        :options="userTypeFilterOptions"
        placeholder="用户类型"
        clearable
        class="rule-filter-select"
      />
      <n-select
        v-model:value="filterStatus"
        :options="statusOptions"
        placeholder="状态"
        clearable
        class="rule-filter-select"
      />
      <div class="spacer"></div>
      <n-button type="primary" @click="openCreateModal">
        <template #icon><n-icon :component="AddOutline" /></template>
        新建用户
      </n-button>
    </div>

    <div class="table-wrap">
      <n-data-table
        :data="displayUsers"
        :columns="columns"
        :row-key="(row: User) => row.id"
        :loading="loading"
        :pagination="pagination"
        flex-height
      >
        <template #empty><n-empty description="暂无用户" /></template>
      </n-data-table>
    </div>

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
            <n-form-item label="用户类型">
              <n-select
                v-model:value="formState.userType"
                :options="userTypeOptions"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-grid v-if="!editingUser" :cols="2" :x-gap="24">
          <n-grid-item>
            <n-form-item label="角色类型">
              <n-select
                v-model:value="formState.roleType"
                :options="roleTypeOptions"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="状态">
              <n-select
                v-model:value="formState.status"
                :options="statusOptions"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-grid v-else :cols="2" :x-gap="24">
          <n-grid-item>
            <n-form-item label="用户类型">
              <n-select
                v-model:value="formState.userType"
                :options="userTypeOptions"
              />
            </n-form-item>
          </n-grid-item>
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
import { ref, reactive, onMounted, computed, h, watch } from 'vue';
import {
  LockClosedOutline,
  AddOutline,
  CreateOutline,
  TrashOutline,
  LinkOutline,
  CloseOutline,
  ChatbubblesOutline,
  SearchOutline,
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
import { useUserStore } from '../../stores/user';

const message = useMessage();

// 2026-09-19 整合重构：内部员工 / 外部用户 / 全部用户 合并为单一「用户管理」页。
//   - 去掉页内 n-tabs 与 KPI 卡片，默认展示全部用户（后端 user_type 字段区分内外）
//   - 新增搜索框 + 用户类型 / 状态 筛选项，筛选行最右侧放「新建用户」按钮
//   - 表单新增「用户类型」字段（INTERNAL / EXTERNAL），落库到 user_type
//   - 列表保留并独立化为 pagination 分页器

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

// 搜索 / 筛选
const searchText = ref('');
const filterUserType = ref<string | null>(null);
const filterStatus = ref<string | null>(null);

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

const userTypeOptions = [
  { label: '内部员工', value: 'INTERNAL' },
  { label: '外部用户', value: 'EXTERNAL' },
];

const userTypeFilterOptions = [
  { label: '全部类型', value: null as string | null },
  { label: '内部员工', value: 'INTERNAL' },
  { label: '外部用户', value: 'EXTERNAL' },
];

// 分页器（客户端分页：displayUsers 已是筛选后结果）
// 对齐校招管控规则配置：pageSize 20 + 快速跳页 + 「共 N 条」前缀
const pagination = reactive({
  page: 1,
  pageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
  showQuickJumper: true,
  prefix: ({ itemCount }: { itemCount: number | undefined }) => `共 ${itemCount ?? 0} 条`,
});

// 表单状态
const formState = reactive({
  username: '',
  realName: '',
  email: '',
  phone: '',
  password: '',
  userType: 'INTERNAL',
  roleType: 'HR',
  status: 'ACTIVE',
});

// token 统一走 useUserStore().accessToken
const userStore = useUserStore();
const tokenOf = () => userStore.accessToken;

// API请求封装：统一返回 { ok, status, data }
// 约定（与 campusControl.ts 一致）：
//   - GET 列表 → 信封 { success, data }
//   - 新建/更新/删除/分配 → 写接口返回裸对象或 204, HTTP 2xx 即成功（无 success 信封）
//   - 因此 handler 一律以 res.ok 判定写操作成功, 以 res.data?.success 判定列表信封
const request = async (url: string, options: RequestInit = {}) => {
  const token = tokenOf();
  if (!token) {
    message.error('请先登录');
    return { ok: false, status: 0, data: null as any };
  }
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });
    let data: any = null;
    const text = await response.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = null;
      }
    }
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: null, error };
  }
};

// 加载用户列表（整合后拉全部用户，内部/外部由 user_type 字段区分）
const loadUsers = async () => {
  loading.value = true;
  try {
    const res = await request(`/api/v1/users/`);
    if (res.ok && res.data?.success) {
      users.value = res.data.data;
    } else if (!res.ok) {
      message.error(res.data?.message || '加载用户列表失败');
    }
  } catch (error) {
    console.error('加载用户列表失败', error);
    message.error('网络错误，请检查后端服务');
  } finally {
    loading.value = false;
  }
};

// 客户端搜索 + 筛选（全部用户已在内存，按关键词/类型/状态过滤）
const displayUsers = computed<User[]>(() => {
  const kw = searchText.value.trim().toLowerCase();
  return users.value.filter((u) => {
    if (filterUserType.value && u.userType !== filterUserType.value) return false;
    if (filterStatus.value && u.status !== filterStatus.value) return false;
    if (kw) {
      const hay = `${u.username || ''} ${u.realName || ''}`.toLowerCase();
      if (!hay.includes(kw)) return false;
    }
    return true;
  });
});

// 筛选变化时回到第 1 页，避免停留在越界空页
watch([searchText, filterUserType, filterStatus], () => {
  pagination.page = 1;
});

// 加载角色列表
const loadRoles = async () => {
  try {
    const res = await request('/api/v1/permissions/roles/');
    if (res.ok && res.data?.success) {
      roles.value = res.data.data;
    }
  } catch (error) {
    message.error(extractApiError(error, '加载角色列表失败'));
  }
};

// 加载用户角色
const loadUserRoles = async (userId: string) => {
  try {
    const res = await request(`/api/v1/permissions/users/${userId}/roles/`);
    if (res.ok && res.data?.success) {
      // 角色对象以 RoleV2.id 标识（与角色表格 row-key=row.id、checked-row-keys 一致）
      userRoles.value = res.data.data.map((ur: any) => ur.id);
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
    userType: 'INTERNAL',
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
    userType: 'INTERNAL',
    roleType: 'HR',
    status: 'ACTIVE'
  });
};

// 创建用户
const handleCreateUser = async () => {
  try {
    const res = await request('/api/v1/users/', {
      method: 'POST',
      body: JSON.stringify(formState)
    });
    if (res.ok) {
      message.success('用户创建成功');
      closeUserModal();
      loadUsers();
    } else {
      message.error(res.data?.message || '创建失败');
    }
  } catch (error) {
    message.error('创建失败');
  }
};

// 更新用户（仅提交基础字段；角色由「分配角色」弹窗管理, 不在此覆盖, 避免清空已分配角色）
const handleUpdateUser = async () => {
  try {
    const payload = {
      realName: formState.realName,
      email: formState.email,
      phone: formState.phone,
      userType: formState.userType,
      status: formState.status,
    };
    const res = await request(`/api/v1/users/${editingUser.value?.id}/`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      message.success('用户更新成功');
      closeUserModal();
      loadUsers();
    } else {
      message.error(res.data?.message || '更新失败');
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
    const res = await request(`/api/v1/users/${userId}/`, {
      method: 'DELETE'
    });
    if (res.ok) {
      message.success('用户删除成功');
      loadUsers();
    } else {
      message.error(res.data?.message || '删除失败');
    }
  } catch (error) {
    message.error('删除失败');
  }
};

// 保存用户角色
const handleSaveUserRoles = async (roleIds: string[]) => {
  try {
    const res = await request(`/api/v1/permissions/users/${selectedUserId.value}/roles/`, {
      method: 'POST',
      body: JSON.stringify({ roleIds })
    });
    if (res.ok) {
      message.success('角色分配成功');
      userRoleModalVisible.value = false;
      loadUsers();
    } else {
      message.error(res.data?.message || '分配失败');
    }
  } catch (error) {
    message.error('分配失败');
  }
};

// 绑定企微
const handleBindWechatWork = async (userId: string, wechatWorkUserId: string) => {
  try {
    const res = await request(`/api/v1/users/${userId}/`, {
      method: 'PUT',
      body: JSON.stringify({ wechatWorkUserId })
    });
    if (res.ok) {
      message.success('企微绑定成功');
      loadUsers();
    } else {
      message.error(res.data?.message || '绑定失败');
    }
  } catch (error) {
    message.error('绑定失败');
  }
};

// 解绑企微
const handleUnbindWechatWork = async (userId: string) => {
  try {
    const res = await request(`/api/v1/users/${userId}/`, {
      method: 'PUT',
      body: JSON.stringify({ wechatWorkUserId: null })
    });
    if (res.ok) {
      message.success('企微解绑成功');
      loadUsers();
    } else {
      message.error(res.data?.message || '解绑失败');
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

// ===== 列定义 =====
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
  title: '用户类型',
  key: 'userType',
  width: 100,
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
              userType: row.userType || 'INTERNAL',
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

// 统一列（整合后展示全部用户，用户类型字段区分内外）
const columns = [
  { title: '用户名', key: 'username', width: 120 },
  { title: '姓名', key: 'realName', width: 100 },
  userTypeColumn,
  statusColumn,
  { title: '角色类型', key: 'roleType', width: 90 },
  wechatColumn,
  actionsColumn,
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

/* 搜索 / 筛选行：复用全局 .toolbar / .rule-filter-search / .rule-filter-select / .spacer
   （glass.css 全局工具类，与校招管控规则配置工具条一致）。
   列表区：.table-wrap 直接作为 .page-body(flex 列) 子元素，flex:1 撑满，
   对齐校招管控规则配置页结构（toolbar + 裸 table-wrap，不包 n-card）。 */

</style>
