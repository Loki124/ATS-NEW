<template>
  <div class="page-container">
    <!-- 模型 B（SETTINGS_PAGE_STRUCTURE.md §2.2）：header 为 .page-container 直接子元素，
         header→内容间距由外壳 .settings-scroll :deep(.page-container) 的 gap 独家提供。 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.UserDirectory.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.UserDirectory.s2') }}</p>
      </div>
    </div>

    <!-- 列表区：区域滚动（R-215）—— .data-body 自身不滚，滚动只发生在 .table-wrap 内的表格体，
         页头 / 筛选工具条 / 分页器保持固定。外壳用全局 .panel-shell（8px 内衬 + 撑满高度）。 -->
    <div class="data-body">
      <div class="glass-panel panel-shell">
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
          <!-- 需求5：直属上级筛选（用户维度，异步搜索用户下拉） -->
          <n-select
            v-model:value="filterDirectManager"
            :options="managerOptions"
            placeholder="直属上级"
            clearable
            filterable
            remote
            :on-search="onManagerSearch"
            class="rule-filter-select"
          />
          <!-- 需求5：身份多选筛选（导师 / 班主任，?role= 并集） -->
          <n-select
            v-model:value="filterRoles"
            :options="roleIdentityOptions"
            placeholder="身份"
            multiple
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
      </div>
    </div>

    <!-- 用户编辑弹窗 -->
    <n-modal
      v-model:show="userModalVisible"
      preset="card"
      :title="editingUser ? '编辑用户' : '新建用户'"
      :style="{ width: '860px', maxWidth: '95vw' }"
      :content-style="{ height: 'min(620px, calc(88vh - 180px))', overflowY: 'auto' }"
      :mask-closable="false"
    >
      <n-form :model="formState" label-placement="top">
        <!-- 基础信息 -->
        <div class="form-section">
          <div class="form-section-title">{{ t('pages.settings.UserDirectory.s7') }}</div>
          <!-- UUID：系统生成、全局唯一，只读展示，占满一整行（不再放在弹窗标题栏） -->
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item :span="2">
              <n-form-item :label="t('pages.settings.UserDirectory.s30')">
                <n-input
                  class="uuid-input"
                  :value="formState.uuid"
                  readonly
                  :placeholder="t('pages.settings.UserDirectory.s31')"
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>
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
          <!-- 密码字段已移除：新建用户统一使用系统预置初始密码（settings.DEFAULT_USER_PASSWORD），
               用户登录后可在「个人信息管理」自主修改。避免"填了不生效"的误导。 -->
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
          <!-- 需求5：直属上级（用户维度，复用用户搜索接口） -->
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item :span="2">
              <n-form-item label="直属上级">
                <n-select
                  v-model:value="formState.directManager"
                  :options="managerOptions"
                  placeholder="请选择直属上级"
                  clearable
                  filterable
                  remote
                  :on-search="onManagerSearch"
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
          <!-- 身份配置 + 管理单元授权（2026-10-21）：同行两列，省一行纵向空间
               粒度：管理单元授权为用户级统一 —— 该用户的全部身份共用同一份范围，
               与后端 UserRoleV2.management_unit_ids 的写入口径一致（多身份取并集）。 -->
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
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
            <n-grid-item>
              <n-form-item :label="t('pages.settings.UserDirectory.s32')">
                <n-tree-select
                  v-model:value="formState.managementUnitIds"
                  :options="mgmtUnitOptions"
                  :loading="mgmtUnitLoading"
                  :disabled="!!mgmtUnitError"
                  multiple
                  checkable
                  clearable
                  filterable
                  :placeholder="t('pages.settings.UserDirectory.s33')"
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <p class="form-hint" :class="{ 'is-error': !!mgmtUnitError }">
            {{ mgmtUnitError || t('pages.settings.UserDirectory.s34') }}
          </p>
        </div>
      </n-form>

      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button @click="closeUserModal">{{ t('pages.settings.UserDirectory.s28') }}</n-button>
          <n-button type="primary" class="gradient-btn" @click="handleUserSubmit">{{ t('pages.settings.UserDirectory.s29') }}</n-button>
        </div>
      </template>
    </n-modal>
