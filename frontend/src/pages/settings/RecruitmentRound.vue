<template>
  <div class="interview-round">
    <div class="page-header">
      <h2>面试轮次管理</h2>
      <n-space>
        <n-input v-model:value="keyword" placeholder="搜索轮次" clearable style="width: 200px" />
        <n-button type="primary" @click="showModal = true">
          <template #icon><n-icon :component="AddOutline" /></template>
          新增轮次
        </n-button>
      </n-space>
    </div>

    <n-data-table
      :columns="columns"
      :data="rounds"
      :loading="loading"
      :pagination="{ pageSize: 20 }"
      :row-key="(r) => r.id"
    />

    <n-modal v-model:show="showModal" preset="card" :title="editing ? '编辑轮次' : '新增轮次'" style="width: 520px">
      <n-form :model="form" label-placement="top">
        <n-form-item label="轮次名称" required>
          <n-input v-model:value="form.name" placeholder="如：初试/复试/终试" />
        </n-form-item>
        <n-form-item label="面试评价表">
          <n-input v-model:value="form.evaluationFormName" placeholder="如：通用评价表（可选）" />
        </n-form-item>
        <n-form-item label="设为通用评价表">
          <n-switch v-model:value="form.isUniversal" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="form.description" type="textarea" :rows="2" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleSave">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import { useMessage, NButton, NTag, NPopconfirm, NIcon, NSpace, NInput, NSwitch, NForm, NFormItem, NModal, NDataTable } from 'naive-ui'
import { AddOutline, EditOutline, PowerOutline } from '@vicons/ionicons5'
import { listRounds, createRound, updateRound, updateRoundStatus } from '../../api/recruitment-process'

const message = useMessage()
const keyword = ref('')
const rounds = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const showModal = ref(false)
const editing = ref<any>(null)
const form = reactive({
  name: '',
  description: '',
  evaluationFormName: '',
  isUniversal: false,
})

const columns = [
  { title: '轮次编号', key: 'code', width: 100 },
  { title: '轮次名称', key: 'name', width: 140 },
  { title: '面试评价表', key: 'evaluationFormName', width: 160, render: (r: any) => r.evaluationFormName || '-' },
  {
    title: '通用评价表',
    key: 'isUniversal',
    width: 110,
    render: (r: any) => r.isUniversal ? h(NTag, { type: 'warning', size: 'small' }, { default: () => '通用' }) : '-',
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (r: any) => h(NTag, { type: r.status === 'ACTIVE' ? 'success' : 'default', size: 'small' }, { default: () => r.status === 'ACTIVE' ? '启用' : '停用' }),
  },
  {
    title: '操作',
    key: 'action',
    width: 200,
    fixed: 'right' as const,
    render: (row: any) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { size: 'small', text: true, onClick: () => handleEdit(row) }, { default: () => '编辑' }),
      h(NButton, { size: 'small', text: true, onClick: () => handleToggleStatus(row) }, { default: () => row.status === 'ACTIVE' ? '停用' : '启用' }),
    ]),
  },
]

async function loadList() {
  loading.value = true
  try {
    rounds.value = await listRounds({ keyword: keyword.value || undefined })
  } catch (e: any) {
    message.error(e?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  editing.value = null
  Object.assign(form, { name: '', description: '', evaluationFormName: '', isUniversal: false })
  showModal.value = true
}

function handleEdit(row: any) {
  editing.value = row
  Object.assign(form, {
    name: row.name,
    description: row.description || '',
    evaluationFormName: row.evaluationFormName || '',
    isUniversal: row.isUniversal,
  })
  showModal.value = true
}

async function handleSave() {
  if (!form.name.trim()) {
    message.error('轮次名称必填')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await updateRound(editing.value.id, form)
      message.success('已保存')
    } else {
      await createRound(form)
      message.success('已新增')
    }
    showModal.value = false
    loadList()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleToggleStatus(row: any) {
  const newStatus = row.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
  try {
    await updateRoundStatus(row.id, newStatus)
    message.success(`已${newStatus === 'ACTIVE' ? '启用' : '停用'}`)
    loadList()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '操作失败')
  }
}

onMounted(() => loadList())
</script>

<style scoped>
.interview-round {
  padding: 20px 24px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
</style>
