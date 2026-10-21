<template>
  <div class="page-container">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">班级管理</h1>
          <p class="page-subtitle">校招生班级（班主任 / HRBP）</p>
        </div>
      </div>

      <div class="toolbar">
        <n-input
          v-model:value="searchText"
          placeholder="搜索班级名称"
          clearable
          class="rule-filter-search"
        >
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <n-switch v-model:value="onlyActive">
          <template #checked>仅显示启用</template>
          <template #unchecked>显示全部</template>
        </n-switch>
        <div class="spacer"></div>
        <n-button type="primary" @click="openCreate">
          <template #icon><n-icon :component="AddOutline" /></template>
          新建班级
        </n-button>
      </div>

      <div class="table-wrap">
        <n-data-table
          :data="list"
          :columns="columns"
          :row-key="(row: any) => row.id"
          :loading="loading"
          :pagination="pagination()"
          :bordered="false"
          flex-height
        >
          <template #empty><n-empty description="暂无班级" /></template>
        </n-data-table>
      </div>

      <!-- 新建 / 编辑 弹窗 -->
      <n-modal
        v-model:show="modalVisible"
        preset="card"
        :title="editing ? '编辑班级' : '新建班级'"
        :style="{ width: '640px' }"
        :mask-closable="false"
      >
        <n-form :model="formState" label-placement="top">
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="班级编号">
                <n-input :value="editing ? formState.code : '自动生成（CL+6位）'" readonly />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="班级名称" required>
                <n-input v-model:value="formState.name" placeholder="请输入班级名称" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="班主任（班主任身份）" required>
                <n-select
                  v-model:value="formState.headTeacher"
                  :options="headTeacherOptions"
                  placeholder="请选择班主任"
                  clearable
                  filterable
                  remote
                  :on-search="onHeadTeacherSearch"
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="HRBP">
                <n-select
                  v-model:value="formState.hrbp"
                  :options="userOptions"
                  placeholder="请选择 HRBP"
                  clearable
                  filterable
                  remote
                  :on-search="onUserSearch"
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="批次">
                <n-input v-model:value="formState.batch" placeholder="如 2026春招" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="启用">
                <n-switch v-model:value="formState.isActive" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-form-item label="备注">
            <n-input v-model:value="formState.remark" type="textarea" placeholder="备注" />
          </n-form-item>
        </n-form>

        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
            <n-button @click="modalVisible = false">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="save">保存</n-button>
          </div>
        </template>
      </n-modal>

      <!-- S5-06（需求 3-2）：班级成员明细抽屉 -->
      <n-drawer v-model:show="membersVisible" :width="720" placement="right">
        <n-drawer-content :title="`班级成员 · ${currentClassName}`" closable>
          <n-data-table
            :data="memberList"
            :columns="memberColumns"
            :row-key="(r: any) => r.id"
            :loading="memberLoading"
            :pagination="{ pageSize: 50 }"
            :bordered="false"
            flex-height
          >
            <template #empty>
              <n-empty description="该班级暂无绑定校招生" />
            </template>
          </n-data-table>
        </n-drawer-content>
      </n-drawer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h, onMounted } from 'vue'
import {
  NButton,
  NDataTable,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NSwitch,
  NTag,
  NSpace,
  NPopconfirm,
  NIcon,
  NEmpty,
  NDrawer,
  useMessage,
} from 'naive-ui'
import { AddOutline, CreateOutline, TrashOutline, SearchOutline } from '@vicons/ionicons5'
import { api } from '../../utils/request'
import {
  extractList,
  extractError,
  searchUsers,
  type SelectOption,
} from '../../utils/campus'
import { column } from '../../composables/useTableColumns'

const message = useMessage()

const list = ref<any[]>([])
const loading = ref(false)
const searchText = ref('')
const onlyActive = ref(true)
const modalVisible = ref(false)
const editing = ref<any | null>(null)
const saving = ref(false)

const headTeacherOptions = ref<SelectOption[]>([])
const userOptions = ref<SelectOption[]>([])

const onHeadTeacherSearch = async (kw: string) => {
  headTeacherOptions.value = await searchUsers(kw, 'head_teacher')
}
const onUserSearch = async (kw: string) => {
  userOptions.value = await searchUsers(kw)
}

const emptyForm = () => ({
  id: null as string | null,
  code: '',
  name: '',
  headTeacher: null as string | null,
  hrbp: null as string | null,
  batch: '',
  isActive: true,
  remark: '',
})
const formState = reactive(emptyForm())

