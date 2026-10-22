<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.JobLevelManagement.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.JobLevelManagement.s2') }}</p>
      </div>
    </div>

    <div class="data-body">
      <div class="glass-panel panel-shell">
        <div class="toolbar">
          <n-input
            v-model:value="searchKeyword"
            :placeholder="t('pages.settings.JobLevelManagement.s6')"
            class="rule-filter-search"
            clearable
            @clear="searchKeyword = ''"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
          <n-select
            v-model:value="statusFilter"
            :options="statusOptions"
            class="rule-filter-select"
          />
          <div class="spacer"></div>
          <n-button quaternary @click="loadJobLevels">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            {{ t('pages.settings.JobLevelManagement.s7') }}
          </n-button>
          <!-- 导出按钮可见性受 recruit:settings:job_level:export 授权（CSV 为客户端导出，无后端端点） -->
          <n-button
            v-permission="'recruit:settings:job_level:export'"
            quaternary
            @click="exportJobLevels"
          >
            <template #icon><n-icon :component="DownloadOutline" /></template>
            {{ t('pages.settings.JobLevelManagement.s8') }}
          </n-button>
          <n-button quaternary @click="handleImportStub">
            <template #icon><n-icon :component="CloudUploadOutline" /></template>
            {{ t('pages.settings.JobLevelManagement.s10') }}
          </n-button>
          <n-button quaternary @click="showCategoryModal = true">
            <template #icon><n-icon :component="LayersOutline" /></template>
            {{ t('pages.settings.JobLevelManagement.s11') }}
          </n-button>
          <n-button quaternary @click="showGradeModal = true">
            <template #icon><n-icon :component="OptionsOutline" /></template>
            {{ t('pages.settings.JobLevelManagement.s12') }}
          </n-button>
          <n-button quaternary @click="showSequenceModal = true">
            <template #icon><n-icon :component="GitBranchOutline" /></template>
            {{ t('pages.settings.JobLevelManagement.s13') }}
          </n-button>
          <n-button type="primary" class="gradient-btn" @click="openCreateModal">
            <template #icon><n-icon :component="AddOutline" /></template>
            {{ t('pages.settings.JobLevelManagement.s9') }}
          </n-button>
        </div>
        <div class="table-wrap">
          <n-data-table
            :data="displayData"
            :columns="columns"
            :row-key="(row: JobLevel) => row.id"
            :loading="loading"
            :pagination="pagination"
            size="medium"
            flex-height
          />
        </div>
      </div>
    </div>

    <!-- 新增 / 编辑职级弹窗（类别下拉来自职级类别；职等受全局上限约束） -->
    <n-modal
      v-model:show="modalVisible"
      preset="card"
      :title="modalTitle"
      :style="{ width: '640px' }"
      :mask-closable="false"
      :centered="true"
      :auto-focus="false"
    >
      <n-form :model="formState" label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item :label="t('pages.settings.JobLevelManagement.s15')" required>
              <n-input
                v-model:value="formState.name"
                :placeholder="t('pages.settings.JobLevelManagement.s28')"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item :label="t('pages.settings.JobLevelManagement.s16')" required>
              <n-select
                v-model:value="formState.category"
                :options="categoryOptions"
                :placeholder="t('pages.settings.JobLevelManagement.s29')"
                filterable
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item :label="t('pages.settings.JobLevelManagement.s17')" required>
              <n-input-number
                v-model:value="formState.grade"
                :min="1"
                :max="jobLevelMaxGrade"
                style="width: 100%"
                :placeholder="t('pages.settings.JobLevelManagement.s30')"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item :label="t('pages.settings.JobLevelManagement.s18')">
              <n-input-number
                v-model:value="formState.sortOrder"
                :min="0"
                :max="9999"
                style="width: 100%"
                :placeholder="t('pages.settings.JobLevelManagement.s31')"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-form-item :label="t('pages.settings.JobLevelManagement.s19')">
          <n-input
            v-model:value="formState.remark"
            type="textarea"
            :rows="3"
            :placeholder="t('pages.settings.JobLevelManagement.s32')"
          />
        </n-form-item>
      </n-form>

      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button text @click="modalVisible = false">{{ t('pages.settings.JobLevelManagement.s26') }}</n-button>
          <n-button type="primary" class="gradient-btn" :loading="submitting" @click="handleSubmit">
            {{ t('pages.settings.JobLevelManagement.s33') }}
          </n-button>
        </div>
      </template>
    </n-modal>

    <!-- 三个子配置弹窗（管理类别 / 职等上限 / 职级序列），受 v-model:show 控制 -->
    <JobLevelCategoryModal v-model:show="showCategoryModal" @saved="loadCategories" />
    <JobLevelGradeModal v-model:show="showGradeModal" />
    <JobLevelSequenceModal v-model:show="showSequenceModal" />
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, computed, onMounted, watch, h } from 'vue';
import {
  AddOutline,
  CreateOutline,
  PowerOutline,
  RefreshOutline,
  SearchOutline,
  DownloadOutline,
  CloudUploadOutline,
  LayersOutline,
  OptionsOutline,
  GitBranchOutline,
} from '@vicons/ionicons5';
import {
  NTag,
  NButton,
  NSpace,
  NIcon,
  NPopconfirm,
  NInput,
  NModal,
  NForm,
  NGrid,
  NGridItem,
  NFormItem,
  NSelect,
  NInputNumber,
  NRadioGroup,
  NRadio,
  NRadioButton,
  useMessage,
} from 'naive-ui';
import JobLevelCategoryModal from './components/JobLevelCategoryModal.vue';
import JobLevelGradeModal from './components/JobLevelGradeModal.vue';
import JobLevelSequenceModal from './components/JobLevelSequenceModal.vue';
import { localPagination } from '../../composables/useTablePagination';
// 列对齐与操作列规格的单一真源（四档规则见 useTableColumns.ts 头）
import { column, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns';
import {
  listJobLevels,
  createJobLevel,
  updateJobLevel,
  setJobLevelEnabled,
  listJobLevelCategories,
  getJobLevelGradeSetting,
} from '../../api/job-level';
import type { JobLevel, JobLevelCategory } from '../../api/job-level';

const { t } = useI18n()

const message = useMessage();

// ===== 状态 =====
const jobLevels = ref<JobLevel[]>([]);
const categories = ref<JobLevelCategory[]>([]);
const loading = ref(false);
const submitting = ref(false);
const jobLevelMaxGrade = ref(999);

// 分页：唯一真源 useTablePagination（默认 20，可切 10/20/50/100），禁手写 pageSize
const pagination = localPagination();

// 启用/停用筛选：ALL=全部 / ACTIVE=启用中 / INACTIVE=停用
const statusFilter = ref<'ALL' | 'ACTIVE' | 'INACTIVE'>('ALL');
// 状态筛选下拉项（与身份管理 RolesTab 的 n-select 筛选同构；复用原 i18n key）
const statusOptions = computed(() => [
  { label: t('pages.settings.JobLevelManagement.s3'), value: 'ALL' as const },
  { label: t('pages.settings.JobLevelManagement.s4'), value: 'ACTIVE' as const },
  { label: t('pages.settings.JobLevelManagement.s5'), value: 'INACTIVE' as const },
]);
watch(statusFilter, () => loadJobLevels());

// 搜索（名称，客户端过滤，输入即筛）
const searchKeyword = ref('');

const displayData = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase();
  let list = jobLevels.value;
  if (keyword) {
    list = list.filter((item) => (item.name || '').toLowerCase().includes(keyword));
  }
  return list;
});

