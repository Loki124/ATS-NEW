<template>
  <div class="job-card" @click="onClick">
    <div class="job-card__head">
      <div class="job-card__title-line">
        <h4 class="job-card__title">{{ job.title }}</h4>
        <span v-if="job.urgent" class="job-card__urgent">{ t('components.dashboard.JobCard.s1') }</span>
      </div>
      <div class="job-card__meta">
        <span class="job-card__meta-item">
          <n-icon :component="LocationOutline" :size="12" />
          {{ job.location || '不限' }}
        </span>
        <span class="job-card__meta-item">
          <n-icon :component="CashOutline" :size="12" />
          {{ job.salary || '面议' }}
        </span>
      </div>
    </div>
    <div class="job-card__foot">
      <span class="job-card__company">{{ job.company || job.department || '内部' }}</span>
      <span class="job-card__count">
        <n-icon :component="PeopleOutline" :size="12" />
        {{ job.candidateCount ?? 0 }} 份
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { LocationOutline, CashOutline, PeopleOutline } from '@vicons/ionicons5'
const { t } = useI18n()

export interface JobCardData {
  id: string
  title: string
  location?: string
  salary?: string
  company?: string
  department?: string
  candidateCount?: number
  urgent?: boolean
}

interface Props {
  job: JobCardData
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'click', job: JobCardData): void
}>()

function onClick() {
  emit('click', props.job)
}
</script>

<style scoped>
.job-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm);
  background: var(--surface);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out);
}

.job-card:hover {
  border-color: var(--brand);
  background: var(--brand-soft);
}

.job-card__head {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.job-card__title-line {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.job-card__title {
  margin: 0;
  font-size: var(--text-body);
  font-weight: 500;
  color: var(--ink);
  line-height: 1.4;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.job-card__urgent {
  background: var(--brand);
  color: white;
  font-size: var(--fs-10);
  font-weight: 500;
  padding: 1px var(--space-1);
  border-radius: var(--radius-sm);
  line-height: 1.2;
}

.job-card__meta {
  display: flex;
  gap: var(--space-3);
  color: var(--ink-faint);
  font-size: var(--text-meta);
}

.job-card__meta-item {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.job-card__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--ink-soft);
  font-size: var(--text-meta);
}

.job-card__company {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.job-card__count {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: var(--brand);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
</style>
