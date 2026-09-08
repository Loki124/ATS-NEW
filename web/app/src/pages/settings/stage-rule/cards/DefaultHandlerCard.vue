<template>
  <section class="config-card">
    <div class="card-title">
      <n-icon :component="PersonOutline" />
      默认处理人
      <span class="title-desc">· 进入本阶段时自动为默认处理人添加待办任务</span>
    </div>

    <div class="flow-block">
      <div class="flow-condition-row flow-condition-row--3">
        <div class="flow-field">
          <label class="field-label">
            数据来源 <span class="required-mark">*</span>
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
            取值字段 <span class="required-mark">*</span>
          </label>
          <n-select
            size="small"
            :value="fieldValue"
            :options="fieldOptions"
            :disabled="form.defaultHandlerType === 'CUSTOM'"
            placeholder="选择字段"
            @update:value="onField"
          />
        </div>
        <div class="flow-field">
          <label class="field-label">处理规则</label>
          <n-select
            size="small"
            :value="ruleValue"
            :options="ruleOptions"
            :disabled="form.defaultHandlerType !== 'CUSTOM'"
            placeholder="指定处理人"
            filterable
            @update:value="onRule"
          />
        </div>
      </div>
      <p class="field-hint">数据来源切换会重置取值字段；「指定人」来源需在选择处理规则处指定具体用户。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NIcon, NSelect } from 'naive-ui'
import { PersonOutline } from '@vicons/ionicons5'
import { HANDLER_SOURCE_OPTIONS, HANDLER_RULE_OPTIONS } from '../constants'
import type { StageRuleFormState } from '../types'

const props = defineProps<{ form: StageRuleFormState }>()

const sourceOptions = HANDLER_SOURCE_OPTIONS
const ruleOptions = HANDLER_RULE_OPTIONS

/** 数据来源 → 取值字段 mock 选项（后端就绪后由字典接口替换） */
const FIELD_BY_SOURCE: Record<string, { label: string; value: string }[]> = {
  FROM_DEMAND: [
    { label: '需求职级', value: 'DEMAND_LEVEL' },
    { label: '需求部门', value: 'DEPARTMENT' },
    { label: '用人经理', value: 'HIRING_MANAGER' },
  ],
  FROM_POSITION: [
    { label: '职位职级', value: 'POSITION_LEVEL' },
    { label: '职位序列', value: 'POSITION_SERIES' },
  ],
  CUSTOM: [],
}

const fieldOptions = computed(() => FIELD_BY_SOURCE[props.form.defaultHandlerType] || [])
const fieldValue = computed(() => props.form.defaultHandlerFields[0] || null)
const ruleValue = computed(() => props.form.defaultHandlerUserIds[0] || null)

function onSource(v: StageRuleFormState['defaultHandlerType']) {
  props.form.defaultHandlerType = v
  props.form.defaultHandlerFields = []
  if (v !== 'CUSTOM') props.form.defaultHandlerUserIds = []
}
function onField(v: string | null) {
  props.form.defaultHandlerFields = v ? [v] : []
}
function onRule(v: string | null) {
  props.form.defaultHandlerUserIds = v ? [v] : []
}
</script>

<style scoped>
.flow-condition-row--3 {
  flex-wrap: wrap;
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
.field-hint {
  font-size: var(--fs-12);
  color: var(--ink-soft);
  line-height: 1.5;
  margin: 8px 0 0;
}
.required-mark {
  color: var(--c-error);
  margin-left: 2px;
}
</style>
