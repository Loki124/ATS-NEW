<template>
  <n-drawer :show="show" :width="400" placement="right" @update:show="$emit('update:show', $event)">
    <n-drawer-content :title="formattedDate" closable>
      <div v-if="items.length === 0" class="schedule-drawer__empty">
        <n-empty description="当天无日程" />
      </div>
      <div v-else class="schedule-drawer__list">
        <div
          v-for="item in items"
          :key="item.id"
          class="schedule-drawer__item"
          @click="$emit('item-click', item)"
        >
          <span class="schedule-drawer__time">{{ item.time }}</span>
          <div class="schedule-drawer__detail">
            <div class="schedule-drawer__name">{{ item.candidateName }}</div>
            <div class="schedule-drawer__position">{{ item.position }}</div>
          </div>
        </div>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import dayjs from 'dayjs'
import { NDrawer, NDrawerContent, NEmpty } from 'naive-ui'

// ScheduleItem 与 WeeklySchedule.vue 字段一致(为避免 .vue 文件循环引用,这里本地重新声明)
export interface ScheduleItem {
  id: string
  date: string
  time: string
  candidateName: string
  position: string
  [key: string]: unknown
}

const props = defineProps<{
  show: boolean
  date: string
  items: ScheduleItem[]
}>()

defineEmits<{
  'update:show': [v: boolean]
  'item-click': [item: ScheduleItem]
}>()

const formattedDate = computed(() => {
  if (!props.date) return ''
  return dayjs(props.date).format('YYYY年M月D日 dddd')
})
</script>

<style scoped>
.schedule-drawer__empty {
  padding: 40px 0;
}

.schedule-drawer__list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.schedule-drawer__item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--color-surface-sunk);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s;
}

.schedule-drawer__item:hover {
  background: var(--color-accent-soft);
}

.schedule-drawer__time {
  font-weight: 600;
  color: var(--color-accent);
  min-width: 50px;
  font-variant-numeric: tabular-nums;
}

.schedule-drawer__detail {
  flex: 1;
}

.schedule-drawer__name {
  font-weight: 500;
  color: var(--color-ink);
}

.schedule-drawer__position {
  font-size: 12px;
  color: var(--color-ink-soft);
}
</style>
