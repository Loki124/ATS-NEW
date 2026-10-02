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
import { computed, ref } from 'vue'
import { NIcon, NSelect } from 'naive-ui'
import { PersonOutline } from '@vicons/ionicons5'
import { HANDLER_SOURCE_OPTIONS, HANDLER_RULE_OPTIONS } from '../constants'
import type { StageRuleFormState } from '../types'
const { t } = useI18n()

const props = defineProps<{
  form: StageRuleFormState
  /** 需求(Demand)资源下 fieldType=PERSON 的真实字段（listFields 过滤，父组件在弹窗每次打开时刷新） */
  demandPersonFields?: any[]
  /** 职位(Position)资源下 fieldType=PERSON 的真实字段（同上） */
  positionPersonFields?: any[]
  /** 系统真实用户列表（listUsers，「指定人」来源时选真人，随数据源实时更新） */
  userOptions?: any[]
}>()

const emit = defineEmits<{
  (e: 'update:defaultHandlerType', v: StageRuleFormState['defaultHandlerType']): void
  (e: 'update:defaultHandlerFields', v: string[]): void
  (e: 'update:defaultHandlerUserIds', v: string[]): void
}>()

const sourceOptions = HANDLER_SOURCE_OPTIONS
const ruleOptions = HANDLER_RULE_OPTIONS

// === 严禁 mock/硬编码：取值字段选项实时映射自真实数据源（文档 §3.2.3 联动语义） ===
//  - 需求中/职位中 → 动态字段定义中「人员(PERSON)」型字段（label=字段名，value=fieldKey，
//    与后端 StageRule.default_handler_fields 的 help_text「如 hiring_manager」字段 key 语义一致）
//  - 指定人(CUSTOM) → 系统真实用户（label=姓名/账号，value=user id，写入 default_handler_user_ids）
const fieldOptions = computed(() => {
  switch (props.form.defaultHandlerType) {
    case 'FROM_DEMAND':
      return (props.demandPersonFields ?? []).map((f: any) => ({ label: f.label, value: f.fieldKey }))
    case 'FROM_POSITION':
      return (props.positionPersonFields ?? []).map((f: any) => ({ label: f.label, value: f.fieldKey }))
    case 'CUSTOM':
      return (props.userOptions ?? []).map((u: any) => ({ label: u.realName || u.username || u.id, value: u.id }))
    default:
      return []
  }
})

/** 指定人(CUSTOM)：选中项进 defaultHandlerUserIds；字段来源：字段 key 进 defaultHandlerFields */
const fieldValue = computed(() => {
  if (props.form.defaultHandlerType === 'CUSTOM') return props.form.defaultHandlerUserIds[0] || null
  return props.form.defaultHandlerFields[0] || null
})

/** 处理规则为静态 UI 规则选项（后端 processing_rule 枚举的展示映射，非业务数据）。
 * 仅本地 UI 态，不落库——原实现误绑 defaultHandlerUserIds，会与「指定人」选择互相覆盖。 */
const ruleValue = ref<string | null>(null)

/** 文档 §3.2.3：NONE 禁用「取值字段」+「处理规则」 */
const isFieldDisabled = computed(() => props.form.defaultHandlerType === 'NONE')
const isRuleDisabled = computed(() => props.form.defaultHandlerType === 'NONE')

function onSource(v: StageRuleFormState['defaultHandlerType']) {
  emit('update:defaultHandlerType', v)
  emit('update:defaultHandlerFields', [])
  emit('update:defaultHandlerUserIds', [])
  ruleValue.value = null
}
function onField(v: string | null) {
  if (props.form.defaultHandlerType === 'CUSTOM') {
    emit('update:defaultHandlerUserIds', v ? [v] : [])
  } else {
    emit('update:defaultHandlerFields', v ? [v] : [])
  }
}
function onRule(v: string | null) {
  ruleValue.value = v
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
