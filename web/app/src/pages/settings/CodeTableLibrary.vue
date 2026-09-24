<template>
  <div class="page-container code-table-library">
    <div class="page-header">
      <h1 class="page-title">{ t('pages.settings.CodeTableLibrary.s1') }</h1>
      <p class="page-subtitle">{ t('pages.settings.CodeTableLibrary.s2') }</p>
    </div>

    <div class="data-body">
      <n-tabs v-model:value="activeTab" type="line" animated class="data-tabs">
        <!-- ===== 行政区划 ===== -->
        <n-tab-pane name="regions" tab="行政区划">
          <n-card class="tab-card">
            <n-space class="filter-row" :wrap="true">
              <n-select
                v-model:value="regionCascade.province"
                :options="provinceOptions"
                :placeholder="t('pages.settings.CodeTableLibrary.s3')"
                clearable
                filterable
                style="width: 180px"
                @update:value="onProvinceChange"
              />
              <n-select
                v-model:value="regionCascade.city"
                :options="cityOptions"
                :placeholder="t('pages.settings.CodeTableLibrary.s4')"
                clearable
                filterable
                :disabled="!regionCascade.province"
                style="width: 180px"
                @update:value="onCityChange"
              />
              <n-select
                v-model:value="regionCascade.county"
                :options="countyOptions"
                :placeholder="t('pages.settings.CodeTableLibrary.s5')"
                clearable
                filterable
                :disabled="!regionCascade.city"
                style="width: 180px"
              />
              <n-input
                v-model:value="regionKeyword"
                :placeholder="t('pages.settings.CodeTableLibrary.s6')"
                clearable
                style="width: 200px"
                @keyup.enter="loadRegions"
              >
                <template #prefix><n-icon :component="SearchOutline" /></template>
              </n-input>
              <n-button type="primary" @click="loadRegions">查询</n-button>
            </n-space>

            <div class="table-wrap">
              <n-data-table
                :columns="regionColumns"
                :data="regionRows"
                :loading="loading"
                :pagination="regionPagination"
                :remote="true"
                :row-key="(row: any) => row.code"
                size="small"
                striped
                flex-height
                @update:page="onRegionPageChange"
              />
            </div>
          </n-card>
        </n-tab-pane>

        <!-- ===== 国家区号 ===== -->
        <n-tab-pane name="countries" tab="国家区号">
          <n-card class="tab-card">
            <n-space class="filter-row" :wrap="true">
              <n-input
                v-model:value="countryKeyword"
                placeholder="搜索国家 / 区号（如 86）"
                clearable
                style="width: 220px"
                @keyup.enter="loadCountries"
              >
                <template #prefix><n-icon :component="SearchOutline" /></template>
              </n-input>
              <n-button type="primary" @click="loadCountries">查询</n-button>
            </n-space>
            <div class="table-wrap">
              <n-data-table
                :columns="countryColumns"
                :data="countryRows"
                :loading="loading"
                :pagination="localPagination()"
                :row-key="(row: any) => row.code"
                size="small"
                striped
                flex-height
              />
            </div>
          </n-card>
        </n-tab-pane>

        <!-- ===== 民族 ===== -->
        <n-tab-pane name="ethnicities" tab="民族">
          <n-card class="tab-card">
            <n-space class="filter-row" :wrap="true">
              <n-input
                v-model:value="ethnicKeyword"
                placeholder="搜索民族 / 代码"
                clearable
                style="width: 220px"
                @keyup.enter="loadEthnicities"
              >
                <template #prefix><n-icon :component="SearchOutline" /></template>
              </n-input>
              <n-button type="primary" @click="loadEthnicities">查询</n-button>
            </n-space>
            <div class="table-wrap">
              <n-data-table
                :columns="ethnicColumns"
                :data="ethnicRows"
                :loading="loading"
                :pagination="localPagination()"
                :row-key="(row: any) => row.code"
                size="small"
                striped
                flex-height
              />
            </div>
          </n-card>
        </n-tab-pane>

        <!-- ===== 语言 ===== -->
        <n-tab-pane name="languages" tab="语言类型">
          <n-card class="tab-card">
            <n-space class="filter-row" :wrap="true">
              <n-input
                v-model:value="langKeyword"
                placeholder="搜索语言 / 代码"
                clearable
                style="width: 220px"
                @keyup.enter="loadLanguages"
              >
                <template #prefix><n-icon :component="SearchOutline" /></template>
              </n-input>
              <n-button type="primary" @click="loadLanguages">查询</n-button>
            </n-space>
            <div class="table-wrap">
              <n-data-table
                :columns="langColumns"
                :data="langRows"
                :loading="loading"
                :pagination="localPagination()"
                :row-key="(row: any) => row.code"
                size="small"
                striped
                flex-height
              />
            </div>
          </n-card>
        </n-tab-pane>

        <!-- ===== 币种（ISO 4217） ===== -->
        <n-tab-pane name="currencies" tab="币种">
          <n-card class="tab-card">
            <n-space class="filter-row" :wrap="true">
              <n-input
                v-model:value="currencyKeyword"
                placeholder="搜索币种 / 代码 / 符号"
                clearable
                style="width: 240px"
                @keyup.enter="loadCurrencies"
              >
                <template #prefix><n-icon :component="SearchOutline" /></template>
              </n-input>
              <n-button type="primary" @click="loadCurrencies">查询</n-button>
            </n-space>
            <div class="table-wrap">
              <n-data-table
                :columns="currencyColumns"
                :data="currencyRows"
                :loading="loading"
                :pagination="localPagination()"
                :row-key="(row: any) => row.code"
                size="small"
                striped
                flex-height
              />
            </div>
          </n-card>
        </n-tab-pane>

        <!-- ===== 行业（GB/T 4754） ===== -->
        <n-tab-pane name="industries" tab="行业">
          <n-card class="tab-card">
            <n-space class="filter-row" :wrap="true">
              <n-select
                v-model:value="industryLevel"
                :options="industryLevelOptions"
                placeholder="层级"
                clearable
                style="width: 140px"
                @update:value="loadIndustries"
              />
              <n-input
                v-model:value="industryKeyword"
                placeholder="搜索行业名称 / 代码"
                clearable
                style="width: 220px"
                @keyup.enter="loadIndustries"
              >
                <template #prefix><n-icon :component="SearchOutline" /></template>
              </n-input>
              <n-button type="primary" @click="loadIndustries">查询</n-button>
            </n-space>
            <div class="table-wrap">
              <n-data-table
                :columns="industryColumns"
                :data="industryRows"
                :loading="loading"
                :pagination="localPagination()"
                :row-key="(row: any) => row.code"
                size="small"
                striped
                flex-height
              />
            </div>
          </n-card>
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, h, onMounted, reactive, computed } from 'vue';
import { NTag, useMessage } from 'naive-ui';
import { SearchOutline } from '@vicons/ionicons5';
import {
  fetchRegions, fetchCountries, fetchEthnicities, fetchLanguages,
  fetchCurrencies, fetchIndustries,
  type Region, type Country, type Ethnicity, type Language, type Currency, type Industry,
} from '@/api/codeTable';
import { localPagination, remotePagination, TABLE_PAGE_SIZE } from '@/composables/useTablePagination';
const { t } = useI18n()

