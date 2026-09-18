<template>
  <div class="page-container permission-management">
    <div class="page-body">
      <div class="page-header">
        <div class="page-header-row">
          <div>
            <h1 class="page-title">身份管理</h1>
            <p class="page-subtitle">角色定义、权限分配与权限模板（资源注册已独立为「资源管理」菜单）</p>
          </div>
          <div class="page-header-actions">
            <n-button @click="templatesModal.show = true">
              <template #icon><n-icon :component="GridOutline" /></template>
              模板管理
            </n-button>
          </div>
        </div>
      </div>

      <n-card :bordered="false" class="glass-panel permission-shell">
        <RolesTab />
      </n-card>
    </div>

    <!-- 模板管理弹窗（原独立 tab 收编为弹窗，入口在标题行右侧） -->
    <n-modal
      v-model:show="templatesModal.show"
      preset="card"
      title="权限模板"
      class="templates-modal"
      :style="{ width: '1100px', 'max-width': '92vw' }"
    >
      <TemplatesTab v-if="templatesModal.show" />
    </n-modal>
  </div>
</template>

<script setup lang="ts">
/**
 * PermissionManagement.vue — 身份管理主页面 (2026-09-18 重构)
 *
 * 原为 4-tab 主壳 (资源/模板/角色/用户授权)，本次拆解:
 *   - 资源管理 (ResourcesTab) → 独立菜单页 PermissionResources.vue (/settings/permissions/resources)
 *   - 模板管理 (TemplatesTab) → 收编为本页标题行「模板管理」按钮打开的弹窗
 *   - 角色管理 (RolesTab)     → 本页主体，菜单更名「身份管理」，去 tab 化
 *   - 用户授权 (UserRolesTab) → 移除：与「用户管理」页的分配角色弹窗重复
 *     (两者均写 user_roles 表: 本页走 /api/v1/user-roles/，用户管理走
 *      /api/v1/permissions/users/{id}/roles/，授权入口统一收敛到用户管理页)
 */
import { reactive } from 'vue'
import { NButton, NCard, NIcon, NModal } from 'naive-ui'
import { GridOutline } from '@vicons/ionicons5'
import RolesTab from './permission/RolesTab.vue'
import TemplatesTab from './permission/TemplatesTab.vue'

const templatesModal = reactive({ show: false })
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

/* 标题行：左标题 + 右操作（模板管理入口右对齐） */
.page-header-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
}
.page-header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  padding-bottom: 2px;
}

.permission-management {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
/* 玻璃面板作为内容根时撑满高度（规范：仿 CampusControl 范式 .glass-panel flex 撑满） */
.permission-shell { display: flex; flex-direction: column; flex: 1; min-height: 0; padding: var(--space-4); }
/* 修复表格 body 高度塌陷：n-card 内容包裹层默认 display:block，导致内层 flex:1 不生效；
   对齐 §2.2 的 .tab-card :deep(.n-card-content) 链 */
.permission-shell :deep(.n-card-content) { flex: 1; min-height: 0; display: flex; flex-direction: column; }
</style>
