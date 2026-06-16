<template>
  <div class="recruitment-process">
    <div class="page-header">
      <h2>招聘流程管理</h2>
      <n-space>
        <n-input v-model:value="keyword" placeholder="搜索流程名称" clearable style="width: 220px" />
        <n-button type="primary" @click="openCustomModal(null)">
          <template #icon><n-icon :component="AddOutline" /></template>
          新建流程
        </n-button>
      </n-space>
    </div>

    <n-data-table
      :columns="columns"
      :data="processes"
      :loading="loading"
      :pagination="{ pageSize: 20 }"
      :row-key="(r) => r.id"
    />

    <!-- Plan K: 自定义招聘流程 modal (原型 2) -->
    <CustomRecruitmentProcessModal
      v-model:show="showCustomModal"
      :editing="customEditing"
      @saved="onCustomSaved"
    />

    <!-- Plan T7: 流程详情 (read-only, single-column) -->
    <ProcessDetailModal
      v-model:show="showDetail"
      :process-id="detailProcessId"
      @go-edit="onGoEdit"
    />

    <!-- 新增/编辑流程弹窗 -->
    <n-modal v-model:show="showCreateModal" preset="card" :title="editing ? '编辑流程' : '新增流程'" style="width: 640px">
      <n-form :model="form" label-placement="top">
        <n-form-item label="流程名称" required>
          <n-input v-model:value="form.name" placeholder="如：社招新流程" />
        </n-form-item>
        <n-form-item label="流程说明">
          <n-input v-model:value="form.description" type="textarea" :rows="2" placeholder="可选" />
        </n-form-item>
        <n-form-item label="适用范围模式">
          <n-radio-group v-model:value="form.applicableMode">
            <n-radio value="ALL">全部满足</n-radio>
            <n-radio value="ANY">任意满足</n-radio>
          </n-radio-group>
        </n-form-item>
        <n-form-item label="是否校验简历评分">
          <n-switch v-model:value="form.validateResumeScore" />
        </n-form-item>
        <n-form-item label="流转异常提示">
          <n-input v-model:value="form.failPrompt" type="textarea" :rows="3" placeholder="候选人不满足进入条件时的展示文本（可选，留空使用默认模板）" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showCreateModal = false">取消</n-button>
          <n-button type="primary" @click="handleSave" :loading="saving">{{ editing ? '保存' : '创建（含起止阶段）' }}</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import { useMessage, NButton, NTag, NPopconfirm, NIcon, NSwitch, NSpace, NRadio, NInput, NForm, NFormItem, NModal, NDataTable, NRadioGroup } from 'naive-ui'
import { AddOutline, CreateOutline, TrashOutline, CopyOutline, PowerOutline, EyeOutline } from '@vicons/ionicons5'
import { listProcesses, getProcess, createProcess, updateProcess, deleteProcess, copyProcess, updateProcessStatus } from '../../api/recruitment-process'
import { useRouter } from 'vue-router'
import CustomRecruitmentProcessModal from './CustomRecruitmentProcessModal.vue'
import ProcessDetailModal from './ProcessDetailModal.vue'

const message = useMessage()
const router = useRouter()
const keyword = ref('')
const processes = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const showCreateModal = ref(false)
const editing = ref<any>(null)
const form = reactive({
  name: '',
  description: '',
  applicableMode: 'ALL' as 'ALL' | 'ANY',
  validateResumeScore: true,
  failPrompt: '',
})

