<script setup lang="ts">
export type Status = 'processing' | 'clean' | 'unocc' | 'occupied'
defineProps<{ status: Status }>()

const config = {
  clean: { icon: '✅', text: '系统中未发现重复简历，该候选人可正常入库。' },
  unocc: { icon: 'ℹ️', text: '系统中已有同名简历，但未被任何流程占用。提交时系统会合并新旧简历信息。' },
  occupied: { icon: '⚠️', text: '该候选人在系统中已被占用。当前被其他流程锁定，请选择处理方式。' },
  processing: { icon: '⏳', text: '简历正在处理中，请稍候...' },
}
</script>

<template>
  <div :class="['cb', $props.status]">
    <span class="cb-icon">{{ config[$props.status]?.icon }}</span>
    <div>{{ config[$props.status]?.text }}</div>
  </div>
</template>

<style scoped>
.cb {
  padding: var(--space-2) var(--space-3);
  border-radius: 8px;
  font-size: 11px;
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  line-height: 1.5;
}
.cb-icon { font-size: var(--fs-16); flex-shrink: 0; margin-top: 1px; }
.cb.clean { background: var(--sl); color: var(--c-success-deep); border: 1px solid var(--c-success-bg); }
.cb.unocc { background: var(--wl); color: var(--c-warning-deep); border: 1px solid var(--c-warning-bg); }
.cb.occupied { background: var(--dl); color: var(--c-error-deep); border: 1px solid var(--c-error-bg); }
.cb.processing { background: var(--bl); color: var(--c-info-deep); border: 1px solid var(--c-info-bg); }
</style>