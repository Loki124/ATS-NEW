<script setup lang="ts">
type Status = 'processing' | 'clean' | 'unocc' | 'occupied'
const props = defineProps<{ status: Status }>()

const config: Record<Status, { label: string; color: string }> = {
  clean: { label: '无重复', color: 'g' },
  unocc: { label: '未占用', color: 'y' },
  occupied: { label: '已占用', color: 'r' },
  processing: { label: '处理中', color: 'b' },
}

const cfg = config[props.status] || { label: '未知', color: 'g' }
</script>

<template>
  <span :class="['tag', `tag-${cfg.color}`]">
    <span :class="['td', `td-${cfg.color}`]"></span>
    {{ cfg.label }}
  </span>
</template>

<style scoped>
.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
}
.td {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}
.tag-g { background: var(--sl); color: #065F46; }
.tag-y { background: var(--wl); color: #92400E; }
.tag-r { background: var(--dl); color: #991B1B; }
.tag-b { background: var(--bl); color: #1E40AF; }
.td-g { background: var(--s); }
.td-y { background: var(--w); }
.td-r { background: var(--d); }
.td-b { background: var(--b); animation: pulse2 1s infinite; }
@keyframes pulse2 { 0%,100% { opacity: 1 } 50% { opacity: 0.3 } }
</style>