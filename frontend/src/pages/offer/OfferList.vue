<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">Offer管理</h1>
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
  candidate: string
  position: string
  status: string
}

const dataSource = ref<DataItem[]>([])

const columns = [
  { title: '候选人', key: 'candidate', render: (row: DataItem) => row.candidate },
  { title: '应聘职位', key: 'position', render: (row: DataItem) => row.position },
  { title: 'Offer状态', key: 'status', render: (row: DataItem) => h(NTag, { type: 'info' }, { default: () => row.status }) },
]
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
