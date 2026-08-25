<template>
  <div class="resources-tab">
    <div class="filter-row">
      <n-input
        v-model:value="search"
        placeholder="搜索资源编码 / 名称"
        clearable
        style="max-width: 280px"
        @keyup.enter="load"
      >
        <template #prefix><n-icon :component="SearchOutline" /></template>
      </n-input>
      <n-select
        v-model:value="moduleFilter"
        :options="moduleOptions"
        placeholder="按模块筛选"
        clearable
        style="max-width: 180px"
        @update:value="load"
      />
      <n-button type="primary" @click="load">刷新</n-button>
      <n-button type="success" @click="onCreate">新建资源</n-button>
    </div>

    <n-data-table
      :columns="columns"
      :data="data"
      :loading="loading"
      :bordered="false"
      :pagination="pagination"
    />

    <n-modal
      v-model:show="modal.show"
      preset="card"
      :title="modal.editing ? '编辑资源' : '新建资源'"
      style="max-width: 600px"
    >
      <n-form :model="modal.form" label-placement="left" label-width="100">
        <n-form-item label="资源编码" required>
          <n-input v-model:value="modal.form.resourceCode" placeholder="recruit:menu:xxx" :disabled="modal.editing" />
        </n-form-item>
        <n-form-item label="资源名称" required>
          <n-input v-model:value="modal.form.resourceName" placeholder="显示名" />
        </n-form-item>
        <n-form-item label="资源类型" required>
          <n-select
            v-model:value="modal.form.resourceType"
            :options="resourceTypeOptions"
          />
        </n-form-item>
        <n-form-item label="模块">
          <n-input v-model:value="modal.form.module" placeholder="recruit / hr / system" />
        </n-form-item>
        <n-form-item label="状态">
          <n-switch v-model:value="statusSwitch" />
          <span style="margin-left: 8px; color: #888">{{ statusSwitch ? '启用' : '禁用' }}</span>
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="modal.show = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" :loading="modal.saving" @click="onSubmit">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
/**
 * ResourcesTab.vue — 权限资源 tab (T20)
 * 后端: GET/POST/PUT/DELETE /api/v1/permissions/resources/
 */
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, NSpace, NInput, NSelect, NDataTable, NModal, NForm, NFormItem, NSwitch, useMessage } from 'naive-ui'
import {
  listResources,
  createResource,
  updateResource,
  deleteResource,
  type PermissionResource,
  type ResourceType,
} from '@/api/permission-resource'
import { SearchOutline } from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const search = ref('')
const moduleFilter = ref<string | null>(null)
const data = ref<PermissionResource[]>([])

const pagination = { pageSize: 20 }

const moduleOptions = computed(() => {
  const modules = new Set<string>()
  data.value.forEach((r) => r.module && modules.add(r.module))
  return Array.from(modules).map((m) => ({ label: m, value: m }))
})

const resourceTypeOptions: { label: string; value: ResourceType }[] = [
  { label: '菜单', value: 'MENU' },
  { label: '按钮', value: 'BUTTON' },
  { label: '字段', value: 'FIELD' },
  { label: 'API', value: 'API' },
]

const columns = [
  { title: '资源编码', key: 'resourceCode', width: 240 },
  { title: '资源名称', key: 'resourceName', width: 160 },
  {
    title: '类型',
    key: 'resourceType',
    width: 80,
  },
  { title: '模块', key: 'module', width: 120 },
  { title: '状态', key: 'status', width: 80, render: (row: PermissionResource) => row.status === 1 ? '启用' : '禁用' },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render(row: PermissionResource) {
      return h(NSpace, {}, () => [
        h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => onEdit(row) }, () => '编辑'),
        h(NPopconfirm, {
          onPositiveClick: () => onDelete(row),
        }, {
          trigger: () => h(NButton, { size: 'small', text: true, type: 'error' }, () => '删除'),
          default: () => `确认删除 ${row.resourceCode}?`,
        }),
      ])
    },
  },
]

// lazy import NPopconfirm for h() to work
import { NPopconfirm } from 'naive-ui'

const modal = reactive({
  show: false,
  editing: false,
  saving: false,
  form: {
    id: '' as string,
    resourceCode: '',
    resourceName: '',
    resourceType: 'MENU' as ResourceType,
    module: '',
    status: 1 as number,
  },
})

const statusSwitch = computed({
  get: () => modal.form.status === 1,
  set: (v: boolean) => { modal.form.status = v ? 1 : 0 },
})

async function load() {
  loading.value = true
  try {
    data.value = await listResources({
      module: moduleFilter.value || undefined,
    })
  } catch (e: any) {
    message.error('加载资源失败: ' + (e?.message ?? e))
  } finally {
    loading.value = false
  }
}

function onCreate() {
  modal.editing = false
  modal.form = {
    id: '',
    resourceCode: '',
    resourceName: '',
    resourceType: 'MENU',
    module: '',
    status: 1,
  }
  modal.show = true
}

function onEdit(row: PermissionResource) {
  modal.editing = true
  modal.form = {
    id: row.id,
    resourceCode: row.resourceCode,
    resourceName: row.resourceName,
    resourceType: row.resourceType,
    module: row.module ?? '',
    status: row.status,
  }
  modal.show = true
}

async function onSubmit() {
  if (!modal.form.resourceCode || !modal.form.resourceName) {
    message.warning('资源编码和名称必填')
    return
  }
  modal.saving = true
  try {
    const payload = {
      resourceCode: modal.form.resourceCode,
      resourceName: modal.form.resourceName,
      resourceType: modal.form.resourceType,
      module: modal.form.module || null,
      status: modal.form.status,
    }
    if (modal.editing) {
      await updateResource(modal.form.id, payload)
      message.success('已更新')
    } else {
      await createResource(payload)
      message.success('已创建')
    }
    modal.show = false
    await load()
  } catch (e: any) {
    message.error('保存失败: ' + (e?.response?.data?.message ?? e?.message ?? e))
  } finally {
    modal.saving = false
  }
}

async function onDelete(row: PermissionResource) {
  try {
    await deleteResource(row.id)
    message.success('已删除')
    await load()
  } catch (e: any) {
    message.error('删除失败: ' + (e?.response?.data?.message ?? e?.message ?? e))
  }
}

onMounted(load)
</script>

<style scoped>
.resources-tab {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.filter-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>