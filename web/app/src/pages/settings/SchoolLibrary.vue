<template>
  <div class="page-container school-library">
<div class="page-body">
    <div class="page-header">
      <h1 class="page-title">院校库</h1>
      <p class="page-subtitle">院校信息库 — 覆盖本专科院校，含双一流 / 985 / 211 / 双万计划等标签</p>
    </div>

    <n-tabs v-model:value="activeTab" type="line" animated class="lib-tabs">
      <!-- ===== Tab 1: 院校 ===== -->
      <n-tab-pane name="schools" tab="院校">
        <div class="kpi-row">
          <div class="kpi-card"><span class="kpi-label">院校总数</span><span class="kpi-value">{{ rows.length }}</span></div>
        </div>

    <n-card>
      <template #header-extra>
        <n-button :loading="loading" @click="reload">刷新</n-button>
      </template>

      <n-space class="filter-row" :wrap="true">
        <n-input
          v-model:value="filters.keyword"
          placeholder="搜索院校名 / 代码"
          clearable
          style="width: 240px"
          @keyup.enter="reload"
        >
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <n-select
          v-model:value="filters.educationLevel"
          :options="schoolEduOptions"
          placeholder="教育层次"
          clearable
          style="width: 120px"
          @update:value="reload"
        />
        <n-select
          v-model:value="filters.schoolType"
          :options="schoolTypeOptions"
          placeholder="院校类型"
          clearable
          filterable
          style="width: 130px"
          @update:value="reload"
        />
        <n-select
          v-model:value="filters.schoolCategory"
          :options="schoolCategoryOptions"
          placeholder="办学性质"
          clearable
          style="width: 120px"
          @update:value="reload"
        />
        <n-select
          v-model:value="filters.province"
          :options="schoolProvinceOptions"
          placeholder="省份"
          clearable
          filterable
          style="width: 130px"
          @update:value="reload"
        />
        <n-select
          v-model:value="filters.tag"
          :options="schoolTagOptions"
          placeholder="院校标签"
          clearable
          filterable
          style="width: 150px"
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
      </n-tab-pane>

      <!-- ===== Tab 2: 专业（阳光高考专业库）===== -->
      <n-tab-pane name="majors" tab="专业">
        <div class="kpi-row">
          <div class="kpi-card"><span class="kpi-label">专业总数</span><span class="kpi-value">{{ majorRows.length }}</span></div>
          <div class="kpi-card"><span class="kpi-label">门类数</span><span class="kpi-value">{{ majorFacets.disciplines.length }}</span></div>
          <div class="kpi-card"><span class="kpi-label">专业类数</span><span class="kpi-value">{{ majorFacets.categories.length }}</span></div>
        </div>

        <n-card>
          <template #header-extra>
            <n-button :loading="majorLoading" @click="loadMajors">刷新</n-button>
          </template>

          <n-space class="filter-row" :wrap="true">
            <n-input
              v-model:value="majorFilters.keyword"
              placeholder="搜索专业名称 / 代码"
              clearable
              style="width: 220px"
              @keyup.enter="loadMajors"
            >
              <template #prefix><n-icon :component="SearchOutline" /></template>
            </n-input>
            <n-select
              v-model:value="majorFilters.discipline"
              :options="disciplineOptions"
              placeholder="门类"
              clearable
              filterable
              style="width: 160px"
              @update:value="loadMajors"
            />
            <n-select
              v-model:value="majorFilters.category"
              :options="categoryOptions"
              placeholder="专业类"
              clearable
              filterable
              style="width: 180px"
              @update:value="loadMajors"
            />
            <n-select
              v-model:value="majorFilters.educationLevel"
              :options="majorEduOptions"
              placeholder="学历层次"
              clearable
              style="width: 170px"
              @update:value="loadMajors"
            />
            <n-button type="primary" @click="loadMajors">搜索</n-button>
          </n-space>

          <n-data-table
            :columns="majorColumns"
            :data="majorRows"
            :loading="majorLoading"
            :pagination="{ pageSize: 15 }"
            :row-key="(row: any) => row.id"
            size="small"
            striped
          />
        </n-card>
      </n-tab-pane>
    </n-tabs>
    </div><!-- /.page-body -->
</div>
</template>