// ===== 数据加载 =====
const loadJobLevels = async () => {
  loading.value = true;
  try {
    const isEnabled =
      statusFilter.value === 'ACTIVE' ? true : statusFilter.value === 'INACTIVE' ? false : undefined;
    jobLevels.value = await listJobLevels({ isEnabled });
  } catch (error) {
    console.error(t('pages.settings.JobLevelManagement.s43'), error);
    message.error(t('pages.settings.JobLevelManagement.s43'));
  } finally {
    loading.value = false;
  }
};

const loadCategories = async () => {
  try {
    categories.value = await listJobLevelCategories({ pageSize: 500 });
  } catch (error) {
    console.error(t('pages.settings.JobLevelManagement.s55'), error);
    message.error(t('pages.settings.JobLevelManagement.s55'));
  }
};

const loadGradeSetting = async () => {
  try {
    const setting = await getJobLevelGradeSetting();
    jobLevelMaxGrade.value = setting.maxGrade || 999;
  } catch (error) {
    console.error(t('pages.settings.JobLevelManagement.s66'), error);
  }
};

// ===== 类别解析（兼容「对象 {id,name}」与「裸 id」两种响应形态）=====
const categoryLabelMap = computed(() => {
  const map = new Map<string, string>();
  for (const item of categories.value) map.set(item.id, item.name || '');
  return map;
});

