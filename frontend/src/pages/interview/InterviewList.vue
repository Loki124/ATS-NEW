<script setup lang="ts">
import { ref, h } from 'vue'
import { NTag } from 'naive-ui'

interface DataItem {
  id: string
  candidate: string
  position: string
  time: string
  interviewer: string
  status: string
}

const columns = ref([
  {
    title: '候选人',
    key: 'candidate',
    render: (row: DataItem) => row.candidate,
  },
  {
    title: '应聘职位',
    key: 'position',
    render: (row: DataItem) => row.position,
  },
  {
    title: '面试时间',
    key: 'time',
    render: (row: DataItem) => row.time,
  },
  {
    title: '面试官',
    key: 'interviewer',
    render: (row: DataItem) => row.interviewer,
  },
  {
    title: '状态',
    key: 'status',
    render: (row: DataItem) => h(NTag, { type: 'info' }, { default: () => row.status }),
  },
])

const dataSource = ref<DataItem[]>([])
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">面试管理</h1>
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
.page-container {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}
</style>
