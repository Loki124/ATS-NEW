<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">数据字典</h1>
    </div>
    <a-card>
      <a-table :columns="columns" :dataSource="dataSource" rowKey="id" :pagination="false" />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
const dataSource = ref([])
const columns = [
  { title: '字典名称', dataIndex: 'name', key: 'name' },
  { title: '所属分类', dataIndex: 'category', key: 'category' },
  { title: '状态', dataIndex: 'status', key: 'status' }
]
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
