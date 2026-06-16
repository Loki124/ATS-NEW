<template>
  <div class="weekly-schedule">
    <div class="weekly-schedule__header">
      <div class="weekly-schedule__nav">
        <n-button text size="small" @click="prev" :aria-label="mode === 'week' ? '上一周' : '上一月'">
          <template #icon>
            <n-icon :component="ChevronBackOutline" />
          </template>
        </n-button>
        <span class="weekly-schedule__range">{{ rangeLabel }}</span>
        <n-button text size="small" @click="next" :aria-label="mode === 'week' ? '下一周' : '下一月'">
          <template #icon>
            <n-icon :component="ChevronForwardOutline" />
          </template>
        </n-button>
      </div>
      <div class="weekly-schedule__segmented" role="radiogroup" aria-label="视图模式">
        <button
          type="button"
          class="weekly-schedule__segment"
          :class="{ 'weekly-schedule__segment--active': mode === 'week' }"
          role="radio"
          :aria-checked="mode === 'week'"
          data-testid="mode-week"
          @click="mode = 'week'"
        >
          本周
        </button>
        <button
          type="button"
          class="weekly-schedule__segment"
          :class="{ 'weekly-schedule__segment--active': mode === 'month' }"
          role="radio"
          :aria-checked="mode === 'month'"
          data-testid="mode-month"
          @click="mode = 'month'"
        >
          本月
        </button>
      </div>
      <n-button size="small" tertiary @click="goToday">{{ mode === 'week' ? '本周' : '本月' }}</n-button>
    </div>

    <!-- Week 模式:7 列横排 -->
    <div v-if="mode === 'week'" class="weekly-schedule__grid">
      <div
        v-for="(day, idx) in weekDays"
        :key="day.iso"
        class="weekly-schedule__col"
        :class="{ 'weekly-schedule__col--today': day.isToday }"
        @click="openDay(day.iso)"
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
            @click.stop="onItemClick(item)"
          >
            <span class="weekly-schedule__time">{{ item.time }}</span>
            <span class="weekly-schedule__name">{{ item.candidateName }}</span>
          </div>
          <div v-if="day.items.length === 0" class="weekly-schedule__empty">—</div>
        </div>
      </div>
    </div>

    <!-- Month 模式:5/6 行 × 7 列 -->
    <div v-else class="month-grid">
      <div class="month-grid__header">
        <span v-for="(label, i) in WEEKDAY_LABELS" :key="i">{{ label }}</span>
      </div>
      <div class="month-grid__body">
        <div
          v-for="cell in monthCells"
          :key="cell.iso"
          class="month-grid__cell"
          :class="{
            'month-grid__cell--today': cell.isToday,
            'month-grid__cell--other': !cell.inMonth,
          }"
          @click="openDay(cell.iso)"
        >
          <span class="month-grid__date">{{ cell.dayNum }}</span>
          <div class="month-grid__dots">
            <span
              v-for="item in cell.items.slice(0, 2)"
              :key="item.id"
              class="month-grid__dot"
              :title="`${item.time} ${item.candidateName}`"
            />
            <span v-if="cell.items.length > 2" class="month-grid__more">+{{ cell.items.length - 2 }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 抽屉 -->
    <ScheduleDayDrawer
      :show="drawerShow"
      :date="drawerDate"
      :items="drawerItems"
      @update:show="drawerShow = $event"
      @item-click="onItemClick"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronBackOutline, ChevronForwardOutline } from '@vicons/ionicons5'
import dayjs from 'dayjs'
import { NButton, NIcon } from 'naive-ui'
import ScheduleDayDrawer from './ScheduleDayDrawer.vue'

export interface ScheduleItem {
  id: string
  date: string // ISO yyyy-mm-dd
  time: string // HH:mm
  candidateName: string
  position: string
  [key: string]: unknown
}

const props = withDefaults(defineProps<{ interviews?: ScheduleItem[] }>(), { interviews: () => [] })

const emit = defineEmits<{
  openDrawer: [date: string]
  itemClick: [item: ScheduleItem]
}>()

const WEEKDAY_LABELS = ['一', '二', '三', '四', '五', '六', '日']
const mode = ref<'week' | 'month'>('week')
const cursor = ref(dayjs())

