<template>
  <div class="data-dashboard">
    <div class="page-header">
      <h1 class="page-title">数据中心</h1>
      <p class="page-subtitle">G35 - 招聘业务 KPI 看板 + 通用数据导出 + 数据订阅</p>
    </div>

    <!-- KPI 卡片 -->
    <n-grid class="stats-row" :cols="6" :x-gap="12" :y-gap="12" responsive="screen">
      <n-grid-item v-for="kpi in kpiCards" :key="kpi.key">
        <n-card class="kpi-card" :bordered="false" embedded>
          <div class="kpi-value">{{ kpi.value }}</div>
          <div class="kpi-label">{{ kpi.label }}</div>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- 数据导出 -->
    <n-card>
      <template #header>通用数据导出</template>
      <n-space class="filter-row" :wrap="true">
        <n-select
          v-model:value="exportResourceVal"
          :options="RESOURCE_OPTIONS"
          placeholder="选择资源"
          clearable
          style="width: 220px"
        />
        <n-select
          v-model:value="exportFormatVal"
          :options="FORMAT_OPTIONS"
          placeholder="格式"
          style="width: 120px"
        />
        <n-button type="primary" :loading="exporting" :disabled="!exportResourceVal" @click="handleExport">
          下载
        </n-button>
      </n-space>
    </n-card>

    <!-- 订阅管理 -->
    <n-card>
      <template #header-extra>
        <n-button type="primary" @click="showAddSub = true">新建订阅</n-button>
      </template>
      <template #header>数据订阅</template>

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
    <n-modal v-model:show="showAddSub" preset="card" title="新建数据订阅" style="width: 540px">
      <n-form :model="subForm" label-placement="left" label-width="100">
        <n-form-item label="资源">
          <n-select v-model:value="subForm.resource" :options="RESOURCE_OPTIONS" placeholder="选择资源" />
        </n-form-item>
        <n-form-item label="指标">
          <n-select v-model:value="subForm.metric" :options="METRIC_OPTIONS" placeholder="选择指标" />
        </n-form-item>
        <n-form-item label="渠道">
          <n-select v-model:value="subForm.channel" :options="CHANNEL_OPTIONS" />
        </n-form-item>
        <n-form-item label="周期">
          <n-select v-model:value="subForm.schedule" :options="SCHEDULE_OPTIONS" />
        </n-form-item>
        <n-form-item label="时间">
          <n-input v-model:value="subForm.scheduleTime" placeholder="09:00 (HH:mm)" />
        </n-form-item>
        <n-form-item label="收件人">
          <n-input v-model:value="subForm.recipients" placeholder="逗号分隔 email / userId" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showAddSub = false">取消</n-button>
          <n-button type="primary" :loading="creating" @click="handleCreateSub">创建</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
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
      h(NButton, { size: 'small', type: 'error', ghost: true, onClick: () => handleDeleteSub(row) }, () => '停用'),
  },
];

onMounted(() => {
  loadKpi();
  loadSubs();
});
</script>

<style scoped>
.data-dashboard {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}
.page-header {
  flex-shrink: 0;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}
.page-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}
.kpi-card {
  text-align: center;
  background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%);
}
.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: #4f46e5;
  line-height: 1.2;
}
.kpi-label {
  font-size: 13px;
  color: #6b7280;
  margin-top: 4px;
}
</style>
