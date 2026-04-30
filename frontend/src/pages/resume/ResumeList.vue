<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">我找的简历</h1>
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
  { title: '简历名称', dataIndex: 'name', key: 'name' },
  { title: '候选人', dataIndex: 'candidate', key: 'candidate' },
  { title: '来源', dataIndex: 'source', key: 'source' },
  { title: '上传时间', dataIndex: 'time', key: 'time' }
]
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
