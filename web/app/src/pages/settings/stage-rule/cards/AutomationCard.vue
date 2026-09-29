<template>
  <section class="config-card">
    <div class="card-title card-title--left">
      <n-icon :component="PulseOutline" />
      {{ t('pages.settings.stage-rule.cards.AutomationCard.s9') }}
      <span class="title-desc">{{ t('pages.settings.stage-rule.cards.AutomationCard.s1') }}</span>
    </div>

    <!-- Block 1: {{ t('pages.settings.stage-rule.cards.AutomationCard.s15') }} -->
    <div class="flow-block">
      <div class="block-header">
        <n-icon :component="SparklesOutline" /> {{ t('pages.settings.stage-rule.cards.AutomationCard.s15') }}
        <span class="block-desc">{{ t('pages.settings.stage-rule.cards.AutomationCard.s2') }}</span>
      </div>
      <div class="option-grid">
        <label class="opt-item">
          <input
            type="checkbox"
            :checked="form.autoEvalN2"
            @change="emit('update:autoEvalN2', ($event.target as HTMLInputElement).checked)"
          />
          <span>{{ t('pages.settings.stage-rule.cards.AutomationCard.s3') }}</span>
        </label>
        <label class="opt-item">
          <input
            type="checkbox"
            :checked="form.autoEvalPrevAa"
            @change="emit('update:autoEvalPrevAa', ($event.target as HTMLInputElement).checked)"
          />
          <span>{{ t('pages.settings.stage-rule.cards.AutomationCard.s4') }}</span>
        </label>
      </div>
    </div>

    <!-- Block 2: {{ t('pages.settings.stage-rule.cards.AutomationCard.s16') }} -->
    <div class="flow-block">
      <div class="block-header block-header--secondary">
        <n-icon :component="ArrowForwardOutline" /> {{ t('pages.settings.stage-rule.cards.AutomationCard.s16') }}
        <span class="block-desc">{{ t('pages.settings.stage-rule.cards.AutomationCard.s5') }}</span>
      </div>
      <div class="flow-condition-row">
        <div class="flow-field">
          <label class="field-label">{{ t('pages.settings.stage-rule.cards.AutomationCard.s6') }}</label>
          <n-select size="small" :value="form.autoAdvanceType" :options="advanceOptions" @update:value="(v: any) => emit('update:autoAdvanceType', v)" />
        </div>
        <div class="flow-field">
          <label class="field-label">{{ t('pages.settings.stage-rule.cards.AutomationCard.s7') }}</label>
          <n-select size="small" :value="form.autoAdvanceTiming" :options="timingOptions" @update:value="(v: any) => emit('update:autoAdvanceTiming', v)" />
        </div>
      </div>
      <div v-if="form.autoAdvanceTiming === 'DELAYED'" class="flow-condition-row">
        <div class="flow-field">
          <label class="field-label">{{ t('pages.settings.stage-rule.cards.AutomationCard.s10') }}</label>
          <n-input-number size="small" :value="form.autoAdvanceDays" :min="1" :max="20" @update:value="(v: number | null) => emit('update:autoAdvanceDays', v)" />
        </div>
      </div>
    </div>

    <!-- Block 3: {{ t('pages.settings.stage-rule.cards.AutomationCard.s17') }} -->
    <div class="flow-block">
      <div class="block-header block-header--split">
        <div class="block-header__main">
          <n-icon :component="PlaySkipForwardOutline" /> {{ t('pages.settings.stage-rule.cards.AutomationCard.s17') }}
          <span class="block-desc">{{ t('pages.settings.stage-rule.cards.AutomationCard.s8') }}</span>
        </div>
        <ModuleSwitch :model-value="form.skipEnabled" @update:model-value="emit('update:skipEnabled', $event)" />
      </div>
      <div class="rule-content" :class="{ 'rule-content--hidden': !form.skipEnabled }">
        <div class="actions-row">
          <button class="btn-outline-primary" type="button" @click="emit('add-skip')">
            <n-icon :component="AddOutline" /> {{ t('pages.settings.stage-rule.cards.AutomationCard.s18') }}
          </button>
        </div>
        <RuleTable :columns="skipColumns" :rows="skipRules.filter((r: SkipRule) => r.enabled)">
          <template #cell-action="{ row }">{{ actionLabel(row.action) }}</template>
          <template #actions="{ row }">
            <div class="action-btns">
              <a @click="emit('edit-skip', row)">{{ t('pages.settings.stage-rule.cards.AutomationCard.s19') }}</a>
              <a class="danger" @click="emit('remove-skip', row)">{{ t('pages.settings.stage-rule.cards.AutomationCard.s20') }}</a>
            </div>
          </template>
        </RuleTable>
      </div>
    </div>

    <!-- Block 4: {{ t('pages.settings.stage-rule.cards.AutomationCard.s21') }} -->
    <div class="flow-block">
      <div class="block-header block-header--split">
        <div class="block-header__main">
          <n-icon :component="HourglassOutline" /> {{ t('pages.settings.stage-rule.cards.AutomationCard.s21') }}
          <span class="block-desc">{{ t('pages.settings.stage-rule.cards.AutomationCard.s11') }}</span>
        </div>
        <ModuleSwitch :model-value="form.archiveEnabled" @update:model-value="emit('update:archiveEnabled', $event)" />
      </div>
      <div class="rule-content" :class="{ 'rule-content--hidden': !form.archiveEnabled }">
        <div class="actions-row">
          <button class="btn-outline-primary" type="button" @click="emit('add-archive')">
            <n-icon :component="AddOutline" /> {{ t('pages.settings.stage-rule.cards.AutomationCard.s18') }}
          </button>
          <button class="btn-outline" type="button" @click="emit('show-stopped')">
            <n-icon :component="EyeOffOutline" /> {{ t('pages.settings.stage-rule.cards.AutomationCard.s22') }}
          </button>
        </div>
        <RuleTable :columns="archiveColumns" :rows="archiveRules.filter((r: ArchiveRule) => r.enabled)">
          <template #cell-action="{ row }">
            <div class="archive-action">
              <div>{{ t('pages.settings.stage-rule.cards.AutomationCard.s12') }}{{ row.lock_days || 0 }}{{ t('pages.settings.stage-rule.cards.AutomationCard.s13') }}{{ row.extend_days || 0 }}{{ t('pages.settings.stage-rule.cards.AutomationCard.s14') }}</div>
              <div>{{ row.effective_scope === 'NEW_ONLY' ? t('pages.settings.stage-rule.cards.AutomationCard.s23') : t('pages.settings.stage-rule.cards.AutomationCard.s24') }}</div>
            </div>
          </template>
          <template #actions="{ row }">
            <div class="action-btns">
              <a @click="emit('edit-archive', row)">{{ t('pages.settings.stage-rule.cards.AutomationCard.s19') }}</a>
              <a class="danger" @click="emit('remove-archive', row)">{{ t('pages.settings.stage-rule.cards.AutomationCard.s20') }}</a>
            </div>
          </template>
        </RuleTable>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { NIcon, NSelect, NInputNumber } from 'naive-ui'
