<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">评分规则</h1>
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
  { title: '规则名称', dataIndex: 'name', key: 'name' },
  { title: '规则类型', dataIndex: 'type', key: 'type' },
  { title: '优先级', dataIndex: 'priority', key: 'priority' }
]
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
