<template>
  <div class="weekly-schedule">
    <div class="weekly-schedule__header">
      <div class="weekly-schedule__nav">
        <n-button text size="small" @click="prevWeek" aria-label="上一周">
          <template #icon>
            <n-icon :component="ChevronBackOutline" />
          </template>
        </n-button>
        <span class="weekly-schedule__range">{{ rangeLabel }}</span>
        <n-button text size="small" @click="nextWeek" aria-label="下一周">
          <template #icon>
            <n-icon :component="ChevronForwardOutline" />
          </template>
        </n-button>
      </div>
      <n-button size="small" tertiary @click="goToday">本周</n-button>
    </div>

    <div class="weekly-schedule__grid">
      <div
        v-for="(day, idx) in weekDays"
        :key="day.iso"
        class="weekly-schedule__col"
        :class="{ 'weekly-schedule__col--today': day.isToday }"
      >
        <div class="weekly-schedule__col-header">
          <span class="weekly-schedule__weekday">{{ WEEKDAY_LABELS[idx] }}</span>
          <span class="weekly-schedule__date">{{ day.dayNum }}</span>
        </div>
        <div class="weekly-schedule__col-body">
          <div
            v-for="item in day.items"
            :key="item.id"
            class="weekly-schedule__slot"
            :title="`${item.time} ${item.candidateName} · ${item.position}`"
          >
            <span class="weekly-schedule__time">{{ item.time }}</span>
            <span class="weekly-schedule__name">{{ item.candidateName }}</span>
          </div>
          <div v-if="day.items.length === 0" class="weekly-schedule__empty">—</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronBackOutline, ChevronForwardOutline } from '@vicons/ionicons5'

export interface ScheduleItem {
  id: string
  date: string // ISO yyyy-mm-dd
  time: string // HH:mm
  candidateName: string
  position: string
}

interface Props {
  interviews?: ScheduleItem[]
}

const props = withDefaults(defineProps<Props>(), {
  interviews: () => [],
})

const WEEKDAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const today = ref(new Date())
const anchorMonday = computed(() => {
  const d = new Date(today.value)
  const day = d.getDay() // 0 (Sun) - 6 (Sat)
  // 将 day 转成 ISO: 周一=0, ..., 周日=6
  const iso = (day + 6) % 7
  d.setDate(d.getDate() - iso)
  d.setHours(0, 0, 0, 0)
  return d
})

function formatIso(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

const weekDays = computed(() => {
  const start = anchorMonday.value
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start)
    d.setDate(start.getDate() + i)
    const iso = formatIso(d)
    const items = props.interviews
      .filter((it) => it.date === iso)
      .sort((a, b) => a.time.localeCompare(b.time))
    return {
      iso,
      dayNum: d.getDate(),
      isToday: iso === formatIso(today.value),
      items,
    }
  })
})

const rangeLabel = computed(() => {
  const start = anchorMonday.value
  const end = new Date(start)
  end.setDate(start.getDate() + 6)
  return `${start.getMonth() + 1}月${start.getDate()}日 — ${end.getMonth() + 1}月${end.getDate()}日`
})

function shiftWeek(deltaWeeks: number) {
  const next = new Date(today.value)
  next.setDate(today.value.getDate() + deltaWeeks * 7)
  today.value = next
}

function prevWeek() {
  shiftWeek(-1)
}

function nextWeek() {
  shiftWeek(1)
}

function goToday() {
  today.value = new Date()
}
</script>

<style scoped>
.weekly-schedule {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.weekly-schedule__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.weekly-schedule__nav {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.weekly-schedule__range {
  color: var(--color-ink);
  font-size: var(--text-body);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  min-width: 140px;
  text-align: center;
}

.weekly-schedule__grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: var(--space-2);
}

.weekly-schedule__col {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border-hairline);
  border-radius: var(--radius-sm);
  background: var(--color-surface-raised);
  min-height: 140px;
  overflow: hidden;
}

.weekly-schedule__col--today {
  border-color: var(--color-accent);
  background: var(--color-accent-soft);
}

.weekly-schedule__col-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border-hairline);
  color: var(--color-ink-soft);
  font-size: var(--text-meta);
}

.weekly-schedule__col--today .weekly-schedule__col-header {
  color: var(--color-accent);
  font-weight: 500;
}

.weekly-schedule__weekday {
  font-weight: 500;
}

.weekly-schedule__date {
  font-variant-numeric: tabular-nums;
}

.weekly-schedule__col-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2);
  flex: 1;
}

.weekly-schedule__slot {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--color-surface-sunk);
  font-size: var(--text-meta);
  line-height: 1.3;
  cursor: default;
}

.weekly-schedule__slot:hover {
  background: var(--color-accent-soft);
}

.weekly-schedule__time {
  color: var(--color-accent);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.weekly-schedule__name {
  color: var(--color-ink);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.weekly-schedule__empty {
  color: var(--color-ink-faint);
  font-size: var(--text-meta);
  text-align: center;
  padding: var(--space-2) 0;
}
</style>
