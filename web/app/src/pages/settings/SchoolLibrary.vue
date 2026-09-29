<template>
  <div class="page-container school-library">
    <div class="page-header">
      <h1 class="page-title">{{ t('pages.settings.SchoolLibrary.s1') }}</h1>
      <p class="page-subtitle">{{ t('pages.settings.SchoolLibrary.s2') }}</p>
    </div>

    <div class="data-body">
      <n-card class="lib-card">
        <template #header-extra>
          <n-space>
            <n-button :loading="loading" @click="reload">{{ t('pages.settings.SchoolLibrary.s3') }}</n-button>
            <n-button type="primary" @click="openCreate">{{ t('pages.settings.SchoolLibrary.s4') }}</n-button>
          </n-space>
        </template>

        <n-space class="filter-row" :wrap="true">
          <n-input
            v-model:value="filters.keyword"
            :placeholder="t('pages.settings.SchoolLibrary.s5')"
            clearable
            style="width: 240px"
            @keyup.enter="reload"
          >
            <template #prefix><n-icon :component="SearchOutline" /></template>
          </n-input>
          <n-select
            v-model:value="filters.educationLevel"
            :options="schoolEduOptions"
            :placeholder="t('pages.settings.SchoolLibrary.s6')"
            clearable
            style="width: 120px"
            @update:value="reload"
          />
          <n-select
            v-model:value="filters.schoolType"
            :options="schoolTypeOptions"
            :placeholder="t('pages.settings.SchoolLibrary.s7')"
            clearable
            filterable
            style="width: 130px"
            @update:value="reload"
          />
          <n-select
            v-model:value="filters.schoolCategory"
            :options="schoolCategoryOptions"
            :placeholder="t('pages.settings.SchoolLibrary.s8')"
            clearable
            style="width: 120px"
            @update:value="reload"
          />
          <n-select
            v-model:value="filters.province"
            :options="schoolProvinceOptions"
            :placeholder="t('pages.settings.SchoolLibrary.s9')"
            clearable
            filterable
            style="width: 130px"
            @update:value="reload"
          />
          <n-select
            v-model:value="filters.tag"
            :options="schoolTagOptions"
            :placeholder="t('pages.settings.SchoolLibrary.s10')"
            clearable
            filterable
            style="width: 150px"
            @update:value="reload"
          />
          <n-button type="primary" @click="reload">{{ t('pages.settings.SchoolLibrary.s11') }}</n-button>
        </n-space>

        <div class="table-wrap">
          <n-data-table
            :columns="columns"
            :data="rows"
            :loading="loading"
            :pagination="localPagination()"
            :row-key="(row: any) => row.id"
            :scroll-x="SCHOOL_TABLE_WIDTH"
            size="small"
            striped
            flex-height
          />
        </div>
      </n-card>

      <!-- 院校详情抽屉 -->
      <n-drawer v-model:show="detailVisible" :width="560" placement="right">
        <n-drawer-content :title="detailRow?.name || t('pages.settings.SchoolLibrary.s46')" closable>
          <n-descriptions bordered :column="1" label-placement="left" size="small">
            <n-descriptions-item :label="t('pages.settings.SchoolLibrary.s12')">{{ detailRow?.code || '-' }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.SchoolLibrary.s13')">
              {{ (detailRow?.formerNames || '').split('|').filter(Boolean).join('、') || '-' }}
            </n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.SchoolLibrary.s14')">{{ detailRow?.educationLevel || '-' }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.SchoolLibrary.s15')">{{ detailRow?.schoolType || '-' }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.SchoolLibrary.s16')">{{ detailRow?.schoolCategory || '-' }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.SchoolLibrary.s17')">
              {{ [detailRow?.province, detailRow?.city].filter(Boolean).join(' / ') || '-' }}
            </n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.SchoolLibrary.s18')">{{ detailRow?.affiliatedTo || '-' }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.SchoolLibrary.s19')">{{ detailRow?.location || '-' }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.SchoolLibrary.s20')">
              <n-space v-if="tagListOf(detailRow).length" :size="[4, 4]">
                <n-tag v-for="tag in tagListOf(detailRow)" :key="tag" size="small" type="info">{{ tag }}</n-tag>
              </n-space>
              <span v-else>-</span>
            </n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.SchoolLibrary.s21')">{{ detailRow?.status || '-' }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.SchoolLibrary.s22')">{{ detailRow?.updatedAt ? formatTime(detailRow.updatedAt) : '-' }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.settings.SchoolLibrary.s23')">
              {{ detailRow?.isCustomized ? t('pages.settings.SchoolLibrary.s63') : t('pages.settings.SchoolLibrary.s64') }}
            </n-descriptions-item>
          </n-descriptions>
          <template #footer>
            <n-space>
              <n-button @click="detailVisible = false">{{ t('pages.settings.SchoolLibrary.s24') }}</n-button>
              <n-button type="primary" @click="openEdit(detailRow!)">编辑</n-button>
            </n-space>
          </template>
        </n-drawer-content>
      </n-drawer>

      <!-- 院校编辑 / 新增弹窗 -->
      <n-modal
        v-model:show="editVisible"
        preset="card"
        :title="editingId ? t('pages.settings.SchoolLibrary.s61') : t('pages.settings.SchoolLibrary.s62')"
        style="width: 680px"
        :mask-closable="false"
      >
        <n-form ref="editFormRef" :model="editForm" :rules="editRules" label-placement="left" label-width="96">
          <n-form-item :label="t('pages.settings.SchoolLibrary.s26')" path="name">
            <n-input v-model:value="editForm.name" :placeholder="t('pages.settings.SchoolLibrary.s27')" maxlength="200" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.SchoolLibrary.s28')" path="code">
            <n-input v-model:value="editForm.code" :placeholder="t('pages.settings.SchoolLibrary.s29')" maxlength="50" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.SchoolLibrary.s30')">
            <n-dynamic-tags v-model:value="formerNameList" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.SchoolLibrary.s31')">
            <n-select v-model:value="editForm.educationLevel" :options="schoolEduOptions" clearable filterable
              tag :placeholder="t('pages.settings.SchoolLibrary.s32')" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.SchoolLibrary.s33')">
            <n-select v-model:value="editForm.schoolType" :options="schoolTypeOptions" clearable filterable
              tag :placeholder="t('pages.settings.SchoolLibrary.s34')" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.SchoolLibrary.s35')">
            <n-select v-model:value="editForm.schoolCategory" :options="schoolCategoryOptions" clearable
              tag :placeholder="t('pages.settings.SchoolLibrary.s36')" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.SchoolLibrary.s37')">
            <n-space :wrap="false">
              <n-select v-model:value="editForm.province" :options="schoolProvinceOptions" clearable filterable
                tag :placeholder="t('pages.settings.SchoolLibrary.s38')" style="width: 150px" />
              <n-input v-model:value="editForm.city" :placeholder="t('pages.settings.SchoolLibrary.s39')" style="width: 150px" />
            </n-space>
          </n-form-item>
          <n-form-item :label="t('pages.settings.SchoolLibrary.s40')">
            <n-input v-model:value="editForm.affiliatedTo" maxlength="100" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.SchoolLibrary.s41')">
            <n-input v-model:value="editForm.location" maxlength="200" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.SchoolLibrary.s42')">
            <n-dynamic-tags v-model:value="editTagList" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.SchoolLibrary.s43')">
            <n-select v-model:value="editForm.status" :options="STATUS_OPTIONS" />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button :disabled="saving" @click="editVisible = false">{{ t('pages.settings.SchoolLibrary.s44') }}</n-button>
            <n-button type="primary" :loading="saving" :disabled="saving" @click="submitEdit">{{ t('pages.settings.SchoolLibrary.s45') }}</n-button>
          </n-space>
        </template>
      </n-modal>
    </div><!-- /.data-body -->
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, h, onMounted, reactive, computed } from 'vue';
import { NTag, NButton, NSpace, useMessage, type FormInst, type FormRules } from 'naive-ui';
import { SchoolOutline, OpenOutline, SearchOutline, CreateOutline } from '@vicons/ionicons5';
import {
  searchSchools, getSchoolFacets, type School, type SchoolFacets,
  createSchool, updateSchool,
} from '@/api/library';
import { localPagination } from '@/composables/useTablePagination';
const { t } = useI18n()

