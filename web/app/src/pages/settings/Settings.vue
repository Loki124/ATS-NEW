<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ t('pages.settings.Settings.s1') }}</h1>
      <p class="page-subtitle">{{ t('pages.settings.Settings.s2') }}</p>
    </div>
    <n-card>
      <n-tabs v-model:value="activeTab" type="line" animated>
        <n-tab-pane name="process" :tab="t('pages.settings.Settings.s3')">
          <n-data-table :columns="processColumns" :data="processData" :row-key="(row: any) => row.id" :pagination="false" />
        </n-tab-pane>
        <n-tab-pane name="stage" :tab="t('pages.settings.Settings.s4')">
          <n-data-table :columns="stageColumns" :data="stageData" :row-key="(row: any) => row.id" :pagination="false" />
        </n-tab-pane>
        <n-tab-pane name="scoring" :tab="t('pages.settings.Settings.s5')">
          <n-data-table :columns="scoringColumns" :data="scoringData" :row-key="(row: any) => row.id" :pagination="false" />
        </n-tab-pane>
      </n-tabs>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref } from 'vue'
const { t } = useI18n()

const activeTab = ref('process')

const processData = ref([])
const processColumns = [
  { title: t('pages.settings.Settings.s6'), key: 'name' },
  { title: t('pages.settings.Settings.s7'), key: 'code' },
  { title: t('pages.settings.Settings.s8'), key: 'status' }
]

const stageData = ref([])
const stageColumns = [
  { title: t('pages.settings.Settings.s9'), key: 'name' },
  { title: t('pages.settings.Settings.s10'), key: 'type' }
]

const scoringData = ref([])
const scoringColumns = [
  { title: t('pages.settings.Settings.s11'), key: 'name' },
  { title: t('pages.settings.Settings.s12'), key: 'type' }
]
</script>

<style scoped>
/* 删除 scoped .page-header/.page-title 覆盖（规范：复用全局 glass.css） */
</style>
