<script setup lang="ts">
export type Status = 'processing' | 'clean' | 'unocc' | 'occupied'
const props = defineProps<{ status: Status }>()

const config: Record<Status, { label: string; tone: 'success' | 'warning' | 'error' | 'info' }> = {
  clean:      { label: '无重复',  tone: 'success' },
  unocc:      { label: '未占用',  tone: 'warning' },
  occupied:   { label: '已占用',  tone: 'error' },
  processing: { label: '处理中',  tone: 'info' },
}

const cfg = config[props.status] || { label: '未知', tone: 'success' as const }
</script>

<template>
  <span :class="['tag', `tag-${cfg.tone}`]">
    <span :class="['td', `td-${cfg.tone}`]"></span>
    {{ cfg.label }}
  </span>
</template>

<style scoped>
.tag {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 2px 7px;
  border-radius: var(--radius-pill);
  font-size: var(--text-meta);
  font-weight: 500;
  white-space: nowrap;
  line-height: 1.6;
}
.td {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}
/* 语义四态（DESIGN.md §4 Badges · v2 液态玻璃） */
.tag-success { background: var(--c-success-soft); color: var(--c-success); }
.tag-warning { background: var(--c-warning-soft); color: var(--c-warning); }
.tag-error   { background: var(--c-error-soft);   color: var(--c-error); }
.tag-info    { background: var(--c-info-soft);    color: var(--c-info); }

.td-success { background: var(--c-success); }
.td-warning { background: var(--c-warning); }
.td-error   { background: var(--c-error); }
.td-info    { background: var(--c-info); animation: status-pulse 1s infinite; }

@keyframes status-pulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.3 } }
</style>