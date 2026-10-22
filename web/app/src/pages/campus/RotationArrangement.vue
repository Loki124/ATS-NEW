<template>
  <div class="page-container">
    <div class="page-body">
      <!-- 校招生管理列表页统一去标题：页面身份由顶部导航承载，页签已表明当前视图 -->

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
        <CampusMockBar :is-mock="isMock" @change="loadList" />
        <n-button :disabled="!checkedRowKeys.length || isMock" @click="openBatch">
          批量调整（{{ checkedRowKeys.length }}）
        </n-button>
        <n-button type="primary" :disabled="isMock" @click="openCreate">
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
          :scroll-x="TABLE_SCROLL_X"
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
        :content-style="{ height: 'min(680px, calc(88vh - 140px))', overflowY: 'auto' }"
        :mask-closable="false"
      >
        <n-form :model="formState" label-placement="top">
          <!-- ① 基本信息（校招生主数据：选人后自动回填，只读） -->
          <div class="form-section">
            <div class="form-section-title">基本信息</div>
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="姓名" required>
                  <n-select
                    v-model:value="formState.person"
                    :options="personOptions"
                    placeholder="搜索并选择校招生"
                    clearable
                    filterable
                    remote
                    :on-search="onPersonSearch"
                    @update:value="onPersonChange"
                  />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="工号">
                  <n-input :value="formState.personEmployeeId" placeholder="选人后自动回填" readonly />
                </n-form-item>
              </n-grid-item>
            </n-grid>
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="教育经历">
                  <n-input :value="formState.personEducation" placeholder="选人后自动回填" readonly />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="预计入职日期">
                  <n-input :value="formState.personExpectedEntryDate" placeholder="选人后自动回填" readonly />
                </n-form-item>
              </n-grid-item>
            </n-grid>
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="入职日期">
                  <n-input :value="formState.personActualEntryDate" placeholder="选人后自动回填" readonly />
                </n-form-item>
              </n-grid-item>
            </n-grid>
          </div>

          <!-- ② 批次&班级（选班级后批次自动回填） -->
          <div class="form-section">
            <div class="form-section-title">批次&amp;班级</div>
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="批次">
                  <n-input v-model:value="formState.batch" placeholder="如 2026秋招（选班级可自动带入）" />
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
                    @update:value="onClassRoomChange"
                  />
                </n-form-item>
              </n-grid-item>
            </n-grid>
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="班主任">
                  <n-select v-model:value="formState.headTeacher" :options="headTeacherOptions" placeholder="请选择班主任" clearable filterable remote :on-search="onHeadTeacherSearch" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="班长">
                  <n-select v-model:value="formState.classMonitor" :options="userOptions" placeholder="请选择班长" clearable filterable remote :on-search="onUserSearch" />
                </n-form-item>
              </n-grid-item>
            </n-grid>
          </div>

          <!-- ③ 轮岗信息（2026-10-22 兵哥指令：直播间 + 客服部门合并为「轮岗资源」→
               原「轮岗位置」单选 + 「具体位置」级联下拉，合并为单个资源下拉，按资源类型分组；
               选资源后轮岗部门自动填充为该资源的归属部门） -->
          <div class="form-section">
            <div class="form-section-title">轮岗信息</div>
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="意向部门">
                  <n-select v-model:value="formState.intentBu" :options="buOpts" placeholder="请选择意向部门" clearable filterable />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="轮岗资源">
                  <n-select
                    v-model:value="formState.resource"
                    :options="resourceOptions"
                    placeholder="请选择轮岗资源"
                    clearable
                    filterable
                    @update:value="onResourceChange"
                  />
                </n-form-item>
              </n-grid-item>
            </n-grid>
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="轮岗部门">
                  <n-tree-select v-model:value="formState.currentDept" :options="deptTreeOptions" :render-label="renderDeptLabel" :placeholder="currentDeptPlaceholder" clearable filterable />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="带教导师">
                  <n-select v-model:value="formState.mentor" :options="mentorOptions" placeholder="请选择带教导师" clearable filterable remote :on-search="onMentorSearch" />
                </n-form-item>
              </n-grid-item>
            </n-grid>
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item :span="2">
                <n-form-item label="轮岗起止日期">
                  <n-space :wrap="false" :size="8" style="width: 100%">
                    <n-date-picker v-model:value="rotationStartTs" type="date" clearable style="flex: 1" />
                    <n-date-picker v-model:value="rotationEndTs" type="date" clearable style="flex: 1" />
                  </n-space>
                </n-form-item>
              </n-grid-item>
            </n-grid>
          </div>

          <!-- ④ 其他（建议/直属上级/阶段/结果等既有字段） -->
          <div class="form-section">
            <div class="form-section-title">其他信息</div>
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="建议部门">
                  <n-tree-select v-model:value="formState.suggestDept" :options="deptTreeOptions" :render-label="renderDeptLabel" placeholder="请选择建议部门" clearable filterable />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="建议导师（校园导师）">
                  <n-select v-model:value="formState.suggestMentor" :options="mentorOptions" placeholder="请选择建议导师" clearable filterable remote :on-search="onMentorSearch" />
                </n-form-item>
              </n-grid-item>
            </n-grid>
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="直属上级">
                  <n-select v-model:value="formState.directManager" :options="userOptions" placeholder="请选择直属上级" clearable filterable remote :on-search="onUserSearch" />
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
          </div>
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
import CampusMockBar from '../../components/campus/CampusMockBar.vue'
import { useCampusMock } from '../../composables/useCampusMock'
import { MOCK_ROTATION_ARRANGEMENTS, resolveDeptRefs } from '../../mocks/campus'
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
/** 班级原始记录（回填批次） */
const classRoomMap = ref<Record<string, any>>({})

