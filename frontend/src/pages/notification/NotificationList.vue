<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">消息通知</h1>
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
  { title: '标题', dataIndex: 'title', key: 'title' },
  { title: '类型', dataIndex: 'type', key: 'type' },
  { title: '时间', dataIndex: 'time', key: 'time' },
  { title: '状态', dataIndex: 'status', key: 'status' }
]
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
