<template>
  <div class="user-roles-tab">
    <div class="filter-row">
      <n-button type="primary" @click="load">刷新</n-button>
      <n-button type="success" @click="onCreate">分配角色</n-button>
    </div>

    <n-data-table
      :columns="columns"
      :data="data"
      :loading="loading"
      :bordered="false"
    />

    <UserRoleEditModal
      v-model:show="editModal.show"
      :grant="editModal.grant"
      @saved="onEditSaved"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * UserRolesTab.vue — V2 用户角色授权 tab (T20 + T22)
 *
 * 后端: GET/POST/PUT/DELETE /api/v1/user-roles/
 *       GET /api/v1/user-roles/suggest-scope/
 *
 * T22 增量: UserRoleEditModal (子组件) 在 T22 实现, 含数据范围 radio + suggest-scope 按钮.
 * T20 仅留按钮 + 占位 modal.
 */
import { h, onMounted, reactive, ref } from 'vue'
import { NButton, NSpace, NDataTable, useMessage } from 'naive-ui'
import { listUserRoles, deleteUserRole, type UserRoleV2 } from '@/api/user-role-v2'
import UserRoleEditModal from './UserRoleEditModal.vue'

const message = useMessage()
const loading = ref(false)
const data = ref<UserRoleV2[]>([])

const columns = [
  {
    title: '用户ID',
    key: 'userId',
    width: 100,
  },
  { title: '角色编码', key: 'roleCode', width: 160 },
  {
    title: '管理单元',
    key: 'managementUnitIds',
    width: 200,
    render: (row: UserRoleV2) => {
      const ids = row.managementUnitIds
      if (!ids || ids.length === 0) return h('span', { style: 'color:#aaa' }, '(全部)')
      return ids.join(', ')
    },
  },
  { title: '生效', key: 'validFrom', width: 110 },
  { title: '失效', key: 'validTo', width: 110 },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render(row: UserRoleV2) {
      return h(NSpace, {}, () => [
        h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => onEdit(row) }, () => '编辑'),
        h(NButton, { size: 'small', text: true, type: 'error', onClick: () => onDelete(row) }, () => '撤销'),
      ])
    },
  },
]

const editModal = reactive({
  show: false,
  grant: null as UserRoleV2 | null,
})

async function load() {
  loading.value = true
  try {
    data.value = await listUserRoles()
  } catch (e: any) {
    message.error('加载失败: ' + (e?.message ?? e))
  } finally {
    loading.value = false
  }
}

function onCreate() {
  editModal.grant = null
  editModal.show = true
}

function onEdit(row: UserRoleV2) {
  editModal.grant = row
  editModal.show = true
}

function onEditSaved() {
  editModal.show = false
  load()
}

async function onDelete(row: UserRoleV2) {
  try {
    await deleteUserRole(row.id)
    message.success('已撤销')
    await load()
  } catch (e: any) {
    message.error('撤销失败: ' + (e?.response?.data?.message ?? e?.message ?? e))
  }
}

onMounted(load)
</script>

<style scoped>
.user-roles-tab {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.filter-row {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}
</style>