const resolveCategoryId = (raw: any): string | null => {
  if (raw == null) return null;
  if (typeof raw === 'object') return raw.id ? String(raw.id) : null;
  return String(raw);
};

const resolveCategoryLabel = (raw: any): string => {
  if (raw == null) return '';
  if (typeof raw === 'object') {
    const label = raw.name ?? raw.value ?? raw.label;
    if (label) return String(label);
    return raw.id ? categoryLabelMap.value.get(String(raw.id)) ?? '' : '';
  }
  return categoryLabelMap.value.get(String(raw)) ?? '';
};

/** 当前值不在可选项里（如类别已停用）时补一个回显项，避免下拉框展示裸 id。 */
const withFallbackOption = (
  options: { label: string; value: string }[],
  value: string | undefined,
): { label: string; value: string }[] => {
  if (!value || options.some((opt) => opt.value === value)) return options;
  return [...options, { label: resolveCategoryLabel(value) || value, value }];
};

const categoryOptions = computed(() => {
  const options = categories.value
    .filter((it) => it.isEnabled !== false && it.status !== 'INACTIVE')
    .map((it) => ({ label: it.name || '', value: it.id }));
  return withFallbackOption(options, formState.category);
});

// ===== 导入入口（仅提示「即将上线」，不实现逻辑，Q4 决策）=====
const handleImportStub = () => {
  message.info(t('pages.settings.JobLevelManagement.s14'));
};

// ===== 弹窗（新增 / 编辑职级）=====
const modalVisible = ref(false);
const editingId = ref<string | null>(null);

const modalTitle = computed(() =>
  editingId.value
    ? t('pages.settings.JobLevelManagement.s27')
    : t('pages.settings.JobLevelManagement.s9'),
);

const formState = reactive({
  name: '',
  category: undefined as string | undefined,
  grade: 1,
  sortOrder: 0,
  remark: '',
});

const openCreateModal = () => {
  editingId.value = null;
  Object.assign(formState, {
    name: '',
    category: undefined,
    grade: 1,
    sortOrder: 0,
    remark: '',
  });
  modalVisible.value = true;
};

const startEdit = (record: JobLevel) => {
  editingId.value = record.id;
  Object.assign(formState, {
    name: record.name || '',
    category: resolveCategoryId(record.category) ?? undefined,
    grade: record.grade ?? 1,
    sortOrder: record.sortOrder ?? 0,
    remark: record.remark || '',
  });
  modalVisible.value = true;
};

// 从 envelope / DRF 错误结构中提取第一条可读错误信息
const extractErrorMessage = (error: any): string => {
  const data = error?.response?.data;
  if (!data) return '';
  if (data.errors && typeof data.errors === 'object') {
    for (const key of Object.keys(data.errors)) {
      const val = data.errors[key];
      if (Array.isArray(val) && val.length) return `${key}: ${val[0]}`;
      if (typeof val === 'string') return `${key}: ${val}`;
    }
  }
  return data.error || data.message || data.detail || '';
};

