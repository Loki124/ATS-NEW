<template>
  <div class="empty-state">
    <div class="empty-state__icon">
      <n-icon :component="icon ?? InboxOutline" :size="32" />
    </div>
    <h4 class="empty-state__title">{{ title }}</h4>
    <p class="empty-state__desc">{{ description }}</p>
    <n-button v-if="actionLabel" size="small" type="primary" @click="emit('action')">
      {{ actionLabel }}
    </n-button>
  </div>
</template>

<script setup lang="ts">
import { InboxOutline } from '@vicons/ionicons5'
import type { Component } from 'vue'

interface Props {
  title?: string
  description?: string
  actionLabel?: string
  icon?: Component
}

withDefaults(defineProps<Props>(), {
  title: '暂无内容',
  description: '当前没有需要处理的事项',
})

const emit = defineEmits<{
  (e: 'action'): void
}>()
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-8) var(--space-4);
  color: var(--color-ink-soft);
}

.empty-state__icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-pill);
  background: var(--color-surface-sunk);
  color: var(--color-ink-faint);
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state__title {
  margin: 0;
  color: var(--color-ink);
  font-size: var(--text-h3);
  font-weight: 500;
}

.empty-state__desc {
  margin: 0;
  color: var(--color-ink-faint);
  font-size: var(--text-body);
}
</style>
