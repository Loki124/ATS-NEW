<template>
  <div class="page-container">
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
      <h1 class="page-title">{{ t('pages.position.PositionList.s1') }}</h1>
      <n-button type="primary" @click="handleCreate">
        <template #icon><n-icon :component="AddOutline" /></template>
        {{ t('pages.position.PositionList.s2') }}
      </n-button>
    </div>

    <n-card>
      <n-tabs v-model:value="activeTab" type="line" animated>
        <n-tab-pane name="all" :tab="t('pages.position.PositionList.s3')">
          <n-data-table :columns="columns" :data="filteredRows" :loading="loading" :pagination="{ pageSize: 10 }" :row-key="(row: PositionRow) => row.id" />
        </n-tab-pane>
        <n-tab-pane name="RECRUITING" :tab="t('pages.position.PositionList.s4')">
          <n-data-table :columns="columns" :data="filteredRows" :loading="loading" :pagination="{ pageSize: 10 }" :row-key="(row: PositionRow) => row.id" />
        </n-tab-pane>
        <n-tab-pane name="PAUSED" :tab="t('pages.position.PositionList.s5')">
          <n-data-table :columns="columns" :data="filteredRows" :loading="loading" :pagination="{ pageSize: 10 }" :row-key="(row: PositionRow) => row.id" />
        </n-tab-pane>
        <n-tab-pane name="CLOSED" :tab="t('pages.position.PositionList.s6')">
          <n-data-table :columns="columns" :data="filteredRows" :loading="loading" :pagination="{ pageSize: 10 }" :row-key="(row: PositionRow) => row.id" />
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <!-- 创建/编辑职位弹窗 -->
    <n-modal
      v-model:show="modalVisible"
      preset="card"
      :title="selectedPosition ? '编辑职位' : '创建职位'"
      style="width: 800px; max-width: 90vw"
    >
      <n-divider title-placement="left">{{ t('pages.position.PositionList.s7') }}</n-divider>
      <n-form ref="formRef" :model="formState" label-placement="top">
        <div class="grid grid-cols-2 gap-x-4">
          <n-form-item path="title" :label="t('pages.position.PositionList.s8')" :rule="{ required: true, message: '请输入职位名称', trigger: 'blur' }">
            <n-input v-model:value="formState.title" :placeholder="t('pages.position.PositionList.s9')" />
          </n-form-item>
          <n-form-item path="department" label="所属部门" :rule="reqSelect('请选择部门')">
            <n-select v-model:value="formState.department" :placeholder="t('pages.position.PositionList.s10')" :options="departmentOptions" />
          </n-form-item>

          <n-form-item path="demand" :label="t('pages.position.PositionList.s11')">
            <n-select v-model:value="formState.demand" :placeholder="t('pages.position.PositionList.s12')" :options="demandOptions" clearable />
          </n-form-item>
          <n-form-item path="process" label="招聘流程" :rule="reqSelect('请选择招聘流程')">
            <n-select v-model:value="formState.process" :placeholder="t('pages.position.PositionList.s13')" :options="processOptions" />
          </n-form-item>

          <n-form-item path="priority" label="优先级" :rule="reqSelect('请选择优先级')">
            <n-select v-model:value="formState.priority" :placeholder="t('pages.position.PositionList.s14')" :options="priorityOptions" />
          </n-form-item>
          <n-form-item path="headCount" :label="t('pages.position.PositionList.s15')" :rule="{ required: true, type: 'number', message: '请输入需求人数', trigger: 'blur' }">
            <n-input-number v-model:value="formState.headCount" :min="1" :max="100" style="width: 100%;" />
          </n-form-item>

          <n-form-item path="salaryMin" :label="t('pages.position.PositionList.s16')">
            <n-input-number v-model:value="formState.salaryMin" :min="0" :step="1000" style="width: 100%;" :placeholder="t('pages.position.PositionList.s17')" />
          </n-form-item>
          <n-form-item path="salaryMax" :label="t('pages.position.PositionList.s18')">
            <n-input-number v-model:value="formState.salaryMax" :min="0" :step="1000" style="width: 100%;" :placeholder="t('pages.position.PositionList.s19')" />
          </n-form-item>

          <n-form-item path="location" :label="t('pages.position.PositionList.s20')">
            <n-input v-model:value="formState.location" :placeholder="t('pages.position.PositionList.s21')" />
          </n-form-item>
        </div>

        <n-divider title-placement="left">{{ t('pages.position.PositionList.s22') }}</n-divider>
        <div class="grid grid-cols-2 gap-x-4">
          <n-form-item path="owner" label="职位负责人" :rule="reqSelect('请选择职位负责人')">
            <n-select v-model:value="formState.owner" :placeholder="t('pages.position.PositionList.s23')" :options="ownerOptions" />
          </n-form-item>
          <n-form-item path="hiringManager" label="用人经理" :rule="reqSelect('请选择用人经理')">
            <n-select v-model:value="formState.hiringManager" :placeholder="t('pages.position.PositionList.s24')" :options="managerOptions" />
          </n-form-item>
        </div>

        <n-divider title-placement="left">{{ t('pages.position.PositionList.s25') }}</n-divider>
        <n-form-item path="description" :label="t('pages.position.PositionList.s26')">
          <n-input v-model:value="formState.description" type="textarea" :rows="4" :placeholder="t('pages.position.PositionList.s27')" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="flex justify-end gap-2">
          <n-button @click="modalVisible = false">{{ t('pages.position.PositionList.s28') }}</n-button>
          <n-button type="primary" :loading="saving" :disabled="saving" @click="handleSave">{{ t('pages.position.PositionList.s29') }}</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 职位详情弹窗 -->
    <n-modal
      v-model:show="detailVisible"
      preset="card"
      :title="t('pages.position.PositionList.s30')"
      style="width: 700px; max-width: 90vw"
    >
      <template v-if="selectedPosition">
        <div class="grid grid-cols-2 gap-4">
          <div><strong>{{ t('pages.position.PositionList.s31') }}</strong>{{ selectedPosition.code }}</div>
          <div><strong>{{ t('pages.position.PositionList.s32') }}</strong>{{ selectedPosition.title }}</div>
          <div><strong>{{ t('pages.position.PositionList.s33') }}</strong>{{ selectedPosition.departmentName }}</div>
          <div><strong>{{ t('pages.position.PositionList.s34') }}</strong>{{ selectedPosition.demandName || '—' }}</div>
          <div><strong>{{ t('pages.position.PositionList.s35') }}</strong>{{ selectedPosition.processName || selectedPosition.process }}</div>
          <div><strong>{{ t('pages.position.PositionList.s36') }}</strong><n-tag :type="getPriorityType(selectedPosition.priority)">{{ selectedPosition.priority || '—' }}</n-tag></div>
          <div><strong>{{ t('pages.position.PositionList.s37') }}</strong><n-tag :type="getStatusType(selectedPosition.state)">{{ selectedPosition.stateDisplay }}</n-tag></div>
          <div><strong>{{ t('pages.position.PositionList.s38') }}</strong>{{ selectedPosition.headcount }}{{ t('pages.position.PositionList.s39') }}</div>
          <div><strong>{{ t('pages.position.PositionList.s40') }}</strong>{{ selectedPosition.filledCount }}{{ t('pages.position.PositionList.s41') }}</div>
          <div><strong>{{ t('pages.position.PositionList.s47') }}</strong>{{ salaryText(selectedPosition) }}</div>
          <div><strong>{{ t('pages.position.PositionList.s42') }}</strong>{{ selectedPosition.location || '—' }}</div>
          <div><strong>{{ t('pages.position.PositionList.s43') }}</strong>{{ selectedPosition.createdAt }}</div>
        </div>
        <n-divider />
        <div class="grid grid-cols-2 gap-4">
          <div><strong>{{ t('pages.position.PositionList.s44') }}</strong>{{ selectedPosition.ownerName || '—' }}</div>
          <div class="col-span-2"><strong>{{ t('pages.position.PositionList.s45') }}</strong>{{ selectedPosition.hiringManagerName || '—' }}</div>
        </div>
        <n-divider />
        <div>
          <strong>{{ t('pages.position.PositionList.s46') }}</strong>
          <p>{{ selectedPosition.description || '—' }}</p>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, computed, h, onMounted } from 'vue'
