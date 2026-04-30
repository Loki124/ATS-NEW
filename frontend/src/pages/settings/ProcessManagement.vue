<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">招聘流程管理</h1>
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
  { title: '流程名称', dataIndex: 'name', key: 'name' },
  { title: '流程编码', dataIndex: 'code', key: 'code' },
  { title: '阶段数', dataIndex: 'stages', key: 'stages' },
  { title: '状态', dataIndex: 'status', key: 'status' }
]
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