import {
  PulseOutline, SparklesOutline, ArrowForwardOutline, PlaySkipForwardOutline,
  HourglassOutline, AddOutline, EyeOffOutline, CloseOutline,
} from '@vicons/ionicons5'
import ModuleSwitch from '../components/ModuleSwitch.vue'
import RuleTable from '../components/RuleTable.vue'
import { AUTO_ADVANCE_OPTIONS, AUTO_ADVANCE_TIMING_OPTIONS, AR_SKIP_ACTION_LABELS } from '../constants'
import type { StageRuleFormState, SkipRule, ArchiveRule } from '../types'
const { t } = useI18n()

const props = defineProps<{
  form: StageRuleFormState
  skipRules: SkipRule[]
  archiveRules: ArchiveRule[]
}>()

const emit = defineEmits<{
  (e: 'update:skipEnabled', v: boolean): void
  (e: 'update:archiveEnabled', v: boolean): void
  (e: 'update:autoEvalN2', v: boolean): void
  (e: 'update:autoEvalPrevAa', v: boolean): void
  (e: 'update:autoAdvanceType', v: StageRuleFormState['autoAdvanceType']): void
  (e: 'update:autoAdvanceTiming', v: StageRuleFormState['autoAdvanceTiming']): void
  (e: 'update:autoAdvanceDays', v: number | null): void
  (e: 'add-skip'): void
  (e: 'add-archive'): void
  (e: 'edit-skip', rule: SkipRule): void
  (e: 'edit-archive', rule: ArchiveRule): void
  (e: 'remove-skip', rule: SkipRule): void
  (e: 'remove-archive', rule: ArchiveRule): void
  (e: 'show-stopped'): void
}>()

const advanceOptions = AUTO_ADVANCE_OPTIONS
const timingOptions = AUTO_ADVANCE_TIMING_OPTIONS

