<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
defineProps<{ draftId: string }>()
const emit = defineEmits<{
  (e: 'action', draftId: string, action: 'pending' | 'merge' | 'apply' | 'cancel' | 'score'): void
}>()
</script>

<template>
  <div class="occ-actions">
    <button class="occ-btn primary" @click="emit('action', draftId, 'pending')">{ t('components.common.OccupiedActions.s1') }</button>
    <button class="occ-btn" @click="emit('action', draftId, 'merge')">{ t('components.common.OccupiedActions.s2') }</button>
    <button class="occ-btn" @click="emit('action', draftId, 'apply')">{ t('components.common.OccupiedActions.s3') }</button>
    <button class="occ-btn warn" @click="emit('action', draftId, 'cancel')">{ t('components.common.OccupiedActions.s4') }</button>
    <button class="occ-btn" @click="emit('action', draftId, 'score')">{ t('components.common.OccupiedActions.s5') }</button>
  </div>
</template>

<style scoped>
.occ-actions { display: flex; gap: 6px; margin-top: var(--space-2); flex-wrap: wrap; }
.occ-btn {
  padding: 5px var(--space-3);
  border: 1px solid var(--g3);
  border-radius: 8px;
  font-size: var(--fs-10);
  cursor: pointer;
  background: var(--glass-bg-card);
  color: var(--g7);
  transition: 0.15s;
}
.occ-btn:hover { border-color: var(--brand); background: var(--brand-a12); }
.occ-btn.primary { background: var(--brand); color: #fff; border-color: var(--brand); }
.occ-btn.primary:hover { background: var(--ph); }
.occ-btn.warn { color: var(--c-error-deep); border-color: var(--c-error-deep); }
.occ-btn.warn:hover { background: var(--c-error-bg); }
</style>