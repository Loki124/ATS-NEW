<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.PositionTitleManagement.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.PositionTitleManagement.s2') }}</p>
      </div>
    </div>

    <div class="page-body">
      <div class="glass-panel panel-shell">
        <div class="toolbar">
          <n-input
            v-model:value="searchKeyword"
            :placeholder="t('pages.settings.PositionTitleManagement.s6')"
            class="rule-filter-search"
            clearable
            @clear="searchKeyword = ''"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
          <n-radio-group v-model:value="statusFilter" size="small">
            <n-radio-button value="ALL">{{ t('pages.settings.PositionTitleManagement.s3') }}</n-radio-button>
            <n-radio-button value="ACTIVE">{{ t('pages.settings.PositionTitleManagement.s4') }}</n-radio-button>
            <n-radio-button value="INACTIVE">{{ t('pages.settings.PositionTitleManagement.s5') }}</n-radio-button>
          </n-radio-group>
          <div class="spacer"></div>
          <n-button quaternary @click="loadJobTitles">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            {{ t('pages.settings.PositionTitleManagement.s7') }}
          </n-button>
          <!-- 导出按钮可见性受 recruit:settings:job_title:export 授权（CSV 为客户端导出，无后端端点） -->
          <n-button
            v-permission="'recruit:settings:job_title:export'"
            quaternary
            @click="exportJobTitles"
          >
            <template #icon><n-icon :component="DownloadOutline" /></template>
            {{ t('pages.settings.PositionTitleManagement.s8') }}
          </n-button>
          <n-button type="primary" class="gradient-btn" @click="openCreateModal">
            <template #icon><n-icon :component="AddOutline" /></template>
            {{ t('pages.settings.PositionTitleManagement.s9') }}
          </n-button>
        </div>
        <div class="table-wrap">
          <n-data-table
            :data="displayData"
            :columns="columns"
            :row-key="(row: JobTitle) => row.id"
            :loading="loading"
            :pagination="pagination"
            size="medium"
            flex-height
          />
        </div>
      </div>
    </div>

    <!-- 新增 / 编辑职务弹窗（职位族三级级联 + 职责说明富文本） -->
    <n-modal
      v-model:show="modalVisible"
      preset="card"
      :title="modalTitle"
      :style="{ width: '720px' }"
      :mask-closable="false"
      :centered="true"
      :auto-focus="false"
    >
      <n-form :model="formState" label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item :label="t('pages.settings.PositionTitleManagement.s10')" required>
              <n-input
                v-model:value="formState.name"
                :placeholder="t('pages.settings.PositionTitleManagement.s23')"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item :label="t('pages.settings.PositionTitleManagement.s11')" required>
              <n-select
                v-model:value="formState.jobFamily"
                :options="jobFamilyOptions"
                :placeholder="t('pages.settings.PositionTitleManagement.s24')"
                filterable
                @update:value="onJobFamilyChange"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item :label="t('pages.settings.PositionTitleManagement.s25')">
              <n-select
                v-model:value="formState.jobCategory"
                :options="jobCategoryOptions"
                :placeholder="t('pages.settings.PositionTitleManagement.s26')"
                filterable
                clearable
                :disabled="!formState.jobFamily"
                @update:value="onJobCategoryChange"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item :label="t('pages.settings.PositionTitleManagement.s27')">
              <n-select
                v-model:value="formState.jobSubcategory"
                :options="jobSubcategoryOptions"
                :placeholder="t('pages.settings.PositionTitleManagement.s28')"
                filterable
                clearable
                :disabled="!formState.jobCategory"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item :label="t('pages.settings.PositionTitleManagement.s12')" required>
              <n-select
                v-model:value="formState.isKeyPosition"
                :options="yesNoOptions"
                :placeholder="t('pages.settings.PositionTitleManagement.s29')"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item :label="t('pages.settings.PositionTitleManagement.s32')">
              <n-select
                v-model:value="formState.isManagement"
                :options="yesNoOptions"
                :placeholder="t('pages.settings.PositionTitleManagement.s33')"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item :label="t('pages.settings.PositionTitleManagement.s34')">
              <n-select
                v-model:value="formState.jobLevelTier"
                :options="jobLevelTierOptions"
                :placeholder="t('pages.settings.PositionTitleManagement.s35')"
                clearable
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item :label="t('pages.settings.PositionTitleManagement.s40')">
              <n-input-number
                v-model:value="formState.sortOrder"
                :min="0"
                :max="9999"
                style="width: 100%"
                :placeholder="t('pages.settings.PositionTitleManagement.s41')"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <n-form-item :label="t('pages.settings.PositionTitleManagement.s30')">
          <rich-editor
            v-model:html="formState.responsibility"
            :placeholder="t('pages.settings.PositionTitleManagement.s31')"
            height="200px"
          />
        </n-form-item>
      </n-form>

      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button text @click="modalVisible = false">{{ t('pages.settings.PositionTitleManagement.s21') }}</n-button>
          <n-button type="primary" class="gradient-btn" :loading="submitting" @click="handleSubmit">
            {{ t('pages.settings.PositionTitleManagement.s42') }}
          </n-button>
        </div>
      </template>
    </n-modal>
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
import RichEditor from '../../components/RichEditor.vue';
import { localPagination } from '../../composables/useTablePagination';
// 列对齐与操作列规格的单一真源（四档规则见 useTableColumns.ts 头）
import { column, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns';
import {
  listPositionDictionaryItems,
  listJobTitles,
  createJobTitle,
  updateJobTitle,
  setJobTitleEnabled,
} from '../../api/job-title';
import type { JobTitle, PositionDictionaryItem } from '../../api/job-title';

const { t } = useI18n()

const message = useMessage();

/** 岗位层级内置枚举（Q7：本期内置 CharField，P1 字典化；取稳定 ASCII 码落库）。 */
const JOB_LEVEL_TIER_ENUM: { value: string; labelKey: string }[] = [
  { value: 'JUNIOR', labelKey: 'pages.settings.PositionTitleManagement.s36' },
  { value: 'INTERMEDIATE', labelKey: 'pages.settings.PositionTitleManagement.s37' },
  { value: 'SENIOR', labelKey: 'pages.settings.PositionTitleManagement.s38' },
  { value: 'EXPERT', labelKey: 'pages.settings.PositionTitleManagement.s39' },
];

/** 职位族三级字典（POSITION_FAMILY / POSITION_CATEGORY / POSITION_SUBCATEGORY）。 */
interface PositionDictionaryGroup {
  family: PositionDictionaryItem[];
  category: PositionDictionaryItem[];
  subcategory: PositionDictionaryItem[];
}

// ===== 状态 =====
const jobTitles = ref<JobTitle[]>([]);
const dictItems = ref<PositionDictionaryGroup>({ family: [], category: [], subcategory: [] });
const loading = ref(false);
const submitting = ref(false);

// 分页：唯一真源 useTablePagination（默认 20，可切 10/20/50/100），禁手写 pageSize
const pagination = localPagination();

// 启用/停用筛选：ALL=全部 / ACTIVE=启用中 / INACTIVE=停用
const statusFilter = ref<'ALL' | 'ACTIVE' | 'INACTIVE'>('ALL');
watch(statusFilter, () => loadJobTitles());

// 搜索（名称，客户端过滤，输入即筛）
const searchKeyword = ref('');

const displayData = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase();
  if (!keyword) return jobTitles.value;
  return jobTitles.value.filter((item) => (item.name || '').toLowerCase().includes(keyword));
});