import { useMessage, NTag, NButton, NSpace, NDropdown } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import {
  listPositions,
  createPosition,
  updatePosition,
  deletePosition,
  transitionPosition,
  listDepartments,
  listProcesses,
  listDemands,
  listUsers,
  extractApiError,
  type PositionRow,
  type Option,
} from '@/api/position'

const { t } = useI18n()
const message = useMessage()

const activeTab = ref('all')
const loading = ref(false)
const modalVisible = ref(false)
const detailVisible = ref(false)
const selectedPosition = ref<PositionRow | null>(null)
const formRef = ref()
const saving = ref(false)

const rows = ref<PositionRow[]>([])

const departmentOptions = ref<Option[]>([])
const demandOptions = ref<Option[]>([])
const processOptions = ref<Option[]>([])
const ownerOptions = ref<Option[]>([])
const managerOptions = ref<Option[]>([])
const priorityOptions = [
  { label: '高', value: '高' },
  { label: '中', value: '中' },
  { label: '低', value: '低' },
]

const defaultFormState = {
  title: '',
  department: undefined as string | undefined,
  demand: undefined as string | undefined,
  process: undefined as string | undefined,
  priority: '中',
  headCount: 1,
  salaryMin: null as number | null,
  salaryMax: null as number | null,
  location: '',
  owner: undefined as string | number | undefined,
  hiringManager: undefined as string | number | undefined,
  description: '',
}

