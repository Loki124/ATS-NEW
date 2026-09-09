<script setup lang="ts">
import { computed } from 'vue';

interface OptionItem {
  value: string;
  label: string;
}

interface Props {
  options: OptionItem[];
  multiple?: boolean;
  modelValue?: string | string[];
  disabled?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  options: () => [],
  multiple: false,
  modelValue: () => '' as string | string[],
  disabled: false,
});
const emit = defineEmits<{ (e: 'update:modelValue', v: string | string[]): void }>();

const selected = computed<string[]>(() =>
  Array.isArray(props.modelValue) ? props.modelValue : props.modelValue ? [props.modelValue as string] : [],
);

function toggle(value: string) {
  if (props.disabled) return;
  if (props.multiple) {
    const set = new Set(selected.value);
    if (set.has(value)) set.delete(value);
    else set.add(value);
    emit('update:modelValue', Array.from(set));
  } else {
    emit('update:modelValue', value);
  }
}

function isSelected(value: string) {
  return selected.value.includes(value);
}
</script>

<template>
  <div class="field-list-options">
    <div class="flo-list" role="listbox" :aria-multiselectable="multiple">
      <button
        v-for="opt in options"
        :key="opt.value"
        type="button"
        class="flo-item"
        :class="{ 'is-selected': isSelected(opt.value) }"
        :disabled="disabled"
        :aria-pressed="isSelected(opt.value)"
        @click="toggle(opt.value)"
      >
        <span class="flo-indicator" :class="{ 'is-multi': multiple }">
          <span v-if="isSelected(opt.value)" class="flo-dot" />
        </span>
        <span class="flo-label">{{ opt.label }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
/* container-type 使内部 @container 查询基于「本组件宽度」而非视口宽度 */
.field-list-options {
  container-type: inline-size;
  width: 100%;
}
.flo-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
  align-items: stretch;
}
.flo-item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2, 8px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
  background: var(--color-bg-subtle, #f9fafb);
  color: var(--text-color-base, #111827);
  font-size: var(--text-sm, 14px);
  line-height: 1.4;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.flo-item:hover:not(:disabled) {
  border-color: var(--primary-color, #2080f0);
}
.flo-item.is-selected {
  border-color: var(--primary-color, #2080f0);
  background: color-mix(in srgb, var(--primary-color, #2080f0) 10%, #ffffff);
}
.flo-item:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.flo-indicator {
  width: 14px;
  height: 14px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.flo-indicator.is-multi {
  border-radius: 4px;
}
.flo-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary-color, #2080f0);
}
.flo-indicator.is-multi .flo-dot {
  border-radius: 2px;
}

/* 容器宽度自适应: 窄容器(<=380px)切换为纵向单列, 宽容器横向换行 */
@container (max-width: 380px) {
  .flo-list {
    flex-direction: column;
    align-items: stretch;
  }
  .flo-item {
    width: 100%;
  }
}
</style>
