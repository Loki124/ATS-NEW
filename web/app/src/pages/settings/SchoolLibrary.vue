<template>
  <div class="page-container school-library">
<div class="page-body">
    <div class="page-header">
      <h1 class="page-title">院校库</h1>
      <p class="page-subtitle">G41 - 院校信息库 (985/211/重点本科)</p>
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
          :options="EDUCATION_LEVEL_OPTIONS"
          placeholder="教育层次"
          clearable
          style="width: 140px"
          @update:value="reload"
        />
        <n-select
          v-model:value="filters.schoolType"
          :options="SCHOOL_TYPE_OPTIONS"
          placeholder="院校类型"
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
  searchSchools, getSchool, type School,
  searchMajors, getMajorFacets, type Major,
} from '@/api/library';

const message = useMessage();

/** 当前 Tab：院校 / 专业 */
const activeTab = ref('schools');

const EDUCATION_LEVEL_OPTIONS = [
  { label: '本科', value: '本科' },
  { label: '专科', value: '专科' },
  { label: '研究生', value: '研究生' },
];

const SCHOOL_TYPE_OPTIONS = [
  { label: '985', value: '985' },
  { label: '211', value: '211' },
  { label: '本科', value: '本科' },
  { label: '专科', value: '专科' },
];

const SCHOOL_CATEGORY_COLORS: Record<string, 'default' | 'success' | 'warning' | 'info' | 'error'> = {
  综合: 'default',
  理工: 'info',
  师范: 'success',
  财经: 'warning',
  政法: 'error',
  语言: 'success',
};

const filters = reactive({ keyword: '', educationLevel: null as string | null, schoolType: null as string | null });
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
    title: '类别',
    key: 'schoolCategory',
    width: 90,
    render: (row: School) => {
      const v = row.schoolCategory || '-';
      const color = SCHOOL_CATEGORY_COLORS[v] || 'default';
      return h(NTag, { size: 'small', type: color }, () => v);
    },
  },
  { title: '省份', key: 'province', width: 90 },
  { title: '城市', key: 'city', width: 90 },
  { title: '地址', key: 'location', ellipsis: { tooltip: true } },
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
    });
  } catch (e: any) {
    message.error('加载院校失败: ' + (e?.response?.data?.message || e.message));
  } finally {
    loading.value = false;
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
