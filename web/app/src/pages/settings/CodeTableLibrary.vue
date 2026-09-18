<template>
  <div class="page-container code-table-library">
    <div class="page-body">
      <div class="page-header">
        <h1 class="page-title">码表库</h1>
        <p class="page-subtitle">标准码表（行政区划 / 国家区号 / 民族 / 语言）为只读国标数据，随标准更新重导；业务码表为可自定义维护的枚举值</p>
      </div>

      <n-tabs v-model:value="topTab" type="line" animated>
        <!-- ===== 标准码表（只读，随国家标准更新） ===== -->
        <n-tab-pane name="standard" tab="标准码表">
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
          </n-tabs>
        </n-tab-pane>

        <!-- ===== 业务码表（可自定义维护的枚举值） ===== -->
        <n-tab-pane name="business" tab="业务码表">
          <n-card>
            <n-space class="filter-row" :wrap="true" align="center">
              <n-select
                v-model:value="bizCategory"
                :options="categoryOptions"
                placeholder="选择类别"
                style="width: 180px"
                @update:value="loadBusiness"
              />
              <n-input
                v-model:value="bizKeyword"
                placeholder="搜索编码 / 名称"
                clearable
                style="width: 220px"
                @keyup.enter="loadBusiness"
                @clear="loadBusiness"
              >
                <template #prefix><n-icon :component="SearchOutline" /></template>
              </n-input>
              <n-button type="primary" @click="openCreate">新增枚举值</n-button>
            </n-space>

            <n-data-table
              :columns="bizColumns"
              :data="bizRows"
              :loading="bizLoading"
              :row-key="(row: any) => row.id"
              size="small"
              striped
            />
          </n-card>
          <n-modal
            v-model:show="showModal"
            preset="card"
            :title="editingId ? '编辑枚举值' : '新增枚举值'"
            style="width: 520px"
            :mask-closable="false"
          >
            <n-form ref="formRef" :model="form" :rules="formRules" label-placement="top">
              <n-form-item label="类别" path="category">
                <n-select v-model:value="form.category" :options="categoryOptions" placeholder="选择类别" />
              </n-form-item>
              <n-form-item label="编码" path="code">
                <n-input v-model:value="form.code" placeholder="如 BACHELOR / CAMPUS" />
              </n-form-item>
              <n-form-item label="名称" path="name">
                <n-input v-model:value="form.name" placeholder="如 本科 / 校园招聘" />
              </n-form-item>
              <n-form-item label="说明" path="description">
                <n-input v-model:value="form.description" type="textarea" placeholder="可选" />
              </n-form-item>
              <n-form-item label="排序" path="sortOrder">
                <n-input-number v-model:value="form.sortOrder" :min="0" />
              </n-form-item>
            </n-form>
            <template #footer>
              <n-space justify="end">
                <n-button @click="showModal = false">取消</n-button>
                <n-button type="primary" :loading="saving" :disabled="saving" @click="saveBiz">保存</n-button>
              </n-space>
            </template>
          </n-modal>
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted, reactive, computed, watch } from 'vue';
import { NTag, NButton, NPopconfirm, useMessage } from 'naive-ui';
import { SearchOutline } from '@vicons/ionicons5';
import {
  fetchRegions, fetchCountries, fetchEthnicities, fetchLanguages,
  fetchBusinessCodes, createBusinessCode, updateBusinessCode, deleteBusinessCode,
  BUSINESS_CATEGORIES,
  type Region, type Country, type Ethnicity, type Language, type BusinessCode,
} from '@/api/codeTable';

const message = useMessage();
const activeTab = ref('regions');
const loading = ref(false);

const LEVEL_LABEL: Record<number, string> = { 1: '省级', 2: '地级', 3: '县级', 4: '乡级' };

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

