<template>
  <div
    class="stat-card workbench-card"
    :class="[
      trend ? `stat-card--${trend}` : '',
      clickable ? 'stat-card--clickable' : '',
    ]"
    :role="clickable ? 'button' : undefined"
    :tabindex="clickable ? 0 : undefined"
    @click="onClick"
    @keydown.enter="onClick"
  >
    <div class="stat-card__label">
      <n-icon v-if="icon" :component="icon" :size="14" class="stat-card__icon" />
      <span>{{ title }}</span>
    </div>
    <div class="stat-card__value-row">
      <span class="stat-card__value">{{ displayValue }}</span>
      <span v-if="suffix" class="stat-card__suffix">{{ suffix }}</span>
    </div>
    <div v-if="trend || meta" class="stat-card__meta">
      <span v-if="trend === 'urgent'" class="stat-card__pill stat-card__pill--urgent">
        紧急
      </span>
      <span v-else-if="trend === 'up'" class="stat-card__pill stat-card__pill--up">
        +{{ trendValue ?? '' }}
      </span>
      <span v-else-if="trend === 'down'" class="stat-card__pill stat-card__pill--down">
        -{{ trendValue ?? '' }}
      </span>
      <span v-if="meta" class="stat-card__meta-text">{{ meta }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'

interface Props {
  title: string
  value: number | string
  suffix?: string
  trend?: 'urgent' | 'up' | 'down' | 'flat'
  trendValue?: number | string
  meta?: string
  icon?: Component
  clickable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  // 2026-06-29 花无缺: 加 suffix/trendValue/meta/icon 默认值消 vue/require-default-prop warnings
  suffix: '',
  trendValue: '',
  meta: '',
  icon: undefined,  // Component 类型默认 null/undefined
  trend: 'flat',
  clickable: false,
})

const emit = defineEmits<{
  (e: 'click'): void
}>()

const displayValue = computed(() => {
  if (typeof props.value === 'number') return props.value.toLocaleString('zh-CN')
  return props.value
})

function onClick() {
  if (props.clickable) emit('click')
}
</script>

<style scoped>
.stat-card {
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--glass-blur-card));
  -webkit-backdrop-filter: blur(var(--glass-blur-card));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  padding: var(--space-4) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  cursor: default;
  transition: border-color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out);
  min-height: 96px;
  box-shadow: var(--shadow-card);
}

.stat-card--clickable {
  cursor: pointer;
}
.stat-card--clickable:hover {
  border-color: var(--brand);
  background: var(--brand-soft);
}

.stat-card__label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 400;
}

.stat-card__icon {
  color: var(--ink-faint);
}

.stat-card__value-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-1);
}

.stat-card__value {
  color: var(--ink);
  font-size: var(--text-h2);
  font-weight: 500;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.stat-card--urgent .stat-card__value {
  color: var(--brand);
}

.stat-card__suffix {
  color: var(--ink-faint);
  font-size: var(--text-meta);
}

.stat-card__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-meta);
}

.stat-card__pill {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
  font-weight: 500;
  font-size: var(--text-meta);
  line-height: 1.4;
}

.stat-card__pill--urgent {
  background: var(--brand-soft);
  color: var(--brand);
}

.stat-card__pill--up {
  background: var(--c-success-soft);
  color: var(--c-success);
}

.stat-card__pill--down {
  background: var(--c-error-soft);
  color: var(--c-error);
}

.stat-card__meta-text {
  color: var(--ink-faint);
}
</style>
