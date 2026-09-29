<template>
  <div class="page-container major-library">
    <div class="page-header">
      <h1 class="page-title">{{ t('pages.settings.MajorLibrary.s1') }}</h1>
      <p class="page-subtitle">{{ t('pages.settings.MajorLibrary.s2') }}</p>
    </div>

    <div class="data-body">
      <n-card class="lib-card">
        <template #header-extra>
          <n-button :loading="loading" @click="reload">{{ t('pages.settings.MajorLibrary.s3') }}</n-button>
        </template>

        <n-space class="filter-row" :wrap="true">
          <n-input
            v-model:value="filters.keyword"
            :placeholder="t('pages.settings.MajorLibrary.s4')"
            clearable
            style="width: 220px"
            @keyup.enter="reload"
          >
            <template #prefix><n-icon :component="SearchOutline" /></template>
          </n-input>
          <n-select
            v-model:value="filters.discipline"
            :options="disciplineOptions"
            :placeholder="t('pages.settings.MajorLibrary.s5')"
            clearable
            filterable
            style="width: 160px"
            @update:value="reload"
          />
          <n-select
            v-model:value="filters.category"
            :options="categoryOptions"
            :placeholder="t('pages.settings.MajorLibrary.s6')"
            clearable
            filterable
            style="width: 180px"
            @update:value="reload"
          />
          <n-select
            v-model:value="filters.educationLevel"
            :options="eduOptions"
            :placeholder="t('pages.settings.MajorLibrary.s7')"
            clearable
            style="width: 170px"
            @update:value="reload"
          />
          <n-button type="primary" @click="reload">{{ t('pages.settings.MajorLibrary.s8') }}</n-button>
        </n-space>

        <div class="table-wrap">
          <n-data-table
            :columns="columns"
            :data="rows"
            :loading="loading"
            :pagination="localPagination()"
            :row-key="(row: any) => row.id"
            :scroll-x="TABLE_WIDTH"
            size="small"
            striped
            flex-height
          />
        </div>
      </n-card>

      <!-- 专业详情抽屉（专业介绍全文 + 阳光高考链接） -->
      <n-drawer v-model:show="detailVisible" :width="560" placement="right">
        <n-drawer-content :title="detailRow?.name || t('pages.settings.MajorLibrary.s29')" closable>
          <n-descriptions bordered :column="1" label-placement="left" size="small">
            <n-descriptions-item :label="t('pages.settings.MajorLibrary.s9')">{{ detailRow?.code || '-' }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.MajorLibrary.s10')">{{ detailRow?.discipline || '-' }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.MajorLibrary.s11')">{{ detailRow?.category || '-' }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.MajorLibrary.s12')">{{ detailRow?.educationLevel || '-' }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.MajorLibrary.s13')">{{ detailRow?.dataYear || '-' }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.MajorLibrary.s14')">
              {{ detailRow?.isCustomized ? t('pages.settings.MajorLibrary.s39') : t('pages.settings.MajorLibrary.s40') }}
            </n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.MajorLibrary.s15')">
              <div style="white-space: pre-wrap; line-height: 1.6">{{ detailRow?.intro || '-' }}</div>
            </n-descriptions-item>
          </n-descriptions>
          <template #footer>
            <n-space>
              <n-button @click="detailVisible = false">{{ t('pages.settings.MajorLibrary.s16') }}</n-button>
              <n-button
                v-if="detailRow?.detailUrl"
                tag="a"
                :href="detailRow.detailUrl"
                target="_blank"
                rel="noopener"
              >
                {{ t('pages.settings.MajorLibrary.s17') }}
              </n-button>
              <n-button type="primary" @click="openEdit(detailRow!)">{{ t('pages.settings.MajorLibrary.s45') }}</n-button>
            </n-space>
          </template>
        </n-drawer-content>
      </n-drawer>

      <!-- 专业编辑弹窗 -->
      <n-modal
        v-model:show="editVisible"
        preset="card"
        :title="t('pages.settings.MajorLibrary.s18')"
        style="width: 640px"
        :mask-closable="false"
      >
        <n-form :model="editForm" label-placement="left" label-width="96">
          <n-form-item :label="t('pages.settings.MajorLibrary.s19')"><n-input v-model:value="editForm.name" /></n-form-item>
          <n-form-item :label="t('pages.settings.MajorLibrary.s20')"><n-input v-model:value="editForm.code" /></n-form-item>
          <n-form-item :label="t('pages.settings.MajorLibrary.s21')"><n-input v-model:value="editForm.discipline" /></n-form-item>
          <n-form-item :label="t('pages.settings.MajorLibrary.s22')"><n-input v-model:value="editForm.category" /></n-form-item>
          <n-form-item :label="t('pages.settings.MajorLibrary.s23')"><n-input v-model:value="editForm.educationLevel" /></n-form-item>
          <n-form-item :label="t('pages.settings.MajorLibrary.s24')"><n-input v-model:value="editForm.dataYear" /></n-form-item>
          <n-form-item :label="t('pages.settings.MajorLibrary.s25')"><n-input v-model:value="editForm.detailUrl" /></n-form-item>
          <n-form-item :label="t('pages.settings.MajorLibrary.s26')">
            <n-input v-model:value="editForm.intro" type="textarea" :rows="6" />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button :disabled="saving" @click="editVisible = false">{{ t('pages.settings.MajorLibrary.s27') }}</n-button>
            <n-button type="primary" :loading="saving" :disabled="saving" @click="submitEdit">
              {{ t('pages.settings.MajorLibrary.s28') }}
            </n-button>
          </n-space>
        </template>
      </n-modal>
    </div><!-- /.data-body -->
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, h, onMounted, reactive, computed } from 'vue';
import { NTag, NButton, NSpace, useMessage } from 'naive-ui';
import { OpenOutline, CreateOutline, SearchOutline } from '@vicons/ionicons5';
import {
  searchMajors, getMajorFacets, type Major, updateMajor,
} from '@/api/library';
import { localPagination } from '@/composables/useTablePagination';
const { t } = useI18n()