const message = useMessage();

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
  { title: t('pages.settings.SchoolLibrary.s47'), key: 'code', width: 100 },
  {
    title: t('pages.settings.SchoolLibrary.s48'),
    key: 'name',
    width: 200,
    render: (row: School) => h('span', { style: 'font-weight: 500' }, row.name),
  },
  {
    // 曾用名：更名前的校名，搜索关键词也会命中它（简历上常写旧校名）
    title: t('pages.settings.SchoolLibrary.s49'),
    key: 'formerNames',
    width: 150,
    ellipsis: { tooltip: true },
    render: (row: School) => {
      const v = (row.formerNames || '').split('|').filter(Boolean).join('、');
      return v
        ? h('span', { style: 'color: var(--n-400, #909399)' }, v)
        : '-';
    },
  },
  {
    title: t('pages.settings.SchoolLibrary.s50'),
    key: 'educationLevel',
    width: 100,
    render: (row: School) => row.educationLevel ? h(NTag, { size: 'small', type: 'info' }, () => row.educationLevel) : '-',
  },
  {
    title: t('pages.settings.SchoolLibrary.s51'),
    key: 'schoolType',
    width: 100,
    render: (row: School) => row.schoolType ? h(NTag, { size: 'small', type: 'success' }, () => row.schoolType) : '-',
  },
  {
    title: t('pages.settings.SchoolLibrary.s52'),
    key: 'schoolCategory',
    width: 90,
    render: (row: School) => {
      const v = row.schoolCategory || '-';
      const color = NATURE_COLORS[v] || 'default';
      return h(NTag, { size: 'small', type: color }, () => v);
    },
  },
  { title: t('pages.settings.SchoolLibrary.s53'), key: 'province', width: 90 },
  { title: t('pages.settings.SchoolLibrary.s54'), key: 'city', width: 90 },
  {
    title: t('pages.settings.SchoolLibrary.s55'),
    key: 'affiliatedTo',
    width: 140,
    render: (row: School) => row.affiliatedTo || '-',
  },
  {
    title: t('pages.settings.SchoolLibrary.s56'),
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
  { title: t('pages.settings.SchoolLibrary.s57'), key: 'location', width: 200, ellipsis: { tooltip: true } },
  {
    title: t('pages.settings.SchoolLibrary.s58'),
    key: 'action',
    width: 140,
    fixed: 'right' as const,
    render: (row: School) =>
      h(NSpace, { size: 2, justify: 'center', wrap: false }, {
        default: () => [
          h(NButton, {
            size: 'tiny',
            quaternary: true,
            onClick: () => openDetail(row),
          }, { default: () => t('pages.settings.SchoolLibrary.s65'), icon: () => h(OpenOutline) }),
          h(NButton, {
            size: 'tiny',
            quaternary: true,
            type: 'primary',
            onClick: () => openEdit(row),
          }, { default: () => t('pages.settings.SchoolLibrary.s66'), icon: () => h(CreateOutline) }),
        ],
      }),
  },
];

