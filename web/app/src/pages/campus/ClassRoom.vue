<template>
  <div class="page-container">
    <div class="page-body">
      <!-- 校招生管理列表页统一去标题：页面身份由顶部导航承载 -->

      <div class="toolbar">
        <n-input
          v-model:value="searchText"
          placeholder="搜索班级名称"
          clearable
          class="rule-filter-search"
        >
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <!-- 2026-10-22：新增班长筛选；下线「仅显示启用」开关（班级不再有启停概念） -->
        <n-select
          v-model:value="filterMonitor"
          :options="monitorOptions"
          placeholder="全部班长"
          clearable
          filterable
          remote
          class="rule-filter-select"
          :on-search="onMonitorSearch"
          @update:value="loadList"
        />
        <div class="spacer"></div>
        <CampusMockBar :is-mock="isMock" @change="loadList" />
        <n-button type="primary" :disabled="isMock" @click="openCreate">
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
          :scroll-x="TABLE_SCROLL_X"
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
                <n-input :value="editing ? formState.code : '自动生成（CL+3位）'" readonly />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="班级名称">
                <n-input
                  :value="editing ? formState.name : nextNameHint"
                  readonly
                  :placeholder="`保存时自动生成（${nextNameHint}）`"
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <!-- 2026-10-22：下线 班主任 / HRBP / 批次 三个字段，改挂 班长
               （模型字段仍在，仅本页不再维护；hrbp 是行级隔离 scope 字段，不可删）
               2026-10-22：同时下线「是否启用」开关（班级不再有启停概念） -->
          <n-grid :cols="2" :x-gap="24">
            <n-grid-item>
              <n-form-item label="班长">
                <n-select
                  v-model:value="formState.classMonitor"
                  :options="userOptions"
                  placeholder="请选择班长"
                  clearable
                  filterable
                  remote
                  :on-search="onUserSearch"
                />
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
      <n-modal
        v-model:show="membersVisible"
        preset="card"
        :title="`班级成员 · ${currentClassName}`"
        :style="{ width: '720px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(640px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
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
      </n-modal>

      <!-- 2026-10-22：阶段分布下钻（该班级 · 该阶段 的轮岗安排明细） -->
      <n-modal
        v-model:show="stageVisible"
        preset="card"
        :title="stageModalTitle"
        :style="{ width: '820px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(560px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-data-table
          :data="stageList"
          :columns="stageColumns"
          :row-key="(r: any) => r.arrangementId"
          :loading="stageLoading"
          :pagination="{ pageSize: 50 }"
          :bordered="false"
        >
          <template #empty>
            <n-empty :description="`该班级暂无「${stageMeta.label}」阶段的校招生`" />
          </template>
        </n-data-table>
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
  NSelect,
  NSpace,
  NTag,
  NIcon,
  NEmpty,
  useMessage,
} from 'naive-ui'
import { AddOutline, CreateOutline, SearchOutline } from '@vicons/ionicons5'
import { api } from '../../utils/request'
import CampusMockBar from '../../components/campus/CampusMockBar.vue'
import { useCampusMock } from '../../composables/useCampusMock'
import { MOCK_CLASS_ROOMS } from '../../mocks/campus'
import {
  extractList,
  extractError,
  searchUsers,
  type SelectOption,
} from '../../utils/campus'
import { column } from '../../composables/useTableColumns'

const message = useMessage()

/** 阶段分布三态（2026-10-22）：待分配 / 轮岗中 / 已完成 */
const STAGE_META = [
  { key: 'PENDING', label: '待分配', type: 'warning' },
  { key: 'ONGOING', label: '轮岗中', type: 'info' },
  { key: 'DONE', label: '已完成', type: 'success' },
] as const

const list = ref<any[]>([])
const loading = ref(false)
const searchText = ref('')
/** 班长筛选（2026-10-22） */
const filterMonitor = ref<string | null>(null)
const monitorOptions = ref<SelectOption[]>([])
const modalVisible = ref(false)
const editing = ref<any | null>(null)
const saving = ref(false)

const userOptions = ref<SelectOption[]>([])

// 示例数据（真实为空时兜底；只读，页面已禁用新建/编辑/删除/成员穿透）
const { pick, isMock, isMockOnly } = useCampusMock()
const mockRows = computed(() => {
  let rows = [...MOCK_CLASS_ROOMS]
  const kw = searchText.value.trim()
  if (kw) rows = rows.filter((r) => String(r.name).includes(kw))
  if (filterMonitor.value) {
    rows = rows.filter((r) => String(r.classMonitor ?? '') === String(filterMonitor.value))
  }
  return rows
})

