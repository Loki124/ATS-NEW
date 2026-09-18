<template>
  <div class="page-container">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">组织管理</h1>
          <p class="page-subtitle">维护组织架构与部门职责，作为管控与权限的归属单元</p>
        </div>
        <div class="page-header-actions">
          <n-radio-group v-model:value="statusFilter" size="small">
            <n-radio-button value="ALL">全部</n-radio-button>
            <n-radio-button value="ACTIVE">启用</n-radio-button>
            <n-radio-button value="INACTIVE">停用</n-radio-button>
          </n-radio-group>
          <n-input
            v-model:value="searchKeyword"
            placeholder="搜索部门名称/编号"
            style="width: 240px"
            clearable
            @clear="searchKeyword = ''"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
          <n-button ghost @click="loadDepartments">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            刷新
          </n-button>
          <n-button ghost @click="openCreateModal">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增部门
          </n-button>
        </div>
      </div>

      <n-card :bordered="false">
        <n-data-table
          :data="displayData"
          :columns="columns"
          :row-key="(row: Department) => row.id"
          :loading="loading"
          :expanded-row-keys="expandedKeys"
          :pagination="{ pageSize: 20, showSizePicker: true, pageSizes: [10, 20, 50], prefix: ({ itemCount }: any) => `共 ${itemCount} 条` }"
          size="medium"
          @update:expanded-row-keys="(k: any) => (expandedKeys = k)"
        />
      </n-card>

      <!-- 部门详情 / 编辑 合一弹窗（居中） -->
      <n-modal
        v-model:show="deptModalVisible"
        preset="card"
        :title="editingDept ? '编辑部门' : '新建部门'"
        :style="{ width: '720px', maxHeight: '88vh' }"
        :mask-closable="false"
        :centered="true"
        :auto-focus="false"
      >
        <div class="dept-modal-scroll" style="max-height: calc(88vh - 132px); overflow-y: auto; padding-right: 8px">
        <n-form :model="formState" label-placement="top">
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
        </div>

        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
            <n-button text @click="closeDeptModal">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="submitting" @click="handleDeptSubmit">保存部门</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 部门详情抽屉：列表隐藏的编号/ID/负责人2/分管VP 等在此完整展示 -->
      <n-drawer v-model:show="detailVisible" :width="520" placement="right" :auto-focus="false">
        <n-drawer-content title="部门详情" :native-scrollbar="false">
          <n-descriptions
            v-if="detailDept"
            label-placement="left"
            bordered
            :column="1"
            size="medium"
          >
            <n-descriptions-item label="部门名称">{{ detailDept.name }}</n-descriptions-item>
            <n-descriptions-item label="部门编号">{{ detailDept.code }}</n-descriptions-item>
            <n-descriptions-item label="部门ID">
              <span style="font-family: monospace; font-size: 12px; color: #8c8c8c">{{ detailDept.id }}</span>
            </n-descriptions-item>
            <n-descriptions-item label="上级部门">
              <span v-if="detailDept.parentId">{{ getParentName(detailDept) }}</span>
              <n-tag v-else type="warning" size="small">顶级</n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="部门层级">
              <n-tag type="info" size="small" :bordered="false">第 {{ levelMap[detailDept.id] || 1 }} 级</n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="部门负责人">{{ getUserName(detailDept.managerId) || '—' }}</n-descriptions-item>
            <n-descriptions-item label="部门负责人 2">{{ getUserName(detailDept.manager2Id) || '—' }}</n-descriptions-item>
            <n-descriptions-item label="部门 HRBP">{{ getUserName(detailDept.hrbpId) || '—' }}</n-descriptions-item>
            <n-descriptions-item label="分管 VP">{{ getUserName(detailDept.manager3Id) || '—' }}</n-descriptions-item>
            <n-descriptions-item label="状态">
              <n-tag :type="detailDept.status === 'INACTIVE' ? 'default' : 'success'" size="small">
                {{ detailDept.status === 'INACTIVE' ? '停用' : '启用' }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="排序值">{{ detailDept.sortOrder ?? '—' }}</n-descriptions-item>
            <n-descriptions-item label="组织路径">{{ detailDept.path || '—' }}</n-descriptions-item>
            <n-descriptions-item label="创建时间">{{ formatTime(detailDept.createdAt) }}</n-descriptions-item>
            <n-descriptions-item label="更新时间">{{ formatTime(detailDept.updatedAt) }}</n-descriptions-item>
          </n-descriptions>
        </n-drawer-content>
      </n-drawer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch, h } from 'vue';