const columns = [
  { title: '流程编号', key: 'code', width: 100 },
  { title: '流程名称', key: 'name', width: 200 },
  {
    title: '适用部门',
    key: 'applicableDepartments',
    width: 140,
    render: (r: any) => formatDepts(r.applicableDepartments),
  },
  {
    title: '阶段数',
    key: 'links',
    width: 80,
    render: (row: any) => row._count?.links ?? 0,
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row: any) => h(NTag, { type: row.status === 'ACTIVE' ? 'success' : 'default' }, { default: () => row.status === 'ACTIVE' ? '启用' : '停用' }),
  },
  { title: '最后修改人', key: 'updater', width: 120, render: (r: any) => r.updater?.realName || '-' },
  { title: '最后修改时间', key: 'updatedAt', width: 170, render: (r: any) => formatDate(r.updatedAt) },
  {
    title: '操作',
    key: 'action',
    width: 280,
    fixed: 'right' as const,
    render: (row: any) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { size: 'small', type: 'primary', text: true, onClick: () => goStages(row) }, { default: () => '阶段' }),
      h(NButton, { size: 'small', text: true, onClick: () => goDetail(row) }, { default: () => '详情' }),
      h(NButton, { size: 'small', text: true, onClick: () => handleEdit(row) }, { default: () => '编辑' }),
      h(NButton, { size: 'small', text: true, onClick: () => handleCopy(row) }, { default: () => '复制' }),
      h(NButton, { size: 'small', text: true, onClick: () => handleToggleStatus(row) }, { default: () => row.status === 'ACTIVE' ? '停用' : '启用' }),
      h(NPopconfirm, { onPositiveClick: () => handleDelete(row) }, {
        trigger: () => h(NButton, { size: 'small', text: true, type: 'error' }, { default: () => '删除' }),
        default: () => '确定要删除此流程吗？此操作不可恢复。',
      }),
    ]),
  },
]

function formatDate(s: string) {
  return s ? new Date(s).toLocaleString('zh-CN', { hour12: false }) : '-'
}

/** 适用部门字段 (JSON 数组) */
function formatDepts(d: any): string {
  if (!d) return '全部'
  if (Array.isArray(d)) {
    if (d.length === 0) return '全部'
    if (d.length <= 2) return d.join(', ')
    return `${d.slice(0, 2).join(', ')} +${d.length - 2}`
  }
  return '全部'
}

/** Plan K: 打开自定义招聘流程 modal */
const showCustomModal = ref(false)
const customEditing = ref<any>(null)

function openCustomModal(row: any | null) {
  customEditing.value = row
  showCustomModal.value = true
}

function onCustomSaved() {
  loadList()
}

async function loadList() {
  loading.value = true
  try {
    processes.value = await listProcesses({ keyword: keyword.value || undefined })
  } catch (e: any) {
    message.error(e?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  editing.value = null
  Object.assign(form, { name: '', description: '', applicableMode: 'ALL', validateResumeScore: true, failPrompt: '' })
  showCreateModal.value = true
}

function handleEdit(row: any) {
  editing.value = row
  Object.assign(form, {
    name: row.name,
    description: row.description || '',
    applicableMode: row.applicableMode || 'ALL',
    validateResumeScore: row.validateResumeScore ?? true,
    failPrompt: row.failPrompt || '',
  })
  showCreateModal.value = true
}

async function handleSave() {
  if (!form.name.trim()) {
    message.error('流程名称必填')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await updateProcess(editing.value.id, form)
      message.success('已保存')
    } else {
      await createProcess(form)
      message.success('已创建，自动添加起止两阶段')
    }
    showCreateModal.value = false
    loadList()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: any) {
  try {
    await deleteProcess(row.id)
    message.success('已删除')
    loadList()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '删除失败')
  }
}

async function handleCopy(row: any) {
  try {
    await copyProcess(row.id, { newName: `${row.name} - 副本` })
    message.success('已复制')
    loadList()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '复制失败')
  }
}

async function handleToggleStatus(row: any) {
  const newStatus = row.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
  try {
    await updateProcessStatus(row.id, newStatus)
    message.success(`已${newStatus === 'ACTIVE' ? '启用' : '停用'}`)
    loadList()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '操作失败')
  }
}

function goStages(row: any) {
  router.push(`/settings/process-stages?processId=${row.id}`)
}

// Plan T7: goDetail 打开只读详情 modal
const showDetail = ref(false)
const detailProcessId = ref('')

function goDetail(row: any) {
  detailProcessId.value = row.id
  showDetail.value = true
}

// 详情 modal 中的 "前往编辑" 按钮 -> 复用现有 handleEdit 流程
function onGoEdit(processId: string) {
  showDetail.value = false
  const row = processes.value.find((p: any) => p.id === processId)
  if (row) handleEdit(row)
}

onMounted(() => loadList())
</script>

<style scoped>
.recruitment-process {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  min-height: 100%;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-shrink: 0;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.recruitment-process :deep(.n-data-table) {
  flex: 1;
}
.recruitment-process :deep(.n-data-table-wrapper) {
  min-height: 200px;
}
</style>