const deptTreeOptions = computed(() => buildDeptTree(deptStore.departments))
const levelMap = computed(() => deptLevelMap(deptStore.departments))
const buOpts = computed(() => buOptions(deptStore.departments, levelMap.value))

// 示例数据（真实为空时兜底；只读，页面已禁用新建/编辑/删除/批量调整）
const { pick, isMock, isMockOnly } = useCampusMock()
const mockRows = computed(() => {
  let rows = resolveDeptRefs(MOCK_ROTATION_ARRANGEMENTS, deptStore.departments).filter(
    (r) => r.stage === activeStage.value,
  )
  const kw = searchText.value.trim()
  if (kw) rows = rows.filter((r) => String(r.note || '').includes(kw))
  return rows
})

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
  /**
   * 校招生是否为「历史账号 id 行」（只有旧口径 person_id、映射不到校招生档案）。
   * 这类行提交时**不覆盖**校招生关联，避免把历史数据冲成空。
   */
  personIsLegacy: false,
  // 基本信息（选人后回填，只读）
  personEmployeeId: '',
  personEducation: '',
  personExpectedEntryDate: '',
  personActualEntryDate: '',
  intentBu: null as string | null,
  suggestDept: null as string | null,
  currentDept: null as string | null,
  suggestMentor: null as string | null,
  mentor: null as string | null,
  headTeacher: null as string | null,
  classMonitor: null as string | null,
  directManager: null as string | null,
  classRoom: null as string | null,
  batch: '',
  // 轮岗资源（具体位置）：2026-10-22 直播间 + 客服部门合并后为**单个**资源 FK；
  // 「轮岗位置类型」由资源自身的 resource_type 决定，不再单独维护。
  resource: null as string | null,
  stage: 'PENDING',
  employeeStatus: '',
  rank: null as number | null,
  finalDept: '',
  result: '',
  note: '',
})
const formState = reactive(emptyForm())

/* ── 轮岗资源（具体位置）───────────────────────────────────────────── */
/** 资源类型 → 中文名（分组标题与展示口径，与后端枚举同源）。 */
const RESOURCE_TYPE_LABEL: Record<string, string> = {
  LIVE_ROOM: '直播间',
  SERVICE_DEPT: '客服部门',
  OTHER: '其他',
}
/** 轮岗资源原始记录（用于「轮岗部门」自动填充其归属部门） */
const resourceMap = ref<Record<string, any>>({})
const resourceRows = ref<any[]>([])