import {
  AddOutline,
  CreateOutline,
  TrashOutline,
  RefreshOutline,
  PersonOutline,
  SearchOutline,
  ChevronForwardOutline,
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
  NTooltip,
  NDrawer,
  NDrawerContent,
  NDescriptions,
  NDescriptionsItem,
  useMessage,
} from 'naive-ui';
import api from '../../api/auth';

import { extractApiError } from '../../api/dynamic-field'
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

// 详情抽屉（点击部门名称打开，展示完整字段：编号/ID/负责人2/分管VP 等列表隐藏项）
const detailVisible = ref(false);
const detailDept = ref<Department | null>(null);
const openDetail = (row: Department) => {
  detailDept.value = row;
  detailVisible.value = true;
};

// 树形表格展开状态：default-expand-all 对异步加载的数据不生效（仅首次挂载读取），
// 改为受控 expanded-keys，数据到达后默认展开所有含子部门的节点
const expandedKeys = ref<string[]>([]);
watch(departments, (list) => {
  const parentIds = new Set<string>();
  for (const d of list) {
    if (d.parentId) parentIds.add(d.parentId);
  }
  expandedKeys.value = Array.from(parentIds);
});

// 启用/停用筛选：ALL=全部 / ACTIVE=启用 / INACTIVE=停用
const statusFilter = ref<'ALL' | 'ACTIVE' | 'INACTIVE'>('ALL');

// 启用/停用筛选变化即重新拉取
watch(statusFilter, () => loadDepartments());

// 部门层级：根据 parentId 链计算深度（顶级部门 = 第 1 级）
const levelMap = computed<Record<string, number>>(() => {
  const map: Record<string, number> = {};
  const byId = new Map(departments.value.map((d) => [d.id, d]));
  for (const d of departments.value) {
    let level = 1;
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

// 表格展示数据：默认按 parentId 组树形（children 空时置 undefined，避免出现空展开箭头）；
// 搜索时退化为平铺过滤列表，保证命中任意层级部门
const displayData = computed(() => {
  if (searchKeyword.value.trim()) return filteredDepartments.value;
  const buildTree = (parentId: string | null): any[] => {
    const children = departments.value
      .filter(d => (d.parentId || null) === parentId)
      .sort((a, b) => (a.sortOrder || 0) - (b.sortOrder || 0));
    return children
      .map(d => {
        const kids = buildTree(d.id);
        return kids.length ? { ...d, children: kids } : { ...d };
      });
  };
  return buildTree(null);
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

// 打开「添加下级」弹窗：复用新建弹窗并预置上级为该部门
const openCreateChildModal = (parent: Department) => {
  openCreateModal();
  if (parent) formState.parentId = parent.id;
};

// 打开编辑弹窗（查看详情与编辑合一：同一弹窗内展示并可改）
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

// 详情抽屉用：父级名称字符串
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

const columns = computed(() => [
  {
    title: '部门名称',
    key: 'name',
    width: 200,
    render: (row: Department) =>
      h(
        NButton,
        { text: true, type: 'primary', size: 'small', onClick: () => openDetail(row) },
        {
          default: () => row.name,
          icon: () => h(NIcon, { component: ChevronForwardOutline }),
        }
      ),
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
      const lvl = levelMap.value[row.id] || 1;
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
    title: '状态',
    key: 'status',
    width: 90,
    render: (row: Department) => {
      // 后端 status 现已由 is_active 反推为 'ACTIVE'/'INACTIVE' 输出；
      // 保留 isActive 兜底以防旧缓存
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
    width: 260,
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

/* 去掉部门树形表格左侧的展开箭头：保留层级缩进，仅隐藏展开三角 */
:deep(.n-data-table-expand-trigger) {
  display: none !important;
}
</style>
