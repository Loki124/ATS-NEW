<template>
  <div class="page-container permission-management">
    <div class="page-body">
      <div class="page-header">
        <h1 class="page-title">{{ t('pages.settings.PermissionManagement.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.PermissionManagement.s2') }}</p>
      </div>

      <div class="glass-panel permission-shell">
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
/* === 2026-08-24 page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
   - 标题区固定（flex-shrink: 0）→ 配置/操作按钮始终可触达
   - 内容区自己滚（flex: 1; min-height: 0; overflow-y: auto）→ 与外层 .settings-scroll 滚职责分离
   - 结构上让 sticky header 天然占据物理空间 → 解决下方内容穿透 header 的视觉 bug === */
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
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  /* 2026-10-15 兵哥：间距朝更小收敛（16px → 8px），页头与内容靠 8px 轻隔即可分层 */
  gap: var(--space-2);
}

.permission-management {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
/* 玻璃面板作为内容根时撑满高度。
 * ⚠️ 2026-10-15 兵哥：内边距 16px → 8px（面板已无投影 + 无页头分隔线，
   再叠 16px 内衬会让内容框显小、行密度虚低）。 */
.permission-shell { display: flex; flex-direction: column; flex: 1; min-height: 0; padding: var(--space-2); }
</style>
