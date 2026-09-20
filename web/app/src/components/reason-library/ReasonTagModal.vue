<template>
  <n-modal
    :show="show"
    preset="card"
    :title="isEdit ? t('reasonLibrary.tags.modal.edit') : t('reasonLibrary.tags.modal.add')"
    style="max-width: 520px"
    :mask-closable="false"
    :bordered="false"
    :segmented="{ content: 'soft', footer: 'soft' }"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <n-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-placement="top"
      require-mark-placement="right-hanging"
    >
      <n-form-item :label="t('reasonLibrary.tags.modal.name')" path="name">
        <n-input
          v-model:value="form.name"
          :placeholder="t('reasonLibrary.tags.modal.namePlaceholder')"
          maxlength="50"
          clearable
          @keydown.enter="handleSubmit"
        />
      </n-form-item>

      <n-form-item :label="t('reasonLibrary.tags.modal.enName')" path="enName">
        <n-input
          v-model:value="form.enName"
          :placeholder="t('reasonLibrary.tags.modal.enNamePlaceholder')"
          maxlength="100"
          clearable
        />
      </n-form-item>

      <n-form-item :label="t('reasonLibrary.tags.modal.tip')" path="tip">
        <n-input
          v-model:value="form.tip"
          type="textarea"
          :placeholder="t('reasonLibrary.tags.modal.tipPlaceholder')"
          :rows="3"
          maxlength="200"
          show-count
        />
      </n-form-item>

      <n-form-item :label="t('reasonLibrary.tags.modal.type')">
        <n-input :value="t('reasonLibrary.common.custom')" disabled />
      </n-form-item>
      <p class="rl-type-hint">{{ t('reasonLibrary.tags.modal.typeHint') }}</p>
    </n-form>

    <template #footer>
      <n-space justify="end">
        <n-button @click="emit('update:show', false)">{{ t('reasonLibrary.common.cancel') }}</n-button>
        <n-button type="primary" :loading="saving" @click="handleSubmit">
          {{ isEdit ? t('reasonLibrary.common.save') : t('reasonLibrary.common.create') }}
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
/**
 * ReasonTagModal (T-16)
 * - 新建: tag=null
 * - 编辑: tag={...}; 系统标签 isSuperAdmin=false 时父组件不会触发 edit 入口 (tags.vue 已拦截)
 * - 类型字段: 永远 disabled 显示「自定义」(Q1+Q2: 系统预置不可新建, 后端亦只接受 type=custom)
 * - 入参 maxlength 50/100/200 与原型 + 后端字段约束对齐 (name 50 / en_name 100 / tip 200)
 */
import { ref, reactive, computed, watch } from 'vue'
import { useMessage, NModal, NForm, NFormItem, NInput, NButton, NSpace, type FormInst, type FormRules } from 'naive-ui'
import { createTag, updateTag, extractReasonApiError } from '../../api/reason-library'
import type { ReasonTag, ReasonTagPayload } from '../../types/reason-library'
import { BIZ_CODE } from '../../types/reason-library'
import { t } from '../../locales/zh-CN'

const props = defineProps<{
  show: boolean
  tag: ReasonTag | null
  isSuperAdmin?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'saved'): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const saving = ref(false)

const isEdit = computed(() => !!props.tag)

const form = reactive<ReasonTagPayload>({
  name: '',
  enName: '',
  tip: '',
})

const rules: FormRules = {
  name: [
    { required: true, message: t('reasonLibrary.tags.modal.nameRequired'), trigger: ['blur', 'input'] },
    { max: 50, message: '50 字以内', trigger: 'blur' },
  ],
  enName: [{ max: 100, message: '100 字符以内', trigger: 'blur' }],
  tip: [{ max: 200, message: '200 字以内', trigger: 'blur' }],
}

// show 变化 / tag 变化时同步表单
watch(
  () => [props.show, props.tag] as const,
  ([show, tag]) => {
    if (show) {
      if (tag) {
        form.name = tag.name
        form.enName = tag.enName || ''
        form.tip = tag.tip || ''
      } else {
        form.name = ''
        form.enName = ''
        form.tip = ''
      }
    }
  },
  { immediate: true },
)

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    if (props.tag) {
      await updateTag(props.tag.id, {
        name: form.name.trim(),
        enName: form.enName?.trim() || undefined,
        tip: form.tip?.trim() || undefined,
      })
      message.success(t('reasonLibrary.common.success'))
    } else {
      await createTag({
        name: form.name.trim(),
        enName: form.enName?.trim() || undefined,
        tip: form.tip?.trim() || undefined,
        type: 'custom',
      })
      message.success(t('reasonLibrary.common.success'))
    }
    emit('saved')
  } catch (e: any) {
    if (e?.code === BIZ_CODE.TAG_NAME_DUPLICATED) {
      message.error(t('reasonLibrary.errors.TAG_NAME_DUPLICATED'))
    } else if (e?.code === BIZ_CODE.SYSTEM_TAG_IMMUTABLE) {
      message.error(t('reasonLibrary.errors.SYSTEM_TAG_IMMUTABLE'))
    } else {
      message.error(extractReasonApiError(e, t('reasonLibrary.common.failed')))
    }
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.rl-type-hint {
  margin: -8px 0 0;
  font-size: var(--fs-12);
  color: var(--ink-faint);
  line-height: 1.6;
}
</style>
