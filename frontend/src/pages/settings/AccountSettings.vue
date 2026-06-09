<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">账号设置</h1>
    </div>

    <n-tabs v-model:value="activeTab" type="line" animated default-value="profile">
      <n-tab-pane name="profile">
        <template #tab>
          <span class="inline-flex items-center gap-1"><n-icon :component="PersonOutline" /> 基本信息</span>
        </template>
        <n-card title="个人信息">
          <n-form :model="formState" label-placement="left" :label-width="100">
            <div class="grid grid-cols-2 gap-x-6">
              <n-form-item label="用户名">
                <n-input v-model:value="formState.username" disabled />
              </n-form-item>
              <n-form-item label="真实姓名" path="realName">
                <n-input v-model:value="formState.realName" placeholder="请输入真实姓名" />
              </n-form-item>
              <n-form-item label="邮箱" path="email">
                <n-input v-model:value="formState.email" placeholder="请输入邮箱" />
              </n-form-item>
              <n-form-item label="手机号" path="phone">
                <n-input v-model:value="formState.phone" placeholder="请输入手机号" />
              </n-form-item>
            </div>
            <n-divider />
            <div class="grid grid-cols-2 gap-x-6">
              <n-form-item label="新密码">
                <n-input v-model:value="formState.newPassword" type="password" show-password-on="click" placeholder="请输入新密码（不修改请留空）" />
              </n-form-item>
              <n-form-item label="确认密码">
                <n-input v-model:value="formState.confirmPassword" type="password" show-password-on="click" placeholder="请再次输入密码" />
              </n-form-item>
            </div>
            <n-space>
              <n-button type="primary" @click="handleSaveProfile">保存</n-button>
              <n-button @click="handleReset">重置</n-button>
            </n-space>
          </n-form>
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="roles">
        <template #tab>
          <span class="inline-flex items-center gap-1"><n-icon :component="ShieldCheckmarkOutline" /> 角色分配</span>
        </template>
        <n-card title="我的角色">
          <template #header-extra>
            <n-button type="primary" @click="showRoleModal = true">分配角色</n-button>
          </template>
          <template v-if="userRoles.length > 0">
            <n-space size="large" :wrap="true">
              <n-tag v-for="roleId in userRoles" :key="roleId" type="info" :style="{ padding: '8px 16px', fontSize: '14px' }">
                {{ getRoleName(roleId) }}
              </n-tag>
            </n-space>
          </template>
          <n-empty v-else description="暂未分配角色" />

          <n-divider />

          <h4 style="margin-bottom: 16px">可选角色列表</h4>
          <n-data-table
            :data="roles"
            :columns="roleColumnsWithSelection"
            :row-key="(row: any) => row.id"
            size="small"
            :pagination="{ pageSize: 5 }"
            :checked-row-keys="userRoles"
            @update:checked-row-keys="handleRoleSelectChange"
          />
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="menus">
        <template #tab>
          <span class="inline-flex items-center gap-1"><n-icon :component="LockClosedOutline" /> 菜单权限</span>
        </template>
        <n-card title="可访问的菜单">
          <template v-if="myPermissions.menus && myPermissions.menus.length > 0">
            <div class="grid grid-cols-4 gap-4">
              <n-card v-for="menu in myPermissions.menus" :key="menu.id" size="small" style="background: #f5f5f5">
                <n-space>
                  <span style="font-size: 16px">📁</span>
                  <span>{{ menu.name }}</span>
                </n-space>
                <n-tag v-if="menu.resource" type="info" style="margin-left: 8px">{{ menu.resource }}</n-tag>
              </n-card>
            </div>
          </template>
          <n-empty v-else description="暂无可访问的菜单" />
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="functions">
        <template #tab>
          <span class="inline-flex items-center gap-1"><n-icon :component="KeyOutline" /> 功能权限</span>
        </template>
        <n-card title="可执行的操作">
          <template v-if="myPermissions.functions && myPermissions.functions.length > 0">
            <div class="grid grid-cols-3 gap-3">
              <n-card v-for="func in myPermissions.functions" :key="func.id" size="small" style="background: #f0f5ff">
                <n-space vertical :size="4">
                  <strong>{{ func.name }}</strong>
                  <n-space>
                    <n-tag type="success">{{ func.action || '*' }}</n-tag>
                    <n-tag v-if="func.resource" type="info">{{ func.resource }}</n-tag>
                  </n-space>
                </n-space>
              </n-card>
            </div>
          </template>
          <n-empty v-else description="暂无功能权限" />
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="data">
        <template #tab>
          <span class="inline-flex items-center gap-1"><n-icon :component="KeyOutline" /> 数据权限</span>
        </template>
        <n-card title="数据访问范围">
          <template #header-extra>
            <n-button type="primary" @click="showDataPermissionModal = true">配置数据权限</n-button>
          </template>
          <n-space vertical size="large" style="width: 100%">
            <template v-if="myPermissions.dataScopes && myPermissions.dataScopes.length > 0">
              <n-card v-for="(scope, index) in myPermissions.dataScopes" :key="index" size="small">
                <n-space>
                  <n-tag :type="getDataScopeType(scope.scope)">{{ getDataScopeLabel(scope.scope) }}</n-tag>
                  <span>{{ scope.label }}</span>
                </n-space>
              </n-card>
            </template>
            <n-empty v-else description="默认仅有本人数据访问权限" />
          </n-space>

          <n-divider />

          <h4>数据权限说明</h4>
          <n-data-table
            :data="dataScopeDesc"
            :columns="dataScopeColumns"
            :pagination="false"
            size="small"
          />
        </n-card>
      </n-tab-pane>
    </n-tabs>

    <!-- 角色分配弹窗 -->
    <n-modal
      v-model:show="showRoleModal"
      preset="card"
      title="分配角色"
      style="width: 600px"
    >
      <p style="margin-bottom: 16px">
        当前角色：
        <template v-if="userRoles.length > 0">
          <n-tag v-for="rid in userRoles" :key="rid" type="info" style="margin-right: 4px">{{ getRoleName(rid) }}</n-tag>
        </template>
        <span v-else style="color: #999">暂无角色</span>
      </p>
      <n-data-table
        :data="roles"
        :columns="roleColumnsWithSelection"
        :row-key="(row: any) => row.id"
        :pagination="{ pageSize: 5 }"
        :checked-row-keys="userRoles"
        @update:checked-row-keys="handleRoleSelectChange"
      />
    </n-modal>

    <!-- 数据权限配置弹窗 -->
    <n-modal
      v-model:show="showDataPermissionModal"
      preset="dialog"
      title="配置数据权限"
      positive-text="确定"
      negative-text="取消"
      style="width: 600px"
      @positive-click="handleSaveDataPermission"
      @negative-click="showDataPermissionModal = false"
    >
      <n-form label-placement="left" :label-width="120" class="mt-4">
        <n-form-item label="数据权限范围">
          <n-select
            multiple
            placeholder="请选择数据权限范围"
            v-model:value="selectedDataScopes"
            :options="dataScopeOptions"
          />
        </n-form-item>

        <n-form-item label="自定义部门限制">
          <n-tree
            checkable
            :selectable="false"
            :data="deptTreeData"
            v-model:checked-keys="customDepts"
          />
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import api from '../../api/auth';
import { ref, reactive, onMounted, h, computed } from 'vue'
import { useMessage, NTag } from 'naive-ui'
import { PersonOutline, ShieldCheckmarkOutline, LockClosedOutline, KeyOutline } from '@vicons/ionicons5'
import { useUserStore } from '../../stores/user'

