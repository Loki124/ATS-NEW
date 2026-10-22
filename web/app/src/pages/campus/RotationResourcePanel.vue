<template>
  <!-- 轮岗资源 · 资源台账面板：作为 RotationResource 的「轮岗资源」页签内容渲染。
       2026-10-22 兵哥指令：直播间 + 客服部门整合为「轮岗资源」一张表 →
       原「直播间」「客服部门」两个面板合并为这一个，用「资源类型」列区分形态。
       页面标题与提示条由宿主页承载（校招生管理各列表页统一去标题），本面板只保留工具栏与表格。 -->
  <div class="campus-panel">
    <div class="campus-panel-body">
      <div class="toolbar">
        <n-input
          v-model:value="searchText"
          placeholder="搜索资源名称"
          clearable
          class="rule-filter-search"
        >
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <!-- 归属部门筛选：部门树多选（组件库 DeptTreeFilter）。
             支持「选父部门 = 含其全部下级」与「展示历史停用部门」；
             部门名比平台名长，用比全局 .rule-filter-select（136px）更宽的固定宽度，
             避免长部门名被压成省略号；仍带 flex-shrink:0，保证与搜索框 / 类型筛选同排不换行。 -->
        <DeptTreeFilter
          v-model="filterDepartment"
          :departments="deptStore.departments"
          placeholder="全部归属部门"
          width="180px"
          class="filter-select-dept"
          @update:model-value="loadList"
        />
        <!-- 资源类型筛选：合并后的核心区分维度（直播间 / 客服部门 / 其他） -->
        <n-select
          v-model:value="filterResourceType"
          :options="resourceTypeOptions"
          placeholder="全部资源类型"
          clearable
          class="rule-filter-select"
          @update:value="loadList"
        />
        <n-select
          v-model:value="filterPlatform"
          :options="platformOptions"
          placeholder="全部平台"
          clearable
          filterable
          class="rule-filter-select"
          @update:value="loadList"
        />
        <!-- 状态筛选：默认「启用」（启停改由行内「启用/停用」按钮操作，工具栏不再用开关控件）。 -->
        <n-select
          v-model:value="filterStatus"
          :options="statusOptions"
          placeholder="全部状态"
          clearable
          class="rule-filter-select"
          @update:value="loadList"
        />
        <div class="spacer"></div>
        <CampusMockBar :is-mock="isMock" @change="loadList" />
        <n-button quaternary :disabled="isMock" @click="onExport">
          <template #icon><n-icon :component="DownloadOutline" /></template>
          导出 Excel
        </n-button>
        <n-button quaternary :disabled="isMock" @click="openImport">
          <template #icon><n-icon :component="CloudUploadOutline" /></template>
          导入 Excel
        </n-button>
        <n-button type="primary" :disabled="isMock" @click="openCreate">
          <template #icon><n-icon :component="AddOutline" /></template>
          新增资源
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
          :scroll-x="TABLE_SCROLL_X"
          flex-height
        >
          <template #empty><n-empty description="暂无轮岗资源" /></template>
        </n-data-table>
      </div>

      <!-- 新建 / 编辑 弹窗 -->
      <n-modal
        v-model:show="modalVisible"
        preset="card"
        :title="editing ? '编辑轮岗资源' : '新建轮岗资源'"
        :style="{ width: '640px' }"
        :mask-closable="false"
      >
        <n-form :model="formState" label-placement="top">
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="资源编号">
                <n-input :value="editing ? formState.resourceNo : noHint" readonly />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="资源类型"
                required
                :validation-status="typeError ? 'error' : undefined"
                :feedback="typeError ?? undefined"
              >
                <n-select
                  v-model:value="formState.resourceType"
                  :options="resourceTypeOptions"
                  placeholder="请选择资源类型"
                  @update:value="onResourceTypeChange"
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item
                label="资源名称"
                required
                :validation-status="nameError ? 'error' : undefined"
                :feedback="nameError ?? undefined"
              >
                <n-input v-model:value="formState.name" placeholder="请输入资源名称" />
              </n-form-item>
            </n-grid-item>
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
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
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
            <n-grid-item>
              <n-form-item label="导师">
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
          </n-grid>

          <!-- 平台仅「直播间」形态有意义；其余类型隐藏并清空（后端会拒绝非直播间的平台值） -->
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="平台" :required="formState.resourceType === 'LIVE_ROOM'">
                <n-select
                  v-model:value="formState.platform"
                  :options="platformOptions"
                  :placeholder="formState.resourceType === 'LIVE_ROOM' ? '请选择平台' : '仅直播间可填平台'"
                  :disabled="formState.resourceType !== 'LIVE_ROOM'"
                  clearable
                  filterable
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="地点">
                <!-- 自由文本（不再是 LOCATION 字典下拉）：后端已同步放开字典校验 -->
                <n-input v-model:value="formState.location" placeholder="请输入地点" clearable />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="容量上限">
                <n-input-number v-model:value="formState.capacity" :min="0" placeholder="容量" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="社招人数">
                <n-input-number v-model:value="formState.socialCount" :min="0" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <!-- 校招人数为只读（由轮岗安排实时统计），与「社招人数」「容量上限」共同决定列表里的饱和度 -->
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="校招人数">
                <n-input-number
                  :value="editing ? formState.campusCount : 0"
                  :min="0"
                  disabled
                  style="width: 100%"
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <!-- 2026-10-22 兵哥指令：去掉「备注」输入项（模型字段仍在，后端不再由本页维护） -->
        </n-form>

        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
            <n-button @click="modalVisible = false">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="save">保存</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 导入 Excel 弹窗 -->
      <n-modal
        v-model:show="importVisible"
        preset="card"
        title="导入轮岗资源（Excel）"
        :style="{ width: '680px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(520px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-space vertical :size="12">
          <n-alert type="info" :show-icon="true" :bordered="false">
            仅支持 .xlsx 格式。「资源编号」留空 = 新建（系统按资源类型自动生成 LR+4 / SD+4 / OT+4 流水号）；
            填写则按该编号更新已有资源。平台仅「直播间」必填，其余类型请留空；
            归属部门须与系统中的部门名称完全一致，不存在的行会被跳过并在下方列出原因。
          </n-alert>
          <n-space align="center" :wrap="false">
            <n-upload
              v-model:file-list="importFileList"
              accept=".xlsx,.xlsm"
              :max="1"
              :custom-request="handleImportUpload"
              @remove="onImportFileRemove"
            >
              <n-button :loading="importing">
                <template #icon><n-icon :component="CloudUploadOutline" /></template>
                选择 Excel 文件
              </n-button>
            </n-upload>
            <n-button size="small" quaternary type="primary" @click="onDownloadTemplate">
              <template #icon><n-icon :component="DownloadOutline" /></template>
              下载导入模板
            </n-button>
          </n-space>
          <div v-if="importResult" class="import-result">
            <n-alert v-if="importResult.success" type="success" :show-icon="true">
              导入完成：新建 {{ importResult.data.created }} 条，更新 {{ importResult.data.updated }} 条，跳过 {{ importResult.data.skipped }} 条
            </n-alert>
            <n-alert v-else type="error" :show-icon="true">
              导入未完成：新建 {{ importResult.data.created }} 条，更新 {{ importResult.data.updated }} 条，跳过 {{ importResult.data.skipped }} 条
            </n-alert>
            <div v-if="importResult.data.errors && importResult.data.errors.length" class="import-error-actions">
              <n-button v-if="importResult.data.errorFile" size="small" type="error" @click="onDownloadErrorFile">
                <template #icon><n-icon :component="DownloadOutline" /></template>
                下载错误明细
              </n-button>
            </div>
            <ul v-if="importResult.data.errors && importResult.data.errors.length" class="import-errors">
              <li v-for="(e, i) in importResult.data.errors" :key="i">{{ e }}</li>
            </ul>
          </div>
        </n-space>
        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
            <n-button @click="importVisible = false">关闭</n-button>
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
  NTag,
  NSpace,
  NPopconfirm,
  NIcon,
  NEmpty,
  NUpload,
  NAlert,
  useMessage,
} from 'naive-ui'
import {
  AddOutline,
  CreateOutline,
  TrashOutline,
  SearchOutline,
  CloudUploadOutline,
  DownloadOutline,
  PlayOutline,
  PauseOutline,
} from '@vicons/ionicons5'
import { api } from '../../utils/request'
import {
  exportRotationResources,
  downloadRotationResourceTemplate,
  importRotationResources,
  setRotationResourceActive,
  downloadRotationResourceImportErrors,
  type RotationResourceImportResult,
} from '../../api/campusRotation'
import CampusMockBar from '../../components/campus/CampusMockBar.vue'
import DeptTreeFilter from '../../components/common/DeptTreeFilter.vue'
import { useCampusMock } from '../../composables/useCampusMock'
import { MOCK_RESOURCES, resolveDeptRefs } from '../../mocks/campus'
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

