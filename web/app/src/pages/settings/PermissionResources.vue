<template>
  <div class="page-container">
    <!-- 模型 B（SETTINGS_PAGE_STRUCTURE.md §2.2）：header 为 .page-container 直接子元素，
         header→内容间距由外壳 .settings-scroll :deep(.page-container) 的 gap 独家提供。 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.PermissionResources.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.PermissionResources.s2') }}</p>
      </div>
    </div>

    <!-- 列表区：区域滚动（R-215）—— .data-body 自身不滚，滚动只发生在 .table-wrap 内的表格体，
         页头 / 筛选工具条 / 分页器保持固定。外壳用全局 .panel-shell（8px 内衬 + 撑满高度）。 -->
    <div class="data-body">
      <div class="glass-panel panel-shell">
        <ResourcesTab />
      </div>
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
import ResourcesTab from './permission/ResourcesTab.vue'
const { t } = useI18n()
</script>

<style scoped>
/* === 数据列表页标准结构（SETTINGS_PAGE_STRUCTURE.md §2.2 + AGENTS.md R-215）
   模型 B：.page-container > .page-header + .data-body > .glass-panel.panel-shell
                              > .resources-tab > .toolbar + .table-wrap > n-data-table[flex-height]
   - .data-body 取代原 .page-body：后者被 SettingsLayout :deep(.page-body)
     {overflow-y:auto!important} 强制整页滚动 → 与表格体内部滚动叠成**双滚动条**，
     且标题/筛选行会随整页滚走（违反 R-215「区域滚动」）。规范 §2.2 称此为「致命陷阱」。
   - .panel-shell / .toolbar / .table-wrap 全部复用 glass.css 全局类，本页不再私有重写。 */
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
.data-body {
  flex: 1;
  min-height: 0;
  overflow-y: hidden;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
</style>
