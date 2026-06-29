<template>
  <div
    class="quick-entry"
    role="button"
    tabindex="0"
    @click="onClick"
    @keydown.enter="onClick"
  >
    <div class="quick-entry__icon">
      <n-icon :component="entry.icon" :size="20" />
    </div>
    <div class="quick-entry__body">
      <div class="quick-entry__label">{{ entry.label }}</div>
      <div class="quick-entry__sub">{{ entry.subtitle }}</div>
    </div>
    <div v-if="entry.count !== undefined" class="quick-entry__count">
      {{ entry.count }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { Component } from 'vue'

export interface QuickEntryData {
  key: string
  label: string
  subtitle: string
  count?: number
  icon: Component
  to?: string
}

interface Props {
  entry: QuickEntryData
}

const props = defineProps<Props>()

const router = useRouter()

const emit = defineEmits<{
  (e: 'click', entry: QuickEntryData): void
}>()

function onClick() {
  emit('click', props.entry)
  if (props.entry.to) router.push(props.entry.to)
}
</script>

<style scoped>
.quick-entry {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border-hairline);
  border-radius: var(--radius-sm);
  background: var(--color-surface-raised);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out);
}

.quick-entry:hover {
  border-color: var(--color-accent);
  background: var(--color-accent-soft);
}

.quick-entry__icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  background: var(--color-accent-soft);
  color: var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.quick-entry__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.quick-entry__label {
  color: var(--color-ink);
  font-size: var(--text-body);
  font-weight: 500;
  line-height: 1.3;
}

.quick-entry__sub {
  color: var(--color-ink-faint);
  font-size: var(--text-meta);
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.quick-entry__count {
  color: var(--color-accent);
  font-size: var(--text-h3);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
</style>
