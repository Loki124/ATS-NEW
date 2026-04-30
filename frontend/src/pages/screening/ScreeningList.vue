<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">简历筛选</h1>
    </div>
    <a-card>
      <a-table :columns="columns" :dataSource="dataSource" rowKey="id" :locale="{ emptyText: '暂无数据' }" />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface DataItem {
  id: string
  candidate: string
  position: string
  status: string
}

const dataSource = ref<DataItem[]>([])

const columns = [
  { title: '候选人', dataIndex: 'candidate', key: 'candidate' },
  { title: '应聘职位', dataIndex: 'position', key: 'position' },
  { title: '筛选状态', dataIndex: 'status', key: 'status' }
]
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>