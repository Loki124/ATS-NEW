<template>
  <div class="page-container">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">轮岗安排</h1>
          <p class="page-subtitle">校招生轮岗生命周期管理（待分配 / 轮岗中 / 完成）</p>
        </div>
      </div>

      <n-tabs v-model:value="activeStage" type="line" @update:value="onTabChange">
        <n-tab-pane name="PENDING" tab="待分配" />
        <n-tab-pane name="ONGOING" tab="轮岗中" />
        <n-tab-pane name="DONE" tab="完成" />
      </n-tabs>

      <div class="toolbar">
        <n-input
          v-model:value="searchText"
          placeholder="搜索备注"
          clearable
          class="rule-filter-search"
        >
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <div class="spacer"></div>
        <n-button :disabled="!checkedRowKeys.length" @click="openBatch">
          批量调整（{{ checkedRowKeys.length }}）
        </n-button>
        <n-button type="primary" @click="openCreate">
          <template #icon><n-icon :component="AddOutline" /></template>
          新建轮岗安排
        </n-button>
      </div>

      <div class="table-wrap">
        <n-data-table
        v-model:checked-row-keys="checkedRowKeys"
        :data="list"
        :columns="columns"
        :row-key="(row: any) => row.id"
          :loading="loading"
          :pagination="pagination()"
          :bordered="false"
          flex-height
        >
          <template #empty><n-empty description="暂无轮岗安排" /></template>
        </n-data-table>
      </div>

      <!-- 新建 / 编辑 弹窗 -->
      <n-modal
        v-model:show="modalVisible"
        preset="card"
        :title="editing ? '编辑轮岗安排' : '新建轮岗安排'"
        :style="{ width: '720px' }"
        :mask-closable="false"
      >
        <n-form :model="formState" label-placement="top">
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="校招生" required>
                <n-select
                  v-model:value="formState.person"
                  :options="personOptions"
                  placeholder="搜索并选择校招生"
                  clearable
                  filterable
                  remote
                  :on-search="onPersonSearch"
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="意向BU（二级部门）">
                <n-select v-model:value="formState.intentBu" :options="buOpts" placeholder="请选择意向BU" clearable filterable />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="建议部门">
                <n-tree-select v-model:value="formState.suggestDept" :options="deptTreeOptions" :render-label="renderDeptLabel" placeholder="请选择建议部门" clearable filterable />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="当前轮岗部门">
                <n-tree-select v-model:value="formState.currentDept" :options="deptTreeOptions" :render-label="renderDeptLabel" placeholder="请选择当前部门" clearable filterable />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="建议导师（校园导师）">
                <n-select v-model:value="formState.suggestMentor" :options="mentorOptions" placeholder="请选择建议导师" clearable filterable remote :on-search="onMentorSearch" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="导师（校园导师）">
                <n-select v-model:value="formState.mentor" :options="mentorOptions" placeholder="请选择导师" clearable filterable remote :on-search="onMentorSearch" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="班主任（班主任身份）">
                <n-select v-model:value="formState.headTeacher" :options="headTeacherOptions" placeholder="请选择班主任" clearable filterable remote :on-search="onHeadTeacherSearch" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="直属上级">
                <n-select v-model:value="formState.directManager" :options="userOptions" placeholder="请选择直属上级" clearable filterable remote :on-search="onUserSearch" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="班级">
                <n-select v-model:value="formState.classRoom" :options="classRoomOptions" placeholder="请选择班级" clearable filterable remote :on-search="onClassRoomSearch" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="阶段" required>
                <n-select v-model:value="formState.stage" :options="stageOptions" placeholder="请选择阶段" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="员工状态">
                <n-input v-model:value="formState.employeeStatus" placeholder="如 在职 / 待入职" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="排名">
                <n-input-number v-model:value="formState.rank" :min="0" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="轮岗开始">
                <n-date-picker v-model:value="rotationStartTs" type="date" clearable style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="轮岗结束">
                <n-date-picker v-model:value="rotationEndTs" type="date" clearable style="width: 100%" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="定岗去向">
                <n-input v-model:value="formState.finalDept" placeholder="定岗去向" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="轮岗结果">
                <n-input v-model:value="formState.result" placeholder="优 / 良 / 中 / 差" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-form-item label="备注">
            <n-input v-model:value="formState.note" type="textarea" placeholder="备注" />
          </n-form-item>
        </n-form>

        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
            <n-button @click="modalVisible = false">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="save">保存</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 批量调整 弹窗 -->
      <n-modal
        v-model:show="batchVisible"
        preset="card"
        title="批量调整"
        :style="{ width: '520px' }"
        :mask-closable="false"
      >
        <n-form label-placement="top">
          <n-form-item label="调整阶段（可选）">
            <n-select v-model:value="batchForm.stage" :options="stageOptions" placeholder="不调整" clearable />
          </n-form-item>
          <n-form-item label="调整当前部门（可选）">
            <n-tree-select v-model:value="batchForm.currentDept" :options="deptTreeOptions" :render-label="renderDeptLabel" placeholder="不调整" clearable filterable />
          </n-form-item>
          <n-form-item label="调整班主任（可选）">
            <n-select v-model:value="batchForm.headTeacher" :options="headTeacherOptions" placeholder="不调整" clearable filterable remote :on-search="onHeadTeacherSearch" />
          </n-form-item>
        </n-form>
        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
            <n-button @click="batchVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submitBatch">应用到 {{ checkedRowKeys.length }} 条</n-button>
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
  NTabs,
  NTabPane,
  NDatePicker,
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
  searchPersons,
  searchClassRooms,
  type SelectOption,
} from '../../utils/campus'

