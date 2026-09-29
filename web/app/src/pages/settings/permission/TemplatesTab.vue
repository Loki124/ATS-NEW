<template>
  <div class="templates-tab">
    <div class="filter-row">
      <n-button type="primary" @click="load">{{ t('pages.settings.permission.TemplatesTab.s1') }}</n-button>
      <n-text depth="3">{{ t('pages.settings.permission.TemplatesTab.s2') }}{{ data.length }}{{ t('pages.settings.permission.TemplatesTab.s3') }}</n-text>
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
import { useI18n } from 'vue-i18n'
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
const { t } = useI18n()

const message = useMessage()
const loading = ref(false)
const data = ref<PermissionTemplate[]>([])

const columns = [
  { title: t('pages.settings.permission.TemplatesTab.s4'), key: 'templateCode', width: 200 },
  { title: t('pages.settings.permission.TemplatesTab.s5'), key: 'templateName', width: 160 },
  { title: t('pages.settings.permission.TemplatesTab.s6'), key: 'description', width: 280 },
  {
    title: t('pages.settings.permission.TemplatesTab.s7'),
    key: 'permissionCodes',
    width: 120,
    render: (row: PermissionTemplate) => row.permissionCodes?.length ?? 0,
  },
  {
    title: t('pages.settings.permission.TemplatesTab.s8'),
    key: 'isSystem',
    width: 100,
    render: (row: PermissionTemplate) => row.isSystem === 1 ? t('pages.settings.permission.TemplatesTab.s9') : t('pages.settings.permission.TemplatesTab.s10'),
  },
  {
    title: t('pages.settings.permission.TemplatesTab.s11'),
    key: 'actions',
    width: 160,
    render(row: PermissionTemplate) {
      return h(NSpace, {}, () => [
        h(NButton, {
          size: 'small',
          text: true,
          type: 'primary',
          onClick: () => viewCodes(row),
        }, () => t('pages.settings.permission.TemplatesTab.s12')),
      ])
    },
  },
]

async function load() {
  loading.value = true
  try {
    data.value = await listTemplates()
  } catch (e: any) {
    message.error(t('pages.settings.permission.TemplatesTab.s13') + (e?.message ?? e))
  } finally {
    loading.value = false
  }
}

function viewCodes(row: PermissionTemplate) {
  const codes = row.permissionCodes?.join('\n') ?? '(空)'
  message.info(`${t('pages.settings.permission.TemplatesTab.s14', { code: row.templateCode, count: row.permissionCodes?.length ?? 0 })}\n${codes}`, {
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