const onUserSearch = async (kw: string) => {
  userOptions.value = await searchUsers(kw)
}
/**
 * 班长筛选下拉：
 * - 示例数据模式 → 选项取自示例班级（假 id MOCK_U_*），筛选可命中；
 * - 真实数据模式 → 远程搜用户（/users/）。
 */
const mockMonitorOptions = computed<SelectOption[]>(() => {
  const map = new Map<string, string>()
  for (const c of MOCK_CLASS_ROOMS) {
    if (c.classMonitor) map.set(String(c.classMonitor), String(c.classMonitorName ?? c.classMonitor))
  }
  return Array.from(map, ([value, label]) => ({ label, value }))
})
const onMonitorSearch = async (kw: string) => {
  if (isMock.value) {
    monitorOptions.value = mockMonitorOptions.value
    return
  }
  monitorOptions.value = await searchUsers(kw)
}

const emptyForm = () => ({
  id: null as string | null,
  code: '',
  name: '',
  classMonitor: null as string | null,
  isActive: true,
  remark: '',
})
const formState = reactive(emptyForm())

/**
 * 新建时展示的下一个班级序号（从 1 开始的流水号，由服务端落库时生成）。
 * 前端只做提示，真正的取值以服务端返回为准。
 */
const nextNameHint = computed(() => {
  const nums = list.value
    .map((r: any) => String(r.name ?? '').trim())
    .filter((s: string) => /^\d+$/.test(s))
    .map((s: string) => Number(s))
  return String(nums.length ? Math.max(...nums) + 1 : 1)
})

