<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">邀约中心</h1>
    </div>
    <a-card>
      <a-table
        :columns="columns"
        :data-source="dataSource"
        :row-key="(record: any) => record.id"
        :locale="{ emptyText: '暂无数据' }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag color="cyan">{{ record.status }}</a-tag>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Table as ATable, Card as ACard, Tag as ATag } from 'ant-design-vue'

const columns = ref([
  { title: '候选人', dataIndex: 'candidate', key: 'candidate' },
  { title: '应聘职位', dataIndex: 'position', key: 'position' },
  { title: '邀约状态', dataIndex: 'status', key: 'status' },
])

const dataSource = ref<any[]>([])
</script>