/** 横向滚动宽度 = 各列宽之和。列宽改动自动跟随，避免字段被容器挤没。 */
const SCHOOL_TABLE_WIDTH = computed(() =>
  columns.reduce((sum: number, c: any) => sum + (c.width || 120), 0));

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
    message.error(t('pages.settings.SchoolLibrary.s67') + (e?.response?.data?.message || e.message));
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

// ===== 院校：详情抽屉 + 编辑弹窗 =====
const STATUS_OPTIONS = [
  { label: t('pages.settings.SchoolLibrary.s59'), value: 'ACTIVE' },
  { label: t('pages.settings.SchoolLibrary.s60'), value: 'INACTIVE' },
];

const detailVisible = ref(false);
const detailRow = ref<School | null>(null);
const editVisible = ref(false);
const editingId = ref<string | null>(null);
const saving = ref(false);
const editFormRef = ref<FormInst | null>(null);
const editForm = reactive<Record<string, any>>({
  name: '', code: '', educationLevel: null, schoolType: null, schoolCategory: null,
  province: null, city: '', affiliatedTo: '', location: '', status: 'ACTIVE',
});
const editTagList = ref<string[]>([]);
const formerNameList = ref<string[]>([]);

const editRules: FormRules = {
    name: { required: true, message: t('pages.settings.SchoolLibrary.s68'), trigger: 'blur' },
    code: { required: true, message: t('pages.settings.SchoolLibrary.s69'), trigger: 'blur' },
};

const tagListOf = (row: School | null) => (row?.tags || '').split('|').filter(Boolean);

function formatTime(v: string) {
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString('zh-CN');
}

function openDetail(row: School) {
  detailRow.value = row;
  detailVisible.value = true;
}

function openEdit(row: School) {
  editingId.value = row.id;
  Object.assign(editForm, {
    name: row.name,
    code: row.code,
    educationLevel: row.educationLevel ?? null,
    schoolType: row.schoolType ?? null,
    schoolCategory: row.schoolCategory ?? null,
    province: row.province ?? null,
    city: row.city ?? '',
    affiliatedTo: row.affiliatedTo ?? '',
    location: row.location ?? '',
    status: row.status ?? 'ACTIVE',
  });
  editTagList.value = tagListOf(row);
  formerNameList.value = (row.formerNames || '').split('|').filter(Boolean);
  detailVisible.value = false;
  editVisible.value = true;
}

function openCreate() {
  editingId.value = null;
  Object.assign(editForm, {
    name: '', code: '', educationLevel: null, schoolType: null, schoolCategory: null,
    province: null, city: '', affiliatedTo: '', location: '', status: 'ACTIVE',
  });
  editTagList.value = [];
  formerNameList.value = [];
  editVisible.value = true;
}

async function submitEdit() {
  try {
    await editFormRef.value?.validate();
  } catch {
    return; // 校验失败：错误已由表单就地展示
  }
  saving.value = true;
  try {
    const payload = {
      ...editForm,
      tags: editTagList.value.join('|'),
      formerNames: formerNameList.value.join('|'),
    };
    if (editingId.value) {
      await updateSchool(editingId.value, payload);
    } else {
      await createSchool(payload);
    }
    message.success(editingId.value ? t('pages.settings.SchoolLibrary.s70') : t('pages.settings.SchoolLibrary.s71'));
    editVisible.value = false;
    await Promise.all([reload(), loadSchoolFacets()]);
  } catch (e: any) {
    message.error(t('pages.settings.SchoolLibrary.s72') + (e?.response?.data?.message || e.message));
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  loadSchoolFacets();
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
.school-library { display: flex; flex-direction: column; gap: var(--space-3); }
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