/** 资源类型（后端枚举 key ↔ 中文名）——合并后区分三种形态的核心字段。 */
const RESOURCE_TYPE_OPTIONS: SelectOption[] = [
  { label: '直播间', value: 'LIVE_ROOM' },
  { label: '客服部门', value: 'SERVICE_DEPT' },
  { label: '其他', value: 'OTHER' },
]
const resourceTypeOptions = RESOURCE_TYPE_OPTIONS
/** 资源类型 → 编号前缀（与后端 RotationResource.NO_PREFIX_BY_TYPE 同口径）。 */
const NO_PREFIX_BY_TYPE: Record<string, string> = {
  LIVE_ROOM: 'LR',
  SERVICE_DEPT: 'SD',
  OTHER: 'OT',
}
const resourceTypeLabel = (key: string | null | undefined) =>
  RESOURCE_TYPE_OPTIONS.find((o) => o.value === key)?.label || key || '-'

const list = ref<any[]>([])
const loading = ref(false)
const searchText = ref('')
/** 归属部门筛选（部门树多选：ids 列表，含「选父即含子树」展开后的结果） */
const filterDepartment = ref<string[]>([])
/** 资源类型筛选 */
const filterResourceType = ref<string | null>(null)
/** 所在平台筛选（仅直播间有意义） */
const filterPlatform = ref<string | null>(null)
/** 状态筛选：默认「启用」。启停改由行内「启用 / 停用」按钮操作。 */
const filterStatus = ref<string | null>('active')
const statusOptions = [
  { label: '启用', value: 'active' },
  { label: '停用', value: 'inactive' },
]
const modalVisible = ref(false)
const editing = ref<any | null>(null)
const saving = ref(false)
/** 字段级错误（就近提示，图标+文字双通道；AGENTS.md R-221） */
const nameError = ref('')
const typeError = ref('')

