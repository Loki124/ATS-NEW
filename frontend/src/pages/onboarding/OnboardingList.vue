<script setup lang="ts">
import { h, ref } from 'vue'
import { Table, Card, Tag } from 'ant-design-vue'

const columns = ref([
  { title: '候选人', dataIndex: 'candidate', key: 'candidate' },
  { title: '应聘职位', dataIndex: 'position', key: 'position' },
  { title: '预计入职日期', dataIndex: 'date', key: 'date' },
  { 
    title: '入职状态', 
    dataIndex: 'status', 
    key: 'status',
    customRender: ({ text }: { text: string }) => h(Tag, { color: 'purple' }, () => text)
  },
])

const dataSource = ref([])
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">待入职</h1>
    </div>
    <Card>
      <Table 
        :columns="columns" 
        :dataSource="dataSource" 
        :rowKey="(record: any) => record.id"
        :locale="{ emptyText: '暂无数据' }"
      />
    </Card>
  </div>
</template>
