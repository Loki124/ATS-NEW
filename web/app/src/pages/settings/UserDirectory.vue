<template>
  <div class="page-container">
<div class="page-body">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.UserDirectory.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.UserDirectory.s2') }}</p>
      </div>
    </div>

    <!-- 搜索 + 筛选行：对齐校招管控规则配置工具条（搜索框 + 筛选项 + spacer 推右按钮） -->
    <div class="toolbar">
      <n-input
        v-model:value="searchText"
        :placeholder="t('pages.settings.UserDirectory.s3')"
        clearable
        class="rule-filter-search"
        @keyup.enter="() => {}"
      >
        <template #prefix><n-icon :component="SearchOutline" /></template>
      </n-input>
      <n-select
        v-model:value="filterUserType"
        :options="userTypeFilterOptions"
        :placeholder="t('pages.settings.UserDirectory.s4')"
        clearable
        class="rule-filter-select"
      />
      <n-select
        v-model:value="filterStatus"
        :options="statusOptions"
        :placeholder="t('pages.settings.UserDirectory.s5')"
        clearable
        class="rule-filter-select"
      />
      <div class="spacer"></div>
      <n-button type="primary" @click="openCreateModal">
        <template #icon><n-icon :component="AddOutline" /></template>
        {{ t('pages.settings.UserDirectory.s6') }}
      </n-button>
    </div>

    <div class="table-wrap">
      <n-data-table
        :data="displayUsers"
        :columns="columns"
        :row-key="(row: User) => row.id"
        :loading="loading"
        :pagination="localPagination()"
        :bordered="false"
        flex-height
      >
        <template #empty><n-empty description="暂无用户" /></template>
      </n-data-table>
    </div>

    <!-- 用户编辑弹窗 -->
    <n-modal
      v-model:show="userModalVisible"
      preset="card"
      :title="editingUser ? '编辑用户(' + formState.uuid + ')' : '新建用户'"
      :style="{ width: '600px' }"
      :mask-closable="false"
    >
      <n-form :model="formState" label-placement="top">
        <!-- 基础信息 -->
        <div class="form-section">
          <div class="form-section-title">{{ t('pages.settings.UserDirectory.s7') }}</div>
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item :label="t('pages.settings.UserDirectory.s8')" required>
                <n-input v-model:value="formState.username" :placeholder="t('pages.settings.UserDirectory.s9')" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item :label="t('pages.settings.UserDirectory.s10')" required>
                <n-input v-model:value="formState.realName" :placeholder="t('pages.settings.UserDirectory.s11')" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item :label="t('pages.settings.UserDirectory.s12')">
                <n-input v-model:value="formState.email" :placeholder="t('pages.settings.UserDirectory.s13')" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item :label="t('pages.settings.UserDirectory.s14')">
                <n-input v-model:value="formState.phone" :placeholder="t('pages.settings.UserDirectory.s15')" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-grid v-if="!editingUser" :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item :label="t('pages.settings.UserDirectory.s16')" required>
                <n-input
                  v-model:value="formState.password"
                  type="password"
                  show-password-on="click"
                  :placeholder="t('pages.settings.UserDirectory.s17')"
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>
        </div>

        <!-- 任职信息 -->
        <div class="form-section">
          <div class="form-section-title">{{ t('pages.settings.UserDirectory.s18') }}</div>
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item :label="t('pages.settings.UserDirectory.s19')">
                <n-input v-model:value="formState.employeeId" :placeholder="t('pages.settings.UserDirectory.s20')" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
            <n-form-item :label="t('pages.settings.UserDirectory.s21')">
              <n-tree-select
                v-model:value="formState.department"
                :options="deptTreeOptions"
                :render-label="renderDeptLabel"
                :placeholder="t('pages.settings.UserDirectory.s22')"
                clearable
                filterable
                :loading="deptStore.loading"
                :default-expand-all="false"
              />
            </n-form-item>
            </n-grid-item>
          </n-grid>
        </div>

        <!-- 权限信息 -->
        <div class="form-section">
          <div class="form-section-title">{{ t('pages.settings.UserDirectory.s23') }}</div>
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item :label="t('pages.settings.UserDirectory.s24')">
                <n-select
                  v-model:value="formState.userType"
                  :options="userTypeOptions"
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item :label="t('pages.settings.UserDirectory.s25')">
                <n-select
                  v-model:value="formState.status"
                  :options="statusOptions"
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item :span="2">
              <n-form-item :label="t('pages.settings.UserDirectory.s26')">
                <n-select
                  v-model:value="formState.roleIds"
                  :options="roleOptions"
                  multiple
                  :placeholder="t('pages.settings.UserDirectory.s27')"
                  clearable
                  filterable
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>
        </div>
      </n-form>

      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button @click="closeUserModal">{{ t('pages.settings.UserDirectory.s28') }}</n-button>
          <n-button type="primary" class="gradient-btn" @click="handleUserSubmit">{{ t('pages.settings.UserDirectory.s29') }}</n-button>
        </div>
      </template>
    </n-modal>
    </div><!-- /.page-body -->