const platformOptions = ref<SelectOption[]>([])
const mentorOptions = ref<SelectOption[]>([])

const deptTreeOptions = computed(() => buildDeptTree(deptStore.departments))
const levelMap = computed(() => deptLevelMap(deptStore.departments))
const buOpts = computed(() => buOptions(deptStore.departments, levelMap.value))

/** 新建时的编号占位文案：随资源类型变化（LR+4 / SD+4 / OT+4）。 */
const noHint = computed(
  () => `自动生成（${NO_PREFIX_BY_TYPE[formState.resourceType] ?? 'LR'}+4位）`,
)

// 示例数据（真实为空时兜底；只读，页面已禁用新增/编辑/删除）
const { pick, isMock, isMockOnly } = useCampusMock()
const mockRows = computed(() => {
  let rows = resolveDeptRefs(MOCK_RESOURCES, deptStore.departments)
  const kw = searchText.value.trim()
  if (kw) rows = rows.filter((r) => String(r.name).includes(kw))
  if (filterDepartment.value.length) {
    const wanted = new Set(filterDepartment.value.map(String))
    rows = rows.filter((r) => wanted.has(String(r.department ?? '')))
  }
  if (filterResourceType.value) {
    rows = rows.filter((r) => String(r.resourceType ?? '') === String(filterResourceType.value))
  }
  if (filterPlatform.value) {
    rows = rows.filter((r) => String(r.platform ?? '') === String(filterPlatform.value))
  }
  // 状态筛选（默认「启用」）
  if (filterStatus.value === 'active') rows = rows.filter((r) => r.isActive !== false)
  else if (filterStatus.value === 'inactive') rows = rows.filter((r) => r.isActive === false)
  return rows
})

