<template>
  <div class="permission-management">
    <n-tabs v-model:value="activeTab" type="line" default-value="mou">
      <!-- MOU 管理 Tab -->
      <n-tab-pane name="mou">
        <template #tab>
          <span class="tab-label">
            <n-icon :component="PeopleOutline" />
            MOU管理
          </span>
        </template>
        <n-card title="管理单元 (MOU) 列表">
          <template #header-extra>
            <n-button type="primary" @click="handleAddMou">
              <template #icon><n-icon :component="AddOutline" /></template>
              新建MOU
            </n-button>
          </template>
          <n-data-table
            :data="mous"
            :columns="mouColumns"
            :row-key="(row: Mou) => row.id"
            :loading="loading"
            :pagination="{ pageSize: 10 }"
          />
        </n-card>
      </n-tab-pane>

      <!-- 权限容器 Tab -->
      <n-tab-pane name="container">
        <template #tab>
          <span class="tab-label">
            <n-icon :component="ServerOutline" />
            权限容器
          </span>
        </template>
        <n-card title="权限容器列表">
          <template #header-extra>
            <n-button type="primary" @click="handleAddContainer()">
              <template #icon><n-icon :component="AddOutline" /></template>
              新建容器
            </n-button>
          </template>
          <n-data-table
            :data="containers"
            :columns="containerColumns"
            :row-key="(row: PermissionContainer) => row.id"
            :pagination="{ pageSize: 10 }"
          />
        </n-card>
      </n-tab-pane>

      <!-- 自动化规则 Tab -->
      <n-tab-pane name="automation">
        <template #tab>
          <span class="tab-label">
            <n-icon :component="RocketOutline" />
            自动化规则
          </span>
        </template>
        <n-card title="自动化权限规则">
          <template #header-extra>
            <n-button type="primary" @click="handleAddRule">
              <template #icon><n-icon :component="AddOutline" /></template>
              新建规则
            </n-button>
          </template>
          <n-data-table
            :data="automationRules"
            :columns="ruleColumns"
            :row-key="(row: AutomationRule) => row.id"
            :pagination="{ pageSize: 10 }"
          />
        </n-card>
      </n-tab-pane>

      <!-- 互斥组 Tab -->
      <n-tab-pane name="mutex">
        <template #tab>
          <span class="tab-label">
            <n-icon :component="AlertCircleOutline" />
            互斥组
          </span>
        </template>
        <n-card title="角色互斥组">
          <template #header-extra>
            <n-button type="primary" @click="handleAddMutex">
              <template #icon><n-icon :component="AddOutline" /></template>
              新建互斥组
            </n-button>
          </template>
          <n-data-table
            :data="mutexGroups"
            :columns="mutexColumns"
            :row-key="(row: MutualExclusionGroup) => row.id"
            :pagination="{ pageSize: 10 }"
          />
        </n-card>
      </n-tab-pane>

      <!-- 审计日志 Tab -->
      <n-tab-pane name="audit">
        <template #tab>
          <span class="tab-label">
            <n-icon :component="TimeOutline" />
            审计日志
          </span>
        </template>
        <n-card title="权限变更审计日志">
          <div class="audit-filters" style="margin-bottom: 16px">
            <n-space>
              <n-date-picker
                type="daterange"
                clearable
                @update:value="handleDateChange"
              />
              <n-select
                placeholder="操作类型"
                style="width: 120px"
                clearable
                :options="actionOptions"
                @update:value="handleActionChange"
              />
              <n-select
                placeholder="目标类型"
                style="width: 120px"
                clearable
                :options="targetTypeOptions"
                @update:value="handleTargetTypeChange"
              />
              <n-button type="primary" @click="loadAuditLogs">查询</n-button>
            </n-space>
          </div>
          <n-data-table
            :data="auditLogs"
            :columns="auditColumns"
            :row-key="(row: PermissionAuditLog) => row.id"
            :loading="auditLoading"
            :pagination="{ pageSize: 10 }"
          />
        </n-card>
      </n-tab-pane>
    </n-tabs>

    <!-- MOU 表单弹窗 -->
    <n-modal
      v-model:show="mouModalVisible"
      preset="card"
      :title="editingMou ? '编辑MOU' : '新建MOU'"
      :style="{ width: '500px' }"
      :mask-closable="false"
    >
      <n-form :model="mouFormState" label-placement="top">
        <n-form-item label="MOU名称" required>
          <n-input v-model:value="mouFormState.name" placeholder="请输入MOU名称" />
        </n-form-item>
        <n-form-item label="MOU编码" required>
          <n-input v-model:value="mouFormState.code" placeholder="请输入MOU编码" :disabled="!!editingMou" />
        </n-form-item>
        <n-form-item label="MOU类型" required>
          <n-select
            v-model:value="mouFormState.mouType"
            placeholder="请选择MOU类型"
            :options="mouTypeOptions"
          />
        </n-form-item>
        <n-form-item label="权限范围">
          <n-input v-model:value="mouFormState.scope" placeholder="如：全部、部门、自定义" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="mouFormState.description" type="textarea" :rows="3" placeholder="请输入MOU描述" />
        </n-form-item>
        <n-form-item label="状态">
          <n-select
            v-model:value="mouFormState.status"
            :options="statusOptions"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <n-button @click="mouModalVisible = false">取消</n-button>
          <n-button type="primary" @click="handleSaveMou">确定</n-button>
        </div>
      </template>
    </n-modal>

    <!-- Container 表单弹窗 -->
    <n-modal
      v-model:show="containerModalVisible"
      preset="card"
      :title="editingContainer ? '编辑容器' : '新建容器'"
      :style="{ width: '500px' }"
      :mask-closable="false"
    >
      <n-form :model="containerFormState" label-placement="top">
        <n-form-item label="容器名称" required>
          <n-input v-model:value="containerFormState.name" placeholder="请输入容器名称" />
        </n-form-item>
        <n-form-item label="容器编码" required>
          <n-input v-model:value="containerFormState.code" placeholder="请输入容器编码" :disabled="!!editingContainer" />
        </n-form-item>
        <n-form-item label="所属MOU" required>
          <n-select
            v-model:value="containerFormState.mouId"
            placeholder="请选择MOU"
            :options="mouSelectOptions"
          />
        </n-form-item>
        <n-form-item label="容器类型" required>
          <n-select
            v-model:value="containerFormState.type"
            placeholder="请选择容器类型"
            :options="containerTypeOptions"
          />
        </n-form-item>
        <n-form-item label="资源过滤">
          <n-input v-model:value="containerFormState.resourceFilter" type="textarea" placeholder="JSON格式的资源过滤条件" :rows="2" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="containerFormState.description" type="textarea" :rows="2" placeholder="请输入容器描述" />
        </n-form-item>
        <n-form-item label="状态">
          <n-select
            v-model:value="containerFormState.status"
            :options="statusOptions"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <n-button @click="containerModalVisible = false">取消</n-button>
          <n-button type="primary" @click="handleSaveContainer">确定</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 自动化规则表单弹窗 -->
    <n-modal
      v-model:show="ruleModalVisible"
      preset="card"
      :title="editingRule ? '编辑规则' : '新建自动化规则'"
      :style="{ width: '600px' }"
      :mask-closable="false"
    >
      <n-form :model="ruleFormState" label-placement="top">
        <n-form-item label="规则名称" required>
          <n-input v-model:value="ruleFormState.name" placeholder="请输入规则名称" />
        </n-form-item>
        <n-form-item label="规则编码" required>
          <n-input v-model:value="ruleFormState.code" placeholder="请输入规则编码" :disabled="!!editingRule" />
        </n-form-item>
        <n-form-item label="触发事件" required>
          <n-select
            v-model:value="ruleFormState.eventType"
            placeholder="请选择触发事件"
            :options="eventTypeOptions"
          />
        </n-form-item>
        <n-form-item label="动作配置" required>
          <n-input v-model:value="ruleFormState.actions" type="textarea" placeholder='JSON格式动作配置，如：[{"type":"assign_role","role_id":"xxx"}]' :rows="3" />
        </n-form-item>
        <n-form-item label="优先级">
          <n-input-number v-model:value="ruleFormState.priority" placeholder="数值越小优先级越高" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="ruleFormState.description" type="textarea" :rows="2" placeholder="请输入规则描述" />
        </n-form-item>
        <n-form-item label="状态">
          <n-select
            v-model:value="ruleFormState.status"
            :options="statusOptions"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <n-button @click="ruleModalVisible = false">取消</n-button>
          <n-button type="primary" @click="handleSaveRule">确定</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 互斥组表单弹窗 -->
    <n-modal
      v-model:show="mutexModalVisible"
      preset="card"
      :title="editingMutex ? '编辑互斥组' : '新建互斥组'"
      :style="{ width: '500px' }"
      :mask-closable="false"
    >
      <n-form :model="mutexFormState" label-placement="top">
        <n-form-item label="互斥组名称" required>
          <n-input v-model:value="mutexFormState.name" placeholder="请输入互斥组名称" />
        </n-form-item>
        <n-form-item label="互斥组编码" required>
          <n-input v-model:value="mutexFormState.code" placeholder="请输入互斥组编码" :disabled="!!editingMutex" />
        </n-form-item>
        <n-form-item label="所属MOU" required>
          <n-select
            v-model:value="mutexFormState.mouId"
            placeholder="请选择MOU"
            :options="mouSelectOptions"
          />
        </n-form-item>
        <n-form-item label="最大角色数">
          <n-input-number v-model:value="mutexFormState.maxRoles" :min="1" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="mutexFormState.description" type="textarea" :rows="2" placeholder="请输入互斥组描述" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <n-button @click="mutexModalVisible = false">取消</n-button>
          <n-button type="primary" @click="handleSaveMutex">确定</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import api from '../../api/auth';
