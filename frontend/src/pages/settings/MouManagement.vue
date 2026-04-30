<template>
  <div class="permission-management">
    <a-tabs v-model:activeKey="activeTab" default-active-key="mou">
      <!-- MOU 管理 Tab -->
      <a-tab-pane key="mou">
        <template #tab>
          <span><TeamOutlined /> MOU管理</span>
        </template>
        <a-card title="管理单元 (MOU) 列表">
          <template #extra>
            <a-button type="primary" @click="handleAddMou">
              <template #icon><PlusOutlined /></template>
              新建MOU
            </a-button>
          </template>
          <a-table
            :dataSource="mous"
            :columns="mouColumns"
            row-key="id"
            :loading="loading"
            :pagination="{ pageSize: 10 }"
          />
        </a-card>
      </a-tab-pane>

      <!-- 权限容器 Tab -->
      <a-tab-pane key="container">
        <template #tab>
          <span><DatabaseOutlined /> 权限容器</span>
        </template>
        <a-card title="权限容器列表">
          <template #extra>
            <a-button type="primary" @click="handleAddContainer()">
              <template #icon><PlusOutlined /></template>
              新建容器
            </a-button>
          </template>
          <a-table
            :dataSource="containers"
            :columns="containerColumns"
            row-key="id"
            :pagination="{ pageSize: 10 }"
          />
        </a-card>
      </a-tab-pane>

      <!-- 自动化规则 Tab -->
      <a-tab-pane key="automation">
        <template #tab>
          <span><RocketOutlined /> 自动化规则</span>
        </template>
        <a-card title="自动化权限规则">
          <template #extra>
            <a-button type="primary" @click="handleAddRule">
              <template #icon><PlusOutlined /></template>
              新建规则
            </a-button>
          </template>
          <a-table
            :dataSource="automationRules"
            :columns="ruleColumns"
            row-key="id"
            :pagination="{ pageSize: 10 }"
          />
        </a-card>
      </a-tab-pane>

      <!-- 互斥组 Tab -->
      <a-tab-pane key="mutex">
        <template #tab>
          <span><ExclamationCircleOutlined /> 互斥组</span>
        </template>
        <a-card title="角色互斥组">
          <template #extra>
            <a-button type="primary" @click="handleAddMutex">
              <template #icon><PlusOutlined /></template>
              新建互斥组
            </a-button>
          </template>
          <a-table
            :dataSource="mutexGroups"
            :columns="mutexColumns"
            row-key="id"
            :pagination="{ pageSize: 10 }"
          />
        </a-card>
      </a-tab-pane>

      <!-- 审计日志 Tab -->
      <a-tab-pane key="audit">
        <template #tab>
          <span><HistoryOutlined /> 审计日志</span>
        </template>
        <a-card title="权限变更审计日志">
          <div class="audit-filters" style="margin-bottom: 16px">
            <a-space>
              <a-range-picker @change="handleDateChange" />
              <a-select placeholder="操作类型" style="width: 120px" allow-clear @change="handleActionChange">
                <a-select-option value="CREATE">创建</a-select-option>
                <a-select-option value="UPDATE">更新</a-select-option>
                <a-select-option value="DELETE">删除</a-select-option>
                <a-select-option value="ASSIGN">分配</a-select-option>
                <a-select-option value="UNASSIGN">取消分配</a-select-option>
              </a-select>
              <a-select placeholder="目标类型" style="width: 120px" allow-clear @change="handleTargetTypeChange">
                <a-select-option value="MOU">MOU</a-select-option>
                <a-select-option value="CONTAINER">容器</a-select-option>
                <a-select-option value="ROLE">角色</a-select-option>
                <a-select-option value="USER">用户</a-select-option>
              </a-select>
              <a-button type="primary" @click="loadAuditLogs">查询</a-button>
            </a-space>
          </div>
          <a-table
            :dataSource="auditLogs"
            :columns="auditColumns"
            row-key="id"
            :loading="auditLoading"
            :pagination="{ pageSize: 10 }"
          />
        </a-card>
      </a-tab-pane>
    </a-tabs>

    <!-- MOU 表单弹窗 -->
    <a-modal
      :open="mouModalVisible"
      :title="editingMou ? '编辑MOU' : '新建MOU'"
      @ok="handleSaveMou"
      @cancel="mouModalVisible = false"
      :width="500"
    >
      <a-form :model="mouFormState" layout="vertical">
        <a-form-item label="MOU名称" name="name" :rules="[{ required: true }]">
          <a-input v-model:value="mouFormState.name" placeholder="请输入MOU名称" />
        </a-form-item>
        <a-form-item label="MOU编码" name="code" :rules="[{ required: true }]">
          <a-input v-model:value="mouFormState.code" placeholder="请输入MOU编码" :disabled="!!editingMou" />
        </a-form-item>
        <a-form-item label="MOU类型" name="mouType" :rules="[{ required: true }]">
          <a-select v-model:value="mouFormState.mouType" placeholder="请选择MOU类型">
            <a-select-option value="DEPARTMENT">部门</a-select-option>
            <a-select-option value="PROJECT">项目</a-select-option>
            <a-select-option value="CUSTOM">自定义</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="权限范围" name="scope">
          <a-input v-model:value="mouFormState.scope" placeholder="如：全部、部门、自定义" />
        </a-form-item>
        <a-form-item label="描述" name="description">
          <a-textarea v-model:value="mouFormState.description" :rows="3" placeholder="请输入MOU描述" />
        </a-form-item>
        <a-form-item label="状态" name="status">
          <a-select v-model:value="mouFormState.status">
            <a-select-option value="ACTIVE">启用</a-select-option>
            <a-select-option value="INACTIVE">停用</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- Container 表单弹窗 -->
    <a-modal
      :open="containerModalVisible"
      :title="editingContainer ? '编辑容器' : '新建容器'"
      @ok="handleSaveContainer"
      @cancel="containerModalVisible = false"
      :width="500"
    >
      <a-form :model="containerFormState" layout="vertical">
        <a-form-item label="容器名称" name="name" :rules="[{ required: true }]">
          <a-input v-model:value="containerFormState.name" placeholder="请输入容器名称" />
        </a-form-item>
        <a-form-item label="容器编码" name="code" :rules="[{ required: true }]">
          <a-input v-model:value="containerFormState.code" placeholder="请输入容器编码" :disabled="!!editingContainer" />
        </a-form-item>
        <a-form-item label="所属MOU" name="mouId" :rules="[{ required: true }]">
          <a-select v-model:value="containerFormState.mouId" placeholder="请选择MOU">
            <a-select-option v-for="m in mous" :key="m.id" :value="m.id">{{ m.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="资源类型" name="resourceType" :rules="[{ required: true }]">
          <a-select v-model:value="containerFormState.resourceType" placeholder="请选择资源类型">
            <a-select-option value="POSITION">职位</a-select-option>
            <a-select-option value="CANDIDATE">候选人</a-select-option>
            <a-select-option value="DEMAND">需求</a-select-option>
            <a-select-option value="INTERVIEW">面试</a-select-option>
            <a-select-option value="OFFER">Offer</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="资源范围" name="resourceScope">
          <a-input v-model:value="containerFormState.resourceScope" placeholder="如：全部、本部门、自定义" />
        </a-form-item>
        <a-form-item label="描述" name="description">
          <a-textarea v-model:value="containerFormState.description" :rows="2" placeholder="请输入容器描述" />
        </a-form-item>
        <a-form-item label="状态" name="status">
          <a-select v-model:value="containerFormState.status">
            <a-select-option value="ACTIVE">启用</a-select-option>
            <a-select-option value="INACTIVE">停用</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 自动化规则表单弹窗 -->
    <a-modal
      :open="ruleModalVisible"
      :title="editingRule ? '编辑规则' : '新建自动化规则'"
      @ok="handleSaveRule"
      @cancel="ruleModalVisible = false"
      :width="600"
    >
      <a-form :model="ruleFormState" layout="vertical">
        <a-form-item label="规则名称" name="name" :rules="[{ required: true }]">
          <a-input v-model:value="ruleFormState.name" placeholder="请输入规则名称" />
        </a-form-item>
        <a-form-item label="规则编码" name="code" :rules="[{ required: true }]">
          <a-input v-model:value="ruleFormState.code" placeholder="请输入规则编码" :disabled="!!editingRule" />
        </a-form-item>
        <a-form-item label="触发类型" name="triggerType" :rules="[{ required: true }]">
          <a-select v-model:value="ruleFormState.triggerType" placeholder="请选择触发类型">
            <a-select-option value="ONBOARDING">入职触发</a-select-option>
            <a-select-option value="ROLE_CHANGE">角色变更</a-select-option>
            <a-select-option value="DEPARTMENT_CHANGE">部门变更</a-select-option>
            <a-select-option value="TIME_TRIGGER">定时触发</a-select-option>
            <a-select-option value="MANUAL">手动触发</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="动作类型" name="actionType" :rules="[{ required: true }]">
          <a-select v-model:value="ruleFormState.actionType" placeholder="请选择动作类型">
            <a-select-option value="ASSIGN_MOU">分配MOU</a-select-option>
            <a-select-option value="ASSIGN_CONTAINER">分配容器</a-select-option>
            <a-select-option value="ASSIGN_ROLE">分配角色</a-select-option>
            <a-select-option value="REVOKE_PERMISSION">撤销权限</a-select-option>
            <a-select-option value="NOTIFY">发送通知</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="优先级" name="priority">
          <a-input-number v-model:value="ruleFormState.priority" placeholder="数值越小优先级越高" />
        </a-form-item>
        <a-form-item label="描述" name="description">
          <a-textarea v-model:value="ruleFormState.description" :rows="2" placeholder="请输入规则描述" />
        </a-form-item>
        <a-form-item label="状态" name="status">
          <a-select v-model:value="ruleFormState.status">
            <a-select-option value="ACTIVE">启用</a-select-option>
            <a-select-option value="INACTIVE">停用</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 互斥组表单弹窗 -->
    <a-modal
      :open="mutexModalVisible"
      :title="editingMutex ? '编辑互斥组' : '新建互斥组'"
      @ok="handleSaveMutex"
      @cancel="mutexModalVisible = false"
      :width="500"
    >
      <a-form :model="mutexFormState" layout="vertical">
        <a-form-item label="互斥组名称" name="name" :rules="[{ required: true }]">
          <a-input v-model:value="mutexFormState.name" placeholder="请输入互斥组名称" />
        </a-form-item>
        <a-form-item label="互斥组编码" name="code" :rules="[{ required: true }]">
          <a-input v-model:value="mutexFormState.code" placeholder="请输入互斥组编码" :disabled="!!editingMutex" />
        </a-form-item>
        <a-form-item label="所属MOU" name="mouId" :rules="[{ required: true }]">
          <a-select v-model:value="mutexFormState.mouId" placeholder="请选择MOU">
            <a-select-option v-for="m in mous" :key="m.id" :value="m.id">{{ m.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="最大角色数" name="maxRoles">
          <a-input-number v-model:value="mutexFormState.maxRoles" :min="1" />
        </a-form-item>
        <a-form-item label="描述" name="description">
          <a-textarea v-model:value="mutexFormState.description" :rows="2" placeholder="请输入互斥组描述" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import { message } from 'ant-design-vue'
import {
  PlusOutlined, TeamOutlined, DatabaseOutlined, RocketOutlined, 
  HistoryOutlined, ExclamationCircleOutlined
} from '@ant-design/icons-vue'

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
  status: string
  createdAt: string
  updatedAt: string
}

interface AutomationRule {
  id: string
  name: string
  code: string
  description?: string
  triggerType: string
  eventType?: string
  triggerConfig?: any
  actionType: string
  actionConfig?: any
  conditions?: any[]
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

const containerFormState = reactive({
  name: '',
  code: '',
  mouId: '',
  description: '',
  resourceType: '',
  resourceScope: '',
  status: 'ACTIVE'
})

// Automation 规则状态
const automationRules = ref<AutomationRule[]>([])
const ruleModalVisible = ref(false)
const editingRule = ref<AutomationRule | null>(null)

const ruleFormState = reactive({
  name: '',
  code: '',
  triggerType: '',
  actionType: '',
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

// 表格列定义
const mouColumns = [
  { title: 'MOU名称', dataIndex: 'name', key: 'name', width: 150 },
  { title: '编码', dataIndex: 'code', key: 'code', width: 120 },
  { title: '类型', dataIndex: 'type', key: 'type', width: 100,
    customRender: ({ text }: { text: string }) => h('a-tag', { color: text === 'DEPARTMENT' ? 'blue' : text === 'PROJECT' ? 'green' : 'orange' },
      text === 'DEPARTMENT' ? '部门' : text === 'PROJECT' ? '项目' : '自定义')
  },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '用户数', dataIndex: 'userCount', key: 'userCount', width: 80,
    customRender: ({ text }: { text: number }) => text || 0
  },
  { title: '状态', dataIndex: 'status', key: 'status', width: 80,
    customRender: ({ text }: { text: string }) => h('a-badge', { status: text === 'ACTIVE' ? 'success' : 'default', text: text === 'ACTIVE' ? '启用' : '停用' })
  },
  { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', width: 160,
    customRender: ({ text }: { text: string }) => text ? new Date(text).toLocaleString('zh-CN') : '-'
  },
  { title: '操作', key: 'action', width: 280,
    customRender: ({ record }: { record: Mou }) => {
      return h('a-space', { size: 'small' }, {
        default: () => [
          h('a-button', { size: 'small', type: 'link', onClick: () => handleBindUsers(record.id) }, '绑定用户'),
          h('a-button', { size: 'small', type: 'link', onClick: () => handleAddContainer(record.id) }, '添加容器'),
          h('a-button', { size: 'small', type: 'link', onClick: () => handleEditMou(record) }, '编辑'),
          h('a-popconfirm', { title: '确认删除此MOU？', onConfirm: () => handleDeleteMou(record), okText: '确认', cancelText: '取消' },
            h('a-button', { size: 'small', type: 'link', danger: true }, '删除'))
        ]
      })
    }
  }
]

const containerColumns = [
  { title: '容器名称', dataIndex: 'name', key: 'name', width: 150 },
  { title: '编码', dataIndex: 'code', key: 'code', width: 120 },
  { title: 'MOU', dataIndex: 'mouId', key: 'mouId', width: 120,
    customRender: ({ text }: { text: string }) => mous.value.find(m => m.id === text)?.name || text
  },
  { title: '资源类型', dataIndex: 'type', key: 'type', width: 120,
    customRender: ({ text }: { text: string }) => h('a-tag', { color: 'blue' }, text)
  },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '状态', dataIndex: 'status', key: 'status', width: 80,
    customRender: ({ text }: { text: string }) => h('a-badge', { status: text === 'ACTIVE' ? 'success' : 'default', text: text === 'ACTIVE' ? '启用' : '停用' })
  },
  { title: '操作', key: 'action', width: 150,
    customRender: ({ record }: { record: PermissionContainer }) => {
      return h('a-space', { size: 'small' }, {
        default: () => [
          h('a-button', { size: 'small', type: 'link', onClick: () => handleEditContainer(record) }, '编辑'),
          h('a-popconfirm', { title: '确认删除此容器？', onConfirm: () => handleDeleteContainer(record), okText: '确认', cancelText: '取消' },
            h('a-button', { size: 'small', type: 'link', danger: true }, '删除'))
        ]
      })
    }
  }
]

const ruleColumns = [
  { title: '规则名称', dataIndex: 'name', key: 'name', width: 180 },
  { title: '编码', dataIndex: 'code', key: 'code', width: 120 },
  { title: '触发类型', dataIndex: 'triggerType', key: 'triggerType', width: 100,
    customRender: ({ text }: { text: string }) => h('a-tag', { color: 'purple' }, text)
  },
  { title: '动作类型', dataIndex: 'actionType', key: 'actionType', width: 100,
    customRender: ({ text }: { text: string }) => h('a-tag', { color: 'cyan' }, text)
  },
  { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '状态', dataIndex: 'status', key: 'status', width: 80,
    customRender: ({ text }: { text: string }) => h('a-badge', { status: text === 'ACTIVE' ? 'success' : 'default', text: text === 'ACTIVE' ? '启用' : '停用' })
  },
  { title: '操作', key: 'action', width: 150,
    customRender: ({ record }: { record: AutomationRule }) => {
      return h('a-space', { size: 'small' }, {
        default: () => [
          h('a-button', { size: 'small', type: 'link', onClick: () => handleEditRule(record) }, '编辑'),
          h('a-popconfirm', { title: '确认删除此规则？', onConfirm: () => handleDeleteRule(record), okText: '确认', cancelText: '取消' },
            h('a-button', { size: 'small', type: 'link', danger: true }, '删除'))
        ]
      })
    }
  }
]

const auditColumns = [
  { title: '时间', dataIndex: 'createdAt', key: 'createdAt', width: 160,
    customRender: ({ text }: { text: string }) => text ? new Date(text).toLocaleString('zh-CN') : '-'
  },
  { title: '操作用户', dataIndex: 'userName', key: 'userName', width: 120 },
  { title: '操作类型', dataIndex: 'action', key: 'action', width: 100,
    customRender: ({ text }: { text: string }) => {
      const colorMap: Record<string, string> = { CREATE: 'green', UPDATE: 'blue', DELETE: 'red', ASSIGN: 'purple', UNASSIGN: 'orange' }
      return h('a-tag', { color: colorMap[text] || 'default' }, text)
    }
  },
  { title: '目标类型', dataIndex: 'targetType', key: 'targetType', width: 100 },
  { title: '目标名称', dataIndex: 'targetName', key: 'targetName', width: 150 },
  { title: 'IP', dataIndex: 'ipAddress', key: 'ipAddress', width: 120 }
]

const mutexColumns = [
  { title: '互斥组名称', dataIndex: 'name', key: 'name', width: 150 },
  { title: '编码', dataIndex: 'code', key: 'code', width: 120 },
  { title: '所属MOU', dataIndex: 'mouId', key: 'mouId', width: 120,
    customRender: ({ text }: { text: string }) => mous.value.find(m => m.id === text)?.name || text
  },
  { title: '最大角色数', dataIndex: 'maxRoles', key: 'maxRoles', width: 100 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '操作', key: 'action', width: 150,
    customRender: ({ record }: { record: MutualExclusionGroup }) => {
      return h('a-space', { size: 'small' }, {
        default: () => [
          h('a-button', { size: 'small', type: 'link', onClick: () => handleEditMutex(record) }, '编辑'),
          h('a-popconfirm', { title: '确认删除此互斥组？', onConfirm: () => handleDeleteMutex(record), okText: '确认', cancelText: '取消' },
            h('a-button', { size: 'small', type: 'link', danger: true }, '删除'))
        ]
      })
    }
  }
]

// 加载 MOU 列表
const loadMous = async () => {
  loading.value = true
  try {
    const response = await fetch('/api/permissions-v2/mou', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    const data = await response.json()
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
    const url = mouId ? `/api/permissions-v2/containers?mouId=${mouId}` : '/api/permissions-v2/containers'
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    const data = await response.json()
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
    const response = await fetch('/api/permissions-v2/automation-rules', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    const data = await response.json()
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
    
    const response = await fetch(`/api/permissions-v2/audit-logs?${params}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    const data = await response.json()
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
    const response = await fetch('/api/permissions-v2/mutual-exclusion-groups', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    const data = await response.json()
    if (data.success) {
      mutexGroups.value = data.data
    }
  } catch (error) {
    message.error('加载互斥组失败')
  }
}

const handleDateChange = (dates: any, dateStrings: string[]) => {
  auditFilters.startDate = dateStrings[0]
  auditFilters.endDate = dateStrings[1]
}

const handleActionChange = (value: string) => {
  auditFilters.action = value
}

const handleTargetTypeChange = (value: string) => {
  auditFilters.targetType = value
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
    const response = await fetch(`/api/permissions-v2/mou/${mou.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    const data = await response.json()
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
    const url = editingMou.value ? `/api/permissions-v2/mou/${editingMou.value.id}` : '/api/permissions-v2/mou'
    const method = editingMou.value ? 'PUT' : 'POST'

    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(mouFormState)
    })
    const data = await response.json()

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
    name: '', code: '', mouId: mouId || '', description: '', resourceType: '', resourceScope: '', status: 'ACTIVE'
  })
  containerModalVisible.value = true
}

const handleEditContainer = (container: PermissionContainer) => {
  editingContainer.value = container
  Object.assign(containerFormState, {
    name: container.name,
    code: container.code,
    mouId: container.mouId,
    description: container.description,
    resourceType: container.type,
    status: container.status
  })
  containerModalVisible.value = true
}

const handleDeleteContainer = async (container: PermissionContainer) => {
  try {
    const response = await fetch(`/api/permissions-v2/containers/${container.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    const data = await response.json()
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
    const url = editingContainer.value ? `/api/permissions-v2/containers/${editingContainer.value.id}` : '/api/permissions-v2/containers'
    const method = editingContainer.value ? 'PUT' : 'POST'

    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(containerFormState)
    })
    const data = await response.json()

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
  Object.assign(ruleFormState, { name: '', code: '', triggerType: '', actionType: '', priority: 0, description: '', status: 'ACTIVE' })
  ruleModalVisible.value = true
}

const handleEditRule = (rule: AutomationRule) => {
  editingRule.value = rule
  Object.assign(ruleFormState, {
    name: rule.name,
    code: rule.code,
    triggerType: rule.eventType,
    priority: rule.priority,
    description: rule.description,
    status: rule.status
  })
  ruleModalVisible.value = true
}

const handleDeleteRule = async (rule: AutomationRule) => {
  try {
    const response = await fetch(`/api/permissions-v2/automation-rules/${rule.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    const data = await response.json()
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
    const url = editingRule.value ? `/api/permissions-v2/automation-rules/${editingRule.value.id}` : '/api/permissions-v2/automation-rules'
    const method = editingRule.value ? 'PUT' : 'POST'

    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(ruleFormState)
    })
    const data = await response.json()

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
    const response = await fetch(`/api/permissions-v2/mutual-exclusion-groups/${mutex.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    const data = await response.json()
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
    const url = editingMutex.value ? `/api/permissions-v2/mutual-exclusion-groups/${editingMutex.value.id}` : '/api/permissions-v2/mutual-exclusion-groups'
    const method = editingMutex.value ? 'PUT' : 'POST'

    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(mutexFormState)
    })
    const data = await response.json()

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
const handleBindUsers = (mouId: string) => {
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
</style>