</div>
</template>
<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { localPagination } from '@/composables/useTablePagination'
// 列对齐与操作列规格的单一真源（四档规则见 useTableColumns.ts 文件头）
import { column, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns'
import { ref, reactive, onMounted, computed, watch, h } from 'vue';
import {
  AddOutline,
  CreateOutline,
  TrashOutline,
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
// 2026-10-18 兵哥：状态改为三态，与后端 User.activation_status 同源同值。
//   PENDING 待激活（管理员开通后未完成首次邮箱验证登录）
//   ACTIVE  已激活
//   DISABLED 已停用（管理员停用 / 软删除）
// 旧值 INACTIVE / LOCKED 已随后端改造下线，此处不再保留。
const STATUS_MAP: Record<string, { type: any; label: string }> = {
  PENDING: { type: 'warning', label: '待激活' },
  ACTIVE: { type: 'success', label: '已激活' },
  DISABLED: { type: 'error', label: '已停用' }
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
  /** 该用户拥有的身份名称列表（后端 roleNames，由 role_code → RoleV2.role_name 批量派生） */
  roleNames?: string[];
  /** 该用户被授权的管理单元名称列表（后端 managementUnitNames，用户级统一口径取并集） */
  managementUnitNames?: string[];
  /** 直属上级（User 外键，可选，零 DDL 复用 core.User.direct_manager） */
  directManager?: string;
  /** 直属上级姓名（只读派生字段，见 03-技术方案 §3.1） */
  directManagerName?: string;
  createdAt: string;
}

interface Role {
  id: string;
  name: string;
  code: string;
  roleType?: string;
}

/** 管理单元树节点（后端 GET /api/v1/management-units/tree/，camelCase 输出） */
interface MgmtUnitNode {
  id: string | number;
  unitName: string;
  parentId?: string | number | null;
  status?: number;
  children?: MgmtUnitNode[];
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
// 需求5：直属上级筛选（按 User 维度，非部门）/ 身份多选筛选（导师·班主任）
const filterDirectManager = ref<string | null>(null);
const filterRoles = ref<string[]>([]);

// 身份筛选选项（导师 / 班主任，对应 RoleV2 身份类型，见 03-技术方案 §0）
const roleIdentityOptions = [
  { label: '导师', value: 'campus_mentor' },
  { label: '班主任', value: 'head_teacher' },
];

// 直属上级用户下拉数据源：复用用户搜索接口（GET /api/v1/users/?search=）异步检索。
// 直属上级是「用户」不是「部门」，故走用户搜索而非部门树。
const managerOptions = ref<{ label: string; value: string }[]>([]);
const onManagerSearch = async (kw: string) => {
  const term = (kw || '').trim();
  if (!term) return;
  const res = await request(`/api/v1/users/?search=${encodeURIComponent(term)}&page_size=50`);
  if (res.ok && res.data?.success) {
    managerOptions.value = (res.data.data || []).map((u: any) => ({
      label: `${u.realName || u.username}${u.employeeId ? `（${u.employeeId}）` : ''}`,
      value: String(u.id),
    }));
  }
};

// 下拉选项
const statusOptions = [
  { label: '待激活', value: 'PENDING' },
  { label: '已激活', value: 'ACTIVE' },
  { label: '已停用', value: 'DISABLED' },
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
  employeeId: '',
  uuid: '',
  roleIds: [] as string[],
  userType: 'INTERNAL',
  // 2026-10-18 兵哥：新建用户默认「待激活」——自助注册已下线，账号只能由管理员开通，
  //   用户需完成一次邮箱验证码登录才自动转为「已激活」。
  status: 'PENDING',
  department: null as string | null,
  // 需求5：直属上级（写 directManager；directManagerName 由后端只读派生）
  directManager: null as string | null,
  // 管理单元授权（用户级统一口径）：该用户全部身份共用这一份范围。
  // 值为字符串（管理单元 id），与 n-tree-select 的 key 类型一致；提交时转回数字。
  managementUnitIds: [] as string[],
});

// ===== 管理单元授权 =====
// 管理单元树：授权范围选择器的数据源。加载失败（如账号缺 recruit:settings:mgmt_unit:list
// 读码）时降级为「不可配置」并给出说明，而不是让授权项静默空白 ——
// 「配了却没生效」是本项目最高频的静默缺陷（ui-interaction-constraints R-203）。
const mgmtUnitTree = ref<MgmtUnitNode[]>([]);
const mgmtUnitLoading = ref(false);
const mgmtUnitError = ref('');

// 身份 + 授权范围是否已成功回显。
// 未成功回显时提交时**省略** managementUnitIds，让后端「缺省 = 不动已有范围」的语义生效
// —— 否则一次 GET 抖动就会把管理员配好的授权范围静默清空（数据丢失，且无提示）。
const roleScopeLoaded = ref(false);

const mgmtUnitOptions = computed<any[]>(() => {
  const build = (nodes: MgmtUnitNode[]): any[] =>
    nodes.map((n) => ({
      key: String(n.id),
      label: n.unitName,
      // 停用单元不可新授权（已授权的仍可回显并可移除）
      disabled: n.status === 0,
      children: n.children?.length ? build(n.children) : undefined,
    }));
  return build(mgmtUnitTree.value);
});

// 身份配置下拉选项（由 roles（RoleV2 列表）派生，value=RoleV2.id）
// label 只存身份名称：下拉选项与已选回显均不显示身份编码（filterable 搜索同样只按名称匹配）。
const roleOptions = computed(() =>
  roles.value.map((r) => ({ label: r.name, value: r.id }))
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

// 部门完整路径（根 → 当前），用于列表「任职部门」列 hover 提示。
// 与 buildDeptTree 相同的回溯逻辑：沿 parentId 上溯拼接部门名，以「 / 」分隔；
// 带 visited 集合防止脏数据（parentId 成环）导致死循环；部门不存在或无父级时退化为自身名称。
function deptFullPath(deptId: string): string {
  const list = deptStore.departments as any[];
  const byId = new Map<string, any>();
  list.forEach((d) => byId.set(String(d.id), d));
  const names: string[] = [];
  const visited = new Set<string>();
  let cur: any = byId.get(String(deptId));
  while (cur && !visited.has(String(cur.id))) {
    visited.add(String(cur.id));
    names.unshift(cur.name);
    cur = cur.parentId ? byId.get(String(cur.parentId)) : null;
  }
  return names.join(' / ');
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

// 加载用户列表：后端为服务端分页（默认 page_size=50、上限 200、响应带 pagination.total）。
// 本页需要「展示全部用户」+ 客户端搜索/筛选，故循环翻页把所有用户一次性拉全，存入 users。
// 需求5：直属上级（direct_manager）/ 身份（role，多值并集）走服务端过滤，挂到查询串上。
const loadUsers = async () => {
  loading.value = true;
  try {
    const all: any[] = [];
    let page = 1;
    const pageSize = 200; // 后端上限，单次取最多
    const extra = new URLSearchParams();
    if (filterDirectManager.value) extra.set('direct_manager', String(filterDirectManager.value));
    if (filterRoles.value.length) extra.set('role', filterRoles.value.join(','));
    const qs = extra.toString();
    while (true) {
      const res = await request(`/api/v1/users/?page=${page}&page_size=${pageSize}${qs ? `&${qs}` : ''}`);
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

// 需求5：直属上级 / 身份筛选走服务端，变化时重新拉取列表（desktopUsers 已清空分页状态由 :data 引用变化自动重置）。
watch([filterDirectManager, filterRoles], () => {
  loadUsers();
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

// 加载用户身份 → 填入编辑表单的身份配置多选（RoleV2.id 列表）
// 同时回填管理单元授权范围：后端按用户级统一口径下发（各身份项携带同一份并集）。
const loadUserRoles = async (userId: string) => {
  try {
    const res = await request(`/api/v1/permissions/users/${userId}/roles/`);
    if (res.ok && res.data?.success) {
      const list = res.data.data || [];
      formState.roleIds = list.map((ur: any) => ur.id);
      const ids = new Set<string>();
      list.forEach((ur: any) =>
        (ur.managementUnitIds || []).forEach((v: any) => ids.add(String(v)))
      );
      formState.managementUnitIds = Array.from(ids);
      roleScopeLoaded.value = true;
    } else {
      roleScopeLoaded.value = false;
    }
  } catch (error) {
    roleScopeLoaded.value = false;
    message.error(extractApiError(error, '加载用户角色失败'));
  }
};

// 加载管理单元树（授权范围选择器的数据源）
const loadMgmtUnits = async () => {
  mgmtUnitLoading.value = true;
  mgmtUnitError.value = '';
  try {
    const res = await request('/api/v1/management-units/tree/');
    if (res.ok && res.data?.success) {
      mgmtUnitTree.value = res.data.data || [];
    } else {
      mgmtUnitError.value = res.data?.message || t('pages.settings.UserDirectory.s35');
    }
  } catch (error) {
    mgmtUnitError.value = extractApiError(error, t('pages.settings.UserDirectory.s35'));
  } finally {
    mgmtUnitLoading.value = false;
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
    employeeId: '',
    uuid: '',
    roleIds: [],
    userType: 'INTERNAL',
    status: 'PENDING',
    department: null,
    directManager: null,
    managementUnitIds: []
  });
  roleScopeLoaded.value = false;
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
    employeeId: '',
    uuid: '',
    roleIds: [],
    userType: 'INTERNAL',
    status: 'PENDING',
    department: null,
    directManager: null,
    managementUnitIds: []
  });
  roleScopeLoaded.value = false;
};

// 创建用户（含工号；身份配置在创建成功后单独保存）
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

// 更新用户（放开花名编辑 + 工号；身份配置在更新成功后单独保存）
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
      directManager: formState.directManager,
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

// 保存用户身份配置 + 管理单元授权（端点：POST /api/v1/permissions/users/{id}/roles/）
// 界面文案统一为「身份配置」，后端端点与字段名仍为 role / roleIds，此处不做重命名。
// managementUnitIds 一并提交：用户级统一口径，后端把同一份范围写到该用户全部身份行。
const saveUserRoles = async (userId: string, roleIds: string[]) => {
  try {
    const payload: Record<string, any> = { roleIds };
    // 只有成功回显过授权范围才提交它：未回显时省略该字段 → 后端按「缺省 = 保留」处理，
    // 避免一次加载失败就把已有授权范围清空。
    if (roleScopeLoaded.value) {
      payload.managementUnitIds = formState.managementUnitIds
        .map((v) => Number(v))
        .filter((n) => Number.isFinite(n));
    }
    const res = await request(`/api/v1/permissions/users/${userId}/roles/`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      message.success('身份配置已保存');
    } else {
      message.error(res.data?.message || '身份保存失败');
    }
  } catch (error) {
    message.error('身份保存失败');
  }
};

// 提交用户表单
const handleUserSubmit = () => {
  // 授权范围挂在「用户 × 身份」上（UserRoleV2.management_unit_ids），
  // 没有身份就没有可挂载的授权行 —— 此时拦下并说明，而不是静默丢弃配置。
  if (formState.managementUnitIds.length && !formState.roleIds.length) {
    message.warning('请先选择身份，再配置管理单元授权');
    return;
  }
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

// 拥有身份：默认展示前 2 个身份名称，超出部分折叠为「+N」。
// 只要发生过折叠就挂 tooltip 展示完整列表（R-110：截断必须提供查看完整信息的途径）；
// 未截断时不挂 tooltip，避免悬浮层与单元格内容重复。
const OWNED_ROLE_VISIBLE = 2;
const ownedRolesColumn = {
  title: '拥有身份',
  key: 'roleNames',
  width: 180,
  render: (row: User) => {
    const names = (row.roleNames || []).filter(Boolean);
    if (!names.length) return h('span', { class: 'cell-muted' }, '-');
    const shown = names.slice(0, OWNED_ROLE_VISIBLE);
    const rest = names.length - shown.length;
    const body = h('span', { class: 'role-tags' }, [
      ...shown.map((n) => h(NTag, { size: 'small', bordered: false, type: 'info' }, { default: () => n })),
      rest > 0 ? h('span', { class: 'role-more' }, `+${rest}`) : null,
    ]);
    if (rest <= 0) return body;
    return h(NTooltip, null, {
      trigger: () => body,
      default: () => h('span', { class: 'role-tip' }, names.join('、')),
    });
  }
};

// 管理单元范围：展示该用户被授权的管理单元（用户级统一口径，多身份取并集）。
// 与「拥有身份」列同款展示规范：默认展示前 2 个名称，超出折叠为「+N」，
// 折叠时挂 tooltip 给出完整列表（R-110：截断必须提供查看完整信息的途径）。
const MGMT_UNIT_VISIBLE = 2;
const mgmtUnitsColumn = {
  title: '管理单元范围',
  key: 'managementUnitNames',
  width: 180,
  render: (row: User) => {
    const names = (row.managementUnitNames || []).filter(Boolean);
    if (!names.length) return h('span', { class: 'cell-muted' }, '-');
    const shown = names.slice(0, MGMT_UNIT_VISIBLE);
    const rest = names.length - shown.length;
    const body = h('span', { class: 'mgmt-tags' }, [
      ...shown.map((n) => h(NTag, { size: 'small', bordered: false, type: 'info' }, { default: () => n })),
      rest > 0 ? h('span', { class: 'role-more' }, `+${rest}`) : null,
    ]);
    if (rest <= 0) return body;
    return h(NTooltip, null, {
      trigger: () => body,
      default: () => h('span', { class: 'role-tip' }, names.join('、')),
    });
  }
};

const actionsColumn = {
  title: '操作',
  key: 'actions',
  width: 160,
  fixed: 'right' as const,
  render: (row: User) => {
    return h(NSpace, { size: 8, wrap: false }, {
      default: () => [
        h(NButton, {
          type: 'primary',
          size: OP_ACTION_BUTTON_SIZE,
          quaternary: true,
          onClick: () => {
            editingUser.value = row;
            Object.assign(formState, {
              username: row.username,
              realName: row.realName,
              email: row.email || '',
              phone: row.phone || '',
              employeeId: row.employeeId || '',
              uuid: row.uuid || '',
              roleIds: [],
              userType: row.userType || 'INTERNAL',
              status: row.status,
              department: row.department != null ? String(row.department) : null,
              directManager: row.directManager != null ? String(row.directManager) : null,
              managementUnitIds: []
            });
            roleScopeLoaded.value = false;
            // 预填直属上级下拉选项（列表已返回 directManagerName，避免弹窗显示裸 id）
            if (row.directManager != null) {
              const idStr = String(row.directManager);
              if (!managerOptions.value.some((o) => o.value === idStr)) {
                managerOptions.value = [
                  { label: row.directManagerName || idStr, value: idStr },
                  ...managerOptions.value,
                ];
              }
            }
            loadUserRoles(row.id);
            userModalVisible.value = true;
          }
        }, { default: () => '编辑', icon: () => h(NIcon, null, { default: () => h(CreateOutline) }) }),
        h(NPopconfirm, {
          onPositiveClick: () => handleDeleteUser(row.id),
          positiveText: '确认',
          negativeText: '取消',
        }, {
          default: () => '确认删除此用户？',
          trigger: () => h(NButton, {
            type: 'error',
            size: OP_ACTION_BUTTON_SIZE,
            quaternary: true,
          }, { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) }),
        }),
      ],
    });
  }
};

// 统一列（整合后展示全部用户，用户类型字段区分内外）
// 列对齐统一走 useTableColumns 工厂（四档规则，短值/枚举居中，长文本左对齐）。
const columns = [
  column({ title: '花名', key: 'username', width: 160, ellipsis: true }, 'short'),
  column({ title: '姓名', key: 'realName', width: 120, ellipsis: true }, 'short'),
  column({ title: '工号', key: 'employeeId', width: 110, ellipsis: true, render: (row: User) => row.employeeId || '-' }, 'short'),
  column({
    title: '任职部门',
    key: 'departmentName',
    width: 150,
    ellipsis: true,
    render: (row: User) => {
      const deptId = row.department != null ? String(row.department) : '';
      const name =
        row.departmentName ||
        (deptId ? deptStore.getById(deptId)?.name : '') ||
        '-';
      // 单元格只显示部门名（列窄，名称过长省略），hover 时 tooltip 展示根→当前完整路径
      // （如「总公司 / 技术中心 / 前端组」）；顶层部门路径与名称一致时无需 tooltip。
      const full = deptId ? deptFullPath(deptId) : '';
      const text = h('span', { class: 'cell-ellipsis' }, name);
      if (!full || full === name) return text;
      return h(NTooltip, null, { trigger: () => text, default: () => full });
    }
  }, 'short'),
  column({
    title: '直属上级',
    key: 'directManagerName',
    width: 120,
    ellipsis: true,
    render: (row: User) => row.directManagerName || '-'
  }, 'short'),
  column(userTypeColumn, 'short'),
  column(statusColumn, 'short'),
  column(ownedRolesColumn, 'short'),
  column(mgmtUnitsColumn, 'short'),
  column(actionsColumn, 'control'),
];

// 生命周期
onMounted(() => {
  loadUsers();
  loadRoles();
  loadMgmtUnits();
  deptStore.loadDepartments();
});
</script>


<style scoped>

/* === 数据列表页标准结构（SETTINGS_PAGE_STRUCTURE.md §2.2 + AGENTS.md R-215）
   模型 B：.page-container > .page-header + .data-body > .glass-panel.panel-shell
                              > .toolbar + .table-wrap > n-data-table[flex-height]
   - .page-container：高度受限的 flex 列（高度由 SettingsLayout :deep 强制）
   - .page-header：flex-shrink:0 固定（间距由外壳 .page-container 的 gap 独家提供）
   - .data-body：滚动容器用 .data-body 而非 .page-body ——
     后者被 SettingsLayout :deep(.page-body){overflow-y:auto!important} 强制整页滚动，
     会与表格体的内部滚动叠成双滚动条（规范 §2.2 的「致命陷阱」）
   - .panel-shell / .table-wrap / .toolbar：全部复用 glass.css 全局类，不私有重写
   - n-data-table 必须带 flex-height，否则表高为 0 或被内容撑开 */
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
.data-body {
  flex: 1;
  min-height: 0;
  overflow-y: hidden;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/* 搜索 / 筛选行：复用全局 .toolbar / .rule-filter-search / .rule-filter-select / .spacer
   （glass.css 全局工具类，与校招管控规则配置工具条一致）。
   列表区：.glass-panel.panel-shell(全局) 内为 toolbar + .table-wrap(全局)，
   .table-wrap flex:1 撑满，只让表体滚动（R-215 区域滚动）。 */

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
  color: var(--ink);
  margin-bottom: var(--space-3);
}
.form-section-title::before {
  content: '';
  width: 3px;
  height: 14px;
  border-radius: 2px;
  background: var(--brand-600);
}

/* UUID 只读输入框：等宽字体便于逐字符核对，不使用 disabled 变灰（仍需清晰可读） */
.uuid-input :deep(.n-input__input-el) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: var(--fs-14);
}

/* 单元格文本：列宽不足时单行省略，完整内容由 hover tooltip 提供（R-110） */
.cell-ellipsis {
  display: inline-block;
  max-width: 100%;
  vertical-align: bottom;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 拥有身份 / 管理单元范围：单行排列，超出列宽的标签由容器裁掉（完整列表走 tooltip） */
.role-tags,
.mgmt-tags {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  max-width: 100%;
  overflow: hidden;
  vertical-align: middle;
}
.role-more {
  flex-shrink: 0;
  font-size: var(--fs-12);
  color: var(--ink-faint);
  font-variant-numeric: tabular-nums;
}
.role-tip {
  display: block;
  max-width: 260px;
  line-height: 1.6;
}
.cell-muted {
  color: var(--ink-faint);
}

/* 表单说明行：授权口径提示 / 加载失败降级说明（错误态用 --c-error-deep 保证对比度达标） */
.form-hint {
  margin: 0;
  font-size: var(--text-small);
  line-height: 1.6;
  color: var(--ink-faint);
}
.form-hint.is-error {
  color: var(--c-error-deep);
}
</style>
