<template>
  <div class="page-container">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">校招生档案</h1>
          <p class="page-subtitle">校招生人员主数据（姓名 / 工号 / 班级 / 班主任 / 院校 / 专业 / 入职日期）</p>
        </div>
      </div>

      <n-alert type="info" :bordered="false" class="scope-alert">
        <template #icon><n-icon :component="InformationCircleOutline" /></template>
        本页仅维护<strong>校招生档案</strong>。内部账号的新建/停用/身份授权属于「权限管理 · 用户管理」，请前往该处操作。
      </n-alert>

      <div class="toolbar">
        <n-input
          v-model:value="searchText"
          placeholder="搜索编号 / 姓名"
          clearable
          class="rule-filter-search"
          @keyup.enter="reload"
        >
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <n-select
          v-model:value="filterBu"
          :options="buChoices"
          placeholder="全部部门"
          clearable
          class="filter-select"
        />
        <div class="spacer"></div>
        <n-button type="primary" :loading="loading" @click="reload">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
        <n-button type="primary" @click="openCreate">
          <template #icon><n-icon :component="AddOutline" /></template>
          新建档案
        </n-button>
      </div>

      <n-tabs
        :value="activeTab"
        type="line"
        justify="start"
        class="status-tabs"
        @update:value="onTabChange"
      >
        <n-tab-pane
          v-for="t in statusTabs"
          :key="t.value"
          :name="t.value"
          :tab="t.label"
        />
      </n-tabs>

      <div class="table-wrap">
        <n-data-table
          :data="list"
          :columns="columns"
          :row-key="(row: any) => row.id"
          :loading="loading"
          :pagination="{ pageSize: 50 }"
          :bordered="false"
          flex-height
        >
          <template #empty>
            <n-empty description="暂无校招生档案" />
          </template>
        </n-data-table>
      </div>

      <n-modal
        v-model:show="modalVisible"
        preset="card"
        :title="editing ? '编辑校招生档案' : '新建校招生档案'"
        :style="{ width: '720px' }"
        :mask-closable="false"
      >
        <n-form :model="formState" label-placement="top">
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="候选人编号">
                <n-input
                  :value="editing ? formState.code : '自动生成（C+8位）'"
                  readonly
                  placeholder="自动生成"
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="姓名" required>
                <n-input v-model:value="formState.name" placeholder="请输入姓名" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="工号">
                <n-input v-model:value="formState.employeeId" placeholder="入职后补录" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="班级">
                <n-select
                  v-model:value="formState.classRoom"
                  :options="classRoomOptions"
                  placeholder="请选择班级"
                  clearable
                  filterable
                  remote
                  :on-search="onClassRoomSearch"
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="部门" required>
                <n-select
                  v-model:value="formState.bu"
                  :options="buChoices"
                  placeholder="请选择部门"
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="状态" required>
                <n-select
                  v-model:value="formState.status"
                  :options="statusChoices"
                  placeholder="请选择状态"
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="班主任">
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
              <n-form-item label="院校标签">
                <n-select v-model:value="formState.school" :options="schoolChoices" clearable />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="专业标签">
                <n-select v-model:value="formState.major" :options="majorChoices" clearable />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="性别">
                <n-select v-model:value="formState.sex" :options="sexChoices" clearable />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="招聘月份">
                <n-input v-model:value="formState.month" placeholder="如 8月" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="职务">
                <n-select v-model:value="formState.position" :options="positionChoices" clearable />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="职级">
                <n-select v-model:value="formState.level" :options="levelChoices" clearable />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="预计入职日期">
                <n-date-picker
                  v-model:value="formState.expectedEntryDate"
                  type="date"
                  clearable
                  style="width: 100%"
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="实际入职日期">
                <n-date-picker
                  v-model:value="formState.actualEntryDate"
                  type="date"
                  clearable
                  style="width: 100%"
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-form-item label="计入核算">
            <n-switch v-model:value="formState.counted" />
          </n-form-item>
        </n-form>

        <template #footer>
          <div class="modal-footer">
            <n-button @click="modalVisible = false">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="save">
              保存
            </n-button>
          </div>
        </template>
      </n-modal>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 校招生档案页（校园招聘 · 人员管理）。
 *
 * 边界（重要）：本页只维护校招生人员主数据（apps/campus_control.Person），
 * **不涉及内部账号的新建/停用/删除、不涉及角色身份授权** —— 那些属于
 * 「权限管理 · 用户管理」，是权限域，权限码 recruit:settings:users:*。
 * 本页权限码为校招域 recruit:campus:person:*。
 */