const message = useMessage();
const activeTab = ref('regions');
const loading = ref(false);

const LEVEL_LABEL: Record<number, string> = { 1: '省级', 2: '地级', 3: '县级', 4: '乡级' };
const INDUSTRY_LEVEL_LABEL: Record<number, string> = { 1: '门类', 2: '大类', 3: '中类', 4: '小类' };

const toOptions = (list: { code: string; name: string }[]) =>
  list.map((r) => ({ label: r.name, value: r.code }));

// ===== 行政区划 =====
const regionCascade = reactive({
  province: null as string | null,
  city: null as string | null,
  county: null as string | null,
});
const regionKeyword = ref('');
const regionRows = ref<Region[]>([]);
const provinces = ref<{ code: string; name: string }[]>([]);
const cities = ref<{ code: string; name: string }[]>([]);
const counties = ref<{ code: string; name: string }[]>([]);
const regionPage = ref(1);
const regionPageSize = ref(TABLE_PAGE_SIZE);
const regionTotal = ref(0);

const provinceOptions = computed(() => toOptions(provinces.value));
const cityOptions = computed(() => toOptions(cities.value));
const countyOptions = computed(() => toOptions(counties.value));
const regionPagination = remotePagination({
  page: regionPage,
  itemCount: regionTotal,
  showSizePicker: true,
  onPageSizeChange: (s: number) => {
    regionPageSize.value = s;
    regionPage.value = 1;
    loadRegions();
  },
});