// ===== 数据加载 =====
const loadJobTitles = async () => {
  loading.value = true;
  try {
    const isEnabled =
      statusFilter.value === 'ACTIVE' ? true : statusFilter.value === 'INACTIVE' ? false : undefined;
    jobTitles.value = await listJobTitles({ isEnabled });
  } catch (error) {
    console.error(t('pages.settings.PositionTitleManagement.s51'), error);
    message.error(t('pages.settings.PositionTitleManagement.s51'));
  } finally {
    loading.value = false;
  }
};

const loadDictionaries = async () => {
  try {
    const [family, category, subcategory] = await Promise.all([
      listPositionDictionaryItems('POSITION_FAMILY'),
      listPositionDictionaryItems('POSITION_CATEGORY'),
      listPositionDictionaryItems('POSITION_SUBCATEGORY'),
    ]);
    dictItems.value = { family, category, subcategory };
  } catch (error) {
    console.error(t('pages.settings.PositionTitleManagement.s57'), error);
    message.error(t('pages.settings.PositionTitleManagement.s57'));
  }
};

// ===== 字典项解析（兼容「对象 {id,value}」与「裸 id」两种响应形态）=====
const dictLabelMap = computed(() => {
  const map = new Map<string, string>();
  const all = [
    ...dictItems.value.family,
    ...dictItems.value.category,
    ...dictItems.value.subcategory,
  ];
  for (const item of all) map.set(item.id, item.value);
  return map;
});

