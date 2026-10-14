<template>
  <!-- 职级序列管理弹窗：专业序列系统内置固定（置灰必选），管理序列开关持久化 -->
  <n-modal
    v-model:show="visible"
    preset="card"
    :title="t('pages.settings.JobLevelManagement.s13')"
    :style="{ width: '560px' }"
    :mask-closable="false"
    :centered="true"
    :auto-focus="false"
  >
    <n-form :model="formState" label-placement="top">
      <n-form-item :label="t('pages.settings.JobLevelManagement.s67')">
        <n-space vertical :size="4">
          <n-checkbox :checked="true" disabled />
          <span style="color: var(--ink-soft); font-size: 13px">
            {{ t('pages.settings.JobLevelManagement.s68') }}
          </span>
        </n-space>
      </n-form-item>
      <n-form-item :label="t('pages.settings.JobLevelManagement.s69')">
        <n-space vertical :size="4">
          <n-switch v-model:value="formState.managementEnabled" />
          <span style="color: var(--ink-soft); font-size: 13px">
            {{ t('pages.settings.JobLevelManagement.s70') }}
          </span>
        </n-space>
      </n-form-item>
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
import {
  NForm,
  NFormItem,
  NSpace,
  NCheckbox,
  NSwitch,
  NModal,
  NButton,
  useMessage,
} from 'naive-ui';
import {
  getJobLevelSequenceSetting,
  updateJobLevelSequenceSetting,
} from '../../../api/job-level';

const { t } = useI18n()
const message = useMessage();

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{
  'update:show': [value: boolean];
  saved: [];
}>();

const visible = computed({
  get: () => props.show,
  set: (value: boolean) => emit('update:show', value),
});

const formState = reactive({ managementEnabled: false });
const saving = ref(false);

/** 进弹窗读取单例当前值。 */
const loadSetting = async () => {
  try {
    const setting = await getJobLevelSequenceSetting();
    formState.managementEnabled = setting.managementEnabled;
  } catch (error) {
    console.error(t('pages.settings.JobLevelManagement.s72'), error);
    message.error(t('pages.settings.JobLevelManagement.s72'));
  }
};

watch(
  () => props.show,
  (value) => {
    if (value) loadSetting();
  },
);

/** 确定：PUT 单例 {managementEnabled}（专业序列恒开、不入表）。 */
const handleSave = async () => {
  saving.value = true;
  try {
    await updateJobLevelSequenceSetting(formState.managementEnabled);
    message.success(t('pages.settings.JobLevelManagement.s71'));
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
