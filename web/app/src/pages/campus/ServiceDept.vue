<template>
  <div class="page-container">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">客服部门</h1>
          <p class="page-subtitle">客服部门资源管理（品牌 / 地点 / 容量 / 客服主管 / 类型）</p>
        </div>
      </div>

      <div class="toolbar">
        <n-input
          v-model:value="searchText"
          placeholder="搜索客服部门名称"
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
          新建客服部门
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
          <template #empty><n-empty description="暂无客服部门" /></template>
        </n-data-table>
      </div>

      <!-- 新建 / 编辑 弹窗 -->
      <n-modal
        v-model:show="modalVisible"
        preset="card"
        :title="editing ? '编辑客服部门' : '新建客服部门'"
        :style="{ width: '640px' }"
        :mask-closable="false"
      >
        <n-form :model="formState" label-placement="top">
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="客服部门编号">
                <n-input :value="editing ? formState.deptNo : '自动生成（SD+6位）'" readonly />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="部门名称" required>
                <n-input v-model:value="formState.name" placeholder="请输入部门名称" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="归属部门" required>
                <n-tree-select
                  v-model:value="formState.department"
                  :options="deptTreeOptions"
                  :render-label="renderDeptLabel"
                  placeholder="请选择归属部门"
                  clearable
                  filterable
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="归属BU（二级部门）" required>
                <n-select
                  v-model:value="formState.bu"
                  :options="buOpts"
                  placeholder="请选择归属BU"
                  clearable
                  filterable
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="客服主管（校园导师）">
                <n-select
                  v-model:value="formState.csSupervisor"
                  :options="supervisorOptions"
                  placeholder="请选择客服主管"
                  clearable
                  filterable
                  remote
                  :on-search="onSupervisorSearch"
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="地点">
                <n-select
                  v-model:value="formState.location"
                  :options="locationOptions"
                  placeholder="请选择地点"
                  clearable
                  filterable
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="品牌">
                <n-select
                  v-model:value="formState.brand"
                  :options="brandOptions"
                  placeholder="请选择品牌"
                  clearable
                  filterable
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="容量上限">
                <n-input-number v-model:value="formState.capacity" :min="0" placeholder="容量" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="客服类型">
                <n-select
                  v-model:value="formState.csType"
                  :options="csTypeOptions"
                  placeholder="请选择客服类型"
                  clearable
                  filterable
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="工位类型">
                <n-select
                  v-model:value="formState.workstationType"
                  :options="workstationOptions"
                  placeholder="请选择工位类型"
                  clearable
                  filterable
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="是否需培训认证">
                <n-switch v-model:value="formState.needTrainingCert" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="社招人数">
                <n-input-number v-model:value="formState.socialCount" :min="0" style="width: 100%" />
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
  NInputNumber,
  NSelect,
  NTreeSelect,
  NSwitch,
  NTag,
  NSpace,
  NPopconfirm,
  NIcon,
  NEmpty,
  useMessage,
} from 'naive-ui'
import { AddOutline, CreateOutline, TrashOutline, SearchOutline } from '@vicons/ionicons5'
import { api } from '../../utils/request'
import { useDepartmentStore } from '../../stores/department'
import {
  extractList,
  extractError,
  buildDeptTree,
  deptLevelMap,
  buOptions,
  searchUsers,
  dictOptions,
  type SelectOption,
} from '../../utils/campus'

const message = useMessage()
const deptStore = useDepartmentStore()

const list = ref<any[]>([])
const loading = ref(false)
const searchText = ref('')
const onlyActive = ref(true)
const modalVisible = ref(false)
const editing = ref<any | null>(null)
const saving = ref(false)

const locationOptions = ref<SelectOption[]>([])
const brandOptions = ref<SelectOption[]>([])
const csTypeOptions = ref<SelectOption[]>([])
const workstationOptions = ref<SelectOption[]>([])
const supervisorOptions = ref<SelectOption[]>([])

const deptTreeOptions = computed(() => buildDeptTree(deptStore.departments))
const levelMap = computed(() => deptLevelMap(deptStore.departments))
const buOpts = computed(() => buOptions(deptStore.departments, levelMap.value))

function renderDeptLabel({ option }: { option: any }) {
  return h('span', option.name)
}

const emptyForm = () => ({
  id: null as string | null,
  deptNo: '',
  name: '',
  department: null as string | null,
  bu: null as string | null,
  brand: '',
  location: null as string | null,
  capacity: null as number | null,
  csSupervisor: null as string | null,
  csType: '',
  workstationType: '',
  needTrainingCert: false,
  socialCount: 0,
  isActive: true,
  remark: '',
})
const formState = reactive(emptyForm())

const onSupervisorSearch = async (kw: string) => {
  supervisorOptions.value = await searchUsers(kw, 'campus_mentor')
}

const loadList = async () => {
  loading.value = true
  try {
    const params: Record<string, any> = { page: 1, page_size: 200 }
    if (searchText.value.trim()) params.search = searchText.value.trim()
    if (onlyActive.value) params.is_active = 'true'
    const resp = await api.get('/campus-rotation/service-depts/', { params })
    list.value = extractList(resp)
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    loading.value = false
  }
}