import { ref, reactive, onMounted, computed, h } from 'vue'
import {
  NTag,
  NBadge,
  NButton,
  NSpace,
  NPopconfirm,
  NIcon,
  useMessage,
} from 'naive-ui'
import {
  AddOutline,
  PeopleOutline,
  ServerOutline,
  RocketOutline,
  TimeOutline,
  AlertCircleOutline,
} from '@vicons/ionicons5'

const message = useMessage()

interface Mou {
  id: string
  name: string
  code: string
  description?: string
  status: string
  type: string
  mouType?: string
  scope?: string
  createdAt: string
  updatedAt: string
  createdBy?: string
  userCount?: number
}

interface PermissionContainer {
  id: string
  name: string
  code: string
  mouId: string
  description?: string
  type: string
  resourceType?: string
  resourceScope?: string
  resourceFilter?: any
  status: string
  createdAt: string
  updatedAt: string
}

interface AutomationRule {
  id: string
  name: string
  code: string
  description?: string
  eventType: string
  triggerType?: string
  actionType?: string
  condition?: any
  actions: string
  priority: number
  status: string
  createdAt: string
  updatedAt: string
  lastTriggered?: string
}

interface PermissionAuditLog {
  id: string
  userId: string
  userName?: string
  action: string
  targetType: string
  targetId: string
  targetName?: string
  changes?: any
  ipAddress?: string
  userAgent?: string
  createdAt: string
}

