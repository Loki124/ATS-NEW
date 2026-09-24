<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { DuplicateInfo } from '@/api/addCandidate'
const { t } = useI18n()

// 2026-06-29 花无缺: Step1Single.vue (line 114) 传 resume.status (Status 全集: processing|clean|unocc|occupied).
//   旧 prop 只接 unocc|occupied, TS2322 fail. 改成接全 Status union,
//   内部 :style 只看 'occupied', 其他值走 else 路径.
defineProps<{ info: Partial<DuplicateInfo>; status: 'processing' | 'clean' | 'unocc' | 'occupied' }>()
</script>

<template>
  <div class="dup-card">
    <div class="dup-row">
      <span class="dup-label">{{ t('components.common.DuplicateInfoCard.s1') }}</span>
      <span class="dup-value">{{ info.existing_resume_id }}</span>
    </div>
    <div class="dup-row">
      <span class="dup-label">{{ t('components.common.DuplicateInfoCard.s2') }}</span>
      <span class="dup-value">{{ info.created_at }}</span>
    </div>
    <div class="dup-row">
      <span class="dup-label">{{ t('components.common.DuplicateInfoCard.s3') }}</span>
      <span class="dup-value">{{ info.history }}</span>
    </div>
    <div class="dup-row">
      <span class="dup-label">{{ t('components.common.DuplicateInfoCard.s4') }}</span>
      <span class="dup-value" :style="{ color: status === 'occupied' ? 'var(--c-error-deep)' : 'var(--c-warning-deep)' }">
        {{ info.cur_status }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.dup-card {
  border: 1px solid var(--c-warning-bg);
  border-radius: 8px;
  padding: 10px 14px;
  background: var(--g1);
  font-size: 11px;
}
.dup-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
.dup-label { color: var(--g5); }
.dup-value { font-weight: 500; }
</style>