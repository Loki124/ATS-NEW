<template>
  <div class="stat-bar" role="group" aria-label="关键指标">
    <div
      v-for="stat in stats"
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
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--glass-blur-card));
  -webkit-backdrop-filter: blur(var(--glass-blur-card));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}
.stat-bar__item {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: var(--space-2) var(--space-6);
  cursor: default;
  transition: background var(--duration-fast) var(--ease-out);
  position: relative;
}
.stat-bar__item[role='button'] {
  cursor: pointer;
}
.stat-bar__item[role='button']:hover {
  background: var(--brand-tint);
}
.stat-bar__item + .stat-bar__item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 1px;
  background: var(--border-hairline);
}
.stat-bar__label {
  font-size: var(--fs-12);
  color: var(--ink-soft);
  margin-bottom: var(--space-1);
}
.stat-bar__value {
  font-size: var(--fs-24);
  font-weight: 600;
  color: var(--ink);
  line-height: 1;
}
/* 强调色 → 语义四态（DESIGN.md §4 状态色） */
.stat-bar__item--amber .stat-bar__value { color: var(--c-warning); }
.stat-bar__item--rose .stat-bar__value { color: var(--c-error); }
.stat-bar__item--sky .stat-bar__value { color: var(--c-info); }
.stat-bar__item--emerald .stat-bar__value { color: var(--c-success); }

/* === 响应式 4→2→1（DESIGN.md §11 断点 · T4.1 收口）===
 *   ≥1281px: 4 列横向（默认）
 *   ≤1280px: padding/字号微缩
 *   ≤768px:  折叠为 2×2 网格
 *   ≤480px:  折叠为单列
 */
@media (max-width: 1280px) {
  .stat-bar__item { padding: var(--space-2) var(--space-4); }
  .stat-bar__value { font-size: var(--fs-20); }
}
@media (max-width: 768px) {
  .stat-bar {
    flex-wrap: wrap;
    height: auto;
  }
  .stat-bar__item {
    flex: 1 1 calc(50% - 1px);
    padding: 10px 14px;
    min-height: 56px;
  }
  .stat-bar__item + .stat-bar__item::before {
    display: none; /* 横向分隔线在 wrap 模式下无意义 */
  }
  /* 2×2 网格的网格线用 nth-child 模拟 */
  .stat-bar__item:nth-child(odd) {
    border-right: 1px solid var(--border-hairline);
  }
  .stat-bar__item:nth-child(1),
  .stat-bar__item:nth-child(2) {
    border-bottom: 1px solid var(--border-hairline);
  }
}
@media (max-width: 480px) {
  .stat-bar__item {
    flex: 1 1 100%;
    border-right: none !important;
  }
  .stat-bar__item:not(:last-child) {
    border-bottom: 1px solid var(--border-hairline) !important;
  }
}
</style>