interface MutualExclusionGroup {
  id: string
  name: string
  code: string
  description?: string
  mouId: string
  maxRoles: number
  createdAt: string
  roles?: any[]
}

const activeTab = ref('mou')

// MOU 管理状态
const mous = ref<Mou[]>([])
const mouModalVisible = ref(false)
const editingMou = ref<Mou | null>(null)
const loading = ref(false)

const mouFormState = reactive({
  name: '',
  code: '',
  mouType: '',
  scope: '',
  description: '',
  status: 'ACTIVE'
})

// Container 管理状态
const containers = ref<PermissionContainer[]>([])
const containerModalVisible = ref(false)
const editingContainer = ref<PermissionContainer | null>(null)

const containerFormState = reactive<{
  name: string
  code: string
  type: string
  mouId: string
  description: string
  resourceFilter: any
  status: string
}>({
  name: '',
  code: '',
  type: '',
  mouId: '',
  description: '',
  resourceFilter: null,
  status: 'ACTIVE'
})

// Automation 规则状态
const automationRules = ref<AutomationRule[]>([])
const ruleModalVisible = ref(false)
const editingRule = ref<AutomationRule | null>(null)

const ruleFormState = reactive({
  name: '',
  code: '',
  eventType: '',
  condition: null,
  actions: '',
  priority: 0,
  description: '',
  status: 'ACTIVE'
})

// 审计日志状态
const auditLogs = ref<PermissionAuditLog[]>([])
const auditLoading = ref(false)
const auditFilters = reactive({
  startDate: '',
  endDate: '',
  action: '',
  targetType: ''
})