const formState = reactive<any>({ ...defaultFormState })

// 🔴 Naive/async-validator 陷阱：规则只写 { required, trigger } 时走「string 类型」校验，
// 而 n-select 绑定的是数值型 id（user.id=1）时会被判非法 —— 明明选了下拉仍报「请选择 X」。
// 用自定义 validator 做「非空」判断，类型无关（字符串 UUID / 数值 id 均通过）。
const reqSelect = (message: string) => ({
  required: true,
  trigger: ['blur', 'change'] as const,
  validator: (_rule: unknown, value: unknown) => {
    if (value === undefined || value === null || value === '') return new Error(message)
    return true
  },
})

// ===== 状态机：合法流转动作（按下限状态映射） =====
const TRANSITION_LABELS: Record<string, string> = {
  submit_publish: '提交发布',
  publish: '发布',
  start_recruiting: '开始招聘',
  pause: '暂停招聘',
  resume: '恢复招聘',
  close: '关闭',
}
const VALID_TRANSITIONS: Record<string, string[]> = {
  DRAFT: ['submit_publish'],
  PENDING_PUBLISH: ['publish'],
  PUBLISHED: ['start_recruiting', 'close'],
  RECRUITING: ['pause', 'close'],
  PAUSED: ['resume', 'close'],
  UNPUBLISHED: ['publish', 'close'],
  CLOSED: [],
}

const filteredRows = computed(() =>
  activeTab.value === 'all' ? rows.value : rows.value.filter((r) => r.state === activeTab.value),
)

const getStatusType = (state: string): 'success' | 'warning' | 'error' | 'info' | 'default' => {
  const map: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
    DRAFT: 'default',
    PENDING_PUBLISH: 'info',
    PUBLISHED: 'info',
    RECRUITING: 'success',
    PAUSED: 'warning',
    UNPUBLISHED: 'default',
    CLOSED: 'error',
  }
  return map[state] || 'default'
}

const getPriorityType = (priority?: string): 'error' | 'warning' | 'success' | 'default' => {
  const map: Record<string, 'error' | 'warning' | 'success' | 'default'> = {
    高: 'error',
    中: 'warning',
    低: 'success',
  }
  return (priority && map[priority]) || 'default'
}

const salaryText = (row: PositionRow): string => {
  const min = row.salaryMin
  const max = row.salaryMax
  if (min != null && max != null) return `${min} - ${max} 元`
  if (min != null) return `${min} 元起`
  if (max != null) return `最高 ${max} 元`
  return '面议'
}

// ===== 数据加载 =====
async function loadPositions() {
  loading.value = true
  try {
    rows.value = await listPositions()
  } finally {
    loading.value = false
  }
}

async function loadOptions() {
  const [depts, procs, demands, users] = await Promise.all([
    listDepartments(),
    listProcesses(),
    listDemands(),
    listUsers(),
  ])
  departmentOptions.value = depts
  processOptions.value = procs
  demandOptions.value = demands
  ownerOptions.value = users
  managerOptions.value = users
}

// ===== 弹窗/动作 =====
const handleCreate = () => {
  selectedPosition.value = null
  Object.assign(formState, defaultFormState)
  modalVisible.value = true
}