/** 分组下拉项（naive-ui 的 n-select 支持 children 分组；分组本身没有 value）。 */
interface ResourceGroupOption {
  label: string
  children: SelectOption[]
  [k: string]: any
}

/** 下拉选项：按资源类型分组（直播间 / 客服部门 / 其他）。 */
const resourceOptions = computed<ResourceGroupOption[]>(() => {
  const groups = new Map<string, SelectOption[]>()
  resourceRows.value.forEach((r: any) => {
    const type = String(r.resourceType || 'OTHER')
    const label = RESOURCE_TYPE_LABEL[type] || type
    if (!groups.has(label)) groups.set(label, [])
    groups.get(label)!.push({
      label: r.name || r.resourceNo || String(r.id),
      value: String(r.id),
    })
  })
  return [...groups.entries()].map(([label, children]) => ({ label, children }))
})

const currentDeptPlaceholder = computed(() =>
  formState.resource ? '选择轮岗资源后自动填充归属部门' : '请选择轮岗部门',
)

/** 选轮岗资源 → 轮岗部门自动填充为该资源的归属部门 */
const onResourceChange = (v: string | null) => {
  if (!v) return
  const deptId = resourceMap.value[String(v)]?.department
  if (deptId) formState.currentDept = String(deptId)
}

/**
 * 选班级 → 批次 / 班长 自动带入。
 * ⚠️ 2026-10-22：班级管理页已下线「批次 / 班主任 / HRBP」维护（模型字段仍在），
 *    新建班级不再有批次 → 这里取不到就留空，由 HR 手工填批次（字段可编辑）。
 */
const onClassRoomChange = (v: string | null) => {
  if (!v) {
    formState.batch = ''
    return
  }
  const cls = classRoomMap.value[String(v)]
  formState.batch = cls?.batch || ''
  // 班长随班级带入（班级管理页维护）；取不到则不动已有值
  const monitorId = cls?.classMonitor
  if (monitorId) {
    formState.classMonitor = String(monitorId)
    if (!userOptions.value.some((o) => o.value === String(monitorId))) {
      userOptions.value = [
        ...userOptions.value,
        { label: cls?.classMonitorName || String(monitorId), value: String(monitorId) },
      ]
    }
  }
}

/** 选校招生 → 基本信息自动回填（工号 / 教育经历 / 入职日期） */
const onPersonChange = (v: string | null) => {
  // 从真实校招生列表里选出来的 → 人员级关联；历史账号 id 选项 → 保持 legacy 标记
  const opt = personOptions.value.find((o) => o.value === v)
  formState.personIsLegacy = !!(v && !opt?.person)
  if (!v) {
    formState.personEmployeeId = ''
    formState.personEducation = ''
    formState.personExpectedEntryDate = ''
    formState.personActualEntryDate = ''
    return
  }
  const p = opt?.person
  if (!p) return
  formState.personEmployeeId = p.employeeId || ''
  formState.personEducation = p.education || ''
  formState.personExpectedEntryDate = p.expectedEntryDate || ''
  formState.personActualEntryDate = p.actualEntryDate || ''
}

const onPersonSearch = async (kw: string) => { personOptions.value = await searchPersons(kw) }
const onMentorSearch = async (kw: string) => { mentorOptions.value = await searchUsers(kw, 'campus_mentor') }
const onHeadTeacherSearch = async (kw: string) => { headTeacherOptions.value = await searchUsers(kw, 'head_teacher') }
const onUserSearch = async (kw: string) => { userOptions.value = await searchUsers(kw) }
const onClassRoomSearch = async (kw: string) => {
  classRoomOptions.value = await searchClassRooms(kw)
  classRoomOptions.value.forEach((o) => {
    classRoomNameMap.value[o.value] = o.label
    if ((o as any).classRoom) classRoomMap.value[o.value] = (o as any).classRoom
  })
}