// 互斥组状态
const mutexGroups = ref<MutualExclusionGroup[]>([])
const mutexModalVisible = ref(false)
const editingMutex = ref<MutualExclusionGroup | null>(null)

const mutexFormState = reactive({
  name: '',
  code: '',
  mouId: '',
  maxRoles: 2,
  description: ''
})

// 下拉选项
const mouTypeOptions = [
  { label: '部门', value: 'DEPARTMENT' },
  { label: '项目', value: 'PROJECT' },
  { label: '自定义', value: 'CUSTOM' },
]

const containerTypeOptions = [
  { label: '项目', value: 'PROJECT' },
  { label: '部门', value: 'DEPT' },
  { label: '人才库', value: 'TALENT_POOL' },
  { label: '自定义', value: 'CUSTOM' },
]

const eventTypeOptions = [
  { label: '入职触发', value: 'onboarding' },
  { label: '转岗触发', value: 'transfer' },
  { label: '组织变更触发', value: 'org_change' },
  { label: '离职触发', value: 'offboarding' },
]

const statusOptions = [
  { label: '启用', value: 'ACTIVE' },
  { label: '停用', value: 'INACTIVE' },
]

const actionOptions = [
  { label: '创建', value: 'CREATE' },
  { label: '更新', value: 'UPDATE' },
  { label: '删除', value: 'DELETE' },
  { label: '分配', value: 'ASSIGN' },
  { label: '取消分配', value: 'UNASSIGN' },
]

const targetTypeOptions = [
  { label: 'MOU', value: 'MOU' },
  { label: '容器', value: 'CONTAINER' },
  { label: '角色', value: 'ROLE' },
  { label: '用户', value: 'USER' },
]

const mouSelectOptions = computed(() =>
  mous.value.map(m => ({ label: m.name, value: m.id }))
)

// 表格列定义
const mouColumns = [
  { title: 'MOU名称', key: 'name', width: 150 },
  { title: '编码', key: 'code', width: 120 },
  {
    title: '类型', key: 'type', width: 100,
    render: (row: Mou) => h(NTag, { type: row.type === 'DEPARTMENT' ? 'info' : row.type === 'PROJECT' ? 'success' : 'warning', size: 'small' },
      { default: () => row.type === 'DEPARTMENT' ? '部门' : row.type === 'PROJECT' ? '项目' : '自定义' })
  },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '用户数', key: 'userCount', width: 80,
    render: (row: Mou) => row.userCount || 0
  },
  {
    title: '状态', key: 'status', width: 80,
    render: (row: Mou) => h(NBadge, { type: row.status === 'ACTIVE' ? 'success' : 'default' }, {
      default: () => row.status === 'ACTIVE' ? '启用' : '停用'
    })
  },
  {
    title: '创建时间', key: 'createdAt', width: 160,
    render: (row: Mou) => row.createdAt ? new Date(row.createdAt).toLocaleString('zh-CN') : '-'
  },
  {
    title: '操作', key: 'action', width: 280,
    render: (row: Mou) => {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => handleBindUsers(row.id) }, { default: () => '绑定用户' }),
          h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => handleAddContainer(row.id) }, { default: () => '添加容器' }),
          h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => handleEditMou(row) }, { default: () => '编辑' }),
          h(NPopconfirm, {
            onPositiveClick: () => handleDeleteMou(row),
            positiveText: '确认',
            negativeText: '取消',
          }, {
            default: () => '确认删除此MOU？',
            trigger: () => h(NButton, { size: 'small', text: true, type: 'error' }, { default: () => '删除' }),
          })
        ]
      })
    }
  }
]

const containerColumns = [
  { title: '容器名称', key: 'name', width: 150 },
  { title: '编码', key: 'code', width: 120 },
  {
    title: 'MOU', key: 'mouId', width: 120,
    render: (row: PermissionContainer) => mous.value.find(m => m.id === row.mouId)?.name || row.mouId
  },
  {
    title: '资源类型', key: 'type', width: 120,
    render: (row: PermissionContainer) => h(NTag, { type: 'info', size: 'small' }, { default: () => row.type })
  },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '状态', key: 'status', width: 80,
    render: (row: PermissionContainer) => h(NBadge, { type: row.status === 'ACTIVE' ? 'success' : 'default' }, {
      default: () => row.status === 'ACTIVE' ? '启用' : '停用'
    })
  },
  {
    title: '操作', key: 'action', width: 150,
    render: (row: PermissionContainer) => {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => handleEditContainer(row) }, { default: () => '编辑' }),
          h(NPopconfirm, {
            onPositiveClick: () => handleDeleteContainer(row),
            positiveText: '确认',
            negativeText: '取消',
          }, {
            default: () => '确认删除此容器？',
            trigger: () => h(NButton, { size: 'small', text: true, type: 'error' }, { default: () => '删除' }),
          })
        ]
      })
    }
  }
]

