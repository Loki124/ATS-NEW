<template>
  <div class="page-container field-acl">
<div class="page-body">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.FieldAclSettings.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.FieldAclSettings.s2') }}</p>
      </div>
    </div>

    <div class="kpi-row">
      <div class="kpi-card"><span class="kpi-label">{{ t('pages.settings.FieldAclSettings.s3') }}</span><span class="kpi-value">{{ rules.length }}</span></div>
    </div>

    <n-card :title="t('pages.settings.FieldAclSettings.s5')" class="mt-4">
      <template #header-extra>
        <n-button size="small" :loading="loading" @click="reload">{{ t('pages.settings.FieldAclSettings.s4') }}</n-button>
      </template>
      <n-empty v-if="!rows.length" :description="t('pages.settings.FieldAclSettings.s6')" />
      <n-data-table
        v-else
        :columns="columns"
        :data="rows"
        :pagination="false"
        :bordered="true"
        size="small"
        :max-height="500"
      />
    </n-card>

    <n-card :title="t('pages.settings.FieldAclSettings.s7')" class="mt-4">
      <n-data-table
        :columns="auditColumns"
        :data="auditLogs"
        :pagination="{ pageSize: 20 }"
        size="small"
        :max-height="400"
      />
    </n-card>
    </div><!-- /.page-body -->
</div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed, onMounted, h } from 'vue';
import { NButton, NTag, NPageHeader, useMessage } from 'naive-ui';
import {
  fetchAclMatrix, listAclRules, queryAclAudit,
  type FieldAclMatrix, type FieldAclAction, type FieldAclRule, type FieldAclAudit,
} from '@/api/field-acl';
const { t } = useI18n()

const message = useMessage();
const matrix = ref<FieldAclMatrix>({});
const rules = ref<FieldAclRule[]>([]);
const auditLogs = ref<FieldAclAudit[]>([]);
const loading = ref(false);

const ROLE_LABELS: Record<string, string> = {
  INTERVIEWER: t('pages.settings.FieldAclSettings.s15'),
  HRBP: 'HRBP',
  HR: 'HR',
  MANAGER: t('pages.settings.FieldAclSettings.s16'),
  ADMIN: t('pages.settings.FieldAclSettings.s17'),
  '*': t('pages.settings.FieldAclSettings.s18'),
};

const ACTION_COLORS: Record<FieldAclAction, 'success' | 'warning' | 'error' | 'default'> = {
  VIEW: 'success',
  MASK: 'warning',
  HIDE: 'error',
};

const ACTION_LABELS: Record<FieldAclAction, string> = {
  VIEW: t('pages.settings.FieldAclSettings.s19'),
  MASK: t('pages.settings.FieldAclSettings.s20'),
  HIDE: t('pages.settings.FieldAclSettings.s21'),
};

const roleCodes = computed(() => {
  const set = new Set<string>();
  for (const r of rules.value) {
    set.add(r.roleCode || '*');
  }
  return Array.from(set);
});

const columns = computed(() => {
  const cols: any[] = [
    { title: t('pages.settings.FieldAclSettings.s8'), key: 'resource', width: 100, fixed: 'left' as const },
    { title: t('pages.settings.FieldAclSettings.s9'), key: 'field', width: 140, fixed: 'left' as const },
  ];
  for (const rc of roleCodes.value) {
    cols.push({
      title: ROLE_LABELS[rc] || rc,
      key: rc,
      width: 100,
      render(row: any) {
        const action = row[rc] as FieldAclAction | undefined;
        if (!action) return h(NTag, { type: 'default', size: 'small' }, () => '-');
        return h(NTag, { type: ACTION_COLORS[action], size: 'small' }, () => ACTION_LABELS[action]);
      },
    });
  }
  return cols;
});

const rows = computed(() => {
  const out: any[] = [];
  for (const [resource, fields] of Object.entries(matrix.value)) {
    for (const [field, roles] of Object.entries(fields)) {
      out.push({ resource, field, ...roles });
    }
  }
  return out;
});

const auditColumns = [
  { title: t('pages.settings.FieldAclSettings.s10'), key: 'createdAt', width: 170,
    render: (r: FieldAclAudit) => r.createdAt ? new Date(r.createdAt).toLocaleString('zh-CN') : '-' },
  { title: t('pages.settings.FieldAclSettings.s11'), key: 'userName', width: 100 },
  { title: t('pages.settings.FieldAclSettings.s12'), key: 'resource', width: 200,
    render: (r: FieldAclAudit) => `${r.resource}.${r.field}` },
  { title: t('pages.settings.FieldAclSettings.s13'), key: 'action', width: 80,
    render: (r: FieldAclAudit) => h(NTag, { type: ACTION_COLORS[r.action] || 'default', size: 'small' }, () => ACTION_LABELS[r.action] || r.action) },
  { title: t('pages.settings.FieldAclSettings.s14'), key: 'result', width: 80 },
];

async function reload() {
  loading.value = true;
  try {
    const [m, rs, logs] = await Promise.all([
      fetchAclMatrix(),
      listAclRules(),
      queryAclAudit({ limit: 50 }),
    ]);
    matrix.value = m;
    rules.value = rs;
    auditLogs.value = logs;
  } catch (err: any) {
    message.error(t('pages.settings.FieldAclSettings.s22') + (err?.message || err));
  } finally {
    loading.value = false;
  }
}

onMounted(reload);
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
  gap: var(--space-4);
}


.field-acl {
  width: 100%;
}
.mt-4 {
  margin-top: var(--space-4);
}
</style>
