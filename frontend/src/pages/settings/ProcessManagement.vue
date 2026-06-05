<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">招聘流程管理</h1>
      <n-button type="primary" @click="handleAdd">
        <template #icon><n-icon :component="AddOutline" /></template>
        新增流程
      </n-button>
    </div>
    <n-card>
      <n-data-table
        :columns="columns"
        :data="dataSource"
        :loading="loading"
        :row-key="(row: any) => row.id"
        :pagination="{ pageSize: 10 }"
      />
    </n-card>

    <!-- 新增/编辑弹窗 -->
    <n-modal
      v-model:show="modalVisible"
      preset="dialog"
      :title="modalTitle"
      positive-text="确定"
      negative-text="取消"
      :loading="submitting"
      @positive-click="handleSubmit"
      @negative-click="modalVisible = false"
    >
      <n-form :model="formData" label-placement="left" :label-width="80" ref="formRef" class="mt-4">
        <n-form-item label="流程名称" path="name">
          <n-input v-model:value="formData.name" placeholder="请输入流程名称" />
        </n-form-item>
        <n-form-item label="流程编码" path="code">
          <n-input v-model:value="formData.code" placeholder="请输入流程编码" :disabled="!!formData.id" />
        </n-form-item>
        <n-form-item label="适用范围" path="applicableRange">
          <n-select v-model:value="formData.applicableRange" placeholder="请选择适用范围" :options="applicableRangeOptions" />
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input v-model:value="formData.description" type="textarea" placeholder="请输入描述" :rows="3" />
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useMessage, NTag, NButton, NSpace } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { get, post, put, del } from '../../api/auth'

const message = useMessage()

const loading = ref(false)
const dataSource = ref<any[]>([])
const modalVisible = ref(false)
const modalTitle = ref('新增流程')
const submitting = ref(false)
const formRef = ref()

const formData = ref({
  id: '',
  name: '',
  code: '',
  applicableRange: 'ALL',
  description: ''
})

const applicableRangeOptions = [
  { label: '全部', value: 'ALL' },
  { label: '社会招聘', value: 'SOCIAL' },
  { label: '校园招聘', value: 'CAMPUS' }
]

const columns = [
  { title: '流程名称', key: 'name' },
  { title: '流程编码', key: 'code' },
  { title: '适用范围', key: 'applicableRange' },
  {
    title: '阶段数',
    key: 'stages',
    render: (row: any) => `${row.stages?.length || 0} 个阶段`
  },
  {
    title: '状态',
    key: 'status',
    render: (row: any) => h(NTag, { type: row.status === 'ACTIVE' ? 'success' : 'error' }, { default: () => row.status === 'ACTIVE' ? '启用' : '禁用' })
  },
  {
    title: '操作',
    key: 'action',
    width: 150,
    render: (row: any) => h(NSpace, {}, () => [
      h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => handleEdit(row) }, { default: () => '编辑' }),
      h(NButton, { text: true, type: 'error', size: 'small', onClick: () => handleDelete(row) }, { default: () => '删除' })
    ])
  }
]

const fetchData = async () => {
  loading.value = true
  try {
    const res = await get('/processes')
    if (res.data.success) {
      dataSource.value = res.data.data
    }
  } catch (error) {
    message.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  formData.value = { id: '', name: '', code: '', applicableRange: 'ALL', description: '' }
  modalTitle.value = '新增流程'
  modalVisible.value = true
}

const handleEdit = (record: any) => {
  formData.value = { ...record }
  modalTitle.value = '编辑流程'
  modalVisible.value = true
}

const handleDelete = async (record: any) => {
  try {
    await del(`/processes/${record.id}`)
    message.success('删除成功')
    fetchData()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '删除失败')
  }
}

const handleSubmit = async () => {
  submitting.value = true
  try {
    if (formData.value.id) {
      await put(`/processes/${formData.value.id}`, formData.value)
      message.success('更新成功')
    } else {
      await post('/processes', formData.value)
      message.success('创建成功')
    }
    modalVisible.value = false
    fetchData()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
