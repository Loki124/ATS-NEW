<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ t('pages.notification.NotificationList.s1') }}</h1>
    </div>
    <n-card :bordered="false" class="rounded-xl">
      <n-data-table
        :columns="columns"
        :data="dataSource"
        :row-key="(row: any) => row.id"
        :max-height="520"
        :virtual-scroll="true"
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, h } from 'vue'
import { NTag } from 'naive-ui'
const { t } = useI18n()

interface DataItem {
  id: string
  title: string
  type: string
  time: string
  status: string
}

const dataSource = ref<DataItem[]>([])

const columns = [
  { title: '标题', key: 'title', width: 320, render: (row: DataItem) => row.title },
  { title: '类型', key: 'type', width: 120, render: (row: DataItem) => row.type },
  { title: '时间', key: 'time', width: 220, render: (row: DataItem) => row.time },
  { title: '状态', key: 'status', width: 120, render: (row: DataItem) => h(NTag, { type: 'info' }, { default: () => row.status }) },
]
</script>

<style scoped>
.page-header { margin-bottom: var(--space-6); }
.page-title { font-size: var(--fs-24); font-weight: 600; margin: 0; }
</style>
