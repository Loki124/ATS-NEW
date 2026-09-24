<template>
  <div class="page-container permission-resources">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">{{ t('pages.settings.PermissionResources.s1') }}</h1>
          <p class="page-subtitle">{{ t('pages.settings.PermissionResources.s2') }}</p>
        </div>
      </div>
      <n-card :bordered="false" class="glass-panel resources-shell">
        <ResourcesTab />
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
/**
 * PermissionResources.vue — 资源管理独立页 (2026-09-18 拆分)
 *
 * 原「权限管理」4-tab 主壳中的资源 tab 抽出为独立菜单项，
 * 归入设置侧边栏「权限管理」分组（/settings/permissions/resources）。
 * 业务逻辑仍在 ResourcesTab 子组件（注册菜单/按钮/字段/API 资源码）。
 */
import { NCard } from 'naive-ui'
import ResourcesTab from './permission/ResourcesTab.vue'
const { t } = useI18n()
</script>

<style scoped>
/* 与 PermissionManagement 同款 page-header + page-body 三件套（滚动契约见 SettingsLayout :deep 规则） */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-header {
  flex-shrink: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.resources-shell {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding: var(--space-4);
}
</style>
