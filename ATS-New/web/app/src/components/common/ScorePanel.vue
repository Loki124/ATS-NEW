<script setup lang="ts">
interface ScoreResult {
  score: number
  passed: boolean
  dimensions: Array<{ name: string; score: number }>
}
const props = defineProps<{ score: ScoreResult }>()

function dimColor(s: number) {
  if (s >= 80) return 'var(--s)'
  if (s >= 60) return 'var(--w)'
  return 'var(--d)'
}
</script>

<template>
  <div class="score-panel">
    <div class="score-panel-title">🎯 模拟评分结果</div>
    <div class="score-overall-row">
      <div :class="['score-big', score.passed ? 'pass' : 'fail']">{{ score.score }}</div>
      <div>
        <div style="font-size:11px;color:var(--g6);">综合匹配分</div>
        <span :class="['score-pass-tag', score.passed ? 'pass' : 'fail']">
          {{ score.passed ? '通过' : '未通过' }}
        </span>
      </div>
    </div>
    <div style="font-size:10px;color:var(--g5);margin-bottom:8px;">及格线：60分 · 仅供参考</div>
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
  border: 1px solid var(--g3);
  border-radius: 8px;
  padding: 12px;
  background: var(--g1);
  margin-top: 8px;
}
.score-panel-title { font-size: 11px; font-weight: 600; color: var(--g7); margin-bottom: 8px; }
.score-overall-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.score-big { font-size: 28px; font-weight: 700; line-height: 1; }
.score-big.pass { color: var(--s); }
.score-big.fail { color: var(--d); }
.score-pass-tag { padding: 2px 8px; border-radius: 20px; font-size: 10px; font-weight: 600; display: inline-block; margin-top: 2px; }
.score-pass-tag.pass { background: var(--sl); color: #065F46; }
.score-pass-tag.fail { background: var(--dl); color: #991B1B; }
.sc-dim { display: flex; align-items: center; gap: 8px; margin-top: 6px; font-size: 11px; }
.sc-dim-name { width: 70px; color: var(--g6); flex-shrink: 0; }
.sc-dim-bar { flex: 1; height: 6px; background: var(--g2); border-radius: 3px; overflow: hidden; }
.sc-dim-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
.sc-dim-score { width: 28px; text-align: right; font-weight: 600; flex-shrink: 0; }
</style>