const message = useMessage()
const deptStore = useDepartmentStore()

const STAGE_MAP: Record<string, { type: any; label: string }> = {
  PENDING: { type: 'warning', label: '待分配' },
  APPROVING: { type: 'info', label: '审批中' },
  ONGOING: { type: 'success', label: '轮岗中' },
  DONE: { type: 'default', label: '完成' },
  TERMINATED: { type: 'error', label: '终止' },
}
const stageOptions: SelectOption[] = Object.entries(STAGE_MAP).map(([value, v]) => ({ label: v.label, value }))

const list = ref<any[]>([])
const loading = ref(false)
const searchText = ref('')
const activeStage = ref<string>('PENDING')
const checkedRowKeys = ref<string[]>([])

const modalVisible = ref(false)
const editing = ref<any | null>(null)
const saving = ref(false)

const batchVisible = ref(false)
const batchForm = reactive({ stage: null as string | null, currentDept: null as string | null, headTeacher: null as string | null })

const personOptions = ref<SelectOption[]>([])
const mentorOptions = ref<SelectOption[]>([])
const headTeacherOptions = ref<SelectOption[]>([])
const userOptions = ref<SelectOption[]>([])
const classRoomOptions = ref<SelectOption[]>([])
const classRoomNameMap = ref<Record<string, string>>({})

const deptTreeOptions = computed(() => buildDeptTree(deptStore.departments))
const levelMap = computed(() => deptLevelMap(deptStore.departments))
const buOpts = computed(() => buOptions(deptStore.departments, levelMap.value))

function renderDeptLabel({ option }: { option: any }) {
  return h('span', option.name)
}

// 日期选择器用时间戳，提交时转 YYYY-MM-DD
const rotationStartTs = ref<number | null>(null)
const rotationEndTs = ref<number | null>(null)
const toDateStr = (ts: number | null) => (ts ? new Date(ts).toISOString().slice(0, 10) : null)

const emptyForm = () => ({
  id: null as string | null,
  person: null as string | null,
  intentBu: null as string | null,
  suggestDept: null as string | null,
  currentDept: null as string | null,
  suggestMentor: null as string | null,
  mentor: null as string | null,
  headTeacher: null as string | null,
  directManager: null as string | null,
  classRoom: null as string | null,
  stage: 'PENDING',
  employeeStatus: '',
  rank: null as number | null,
  finalDept: '',
  result: '',
  note: '',
})
const formState = reactive(emptyForm())

