<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">账号设置</h1>
    </div>
    
    <a-tabs v-model:activeKey="activeTab" default-active-key="profile">
      <a-tab-pane key="profile">
        <template #tab>
          <span><UserOutlined /> 基本信息</span>
        </template>
        <a-card title="个人信息">
          <a-form :model="formState" :label-col="{ span: 4 }" :wrapper-col="{ span: 18 }">
            <a-row :gutter="24">
              <a-col :span="12">
                <a-form-item label="用户名">
                  <a-input v-model:value="formState.username" disabled />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="真实姓名" name="realName">
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
            <a-divider />
            <a-row :gutter="24">
              <a-col :span="12">
                <a-form-item label="新密码">
                  <a-input-password v-model:value="formState.newPassword" placeholder="请输入新密码（不修改请留空）" />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="确认密码">
                  <a-input-password v-model:value="formState.confirmPassword" placeholder="请再次输入密码" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-space>
              <a-button type="primary" @click="handleSaveProfile">保存</a-button>
              <a-button @click="handleReset">重置</a-button>
            </a-space>
          </a-form>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="roles">
        <template #tab>
          <span><SafetyOutlined /> 角色分配</span>
        </template>
        <a-card 
          :title="'我的角色'"
        >
          <template #extra>
            <a-button type="primary" @click="showRoleModal = true">分配角色</a-button>
          </template>
          <template v-if="userRoles.length > 0">
            <a-space size="large" wrap>
              <a-tag v-for="roleId in userRoles" :key="roleId" color="blue" style="padding: 8px 16px; font-size: 14px">
                {{ getRoleName(roleId) }}
              </a-tag>
            </a-space>
          </template>
          <a-empty v-else description="暂未分配角色" />
          
          <a-divider />
          
          <h4 style="margin-bottom: 16px">可选角色列表</h4>
          <a-table
            :dataSource="roles"
            :columns="roleColumns"
            row-key="id"
            :size="'small'"
            :pagination="{ pageSize: 5 }"
            :row-selection="{ type: 'checkbox', selectedRowKeys: userRoles, onChange: handleRoleSelectChange }"
          />
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="menus">
        <template #tab>
          <span><LockOutlined /> 菜单权限</span>
        </template>
        <a-card title="可访问的菜单">
          <template v-if="myPermissions.menus && myPermissions.menus.length > 0">
            <a-row :gutter="[16, 16]">
              <a-col :span="6" v-for="menu in myPermissions.menus" :key="menu.id">
                <a-card size="small" style="background: #f5f5f5">
                  <a-space>
                    <span style="font-size: 16px">📁</span>
                    <span>{{ menu.name }}</span>
                  </a-space>
                  <a-tag v-if="menu.resource" color="blue" style="margin-left: 8px">{{ menu.resource }}</a-tag>
                </a-card>
              </a-col>
            </a-row>
          </template>
          <a-empty v-else description="暂无可访问的菜单" />
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="functions">
        <template #tab>
          <span><KeyOutlined /> 功能权限</span>
        </template>
        <a-card title="可执行的操作">
          <template v-if="myPermissions.functions && myPermissions.functions.length > 0">
            <a-row :gutter="[12, 12]">
              <a-col :span="8" v-for="func in myPermissions.functions" :key="func.id">
                <a-card size="small" style="background: #f0f5ff">
                  <a-space direction="vertical" :size="4">
                    <strong>{{ func.name }}</strong>
                    <a-space>
                      <a-tag color="green">{{ func.action || '*' }}</a-tag>
                      <a-tag v-if="func.resource" color="blue">{{ func.resource }}</a-tag>
                    </a-space>
                  </a-space>
                </a-card>
              </a-col>
            </a-row>
          </template>
          <a-empty v-else description="暂无功能权限" />
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="data">
        <template #tab>
          <span><KeyOutlined /> 数据权限</span>
        </template>
        <a-card title="数据访问范围">
          <template #extra>
            <a-button type="primary" @click="showDataPermissionModal = true">配置数据权限</a-button>
          </template>
          <a-space direction="vertical" size="large" style="width: 100%">
            <template v-if="myPermissions.dataScopes && myPermissions.dataScopes.length > 0">
              <a-card v-for="(scope, index) in myPermissions.dataScopes" :key="index" size="small">
                <a-space>
                  <a-tag :color="getDataScopeColor(scope.scope)">{{ getDataScopeLabel(scope.scope) }}</a-tag>
                  <span>{{ scope.label }}</span>
                </a-space>
              </a-card>
            </template>
            <a-empty v-else description="默认仅有本人数据访问权限" />
          </a-space>
          
          <a-divider />
          
          <h4>数据权限说明</h4>
          <a-table
            :dataSource="dataScopeDesc"
            :columns="dataScopeColumns"
            :pagination="false"
            :size="'small'"
          />
        </a-card>
      </a-tab-pane>
    </a-tabs>

    <!-- 角色分配弹窗 -->
    <a-modal
      v-model:open="showRoleModal"
      title="分配角色"
      :footer="null"
      :width="600"
    >
      <p style="margin-bottom: 16px">
        当前角色：
        <template v-if="userRoles.length > 0">
          <a-tag v-for="rid in userRoles" :key="rid" color="blue">{{ getRoleName(rid) }}</a-tag>
        </template>
        <span v-else style="color: #999">暂无角色</span>
      </p>
      <a-table
        :dataSource="roles"
        :columns="roleColumns"
        row-key="id"
        :pagination="{ pageSize: 5 }"
        :row-selection="{ type: 'checkbox', selectedRowKeys: userRoles, onChange: handleRoleSelectChange }"
      />
    </a-modal>

    <!-- 数据权限配置弹窗 -->
    <a-modal
      v-model:open="showDataPermissionModal"
      title="配置数据权限"
      @ok="handleSaveDataPermission"
      @cancel="showDataPermissionModal = false"
      :width="600"
    >
      <a-form :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="数据权限范围">
          <a-select
            mode="multiple"
            placeholder="请选择数据权限范围"
            v-model:value="selectedDataScopes"
          >
            <a-select-option value="ALL">全部数据</a-select-option>
            <a-select-option value="DEPT">本部门数据</a-select-option>
            <a-select-option value="DEPT_AND_CHILD">本部门及下级数据</a-select-option>
            <a-select-option value="PERSONAL">仅本人数据</a-select-option>
          </a-select>
        </a-form-item>
        
        <a-form-item label="自定义部门限制">
          <a-tree
            checkable
            :selectable="false"
            :tree-data="deptTreeData"
            v-model:checked-keys="customDepts"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import { message } from 'ant-design-vue'