const loadDicts = async () => {
  try {
    const [loc, brand, csType, ws] = await Promise.all([
      dictOptions('LOCATION'),
      dictOptions('BRAND'),
      dictOptions('CS_TYPE'),
      dictOptions('WORKSTATION_TYPE'),
    ])
    locationOptions.value = loc
    brandOptions.value = brand
    csTypeOptions.value = csType
    workstationOptions.value = ws
  } catch (e: any) {
    message.error(extractError(e))
  }
}

const openCreate = () => {
  Object.assign(formState, emptyForm())
  editing.value = null
  supervisorOptions.value = []
  modalVisible.value = true
}

const openEdit = (row: any) => {
  Object.assign(formState, emptyForm(), {
    id: row.id,
    deptNo: row.deptNo,
    name: row.name,
    department: row.department != null ? String(row.department) : null,
    bu: row.bu != null ? String(row.bu) : null,
    brand: row.brand || '',
    location: row.location ?? null,
    capacity: row.capacity ?? null,
    csSupervisor: row.csSupervisor != null ? String(row.csSupervisor) : null,
    csType: row.csType || '',
    workstationType: row.workstationType || '',
    needTrainingCert: row.needTrainingCert === true,
    socialCount: row.socialCount ?? 0,
    isActive: row.isActive !== false,
    remark: row.remark || '',
  })
  editing.value = row
  supervisorOptions.value = row.csSupervisor != null ? [{ label: String(row.csSupervisor), value: String(row.csSupervisor) }] : []
  modalVisible.value = true
}

const save = async () => {
  if (!formState.name.trim()) {
    message.warning('请填写部门名称')
    return
  }
  saving.value = true
  const payload: any = {
    name: formState.name,
    department: formState.department,
    bu: formState.bu,
    brand: formState.brand || null,
    location: formState.location,
    capacity: formState.capacity,
    csSupervisor: formState.csSupervisor,
    csType: formState.csType || null,
    workstationType: formState.workstationType || null,
    needTrainingCert: formState.needTrainingCert,
    socialCount: formState.socialCount,
    isActive: formState.isActive,
    remark: formState.remark,
  }
  try {
    if (editing.value) {
      await api.put(`/campus-rotation/service-depts/${editing.value.id}/`, payload)
      message.success('更新成功')
    } else {
      await api.post('/campus-rotation/service-depts/', payload)
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
    await api.delete(`/campus-rotation/service-depts/${row.id}/`)
    message.success('已删除')
    loadList()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

// 字典项 key → 中文名（表格展示用）
const dictLabel = (options: SelectOption[], key: string | null | undefined) => {
  if (!key) return '-'
  return options.find((o) => o.value === key)?.label || key
}
const deptName = (id: any) => (id != null ? deptStore.getById(String(id))?.name || String(id) : '-')

const columns = [
  { title: '编号', key: 'deptNo', width: 120, render: (row: any) => row.deptNo || '-' },
  { title: '名称', key: 'name', width: 160, ellipsis: true, render: (row: any) => row.name || '-' },
  { title: '归属部门', key: 'department', width: 160, ellipsis: true, render: (row: any) => deptName(row.department) },
  { title: '归属BU', key: 'bu', width: 160, ellipsis: true, render: (row: any) => deptName(row.bu) },
  { title: '客服主管', key: 'csSupervisor', width: 140, render: (row: any) => (row.csSupervisor != null ? String(row.csSupervisor) : '-') },
  { title: '地点', key: 'location', width: 100, render: (row: any) => dictLabel(locationOptions.value, row.location) },
  { title: '品牌', key: 'brand', width: 110, render: (row: any) => dictLabel(brandOptions.value, row.brand) },
  { title: '客服类型', key: 'csType', width: 100, render: (row: any) => dictLabel(csTypeOptions.value, row.csType) },
  { title: '工位类型', key: 'workstationType', width: 100, render: (row: any) => dictLabel(workstationOptions.value, row.workstationType) },
  { title: '容量', key: 'capacity', width: 80, render: (row: any) => row.capacity ?? '-' },
  { title: '社招人数', key: 'socialCount', width: 90, render: (row: any) => row.socialCount ?? 0 },
  { title: '校招占用', key: 'campusCount', width: 90, render: (row: any) => row.campusCount ?? 0 },
  {
    title: '启用',
    key: 'isActive',
    width: 80,
    render: (row: any) =>
      h(NTag, { type: row.isActive !== false ? 'success' : 'default', size: 'small' }, {
        default: () => (row.isActive !== false ? '启用' : '停用'),
      }),
  },
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
            default: () => '确认删除该客服部门？',
            trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'error' }, { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) }),
          }),
        ],
      }),
  },
]

const pagination = () => ({ pageSize: 50, showSizePicker: false })

onMounted(() => {
  deptStore.loadDepartments()
  loadDicts()
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
