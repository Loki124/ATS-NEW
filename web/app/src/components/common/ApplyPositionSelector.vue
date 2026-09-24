<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
const props = defineProps<{ positions: string[]; modelValue: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', val: string): void }>()

function select(pos: string) {
  emit('update:modelValue', pos)
}
</script>

<template>
  <div class="apply-pos">
    <div class="apply-pos-title">{{ t('components.common.ApplyPositionSelector.s1') }}</div>
    <div class="apply-pos-list">
      <div
        v-for="p in positions"
        :key="p"
        :class="['apply-pos-item', { sel: modelValue === p }]"
        @click="select(p)"
      >
        {{ p }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.apply-pos {
  margin-top: var(--space-2);
  padding: 10px var(--space-3);
  background: var(--c-info-soft);
  border: 1px solid var(--c-info-bg);
  border-radius: 8px;
}
.apply-pos-title { font-size: 11px; font-weight: 600; color: var(--c-info-deep); margin-bottom: 6px; }
.apply-pos-list { display: flex; flex-wrap: wrap; gap: 6px; }
.apply-pos-item {
  padding: var(--space-1) 10px;
  border: 1px solid var(--g3);
  border-radius: 8px;
  cursor: pointer;
  font-size: var(--fs-10);
  background: var(--glass-bg-card);
  transition: 0.15s;
}
.apply-pos-item:hover { border-color: var(--brand); }
.apply-pos-item.sel { border-color: var(--brand); background: var(--brand-a12); color: var(--brand); font-weight: 500; }
</style>
