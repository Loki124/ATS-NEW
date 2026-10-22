<template>
  <!-- 2026-10-21 (整改卡 E2 · AGENTS.md R-224): 抽屉回改居中弹窗。
       内容区固定高度 (R-223) + 仅内容区滚动 (R-215) + mask-closable=false (防误触丢失)。 -->
  <n-modal
    :show="show"
    preset="card"
    :title="formattedDate"
    :style="{ width: '400px', maxWidth: '95vw' }"
    :content-style="{ height: 'min(520px, calc(88vh - 180px))', overflowY: 'auto' }"
    :mask-closable="false"
    :bordered="false"
    @update:show="$emit('update:show', $event)"
  >
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
  </n-modal>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import dayjs from 'dayjs'
import { NEmpty, NModal } from 'naive-ui'

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
  gap: var(--space-2);
}

.schedule-drawer__item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--glass-bg-panel);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s;
}

.schedule-drawer__item:hover {
  background: var(--brand-soft);
}

.schedule-drawer__time {
  font-weight: 600;
  color: var(--brand-fg);
  min-width: 50px;
  font-variant-numeric: tabular-nums;
}

.schedule-drawer__detail {
  flex: 1;
}

.schedule-drawer__name {
  font-weight: 500;
  color: var(--ink);
}

.schedule-drawer__position {
  font-size: var(--fs-12);
  color: var(--ink-soft);
}
</style>
