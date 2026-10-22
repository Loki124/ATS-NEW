<template>
  <div class="page-container">
    <!-- 模型 B（SETTINGS_PAGE_STRUCTURE.md §2.2）：header 为 .page-container 直接子元素，
         header→内容间距由外壳 .settings-scroll :deep(.page-container) 的 gap 独家提供。 -->
    <div class="page-header">
      <h1 class="page-title">{{ t('pages.settings.PermissionManagement.s1') }}</h1>
      <p class="page-subtitle">{{ t('pages.settings.PermissionManagement.s2') }}</p>
    </div>

    <!-- 列表区：区域滚动（R-215）—— .data-body 自身不滚，滚动只发生在 .table-wrap 内的表格体，
         页头 / 筛选工具条 / 分页器保持固定。外壳用全局 .panel-shell（8px 内衬 + 撑满高度）。 -->
    <div class="data-body">
      <div class="glass-panel panel-shell">
        <RolesTab />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
/**
 * PermissionManagement.vue — 身份管理主页面 (2026-09-18 重构)
 *
 * 原为 4-tab 主壳 (资源/模板/角色/用户授权)，本次拆解:
 *   - 资源管理 (ResourcesTab) → 独立菜单页 PermissionResources.vue (/settings/permissions/resources)
 *   - 角色管理 (RolesTab)     → 本页主体，菜单更名「身份管理」，去 tab 化
 *   - 用户授权 (UserRolesTab) → 移除：与「用户管理」页的分配角色弹窗重复
 *     (两者均写 user_roles 表: 本页走 /api/v1/user-roles/，用户管理走
 *      /api/v1/permissions/users/{id}/roles/，授权入口统一收敛到用户管理页)
 *
 * 2026-10-15 兵哥：模板管理 (TemplatesTab) 入口与弹窗整体下线 ——
 *   模板基础信息（编码/描述/是否预置/权限码数量）已并入模板下拉的「查看权限码」弹窗
 *   （components/role/PermissionCodeModal.vue），列表页不再保留「模板管理」按钮。
 */
import RolesTab from './permission/RolesTab.vue'
const { t } = useI18n()
</script>

<style scoped>
/* === 数据列表页标准结构（SETTINGS_PAGE_STRUCTURE.md §2.2 + AGENTS.md R-215）
   模型 B：.page-container > .page-header + .data-body > .glass-panel.panel-shell
                              > .roles-tab > .toolbar + .table-wrap > n-data-table[flex-height]
   - .data-body 取代原 .page-body：后者被 SettingsLayout :deep(.page-body)
     {overflow-y:auto!important} 强制整页滚动 → 与表格体内部滚动叠成**双滚动条**，
     且标题/工具条会随整页滚走（违反 R-215「区域滚动」）。规范 §2.2 称此为「致命陷阱」。
   - .panel-shell / .toolbar / .table-wrap 全部复用 glass.css 全局类，本页不再私有重写。 */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
/* 标题区（2026-10-15 兵哥：模板管理入口下线，页头回归纯标题） */
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
