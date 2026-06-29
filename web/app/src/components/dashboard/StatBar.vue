<template>
  <div class="stat-bar" role="group" aria-label="关键指标">
    <div
      v-for="(stat, idx) in stats"
      :key="stat.key"
      class="stat-bar__item"
      :class="[`stat-bar__item--${stat.accentColor}`]"
      :role="stat.href ? 'button' : undefined"
      :tabindex="stat.href ? 0 : undefined"
      @click="onClick(stat)"
      @keydown.enter="onClick(stat)"
    >
      <span class="stat-bar__label">{{ stat.label }}</span>
      <span class="stat-bar__value">{{ stat.value }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

export interface StatItem {
  key: string
  label: string
  value: number | string
  icon?: string
  accentColor: 'amber' | 'rose' | 'sky' | 'emerald'
  href?: string
}

defineProps<{ stats: StatItem[] }>()

const router = useRouter()
function onClick(stat: StatItem) {
  if (stat.href) router.push(stat.href)
}
</script>

<style scoped>
.stat-bar {
  display: flex;
  align-items: stretch;
  height: 64px;
  background: var(--paper-2, #fafafa);
  border: 1px solid var(--paper-3, #e5e5e5);
  border-radius: 12px;
  overflow: hidden;
}
.stat-bar__item {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 8px 24px;
  cursor: default;
  transition: background 0.15s;
  position: relative;
}
.stat-bar__item[role='button'] {
  cursor: pointer;
}
.stat-bar__item[role='button']:hover {
  background: var(--paper-3, #e5e5e5);
}
.stat-bar__item + .stat-bar__item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 1px;
  background: var(--paper-3, #e5e5e5);
}
.stat-bar__label {
  font-size: 12px;
  color: var(--ink-2, #666);
  margin-bottom: 4px;
}
.stat-bar__value {
  font-size: 24px;
  font-weight: 600;
  color: var(--ink-1, #222);
  line-height: 1;
}
.stat-bar__item--amber .stat-bar__value { color: #d97706; }
.stat-bar__item--rose .stat-bar__value { color: #e11d48; }
.stat-bar__item--sky .stat-bar__value { color: #0284c7; }
.stat-bar__item--emerald .stat-bar__value { color: #059669; }
@media (max-width: 1280px) {
  .stat-bar__item { padding: 8px 16px; }
  .stat-bar__value { font-size: 20px; }
}
</style>
