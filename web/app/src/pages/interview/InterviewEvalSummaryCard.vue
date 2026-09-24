<script setup lang="ts">
import { useI18n } from 'vue-i18n'
/**
 * 面试评价 · 紧凑摘要卡（嵌入候选人详情 / 列表）
 * 与 InterviewEvaluationModal 共用 Evaluation 数据结构（v2 设计稿）。
 * 2026-09-03：旧版本引用了不存在的 `groups / overallScore / recommendation / RecValue / Candidate.round`，
 *   已按新版 Evaluation 契约重写（compliances + values + finalResult）。
 */
import { computed } from 'vue'
import { NTag } from 'naive-ui'
import type { Evaluation, FinalResult } from './InterviewEvaluationModal.vue'
const { t } = useI18n()

const props = defineProps<{ evaluation: Evaluation }>()

const REC_LABEL: Record<FinalResult, string> = {
  PASS: '通过', FAIL: '不通过', PENDING: '待定',
}
const REC_TYPE: Record<FinalResult, 'success' | 'warning' | 'info'> = {
  PASS: 'success', FAIL: 'warning', PENDING: 'info',
}

// 五能 5 维均值
const overallScore = computed(() => {
  const vals = Object.values(props.evaluation.values).filter(v => typeof v === 'number' && !isNaN(v))
  if (vals.length === 0) return 0
  return vals.reduce((s, v) => s + v, 0) / vals.length
})

function dimColor(s: number) {
  if (s >= 4) return 'var(--c-success)'
  if (s >= 3) return 'var(--c-warning)'
  return 'var(--c-error)'
}
</script>

<template>
  <div class="ats-sum glass-card">
    <div class="ats-sum__top">
      <div>
        <div class="ats-sum__name">{{ evaluation.candidate.name }}</div>
        <div class="ats-sum__pos">{{ evaluation.candidate.position }} · {{ evaluation.candidate.level }}</div>
      </div>
      <n-tag :type="REC_TYPE[evaluation.finalResult]" :bordered="false" round>
        {{ REC_LABEL[evaluation.finalResult] }}
      </n-tag>
    </div>

    <div class="ats-sum__score">
      <span class="ats-sum__num" :style="{ color: dimColor(overallScore) }">
        {{ overallScore.toFixed(1) }}
      </span>
      <span class="ats-sum__den">/ 5</span>
      <span class="ats-sum__cap">{ t('pages.interview.InterviewEvalSummaryCard.s1') }</span>
    </div>

    <div v-if="evaluation.comment" class="ats-sum__comment">{{ evaluation.comment }}</div>
  </div>
</template>

<style scoped>
.ats-sum { padding: var(--space-4); display: grid; gap: var(--space-3); }
.ats-sum__top { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-2); }
.ats-sum__name { font-size: var(--text-body); font-weight: 700; color: var(--ink); }
.ats-sum__pos { font-size: var(--text-meta); color: var(--ink-faint); margin-top: 2px; }

.ats-sum__score { display: flex; align-items: baseline; gap: var(--space-1); }
.ats-sum__num { font-size: 30px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.ats-sum__den { font-size: var(--text-small); color: var(--ink-faint); }
.ats-sum__cap { font-size: var(--text-meta); color: var(--ink-faint); margin-left: var(--space-1); }

.ats-sum__comment {
  margin: 0; font-size: var(--text-meta); line-height: 1.6; color: var(--ink-faint);
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}
</style>