const regionColumns = [
  { title: '区划代码', key: 'code', width: 140 },
  { title: '名称', key: 'name', width: 200 },
  {
    title: '层级', key: 'level', width: 90,
    render: (row: Region) => h(NTag, { size: 'small', type: 'info' }, () => LEVEL_LABEL[row.level] || '-'),
  },
  { title: '上级代码', key: 'parentCode', width: 140, render: (row: Region) => row.parentCode || '-' },
];

async function loadRegions() {
  loading.value = true;
  try {
    // 级联优先级：区县 > 市 > 省；未选则按层级+关键词查
    const parentCode = regionCascade.county || regionCascade.city || regionCascade.province || undefined;
    const res = await fetchRegions({
      parentCode,
      keyword: regionKeyword.value || undefined,
      page: regionPage.value,
      page_size: regionPageSize.value,
    });
    regionRows.value = res.data;
    regionTotal.value = res.pagination?.total ?? res.data.length;
  } catch (e: any) {
    message.error('加载行政区划失败: ' + (e?.response?.data?.detail || e.message));
  } finally {
    loading.value = false;
  }
}

function onRegionPageChange(page: number) {
  regionPage.value = page;
  loadRegions();
}

async function loadProvinces() {
  try {
    const res = await fetchRegions({ level: 1, page_size: 100 });
    provinces.value = res.data;
  } catch {
    /* 级联可选项失败不阻塞 */
  }
}

async function onProvinceChange() {
  regionCascade.city = null;
  regionCascade.county = null;
  cities.value = [];
  counties.value = [];
  regionPage.value = 1;
  if (regionCascade.province) {
    try {
      const res = await fetchRegions({ level: 2, parentCode: regionCascade.province, page_size: 500 });
      cities.value = res.data;
    } catch { /* noop */ }
  }
  loadRegions();
}

async function onCityChange() {
  regionCascade.county = null;
  counties.value = [];
  regionPage.value = 1;
  if (regionCascade.city) {
    try {
      const res = await fetchRegions({ level: 3, parentCode: regionCascade.city, page_size: 500 });
      counties.value = res.data;
    } catch { /* noop */ }
  }
  loadRegions();
}

// ===== 国家区号 =====
const countryKeyword = ref('');
const countryRows = ref<Country[]>([]);
const countryColumns = [
  { title: '区号', key: 'phoneCode', width: 100,
    render: (row: Country) => h('span', { style: 'font-weight:600' }, row.phoneCode || '-') },
  { title: '中文名称', key: 'nameCn', width: 160 },
  { title: '英文名称', key: 'nameEn', width: 200 },
  { title: 'ISO alpha-2', key: 'code', width: 110 },
  { title: 'ISO alpha-3', key: 'code3', width: 110 },
];

async function loadCountries() {
  loading.value = true;
  try {
    const res = await fetchCountries({ keyword: countryKeyword.value || undefined, page_size: 300 });
    countryRows.value = res.data;
  } catch (e: any) {
    message.error('加载国家失败: ' + (e?.response?.data?.detail || e.message));
  } finally {
    loading.value = false;
  }
}

// ===== 民族 =====
const ethnicKeyword = ref('');
const ethnicRows = ref<Ethnicity[]>([]);
const ethnicColumns = [
  { title: '数字代码', key: 'code', width: 110 },
  { title: '民族', key: 'name', width: 160 },
  { title: '罗马字母码', key: 'letterCode', width: 120, render: (row: Ethnicity) => row.letterCode || '-' },
];

async function loadEthnicities() {
  loading.value = true;
  try {
    const res = await fetchEthnicities({ keyword: ethnicKeyword.value || undefined, page_size: 200 });
    ethnicRows.value = res.data;
  } catch (e: any) {
    message.error('加载民族失败: ' + (e?.response?.data?.detail || e.message));
  } finally {
    loading.value = false;
  }
}

// ===== 语言 =====
const langKeyword = ref('');
const langRows = ref<Language[]>([]);
const langColumns = [
  { title: '代码', key: 'code', width: 110 },
  { title: '中文名称', key: 'nameCn', width: 200 },
  { title: '英文名称', key: 'nameEn', width: 200 },
];

async function loadLanguages() {
  loading.value = true;
  try {
    const res = await fetchLanguages({ keyword: langKeyword.value || undefined, page_size: 700 });
    langRows.value = res.data;
  } catch (e: any) {
    message.error('加载语言失败: ' + (e?.response?.data?.detail || e.message));
  } finally {
    loading.value = false;
  }
}