const resolveDictId = (raw: any): string | null => {
  if (raw == null) return null;
  if (typeof raw === 'object') return raw.id ? String(raw.id) : null;
  return String(raw);
};

const resolveDictLabel = (raw: any): string => {
  if (raw == null) return '';
  if (typeof raw === 'object') {
    const label = raw.value ?? raw.name ?? raw.label;
    if (label) return String(label);
    return raw.id ? dictLabelMap.value.get(String(raw.id)) ?? '' : '';
  }
  return dictLabelMap.value.get(String(raw)) ?? '';
};

/** 当前值不在可选项里（如字典项已停用）时补一个回显项，避免下拉框展示裸 id。 */
const withFallbackOption = (
  options: { label: string; value: string }[],
  value: string | undefined,
): { label: string; value: string }[] => {
  if (!value || options.some((opt) => opt.value === value)) return options;
  return [...options, { label: resolveDictLabel(value) || value, value }];
};

const toDictOption = (item: PositionDictionaryItem) => ({ label: item.value, value: item.id });

const jobFamilyOptions = computed(() => {
  const options = dictItems.value.family.filter((it) => it.isActive).map(toDictOption);
  return withFallbackOption(options, formState.jobFamily);
});

// 职位类按所选职位族的 parentId 客户端级联过滤（P1 起后端校验一致）
const jobCategoryOptions = computed(() => {
  const familyId = formState.jobFamily;
  if (!familyId) return [];
  const options = dictItems.value.category
    .filter((it) => it.isActive && it.parentId === familyId)
    .map(toDictOption);
  return withFallbackOption(options, formState.jobCategory);
});

// 职位子类按所选职位类的 parentId 客户端级联过滤
const jobSubcategoryOptions = computed(() => {
  const categoryId = formState.jobCategory;
  if (!categoryId) return [];
  const options = dictItems.value.subcategory
    .filter((it) => it.isActive && it.parentId === categoryId)
    .map(toDictOption);
  return withFallbackOption(options, formState.jobSubcategory);
});

const yesNoOptions = computed(() => [
  { label: t('pages.settings.PositionTitleManagement.s14'), value: 'YES' },
  { label: t('pages.settings.PositionTitleManagement.s15'), value: 'NO' },
]);

const jobLevelTierOptions = computed(() =>
  JOB_LEVEL_TIER_ENUM.map((item) => ({ label: t(item.labelKey), value: item.value })),
);

// ===== 弹窗（新增 / 编辑）=====
const modalVisible = ref(false);
const editingId = ref<string | null>(null);

const modalTitle = computed(() =>
  editingId.value
    ? t('pages.settings.PositionTitleManagement.s22')
    : t('pages.settings.PositionTitleManagement.s9'),
);

const formState = reactive({
  name: '',
  jobFamily: undefined as string | undefined,
  jobCategory: undefined as string | undefined,
  jobSubcategory: undefined as string | undefined,
  isKeyPosition: 'NO',
  responsibility: '',
  isManagement: 'NO',
  jobLevelTier: undefined as string | undefined,
  sortOrder: 0,
});

const openCreateModal = () => {
  editingId.value = null;
  Object.assign(formState, {
    name: '',
    jobFamily: undefined,
    jobCategory: undefined,
    jobSubcategory: undefined,
    isKeyPosition: 'NO',
    responsibility: '',
    isManagement: 'NO',
    jobLevelTier: undefined,
    sortOrder: 0,
  });
  modalVisible.value = true;
};