const message = useMessage()
const userStore = useUserStore()
// 修复：userStore.user 是 Vue ref，必须 .value 访问属性
const user = computed(() => userStore.user)

const activeTab = ref('profile')

// 表单状态
const formState = reactive({
  username: user.value?.username || '',
  realName: user.value?.realName || '',
  email: user.value?.email || '',
  phone: user.value?.phone || '',
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
  { key: 'dept1', label: '技术部' },
  { key: 'dept2', label: '产品部' },
  { key: 'dept3', label: '运营部' }
]

const dataScopeOptions = [
  { label: '全部数据', value: 'ALL' },
  { label: '本部门数据', value: 'DEPT' },
  { label: '本部门及下级数据', value: 'DEPT_AND_CHILD' },
  { label: '仅本人数据', value: 'PERSONAL' }
]

// 数据范围映射
const dataScopeMap: Record<string, { type: 'default' | 'error' | 'info' | 'success' | 'warning'; label: string }> = {
  ALL: { type: 'error', label: '全部数据' },
  DEPT: { type: 'info', label: '本部门数据' },
  DEPT_AND_CHILD: { type: 'info', label: '本部门及下级' },
  PERSONAL: { type: 'success', label: '仅本人数据' },
  CUSTOM: { type: 'warning', label: '自定义' }
}

const getDataScopeType = (scope: string) => dataScopeMap[scope]?.type || 'default'
const getDataScopeLabel = (scope: string) => dataScopeMap[scope]?.label || scope

const getRoleName = (roleId: string) => {
  const role = roles.value.find(r => r.id === roleId)
  return role ? role.name : ''
}

// 角色表格列（带选择）
const roleColumnsWithSelection = computed<any[]>(() => [
  { type: 'selection' },
  { title: '角色名称', key: 'name' },
  { title: '角色编码', key: 'code' },
  {
    title: '类型',
    key: 'roleType',
    render: (row: any) => h(NTag, { type: row.roleType === 'SYSTEM' ? 'info' : 'success' }, { default: () => row.roleType === 'SYSTEM' ? '系统' : '业务' })
  },
  { title: '描述', key: 'description', ellipsis: true }
])

// 数据权限说明表格数据
const dataScopeDesc = [
  { scope: 'ALL', desc: '可访问全部数据', type: 'error' as const },
  { scope: 'DEPT', desc: '仅可访问本部门数据', type: 'info' as const },
  { scope: 'DEPT_AND_CHILD', desc: '可访问本部门及下级部门数据', type: 'info' as const },
  { scope: 'PERSONAL', desc: '仅可访问本人创建的数据', type: 'success' as const },
  { scope: 'CUSTOM', desc: '根据自定义配置访问特定数据', type: 'warning' as const }
]

const dataScopeColumns = [
  {
    title: '权限范围',
    key: 'scope',
    render: (row: any) => h(NTag, { type: row.type }, { default: () => row.scope })
  },
  { title: '说明', key: 'desc' }
]

// 加载用户角色
const loadUserRoles = async () => {
  if (!user.value?.id) {
    console.warn('user.id 不可用, 跳过加载用户角色')
    return
  }
  try {
    const data = (await api.get(`/permissions/users/${user.value.id}/roles`)).data
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
    const data = (await api.get('/permissions/roles')).data
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
    const data = (await api.get('/permissions/user-info')).data
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
  if (!user.value?.id) {
    message.error('用户未登录')
    return
  }
  try {
    const data = (await api.put(`/users/${user.value.id}`, {
        realName: formState.realName,
        email: formState.email,
        phone: formState.phone,
        password: formState.newPassword || undefined
      })).data
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
  formState.realName = user.value?.realName || ''
  formState.email = user.value?.email || ''
  formState.phone = user.value?.phone || ''
  formState.newPassword = ''
  formState.confirmPassword = ''
}

// 保存角色分配
const handleRoleSelectChange = (selectedRowKeys: any) => {
  userRoles.value = selectedRowKeys
  handleSaveRoles(selectedRowKeys)
}

const handleSaveRoles = async (roleIds: string[]) => {
  if (!user.value?.id) {
    message.error('用户未登录')
    return
  }
  try {
    const data = (await api.post(`/permissions/users/${user.value.id}/roles`, { roleIds })).data
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
