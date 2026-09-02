<script setup lang="ts">
defineProps<{ draftId: string }>()
const emit = defineEmits<{
  (e: 'action', draftId: string, action: 'pending' | 'merge' | 'apply' | 'cancel' | 'score'): void
}>()
</script>

<template>
  <div class="occ-actions">
    <button class="occ-btn primary" @click="emit('action', draftId, 'pending')">上传至待分配</button>
    <button class="occ-btn" @click="emit('action', draftId, 'merge')">合并至已有简历</button>
    <button class="occ-btn" @click="emit('action', draftId, 'apply')">申请分配</button>
    <button class="occ-btn warn" @click="emit('action', draftId, 'cancel')">取消上传</button>
    <button class="occ-btn" @click="emit('action', draftId, 'score')">模拟评分</button>
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