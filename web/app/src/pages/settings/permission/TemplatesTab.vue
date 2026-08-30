<template>
  <div class="templates-tab">
    <div class="filter-row">
      <n-button type="primary" @click="load">刷新</n-button>
      <n-text depth="3">共 {{ data.length }} 个模板 (系统预置不可编辑)</n-text>
    </div>

    <n-data-table
      :columns="columns"
      :data="data"
      :loading="loading"
      :bordered="false"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * TemplatesTab.vue — 权限模板 tab (T20)
 *
 * 后端 PermissionTemplate 是只读 ReadOnlyModelViewSet — 仅 list.
 * 模板由 seed_v2_init 命令注入 (T15, 4 个预置模板).
 *
 * 用途: 角色管理 tab 的 "从模板克隆" 弹窗需要从这拉 template_code 列表
 *   — 这里加载一次缓存, 后续 clone 时直接用本组件的 data.
 */
import { h, onMounted, ref } from 'vue'
import { NButton, NSpace, NDataTable, NText, useMessage } from 'naive-ui'
import { listTemplates, type PermissionTemplate } from '@/api/permission-template'

const message = useMessage()
const loading = ref(false)
const data = ref<PermissionTemplate[]>([])

const columns = [
  { title: '模板编码', key: 'templateCode', width: 200 },
  { title: '模板名称', key: 'templateName', width: 160 },
  { title: '描述', key: 'description', width: 280 },
  {
    title: '权限码数量',
    key: 'permissionCodes',
    width: 120,
    render: (row: PermissionTemplate) => row.permissionCodes?.length ?? 0,
  },
  {
    title: '系统预置',
    key: 'isSystem',
    width: 100,
    render: (row: PermissionTemplate) => row.isSystem === 1 ? '是' : '否',
  },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render(row: PermissionTemplate) {
      return h(NSpace, {}, () => [
        h(NButton, {
          size: 'small',
          text: true,
          type: 'primary',
          onClick: () => viewCodes(row),
        }, () => '查看权限码'),
      ])
    },
  },
]

async function load() {
  loading.value = true
  try {
    data.value = await listTemplates()
  } catch (e: any) {
    message.error('加载模板失败: ' + (e?.message ?? e))
  } finally {
    loading.value = false
  }
}

function viewCodes(row: PermissionTemplate) {
  const codes = row.permissionCodes?.join('\n') ?? '(空)'
  message.info(`模板 ${row.templateCode} 权限码 (${row.permissionCodes?.length ?? 0}):\n${codes}`, {
    duration: 8000,
  })
}

onMounted(load)
</script>

<style scoped>
.templates-tab {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.filter-row {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}
</style>