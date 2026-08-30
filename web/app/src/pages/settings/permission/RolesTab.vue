<template>
  <div class="roles-tab">
    <div class="filter-row">
      <n-button type="primary" @click="load">刷新</n-button>
      <n-button type="success" @click="onCreate">新建角色</n-button>
      <n-button type="info" @click="onCloneFromTemplate">从模板克隆</n-button>
    </div>

    <n-data-table
      :columns="columns"
      :data="data"
      :loading="loading"
      :bordered="false"
    />

    <!-- 从模板克隆 modal -->
    <n-modal
      v-model:show="cloneModal.show"
      preset="card"
      title="从模板克隆新角色"
      style="max-width: 480px"
    >
      <n-form :model="cloneModal.form" label-placement="left" label-width="100">
        <n-form-item label="模板" required>
          <n-select
            v-model:value="cloneModal.form.templateCode"
            :options="templateOptions"
            placeholder="选择预置模板"
          />
        </n-form-item>
        <n-form-item label="新角色编码" required>
          <n-input v-model:value="cloneModal.form.roleCode" placeholder="e.g. CUSTOM_HR" />
        </n-form-item>
        <n-form-item label="新角色名称" required>
          <n-input v-model:value="cloneModal.form.roleName" placeholder="e.g. 自定义 HR" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="cloneModal.show = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" :loading="cloneModal.saving" @click="onSubmitClone">克隆</n-button>
        </n-space>
      </template>
    </n-modal>

    <RoleEditModal
      v-model:show="editModal.show"
      :role="editModal.role"
      @saved="onEditSaved"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * RolesTab.vue — V2 角色管理 tab (T20 + T21)
 *
 * 后端: GET/POST/PUT/DELETE /api/v1/roles/
 *       POST /api/v1/roles/clone-from-template/
 *
 * T21 增量: "从模板克隆" modal + RoleEditModal (子组件) 在 T21 实现.
 * T20 仅留按钮 + modal 骨架 + 占位提示.
 */
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, NSpace, NDataTable, NModal, NForm, NFormItem, NSelect, NInput, useMessage } from 'naive-ui'
import { listRoles, cloneFromTemplate, deleteRole, type RoleV2 } from '@/api/role-v2'
import { listTemplates, type PermissionTemplate } from '@/api/permission-template'
import RoleEditModal from './RoleEditModal.vue'

const message = useMessage()
const loading = ref(false)
const data = ref<RoleV2[]>([])
const templates = ref<PermissionTemplate[]>([])

const templateOptions = computed(() =>
  templates.value.map((t) => ({ label: `${t.templateName} (${t.templateCode})`, value: t.templateCode })),
)

const columns = [
  { title: '角色编码', key: 'roleCode', width: 160 },
  { title: '角色名称', key: 'roleName', width: 160 },
  { title: '模板来源', key: 'templateCode', width: 140 },
  { title: '默认数据范围', key: 'defaultDataScopeType', width: 140 },
  {
    title: '权限码数',
    key: 'permissionCodes',
    width: 100,
    render: (row: RoleV2) => row.permissionCodes?.length ?? 0,
  },
  {
    title: '系统',
    key: 'isSystem',
    width: 80,
    render: (row: RoleV2) => row.isSystem === 1 ? '预置' : '自定义',
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render(row: RoleV2) {
      return h(NSpace, {}, () => [
        h(NButton, {
          size: 'small',
          text: true,
          type: 'primary',
          onClick: () => onEdit(row),
        }, () => '编辑'),
        h(NButton, {
          size: 'small',
          text: true,
          type: 'error',
          disabled: row.isSystem === 1,
          onClick: () => onDelete(row),
        }, () => '删除'),
      ])
    },
  },
]

const cloneModal = reactive({
  show: false,
  saving: false,
  form: {
    templateCode: '' as string,
    roleCode: '',
    roleName: '',
  },
})

const editModal = reactive({
  show: false,
  role: null as RoleV2 | null,
})

async function load() {
  loading.value = true
  try {
    const [roles, tpls] = await Promise.all([listRoles(), listTemplates()])
    data.value = roles
    templates.value = tpls
  } catch (e: any) {
    message.error('加载失败: ' + (e?.message ?? e))
  } finally {
    loading.value = false
  }
}

function onCreate() {
  // T21: 跳到 RoleEditModal 不带 role, 用空 form 让用户从 0 填
  // 但本任务 T20 暂时只提示
  message.warning('T21 起支持: 在编辑 modal 内可逐个勾选资源 (先选模板更好)')
}

function onCloneFromTemplate() {
  cloneModal.form = { templateCode: '', roleCode: '', roleName: '' }
  cloneModal.show = true
}

async function onSubmitClone() {
  const { templateCode, roleCode, roleName } = cloneModal.form
  if (!templateCode || !roleCode || !roleName) {
    message.warning('模板 + 新角色编码 + 新角色名称 必填')
    return
  }
  cloneModal.saving = true
  try {
    await cloneFromTemplate({ templateCode, roleCode, roleName })
    message.success(`已从模板 ${templateCode} 克隆出 ${roleCode}`)
    cloneModal.show = false
    await load()
  } catch (e: any) {
    message.error('克隆失败: ' + (e?.response?.data?.message ?? e?.message ?? e))
  } finally {
    cloneModal.saving = false
  }
}

function onEdit(row: RoleV2) {
  editModal.role = row
  editModal.show = true
}

function onEditSaved() {
  editModal.show = false
  load()
}

async function onDelete(row: RoleV2) {
  try {
    await deleteRole(row.id)
    message.success('已删除')
    await load()
  } catch (e: any) {
    message.error('删除失败: ' + (e?.response?.data?.message ?? e?.message ?? e))
  }
}

onMounted(load)
</script>

<style scoped>
.roles-tab {
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