import { UserOutlined, SafetyOutlined, LockOutlined, KeyOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '../../stores/user'

const userStore = useUserStore()
const user = userStore.user

const activeTab = ref('profile')

// 表单状态
const formState = reactive({
  username: user?.username || '',
  realName: user?.realName || '',
  email: user?.email || '',
  phone: user?.phone || '',
  newPassword: '',
  confirmPassword: ''
})

// 角色管理状态
const roles = ref<any[]>([])
const userRoles = ref<string[]>([])
const showRoleModal = ref(false)

// 权限配置状态
const myPermissions = ref<{
  menus: any[];
  functions: any[];
  dataScopes: { scope: string; label: string }[];
}>({ menus: [], functions: [], dataScopes: [] })

// 数据权限配置状态
const showDataPermissionModal = ref(false)
const selectedDataScopes = ref<string[]>([])
const customDepts = ref<string[]>([])

// 部门树数据
const deptTreeData = [
  { key: 'dept1', title: '技术部' },
  { key: 'dept2', title: '产品部' },
  { key: 'dept3', title: '运营部' }
]

// 权限类型映射
const permissionTypeMap: Record<string, { color: string; label: string }> = {
  MENU: { color: 'blue', label: '菜单权限' },
  FUNCTION: { color: 'green', label: '功能权限' },
  DATA: { color: 'orange', label: '数据权限' }
}

// 数据范围映射
const dataScopeMap: Record<string, { color: string; label: string }> = {
  ALL: { color: 'red', label: '全部数据' },
  DEPT: { color: 'blue', label: '本部门数据' },
  DEPT_AND_CHILD: { color: 'cyan', label: '本部门及下级' },
  PERSONAL: { color: 'green', label: '仅本人数据' },
  CUSTOM: { color: 'purple', label: '自定义' }
}

const getDataScopeColor = (scope: string) => dataScopeMap[scope]?.color || 'default'
const getDataScopeLabel = (scope: string) => dataScopeMap[scope]?.label || scope

const getRoleName = (roleId: string) => {
  const role = roles.value.find(r => r.id === roleId)
  return role ? role.name : ''
}

// 角色表格列
const roleColumns = [
  { title: '角色名称', dataIndex: 'name', key: 'name' },
  { title: '角色编码', dataIndex: 'code', key: 'code' },
  { title: '类型', dataIndex: 'roleType', key: 'roleType',
    customRender: ({ text }: { text: string }) => (
      h('span', {}, [
        h('a-tag', { color: text === 'SYSTEM' ? 'blue' : 'green' }, text === 'SYSTEM' ? '系统' : '业务')
      ])
    )
  },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true }
]