const handleSubmit = async () => {
  if (!formState.name.trim()) {
    message.error(t('pages.settings.JobLevelManagement.s34'));
    return;
  }
  if (!formState.category) {
    message.error(t('pages.settings.JobLevelManagement.s35'));
    return;
  }
  if (formState.grade == null || formState.grade < 1) {
    message.error(t('pages.settings.JobLevelManagement.s36'));
    return;
  }
  if (formState.grade > jobLevelMaxGrade.value) {
    message.error(t('pages.settings.JobLevelManagement.s37', { max: jobLevelMaxGrade.value }));
    return;
  }
  submitting.value = true;
  try {
    const payload = {
      name: formState.name.trim(),
      category: formState.category,
      grade: Number(formState.grade),
      sortOrder: Number.isFinite(formState.sortOrder) ? Number(formState.sortOrder) : 0,
      remark: formState.remark || '',
    };
    if (editingId.value) {
      await updateJobLevel(editingId.value, payload);
      message.success(t('pages.settings.JobLevelManagement.s39'));
    } else {
      await createJobLevel(payload);
      message.success(t('pages.settings.JobLevelManagement.s38'));
    }
    modalVisible.value = false;
    loadJobLevels();
  } catch (error: any) {
    message.error(
      extractErrorMessage(error) ||
        (editingId.value
          ? t('pages.settings.JobLevelManagement.s41')
          : t('pages.settings.JobLevelManagement.s40')),
    );
  } finally {
    submitting.value = false;
  }
};

// ===== 启停（is_enabled 软停：仅提示不硬阻止）=====
const isRowEnabled = (row: JobLevel): boolean => {
  if (row.status) return row.status !== 'INACTIVE';
  return row.isEnabled !== false;
};

const handleToggleEnabled = async (row: JobLevel) => {
  const next = !isRowEnabled(row);
  try {
    await setJobLevelEnabled(row.id, next);
    message.success(
      next
        ? t('pages.settings.JobLevelManagement.s45')
        : t('pages.settings.JobLevelManagement.s44'),
    );
    loadJobLevels();
  } catch (error: any) {
    message.error(extractErrorMessage(error) || t('pages.settings.JobLevelManagement.s42'));
  }
};

// ===== 表格列 =====
const renderActions = (row: JobLevel) => {
  const enabled = isRowEnabled(row);
  return h(NSpace, { size: 8, wrap: false }, {
    default: () => [
      h(
        NButton,
        {
          quaternary: true,
          type: 'primary',
          size: OP_ACTION_BUTTON_SIZE,
          onClick: () => startEdit(row),
        },
        {
          default: () => t('pages.settings.JobLevelManagement.s21'),
          icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
        },
      ),
      enabled
        ? h(
            NPopconfirm,
            {
              onPositiveClick: () => handleToggleEnabled(row),
              positiveText: t('pages.settings.JobLevelManagement.s25'),
              negativeText: t('pages.settings.JobLevelManagement.s26'),
            },
            {
              default: () => t('pages.settings.JobLevelManagement.s24'),
              trigger: () =>
                h(
                  NButton,
                  { quaternary: true, type: 'warning', size: OP_ACTION_BUTTON_SIZE },
                  {
                    default: () => t('pages.settings.JobLevelManagement.s22'),
                    icon: () => h(NIcon, null, { default: () => h(PowerOutline) }),
                  },
                ),
            },
          )
        : h(
            NButton,
            {
              quaternary: true,
              type: 'primary',
              size: OP_ACTION_BUTTON_SIZE,
              onClick: () => handleToggleEnabled(row),
            },
            {
              default: () => t('pages.settings.JobLevelManagement.s23'),
              icon: () => h(NIcon, null, { default: () => h(PowerOutline) }),
            },
          ),
    ],
  });
};

