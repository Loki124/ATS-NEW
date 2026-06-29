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
.occ-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.occ-btn {
  padding: 5px 12px;
  border: 1px solid var(--g3);
  border-radius: 8px;
  font-size: 10px;
  cursor: pointer;
  background: #fff;
  color: var(--g7);
  transition: 0.15s;
}
.occ-btn:hover { border-color: var(--p); background: var(--pl); }
.occ-btn.primary { background: var(--p); color: #fff; border-color: var(--p); }
.occ-btn.primary:hover { background: var(--ph); }
.occ-btn.warn { color: #991B1B; border-color: var(--d); }
.occ-btn.warn:hover { background: var(--dl); }
</style>