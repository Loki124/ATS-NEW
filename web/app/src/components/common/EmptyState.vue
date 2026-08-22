<template>
  <div class="empty-state">
    <div class="empty-icon">{{ icon || '📋' }}</div>
    <h3 class="empty-title">{{ title || '暂无数据' }}</h3>
    <p v-if="description" class="empty-desc">{{ description }}</p>
    <div v-if="actionLabel" class="empty-actions">
      <button class="btn btn-primary" @click="$emit('action')">{{ actionLabel }}</button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  icon?: string
  title?: string
  description?: string
  actionLabel?: string
}>()
defineEmits<{ (e: 'action'): void }>()
</script>

<style scoped>
.empty-state {
  display: flex; flex-direction: column; align-items: center;
  gap: var(--space-3);
  padding: var(--space-8) var(--space-4);
  text-align: center;
}
.empty-icon { font-size: 48px; line-height: 1; opacity: .8; }
.empty-title { font-size: var(--text-h3); font-weight: 600; color: var(--ink); margin: 0; }
.empty-desc { color: var(--ink-soft); font-size: var(--text-body); margin: 0; max-width: 36ch; }
.empty-actions { margin-top: var(--space-3); }
</style>