<template>
  <div class="page-container data-dashboard">
<div class="page-body">
    <div class="page-header">
      <h1 class="page-title">{{ t('pages.settings.DataDashboard.s1') }}</h1>
      <p class="page-subtitle">{{ t('pages.settings.DataDashboard.s2') }}</p>
    </div>

    <!-- KPI 卡片 -->
    <n-grid class="stats-row" :cols="6" :x-gap="12" :y-gap="12" responsive="screen">
      <n-grid-item v-for="card in kpiCards" :key="card.key">
        <div class="kpi-card kpi-card--accent">
          <div class="kpi-value">{{ card.value }}</div>
          <div class="kpi-label">{{ card.label }}</div>
        </div>
      </n-grid-item>
    </n-grid>

    <!-- 数据导出 -->
    <n-card>
      <template #header>{{ t('pages.settings.DataDashboard.s19') }}</template>
      <n-space class="filter-row" :wrap="true">
        <n-select
          v-model:value="exportResourceVal"
          :options="RESOURCE_OPTIONS"
          :placeholder="t('pages.settings.DataDashboard.s3')"
          clearable
          style="width: 220px"
        />
        <n-select
          v-model:value="exportFormatVal"
          :options="FORMAT_OPTIONS"
          :placeholder="t('pages.settings.DataDashboard.s4')"
          style="width: 120px"
        />
        <n-button type="primary" :loading="exporting" :disabled="!exportResourceVal" @click="handleExport">
          {{ t('pages.settings.DataDashboard.s5') }}
        </n-button>
      </n-space>
    </n-card>

    <!-- 订阅管理 -->
    <n-card>
      <template #header-extra>
        <n-button type="primary" @click="showAddSub = true">{{ t('pages.settings.DataDashboard.s6') }}</n-button>
      </template>
      <template #header>{{ t('pages.settings.DataDashboard.s20') }}</template>

      <n-data-table
        :columns="subColumns"
        :data="subs"
        :loading="subLoading"
        :row-key="(row: any) => row.id"
        size="small"
        striped
        :pagination="{ pageSize: 10 }"
      />
    </n-card>

    <!-- 新建订阅弹窗 -->
</div><!-- /.page-body -->
<n-modal v-model:show="showAddSub" preset="card" :title="t('pages.settings.DataDashboard.s7')" style="width: 540px; max-width: 90vw">
      <n-form :model="subForm" label-placement="left" label-width="100">
        <n-form-item :label="t('pages.settings.DataDashboard.s8')">
          <n-select v-model:value="subForm.resource" :options="RESOURCE_OPTIONS" :placeholder="t('pages.settings.DataDashboard.s9')" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.DataDashboard.s10')">
          <n-select v-model:value="subForm.metric" :options="METRIC_OPTIONS" :placeholder="t('pages.settings.DataDashboard.s11')" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.DataDashboard.s12')">
          <n-select v-model:value="subForm.channel" :options="CHANNEL_OPTIONS" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.DataDashboard.s13')">
          <n-select v-model:value="subForm.schedule" :options="SCHEDULE_OPTIONS" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.DataDashboard.s14')">
          <n-input v-model:value="subForm.scheduleTime" placeholder="09:00 (HH:mm)" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.DataDashboard.s15')">
          <n-input v-model:value="subForm.recipients" :placeholder="t('pages.settings.DataDashboard.s16')" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showAddSub = false">{{ t('pages.settings.DataDashboard.s17') }}</n-button>
          <n-button type="primary" class="gradient-btn" :loading="creating" @click="handleCreateSub">{{ t('pages.settings.DataDashboard.s18') }}</n-button>
        </n-space>
      </template>
    </n-modal>
</div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, h, onMounted, reactive } from 'vue';
import { NButton, NTag, NSpace, useMessage } from 'naive-ui';
import {
  getKpi,
  exportResource as exportResourceApi,
  listSubscriptions,
  createSubscription,
  deleteSubscription,
  RESOURCE_OPTIONS,
  CHANNEL_OPTIONS,
  SCHEDULE_OPTIONS,
  type DashboardKpi,
  type DataSubscription,
} from '@/api/data';
const { t } = useI18n()

const message = useMessage();

const kpi = ref<DashboardKpi | null>(null);
const kpiCards = ref<{ key: string; label: string; value: number }[]>([]);

