<template>
  <!-- 职等管理弹窗：全局单例（默认 40，范围 1-999，越界拦截） -->
  <n-modal
    v-model:show="visible"
    preset="card"
    :title="t('pages.settings.JobLevelManagement.s12')"
    :style="{ width: '480px' }"
    :mask-closable="false"
    :centered="true"
    :auto-focus="false"
  >
    <n-form :model="formState" label-placement="top">
      <n-form-item :label="t('pages.settings.JobLevelManagement.s61')" required>
        <n-input-number
          v-model:value="formState.maxGrade"
          :min="1"
          :max="999"
          style="width: 100%"
          :placeholder="t('pages.settings.JobLevelManagement.s63')"
        />
      </n-form-item>
      <n-alert type="info" :show-icon="true">
        {{ t('pages.settings.JobLevelManagement.s62') }}
      </n-alert>
    </n-form>

    <template #footer>
      <div style="display: flex; justify-content: flex-end; gap: var(--space-2)">
        <n-button text @click="visible = false">{{ t('pages.settings.JobLevelManagement.s26') }}</n-button>
        <n-button type="primary" class="gradient-btn" :loading="saving" @click="handleSave">
          {{ t('pages.settings.JobLevelManagement.s64') }}
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, computed, watch } from 'vue';
import { NForm, NFormItem, NInputNumber, NModal, NAlert, NButton, useMessage } from 'naive-ui';
import { getJobLevelGradeSetting, updateJobLevelGradeSetting } from '../../../api/job-level';

const { t } = useI18n()
const message = useMessage();

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{
  'update:show': [value: boolean];
  /** 保存成功后通知父页刷新（职等上限约束已变）。 */
  saved: [];
}>();

const visible = computed({
  get: () => props.show,
  set: (value: boolean) => emit('update:show', value),
});

const formState = reactive({ maxGrade: 40 });
const saving = ref(false);

/** 进弹窗读取单例当前值（缺省 40）。 */
const loadSetting = async () => {
  try {
    const setting = await getJobLevelGradeSetting();
    formState.maxGrade = setting.maxGrade;
  } catch (error) {
    console.error(t('pages.settings.JobLevelManagement.s66'), error);
    message.error(t('pages.settings.JobLevelManagement.s66'));
  }
};

watch(
  () => props.show,
  (value) => {
    if (value) loadSetting();
  },
);

/** 确定：越界（<1 或 >999）/ 非整数拦截后 PUT 单例。 */
const handleSave = async () => {
  const value = Number(formState.maxGrade);
  if (!Number.isInteger(value) || value < 1 || value > 999) {
    message.error(t('pages.settings.JobLevelManagement.s63'));
    return;
  }
  saving.value = true;
  try {
    await updateJobLevelGradeSetting(value);
    message.success(t('pages.settings.JobLevelManagement.s65'));
    emit('saved');
    visible.value = false;
  } catch (error: any) {
    const data = error?.response?.data;
    message.error(data?.message || data?.error || t('pages.settings.JobLevelManagement.s57'));
  } finally {
    saving.value = false;
  }
};
</script>