const onPersonSearch = async (kw: string) => { personOptions.value = await searchPersons(kw) }
const onMentorSearch = async (kw: string) => { mentorOptions.value = await searchUsers(kw, 'campus_mentor') }
const onHeadTeacherSearch = async (kw: string) => { headTeacherOptions.value = await searchUsers(kw, 'head_teacher') }
const onUserSearch = async (kw: string) => { userOptions.value = await searchUsers(kw) }
const onClassRoomSearch = async (kw: string) => {
  classRoomOptions.value = await searchClassRooms(kw)
  classRoomOptions.value.forEach((o) => { classRoomNameMap.value[o.value] = o.label })
}

const loadClassRooms = async () => {
  try {
    const resp = await api.get('/campus-rotation/class-rooms/', { params: { page: 1, page_size: 200 } })
    const arr = extractList(resp)
    arr.forEach((c: any) => { classRoomNameMap.value[String(c.id)] = c.name || c.code || String(c.id) })
  } catch { /* 非关键 */ }
}

const loadList = async () => {
  loading.value = true
  try {
    const params: Record<string, any> = { page: 1, page_size: 200, stage: activeStage.value }
    if (searchText.value.trim()) params.search = searchText.value.trim()
    const resp = await api.get('/campus-rotation/rotation-arrangements/', { params })
    list.value = extractList(resp)
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    loading.value = false
  }
}

const onTabChange = () => { checkedRowKeys.value = []; loadList() }

const openCreate = () => {
  Object.assign(formState, emptyForm())
  rotationStartTs.value = null
  rotationEndTs.value = null
  editing.value = null
  personOptions.value = []
  mentorOptions.value = []
  headTeacherOptions.value = []
  userOptions.value = []
  modalVisible.value = true
}

const openEdit = (row: any) => {
  Object.assign(formState, emptyForm(), {
    id: row.id,
    person: row.personId != null ? String(row.personId) : null,
    intentBu: row.intentBu != null ? String(row.intentBu) : null,
    suggestDept: row.suggestDept != null ? String(row.suggestDept) : null,
    currentDept: row.currentDept != null ? String(row.currentDept) : null,
    suggestMentor: row.suggestMentor != null ? String(row.suggestMentor) : null,
    mentor: row.mentor != null ? String(row.mentor) : null,
    headTeacher: row.headTeacher != null ? String(row.headTeacher) : null,
    directManager: row.directManager != null ? String(row.directManager) : null,
    classRoom: row.classRoom != null ? String(row.classRoom) : null,
    stage: row.stage || 'PENDING',
    employeeStatus: row.employeeStatus || '',
    rank: row.rank ?? null,
    finalDept: row.finalDept || '',
    result: row.result || '',
    note: row.note || '',
  })
  rotationStartTs.value = row.rotationStart ? new Date(row.rotationStart).getTime() : null
  rotationEndTs.value = row.rotationEnd ? new Date(row.rotationEnd).getTime() : null
  editing.value = row
  personOptions.value = row.personId != null ? [{ label: String(row.personId), value: String(row.personId) }] : []
  mentorOptions.value = row.mentor != null ? [{ label: String(row.mentor), value: String(row.mentor) }] : []
  headTeacherOptions.value = row.headTeacher != null ? [{ label: String(row.headTeacher), value: String(row.headTeacher) }] : []
  userOptions.value = row.directManager != null ? [{ label: String(row.directManager), value: String(row.directManager) }] : []
  if (row.classRoom != null) classRoomNameMap.value[String(row.classRoom)] = String(row.classRoom)
  modalVisible.value = true
}

