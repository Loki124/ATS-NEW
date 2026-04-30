<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">人才库</h1>
    </div>
    <a-card>
      <a-table :columns="columns" :dataSource="dataSource" rowKey="id" :locale="{ emptyText: '暂无数据' }" />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const dataSource = ref([])

const columns = [
  { title: '姓名', dataIndex: 'name', key: 'name' },
  { title: '手机号', dataIndex: 'phone', key: 'phone' },
  { title: '最高学历', dataIndex: 'education', key: 'education' },
  { title: '人才库类型', dataIndex: 'type', key: 'type' }
]
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
