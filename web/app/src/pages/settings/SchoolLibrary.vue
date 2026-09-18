<template>
  <div class="page-container school-library">
    <div class="page-header">
      <h1 class="page-title">院校库</h1>
      <p class="page-subtitle">院校信息库 — 覆盖本专科院校，含双一流 / 985 / 211 / 双万计划等标签</p>
    </div>

<div class="page-body">
    <n-tabs v-model:value="activeTab" type="line" animated class="lib-tabs">
      <!-- ===== Tab 1: 院校 ===== -->
      <n-tab-pane name="schools" tab="院校">
        <div class="kpi-row">
          <div class="kpi-card"><span class="kpi-label">院校总数</span><span class="kpi-value">{{ rows.length }}</span></div>
        </div>

    <n-card>
      <template #header-extra>
        <n-space>
          <n-button :loading="loading" @click="reload">刷新</n-button>
          <n-button type="primary" @click="openCreate">新增院校</n-button>
        </n-space>
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
        :pagination="localPagination()"
        :row-key="(row: any) => row.id"
        :scroll-x="SCHOOL_TABLE_WIDTH"
        size="small"
        striped
      />
    </n-card>

        <!-- 院校详情抽屉 -->
        <n-drawer v-model:show="detailVisible" :width="560" placement="right">
          <n-drawer-content :title="detailRow?.name || '院校详情'" closable>
            <n-descriptions bordered :column="1" label-placement="left" size="small">
              <n-descriptions-item label="院校代码">{{ detailRow?.code || '-' }}</n-descriptions-item>
              <n-descriptions-item label="曾用名">
                {{ (detailRow?.formerNames || '').split('|').filter(Boolean).join('、') || '-' }}
              </n-descriptions-item>
              <n-descriptions-item label="教育层次">{{ detailRow?.educationLevel || '-' }}</n-descriptions-item>
              <n-descriptions-item label="院校类型">{{ detailRow?.schoolType || '-' }}</n-descriptions-item>
              <n-descriptions-item label="办学性质">{{ detailRow?.schoolCategory || '-' }}</n-descriptions-item>
              <n-descriptions-item label="地区">
                {{ [detailRow?.province, detailRow?.city].filter(Boolean).join(' / ') || '-' }}
              </n-descriptions-item>
              <n-descriptions-item label="主管部门">{{ detailRow?.affiliatedTo || '-' }}</n-descriptions-item>
              <n-descriptions-item label="详细地址">{{ detailRow?.location || '-' }}</n-descriptions-item>
              <n-descriptions-item label="院校标签">
                <n-space v-if="tagListOf(detailRow).length" :size="[4, 4]">
                  <n-tag v-for="t in tagListOf(detailRow)" :key="t" size="small" type="info">{{ t }}</n-tag>
                </n-space>
                <span v-else>-</span>
              </n-descriptions-item>
              <n-descriptions-item label="状态">{{ detailRow?.status || '-' }}</n-descriptions-item>
              <n-descriptions-item label="最后更新">{{ detailRow?.updatedAt ? formatTime(detailRow.updatedAt) : '-' }}</n-descriptions-item>
              <n-descriptions-item label="人工维护">
                {{ detailRow?.isCustomized ? '是（导入不会覆盖）' : '否（导入会覆盖）' }}
              </n-descriptions-item>
            </n-descriptions>
            <template #footer>
              <n-space>
                <n-button @click="detailVisible = false">关闭</n-button>
                <n-button type="primary" @click="openEdit(detailRow!)">编辑</n-button>
              </n-space>
            </template>
          </n-drawer-content>
        </n-drawer>

        <!-- 院校编辑 / 新增弹窗 -->
        <n-modal
          v-model:show="editVisible"
          preset="card"
          :title="editingId ? '编辑院校' : '新增院校'"
          style="width: 680px"
          :mask-closable="false"
        >
          <n-form ref="editFormRef" :model="editForm" :rules="editRules" label-placement="left" label-width="96">
            <n-form-item label="院校名称" path="name">
              <n-input v-model:value="editForm.name" placeholder="必填" maxlength="200" />
            </n-form-item>
            <n-form-item label="院校代码" path="code">
              <n-input v-model:value="editForm.code" placeholder="必填，唯一" maxlength="50" />
            </n-form-item>
            <n-form-item label="曾用名">
              <n-dynamic-tags v-model:value="formerNameList" />
            </n-form-item>
            <n-form-item label="教育层次">
              <n-select v-model:value="editForm.educationLevel" :options="schoolEduOptions" clearable filterable
                tag placeholder="可输入自定义值" />
            </n-form-item>
            <n-form-item label="院校类型">
              <n-select v-model:value="editForm.schoolType" :options="schoolTypeOptions" clearable filterable
                tag placeholder="可输入自定义值" />
            </n-form-item>
            <n-form-item label="办学性质">
              <n-select v-model:value="editForm.schoolCategory" :options="schoolCategoryOptions" clearable
                tag placeholder="如 公办 / 民办" />
            </n-form-item>
            <n-form-item label="地区">
              <n-space :wrap="false">
                <n-select v-model:value="editForm.province" :options="schoolProvinceOptions" clearable filterable
                  tag placeholder="省份" style="width: 150px" />
                <n-input v-model:value="editForm.city" placeholder="城市" style="width: 150px" />
              </n-space>
            </n-form-item>
            <n-form-item label="主管部门">
              <n-input v-model:value="editForm.affiliatedTo" maxlength="100" />
            </n-form-item>
            <n-form-item label="详细地址">
              <n-input v-model:value="editForm.location" maxlength="200" />
            </n-form-item>
            <n-form-item label="院校标签">
              <n-dynamic-tags v-model:value="editTagList" />
            </n-form-item>
            <n-form-item label="状态">
              <n-select v-model:value="editForm.status" :options="STATUS_OPTIONS" />
            </n-form-item>
          </n-form>
          <template #footer>
            <n-space justify="end">
              <n-button :disabled="saving" @click="editVisible = false">取消</n-button>
              <n-button type="primary" :loading="saving" :disabled="saving" @click="submitEdit">保存</n-button>
            </n-space>
          </template>
        </n-modal>
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
            :pagination="localPagination()"
            :row-key="(row: any) => row.id"
            :scroll-x="MAJOR_TABLE_WIDTH"
            size="small"
            striped
          />
        </n-card>

        <!-- 专业详情抽屉（专业介绍全文 + 阳光高考链接） -->
        <n-drawer v-model:show="majorDetailVisible" :width="560" placement="right">
          <n-drawer-content :title="majorDetailRow?.name || '专业详情'" closable>
            <n-descriptions bordered :column="1" label-placement="left" size="small">
              <n-descriptions-item label="专业代码">{{ majorDetailRow?.code || '-' }}</n-descriptions-item>
              <n-descriptions-item label="门类">{{ majorDetailRow?.discipline || '-' }}</n-descriptions-item>
              <n-descriptions-item label="专业类">{{ majorDetailRow?.category || '-' }}</n-descriptions-item>
              <n-descriptions-item label="学历层次">{{ majorDetailRow?.educationLevel || '-' }}</n-descriptions-item>
              <n-descriptions-item label="数据年份">{{ majorDetailRow?.dataYear || '-' }}</n-descriptions-item>
              <n-descriptions-item label="人工维护">
                {{ majorDetailRow?.isCustomized ? '是（导入不会覆盖）' : '否（导入会覆盖）' }}
              </n-descriptions-item>
              <n-descriptions-item label="专业介绍">
                <div style="white-space: pre-wrap; line-height: 1.6">{{ majorDetailRow?.intro || '-' }}</div>
              </n-descriptions-item>
            </n-descriptions>
            <template #footer>
              <n-space>
                <n-button @click="majorDetailVisible = false">关闭</n-button>
                <n-button
                  v-if="majorDetailRow?.detailUrl"
                  tag="a"
                  :href="majorDetailRow.detailUrl"
                  target="_blank"
                  rel="noopener"
                >
                  阳光高考原文
                </n-button>
                <n-button type="primary" @click="openMajorEdit(majorDetailRow!)">编辑</n-button>
              </n-space>
            </template>
          </n-drawer-content>
        </n-drawer>

        <!-- 专业编辑弹窗 -->
        <n-modal
          v-model:show="majorEditVisible"
          preset="card"
          title="编辑专业"
          style="width: 640px"
          :mask-closable="false"
        >
          <n-form :model="majorEditForm" label-placement="left" label-width="96">
            <n-form-item label="专业名称"><n-input v-model:value="majorEditForm.name" /></n-form-item>
            <n-form-item label="专业代码"><n-input v-model:value="majorEditForm.code" /></n-form-item>
            <n-form-item label="门类"><n-input v-model:value="majorEditForm.discipline" /></n-form-item>
            <n-form-item label="专业类"><n-input v-model:value="majorEditForm.category" /></n-form-item>
            <n-form-item label="学历层次"><n-input v-model:value="majorEditForm.educationLevel" /></n-form-item>
            <n-form-item label="数据年份"><n-input v-model:value="majorEditForm.dataYear" /></n-form-item>
            <n-form-item label="详情 URL"><n-input v-model:value="majorEditForm.detailUrl" /></n-form-item>
            <n-form-item label="专业介绍">
              <n-input v-model:value="majorEditForm.intro" type="textarea" :rows="6" />
            </n-form-item>
          </n-form>
          <template #footer>
            <n-space justify="end">
              <n-button :disabled="majorSaving" @click="majorEditVisible = false">取消</n-button>
              <n-button type="primary" :loading="majorSaving" :disabled="majorSaving" @click="submitMajorEdit">
                保存
              </n-button>
            </n-space>
          </template>
        </n-modal>
      </n-tab-pane>
    </n-tabs>
    </div><!-- /.page-body -->