const ruleColumns = [
  { title: '规则名称', key: 'name', width: 180 },
  { title: '编码', key: 'code', width: 120 },
  {
    title: '触发类型', key: 'triggerType', width: 100,
    render: (row: AutomationRule) => h(NTag, { type: 'warning', size: 'small' }, { default: () => row.triggerType || '' })
  },
  {
    title: '动作类型', key: 'actionType', width: 100,
    render: (row: AutomationRule) => h(NTag, { type: 'info', size: 'small' }, { default: () => row.actionType || '' })
  },
  { title: '优先级', key: 'priority', width: 80 },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '状态', key: 'status', width: 80,
    render: (row: AutomationRule) => h(NBadge, { type: row.status === 'ACTIVE' ? 'success' : 'default' }, {
      default: () => row.status === 'ACTIVE' ? '启用' : '停用'
    })
  },
  {
    title: '操作', key: 'action', width: 150,
    render: (row: AutomationRule) => {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => handleEditRule(row) }, { default: () => '编辑' }),
          h(NPopconfirm, {
            onPositiveClick: () => handleDeleteRule(row),
            positiveText: '确认',
            negativeText: '取消',
          }, {
            default: () => '确认删除此规则？',
            trigger: () => h(NButton, { size: 'small', text: true, type: 'error' }, { default: () => '删除' }),
          })
        ]
      })
    }
  }
]

const auditColumns = [
  {
    title: '时间', key: 'createdAt', width: 160,
    render: (row: PermissionAuditLog) => row.createdAt ? new Date(row.createdAt).toLocaleString('zh-CN') : '-'
  },
  { title: '操作用户', key: 'userName', width: 120 },
  {
    title: '操作类型', key: 'action', width: 100,
    render: (row: PermissionAuditLog) => {
      const typeMap: Record<string, any> = { CREATE: 'success', UPDATE: 'info', DELETE: 'error', ASSIGN: 'warning', UNASSIGN: 'warning' }
      return h(NTag, { type: typeMap[row.action] || 'default', size: 'small' }, { default: () => row.action })
    }
  },
  { title: '目标类型', key: 'targetType', width: 100 },
  { title: '目标名称', key: 'targetName', width: 150 },
  { title: 'IP', key: 'ipAddress', width: 120 }
]

const mutexColumns = [
  { title: '互斥组名称', key: 'name', width: 150 },
  { title: '编码', key: 'code', width: 120 },
  {
    title: '所属MOU', key: 'mouId', width: 120,
    render: (row: MutualExclusionGroup) => mous.value.find(m => m.id === row.mouId)?.name || row.mouId
  },
  { title: '最大角色数', key: 'maxRoles', width: 100 },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '操作', key: 'action', width: 150,
    render: (row: MutualExclusionGroup) => {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => handleEditMutex(row) }, { default: () => '编辑' }),
          h(NPopconfirm, {
            onPositiveClick: () => handleDeleteMutex(row),
            positiveText: '确认',
            negativeText: '取消',
          }, {
            default: () => '确认删除此互斥组？',
            trigger: () => h(NButton, { size: 'small', text: true, type: 'error' }, { default: () => '删除' }),
          })
        ]
      })
    }
  }
]

// 加载 MOU 列表
const loadMous = async () => {
  loading.value = true
  try {
    const data = (await api.get('/permissions-v2/mou')).data
    if (data.success) {
      mous.value = data.data
    }
  } catch (error) {
    message.error('加载MOU列表失败')
  } finally {
    loading.value = false
  }
}

// 加载 Container 列表
const loadContainers = async (mouId?: string) => {
  try {
    const url = mouId ? `/permissions-v2/containers?mouId=${mouId}` : '/permissions-v2/containers'
    const data = (await api.get(url)).data
    if (data.success) {
      containers.value = data.data
    }
  } catch (error) {
    message.error('加载容器列表失败')
  }
}

