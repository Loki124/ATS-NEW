<script setup lang="ts">
import type { DuplicateInfo } from '@/api/addCandidate'

defineProps<{ info: Partial<DuplicateInfo>; status: 'unocc' | 'occupied' }>()
</script>

<template>
  <div class="dup-card">
    <div class="dup-row">
      <span class="dup-label">已有简历ID</span>
      <span class="dup-value">{{ info.existing_resume_id }}</span>
    </div>
    <div class="dup-row">
      <span class="dup-label">创建时间</span>
      <span class="dup-value">{{ info.created_at }}</span>
    </div>
    <div class="dup-row">
      <span class="dup-label">历史应聘</span>
      <span class="dup-value">{{ info.history }}</span>
    </div>
    <div class="dup-row">
      <span class="dup-label">当前状态</span>
      <span class="dup-value" :style="{ color: status === 'occupied' ? '#991B1B' : '#92400E' }">
        {{ info.cur_status }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.dup-card {
  border: 1px solid #FDE68A;
  border-radius: 8px;
  padding: 10px 14px;
  background: #FFFDF5;
  font-size: 11px;
}
.dup-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
.dup-label { color: var(--g5); }
.dup-value { font-weight: 500; }
</style>