// ===== 币种（ISO 4217） =====
const currencyKeyword = ref('');
const currencyRows = ref<Currency[]>([]);
const currencyColumns = [
  { title: '代码', key: 'code', width: 90 },
  { title: '数字代码', key: 'codeNumeric', width: 100, render: (row: Currency) => row.codeNumeric || '-' },
  { title: '符号', key: 'symbol', width: 80, render: (row: Currency) => row.symbol || '-' },
  { title: '中文名称', key: 'nameCn', width: 160 },
  { title: '英文名称', key: 'nameEn', width: 220 },
];

async function loadCurrencies() {
  loading.value = true;
  try {
    const res = await fetchCurrencies({ keyword: currencyKeyword.value || undefined, page_size: 300 });
    currencyRows.value = res.data;
  } catch (e: any) {
    message.error('加载币种失败: ' + (e?.response?.data?.detail || e.message));
  } finally {
    loading.value = false;
  }
}

// ===== 行业（GB/T 4754） =====
const industryLevel = ref<number | null>(null);
const industryKeyword = ref('');
const industryRows = ref<Industry[]>([]);
const industryLevelOptions = [
  { label: '门类', value: 1 },
  { label: '大类', value: 2 },
  { label: '中类', value: 3 },
  { label: '小类', value: 4 },
];
const industryColumns = [
  { title: '代码', key: 'code', width: 100 },
  { title: '名称', key: 'name', width: 260 },
  {
    title: '层级', key: 'level', width: 90,
    render: (row: Industry) => h(NTag, { size: 'small', type: 'info' }, () => INDUSTRY_LEVEL_LABEL[row.level] || '-'),
  },
  { title: '上级代码', key: 'parentCode', width: 120, render: (row: Industry) => row.parentCode || '-' },
];

async function loadIndustries() {
  loading.value = true;
  try {
    const res = await fetchIndustries({
      level: industryLevel.value || undefined,
      keyword: industryKeyword.value || undefined,
      page_size: 300,
    });
    industryRows.value = res.data;
  } catch (e: any) {
    message.error('加载行业失败: ' + (e?.response?.data?.detail || e.message));
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadProvinces();
  loadRegions();
  loadCountries();
  loadEthnicities();
  loadLanguages();
  loadCurrencies();
  loadIndustries();
});
</script>

<style scoped>
/* 「只滚数据列表行内」布局链：标题固定 → .data-body 不滚动（避开 SettingsLayout 对 .page-body 的
   overflow-y:auto!important 强制整体滚动）→ tabs/筛选栏固定 → 仅 n-data-table 表体内部滚动
   （参照校招管控-规则配置页 CampusControl.vue）。机制与 CampusControl 一致：pane-wrapper /
   tab-pane overflow:hidden + flex 列，表格用全局 .table-wrap(flex:1;min-height:0) + flex-height
   撑满并内部滚动。 */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-header { flex-shrink: 0; }
/* .data-body 不再整体滚动：作为 flex 列撑满剩余高度，真实滚动交给表格体 */
.data-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
/* 对齐校招管控-规则配置页（CampusControl）的「只滚表格行内」链：
   容器不用 .page-body（SettingsLayout 用 !important 强制其 overflow-y:auto 整体滚动），
   改用 .data-body（透明、避开该 !important）；n-tabs 直接挂 .data-tabs 撑满高度。 */
.data-tabs {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

/* tabs 填满 .data-body；导航栏固定不滚，pane 内部由表格滚动 */
.data-body :deep(.n-tabs) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.data-body :deep(.n-tabs-nav) {
  background: transparent;
  flex-shrink: 0;
}
.data-body :deep(.n-tabs-pane-wrapper) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.data-body :deep(.n-tab-pane) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* tab-pane 内 n-card 撑满高度：筛选栏固定、.table-wrap 滚动 */
.tab-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
/* naive-ui 该版本 n-card 内容包裹层类名是 .n-card-content（单下划线，非 .n-card__content）；
   其默认 display:block，须改为 flex 列并 min-height:0，内部 .table-wrap(flex:1) 才能撑满卡片高度 */
.tab-card :deep(.n-card-content) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.filter-row { margin-bottom: var(--space-3); flex-shrink: 0; }
</style>
