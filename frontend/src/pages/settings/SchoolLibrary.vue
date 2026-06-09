<template>
  <div class="school-library">
    <div class="page-header">
      <h1 class="page-title">院校库</h1>
      <p class="page-subtitle">G41 - 院校信息库 (985/211/重点本科)</p>
    </div>

    <n-card>
      <template #header-extra>
        <n-button @click="reload" :loading="loading">刷新</n-button>
      </template>

      <n-space class="filter-row" :wrap="true">
        <n-input
          v-model:value="filters.keyword"
          placeholder="搜索院校名 / 代码"
          clearable
          style="width: 240px"
          @keyup.enter="reload"
        />
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
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted, reactive } from 'vue';
import { NTag, NButton, NSpace, useMessage } from 'naive-ui';
import { SchoolOutline, OpenOutline } from '@vicons/ionicons5';
import { searchSchools, getSchool, type School } from '@/api/library';

const message = useMessage();

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

onMounted(() => { reload(); });
</script>

<style scoped>
.school-library { display: flex; flex-direction: column; gap: 12px; height: 100%; }
.page-header { padding: 0 0 4px 0; }
.page-title { font-size: 22px; font-weight: 600; margin: 0; }
.page-subtitle { color: #888; margin: 4px 0 0 0; font-size: 13px; }
.filter-row { margin-bottom: 12px; }
</style>
