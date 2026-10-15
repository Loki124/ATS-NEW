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
      :row-key="(r: PermissionTemplate) => r.id"
    />

    <!-- 权限码明细抽屉：按功能模块分组展示中文名（英文 code 作副文本/悬浮） -->
    <n-drawer v-model:show="codesDrawer.show" :width="460" placement="right">
      <n-drawer-content
        :title="`权限码明细 · ${codesDrawer.row?.templateName ?? ''}`"
        :native-scrollbar="false"
      >
        <template v-if="codesDrawer.groups.length">
          <div v-for="g in codesDrawer.groups" :key="g.module" class="code-group">
            <div class="code-group-title">{{ g.moduleLabel }}</div>
            <div v-for="it in g.items" :key="it.code" class="code-item">
              <span class="code-name">{{ it.name }}</span>
              <span class="code-raw" :title="it.code">{{ it.code }}</span>
            </div>
          </div>
        </template>
        <n-empty v-else description="该模板暂无权限码" />
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { NButton, NSpace, NDataTable, NText, NTag, NDrawer, NDrawerContent, NEmpty, useMessage } from 'naive-ui'
import { listTemplates, type PermissionTemplate } from '@/api/permission-template'
import { useResourceNames, groupPermissionCodesByModule, type GroupedCode } from '@/composables/useResourceNames'
const { t } = useI18n()
const message = useMessage()
const { ensureLoaded } = useResourceNames()

const loading = ref(false)
const data = ref<PermissionTemplate[]>([])

const codesDrawer = reactive<{ show: boolean; row: PermissionTemplate | null; groups: GroupedCode[] }>({
  show: false,
  row: null,
  groups: [],
})

const columns = [
  { title: t('pages.settings.permission.TemplatesTab.s4'), key: 'templateCode', width: 200,
    render: (row: PermissionTemplate) => h('span', { class: 'cell-code' }, row.templateCode) },
  { title: t('pages.settings.permission.TemplatesTab.s5'), key: 'templateName', width: 160 },
  { title: t('pages.settings.permission.TemplatesTab.s6'), key: 'description', width: 280,
    ellipsis: { tooltip: true } },
  {
    title: t('pages.settings.permission.TemplatesTab.s7'),
    key: 'permissionCodes',
    width: 120,
    render: (row: PermissionTemplate) =>
      h(NTag, { size: 'small', type: 'info', bordered: false },
        { default: () => `${row.permissionCodes?.length ?? 0} 项` }),
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
    const [tpls] = await Promise.all([listTemplates(), ensureLoaded()])
    data.value = tpls
  } catch (e: any) {
    message.error(t('pages.settings.permission.TemplatesTab.s13') + (e?.message ?? e))
  } finally {
    loading.value = false
  }
}

function viewCodes(row: PermissionTemplate) {
  codesDrawer.row = row
  codesDrawer.groups = groupPermissionCodesByModule(row.permissionCodes ?? [])
  codesDrawer.show = true
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
/* 资源码（英文）弱化展示，避免抢视觉（中文名才是主体） */
.cell-code { color: var(--ink-soft); font-family: var(--font-mono, monospace); }

/* ===== 权限码明细抽屉：按模块分组 ===== */
.code-group { margin-bottom: var(--space-3); }
.code-group-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--ink, #1e293b);
  padding: 4px 8px;
  border-left: 3px solid var(--brand, #4f46e5);
  background: var(--surface-2, #f1f5f9);
  border-radius: 4px;
  margin-bottom: 6px;
}
.code-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
  padding: 4px 8px;
}
.code-name { color: var(--ink, #1e293b); }
.code-raw {
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  color: var(--ink-soft, #94a3b8);
  max-width: 52%;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