function renderDeptLabel({ option }: { option: any }) {
  return h('span', option.name)
}

const emptyForm = () => ({
  id: null as string | null,
  resourceNo: '',
  name: '',
  /** 资源类型：新建默认「直播间」（与后端模型默认值一致） */
  resourceType: 'LIVE_ROOM' as string,
  department: null as string | null,
  bu: null as string | null,
  mentor: null as string | null,
  platform: null as string | null,
  /** 地点：自由文本（不再限定 LOCATION 字典项） */
  location: '',
  capacity: null as number | null,
  socialCount: 0,
  /** 校招人数：只读（后端按轮岗安排实时聚合），仅用于表单展示 */
  campusCount: 0,
  // isActive：模型字段保留（后端仍在用），本页不再维护启停 → 恒为 true
  isActive: true,
})
const formState = reactive(emptyForm())

/** 切换资源类型：非直播间必须清空平台（后端会拒绝非直播间的平台值）。 */
const onResourceTypeChange = (value: string) => {
  formState.resourceType = value
  if (value !== 'LIVE_ROOM') formState.platform = null
}

const onMentorSearch = async (kw: string) => {
  mentorOptions.value = await searchUsers(kw, 'campus_mentor')
}

const loadList = async () => {
  loading.value = true
  try {
    if (isMockOnly.value) {
      list.value = mockRows.value
      return
    }
    const params: Record<string, any> = { page: 1, page_size: 200 }
    if (searchText.value.trim()) params.search = searchText.value.trim()
    // 后端 resources 列表支持 department / resource_type / platform / is_active 四个筛选参数
    // （department 支持逗号分隔的多选部门 id）
    if (filterDepartment.value.length) params.department = filterDepartment.value.join(',')
    if (filterResourceType.value) params.resource_type = filterResourceType.value
    if (filterPlatform.value) params.platform = filterPlatform.value
    // 状态筛选：默认「启用」；清空（全部状态）则不传该参数
    if (filterStatus.value === 'active') params.is_active = 'true'
    else if (filterStatus.value === 'inactive') params.is_active = 'false'
    const resp = await api.get('/campus-rotation/resources/', { params })
    list.value = pick(extractList(resp), mockRows.value)
  } catch (e: any) {
    // 接口失败：auto 模式用示例数据兜底
    list.value = pick([], mockRows.value)
    message.error(extractError(e))
  } finally {
    loading.value = false
  }
}

const loadDicts = async () => {
  try {
    // 只剩「直播间平台」一个字典（品牌 / 客服类型 / 工位类型随字段下线而移除）
    platformOptions.value = await dictOptions('LIVE_ROOM_PLATFORM')
  } catch (e: any) {
    message.error(extractError(e))
  }
}

const openCreate = () => {
  Object.assign(formState, emptyForm())
  editing.value = null
  mentorOptions.value = []
  nameError.value = ''
  typeError.value = ''
  modalVisible.value = true
}

