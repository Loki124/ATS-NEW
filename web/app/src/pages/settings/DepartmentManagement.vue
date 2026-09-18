<template>
  <div class="page-container">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">组织管理</h1>
          <p class="page-subtitle">维护组织架构与部门职责，作为管控与权限的归属单元</p>
        </div>
        <div class="page-header-actions">
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
          <n-button tertiary @click="loadDepartments">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            刷新
          </n-button>
          <n-button type="primary" class="gradient-btn" @click="openCreateModal">
            <template #icon><n-icon :component="AddOutline" /></template>
            新建部门
          </n-button>
        </div>
      </div>

      <div class="org-layout">
        <!-- 左侧：部门树 -->
        <n-card class="org-tree-card" :bordered="false">
          <div class="org-tree-head">
            <span class="org-tree-title">组织架构</span>
            <span class="org-tree-count">{{ departments.length }} 个部门</span>
          </div>
          <div class="org-tree-body">
            <n-tree
              v-if="treeOptions.length"
              block-line
              :data="treeOptions"
              :expanded-keys="expandedKeys"
              :selected-keys="selectedKeys"
              :render-label="renderTreeNode"
              :render-suffix="renderTreeSuffix"
              :on-update:expanded-keys="onExpandedKeys"
              @update:selected-keys="onTreeSelect"
            />
            <n-empty v-else description="暂无部门数据" />
          </div>
        </n-card>

        <!-- 右侧：未选中时的占位提示 -->
        <div v-if="!drawerVisible" class="org-detail-placeholder">
          <n-empty description="从左侧组织架构中选择部门查看详情" />
        </div>
      </div>

      <!-- 右侧：部门详情抽屉 -->
      <n-drawer v-model:show="drawerVisible" :width="440" placement="right">
        <n-drawer-content :title="selectedDept?.name || '部门详情'" :native-scrollbar="false">
          <template v-if="selectedDept">
            <n-descriptions :column="1" label-placement="left" bordered size="small">
              <n-descriptions-item label="部门编号">{{ selectedDept.code }}</n-descriptions-item>
              <n-descriptions-item label="部门名称">{{ selectedDept.name }}</n-descriptions-item>
              <n-descriptions-item label="上级部门">{{ parentName(selectedDept) }}</n-descriptions-item>
              <n-descriptions-item label="状态">
                <n-tag :type="selectedDept.status === 'ACTIVE' ? 'success' : 'default'" size="small">
                  {{ selectedDept.status === 'ACTIVE' ? '启用' : '停用' }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="排序值">{{ selectedDept.sortOrder ?? 0 }}</n-descriptions-item>
            </n-descriptions>

            <div class="detail-section-title">人员配置</div>
            <n-descriptions :column="1" label-placement="left" bordered size="small">
              <n-descriptions-item label="部门负责人">{{ getUserName(selectedDept.managerId) || '—' }}</n-descriptions-item>
              <n-descriptions-item label="部门负责人 2">{{ getUserName(selectedDept.manager2Id) || '—' }}</n-descriptions-item>
              <n-descriptions-item label="部门 HRBP">{{ getUserName(selectedDept.hrbpId) || '—' }}</n-descriptions-item>
              <n-descriptions-item label="分管 VP">{{ getUserName(selectedDept.manager3Id) || '—' }}</n-descriptions-item>
            </n-descriptions>
          </template>

          <template #footer>
            <n-space justify="end" :size="12">
              <n-button tertiary @click="openCreateChildModal(selectedDept)">
                <template #icon><n-icon :component="AddOutline" /></template>
                新增子部门
              </n-button>
              <n-popconfirm
                positive-text="确认删除"
                negative-text="取消"
                @positive-click="() => handleDelete(selectedDept)"
              >
                <template #trigger>
                  <n-button tertiary type="error">
                    <template #icon><n-icon :component="TrashOutline" /></template>
                    删除
                  </n-button>
                </template>
                确认删除部门「{{ selectedDept?.name }}」？删除后将影响其下子部门与人员归属。
              </n-popconfirm>
              <n-button @click="openEditModal(selectedDept)">
                <template #icon><n-icon :component="CreateOutline" /></template>
                编辑
              </n-button>
            </n-space>
          </template>
        </n-drawer-content>
      </n-drawer>

      <!-- 部门编辑弹窗 -->
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, h, watch } from 'vue';
import {
  AddOutline,
  CreateOutline,
  TrashOutline,
  RefreshOutline,
  SearchOutline,
  PeopleOutline,
} from '@vicons/ionicons5';
import {
  NTag,
  NButton,
  NSpace,
  NIcon,
  NPopconfirm,
  NTree,
  NEmpty,
  NCard,
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
  NDivider,
  NDrawer,
  NDrawerContent,
  NDescriptions,
  NDescriptionsItem,
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

const drawerVisible = ref(false);
const selectedDept = ref<Department | null>(null);

const expandedKeys = ref<Array<string | number>>([]);

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

const getUserName = (userId?: string | null) => {
  if (!userId) return null;
  const user = users.value.find(u => String(u.id) === String(userId));
  return user ? user.realName || user.username : null;
};

const parentName = (dept: Department) => {
  if (!dept.parentId) return '顶级部门';
  const parent = departments.value.find(d => String(d.id) === String(dept.parentId));
  return parent ? `${parent.name}（${parent.code}）` : '—';
};

// 部门树（支持按关键字过滤：命中节点或其子孙者保留）
const treeOptions = computed(() => buildTree(departments.value, searchKeyword.value));

function buildTree(list: Department[], keyword: string): any[] {
  const kw = keyword.trim().toLowerCase();
  const map = new Map<string, any>();
  list.forEach(d =>
    map.set(String(d.id), { label: d.name, key: String(d.id), dept: d, children: [] as any[] })
  );
  const roots: any[] = [];
  list.forEach(d => {
    const node = map.get(String(d.id))!;
    const pid = d.parentId ? String(d.parentId) : null;
    if (pid && map.has(pid)) map.get(pid)!.children.push(node);
    else roots.push(node);
  });
  if (!kw) return roots;
  const filterNode = (node: any): any => {
    const children = (node.children || []).map(filterNode).filter(Boolean);
    const selfMatch =
      node.dept.name.toLowerCase().includes(kw) || node.dept.code.toLowerCase().includes(kw);
    if (selfMatch || children.length) return { ...node, children };
    return null;
  };
  return roots.map(filterNode).filter(Boolean);
}

// 搜索时自动展开全部命中节点
function collectKeys(nodes: any[]): string[] {
  const out: string[] = [];
  const walk = (ns: any[]) =>
    ns.forEach(n => {
      out.push(n.key);
      if (n.children?.length) walk(n.children);
    });
  walk(nodes);
  return out;
}
watch(searchKeyword, kw => {
  if (kw.trim()) expandedKeys.value = collectKeys(treeOptions.value);
});

const selectedKeys = computed<string[]>(() =>
  selectedDept.value ? [String(selectedDept.value.id)] : []
);

const onExpandedKeys = (keys: Array<string | number>) => {
  expandedKeys.value = keys;
};

const onTreeSelect = (keys: Array<string | number>) => {
  const id = keys[0];
  if (!id) {
    drawerVisible.value = false;
    selectedDept.value = null;
    return;
  }
  const dept = departments.value.find(d => String(d.id) === String(id)) || null;
  selectedDept.value = dept;
  drawerVisible.value = !!dept;
};

// 树节点 label（图标 + 名称 + 停用标记）
const renderTreeNode = ({ option }: any) => {
  return h('div', { class: 'tree-label' }, [
    h(NIcon, { component: PeopleOutline, class: 'tree-label-icon' }),
    h('span', { class: 'tree-label-text' }, option.label),
    option.dept?.status === 'INACTIVE'
      ? h(NTag, { size: 'tiny', type: 'default', bordered: false }, { default: () => '停用' })
      : null,
  ]);
};

// 树节点后缀操作（悬停显隐：新增子部门 / 编辑 / 删除）
const renderTreeSuffix = ({ option }: any) => {
  const dept = option.dept;
  return h('span', { class: 'tree-actions' }, [
    h(
      NButton,
      {
        text: true,
        type: 'primary',
        size: 'tiny',
        title: '新增子部门',
        onClick: (e: MouseEvent) => {
          e.stopPropagation();
          openCreateChildModal(dept);
        },
      },
      { default: () => '', icon: () => h(NIcon, { component: AddOutline }) }
    ),
    h(
      NButton,
      {
        text: true,
        type: 'primary',
        size: 'tiny',
        title: '编辑',
        onClick: (e: MouseEvent) => {
          e.stopPropagation();
          openEditModal(dept);
        },
      },
      { default: () => '', icon: () => h(NIcon, { component: CreateOutline }) }
    ),
    h(
      NPopconfirm,
      {
        positiveText: '确认',
        negativeText: '取消',
        onPositiveClick: (e: MouseEvent) => {
          e?.stopPropagation?.();
          handleDelete(dept);
        },
      },
      {
        default: () => '确认删除该部门？',
        trigger: () =>
          h(
            NButton,
            {
              text: true,
              type: 'error',
              size: 'tiny',
              title: '删除',
              onClick: (e: MouseEvent) => e.stopPropagation(),
            },
            { default: () => '', icon: () => h(NIcon, { component: TrashOutline }) }
          ),
      }
    ),
  ]);
};

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
  if (!editingDept.value) return false;
  return isDescendantOrSelf(id, editingDept.value.id);
};

