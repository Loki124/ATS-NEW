<template>
  <section class="config-card">
    <div class="card-title card-title--left">
      <n-icon :component="PersonOutline" />
      {{ t('pages.settings.stage-rule.cards.DefaultHandlerCard.s5') }}
      <span class="title-desc">{{ t('pages.settings.stage-rule.cards.DefaultHandlerCard.s1') }}</span>
    </div>

    <!-- 原型 Card 2：三个下拉直接放在 config-card 内，无 flow-block 白块包裹 -->
    <div class="flow-condition-row flow-condition-row--3">
      <div class="flow-field">
        <label class="field-label">
          {{ t('pages.settings.stage-rule.cards.DefaultHandlerCard.s17') }} <span class="required-mark">*</span>
        </label>
        <n-select
          size="small"
          :value="form.defaultHandlerType"
          :options="sourceOptions"
          @update:value="onSource"
        />
      </div>
      <div class="flow-field">
        <label class="field-label">
          {{ t('pages.settings.stage-rule.cards.DefaultHandlerCard.s18') }} <span class="required-mark">*</span>
        </label>
        <n-select
          size="small"
          :value="fieldValue"
          :options="fieldOptions"
          :disabled="isFieldDisabled"
          :placeholder="t('pages.settings.stage-rule.cards.DefaultHandlerCard.s3')"
          @update:value="onField"
        />
      </div>
      <div class="flow-field">
        <label class="field-label">{{ t('pages.settings.stage-rule.cards.DefaultHandlerCard.s2') }}</label>
        <n-select
          size="small"
          :value="ruleValue"
          :options="ruleOptions"
          :disabled="isRuleDisabled"
          :placeholder="t('pages.settings.stage-rule.cards.DefaultHandlerCard.s4')"
          filterable
          @update:value="onRule"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { NIcon, NSelect } from 'naive-ui'
import { PersonOutline } from '@vicons/ionicons5'
import { HANDLER_SOURCE_OPTIONS, HANDLER_RULE_OPTIONS } from '../constants'
import type { StageRuleFormState } from '../types'
const { t } = useI18n()

const props = defineProps<{ form: StageRuleFormState }>()

const emit = defineEmits<{
  (e: 'update:defaultHandlerType', v: StageRuleFormState['defaultHandlerType']): void
  (e: 'update:defaultHandlerFields', v: string[]): void
  (e: 'update:defaultHandlerUserIds', v: string[]): void
}>()

const sourceOptions = HANDLER_SOURCE_OPTIONS
const ruleOptions = HANDLER_RULE_OPTIONS

// === 按 HTML 原型 + 设计文档 §3.2.3 联动映射 ===
const FIELD_BY_SOURCE: Record<string, { label: string; value: string }[]> = {
  FROM_DEMAND: [
    { label: 'HRBP', value: 'HRBP' },
    { label: t('pages.settings.stage-rule.cards.DefaultHandlerCard.s6'), value: 'HIRING_MANAGER' },
    { label: t('pages.settings.stage-rule.cards.DefaultHandlerCard.s7'), value: 'HIRING_MANAGER_SUPER' },
    { label: t('pages.settings.stage-rule.cards.DefaultHandlerCard.s8'), value: 'PRESIDENT' },
    { label: 'VP', value: 'VP' },
  ],
  FROM_POSITION: [
    { label: 'HRBP', value: 'HRBP' },
    { label: t('pages.settings.stage-rule.cards.DefaultHandlerCard.s9'), value: 'HIRING_MANAGER' },
    { label: t('pages.settings.stage-rule.cards.DefaultHandlerCard.s10'), value: 'HIRING_MANAGER_SUPER' },
    { label: t('pages.settings.stage-rule.cards.DefaultHandlerCard.s11'), value: 'PRESIDENT' },
    { label: 'VP', value: 'VP' },
  ],
  CUSTOM: [
    { label: t('pages.settings.stage-rule.cards.DefaultHandlerCard.s12'), value: 'liu_xingxing' },
    { label: t('pages.settings.stage-rule.cards.DefaultHandlerCard.s13'), value: 'zhang_san' },
    { label: t('pages.settings.stage-rule.cards.DefaultHandlerCard.s14'), value: 'li_si' },
    { label: t('pages.settings.stage-rule.cards.DefaultHandlerCard.s15'), value: 'wang_wu' },
    { label: t('pages.settings.stage-rule.cards.DefaultHandlerCard.s16'), value: 'zhao_liu' },
  ],
  NONE: [],
}

/** 数据来源 → 取值字段（CUSTOM 走用户列表，其他走字段；NONE 禁用） */
const fieldOptions = computed(() => FIELD_BY_SOURCE[props.form.defaultHandlerType] || [])
const fieldValue = computed(() => props.form.defaultHandlerFields[0] || null)
const ruleValue = computed(() => props.form.defaultHandlerUserIds[0] || null)
/** 文档 §3.2.3：NONE 禁用「取值字段」+「处理规则」 */
const isFieldDisabled = computed(() => props.form.defaultHandlerType === 'NONE')
const isRuleDisabled = computed(() => props.form.defaultHandlerType === 'NONE')

function onSource(v: StageRuleFormState['defaultHandlerType']) {
  emit('update:defaultHandlerType', v)
  emit('update:defaultHandlerFields', [])
  if (v !== 'CUSTOM') emit('update:defaultHandlerUserIds', [])
}
function onField(v: string | null) {
  emit('update:defaultHandlerFields', v ? [v] : [])
}
function onRule(v: string | null) {
  emit('update:defaultHandlerUserIds', v ? [v] : [])
}
</script>

<style scoped>
.flow-condition-row--3 {
  flex-wrap: nowrap;
  align-items: flex-end;  /* 三下拉基线对齐：label 在上，select 底对齐 */
}
.flow-condition-row--3 .flow-field {
  flex: 1 1 180px;
  min-width: 160px;
}
.field-label {
  display: block;
  font-size: var(--fs-12);
  color: var(--ink-soft);
  margin-bottom: 4px;
  font-weight: 500;
  line-height: 1.3;
}
.required-mark {
  color: var(--c-error);
  margin-left: 2px;
}
</style>
