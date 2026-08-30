<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { Target } from 'lucide-vue-next'
interface ScoreResult {
  score: number
  passed: boolean
  dimensions: Array<{ name: string; score: number }>
}
const props = defineProps<{ score: ScoreResult }>()

function dimColor(s: number) {
  if (s >= 80) return 'var(--c-success)'
  if (s >= 60) return 'var(--c-warning)'
  return 'var(--c-error)'
}
</script>

<template>
  <div class="score-panel glass-card">
    <div class="score-panel-title"><NIcon :size="16" style="vertical-align:-2px;margin-right:4px;color:var(--brand)" aria-hidden="true"><Target /></NIcon>模拟评分结果</div>
    <div class="score-overall-row">
      <div :class="['score-big', score.passed ? 'pass' : 'fail']">{{ score.score }}</div>
      <div>
        <div class="score-subtitle">综合匹配分</div>
        <span :class="['score-pass-tag', score.passed ? 'pass' : 'fail']">
          {{ score.passed ? '通过' : '未通过' }}
        </span>
      </div>
    </div>
    <div class="score-hint">及格线：60分 · 仅供参考</div>
    <div v-for="dim in score.dimensions" :key="dim.name" class="sc-dim">
      <span class="sc-dim-name">{{ dim.name }}</span>
      <div class="sc-dim-bar">
        <div class="sc-dim-fill" :style="{ width: `${dim.score}%`, background: dimColor(dim.score) }"></div>
      </div>
      <span class="sc-dim-score">{{ dim.score }}</span>
    </div>
  </div>
</template>

<style scoped>
.score-panel {
  /* .glass-card 提供半透明背景+blur+描边+圆角+阴影 */
  padding: var(--space-3);
  margin-top: var(--space-2);
}
.score-panel-title {
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--ink);
  margin-bottom: var(--space-2);
}
.score-overall-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.score-big {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.score-big.pass { color: var(--c-success); }
.score-big.fail { color: var(--c-error); }
.score-subtitle {
  font-size: var(--text-meta);
  color: var(--ink-soft);
}
.score-pass-tag {
  padding: 2px var(--space-2);
  border-radius: var(--radius-pill);
  font-size: var(--text-meta);
  font-weight: 600;
  display: inline-block;
  margin-top: var(--space-1);
}
.score-pass-tag.pass { background: var(--c-success-soft); color: var(--c-success); }
.score-pass-tag.fail { background: var(--c-error-soft);   color: var(--c-error); }
.score-hint {
  font-size: var(--text-meta);
  color: var(--ink-faint);
  margin-bottom: var(--space-2);
}
.sc-dim {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
  font-size: var(--text-small);
}
.sc-dim-name {
  width: 70px;
  color: var(--ink-soft);
  flex-shrink: 0;
}
.sc-dim-bar {
  flex: 1;
  height: 6px;
  background: var(--glass-bg-input);
  border-radius: var(--radius-pill);
  overflow: hidden;
  border: 1px solid var(--border-hairline);
}
.sc-dim-fill {
  height: 100%;
  border-radius: var(--radius-pill);
  transition: width var(--duration-base) var(--ease-out);
}
.sc-dim-score {
  width: 28px;
  text-align: right;
  font-weight: 600;
  flex-shrink: 0;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
</style>