// 打开新建弹窗（顶级）
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

// 打开新建子部门弹窗（预设上级）
const openCreateChildModal = (dept: Department | null) => {
  openCreateModal();
  if (dept) formState.parentId = dept.id;
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
        await loadDepartments();
        // 若抽屉打开的是被编辑部门，刷新详情
        if (selectedDept.value && selectedDept.value.id === editingDept.value.id) {
          selectedDept.value =
            departments.value.find(d => d.id === selectedDept.value!.id) || selectedDept.value;
        }
      } else {
        message.error(extractErrorMessage(res.data) || '更新失败');
      }
    } else {
      const res = await api.post('/departments/', payload);
      if (res.status === 201 || res.data?.success === true) {
        message.success('部门创建成功');
        closeDeptModal();
        await loadDepartments();
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
const handleDelete = async (record: Department | null) => {
  if (!record) return;
  try {
    const res = await api.delete(`/departments/${record.id}/`);
    if (res.data?.success) {
      message.success('部门删除成功');
      if (selectedDept.value && String(selectedDept.value.id) === String(record.id)) {
        drawerVisible.value = false;
        selectedDept.value = null;
      }
      loadDepartments();
    } else {
      message.error(res.data?.error || res.data?.message || '删除失败');
    }
  } catch (error: any) {
    message.error(error.response?.data?.error || error.response?.data?.message || '删除失败');
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

/* 左树 + 右详情布局 */
.org-layout {
  display: flex;
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
}
.org-tree-card {
  width: 360px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--glass-bg-elevated);
}
.org-tree-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 4px 12px;
}
.org-tree-title {
  font-weight: 600;
  color: var(--ink);
  font-size: var(--fs-15);
}
.org-tree-count {
  font-size: 12px;
  color: var(--ink-faint);
}
.org-tree-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
}
.org-detail-placeholder {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--border-hairline);
  border-radius: var(--radius-lg);
  background: var(--glass-bg-subtle);
}
.detail-section-title {
  margin: 20px 0 12px;
  font-weight: 600;
  color: var(--ink);
  font-size: var(--fs-14);
}

/* 树节点 label / 悬停操作按钮（render 函数节点需经 :deep 命中） */
.org-tree-body :deep(.tree-label) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.org-tree-body :deep(.tree-label-icon) {
  color: var(--ink-soft);
}
.org-tree-body :deep(.tree-actions) {
  display: inline-flex;
  gap: 2px;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.15s var(--ease-out);
}
.org-tree-body :deep(.n-tree-node-content:hover .tree-actions) {
  opacity: 1;
  visibility: visible;
}
.org-tree-body :deep(.tree-actions .n-button) {
  padding: 2px 4px;
}
</style>
