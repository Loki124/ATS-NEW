<template>
  <div class="page-container permission-management">

    <div class="page-body">
    <div class="page-header">
      <div>
        <h1 class="page-title">权限管理</h1>
        <p class="page-subtitle">资源注册、权限模板、角色克隆、用户授权（V2 4-tab 主壳）</p>
      </div>
    </div>
    <n-card :bordered="false" class="glass-panel permission-shell">
      <n-tabs v-model:value="activeTab" type="line" animated>
        <n-tab-pane name="resources" tab="资源管理">
          <ResourcesTab />
        </n-tab-pane>
        <n-tab-pane name="templates" tab="模板管理">
          <TemplatesTab />
        </n-tab-pane>
        <n-tab-pane name="roles" tab="角色管理">
          <RolesTab />
        </n-tab-pane>
        <n-tab-pane name="user-roles" tab="用户授权">
          <UserRolesTab />
        </n-tab-pane>
      </n-tabs>
    </n-card>
    </div><!-- /.page-body -->

  </div>
</template>

<script setup lang="ts">
/**
 * PermissionManagement.vue — V2 权限管理 4-tab 主壳 (T20)
 *
 * 4 个子 tab:
 *   - 资源管理 (ResourcesTab)  → PermissionResource (注册菜单/按钮/字段/API)
 *   - 模板管理 (TemplatesTab)  → PermissionTemplate (角色权限集合快照)
 *   - 角色管理 (RolesTab)      → RoleV2 (从模板克隆 + per-resource 勾选)
 *   - 用户授权 (UserRolesTab)  → UserRoleV2 (分配角色 + 数据范围)
 *
 * 设计:
 *   - 单页单 tab, 子组件懒加载 (避免一次性拉所有资源/模板/角色)
 *   - 路由: /settings/permissions (router/index.ts 单独挂, 与 MouManagement 并列)
 *   - 子组件不放业务逻辑, 仅展示 + 调用对应的 V2 API wrapper
 *
 * T20 状态: 4 个子组件各实现最小 NDataTable + 新建按钮 (CRUD 后续 task 完善)
 */
import { ref } from 'vue'
import { NCard, NTabs, NTabPane } from 'naive-ui'
import ResourcesTab from './permission/ResourcesTab.vue'
import TemplatesTab from './permission/TemplatesTab.vue'
import RolesTab from './permission/RolesTab.vue'
import UserRolesTab from './permission/UserRolesTab.vue'

const activeTab = ref('resources')
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
  gap: 16px;
}


/* === 2026-08-24 page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
   - 标题区固定（flex-shrink: 0）→ 配置/操作按钮始终可触达
   - 内容区自己滚（flex: 1; min-height: 0; overflow-y: auto）→ 与外层 .settings-scroll 滚职责分离
   - 结构上让 sticky header 天然占据物理空间 → 解决下方内容穿透 header 的视觉 bug === */
/* === 2026-08-24 page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
   - 标题区固定（flex-shrink: 0）→ 配置/操作按钮始终可触达
   - 内容区自己滚（flex: 1; min-height: 0; overflow-y: auto）→ 与外层 .settings-scroll 滚职责分离
   - 结构上让 sticky header 天然占据物理空间 → 解决下方内容穿透 header 的视觉 bug === */
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
  gap: 16px;
}


.permission-management {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
/* 玻璃面板作为内容根时撑满高度（规范：仿 CampusControl 范式 .glass-panel flex 撑满） */
.permission-shell { display: flex; flex-direction: column; flex: 1; min-height: 0; padding: var(--space-4); }
</style>