const loadList = async () => {
  loading.value = true
  try {
    const params: Record<string, any> = { page: 1, page_size: 200 }
    if (searchText.value.trim()) params.search = searchText.value.trim()
    if (onlyActive.value) params.is_active = 'true'
    const resp = await api.get('/campus-rotation/class-rooms/', { params })
    list.value = extractList(resp)
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  Object.assign(formState, emptyForm())
  editing.value = null
  headTeacherOptions.value = []
  userOptions.value = []
  modalVisible.value = true
}

const openEdit = (row: any) => {
  Object.assign(formState, emptyForm(), {
    id: row.id,
    code: row.code,
    name: row.name,
    headTeacher: row.headTeacher != null ? String(row.headTeacher) : null,
    hrbp: row.hrbp != null ? String(row.hrbp) : null,
    batch: row.batch || '',
    isActive: row.isActive !== false,
    remark: row.remark || '',
  })
  editing.value = row
  if (row.headTeacher != null) headTeacherOptions.value = [{ label: String(row.headTeacher), value: String(row.headTeacher) }]
  if (row.hrbp != null) userOptions.value = [...userOptions.value.filter((o) => o.value !== String(row.hrbp)), { label: String(row.hrbp), value: String(row.hrbp) }]
  modalVisible.value = true
}

const save = async () => {
  if (!formState.name.trim()) {
    message.warning('请填写班级名称')
    return
  }
  saving.value = true
  const payload: any = {
    name: formState.name,
    headTeacher: formState.headTeacher,
    hrbp: formState.hrbp,
    batch: formState.batch,
    isActive: formState.isActive,
    remark: formState.remark,
  }
  try {
    if (editing.value) {
      await api.put(`/campus-rotation/class-rooms/${editing.value.id}/`, payload)
      message.success('更新成功')
    } else {
      await api.post('/campus-rotation/class-rooms/', payload)
      message.success('创建成功')
    }
    modalVisible.value = false
    loadList()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    saving.value = false
  }
}

const remove = async (row: any) => {
  try {
    await api.delete(`/campus-rotation/class-rooms/${row.id}/`)
    message.success('已删除')
    loadList()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

// S5-06（需求 3-2）：班级成员明细穿透 —— 列表「校招人数」可点击打开抽屉
const membersVisible = ref(false)
const memberLoading = ref(false)
const memberList = ref<any[]>([])
const currentClassName = ref('')
const openMembers = async (row: any) => {
  currentClassName.value = row.name || row.code || ''
  membersVisible.value = true
  memberLoading.value = true
  try {
    const resp = await api.get(`/campus-rotation/class-rooms/${row.id}/members/`)
    const d = resp?.data
    memberList.value = (d?.data ?? []) as any[]
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    memberLoading.value = false
  }
}
// S5-08：列对齐接入 useTableColumns 单一真源
const memberColumns = [
  column({ title: '姓名', key: 'name', width: 110, render: (r: any) => r.name || '-' }),
  column({ title: '工号', key: 'employeeId', width: 120, render: (r: any) => r.employeeId || '-' }),
  column({ title: '在职状态', key: 'status', width: 110, render: (r: any) => r.status || '-' }),
  column({ title: '班主任', key: 'headTeacherName', width: 120, render: (r: any) => r.headTeacherName || '-' }),
  column({ title: '部门', key: 'bu', width: 110, render: (r: any) => r.bu || '-' }),
  column({ title: '院校', key: 'school', width: 90, render: (r: any) => r.school || '-' }),
  column({ title: '专业', key: 'major', width: 90, render: (r: any) => r.major || '-' }),
]

const columns = [
  column({ title: '编号', key: 'code', width: 120, render: (row: any) => row.code || '-' }),
  column({ title: '班级名称', key: 'name', width: 160, ellipsis: true, render: (row: any) => row.name || '-' }),
  column({ title: '班主任', key: 'headTeacher', width: 140, render: (row: any) => (row.headTeacher != null ? String(row.headTeacher) : '-') }),
  column({ title: 'HRBP', key: 'hrbp', width: 140, render: (row: any) => (row.hrbp != null ? String(row.hrbp) : '-') }),
  column({ title: '批次', key: 'batch', width: 120, render: (row: any) => row.batch || '-' }),
  column({ title: '校招人数', key: 'studentCount', width: 100, render: (row: any) => h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openMembers(row) }, { default: () => String(row.studentCount ?? 0) }) }, 'numeric'),
  column(
    {
      title: '启用',
      key: 'isActive',
      width: 80,
      render: (row: any) =>
        h(NTag, { type: row.isActive !== false ? 'success' : 'default', size: 'small' }, {
          default: () => (row.isActive !== false ? '启用' : '停用'),
        }),
    },
    'short',
  ),
  column(
    {
      title: '操作',
      key: 'actions',
      width: 140,
      fixed: 'right' as const,
      render: (row: any) =>
        h(NSpace, { size: 8, wrap: false }, {
          default: () => [
            h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openEdit(row) }, { default: () => '编辑', icon: () => h(NIcon, null, { default: () => h(CreateOutline) }) }),
            h(NPopconfirm, { onPositiveClick: () => remove(row), positiveText: '确认', negativeText: '取消' }, {
              default: () => '确认删除该班级？',
              trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'error' }, { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) }),
            }),
          ],
        }),
    },
    'control',
  ),
]

const pagination = () => ({ pageSize: 50, showSizePicker: false })

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.page-header {
  flex-shrink: 0;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.spacer {
  flex: 1;
}
</style>
