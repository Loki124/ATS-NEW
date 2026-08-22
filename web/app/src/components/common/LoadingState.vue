<template>
  <!-- page: 全屏玻璃 spinner -->
  <div v-if="type === 'page'" class="loading-page glass-panel">
    <n-spin :size="48" :show="true">
      <template #description>
        <span class="loading-text">{{ text || '加载中...' }}</span>
      </template>
    </n-spin>
  </div>

  <!-- section: 卡片骨架 -->
  <div v-else-if="type === 'section'" class="loading-section">
    <n-skeleton :height="height || 120" :sharp="false" />
  </div>

  <!-- button: 按钮内 spinner -->
  <span v-else-if="type === 'button'" class="loading-btn" :aria-busy="true">
    <n-spin :size="14" :show="true" />
    <span class="ml-2">{{ text || '处理中' }}</span>
  </span>
</template>

<script setup lang="ts">
defineProps<{
  type?: 'page' | 'section' | 'button'
  text?: string
  height?: number
}>()
</script>

<style scoped>
.loading-page {
  display: flex; align-items: center; justify-content: center;
  min-height: 60vh; padding: var(--space-8);
}
.loading-text { color: var(--ink-soft); font-size: var(--text-body); }
.loading-section { padding: var(--space-4); }
.loading-btn { display: inline-flex; align-items: center; }
.ml-2 { margin-left: 8px; }
</style>