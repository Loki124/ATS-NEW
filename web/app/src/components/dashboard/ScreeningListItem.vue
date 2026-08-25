<template>
  <div class="screening-item" @click="onClick">
    <div class="screening-item__head">
      <span class="screening-item__title">{{ screening.title }}</span>
      <n-tag
        v-if="screening.tag"
        :type="screening.tagType ?? 'default'"
        size="small"
        :bordered="false"
        round
      >
        {{ screening.tag }}
      </n-tag>
    </div>
    <div class="screening-item__meta">
      <span>{{ screening.department }}</span>
      <span class="screening-item__dot">·</span>
      <span>{{ screening.location }}</span>
      <span class="screening-item__dot">·</span>
      <span>{{ screening.salary }}</span>
    </div>
    <div class="screening-item__foot">
      <span class="screening-item__time">{{ screening.postedAt }}</span>
      <span class="screening-item__apply">
        <n-icon :component="PersonAddOutline" :size="12" />
        {{ screening.applicantCount ?? 0 }} 份简历
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { PersonAddOutline } from '@vicons/ionicons5'

export type ScreeningTagType = 'default' | 'primary' | 'info' | 'success' | 'warning' | 'error'

export interface ScreeningItemData {
  id: string
  title: string
  department: string
  location: string
  salary: string
  postedAt: string
  applicantCount?: number
  tag?: string
  tagType?: ScreeningTagType
}

interface Props {
  screening: ScreeningItemData
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'click', item: ScreeningItemData): void
}>()

function onClick() {
  emit('click', props.screening)
}
</script>

<style scoped>
.screening-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm);
  background: var(--surface);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out);
}

.screening-item:hover {
  border-color: var(--brand);
  background: var(--brand-soft);
}

.screening-item__head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  justify-content: space-between;
}

.screening-item__title {
  color: var(--ink);
  font-size: var(--text-body);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.screening-item__meta {
  color: var(--ink-faint);
  font-size: var(--text-meta);
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.screening-item__dot {
  color: var(--ink-faint);
}

.screening-item__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--ink-soft);
  font-size: var(--text-meta);
}

.screening-item__apply {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: var(--brand);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
</style>
