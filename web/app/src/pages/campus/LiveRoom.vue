<template>
  <div class="page-container">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">轮岗资源</h1>
          <p class="page-subtitle">直播间资源管理（平台 / 地点 / 容量 / 导师）</p>
        </div>
      </div>

      <div class="toolbar">
        <n-input
          v-model:value="searchText"
          placeholder="搜索直播间名称"
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
        <n-dropdown :options="addResourceOptions" @select="onAddResourceSelect">
          <n-button type="primary">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增资源
          </n-button>
        </n-dropdown>
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
          <template #empty><n-empty description="暂无直播间" /></template>
        </n-data-table>
      </div>

      <!-- 新建 / 编辑 弹窗 -->
      <n-modal
        v-model:show="modalVisible"
        preset="card"
        :title="editing ? '编辑直播间' : '新建直播间'"
        :style="{ width: '640px' }"
        :mask-closable="false"
      >
        <n-form :model="formState" label-placement="top">
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="直播间编号">
                <n-input :value="editing ? formState.roomNo : '自动生成（LR+6位）'" readonly />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="直播间名称" required>
                <n-input v-model:value="formState.name" placeholder="请输入直播间名称" />
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
              <n-form-item label="直播间导师（校园导师）">
                <n-select
                  v-model:value="formState.mentor"
                  :options="mentorOptions"
                  placeholder="请选择导师"
                  clearable
                  filterable
                  remote
                  :on-search="onMentorSearch"
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
              <n-form-item label="平台">
                <n-select
                  v-model:value="formState.platform"
                  :options="platformOptions"
                  placeholder="请选择平台"
                  clearable
                  filterable
                />
              </n-form-item>
            </n-grid-item>
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
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
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
import { useRouter } from 'vue-router'
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
  NDropdown,
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
import { column } from '../../composables/useTableColumns'

const message = useMessage()
const deptStore = useDepartmentStore()
const router = useRouter()

const addResourceOptions = [
  { label: '新增直播间', key: 'live_room' },
  { label: '新增客服部门', key: 'service_dept' },
]
const onAddResourceSelect = (key: string) => {
  if (key === 'live_room') {
    openCreate()
  } else if (key === 'service_dept') {
    router.push('/campus/service-dept')
  }
}

const list = ref<any[]>([])
const loading = ref(false)
const searchText = ref('')
const onlyActive = ref(true)
const modalVisible = ref(false)
const editing = ref<any | null>(null)
const saving = ref(false)

const platformOptions = ref<SelectOption[]>([])
const locationOptions = ref<SelectOption[]>([])
const brandOptions = ref<SelectOption[]>([])
const mentorOptions = ref<SelectOption[]>([])

const deptTreeOptions = computed(() => buildDeptTree(deptStore.departments))
const levelMap = computed(() => deptLevelMap(deptStore.departments))
const buOpts = computed(() => buOptions(deptStore.departments, levelMap.value))

function renderDeptLabel({ option }: { option: any }) {
  return h('span', option.name)
}

const emptyForm = () => ({
  id: null as string | null,
  roomNo: '',
  name: '',
  department: null as string | null,
  bu: null as string | null,
  mentor: null as string | null,
  platform: null as string | null,
  brand: null as string | null,
  location: null as string | null,
  capacity: null as number | null,
  socialCount: 0,
  isActive: true,
  remark: '',
})
const formState = reactive(emptyForm())

const onMentorSearch = async (kw: string) => {
  mentorOptions.value = await searchUsers(kw, 'campus_mentor')
}

const loadList = async () => {
  loading.value = true
  try {
    const params: Record<string, any> = { page: 1, page_size: 200 }
    if (searchText.value.trim()) params.search = searchText.value.trim()
    if (onlyActive.value) params.is_active = 'true'
    const resp = await api.get('/campus-rotation/live-rooms/', { params })
    list.value = extractList(resp)
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    loading.value = false
  }
}

const loadDicts = async () => {
  try {
    const [plat, brand, loc] = await Promise.all([
      dictOptions('LIVE_ROOM_PLATFORM'),
      dictOptions('BRAND'),
      dictOptions('LOCATION'),
    ])
    platformOptions.value = plat
    brandOptions.value = brand
    locationOptions.value = loc
  } catch (e: any) {
    message.error(extractError(e))
  }
}

const openCreate = () => {
  Object.assign(formState, emptyForm())
  editing.value = null
  mentorOptions.value = []
  modalVisible.value = true
}

const openEdit = (row: any) => {
  Object.assign(formState, emptyForm(), {
    id: row.id,
    roomNo: row.roomNo,
    name: row.name,
    department: row.department != null ? String(row.department) : null,
    bu: row.bu != null ? String(row.bu) : null,
    mentor: row.mentor != null ? String(row.mentor) : null,
    platform: row.platform ?? null,
    brand: row.brand ?? null,
    location: row.location ?? null,
    capacity: row.capacity ?? null,
    socialCount: row.socialCount ?? 0,
    isActive: row.isActive !== false,
    remark: row.remark || '',
  })
  editing.value = row
  mentorOptions.value = row.mentor != null ? [{ label: String(row.mentor), value: String(row.mentor) }] : []
  modalVisible.value = true
}

const save = async () => {
  if (!formState.name.trim()) {
    message.warning('请填写直播间名称')
    return
  }
  saving.value = true
  const payload: any = {
    name: formState.name,
    department: formState.department,
    bu: formState.bu,
    mentor: formState.mentor,
    platform: formState.platform,
    brand: formState.brand,
    location: formState.location,
    capacity: formState.capacity,
    socialCount: formState.socialCount,
    isActive: formState.isActive,
    remark: formState.remark,
  }
  try {
    if (editing.value) {
      await api.put(`/campus-rotation/live-rooms/${editing.value.id}/`, payload)
      message.success('更新成功')
    } else {
      await api.post('/campus-rotation/live-rooms/', payload)
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
    await api.delete(`/campus-rotation/live-rooms/${row.id}/`)
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

// S5-08：列对齐接入 useTableColumns 单一真源
const columns = [
  column({ title: '编号', key: 'roomNo', width: 120, render: (row: any) => row.roomNo || '-' }),
  column({ title: '名称', key: 'name', width: 160, ellipsis: true, render: (row: any) => row.name || '-' }),
  column({ title: '归属部门', key: 'department', width: 160, ellipsis: true, render: (row: any) => deptName(row.department) }),
  column({ title: '归属BU', key: 'bu', width: 160, ellipsis: true, render: (row: any) => deptName(row.bu) }),
  column({ title: '导师', key: 'mentor', width: 140, render: (row: any) => (row.mentor != null ? String(row.mentor) : '-') }),
  column({ title: '平台', key: 'platform', width: 120, render: (row: any) => dictLabel(platformOptions.value, row.platform) }),
  column({ title: '品牌', key: 'brand', width: 110, render: (row: any) => dictLabel(brandOptions.value, row.brand) }),
  column({ title: '地点', key: 'location', width: 100, render: (row: any) => dictLabel(locationOptions.value, row.location) }),
  column({ title: '容量', key: 'capacity', width: 80, render: (row: any) => row.capacity ?? '-' }, 'numeric'),
  column({ title: '社招人数', key: 'socialCount', width: 90, render: (row: any) => row.socialCount ?? 0 }, 'numeric'),
  column({ title: '校招占用', key: 'campusCount', width: 90, render: (row: any) => row.campusCount ?? 0 }, 'numeric'),
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
              default: () => '确认删除该直播间？',
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