const openEdit = (row: any) => {
  Object.assign(formState, emptyForm(), {
    id: row.id,
    resourceNo: row.resourceNo,
    name: row.name,
    resourceType: row.resourceType || 'LIVE_ROOM',
    department: row.department != null ? String(row.department) : null,
    bu: row.bu != null ? String(row.bu) : null,
    mentor: row.mentor != null ? String(row.mentor) : null,
    platform: row.platform ?? null,
    location: row.location ?? '',
    capacity: row.capacity ?? null,
    socialCount: row.socialCount ?? 0,
    campusCount: row.campusCount ?? 0,
    isActive: row.isActive !== false,
  })
  editing.value = row
  mentorOptions.value = row.mentor != null ? [{ label: String(row.mentor), value: String(row.mentor) }] : []
  nameError.value = ''
  typeError.value = ''
  modalVisible.value = true
}

const save = async () => {
  // 示例数据二次守卫（与 CampusPerson/ClassRoom 同口径）：模板层 disabled 只挡点击，
  // 此处挡代码路径直入。示例行 id 是 MOCK_ 前缀假 id，落到后端必然 404。
  if (isMock.value) {
    message.warning('示例数据仅供查看，请切回真实数据后再操作')
    return
  }
  // 字段级校验：先就地标错（就近提示），再兜底 toast（不依赖颜色单独表意）
  nameError.value = formState.name.trim() ? '' : '请填写资源名称'
  typeError.value = formState.resourceType ? '' : '请选择资源类型'
  if (nameError.value || typeError.value) {
    message.warning(nameError.value || typeError.value)
    return
  }
  saving.value = true
  const payload: any = {
    name: formState.name,
    resourceType: formState.resourceType,
    department: formState.department,
    bu: formState.bu,
    mentor: formState.mentor,
    // 平台仅直播间形态有意义；其余类型提交空串（后端对非直播间的平台值会 400）
    platform: formState.resourceType === 'LIVE_ROOM' ? formState.platform : null,
    location: formState.location,
    capacity: formState.capacity,
    socialCount: formState.socialCount,
    isActive: formState.isActive,
  }
  try {
    if (editing.value) {
      await api.put(`/campus-rotation/resources/${editing.value.id}/`, payload)
      message.success('更新成功')
    } else {
      await api.post('/campus-rotation/resources/', payload)
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
    await api.delete(`/campus-rotation/resources/${row.id}/`)
    message.success('已删除')
    loadList()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/* ── 启用 / 停用 ───────────────────────────────────────────────────────────
 * R-106：停用属**可逆**操作 → 直接执行 + 提示，禁止确认弹窗（确认框只留给不可逆操作）。
 * 用 PATCH 局部更新（partial update 只校验传入字段，不会触发部门/BU/导师/字典校验）。 */
const toggleActive = async (row: any) => {
  if (isMock.value) {
    message.warning('示例数据仅供查看，请切回真实数据后再操作')
    return
  }
  const next = row.isActive === false
  try {
    await setRotationResourceActive(row.id, next)
    message.success(`${next ? '已启用' : '已停用'}资源「${row.name || row.resourceNo || ''}」`)
    loadList()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/* ── 导入 / 导出（Excel）───────────────────────────────────────────────── */
const importVisible = ref(false)
const importing = ref(false)
const importFileList = ref<any[]>([])
const importResult = ref<RotationResourceImportResult | null>(null)

const openImport = () => {
  importResult.value = null
  importFileList.value = []
  importVisible.value = true
}

const onImportFileRemove = () => {
  importResult.value = null
}

const onDownloadTemplate = async () => {
  try {
    await downloadRotationResourceTemplate()
    message.success('导入模板已下载')
  } catch (e: any) {
    message.error(extractError(e))
  }
}

const onExport = async () => {
  try {
    await exportRotationResources()
    message.success('导出已开始')
  } catch (e: any) {
    message.error(extractError(e))
  }
}

const onDownloadErrorFile = () => {
  const file = importResult.value?.data?.errorFile
  if (!file) return
  downloadRotationResourceImportErrors(file, `rotation_resources_import_errors_${Date.now()}.xlsx`)
}

/**
 * n-upload 的自定义上传：直接打后端导入端点（multipart）。
 * ⚠️ 后端业务校验失败返 400，api 层 validateStatus 让 4xx 走 then 分支
 *    （否则会被当成网络错误、丢掉「哪一行错了」的明细）。
 */
const handleImportUpload = ({ file, onFinish, onError }: any) => {
  const raw = file.file as File
  if (!raw) {
    onError()
    return
  }
  importing.value = true
  importResult.value = null
  importRotationResources(raw)
    .then((res) => {
      importResult.value = res
      if (res.success) {
        message.success(
          `导入完成：新建 ${res.data.created} 条，更新 ${res.data.updated} 条，跳过 ${res.data.skipped} 条`,
        )
        loadList()
        onFinish()
      } else {
        message.error(
          `导入未完成：跳过 ${res.data.skipped} 条，${res.data.errors?.length ?? 0} 条有问题`,
        )
        onError()
      }
    })
    .catch((e: any) => {
      const errRes = e?.response?.data
      if (errRes?.data) {
        importResult.value = errRes as RotationResourceImportResult
        message.error('导入失败，请查看错误明细')
      } else {
        message.error(extractError(e))
      }
      onError()
    })
    .finally(() => {
      importing.value = false
    })
}

// 字典项 key → 中文名（表格展示用）
const dictLabel = (options: SelectOption[], key: string | null | undefined) => {
  if (!key) return '-'
  return options.find((o) => o.value === key)?.label || key
}
const deptName = (id: any) => (id != null ? deptStore.getById(String(id))?.name || String(id) : '-')

/**
 * 饱和度 = round((社招人数 + 校招人数) / 容量上限 × 100)%
 *
 * 口径沿用原系统与《校招生管理需求规格与实施方案》§3.2.2：
 *   >70% 危险 / >40% 警告 / 其余正常。
 * 容量上限为空或 0 时无法计算 → 显示「—」（不静默当成 0%）。
 */
const saturationOf = (row: any): number | null => {
  const capacity = Number(row?.capacity)
  if (!Number.isFinite(capacity) || capacity <= 0) return null
  const used = (Number(row?.socialCount) || 0) + (Number(row?.campusCount) || 0)
  return Math.round((used / capacity) * 100)
}

/** 饱和度分档：>70% 危险 / >40% 警告 / 其余正常（颜色 + 数字双通道，不靠颜色单独表意） */
const saturationLevel = (v: number): 'error' | 'warning' | 'success' =>
  v > 70 ? 'error' : v > 40 ? 'warning' : 'success'

const saturationTag = (row: any) => {
  const v = saturationOf(row)
  if (v === null) {
    return h(NTag, { size: 'small', bordered: false, class: 'saturation-cell' }, { default: () => '—' })
  }
  return h(
    NTag,
    {
      type: saturationLevel(v),
      size: 'small',
      bordered: false,
      class: 'saturation-cell',
      title: `饱和度 ${v}%`,
    },
    { default: () => `${v}%` },
  )
}

// S5-08：列对齐接入 useTableColumns 单一真源
// 2026-10-22 兵哥指令：直播间编号 / 名称 / 导师 与 客服部门编号 / 名称 / 主管
//   统一为「资源编号 / 资源名称 / 导师」，并新增「资源类型」列；
//   品牌 / 客服类型 / 工位类型列随字段下线而移除。
const columns = [
  column({ title: '资源编号', key: 'resourceNo', width: 120, render: (row: any) => row.resourceNo || '-' }),
  column({ title: '资源名称', key: 'name', width: 160, ellipsis: true, render: (row: any) => row.name || '-' }),
  column({
    title: '资源类型',
    key: 'resourceType',
    width: 100,
    render: (row: any) => resourceTypeLabel(row.resourceType),
  }),
  column({ title: '归属部门', key: 'department', width: 160, ellipsis: true, render: (row: any) => deptName(row.department) }),
  column({ title: '归属BU', key: 'bu', width: 160, ellipsis: true, render: (row: any) => deptName(row.bu) }),
  column({
    title: '导师',
    key: 'mentor',
    width: 140,
    render: (row: any) => row.mentorName || (row.mentor != null ? String(row.mentor) : '-'),
  }),
  column({ title: '平台', key: 'platform', width: 120, render: (row: any) => dictLabel(platformOptions.value, row.platform) }),
  column({ title: '地点', key: 'location', width: 100, render: (row: any) => row.location || '-' }),
  column({ title: '容量', key: 'capacity', width: 80, render: (row: any) => row.capacity ?? '-' }, 'numeric'),
  column({ title: '社招人数', key: 'socialCount', width: 90, render: (row: any) => row.socialCount ?? 0 }, 'numeric'),
  column({ title: '校招占用', key: 'campusCount', width: 90, render: (row: any) => row.campusCount ?? 0 }, 'numeric'),
  column({ title: '饱和度', key: 'saturation', width: 100, render: (row: any) => saturationTag(row) }, 'numeric'),
  column(
    {
      title: '操作',
      key: 'actions',
      // 三个按钮（编辑 / 启用·停用 / 删除）：按每按钮 ≈74px + 间距 8 + 单元格内边距 24 估 268px
      width: 268,
      fixed: 'right' as const,
      render: (row: any) =>
        h(NSpace, { size: 8, wrap: false }, {
          default: () => [
            h(NButton, { size: 'small', quaternary: true, type: 'primary', disabled: isMock.value, onClick: () => openEdit(row) }, { default: () => '编辑', icon: () => h(NIcon, null, { default: () => h(CreateOutline) }) }),
            // 行内「启用 / 停用」按钮（可逆操作，直接执行不弹确认框，R-106）
            h(
              NButton,
              {
                size: 'small',
                quaternary: true,
                type: row.isActive !== false ? 'warning' : 'success',
                disabled: isMock.value,
                onClick: () => toggleActive(row),
              },
              {
                default: () => (row.isActive !== false ? '停用' : '启用'),
                icon: () => h(NIcon, null, { default: () => h(row.isActive !== false ? PauseOutline : PlayOutline) }),
              },
            ),
            h(NPopconfirm, { onPositiveClick: () => remove(row), positiveText: '确认', negativeText: '取消' }, {
              default: () => '确认删除该轮岗资源？',
              trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'error', disabled: isMock.value }, { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) }),
            }),
          ],
        }),
    },
    'control',
  ),
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
  loadDicts()
  loadList()
})
</script>

<style scoped>
.campus-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.campus-panel-body {
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
/* 归属部门筛选：部门名比平台名长，用比全局 .rule-filter-select（136px）更宽的固定宽度，
   避免长部门名被压成省略号；仍带 flex-shrink:0，保证与搜索框 / 类型筛选同排不换行。 */
.filter-select-dept {
  width: 180px;
  flex-shrink: 0;
}
/* 饱和度百分比：等宽数字，数值刷新不抖动（R-204） */
.saturation-cell {
  font-variant-numeric: tabular-nums;
}
/* 导入结果区：统计提示 + 错误明细列表（与设置中心编制管控的导入弹窗同版式） */
.import-result {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.import-error-actions {
  display: flex;
  gap: var(--space-2);
}
.import-errors {
  margin: 0;
  padding-left: var(--space-4);
  max-height: 180px;
  overflow-y: auto;
  font-size: var(--fs-13);
  color: var(--ink-soft);
}
.import-errors li {
  overflow-wrap: anywhere;
}
.spacer {
  flex: 1;
}
</style>