const handleEdit = (record: PositionRow) => {
  selectedPosition.value = record
  Object.assign(formState, {
    title: record.title,
    department: record.department,
    demand: record.demand || undefined,
    process: record.process,
    priority: record.priority || '中',
    headCount: record.headcount,
    salaryMin: record.salaryMin != null ? Number(record.salaryMin) : null,
    salaryMax: record.salaryMax != null ? Number(record.salaryMax) : null,
    location: record.location || '',
    owner: record.owner,
    hiringManager: record.hiringManager,
    description: record.description || '',
  })
  modalVisible.value = true
}

const handleView = (record: PositionRow) => {
  selectedPosition.value = record
  detailVisible.value = true
}

const handleSave = async () => {
  saving.value = true
  try {
    await formRef.value?.validate()
    const payload = {
      title: formState.title,
      department: formState.department,
      demand: formState.demand || null,
      process: formState.process,
      priority: formState.priority,
      headcount: formState.headCount,
      salaryMin: formState.salaryMin,
      salaryMax: formState.salaryMax,
      location: formState.location,
      owner: formState.owner,
      hiringManager: formState.hiringManager,
      description: formState.description,
    }
    if (selectedPosition.value) {
      await updatePosition(selectedPosition.value.id, payload)
      message.success('职位更新成功')
    } else {
      await createPosition(payload)
      message.success('职位创建成功')
    }
    modalVisible.value = false
    await loadPositions()
  } catch (error) {
    message.error(extractApiError(error, '保存失败'))
  } finally {
    saving.value = false
  }
}

const handleTransition = async (record: PositionRow, action: string) => {
  try {
    await transitionPosition(record.id, action)
    message.success(`已执行：${TRANSITION_LABELS[action] || action}`)
    await loadPositions()
  } catch (error) {
    message.error(extractApiError(error, '状态流转失败'))
  }
}

const handleDelete = async (record: PositionRow) => {
  if (!window.confirm(`确认删除职位「${record.title}」？该操作会软删除（不可恢复展示）。`)) return
  try {
    await deletePosition(record.id)
    message.success('职位已删除')
    await loadPositions()
  } catch (error) {
    message.error(extractApiError(error, '删除失败'))
  }
}

const columns = computed(() => [
  { title: '职位编号', key: 'code', width: 110 },
  { title: '职位名称', key: 'title', width: 180, ellipsis: { tooltip: true } },
  { title: '所属部门', key: 'departmentName', width: 110 },
  { title: '关联需求', key: 'demandName', width: 140, ellipsis: { tooltip: true } },
  { title: '招聘流程', key: 'processName', width: 140, ellipsis: { tooltip: true } },
  {
    title: '优先级',
    key: 'priority',
    width: 80,
    render: (row: PositionRow) => h(NTag, { type: getPriorityType(row.priority) }, { default: () => row.priority || '—' }),
  },
  {
    title: '职位状态',
    key: 'state',
    width: 90,
    render: (row: PositionRow) => h(NTag, { type: getStatusType(row.state) }, { default: () => row.stateDisplay }),
  },
  {
    title: '需求/已入职',
    key: 'headcount',
    width: 110,
    render: (row: PositionRow) => `${row.headcount}/${row.filledCount}`,
  },
  { title: '创建时间', key: 'createdAt', width: 170 },
  {
    title: '操作',
    key: 'action',
    width: 220,
    fixed: 'right',
    render: (row: PositionRow) => {
      const children = [
        h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => handleView(row) }, { default: () => '查看' }),
        h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => handleEdit(row) }, { default: () => '编辑' }),
      ]
      const actions = VALID_TRANSITIONS[row.state] || []
      if (actions.length) {
        const opts = actions.map((a) => ({ label: TRANSITION_LABELS[a], key: a }))
        children.push(
          h(
            NDropdown,
            { options: opts, onSelect: (k: string) => handleTransition(row, k), trigger: 'click' },
            { default: () => h(NButton, { text: true, type: 'primary', size: 'small' }, { default: () => '状态流转' }) },
          ),
        )
      }
      children.push(
        h(NButton, { text: true, type: 'error', size: 'small', onClick: () => handleDelete(row) }, { default: () => '删除' }),
      )
      return h(NSpace, { size: 'small' }, () => children)
    },
  },
])

onMounted(() => {
  loadPositions()
  loadOptions()
})
</script>

<style scoped>
.page-container {
  padding: var(--space-6);
}

.page-header {
  margin-bottom: var(--space-6);
}

.page-title {
  margin: 0;
  font-size: var(--fs-20);
  font-weight: 500;
}
</style>
