<template>
  <div class="skeleton-card" :class="`skeleton-card--${variant}`">
    <div class="skeleton-card__header">
      <div class="skeleton-bar skeleton-bar--title" />
      <div v-if="variant === 'stat'" class="skeleton-bar skeleton-bar--value" />
    </div>
    <div v-if="variant !== 'stat'" class="skeleton-card__body">
      <div class="skeleton-bar skeleton-bar--line" />
      <div class="skeleton-bar skeleton-bar--line skeleton-bar--short" />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * SkeletonCard - 骨架占位
 *
 * Plan O: Dashboard 子组件 lazy load 时的占位
 *  variants:
 *    - stat:    用于 StatCard (标题 + 数值条)
 *    - list:    用于 JobCard / ScreeningListItem (列表行)
 *    - panel:   用于 WeeklySchedule / MatterList (完整面板)
 *    - default: 通用
 */
withDefaults(defineProps<{
  variant?: 'stat' | 'list' | 'panel' | 'default'
}>(), { variant: 'default' })
</script>

<style scoped>
.skeleton-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--card-color, #fff);
  border-radius: 8px;
  border: 1px solid var(--border-color, rgba(0, 0, 0, 0.06));
  min-height: 80px;
}
.skeleton-card__header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.skeleton-card__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.skeleton-bar {
  height: 12px;
  border-radius: 4px;
  background: linear-gradient(90deg,
    rgba(0, 0, 0, 0.04) 0%,
    rgba(0, 0, 0, 0.08) 50%,
    rgba(0, 0, 0, 0.04) 100%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
}
.skeleton-bar--title { width: 60%; }
.skeleton-bar--value { width: 40%; height: 24px; }
.skeleton-bar--line { width: 100%; }
.skeleton-bar--short { width: 60%; }

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
