<!--
  面试配置 Card 3（HTML 原型 .option-grid + 原生 input[type="checkbox"] + label）
  原型控件：14x14 checkbox + accent-color: var(--brand) + 13px 字号 + 5px gap
-->
<template>
  <section class="config-card">
    <div class="card-title">
      <span class="title-left">
        <n-icon :component="ClipboardOutline" />
        {{ t('pages.settings.stage-rule.cards.InterviewConfigCard.s4') }}
        <span class="title-desc">{{ t('pages.settings.stage-rule.cards.InterviewConfigCard.s1') }}</span>
      </span>
    </div>

    <!-- 面试轮次 + 面试形式 横排（HTML 原型 .flow-condition-row 双列并排） -->
    <div class="flow-condition-row">
      <!-- 面试轮次：选项来自「面试轮次管理」真实数据源（父组件传入），随数据源实时更新 -->
      <div class="flow-field">
        <label class="field-label">{{ t('pages.settings.stage-rule.cards.InterviewConfigCard.s2') }}</label>
        <div v-if="roundOptions.length" class="option-grid">
          <label v-for="opt in roundOptions" :key="opt.value" class="opt-item">
            <input
              type="checkbox"
              :checked="isOn(form.interviewRoundIds, opt.value)"
              @change="toggle(form.interviewRoundIds, opt.value, ($event.target as HTMLInputElement).checked)"
            />
            <span>{{ opt.label }}</span>
          </label>
        </div>
        <p v-else class="option-empty">{{ t('pages.settings.stage-rule.cards.InterviewConfigCard.s5') }}</p>
      </div>

      <!-- 面试形式 -->
      <div class="flow-field">
        <label class="field-label">{{ t('pages.settings.stage-rule.cards.InterviewConfigCard.s3') }}</label>
        <div class="option-grid">
          <label v-for="opt in formatOptions" :key="opt.value" class="opt-item">
            <input
              type="checkbox"
              :checked="isOn(form.interviewFormat, opt.value)"
              @change="toggle(form.interviewFormat, opt.value, ($event.target as HTMLInputElement).checked)"
            />
            <span>{{ opt.label }}</span>
          </label>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { NIcon } from 'naive-ui'
import { ClipboardOutline } from '@vicons/ionicons5'
import { INTERVIEW_FORMAT_OPTIONS } from '../constants'
import type { StageRuleFormState } from '../types'
const { t } = useI18n()

const props = defineProps<{
  form: StageRuleFormState
  /** 面试轮次真实数据源（listRounds 返回，同「面试轮次管理」页），父组件在弹窗每次打开时刷新 */
  rounds?: any[]
}>()

// 严禁 mock/硬编码：轮次选项实时映射自真实数据源（label=轮次名称，value=轮次 id，
// 与 form.interviewRoundIds 及 ProcessStageRules.vue 老页面的存储格式一致）
const roundOptions = computed(() => (props.rounds ?? []).map((r: any) => ({ label: r.name, value: r.id })))
const formatOptions = INTERVIEW_FORMAT_OPTIONS

function isOn(list: string[], v: string) {
  return list.includes(v)
}
function toggle(list: string[], v: string, checked: boolean) {
  const i = list.indexOf(v)
  if (checked && i < 0) list.push(v)
  if (!checked && i >= 0) list.splice(i, 1)
}
</script>

<style scoped>
/* ===== card-title 双层布局（HTML 原型 .title-left + .title-actions） ===== */
.card-title {
  flex-wrap: wrap;
  gap: var(--space-2);
}
.title-left {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  min-width: 0;
}

/* ===== option-grid（HTML 原型 .option-grid） ===== */
.flow-condition-row {
  display: flex;
  gap: var(--space-4);
  align-items: flex-start;
}
.flow-field {
  flex: 1 1 0;
  min-width: 0;
}
.field-label {
  display: block;
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 6px;
}
.option-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  padding: 2px 0;
}
.opt-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-13);
  color: var(--ink);
  cursor: pointer;
  white-space: nowrap;
  padding: 1px 0;
  transition: color var(--duration-fast) var(--ease-out);
}
.opt-item:hover { color: var(--brand); }
.option-empty {
  margin: 2px 0 0;
  font-size: var(--fs-13);
  color: var(--ink-faint);
  line-height: 1.5;
}
.opt-item input[type="checkbox"] {
  width: 14px;
  height: 14px;
  accent-color: var(--brand);
  cursor: pointer;
  flex-shrink: 0;
  margin: 0;
}
</style>