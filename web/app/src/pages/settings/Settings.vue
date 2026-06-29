<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">系统设置</h1>
    </div>
    <n-card>
      <n-tabs v-model:value="activeTab" type="line" animated>
        <n-tab-pane name="process" tab="招聘流程管理">
          <n-data-table :columns="processColumns" :data="processData" :row-key="(row: any) => row.id" :pagination="false" />
        </n-tab-pane>
        <n-tab-pane name="stage" tab="阶段配置">
          <n-data-table :columns="stageColumns" :data="stageData" :row-key="(row: any) => row.id" :pagination="false" />
        </n-tab-pane>
        <n-tab-pane name="scoring" tab="评分规则">
          <n-data-table :columns="scoringColumns" :data="scoringData" :row-key="(row: any) => row.id" :pagination="false" />
        </n-tab-pane>
      </n-tabs>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeTab = ref('process')

const processData = ref([])
const processColumns = [
  { title: '流程名称', key: 'name' },
  { title: '流程编码', key: 'code' },
  { title: '状态', key: 'status' }
]

const stageData = ref([])
const stageColumns = [
  { title: '阶段名称', key: 'name' },
  { title: '阶段类型', key: 'type' }
]

const scoringData = ref([])
const scoringColumns = [
  { title: '规则名称', key: 'name' },
  { title: '规则类型', key: 'type' }
]
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
