<template>
  <!--
    统计概览 · BG 合并格（名称 + 该 BG 人数）。

    与 StatsRateCell 同理：用模板渲染而非 h()，scoped 样式才命中
    （h() 造的 VNode 不带 data-v-xxx → scoped 规则失效）。
  -->
  <div class="stats-bg">
    <span class="stats-bg__name">{{ name }}</span>
    <span v-if="total != null" class="stats-bg__total">{{ total }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  /** BG 名 */
  name: string
  /** 该 BG 下的校招生总人数；null = 不展示人数 */
  total?: number | null
}>()
</script>

<style scoped>
.stats-bg {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.3;
}
.stats-bg__name {
  font-weight: 600;
  color: var(--ink);
}
.stats-bg__total {
  color: var(--ink-faint);
  font-size: var(--text-meta);
  font-variant-numeric: tabular-nums;
}
</style>