// ===== Week 模式 =====
const weekStart = computed(() => cursor.value.startOf('week').add(1, 'day')) // 周一
const weekDays = computed(() => {
  const days = []
  for (let i = 0; i < 7; i++) {
    const d = weekStart.value.add(i, 'day')
    const iso = d.format('YYYY-MM-DD')
    days.push({
      iso,
      dayNum: d.date(),
      isToday: d.isSame(dayjs(), 'day'),
      items: props.interviews.filter((it) => it.date === iso),
    })
  }
  return days
})

// ===== Month 模式 =====
const monthCells = computed(() => {
  const first = cursor.value.startOf('month')
  const gridStart = first.startOf('week').add(1, 'day')
  const cells = []
  for (let i = 0; i < 42; i++) {
    const d = gridStart.add(i, 'day')
    const iso = d.format('YYYY-MM-DD')
    cells.push({
      iso,
      dayNum: d.date(),
      inMonth: d.month() === cursor.value.month(),
      isToday: d.isSame(dayjs(), 'day'),
      items: props.interviews.filter((it) => it.date === iso),
    })
  }
  return cells
})

const rangeLabel = computed(() => {
  if (mode.value === 'week') {
    return `${weekStart.value.format('M月D日')} - ${weekStart.value.add(6, 'day').format('M月D日')}`
  }
  return cursor.value.format('YYYY年M月')
})

// ===== 导航 =====
function prev() {
  if (mode.value === 'week') cursor.value = cursor.value.subtract(7, 'day')
  else cursor.value = cursor.value.subtract(1, 'month')
}
function next() {
  if (mode.value === 'week') cursor.value = cursor.value.add(7, 'day')
  else cursor.value = cursor.value.add(1, 'month')
}
function goToday() {
  cursor.value = dayjs()
}

// ===== 抽屉 =====
const drawerShow = ref(false)
const drawerDate = ref('')
const drawerItems = computed(() => {
  if (!drawerDate.value) return []
  return props.interviews.filter((it) => it.date === drawerDate.value)
})

function openDay(iso: string) {
  drawerDate.value = iso
  drawerShow.value = true
  emit('openDrawer', iso)
}

function onItemClick(item: ScheduleItem) {
  emit('itemClick', item)
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
  gap: var(--space-3);
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

.weekly-schedule__segmented {
  display: inline-flex;
  align-items: center;
  background: var(--color-surface-sunk);
  border-radius: var(--radius-sm);
  padding: 2px;
  gap: 2px;
}

.weekly-schedule__segment {
  appearance: none;
  background: transparent;
  border: 0;
  padding: 4px 12px;
  font-size: var(--text-meta);
  color: var(--color-ink-soft);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  font: inherit;
}

.weekly-schedule__segment:hover {
  color: var(--color-ink);
}

.weekly-schedule__segment--active {
  background: var(--color-surface-raised);
  color: var(--color-accent);
  font-weight: 500;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
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
  cursor: pointer;
  transition: background 0.15s;
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

/* Month 模式 */
.month-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.month-grid__header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}

.month-grid__header span {
  text-align: center;
  font-size: 12px;
  color: var(--color-ink-soft);
  padding: 4px 0;
}

.month-grid__body {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  grid-auto-rows: 90px;
  gap: 4px;
}

.month-grid__cell {
  border: 1px solid var(--color-border-hairline);
  border-radius: var(--radius-sm);
  padding: 4px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  background: var(--color-surface-raised);
  transition: background 0.15s;
}

.month-grid__cell:hover {
  background: var(--color-accent-soft);
}

.month-grid__cell--other {
  opacity: 0.4;
}

.month-grid__cell--today {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
}

.month-grid__date {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-ink);
  font-variant-numeric: tabular-nums;
}

.month-grid__dots {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  margin-top: 4px;
  align-items: center;
}

.month-grid__dot {
  width: 6px;
  height: 6px;
  background: var(--color-accent);
  border-radius: 50%;
  display: inline-block;
}

.month-grid__more {
  font-size: 10px;
  color: var(--color-ink-soft);
}
</style>
