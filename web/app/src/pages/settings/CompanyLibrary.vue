<template>
  <div class="company-library">
    <div class="page-header">
      <h1 class="page-title">公司库</h1>
      <p class="page-subtitle">G41 - 公司信息库 (央企/民企/外企)</p>
    </div>

    <n-card>
      <template #header-extra>
        <n-button @click="reload" :loading="loading">刷新</n-button>
      </template>

      <n-space class="filter-row" :wrap="true">
        <n-input
          v-model:value="filters.keyword"
          placeholder="搜索公司名 / 代码"
          clearable
          style="width: 240px"
          @keyup.enter="reload"
        />
        <n-select
          v-model:value="filters.industry"
          :options="industryOptions"
          placeholder="行业"
          clearable
          style="width: 160px"
          @update:value="reload"
        />
        <n-select
          v-model:value="filters.scale"
          :options="SCALE_OPTIONS"
          placeholder="规模"
          clearable
          style="width: 140px"
          @update:value="reload"
        />
        <n-button type="primary" @click="reload">搜索</n-button>
      </n-space>

      <n-data-table
        :columns="columns"
        :data="rows"
        :loading="loading"
        :pagination="{ pageSize: 15 }"
        :row-key="(row: any) => row.id"
        size="small"
        striped
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted, reactive } from 'vue';
import { NTag, NButton, NSpace, useMessage } from 'naive-ui';
import { BusinessOutline, OpenOutline, StarOutline, Star } from '@vicons/ionicons5';
import { searchCompanies, getCompany, listCompanyIndustries, type Company } from '@/api/library';

const message = useMessage();

const SCALE_OPTIONS = [
  { label: '100000+', value: '100000+' },
  { label: '10000+', value: '10000+' },
  { label: '5000+', value: '5000+' },
  { label: '1000+', value: '1000+' },
  { label: '500+', value: '500+' },
];

const filters = reactive({ keyword: '', industry: null as string | null, scale: null as string | null });
const industryOptions = ref<{ label: string; value: string }[]>([]);
const rows = ref<Company[]>([]);
const loading = ref(false);

const columns = [
  { title: '代码', key: 'code', width: 130 },
  { title: '公司名称', key: 'name', width: 240, render: (row: Company) => h('span', { style: 'font-weight: 500' }, row.name) },
  {
    title: '标杆',
    key: 'isBenchmark',
    width: 70,
    render: (row: Company) =>
      row.isBenchmark
        ? h(NTag, { size: 'small', type: 'warning', round: true }, { default: () => '标杆', icon: () => h(StarOutline) })
        : '-',
  },
  {
    title: '行业',
    key: 'industry',
    width: 110,
    render: (row: Company) => row.industry ? h(NTag, { size: 'small', type: 'info' }, () => row.industry) : '-',
  },
  {
    title: '规模',
    key: 'scale',
    width: 100,
    render: (row: Company) => row.scale ? h(NTag, { size: 'small', type: 'success' }, () => row.scale) : '-',
  },
  { title: '简介', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '操作',
    key: 'action',
    width: 100,
    fixed: 'right' as const,
    render: (row: Company) =>
      h(NButton, {
        size: 'tiny',
        quaternary: true,
        onClick: () => viewDetail(row),
      }, { default: () => '查看', icon: () => h(OpenOutline) }),
  },
];

async function loadIndustries() {
  try {
    const list = await listCompanyIndustries();
    industryOptions.value = list.map((v: string) => ({ label: v, value: v }));
  } catch (e) {
    /* ignore */
  }
}

async function reload() {
  loading.value = true;
  try {
    rows.value = await searchCompanies({
      keyword: filters.keyword || undefined,
      industry: filters.industry || undefined,
      scale: filters.scale || undefined,
    });
  } catch (e: any) {
    message.error('加载公司失败: ' + (e?.response?.data?.message || e.message));
  } finally {
    loading.value = false;
  }
}

async function viewDetail(row: Company) {
  try {
    const detail = await getCompany(row.id);
    message.info(`${detail.name} - ${detail.industry || '-'} / ${detail.scale || '-'}`);
  } catch (e) {
    message.error('加载详情失败');
  }
}

onMounted(async () => {
  await loadIndustries();
  await reload();
});
</script>

<style scoped>
.company-library { display: flex; flex-direction: column; gap: 12px; height: 100%; }
.page-header { padding: 0 0 4px 0; }
.page-title { font-size: 22px; font-weight: 600; margin: 0; }
.page-subtitle { color: #888; margin: 4px 0 0 0; font-size: 13px; }
.filter-row { margin-bottom: 12px; }
</style>
