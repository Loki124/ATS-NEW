<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">消息通知</h1>
    </div>
    <n-card :bordered="false" class="rounded-xl">
      <n-data-table :columns="columns" :data="dataSource" :row-key="(row) => row.id" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, h } from 'vue'
import { NTag } from 'naive-ui'

interface DataItem {
  id: string
  title: string
  type: string
  time: string
  status: string
}

const dataSource = ref<DataItem[]>([])

const columns = [
  { title: '标题', key: 'title', render: (row: DataItem) => row.title },
  { title: '类型', key: 'type', render: (row: DataItem) => row.type },
  { title: '时间', key: 'time', render: (row: DataItem) => row.time },
  { title: '状态', key: 'status', render: (row: DataItem) => h(NTag, { type: 'info' }, { default: () => row.status }) },
]
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