const exportResourceVal = ref<string | null>(null);
const exportFormatVal = ref<'csv' | 'json'>('csv');
const exporting = ref(false);

const subs = ref<DataSubscription[]>([]);
const subLoading = ref(false);
const showAddSub = ref(false);
const creating = ref(false);
const subForm = reactive<Partial<DataSubscription>>({
  resource: 'Candidate',
  metric: 'all',
  channel: 'SYSTEM',
  schedule: 'DAILY',
  scheduleTime: '09:00',
  recipients: '',
});

const FORMAT_OPTIONS = [
  { label: 'CSV', value: 'csv' },
  { label: 'JSON', value: 'json' },
];

const METRIC_OPTIONS = [
  { label: '全部数据 all', value: 'all' },
  { label: '按状态统计 count_by_status', value: 'count_by_status' },
  { label: '按部门统计 count_by_dept', value: 'count_by_dept' },
  { label: '导出 CSV export_csv', value: 'export_csv' },
];

async function loadKpi() {
  try {
    const data = await getKpi();
    kpi.value = data;
    kpiCards.value = [
      { key: 'totalCandidates',   label: '候选人总数',   value: data.totalCandidates },
      { key: 'activeDemands',     label: '在招需求',     value: data.activeDemands },
      { key: 'openPositions',     label: '开放职位',     value: data.openPositions },
      { key: 'ongoingInterviews', label: '进行中面试',   value: data.ongoingInterviews },
      { key: 'sentOffers',        label: '已发 Offer',   value: data.sentOffers },
      { key: 'pendingOnboardings',label: '待入职',       value: data.pendingOnboardings },
    ];
  } catch (e: any) {
    message.error('加载 KPI 失败: ' + (e?.message || 'unknown'));
  }
}

async function loadSubs() {
  subLoading.value = true;
  try {
    subs.value = await listSubscriptions();
  } catch (e: any) {
    message.error('加载订阅失败: ' + (e?.message || 'unknown'));
  } finally {
    subLoading.value = false;
  }
}

async function handleExport() {
  if (!exportResourceVal.value) return;
  exporting.value = true;
  try {
    const blob = await exportResourceApi(exportResourceVal.value, exportFormatVal.value);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${exportResourceVal.value}-${Date.now()}.${exportFormatVal.value}`;
    a.click();
    URL.revokeObjectURL(url);
    message.success('导出已开始');
  } catch (e: any) {
    message.error('导出失败: ' + (e?.message || 'unknown'));
  } finally {
    exporting.value = false;
  }
}

async function handleCreateSub() {
  if (!subForm.resource) {
    message.warning('请选择资源');
    return;
  }
  creating.value = true;
  try {
    await createSubscription(subForm);
    message.success('订阅已创建');
    showAddSub.value = false;
    await loadSubs();
  } catch (e: any) {
    message.error('创建失败: ' + (e?.message || 'unknown'));
  } finally {
    creating.value = false;
  }
}

async function handleDeleteSub(row: DataSubscription) {
  try {
    await deleteSubscription(row.id);
    message.success('订阅已停用');
    await loadSubs();
  } catch (e: any) {
    message.error('停用失败: ' + (e?.message || 'unknown'));
  }
}

const subColumns = [
  { title: '资源', key: 'resource', width: 120 },
  { title: '指标', key: 'metric', width: 180 },
  {
    title: '渠道',
    key: 'channel',
    width: 100,
    render: (row: DataSubscription) => h(NTag, { size: 'small', type: 'info' }, () => row.channel),
  },
  { title: '周期', key: 'schedule', width: 100 },
  { title: '时间', key: 'scheduleTime', width: 80 },
  { title: '收件人', key: 'recipients', ellipsis: { tooltip: true } },
  { title: '运行次数', key: 'runCount', width: 90 },
  {
    title: '操作',
    key: 'action',
    width: 90,
    render: (row: DataSubscription) =>
      h(NButton, { size: 'small', type: 'error', onClick: () => handleDeleteSub(row) }, () => '停用'),
  },
];

onMounted(() => {
  loadKpi();
  loadSubs();
});
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


.data-dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: 100%;
}
/* KPI 卡改用全局 .kpi-card.kpi-card--accent（glass.css）：渐变 + 居中均走 CSS 变量，无硬编码 hex */
</style>