const startEdit = (record: JobTitle) => {
  editingId.value = record.id;
  Object.assign(formState, {
    name: record.name || '',
    jobFamily: resolveDictId(record.jobFamily) ?? undefined,
    jobCategory: resolveDictId(record.jobCategory) ?? undefined,
    jobSubcategory: resolveDictId(record.jobSubcategory) ?? undefined,
    isKeyPosition: record.isKeyPosition === true ? 'YES' : 'NO',
    responsibility: record.responsibility || '',
    isManagement: record.isManagement === true ? 'YES' : 'NO',
    jobLevelTier: record.jobLevelTier ?? undefined,
    sortOrder: record.sortOrder ?? 0,
  });
  modalVisible.value = true;
};

// 级联重置仅在用户交互时触发（@update:value），避免回显编辑值时误清空下级
const onJobFamilyChange = () => {
  formState.jobCategory = undefined;
  formState.jobSubcategory = undefined;
};

const onJobCategoryChange = () => {
  formState.jobSubcategory = undefined;
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
    message.error(t('pages.settings.PositionTitleManagement.s43'));
    return;
  }
  if (!formState.jobFamily) {
    message.error(t('pages.settings.PositionTitleManagement.s44'));
    return;
  }
  if (formState.isKeyPosition !== 'YES' && formState.isKeyPosition !== 'NO') {
    message.error(t('pages.settings.PositionTitleManagement.s45'));
    return;
  }
  submitting.value = true;
  try {
    const payload = {
      name: formState.name.trim(),
      jobFamily: formState.jobFamily,
      jobCategory: formState.jobCategory ?? null,
      jobSubcategory: formState.jobSubcategory ?? null,
      isKeyPosition: formState.isKeyPosition === 'YES',
      responsibility: formState.responsibility || '',
      isManagement: formState.isManagement === 'YES',
      jobLevelTier: formState.jobLevelTier ?? null,
      sortOrder: Number.isFinite(formState.sortOrder) ? Number(formState.sortOrder) : 0,
    };
    if (editingId.value) {
      await updateJobTitle(editingId.value, payload);
      message.success(t('pages.settings.PositionTitleManagement.s47'));
    } else {
      await createJobTitle(payload);
      message.success(t('pages.settings.PositionTitleManagement.s46'));
    }
    modalVisible.value = false;
    loadJobTitles();
  } catch (error: any) {
    message.error(
      extractErrorMessage(error) ||
        (editingId.value
          ? t('pages.settings.PositionTitleManagement.s49')
          : t('pages.settings.PositionTitleManagement.s48')),
    );
  } finally {
    submitting.value = false;
  }
};

// ===== 启停（is_enabled 软停：仅提示不硬阻止，Q5）=====
const isRowEnabled = (row: JobTitle): boolean => {
  if (row.status) return row.status !== 'INACTIVE';
  return row.isEnabled !== false;
};

const handleToggleEnabled = async (row: JobTitle) => {
  const next = !isRowEnabled(row);
  try {
    await setJobTitleEnabled(row.id, next);
    message.success(
      next
        ? t('pages.settings.PositionTitleManagement.s53')
        : t('pages.settings.PositionTitleManagement.s52'),
    );
    loadJobTitles();
  } catch (error: any) {
    message.error(extractErrorMessage(error) || t('pages.settings.PositionTitleManagement.s50'));
  }
};

// ===== 表格列 =====
const renderDictCell = (raw: any) => {
  const label = resolveDictLabel(raw);
  if (!label) return h('span', { style: 'color: #bfbfbf' }, '—');
  return h('span', {}, label);
};

const renderActions = (row: JobTitle) => {
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
          default: () => t('pages.settings.PositionTitleManagement.s16'),
          icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
        },
      ),
      enabled
        ? h(
            NPopconfirm,
            {
              onPositiveClick: () => handleToggleEnabled(row),
              positiveText: t('pages.settings.PositionTitleManagement.s20'),
              negativeText: t('pages.settings.PositionTitleManagement.s21'),
            },
            {
              default: () => t('pages.settings.PositionTitleManagement.s19'),
              trigger: () =>
                h(
                  NButton,
                  { quaternary: true, type: 'warning', size: OP_ACTION_BUTTON_SIZE },
                  {
                    default: () => t('pages.settings.PositionTitleManagement.s17'),
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
              default: () => t('pages.settings.PositionTitleManagement.s18'),
              icon: () => h(NIcon, null, { default: () => h(PowerOutline) }),
            },
          ),
    ],
  });
};

