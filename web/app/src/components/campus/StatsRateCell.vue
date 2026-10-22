<template>
  <!--
    统计概览 · 比率单元格（数字 + 量度条）。

    为什么用独立组件而不是在列 render 里 h()：
    Vue 的 scoped 样式只作用于**模板里的元素**；列 render 里 h() 造的 VNode 不带
    data-v-xxx → scoped 规则完全不命中（见 web/app/scripts/check-h-render-scope.mjs）。
    本组件用模板渲染，样式自然生效，且不污染全局。

    数字是主信息，量度条是**冗余编码**（同一条信息的第二通道）——
    不靠颜色单独承载信息，颜色失效时数字依然可读。
  -->
  <div class="stats-rate" :class="`stats-rate--${tone}`">
    <span class="stats-rate__value" :class="{ 'stats-rate__value--none': value == null }">
      {{ display }}
    </span>
    <span class="stats-rate__track" aria-hidden="true">
      <span class="stats-rate__fill" :style="{ transform: `scaleX(${ratio})` }"></span>
    </span>
  </div>
</template>

<script lang="ts">
/** 语义档位：good / warn / bad / neutral（neutral = 无好坏之分，如女生比）。 */
export type RateTone = 'good' | 'warn' | 'bad' | 'neutral'
</script>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 比率（0~1）；null = 分母为 0，「无意义」——必须与真实的 0 区分 */
    value: number | null
    tone?: RateTone
  }>(),
  { tone: 'neutral' },
)

/** null → 「—」（不是 0%）。 */
const display = computed(() =>
  props.value == null ? '—' : `${(props.value * 100).toFixed(1)}%`,
)

/** 量度条比例：null 不画条（长度 0），并钳制到 0~1 防越界。 */
const ratio = computed(() =>
  props.value == null ? 0 : Math.max(0, Math.min(1, props.value)),
)
</script>

<style scoped>
.stats-rate {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  width: 100%;
}
.stats-rate__value {
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  color: var(--ink-soft);
}
/* 「—」= 分母为 0、无意义：比真实数值更淡，避免与 0% 混淆 */
.stats-rate__value--none {
  color: var(--ink-faint);
  opacity: 0.7;
}
.stats-rate__track {
  width: 100%;
  height: 3px;
  border-radius: 2px;
  background: var(--border-hairline);
  overflow: hidden;
}
/* 只动 transform（不改 width）→ 天然满足 R-206「只动画 transform / opacity」 */
.stats-rate__fill {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 2px;
  transform-origin: left center;
  background: var(--ink-faint);
}
.stats-rate--good .stats-rate__fill {
  background: var(--c-success-deep);
}
.stats-rate--warn .stats-rate__fill {
  background: var(--c-warning-deep);
}
.stats-rate--bad .stats-rate__fill {
  background: var(--c-error-deep);
}
.stats-rate--neutral .stats-rate__fill {
  background: var(--c-info-deep);
}
</style>