// 数据权限说明表格数据
const dataScopeDesc = [
  { scope: 'ALL', desc: '可访问全部数据', color: 'red' },
  { scope: 'DEPT', desc: '仅可访问本部门数据', color: 'blue' },
  { scope: 'DEPT_AND_CHILD', desc: '可访问本部门及下级部门数据', color: 'cyan' },
  { scope: 'PERSONAL', desc: '仅可访问本人创建的数据', color: 'green' },
  { scope: 'CUSTOM', desc: '根据自定义配置访问特定数据', color: 'purple' }
]

const dataScopeColumns = [
  { title: '权限范围', dataIndex: 'scope', 
    customRender: ({ text, record }: { text: string; record: any }) => 
      h('a-tag', { color: record.color }, text)
  },
  { title: '说明', dataIndex: 'desc', key: 'desc' }
]

// 加载用户角色
const loadUserRoles = async () => {
  try {
    const response = await fetch(`/api/permissions/users/${user?.id}/roles`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    const data = await response.json()
    if (data.success) {
      userRoles.value = data.data.map((ur: any) => ur.roleId)
    }
  } catch (error) {
    console.error('加载用户角色失败', error)
  }
}

// 加载角色列表
const loadRoles = async () => {
  try {
    const response = await fetch('/api/permissions/roles', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    const data = await response.json()
    if (data.success) {
      roles.value = data.data
    }
  } catch (error) {
    console.error('加载角色列表失败', error)
  }
}

// 加载用户权限信息
const loadMyPermissions = async () => {
  try {
    const response = await fetch('/api/permissions/user-info', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    const data = await response.json()
    if (data.success) {
      myPermissions.value = {
        menus: data.data.menus || [],
        functions: data.data.functions || [],
        dataScopes: data.data.dataScopes || []
      }
      // 设置数据权限范围
      if (data.data.dataScopes?.length > 0) {
        selectedDataScopes.value = data.data.dataScopes.map((s: any) => s.scope)
      }
    }
  } catch (error) {
    console.error('加载用户权限失败', error)
  }
}

// 保存个人信息
const handleSaveProfile = async () => {
  try {
    const response = await fetch(`/api/users/${user?.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        realName: formState.realName,
        email: formState.email,
        phone: formState.phone,
        password: formState.newPassword || undefined
      })
    })
    const data = await response.json()
    if (data.success) {
      message.success('个人信息保存成功')
    } else {
      message.error(data.error || '保存失败')
    }
  } catch (error) {
    message.error('保存失败')
  }
}

// 重置表单
const handleReset = () => {
  formState.realName = user?.realName || ''
  formState.email = user?.email || ''
  formState.phone = user?.phone || ''
  formState.newPassword = ''
  formState.confirmPassword = ''
}

// 保存角色分配
const handleRoleSelectChange = (selectedRowKeys: any) => {
  userRoles.value = selectedRowKeys
  handleSaveRoles(selectedRowKeys)
}

const handleSaveRoles = async (roleIds: string[]) => {
  try {
    const response = await fetch(`/api/permissions/users/${user?.id}/roles`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ roleIds })
    })
    const data = await response.json()
    if (data.success) {
      message.success('角色分配成功')
      loadMyPermissions()
    } else {
      message.error(data.error || '分配失败')
    }
  } catch (error) {
    message.error('分配失败')
  }
}

// 保存数据权限配置
const handleSaveDataPermission = async () => {
  try {
    message.success('数据权限配置保存成功')
    showDataPermissionModal.value = false
  } catch (error) {
    message.error('保存失败')
  }
}

onMounted(() => {
  loadUserRoles()
  loadRoles()
  loadMyPermissions()
})
</script>

<style scoped>
.page-container {
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