const message = useMessage();

const filters = reactive({
  keyword: '',
  discipline: null as string | null,
  category: null as string | null,
  educationLevel: null as string | null,
});
const rows = ref<Major[]>([]);
const loading = ref(false);
const facets = ref<{ disciplines: string[]; categories: string[]; educationLevels: string[] }>({
  disciplines: [], categories: [], educationLevels: [],
});

const toOptions = (list: string[]) => list.map((v) => ({ label: v, value: v }));
const disciplineOptions = computed(() => toOptions(facets.value.disciplines));
const categoryOptions = computed(() => toOptions(facets.value.categories));
const eduOptions = computed(() => toOptions(facets.value.educationLevels));

const columns = [
  { title: t('pages.settings.MajorLibrary.s30'), key: 'code', width: 100 },
  {
    title: t('pages.settings.MajorLibrary.s31'), key: 'name', width: 180,
    render: (row: Major) => h('span', { style: 'font-weight: 500' }, row.name),
  },
  {
    title: t('pages.settings.MajorLibrary.s32'), key: 'discipline', width: 100,
    render: (row: Major) => row.discipline
      ? h(NTag, { size: 'small', type: 'info' }, () => row.discipline) : '-',
  },
  {
    title: t('pages.settings.MajorLibrary.s33'), key: 'category', width: 150,
    render: (row: Major) => row.category
      ? h(NTag, { size: 'small', type: 'success' }, () => row.category) : '-',
  },
  {
    title: t('pages.settings.MajorLibrary.s34'), key: 'educationLevel', width: 140,
    render: (row: Major) => row.educationLevel
      ? h(NTag, { size: 'small', type: 'warning' }, () => row.educationLevel) : '-',
  },
  { title: t('pages.settings.MajorLibrary.s35'), key: 'dataYear', width: 80 },
  {
    title: t('pages.settings.MajorLibrary.s36'), key: 'intro', width: 320, ellipsis: { tooltip: true },
    render: (row: Major) => row.intro || '-',
  },
  {
    title: t('pages.settings.MajorLibrary.s37'), key: 'action', width: 140, fixed: 'right' as const,
    render: (row: Major) =>
      h(NSpace, { size: 2, justify: 'center', wrap: false }, {
        default: () => [
          h(NButton, {
            size: 'tiny', quaternary: true,
            onClick: () => openDetail(row),
          }, { default: () => t('pages.settings.MajorLibrary.s41'), icon: () => h(OpenOutline) }),
          h(NButton, {
            size: 'tiny', quaternary: true, type: 'primary',
            onClick: () => openEdit(row),
          }, { default: () => t('pages.settings.MajorLibrary.s42'), icon: () => h(CreateOutline) }),
        ],
      }),
  },
];

/** 横向滚动宽度 = 各列宽之和（同院校表） */
const TABLE_WIDTH = computed(() =>
  columns.reduce((sum: number, c: any) => sum + (c.width || 120), 0));

async function reload() {
  loading.value = true;
  try {
    rows.value = await searchMajors({
      keyword: filters.keyword || undefined,
      discipline: filters.discipline || undefined,
      category: filters.category || undefined,
      educationLevel: filters.educationLevel || undefined,
    });
  } catch (e: any) {
    message.error(t('pages.settings.MajorLibrary.s43') + (e?.response?.data?.message || e.message));
  } finally {
    loading.value = false;
  }
}

async function loadFacets() {
  try {
    facets.value = await getMajorFacets();
  } catch {
    /* 筛选可选项加载失败不阻塞主流程 */
  }
}

// ===== 专业：详情抽屉 + 编辑弹窗 =====
const detailVisible = ref(false);
const detailRow = ref<Major | null>(null);
const editVisible = ref(false);
const saving = ref(false);
const editForm = reactive<Record<string, any>>({
  name: '', code: '', discipline: '', category: '',
  educationLevel: '', dataYear: '', detailUrl: '', intro: '',
});

function openDetail(row: Major) {
  detailRow.value = row;
  detailVisible.value = true;
}

function openEdit(row: Major) {
  Object.assign(editForm, {
    name: row.name ?? '',
    code: row.code ?? '',
    discipline: row.discipline ?? '',
    category: row.category ?? '',
    educationLevel: row.educationLevel ?? '',
    dataYear: row.dataYear ?? '',
    detailUrl: row.detailUrl ?? '',
    intro: row.intro ?? '',
  });
  detailRow.value = row;
  detailVisible.value = false;
  editVisible.value = true;
}

async function submitEdit() {
  const row = detailRow.value;
  if (!row) return;
  saving.value = true;
  try {
    await updateMajor(row.id, { ...editForm });
    message.success(t('pages.settings.MajorLibrary.s38'));
    editVisible.value = false;
    await reload();
  } catch (e: any) {
    message.error(t('pages.settings.MajorLibrary.s44') + (e?.response?.data?.message || e.message));
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  loadFacets();
  reload();
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
.major-library { display: flex; flex-direction: column; gap: var(--space-3); }
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
