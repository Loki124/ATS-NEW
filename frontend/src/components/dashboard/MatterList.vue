<template>
  <div class="matter-list">
    <div v-if="matters.length === 0" class="matter-list__empty">
      <n-empty description="暂无相关事项" size="small" />
    </div>
    <div
      v-for="matter in matters"
      :key="matter.id"
      class="matter-list__row"
      :class="`matter-list__row--${matter.tone ?? 'neutral'}`"
    >
      <div class="matter-list__cell matter-list__cell--title">
        <n-icon
          v-if="matter.icon"
          :component="matter.icon"
          :size="14"
          class="matter-list__icon"
        />
        <span class="matter-list__title-text">{{ matter.title }}</span>
      </div>
      <div class="matter-list__cell matter-list__cell--meta">
        {{ matter.meta }}
      </div>
      <div class="matter-list__cell matter-list__cell--time">
        {{ matter.time }}
      </div>
      <div class="matter-list__cell matter-list__cell--action">
        <n-button
          v-if="matter.actionLabel"
          size="tiny"
          tertiary
          type="primary"
          @click="emit('action', matter)"
        >
          {{ matter.actionLabel }}
        </n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

export type MatterTone = 'urgent' | 'warning' | 'info' | 'neutral'

export interface MatterItem {
  id: string
  title: string
  meta?: string
  time?: string
  tone?: MatterTone
  icon?: Component
  actionLabel?: string
}

interface Props {
  matters: MatterItem[]
}

defineProps<Props>()

const emit = defineEmits<{
  (e: 'action', matter: MatterItem): void
}>()
</script>

<style scoped>
.matter-list {
  display: flex;
  flex-direction: column;
}

.matter-list__empty {
  padding: var(--space-6) 0;
  display: flex;
  justify-content: center;
}

.matter-list__row {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr) auto auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-2);
  border-bottom: 1px solid var(--color-border-hairline);
  font-size: var(--text-body);
}

.matter-list__row:last-child {
  border-bottom: none;
}

.matter-list__row--urgent .matter-list__title-text {
  color: var(--color-accent);
  font-weight: 500;
}

.matter-list__cell--title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.matter-list__icon {
  color: var(--color-accent);
  flex-shrink: 0;
}

.matter-list__title-text {
  color: var(--color-ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.matter-list__cell--meta {
  color: var(--color-ink-soft);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.matter-list__cell--time {
  color: var(--color-ink-faint);
  font-size: var(--text-meta);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.matter-list__cell--action {
  display: flex;
  justify-content: flex-end;
}
</style>
