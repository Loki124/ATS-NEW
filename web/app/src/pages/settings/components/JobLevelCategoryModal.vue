<template>
  <!-- 类别管理弹窗：名称增改 / 停用启用 / 包含职级数展示；保存按后端单条 CRUD 逐条提交并汇总结果 -->
  <n-modal
    v-model:show="visible"
    preset="card"
    :title="t('pages.settings.JobLevelManagement.s11')"
    :style="{ width: '640px' }"
    :mask-closable="false"
    :centered="true"
    :auto-focus="false"
  >
    <n-alert type="info" :show-icon="true" style="margin-bottom: var(--space-3)">
      {{ t('pages.settings.JobLevelManagement.s59') }}
    </n-alert>

    <n-data-table
      :data="rows"
      :columns="columns"
      :row-key="(row: CategoryRow) => row.key"
      :loading="loading"
      :pagination="false"
      size="small"
    />

    <div style="margin-top: var(--space-3)">
      <n-button dashed @click="addRow">
        <template #icon><n-icon :component="AddOutline" /></template>
        {{ t('pages.settings.JobLevelManagement.s54') }}
      </n-button>
    </div>

    <template #footer>
      <div style="display: flex; justify-content: flex-end; gap: var(--space-2)">
        <n-button text @click="visible = false">{{ t('pages.settings.JobLevelManagement.s26') }}</n-button>
        <n-button type="primary" class="gradient-btn" :loading="saving" @click="handleSave">
          {{ t('pages.settings.JobLevelManagement.s33') }}
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed, watch, h } from 'vue';
import { AddOutline } from '@vicons/ionicons5';
import {
  NTag,
  NButton,
  NIcon,
  NInput,
  NDataTable,
  NModal,
  NAlert,
  useMessage,
} from 'naive-ui';
import {
  listJobLevelCategories,
  createJobLevelCategory,
  updateJobLevelCategory,
  setJobLevelCategoryEnabled,
} from '../../../api/job-level';

const { t } = useI18n()
const message = useMessage();

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{
  'update:show': [value: boolean];
  /** 保存成功（含停用切换）后通知父页刷新。 */
  saved: [];
}>();

const visible = computed({
  get: () => props.show,
  set: (value: boolean) => emit('update:show', value),
});

/** 弹窗内类别行（新建行无 id，key 为临时值）。 */
interface CategoryRow {
  key: string;
  id?: string;
  name: string;
  isEnabled: boolean;
  jobLevelCount: number;
  sortOrder: number;
}

const rows = ref<CategoryRow[]>([]);
const loading = ref(false);
const saving = ref(false);

let tempKeySeq = 0;

const loadCategories = async () => {
  loading.value = true;
  try {
    const list = await listJobLevelCategories();
    rows.value = list.map((item) => ({
      key: item.id,
      id: item.id,
      name: item.name || '',
      isEnabled: item.isEnabled !== false && item.status !== 'INACTIVE',
      jobLevelCount: Number(item.jobLevelCount ?? 0),
      sortOrder: Number(item.sortOrder ?? 0),
    }));
  } catch (error: any) {
    console.error(t('pages.settings.JobLevelManagement.s55'), error);
    message.error(t('pages.settings.JobLevelManagement.s55'));
  } finally {
    loading.value = false;
  }
};

// 打开弹窗时重新拉取（保证职级数与启停态最新）
watch(
  () => props.show,
  (value) => {
    if (value) loadCategories();
  },
);

/** 「+ 添加类别」：追加空行，顺序取当前最大值 + 1。 */
const addRow = () => {
  const maxSort = rows.value.reduce((max, row) => Math.max(max, row.sortOrder || 0), 0);
  tempKeySeq += 1;
  rows.value.push({
    key: `__new_${tempKeySeq}_${Date.now()}`,
    name: '',
    isEnabled: true,
    jobLevelCount: 0,
    sortOrder: maxSort + 1,
  });
};

/** 行内停用 / 启用链接（即时生效，PATCH 软停）。 */
const handleToggle = async (row: CategoryRow) => {
  if (!row.id) return;
  const next = !row.isEnabled;
  try {
    await setJobLevelCategoryEnabled(row.id, next);
    row.isEnabled = next;
    message.success(
      next
        ? t('pages.settings.JobLevelManagement.s45')
        : t('pages.settings.JobLevelManagement.s44'),
    );
    emit('saved');
  } catch (error: any) {
    message.error(extractErrorMessage(error) || t('pages.settings.JobLevelManagement.s42'));
  }
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

/**
 * 保存：后端仅提供单条 CRUD，故逐条提交并汇总结果 ——
 * 已有行 PUT 名称，新建行 POST 名称 + 顺序；任一失败即中断并提示首条错误。
 */
const handleSave = async () => {
  const hasEmpty = rows.value.some((row) => !row.name.trim());
  if (hasEmpty) {
    message.error(t('pages.settings.JobLevelManagement.s58'));
    return;
  }
  saving.value = true;
  try {
    const errors: string[] = [];
    for (const row of rows.value) {
      try {
        if (row.id) {
          await updateJobLevelCategory(row.id, { name: row.name.trim() });
        } else {
          await createJobLevelCategory({ name: row.name.trim(), sortOrder: row.sortOrder });
        }
      } catch (error: any) {
        errors.push(`${row.name}: ${extractErrorMessage(error) || t('pages.settings.JobLevelManagement.s57')}`);
      }
    }
    if (errors.length) {
      message.error(`${t('pages.settings.JobLevelManagement.s56')}：${errors[0]}`);
      return;
    }
    message.success(t('pages.settings.JobLevelManagement.s56'));
    emit('saved');
    visible.value = false;
  } finally {
    saving.value = false;
  }
};

const columns = computed(() => [
  {
    title: t('pages.settings.JobLevelManagement.s50'),
    key: 'name',
    render: (row: CategoryRow) =>
      h(NInput, {
        value: row.name,
        placeholder: t('pages.settings.JobLevelManagement.s53'),
        onUpdateValue: (value: string) => {
          row.name = value;
        },
      }),
  },
  {
    title: t('pages.settings.JobLevelManagement.s51'),
    key: 'jobLevelCount',
    width: 130,
    render: (row: CategoryRow) =>
      h('span', {}, t('pages.settings.JobLevelManagement.s52', { n: row.jobLevelCount })),
  },
  {
    title: t('pages.settings.JobLevelManagement.s49'),
    key: 'status',
    width: 100,
    render: (row: CategoryRow) =>
      h(
        NTag,
        { type: row.isEnabled ? 'success' : 'default', size: 'small', bordered: false },
        {
          default: () =>
            row.isEnabled
              ? t('pages.settings.JobLevelManagement.s4')
              : t('pages.settings.JobLevelManagement.s5'),
        },
      ),
  },
  {
    title: t('pages.settings.JobLevelManagement.s20'),
    key: 'actions',
    width: 100,
    render: (row: CategoryRow) =>
      row.id
        ? h(
            NButton,
            {
              text: true,
              type: row.isEnabled ? 'warning' : 'primary',
              size: 'small',
              onClick: () => handleToggle(row),
            },
            {
              default: () =>
                row.isEnabled
                  ? t('pages.settings.JobLevelManagement.s22')
                  : t('pages.settings.JobLevelManagement.s23'),
            },
          )
        : h('span', { style: 'color: #bfbfbf' }, '—'),
  },
]);
</script>