const columns = computed(() => [
  column({
    title: t('pages.settings.PositionTitleManagement.s10'),
    key: 'name',
    width: 220,
    render: (row: JobTitle) =>
      h('span', { style: 'font-weight: 500; color: var(--ink)' }, row.name || '—'),
  }, 'short'),
  column({
    title: t('pages.settings.PositionTitleManagement.s11'),
    key: 'jobFamily',
    width: 180,
    render: (row: JobTitle) => renderDictCell(row.jobFamily),
  }, 'short'),
  column({
    title: t('pages.settings.PositionTitleManagement.s12'),
    key: 'isKeyPosition',
    width: 110,
    render: (row: JobTitle) => {
      const yes = row.isKeyPosition === true;
      return h(
        NTag,
        { type: yes ? 'success' : 'default', size: 'small', bordered: false },
        {
          default: () =>
            yes
              ? t('pages.settings.PositionTitleManagement.s14')
              : t('pages.settings.PositionTitleManagement.s15'),
        },
      );
    },
  }, 'short'),
  column({
    // 行内操作：编辑 type=primary、启停 type=warning/primary（语义色保留，不单色化）；
    // 本页无删除按钮。NSpace wrap:false，size 取 OP_ACTION_BUTTON_SIZE。
    title: t('pages.settings.PositionTitleManagement.s13'),
    key: 'actions',
    width: 160,
    fixed: 'right' as const,
    render: (row: JobTitle) => renderActions(row),
  }, 'control'),
]);

/* ============================ CSV 导出（utf-8-sig BOM，Excel 友好）============================ */

// 导出列（与列表一致，不含在职员工数 —— Q3 本期隐藏）
const EXPORT_HEADERS = [
  'pages.settings.PositionTitleManagement.s10',
  'pages.settings.PositionTitleManagement.s11',
  'pages.settings.PositionTitleManagement.s12',
  'pages.settings.PositionTitleManagement.s58',
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

const exportJobTitles = async () => {
  let all: JobTitle[] = [];
  try {
    all = await listJobTitles({ pageSize: 1000 });
  } catch (error) {
    console.error(t('pages.settings.PositionTitleManagement.s51'), error);
    message.error(t('pages.settings.PositionTitleManagement.s51'));
    return;
  }
  if (!all.length) {
    message.warning(t('pages.settings.PositionTitleManagement.s54'));
    return;
  }
  const yesLabel = t('pages.settings.PositionTitleManagement.s14');
  const noLabel = t('pages.settings.PositionTitleManagement.s15');
  const activeLabel = t('pages.settings.PositionTitleManagement.s4');
  const inactiveLabel = t('pages.settings.PositionTitleManagement.s5');
  const rows = all.map((row) => [
    row.name || '',
    resolveDictLabel(row.jobFamily),
    row.isKeyPosition === true ? yesLabel : noLabel,
    isRowEnabled(row) ? activeLabel : inactiveLabel,
  ]);
  const headerLine = EXPORT_HEADERS.map((key) => csvEscape(t(key))).join(',');
  const lines = [headerLine, ...rows.map((r) => r.map(csvEscape).join(','))];
  const content = '\uFEFF' + lines.join('\r\n');
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
  const fileName = `${t('pages.settings.PositionTitleManagement.s56')}_${new Date().toISOString().slice(0, 10)}.csv`;
  triggerDownload(blob, fileName);
  message.success(t('pages.settings.PositionTitleManagement.s55', { n: all.length }));
};

onMounted(() => {
  loadJobTitles();
  loadDictionaries();
});
</script>

<style scoped>
/* === 2026-08-24 page-header + page-body 三件套（与 DepartmentManagement 同款） === */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
/* .page-header 的 flex-shrink:0 与 .spacer 的 flex:1 已由 glass.css 全局提供，此处不私有重写 */
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/* .glass-panel 已是全局类（glass.css §4）；panel-shell 让面板撑满 page-body，
 * 内部 .toolbar + .table-wrap(flex-height) 与身份管理 RolesTab 同构（2026-10-15 兵哥：页面结构统一） */
.panel-shell {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding: var(--space-2);
}
/* 搜索框宽度与身份管理工具条一致（RolesTab scoped 同款覆盖全局 200px） */
.rule-filter-search { width: 240px; max-width: 240px; }
</style>
