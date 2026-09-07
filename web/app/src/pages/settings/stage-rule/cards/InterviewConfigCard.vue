<template>
  <section class="config-card">
    <div class="card-title">
      <n-icon :component="VideocamOutline" />
      面试配置
      <span class="title-desc">· 配置本阶段的面试轮次与面试形式</span>
    </div>

    <!-- 面试轮次 -->
    <div class="flow-block">
      <div class="block-header">
        <n-icon :component="LayersOutline" /> 面试轮次
        <span class="block-desc">· 可多选</span>
      </div>
      <div class="option-grid">
        <button
          v-for="opt in roundOptions"
          :key="opt.value"
          type="button"
          class="tag-chip"
          :class="{ 'tag-chip--on': isOn(form.interviewRoundIds, opt.value) }"
          @click="toggle(form.interviewRoundIds, opt.value)"
        >
          {{ opt.label }}
          <n-icon v-if="isOn(form.interviewRoundIds, opt.value)" class="tag-chip__x" :component="CloseOutline" @click.stop="toggle(form.interviewRoundIds, opt.value)" />
        </button>
      </div>
      <div v-if="roundOverflow > 0" class="tag-overflow">
        <button type="button" class="tag-more" @click="roundExpanded = !roundExpanded">
          +{{ roundOverflow }} 项{{ roundExpanded ? ' 收起' : '' }}
        </button>
      </div>
    </div>

    <!-- 面试形式 -->
    <div class="flow-block">
      <div class="block-header">
        <n-icon :component="PhonePortraitOutline" /> 面试形式
        <span class="block-desc">· 可多选</span>
      </div>
      <div class="option-grid">
        <button
          v-for="opt in formatOptions"
          :key="opt.value"
          type="button"
          class="tag-chip"
          :class="{ 'tag-chip--on': isOn(form.interviewFormat, opt.value) }"
          @click="toggle(form.interviewFormat, opt.value)"
        >
          {{ opt.label }}
          <n-icon v-if="isOn(form.interviewFormat, opt.value)" class="tag-chip__x" :component="CloseOutline" @click.stop="toggle(form.interviewFormat, opt.value)" />
        </button>
      </div>
      <div v-if="formatOverflow > 0" class="tag-overflow">
        <button type="button" class="tag-more" @click="formatExpanded = !formatExpanded">
          +{{ formatOverflow }} 项{{ formatExpanded ? ' 收起' : '' }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NIcon } from 'naive-ui'
import { VideocamOutline, LayersOutline, PhonePortraitOutline, CloseOutline } from '@vicons/ionicons5'
import { INTERVIEW_ROUND_OPTIONS, INTERVIEW_FORMAT_OPTIONS } from '../constants'
import type { StageRuleFormState } from '../types'

const props = defineProps<{ form: StageRuleFormState }>()

const roundOptions = INTERVIEW_ROUND_OPTIONS
const formatOptions = INTERVIEW_FORMAT_OPTIONS

const roundExpanded = ref(false)
const formatExpanded = ref(false)
/** 可视上限（超出折叠为 +N）；原型用 getBoundingClientRect 实测，这里以计数上限等价实现 */
const VISIBLE_CAP = 5

function isOn(list: string[], v: string) {
  return list.includes(v)
}
function toggle(list: string[], v: string) {
  const i = list.indexOf(v)
  if (i >= 0) list.splice(i, 1)
  else list.push(v)
}

const roundOverflow = computed(() =>
  props.form.interviewRoundIds.length > VISIBLE_CAP && !roundExpanded.value ? props.form.interviewRoundIds.length - VISIBLE_CAP : 0,
)
const formatOverflow = computed(() =>
  props.form.interviewFormat.length > VISIBLE_CAP && !formatExpanded.value ? props.form.interviewFormat.length - VISIBLE_CAP : 0,
)
</script>

<style scoped>
.option-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px var(--space-2);
  padding: 4px 0;
}
.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-13);
  color: var(--ink-soft);
  background: var(--g1);
  border: 1px solid var(--g2);
  border-radius: var(--radius-pill);
  padding: var(--space-1) var(--space-3);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  line-height: 1.4;
}
.tag-chip:hover {
  border-color: var(--brand);
  color: var(--brand);
}
.tag-chip--on {
  background: var(--brand-a12);
  color: var(--brand);
  border-color: var(--brand);
  font-weight: 500;
}
.tag-chip__x {
  font-size: 12px;
}
.tag-overflow {
  margin-top: 6px;
}
.tag-more {
  background: transparent;
  border: none;
  color: var(--brand);
  font-size: var(--fs-12);
  cursor: pointer;
  font-weight: 500;
  padding: 0;
}
.tag-more:hover {
  color: var(--brand-hover);
  text-decoration: underline;
}
</style>
