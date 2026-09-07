<!--
  面试配置 Card 3（HTML 原型 .option-grid + 原生 input[type="checkbox"] + label）
  原型控件：14x14 checkbox + accent-color: var(--brand) + 13px 字号 + 5px gap
-->
<template>
  <section class="config-card">
    <div class="card-title">
      <span class="title-left">
        <n-icon :component="VideocamOutline" />
        面试配置
        <span class="title-desc">· 面试轮次、形式配置</span>
      </span>
    </div>

    <!-- 面试轮次 -->
    <div class="flow-block">
      <div class="block-header">
        <n-icon :component="LayersOutline" /> 面试轮次
      </div>
      <div class="option-grid">
        <label v-for="opt in roundOptions" :key="opt.value" class="opt-item">
          <input
            type="checkbox"
            :checked="isOn(form.interviewRoundIds, opt.value)"
            @change="toggle(form.interviewRoundIds, opt.value, ($event.target as HTMLInputElement).checked)"
          />
          <span>{{ opt.label }}</span>
        </label>
      </div>
    </div>

    <!-- 面试形式 -->
    <div class="flow-block">
      <div class="block-header">
        <n-icon :component="PhonePortraitOutline" /> 面试形式
      </div>
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
  </section>
</template>

<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { VideocamOutline, LayersOutline, PhonePortraitOutline } from '@vicons/ionicons5'
import { INTERVIEW_ROUND_OPTIONS, INTERVIEW_FORMAT_OPTIONS } from '../constants'
import type { StageRuleFormState } from '../types'

const props = defineProps<{ form: StageRuleFormState }>()
const roundOptions = INTERVIEW_ROUND_OPTIONS
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
.option-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 2px var(--space-3);
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
</style>