<script setup lang="ts">
import { h, ref } from 'vue'
import { NTag } from 'naive-ui'

interface DataItem {
  id: string
  candidate: string
  position: string
  date: string
  status: string
}

const columns = ref([
  { title: '候选人', key: 'candidate', render: (row: DataItem) => row.candidate },
  { title: '应聘职位', key: 'position', render: (row: DataItem) => row.position },
  { title: '预计入职日期', key: 'date', render: (row: DataItem) => row.date },
  {
    title: '入职状态',
    key: 'status',
    render: (row: DataItem) => h(NTag, { type: 'info' }, { default: () => row.status }),
  },
])

const dataSource = ref<DataItem[]>([])
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">待入职</h1>
    </div>
    <n-card :bordered="false" class="rounded-xl">
      <n-data-table
        :columns="columns"
        :data="dataSource"
        :row-key="(row: DataItem) => row.id"
      />
    </n-card>
  </div>
</template>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