</div>
</template>

<script setup lang="ts">
import { ref, h, onMounted, reactive, computed } from 'vue';
import { NTag, NButton, NSpace, useMessage, type FormInst, type FormRules } from 'naive-ui';
import { SchoolOutline, OpenOutline, SearchOutline, CreateOutline } from '@vicons/ionicons5';
import {
  searchSchools, getSchoolFacets, type School, type SchoolFacets,
  createSchool, updateSchool,
  searchMajors, getMajorFacets, type Major, updateMajor,
} from '@/api/library';
import { localPagination } from '@/composables/useTablePagination';

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
  {
    title: '院校名称',
    key: 'name',
    width: 200,
    render: (row: School) => h('span', { style: 'font-weight: 500' }, row.name),
  },
  {
    // 曾用名：更名前的校名，搜索关键词也会命中它（简历上常写旧校名）
    title: '曾用名',
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
    width: 140,
    fixed: 'right' as const,
    render: (row: School) =>
      h(NSpace, { size: 2, justify: 'center', wrap: false }, {
        default: () => [
          h(NButton, {
            size: 'tiny',
            quaternary: true,
            onClick: () => openDetail(row),
          }, { default: () => '查看', icon: () => h(OpenOutline) }),
          h(NButton, {
            size: 'tiny',
            quaternary: true,
            type: 'primary',
            onClick: () => openEdit(row),
          }, { default: () => '编辑', icon: () => h(CreateOutline) }),
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

// ===== 院校：详情抽屉 + 编辑弹窗 =====
const STATUS_OPTIONS = [
  { label: '启用', value: 'ACTIVE' },
  { label: '停用', value: 'INACTIVE' },
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
  name: { required: true, message: '请填写院校名称', trigger: 'blur' },
  code: { required: true, message: '请填写院校代码', trigger: 'blur' },
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
    message.success(editingId.value ? '已保存院校信息' : '已新增院校');
    editVisible.value = false;
    await Promise.all([reload(), loadSchoolFacets()]);
  } catch (e: any) {
    message.error('保存失败: ' + (e?.response?.data?.message || e.message));
  } finally {
    saving.value = false;
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
    title: '专业介绍', key: 'intro', width: 320, ellipsis: { tooltip: true },
    render: (row: Major) => row.intro || '-',
  },
  {
    title: '操作', key: 'action', width: 140, fixed: 'right' as const,
    render: (row: Major) =>
      h(NSpace, { size: 2, justify: 'center', wrap: false }, {
        default: () => [
          h(NButton, {
            size: 'tiny', quaternary: true,
            onClick: () => openMajorDetail(row),
          }, { default: () => '查看', icon: () => h(OpenOutline) }),
          h(NButton, {
            size: 'tiny', quaternary: true, type: 'primary',
            onClick: () => openMajorEdit(row),
          }, { default: () => '编辑', icon: () => h(CreateOutline) }),
        ],
      }),
  },
];

/** 横向滚动宽度 = 各列宽之和（同院校表） */
const MAJOR_TABLE_WIDTH = computed(() =>
  majorColumns.reduce((sum: number, c: any) => sum + (c.width || 120), 0));

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

// ===== 专业：详情抽屉 + 编辑弹窗 =====
const majorDetailVisible = ref(false);
const majorDetailRow = ref<Major | null>(null);
const majorEditVisible = ref(false);
const majorSaving = ref(false);
const majorEditForm = reactive<Record<string, any>>({
  name: '', code: '', discipline: '', category: '',
  educationLevel: '', dataYear: '', detailUrl: '', intro: '',
});

function openMajorDetail(row: Major) {
  majorDetailRow.value = row;
  majorDetailVisible.value = true;
}

function openMajorEdit(row: Major) {
  Object.assign(majorEditForm, {
    name: row.name ?? '',
    code: row.code ?? '',
    discipline: row.discipline ?? '',
    category: row.category ?? '',
    educationLevel: row.educationLevel ?? '',
    dataYear: row.dataYear ?? '',
    detailUrl: row.detailUrl ?? '',
    intro: row.intro ?? '',
  });
  majorDetailRow.value = row;
  majorDetailVisible.value = false;
  majorEditVisible.value = true;
}

async function submitMajorEdit() {
  const row = majorDetailRow.value;
  if (!row) return;
  majorSaving.value = true;
  try {
    await updateMajor(row.id, { ...majorEditForm });
    message.success('已保存专业信息');
    majorEditVisible.value = false;
    await loadMajors();
  } catch (e: any) {
    message.error('保存失败: ' + (e?.response?.data?.message || e.message));
  } finally {
    majorSaving.value = false;
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