const save = async () => {
  if (!formState.person) {
    message.warning('请选择校招生')
    return
  }
  saving.value = true
  const payload: any = {
    personId: Number(formState.person),
    intentBu: formState.intentBu,
    suggestDept: formState.suggestDept,
    currentDept: formState.currentDept,
    suggestMentor: formState.suggestMentor,
    mentor: formState.mentor,
    headTeacher: formState.headTeacher,
    directManager: formState.directManager,
    classRoom: formState.classRoom,
    stage: formState.stage,
    employeeStatus: formState.employeeStatus,
    rotationStart: toDateStr(rotationStartTs.value),
    rotationEnd: toDateStr(rotationEndTs.value),
    rank: formState.rank,
    finalDept: formState.finalDept,
    result: formState.result,
    note: formState.note,
  }
  try {
    if (editing.value) {
      await api.put(`/campus-rotation/rotation-arrangements/${editing.value.id}/`, payload)
      message.success('更新成功')
    } else {
      await api.post('/campus-rotation/rotation-arrangements/', payload)
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
    await api.delete(`/campus-rotation/rotation-arrangements/${row.id}/`)
    message.success('已删除')
    loadList()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

const openBatch = () => {
  batchForm.stage = null
  batchForm.currentDept = null
  batchForm.headTeacher = null
  batchVisible.value = true
}

const submitBatch = async () => {
  if (!checkedRowKeys.value.length) return
  const hasAny = batchForm.stage || batchForm.currentDept || batchForm.headTeacher
  if (!hasAny) {
    message.warning('请至少选择一个调整项')
    return
  }
  saving.value = true
  const payload: any = { ids: checkedRowKeys.value }
  if (batchForm.stage) payload.stage = batchForm.stage
  if (batchForm.currentDept) payload.currentDept = batchForm.currentDept
  if (batchForm.headTeacher) payload.headTeacher = batchForm.headTeacher
  try {
    const resp = await api.post('/campus-rotation/rotation-arrangements/batch-assign/', payload)
    const updated = resp?.data?.data?.updated
    message.success(`已更新 ${updated ?? checkedRowKeys.value.length} 条`)
    batchVisible.value = false
    checkedRowKeys.value = []
    loadList()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    saving.value = false
  }
}

const deptName = (id: any) => (id != null ? deptStore.getById(String(id))?.name || String(id) : '-')
const userName = (id: any, cache?: Record<string, string>) => {
  if (id == null) return '-'
  const s = String(id)
  return cache?.[s] || s
}

const columns = [
  { type: 'selection' as const, width: 40 },
  { title: '校招生ID', key: 'personId', width: 110, render: (row: any) => row.personId ?? '-' },
  { title: '意向BU', key: 'intentBu', width: 140, ellipsis: true, render: (row: any) => deptName(row.intentBu) },
  { title: '当前部门', key: 'currentDept', width: 140, ellipsis: true, render: (row: any) => deptName(row.currentDept) },
  { title: '班主任', key: 'headTeacher', width: 120, render: (row: any) => userName(row.headTeacher) },
  { title: '直属上级', key: 'directManager', width: 120, render: (row: any) => userName(row.directManager) },
  { title: '班级', key: 'classRoom', width: 120, render: (row: any) => userName(row.classRoom, classRoomNameMap.value) },
  {
    title: '阶段',
    key: 'stage',
    width: 100,
    render: (row: any) => {
      const m = STAGE_MAP[row.stage] || { type: 'default', label: row.stage }
      return h(NTag, { type: m.type, size: 'small' }, { default: () => m.label })
    },
  },
  { title: '员工状态', key: 'employeeStatus', width: 100, render: (row: any) => row.employeeStatus || '-' },
  { title: '定岗去向', key: 'finalDept', width: 100, render: (row: any) => row.finalDept || '-' },
  { title: '结果', key: 'result', width: 80, render: (row: any) => row.result || '-' },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    fixed: 'right' as const,
    render: (row: any) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openEdit(row) }, { default: () => '编辑', icon: () => h(NIcon, null, { default: () => h(CreateOutline) }) }),
          h(NPopconfirm, { onPositiveClick: () => remove(row), positiveText: '确认', negativeText: '取消' }, {
            default: () => '确认删除该安排？',
            trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'error' }, { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) }),
          }),
        ],
      }),
  },
]

const pagination = () => ({ pageSize: 50, showSizePicker: false })

onMounted(() => {
  deptStore.loadDepartments()
  loadClassRooms()
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
