<script setup lang="ts">
/**
 * 面试评价 · 紧凑摘要卡（嵌入候选人详情 / 列表）
 * 与 InterviewEvaluationModal 共用 Evaluation 数据结构。
 */
import { computed } from 'vue'
import { NTag } from 'naive-ui'
import type { Evaluation, RecValue } from './InterviewEvaluationModal.vue'

const props = defineProps<{ evaluation: Evaluation }>()

const REC_LABEL: Record<RecValue, string> = {
  PASS: '通过', MANAGER: '经理', DISCUSS: '面议', FAIL: '不通过',
}
const REC_TYPE: Record<RecValue, 'success' | 'info' | 'warning' | 'error'> = {
  PASS: 'success', MANAGER: 'info', DISCUSS: 'warning', FAIL: 'error',
}
const allDims = computed(() => props.evaluation.groups.flatMap(g => g.items))
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
        <div class="ats-sum__pos">{{ evaluation.candidate.position }} · {{ evaluation.candidate.round }}</div>
      </div>
      <n-tag :type="REC_TYPE[evaluation.recommendation]" :bordered="false" round>
        {{ REC_LABEL[evaluation.recommendation] }}
      </n-tag>
    </div>

    <div class="ats-sum__score">
      <span class="ats-sum__num" :style="{ color: dimColor(evaluation.overallScore) }">
        {{ evaluation.overallScore.toFixed(1) }}
      </span>
      <span class="ats-sum__den">/ 5</span>
      <span class="ats-sum__cap">综合评分</span>
    </div>

    <div class="ats-sum__dims">
      <div v-for="d in allDims" :key="d.key" class="ats-sum__dim">
        <span class="ats-sum__dim-name">{{ d.name }}</span>
        <div class="ats-sum__bar">
          <div class="ats-sum__fill" :style="{ width: (d.score * 20) + '%', background: dimColor(d.score) }" />
        </div>
        <span class="ats-sum__dim-score" :style="{ color: dimColor(d.score) }">{{ d.score }}</span>
      </div>
    </div>

    <p class="ats-sum__comment">{{ evaluation.comment }}</p>
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

.ats-sum__dims { display: grid; gap: var(--space-2); }
.ats-sum__dim { display: grid; grid-template-columns: 64px 1fr 22px; align-items: center; gap: var(--space-2); }
.ats-sum__dim-name { font-size: var(--text-meta); color: var(--ink-soft); }
.ats-sum__bar { height: 6px; background: var(--glass-bg-input); border-radius: var(--radius-pill); overflow: hidden; border: 1px solid var(--border-hairline); }
.ats-sum__fill { height: 100%; border-radius: var(--radius-pill); transition: width var(--duration-base) var(--ease-out); }
.ats-sum__dim-score { font-size: var(--text-meta); font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; }

.ats-sum__comment {
  margin: 0; font-size: var(--text-meta); line-height: 1.6; color: var(--ink-faint);
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}
</style>