import { ref, reactive, h, computed, onMounted } from 'vue'
import {
  NAlert,
  NButton,
  NDataTable,
  NDatePicker,
  NEmpty,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NIcon,
  NInput,
  NModal,
  NPopconfirm,
  NSelect,
  NSpace,
  NSwitch,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
} from 'naive-ui'
import {
  AddOutline,
  CreateOutline,
  InformationCircleOutline,
  RefreshOutline,
  SearchOutline,
  TrashOutline,
} from '@vicons/ionicons5'
import { api } from '../../utils/request'
import {
  extractList,
  extractError,
  searchUsers,
  searchClassRooms,
  DEPTS,
  SCHOOLS,
  MAJORS,
  SEXES,
  STATUS,
  POSITIONS,
  LEVELS,
  type SelectOption,
} from '../../utils/campus'
import { column } from '../../composables/useTableColumns'

const message = useMessage()

const list = ref<any[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const editing = ref<any | null>(null)
const saving = ref(false)

const searchText = ref('')
const filterBu = ref<string | null>(null)

// S5-05（需求 2-1）：状态页签，待入职独立展示。value='' = 全部；'待入职' 映射后端 '在途待入职'
const statusTabs = [
  { label: '全部', value: '' },
  { label: '在职', value: '在职' },
  { label: '待入职', value: '在途待入职' },
  { label: '在途Offer', value: '在途Offer' },
  { label: '候选池', value: '候选池' },
]
const activeTab = ref<string>('')
const onTabChange = (v: string) => {
  activeTab.value = v
  reload()
}

// 枚举单一真源见 utils/campus（与后端 apps/campus_control/constants.py 保持一致，G-08 已收敛）

const toChoices = (arr: string[]) => arr.map((v) => ({ label: v, value: v }))
const buChoices = toChoices(DEPTS)
const schoolChoices = toChoices(SCHOOLS)
const majorChoices = toChoices(MAJORS)
const sexChoices = toChoices(SEXES)
const statusChoices = toChoices(STATUS)
const positionChoices = toChoices(POSITIONS)
const levelChoices = toChoices(LEVELS)

const emptyForm = () => ({
  id: null as string | null,
  code: '',
  name: '',
  employeeId: '',
  bu: null as string | null,
  school: null as string | null,
  major: null as string | null,
  sex: null as string | null,
  month: '',
  status: '候选池' as string,
  position: '' as string,
  level: '' as string,
  headTeacher: null as string | null,
  classRoom: null as string | null,
  expectedEntryDate: null as number | null,
  actualEntryDate: null as number | null,
  counted: true,
})
const formState = reactive(emptyForm())

// S5-04：班级 / 班主任 远程搜索（复用 utils/campus.searchClassRooms / searchUsers）
const classRoomOptions = ref<SelectOption[]>([])
const headTeacherOptions = ref<SelectOption[]>([])
const onClassRoomSearch = async (kw: string) => {
  classRoomOptions.value = await searchClassRooms(kw)
}
const onHeadTeacherSearch = async (kw: string) => {
  headTeacherOptions.value = await searchUsers(kw)
}

/** 后端日期字段接受 YYYY-MM-DD；空值统一转 null，避免传空串触发 400。 */
const toDateStr = (ts: number | null): string | null => {
  if (!ts) return null
  const d = new Date(ts)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

const loadList = async () => {
  loading.value = true
  try {
    const params: Record<string, any> = { page: 1, page_size: 200 }
    if (searchText.value.trim()) params.search = searchText.value.trim()
    if (filterBu.value) params.bu = filterBu.value
    if (activeTab.value) params.status = activeTab.value
    const resp = await api.get('/campus/persons/', { params })
    list.value = extractList(resp)
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    loading.value = false
  }
}

const reload = () => loadList()

const openCreate = () => {
  Object.assign(formState, emptyForm())
  editing.value = null
  modalVisible.value = true
}

const openEdit = (row: any) => {
  Object.assign(formState, emptyForm(), {
    id: row.id,
    code: row.code,
    name: row.name || '',
    employeeId: row.employeeId || '',
    bu: row.bu || null,
    school: row.school || null,
    major: row.major || null,
    sex: row.sex || null,
    month: row.month || '',
    status: row.status || '候选池',
    position: row.position || '',
    level: row.level || '',
    headTeacher: row.headTeacher != null ? String(row.headTeacher) : null,
    classRoom: row.classRoom != null ? String(row.classRoom) : null,
    expectedEntryDate: row.expectedEntryDate ? new Date(row.expectedEntryDate).getTime() : null,
    actualEntryDate: row.actualEntryDate ? new Date(row.actualEntryDate).getTime() : null,
    counted: row.counted !== false,
  })
  editing.value = row
  // 预置已选班级 / 班主任，保证编辑时选择器回显当前值
  classRoomOptions.value = row.classRoom != null
    ? [{ label: row.classRoomName || String(row.classRoom), value: String(row.classRoom) }]
    : []
  headTeacherOptions.value = row.headTeacher != null
    ? [{ label: row.headTeacherName || String(row.headTeacher), value: String(row.headTeacher) }]
    : []
  modalVisible.value = true
}

const save = async () => {
  if (!formState.name.trim()) {
    message.warning('请填写姓名')
    return
  }
  if (!formState.bu) {
    message.warning('请选择部门')
    return
  }
  saving.value = true
  const payload: any = {
    name: formState.name.trim(),
    employee_id: formState.employeeId || '',
    bu: formState.bu,
    school: formState.school || '',
    major: formState.major || '',
    sex: formState.sex || '',
    month: formState.month || '',
    status: formState.status,
    position: formState.position || '',
    level: formState.level || '',
    head_teacher: formState.headTeacher,
    class_room: formState.classRoom,
    expectedEntryDate: toDateStr(formState.expectedEntryDate),
    actualEntryDate: toDateStr(formState.actualEntryDate),
    counted: formState.counted,
  }
  try {
    if (editing.value) {
      await api.put(`/campus/persons/${editing.value.id}/`, payload)
      message.success('更新成功')
    } else {
      await api.post('/campus/persons/', payload)
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
    await api.delete(`/campus/persons/${row.id}/`)
    message.success('已删除该档案')
    loadList()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

const statusTagType = (s: string) => {
  if (s === '在职') return 'success'
  if (s === '在途待入职' || s === '在途Offer') return 'warning'
  return 'default'
}

// S5-04（需求 2-2）：列顺序 = 姓名→工号→在职状态→入职时间→班级→班主任→部门→职务→职级→性别→院校→专业
// D-02：隐藏「候选人编号」列（库字段 code 保留）。
// 新增：工号(employeeId) / 班级(classRoomName) / 班主任(headTeacherName)
// S5-08：列对齐接入 useTableColumns 单一真源（数据列表尽量居中，操作列 control 档）
const columns = [
  column({ title: '姓名', key: 'name', width: 110, render: (row: any) => row.name || '-' }),
  column({ title: '工号', key: 'employeeId', width: 120, render: (row: any) => row.employeeId || '-' }),
  column(
    {
      title: '在职状态', key: 'status', width: 110,
      render: (row: any) =>
        h(NTag, { type: statusTagType(row.status), size: 'small' }, { default: () => row.status || '-' }),
    },
    'short',
  ),
  column({ title: '入职时间', key: 'actualEntryDate', width: 120, render: (row: any) => row.actualEntryDate || '-' }),
  column({ title: '班级', key: 'classRoomName', width: 140, ellipsis: true, render: (row: any) => row.classRoomName || '-' }),
  column({ title: '班主任', key: 'headTeacherName', width: 120, render: (row: any) => row.headTeacherName || '-' }),
  column({ title: '部门', key: 'bu', width: 110, render: (row: any) => row.bu || '-' }),
  column({ title: '职务', key: 'position', width: 100, render: (row: any) => row.position || '-' }),
  column({ title: '职级', key: 'level', width: 80, render: (row: any) => row.level || '-' }),
  column({ title: '性别', key: 'sex', width: 70, render: (row: any) => row.sex || '-' }),
  column({ title: '院校', key: 'school', width: 90, render: (row: any) => row.school || '-' }),
  column({ title: '专业', key: 'major', width: 90, render: (row: any) => row.major || '-' }),
  column(
    {
      title: '操作', key: 'actions', width: 140, fixed: 'right' as const,
      render: (row: any) =>
        h(NSpace, { size: 8, wrap: false }, {
          default: () => [
            h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openEdit(row) },
              { default: () => '编辑', icon: () => h(NIcon, null, { default: () => h(CreateOutline) }) }),
            h(NPopconfirm, { onPositiveClick: () => remove(row), positiveText: '确认', negativeText: '取消' }, {
              default: () => '确认删除该校招生档案？',
              trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'error' },
                { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) }),
            }),
          ],
        }),
    },
    'control',
  ),
]

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
.scope-alert {
  flex-shrink: 0;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
/* S5-05：状态页签栏（替代原状态下拉）；与工具栏分离成独立一行 */
.status-tabs {
  margin: 0 0 var(--space-2);
}
/* 本页有 9 个筛选下拉，为控制工具栏单行不换行，搜索框收窄至 220px
 * （全局 .rule-filter-search 为 240px）。属有意例外，非遗漏。 */
.rule-filter-search {
  width: 220px;
}
.filter-select {
  width: 150px;
}
.spacer {
  flex: 1;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