</div>
</template>
<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { localPagination } from '@/composables/useTablePagination'
import { ref, reactive, onMounted, computed, h } from 'vue';
import {
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
  NSelect,
  useMessage,
} from 'naive-ui';
import { extractApiError } from '../../api/dynamic-field';
import { useUserStore } from '../../stores/user';
import { useDepartmentStore } from '../../stores/department';
const { t } = useI18n()

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
  department?: string;
  departmentName?: string;
  employeeId?: string;
  positionTitle?: string;
  uuid?: string;
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

// 搜索 / 筛选
const searchText = ref('');
const filterUserType = ref<string | null>(null);
const filterStatus = ref<string | null>(null);

// 下拉选项
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
  { label: '全部类型', value: '' as string },
  { label: '内部员工', value: 'INTERNAL' },
  { label: '外部用户', value: 'EXTERNAL' },
];

// 分页器走 useTablePagination 的 localPagination()（SETTINGS_PAGE_STRUCTURE.md §4.x）
// 客户端分页：displayUsers 已是筛选后数组，naive-ui 自动从 :data 长度计算 itemCount，无需手动维护

// 表单状态
const formState = reactive({
  username: '',
  realName: '',
  email: '',
  phone: '',
  password: '',
  employeeId: '',
  uuid: '',
  roleIds: [] as string[],
  userType: 'INTERNAL',
  status: 'ACTIVE',
  department: null as string | null,
});

// 角色配置下拉选项（由 roles（RoleV2 列表）派生，value=RoleV2.id）
const roleOptions = computed(() =>
  roles.value.map((r) => ({ label: `${r.name}（${r.code}）`, value: r.id }))
);

// token 统一走 useUserStore().accessToken
const userStore = useUserStore();
const tokenOf = () => userStore.accessToken;

// 任职部门选择器数据源：复用组织管理部门（useDepartmentStore 共享缓存）。
// 改用树形 n-tree-select 展示部门层级：节点 label=完整路径（选中后输入框回显完整路径，
// 如「总公司/技术中心/前端组」），render-label 在树内只显示部门名称 + 缩进体现层级深度；
// 任意部门（含父级）均可直接选中，value=部门 id，直接落 User.department FK。
const deptStore = useDepartmentStore();
const deptTreeOptions = computed(() => buildDeptTree(deptStore.departments));
function buildDeptTree(list: any[]): any[] {
  const nameById = new Map<string, string>();
  list.forEach((d) => nameById.set(String(d.id), d.name));
  const nodeById = new Map<string, any>();
  list.forEach((d) => {
    nodeById.set(String(d.id), {
      key: String(d.id),
      label: '', // 完整路径，选中后触发器回显
      name: d.name,
      children: [] as any[],
    });
  });
  const roots: any[] = [];
  list.forEach((d) => {
    const node = nodeById.get(String(d.id));
    // 计算完整路径（根→当前）
    const path: string[] = [];
    let cur: any = d;
    while (cur) {
      path.unshift(nameById.get(String(cur.id)) || String(cur.id));
      cur = cur.parentId ? list.find((x) => String(x.id) === String(cur.parentId)) : null;
    }
    node.label = path.join('/');
    if (d.parentId) {
      const parent = nodeById.get(String(d.parentId));
      if (parent) parent.children.push(node);
      else roots.push(node);
    } else {
      roots.push(node);
    }
  });
  const clean = (nodes: any[]): any[] =>
    nodes
      .map((n) => ({
        key: n.key,
        label: n.label,
        name: n.name,
        children: n.children.length ? clean(n.children) : undefined,
      }))
      .sort((a, b) => a.label.localeCompare(b.label));
  return clean(roots);
}
// 树内节点只显示部门名称（层级深度由 n-tree-select 缩进体现），不重复完整路径
function renderDeptLabel({ option }: { option: any }) {
  return h('span', option.name);
}

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