// ===== 业务码表（可自定义维护） =====
const topTab = ref('standard');
const bizCategory = ref('EDUCATION');
const bizKeyword = ref('');
const bizRows = ref<BusinessCode[]>([]);
const bizLoading = ref(false);
const showModal = ref(false);
const editingId = ref<string | null>(null);
const saving = ref(false);
const formRef = ref<any>(null);
const form = reactive({
  category: 'EDUCATION',
  code: '',
  name: '',
  description: '',
  parentCode: '',
  sortOrder: 0,
});
const formRules = {
  category: { required: true, message: '请选择类别', trigger: 'change' },
  code: { required: true, message: '请输入编码', trigger: 'blur' },
  name: { required: true, message: '请输入名称', trigger: 'blur' },
};

const categoryLabel = (v: string) =>
  BUSINESS_CATEGORIES.find((c) => c.value === v)?.label || v;
const categoryOptions = BUSINESS_CATEGORIES.map((c) => ({ label: c.label, value: c.value }));

const bizColumns = [
  { title: '类别', key: 'category', width: 110, render: (row: BusinessCode) => categoryLabel(row.category) },
  { title: '编码', key: 'code', width: 160 },
  { title: '名称', key: 'name', width: 160 },
  { title: '说明', key: 'description', width: 200, render: (row: BusinessCode) => row.description || '-' },
  { title: '排序', key: 'sortOrder', width: 80 },
  {
    title: '操作', key: 'actions', width: 130,
    render: (row: BusinessCode) =>
      h('div', { class: 'row-actions' }, [
        h(NButton, { size: 'small', quaternary: true, onClick: () => openEdit(row) }, () => '编辑'),
        h(
          NPopconfirm,
          { positiveText: '删除', negativeText: '取消', onPositiveClick: () => removeBiz(row) },
          {
            trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'error' }, () => '删除'),
            default: () => `确认删除「${row.name}」？该值可能被候选人/职位数据引用，删除后仅软删除保留引用。`,
          },
        ),
      ]),
  },
];

async function loadBusiness() {
  bizLoading.value = true;
  try {
    const res = await fetchBusinessCodes({
      category: bizCategory.value,
      keyword: bizKeyword.value || undefined,
    });
    bizRows.value = res.data || [];
  } catch (e: any) {
    message.error('加载业务码表失败: ' + (e?.response?.data?.message || e.message));
  } finally {
    bizLoading.value = false;
  }
}

function openCreate() {
  editingId.value = null;
  form.category = bizCategory.value;
  form.code = '';
  form.name = '';
  form.description = '';
  form.parentCode = '';
  form.sortOrder = 0;
  showModal.value = true;
}

function openEdit(row: BusinessCode) {
  editingId.value = row.id;
  form.category = row.category;
  form.code = row.code;
  form.name = row.name;
  form.description = row.description || '';
  form.parentCode = row.parentCode || '';
  form.sortOrder = row.sortOrder || 0;
  showModal.value = true;
}

async function saveBiz() {
  if (!formRef.value) return;
  try {
    await formRef.value.validate();
  } catch {
    return;
  }
  saving.value = true;
  const payload = {
    category: form.category,
    code: form.code.trim(),
    name: form.name.trim(),
    description: form.description || undefined,
    parent_code: form.parentCode || undefined,
    sort_order: form.sortOrder || 0,
  };
  try {
    if (editingId.value) {
      await updateBusinessCode(editingId.value, payload);
      message.success('已保存修改');
    } else {
      await createBusinessCode(payload);
      message.success('已新增枚举值');
    }
    showModal.value = false;
    await loadBusiness();
  } catch (e: any) {
    const errs = e?.response?.data?.errors;
    const msg = errs ? JSON.stringify(errs) : (e?.response?.data?.message || e.message);
    message.error('保存失败: ' + msg);
  } finally {
    saving.value = false;
  }
}

async function removeBiz(row: BusinessCode) {
  try {
    await deleteBusinessCode(row.id);
    message.success(`已删除「${row.name}」`);
    await loadBusiness();
  } catch (e: any) {
    message.error('删除失败: ' + (e?.response?.data?.message || e.message));
  }
}

// 进入业务 Tab 时加载一次
watch(topTab, (v) => {
  if (v === 'business' && bizRows.value.length === 0) loadBusiness();
});

onMounted(() => {
  loadProvinces();
  loadRegions();
  loadCountries();
  loadEthnicities();
  loadLanguages();
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
