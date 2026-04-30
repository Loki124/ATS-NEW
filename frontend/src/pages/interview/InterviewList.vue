<script setup lang="ts">
import { ref, h } from 'vue'
import { Table as aTable, Card as aCard, Tag as aTag } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'

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
    dataIndex: 'candidate',
    key: 'candidate'
  },
  {
    title: '应聘职位',
    dataIndex: 'position',
    key: 'position'
  },
  {
    title: '面试时间',
    dataIndex: 'time',
    key: 'time'
  },
  {
    title: '面试官',
    dataIndex: 'interviewer',
    key: 'interviewer'
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    customRender: ({ text }: { text: string }) => h(aTag, { color: 'blue' }, () => text)
  }
])

const dataSource = ref<DataItem[]>([])

const locale = ref({
  emptyText: '暂无数据'
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">面试管理</h1>
    </div>
    <a-card>
      <a-table
        :columns="columns"
        :data-source="dataSource"
        :row-key="(record: DataItem) => record.id"
        :locale="locale"
      />
    </a-card>
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