// 加载用户列表：后端为服务端分页（默认 page_size=20、上限 200、响应带 pagination.total）。
// 本页需要「展示全部用户」+ 客户端搜索/筛选，故循环翻页把所有用户一次性拉全，存入 users。
const loadUsers = async () => {
  loading.value = true;
  try {
    const all: any[] = [];
    let page = 1;
    const pageSize = 200; // 后端上限，单次取最多
    while (true) {
      const res = await request(`/api/v1/users/?page=${page}&page_size=${pageSize}`);
      if (!res.ok || !res.data?.success) {
        message.error(res.data?.message || '加载用户列表失败');
        break;
      }
      const pageData: any[] = res.data.data || [];
      all.push(...pageData);
      const total: number = res.data.pagination?.total ?? pageData.length;
      if (pageData.length === 0 || all.length >= total) break;
      page += 1;
    }
    users.value = all;
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

// 筛选结果变化时：回到第 1 页（localPagination 非受控，需通过 :key 触发或 reset）
// 注：naive-ui localPagination 在 :data 数组引用变化时自动重置页码，无需显式处理。

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

// 加载用户角色 → 填入编辑表单的角色配置多选（RoleV2.id 列表）
const loadUserRoles = async (userId: string) => {
  try {
    const res = await request(`/api/v1/permissions/users/${userId}/roles/`);
    if (res.ok && res.data?.success) {
      formState.roleIds = res.data.data.map((ur: any) => ur.id);
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
    employeeId: '',
    uuid: '',
    roleIds: [],
    userType: 'INTERNAL',
    status: 'ACTIVE',
    department: null
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
    employeeId: '',
    uuid: '',
    roleIds: [],
    userType: 'INTERNAL',
    status: 'ACTIVE',
    department: null
  });
};

// 创建用户（含工号；角色配置在创建成功后单独保存）
const handleCreateUser = async () => {
  try {
    const res = await request('/api/v1/users/', {
      method: 'POST',
      body: JSON.stringify(formState)
    });
    if (res.ok) {
      const newId = res.data?.id || res.data?.data?.id;
      if (newId && formState.roleIds.length) {
        await saveUserRoles(String(newId), formState.roleIds);
      }
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

// 更新用户（放开用户名编辑 + 工号；角色配置在更新成功后单独保存）
const handleUpdateUser = async () => {
  try {
    const payload = {
      username: formState.username,
      realName: formState.realName,
      email: formState.email,
      phone: formState.phone,
      employeeId: formState.employeeId || null,
      userType: formState.userType,
      status: formState.status,
      department: formState.department,
    };
    const res = await request(`/api/v1/users/${editingUser.value?.id}/`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      await saveUserRoles(String(editingUser.value?.id), formState.roleIds);
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

// 保存用户角色配置（复用原「分配角色」端点：POST /api/v1/permissions/users/{id}/roles/）
const saveUserRoles = async (userId: string, roleIds: string[]) => {
  try {
    const res = await request(`/api/v1/permissions/users/${userId}/roles/`, {
      method: 'POST',
      body: JSON.stringify({ roleIds })
    });
    if (res.ok) {
      message.success('角色配置已保存');
    } else {
      message.error(res.data?.message || '角色保存失败');
    }
  } catch (error) {
    message.error('角色保存失败');
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
      return h(NSpace, { size: 'small', wrap: false }, {
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
  width: 160,
  render: (row: User) => {
    return h(NSpace, { size: 'small', wrap: false }, {
      default: () => [
        h(NButton, {
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
              employeeId: row.employeeId || '',
              uuid: row.uuid || '',
              roleIds: [],
              userType: row.userType || 'INTERNAL',
              status: row.status,
              department: row.department != null ? String(row.department) : null
            });
            loadUserRoles(row.id);
            userModalVisible.value = true;
          }
        }, { default: () => '编辑', icon: () => h(NIcon, { component: CreateOutline }) }),
        h(NPopconfirm, {
          onPositiveClick: () => handleDeleteUser(row.id),
          positiveText: '确认',
          negativeText: '取消',
        }, {
          default: () => '确认删除此用户？',
          trigger: () => h(NButton, {
            type: 'error',
            size: 'small',
          }, { default: () => '删除', icon: () => h(NIcon, { component: TrashOutline }) }),
        }),
      ],
    });
  }
};

// 统一列（整合后展示全部用户，用户类型字段区分内外）
const columns = [
  { title: '用户名', key: 'username', width: 160, ellipsis: true },
  { title: '姓名', key: 'realName', width: 120, ellipsis: true },
  { title: '工号', key: 'employeeId', width: 110, ellipsis: true, render: (row: User) => row.employeeId || '-' },
  {
    title: '任职部门',
    key: 'departmentName',
    width: 150,
    ellipsis: true,
    render: (row: User) => {
      const name =
        row.departmentName ||
        (row.department ? deptStore.getById(String(row.department))?.name : '') ||
        '-';
      return name;
    }
  },
  userTypeColumn,
  statusColumn,
  { title: '角色类型', key: 'roleType', width: 90, ellipsis: true },
  wechatColumn,
  actionsColumn,
];

// 生命周期
onMounted(() => {
  loadUsers();
  loadRoles();
  deptStore.loadDepartments();
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

/* 编辑弹窗：基础信息 / 任职信息 / 权限信息 三模块分组
   - 模块标题用 3px 品牌强调条（token，随主题切换，不硬编码 hex），与 scope-block 标题层次一致
   - 模块间距用 --space-4 节奏，模块内字段无需额外 gap（n-form-item 自带纵向间距） */
.form-section {
  margin-bottom: var(--space-4);
}
.form-section:last-child {
  margin-bottom: 0;
}
.form-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--space-3);
}
.form-section-title::before {
  content: '';
  width: 3px;
  height: 14px;
  border-radius: 2px;
  background: var(--brand-600);
}

</style>
