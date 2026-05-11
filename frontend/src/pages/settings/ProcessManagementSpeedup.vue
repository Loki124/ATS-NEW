<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">流程管理</h1>
    </div>
    <a-card>
      <a-table
        :columns="columns"
        :dataSource="dataSource"
        :loading="loading"
        :pagination="{ pageSize: 10 }"
        rowKey="id"
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
              <a-button type="link" size="small">配置</a-button>
              <a-button type="link" size="small">编辑</a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { get } from '../../api/auth'

const loading = ref(false)
const dataSource = ref<any[]>([])

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
    console.error('获取数据失败', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>