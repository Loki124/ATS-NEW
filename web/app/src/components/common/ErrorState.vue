<template>
  <div class="error-state" :class="[`is-${type}`, { 'is-compact': compact }]">
    <div class="error-icon" aria-hidden="true">{{ icon || '⚠️' }}</div>
    <h3 class="error-title">{{ title || '加载失败' }}</h3>
    <p v-if="description" class="error-desc">{{ description }}</p>

    <div v-if="errorCode || detail" class="error-code">
      <button class="error-code-toggle" type="button" @click="showDetail = !showDetail">
        {{ showDetail ? '收起错误详情' : '查看错误详情' }}
      </button>
      <pre v-if="showDetail" class="error-code-body">{{ errorCode || detail }}</pre>
    </div>

    <div v-if="retryLabel || $slots.action" class="error-actions">
      <button v-if="retryLabel" class="btn btn-primary" @click="$emit('retry')">{{ retryLabel }}</button>
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

withDefaults(
  defineProps<{
    type?: 'page' | 'section' | 'inline'
    icon?: string
    title?: string
    description?: string
    /** 结构化错误码（如 ATS-ERR-xxx），与 detail 二选一展示 */
    errorCode?: string
    /** 原始错误文本（如 err.stack / JSON），折叠展示 */
    detail?: string
    retryLabel?: string
    compact?: boolean
  }>(),
  { type: 'section', compact: false },
)

defineEmits<{ (e: 'retry'): void }>()

const showDetail = ref(false)
</script>

<style scoped>
.error-state {
  display: flex; flex-direction: column; align-items: center;
  gap: var(--space-3);
  padding: var(--space-8) var(--space-4);
  text-align: center;
}
.error-state.is-page { min-height: 60vh; justify-content: center; }
.error-state.is-inline { padding: var(--space-3); }
.error-state.is-compact { gap: var(--space-2); padding: var(--space-4); }

.error-icon { font-size: 44px; line-height: 1; opacity: .85; }
.error-state.is-compact .error-icon { font-size: 28px; }

.error-title { font-size: var(--text-h3); font-weight: 600; color: var(--ink); margin: 0; }
.error-state.is-compact .error-title { font-size: var(--text-body); }

.error-desc { color: var(--ink-soft); font-size: var(--text-body); margin: 0; max-width: 42ch; }

.error-code { width: 100%; max-width: 42ch; }
.error-code-toggle {
  background: none; border: none; color: var(--brand, #6366f1);
  font-size: var(--text-sm); cursor: pointer; padding: var(--space-1);
}
.error-code-body {
  margin: var(--space-2) 0 0; padding: var(--space-2);
  background: var(--surface-2, #f4f4f5); border-radius: var(--radius-sm, 8px);
  font-size: var(--text-xs); color: var(--ink-soft);
  text-align: left; white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow: auto;
}

.error-actions { margin-top: var(--space-3); }

.btn {
  display: inline-flex; align-items: center; justify-content: center;
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md, 10px); border: 1px solid transparent;
  font-size: var(--text-body); cursor: pointer;
}
.btn-primary { background: var(--brand, #6366f1); color: #fff; }
.btn-primary:hover { filter: brightness(1.05); }
</style>