const loadClassRooms = async () => {
  try {
    const resp = await api.get('/campus-rotation/class-rooms/', { params: { page: 1, page_size: 200 } })
    const arr = extractList(resp)
    arr.forEach((c: any) => {
      classRoomNameMap.value[String(c.id)] = c.name || c.code || String(c.id)
      classRoomMap.value[String(c.id)] = c
    })
  } catch { /* 非关键 */ }
}

/** 加载轮岗资源（具体位置的下拉选项；直播间 + 客服部门 + 其他 合一） */
const loadResources = async () => {
  try {
    const resp = await api.get('/campus-rotation/resources/', { params: { page: 1, page_size: 200 } })
    const rows = extractList(resp)
    resourceRows.value = rows
    rows.forEach((r: any) => { resourceMap.value[String(r.id)] = r })
  } catch { /* 非关键：轮岗资源可留空 */ }
}

const loadList = async () => {
  loading.value = true
  try {
    if (isMockOnly.value) {
      list.value = mockRows.value
      return
    }
    const params: Record<string, any> = { page: 1, page_size: 200, stage: activeStage.value }
    if (searchText.value.trim()) params.search = searchText.value.trim()
    const resp = await api.get('/campus-rotation/rotation-arrangements/', { params })
    list.value = pick(extractList(resp), mockRows.value)
  } catch (e: any) {
    // 接口失败：auto 模式用示例数据兜底
    list.value = pick([], mockRows.value)
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
  // 2026-10-22：校招生改用人员级关联（Person 主键 nanoid）。
  //   历史行只有旧口径 person_id（账号 id）且映射不到档案（迁移 0014 已尽量回填，
  //   剩下的是「孤儿行」）→ 标记 personIsLegacy，提交时不覆盖，保持原样。
  const hasCampusPerson = row.campusPerson != null && row.campusPerson !== ''
  const legacyPersonId = row.personId != null ? String(row.personId) : null
  Object.assign(formState, emptyForm(), {
    id: row.id,
    person: hasCampusPerson ? String(row.campusPerson) : legacyPersonId,
    personIsLegacy: !hasCampusPerson && legacyPersonId != null,
    // 基本信息：编辑态直接用行上带回来的校招生主数据（列表接口已补该字段）
    personEmployeeId: row.personEmployeeId || '',
    personEducation: row.personEducation || '',
    personExpectedEntryDate: row.personExpectedEntryDate || '',
    personActualEntryDate: row.personActualEntryDate || '',
    intentBu: row.intentBu != null ? String(row.intentBu) : null,
    suggestDept: row.suggestDept != null ? String(row.suggestDept) : null,
    currentDept: row.currentDept != null ? String(row.currentDept) : null,
    suggestMentor: row.suggestMentor != null ? String(row.suggestMentor) : null,
    mentor: row.mentor != null ? String(row.mentor) : null,
    headTeacher: row.headTeacher != null ? String(row.headTeacher) : null,
    classMonitor: row.classMonitor != null ? String(row.classMonitor) : null,
    directManager: row.directManager != null ? String(row.directManager) : null,
    classRoom: row.classRoom != null ? String(row.classRoom) : null,
    batch: row.batch || classRoomMap.value[String(row.classRoom)]?.batch || '',
    resource: row.resource != null ? String(row.resource) : null,
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
  personOptions.value = hasCampusPerson
    ? [{ label: row.personName || String(row.campusPerson), value: String(row.campusPerson) }]
    : (legacyPersonId != null
        ? [{ label: `历史关联（账号 id ${legacyPersonId}）`, value: legacyPersonId }]
        : [])
  mentorOptions.value = row.mentor != null ? [{ label: String(row.mentor), value: String(row.mentor) }] : []
  headTeacherOptions.value = row.headTeacher != null ? [{ label: String(row.headTeacher), value: String(row.headTeacher) }] : []
  userOptions.value = row.directManager != null ? [{ label: String(row.directManager), value: String(row.directManager) }] : []
  if (row.classMonitor != null) {
    userOptions.value = [
      ...userOptions.value,
      { label: row.classMonitorName || String(row.classMonitor), value: String(row.classMonitor) },
    ]
  }
  if (row.classRoom != null) classRoomNameMap.value[String(row.classRoom)] = String(row.classRoom)
  modalVisible.value = true
}

const save = async () => {
  // 示例数据二次守卫（与 CampusPerson/ClassRoom 同口径）：模板层 disabled 只挡点击，
  // 此处挡代码路径直入。示例行 id 是 MOCK_ 前缀假 id，落到后端必然 404。
  if (isMock.value) {
    message.warning('示例数据仅供查看，请切回真实数据后再操作')
    return
  }
  if (!formState.person) {
    message.warning('请选择校招生')
    return
  }
  saving.value = true
  const payload: any = {
    // 2026-10-22：校招生改用**人员级关联**（Person 主键 nanoid）提交。
    //   旧写法 `personId: Number(formState.person)` 有两个致命问题：
    //     ① 下拉 value 是 Person 的 nanoid 字符串 → Number(...) 得 NaN → 后端 400「校招生必须是整数」；
    //     ② person_id 语义是「校招生账号 id」，而校招生通常没有账号 → 定位不到人。
    //   后端收到 campus_person 后会自动把 person_id 镜像成该人的 user_id（无账号则为空）。
    //   历史行（只有旧口径账号 id、映射不到档案）→ 不提交校招生字段，保持原样不被冲掉。
    intentBu: formState.intentBu,
    suggestDept: formState.suggestDept,
    currentDept: formState.currentDept,
    suggestMentor: formState.suggestMentor,
    mentor: formState.mentor,
    headTeacher: formState.headTeacher,
    classMonitor: formState.classMonitor,
    batch: formState.batch,
    directManager: formState.directManager,
    classRoom: formState.classRoom,
    resource: formState.resource,
    stage: formState.stage,
    employeeStatus: formState.employeeStatus,
    rotationStart: toDateStr(rotationStartTs.value),
    rotationEnd: toDateStr(rotationEndTs.value),
    rank: formState.rank,
    finalDept: formState.finalDept,
    result: formState.result,
    note: formState.note,
  }
  // 校招生关联：人员级（nanoid）。历史行不提交，避免把旧口径账号 id 冲成空。
  if (!formState.personIsLegacy) payload.campusPerson = formState.person
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
  if (isMock.value) {
    message.warning('示例数据仅供查看，请切回真实数据后再操作')
    return
  }
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
  // 2026-10-22：person_id 是旧口径「校招生账号 id」（多数为空），主展示改为姓名/档案 id
  { title: '校招生', key: 'personName', width: 110, ellipsis: true, render: (row: any) => row.personName || (row.personId != null ? String(row.personId) : '-') },
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
    width: 168,
    fixed: 'right' as const,
    render: (row: any) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', disabled: isMock.value, onClick: () => openEdit(row) }, { default: () => '编辑', icon: () => h(NIcon, null, { default: () => h(CreateOutline) }) }),
          h(NPopconfirm, { onPositiveClick: () => remove(row), positiveText: '确认', negativeText: '取消' }, {
            default: () => '确认删除该安排？',
            trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'error', disabled: isMock.value }, { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) }),
          }),
        ],
      }),
  },
]

/**
 * 表格横向滚动宽度 = 各列 width 之和。
 * naive-ui 必须显式给 `scroll-x` 才会横向滚动；不给时列宽总和超出容器会被直接裁掉，
 * 且 `fixed:'right'` 的操作列会盖住相邻列（2026-10-21 样式优化，与档案页同口径）。
 */
const TABLE_SCROLL_X = columns.reduce((sum, c) => sum + (typeof c.width === 'number' ? c.width : 100), 0)

const pagination = () => ({ pageSize: 50, showSizePicker: false })

onMounted(() => {
  deptStore.loadDepartments()
  loadClassRooms()
  loadResources()
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
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.spacer {
  flex: 1;
}

/* ── 表单分组（基本信息 / 批次&班级 / 轮岗信息 / 其他信息）───────── */
.form-section {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--surface);
  margin-bottom: var(--space-3);
}
.form-section-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  padding-left: var(--space-2);
  border-left: 3px solid var(--brand);
  font-size: var(--text-h4);
  font-weight: 600;
  line-height: 1.3;
}
</style>
