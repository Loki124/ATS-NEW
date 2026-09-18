<template>
  <div class="page-container code-table-library">
    <div class="page-body">
      <div class="page-header">
        <h1 class="page-title">静态数据</h1>
        <p class="page-subtitle">国家与行业标准码表（行政区划 / 国家区号 / 民族 / 语言 / 币种 / 行业），为只读国标数据，随标准更新重导</p>
      </div>

      <n-tabs v-model:value="activeTab" type="line" animated>
        <!-- ===== 行政区划 ===== -->
        <n-tab-pane name="regions" tab="行政区划">
          <n-card>
            <n-space class="filter-row" :wrap="true">
              <n-select
                v-model:value="regionCascade.province"
                :options="provinceOptions"
                placeholder="省 / 直辖市"
                clearable
                filterable
                style="width: 180px"
                @update:value="onProvinceChange"
              />
              <n-select
                v-model:value="regionCascade.city"
                :options="cityOptions"
                placeholder="地级市"
                clearable
                filterable
                :disabled="!regionCascade.province"
                style="width: 180px"
                @update:value="onCityChange"
              />
              <n-select
                v-model:value="regionCascade.county"
                :options="countyOptions"
                placeholder="区 / 县"
                clearable
                filterable
                :disabled="!regionCascade.city"
                style="width: 180px"
              />
              <n-input
                v-model:value="regionKeyword"
                placeholder="搜索区划名称 / 代码"
                clearable
                style="width: 200px"
                @keyup.enter="loadRegions"
              >
                <template #prefix><n-icon :component="SearchOutline" /></template>
              </n-input>
              <n-button type="primary" @click="loadRegions">查询</n-button>
            </n-space>

            <n-data-table
              :columns="regionColumns"
              :data="regionRows"
              :loading="loading"
              :pagination="regionPagination"
              :remote="true"
              :row-key="(row: any) => row.code"
              size="small"
              striped
              @update:page="onRegionPageChange"
            />
          </n-card>
        </n-tab-pane>

        <!-- ===== 国家区号 ===== -->
        <n-tab-pane name="countries" tab="国家区号">
          <n-card>
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
            <n-data-table
              :columns="countryColumns"
              :data="countryRows"
              :loading="loading"
              :pagination="{ pageSize: 20 }"
              :row-key="(row: any) => row.code"
              size="small"
              striped
            />
          </n-card>
        </n-tab-pane>

        <!-- ===== 民族 ===== -->
        <n-tab-pane name="ethnicities" tab="民族">
          <n-card>
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
            <n-data-table
              :columns="ethnicColumns"
              :data="ethnicRows"
              :loading="loading"
              :pagination="{ pageSize: 30 }"
              :row-key="(row: any) => row.code"
              size="small"
              striped
            />
          </n-card>
        </n-tab-pane>

        <!-- ===== 语言 ===== -->
        <n-tab-pane name="languages" tab="语言类型">
          <n-card>
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
            <n-data-table
              :columns="langColumns"
              :data="langRows"
              :loading="loading"
              :pagination="{ pageSize: 30 }"
              :row-key="(row: any) => row.code"
              size="small"
              striped
            />
          </n-card>
        </n-tab-pane>

        <!-- ===== 币种（ISO 4217） ===== -->
        <n-tab-pane name="currencies" tab="币种">
          <n-card>
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
            <n-data-table
              :columns="currencyColumns"
              :data="currencyRows"
              :loading="loading"
              :pagination="{ pageSize: 30 }"
              :row-key="(row: any) => row.code"
              size="small"
              striped
            />
          </n-card>
        </n-tab-pane>

        <!-- ===== 行业（GB/T 4754） ===== -->
        <n-tab-pane name="industries" tab="行业">
          <n-card>
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
            <n-data-table
              :columns="industryColumns"
              :data="industryRows"
              :loading="loading"
              :pagination="{ pageSize: 30 }"
              :row-key="(row: any) => row.code"
              size="small"
              striped
            />
          </n-card>
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted, reactive, computed } from 'vue';
import { NTag, useMessage } from 'naive-ui';
import { SearchOutline } from '@vicons/ionicons5';
import {
  fetchRegions, fetchCountries, fetchEthnicities, fetchLanguages,
  fetchCurrencies, fetchIndustries,
  type Region, type Country, type Ethnicity, type Language, type Currency, type Industry,
} from '@/api/codeTable';

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
const regionTotal = ref(0);

const provinceOptions = computed(() => toOptions(provinces.value));
const cityOptions = computed(() => toOptions(cities.value));
const countyOptions = computed(() => toOptions(counties.value));
const regionPagination = computed(() => ({
  page: regionPage.value,
  pageSize: 50,
  itemCount: regionTotal.value,
  showSizePicker: false,
}));

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
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-header { flex-shrink: 0; }
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.filter-row { margin-bottom: var(--space-3); }
</style>
