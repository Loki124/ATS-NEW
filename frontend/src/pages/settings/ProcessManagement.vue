<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">招聘流程管理</h1>
      <a-button type="primary" @click="handleAdd">
        <template #icon><PlusOutlined /></template>
        新增流程
      </a-button>
    </div>
    <a-card>
      <a-table
        :columns="columns"
        :dataSource="dataSource"
        :loading="loading"
        rowKey="id"
        :pagination="{ pageSize: 10 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'ACTIVE' ? 'green' : 'red'">
              {{ record.status === 'ACTIVE' ? '启用' : '禁用' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'stages'">
            {{ record.stages?.length || 0 }} 个阶段
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="handleEdit(record)">编辑</a-button>
              <a-button type="link" size="small" danger @click="handleDelete(record)">删除</a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 新增/编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="modalTitle"
      @ok="handleSubmit"
      @cancel="modalVisible = false"
      :confirmLoading="submitting"
    >
      <a-form :model="formData" :label-col="{ span: 6 }" ref="formRef">
        <a-form-item label="流程名称" name="name">
          <a-input v-model:value="formData.name" placeholder="请输入流程名称" />
        </a-form-item>
        <a-form-item label="流程编码" name="code">
          <a-input v-model:value="formData.code" placeholder="请输入流程编码" :disabled="!!formData.id" />
        </a-form-item>
        <a-form-item label="适用范围" name="applicableRange">
          <a-select v-model:value="formData.applicableRange" placeholder="请选择适用范围">
            <a-select-option value="ALL">全部</a-select-option>
            <a-select-option value="SOCIAL">社会招聘</a-select-option>
            <a-select-option value="CAMPUS">校园招聘</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="描述" name="description">
          <a-textarea v-model:value="formData.description" placeholder="请输入描述" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { get, post, put, del } from '../../api/auth'

const loading = ref(false)
const dataSource = ref([])
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

const columns = [
  { title: '流程名称', dataIndex: 'name', key: 'name' },
  { title: '流程编码', dataIndex: 'code', key: 'code' },
  { title: '适用范围', dataIndex: 'applicableRange', key: 'applicableRange' },
  { title: '阶段数', key: 'stages' },
  { title: '状态', key: 'status' },
  { title: '操作', key: 'action', width: 150 }
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