<script setup lang="ts">
import { ref, h, onMounted, reactive, computed } from 'vue';
import { NTag, NButton, NSpace, useMessage } from 'naive-ui';
import { SchoolOutline, OpenOutline, SearchOutline } from '@vicons/ionicons5';
import {
  searchSchools, getSchool, getSchoolFacets, type School, type SchoolFacets,
  searchMajors, getMajorFacets, type Major,
} from '@/api/library';

const message = useMessage();

/** 当前 Tab：院校 / 专业 */
const activeTab = ref('schools');

// 筛选项一律取自后端 facets —— 真实导入的数据里院校类型是 综合/工科/师范…
// 原先硬编码的 985/211/本科/专科 与数据完全不符（985/211 在「标签」里，不在类型里）。
const schoolFacets = ref<SchoolFacets>({
  schoolTypes: [], schoolCategories: [], educationLevels: [], provinces: [], tags: [],
});
const toSchoolOpts = (list: string[]) => list.map((v) => ({ label: v, value: v }));
const schoolTypeOptions = computed(() => toSchoolOpts(schoolFacets.value.schoolTypes));
const schoolEduOptions = computed(() => toSchoolOpts(schoolFacets.value.educationLevels));
const schoolProvinceOptions = computed(() => toSchoolOpts(schoolFacets.value.provinces));
const schoolCategoryOptions = computed(() => toSchoolOpts(schoolFacets.value.schoolCategories));
const schoolTagOptions = computed(() => toSchoolOpts(schoolFacets.value.tags));

/** 办学性质配色（公办/民办），区别于院校类型的学科属性 */
const NATURE_COLORS: Record<string, 'default' | 'success' | 'warning' | 'info' | 'error'> = {
  公办: 'success',
  民办: 'warning',
};

const filters = reactive({
  keyword: '',
  educationLevel: null as string | null,
  schoolType: null as string | null,
  schoolCategory: null as string | null,
  province: null as string | null,
  tag: null as string | null,
});
const rows = ref<School[]>([]);
const loading = ref(false);

const columns = [
  { title: '代码', key: 'code', width: 100 },
  { title: '院校名称', key: 'name', width: 200, render: (row: School) => h('span', { style: 'font-weight: 500' }, row.name) },
  {
    title: '教育层次',
    key: 'educationLevel',
    width: 100,
    render: (row: School) => row.educationLevel ? h(NTag, { size: 'small', type: 'info' }, () => row.educationLevel) : '-',
  },
  {
    title: '院校类型',
    key: 'schoolType',
    width: 100,
    render: (row: School) => row.schoolType ? h(NTag, { size: 'small', type: 'success' }, () => row.schoolType) : '-',
  },
  {
    title: '办学性质',
    key: 'schoolCategory',
    width: 90,
    render: (row: School) => {
      const v = row.schoolCategory || '-';
      const color = NATURE_COLORS[v] || 'default';
      return h(NTag, { size: 'small', type: color }, () => v);
    },
  },
  { title: '省份', key: 'province', width: 90 },
  { title: '城市', key: 'city', width: 90 },
  {
    title: '主管部门',
    key: 'affiliatedTo',
    width: 140,
    render: (row: School) => row.affiliatedTo || '-',
  },
  {
    title: '标签',
    key: 'tags',
    width: 220,
    render: (row: School) => {
      const list = (row.tags || '').split('|').filter(Boolean);
      if (!list.length) return '-';
      const chips = list.slice(0, 2).map((t) =>
        h(NTag, { size: 'small', type: 'info' }, () => t));
      if (list.length > 2) {
        chips.push(h('span', { style: 'font-size: 12px; color: var(--n-400, #909399)' }, `+${list.length - 2}`));
      }
      // 截断内容必须可查看完整信息（title 兜底）
      return h('div', {
        style: 'display: flex; align-items: center; gap: 4px; flex-wrap: wrap',
        title: list.join('、'),
      }, chips);
    },
  },
  { title: '地址', key: 'location', width: 200, ellipsis: { tooltip: true } },
  {
    title: '操作',
    key: 'action',
    width: 100,
    fixed: 'right' as const,
    render: (row: School) =>
      h(NButton, {
        size: 'tiny',
        quaternary: true,
        onClick: () => viewDetail(row),
      }, { default: () => '查看', icon: () => h(OpenOutline) }),
  },
];

