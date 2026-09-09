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
.field-list-options {
  width: 100%;
}
.flo-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
  align-items: center;
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
  white-space: nowrap;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
  /* 保证每个选项至少有个舒适宽度，且在极窄容器里仍能占满一行 */
  min-width: 80px;
  flex: 0 1 auto;
}
.flo-item:hover:not(:disabled) {
  border-color: var(--primary-color, #2080f0);
}
.flo-item.is-selected {
  border-color: var(--primary-color, #2080f0);
  background: color-mix(in srgb, var(--primary-color, #2080f0) 10%, #ffffff);
  box-shadow: 0 0 0 1px var(--primary-color, #2080f0) inset;
}
.flo-item:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.flo-indicator {
  width: 16px;
  height: 16px;
  border: 1px solid var(--border-color, #d1d5db);
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  background: #ffffff;
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
</style>
