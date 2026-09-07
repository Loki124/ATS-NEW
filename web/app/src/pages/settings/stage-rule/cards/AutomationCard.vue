<template>
  <section class="config-card">
    <div class="card-title">
      <n-icon :component="GitNetworkOutline" />
      流程自动化
      <span class="title-desc">· 配置阶段的自动评估、流转、跳过与归档规则</span>
    </div>

    <!-- Block 1: 自动评估 -->
    <div class="flow-block">
      <div class="block-header">
        <n-icon :component="ConstructOutline" /> 自动评估
        <span class="block-desc">· 当前阶段的自动化评估规则</span>
      </div>
      <div class="option-grid">
        <label class="opt-item">
          <n-checkbox :checked="form.autoEvalN2" @update:checked="(v: boolean) => (form.autoEvalN2 = v)" />
          <span>N+2 推荐免筛选</span>
        </label>
        <label class="opt-item">
          <n-checkbox :checked="form.autoEvalPrevAa" @update:checked="(v: boolean) => (form.autoEvalPrevAa = v)" />
          <span>引用前序双 A 的一致意见</span>
        </label>
      </div>
    </div>

    <!-- Block 2: 自动流转 -->
    <div class="flow-block">
      <div class="block-header block-header--secondary">
        <n-icon :component="ArrowForwardOutline" /> 自动流转
        <span class="block-desc">· 满足条件时在到达执行时机后自动流转到下阶段</span>
      </div>
      <div class="flow-condition-row">
        <div class="flow-field">
          <label class="field-label">自动流转条件</label>
          <n-select size="small" :value="form.autoAdvanceType" :options="advanceOptions" @update:value="(v: any) => (form.autoAdvanceType = v)" />
        </div>
        <div class="flow-field">
          <label class="field-label">执行时机</label>
          <n-select size="small" :value="form.autoAdvanceTiming" :options="timingOptions" @update:value="(v: any) => (form.autoAdvanceTiming = v)" />
        </div>
      </div>
      <div v-if="form.autoAdvanceTiming === 'DELAYED'" class="flow-condition-row">
        <div class="flow-field">
          <label class="field-label">延迟天数 (1-20 工作日)</label>
          <n-input-number size="small" :value="form.autoAdvanceDays" :min="1" :max="20" @update:value="(v: number | null) => (form.autoAdvanceDays = v)" />
        </div>
      </div>
    </div>

    <!-- Block 3: 自动跳过 -->
    <div class="flow-block">
      <div class="block-header block-header--split">
        <div class="block-header__main">
          <n-icon :component="PlaySkipForwardOutline" /> 自动跳过
          <span class="block-desc">· 满足规则时不再停留，直接判断是否满足下阶段进入条件</span>
        </div>
        <ModuleSwitch :model-value="form.skipEnabled" @update:model-value="emit('update:skipEnabled', $event)" />
      </div>
      <div class="rule-content" :class="{ 'rule-content--hidden': !form.skipEnabled }">
        <div class="actions-row">
          <button class="btn-outline-primary" type="button" @click="emit('add-skip')">
            <n-icon :component="AddOutline" /> 添加规则
          </button>
        </div>
        <RuleTable :columns="skipColumns" :rows="skipRules">
          <template #cell-action="{ row }">{{ actionLabel(row.action) }}</template>
          <template #actions="{ row }">
            <div class="action-btns">
              <a @click="emit('edit-skip', row)">编辑</a>
              <a class="danger" @click="emit('remove-skip', row)">删除</a>
            </div>
          </template>
        </RuleTable>
      </div>
    </div>

    <!-- Block 4: 自动归档 -->
    <div class="flow-block">
      <div class="block-header block-header--split">
        <div class="block-header__main">
          <n-icon :component="ArchiveOutline" /> 自动归档
          <span class="block-desc">· 满足规则时自动归档候选人</span>
        </div>
        <ModuleSwitch :model-value="form.archiveEnabled" @update:model-value="emit('update:archiveEnabled', $event)" />
      </div>
      <div class="rule-content" :class="{ 'rule-content--hidden': !form.archiveEnabled }">
        <div class="actions-row">
          <button class="btn-outline-primary" type="button" @click="emit('add-archive')">
            <n-icon :component="AddOutline" /> 添加规则
          </button>
          <button class="btn-text-primary" type="button" @click="emit('show-stopped')">
            <n-icon :component="EyeOffOutline" /> 查看已停用规则
          </button>
        </div>
        <RuleTable :columns="archiveColumns" :rows="archiveRules">
          <template #cell-action="{ row }">锁定 {{ row.lock_days || 0 }} 天</template>
          <template #actions="{ row }">
            <div class="action-btns">
              <a @click="emit('edit-archive', row)">编辑</a>
              <a class="danger" @click="emit('remove-archive', row)">删除</a>
            </div>
          </template>
        </RuleTable>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { NIcon, NSelect, NCheckbox, NInputNumber } from 'naive-ui'
import {
  GitNetworkOutline, ConstructOutline, ArrowForwardOutline, PlaySkipForwardOutline,
  ArchiveOutline, AddOutline, EyeOffOutline, CloseOutline,
} from '@vicons/ionicons5'
import ModuleSwitch from '../components/ModuleSwitch.vue'
import RuleTable from '../components/RuleTable.vue'
import { AUTO_ADVANCE_OPTIONS, AUTO_ADVANCE_TIMING_OPTIONS, AR_SKIP_ACTION_LABELS } from '../constants'
import type { StageRuleFormState, SkipRule, ArchiveRule } from '../types'

const props = defineProps<{
  form: StageRuleFormState
  skipRules: SkipRule[]
  archiveRules: ArchiveRule[]
}>()

const emit = defineEmits<{
  (e: 'update:skipEnabled', v: boolean): void
  (e: 'update:archiveEnabled', v: boolean): void
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

const skipColumns = [
  { key: 'name', title: '规则名', width: '28%' },
  { key: 'expression', title: '执行条件', width: '32%' },
  { key: 'action', title: '执行动作', width: '20%' },
]
const archiveColumns = [
  { key: 'name', title: '规则名', width: '28%' },
  { key: 'expression', title: '执行条件', width: '32%' },
  { key: 'action', title: '执行动作', width: '20%' },
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
}
.actions-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-top: 8px;
}
.btn-outline-primary {
  background: transparent;
  border: 1px dashed var(--brand);
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
  background: var(--brand-a12);
  border-style: solid;
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