/** 列宽对齐 HTML 原型（规则名称 70 / 执行条件 220 / 执行动作 120 / 操作 140） */
const skipColumns = [
  { key: 'name', title: t('pages.settings.stage-rule.cards.AutomationCard.s25'), width: '70px' },
  { key: 'expression', title: t('pages.settings.stage-rule.cards.AutomationCard.s26'), width: '220px' },
  { key: 'action', title: t('pages.settings.stage-rule.cards.AutomationCard.s27'), width: '120px' },
]
const archiveColumns = [
  { key: 'name', title: t('pages.settings.stage-rule.cards.AutomationCard.s25'), width: '70px' },
  { key: 'expression', title: t('pages.settings.stage-rule.cards.AutomationCard.s26'), width: '220px' },
  { key: 'action', title: t('pages.settings.stage-rule.cards.AutomationCard.s27'), width: '150px' },
]

function actionLabel(a: SkipRule['action']) {
  return AR_SKIP_ACTION_LABELS[a] || a
}
</script>

<style scoped>
.flow-condition-row {
  display: flex;
  gap: var(--space-4);
  align-items: flex-end;
}
.flow-condition-row + .flow-condition-row {
  margin-top: 12px;
}
.flow-field {
  flex: 1;
  min-width: 0;
}
.field-label {
  display: block;
  font-size: var(--fs-12);
  color: var(--ink-soft);
  margin-bottom: 4px;
  font-weight: 500;
  line-height: 1.3;
}
.option-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px var(--space-4);
  padding: 4px 0;
}
.opt-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-13);
  color: var(--ink);
  cursor: pointer;
  white-space: nowrap;
  padding: 2px 0;
  transition: color var(--duration-fast) var(--ease-out);
}
.opt-item:hover { color: var(--brand); }
.opt-item input[type="checkbox"] {
  width: 14px;
  height: 14px;
  accent-color: var(--brand);
  cursor: pointer;
  flex-shrink: 0;
  margin: 0;
}
.actions-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-top: 8px;
}
/* 原型 .btn-outline.primary：实线品牌描边 + 白底，hover 实心品牌底 + 白字 */
.btn-outline-primary {
  background: var(--surface);
  border: 1px solid var(--brand);
  color: var(--brand);
  padding: 0 14px;
  height: 30px;
  border-radius: var(--radius-sm);
  font-size: var(--fs-12);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  font-weight: 500;
}
.btn-outline-primary:hover {
  background: var(--brand);
  border-color: var(--brand);
  color: var(--on-brand);
  box-shadow: var(--shadow-sm);
}

/* 原型 .btn-outline：灰虚线次要按钮，与主按钮在颜色上明确区分 */
.btn-outline {
  background: transparent;
  border: 1px dashed var(--g6);
  color: var(--ink-soft);
  padding: 0 14px;
  height: 30px;
  border-radius: var(--radius-sm);
  font-size: var(--fs-12);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  font-weight: 500;
}
.btn-outline:hover {
  background: var(--brand-a12);
  border-color: var(--brand);
  color: var(--brand);
}

/* {{ t('pages.settings.stage-rule.cards.AutomationCard.s21') }}执行动作（HTML 原型 .rule-table .action-btns 同款多行结构） */
.archive-action {
  white-space: nowrap;
  line-height: 1.45;
  color: var(--ink);
}
.archive-action div + div {
  color: var(--ink-soft);
}
.btn-text-primary {
  background: transparent;
  border: none;
  color: var(--brand);
  font-size: var(--fs-12);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
  padding: 0 var(--space-1);
}
.btn-text-primary:hover {
  color: var(--brand-hover);
}
.action-btns {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.action-btns a {
  color: var(--brand);
  text-decoration: none;
  cursor: pointer;
  font-size: var(--fs-12);
}
.action-btns a:hover {
  color: var(--brand-hover);
  text-decoration: underline;
}
.action-btns a.danger {
  color: var(--c-error);
}
.action-btns a.danger:hover {
  color: var(--c-error-deep);
}
.rule-content {
  transition: opacity var(--duration-base) var(--ease-out), max-height var(--duration-base) var(--ease-out);
  overflow: hidden;
  max-height: 2000px;
  opacity: 1;
}
.rule-content--hidden {
  max-height: 0;
  opacity: 0;
  pointer-events: none;
  margin: 0 !important;
}
@media (max-width: 767px) {
  .flow-condition-row {
    flex-direction: column;
    gap: 10px;
  }
}
</style>
