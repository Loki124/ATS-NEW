<script setup lang="ts">
/**
 * 权限管理 - PermissionManagement
 * PRD G43 字段级 ACL 配套 (Phase 1: 角色 + 权限 V1)
 *
 * 后端: /api/permissions (17 个端点)
 *   GET  /menus         菜单权限树
 *   GET  /functions     功能权限
 *   GET  /data-scope    数据范围
 *   GET  /roles         角色列表
 *   GET  /roles/:id     角色详情
 *   POST /roles         创建角色
 *   PUT  /roles/:id     更新角色
 *   DELETE /roles/:id   删除角色
 */
import { ref, h, onMounted, computed } from 'vue'
import { NTag, NSpace, NButton, NIcon, NDataTable, NCard, NInput, useMessage, useDialog } from 'naive-ui'
import { ShieldCheckmarkOutline, AddOutline, RefreshOutline, TrashOutline } from '@vicons/ionicons5'
import api from '../../api/auth'

const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const roles = ref<any[]>([])
const menus = ref<any[]>([])
const functions = ref<any[]>([])
const filter = ref('')

const columns = computed(() => [
  { title: 'ID', key: 'id', width: 80, ellipsis: { tooltip: true } },
  { title: '角色名', key: 'name', width: 180 },
  { title: '角色编码', key: 'code', width: 160 },
  {
    title: '类型', key: 'roleType', width: 120,
    render: (row: any) => h(NTag, { type: row.roleType === 'SYSTEM' ? 'warning' : 'info', size: 'small' }, { default: () => row.roleType || 'CUSTOM' }),
  },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  { title: '创建时间', key: 'createdAt', width: 160, render: (row: any) => row.createdAt?.slice(0, 16) || '—' },
  {
    title: '操作', key: 'actions', width: 200, fixed: 'right' as const,
    render: (row: any) => h(NSpace, { size: 4 }, {
      default: () => [
        row.roleType !== 'SYSTEM' && h(NButton, {
          size: 'tiny',
          type: 'error',
          quaternary: true,
          onClick: () => handleDelete(row),
        }, { default: () => '删除' }),
      ].filter(Boolean),
    }),
  },
])

async function loadRoles() {
  loading.value = true
  try {
    const { data } = await api.get('/permissions/roles')
    if (data.success) roles.value = data.data
  } catch (e: any) {
    message.error(`加载角色失败: ${e.message}`)
  } finally {
    loading.value = false
  }
}

async function loadMenus() {
  try {
    const { data } = await api.get('/permissions/menus')
    if (data.success) menus.value = data.data
  } catch (e: any) {
    // 静默失败（菜单可能没权限）
  }
}

async function loadFunctions() {
  try {
    const { data } = await api.get('/permissions/functions')
    if (data.success) functions.value = data.data
  } catch (e: any) {
    // 静默
  }
}

function handleAdd() {
  message.info('角色创建功能：请联系 SUPER_ADMIN 或在下个迭代实现')
}

function handleDelete(row: any) {
  dialog.warning({
    title: '确认删除',
    content: `确定删除角色「${row.name}」?此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.delete(`/permissions/roles/${row.id}`)
        message.success('已删除')
        loadRoles()
      } catch (e: any) {
        message.error(`删除失败: ${e.response?.data?.message || e.message}`)
      }
    },
  })
}

const filteredRoles = computed(() => {
  if (!filter.value) return roles.value
  return roles.value.filter((r) => r.name?.includes(filter.value) || r.code?.includes(filter.value))
})

const stats = computed(() => ({
  total: roles.value.length,
  system: roles.value.filter((r) => r.roleType === 'SYSTEM').length,
  custom: roles.value.filter((r) => r.roleType !== 'SYSTEM').length,
  menus: Array.isArray(menus.value) ? menus.value.length : 0,
  functions: functions.value.length,
}))

onMounted(() => {
  loadRoles()
  loadMenus()
  loadFunctions()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">权限管理</h1>
      <n-space>
        <n-button @click="loadRoles" :loading="loading">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
        <n-button type="primary" @click="handleAdd">
          <template #icon><n-icon :component="AddOutline" /></template>
          新建角色
        </n-button>
      </n-space>
    </div>

    <!-- 统计 -->
    <n-grid x-gap="12" y-gap="12" cols="5" responsive="screen" :item-responsive="true" class="stats-row">
      <n-gi><n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">总角色数</div>
        <div class="stat-value">{{ stats.total }}</div>
      </n-card></n-gi>
      <n-gi><n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">系统角色</div>
        <div class="stat-value" style="color: #fa8c16;">{{ stats.system }}</div>
      </n-card></n-gi>
      <n-gi><n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">自定义角色</div>
        <div class="stat-value" style="color: #1890ff;">{{ stats.custom }}</div>
      </n-card></n-gi>
      <n-gi><n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">菜单权限</div>
        <div class="stat-value">{{ stats.menus }}</div>
      </n-card></n-gi>
      <n-gi><n-card size="small" :bordered="false" class="stat-card">
        <div class="stat-label">功能权限</div>
        <div class="stat-value">{{ stats.functions }}</div>
      </n-card></n-gi>
    </n-grid>

    <n-card :bordered="false" class="rounded-xl">
      <n-space class="filter-row">
        <n-input
          v-model:value="filter"
          placeholder="搜索角色名或编码"
          style="width: 240px"
          clearable
        >
          <template #prefix><n-icon :component="ShieldCheckmarkOutline" /></template>
        </n-input>
        <n-button @click="loadRoles">查询</n-button>
      </n-space>

      <n-data-table
        :columns="columns"
        :data="filteredRoles"
        :loading="loading"
        :row-key="(row: any) => row.id"
        :pagination="{ pageSize: 20 }"
      />
    </n-card>
  </div>
</template>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
.stats-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-label { font-size: 12px; color: #8c8c8c; }
.stat-value { font-size: 22px; font-weight: 600; margin-top: 4px; }
.filter-row { margin-bottom: 12px; }
</style>