// 加载自动化规则
const loadAutomationRules = async () => {
  try {
    const data = (await api.get('/permissions-v2/automation-rules')).data
    if (data.success) {
      automationRules.value = data.data
    }
  } catch (error) {
    message.error('加载自动化规则失败')
  }
}

// 加载审计日志
const loadAuditLogs = async () => {
  auditLoading.value = true
  try {
    const params = new URLSearchParams()
    if (auditFilters.startDate) params.append('startDate', auditFilters.startDate)
    if (auditFilters.endDate) params.append('endDate', auditFilters.endDate)
    if (auditFilters.action) params.append('action', auditFilters.action)
    if (auditFilters.targetType) params.append('targetType', auditFilters.targetType)

    const data = (await api.get(`/permissions-v2/audit-logs?${params}`)).data
    if (data.success) {
      auditLogs.value = data.data
    }
  } catch (error) {
    message.error('加载审计日志失败')
  } finally {
    auditLoading.value = false
  }
}

// 加载互斥组
const loadMutexGroups = async () => {
  try {
    const data = (await api.get('/permissions-v2/mutual-exclusion-groups')).data
    if (data.success) {
      mutexGroups.value = data.data
    }
  } catch (error) {
    message.error('加载互斥组失败')
  }
}

const handleDateChange = (value: [number, number] | null) => {
  if (value && value.length === 2) {
    auditFilters.startDate = new Date(value[0]).toISOString().slice(0, 10)
    auditFilters.endDate = new Date(value[1]).toISOString().slice(0, 10)
  } else {
    auditFilters.startDate = ''
    auditFilters.endDate = ''
  }
}

const handleActionChange = (value: string) => {
  auditFilters.action = value || ''
}

const handleTargetTypeChange = (value: string) => {
  auditFilters.targetType = value || ''
}

// MOU 操作
const handleAddMou = () => {
  editingMou.value = null
  Object.assign(mouFormState, { name: '', code: '', mouType: '', scope: '', description: '', status: 'ACTIVE' })
  mouModalVisible.value = true
}

const handleEditMou = (mou: Mou) => {
  editingMou.value = mou
  Object.assign(mouFormState, {
    name: mou.name,
    code: mou.code,
    mouType: mou.type,
    scope: mou.scope,
    description: mou.description,
    status: mou.status
  })
  mouModalVisible.value = true
}

const handleDeleteMou = async (mou: Mou) => {
  try {
    const data = (await api.delete(`/permissions-v2/mou/${mou.id}`)).data
    if (data.success) {
      message.success('删除成功')
      loadMous()
    } else {
      message.error(data.error || '删除失败')
    }
  } catch (error) {
    message.error('删除失败')
  }
}

const handleSaveMou = async () => {
  try {
    const url = editingMou.value ? `/permissions-v2/mou/${editingMou.value.id}` : '/permissions-v2/mou'
    const method = editingMou.value ? 'PUT' : 'POST'

    const data = (await (api as any)[method.toLowerCase()](url, mouFormState)).data

    if (data.success) {
      message.success(editingMou.value ? '更新成功' : '创建成功')
      mouModalVisible.value = false
      loadMous()
    } else {
      message.error(data.error || '操作失败')
    }
  } catch (error) {
    console.error(error)
  }
}

// Container 操作
const handleAddContainer = (mouId?: string) => {
  editingContainer.value = null
  Object.assign(containerFormState, {
    name: '', code: '', type: '', mouId: mouId || '', description: '', resourceFilter: null, status: 'ACTIVE'
  })
  containerModalVisible.value = true
}

const handleEditContainer = (container: PermissionContainer) => {
  editingContainer.value = container
  Object.assign(containerFormState, {
    name: container.name,
    code: container.code,
    type: container.type,
    mouId: container.mouId,
    description: container.description,
    resourceFilter: container.resourceFilter,
    status: container.status
  })
  containerModalVisible.value = true
}

const handleDeleteContainer = async (container: PermissionContainer) => {
  try {
    const data = (await api.delete(`/permissions-v2/containers/${container.id}`)).data
    if (data.success) {
      message.success('删除成功')
      loadContainers()
    } else {
      message.error(data.error || '删除失败')
    }
  } catch (error) {
    message.error('删除失败')
  }
}