const loadList = async () => {
  loading.value = true
  try {
    if (isMockOnly.value) {
      list.value = mockRows.value
      monitorOptions.value = mockMonitorOptions.value
      return
    }
    const params: Record<string, any> = { page: 1, page_size: 200 }
    if (searchText.value.trim()) params.search = searchText.value.trim()
    if (filterMonitor.value) params.class_monitor = filterMonitor.value
    const resp = await api.get('/campus-rotation/class-rooms/', { params })
    list.value = pick(extractList(resp), mockRows.value)
  } catch (e: any) {
    // 接口失败：auto 模式用示例数据兜底
    list.value = pick([], mockRows.value)
    message.error(extractError(e))
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  Object.assign(formState, emptyForm())
  editing.value = null
  userOptions.value = []
  modalVisible.value = true
}

const openEdit = (row: any) => {
  Object.assign(formState, emptyForm(), {
    id: row.id,
    code: row.code,
    name: row.name,
    classMonitor: row.classMonitor != null ? String(row.classMonitor) : null,
    isActive: row.isActive !== false,
    remark: row.remark || '',
  })
  editing.value = row
  if (row.classMonitor != null) {
    userOptions.value = [
      ...userOptions.value.filter((o) => o.value !== String(row.classMonitor)),
      { label: row.classMonitorName || String(row.classMonitor), value: String(row.classMonitor) },
    ]
  }
  modalVisible.value = true
}

const save = async () => {
  // 示例数据二次守卫：模板层的 disabled 只挡点击，此处挡「代码路径直入」
  // （与 CampusPerson.vue 的 save/remove 同口径）。示例行的 id 是 MOCK_ 前缀的
  // 假 id，落到后端必然 404/写脏数据。
  if (isMock.value) {
    message.warning('示例数据仅供查看，请切回真实数据后再操作')
    return
  }
  saving.value = true
  const payload: any = {
    // 班级名称 = 服务端生成的流水号（从 1 开始），前端不传
    classMonitor: formState.classMonitor,
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

// 2026-10-22：班级删除入口下线（班级编号是流水号，删除会占坑）→ 前端不再保留删除函数；
// 后端 DELETE /class-rooms/{id}/ 端点保留（权限码 recruit:campus:class:delete 不变）。

// S5-06（需求 3-2）：班级成员明细穿透 —— 列表「校招人数」可点击打开抽屉
const membersVisible = ref(false)
const memberLoading = ref(false)
const memberList = ref<any[]>([])
const currentClassName = ref('')
const openMembers = async (row: any) => {
  // 🔴 示例数据守卫：成员穿透按班级 id 反查真实人员，示例行 id 是 MOCK_ 前缀假 id，
  // 后端查不到 → 404（2026-10-21 班级管理页实际报错）。此处直接拦下并说明，
  // 不发请求；示例数据本就无对应人员，穿透没有意义。
  if (isMock.value) {
    message.warning('示例数据无对应人员明细，请切回真实数据后再查看')
    return
  }
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

/* ── 阶段分布下钻（2026-10-22）────────────────────────────────── */
const stageVisible = ref(false)
const stageLoading = ref(false)
const stageList = ref<any[]>([])
const stageKey = ref<string>('PENDING')
const stageClassName = ref<string>('')

const stageMeta = computed(() => STAGE_META.find((s) => s.key === stageKey.value) ?? STAGE_META[0])
const stageModalTitle = computed(() =>
  `阶段明细 · ${stageClassName.value} · ${stageMeta.value.label}`,
)

/** 点击阶段分布的计数 → 打开该班级该阶段的轮岗安排明细 */
const openStageMembers = async (row: any, stage: string) => {
  if (isMock.value) {
    message.warning('示例数据无对应轮岗明细，请切回真实数据后再查看')
    return
  }
  stageKey.value = stage
  stageClassName.value = row.name || row.code || ''
  stageVisible.value = true
  stageLoading.value = true
  stageList.value = []
  try {
    const resp = await api.get(
      `/campus-rotation/class-rooms/${row.id}/stage-members/`,
      { params: { stage } },
    )
    stageList.value = (resp?.data?.data?.items ?? []) as any[]
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    stageLoading.value = false
  }
}

const stageColumns = [
  column({ title: '校招生', key: 'personName', width: 110, render: (r: any) => r.personName || '-' }),
  column({ title: '工号', key: 'employeeId', width: 120, render: (r: any) => r.employeeId || '-' }),
  column({ title: '轮岗部门', key: 'currentDept', width: 140, render: (r: any) => r.currentDept || '-' }),
  column({ title: '带教导师', key: 'mentor', width: 110, render: (r: any) => r.mentor || '-' }),
  column({ title: '轮岗起', key: 'rotationStart', width: 110, render: (r: any) => r.rotationStart || '-' }),
  column({ title: '轮岗止', key: 'rotationEnd', width: 110, render: (r: any) => r.rotationEnd || '-' }),
]

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
  column({ title: '班级名称', key: 'name', width: 120, ellipsis: true, render: (row: any) => row.name || '-' }),
  // 2026-10-22：下线 班主任 / HRBP / 批次 三列，改挂 班长
  column({ title: '班长', key: 'classMonitorName', width: 140, render: (row: any) => row.classMonitorName || (row.classMonitor != null ? String(row.classMonitor) : '-') }),
  column({ title: '校招人数', key: 'studentCount', width: 100, render: (row: any) => h(NButton, { size: 'small', quaternary: true, type: 'primary', disabled: isMock.value, onClick: () => openMembers(row) }, { default: () => String(row.studentCount ?? 0) }) }, 'numeric'),
  // 2026-10-22：阶段分布（三态计数，**标签形式**展示，点击可下钻到该班该阶段的校招生明细）
  //   - 标签用 NTag（根元素 inline-flex → 行内级 → 单元格 text-align:center 生效，视觉居中）；
  //     早前用 quaternary 按钮（无底色边框），看着像纯文字、不是标签。
  //   - 可下钻的那一档用真实 <button> 承载（键盘可达，R-109），外观完全交给内层 NTag。
  //   - 计数为 0 / 示例数据时不可下钻 → 纯标签。
  column(
    {
      title: '阶段分布',
      key: 'stageCounts',
      width: 260,
      render: (row: any) =>
        h(NSpace, { size: 6, wrap: false }, {
          default: () => STAGE_META.map((s) => {
            const n = row.stageCounts?.[s.key] ?? 0
            const disabled = isMock.value || !n
            const tag = () =>
              h(NTag, { type: s.type, size: 'small', bordered: false }, { default: () => `${s.label} ${n}` })
            if (disabled) return tag()
            return h(
              'button',
              {
                type: 'button',
                class: 'stage-chip',
                title: `查看「${s.label}」的校招生明细`,
                'aria-label': `查看${row.name || row.code || ''}的${s.label}校招生明细`,
                onClick: () => openStageMembers(row, s.key),
              },
              { default: tag },
            )
          }),
        }),
    },
    'control',
  ),
  column(
    {
      title: '操作',
      key: 'actions',
      width: 96,
      fixed: 'right' as const,
      render: (row: any) =>
        h(NSpace, { size: 8, wrap: false }, {
          default: () => [
            // 2026-10-22：下线班级删除按钮（班级编号是流水号，删掉会占坑）
            h(NButton, { size: 'small', quaternary: true, type: 'primary', disabled: isMock.value, onClick: () => openEdit(row) }, { default: () => '编辑', icon: () => h(NIcon, null, { default: () => h(CreateOutline) }) }),
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
  loadList()
})
</script>

<style scoped>
/* 阶段分布：可下钻的那一档用真实 <button> 承载（键盘可达，R-109），
   视觉完全交给内层 NTag —— 故把 button 的原生外观（边框/底色/内边距）复位。 */
.stage-chip {
  display: inline-flex;
  align-items: center;
  border: none;
  background: none;
  padding: 0;
  cursor: pointer;
  line-height: 1;
}
.stage-chip:focus-visible {
  outline: 2px solid var(--brand-button);
  outline-offset: 2px;
}

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
</style>