const columns = computed(() => [
  column({
    title: t('pages.settings.JobLevelManagement.s15'),
    key: 'name',
    width: 200,
    render: (row: JobLevel) =>
      h('span', { style: 'font-weight: 500; color: var(--ink)' }, row.name || '—'),
  }, 'short'),
  column({
    title: t('pages.settings.JobLevelManagement.s16'),
    key: 'category',
    width: 160,
    render: (row: JobLevel) =>
      h('span', {}, row.categoryName || resolveCategoryLabel(row.category) || '—'),
  }, 'short'),
  column({
    title: t('pages.settings.JobLevelManagement.s17'),
    key: 'grade',
    width: 100,
    render: (row: JobLevel) => h('span', {}, String(row.grade ?? '—')),
  }, 'numeric'),
  column({
    title: t('pages.settings.JobLevelManagement.s18'),
    key: 'sortOrder',
    width: 110,
    render: (row: JobLevel) => h('span', {}, String(row.sortOrder ?? '—')),
  }, 'numeric'),
  column({
    // 备注为长文本/描述，按四档规则 D 档强制左对齐（不居中），保留 ellipsis
    title: t('pages.settings.JobLevelManagement.s19'),
    key: 'remark',
    width: 200,
    ellipsis: { tooltip: true },
    render: (row: JobLevel) => h('span', {}, row.remark || '—'),
  }, 'text'),
  column({
    title: t('pages.settings.JobLevelManagement.s49'),
    key: 'status',
    width: 100,
    render: (row: JobLevel) => {
      const enabled = isRowEnabled(row);
      return h(
        NTag,
        { type: enabled ? 'success' : 'default', size: 'small', bordered: false },
        {
          default: () => (enabled
            ? t('pages.settings.JobLevelManagement.s4')
            : t('pages.settings.JobLevelManagement.s5')),
        },
      );
    },
  }, 'short'),
  column({
    // 行内操作：编辑 type=primary、启停 type=warning/primary（语义色保留，不单色化）；
    // 本页无删除按钮。NSpace wrap:false，size 取 OP_ACTION_BUTTON_SIZE。
    title: t('pages.settings.JobLevelManagement.s20'),
    key: 'actions',
    width: 160,
    fixed: 'right' as const,
    render: (row: JobLevel) => renderActions(row),
  }, 'control'),
]);

/* ============================ CSV 导出（utf-8-sig BOM，Excel 友好）============================ */

const EXPORT_HEADERS = [
  'pages.settings.JobLevelManagement.s15',
  'pages.settings.JobLevelManagement.s16',
  'pages.settings.JobLevelManagement.s17',
  'pages.settings.JobLevelManagement.s49',
];

// CSV 字段转义：含逗号/引号/换行则包裹双引号并转义内部引号
const csvEscape = (v: string | number): string => {
  const s = v == null ? '' : String(v);
  if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
};

// 触发浏览器下载
const triggerDownload = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

const exportJobLevels = async () => {
  let all: JobLevel[] = [];
  try {
    all = await listJobLevels({ pageSize: 1000 });
  } catch (error) {
    console.error(t('pages.settings.JobLevelManagement.s43'), error);
    message.error(t('pages.settings.JobLevelManagement.s43'));
    return;
  }
  if (!all.length) {
    message.warning(t('pages.settings.JobLevelManagement.s46'));
    return;
  }
  const activeLabel = t('pages.settings.JobLevelManagement.s4');
  const inactiveLabel = t('pages.settings.JobLevelManagement.s5');
  const rows = all.map((row) => [
    row.name || '',
    row.categoryName || resolveCategoryLabel(row.category),
    String(row.grade ?? ''),
    isRowEnabled(row) ? activeLabel : inactiveLabel,
  ]);
  const headerLine = EXPORT_HEADERS.map((key) => csvEscape(t(key))).join(',');
  const lines = [headerLine, ...rows.map((r) => r.map(csvEscape).join(','))];
  const content = '\uFEFF' + lines.join('\r\n');
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
  const fileName = `${t('pages.settings.JobLevelManagement.s48')}_${new Date().toISOString().slice(0, 10)}.csv`;
  triggerDownload(blob, fileName);
  message.success(t('pages.settings.JobLevelManagement.s47', { n: all.length }));
};

// 三个子配置弹窗的显隐
const showCategoryModal = ref(false);
const showGradeModal = ref(false);
const showSequenceModal = ref(false);

onMounted(() => {
  loadJobLevels();
  loadCategories();
  loadGradeSetting();
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
.data-body {
  flex: 1;
  min-height: 0;
  overflow-y: hidden;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
/* .glass-panel 已是全局类（glass.css §4）；panel-shell 让面板撑满 page-body，
 * 内部 .toolbar + .table-wrap(flex-height) 与身份管理 RolesTab 同构（2026-10-15 兵哥：页面结构统一） */
/* 搜索框宽度与身份管理工具条一致（RolesTab scoped 同款覆盖全局 200px） */
</style>