async function reload() {
  loading.value = true;
  try {
    rows.value = await searchSchools({
      keyword: filters.keyword || undefined,
      educationLevel: filters.educationLevel || undefined,
      schoolType: filters.schoolType || undefined,
      schoolCategory: filters.schoolCategory || undefined,
      province: filters.province || undefined,
      tag: filters.tag || undefined,
    });
  } catch (e: any) {
    message.error('加载院校失败: ' + (e?.response?.data?.message || e.message));
  } finally {
    loading.value = false;
  }
}

async function loadSchoolFacets() {
  try {
    schoolFacets.value = await getSchoolFacets();
  } catch {
    /* 筛选项加载失败不阻塞主流程，下拉为空即可 */
  }
}

async function viewDetail(row: School) {
  try {
    const detail = await getSchool(row.id);
    message.info(`${detail.name} (${detail.code}) - ${detail.province || ''}${detail.city || ''}`);
  } catch (e: any) {
    message.error('加载详情失败');
  }
}

// ===== 专业 Tab =====
const majorFilters = reactive({
  keyword: '',
  discipline: null as string | null,
  category: null as string | null,
  educationLevel: null as string | null,
});
const majorRows = ref<Major[]>([]);
const majorLoading = ref(false);
const majorFacets = ref<{ disciplines: string[]; categories: string[]; educationLevels: string[] }>({
  disciplines: [], categories: [], educationLevels: [],
});

const toOptions = (list: string[]) => list.map((v) => ({ label: v, value: v }));
const disciplineOptions = computed(() => toOptions(majorFacets.value.disciplines));
const categoryOptions = computed(() => toOptions(majorFacets.value.categories));
const majorEduOptions = computed(() => toOptions(majorFacets.value.educationLevels));

const majorColumns = [
  { title: '专业代码', key: 'code', width: 100 },
  {
    title: '专业名称', key: 'name', width: 180,
    render: (row: Major) => h('span', { style: 'font-weight: 500' }, row.name),
  },
  {
    title: '门类', key: 'discipline', width: 100,
    render: (row: Major) => row.discipline
      ? h(NTag, { size: 'small', type: 'info' }, () => row.discipline) : '-',
  },
  {
    title: '专业类', key: 'category', width: 150,
    render: (row: Major) => row.category
      ? h(NTag, { size: 'small', type: 'success' }, () => row.category) : '-',
  },
  {
    title: '学历层次', key: 'educationLevel', width: 140,
    render: (row: Major) => row.educationLevel
      ? h(NTag, { size: 'small', type: 'warning' }, () => row.educationLevel) : '-',
  },
  { title: '年份', key: 'dataYear', width: 80 },
  {
    title: '专业介绍', key: 'intro', ellipsis: { tooltip: true },
    render: (row: Major) => row.intro || '-',
  },
  {
    title: '操作', key: 'action', width: 100, fixed: 'right' as const,
    render: (row: Major) => (row.detailUrl
      ? h(NButton, {
          size: 'tiny', quaternary: true,
          onClick: () => window.open(row.detailUrl, '_blank'),
        }, { default: () => '详情', icon: () => h(OpenOutline) })
      : '-'),
  },
];

async function loadMajors() {
  majorLoading.value = true;
  try {
    majorRows.value = await searchMajors({
      keyword: majorFilters.keyword || undefined,
      discipline: majorFilters.discipline || undefined,
      category: majorFilters.category || undefined,
      educationLevel: majorFilters.educationLevel || undefined,
    });
  } catch (e: any) {
    message.error('加载专业失败: ' + (e?.response?.data?.message || e.message));
  } finally {
    majorLoading.value = false;
  }
}

async function loadMajorFacets() {
  try {
    majorFacets.value = await getMajorFacets();
  } catch {
    /* 筛选可选项加载失败不阻塞主流程 */
  }
}

onMounted(() => {
  loadSchoolFacets();
  reload();
  loadMajorFacets();
  loadMajors();
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


.school-library { display: flex; flex-direction: column; gap: var(--space-3); }
/* 删除 scoped .page-header/.page-title/.page-subtitle 覆盖（规范：复用全局 glass.css） */
.filter-row { margin-bottom: var(--space-3); }
</style>