const handleSaveContainer = async () => {
  try {
    const url = editingContainer.value ? `/permissions-v2/containers/${editingContainer.value.id}` : '/permissions-v2/containers'
    const method = editingContainer.value ? 'PUT' : 'POST'

    const data = (await (api as any)[method.toLowerCase()](url, containerFormState)).data

    if (data.success) {
      message.success(editingContainer.value ? '更新成功' : '创建成功')
      containerModalVisible.value = false
      loadContainers()
    } else {
      message.error(data.error || '操作失败')
    }
  } catch (error) {
    console.error(error)
  }
}

// Automation 规则操作
const handleAddRule = () => {
  editingRule.value = null
  Object.assign(ruleFormState, { name: '', code: '', eventType: '', condition: null, actions: '', priority: 0, description: '', status: 'ACTIVE' })
  ruleModalVisible.value = true
}

const handleEditRule = (rule: AutomationRule) => {
  editingRule.value = rule
  Object.assign(ruleFormState, {
    name: rule.name,
    code: rule.code,
    eventType: rule.eventType,
    condition: rule.condition,
    actions: rule.actions,
    priority: rule.priority,
    description: rule.description,
    status: rule.status
  })
  ruleModalVisible.value = true
}

const handleDeleteRule = async (rule: AutomationRule) => {
  try {
    const data = (await api.delete(`/permissions-v2/automation-rules/${rule.id}`)).data
    if (data.success) {
      message.success('删除成功')
      loadAutomationRules()
    } else {
      message.error(data.error || '删除失败')
    }
  } catch (error) {
    message.error('删除失败')
  }
}

const handleSaveRule = async () => {
  try {
    const url = editingRule.value ? `/permissions-v2/automation-rules/${editingRule.value.id}` : '/permissions-v2/automation-rules'
    const method = editingRule.value ? 'PUT' : 'POST'

    const data = (await (api as any)[method.toLowerCase()](url, ruleFormState)).data

    if (data.success) {
      message.success(editingRule.value ? '更新成功' : '创建成功')
      ruleModalVisible.value = false
      loadAutomationRules()
    } else {
      message.error(data.error || '操作失败')
    }
  } catch (error) {
    console.error(error)
  }
}

// 互斥组操作
const handleAddMutex = () => {
  editingMutex.value = null
  Object.assign(mutexFormState, { name: '', code: '', mouId: '', maxRoles: 2, description: '' })
  mutexModalVisible.value = true
}

const handleEditMutex = (mutex: MutualExclusionGroup) => {
  editingMutex.value = mutex
  Object.assign(mutexFormState, {
    name: mutex.name,
    code: mutex.code,
    mouId: mutex.mouId,
    maxRoles: mutex.maxRoles,
    description: mutex.description
  })
  mutexModalVisible.value = true
}

const handleDeleteMutex = async (mutex: MutualExclusionGroup) => {
  try {
    const data = (await api.delete(`/permissions-v2/mutual-exclusion-groups/${mutex.id}`)).data
    if (data.success) {
      message.success('删除成功')
      loadMutexGroups()
    } else {
      message.error(data.error || '删除失败')
    }
  } catch (error) {
    message.error('删除失败')
  }
}

const handleSaveMutex = async () => {
  try {
    const url = editingMutex.value ? `/permissions-v2/mutual-exclusion-groups/${editingMutex.value.id}` : '/permissions-v2/mutual-exclusion-groups'
    const method = editingMutex.value ? 'PUT' : 'POST'

    const data = (await (api as any)[method.toLowerCase()](url, mutexFormState)).data

    if (data.success) {
      message.success(editingMutex.value ? '更新成功' : '创建成功')
      mutexModalVisible.value = false
      loadMutexGroups()
    } else {
      message.error(data.error || '操作失败')
    }
  } catch (error) {
    console.error(error)
  }
}

// 用户绑定 MOU (简化)
const handleBindUsers = (_mouId: string) => {
  message.info('绑定用户功能开发中')
}

onMounted(() => {
  loadMous()
  loadContainers()
  loadAutomationRules()
  loadAuditLogs()
  loadMutexGroups()
})
</script>

<style scoped>
.permission-management {
  padding: 24px;
}
.page-header {
  margin-bottom: 24px;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}
.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
</style>
