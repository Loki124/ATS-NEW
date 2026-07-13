<template>
  <div class="permission-management">
    <n-card title="权限管理" class="mb-4">
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
.permission-management {
  width: 100%;
  height: 100%;
}
</style>