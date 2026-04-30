<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">系统设置</h1>
    </div>
    <a-card>
      <a-tabs v-model:activeKey="activeTab">
        <a-tab-pane key="process" tab="招聘流程管理">
          <a-table :columns="processColumns" :dataSource="processData" rowKey="id" :pagination="false" />
        </a-tab-pane>
        <a-tab-pane key="stage" tab="阶段配置">
          <a-table :columns="stageColumns" :dataSource="stageData" rowKey="id" :pagination="false" />
        </a-tab-pane>
        <a-tab-pane key="scoring" tab="评分规则">
          <a-table :columns="scoringColumns" :dataSource="scoringData" rowKey="id" :pagination="false" />
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeTab = ref('process')

const processData = ref([])
const processColumns = [
  { title: '流程名称', dataIndex: 'name', key: 'name' },
  { title: '流程编码', dataIndex: 'code', key: 'code' },
  { title: '状态', dataIndex: 'status', key: 'status' }
]

const stageData = ref([])
const stageColumns = [
  { title: '阶段名称', dataIndex: 'name', key: 'name' },
  { title: '阶段类型', dataIndex: 'type', key: 'type' }
]

const scoringData = ref([])
const scoringColumns = [
  { title: '规则名称', dataIndex: 'name', key: 'name' },
  { title: '规则类型', dataIndex: 'type', key: 'type' }
]
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>