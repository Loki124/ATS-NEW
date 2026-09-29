<template>
  <div class="page-container company-library">
    <div class="page-header">
      <h1 class="page-title">{{ t('pages.settings.CompanyLibrary.s1') }}</h1>
      <p class="page-subtitle">{{ t('pages.settings.CompanyLibrary.s3') }}</p>
    </div>

    <div class="data-body">
      <n-card class="lib-card">
        <template #header-extra>
          <n-button :loading="loading" @click="reload">{{ t('pages.settings.CompanyLibrary.s2') }}</n-button>
        </template>

        <n-space class="filter-row" :wrap="true">
          <n-input
            v-model:value="filters.keyword"
            :placeholder="t('pages.settings.CompanyLibrary.s4')"
            clearable
            style="width: 240px"
            @keyup.enter="reload"
          >
            <template #prefix><n-icon :component="SearchOutline" /></template>
          </n-input>
          <n-select
            v-model:value="filters.industry"
            :options="industryOptions"
            :placeholder="t('pages.settings.CompanyLibrary.s5')"
            clearable
            style="width: 160px"
            @update:value="reload"
          />
          <n-select
            v-model:value="filters.scale"
            :options="SCALE_OPTIONS"
            :placeholder="t('pages.settings.CompanyLibrary.s6')"
            clearable
            style="width: 140px"
            @update:value="reload"
          />
          <n-button type="primary" @click="reload">{{ t('pages.settings.CompanyLibrary.s7') }}</n-button>
        </n-space>

        <div class="table-wrap">
          <n-data-table
            :columns="columns"
            :data="rows"
            :loading="loading"
            :pagination="localPagination()"
            :row-key="(row: any) => row.id"
            size="small"
            striped
            flex-height
          />
        </div>
      </n-card>
    </div><!-- /.data-body -->
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, h, onMounted, reactive } from 'vue';
import { NTag, NButton, NSpace, useMessage } from 'naive-ui';
import { BusinessOutline, OpenOutline, StarOutline, SearchOutline } from '@vicons/ionicons5';
import { searchCompanies, getCompany, listCompanyIndustries, type Company } from '@/api/library';
import { localPagination } from '@/composables/useTablePagination';
const { t } = useI18n()

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
  { title: t('pages.settings.CompanyLibrary.s8'), key: 'code', width: 130 },
  { title: t('pages.settings.CompanyLibrary.s9'), key: 'name', width: 240, render: (row: Company) => h('span', { style: 'font-weight: 500' }, row.name) },
  {
    title: t('pages.settings.CompanyLibrary.s10'),
    key: 'isBenchmark',
    width: 70,
    render: (row: Company) =>
      row.isBenchmark
        ? h(NTag, { size: 'small', type: 'warning', round: true }, { default: () => t('pages.settings.CompanyLibrary.s16'), icon: () => h(StarOutline) })
        : '-',
  },
  {
    title: t('pages.settings.CompanyLibrary.s11'),
    key: 'industry',
    width: 110,
    render: (row: Company) => row.industry ? h(NTag, { size: 'small', type: 'info' }, () => row.industry) : '-',
  },
  {
    title: t('pages.settings.CompanyLibrary.s12'),
    key: 'scale',
    width: 100,
    render: (row: Company) => row.scale ? h(NTag, { size: 'small', type: 'success' }, () => row.scale) : '-',
  },
  { title: t('pages.settings.CompanyLibrary.s13'), key: 'description', ellipsis: { tooltip: true } },
  {
    title: t('pages.settings.CompanyLibrary.s14'),
    key: 'action',
    width: 100,
    fixed: 'right' as const,
    render: (row: Company) =>
      h(NButton, {
        size: 'tiny',
        quaternary: true,
        onClick: () => viewDetail(row),
      }, { default: () => t('pages.settings.CompanyLibrary.s17'), icon: () => h(OpenOutline) }),
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
    message.error(t('pages.settings.CompanyLibrary.s18') + (e?.response?.data?.message || e.message));
  } finally {
    loading.value = false;
  }
}

async function viewDetail(row: Company) {
  try {
    const detail = await getCompany(row.id);
    message.info(`${detail.name} - ${detail.industry || '-'} / ${detail.scale || '-'}`);
  } catch (e) {
    message.error(t('pages.settings.CompanyLibrary.s15'));
  }
}

onMounted(async () => {
  await loadIndustries();
  await reload();
});
</script>

<style scoped>
/* 「只滚数据列表行内」布局链（与 CodeTableLibrary / CampusControl 同款）：
   .data-body 填高、不滚动；filter 固定；仅 .table-wrap 内 n-data-table 表体内部滚动。
   内层用 .data-body 而非 .page-body，规避 SettingsLayout 对 .page-body 的 overflow:auto!important 强制。 */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-header { flex-shrink: 0; }
.data-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.company-library { display: flex; flex-direction: column; gap: var(--space-3); }
/* n-card 撑满剩余高度；其 .n-card-content（naive-ui 单下划线内容层）改 flex 列，
   内部 .table-wrap(flex:1) 才能把高度传给 n-data-table[flex-height] 实现表体内部滚动 */
.lib-card { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.lib-card :deep(.n-card-content) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.filter-row { flex-shrink: 0; margin-bottom: var(--space-3); }
/* .table-wrap 为全局类（flex:1; min-height:0），此处复用，不再私有重写 */
</style>
