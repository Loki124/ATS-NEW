<template>
  <span
    class="ki"
    :class="kind === 'derived' ? 'ki-derived' : 'ki-atomic'"
    :style="{ fontSize: size + 'px' }"
    :title="kind === 'derived' ? t('metrics.legend.derived') : t('metrics.legend.atomic')"
  >
    <svg v-if="kind === 'atomic'" viewBox="0 0 24 24" width="1em" height="1em" aria-hidden="true">
      <circle cx="12" cy="12" r="2" fill="currentColor" stroke="none" />
      <ellipse cx="12" cy="12" rx="9" ry="3.4" transform="rotate(0 12 12)" />
      <ellipse cx="12" cy="12" rx="9" ry="3.4" transform="rotate(60 12 12)" />
      <ellipse cx="12" cy="12" rx="9" ry="3.4" transform="rotate(120 12 12)" />
    </svg>
    <svg v-else viewBox="0 0 24 24" width="1em" height="1em" aria-hidden="true">
      <line x1="6" y1="12" x2="18" y2="6" />
      <line x1="6" y1="12" x2="18" y2="18" />
      <circle cx="6" cy="12" r="3" fill="currentColor" stroke="none" />
      <circle cx="18" cy="6" r="3" />
      <circle cx="18" cy="18" r="3" />
    </svg>
  </span>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

withDefaults(
  defineProps<{
    /** atomic = 原子指标（对象路径）/ derived = 派生指标（参数化 Handler） */
    kind: 'atomic' | 'derived'
    /** 图标字号（px），默认 16；SVG 内部用 1em 跟随字号 */
    size?: number
  }>(),
  { size: 16 },
)

const { t } = useI18n()
</script>

<style scoped>
.ki {
  display: inline-flex;
  vertical-align: -2px;
}
.ki svg {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
}
.ki-atomic {
  color: var(--brand);
}
.ki-derived {
  color: var(--brand-grad-a);
}
</style>
